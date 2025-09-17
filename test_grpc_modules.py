#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/app/backend/src')

from grpc_proto_loader import GrpcProtoLoader

def test_grpc_modules():
    print("🔧 Testing gRPC module generation...")
    
    loader = GrpcProtoLoader("/app/backend/config/proto")
    
    # Compile proto files
    if loader.compile_proto_files():
        print("✅ Compilation successful")
        print(f"📁 Temp dir: {loader.temp_dir}")
        
        # List all generated Python files
        from pathlib import Path
        if loader.temp_dir and Path(loader.temp_dir).exists():
            temp_path = Path(loader.temp_dir)
            print("\n📋 Generated modules:")
            
            for py_file in temp_path.rglob("*_pb2_grpc.py"):
                relative_path = py_file.relative_to(temp_path)
                module_path = str(relative_path).replace('/', '.').replace('.py', '')
                print(f"  {module_path}")
        
    else:
        print("❌ Compilation failed")

if __name__ == "__main__":
    test_grpc_modules()