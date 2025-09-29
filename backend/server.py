import os
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.blueprint_file_manager import BlueprintFileManager
from src.blueprint_models import (
    FileOperationRequest,
)
from src.blueprint_config_manager import BlueprintConfigurationManager
from src.blueprint_config_models import (
    CreateSchemaRequest,
    CreateEntityRequest,
    UpdateEntityRequest,
    GenerateFilesRequest,
    EnvironmentOverrideRequest,
)
from src.graph_builder import TraceGraphBuilder

logger = logging.getLogger(__name__)

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Initialize managers (existing init code assumed above in original file)
try:
    BASE_DIR = "/app"
    ENTITY_DEFINITIONS_PATH = os.path.join(BASE_DIR, "backend", "config", "entity_definitions.json")
    blueprint_file_manager = BlueprintFileManager()
    blueprint_config_manager = BlueprintConfigurationManager(ENTITY_DEFINITIONS_PATH, blueprint_file_manager)
    graph_builder = TraceGraphBuilder("config/topics.yaml")
except Exception as init_err:
    logger.error(f"Initialization error: {init_err}")
    blueprint_file_manager = None
    blueprint_config_manager = None
    graph_builder = None

# ... existing routes and implementations above ...

@api_router.get("/blueprint/config/entity-definitions")
async def get_entity_definitions():
    if not blueprint_config_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        definitions = await blueprint_config_manager.get_entity_definitions()
        return definitions.dict()
    except Exception as e:
        logger.error(f"❌ Failed to get entity definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/config/ui-config")
async def get_blueprint_ui_config():
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        ui_config, warnings = await blueprint_config_manager.load_blueprint_config(root_path)
        return {"config": ui_config.dict(), "warnings": warnings}
    except Exception as e:
        logger.error(f"❌ Failed to get blueprint UI config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/config/reset")
async def reset_blueprint_ui_config():
    """Reset the UI configuration to match what's on disk by reparsing blueprint_cnf.json and related files.
    This ignores any existing blueprint_ui_config.json and overwrites it with a fresh parse result.
    """
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")

        # Ensure entity definitions are loaded
        await blueprint_config_manager.load_entity_definitions()

        # Parse directory regardless of existing UI config
        parse_result, ui_config = await blueprint_config_manager.parser.parse_blueprint_directory(root_path)
        if not ui_config:
            # If parsing failed, surface errors
            detail = "; ".join(parse_result.errors) if parse_result and parse_result.errors else "Failed to parse blueprint directory"
            raise HTTPException(status_code=400, detail=detail)

        # Save freshly parsed UI config to disk
        saved = await blueprint_config_manager.save_blueprint_config(root_path, ui_config)
        if not saved:
            raise HTTPException(status_code=500, detail="Failed to save refreshed UI configuration")

        return {
            "success": True,
            "warnings": parse_result.warnings if parse_result else [],
            "config": ui_config.dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reset blueprint UI config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ... existing routes below ...

app.include_router(api_router)