"""
Main application entry point for Marauder's Map
"""
import asyncio
import logging
import yaml
import sys
from pathlib import Path
from src.kafka_consumer import KafkaConsumerService
from src.protobuf_decoder import ProtobufDecoder, MockProtobufDecoder
from src.graph_builder import TraceGraphBuilder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KafkaTraceViewerApp:
    """Main application orchestrator for standalone mode"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.kafka_consumer = None
        self.graph_builder = None
        self.decoder = None

        self._load_config()
        self._initialize_components()

    def _load_config(self):
        """Load application configuration"""
        try:
            # Load settings
            with open(self.config_dir / "settings.yaml", 'r') as f:
                self.settings = yaml.safe_load(f)

            # Load topics configuration
            with open(self.config_dir / "topics.yaml", 'r') as f:
                self.topics_config = yaml.safe_load(f)

            logger.info("Configuration loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

    def _initialize_components(self):
        """Initialize all application components"""
        try:
            # Check if we should use mock mode
            kafka_config_path = self.config_dir / "kafka.yaml"
            with open(kafka_config_path, 'r') as f:
                kafka_config = yaml.safe_load(f)

            # Initialize protobuf decoder
            proto_dir = self.config_dir / "proto"
            if kafka_config.get('mock_mode', True):
                self.decoder = MockProtobufDecoder()
                logger.info("Using mock protobuf decoder")
            else:
                if not proto_dir.exists():
                    raise FileNotFoundError(f"Proto directory not found: {proto_dir}")
                self.decoder = ProtobufDecoder(str(proto_dir))
                logger.info("Using real protobuf decoder")

            # Load protobuf definitions for each topic
            for topic_name, topic_config in self.topics_config.get('topics', {}).items():
                self.decoder.load_topic_protobuf(
                    topic_name,
                    topic_config['proto_file'],
                    topic_config['message_type']
                )

            # Initialize graph builder
            self.graph_builder = TraceGraphBuilder(
                topics_config_path=str(self.config_dir / "topics.yaml"),
                max_traces=self.settings.get('max_traces', 1000)
            )

            # Initialize Kafka consumer
            self.kafka_consumer = KafkaConsumerService(
                config_path=str(kafka_config_path),
                decoder=self.decoder,
                trace_header_field=self.settings.get('trace_header_field', 'traceparent')
            )

            # Register message handler
            self.kafka_consumer.add_message_handler(self.graph_builder.add_message)

            # Get topics from graph configuration
            topics = self.graph_builder.topic_graph.get_all_topics()
            self.kafka_consumer.subscribe_to_topics(topics)

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            sys.exit(1)

    async def start(self):
        """Start the application"""
        logger.info("Starting Marauder's Map (standalone mode)...")

        try:
            # Start Kafka consumer
            await self.kafka_consumer.start_consuming_async()

        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the application"""
        logger.info("Shutting down...")

        if self.kafka_consumer:
            self.kafka_consumer.stop_consuming()

        logger.info("Application shutdown complete")

def main():
    """Main entry point"""
    print("Marauder's Map - Standalone Consumer")
    print("This runs only the Kafka consumer for testing purposes.")
    print("Use the web server (server.py) for the full application.\n")

    app = KafkaTraceViewerApp()

    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()