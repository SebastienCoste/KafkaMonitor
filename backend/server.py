import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import yaml

from src.blueprint_file_manager import BlueprintFileManager
from src.blueprint_models import FileOperationRequest
from src.blueprint_config_manager import BlueprintConfigurationManager
from src.blueprint_config_models import (
    CreateSchemaRequest,
    CreateEntityRequest,
    UpdateEntityRequest,
    GenerateFilesRequest,
    EnvironmentOverrideRequest,
)
from src.graph_builder import TraceGraphBuilder
from src.protobuf_decoder import ProtobufDecoder, MockProtobufDecoder

# -----------------------------------------------------------------------------
# App and Router
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()
api_router = APIRouter(prefix="/api")

# -----------------------------------------------------------------------------
# Initialization (portable for local and server)
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.resolve()
ENTITY_DEFINITIONS_PATH = str((ROOT_DIR / "config" / "entity_definitions.json").resolve())

blueprint_file_manager: Optional[BlueprintFileManager] = None
blueprint_config_manager: Optional[BlueprintConfigurationManager] = None
graph_builder: Optional[TraceGraphBuilder] = None

try:
    blueprint_file_manager = BlueprintFileManager()
    blueprint_config_manager = BlueprintConfigurationManager(ENTITY_DEFINITIONS_PATH, blueprint_file_manager)

    topics_yaml = ROOT_DIR / "config" / "topics.yaml"
    settings_yaml = ROOT_DIR / "config" / "settings.yaml"
    kafka_yaml = ROOT_DIR / "config" / "kafka.yaml"

    if topics_yaml.exists():
        logger.info(f"Loading topic graph from {topics_yaml}")
        graph_builder = TraceGraphBuilder(str(topics_yaml))

    # Optional protobuf decoder init (to mirror run_local.py logging)
    if settings_yaml.exists() and topics_yaml.exists():
        try:
            with open(settings_yaml, 'r') as f:
                settings = yaml.safe_load(f) or {}
            with open(topics_yaml, 'r') as f:
                topics_cfg = yaml.safe_load(f) or {}

            proto_dir = ROOT_DIR / "config" / "proto"
            use_mock = True
            if kafka_yaml.exists():
                with open(kafka_yaml, 'r') as f:
                    kafka_cfg = yaml.safe_load(f) or {}
                    use_mock = kafka_cfg.get('mock_mode', True)

            if use_mock:
                decoder = MockProtobufDecoder()
                logger.info("Using mock protobuf decoder (server)")
            else:
                if not proto_dir.exists():
                    logger.warning(f"Proto directory not found: {proto_dir}")
                    decoder = MockProtobufDecoder()
                else:
                    decoder = ProtobufDecoder(str(proto_dir))
                    logger.info("Using real protobuf decoder (server)")

            # Load per-topic protobufs (safe with missing fields)
            for topic_name, topic_cfg in (topics_cfg.get('topics') or {}).items():
                try:
                    decoder.load_topic_protobuf(
                        topic_name,
                        topic_cfg.get('proto_file', ''),
                        topic_cfg.get('message_type', '')
                    )
                    logger.info(f"Loaded protobuf for topic {topic_name}")
                except Exception as e:
                    logger.warning(f"Failed to load protobuf for topic {topic_name}: {e}")

            if graph_builder is None:
                graph_builder = TraceGraphBuilder(str(topics_yaml), max_traces=settings.get('max_traces', 1000))
                logger.info("Initialized TraceGraphBuilder (server)")
        except Exception as init_warn:
            logger.warning(f"Optional Kafka/protobuf init skipped: {init_warn}")
except Exception as init_err:
    logger.error(f"Initialization error: {init_err}")

# -----------------------------------------------------------------------------
# Serve static assets and frontend build
# -----------------------------------------------------------------------------
static_dir = ROOT_DIR.parent / "frontend" / "build" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_frontend_root():
    index_path = ROOT_DIR.parent / "frontend" / "build" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    # Fallback to a friendly message if build not present
    return JSONResponse({"detail": "Frontend build not found. Please run 'yarn build' in frontend/."}, status_code=404)

# Catch-all for SPA routes (non-API)
@app.get("/{full_path:path}")
async def serve_frontend_catchall(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not Found")
    index_path = ROOT_DIR.parent / "frontend" / "build" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Frontend build not found")

# -----------------------------------------------------------------------------
# Basic & App Config Endpoints
# -----------------------------------------------------------------------------
@api_router.get("/health")
async def health():
    return {"status": "ok"}

@api_router.get("/app-config")
async def get_app_config():
    return {
        "app_name": "Blueprint Configuration Manager",
        "version": "1.0.0",
        "environment": "development",
        "tabs": {
            "trace_viewer": {"enabled": True, "title": "Trace Viewer"},
            "grpc_integration": {"enabled": True, "title": "gRPC Integration"},
            "blueprint_creator": {"enabled": True, "title": "Blueprint Creator"}
        },
        "landing_page": {"enabled": True}
    }

@api_router.get("/environments")
async def get_environments():
    envs = ["DEV", "TEST", "INT", "LOAD", "PROD"]
    current = "DEV"
    return {
        "environments": envs,
        "default": current,
        # Back-compat keys
        "available_environments": envs,
        "current_environment": current
    }

# -----------------------------------------------------------------------------
# Blueprint File APIs (file-tree, content, create-file, namespace)
# -----------------------------------------------------------------------------
@api_router.get("/blueprint/file-tree")
async def get_blueprint_file_tree(path: str = ""):
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        files = await blueprint_file_manager.get_file_tree(path)
        # Convert Pydantic models to dicts if needed
        return {"files": [f.dict() if hasattr(f, 'dict') else f for f in files]}
    except Exception as e:
        logger.error(f"Error getting file tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/file-content/{path:path}")
async def get_blueprint_file_content(path: str):
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        content = await blueprint_file_manager.read_file(path)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/create-file")
async def create_or_overwrite_file(request: FileOperationRequest):
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        # Overwrite path if requested
        if request.overwrite:
            await blueprint_file_manager.write_file(request.path, request.content or "")
            return {"success": True, "message": "File overwritten"}
        # Otherwise, create new file
        await blueprint_file_manager.create_file(request.path)
        if request.content is not None:
            await blueprint_file_manager.write_file(request.path, request.content)
        return {"success": True, "message": "File created"}
    except FileExistsError:
        raise HTTPException(status_code=409, detail="File already exists")
    except Exception as e:
        logger.error(f"Error creating/overwriting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Convenience: namespace detection from blueprint_cnf.json at project root
@api_router.get("/blueprint/namespace")
async def get_blueprint_namespace():
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        content = await blueprint_file_manager.read_file("blueprint_cnf.json")
        data = json.loads(content)
        return {"namespace": data.get("namespace", ""), "source": "blueprint_cnf.json"}
    except FileNotFoundError:
        return {"namespace": "", "source": "not_found"}
    except Exception as e:
        logger.error(f"Failed to read blueprint namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# Blueprint UI Config APIs (schemas, entities, overrides, generate, validate)
# -----------------------------------------------------------------------------
@api_router.get("/blueprint/config/entity-definitions")
async def get_entity_definitions():
    if not blueprint_config_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        definitions = await blueprint_config_manager.get_entity_definitions()
        return definitions.dict()
    except Exception as e:
        logger.error(f"Failed to get entity definitions: {e}")
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
        logger.error(f"Failed to get blueprint UI config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/config/reset")
async def reset_blueprint_ui_config():
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        # Force parse and save fresh UI config
        parse_result, ui_config = await blueprint_config_manager.parser.parse_blueprint_directory(root_path)
        if not ui_config:
            detail = "; ".join(parse_result.errors) if parse_result and parse_result.errors else "Failed to parse blueprint directory"
            raise HTTPException(status_code=400, detail=detail)
        saved = await blueprint_config_manager.save_blueprint_config(root_path, ui_config)
        if not saved:
            raise HTTPException(status_code=500, detail="Failed to save refreshed UI configuration")
        return {"success": True, "warnings": parse_result.warnings if parse_result else [], "config": ui_config.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset blueprint UI config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/config")
async def get_blueprint_config():
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            return {"success": False, "message": "Blueprint root path not set", "config": None, "root_path": None}
        ui_config, warnings = await blueprint_config_manager.load_blueprint_config(root_path)
        return {"success": True, "config": ui_config.dict() if ui_config else None, "warnings": warnings, "root_path": root_path}
    except Exception as e:
        logger.error(f"Failed to get blueprint config: {e}")
        return {"success": False, "message": str(e), "config": None, "root_path": blueprint_file_manager.root_path if blueprint_file_manager else None}

@api_router.post("/blueprint/config")
async def set_blueprint_root_path(request: Dict[str, Any]):
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        root_path = request.get("root_path")
        if not root_path:
            raise HTTPException(status_code=400, detail="Root path is required")
        blueprint_file_manager.set_root_path(root_path)
        return {"success": True, "root_path": root_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set blueprint root path: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/config/schemas")
async def create_configuration_schema(request: CreateSchemaRequest):
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        schema_id, warnings = await blueprint_config_manager.create_schema(root_path, request)
        if not schema_id:
            detail = "; ".join(warnings) if warnings else "Failed to create schema"
            raise HTTPException(status_code=400, detail=detail)
        return {"success": True, "schema_id": schema_id, "warnings": warnings}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create configuration schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/config/entities")
async def create_entity_configuration(request: CreateEntityRequest):
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        entity_id, warnings = await blueprint_config_manager.create_entity(root_path, request)
        if not entity_id:
            detail = "; ".join(warnings) if warnings else "Failed to create entity"
            raise HTTPException(status_code=400, detail=detail)
        return {"success": True, "entity_id": entity_id, "warnings": warnings}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create entity configuration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred while creating entity")

@api_router.put("/blueprint/config/entities/{entity_id}")
async def update_entity_configuration(entity_id: str, request: UpdateEntityRequest):
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        success, warnings, status_code = await blueprint_config_manager.update_entity(root_path, entity_id, request)
        if not success:
            detail = "; ".join(warnings) if warnings else "Failed to update entity"
            raise HTTPException(status_code=status_code, detail=detail)
        return {"success": True, "warnings": warnings}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update entity configuration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred while updating entity")
# -----------------------------------------------------------------------------
# Build & Output files APIs (minimal placeholders for local)
# -----------------------------------------------------------------------------
@api_router.post("/blueprint/build")
async def build_blueprint(request: Dict[str, Any]):
    # Placeholder: emit success and rely on WebSocket for async updates in full impl
    root_path = request.get("root_path")
    if not root_path:
        raise HTTPException(status_code=400, detail="root_path is required")
    return {"status": "started", "root_path": root_path, "script": request.get("script_name", "buildBlueprint.sh")}

@api_router.post("/blueprint/cancel-build")
async def cancel_build():
    return {"status": "canceled"}

@api_router.get("/blueprint/output-files")
async def get_output_files(root_path: str):
    try:
        # List files under root_path/dist if present
        dist_dir = Path(root_path) / "dist"
        files = []
        if dist_dir.exists() and dist_dir.is_dir():
            for name in sorted(os.listdir(dist_dir)):
                p = dist_dir / name
                if p.is_file():
                    files.append({"name": name, "path": str(p), "size": p.stat().st_size})
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/validate-config")
async def validate_blueprint_config(path: str = "blueprint_cnf.json"):
    try:
        # Basic check: file exists and is valid JSON
        full = Path(blueprint_file_manager.root_path or ".") / path if not os.path.isabs(path) else Path(path)
        if not full.exists():
            raise HTTPException(status_code=404, detail=f"Config not found: {path}")
        data = json.loads(full.read_text())
        return {"valid": True, "errors": [], "warnings": [], "path": str(full), "keys": list(data.keys())}
    except HTTPException:
        raise
    except Exception as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}

@api_router.post("/blueprint/validate/{filename}")
async def validate_blueprint_tgz(filename: str, payload: Dict[str, Any]):
    return {"status": "validated", "file": filename, "environment": payload.get("environment")}

@api_router.post("/blueprint/activate/{filename}")
async def activate_blueprint_tgz(filename: str, payload: Dict[str, Any]):
    return {"status": "activated", "file": filename, "environment": payload.get("environment")}

@api_router.delete("/blueprint/config/entities/{entity_id}")
async def delete_entity_configuration(entity_id: str):
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        success, warnings, status_code = await blueprint_config_manager.delete_entity(root_path, entity_id)
        if not success:
            detail = "; ".join(warnings) if warnings else "Failed to delete entity"
            raise HTTPException(status_code=status_code, detail=detail)
        return {"success": True, "warnings": warnings}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete entity configuration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred while deleting entity")

@api_router.post("/blueprint/config/entities/{entity_id}/environment-overrides")
async def set_environment_override(entity_id: str, request: EnvironmentOverrideRequest):
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        success, warnings, status_code = await blueprint_config_manager.set_environment_override(root_path, request)
        if not success:
            detail = "; ".join(warnings) if warnings else "Failed to set environment override"
            raise HTTPException(status_code=status_code, detail=detail)
        return {"success": True, "warnings": warnings}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set environment override: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred while setting environment override")

@api_router.post("/blueprint/config/generate")
async def generate_configuration_files(request: GenerateFilesRequest):
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        if not request.outputPath:
            request.outputPath = root_path
        result = await blueprint_config_manager.generate_files(root_path, request)
        return result.dict()
    except Exception as e:
        logger.error(f"Failed to generate configuration files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/config/validate")
async def validate_blueprint_configuration():
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        result = await blueprint_config_manager.validate_configuration(blueprint_file_manager.root_path)
        return result.dict()
    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# Kafka/Traces placeholder endpoints (keep UI functional in mock mode)
# -----------------------------------------------------------------------------
@api_router.get("/topics")
async def get_topics():
    try:
        if graph_builder:
            topics = graph_builder.topic_graph.get_all_topics()
            return {"topics": topics, "monitored": topics}
        return {"topics": ["user-events", "analytics", "notifications", "processed-events"], "monitored": ["user-events", "analytics", "notifications", "processed-events"]}
    except Exception as e:
        logger.error(f"Failed to get topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/topics/graph")
async def get_topic_graph():
    try:
        if graph_builder:
            topics = graph_builder.topic_graph.get_all_topics()
            edges = graph_builder.topic_graph.edges
            return {
                "nodes": [{"id": t, "label": t} for t in topics],
                "edges": [{"source": e.source, "target": e.destination} for e in edges]
            }
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
        logger.error(f"Failed to get topic graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/statistics")
async def get_statistics():
    try:
        return {"total_traces": 0, "active_topics": 4, "processed_messages": 0, "error_count": 0}
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/traces")
async def get_traces():
    try:
        return {"traces": [], "total": 0, "page": 1, "per_page": 50}
    except Exception as e:
        logger.error(f"Failed to get traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# WebSockets
# -----------------------------------------------------------------------------
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@api_router.websocket("/ws/blueprint")
async def blueprint_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "blueprint_ping"})
    except WebSocketDisconnect:
        logger.info("Blueprint WebSocket disconnected")
    except Exception as e:
        logger.error(f"Blueprint WebSocket error: {e}")

# -----------------------------------------------------------------------------
# Middleware and Router Mount
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)