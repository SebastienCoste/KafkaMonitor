"""
Protobuf message decoder with support for multiple proto files per topic and subfolder imports
"""
import os
import importlib.util
import tempfile
import subprocess
import shutil
from typing import Dict, Any, Optional, List
from google.protobuf.message import Message
from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import message_factory
import logging
from pathlib import Path

# Set up extensive logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ProtobufDecodingError(Exception):
    """Custom exception for protobuf decoding errors"""
    pass

class ProtobufDecoder:
    """Handles protobuf message decoding for multiple topics with caching"""

    def __init__(self, proto_dir: str):
        self.proto_dir = Path(proto_dir)
        self.topic_decoders: Dict[str, 'TopicDecoder'] = {}
        
        # Initialize cache
        from src.protobuf_cache import ProtobufCache
        self.cache = ProtobufCache(str(self.proto_dir))
        
    def load_topic_protobuf(self, topic: str, proto_file: str, message_type: str):
        """Load protobuf definition for a specific topic"""
        logger.info(f"🔄 Loading protobuf for topic: {topic}")
        logger.info(f"📄 Proto file: {proto_file}")
        logger.info(f"🎯 Message type: {message_type}")
        logger.info(f"📂 Proto directory: {self.proto_dir}")
        
        try:
            # Handle both direct files and subfolder files
            proto_path = None
            
            # First try direct path
            direct_path = self.proto_dir / proto_file
            if direct_path.exists():
                proto_path = direct_path
                logger.debug(f"✅ Found proto file at direct path: {proto_path}")
            else:
                # Search in subdirectories
                logger.debug(f"🔍 Direct path not found, searching subdirectories...")
                for root, dirs, files in os.walk(self.proto_dir):
                    for file in files:
                        if file == proto_file or file == os.path.basename(proto_file):
                            candidate_path = Path(root) / file
                            logger.debug(f"🔍 Found candidate: {candidate_path}")
                            if candidate_path.exists():
                                proto_path = candidate_path
                                logger.debug(f"✅ Found proto file in subdirectory: {proto_path}")
                                break
                    if proto_path:
                        break
            
            if not proto_path or not proto_path.exists():
                logger.error(f"❌ Proto file not found: {proto_file}")
                logger.error(f"🔍 Searched in directory: {self.proto_dir}")
                logger.error(f"🔍 Available files:")
                for root, dirs, files in os.walk(self.proto_dir):
                    for file in files:
                        if file.endswith('.proto'):
                            logger.error(f"  📄 {os.path.relpath(os.path.join(root, file), self.proto_dir)}")
                raise FileNotFoundError(f"Proto file not found: {proto_file}")
                
            logger.info(f"🎯 Using proto file: {proto_path}")
            decoder = TopicDecoder(str(proto_path), message_type)
            self.topic_decoders[topic] = decoder
            logger.info(f"✅ Successfully loaded protobuf decoder for topic '{topic}' with message type '{message_type}'")
            
        except Exception as e:
            logger.error(f"💥 Failed to load protobuf for topic '{topic}': {str(e)}")
            logger.error(f"🔴 Error type: {type(e).__name__}")
            if hasattr(e, '__cause__') and e.__cause__:
                logger.error(f"🔴 Caused by: {e.__cause__}")
            raise

    def decode_message(self, topic: str, message_bytes: bytes) -> Dict[str, Any]:
        """
        Decode protobuf message for a specific topic
        
        Args:
            topic: Kafka topic name
            message_bytes: Raw message bytes
            
        Returns:
            Decoded message as dictionary
        """
        if topic not in self.topic_decoders:
            raise ValueError(f"No protobuf decoder loaded for topic: {topic}")
            
        return self.topic_decoders[topic].decode_message(message_bytes)

    def get_available_topics(self) -> List[str]:
        """Get list of topics with loaded protobuf decoders"""
        return list(self.topic_decoders.keys())

class TopicDecoder:
    """Handles protobuf decoding for a single topic"""
    
    def __init__(self, proto_file_path: str, message_type: str):
        self.proto_file_path = proto_file_path
        self.message_type = message_type
        self.message_class = None
        self._load_proto_definition()

    def _load_proto_definition(self):
        """Load and compile protobuf definition with support for subfolder imports"""
        logger.info(f"🔄 Starting protobuf compilation for: {self.proto_file_path}")
        logger.info(f"🎯 Target message type: {self.message_type}")
        
        try:
            # Create temporary directory for compiled proto
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"📁 Created temp directory: {temp_dir}")
                
                # Get the root proto directory and the proto file path
                proto_path = Path(self.proto_file_path)
                if not proto_path.exists():
                    raise FileNotFoundError(f"Proto file not found: {self.proto_file_path}")
                
                # Find the root proto directory (contains all proto files and subfolders)
                proto_root = proto_path.parent
                while proto_root.name != 'proto' and proto_root.parent != proto_root:
                    proto_root = proto_root.parent
                
                logger.info(f"📂 Proto root directory: {proto_root}")
                logger.info(f"📄 Proto file: {proto_path}")
                
                # Copy entire proto directory structure to temp directory to handle imports
                temp_proto_dir = Path(temp_dir) / "proto"
                logger.debug(f"📋 Copying proto directory to: {temp_proto_dir}")
                shutil.copytree(proto_root, temp_proto_dir)
                
                # Get relative path from proto root
                relative_proto_path = proto_path.relative_to(proto_root)
                temp_proto_file = temp_proto_dir / relative_proto_path
                
                logger.debug(f"🔗 Relative proto path: {relative_proto_path}")
                logger.debug(f"🎯 Temp proto file: {temp_proto_file}")
                
                # First, compile all dependency proto files (common/*.proto)
                logger.info("🔧 Compiling dependency proto files first...")
                dependency_files = []
                for root, dirs, files in os.walk(temp_proto_dir):
                    for file in files:
                        if file.endswith('.proto'):
                            full_path = Path(root) / file
                            relative_path = full_path.relative_to(temp_proto_dir)
                            dependency_files.append(str(relative_path))
                
                logger.debug(f"📋 Found proto files: {dependency_files}")
                
                # Compile all proto files at once to handle dependencies
                cmd = [
                    'protoc',
                    f'--python_out={temp_dir}',
                    f'--proto_path={temp_proto_dir}',
                ] + dependency_files
                
                logger.info(f"🚀 Running protoc command: {' '.join(cmd)}")
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_proto_dir)
                
                if result.returncode != 0:
                    logger.error(f"❌ Protoc compilation failed!")
                    logger.error(f"🔴 Return code: {result.returncode}")
                    logger.error(f"🔴 STDERR: {result.stderr}")
                    logger.error(f"🔴 STDOUT: {result.stdout}")
                    
                    # List files in temp directory for debugging
                    logger.error("📋 Files in temp proto directory:")
                    for root, dirs, files in os.walk(temp_proto_dir):
                        for file in files:
                            logger.error(f"  📄 {os.path.join(root, file)}")
                    
                    raise ProtobufDecodingError(f"Failed to compile proto: {result.stderr}")
                
                logger.info("✅ Protoc compilation successful!")
                logger.debug(f"📤 STDOUT: {result.stdout}")
                
                # Find the generated Python file
                proto_name = proto_path.stem
                
                # Look for the generated file in the expected location
                expected_py_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('_pb2.py'):
                            full_path = os.path.join(root, file)
                            expected_py_files.append(full_path)
                            logger.debug(f"📄 Found generated file: {full_path}")
                
                # Find the specific file we need
                target_py_file = None
                for py_file in expected_py_files:
                    if proto_name + '_pb2.py' in py_file:
                        target_py_file = py_file
                        break
                
                if not target_py_file:
                    logger.error(f"❌ Could not find generated Python file for {proto_name}")
                    logger.error(f"🔍 Expected files containing '{proto_name}_pb2.py'")
                    logger.error(f"🔍 Found files: {expected_py_files}")
                    raise ProtobufDecodingError(f"Generated Python file not found for {proto_name}")
                
                logger.info(f"🎯 Found target Python file: {target_py_file}")
                
                # Import the compiled proto module with proper Python path handling
                module_name = f"{proto_name}_pb2"
                spec = importlib.util.spec_from_file_location(module_name, target_py_file)
                proto_module = importlib.util.module_from_spec(spec)
                
                logger.debug(f"📦 Loading module: {module_name}")
                
                # Add the temp directory to Python path temporarily to handle imports
                import sys
                original_path = sys.path[:]
                temp_dir_added = False
                
                try:
                    # Add temp directory to sys.path for imports
                    if temp_dir not in sys.path:
                        sys.path.insert(0, temp_dir)
                        temp_dir_added = True
                        logger.debug(f"🔗 Added temp directory to Python path: {temp_dir}")
                    
                    # Add the directory containing the generated files to path
                    generated_dir = os.path.dirname(target_py_file)
                    if generated_dir not in sys.path:
                        sys.path.insert(0, generated_dir)
                        logger.debug(f"🔗 Added generated directory to Python path: {generated_dir}")
                    
                    # Also add the parent directory for relative imports
                    parent_dir = os.path.dirname(generated_dir)
                    if parent_dir not in sys.path:
                        sys.path.insert(0, parent_dir)
                        logger.debug(f"🔗 Added parent directory to Python path: {parent_dir}")
                    
                    logger.debug(f"🐍 Current Python path: {sys.path[:5]}...")  # Show first 5 entries
                    
                    spec.loader.exec_module(proto_module)
                    logger.debug(f"✅ Module loaded successfully")
                    
                finally:
                    # Restore original Python path
                    if temp_dir_added:
                        sys.path = original_path
                        logger.debug(f"🔄 Restored original Python path")
                
                # Get the specific message class
                if hasattr(proto_module, self.message_type):
                    self.message_class = getattr(proto_module, self.message_type)
                    logger.info(f"✅ Successfully loaded message class: {self.message_type}")
                    logger.debug(f"🏷️  Message class type: {type(self.message_class)}")
                else:
                    available_classes = []
                    for attr_name in dir(proto_module):
                        attr = getattr(proto_module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, Message):
                            available_classes.append(attr_name)
                    
                    logger.error(f"❌ Message type '{self.message_type}' not found in module")
                    logger.error(f"🔍 Available message classes: {available_classes}")
                    logger.error(f"🔍 All module attributes: {[attr for attr in dir(proto_module) if not attr.startswith('_')]}")
                    
                    raise ProtobufDecodingError(
                        f"Message type '{self.message_type}' not found. Available: {available_classes}"
                    )

        except Exception as e:
            logger.error(f"💥 Failed to load protobuf definition: {str(e)}")
            logger.error(f"🔴 Error type: {type(e).__name__}")
            if hasattr(e, '__cause__') and e.__cause__:
                logger.error(f"🔴 Caused by: {e.__cause__}")
            raise ProtobufDecodingError(f"Protobuf loading failed: {str(e)}") from e

    def decode_message(self, message_bytes: bytes) -> Dict[str, Any]:
        """
        Decode protobuf message to dictionary
        
        Args:
            message_bytes: Raw message bytes
            
        Returns:
            Decoded message as dictionary
        """
        try:
            if not self.message_class:
                raise RuntimeError("Message class not loaded")
                
            message_obj = self.message_class()
            message_obj.ParseFromString(message_bytes)
            
            return self._message_to_dict(message_obj)

        except Exception as e:
            logger.error(f"Failed to decode protobuf message: {e}")
            raise

    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convert protobuf message to dictionary"""
        from google.protobuf.json_format import MessageToDict
        return MessageToDict(message, preserving_proto_field_name=True)

class MockProtobufDecoder:
    """Mock decoder for development and testing"""
    
    def __init__(self):
        self.mock_data_templates = {
            'user-events': {
                'trace_id': 'trace-{trace_id}',
                'user_id': 'user-{user_id}',
                'session_id': 'session-{session_id}',
                'event_type': 'page_view',
                'timestamp': 0,
                'page_url': '/dashboard',
                'user_agent': 'Mozilla/5.0',
                'properties': {'source': 'web', 'version': '1.0'}
            },
            'processed-events': {
                'trace_id': 'trace-{trace_id}',
                'original_event_id': 'event-{event_id}',
                'processing_stage': 'enrichment',
                'processed_timestamp': 0,
                'processing_result': 'success',
                'tags': ['user_action', 'web'],
                'confidence_score': 0.95,
                'enriched_properties': {'geo_country': 'US', 'device_type': 'desktop'},
                'user_segment': 'premium',
                'requires_notification': True
            },
            'notifications': {
                'trace_id': 'trace-{trace_id}',
                'notification_id': 'notif-{notif_id}',
                'user_id': 'user-{user_id}',
                'notification_type': 'email',
                'created_timestamp': 0,
                'title': 'Welcome!',
                'content': 'Thanks for using our service',
                'channel': 'email',
                'sent_successfully': True,
                'delivery_status': 'delivered',
                'sent_timestamp': 0,
                'retry_count': 0,
                'failure_reason': ''
            },
            'analytics': {
                'trace_id': 'trace-{trace_id}',
                'event_name': 'user_engagement',
                'event_category': 'user_behavior',
                'timestamp': 0,
                'metrics': {'duration': 120.5, 'clicks': 5},
                'dimensions': {'page': 'dashboard', 'feature': 'analytics'},
                'aggregation_period': 'hourly',
                'total_value': 125.0,
                'event_count': 1,
                'user_id': 'user-{user_id}',
                'session_id': 'session-{session_id}'
            }
        }
        
    def load_topic_protobuf(self, topic: str, proto_file: str, message_type: str):
        """Mock implementation - just log the configuration"""
        logger.info(f"Mock: Loading protobuf for topic '{topic}' (proto: {proto_file}, type: {message_type})")
        
    def decode_message(self, topic: str, message_bytes: bytes) -> Dict[str, Any]:
        """Mock decode - return template data"""
        if topic in self.mock_data_templates:
            # In a real scenario, we'd parse message_bytes
            # For mock, return template with some variation
            import time, random
            data = self.mock_data_templates[topic].copy()
            
            # Add some dynamic values
            if 'timestamp' in data:
                data['timestamp'] = int(time.time())
            if 'processed_timestamp' in data:
                data['processed_timestamp'] = int(time.time())
            if 'created_timestamp' in data:
                data['created_timestamp'] = int(time.time())
            if 'sent_timestamp' in data:
                data['sent_timestamp'] = int(time.time())
                
            return data
        else:
            return {'error': f'No mock data for topic: {topic}', 'raw_data': str(message_bytes)}
    
    def get_available_topics(self) -> List[str]:
        """Get mock topics"""
        return list(self.mock_data_templates.keys())