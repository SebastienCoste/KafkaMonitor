"""
Protobuf message decoder with support for multiple proto files per topic
"""
import os
import importlib.util
import tempfile
import subprocess
from typing import Dict, Any, Optional, List
from google.protobuf.message import Message
from google.protobuf import descriptor_pb2
from google.protobuf import descriptor_pool
from google.protobuf import message_factory
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ProtobufDecoder:
    """Handles protobuf message decoding for multiple topics"""

    def __init__(self, proto_dir: str):
        self.proto_dir = Path(proto_dir)
        self.topic_decoders: Dict[str, 'TopicDecoder'] = {}
        
    def load_topic_protobuf(self, topic: str, proto_file: str, message_type: str):
        """Load protobuf definition for a specific topic"""
        try:
            proto_path = self.proto_dir / proto_file
            if not proto_path.exists():
                raise FileNotFoundError(f"Proto file not found: {proto_path}")
                
            decoder = TopicDecoder(str(proto_path), message_type)
            self.topic_decoders[topic] = decoder
            logger.info(f"Loaded protobuf decoder for topic '{topic}' with message type '{message_type}'")
            
        except Exception as e:
            logger.error(f"Failed to load protobuf for topic '{topic}': {e}")
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
        """Load and compile protobuf definition"""
        try:
            # Create temporary directory for compiled proto
            with tempfile.TemporaryDirectory() as temp_dir:
                # Compile proto file
                proto_dir = os.path.dirname(self.proto_file_path)
                proto_file = os.path.basename(self.proto_file_path)
                
                cmd = [
                    'protoc',
                    f'--python_out={temp_dir}',
                    f'--proto_path={proto_dir}',
                    self.proto_file_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"Failed to compile proto: {result.stderr}")

                # Import compiled proto module
                proto_name = os.path.splitext(proto_file)[0]
                py_file = os.path.join(temp_dir, f"{proto_name}_pb2.py")

                spec = importlib.util.spec_from_file_location(f"{proto_name}_pb2", py_file)
                proto_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(proto_module)

                # Get the specific message class
                if hasattr(proto_module, self.message_type):
                    self.message_class = getattr(proto_module, self.message_type)
                    logger.info(f"Loaded message class: {self.message_type}")
                else:
                    available_classes = [attr for attr in dir(proto_module) 
                                       if isinstance(getattr(proto_module, attr), type) 
                                       and issubclass(getattr(proto_module, attr), Message)]
                    raise ValueError(f"Message type '{self.message_type}' not found. Available: {available_classes}")

        except Exception as e:
            logger.error(f"Failed to load protobuf definition: {e}")
            raise

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