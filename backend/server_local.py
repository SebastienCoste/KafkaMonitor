#!/usr/bin/env python3
"""
Local development server for Kafka Trace Viewer
This server properly serves static files for local development
"""

import os
import sys
import yaml
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path.cwd()))

from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

# Simple lifespan for local development
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting local development server...")
    yield
    print("🛑 Shutting down local development server...")

# Create FastAPI app
app = FastAPI(title="Kafka Trace Viewer - Local", version="1.0.0", lifespan=lifespan)

# Mount static files FIRST - this is crucial for local development
if os.path.exists("../frontend/build/static"):
    app.mount("/static", StaticFiles(directory="../frontend/build/static"), name="static")
    print("✅ Mounted static files from ../frontend/build/static")

# Load configuration files
def load_config():
    """Load configuration from YAML files"""
    config = {}
    
    # Load settings
    settings_path = Path("config/settings.yaml")
    if settings_path.exists():
        with open(settings_path, 'r') as f:
            config['settings'] = yaml.safe_load(f)
    else:
        config['settings'] = {}
    
    # Load topics
    topics_path = Path("config/topics.yaml")
    if topics_path.exists():
        with open(topics_path, 'r') as f:
            topics_config = yaml.safe_load(f)
            config['topics'] = topics_config
            
            # Extract topic information
            all_topics = []
            monitored_topics = []
            
            for topic_name, topic_info in topics_config.get('topics', {}).items():
                all_topics.append(topic_name)
                # Check if topic should be monitored by default
                if topic_info.get('monitored', True):
                    monitored_topics.append(topic_name)
            
            # Also check for default_monitored_topics
            default_monitored = topics_config.get('default_monitored_topics', [])
            for topic in default_monitored:
                if topic not in monitored_topics:
                    monitored_topics.append(topic)
            
            config['all_topics'] = all_topics
            config['monitored_topics'] = monitored_topics
    else:
        config['topics'] = {}
        config['all_topics'] = []
        config['monitored_topics'] = []
    
    # Check activate_all_on_startup setting
    activate_all = config['settings'].get('topic_monitoring', {}).get('activate_all_on_startup', True)
    if activate_all:
        config['monitored_topics'] = config['all_topics'].copy()
    
    return config

# Load configuration on startup
app_config = load_config()
print(f"📋 Loaded configuration: {len(app_config['all_topics'])} topics, {len(app_config['monitored_topics'])} monitored")

# For local development, we'll create essential endpoints
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import List

# Store WebSocket connections
websocket_connections: List[WebSocket] = []

@app.get("/api/health")
async def health():
    return {"status": "healthy", "message": "Local development server", "static_mounted": True}

@app.get("/api/traces")
async def get_traces():
    return {"traces": [], "message": "Local development mode - no traces available"}

@app.get("/api/topics")
async def get_topics():
    return {
        "monitored_topics": ["user-events", "processed-events", "analytics", "notifications"],
        "all_topics": ["user-events", "processed-events", "analytics", "notifications"],
        "message": "Local development mode"
    }

@app.get("/api/statistics")
async def get_statistics():
    return {
        "traces": {"total": 0, "active": 0},
        "topics": {"total": 4, "monitored": 4},
        "messages": {"total": 0, "rate": 0},
        "message": "Local development mode"
    }

@app.get("/api/graph")
async def get_graph():
    return {
        "nodes": [],
        "edges": [],
        "statistics": {"components": 0, "nodes": 0, "edges": 0},
        "message": "Local development mode"
    }

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": "Connected to local development server",
            "timestamp": "2025-09-16T06:00:00Z"
        }))
        
        # Keep connection alive and handle messages
        while True:
            try:
                # Wait for client messages (though we don't expect many)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back for testing
                await websocket.send_text(json.dumps({
                    "type": "echo",
                    "message": f"Received: {message}",
                    "timestamp": "2025-09-16T06:00:00Z"
                }))
            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "timestamp": "2025-09-16T06:00:00Z"
                }))
                
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        print("📱 WebSocket client disconnected")
    except Exception as e:
        print(f"📱 WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

print("✅ Created basic API endpoints with WebSocket support")

# Serve the main index.html
@app.get("/")
async def serve_frontend():
    """Serve the React app index.html"""
    index_path = "../frontend/build/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"error": "Frontend build not found. Run 'npm run build' first."}

# Catch-all route for SPA routing
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch-all route for SPA routing"""
    # Don't interfere with API routes or static files
    if full_path.startswith("api/") or full_path.startswith("static/"):
        return {"error": "Not found"}
    
    # For all other routes, serve the React app
    index_path = "../frontend/build/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"error": "Frontend build not found"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("🌐 Local Kafka Trace Viewer Server")
    print("="*50)
    print("📁 Static files: /static/*")
    print("🔗 Frontend: http://localhost:8002")
    print("📡 API: http://localhost:8002/api/*")
    print("🛑 Press Ctrl+C to stop")
    print("="*50)
    
    uvicorn.run("server_local:app", host="0.0.0.0", port=8002, reload=False)