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

# Initialize managers (portable path resolution for local and server environments)
try:
    from pathlib import Path
    ROOT_DIR = Path(__file__).parent.resolve()
    ENTITY_DEFINITIONS_PATH = str((ROOT_DIR / "config" / "entity_definitions.json").resolve())

    blueprint_file_manager = BlueprintFileManager()
    blueprint_config_manager = BlueprintConfigurationManager(ENTITY_DEFINITIONS_PATH, blueprint_file_manager)

    # Initialize graph builder only if topics.yaml exists; otherwise, leave None and endpoints will fallback
    topics_cfg = ROOT_DIR / "config" / "topics.yaml"
    if topics_cfg.exists():
        graph_builder = TraceGraphBuilder(str(topics_cfg))
    else:
        graph_builder = None
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

# Add missing essential routes for Blueprint Creator

@api_router.get("/blueprint/config")
async def get_blueprint_config():
    """Get blueprint configuration - main endpoint for Blueprint Creator"""
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            # Return empty config if no root path is set
            return {
                "success": False,
                "message": "Blueprint root path not set",
                "config": None,
                "root_path": None
            }
        
        ui_config, warnings = await blueprint_config_manager.load_blueprint_config(root_path)
        return {
            "success": True,
            "config": ui_config.dict() if ui_config else None,
            "warnings": warnings,
            "root_path": root_path
        }
    except Exception as e:
        logger.error(f"❌ Failed to get blueprint config: {e}")
        return {
            "success": False,
            "message": str(e),
            "config": None,
            "root_path": blueprint_file_manager.root_path if blueprint_file_manager else None
        }

@api_router.post("/blueprint/config")
async def set_blueprint_root_path(request: dict):
    """Set blueprint root path"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        root_path = request.get("root_path", "/app")
        blueprint_file_manager.set_root_path(root_path)
        return {"success": True, "root_path": root_path}
    except Exception as e:
        logger.error(f"❌ Failed to set blueprint root path: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/app-config")
async def get_app_config():
    """Get application configuration"""
    return {
        "app_name": "Blueprint Configuration Manager",
        "version": "1.0.0",
        "environment": "production",
        "features": {
            "blueprint_creator": True,
            "trace_viewer": True,
            "environment_management": True
        }
    }

@api_router.get("/environments")
async def get_environments():
    """Get available environments"""
    try:
        # Return standard environments
        environments = ["DEV", "TEST", "INT", "LOAD", "PROD"]
        return {
            "environments": environments,
            "default": "DEV"
        }
    except Exception as e:
        logger.error(f"❌ Failed to get environments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/topics")
async def get_topics():
    """Get available topics"""
    try:
        if graph_builder:
            topics = graph_builder.topic_graph.get_all_topics()
            return {
                "topics": topics,
                "monitored": topics  # All topics are monitored by default
            }
        else:
            return {
                "topics": ["user-events", "analytics", "notifications", "processed-events"],
                "monitored": ["user-events", "analytics", "notifications", "processed-events"]
            }
    except Exception as e:
        logger.error(f"❌ Failed to get topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/topics/graph")
async def get_topic_graph():
    """Get topic graph data"""
    try:
        if graph_builder:
            # Return simplified graph structure
            topics = graph_builder.topic_graph.get_all_topics()
            edges = graph_builder.topic_graph.edges
            return {
                "nodes": [{"id": topic, "label": topic} for topic in topics],
                "edges": [{"source": edge.source, "target": edge.destination} for edge in edges]
            }
        else:
            return {
                "nodes": [
                    {"id": "user-events", "label": "user-events"},
                    {"id": "analytics", "label": "analytics"},
                    {"id": "notifications", "label": "notifications"},
                    {"id": "processed-events", "label": "processed-events"}
                ],
                "edges": [
                    {"source": "user-events", "target": "analytics"},
                    {"source": "user-events", "target": "notifications"},
                    {"source": "analytics", "target": "processed-events"}
                ]
            }
    except Exception as e:
        logger.error(f"❌ Failed to get topic graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/statistics")
async def get_statistics():
    """Get system statistics"""
    try:
        return {
            "total_traces": 0,
            "active_topics": 4,
            "processed_messages": 0,
            "error_count": 0,
            "last_updated": "2025-01-29T23:34:24Z"
        }
    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/traces")
async def get_traces():
    """Get trace data"""
    try:
        return {
            "traces": [],
            "total": 0,
            "page": 1,
            "per_page": 50
        }
    except Exception as e:
        logger.error(f"❌ Failed to get traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping", "timestamp": "2025-01-29T23:34:24Z"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@api_router.websocket("/ws/blueprint")
async def blueprint_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for blueprint updates"""
    await websocket.accept()
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.send_json({"type": "blueprint_ping", "timestamp": "2025-01-29T23:34:24Z"})
    except WebSocketDisconnect:
        logger.info("Blueprint WebSocket disconnected")
    except Exception as e:
        logger.error(f"Blueprint WebSocket error: {e}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)