#!/usr/bin/env python3

import sys
import os
import tempfile
from pathlib import Path

# Add the backend src to path
sys.path.insert(0, '/app/backend/src')

from grpc_proto_loader import GrpcProtoLoader

def main():
    print("🔧 Testing gRPC proto loading...")
    
    loader = GrpcProtoLoader("/app/backend/config/proto/grpc")
    
    print("📋 Validating proto files...")
    validation = loader.validate_proto_files()
    print(f"Validation result: {validation}")
    
    if validation.get('all_present'):
        print("🔨 Compiling proto files...")
        if loader.compile_proto_files():
            print("✅ Proto files compiled successfully")
            
            print("📦 Loading service modules...")
            if loader.load_service_modules():
                print("✅ Service modules loaded successfully")
                
                print("🔍 Available modules:")
                for service, modules in loader.compiled_modules.items():
                    print(f"  {service}: {list(modules.keys())}")
                    
            else:
                print("❌ Failed to load service modules")
        else:
            print("❌ Failed to compile proto files")
    else:
        print("❌ Proto validation failed")

if __name__ == "__main__":
    main()