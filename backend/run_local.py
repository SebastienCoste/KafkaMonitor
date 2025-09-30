#!/usr/bin/env python3
"""
Local development runner for Kafka Trace Viewer
Handles setup and provides better error messages for local development
"""
import os
import sys
import subprocess
import socket
from pathlib import Path
import argparse

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

def check_port_available(port):
    """Check if a port is available"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', port))
        return True
    except OSError:
        return False


def kill_process_on_port(port):
    """Attempt to kill any process using the given TCP port (best-effort, cross-platform)."""
    import platform
    import time
    import signal
    system = platform.system().lower()
    print(f"🧹 Attempting to free port {port} (detected OS: {system})...")

    killed_any = False

    try:
        if 'windows' in system:
            # netstat -ano | findstr :port
            try:
                result = subprocess.run(
                    ['cmd', '/c', f'netstat -ano | findstr :{port}'],
                    capture_output=True, text=True
                )
                lines = [l for l in result.stdout.splitlines() if l.strip()]
                pids = set()
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        pids.add(parts[-1])
                for pid in pids:
                    print(f"🔪 taskkill PID {pid}")
                    subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True)
                    killed_any = True
            except Exception as e:
                print(f"⚠️ Windows kill attempt failed: {e}")
        else:
            # Try lsof first
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True)
                if result.returncode == 0:
                    pids = [p for p in result.stdout.splitlines() if p.strip()]
                    for pid in pids:
                        try:
                            print(f"🔪 Killing PID {pid} (SIGTERM)")
                            os.kill(int(pid), signal.SIGTERM)
                            killed_any = True
                        except Exception as e:
                            print(f"⚠️ Failed to SIGTERM PID {pid}: {e}")
                    time.sleep(1)
                    # Force kill remaining
                    for pid in pids:
                        try:
                            print(f"🪓 Forcing kill PID {pid} (SIGKILL)")
                            os.kill(int(pid), signal.SIGKILL)
                        except Exception:
                            pass
                else:
                    # Fallback to fuser
                    print("ℹ️ lsof not available or no PID found, trying fuser")
                    subprocess.run(['fuser', '-k', f'{port}/tcp'], capture_output=True)
                    killed_any = True
            except FileNotFoundError:
                # lsof not found, try fuser directly
                try:
                    subprocess.run(['fuser', '-k', f'{port}/tcp'], capture_output=True)
                    killed_any = True
                except Exception as e:
                    print(f"⚠️ fuser failed: {e}")
            except Exception as e:
                print(f"⚠️ Unix kill attempt failed: {e}")
    finally:
        time.sleep(0.8)
        if not check_port_available(port):
            print(f"❌ Port {port} is still in use after kill attempts.")
        elif killed_any:
            print(f"✅ Freed port {port} successfully.")
        else:
            print(f"ℹ️ No process found on port {port}.")

def main():
    """Main function to run all checks and start the server"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Kafka Trace Viewer Local Development')
    parser.add_argument('--port', type=int, default=8001, help='Port to run the server on (default: 8001)')
    args = parser.parse_args()
    
    print("🚀 Kafka Trace Viewer - Local Development Setup")
    print("=" * 50)
    
    # Check if port is available; if not, try to free it automatically
    if not check_port_available(args.port):
        print(f"⚠️  Port {args.port} is already in use!")
        kill_process_on_port(args.port)
        if not check_port_available(args.port):
            print(f"❌ Unable to free port {args.port}. You can try a different port: python run_local.py --port 8002")
            sys.exit(1)
        else:
            print(f"✅ Proceeding to start server on freed port {args.port}")
    
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
        
        print(f"\n🌐 Starting server at:")
        print(f"   - API: http://localhost:{args.port}")
        print(f"   - Health: http://localhost:{args.port}/api/health") 
        print(f"   - Docs: http://localhost:{args.port}/docs")
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
        uvicorn.run("server:app", host="0.0.0.0", port=args.port, reload=False)
        
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