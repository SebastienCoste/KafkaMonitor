from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import sys
import logging
import asyncio
import json
import yaml
import traceback
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

# Import our custom modules
from src.models import KafkaMessage, TraceInfo, TopicConfig
from src.protobuf_decoder import ProtobufDecoder, MockProtobufDecoder
from src.kafka_consumer import KafkaConsumerService
from src.graph_builder import TraceGraphBuilder
from src.grpc_client import GrpcClient
from src.environment_manager import EnvironmentManager
from src.blueprint_models import *
from src.blueprint_file_manager import BlueprintFileManager
from src.blueprint_build_manager import BlueprintBuildManager
from src.redis_service import RedisService
from src.blueprint_manager import BlueprintManager


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Note: FastAPI app creation moved to after lifespan definition

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Global variables for Kafka trace viewer components
graph_builder: Optional[TraceGraphBuilder] = None
kafka_consumer: Optional[KafkaConsumerService] = None
grpc_client: Optional[GrpcClient] = None
environment_manager: Optional[EnvironmentManager] = None
websocket_connections: List[WebSocket] = []

# Global variables for Blueprint Creator components
blueprint_file_manager: Optional[BlueprintFileManager] = None
blueprint_build_manager: Optional[BlueprintBuildManager] = None
blueprint_websocket_connections: List[WebSocket] = []

# Global variables for Redis Verify components
redis_service: Optional[RedisService] = None
blueprint_manager: Optional[BlueprintManager] = None

# Global settings
settings: Dict[str, Any] = {}

# Configuration paths
CONFIG_DIR = ROOT_DIR / "config"
PROTO_DIR = CONFIG_DIR / "proto"
ENVIRONMENTS_DIR = CONFIG_DIR / "environments"
GRPC_PROTOS_DIR = PROTO_DIR / "grpc"  # Updated to use subfolder under proto

async def initialize_blueprint_components():
    """Initialize Blueprint Creator components (independent of Kafka)"""
    logger.info("🏗️ Initializing Blueprint Creator components...")
    global blueprint_file_manager, blueprint_build_manager, redis_service, blueprint_manager, environment_manager
    
    try:
        blueprint_file_manager = BlueprintFileManager()
        blueprint_build_manager = BlueprintBuildManager()
        logger.info("✅ Blueprint Creator base components initialized")
        
        # Initialize minimal environment manager for blueprint operations
        if not environment_manager:
            from src.environment_manager import EnvironmentManager
            
            # Create minimal environment manager without protobuf decoder
            environment_manager = EnvironmentManager(
                environments_dir=str(CONFIG_DIR / "environments"),
                protobuf_decoder=None,  # No protobuf support in minimal mode
                settings={}
            )
            logger.info("✅ Minimal Environment Manager initialized for blueprints")
        
        # Initialize Redis and Blueprint Manager components
        logger.info("🔧 Initializing Redis and Blueprint Manager components...")
        redis_service = RedisService(environment_manager)
        blueprint_manager = BlueprintManager(blueprint_file_manager)
        logger.info("✅ Redis and Blueprint Manager components initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Blueprint components: {str(e)}")
        logger.error(f"🔴 Traceback: {traceback.format_exc()}")
        raise

async def initialize_kafka_components():
    """Initialize Kafka trace viewer components"""
    logger.info("🚀 Starting Kafka trace viewer component initialization")
    global graph_builder, kafka_consumer, grpc_client, environment_manager
    global blueprint_file_manager, blueprint_build_manager
    global redis_service, blueprint_manager, settings
    
    # First initialize Blueprint components (these should always work)
    await initialize_blueprint_components()
    
    # Check if required directories exist
    if not CONFIG_DIR.exists():
        logger.error(f"❌ Configuration directory not found: {CONFIG_DIR}")
        logger.info("💡 Make sure you're running from the correct directory with config/ folder")
        raise FileNotFoundError(f"Configuration directory not found: {CONFIG_DIR}")
    
    if not PROTO_DIR.exists():
        logger.error(f"❌ Proto directory not found: {PROTO_DIR}")
        logger.info("💡 Creating proto directory structure...")
        PROTO_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info("📄 Loading configuration files...")
        
        # Load settings
        settings_path = CONFIG_DIR / "settings.yaml"
        logger.info(f"📋 Loading settings from: {settings_path}")
        with open(settings_path, 'r') as f:
            settings = yaml.safe_load(f)
        logger.debug(f"⚙️  Settings loaded: {settings}")
        
        # Load topics configuration
        topics_path = CONFIG_DIR / "topics.yaml"
        logger.info(f"📋 Loading topics from: {topics_path}")
        with open(topics_path, 'r') as f:
            topics_config = yaml.safe_load(f)
        logger.debug(f"🎯 Topics config loaded: {topics_config}")
        
        # Initialize protobuf decoder
        kafka_config_path = CONFIG_DIR / "kafka.yaml"
        logger.info(f"📋 Loading Kafka config from: {kafka_config_path}")
        with open(kafka_config_path, 'r') as f:
            kafka_config = yaml.safe_load(f)
        
        logger.info(f"🎭 Mock mode: {kafka_config.get('mock_mode', True)}")
        
        if kafka_config.get('mock_mode', True):
            decoder = MockProtobufDecoder()
            logger.info("🎭 Using mock protobuf decoder")
        else:
            logger.info(f"🔧 Using real protobuf decoder with proto dir: {PROTO_DIR}")
            decoder = ProtobufDecoder(str(PROTO_DIR))
            logger.info("✅ Real protobuf decoder initialized")
        
        # Load protobuf definitions for each topic
        logger.info("🔄 Loading protobuf definitions for topics...")
        for topic_name, topic_config in topics_config.get('topics', {}).items():
            logger.info(f"📄 Loading protobuf for topic: {topic_name}")
            logger.debug(f"  📄 Proto file: {topic_config['proto_file']}")
            logger.debug(f"  🎯 Message type: {topic_config['message_type']}")
            
            try:
                decoder.load_topic_protobuf(
                    topic_name,
                    topic_config['proto_file'],
                    topic_config['message_type']
                )
                logger.info(f"✅ Successfully loaded protobuf for topic: {topic_name}")
            except Exception as e:
                logger.error(f"💥 Failed to load protobuf for topic {topic_name}: {str(e)}")
                logger.error(f"🔴 Error type: {type(e).__name__}")
                logger.error(f"🔴 Traceback: {traceback.format_exc()}")
                raise
        
        # Update Environment Manager with full Kafka setup
        logger.info("🌍 Updating Environment Manager with Kafka support...")
        environment_manager = EnvironmentManager(
            environments_dir=str(CONFIG_DIR / "environments"),
            protobuf_decoder=decoder,
            settings=settings
        )
        logger.info("✅ Full Environment Manager initialized with Kafka support")
        
        # Update Redis service with full environment manager
        logger.info("🔧 Updating Redis service with full environment manager...")
        redis_service = RedisService(environment_manager)
        logger.info("✅ Redis service updated with full environment support")
        
        # Default to DEV environment (or first available)
        available_envs = environment_manager.list_environments()
        config_default_env = settings.get('application', {}).get('start_env', 'DEV')
        default_env = config_default_env if config_default_env in available_envs else (available_envs[0] if available_envs else None)
        
        if default_env:
            logger.info(f"🔄 Switching to default environment: {default_env}")
            result = environment_manager.switch_environment(default_env)
            
            if result['success']:
                # Get references to the services created by environment manager
                graph_builder = environment_manager.graph_builder
                kafka_consumer = environment_manager.kafka_consumer
                
                # Start Kafka consumer
                environment_manager.start_kafka_consumer()
                logger.info(f"✅ Default environment {default_env} initialized and started")
            else:
                logger.error(f"❌ Failed to initialize default environment: {result.get('error')}")
        else:
            logger.warning("⚠️  No environments found - services will be initialized on first environment switch")
        
        # Initialize gRPC client with entire proto directory
        logger.info("🔧 Initializing gRPC client...")
        grpc_client = GrpcClient(str(PROTO_DIR), str(ENVIRONMENTS_DIR))
        
        # Try to auto-initialize proto files if they exist
        try:
            logger.info("🔄 Attempting auto-initialization of gRPC proto files...")
            init_result = await grpc_client.initialize()
            if init_result.get('success'):
                logger.info("✅ gRPC client proto files auto-initialized successfully")
            else:
                logger.warning(f"⚠️  gRPC proto auto-initialization failed: {init_result.get('error', 'Unknown error')}")
                logger.info("💡 gRPC client created but will need manual initialization via /api/grpc/initialize")
        except Exception as e:
            logger.warning(f"⚠️  gRPC auto-initialization error: {str(e)}")
            logger.info("💡 gRPC client created but will need manual initialization via /api/grpc/initialize")
        
        logger.info("✅ gRPC client setup completed")
        
        logger.info("🎉 Kafka trace viewer components initialized successfully!")
        
    except Exception as e:
        logger.error(f"💥 Failed to initialize Kafka components: {str(e)}")
        logger.error(f"🔴 Error type: {type(e).__name__}")
        logger.error(f"🔴 Traceback: {traceback.format_exc()}")
        raise


# API Routes for Kafka Trace Viewer
@api_router.get("/")
async def root():
    return {"message": "Kafka Trace Viewer API", "status": "running"}

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "traces_count": len(graph_builder.traces) if graph_builder else 0
    }

@api_router.get("/settings")
async def get_settings():
    """Get application settings"""
    return {
        "trace_header_field": settings.get("trace_header_field", "trace_id"),
        "max_traces": settings.get("max_traces", 1000),
        "cleanup_interval": settings.get("cleanup_interval", 300)
    }

@api_router.get("/app-config")
async def get_app_config():
    """Get application configuration including tab settings"""
    return {
        "tabs": settings.get("tabs", {
            "trace_viewer": {"enabled": True, "title": "Trace Viewer"},
            "grpc_integration": {"enabled": True, "title": "gRPC Integration"},
            "blueprint_creator": {"enabled": True, "title": "Blueprint Creator"}
        }),
        "landing_page": settings.get("landing_page", {
            "enabled": True,
            "title": "Marauder's Map",
            "subtitle": "Comprehensive monitoring and management platform"
        })
    }

# Environment Management Endpoints

@api_router.get("/environments")
async def list_environments():
    """Get list of available environments"""
    if not environment_manager:
        raise HTTPException(status_code=503, detail="Environment manager not initialized")
    
    try:
        result = environment_manager.get_current_environment()
        return result
    except Exception as e:
        logger.error(f"Error listing environments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/environments/switch")
async def switch_environment(request: Dict[str, str]):
    """Switch to a different environment"""
    if not environment_manager:
        raise HTTPException(status_code=503, detail="Environment manager not initialized")
    
    environment = request.get('environment')
    if not environment:
        raise HTTPException(status_code=400, detail="Environment name is required")
    
    try:
        global graph_builder, kafka_consumer
        
        result = environment_manager.switch_environment(environment)
        
        if result['success']:
            # Update global references
            graph_builder = environment_manager.graph_builder
            kafka_consumer = environment_manager.kafka_consumer
            
            # Start Kafka consumer for new environment
            environment_manager.start_kafka_consumer()
            
            # Notify WebSocket clients about environment change
            await broadcast_environment_change(environment)
            
        return result
    except Exception as e:
        logger.error(f"Error switching environment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/environments/{environment}/config")
async def get_environment_config(environment: str):
    """Get configuration for a specific environment"""
    if not environment_manager:
        raise HTTPException(status_code=503, detail="Environment manager not initialized")
    
    try:
        result = environment_manager.get_environment_config(environment)
        return result
    except Exception as e:
        logger.error(f"Error getting environment config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def broadcast_environment_change(environment: str):
    """Broadcast environment change to all WebSocket clients"""
    if websocket_connections:
        message = {
            'type': 'environment_change',
            'environment': environment,
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to all connected clients
        disconnected = []
        for websocket in websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send environment change to WebSocket client: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            websocket_connections.remove(ws)

@api_router.get("/traces")
async def get_traces():
    """Get all available trace IDs with summary"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        summary = graph_builder.get_trace_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting traces: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trace/{trace_id}")
async def get_trace(trace_id: str):
    """Get detailed trace information"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        trace = graph_builder.get_trace(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        return trace.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace {trace_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trace/{trace_id}/flow")
async def get_trace_flow(trace_id: str):
    """Get trace flow visualization data"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        flow_data = graph_builder.get_trace_flow_data(trace_id)
        if not flow_data:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

        return flow_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trace flow {trace_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@api_router.get("/kafka/subscription-status")
async def get_kafka_subscription_status():
    """Get Kafka subscription status and topic availability"""
    if not kafka_consumer:
        raise HTTPException(status_code=503, detail="Kafka consumer not initialized")
    
    try:
        status = kafka_consumer.get_subscription_status()
        return {
            'success': True,
            **status
        }
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/kafka/refresh-subscription")
async def refresh_kafka_subscription():
    """Manually refresh Kafka topic subscription to pick up new topics"""
    if not kafka_consumer:
        raise HTTPException(status_code=503, detail="Kafka consumer not initialized")
    
    try:
        kafka_consumer.refresh_topic_subscription()
        status = kafka_consumer.get_subscription_status()
        return {
            'success': True,
            'message': 'Topic subscription refreshed',
            **status
        }
    except Exception as e:
        logger.error(f"Error refreshing subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/topics/graph")
async def get_topics_graph():
    """Get topic graph configuration"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        return graph_builder.get_topic_graph_data()
    except Exception as e:
        logger.error(f"Error getting topics graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/graph/disconnected")
async def get_disconnected_graphs():
    """Get all disconnected graph components with enhanced statistics"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        disconnected_graphs = graph_builder.get_disconnected_graphs()
        return {
            'success': True,
            'components': disconnected_graphs,
            'total_components': len(disconnected_graphs)
        }
    except Exception as e:
        logger.error(f"Error getting disconnected graphs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/graph/filtered")
async def get_filtered_graph(time_filter: str = "all", custom_minutes: Optional[int] = None):
    """Get filtered graph data based on time range"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        filtered_data = graph_builder.get_filtered_graph_data(time_filter, custom_minutes)
        return {
            'success': True,
            **filtered_data
        }
    except Exception as e:
        logger.error(f"Error getting filtered graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/graph/apply-mock")
async def apply_mock_graph():
    """Apply mock graph configuration for testing disconnected graphs"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        from src.mock_graph_generator import MockGraphGenerator
        
        mock_generator = MockGraphGenerator()
        mock_generator.apply_mock_configuration(graph_builder)
        
        return {
            'success': True,
            'message': 'Mock graph configuration applied successfully',
            'total_traces': len(graph_builder.traces),
            'total_topics': len(graph_builder.topic_graph.get_all_topics())
        }
    except Exception as e:
        logger.error(f"Error applying mock graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/topics")
async def get_topics():
    """Get all available topics"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        all_topics = graph_builder.topic_graph.get_all_topics()
        monitored_topics = graph_builder.get_monitored_topics()
        
        return {
            "all_topics": all_topics,
            "monitored_topics": monitored_topics,
            "available_for_monitoring": [t for t in all_topics if t not in monitored_topics]
        }
    except Exception as e:
        logger.error(f"Error getting topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/topics/monitor")
async def set_monitored_topics(topics: List[str]):
    """Set which topics to monitor"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        graph_builder.set_monitored_topics(topics)
        return {
            "success": True,
            "monitored_topics": graph_builder.get_monitored_topics()
        }
    except Exception as e:
        logger.error(f"Error setting monitored topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/statistics")
async def get_statistics():
    """Get detailed statistics about traces and topics"""
    if not graph_builder:
        raise HTTPException(status_code=503, detail="Graph builder not initialized")
    
    try:
        return graph_builder.get_statistics()
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Blueprint Creator Endpoints

@api_router.get("/blueprint/config")
async def get_blueprint_config():
    """Get current blueprint configuration"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    return {
        "root_path": blueprint_file_manager.root_path,
        "auto_refresh": True,
        "available_templates": blueprint_file_manager.get_available_templates()
    }

@api_router.put("/blueprint/config")
async def set_blueprint_config(request: Dict[str, str]):
    """Set blueprint root path"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    root_path = request.get('root_path')
    if not root_path:
        raise HTTPException(status_code=400, detail="Root path is required")
    
    try:
        blueprint_file_manager.set_root_path(root_path)
        return {"success": True, "root_path": blueprint_file_manager.root_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@api_router.get("/blueprint/file-tree")
async def get_blueprint_file_tree(path: str = ""):
    """Get blueprint file tree structure"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    try:
        file_tree = await blueprint_file_manager.get_file_tree(path)
        return {"files": file_tree}
    except Exception as e:
        logger.error(f"Error getting file tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/file-content/{path:path}")
async def get_blueprint_file_content(path: str):
    """Get content of a blueprint file"""
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

@api_router.put("/blueprint/file-content/{path:path}")
async def save_blueprint_file_content(path: str, request: Dict[str, str]):
    """Save content to a blueprint file"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    content = request.get('content', '')
    
    try:
        await blueprint_file_manager.write_file(path, content)
        
        # Notify WebSocket clients about file change
        await broadcast_blueprint_change("file_updated", {"path": path})
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error saving file {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/create-file")
async def create_blueprint_file(request: FileOperationRequest):
    """Create a new blueprint file"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    try:
        template_name = request.new_path  # Using new_path as template name for simplicity
        await blueprint_file_manager.create_file(request.path, template_name)
        
        # Notify WebSocket clients about file creation
        await broadcast_blueprint_change("file_created", {"path": request.path})
        
        return {"success": True}
    except FileExistsError:
        raise HTTPException(status_code=409, detail="File already exists")
    except Exception as e:
        logger.error(f"Error creating file {request.path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/blueprint/delete-file/{path:path}")
async def delete_blueprint_file(path: str):
    """Delete a blueprint file or directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    try:
        await blueprint_file_manager.delete_file(path)
        
        # Notify WebSocket clients about file deletion
        await broadcast_blueprint_change("file_deleted", {"path": path})
        
        return {"success": True}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.error(f"Error deleting file {path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/move-file")
async def move_blueprint_file(request: Dict[str, str]):
    """Move or rename a blueprint file/directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    source_path = request.get('source_path')
    destination_path = request.get('destination_path')
    
    if not source_path or not destination_path:
        raise HTTPException(status_code=400, detail="Source and destination paths are required")
    
    try:
        await blueprint_file_manager.move_file(source_path, destination_path)
        
        # Notify WebSocket clients about file move
        await broadcast_blueprint_change("file_moved", {
            "source_path": source_path,
            "destination_path": destination_path
        })
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error moving file {source_path} to {destination_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/rename-file")
async def rename_blueprint_file(request: Dict[str, str]):
    """Rename a blueprint file/directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    source_path = request.get('source_path')
    new_name = request.get('new_name')
    
    if not source_path or not new_name:
        raise HTTPException(status_code=400, detail="Source path and new name are required")
    
    try:
        # Calculate destination path
        source_dir = os.path.dirname(source_path)
        destination_path = os.path.join(source_dir, new_name) if source_dir else new_name
        
        await blueprint_file_manager.move_file(source_path, destination_path)
        
        # Notify WebSocket clients about file rename
        await broadcast_blueprint_change("file_renamed", {
            "source_path": source_path,
            "destination_path": destination_path,
            "new_name": new_name
        })
        
        return {"success": True, "new_path": destination_path}
    except Exception as e:
        logger.error(f"Error renaming file {source_path} to {new_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/create-directory")
async def create_blueprint_directory(request: FileOperationRequest):
    """Create a new directory"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    try:
        await blueprint_file_manager.create_directory(request.path)
        
        # Notify WebSocket clients about directory creation
        await broadcast_blueprint_change("directory_created", {"path": request.path})
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error creating directory {request.path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/build")
async def build_blueprint(request: BuildRequest):
    """Execute blueprint build"""
    if not blueprint_build_manager:
        raise HTTPException(status_code=503, detail="Blueprint build manager not initialized")
    
    try:
        # Execute build with WebSocket broadcasting
        result = await blueprint_build_manager.execute_build(
            request.root_path, 
            request.script_name,
            websocket=None,  # We'll broadcast to all connected clients
            broadcast_callback=broadcast_blueprint_change
        )
        
        return result.dict()
    except Exception as e:
        logger.error(f"Error building blueprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/build-status")
async def get_blueprint_build_status():
    """Get current build status"""
    if not blueprint_build_manager:
        raise HTTPException(status_code=503, detail="Blueprint build manager not initialized")
    
    return blueprint_build_manager.get_build_status()

@api_router.post("/blueprint/cancel-build")
async def cancel_blueprint_build():
    """Cancel current build"""
    if not blueprint_build_manager:
        raise HTTPException(status_code=503, detail="Blueprint build manager not initialized")
    
    try:
        cancelled = await blueprint_build_manager.cancel_build()
        return {"success": cancelled}
    except Exception as e:
        logger.error(f"Error canceling build: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/output-files")
async def get_blueprint_output_files(root_path: str):
    """Get list of generated output files"""
    if not blueprint_build_manager:
        raise HTTPException(status_code=503, detail="Blueprint build manager not initialized")
    
    try:
        files = await blueprint_build_manager.list_output_files(root_path)
        return {"files": files}
    except Exception as e:
        logger.error(f"Error listing output files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/validate/{filepath:path}")
async def validate_blueprint(filepath: str, request: DeploymentRequest):
    """Validate blueprint with blueprint server"""
    # Extract just the filename from the filepath (remove 'out/' prefix if present)
    filename = filepath.split('/')[-1] if '/' in filepath else filepath
    logger.info(f"🔍 Blueprint validation requested for filepath: {filepath}, filename: {filename}")
    logger.info(f"🔍 Request data: environment={request.environment}, action={request.action}")
    
    if not blueprint_build_manager or not environment_manager or not blueprint_file_manager:
        logger.error("❌ Required managers not initialized")
        raise HTTPException(status_code=503, detail="Required managers not initialized")
    
    try:
        logger.info("🔍 Extracting namespace from blueprint_cnf.json...")
        # Get namespace from blueprint_cnf.json
        namespace = None
        try:
            config_validation = await blueprint_file_manager.validate_blueprint_config("blueprint_cnf.json")
            if config_validation.get('valid') and config_validation.get('config'):
                namespace = config_validation['config'].get('namespace')
                logger.info(f"✅ Extracted namespace: {namespace}")
            else:
                logger.warning(f"⚠️ Blueprint config validation failed: {config_validation}")
        except Exception as e:
            logger.warning(f"⚠️ Could not extract namespace from blueprint_cnf.json: {e}")
        
        logger.info(f"🔍 Getting environment configuration for: {request.environment}")
        # Get environment configuration
        env_config_data = environment_manager.get_environment_config(request.environment)
        if not env_config_data.get('success'):
            logger.error(f"❌ Environment {request.environment} not found")
            raise HTTPException(status_code=400, detail=f"Environment {request.environment} not found")
        
        blueprint_config = env_config_data['config'].get('blueprint_server')
        if not blueprint_config:
            logger.error(f"❌ Blueprint server not configured for environment {request.environment}")
            raise HTTPException(status_code=400, detail=f"Blueprint server not configured for environment {request.environment}")
        
        logger.info(f"🔍 Blueprint server config: {blueprint_config}")
        env_config = EnvironmentConfig(**blueprint_config)
        
        logger.info(f"🔍 Starting blueprint validation - file: {filepath}, env: {request.environment}, namespace: {namespace}")
        # Deploy with validate action - use full filepath to locate file in out/ directory
        result = await blueprint_build_manager.deploy_blueprint(
            request.root_path if hasattr(request, 'root_path') else blueprint_file_manager.root_path,
            filepath,
            request.environment,
            DeploymentAction.VALIDATE,
            env_config,
            namespace
        )
        
        logger.info(f"✅ Blueprint validation completed - success: {result.success}")
        return result.dict()
    except Exception as e:
        logger.error(f"❌ Error validating blueprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/blueprint/activate/{filepath:path}")
async def activate_blueprint(filepath: str, request: DeploymentRequest):
    """Activate blueprint with blueprint server"""
    # Extract just the filename from the filepath (remove 'out/' prefix if present)
    filename = filepath.split('/')[-1] if '/' in filepath else filepath
    logger.info(f"🔍 Blueprint activation requested for filepath: {filepath}, filename: {filename}")
    
    if not blueprint_build_manager or not environment_manager or not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Required managers not initialized")
    
    try:
        # Get namespace from blueprint_cnf.json
        namespace = None
        try:
            config_validation = await blueprint_file_manager.validate_blueprint_config("blueprint_cnf.json")
            if config_validation.get('valid') and config_validation.get('config'):
                namespace = config_validation['config'].get('namespace')
        except Exception as e:
            logger.warning(f"Could not extract namespace from blueprint_cnf.json: {e}")
        
        # Get environment configuration
        env_config_data = environment_manager.get_environment_config(request.environment)
        if not env_config_data.get('success'):
            raise HTTPException(status_code=400, detail=f"Environment {request.environment} not found")
        
        blueprint_config = env_config_data['config'].get('blueprint_server')
        if not blueprint_config:
            raise HTTPException(status_code=400, detail=f"Blueprint server not configured for environment {request.environment}")
        
        env_config = EnvironmentConfig(**blueprint_config)
        
        # Deploy with activate action - use full filepath to locate file in out/ directory
        result = await blueprint_build_manager.deploy_blueprint(
            request.root_path if hasattr(request, 'root_path') else blueprint_file_manager.root_path,
            filepath,
            request.environment,
            DeploymentAction.ACTIVATE,
            env_config,
            namespace
        )
        
        return result.dict()
    except Exception as e:
        logger.error(f"Error activating blueprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/validate-config")
async def validate_blueprint_config(path: str = "blueprint_cnf.json"):
    """Validate blueprint configuration file"""
    if not blueprint_file_manager:
        raise HTTPException(status_code=503, detail="Blueprint file manager not initialized")
    
    try:
        validation_result = await blueprint_file_manager.validate_blueprint_config(path)
        return validation_result
    except Exception as e:
        logger.error(f"Error validating blueprint config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Script endpoints removed as per FIX 1 requirement

# Redis Verify Endpoints

@api_router.get("/redis/files")
async def get_redis_files(environment: str, namespace: Optional[str] = None):
    """Get Redis files for environment and namespace"""
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not initialized")
    
    try:
        # Use provided namespace or detect from blueprint
        if not namespace:
            if not blueprint_manager:
                raise HTTPException(status_code=503, detail="Blueprint manager not initialized")
            
            namespace = await blueprint_manager.get_current_namespace()
            if not namespace:
                raise HTTPException(
                    status_code=400, 
                    detail="No namespace provided and unable to detect from blueprint configuration"
                )
        
        logger.info(f"🔍 Getting Redis files for environment: {environment}, namespace: {namespace}")
        files = await redis_service.get_files_by_namespace(environment, namespace)
        
        return {
            "status": "success",
            "environment": environment,
            "namespace": namespace,
            "files": [
                {
                    "key": file.key,
                    "size_bytes": file.size_bytes,
                    "last_modified": file.last_modified
                }
                for file in files
            ],
            "total_count": len(files)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get Redis files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/redis/file-content")
async def get_redis_file_content(key: str, environment: str):
    """Get content of specific Redis file"""
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not initialized")
    
    try:
        logger.info(f"🔍 Getting Redis file content for key: {key}, environment: {environment}")
        content = await redis_service.get_file_content(environment, key)
        
        return {
            "status": "success",
            "key": key,
            "environment": environment,
            "content": content,
            "content_type": "application/json"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get Redis file content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/redis/test-connection")
async def test_redis_connection(request: Dict[str, str]):
    """Test Redis connection for environment"""
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not initialized")
    
    environment = request.get('environment')
    if not environment:
        raise HTTPException(status_code=400, detail="Environment is required")
    
    try:
        logger.info(f"🔍 Testing Redis connection for environment: {environment}")
        result = await redis_service.test_connection(environment)
        return result
        
    except Exception as e:
        logger.error(f"❌ Redis connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/redis/environments")
async def get_redis_environments():
    """Get list of environments with Redis configuration"""
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not initialized")
    
    try:
        environments = redis_service.get_available_environments()
        return {
            "status": "success",
            "environments": environments
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get Redis environments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/blueprint/namespace")
async def get_blueprint_namespace():
    """Get current blueprint namespace"""
    if not blueprint_manager:
        raise HTTPException(status_code=503, detail="Blueprint manager not initialized")
    
    try:
        logger.info("🔍 Getting current blueprint namespace")
        namespace = await blueprint_manager.get_current_namespace()
        
        if not namespace:
            raise HTTPException(
                status_code=404,
                detail="Blueprint namespace not found in configuration"
            )
        
        return {
            "namespace": namespace,
            "source": "blueprint_cnf.json"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get blueprint namespace: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def broadcast_blueprint_change(event_type: str, data: Dict[str, Any]):
    """Broadcast blueprint changes to all WebSocket clients"""
    if blueprint_websocket_connections:
        message = WebSocketMessage(type=event_type, data=data)
        
        # Send to all connected clients
        disconnected = []
        for websocket in blueprint_websocket_connections:
            try:
                await websocket.send_text(message.json())
            except Exception as e:
                logger.warning(f"Failed to send blueprint change to WebSocket client: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for ws in disconnected:
            blueprint_websocket_connections.remove(ws)

@api_router.websocket("/ws/blueprint")
async def blueprint_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for Blueprint Creator real-time updates"""
    await websocket.accept()
    blueprint_websocket_connections.append(websocket)

    try:
        while True:
            # Keep connection alive with less frequent updates
            await asyncio.sleep(30)  # Only send updates every 30 seconds

            # Send periodic file tree refresh only if auto-refresh is enabled
            # Note: We can't directly check frontend autoRefresh state here
            # The frontend should manage its own refresh frequency
            try:
                # Send a simple ping to keep connection alive
                ping_data = {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(ping_data))
            except Exception as e:
                logger.debug(f"Error sending ping: {e}")
                break

    except WebSocketDisconnect:
        blueprint_websocket_connections.remove(websocket)
        logger.debug("Blueprint WebSocket connection closed")
    except Exception as e:
        logger.error(f"Blueprint WebSocket error: {e}")
        if websocket in blueprint_websocket_connections:
            blueprint_websocket_connections.remove(websocket)

# gRPC Integration Endpoints

@api_router.get("/grpc/status")
async def get_grpc_status():
    """Get gRPC client status"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        return grpc_client.get_status()
    except Exception as e:
        logger.error(f"Error getting gRPC status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/initialize")
async def initialize_grpc():
    """Initialize gRPC client and load proto files"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        result = await grpc_client.initialize()
        return result
    except Exception as e:
        logger.error(f"Error initializing gRPC client: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grpc/environments")
async def get_grpc_environments():
    """Get list of available environments"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        environments = grpc_client.list_environments()
        return {"environments": environments}
    except Exception as e:
        logger.error(f"Error getting environments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/environment")
async def set_grpc_environment(request: Dict[str, str]):
    """Set the current gRPC environment"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    environment = request.get('environment')
    if not environment:
        raise HTTPException(status_code=400, detail="Environment is required")
    
    try:
        result = grpc_client.set_environment(environment)
        return result
    except Exception as e:
        logger.error(f"Error setting environment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/credentials")
async def set_grpc_credentials(request: Dict[str, str]):
    """Set gRPC credentials (stored in memory only)"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    authorization = request.get('authorization', '')
    x_pop_token = request.get('x_pop_token', '')
    
    try:
        result = grpc_client.set_credentials(authorization, x_pop_token)
        return result
    except Exception as e:
        logger.error(f"Error setting credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grpc/asset-storage/urls")
async def get_asset_storage_urls():
    """Get available asset-storage URLs for current environment"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        result = grpc_client.get_asset_storage_urls()
        return result
    except Exception as e:
        logger.error(f"Error getting asset-storage URLs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/asset-storage/set-url")
async def set_asset_storage_url(request: Dict[str, str]):
    """Set which asset-storage URL to use (reader or writer)"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    url_type = request.get('url_type', 'reader')
    
    try:
        result = grpc_client.set_asset_storage_url(url_type)
        return result
    except Exception as e:
        logger.error(f"Error setting asset-storage URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# IngressServer Endpoints

@api_router.post("/grpc/debug/create_message/{service_name}/{method_name}")
async def debug_create_message(service_name: str, method_name: str, request_data: dict):
    """DEBUG: Test message creation without making gRPC call"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    result = grpc_client.debug_message_creation(service_name, method_name, request_data)
    return result

@api_router.post("/grpc/{service_name}/{method_name}")
async def dynamic_grpc_call(service_name: str, method_name: str, request: Dict[str, Any]):
    """Dynamic gRPC method call for any service and method"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        logger.info(f"🔧 Making dynamic gRPC call: {service_name}.{method_name}")
        logger.debug(f"📝 Request data: {request}")
        
        result = await grpc_client.call_dynamic_method(service_name, method_name, request)
        return result
    except Exception as e:
        logger.error(f"❌ Error in dynamic gRPC call {service_name}.{method_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grpc/debug/message/{service_name}/{message_name}")
async def debug_message_search(service_name: str, message_name: str):
    """Debug message class search process"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        result = {"steps": [], "found": False, "message_class": None}
        
        if service_name not in grpc_client.proto_loader.compiled_modules:
            result["steps"].append(f"❌ Service {service_name} not found")
            return result
        
        pb2_module = grpc_client.proto_loader.compiled_modules[service_name].get('pb2')
        if not pb2_module:
            result["steps"].append(f"❌ pb2 module not found for {service_name}")
            return result
        
        result["steps"].append(f"✅ Found pb2 module for {service_name}")
        
        # Try direct access
        if hasattr(pb2_module, message_name):
            result["steps"].append(f"✅ Found {message_name} directly in pb2 module")
            result["found"] = True
            return result
        
        result["steps"].append(f"❌ {message_name} not found directly in pb2 module")
        
        # Search imported modules
        pb2_modules = [attr for attr in dir(pb2_module) if not attr.startswith('_') and 'pb2' in attr]
        result["steps"].append(f"📋 Found {len(pb2_modules)} pb2 modules: {pb2_modules}")
        
        for attr_name in pb2_modules:
            try:
                imported_module = getattr(pb2_module, attr_name)
                module_attrs = [attr for attr in dir(imported_module) if not attr.startswith('_')]
                result["steps"].append(f"🔍 Module {attr_name} has {len(module_attrs)} attributes")
                
                if hasattr(imported_module, message_name):
                    result["steps"].append(f"✅ Found {message_name} in module {attr_name}")
                    result["found"] = True
                    result["module"] = attr_name
                    return result
                else:
                    result["steps"].append(f"❌ {message_name} not in {attr_name}")
                    
            except Exception as e:
                result["steps"].append(f"❌ Error accessing {attr_name}: {str(e)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in debug message search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grpc/debug/module/{service_name}/{module_name}")
async def debug_module_contents(service_name: str, module_name: str):
    """Debug a specific module to see what message classes it contains"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        if service_name not in grpc_client.proto_loader.compiled_modules:
            raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
        
        pb2_module = grpc_client.proto_loader.compiled_modules[service_name].get('pb2')
        if not pb2_module:
            raise HTTPException(status_code=404, detail=f"pb2 module not found for {service_name}")
        
        if not hasattr(pb2_module, module_name):
            raise HTTPException(status_code=404, detail=f"Module {module_name} not found")
        
        target_module = getattr(pb2_module, module_name)
        
        # Get all message classes from the module
        message_classes = []
        for attr_name in dir(target_module):
            if not attr_name.startswith('_'):
                attr_value = getattr(target_module, attr_name)
                if hasattr(attr_value, 'DESCRIPTOR'):
                    message_classes.append(attr_name)
        
        return {
            "module": module_name,
            "message_classes": message_classes
        }
        
    except Exception as e:
        logger.error(f"❌ Error in debug module: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grpc/debug/messages")
async def debug_available_messages():
    """Debug endpoint to see what message classes are available"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        debug_info = {}
        
        for service_name, modules in grpc_client.proto_loader.compiled_modules.items():
            debug_info[service_name] = {}
            
            for module_type, module in modules.items():
                debug_info[service_name][module_type] = []
                
                # Get all attributes that look like message classes
                for attr_name in dir(module):
                    if not attr_name.startswith('_'):
                        attr_value = getattr(module, attr_name)
                        # Check if this looks like a protobuf message class
                        if hasattr(attr_value, 'DESCRIPTOR'):
                            debug_info[service_name][module_type].append(attr_name)
        
        return {"available_messages": debug_info}
        
    except Exception as e:
        logger.error(f"❌ Error in debug messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/grpc/{service_name}/example/{method_name}")
async def get_method_example(service_name: str, method_name: str):
    """Get example request data for a specific gRPC method"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        example = await grpc_client.get_method_example(service_name, method_name)
        return {"example": example}
    except Exception as e:
        logger.error(f"❌ Error getting example for {service_name}.{method_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/ingress/upsert-content")
async def upsert_content(request: Dict[str, Any]):
    """Call IngressServer.UpsertContent"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        content_data = request.get('content_data', {})
        random_field = request.get('random_field')
        
        result = await grpc_client.upsert_content(content_data, random_field)
        return result
    except Exception as e:
        logger.error(f"Error in upsert_content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/ingress/batch-create-assets")
async def batch_create_assets(request: Dict[str, Any]):
    """Call IngressServer.BatchCreateAssets"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        assets_data = request.get('assets_data', [])
        
        result = await grpc_client.batch_create_assets(assets_data)
        return result
    except Exception as e:
        logger.error(f"Error in batch_create_assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/ingress/batch-add-download-counts")
async def batch_add_download_counts(request: Dict[str, Any]):
    """Call IngressServer.BatchAddDownloadCounts"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        player_id = request.get('player_id', '')
        content_ids = request.get('content_ids', [])
        
        result = await grpc_client.batch_add_download_counts(player_id, content_ids)
        return result
    except Exception as e:
        logger.error(f"Error in batch_add_download_counts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/ingress/batch-add-ratings")
async def batch_add_ratings(request: Dict[str, Any]):
    """Call IngressServer.BatchAddRatings"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        rating_data = request.get('rating_data', {})
        
        result = await grpc_client.batch_add_ratings(rating_data)
        return result
    except Exception as e:
        logger.error(f"Error in batch_add_ratings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AssetStorageService Endpoints

@api_router.post("/grpc/asset-storage/batch-get-signed-urls")
async def batch_get_signed_urls(request: Dict[str, Any]):
    """Call AssetStorageService.BatchGetSignedUrls"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        asset_ids = request.get('asset_ids', [])
        
        result = await grpc_client.batch_get_signed_urls(asset_ids)
        return result
    except Exception as e:
        logger.error(f"Error in batch_get_signed_urls: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/grpc/asset-storage/batch-update-statuses")
async def batch_update_statuses(request: Dict[str, Any]):
    """Call AssetStorageService.BatchUpdateStatuses"""
    if not grpc_client:
        raise HTTPException(status_code=503, detail="gRPC client not initialized")
    
    try:
        asset_updates = request.get('asset_updates', [])
        
        result = await grpc_client.batch_update_statuses(asset_updates)
        return result
    except Exception as e:
        logger.error(f"Error in batch_update_statuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Static file serving through API routes to bypass infrastructure SPA routing
@api_router.get("/static/js/{filename}")
async def serve_js(filename: str):
    """Serve JavaScript files"""
    file_path = f"../frontend/build/static/js/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="JavaScript file not found")

@api_router.get("/static/css/{filename}")
async def serve_css(filename: str):
    """Serve CSS files"""
    file_path = f"../frontend/build/static/css/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/css")
    else:
        raise HTTPException(status_code=404, detail="CSS file not found")

@api_router.get("/static/media/{filename}")
async def serve_media(filename: str):
    """Serve media files"""
    file_path = f"../frontend/build/static/media/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Media file not found")

@api_router.get("/debug/static-test")
async def debug_static_test():
    """Debug route to test static file serving"""
    build_dir = "../frontend/build"
    static_dir = f"{build_dir}/static"
    js_dir = f"{static_dir}/js"
    
    result = {
        "build_exists": os.path.exists(build_dir),
        "static_exists": os.path.exists(static_dir),
        "js_exists": os.path.exists(js_dir),
        "js_files": [],
        "css_files": []
    }
    
    if os.path.exists(js_dir):
        result["js_files"] = os.listdir(js_dir)
    
    css_dir = f"{static_dir}/css"
    if os.path.exists(css_dir):
        result["css_files"] = os.listdir(css_dir)
    
    return result

# File Upload Endpoint for Assets

@api_router.post("/grpc/upload-file")
async def upload_file(file: bytes, upload_url: str):
    """Upload file to a signed URL"""
    try:
        import httpx
        
        # Upload file to the provided signed URL
        async with httpx.AsyncClient() as client:
            response = await client.put(upload_url, content=file)
            
        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'content_length': len(file),
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/debug/environment")
async def debug_environment():
    """Debug endpoint to check environment and HTML content"""
    index_path = "../frontend/build/index.html"
    
    # Read current HTML content
    html_preview = "File not found"
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            html_preview = html_content[:500]  # First 500 characters
            
    return {
        "environment": os.environ.get('ENVIRONMENT', 'local'),
        "environment_var_set": 'ENVIRONMENT' in os.environ,
        "html_preview": html_preview,
        "static_references": [
            line.strip() for line in html_preview.split('\n') 
            if 'static/' in line or 'src=' in line or 'href=' in line
        ][:5]
    }

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        while True:
            # Keep connection alive and send periodic updates
            await asyncio.sleep(5)

            if graph_builder:
                update_data = {
                    "type": "trace_update",
                    "timestamp": datetime.now().isoformat(),
                    "trace_count": len(graph_builder.traces),
                    "latest_traces": graph_builder.get_all_trace_ids()[-10:],  # Last 10 traces
                    "monitored_topics": graph_builder.get_monitored_topics()
                }

                await websocket.send_text(json.dumps(update_data))

    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.debug("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

# Note: App configuration moved after app creation

from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("🗺️ Marauder's Map awakening... 'I solemnly swear I am up to no good'")
    
    # Always initialize Blueprint components first
    try:
        await initialize_blueprint_components()
        logger.info("✅ Blueprint components startup complete")
    except Exception as e:
        logger.error(f"❌ Failed to start Blueprint components: {e}")
        logger.error("⚠️  Blueprint functionality may be limited")
    
    # Check if Trace Viewer is enabled before starting Kafka components
    trace_viewer_enabled = settings.get("tabs", {}).get("trace_viewer", {}).get("enabled", True)
    
    if trace_viewer_enabled:
        logger.info("🔍 Trace Viewer is enabled - initializing Kafka components")
        try:
            await initialize_kafka_components()
            logger.info("✅ Marauder's Map fully activated - 'Mischief Managed'")
        except Exception as e:
            logger.error(f"❌ Failed to start Kafka components: {e}")
            logger.error("⚠️  Continuing without Kafka components - manual initialization required")
    else:
        logger.info("⚠️  Trace Viewer is disabled - skipping Kafka components initialization")
        logger.info("✅ Marauder's Map revealed - 'Mischief Managed' (tracking mode only)")
    
    yield
    
    # Shutdown
    logger.info("🔄 Application shutting down...")
    if kafka_consumer:
        kafka_consumer.stop_consuming()
    
    # Close Redis connections
    if redis_service:
        redis_service.close_all_connections()
    
    # Close WebSocket connections
    for websocket in websocket_connections:
        try:
            await websocket.close()
        except:
            pass
    
    logger.info("✅ Application shutdown complete")

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the FastAPI app with lifespan
app = FastAPI(title="Kafka Trace Viewer", version="1.0.0", lifespan=lifespan)

# Environment-aware static file serving
# In production/deployed environments, static files need to be served via API routes
# In local development, they can be served directly via mounting
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')
logger.info(f"🌍 Running in {ENVIRONMENT} environment")

if ENVIRONMENT == 'local' and os.path.exists("../frontend/build/static"):
    # Local development: mount static files normally
    app.mount("/static", StaticFiles(directory="../frontend/build/static"), name="static")
    logger.info("📁 Mounted static files for local development")

# Include the router in the main app
app.include_router(api_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging already configured above

# Static file routes moved to API router to bypass infrastructure routing

# Static file routes - handle both deployed and local environments
@app.get("/static/js/{filename}")
async def serve_static_js(filename: str):
    """Serve JavaScript files from /static/ path (redirect to API route or serve directly)"""
    file_path = f"../frontend/build/static/js/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="JavaScript file not found")

@app.get("/static/css/{filename}")
async def serve_static_css(filename: str):
    """Serve CSS files from /static/ path (redirect to API route or serve directly)"""
    file_path = f"../frontend/build/static/css/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/css")
    else:
        raise HTTPException(status_code=404, detail="CSS file not found")

@app.get("/static/media/{filename}")
async def serve_static_media(filename: str):
    """Serve media files from /static/ path (redirect to API route or serve directly)"""
    file_path = f"../frontend/build/static/media/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Media file not found")

# Frontend routes
@app.get("/")
async def serve_frontend():
    """Serve the React app index.html with environment-aware static paths"""
    index_path = "../frontend/build/index.html"
    
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend build not found")
    
    # Read the index.html content
    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # In production/deployed environments, rewrite static paths to use API routes
    if ENVIRONMENT != 'local':
        html_content = html_content.replace('src="/static/', 'src="/api/static/')
        html_content = html_content.replace('href="/static/', 'href="/api/static/')
        logger.debug("🔄 Rewritten static paths for production environment")
    
    return Response(content=html_content, media_type="text/html")

# Catch-all route for SPA routing - must be last
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch-all route for SPA routing - serve index.html for any non-API routes"""
    # Don't interfere with API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # For all other routes, serve the React app (SPA routing) with environment-aware paths
    index_path = "../frontend/build/index.html"
    
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend build not found")
    
    # Read the index.html content
    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # In production/deployed environments, rewrite static paths to use API routes
    if ENVIRONMENT != 'local':
        html_content = html_content.replace('src="/static/', 'src="/api/static/')
        html_content = html_content.replace('href="/static/', 'href="/api/static/')
    
    return Response(content=html_content, media_type="text/html")
if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,  # More verbose for local development
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Starting Kafka Trace Viewer Server...")
    logger.info(f"📂 Working directory: {os.getcwd()}")
    logger.info(f"📂 Config directory: {CONFIG_DIR}")
    logger.info(f"📂 Proto directory: {PROTO_DIR}")
    
    # Check basic requirements before starting
    if not CONFIG_DIR.exists():
        logger.error(f"❌ Configuration directory not found: {CONFIG_DIR}")
        logger.error("💡 Make sure you're running from the backend/ directory")
        logger.error("💡 Try: cd backend && python server.py")
        sys.exit(1)
    
    try:
        uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False)
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        raise