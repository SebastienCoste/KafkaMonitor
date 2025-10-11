import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import yaml

from src.blueprint_file_manager import BlueprintFileManager
from src.blueprint_models import FileOperationRequest
from src.blueprint_config_manager import BlueprintConfigurationManager
from src.blueprint_build_manager import BlueprintBuildManager
from src.blueprint_config_models import (
    CreateSchemaRequest,
    CreateEntityRequest,
    UpdateEntityRequest,
    GenerateFilesRequest,
    EnvironmentOverrideRequest,
)
from src.graph_builder import TraceGraphBuilder
from src.protobuf_decoder import ProtobufDecoder, MockProtobufDecoder
from src.performance.task_manager import AsyncTaskManager

# -----------------------------------------------------------------------------
# App and Router
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Startup event to log all registered routes and initialize gRPC
@app.on_event("startup")
async def startup_event():
    logger.info("="*80)
    logger.info("🚀 APPLICATION STARTUP - INITIALIZING TASK MANAGER")
    logger.info("="*80)
    
    # Initialize task manager FIRST, before any other async operations
    app.state.task_manager = AsyncTaskManager(max_concurrent=20)
    logger.info("✅ Task manager initialized with 20 max concurrent tasks")
    
    logger.info("="*80)
    logger.info("🚀 APPLICATION STARTUP - REGISTERED ROUTES:")
    logger.info("="*80)
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            logger.info(f"  {list(route.methods)} {route.path}")
    logger.info("="*80)
    
    # Initialize gRPC client automatically
    try:
        from src.grpc_client import GrpcClient
        
        proto_root = ROOT_DIR / "config" / "proto"
        env_dir = ROOT_DIR / "config" / "environments"
        
        if proto_root.exists() and len(list(proto_root.rglob("*.proto"))) > 0:
            logger.info("🔧 Auto-initializing gRPC client...")
            app.state.grpc_client = GrpcClient(str(proto_root), str(env_dir))
            result = await app.state.grpc_client.initialize()
            
            if result.get('success'):
                logger.info(f"✅ gRPC client initialized: {len(result.get('available_services', {}))} services loaded")
            else:
                logger.warning(f"⚠️ gRPC initialization failed: {result.get('error')}")
        else:
            logger.info("ℹ️ No proto files found, skipping gRPC auto-initialization")
    except Exception as e:
        logger.error(f"❌ Error auto-initializing gRPC: {e}")
    
    # Perform Git integration migration if needed
    try:
        if hasattr(app.state, 'integration_manager') and app.state.integration_manager:
            from src.migration_helper import IntegrationMigration
            
            integrator_path = ROOT_DIR / "integrator"
            integration_path = ROOT_DIR / "integration"
            
            migration = IntegrationMigration(
                str(integrator_path),
                str(integration_path)
            )
            
            if migration.detect_legacy_setup():
                logger.info("🔄 Legacy Git setup detected, performing automatic migration...")
                success, project_info, error = await migration.migrate_existing_setup()
                
                if success and project_info:
                    # Add migrated project to integration manager
                    app.state.integration_manager.manifest.add_project(project_info)
                    app.state.integration_manager._save_manifest(app.state.integration_manager.manifest)
                    logger.info(f"✅ Migration successful: {project_info.name} -> integration/{project_info.path}")
                    logger.info(f"   Git URL: {project_info.git_url}")
                    logger.info(f"   Branch: {project_info.branch}")
                    logger.info(f"   Namespace: {project_info.namespace or 'N/A'}")
                elif error:
                    logger.warning(f"⚠️ Migration failed: {error}")
            else:
                logger.info("ℹ️ No legacy Git setup detected, skipping migration")
    except Exception as e:
        logger.error(f"❌ Error during Git integration migration: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Initialize Kafka consumer automatically
    global kafka_consumer
    try:
        from src.kafka_consumer import KafkaConsumerService
        from src.protobuf_decoder import ProtobufDecoder, MockProtobufDecoder
        
        # Read the start_env from settings.yaml
        settings_path = ROOT_DIR / "config" / "settings.yaml"
        kafka_yaml = ROOT_DIR / "config" / "kafka.yaml"
        
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                settings = yaml.safe_load(f)
                start_env = settings.get('application', {}).get('start_env', 'INT')
        else:
            start_env = 'INT'
        
        logger.info(f"🔧 Auto-initializing Kafka consumer for environment: {start_env}")
        
        # Load environment configuration and set environment variables
        env_file = ROOT_DIR / "config" / "environments" / f"{start_env.lower()}.yaml"
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_config = yaml.safe_load(f)
            
            kafka_config = env_config.get('kafka', {})
            if kafka_config and kafka_config.get('bootstrap_servers'):
                logger.info(f"   Bootstrap servers: {kafka_config.get('bootstrap_servers')}")
                
                # Set environment variables so KafkaConsumerService can read them
                os.environ['KAFKA_BOOTSTRAP_SERVERS'] = kafka_config.get('bootstrap_servers', '')
                os.environ['KAFKA_USERNAME'] = kafka_config.get('username', kafka_config.get('sasl_username', ''))
                os.environ['KAFKA_PASSWORD'] = kafka_config.get('password', kafka_config.get('sasl_password', ''))
                os.environ['KAFKA_SECURITY_PROTOCOL'] = kafka_config.get('security_protocol', 'SASL_SSL')
                os.environ['KAFKA_SASL_MECHANISM'] = kafka_config.get('sasl_mechanism', 'SCRAM-SHA-512')
                
                # Initialize decoder
                proto_dir = ROOT_DIR / "config" / "proto"
                if proto_dir.exists() and list(proto_dir.rglob("*.proto")):
                    decoder = ProtobufDecoder(str(proto_dir))
                    logger.info("Using real protobuf decoder for Kafka")
                    
                    # Load topic-to-protobuf mappings from topics.yaml
                    topics_yaml_path = ROOT_DIR / "config" / "topics.yaml"
                    if topics_yaml_path.exists():
                        try:
                            with open(topics_yaml_path, 'r') as f:
                                topics_config = yaml.safe_load(f)
                            
                            topics_cfg = topics_config.get('topics', {})
                            for topic_name, topic_cfg in topics_cfg.items():
                                try:
                                    proto_file = topic_cfg.get('proto_file', '')
                                    message_type = topic_cfg.get('message_type', '')
                                    if proto_file and message_type:
                                        decoder.load_topic_protobuf(topic_name, proto_file, message_type)
                                        logger.debug(f"   Loaded protobuf for topic '{topic_name}': {proto_file} -> {message_type}")
                                except Exception as topic_err:
                                    logger.warning(f"   Could not load protobuf for topic '{topic_name}': {topic_err}")
                            logger.info(f"   Loaded protobuf mappings for {len(topics_cfg)} topics")
                        except Exception as e:
                            logger.warning(f"Could not load topic protobuf mappings: {e}")
                else:
                    decoder = MockProtobufDecoder()
                    logger.info("Using mock protobuf decoder for Kafka")
                
                # Get trace header field from settings
                trace_header_field = settings.get('trace_header_field', 'traceparent')
                
                # Initialize Kafka consumer
                kafka_consumer = KafkaConsumerService(
                    config_path=str(kafka_yaml),
                    decoder=decoder,
                    trace_header_field=trace_header_field
                )
                
                # Add message handler if graph_builder exists
                if graph_builder:
                    kafka_consumer.add_message_handler(graph_builder.add_message)
                    logger.info("✅ Added message handler to Kafka consumer")
                
                # Subscribe to topics
                topics_yaml_path = ROOT_DIR / "config" / "topics.yaml"
                if topics_yaml_path.exists() and graph_builder:
                    all_topics = graph_builder.topic_graph.get_all_topics()
                    if all_topics:
                        logger.info(f"📋 Subscribing to {len(all_topics)} topics on startup...")
                        kafka_consumer.subscribe_to_topics(all_topics)
                        logger.info(f"✅ Kafka consumer subscribed to topics")
                        
                        # Start consuming messages asynchronously
                        logger.info(f"🚀 Starting Kafka message consumption...")
                        asyncio.create_task(kafka_consumer.start_consuming_async())
                        logger.info(f"✅ Kafka consumer started")
                    else:
                        logger.warning("⚠️ No topics found in topic graph")
                else:
                    logger.warning("⚠️ No topics.yaml found or graph_builder not initialized")
            else:
                logger.warning(f"⚠️ No Kafka configuration found in {start_env} environment")
        else:
            logger.warning(f"⚠️ Environment file not found: {env_file}")
    except Exception as e:
        logger.error(f"❌ Error auto-initializing Kafka consumer: {e}")
        import traceback
        logger.error(traceback.format_exc())

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown handler"""
    logger.info("🛑 APPLICATION SHUTDOWN - CLEANING UP RESOURCES")
    
    # Shutdown task manager first
    if hasattr(app.state, 'task_manager'):
        await app.state.task_manager.shutdown()
    
    # Gracefully stop Kafka consumer
    global kafka_consumer
    if kafka_consumer is not None:
        try:
            logger.info("🛑 Gracefully shutting down Kafka consumer...")
            await kafka_consumer.stop_consuming_gracefully(timeout=10)
            await kafka_consumer.cleanup_resources()
            logger.info("✅ Kafka consumer shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during Kafka consumer shutdown: {e}")
    
    logger.info("✅ Application shutdown completed")

# -----------------------------------------------------------------------------
# Initialization (portable for local and server)
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.resolve()
ENTITY_DEFINITIONS_PATH = str((ROOT_DIR / "config" / "entity_definitions.json").resolve())

blueprint_file_manager: Optional[BlueprintFileManager] = None
blueprint_config_manager: Optional[BlueprintConfigurationManager] = None
blueprint_build_manager: Optional[BlueprintBuildManager] = None
graph_builder: Optional[TraceGraphBuilder] = None
kafka_consumer = None  # Will be initialized on startup or environment switch

try:
    blueprint_file_manager = BlueprintFileManager()
    blueprint_config_manager = BlueprintConfigurationManager(ENTITY_DEFINITIONS_PATH, blueprint_file_manager)
    blueprint_build_manager = BlueprintBuildManager()
    
    # Initialize Git service (legacy single-project)
    from src.git_service import GitService
    integrator_path = ROOT_DIR / "integrator"
    git_config_path = ROOT_DIR / "config" / "git.yaml"
    app.state.git_service = GitService(
        str(integrator_path), 
        timeout=300,
        config_path=str(git_config_path) if git_config_path.exists() else None
    )
    logger.info(f"Initialized Git service with integrator path: {integrator_path}")
    
    # Initialize Integration Manager (multi-project)
    from src.integration_manager import IntegrationManager
    from src.migration_helper import IntegrationMigration
    
    integration_path = ROOT_DIR / "integration"
    app.state.integration_manager = IntegrationManager(
        str(integration_path),
        git_config_path=str(git_config_path) if git_config_path.exists() else None
    )
    logger.info(f"Initialized Integration Manager with integration path: {integration_path}")

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

@api_router.post("/environments/switch")
async def switch_environment(request: Dict[str, Any]):
    """Switch to a different environment and reinitialize Kafka consumer"""
    global graph_builder, kafka_consumer
    
    try:
        new_env = request.get("environment")
        if not new_env:
            raise HTTPException(status_code=400, detail="Environment is required")
        
        logger.info(f"🔄 Starting graceful environment switch to: {new_env}")
        
        # Phase 1: Graceful Kafka consumer shutdown with timeout
        if kafka_consumer is not None:
            logger.info("🛑 Gracefully stopping Kafka consumer...")
            try:
                await kafka_consumer.stop_consuming_gracefully(timeout=10)
                await kafka_consumer.cleanup_resources()
                logger.info("✅ Kafka consumer gracefully stopped and cleaned up")
            except Exception as e:
                logger.error(f"❌ Error during graceful Kafka shutdown: {e}")
                # Force cleanup as fallback
                if kafka_consumer:
                    try:
                        kafka_consumer.stop_consuming()
                    except:
                        pass
            finally:
                kafka_consumer = None
        
        # Phase 2: Efficient trace clearing with batching
        if graph_builder is not None:
            logger.info("🧹 Clearing trace data with batching...")
            if hasattr(graph_builder, 'clear_traces_efficiently'):
                await graph_builder.clear_traces_efficiently()
            else:
                # Fallback to simple clearing if method not available yet
                graph_builder.traces.clear()
                graph_builder.trace_order.clear()
            logger.info("✅ Trace data cleared efficiently")
        
        # Phase 3: Clean up any remaining async tasks for this environment
        if hasattr(app.state, 'task_manager'):
            logger.info("🧹 Cleaning up environment-specific tasks...")
            await app.state.task_manager.cleanup_environment_tasks(new_env)
        
        # Phase 4: Force garbage collection to free memory immediately
        import gc
        before_gc = gc.get_count()
        collected = gc.collect()
        after_gc = gc.get_count()
        logger.info(f"🗑️ Garbage collection: collected {collected} objects, before: {before_gc}, after: {after_gc}")
        
        # Phase 5: Load new environment configuration
        env_file = ROOT_DIR / "config" / "environments" / f"{new_env.lower()}.yaml"
        if not env_file.exists():
            raise HTTPException(status_code=404, detail=f"Environment configuration not found: {new_env}")
        
        with open(env_file, 'r') as f:
            env_config = yaml.safe_load(f)
        
        # Reinitialize Kafka consumer for new environment
        kafka_config = env_config.get('kafka', {})
        if kafka_config and kafka_config.get('bootstrap_servers'):
            logger.info(f"🔌 Initializing Kafka consumer for {new_env}...")
            logger.info(f"   Bootstrap servers: {kafka_config.get('bootstrap_servers')}")
            
            try:
                from src.kafka_consumer import KafkaConsumerService
                from src.protobuf_decoder import ProtobufDecoder, MockProtobufDecoder
                
                # Set environment variables for KafkaConsumerService
                os.environ['KAFKA_BOOTSTRAP_SERVERS'] = kafka_config.get('bootstrap_servers', '')
                os.environ['KAFKA_USERNAME'] = kafka_config.get('username', kafka_config.get('sasl_username', ''))
                os.environ['KAFKA_PASSWORD'] = kafka_config.get('password', kafka_config.get('sasl_password', ''))
                os.environ['KAFKA_SECURITY_PROTOCOL'] = kafka_config.get('security_protocol', 'SASL_SSL')
                os.environ['KAFKA_SASL_MECHANISM'] = kafka_config.get('sasl_mechanism', 'SCRAM-SHA-512')
                
                # Initialize decoder
                proto_dir = ROOT_DIR / "config" / "proto"
                if proto_dir.exists() and list(proto_dir.rglob("*.proto")):
                    decoder = ProtobufDecoder(str(proto_dir))
                    
                    # Load topic-to-protobuf mappings from topics.yaml
                    topics_yaml_path = ROOT_DIR / "config" / "topics.yaml"
                    if topics_yaml_path.exists():
                        try:
                            with open(topics_yaml_path, 'r') as f:
                                topics_config = yaml.safe_load(f)
                            
                            topics_cfg = topics_config.get('topics', {})
                            for topic_name, topic_cfg in topics_cfg.items():
                                try:
                                    proto_file = topic_cfg.get('proto_file', '')
                                    message_type = topic_cfg.get('message_type', '')
                                    if proto_file and message_type:
                                        decoder.load_topic_protobuf(topic_name, proto_file, message_type)
                                except Exception as topic_err:
                                    logger.warning(f"Could not load protobuf for topic '{topic_name}': {topic_err}")
                        except Exception as e:
                            logger.warning(f"Could not load topic protobuf mappings: {e}")
                else:
                    decoder = MockProtobufDecoder()
                
                # Read settings
                settings_path = ROOT_DIR / "config" / "settings.yaml"
                kafka_yaml = ROOT_DIR / "config" / "kafka.yaml"
                
                with open(settings_path, 'r') as f:
                    settings = yaml.safe_load(f)
                trace_header_field = settings.get('trace_header_field', 'traceparent')
                
                # Initialize Kafka consumer
                kafka_consumer = KafkaConsumerService(
                    config_path=str(kafka_yaml),
                    decoder=decoder,
                    trace_header_field=trace_header_field
                )
                
                # Add message handler if graph_builder exists
                if graph_builder:
                    kafka_consumer.add_message_handler(graph_builder.add_message)
                
                # Subscribe to topics
                topics_yaml = ROOT_DIR / "config" / "topics.yaml"
                if topics_yaml.exists() and graph_builder:
                    all_topics = graph_builder.topic_graph.get_all_topics()
                    if all_topics:
                        logger.info(f"📋 Subscribing to {len(all_topics)} topics...")
                        kafka_consumer.subscribe_to_topics(all_topics)
                        
                        # Start consuming messages asynchronously
                        logger.info(f"🚀 Starting Kafka message consumption for {new_env}...")
                        
                        # IMPORTANT: Use managed task creation instead of bare asyncio.create_task
                        if hasattr(app.state, 'task_manager'):
                            logger.info(f"🚀 Starting managed Kafka consumption task for {new_env}...")
                            await app.state.task_manager.create_managed_task(
                                kafka_consumer.start_consuming_async(),
                                name=f"kafka_consumer_{new_env}",
                                environment=new_env,
                                task_type="kafka"
                            )
                        else:
                            # Fallback to existing method if task manager not available
                            asyncio.create_task(kafka_consumer.start_consuming_async())
                
                logger.info(f"✅ Kafka consumer initialized for {new_env}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Kafka consumer: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Continue anyway, don't fail the environment switch
        else:
            logger.warning(f"⚠️ No Kafka configuration found for {new_env}")
        
        # Update settings.yaml to persist the change
        settings_path = ROOT_DIR / "config" / "settings.yaml"
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                settings = yaml.safe_load(f)
            
            if 'application' not in settings:
                settings['application'] = {}
            settings['application']['start_env'] = new_env
            
            with open(settings_path, 'w') as f:
                yaml.dump(settings, f, default_flow_style=False)
        
        # Store in app state for current session
        app.state.current_environment = new_env
        
        logger.info(f"✅ Environment switch to {new_env} completed successfully")
        
        return {
            "success": True,
            "environment": new_env,
            "message": f"Switched to {new_env} environment",
            "kafka_connected": kafka_consumer.running if kafka_consumer else False,
            "memory_freed": collected > 0,
            "tasks_managed": hasattr(app.state, 'task_manager')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching environment: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

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

@api_router.put("/blueprint/file-content/{path:path}")
async def save_blueprint_file_content(path: str, request: Dict[str, Any]):
    """Save content to a blueprint file"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        content = request.get("content", "")
        await blueprint_file_manager.write_file(path, content)
        return {"success": True, "message": f"File saved: {path}"}
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/blueprint/delete-file/{path:path}")
async def delete_blueprint_file(path: str):
    """Delete a blueprint file or directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Root path not set")
        
        full_path = Path(root_path) / path
        
        if full_path.is_file():
            full_path.unlink()
            logger.info(f"Deleted file: {path}")
        elif full_path.is_dir():
            import shutil
            shutil.rmtree(full_path)
            logger.info(f"Deleted directory: {path}")
        else:
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        
        return {"success": True, "message": f"Deleted: {path}"}
    except Exception as e:
        logger.error(f"Failed to delete: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/move-file")
async def move_blueprint_file(request: Dict[str, Any]):
    """Move or rename a blueprint file/directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        source_path = request.get("source_path")
        destination_path = request.get("destination_path")
        
        if not source_path or not destination_path:
            raise HTTPException(status_code=400, detail="source_path and destination_path are required")
        
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Root path not set")
        
        source = Path(root_path) / source_path
        destination = Path(root_path) / destination_path
        
        if not source.exists():
            raise HTTPException(status_code=404, detail=f"Source not found: {source_path}")
        
        # Create parent directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        source.rename(destination)
        logger.info(f"Moved {source_path} to {destination_path}")
        
        return {"success": True, "message": f"Moved to {destination_path}"}
    except Exception as e:
        logger.error(f"Failed to move file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/rename-file")
async def rename_blueprint_file(request: Dict[str, Any]):
    """Rename a blueprint file/directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        source_path = request.get("source_path")
        new_name = request.get("new_name")
        
        if not source_path or not new_name:
            raise HTTPException(status_code=400, detail="source_path and new_name are required")
        
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Root path not set")
        
        source = Path(root_path) / source_path
        destination = source.parent / new_name
        
        if not source.exists():
            raise HTTPException(status_code=404, detail=f"Source not found: {source_path}")
        
        if destination.exists():
            raise HTTPException(status_code=409, detail=f"Destination already exists: {new_name}")
        
        source.rename(destination)
        logger.info(f"Renamed {source_path} to {new_name}")
        
        return {"success": True, "message": f"Renamed to {new_name}"}
    except Exception as e:
        logger.error(f"Failed to rename file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/create-directory")
async def create_blueprint_directory(request: FileOperationRequest):
    """Create a new directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    try:
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Root path not set")
        
        new_dir = Path(root_path) / request.path
        new_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {request.path}")
        
        return {"success": True, "message": f"Directory created: {request.path}"}
    except Exception as e:
        logger.error(f"Failed to create directory: {e}")
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
        # List .tar.gz and .tgz files in multiple possible output directories
        root = Path(root_path)
        possible_dirs = [
            root / "dist",
            root / "out",
            root / "build",
            root / "output",
            root  # Check root directory too
        ]
        
        files = []
        for check_dir in possible_dirs:
            if not check_dir.exists() or not check_dir.is_dir():
                continue
            
            try:
                for name in sorted(os.listdir(check_dir)):
                    p = check_dir / name
                    # Check for .tar.gz, .tgz files
                    if p.is_file() and (name.endswith('.tar.gz') or name.endswith('.tgz')):
                        try:
                            stat = p.stat()
                            # Get relative directory name
                            rel_dir = check_dir.relative_to(root) if check_dir != root else Path(".")
                            files.append({
                                "name": name,
                                "path": str(p),
                                "size": stat.st_size,
                                "modified": int(stat.st_mtime),
                                "directory": str(rel_dir)
                            })
                        except (OSError, FileNotFoundError) as e:
                            logger.warning(f"Skipping file {p}: {e}")
                            continue
            except PermissionError:
                logger.warning(f"Permission denied reading directory: {check_dir}")
                continue
        
        logger.info(f"Found {len(files)} output files in {root_path}")
        return {"files": files}
    except Exception as e:
        logger.error(f"Error loading output files: {e}")
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

@api_router.post("/blueprint/validate/{filepath:path}")
async def validate_blueprint_tgz(filepath: str, payload: Dict[str, Any]):
    """Validate a blueprint .tgz file by calling blueprint server
    
    Args:
        filepath: Path to the .tgz file (can be full path or just filename)
        payload: Contains tgz_file, environment, and action
    """
    if not blueprint_build_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint build manager not initialized")
    
    # Extract just the filename from the path
    from pathlib import Path
    filename = Path(filepath).name
    environment = payload.get('environment', 'TEST')
    
    logger.info("="*80)
    logger.info(f"📋 [VALIDATE] Starting blueprint validation")
    logger.info(f"   File: {filename}")
    logger.info(f"   Full path: {filepath}")
    logger.info(f"   Environment: {environment}")
    logger.info(f"   Payload: {payload}")
    logger.info("="*80)
    
    try:
        # Get root path
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        
        # Resolve the full path to the .tgz file
        # If it's just a filename, look for it in the out/ directory
        if not filepath.startswith('/'):
            # Try common output directories
            output_dirs = ['out', 'output', 'build', 'dist']
            full_tgz_path = None
            
            for output_dir in output_dirs:
                potential_path = os.path.join(root_path, output_dir, filepath)
                if os.path.exists(potential_path):
                    full_tgz_path = potential_path
                    logger.info(f"📁 Found blueprint file at: {full_tgz_path}")
                    break
            
            if not full_tgz_path:
                # Try root directory as fallback
                potential_path = os.path.join(root_path, filepath)
                if os.path.exists(potential_path):
                    full_tgz_path = potential_path
                    logger.info(f"📁 Found blueprint file at: {full_tgz_path}")
                else:
                    logger.error(f"❌ Blueprint file not found in any output directory: {filepath}")
                    logger.error(f"   Searched in: {', '.join([os.path.join(root_path, d) for d in output_dirs])}")
                    raise HTTPException(status_code=404, detail=f"Blueprint file not found: {filepath}")
        else:
            full_tgz_path = filepath
            if not os.path.exists(full_tgz_path):
                logger.error(f"❌ Blueprint file not found at: {full_tgz_path}")
                raise HTTPException(status_code=404, detail=f"Blueprint file not found: {filepath}")
        
        logger.info(f"✅ Using blueprint file: {full_tgz_path}")
        
        # Load environment configuration from YAML
        import yaml
        from pathlib import Path
        env_file = Path(__file__).parent / "config" / "environments" / f"{environment.lower()}.yaml"
        
        logger.info(f"📂 Loading environment config from: {env_file}")
        
        if not env_file.exists():
            logger.error(f"❌ Environment config file not found: {env_file}")
            raise HTTPException(status_code=400, detail=f"Environment {environment} not configured")
        
        with open(env_file, 'r') as f:
            env_config_data = yaml.safe_load(f)
        
        if 'blueprint_server' not in env_config_data:
            logger.error(f"❌ 'blueprint_server' section not found in {env_file}")
            raise HTTPException(status_code=400, detail=f"Blueprint server not configured for {environment}")
        
        env_config = env_config_data['blueprint_server']
        logger.info(f"🔧 Loaded environment config:")
        logger.info(f"   Base URL: {env_config.get('base_url')}")
        logger.info(f"   Validate path: {env_config.get('validate_path')}")
        logger.info(f"   Auth header: {env_config.get('auth_header_name')}: {env_config.get('auth_header_value')[:10]}...")
        
        # Get namespace from blueprint_cnf.json
        blueprint_cnf_path = os.path.join(root_path, "blueprint_cnf.json")
        namespace = "default"
        if os.path.exists(blueprint_cnf_path):
            with open(blueprint_cnf_path, 'r') as f:
                blueprint_cnf = json.load(f)
                namespace = blueprint_cnf.get('namespace', 'default')
        
        logger.info(f"📦 Using namespace: {namespace}")
        
        # Call deployment manager
        from src.blueprint_models import EnvironmentConfig, DeploymentAction
        env_cfg = EnvironmentConfig(**env_config)
        
        logger.info(f"🚀 Calling blueprint server validate endpoint...")
        result = await blueprint_build_manager.deploy_blueprint(
            root_path=root_path,
            tgz_file=full_tgz_path,
            environment=environment,
            action=DeploymentAction.VALIDATE,
            env_config=env_cfg,
            namespace=namespace
        )
        
        logger.info(f"📥 Response received:")
        logger.info(f"   Success: {result.success}")
        logger.info(f"   Status Code: {result.status_code}")
        logger.info(f"   Response Length: {len(result.response)} chars")
        logger.info(f"   Response Preview: {result.response[:500] if result.response else 'None'}")
        if result.error_message:
            logger.error(f"   Error: {result.error_message}")
        logger.info("="*80)
        
        return {
            "status": "validated" if result.success else "failed",
            "success": result.success,
            "file": filename,
            "filepath": filepath,
            "environment": environment,
            "status_code": result.status_code,
            "response": result.response,
            "error_message": result.error_message,
            "details": {
                "namespace": namespace,
                "endpoint": env_cfg.base_url + env_cfg.validate_path.replace('{namespace}', namespace)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/activate/{filepath:path}")
async def activate_blueprint_tgz(filepath: str, payload: Dict[str, Any]):
    """Activate a blueprint .tgz file by calling blueprint server
    
    Args:
        filepath: Path to the .tgz file (can be full path or just filename)
        payload: Contains tgz_file, environment, and action
    """
    if not blueprint_build_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint build manager not initialized")
    
    # Extract just the filename from the path
    from pathlib import Path
    filename = Path(filepath).name
    environment = payload.get('environment', 'TEST')
    
    logger.info("="*80)
    logger.info(f"🚀 [ACTIVATE] Starting blueprint activation")
    logger.info(f"   File: {filename}")
    logger.info(f"   Full path: {filepath}")
    logger.info(f"   Environment: {environment}")
    logger.info(f"   Payload: {payload}")
    logger.info("="*80)
    
    try:
        # Get root path
        root_path = blueprint_file_manager.root_path
        if not root_path:
            raise HTTPException(status_code=400, detail="Blueprint root path not set")
        
        # Resolve the full path to the .tgz file
        # If it's just a filename, look for it in the out/ directory
        if not filepath.startswith('/'):
            # Try common output directories
            output_dirs = ['out', 'output', 'build', 'dist']
            full_tgz_path = None
            
            for output_dir in output_dirs:
                potential_path = os.path.join(root_path, output_dir, filepath)
                if os.path.exists(potential_path):
                    full_tgz_path = potential_path
                    logger.info(f"📁 Found blueprint file at: {full_tgz_path}")
                    break
            
            if not full_tgz_path:
                # Try root directory as fallback
                potential_path = os.path.join(root_path, filepath)
                if os.path.exists(potential_path):
                    full_tgz_path = potential_path
                    logger.info(f"📁 Found blueprint file at: {full_tgz_path}")
                else:
                    logger.error(f"❌ Blueprint file not found in any output directory: {filepath}")
                    logger.error(f"   Searched in: {', '.join([os.path.join(root_path, d) for d in output_dirs])}")
                    raise HTTPException(status_code=404, detail=f"Blueprint file not found: {filepath}")
        else:
            full_tgz_path = filepath
            if not os.path.exists(full_tgz_path):
                logger.error(f"❌ Blueprint file not found at: {full_tgz_path}")
                raise HTTPException(status_code=404, detail=f"Blueprint file not found: {filepath}")
        
        logger.info(f"✅ Using blueprint file: {full_tgz_path}")
        
        # Load environment configuration from YAML
        import yaml
        from pathlib import Path
        env_file = Path(__file__).parent / "config" / "environments" / f"{environment.lower()}.yaml"
        
        logger.info(f"📂 Loading environment config from: {env_file}")
        
        if not env_file.exists():
            logger.error(f"❌ Environment config file not found: {env_file}")
            raise HTTPException(status_code=400, detail=f"Environment {environment} not configured")
        
        with open(env_file, 'r') as f:
            env_config_data = yaml.safe_load(f)
        
        if 'blueprint_server' not in env_config_data:
            logger.error(f"❌ 'blueprint_server' section not found in {env_file}")
            raise HTTPException(status_code=400, detail=f"Blueprint server not configured for {environment}")
        
        env_config = env_config_data['blueprint_server']
        logger.info(f"🔧 Loaded environment config:")
        logger.info(f"   Base URL: {env_config.get('base_url')}")
        logger.info(f"   Activate path: {env_config.get('activate_path')}")
        logger.info(f"   Auth header: {env_config.get('auth_header_name')}: {env_config.get('auth_header_value')[:10]}...")
        
        # Get namespace from blueprint_cnf.json
        blueprint_cnf_path = os.path.join(root_path, "blueprint_cnf.json")
        namespace = "default"
        if os.path.exists(blueprint_cnf_path):
            with open(blueprint_cnf_path, 'r') as f:
                blueprint_cnf = json.load(f)
                namespace = blueprint_cnf.get('namespace', 'default')
        
        logger.info(f"📦 Using namespace: {namespace}")
        
        # Call deployment manager
        from src.blueprint_models import EnvironmentConfig, DeploymentAction
        env_cfg = EnvironmentConfig(**env_config)
        
        logger.info(f"🚀 Calling blueprint server activate endpoint...")
        result = await blueprint_build_manager.deploy_blueprint(
            root_path=root_path,
            tgz_file=full_tgz_path,
            environment=environment,
            action=DeploymentAction.ACTIVATE,
            env_config=env_cfg,
            namespace=namespace
        )
        
        logger.info(f"📥 Response received:")
        logger.info(f"   Success: {result.success}")
        logger.info(f"   Status Code: {result.status_code}")
        logger.info(f"   Response Length: {len(result.response)} chars")
        logger.info(f"   Response Preview: {result.response[:500] if result.response else 'None'}")
        if result.error_message:
            logger.error(f"   Error: {result.error_message}")
        logger.info("="*80)
        
        return {
            "status": "activated" if result.success else "failed",
            "success": result.success,
            "file": filename,
            "filepath": filepath,
            "environment": environment,
            "status_code": result.status_code,
            "response": result.response,
            "error_message": result.error_message,
            "details": {
                "namespace": namespace,
                "endpoint": env_cfg.base_url + env_cfg.activate_path.replace('{namespace}', namespace)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Activation error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

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
# Multi-Project Git Integration API Endpoints
# -----------------------------------------------------------------------------

@api_router.get("/blueprint/integration/projects")
async def get_integration_projects():
    """Get list of all projects in integration directory"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        # Discover and return all projects
        projects = await app.state.integration_manager.discover_projects()
        return {
            "success": True,
            "projects": [project.dict() for project in projects],
            "total": len(projects)
        }
    except Exception as e:
        logger.error(f"Error getting integration projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/integration/add-project")
async def add_git_project(request: Dict[str, Any]):
    """Add a new Git project (clone if needed, or return existing)"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        from src.integration_models import AddProjectRequest
        
        # Validate request
        add_request = AddProjectRequest(**request)
        
        # Get or create project
        project, error = await app.state.integration_manager.get_or_create_project(add_request)
        
        if error:
            return {
                "success": False,
                "message": error,
                "project": None
            }
        
        # Broadcast update to WebSocket clients
        await websocket_manager.broadcast({
            "type": "project_added",
            "project": project.dict()
        })
        
        return {
            "success": True,
            "message": f"Project added successfully: {project.name}",
            "project": project.dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.delete("/blueprint/integration/projects/{project_id}")
async def remove_project(project_id: str, force: bool = False):
    """Remove project from integration directory (hard delete)"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        success, error = await app.state.integration_manager.remove_project(project_id, force)
        
        if not success:
            return {
                "success": False,
                "message": error or "Failed to remove project"
            }
        
        # Broadcast update to WebSocket clients
        await websocket_manager.broadcast({
            "type": "project_removed",
            "project_id": project_id
        })
        
        return {
            "success": True,
            "message": f"Project removed successfully: {project_id}"
        }
    except Exception as e:
        logger.error(f"Error removing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/blueprint/integration/projects/{project_id}/git/status")
async def get_project_git_status(project_id: str):
    """Get Git status for specific project"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        status = await app.state.integration_manager.get_project_git_status(project_id)
        
        if not status:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        return {
            "success": True,
            "project_id": project_id,
            "status": {
                "is_repo": status.is_repo,
                "current_branch": status.current_branch,
                "remote_url": status.remote_url,
                "has_uncommitted_changes": status.has_uncommitted_changes,
                "uncommitted_files": status.uncommitted_files,
                "ahead_commits": status.ahead_commits,
                "behind_commits": status.behind_commits,
                "last_commit": status.last_commit,
                "last_commit_author": status.last_commit_author,
                "last_commit_date": status.last_commit_date
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project Git status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/integration/projects/{project_id}/git/pull")
async def pull_project_changes(project_id: str):
    """Pull latest changes for specific project"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        git_service = app.state.integration_manager.get_git_service(project_id)
        if not git_service:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        result = await git_service.pull_changes()
        
        if result.success:
            # Broadcast update
            await websocket_manager.broadcast({
                "type": "project_git_operation",
                "project_id": project_id,
                "operation": "pull",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pulling project changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/integration/projects/{project_id}/git/push")
async def push_project_changes(project_id: str, request: Dict[str, Any]):
    """Push changes for specific project"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        commit_message = request.get('commit_message')
        force = request.get('force', False)
        selected_files = request.get('selected_files', None)  # Optional list of files to stage
        
        if not commit_message:
            raise HTTPException(status_code=400, detail="commit_message is required")
        
        git_service = app.state.integration_manager.get_git_service(project_id)
        if not git_service:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        # If specific files are selected, stage them first
        if selected_files and isinstance(selected_files, list) and len(selected_files) > 0:
            result = await git_service.push_selected_changes(commit_message, selected_files, force)
        else:
            # Push all changes (existing behavior)
            result = await git_service.push_changes(commit_message, force)
        
        if result.success:
            # Broadcast update
            await websocket_manager.broadcast({
                "type": "project_git_operation",
                "project_id": project_id,
                "operation": "push",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error,
            "details": result.details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pushing project changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/integration/projects/{project_id}/git/reset")
async def reset_project_changes(project_id: str):
    """Reset all local changes for specific project"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        git_service = app.state.integration_manager.get_git_service(project_id)
        if not git_service:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        result = await git_service.reset_changes()
        
        if result.success:
            # Broadcast update
            await websocket_manager.broadcast({
                "type": "project_git_operation",
                "project_id": project_id,
                "operation": "reset",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting project changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/integration/projects/{project_id}/git/switch-branch")
async def switch_project_branch(project_id: str, request: Dict[str, Any]):
    """Switch branch for specific project"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        branch_name = request.get('branch_name')
        
        if not branch_name:
            raise HTTPException(status_code=400, detail="branch_name is required")
        
        git_service = app.state.integration_manager.get_git_service(project_id)
        if not git_service:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        result = await git_service.switch_branch(branch_name)
        
        if result.success:
            # Broadcast update
            await websocket_manager.broadcast({
                "type": "project_git_operation",
                "project_id": project_id,
                "operation": "switch_branch",
                "success": True,
                "message": result.message,
                "branch": branch_name
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error,
            "details": result.details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching project branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/blueprint/integration/projects/{project_id}/git/branches")
async def get_project_branches(project_id: str):
    """Get list of all branches for specific project"""
    if not hasattr(app.state, 'integration_manager') or not app.state.integration_manager:
        raise HTTPException(status_code=503, detail="Integration manager not initialized")
    
    try:
        git_service = app.state.integration_manager.get_git_service(project_id)
        if not git_service:
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        branches = await git_service.list_branches()
        
        return {
            "success": True,
            "project_id": project_id,
            "branches": branches
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# Legacy Single-Project Git Integration API Endpoints (Deprecated)
# These endpoints are maintained for backward compatibility
# New code should use the multi-project endpoints above
# -----------------------------------------------------------------------------

@api_router.get("/blueprint/git/status")
async def get_git_status():
    """Get current Git repository status"""
    if not hasattr(app.state, 'git_service') or not app.state.git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        status = await app.state.git_service.get_status()
        return {
            "success": True,
            "status": {
                "is_repo": status.is_repo,
                "current_branch": status.current_branch,
                "remote_url": status.remote_url,
                "has_uncommitted_changes": status.has_uncommitted_changes,
                "uncommitted_files": status.uncommitted_files,
                "ahead_commits": status.ahead_commits,
                "behind_commits": status.behind_commits,
                "last_commit": status.last_commit,
                "last_commit_author": status.last_commit_author,
                "last_commit_date": status.last_commit_date
            }
        }
    except Exception as e:
        logger.error(f"Error getting Git status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/blueprint/git/branches")
async def get_git_branches():
    """Get list of all branches"""
    if not hasattr(app.state, 'git_service') or not app.state.git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        branches = await app.state.git_service.list_branches()
        return {
            "success": True,
            "branches": branches
        }
    except Exception as e:
        logger.error(f"Error getting Git branches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/git/clone")
async def clone_repository(request: Dict[str, Any]):
    """Clone a Git repository into integrator folder"""
    if not hasattr(app.state, 'git_service') or not app.state.git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        git_url = request.get('git_url')
        branch = request.get('branch', 'main')
        credentials = request.get('credentials')
        
        if not git_url:
            raise HTTPException(status_code=400, detail="git_url is required")
        
        result = await app.state.git_service.clone_repository(git_url, branch, credentials)
        
        if result.success:
            # Set integrator path as blueprint root path
            integrator_path = str(app.state.git_service.integrator_path)
            if blueprint_file_manager:
                blueprint_file_manager.set_root_path(integrator_path)
                logger.info(f"Set blueprint root path to integrator: {integrator_path}")
            
            # Broadcast update to WebSocket clients
            await websocket_manager.broadcast({
                "type": "git_operation",
                "operation": "clone",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error,
            "details": result.details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/git/pull")
async def pull_changes():
    """Pull latest changes from remote repository"""
    if not hasattr(app.state, 'git_service') or not app.state.git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        result = await app.state.git_service.pull_changes()
        
        if result.success:
            # Broadcast update to WebSocket clients
            await websocket_manager.broadcast({
                "type": "git_operation",
                "operation": "pull",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error
        }
    except Exception as e:
        logger.error(f"Error pulling changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/git/push")
async def push_changes(request: Dict[str, Any]):
    """Add all changes, commit, and push to remote repository"""
    if not hasattr(app.state, 'git_service') or not app.state.git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        commit_message = request.get('commit_message')
        force = request.get('force', False)
        
        if not commit_message:
            raise HTTPException(status_code=400, detail="commit_message is required")
        
        result = await app.state.git_service.push_changes(commit_message, force)
        
        if result.success:
            # Broadcast update to WebSocket clients
            await websocket_manager.broadcast({
                "type": "git_operation",
                "operation": "push",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error,
            "details": result.details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pushing changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/git/reset")
async def reset_changes():
    """Reset all local changes to HEAD"""
    if not hasattr(app.state, 'git_service') or not app.state.git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        result = await app.state.git_service.reset_changes()
        
        if result.success:
            # Broadcast update to WebSocket clients
            await websocket_manager.broadcast({
                "type": "git_operation",
                "operation": "reset",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error
        }
    except Exception as e:
        logger.error(f"Error resetting changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/blueprint/git/switch-branch")
async def switch_branch(request: Dict[str, Any]):
    """Switch to a different branch"""
    if not hasattr(app.state, 'git_service') or not app.state.git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        branch_name = request.get('branch_name')
        
        if not branch_name:
            raise HTTPException(status_code=400, detail="branch_name is required")
        
        result = await app.state.git_service.switch_branch(branch_name)
        
        if result.success:
            # Broadcast update to WebSocket clients
            await websocket_manager.broadcast({
                "type": "git_operation",
                "operation": "switch_branch",
                "success": True,
                "message": result.message
            })
        
        return {
            "success": result.success,
            "message": result.message,
            "output": result.output,
            "error": result.error,
            "details": result.details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error switching branch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# Kafka/Traces placeholder endpoints (keep UI functional in mock mode)
# -----------------------------------------------------------------------------
@api_router.get("/topics")
async def get_topics():
    try:
        # Get topics with statistics from graph_builder
        if graph_builder:
            stats = graph_builder.get_statistics()
            topic_stats = stats.get('topics', {})
            topic_details_dict = topic_stats.get('details', {})
            
            # Convert dict to list and add topic name
            topic_details = []
            for topic_name, details in topic_details_dict.items():
                topic_info = {
                    'name': topic_name,
                    **details  # Spread all the details
                }
                topic_details.append(topic_info)
            
            # Extract topic names
            all_topics = list(topic_details_dict.keys())
            
            # Use stored monitored topics if available, otherwise use all topics with messages
            if hasattr(app.state, 'monitored_topics') and app.state.monitored_topics:
                monitored = app.state.monitored_topics
            else:
                # Default: monitor topics that have messages
                monitored = [t for t, d in topic_details_dict.items() if d.get('message_count', 0) > 0]
                # If no topics have messages yet, monitor all topics
                if not monitored:
                    monitored = all_topics
            
            return {
                "topics": all_topics,
                "monitored": monitored,
                "topic_details": topic_details  # Include full statistics
            }
        
        # Fallback: Try to get from configuration file
        topics_yaml = ROOT_DIR / "config" / "topics.yaml"
        if topics_yaml.exists():
            with open(topics_yaml, 'r') as f:
                topics_cfg = yaml.safe_load(f)
                configured_topics = list(topics_cfg.get('topics', {}).keys())
                return {"topics": configured_topics, "monitored": configured_topics}
        
        # Final fallback
        return {"topics": [], "monitored": []}
    except Exception as e:
        logger.error(f"Failed to get topics: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
            # Get topic graph data with statistics and colors
            graph_data = graph_builder.get_topic_graph_data()
            return graph_data
        
        # Fallback with basic data
        return {
            "nodes": [],
            "edges": []
        }
    except Exception as e:
        logger.error(f"Failed to get topic graph: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/graph/disconnected")
async def get_disconnected_components():
    """Get disconnected components in the topic graph with real-time statistics"""
    try:
        if graph_builder:
            # Get real disconnected components from graph_builder with real statistics
            components = graph_builder.get_disconnected_graphs()
            
            return {
                "success": True,
                "components": components,
                "total_components": len(components)
            }
        
        # Fallback when graph_builder is not available
        return {"success": True, "components": [], "total_components": 0}
    except Exception as e:
        logger.error(f"Failed to get disconnected components: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
    """Get comprehensive statistics including topic details from graph_builder"""
    try:
        if graph_builder:
            # Get real-time statistics from graph_builder
            return graph_builder.get_statistics()
        
        # Fallback when graph_builder is not available
        return {
            "traces": {
                "total": 0,
                "max_capacity": 1000,
                "utilization": 0
            },
            "topics": {
                "total": 0,
                "monitored": 0,
                "with_messages": 0,
                "details": {}
            },
            "messages": {
                "total": 0,
                "by_topic": {}
            },
            "time_range": {
                "earliest": None,
                "latest": None
            }
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/traces")
async def get_traces():
    try:
        if graph_builder is None:
            return {"traces": [], "total": 0, "page": 1, "per_page": 50}
        
        # Get trace summary from graph_builder
        summary = graph_builder.get_trace_summary()
        
        return {
            "traces": summary.get('traces', []),
            "total": summary.get('total_traces', 0),
            "page": 1,
            "per_page": 50
        }
    except Exception as e:
        logger.error(f"Failed to get traces: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trace/{trace_id}")
async def get_trace_detail(trace_id: str):
    """Get detailed information about a specific trace"""
    try:
        if graph_builder is None:
            raise HTTPException(status_code=503, detail="Graph builder not initialized")
        
        # Get trace from graph_builder
        if trace_id not in graph_builder.traces:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        
        trace = graph_builder.traces[trace_id]
        
        # Build detailed trace response
        messages = [msg.to_dict() for msg in trace.messages]
        
        # Calculate duration
        duration_ms = 0
        if trace.start_time and trace.end_time:
            duration_ms = int((trace.end_time - trace.start_time).total_seconds() * 1000)
        
        return {
            "trace_id": trace_id,
            "start_time": trace.start_time.isoformat() if trace.start_time else None,
            "end_time": trace.end_time.isoformat() if trace.end_time else None,
            "duration_ms": duration_ms,
            "message_count": len(trace.messages),
            "topics": list(trace.topics),
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace detail: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trace/{trace_id}/flow")
async def get_trace_flow(trace_id: str):
    """Get flow/graph data for a specific trace"""
    try:
        if graph_builder is None:
            raise HTTPException(status_code=503, detail="Graph builder not initialized")
        
        # Get trace from graph_builder
        if trace_id not in graph_builder.traces:
            raise HTTPException(status_code=404, detail=f"Trace not found: {trace_id}")
        
        trace = graph_builder.traces[trace_id]
        
        # Build nodes (topics) and edges (message flow)
        nodes = []
        edges = []
        topic_set = set()
        
        for i, msg in enumerate(trace.messages):
            topic = msg.topic
            if topic and topic not in topic_set:
                nodes.append({
                    "id": topic,
                    "label": topic,
                    "message_count": sum(1 for m in trace.messages if m.topic == topic)
                })
                topic_set.add(topic)
            
            # Create edge to next message's topic
            if i < len(trace.messages) - 1:
                next_topic = trace.messages[i + 1].topic
                if topic and next_topic and topic != next_topic:
                    edges.append({
                        "source": topic,
                        "target": next_topic,
                        "label": f"msg {i+1}"
                    })
        
        return {
            "trace_id": trace_id,
            "nodes": nodes,
            "edges": edges
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace flow: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# WebSocket Connection Manager
# -----------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {e}")
                dead_connections.append(connection)
        
        # Remove dead connections
        for conn in dead_connections:
            self.disconnect(conn)

websocket_manager = ConnectionManager()

async def broadcast_message(message: dict):
    """Helper function to broadcast messages"""
    await websocket_manager.broadcast(message)

# -----------------------------------------------------------------------------
# WebSockets
# -----------------------------------------------------------------------------
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        websocket_manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}")

@api_router.websocket("/ws/blueprint")
async def blueprint_websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for messages
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("Blueprint WebSocket disconnected")
    except Exception as e:
        websocket_manager.disconnect(websocket)
        logger.error(f"Blueprint WebSocket error: {e}")

# -----------------------------------------------------------------------------
# Redis Verification API Endpoints
# -----------------------------------------------------------------------------

@api_router.post("/redis/test-connection")
async def test_redis_connection(request: Dict[str, Any]):
    """Test Redis connection for a specific environment"""
    environment = request.get("environment", "DEV") if request else "DEV"
    # Handle empty string
    if not environment:
        environment = "DEV"
    
    logger.info("="*80)
    logger.info(f"🔌 [REDIS TEST] Endpoint HIT!")
    logger.info(f"🔌 [REDIS TEST] Request body: {request}")
    logger.info(f"🔌 [REDIS TEST] Testing Redis connection for environment: '{environment}'")
    logger.info("="*80)
    
    try:
        # Read Redis configuration from environment-specific file
        env_file = ROOT_DIR / "config" / "environments" / f"{environment.lower()}.yaml"
        logger.info(f"📁 Environment config file: {env_file}")
        
        if not env_file.exists():
            logger.error(f"❌ Environment config not found: {env_file}")
            return {
                "status": "failed",
                "error": f"Environment configuration file not found: {environment.lower()}.yaml"
            }
        
        with open(env_file, 'r') as f:
            env_config = yaml.safe_load(f)
        
        logger.info(f"🔧 Looking for redis configuration in {environment} environment file...")
        redis_config = env_config.get('redis')
        
        if not redis_config:
            logger.warning(f"⚠️ No Redis config found in {environment} environment file")
            return {
                "status": "failed",
                "error": f"No Redis configuration found for environment: {environment}"
            }
        
        logger.info(f"✅ Found Redis config - Host: {redis_config.get('host')}, Port: {redis_config.get('port')}")
        
        # Try to connect to Redis (support both standalone and cluster)
        import redis
        from redis.cluster import RedisCluster
        try:
            logger.info(f"🔌 Attempting connection...")
            
            # Detect if this is a cluster configuration
            is_cluster = 'clustercfg' in redis_config.get('host', '').lower() or redis_config.get('cluster', False)
            
            # Build base connection parameters
            base_params = {
                'socket_timeout': redis_config.get('socket_timeout', 5),
                'socket_connect_timeout': redis_config.get('connection_timeout', 5),
            }
            
            # Add authentication if token is provided
            if redis_config.get('token'):
                base_params['password'] = redis_config.get('token')
            elif redis_config.get('password'):
                base_params['password'] = redis_config.get('password')
            
            # Add SSL if ca_cert_path is provided
            if redis_config.get('ca_cert_path'):
                import ssl
                base_params['ssl'] = True
                base_params['ssl_cert_reqs'] = ssl.CERT_REQUIRED
                ca_cert_full_path = ROOT_DIR / redis_config.get('ca_cert_path')
                if ca_cert_full_path.exists():
                    base_params['ssl_ca_certs'] = str(ca_cert_full_path)
                    logger.info(f"🔒 Using SSL with CA cert: {ca_cert_full_path}")
            
            # Create appropriate client
            if is_cluster:
                logger.info(f"🔗 Detected Redis Cluster configuration")
                redis_client = RedisCluster(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    **base_params
                )
            else:
                logger.info(f"📍 Using standalone Redis configuration")
                conn_params = {
                    'host': redis_config.get('host', 'localhost'),
                    'port': redis_config.get('port', 6379),
                    **base_params
                }
                # Add DB only for standalone Redis (clusters don't support db selection)
                if redis_config.get('db') is not None:
                    conn_params['db'] = redis_config.get('db', 0)
                
                redis_client = redis.Redis(**conn_params)
            
            # Test connection with ping
            redis_client.ping()
            redis_client.close()
            logger.info(f"✅ Redis connection successful!")
            
            return {
                "status": "connected",
                "host": redis_config.get('host'),
                "port": redis_config.get('port')
            }
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return {
                "status": "failed",
                "error": f"Cannot connect to Redis: {str(e)}"
            }
        except Exception as e:
            logger.error(f"❌ Redis error: {e}")
            return {
                "status": "failed",
                "error": f"Redis error: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"❌ Error testing Redis connection: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "failed",
            "error": str(e)
        }

@api_router.get("/redis/environments")
async def get_redis_environments():
    """Get list of environments that have Redis configuration"""
    try:
        env_dir = ROOT_DIR / "config" / "environments"
        environments = []
        
        if env_dir.exists():
            for env_file in env_dir.glob("*.yaml"):
                try:
                    with open(env_file, 'r') as f:
                        config = yaml.safe_load(f)
                        if config.get('redis'):
                            env_name = env_file.stem.upper()
                            environments.append(env_name)
                except Exception as e:
                    logger.warning(f"Could not load {env_file}: {e}")
        
        return {
            "environments": environments,
            "count": len(environments)
        }
    except Exception as e:
        logger.error(f"Error getting Redis environments: {e}")
        return {"environments": [], "count": 0, "error": str(e)}

@api_router.get("/redis/file-content")
async def get_redis_file_content(key: str, environment: str):
    """Get content of a specific Redis key"""
    logger.info("="*80)
    logger.info(f"📄 [REDIS FILE CONTENT] Endpoint HIT!")
    logger.info(f"📄 [REDIS FILE CONTENT] Key: '{key}'")
    logger.info(f"📄 [REDIS FILE CONTENT] Environment: '{environment}'")
    logger.info("="*80)
    
    # Validate parameters
    if not key:
        logger.warning("❌ [REDIS FILE CONTENT] Missing key parameter")
        return {"error": "Key parameter is required"}
    
    if not environment:
        logger.warning("❌ [REDIS FILE CONTENT] Missing environment parameter")
        return {"error": "Environment parameter is required"}
    
    try:
        # Read Redis configuration from environment-specific file
        env_file = ROOT_DIR / "config" / "environments" / f"{environment.lower()}.yaml"
        logger.info(f"📁 Looking for environment config at: {env_file}")
        
        if not env_file.exists():
            logger.error(f"❌ Environment config not found: {env_file}")
            return {"error": f"Environment configuration file not found: {environment.lower()}.yaml"}
        
        with open(env_file, 'r') as f:
            env_config = yaml.safe_load(f)
        
        redis_config = env_config.get('redis')
        
        if not redis_config:
            logger.warning(f"⚠️ No Redis configuration in {environment} environment file")
            return {"error": f"No Redis configuration found for environment: {environment}"}
        
        logger.info(f"✅ Redis config found - Host: {redis_config.get('host')}, Port: {redis_config.get('port')}")
        
        # Connect to Redis (support both standalone and cluster)
        import redis
        from redis.cluster import RedisCluster
        try:
            logger.info(f"🔌 Connecting to Redis...")
            
            # Detect if this is a cluster configuration
            is_cluster = 'clustercfg' in redis_config.get('host', '').lower() or redis_config.get('cluster', False)
            
            # Build base connection parameters
            base_params = {
                'socket_timeout': redis_config.get('socket_timeout', 5),
                'socket_connect_timeout': redis_config.get('connection_timeout', 5),
            }
            
            # Add authentication
            if redis_config.get('token'):
                base_params['password'] = redis_config.get('token')
            elif redis_config.get('password'):
                base_params['password'] = redis_config.get('password')
            
            # Add SSL if ca_cert_path is provided
            if redis_config.get('ca_cert_path'):
                import ssl
                base_params['ssl'] = True
                base_params['ssl_cert_reqs'] = ssl.CERT_REQUIRED
                ca_cert_full_path = ROOT_DIR / redis_config.get('ca_cert_path')
                if ca_cert_full_path.exists():
                    base_params['ssl_ca_certs'] = str(ca_cert_full_path)
                    logger.info(f"🔒 Using SSL with CA cert: {ca_cert_full_path}")
            
            # Create appropriate client
            if is_cluster:
                logger.info(f"🔗 Using Redis Cluster client")
                redis_client = RedisCluster(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    **base_params
                )
            else:
                logger.info(f"📍 Using standalone Redis client")
                conn_params = {
                    'host': redis_config.get('host', 'localhost'),
                    'port': redis_config.get('port', 6379),
                    **base_params
                }
                if redis_config.get('db') is not None:
                    conn_params['db'] = redis_config.get('db', 0)
                
                redis_client = redis.Redis(**conn_params)
            
            # Test connection
            redis_client.ping()
            logger.info(f"✅ Redis connection successful")
            
            # Get the key content
            logger.info(f"📖 Fetching content for key: {key}")
            content = redis_client.get(key)
            
            if content is None:
                logger.warning(f"⚠️ Key not found: {key}")
                redis_client.close()
                return {"error": f"Key not found: {key}"}
            
            # Decode content
            try:
                decoded_content = content.decode('utf-8') if isinstance(content, bytes) else str(content)
                logger.info(f"✅ Successfully retrieved content ({len(decoded_content)} bytes)")
            except UnicodeDecodeError:
                # If it's binary data, return base64 encoded
                import base64
                decoded_content = base64.b64encode(content).decode('utf-8')
                logger.info(f"✅ Retrieved binary content ({len(content)} bytes, base64 encoded)")
                redis_client.close()
                return {
                    "key": key,
                    "content": decoded_content,
                    "encoding": "base64",
                    "size": len(content)
                }
            
            redis_client.close()
            
            return {
                "key": key,
                "content": decoded_content,
                "encoding": "utf-8",
                "size": len(decoded_content)
            }
            
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return {"error": f"Cannot connect to Redis: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Redis error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": f"Redis error: {str(e)}"}
            
    except Exception as e:
        logger.error(f"❌ Error getting Redis file content: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@api_router.get("/redis/files")
async def get_redis_files(environment: str = "", namespace: str = ""):
    """Get list of files stored in Redis for a specific environment and namespace"""
    logger.info("="*80)
    logger.info(f"🔍 [REDIS FILES] Endpoint HIT!")
    logger.info(f"🔍 [REDIS FILES] Environment parameter: '{environment}' (empty={not environment})")
    logger.info(f"🔍 [REDIS FILES] Namespace parameter: '{namespace}' (empty={not namespace})")
    logger.info("="*80)
    
    # Validate parameters
    if not environment:
        logger.warning("❌ [REDIS FILES] Missing environment parameter")
        return {
            "files": [],
            "count": 0,
            "error": "Environment parameter is required"
        }
    
    if not namespace:
        logger.warning("❌ [REDIS FILES] Missing namespace parameter")
        return {
            "files": [],
            "count": 0,
            "error": "Namespace parameter is required. Make sure blueprint_cnf.json is configured with a namespace."
        }
    
    try:
        # Read Redis configuration from environment-specific file
        env_file = ROOT_DIR / "config" / "environments" / f"{environment.lower()}.yaml"
        logger.info(f"📁 Looking for environment config at: {env_file}")
        
        if not env_file.exists():
            logger.error(f"❌ Environment config not found: {env_file}")
            return {"files": [], "count": 0, "error": f"Environment configuration file not found: {environment.lower()}.yaml"}
        
        logger.info(f"✅ Found environment config, loading...")
        with open(env_file, 'r') as f:
            env_config = yaml.safe_load(f)
        
        logger.info(f"🔧 Looking for Redis config in {environment} environment file...")
        redis_config = env_config.get('redis')
        
        if not redis_config:
            logger.warning(f"⚠️ No Redis configuration in {environment} environment file")
            return {"files": [], "count": 0, "error": f"No Redis configuration found for environment: {environment}"}
        
        logger.info(f"✅ Redis config found - Host: {redis_config.get('host')}, Port: {redis_config.get('port')}")
        
        # Connect to Redis (support both standalone and cluster)
        import redis
        from redis.cluster import RedisCluster
        try:
            logger.info(f"🔌 Connecting to Redis...")
            
            # Detect if this is a cluster configuration
            is_cluster = 'clustercfg' in redis_config.get('host', '').lower() or redis_config.get('cluster', False)
            
            # Build base connection parameters
            base_params = {
                'socket_timeout': redis_config.get('socket_timeout', 5),
                'socket_connect_timeout': redis_config.get('connection_timeout', 5),
            }
            
            # Add authentication if token is provided
            if redis_config.get('token'):
                base_params['password'] = redis_config.get('token')
            elif redis_config.get('password'):
                base_params['password'] = redis_config.get('password')
            
            # Add SSL if ca_cert_path is provided
            if redis_config.get('ca_cert_path'):
                import ssl
                base_params['ssl'] = True
                base_params['ssl_cert_reqs'] = ssl.CERT_REQUIRED
                ca_cert_full_path = ROOT_DIR / redis_config.get('ca_cert_path')
                if ca_cert_full_path.exists():
                    base_params['ssl_ca_certs'] = str(ca_cert_full_path)
                    logger.info(f"🔒 Using SSL with CA cert: {ca_cert_full_path}")
            
            # Create appropriate client
            if is_cluster:
                logger.info(f"🔗 Detected Redis Cluster - keys may be distributed across nodes")
                redis_client = RedisCluster(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    **base_params
                )
            else:
                logger.info(f"📍 Using standalone Redis configuration")
                conn_params = {
                    'host': redis_config.get('host', 'localhost'),
                    'port': redis_config.get('port', 6379),
                    **base_params
                }
                # Add DB only for standalone Redis (clusters don't support db selection)
                if redis_config.get('db') is not None:
                    conn_params['db'] = redis_config.get('db', 0)
                
                redis_client = redis.Redis(**conn_params)
            
            # Test connection
            redis_client.ping()
            logger.info(f"✅ Redis connection successful")
            
            # Scan for keys matching the namespace pattern
            patterns = [
                f"{namespace}:*",
                f"{namespace}:{environment}:*",
                f"*:{namespace}:*"
            ]
            logger.info(f"🔎 Scanning Redis with patterns: {patterns}")
            
            all_keys = set()
            for pattern in patterns:
                logger.info(f"  Scanning pattern: {pattern}")
                pattern_keys = []
                
                # For cluster, we need to scan all nodes
                if is_cluster:
                    # RedisCluster.scan_iter() is the recommended way for clusters
                    # It automatically handles scanning across all nodes and returns an iterator
                    try:
                        logger.info(f"    Using scan_iter for cluster scanning...")
                        for key in redis_client.scan_iter(match=pattern, count=100):
                            # Decode key if it's bytes
                            decoded_key = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                            pattern_keys.append(decoded_key)
                            all_keys.add(decoded_key)
                        logger.info(f"    Found {len(pattern_keys)} keys for pattern: {pattern}")
                    except Exception as scan_error:
                        logger.error(f"❌ Cluster scan error for pattern {pattern}: {scan_error}")
                        logger.error(f"Error type: {type(scan_error)}")
                        # Try alternative approach: scan each node individually
                        try:
                            logger.info(f"    Trying per-node scan approach...")
                            nodes = redis_client.get_nodes()
                            for node in nodes:
                                cursor = 0
                                while True:
                                    cursor, keys = node.scan(cursor, match=pattern, count=100)
                                    for key in keys:
                                        decoded_key = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                                        pattern_keys.append(decoded_key)
                                        all_keys.add(decoded_key)
                                    if cursor == 0:
                                        break
                            logger.info(f"    Found {len(pattern_keys)} keys for pattern: {pattern} (per-node scan)")
                        except Exception as node_scan_error:
                            logger.error(f"❌ Per-node scan also failed: {node_scan_error}")
                else:
                    # Standard scan for standalone Redis
                    cursor = 0
                    while True:
                        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                        decoded_keys = [k.decode('utf-8') if isinstance(k, bytes) else str(k) for k in keys]
                        pattern_keys.extend(decoded_keys)
                        all_keys.update(decoded_keys)
                        if cursor == 0:
                            break
                    logger.info(f"    Found {len(pattern_keys)} keys for pattern: {pattern}")
            
            redis_client.close()
            logger.info(f"✅ Total unique keys found: {len(all_keys)}")
            
            # Return keys as file list
            files = [{"key": key, "name": key} for key in sorted(all_keys)]
            
            return {
                "files": files,
                "count": len(files),
                "environment": environment,
                "namespace": namespace
            }
            
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return {"files": [], "count": 0, "error": f"Cannot connect to Redis: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Redis error: {e}")
            return {"files": [], "count": 0, "error": f"Redis error: {str(e)}"}
            
    except Exception as e:
        logger.error(f"❌ Error getting Redis files: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"files": [], "count": 0, "error": str(e)}

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

@api_router.post("/grpc/environment")
async def set_grpc_environment(request: Dict[str, Any]):
    """Set the current gRPC environment"""
    try:
        environment = request.get("environment")
        if not environment:
            return {"success": False, "error": "Environment is required"}
        
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            return {"success": False, "error": "gRPC client not initialized"}
        
        # Set the environment
        app.state.grpc_client.set_environment(environment)
        logger.info(f"✅ gRPC environment set to: {environment}")
        
        return {
            "success": True,
            "environment": environment,
            "message": f"Environment set to {environment}"
        }
    except Exception as e:
        logger.error(f"Error setting gRPC environment: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/grpc/credentials")
async def set_grpc_credentials(request: Dict[str, Any]):
    """Set gRPC credentials (authorization and x-pop-token)"""
    try:
        authorization = request.get("authorization")
        x_pop_token = request.get("x_pop_token")
        
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            return {"success": False, "error": "gRPC client not initialized"}
        
        # Set the credentials
        app.state.grpc_client.set_credentials(authorization, x_pop_token)
        logger.info(f"✅ gRPC credentials set")
        
        return {
            "success": True,
            "message": "Credentials set successfully"
        }
    except Exception as e:
        logger.error(f"Error setting gRPC credentials: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/grpc/asset-storage/urls")
async def get_asset_storage_urls():
    """Get available asset-storage URLs for current environment"""
    try:
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            return {"success": False, "error": "gRPC client not initialized"}
        
        # grpc_client.get_asset_storage_urls() already returns a complete response
        # with success, urls dict, and current_selection
        return app.state.grpc_client.get_asset_storage_urls()
    except Exception as e:
        logger.error(f"Error getting asset storage URLs: {e}")
        return {"success": False, "error": str(e)}

@api_router.post("/grpc/asset-storage/set-url")
async def set_asset_storage_url(request: Dict[str, Any]):
    """Set which asset-storage URL to use (reader or writer)"""
    try:
        url_type = request.get("url_type", "reader")
        
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            return {"success": False, "error": "gRPC client not initialized"}
        
        # Set the URL type
        app.state.grpc_client.set_asset_storage_url(url_type)
        logger.info(f"✅ Asset storage URL type set to: {url_type}")
        
        return {
            "success": True,
            "url_type": url_type,
            "message": f"Using {url_type} URL"
        }
    except Exception as e:
        logger.error(f"Error setting asset storage URL: {e}")
        return {"success": False, "error": str(e)}

@api_router.get("/grpc/{service_name}/example/{method_name}")
async def get_grpc_method_example(service_name: str, method_name: str):
    """Get example request data for a gRPC method"""
    logger.info(f"📋 [gRPC EXAMPLE] Generating example for {service_name}.{method_name}")
    
    try:
        # Check if gRPC client is initialized
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            logger.error("❌ gRPC client not initialized")
            return {
                "success": False,
                "error": "gRPC client not initialized. Please initialize first."
            }
        
        # Get example request data
        example = await app.state.grpc_client.get_method_example(service_name, method_name)
        
        if example:
            logger.info(f"✅ Generated example for {service_name}.{method_name}")
            return {
                "success": True,
                "example": example
            }
        else:
            return {
                "success": False,
                "error": f"Could not generate example for {service_name}.{method_name}"
            }
        
    except Exception as e:
        logger.error(f"❌ Error generating example: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

@api_router.post("/grpc/upload-proxy")
async def upload_file_proxy(
    url: str = Form(...),
    file: UploadFile = File(...),
    authorization: Optional[str] = Form(None),
    x_pop_token: Optional[str] = Form(None)
):
    """Proxy file uploads to avoid CORS issues with S3 signed URLs"""
    logger.info(f"📤 [FILE UPLOAD PROXY] Uploading to: {url}")
    logger.info(f"📄 File: {file.filename} ({file.size} bytes)")
    logger.info(f"📄 Content-Type from file: {file.content_type}")
    
    try:
        import httpx
        from urllib.parse import urlparse, parse_qs
        
        # Read file content
        file_content = await file.read()
        
        # Parse the URL to check for signed headers
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Check if Content-Type was included in the signature
        signed_headers = query_params.get('X-Amz-SignedHeaders', [''])[0]
        logger.info(f"🔍 Signed headers: {signed_headers}")
        
        # Prepare headers
        headers = {}
        
        # For S3 signed URLs, Content-Type MUST match what was used during signing
        # If content-type is in signed headers, we need to send the exact same value
        if 'content-type' in signed_headers.lower():
            # Infer content type from file
            import mimetypes
            content_type = file.content_type
            
            # If browser didn't provide content type, guess from filename
            if not content_type or content_type == 'application/octet-stream':
                guessed_type, _ = mimetypes.guess_type(file.filename)
                content_type = guessed_type or 'application/octet-stream'
            
            headers['Content-Type'] = content_type
            logger.info(f"📝 Using Content-Type: {content_type} (from {'browser' if file.content_type else 'filename'})")
        else:
            # If content-type is NOT in signed headers, don't send it
            # This allows S3 to accept any content type
            logger.info(f"📝 Content-Type not in signed headers - not sending Content-Type header")
        
        # IMPORTANT: Do NOT send Authorization or X-POP-TOKEN headers to S3 signed URLs!
        # S3 signed URLs already contain authentication in query parameters (X-Amz-Signature, etc.)
        # Sending additional auth headers causes S3 to reject with:
        # "Only one auth mechanism allowed"
        # 
        # These auth headers are for gRPC service calls, not for S3 uploads
        # If you need to pass credentials through, they should be in the signed URL itself
        
        logger.info(f"📨 Request headers: {headers}")
        
        # Upload to the target URL using httpx (supports async)
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.put(url, content=file_content, headers=headers)
        
        # Check if upload was successful (2xx status codes)
        if 200 <= response.status_code < 300:
            logger.info(f"✅ Upload successful: {response.status_code}")
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "File uploaded successfully"
            }
        else:
            # Upload failed - return error details
            error_text = response.text[:500]  # First 500 chars of error response
            logger.error(f"❌ Upload failed with status {response.status_code}: {error_text}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": f"S3 returned {response.status_code}: {error_text}"
            }
        
    except Exception as e:
        logger.error(f"❌ Upload proxy error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e)
        }

@api_router.post("/grpc/{service_name}/{method_name}")
async def call_grpc_method(service_name: str, method_name: str, request_data: Dict[str, Any]):
    """Call a gRPC service method dynamically"""
    logger.info("="*80)
    logger.info(f"📞 [gRPC CALL] Endpoint HIT!")
    logger.info(f"📞 [gRPC CALL] Service: {service_name}")
    logger.info(f"📞 [gRPC CALL] Method: {method_name}")
    logger.info(f"📞 [gRPC CALL] Request data keys: {list(request_data.keys())}")
    logger.info("="*80)
    
    try:
        # Check if gRPC client is initialized
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            logger.error("❌ gRPC client not initialized")
            return {
                "success": False,
                "error": "gRPC client not initialized. Please initialize first."
            }
        
        # Call the dynamic method
        result = await app.state.grpc_client.call_dynamic_method(
            service_name=service_name,
            method_name=method_name,
            request_data=request_data
        )
        
        logger.info(f"✅ gRPC call completed - Success: {result.get('success', False)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error calling gRPC method: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
