"""
Kafka consumer implementation with SASL/SCRAM authentication and mock support
"""
import asyncio
import logging
import random
import time
import traceback
import os
from typing import Dict, List, Callable, Optional
from confluent_kafka import Consumer, KafkaError, KafkaException
import yaml
from datetime import datetime
from src.models import KafkaMessage
from src.protobuf_decoder import ProtobufDecoder, MockProtobufDecoder

# Set up extensive logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class KafkaConsumerService:
    """Kafka consumer with SASL/SCRAM authentication and mock support"""

    def __init__(self, config_path: str, decoder: ProtobufDecoder, trace_header_field: str):
        logger.info(f"🔄 Initializing KafkaConsumerService")
        logger.info(f"📄 Config path: {config_path}")
        logger.info(f"🎯 Trace header field: {trace_header_field}")
        logger.info(f"🔧 Decoder type: {type(decoder).__name__}")
        
        self.config_path = config_path
        self.decoder = decoder
        self.trace_header_field = trace_header_field
        self.consumer = None
        self.running = False
        self.mock_mode = False
        self.message_handlers: List[Callable[[KafkaMessage], None]] = []
        self.subscribed_topics = []
        self._load_config()
        
        logger.info(f"✅ KafkaConsumerService initialized successfully")

    def _load_config(self):
        """Load Kafka configuration from YAML file and environment variables"""
        logger.info(f"🔄 Loading Kafka configuration from: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.debug(f"📋 Raw config loaded: {config}")
            
            self.mock_mode = config.get('mock_mode', False)
            logger.info(f"🎭 Mock mode: {self.mock_mode}")
            
            if not self.mock_mode:
                # Override config with environment variables if available
                bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', config.get('bootstrap_servers', 'localhost:9092'))
                username = os.getenv('KAFKA_USERNAME', config.get('sasl_username', ''))
                password = os.getenv('KAFKA_PASSWORD', config.get('sasl_password', ''))
                security_protocol = os.getenv('KAFKA_SECURITY_PROTOCOL', config.get('security_protocol', 'PLAINTEXT'))
                sasl_mechanism = os.getenv('KAFKA_SASL_MECHANISM', config.get('sasl_mechanism', ''))
                
                # Build confluent-kafka consumer config for real Kafka
                self.kafka_config = {
                    'bootstrap.servers': bootstrap_servers,
                    'group.id': config.get('group_id', 'kafka-trace-viewer'),
                    'auto.offset.reset': config.get('auto_offset_reset', 'latest'),
                    'enable.auto.commit': config.get('enable_auto_commit', True),
                    'session.timeout.ms': config.get('session_timeout_ms', 6000),
                    'heartbeat.interval.ms': config.get('heartbeat_interval_ms', 3000),
                }
                
                # Add security configuration only if credentials are provided
                if security_protocol and security_protocol != 'PLAINTEXT':
                    self.kafka_config['security.protocol'] = security_protocol
                    
                    if sasl_mechanism:
                        self.kafka_config['sasl.mechanism'] = sasl_mechanism
                    
                    if username:
                        self.kafka_config['sasl.username'] = username
                    
                    if password:
                        self.kafka_config['sasl.password'] = password
                
                logger.info(f"🔗 Loaded Kafka config for {bootstrap_servers}")
                logger.info(f"🔧 Security protocol: {security_protocol}")
                logger.debug(f"🔧 Kafka config (credentials hidden): {dict((k, '***' if 'password' in k.lower() else v) for k, v in self.kafka_config.items())}")
            else:
                logger.info("🎭 Running in mock mode - will generate fake messages")
                
        except Exception as e:
            logger.error(f"💥 Failed to load Kafka configuration: {str(e)}")
            logger.error(f"🔴 Error type: {type(e).__name__}")
            logger.error(f"🔴 Traceback: {traceback.format_exc()}")
            raise

    def add_message_handler(self, handler: Callable[[KafkaMessage], None]):
        """Add a message handler callback"""
        self.message_handlers.append(handler)

    def subscribe_to_topics(self, topics: List[str]):
        """Subscribe to specified topics with graceful handling of missing topics"""
        self.subscribed_topics = topics
        self._original_topics = topics.copy()  # Store original list for retrying later
        
        if not self.mock_mode:
            try:
                self.consumer = Consumer(self.kafka_config)
                
                # Try to subscribe to all topics first
                self.consumer.subscribe(topics)
                logger.info(f"✅ Successfully subscribed to topics: {topics}")
                
                # Verify topics exist by getting metadata (with timeout)
                try:
                    metadata = self.consumer.list_topics(timeout=5.0)
    def refresh_topic_subscription(self):
        """Refresh topic subscription to pick up newly created topics"""
        if self.mock_mode or not self.consumer:
            return
            
        try:
            # Get current metadata to see if new topics are available
            metadata = self.consumer.list_topics(timeout=5.0)
            existing_topics = set(metadata.topics.keys())
            
            # Find topics from our original list that now exist
            originally_requested = getattr(self, '_original_topics', self.subscribed_topics)
            newly_available = [topic for topic in originally_requested if topic in existing_topics and topic not in self.subscribed_topics]
            
            if newly_available:
                # Add newly available topics to subscription
                updated_topics = self.subscribed_topics + newly_available
                self.consumer.subscribe(updated_topics)
                self.subscribed_topics = updated_topics
                logger.info(f"✅ Added newly available topics: {newly_available}")
                logger.info(f"📡 Now subscribed to: {updated_topics}")
                
        except Exception as e:
            logger.warning(f"⚠️  Error refreshing topic subscription: {e}")
    
    def get_subscription_status(self):
        """Get current subscription status and topic availability"""
        if self.mock_mode:
            return {
                'mode': 'mock',
                'subscribed_topics': self.subscribed_topics,
                'status': 'All topics available in mock mode'
            }
            
        if not self.consumer:
            return {
                'mode': 'real',
                'subscribed_topics': [],
                'status': 'Consumer not initialized'
            }
            
        try:
            metadata = self.consumer.list_topics(timeout=5.0)
            existing_topics = set(metadata.topics.keys())
            
            return {
                'mode': 'real',
                'subscribed_topics': self.subscribed_topics,
                'existing_topics': list(existing_topics),
                'missing_topics': [topic for topic in getattr(self, '_original_topics', self.subscribed_topics) if topic not in existing_topics],
                'status': f'Subscribed to {len(self.subscribed_topics)} topics'
            }
        except Exception as e:
            return {
                'mode': 'real',
                'subscribed_topics': self.subscribed_topics,
                'status': f'Error getting topic info: {e}'
            }
                    existing_topics = set(metadata.topics.keys())
                    missing_topics = [topic for topic in topics if topic not in existing_topics]
                    
                    if missing_topics:
                        logger.warning(f"⚠️  Topics not found on broker: {missing_topics}")
                        logger.info(f"📋 Available topics on broker: {list(existing_topics)}")
                        
                        # Filter to only existing topics
                        valid_topics = [topic for topic in topics if topic in existing_topics]
                        
                        if valid_topics:
                            # Re-subscribe to only valid topics
                            self.consumer.subscribe(valid_topics)
                            self.subscribed_topics = valid_topics
                            logger.info(f"✅ Re-subscribed to existing topics only: {valid_topics}")
                        else:
                            logger.warning("⚠️  No valid topics found - consumer will be in standby mode")
                            self.subscribed_topics = []
                    else:
                        logger.info(f"✅ All topics exist on broker: {topics}")
                        
                except Exception as metadata_error:
                    logger.warning(f"⚠️  Could not verify topic existence: {metadata_error}")
                    logger.info("📡 Proceeding with subscription - will handle missing topics during consumption")
                    
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to topics: {e}")
                # Don't raise the exception - allow system to continue in mock mode
                logger.warning("🔄 Switching to mock mode due to subscription failure")
                self.mock_mode = True
                self.subscribed_topics = topics
        else:
            logger.info(f"🎭 Mock mode: Would subscribe to topics: {topics}")

    def start_consuming(self):
        """Start consuming messages"""
        self.running = True
        logger.info("Starting message consumption...")

        if self.mock_mode:
            self._start_mock_consuming()
        else:
            self._start_real_consuming()

    def _start_real_consuming(self):
        """Start consuming from real Kafka"""
        if not self.consumer:
            raise RuntimeError("Consumer not initialized. Call subscribe_to_topics first.")

        # Topic refresh counter
        poll_count = 0
        topic_refresh_interval = 300  # Refresh every 5 minutes (300 polls of 1 second each)

        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    # Periodically check for new topics
                    poll_count += 1
                    if poll_count >= topic_refresh_interval:
                        self.refresh_topic_subscription()
                        poll_count = 0
                    continue

                if msg.error():
                    error_code = msg.error().code()
                    error_msg = str(msg.error())
                    
                    if error_code == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition {msg.topic()}[{msg.partition()}]")
                    elif error_code == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        # Handle unknown topic or partition error gracefully
                        logger.warning(f"⚠️  Topic/partition not available: {error_msg}")
                        logger.info("💡 This is expected when topics are configured but not yet created on the broker")
                        # Don't log this as an error repeatedly - it's handled gracefully
                    elif "Unknown topic" in error_msg or "topic not available" in error_msg.lower():
                        # Handle various forms of topic not found errors
                        logger.warning(f"⚠️  Topic availability issue: {error_msg}")
                        logger.info("💡 Continuing consumption - this topic may be created later")
                    else:
                        logger.error(f"❌ Consumer error: {error_msg}")
                    continue

                # Process message
                try:
                    kafka_msg = self._process_message(msg)
                    if kafka_msg:
                        # Call all registered handlers
                        for handler in self.message_handlers:
                            handler(kafka_msg)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            self.stop_consuming()

    def _start_mock_consuming(self):
        """Start consuming mock messages"""
        trace_counter = 1
        message_counter = 1
        
        try:
            while self.running:
                # Generate mock messages for each subscribed topic
                for topic in self.subscribed_topics:
                    if not self.running:
                        break
                        
                    # Create mock message
                    kafka_msg = self._create_mock_message(topic, trace_counter, message_counter)
                    
                    # Call all registered handlers
                    for handler in self.message_handlers:
                        try:
                            handler(kafka_msg)
                        except Exception as e:
                            logger.error(f"Error in message handler: {e}")
                    
                    message_counter += 1
                    
                # Increment trace occasionally
                if random.random() < 0.3:  # 30% chance to start new trace
                    trace_counter += 1
                    
                # Sleep between messages
                time.sleep(2.0 + random.uniform(-0.5, 1.0))  # 1.5-3 seconds
                
        except KeyboardInterrupt:
            logger.info("Mock consumer interrupted")
        finally:
            logger.info("Mock consumer stopped")

    def _create_mock_message(self, topic: str, trace_id: int, message_id: int) -> KafkaMessage:
        """Create a mock Kafka message"""
        # Generate mock message bytes (in real scenario this would be protobuf)
        mock_bytes = f"mock_message_{message_id}_{topic}".encode('utf-8')
        
        # Decode using mock decoder
        try:
            decoded_value = self.decoder.decode_message(topic, mock_bytes)
        except Exception as e:
            logger.error(f"Mock decode error: {e}")
            decoded_value = {"error": str(e)}
        
        # Update trace_id in decoded value to match our pattern
        current_trace_id = f"trace-{trace_id:03d}"
        if isinstance(decoded_value, dict) and 'trace_id' in decoded_value:
            decoded_value['trace_id'] = current_trace_id
        
        # Extract trace ID
        trace_id_value = None
        if self.trace_header_field in decoded_value:
            trace_id_value = decoded_value[self.trace_header_field]
        
        return KafkaMessage(
            topic=topic,
            partition=random.randint(0, 2),
            offset=message_id,
            key=f"key-{message_id}",
            timestamp=datetime.now(),
            headers={self.trace_header_field: trace_id_value or current_trace_id},
            raw_value=mock_bytes,
            decoded_value=decoded_value,
            trace_id=trace_id_value or current_trace_id
        )

    def _process_message(self, msg) -> Optional[KafkaMessage]:
        """Process a single Kafka message"""
        try:
            # Extract headers
            headers = {}
            if msg.headers():
                headers = {k: v.decode('utf-8') if isinstance(v, bytes) else str(v)
                          for k, v in msg.headers()}

            # Decode protobuf message
            decoded_value = self.decoder.decode_message(msg.topic(), msg.value())

            # Extract trace ID from headers or decoded message
            trace_id = None
            if self.trace_header_field in headers:
                trace_id = headers[self.trace_header_field]
            elif self.trace_header_field in decoded_value:
                trace_id = decoded_value[self.trace_header_field]

            # Create KafkaMessage object
            kafka_msg = KafkaMessage(
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                key=msg.key().decode('utf-8') if msg.key() else None,
                timestamp=datetime.fromtimestamp(msg.timestamp()[1] / 1000.0),
                headers=headers,
                raw_value=msg.value(),
                decoded_value=decoded_value,
                trace_id=trace_id
            )

            logger.debug(f"Processed message: {kafka_msg.topic}[{kafka_msg.partition}]:{kafka_msg.offset}")
            return kafka_msg

        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            return None

    def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Consumer stopped")

    async def start_consuming_async(self):
        """Start consuming messages asynchronously"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.start_consuming)