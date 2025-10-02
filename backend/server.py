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
    
    # Read default environment from settings.yaml
    current = "DEV"  # Fallback default
    try:
        settings_path = ROOT_DIR / "config" / "settings.yaml"
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                settings = yaml.safe_load(f)
                start_env = settings.get('application', {}).get('start_env', 'DEV')
                if start_env in envs:
                    current = start_env
                    logger.info(f"Using start_env from settings.yaml: {current}")
                else:
                    logger.warning(f"Invalid start_env '{start_env}' in settings.yaml, using DEV")
    except Exception as e:
        logger.warning(f"Could not read start_env from settings.yaml: {e}")
    
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
    """Execute build script and stream output via WebSocket"""
    root_path = request.get("root_path")
    script_name = request.get("script_name", "buildBlueprint.sh")
    
    if not root_path:
        raise HTTPException(status_code=400, detail="root_path is required")
    
    root_path_obj = Path(root_path)
    script_path = root_path_obj / script_name
    
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Build script not found: {script_name}")
    
    if not os.access(script_path, os.X_OK):
        raise HTTPException(status_code=403, detail=f"Build script is not executable: {script_name}")
    
    try:
        # Broadcast build started
        await broadcast_message({
            "type": "build_started",
            "data": {"script": script_name}
        })
        
        # Execute build script synchronously and capture output
        import subprocess
        process = subprocess.Popen(
            ['/bin/bash', str(script_path)],
            cwd=str(root_path_obj),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Read and broadcast output line by line as it comes
        for line in iter(process.stdout.readline, ''):
            if line:
                await broadcast_message({
                    "type": "build_output",
                    "data": {"content": line.rstrip()}
                })
        
        # Wait for process to complete
        return_code = process.wait()
        success = return_code == 0
        
        # Find generated .tar.gz files
        dist_dir = root_path_obj / "dist"
        generated_files = []
        if dist_dir.exists():
            for f in dist_dir.glob("*.tar.gz"):
                if f.is_file():
                    stat = f.stat()
                    generated_files.append({
                        "name": f.name,
                        "path": str(f),
                        "size": stat.st_size,
                        "modified": int(stat.st_mtime),
                        "directory": "dist"
                    })
        
        # Broadcast build complete
        await broadcast_message({
            "type": "build_complete",
            "data": {
                "success": success,
                "return_code": return_code,
                "generated_files": generated_files
            }
        })
        
        return {
            "status": "completed" if success else "failed",
            "return_code": return_code,
            "files_generated": len(generated_files)
        }
        
    except Exception as e:
        logger.error(f"Build error: {e}")
        await broadcast_message({
            "type": "build_error",
            "data": {"error": str(e)}
        })
        raise HTTPException(status_code=500, detail=str(e))

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

@api_router.post("/blueprint/config/generate-all")
async def generate_all_configuration_files():
    """Generate configuration files for all schemas in all environments"""
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        
        # Load UI config to get all schemas
        ui_config, warnings = await blueprint_config_manager.load_blueprint_config(root_path)
        
        total_files = 0
        all_errors = []
        
        # Generate files for each schema across all environments
        for schema in ui_config.schemas:
            request = GenerateFilesRequest(
                schemaId=schema.id,
                environments=["DEV", "TEST", "INT", "LOAD", "PROD"],
                outputPath=root_path
            )
            result = await blueprint_config_manager.generate_files(root_path, request)
            if result.success:
                total_files += len(result.files)
            else:
                all_errors.extend(result.errors)
        
        return {
            "success": len(all_errors) == 0,
            "filesGenerated": total_files,
            "errors": all_errors
        }
    except Exception as e:
        logger.error(f"Failed to generate all configuration files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/config/generate-cnf")
async def generate_blueprint_cnf():
    """Generate blueprint_cnf.json file"""
    if not blueprint_config_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint configuration manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        
        # For now, return success - the actual CNF generation would go here
        return {
            "success": True,
            "message": "Blueprint CNF generation not yet implemented"
        }
    except Exception as e:
        logger.error(f"Failed to generate blueprint CNF: {e}")
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
        # Try to get topics from configuration file
        topics_yaml = ROOT_DIR / "config" / "topics.yaml"
        settings_yaml = ROOT_DIR / "config" / "settings.yaml"
        
        # Check if we should activate all topics
        activate_all = False
        if settings_yaml.exists():
            try:
                with open(settings_yaml, 'r') as f:
                    settings = yaml.safe_load(f)
                    activate_all = settings.get('topic_monitoring', {}).get('activate_all_on_startup', False)
            except Exception as e:
                logger.warning(f"Could not read activate_all_on_startup from settings.yaml: {e}")
        
        if topics_yaml.exists():
            with open(topics_yaml, 'r') as f:
                topics_cfg = yaml.safe_load(f)
                configured_topics = list(topics_cfg.get('topics', {}).keys())
                
                # If activate_all_on_startup is true, monitor all topics
                if activate_all:
                    monitored = configured_topics
                    logger.info(f"Activating all {len(configured_topics)} topics on startup")
                else:
                    monitored = topics_cfg.get('default_monitored_topics', configured_topics)
                
                return {"topics": configured_topics, "monitored": monitored}
        
        # Fallback to graph builder
        if graph_builder:
            topics = graph_builder.topic_graph.get_all_topics()
            if topics:
                return {"topics": list(topics), "monitored": list(topics)}
        
        # Final fallback
        return {"topics": ["user-events", "analytics", "notifications", "processed-events"], "monitored": ["user-events", "analytics", "notifications", "processed-events"]}
    except Exception as e:
        logger.error(f"Failed to get topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/topics/monitor")
async def update_monitored_topics(topics: List[str]):
    """Update the list of monitored topics"""
    try:
        # Store monitored topics in app state
        if not hasattr(app.state, 'monitored_topics'):
            app.state.monitored_topics = []
        
        app.state.monitored_topics = topics
        logger.info(f"Updated monitored topics: {topics}")
        
        return {
            "success": True,
            "monitored_topics": topics,
            "count": len(topics)
        }
    except Exception as e:
        logger.error(f"Failed to update monitored topics: {e}")
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

@api_router.get("/graph/disconnected")
async def get_disconnected_components():
    """Get disconnected components in the topic graph"""
    try:
        # Get the full graph from topics
        topics_graph_response = await get_topic_graph()
        nodes = topics_graph_response.get("nodes", [])
        edges = topics_graph_response.get("edges", [])
        
        if not nodes:
            return {"success": True, "components": [], "total_components": 0}
        
        # Extract topic names from nodes
        topic_names = [node.get("id") or node.get("label") for node in nodes]
        
        # Create component structure with all required fields for frontend
        component = {
            "component_id": 0,  # Numeric ID starting from 0
            "topics": topic_names,  # Array of topic names
            "topic_count": len(topic_names),  # Number of topics
            "nodes": nodes,
            "edges": edges,
            "statistics": {
                "total_messages": len(edges) * 100,
                "active_traces": len(nodes) * 5,  # Mock: 5 traces per topic
                "health_score": 85,
                "median_trace_age": 120,  # 2 minutes in seconds
                "p95_trace_age": 300,  # 5 minutes in seconds
                "avg_latency_ms": 45.2,
                "throughput": len(nodes) * 10
            }
        }
        
        return {
            "success": True,
            "components": [component],
            "total_components": 1
        }
    except Exception as e:
        logger.error(f"Failed to get disconnected components: {e}")
        return {"success": False, "components": [], "total_components": 0}

@api_router.get("/graph/filtered")
async def get_filtered_graph(topic: str = None, depth: int = 2):
    """Get filtered graph centered around a topic"""
    try:
        if not topic:
            # Return full graph if no topic specified
            if graph_builder:
                topics = graph_builder.topic_graph.get_all_topics()
                edges = graph_builder.topic_graph.edges
                return {
                    "nodes": [{"id": t, "label": t} for t in topics],
                    "edges": [{"source": e.source, "target": e.destination} for e in edges]
                }
        
        if graph_builder and hasattr(graph_builder, 'get_subgraph'):
            subgraph = graph_builder.get_subgraph(topic, depth)
            return subgraph
        
        # Return empty graph
        return {"nodes": [], "edges": []}
    except Exception as e:
        logger.error(f"Failed to get filtered graph: {e}")
        return {"nodes": [], "edges": []}

@api_router.post("/graph/apply-mock")
async def apply_mock_data():
    """Apply mock data to the graph for testing"""
    try:
        # Create mock graph data
        mock_nodes = [
            {"id": "user-events", "label": "user-events"},
            {"id": "analytics", "label": "analytics"},
            {"id": "notifications", "label": "notifications"},
            {"id": "processed-events", "label": "processed-events"},
            {"id": "test-events", "label": "test-events"},
            {"id": "test-processes", "label": "test-processes"}
        ]
        mock_edges = [
            {"source": "user-events", "target": "analytics"},
            {"source": "user-events", "target": "notifications"},
            {"source": "analytics", "target": "processed-events"},
            {"source": "test-events", "target": "test-processes"}
        ]
        
        return {
            "success": True,
            "message": "Mock data applied",
            "nodes": mock_nodes,
            "edges": mock_edges
        }
    except Exception as e:
        logger.error(f"Failed to apply mock data: {e}")
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
# gRPC Integration API Endpoints  
# -----------------------------------------------------------------------------

@api_router.get("/grpc/status")
async def get_grpc_status():
    """Get gRPC client status"""
    try:
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            return {
                "initialized": False,
                "message": "gRPC client not initialized",
                "proto_files_required": True
            }
        
        # Check if proto files are available (use relative path)
        proto_dir = ROOT_DIR / "config" / "proto"
        has_protos = proto_dir.exists() and len(list(proto_dir.rglob("*.proto"))) > 0
        
        return {
            "initialized": True,
            "proto_files_present": has_protos,
            "current_environment": getattr(app.state.grpc_client, 'current_environment', 'DEV'),
            "available_services": app.state.grpc_client.proto_loader.list_available_services() if app.state.grpc_client.proto_loader.compiled_modules else {}
        }
    except Exception as e:
        logger.error(f"Error getting gRPC status: {e}")
        return {"initialized": False, "error": str(e)}

@api_router.get("/grpc/environments")
async def get_grpc_environments():
    """Get available gRPC environments"""
    try:
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            # Initialize gRPC client if not exists (use relative paths)
            from src.grpc_client import GrpcClient
            proto_root = ROOT_DIR / "config" / "proto"
            env_dir = ROOT_DIR / "config" / "environments"
            
            # Don't create directories, just check if they exist
            if not env_dir.exists():
                logger.warning(f"Environments directory not found: {env_dir}")
                return {"environments": ["DEV", "TEST", "INT", "LOAD", "PROD"], "current": "DEV"}
            
            app.state.grpc_client = GrpcClient(str(proto_root), str(env_dir))
        
        environments = app.state.grpc_client.list_environments()
        return {
            "environments": environments,
            "current": getattr(app.state.grpc_client, 'current_environment', 'DEV')
        }
    except Exception as e:
        logger.error(f"Error getting gRPC environments: {e}")
        return {"environments": ["DEV", "TEST", "INT", "LOAD", "PROD"], "current": "DEV", "error": str(e)}

@api_router.post("/grpc/initialize")
async def initialize_grpc():
    """Initialize gRPC client and load proto files"""
    try:
        from src.grpc_client import GrpcClient
        
        # Use relative paths from ROOT_DIR
        proto_root = ROOT_DIR / "config" / "proto"
        env_dir = ROOT_DIR / "config" / "environments"
        
        # Check if proto files exist
        if not proto_root.exists() or len(list(proto_root.rglob("*.proto"))) == 0:
            return {
                "success": False,
                "error": f"Proto files must be placed in backend/config/proto/ directory before initialization. Current path: {proto_root}",
                "proto_directory": str(proto_root)
            }
        
        # Initialize client
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            app.state.grpc_client = GrpcClient(str(proto_root), str(env_dir))
        
        result = await app.state.grpc_client.initialize()
        
        if result.get('success'):
            return {
                "success": True,
                "message": "gRPC client initialized successfully",
                "available_services": result.get('available_services', {}),
                "environments": result.get('environments', [])
            }
        else:
            return result
            
    except Exception as e:
        logger.error(f"Error initializing gRPC: {e}")
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

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
# -----------------------------------------------------------------------------
# Serve static assets and frontend build (AFTER API router registration)
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
