#!/usr/bin/env python3
"""
Local development runner for Kafka Trace Viewer
Handles setup and provides better error messages for local development
"""
import os
import sys
import subprocess
from pathlib import Path

def check_system_requirements():
    """Check if all system requirements are met"""
    print("🔍 Checking system requirements...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print(f"❌ Python 3.11+ required, found {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check protoc
    try:
        result = subprocess.run(['protoc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {result.stdout.strip()}")
        else:
            print("❌ protoc command failed")
            return False
    except FileNotFoundError:
        print("❌ protoc (Protocol Buffers compiler) not found")
        print("💡 Install with: brew install protobuf (macOS) or apt-get install protobuf-compiler (Ubuntu)")
        return False
    
    return True

def check_project_structure():
    """Check if we're in the right directory with proper structure"""
    print("\n📁 Checking project structure...")
    
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    
    # Check if we're in backend directory
    if current_dir.name != 'backend':
        print("⚠️  You should run this from the backend/ directory")
        print("💡 Try: cd backend && python run_local.py")
    
    # Check required files and directories
    required_items = [
        'server.py',
        'requirements.txt',
        'config',
        'config/kafka.yaml',
        'config/topics.yaml',
        'config/settings.yaml',
        'config/proto'
    ]
    
    missing_items = []
    for item in required_items:
        if not Path(item).exists():
            missing_items.append(item)
        else:
            print(f"✅ {item}")
    
    if missing_items:
        print(f"\n❌ Missing required files/directories: {missing_items}")
        return False
    
    return True

def check_dependencies():
    """Check Python dependencies"""
    print("\n🐍 Checking Python dependencies...")
    
    package_mappings = {
        'fastapi': 'fastapi',
        'confluent-kafka': 'confluent_kafka',
        'protobuf': 'google.protobuf',
        'pyyaml': 'yaml', 
        'websockets': 'websockets'
    }
    
    missing_packages = []
    for package_name, import_name in package_mappings.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"❌ {package_name}")
    
    if missing_packages:
        print(f"\n💡 Install missing packages with: pip install {' '.join(missing_packages)}")
        print("💡 Or install all requirements: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main function to run all checks and start the server"""
    print("🚀 Kafka Trace Viewer - Local Development Setup")
    print("=" * 50)
    
    # Run all checks
    if not check_system_requirements():
        print("\n❌ System requirements not met. Please install missing components.")
        sys.exit(1)
    
    if not check_project_structure():
        print("\n❌ Project structure issues found. Please fix and try again.")
        sys.exit(1)
    
    if not check_dependencies():
        print("\n❌ Python dependencies missing. Please install them.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ All checks passed! Starting Kafka Trace Viewer...")
    print("=" * 50)
    
    # Start the server
    try:
        # Add current directory to Python path
        sys.path.insert(0, str(Path.cwd()))
        
        print("\n🌐 Starting server at:")
        print("   - API: http://localhost:8001")
        print("   - Health: http://localhost:8001/api/health") 
        print("   - Docs: http://localhost:8001/docs")
        print("\n💡 Start the frontend separately with: cd frontend && yarn start")
        print("🛑 Press Ctrl+C to stop the server")
        print("\n" + "=" * 50)
        
        # Import and start the server using uvicorn
        import uvicorn
        import logging
        
        # Configure logging for local development
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Start the server (this will keep running)
        uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        print("✅ Shutdown complete")
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()