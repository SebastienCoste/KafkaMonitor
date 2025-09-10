"""
Protobuf compilation caching system to avoid recompiling on every startup
"""
import os
import hashlib
import pickle
import shutil
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ProtobufCache:
    """Manages protobuf compilation caching"""
    
    def __init__(self, proto_dir: str, cache_dir: str = None):
        self.proto_dir = Path(proto_dir)
        self.cache_dir = Path(cache_dir or (self.proto_dir.parent / ".protobuf_cache"))
        self.cache_dir.mkdir(exist_ok=True)
        
    def _get_proto_files_hash(self) -> str:
        """Calculate hash of all proto files to detect changes"""
        hasher = hashlib.md5()
        
        # Get all proto files and their content
        proto_files = []
        for proto_file in sorted(self.proto_dir.rglob("*.proto")):
            proto_files.append((str(proto_file.relative_to(self.proto_dir)), proto_file.read_text()))
        
        # Hash the combined content
        for file_path, content in proto_files:
            hasher.update(file_path.encode())
            hasher.update(content.encode())
            
        return hasher.hexdigest()
    
    def _get_cache_path(self, topic: str, proto_file: str) -> Path:
        """Get cache path for a specific topic/proto combination"""
        safe_topic = topic.replace('/', '_').replace('-', '_')
        safe_proto = proto_file.replace('/', '_').replace('.proto', '')
        return self.cache_dir / f"{safe_topic}_{safe_proto}"
    
    def is_cache_valid(self, topic: str, proto_file: str) -> bool:
        """Check if cached compilation is still valid"""
        cache_path = self._get_cache_path(topic, proto_file)
        hash_file = cache_path / "hash.txt"
        
        if not cache_path.exists() or not hash_file.exists():
            return False
            
        try:
            cached_hash = hash_file.read_text().strip()
            current_hash = self._get_proto_files_hash()
            return cached_hash == current_hash
        except:
            return False
    
    def save_compilation(self, topic: str, proto_file: str, generated_files: Dict[str, Path], message_class: Any):
        """Save compiled protobuf to cache"""
        cache_path = self._get_cache_path(topic, proto_file)
        cache_path.mkdir(exist_ok=True)
        
        try:
            # Save hash
            current_hash = self._get_proto_files_hash()
            (cache_path / "hash.txt").write_text(current_hash)
            
            # Save generated Python files
            py_files_dir = cache_path / "generated"
            py_files_dir.mkdir(exist_ok=True)
            
            for file_name, file_path in generated_files.items():
                if file_path.exists():
                    shutil.copy2(file_path, py_files_dir / file_name)
            
            # Save message class info
            class_info = {
                'module_name': message_class.__module__,
                'class_name': message_class.__name__,
                'topic': topic,
                'proto_file': proto_file
            }
            
            with open(cache_path / "class_info.pkl", 'wb') as f:
                pickle.dump(class_info, f)
                
            logger.info(f"💾 Cached protobuf compilation for topic '{topic}'")
            
        except Exception as e:
            logger.error(f"Failed to save cache for {topic}: {e}")
            # Clean up partial cache
            if cache_path.exists():
                shutil.rmtree(cache_path)
    
    def load_compilation(self, topic: str, proto_file: str, message_type: str) -> Optional[Any]:
        """Load compiled protobuf from cache"""
        cache_path = self._get_cache_path(topic, proto_file)
        
        if not self.is_cache_valid(topic, proto_file):
            return None
            
        try:
            # Load class info
            with open(cache_path / "class_info.pkl", 'rb') as f:
                class_info = pickle.load(f)
            
            # Load generated Python files
            py_files_dir = cache_path / "generated"
            if not py_files_dir.exists():
                return None
            
            # Find the main protobuf file
            proto_name = Path(proto_file).stem
            main_pb_file = py_files_dir / f"{proto_name}_pb2.py"
            
            if not main_pb_file.exists():
                return None
            
            # Load the module
            spec = importlib.util.spec_from_file_location(f"{proto_name}_pb2", main_pb_file)
            proto_module = importlib.util.module_from_spec(spec)
            
            # Add cache directory to Python path temporarily for imports
            import sys
            original_path = sys.path[:]
            sys.path.insert(0, str(py_files_dir))
            
            try:
                spec.loader.exec_module(proto_module)
                
                # Get the message class
                if hasattr(proto_module, message_type):
                    message_class = getattr(proto_module, message_type)
                    logger.info(f"📦 Loaded cached protobuf for topic '{topic}' -> {message_type}")
                    return message_class
                else:
                    logger.warning(f"Message type '{message_type}' not found in cached module")
                    return None
                    
            finally:
                sys.path = original_path
                
        except Exception as e:
            logger.error(f"Failed to load cache for {topic}: {e}")
            return None
    
    def clear_cache(self):
        """Clear all cached protobuf compilations"""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            logger.info("🗑️  Cleared protobuf cache")