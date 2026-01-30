"""Public Dashboard FastAPI application."""

import hashlib
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import httpx
import yaml
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Configuration with environment variable defaults
HA_URL = os.getenv("HA_URL", "http://supervisor/core")
HA_TOKEN = os.getenv("HA_TOKEN") or os.getenv("SUPERVISOR_TOKEN")
JWT_SECRET = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

# Path configuration - use environment variables for flexibility
WWW_SRC_DIR = os.getenv("WWW_SRC_DIR", "/var/www/src")
WWW_PUBLIC_DIR = os.getenv("WWW_PUBLIC_DIR", "/var/www/build")
CONFIG_DIR = os.getenv("CONFIG_DIR", "/config")
CONFIG_FILE = str(Path(CONFIG_DIR) / "public_dashboard_config.yaml")

logger = logging.getLogger(__name__)
logger.info("HA_URL: %s", HA_URL)
logger.info("HA_TOKEN: %s", "***" if HA_TOKEN else "NOT SET")


def load_dashboard_config() -> dict:
    """Load dashboard config from file."""
    config_path = Path(CONFIG_FILE)
    try:
        with config_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {"user_entities": [], "admin_entities": []}
    except FileNotFoundError:
        # Create config directory if it doesn't exist
        Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
        return {"user_entities": [], "admin_entities": [], "links": []}


def save_dashboard_config() -> None:
    """Save dashboard config to file."""
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    config_path = Path(CONFIG_FILE)
    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            dashboard_config, f, default_flow_style=False, indent=2, allow_unicode=True
        )


# Load config on startup
dashboard_config = load_dashboard_config()
# Ensure links key exists for backward compatibility
if "links" not in dashboard_config:
    dashboard_config["links"] = []

# Setup
app = FastAPI(title="Public Dashboard API")
security = HTTPBearer()

# Serve static files - check if directory exists first
www_src_dir = Path(WWW_SRC_DIR)
if www_src_dir.exists():
    app.mount("/src", StaticFiles(directory=www_src_dir.absolute()), name="src")
else:
    logger.warning("WWW_SRC_DIR not found: %s", www_src_dir)

# Serve built static files
static_dir = Path(WWW_PUBLIC_DIR) / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir.absolute()), name="static")
else:
    logger.warning("Static files not found: %s", static_dir)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,  # ty:ignore[invalid-argument-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)


def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return hash_password(plain_password) == hashed_password


USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": hash_password(os.getenv("ADMIN_PASSWORD", "admin123")),
        "role": "admin",
    }
}


# Models
class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str


class EntityConfig(BaseModel):
    """Entity configuration model."""

    entity_id: str
    display_name: str
    icon: str | None = None
    entity_type: str  # "sensor", "binary_sensor", "switch", "input_boolean"


class DashboardEntity(BaseModel):
    """Dashboard entity model."""

    entity_id: str
    display_name: str
    icon: str
    state: str
    entity_type: str
    controllable: bool = False


class AddEntityRequest(BaseModel):
    """Add entity request model."""

    entity_id: str
    display_name: str
    dashboard: str  # "user" or "admin"
    icon: str | None = None


class AddLinkRequest(BaseModel):
    """Add link request model."""

    text: str
    url: str | None = None


class ToggleRequest(BaseModel):
    """Toggle request model."""

    action: str


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
    ] = None,
) -> dict | None:
    """Get optional user from token."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        return USERS_DB.get(username)
    except JWTError:
        return None


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """Get current user from token."""
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = USERS_DB.get(username)
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        return user  # noqa: TRY300
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Require admin role."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class HAClient:
    """Home Assistant client."""

    def __init__(self) -> None:
        """Initialize HA client."""
        self.headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

    async def get_states(self) -> dict[str, Any]:
        """Get all HA states."""
        url = f"{HA_URL}/api/states"
        logger.info("Requesting HA states from: %s", url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code != 200:  # noqa: PLR2004
                logger.exception(
                    "HA request failed: %s - %s", response.status_code, response.text
                )
                raise HTTPException(
                    status_code=503, detail="Home Assistant unavailable"
                ) from None
            return {state["entity_id"]: state for state in response.json()}

    async def get_entity_state(self, entity_id: str) -> dict[str, Any]:
        """Get single entity state."""
        url = f"{HA_URL}/api/states/{entity_id}"
        logger.info("Requesting HA entity from: %s", url)
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 404:  # noqa: PLR2004
                raise HTTPException(status_code=404, detail="Entity not found")
            if response.status_code != 200:  # noqa: PLR2004
                logger.exception(
                    "HA request failed: %s - %s", response.status_code, response.text
                )
                raise HTTPException(
                    status_code=503, detail="Home Assistant unavailable"
                ) from None
            return response.json()

    async def toggle_entity(self, entity_id: str, action: str = "toggle") -> None:
        """Toggle entity state."""
        domain = entity_id.split(".")[0]
        if domain not in ["switch", "input_boolean", "light"]:
            raise HTTPException(status_code=400, detail="Entity not controllable")

        service_data = {"entity_id": entity_id}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HA_URL}/api/services/{domain}/{action}",
                headers=self.headers,
                json=service_data,
            )
            if response.status_code not in [200, 201]:
                raise HTTPException(status_code=503, detail="Failed to control entity")


ha_client = HAClient()


def _raise_invalid_dashboard_error() -> None:
    """Raise invalid dashboard type error."""
    raise HTTPException(status_code=400, detail="Invalid dashboard type")


def _raise_link_not_found_error() -> None:
    """Raise link not found error."""
    raise HTTPException(status_code=404, detail="Link not found")


def is_controllable_entity(entity_id: str) -> bool:
    """Check if entity is controllable."""
    domain = entity_id.split(".")[0]
    return domain in ["switch", "input_boolean", "light"]


def get_entity_icon(entity_id: str, attributes: dict) -> str:
    """Get entity icon."""
    domain = entity_id.split(".")[0]
    if "icon" in attributes:
        return attributes["icon"]

    # Default icons by domain
    icons = {
        "sensor": "mdi:gauge",
        "binary_sensor": "mdi:checkbox-marked-circle",
        "switch": "mdi:toggle-switch",
        "input_boolean": "mdi:toggle-switch",
        "light": "mdi:lightbulb",
    }
    return icons.get(domain, "mdi:help")


# API Endpoints
@app.post("/api/login")
async def login(request: LoginRequest) -> TokenResponse:
    """User login endpoint."""
    user = USERS_DB.get(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user["username"]})
    logger.info("User %s logged in", request.username)
    return TokenResponse(access_token=access_token, token_type="bearer")  # noqa: S106


@app.get("/api/me")
async def get_me(
    user: Annotated[dict | None, Depends(get_optional_user)] = None,
) -> dict:
    """Get current user info."""
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "username": user["username"], "role": user["role"]}


@app.get("/api/dashboard")
async def get_user_dashboard() -> dict:
    """Get user dashboard entities (public access)."""
    try:
        states = await ha_client.get_states()
        entities = []

        for entity_config in dashboard_config["user_entities"]:
            entity_id = entity_config["entity_id"]
            if entity_id in states:
                state = states[entity_id]
                entities.append(
                    DashboardEntity(
                        entity_id=entity_id,
                        display_name=entity_config["display_name"],
                        icon=entity_config.get("icon")
                        or get_entity_icon(entity_id, state["attributes"]),
                        state=state["state"],
                        entity_type=entity_id.split(".")[0],
                        controllable=False,
                    )
                )

        return {"entities": entities, "last_updated": datetime.now(UTC).isoformat()}
    except Exception:
        logger.exception("Failed to get user dashboard")
        raise HTTPException(status_code=503, detail="Service unavailable") from None


@app.get("/api/admin/dashboard")
async def get_admin_dashboard(_admin: Annotated[dict, Depends(require_admin)]) -> dict:
    """Get admin dashboard entities."""
    try:
        states = await ha_client.get_states()
        entities = []

        for entity_config in dashboard_config["admin_entities"]:
            entity_id = entity_config["entity_id"]
            if entity_id in states:
                state = states[entity_id]
                entities.append(
                    DashboardEntity(
                        entity_id=entity_id,
                        display_name=entity_config["display_name"],
                        icon=entity_config.get("icon")
                        or get_entity_icon(entity_id, state["attributes"]),
                        state=state["state"],
                        entity_type=entity_id.split(".")[0],
                        controllable=is_controllable_entity(entity_id),
                    )
                )

        return {"entities": entities, "last_updated": datetime.now(UTC).isoformat()}
    except Exception:
        logger.exception("Failed to get admin dashboard")
        raise HTTPException(status_code=503, detail="Service unavailable") from None


@app.get("/api/admin/entities/search")
async def search_entities(
    query: str = "", _admin: Annotated[dict | None, Depends(require_admin)] = None
) -> dict:
    """Search available HA entities."""
    try:
        states = await ha_client.get_states()
        results = []

        for entity_id, state in states.items():
            if (
                query.lower() in entity_id.lower()
                or query.lower() in state["attributes"].get("friendly_name", "").lower()
            ):
                results.append(
                    {
                        "entity_id": entity_id,
                        "friendly_name": state["attributes"].get(
                            "friendly_name", entity_id
                        ),
                        "domain": entity_id.split(".")[0],
                        "state": state["state"],
                        "icon": get_entity_icon(entity_id, state["attributes"]),
                    }
                )

        return {"entities": results[:50]}  # Limit results
    except Exception:
        logger.exception("Failed to search entities")
        raise HTTPException(status_code=503, detail="Service unavailable") from None


@app.post("/api/admin/entities/add")
async def add_entity(
    request: AddEntityRequest, admin: Annotated[dict, Depends(require_admin)]
) -> dict:
    """Add entity to dashboard."""
    try:
        # Verify entity exists
        await ha_client.get_entity_state(request.entity_id)

        entity_config = {
            "entity_id": request.entity_id,
            "display_name": request.display_name,
            "icon": request.icon,
        }

        if request.dashboard == "user":
            dashboard_config["user_entities"].append(entity_config)
        elif request.dashboard == "admin":
            dashboard_config["admin_entities"].append(entity_config)
        else:
            _raise_invalid_dashboard_error()

        # Save to file
        save_dashboard_config()

        logger.info(
            "Admin %s added entity %s to %s dashboard",
            admin["username"],
            request.entity_id,
            request.dashboard,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to add entity")
        raise HTTPException(status_code=503, detail="Failed to add entity") from None
    else:
        return {
            "success": True,
            "message": f"Entity added to {request.dashboard} dashboard",
        }


@app.delete("/api/admin/entities/{entity_id}")
async def remove_entity(
    entity_id: str,
    dashboard: str,
    admin: Annotated[dict, Depends(require_admin)],
) -> dict:
    """Remove entity from dashboard."""
    try:
        target_list = dashboard_config.get(f"{dashboard}_entities", [])
        dashboard_config[f"{dashboard}_entities"] = [
            e for e in target_list if e["entity_id"] != entity_id
        ]

        # Save to file
        save_dashboard_config()

        logger.info(
            "Admin %s removed entity %s from %s dashboard",
            admin["username"],
            entity_id,
            dashboard,
        )
    except Exception:
        logger.exception("Failed to remove entity")
        raise HTTPException(status_code=503, detail="Failed to remove entity") from None
    else:
        return {
            "success": True,
            "message": f"Entity removed from {dashboard} dashboard",
        }


@app.get("/api/links")
async def get_links() -> dict:
    """Get links (public access)."""
    return {"links": dashboard_config["links"]}


@app.post("/api/admin/links/add")
async def add_link(
    request: AddLinkRequest, admin: Annotated[dict, Depends(require_admin)]
) -> dict:
    """Add link."""
    try:
        link_config = {"text": request.text, "url": request.url}

        dashboard_config["links"].append(link_config)
        save_dashboard_config()

        logger.info("Admin %s added link: %s", admin["username"], request.text)
    except Exception:
        logger.exception("Failed to add link")
        raise HTTPException(status_code=503, detail="Failed to add link") from None
    else:
        return {"success": True, "message": "Link added"}


@app.delete("/api/admin/links/{link_index}")
async def remove_link(
    link_index: int, admin: Annotated[dict, Depends(require_admin)]
) -> dict | None:
    """Remove link."""
    try:
        if 0 <= link_index < len(dashboard_config["links"]):
            removed_link = dashboard_config["links"].pop(link_index)
            save_dashboard_config()
            logger.info(
                "Admin %s removed link: %s", admin["username"], removed_link["text"]
            )
            return {"success": True, "message": "Link removed"}

        _raise_link_not_found_error()
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to remove link")
        raise HTTPException(status_code=503, detail="Failed to remove link") from None


@app.post("/api/admin/toggle/{entity_id}")
async def toggle_entity_endpoint(
    entity_id: str,
    request: ToggleRequest,
    admin: Annotated[dict, Depends(require_admin)],
) -> dict:
    """Toggle controllable entity (admin only)."""
    if not is_controllable_entity(entity_id):
        raise HTTPException(status_code=400, detail="Entity not controllable")

    if request.action not in ["toggle", "turn_on", "turn_off"]:
        raise HTTPException(status_code=400, detail="Invalid action")

    try:
        await ha_client.toggle_entity(entity_id, request.action)
        logger.info(
            "Admin %s performed %s on %s", admin["username"], request.action, entity_id
        )
    except Exception:
        logger.exception("Failed to toggle entity %s", entity_id)
        raise HTTPException(
            status_code=503, detail="Failed to control entity"
        ) from None
    else:
        return {
            "success": True,
            "message": f"Entity {entity_id} {request.action} successful",
        }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}


# Root route must be last to catch all remaining requests
@app.get("/", response_model=None)
async def read_index() -> FileResponse | dict:
    """Serve the main index.html file."""
    index_file = Path(WWW_PUBLIC_DIR) / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"error": "index.html not found", "path": str(index_file)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8001")))
