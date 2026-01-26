import os
import yaml
import logging
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import httpx
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from jose import JWTError, jwt

# Configuration
HA_URL = os.getenv("HA_URL", "http://supervisor/core")
HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("SUPERVISOR_TOKEN")
# Generate JWT secret automatically
JWT_SECRET = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

logger = logging.getLogger(__name__)
logger.info(f"HA_URL: {HA_URL}")
logger.info(f"HA_TOKEN: {'***' if HA_TOKEN else 'NOT SET'}")

# In-memory storage (use database in production)
dashboard_config = {
    "user_entities": [],
    "admin_entities": [],
    "links": []
}

# Load dashboard config from file
def load_dashboard_config():
    try:
        with open('dashboard_config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {"user_entities": [], "admin_entities": []}
    except FileNotFoundError:
        return {"user_entities": [], "admin_entities": [], "links": []}

# Save dashboard config to file
def save_dashboard_config():
    with open('dashboard_config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(dashboard_config, f, default_flow_style=False, indent=2, allow_unicode=True)

# Load config on startup
dashboard_config = load_dashboard_config()
# Ensure links key exists for backward compatibility
if "links" not in dashboard_config:
    dashboard_config["links"] = []

# Setup
app = FastAPI(title="Building Dashboard API")
security = HTTPBearer()

# Serve static files first
app.mount("/src", StaticFiles(directory="/var/www/src"), name="src")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple password hashing
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": hash_password(os.getenv("ADMIN_PASSWORD", "admin123")),
        "role": "admin"
    }
}

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class EntityConfig(BaseModel):
    entity_id: str
    display_name: str
    icon: Optional[str] = None
    entity_type: str  # "sensor", "binary_sensor", "switch", "input_boolean"

class DashboardEntity(BaseModel):
    entity_id: str
    display_name: str
    icon: str
    state: str
    entity_type: str
    controllable: bool = False

class AddEntityRequest(BaseModel):
    entity_id: str
    display_name: str
    dashboard: str  # "user" or "admin"
    icon: Optional[str] = None

class AddLinkRequest(BaseModel):
    text: str
    url: Optional[str] = None

class ToggleRequest(BaseModel):
    action: str

# Auth functions
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[dict]:
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return USERS_DB.get(username)
    except JWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = USERS_DB.get(username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Home Assistant client
class HAClient:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def get_states(self) -> Dict[str, Any]:
        url = f"{HA_URL}/api/states"
        logger.info(f"Requesting HA states from: {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"HA request failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=503, detail="Home Assistant unavailable")
            return {state["entity_id"]: state for state in response.json()}
    
    async def get_entity_state(self, entity_id: str) -> Dict[str, Any]:
        url = f"{HA_URL}/api/states/{entity_id}"
        logger.info(f"Requesting HA entity from: {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Entity not found")
            if response.status_code != 200:
                logger.error(f"HA request failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=503, detail="Home Assistant unavailable")
            return response.json()
    
    async def toggle_entity(self, entity_id: str, action: str = "toggle"):
        domain = entity_id.split(".")[0]
        if domain not in ["switch", "input_boolean", "light"]:
            raise HTTPException(status_code=400, detail="Entity not controllable")
        
        service_data = {"entity_id": entity_id}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HA_URL}/api/services/{domain}/{action}",
                headers=self.headers,
                json=service_data
            )
            if response.status_code not in [200, 201]:
                raise HTTPException(status_code=503, detail="Failed to control entity")

ha_client = HAClient()

# Helper functions
def is_controllable_entity(entity_id: str) -> bool:
    domain = entity_id.split(".")[0]
    return domain in ["switch", "input_boolean", "light"]

def get_entity_icon(entity_id: str, attributes: dict) -> str:
    domain = entity_id.split(".")[0]
    if "icon" in attributes:
        return attributes["icon"]
    
    # Default icons by domain
    icons = {
        "sensor": "mdi:gauge",
        "binary_sensor": "mdi:checkbox-marked-circle",
        "switch": "mdi:toggle-switch",
        "input_boolean": "mdi:toggle-switch",
        "light": "mdi:lightbulb"
    }
    return icons.get(domain, "mdi:help")

# API Endpoints
@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = USERS_DB.get(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["username"]})
    logger.info(f"User {request.username} logged in")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me")
async def get_me(user: Optional[dict] = Depends(get_optional_user)):
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "username": user["username"], "role": user["role"]}

@app.get("/api/dashboard")
async def get_user_dashboard():
    """Get user dashboard entities (public access)"""
    try:
        states = await ha_client.get_states()
        entities = []
        
        for entity_config in dashboard_config["user_entities"]:
            entity_id = entity_config["entity_id"]
            if entity_id in states:
                state = states[entity_id]
                entities.append(DashboardEntity(
                    entity_id=entity_id,
                    display_name=entity_config["display_name"],
                    icon=entity_config.get("icon") or get_entity_icon(entity_id, state["attributes"]),
                    state=state["state"],
                    entity_type=entity_id.split(".")[0],
                    controllable=False
                ))
        
        return {"entities": entities, "last_updated": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error(f"Failed to get user dashboard: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/admin/dashboard")
async def get_admin_dashboard(admin: dict = Depends(require_admin)):
    """Get admin dashboard entities"""
    try:
        states = await ha_client.get_states()
        entities = []
        
        for entity_config in dashboard_config["admin_entities"]:
            entity_id = entity_config["entity_id"]
            if entity_id in states:
                state = states[entity_id]
                entities.append(DashboardEntity(
                    entity_id=entity_id,
                    display_name=entity_config["display_name"],
                    icon=entity_config.get("icon") or get_entity_icon(entity_id, state["attributes"]),
                    state=state["state"],
                    entity_type=entity_id.split(".")[0],
                    controllable=is_controllable_entity(entity_id)
                ))
        
        return {"entities": entities, "last_updated": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        logger.error(f"Failed to get admin dashboard: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/admin/entities/search")
async def search_entities(query: str = "", admin: dict = Depends(require_admin)):
    """Search available HA entities"""
    try:
        states = await ha_client.get_states()
        results = []
        
        for entity_id, state in states.items():
            if query.lower() in entity_id.lower() or query.lower() in state["attributes"].get("friendly_name", "").lower():
                results.append({
                    "entity_id": entity_id,
                    "friendly_name": state["attributes"].get("friendly_name", entity_id),
                    "domain": entity_id.split(".")[0],
                    "state": state["state"],
                    "icon": get_entity_icon(entity_id, state["attributes"])
                })
        
        return {"entities": results[:50]}  # Limit results
    except Exception as e:
        logger.error(f"Failed to search entities: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/admin/entities/add")
async def add_entity(request: AddEntityRequest, admin: dict = Depends(require_admin)):
    """Add entity to dashboard"""
    try:
        # Verify entity exists
        await ha_client.get_entity_state(request.entity_id)
        
        entity_config = {
            "entity_id": request.entity_id,
            "display_name": request.display_name,
            "icon": request.icon
        }
        
        if request.dashboard == "user":
            dashboard_config["user_entities"].append(entity_config)
        elif request.dashboard == "admin":
            dashboard_config["admin_entities"].append(entity_config)
        else:
            raise HTTPException(status_code=400, detail="Invalid dashboard type")
        
        # Save to file
        save_dashboard_config()
        
        logger.info(f"Admin {admin['username']} added entity {request.entity_id} to {request.dashboard} dashboard")
        return {"success": True, "message": f"Entity added to {request.dashboard} dashboard"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add entity: {e}")
        raise HTTPException(status_code=503, detail="Failed to add entity")

@app.delete("/api/admin/entities/{entity_id}")
async def remove_entity(entity_id: str, dashboard: str, admin: dict = Depends(require_admin)):
    """Remove entity from dashboard"""
    try:
        target_list = dashboard_config.get(f"{dashboard}_entities", [])
        dashboard_config[f"{dashboard}_entities"] = [
            e for e in target_list if e["entity_id"] != entity_id
        ]
        
        # Save to file
        save_dashboard_config()
        
        logger.info(f"Admin {admin['username']} removed entity {entity_id} from {dashboard} dashboard")
        return {"success": True, "message": f"Entity removed from {dashboard} dashboard"}
    except Exception as e:
        logger.error(f"Failed to remove entity: {e}")
        raise HTTPException(status_code=503, detail="Failed to remove entity")

@app.get("/api/links")
async def get_links():
    """Get links (public access)"""
    return {"links": dashboard_config["links"]}

@app.post("/api/admin/links/add")
async def add_link(request: AddLinkRequest, admin: dict = Depends(require_admin)):
    """Add link"""
    try:
        link_config = {
            "text": request.text,
            "url": request.url
        }
        
        dashboard_config["links"].append(link_config)
        save_dashboard_config()
        
        logger.info(f"Admin {admin['username']} added link: {request.text}")
        return {"success": True, "message": "Link added"}
    except Exception as e:
        logger.error(f"Failed to add link: {e}")
        raise HTTPException(status_code=503, detail="Failed to add link")

@app.delete("/api/admin/links/{link_index}")
async def remove_link(link_index: int, admin: dict = Depends(require_admin)):
    """Remove link"""
    try:
        if 0 <= link_index < len(dashboard_config["links"]):
            removed_link = dashboard_config["links"].pop(link_index)
            save_dashboard_config()
            logger.info(f"Admin {admin['username']} removed link: {removed_link['text']}")
            return {"success": True, "message": "Link removed"}
        else:
            raise HTTPException(status_code=404, detail="Link not found")
    except Exception as e:
        logger.error(f"Failed to remove link: {e}")
        raise HTTPException(status_code=503, detail="Failed to remove link")

@app.post("/api/admin/toggle/{entity_id}")
async def toggle_entity(entity_id: str, request: ToggleRequest, admin: dict = Depends(require_admin)):
    """Toggle controllable entity (admin only)"""
    if not is_controllable_entity(entity_id):
        raise HTTPException(status_code=400, detail="Entity not controllable")
    
    if request.action not in ["toggle", "turn_on", "turn_off"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    try:
        await ha_client.toggle_entity(entity_id, request.action)
        logger.info(f"Admin {admin['username']} performed {request.action} on {entity_id}")
        return {"success": True, "message": f"Entity {entity_id} {request.action} successful"}
    except Exception as e:
        logger.error(f"Failed to toggle entity {entity_id}: {e}")
        raise HTTPException(status_code=503, detail="Failed to control entity")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Root route must be last to catch all remaining requests
@app.get("/")
async def read_index():
    return FileResponse('/var/www/public/index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)