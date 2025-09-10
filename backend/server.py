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


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Note: FastAPI app creation moved to after lifespan definition

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Global variables for Kafka trace viewer components
graph_builder: Optional[TraceGraphBuilder] = None
kafka_consumer: Optional[KafkaConsumerService] = None
websocket_connections: List[WebSocket] = []

# Configuration paths
CONFIG_DIR = ROOT_DIR / "config"
PROTO_DIR = CONFIG_DIR / "proto"

async def initialize_kafka_components():
    """Initialize Kafka trace viewer components"""
    logger.info("🚀 Starting Kafka trace viewer component initialization")
    global graph_builder, kafka_consumer
    
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
        
        # Initialize graph builder
        logger.info("🕸️  Initializing graph builder...")
        graph_builder = TraceGraphBuilder(
            topics_config_path=str(CONFIG_DIR / "topics.yaml"),
            max_traces=settings.get('max_traces', 1000)
        )
        logger.info("✅ Graph builder initialized")
        
        # Initialize Kafka consumer
        logger.info("🔌 Initializing Kafka consumer...")
        kafka_consumer = KafkaConsumerService(
            config_path=str(kafka_config_path),
            decoder=decoder,
            trace_header_field=settings.get('trace_header_field', 'trace_id')
        )
        logger.info("✅ Kafka consumer initialized")
        
        # Register message handler
        logger.info("🔗 Registering message handler...")
        kafka_consumer.add_message_handler(graph_builder.add_message)
        logger.info("✅ Message handler registered")
        
        # Subscribe to all topics from graph
        all_topics = graph_builder.topic_graph.get_all_topics()
        logger.info(f"📡 Subscribing to topics: {all_topics}")
        kafka_consumer.subscribe_to_topics(all_topics)
        logger.info("✅ Topic subscription complete")
        
        # Start Kafka consumer in background
        logger.info("🚀 Starting Kafka consumer in background...")
        asyncio.create_task(kafka_consumer.start_consuming_async())
        logger.info("✅ Kafka consumer task created")
        
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
        "timestamp": datetime.now().isoformat(),
        "traces_count": len(graph_builder.traces) if graph_builder else 0
    }

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

# Serve static files (frontend)
if os.path.exists("../frontend/build"):
    app.mount("/static", StaticFiles(directory="../frontend/build/static"), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse("../frontend/build/index.html")

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