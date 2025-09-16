#!/usr/bin/env python3
"""
Local development server for Kafka Trace Viewer
This server properly serves static files for local development
"""

import os
import sys
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

# For local development, we'll create essential endpoints
# Note: Full functionality requires fixing the main server.py

@app.get("/api/health")
async def health():
    return {"status": "healthy", "message": "Local development server", "static_mounted": True}

print("✅ Created basic API endpoints")

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