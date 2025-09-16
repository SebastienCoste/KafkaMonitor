"""
Mock Graph Generator for Testing Disconnected Graphs

Generates mock topic graphs with multiple disconnected components,
including cyclic loops, for testing the enhanced graph visualization.
"""
import logging
import random
import string
import json
from typing import Dict, List, Set, Tuple
from datetime import datetime, timedelta
from src.models import KafkaMessage, TraceInfo

logger = logging.getLogger(__name__)

class MockGraphGenerator:
    """Generates mock graph data for testing disconnected graph visualization"""
    
    def __init__(self):
        self.component_templates = [
            # Component 1: User flow with retry loop
            {
                'topics': ['user-registration', 'email-verification', 'user-activation', 'notification-sent'],
                'edges': [
                    ('user-registration', 'email-verification'),
                    ('email-verification', 'user-activation'),
                    ('user-activation', 'notification-sent'),
                    ('notification-sent', 'email-verification')  # Retry loop
                ]
            },
            # Component 2: Payment processing with error handling
            {
                'topics': ['payment-request', 'payment-validation', 'payment-processed', 'payment-failed', 'retry-payment'],
                'edges': [
                    ('payment-request', 'payment-validation'),
                    ('payment-validation', 'payment-processed'),
                    ('payment-validation', 'payment-failed'),
                    ('payment-failed', 'retry-payment'),
                    ('retry-payment', 'payment-validation')  # Retry loop
                ]
            },
            # Component 3: Content processing pipeline
            {
                'topics': ['content-upload', 'content-analysis', 'content-approved', 'content-published'],
                'edges': [
                    ('content-upload', 'content-analysis'),
                    ('content-analysis', 'content-approved'),
                    ('content-approved', 'content-published')
                ]
            },
            # Component 4: Analytics and monitoring (isolated)
            {
                'topics': ['metrics-collection', 'data-aggregation', 'report-generation'],
                'edges': [
                    ('metrics-collection', 'data-aggregation'),
                    ('data-aggregation', 'report-generation'),
                    ('report-generation', 'metrics-collection')  # Cyclic for continuous monitoring
                ]
            },
            # Component 5: Order fulfillment with complex loops
            {
                'topics': ['order-placed', 'inventory-check', 'payment-capture', 'shipping-label', 'order-shipped', 'delivery-confirmation'],
                'edges': [
                    ('order-placed', 'inventory-check'),
                    ('inventory-check', 'payment-capture'),
                    ('payment-capture', 'shipping-label'),
                    ('shipping-label', 'order-shipped'),
                    ('order-shipped', 'delivery-confirmation'),
                    ('inventory-check', 'order-placed'),  # Stock reorder loop
                    ('delivery-confirmation', 'inventory-check')  # Restock trigger
                ]
            },
            # Component 6: Simple isolated component
            {
                'topics': ['system-health', 'alert-trigger'],
                'edges': [
                    ('system-health', 'alert-trigger'),
                    ('alert-trigger', 'system-health')  # Health check loop
                ]
            }
        ]
    
    def generate_mock_topic_graph_config(self, num_components: int = None) -> Dict[str, any]:
        """Generate a mock topic configuration with disconnected components"""
        if num_components is None:
            num_components = random.randint(3, len(self.component_templates))
        
        # Select random components
        selected_components = random.sample(self.component_templates, min(num_components, len(self.component_templates)))
        
        # Build configuration
        topics = {}
        topic_edges = []
        all_topics = set()
        
        for i, component in enumerate(selected_components):
            # Add topics from this component
            for topic in component['topics']:
                # Make topic names unique across components
                unique_topic = f"{topic}"
                all_topics.add(unique_topic)
                
                topics[unique_topic] = {
                    'proto_file': f"mock_{topic.replace('-', '_')}.proto",
                    'message_type': f"Mock{self._to_camel_case(topic)}Event",
                    'description': f"Mock {topic.replace('-', ' ')} events for component {i+1}",
                    'component': i
                }
            
            # Add edges from this component
            for source, destination in component['edges']:
                topic_edges.append({
                    'source': source,
                    'destination': destination,
                    'component': i
                })
        
        # Add some default monitored topics
        monitored_topics = list(all_topics)[:max(1, len(all_topics) // 2)]
        
        config = {
            'topics': topics,
            'topic_edges': topic_edges,
            'default_monitored_topics': monitored_topics,
            'components_info': {
                'total_components': len(selected_components),
                'component_sizes': [len(comp['topics']) for comp in selected_components]
            }
        }
        
        logger.info(f"✅ Generated mock topic graph with {num_components} components and {len(all_topics)} topics")
        return config
    
    def generate_mock_traces_with_age_variation(self, topic_graph, num_traces: int = 50) -> Dict[str, TraceInfo]:
        """Generate mock traces with varying ages for testing color coding"""
        traces = {}
        now = datetime.now()
        all_topics = list(topic_graph.get_all_topics())
        
        logger.info(f"🎲 Generating {num_traces} mock traces with age variation...")
        
        for i in range(num_traces):
            trace_id = f"mock-trace-{i:03d}"
            
            # Create trace with random age (0 seconds to 2 hours old)
            age_seconds = random.uniform(0, 7200)  # 0 to 2 hours
            start_time = now - timedelta(seconds=age_seconds)
            end_time = start_time + timedelta(seconds=random.uniform(1, 300))  # 1s to 5min duration
            
            trace = TraceInfo(trace_id=trace_id)
            trace.start_time = start_time
            trace.end_time = end_time
            
            # Generate messages for this trace
            num_messages = random.randint(1, 10)
            selected_topics = random.sample(all_topics, min(num_messages, len(all_topics)))
            
            for j, topic in enumerate(selected_topics):
                msg_time = start_time + timedelta(seconds=j * random.uniform(1, 30))
                
                # Create mock message
                mock_value = self._generate_mock_message_value(topic)
                message = KafkaMessage(
                    topic=topic,
                    partition=random.randint(0, 2),
                    offset=random.randint(1000, 9999),
                    key=f"key-{i}-{j}",
                    raw_value=mock_value,
                    decoded_value=json.loads(mock_value.decode('utf-8')),
                    headers={'trace_id': trace_id, 'component': f"comp-{random.randint(0, 3)}"},
                    timestamp=msg_time,
                    trace_id=trace_id
                )
                
                trace.add_message(message)
            
            traces[trace_id] = trace
        
        logger.info(f"✅ Generated {len(traces)} mock traces")
        return traces
    
    def _generate_mock_message_value(self, topic: str) -> bytes:
        """Generate mock message value based on topic"""
        mock_data = {
            'event_type': topic,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'id': ''.join(random.choices(string.ascii_letters + string.digits, k=8)),
                'value': random.randint(1, 1000),
                'status': random.choice(['pending', 'processing', 'completed', 'failed'])
            }
        }
        
        # Convert to bytes (simplified JSON)
        import json
        return json.dumps(mock_data).encode('utf-8')
    
    def _to_camel_case(self, snake_str: str) -> str:
        """Convert snake_case to CamelCase"""
        components = snake_str.replace('-', '_').split('_')
        return ''.join(word.capitalize() for word in components)
    
    def apply_mock_configuration(self, graph_builder) -> None:
        """Apply mock configuration to a graph builder instance"""
        logger.info("🔧 Applying mock graph configuration...")
        
        # Generate mock config
        mock_config = self.generate_mock_topic_graph_config(num_components=4)
        
        # Clear existing configuration
        graph_builder.topic_graph.edges.clear()
        
        # Apply new edges
        for edge_config in mock_config['topic_edges']:
            graph_builder.topic_graph.add_edge(edge_config['source'], edge_config['destination'])
        
        # Set monitored topics
        graph_builder.monitored_topics = set(mock_config['default_monitored_topics'])
        
        # Generate and apply mock traces
        mock_traces = self.generate_mock_traces_with_age_variation(graph_builder.topic_graph, num_traces=75)
        
        # Clear existing traces and add mock ones
        graph_builder.traces.clear()
        graph_builder.trace_order.clear()
        
        for trace_id, trace in mock_traces.items():
            graph_builder.traces[trace_id] = trace
            graph_builder.trace_order.append(trace_id)
        
        logger.info(f"✅ Applied mock configuration: {len(mock_config['topic_edges'])} edges, {len(mock_traces)} traces")
        logger.info(f"📊 Components: {mock_config['components_info']['component_sizes']}")
    
    def generate_cyclic_component(self, size: int = 5) -> Dict[str, any]:
        """Generate a single component with guaranteed cyclic loops"""
        topics = []
        edges = []
        
        # Create topics
        for i in range(size):
            topics.append(f"cyclic-node-{i}")
        
        # Create a cycle
        for i in range(size):
            next_i = (i + 1) % size
            edges.append((topics[i], topics[next_i]))
        
        # Add some cross-connections for complexity
        if size > 3:
            edges.append((topics[0], topics[size // 2]))
            edges.append((topics[size // 2], topics[-1]))
        
        return {
            'topics': topics,
            'edges': edges,
            'type': 'cyclic',
            'size': size
        }