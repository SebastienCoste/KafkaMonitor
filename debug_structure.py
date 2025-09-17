#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/app/backend/src')

from grpc_proto_loader import GrpcProtoLoader

def debug_structure():
    print("🔧 Debugging directory structure...")
    
    loader = GrpcProtoLoader("/app/backend/config/proto")
    
    # Compile proto files
    if loader.compile_proto_files():
        print("✅ Compilation successful")
        print(f"📁 Temp dir: {loader.temp_dir}")
        
        # List directory structure
        from pathlib import Path
        if loader.temp_dir and Path(loader.temp_dir).exists():
            temp_path = Path(loader.temp_dir)
            print("\n📋 Directory structure:")
            
            def print_tree(path, prefix=""):
                items = sorted(path.iterdir())
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    print(f"{prefix}{current_prefix}{item.name}")
                    
                    if item.is_dir() and not item.name.startswith('.') and len(prefix) < 20:
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        print_tree(item, next_prefix)
            
            print_tree(temp_path)
        
    else:
        print("❌ Compilation failed")

if __name__ == "__main__":
    debug_structure()