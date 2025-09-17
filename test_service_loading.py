#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/app/backend/src')

from grpc_proto_loader import GrpcProtoLoader

def test_service_loading():
    print("🔧 Testing service loading...")
    
    loader = GrpcProtoLoader("/app/backend/config/proto/grpc")
    
    # Validate and compile
    if loader.validate_proto_files().get('all_present'):
        if loader.compile_proto_files():
            print("✅ Compilation successful")
            
            # Enable debug logging
            import logging
            logging.basicConfig(level=logging.DEBUG)
            
            # Try loading service modules
            print("📦 Attempting to load service modules...")
            result = loader.load_service_modules()
            
            if result:
                print("✅ Service modules loaded successfully!")
                print(f"Available modules: {list(loader.compiled_modules.keys())}")
            else:
                print("❌ Failed to load service modules")
        else:
            print("❌ Compilation failed")
    else:
        print("❌ Validation failed")

if __name__ == "__main__":
    test_service_loading()