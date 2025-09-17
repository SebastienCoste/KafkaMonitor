#!/usr/bin/env python3

import sys
import os
import tempfile
from pathlib import Path
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Add the backend src to path
sys.path.insert(0, '/app/backend/src')

from grpc_proto_loader import GrpcProtoLoader

def main():
    print("🔧 Simple gRPC test...")
    
    loader = GrpcProtoLoader("/app/backend/config/proto/grpc")
    
    # Validate and compile
    if loader.validate_proto_files().get('all_present'):
        if loader.compile_proto_files():
            print("✅ Compilation successful")
            print(f"📁 Temp dir: {loader.temp_dir}")
            
            # Check if temp dir exists and has the files
            if loader.temp_dir and Path(loader.temp_dir).exists():
                temp_path = Path(loader.temp_dir)
                print("📋 Files in temp directory:")
                
                # List all Python files
                for py_file in temp_path.rglob("*.py"):
                    print(f"  {py_file.relative_to(temp_path)}")
                
                # Try simple direct import
                sys.path.insert(0, str(temp_path))
                
                try:
                    print("\n🔍 Testing direct imports...")
                    
                    # Try importing the grpc package
                    import grpc as grpc_pkg
                    print(f"✅ grpc package imported: {grpc_pkg}")
                    
                    # Try importing ingress_server modules
                    from grpc.ingress_server import ingress_server_pb2
                    print(f"✅ ingress_server_pb2 imported: {ingress_server_pb2}")
                    
                    from grpc.ingress_server import ingress_server_pb2_grpc
                    print(f"✅ ingress_server_pb2_grpc imported: {ingress_server_pb2_grpc}")
                    
                    # Check if service class exists
                    if hasattr(ingress_server_pb2_grpc, 'IngressServerStub'):
                        print("✅ IngressServerStub found")
                    else:
                        print("❌ IngressServerStub not found")
                        print(f"Available attributes: {dir(ingress_server_pb2_grpc)}")
                    
                except Exception as e:
                    print(f"❌ Direct import failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Remove temp path from sys.path
                sys.path.remove(str(temp_path))
            
        else:
            print("❌ Compilation failed")
    else:
        print("❌ Validation failed")

if __name__ == "__main__":
    main()