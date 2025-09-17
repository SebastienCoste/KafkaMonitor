#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/app/backend/src')
import tempfile
from pathlib import Path

# Test direct import from the compiled temp directory
def test_direct_import():
    print("🔧 Testing direct import from temp directory...")
    
    from grpc_proto_loader import GrpcProtoLoader
    
    loader = GrpcProtoLoader("/app/backend/config/proto/grpc")
    
    if loader.validate_proto_files().get('all_present'):
        if loader.compile_proto_files():
            print("✅ Compilation successful")
            print(f"📁 Temp dir: {loader.temp_dir}")
            
            # Add temp dir to path
            if loader.temp_dir:
                sys.path.insert(0, loader.temp_dir)
                
                try:
                    # Test importing proto_gen modules directly
                    print("🔍 Testing proto_gen imports...")
                    
                    import proto_gen.ingress_server.ingress_server_pb2 as ingress_pb2
                    import proto_gen.ingress_server.ingress_server_pb2_grpc as ingress_grpc
                    
                    print("✅ Direct imports successful!")
                    
                    # Check for service stub
                    if hasattr(ingress_grpc, 'IngressServerStub'):
                        print("✅ IngressServerStub found")
                        print(f"🔍 Service methods: {[m for m in dir(ingress_grpc.IngressServerStub) if not m.startswith('_')]}")
                    else:
                        print("❌ IngressServerStub not found")
                        print(f"Available: {[a for a in dir(ingress_grpc) if not a.startswith('_')]}")
                    
                    # Test asset storage
                    import proto_gen.asset_storage.asset_storage_pb2 as asset_pb2
                    import proto_gen.asset_storage.asset_storage_pb2_grpc as asset_grpc
                    
                    print("✅ Asset storage imports successful!")
                    
                    if hasattr(asset_grpc, 'AssetStorageServiceStub'):
                        print("✅ AssetStorageServiceStub found")
                        print(f"🔍 Service methods: {[m for m in dir(asset_grpc.AssetStorageServiceStub) if not m.startswith('_')]}")
                    else:
                        print("❌ AssetStorageServiceStub not found")
                        print(f"Available: {[a for a in dir(asset_grpc) if not a.startswith('_')]}")
                    
                except Exception as e:
                    print(f"❌ Import failed: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Remove temp dir from path
                sys.path.remove(loader.temp_dir)
        else:
            print("❌ Compilation failed")
    else:
        print("❌ Validation failed")

if __name__ == "__main__":
    test_direct_import()