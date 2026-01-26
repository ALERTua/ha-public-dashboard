import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import httpx
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# Configuration
HA_URL = os.getenv("HA_URL", "http://homeassistant:8123")
HA_TOKEN = os.getenv("HA_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# Whitelisted entities (SECURITY CRITICAL)
READABLE_ENTITIES = {
    "sensor.building_power_status",
    "sensor.water_system_status", 
    "sensor.heating_system_status",
    "binary_sensor.building_occupied"
}

ADMIN_CONTROLLABLE_ENTITIES = {
    "input_boolean.emergency_lighting",
    "input_boolean.water_pump_override",
    "input_boolean.heating_boost"
}

# User database (in production, use proper database)
USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "role": "admin"
    },
    "user": {
        "username": "user", 
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "role": "user"
    }
}

# Setup
app = FastAPI(title="Building Dashboard API")
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class UserInfo(BaseModel):
    username: str
    role: str

class BuildingStatus(BaseModel):
    power: str
    water: str
    heating: str
    occupied: bool
    last_updated: str

class ToggleRequest(BaseModel):
    action: str  # "toggle", "turn_on", "turn_off"

# Auth functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

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
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{HA_URL}/api/states", headers=self.headers)
            if response.status_code != 200:
                raise HTTPException(status_code=503, detail="Home Assistant unavailable")
            return {state["entity_id"]: state for state in response.json()}
    
    async def toggle_entity(self, entity_id: str, action: str = "toggle"):
        if entity_id not in ADMIN_CONTROLLABLE_ENTITIES:
            raise HTTPException(status_code=400, detail="Entity not controllable")
        
        service_data = {"entity_id": entity_id}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HA_URL}/api/services/input_boolean/{action}",
                headers=self.headers,
                json=service_data
            )
            if response.status_code not in [200, 201]:
                raise HTTPException(status_code=503, detail="Failed to control entity")

ha_client = HAClient()

# API Endpoints
@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = USERS_DB.get(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["username"]})
    logger.info(f"User {request.username} logged in")
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserInfo)
async def get_me(user: dict = Depends(get_current_user)):
    return {"username": user["username"], "role": user["role"]}

@app.get("/api/status", response_model=BuildingStatus)
async def get_building_status():
    """Public endpoint - no auth required"""
    try:
        states = await ha_client.get_states()
        
        # Extract only whitelisted entities
        power_state = states.get("sensor.building_power_status", {}).get("state", "unknown")
        water_state = states.get("sensor.water_system_status", {}).get("state", "unknown") 
        heating_state = states.get("sensor.heating_system_status", {}).get("state", "unknown")
        occupied_state = states.get("binary_sensor.building_occupied", {}).get("state", "off") == "on"
        
        return BuildingStatus(
            power=power_state,
            water=water_state,
            heating=heating_state,
            occupied=occupied_state,
            last_updated=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to get building status: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.get("/api/admin/entities")
async def get_admin_entities(admin: dict = Depends(require_admin)):
    """Get controllable entities for admin"""
    try:
        states = await ha_client.get_states()
        entities = {}
        
        for entity_id in ADMIN_CONTROLLABLE_ENTITIES:
            if entity_id in states:
                state = states[entity_id]
                entities[entity_id] = {
                    "state": state["state"],
                    "friendly_name": state["attributes"].get("friendly_name", entity_id),
                    "icon": state["attributes"].get("icon", "mdi:help")
                }
        
        return entities
    except Exception as e:
        logger.error(f"Failed to get admin entities: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/admin/toggle/{entity_id}")
async def toggle_entity(entity_id: str, request: ToggleRequest, admin: dict = Depends(require_admin)):
    """Toggle input_boolean entity (admin only)"""
    if entity_id not in ADMIN_CONTROLLABLE_ENTITIES:
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
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)