"""
Environment Manager for Kafka Monitoring

Manages switching between different environments (DEV/TEST/INT/LOAD/PROD)
each with their own Kafka and gRPC configurations.
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.kafka_consumer import KafkaConsumerService
from src.graph_builder import TraceGraphBuilder
from src.protobuf_decoder import ProtobufDecoder

logger = logging.getLogger(__name__)

class EnvironmentManager:
    """Manages environment switching for Kafka monitoring"""
    
    def __init__(self, environments_dir: str, protobuf_decoder: ProtobufDecoder):
        self.environments_dir = Path(environments_dir)
        self.protobuf_decoder = protobuf_decoder
        self.current_environment = None
        self.current_config = None
        self.kafka_consumer = None
        self.graph_builder = None
        self.trace_header_field = "trace_id"  # Default trace header field
        
        logger.info(f"🌍 EnvironmentManager initialized with directory: {environments_dir}")
    
    def list_environments(self) -> List[str]:
        """Get list of available environments"""
        environments = []
        if self.environments_dir.exists():
            for env_file in self.environments_dir.glob("*.yaml"):
                environments.append(env_file.stem.upper())
        return sorted(environments)
    
    def get_current_environment(self) -> Dict[str, Any]:
        """Get current environment info"""
        return {
            'current_environment': self.current_environment,
            'available_environments': self.list_environments(),
            'kafka_connected': self.kafka_consumer is not None and self.kafka_consumer.running if self.kafka_consumer else False,
            'total_traces': len(self.graph_builder.traces) if self.graph_builder else 0
        }
    
    def switch_environment(self, environment: str) -> Dict[str, Any]:
        """Switch to a different environment"""
        logger.info(f"🔄 Switching to environment: {environment}")
        
        try:
            # Load environment configuration
            env_file = self.environments_dir / f"{environment.lower()}.yaml"
            if not env_file.exists():
                return {
                    'success': False,
                    'error': f'Environment configuration not found: {environment}'
                }
            
            with open(env_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Stop current services
            self._cleanup_current_environment()
            
            # Set new environment
            self.current_environment = environment
            self.current_config = config
            
            # Initialize new services
            result = self._initialize_services(config)
            
            if result['success']:
                logger.info(f"✅ Successfully switched to environment: {environment}")
                return {
                    'success': True,
                    'environment': environment,
                    'message': f'Switched to {environment} environment',
                    'kafka_config': {
                        'bootstrap_servers': config.get('kafka', {}).get('bootstrap_servers', 'N/A'),
                        'security_protocol': config.get('kafka', {}).get('security_protocol', 'N/A')
                    }
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"💥 Failed to switch environment: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to switch environment: {str(e)}'
            }
    
    def _cleanup_current_environment(self):
        """Clean up current environment services"""
        logger.info("🧹 Cleaning up current environment...")
        
        # Stop Kafka consumer
        if self.kafka_consumer:
            try:
                self.kafka_consumer.stop()
            except Exception as e:
                logger.warning(f"Error stopping Kafka consumer: {e}")
            self.kafka_consumer = None
        
        # Clear graph builder
        if self.graph_builder:
            self.graph_builder.traces.clear()
            self.graph_builder.trace_order.clear()
            self.graph_builder = None
    
    def _initialize_services(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize Kafka and graph services for the environment"""
        logger.info("🔧 Initializing services for new environment...")
        
        try:
            # Create temporary Kafka config file for this environment
            kafka_config = config.get('kafka', {})
            temp_config = {
                'bootstrap_servers': kafka_config.get('bootstrap_servers', 'localhost:9092'),
                'security_protocol': kafka_config.get('security_protocol', 'PLAINTEXT'),
                'sasl_mechanism': kafka_config.get('sasl_mechanism', ''),
                'username': kafka_config.get('username', ''),
                'password': kafka_config.get('password', ''),
                'group_id': f"kafka-trace-viewer-{self.current_environment.lower()}",
                'auto_offset_reset': 'latest'  # Always start from latest to avoid offset issues
            }
            
            # Initialize graph builder
            self.graph_builder = TraceGraphBuilder(
                topic_config_path="config/topics.yaml",
                trace_header_field=self.trace_header_field
            )
            
            # Initialize Kafka consumer with temporary config
            # We'll pass the config directly instead of using a file
            self.kafka_consumer = self._create_kafka_consumer_with_config(temp_config)
            
            # Set up message handling
            self.kafka_consumer.add_message_handler(self.graph_builder.add_message)
            
            # Subscribe to all topics
            all_topics = self.graph_builder.topic_graph.get_all_topics()
            self.kafka_consumer.subscribe_to_topics(all_topics)
            
            logger.info(f"✅ Services initialized for environment: {self.current_environment}")
            return {
                'success': True,
                'message': 'Services initialized successfully'
            }
            
        except Exception as e:
            logger.error(f"💥 Failed to initialize services: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to initialize services: {str(e)}'
            }
    
    def _create_kafka_consumer_with_config(self, kafka_config: Dict[str, Any]) -> KafkaConsumerService:
        """Create Kafka consumer with direct configuration"""
        # Create a temporary consumer that accepts config directly
        consumer = KafkaConsumerService.__new__(KafkaConsumerService)
        consumer.decoder = self.protobuf_decoder
        consumer.trace_header_field = self.trace_header_field
        consumer.consumer = None
        consumer.running = False
        consumer.mock_mode = False
        consumer.message_handlers = []
        consumer.subscribed_topics = []
        
        # Set Kafka config directly
        consumer.kafka_config = {
            'bootstrap.servers': kafka_config.get('bootstrap_servers', 'localhost:9092'),
            'group.id': kafka_config.get('group_id', 'kafka-trace-viewer'),
            'auto.offset.reset': kafka_config.get('auto_offset_reset', 'latest'),
            'enable.auto.commit': True,
            'session.timeout.ms': 6000,
            'heartbeat.interval.ms': 3000,
        }
        
        # Add security configuration if needed
        security_protocol = kafka_config.get('security_protocol', 'PLAINTEXT')
        if security_protocol and security_protocol != 'PLAINTEXT':
            consumer.kafka_config['security.protocol'] = security_protocol
            
            sasl_mechanism = kafka_config.get('sasl_mechanism')
            if sasl_mechanism:
                consumer.kafka_config['sasl.mechanism'] = sasl_mechanism
            
            username = kafka_config.get('username')
            password = kafka_config.get('password')
            if username and password:
                consumer.kafka_config['sasl.username'] = username
                consumer.kafka_config['sasl.password'] = password
        
        logger.info(f"📡 Kafka consumer configured for: {kafka_config.get('bootstrap_servers')}")
        return consumer
    
    def start_kafka_consumer(self):
        """Start the Kafka consumer for current environment"""
        if self.kafka_consumer:
            import asyncio
            asyncio.create_task(self.kafka_consumer.start_consuming_async())
            logger.info(f"🚀 Started Kafka consumer for environment: {self.current_environment}")
    
    def get_environment_config(self, environment: str = None) -> Dict[str, Any]:
        """Get configuration for a specific environment"""
        env = environment or self.current_environment
        if not env:
            return {'success': False, 'error': 'No environment specified'}
        
        try:
            env_file = self.environments_dir / f"{env.lower()}.yaml"
            if not env_file.exists():
                return {'success': False, 'error': f'Environment not found: {env}'}
            
            with open(env_file, 'r') as f:
                config = yaml.safe_load(f)
            
            return {
                'success': True,
                'environment': env,
                'config': config
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}