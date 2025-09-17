#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/app/backend/src')

from grpc_proto_loader import GrpcProtoLoader

def test_import():
    print("🔧 Testing imports...")
    
    loader = GrpcProtoLoader("/app/backend/config/proto")
    
    # Compile proto files
    if loader.compile_proto_files():
        print("✅ Compilation successful")
        
        # Add temp directory to sys.path
        sys.path.insert(0, loader.temp_dir)
        
        try:
            # Test importing the modules
            print("🔍 Testing ingress_service import...")
            import proto_gen.eadp.cadie.ingressserver.v1.ingress_service_pb2 as ingress_pb2
            import proto_gen.eadp.cadie.ingressserver.v1.ingress_service_pb2_grpc as ingress_grpc
            print("✅ Ingress service modules imported successfully")
            
            print("🔍 Testing storage_service import...")
            import proto_gen.eadp.cadie.shared.storageinterface.v1.storage_service_admin_pb2 as storage_pb2
            import proto_gen.eadp.cadie.shared.storageinterface.v1.storage_service_admin_pb2_grpc as storage_grpc
            print("✅ Storage service modules imported successfully")
            
            # Check for service stubs
            if hasattr(ingress_grpc, 'IngressServerStub'):
                print("✅ IngressServerStub found")
            else:
                print("❌ IngressServerStub not found")
                print(f"Available: {[attr for attr in dir(ingress_grpc) if not attr.startswith('_')]}")
            
            if hasattr(storage_grpc, 'AssetStorageServiceStub'):
                print("✅ AssetStorageServiceStub found")
            else:
                print("❌ AssetStorageServiceStub not found")
                print(f"Available: {[attr for attr in dir(storage_grpc) if not attr.startswith('_')]}")
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            import traceback
            traceback.print_exc()
        
        # Remove temp directory from sys.path
        sys.path.remove(loader.temp_dir)
        
    else:
        print("❌ Compilation failed")

if __name__ == "__main__":
    test_import()