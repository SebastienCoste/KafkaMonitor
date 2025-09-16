from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# Configuration paths
CONFIG_DIR = ROOT_DIR / "config"
PROTO_DIR = CONFIG_DIR / "proto"
ENVIRONMENTS_DIR = CONFIG_DIR / "environments"
GRPC_PROTOS_DIR = PROTO_DIR / "grpc"  # Updated to use subfolder under proto

async def initialize_kafka_components():
    """Initialize Kafka trace viewer components"""
    logger.info("🚀 Starting Kafka trace viewer component initialization")
    global graph_builder, kafka_consumer, grpc_client, environment_manager
    
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
        
        # Initialize Environment Manager
        logger.info("🌍 Initializing Environment Manager...")
        environment_manager = EnvironmentManager(
            environments_dir=str(CONFIG_DIR / "environments"),
            protobuf_decoder=decoder,
            settings=settings
        )
        logger.info("✅ Environment Manager initialized")
        
        # Default to DEV environment (or first available)
        available_envs = environment_manager.list_environments()
        default_env = 'DEV' if 'DEV' in available_envs else (available_envs[0] if available_envs else None)
        
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
        
        # Initialize gRPC client
        logger.info("🔧 Initializing gRPC client...")
        grpc_client = GrpcClient(str(GRPC_PROTOS_DIR), str(ENVIRONMENTS_DIR))
        
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
            'response': response.text if response.status_code != 200 else 'Upload successful'
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
from fastapi.responses import FileResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    # Startup
    logger.info("🚀 Application starting up...")
    try:
        await initialize_kafka_components()
        logger.info("✅ Application startup complete")
    except Exception as e:
        logger.error(f"❌ Failed to start Kafka components: {e}")
        logger.error("⚠️  Continuing without Kafka components - manual initialization required")
    
    yield
    
    # Shutdown
    logger.info("🔄 Application shutting down...")
    if kafka_consumer:
        kafka_consumer.stop_consuming()
    
    # Close WebSocket connections
    for websocket in websocket_connections:
        try:
            await websocket.close()
        except:
            pass
    
    logger.info("✅ Application shutdown complete")

# Create the FastAPI app with lifespan
app = FastAPI(title="Kafka Trace Viewer", version="1.0.0", lifespan=lifespan)

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Frontend routes must be defined at the end to avoid conflicts with API routes
@app.get("/")
async def serve_frontend():
    """Serve the React app index.html"""
    if os.path.exists("../frontend/build/index.html"):
        return FileResponse("../frontend/build/index.html")
    else:
        raise HTTPException(status_code=404, detail="Frontend build not found")

# Catch-all route for SPA routing - must be last
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch-all route for SPA routing - serve index.html for any non-API routes"""
    # Don't interfere with API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    # For all other routes, serve the React app (SPA routing)
    if os.path.exists("../frontend/build/index.html"):
        return FileResponse("../frontend/build/index.html")
    else:
        raise HTTPException(status_code=404, detail="Frontend build not found")

# Mount static files at the very end - this should have the highest priority for /static/* paths
if os.path.exists("../frontend/build/static"):
    app.mount("/static", StaticFiles(directory="../frontend/build/static"), name="static")
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