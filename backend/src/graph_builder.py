"""
Topic graph builder and trace management with FIFO eviction
"""
import logging
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
import yaml
from src.models import KafkaMessage, TraceInfo, TopicGraph, TopicEdge

logger = logging.getLogger(__name__)

class TraceGraphBuilder:
    """Manages topic graph and trace collection with FIFO eviction"""

    def __init__(self, topics_config_path: str, max_traces: int = 1000):
        self.topics_config_path = topics_config_path
        self.max_traces = max_traces
        self.topic_graph = TopicGraph()
        self.traces: Dict[str, TraceInfo] = {}
        self.trace_order = deque()  # For FIFO eviction
        self.monitored_topics: Set[str] = set()
        self._load_topic_graph()

    def _load_topic_graph(self):
        """Load topic graph configuration"""
        try:
            with open(self.topics_config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Load topic edges
            for edge_config in config.get('topic_edges', []):
                source = edge_config['source']
                destination = edge_config['destination']
                self.topic_graph.add_edge(source, destination)

            # Load default monitored topics
            default_topics = config.get('default_monitored_topics', [])
            self.monitored_topics = set(default_topics)

            logger.info(f"Loaded topic graph with {len(self.topic_graph.edges)} edges")
            logger.info(f"Default monitored topics: {self.monitored_topics}")
            logger.debug(f"All topics in graph: {self.topic_graph.get_all_topics()}")

        except Exception as e:
            logger.error(f"Failed to load topic graph: {e}")
            raise

    def set_monitored_topics(self, topics: List[str]):
        """Set which topics to monitor for traces"""
        available_topics = set(self.topic_graph.get_all_topics())
        valid_topics = [t for t in topics if t in available_topics]
        invalid_topics = [t for t in topics if t not in available_topics]
        
        if invalid_topics:
            logger.warning(f"Invalid topics ignored: {invalid_topics}")
            
        self.monitored_topics = set(valid_topics)
        logger.info(f"Updated monitored topics: {self.monitored_topics}")

    def get_monitored_topics(self) -> List[str]:
        """Get currently monitored topics"""
        return list(self.monitored_topics)

    def add_message(self, message: KafkaMessage):
        """Add a message to the appropriate trace"""
        # Only process messages from monitored topics
        if message.topic not in self.monitored_topics:
            logger.debug(f"Ignoring message from non-monitored topic: {message.topic}")
            return

        if not message.trace_id:
            logger.debug(f"Message without trace ID: {message.topic}[{message.partition}]:{message.offset}")
            return

        # Get or create trace
        if message.trace_id not in self.traces:
            self._create_new_trace(message.trace_id)

        # Add message to trace
        trace = self.traces[message.trace_id]
        trace.add_message(message)

        logger.debug(f"Added message to trace {message.trace_id}: {message.topic}")

        # Update trace order for FIFO
        if message.trace_id in self.trace_order:
            self.trace_order.remove(message.trace_id)
        self.trace_order.append(message.trace_id)

        # Enforce max traces limit
        self._enforce_trace_limit()

    def _create_new_trace(self, trace_id: str):
        """Create a new trace"""
        self.traces[trace_id] = TraceInfo(trace_id=trace_id)
        logger.info(f"Created new trace: {trace_id}")

    def _enforce_trace_limit(self):
        """Enforce maximum trace limit with FIFO eviction"""
        while len(self.traces) > self.max_traces:
            oldest_trace_id = self.trace_order.popleft()
            if oldest_trace_id in self.traces:
                del self.traces[oldest_trace_id]
                logger.debug(f"Evicted trace: {oldest_trace_id}")

    def get_trace(self, trace_id: str) -> Optional[TraceInfo]:
        """Get trace by ID"""
        return self.traces.get(trace_id)

    def get_all_trace_ids(self) -> List[str]:
        """Get all available trace IDs"""
        return list(self.traces.keys())

    def get_trace_summary(self) -> Dict[str, Any]:
        """Get summary of all traces"""
        summary = {
            'total_traces': len(self.traces),
            'max_traces': self.max_traces,
            'monitored_topics': list(self.monitored_topics),
            'traces': []
        }

        # Sort traces by most recent first
        sorted_traces = sorted(
            self.traces.items(),
            key=lambda x: x[1].end_time or x[1].start_time or datetime.min,
            reverse=True
        )

        for trace_id, trace in sorted_traces:
            summary['traces'].append({
                'trace_id': trace_id,
                'message_count': len(trace.messages),
                'topics': trace.topics,
                'start_time': trace.start_time.isoformat() if trace.start_time else None,
                'end_time': trace.end_time.isoformat() if trace.end_time else None,
                'duration_ms': self._calculate_duration(trace)
            })

        return summary

    def _calculate_duration(self, trace: TraceInfo) -> Optional[int]:
        """Calculate trace duration in milliseconds"""
        if trace.start_time and trace.end_time:
            return int((trace.end_time - trace.start_time).total_seconds() * 1000)
        return None

    def get_topic_graph_data(self) -> Dict[str, Any]:
        """Get topic graph data for visualization"""
        nodes = []
        edges = []

        # Create nodes for all topics
        all_topics = self.topic_graph.get_all_topics()
        for topic in all_topics:
            # Count messages in this topic
            message_count = sum(
                len([msg for msg in trace.messages if msg.topic == topic])
                for trace in self.traces.values()
            )
            
            nodes.append({
                'id': topic,
                'label': f"{topic}\n({message_count} msgs)",
                'type': 'topic',
                'message_count': message_count,
                'monitored': topic in self.monitored_topics
            })

        # Create edges
        for edge in self.topic_graph.edges:
            # Count flow through this edge
            flow_count = self._count_edge_flow(edge.source, edge.destination)
            
            edges.append({
                'source': edge.source,
                'target': edge.destination,
                'type': 'flow',
                'flow_count': flow_count
            })

        return {
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'topic_count': len(all_topics),
                'edge_count': len(edges),
                'monitored_count': len(self.monitored_topics)
            }
        }

    def _count_edge_flow(self, source: str, destination: str) -> int:
        """Count message flow between two topics across all traces"""
        flow_count = 0
        for trace in self.traces.values():
            source_messages = [msg for msg in trace.messages if msg.topic == source]
            dest_messages = [msg for msg in trace.messages if msg.topic == destination]
            
            # Simple heuristic: if both topics have messages, count as flow
            if source_messages and dest_messages:
                flow_count += min(len(source_messages), len(dest_messages))
                
        return flow_count

    def get_trace_flow_data(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace flow data for visualization"""
        trace = self.get_trace(trace_id)
        if not trace:
            return None

        # Build trace-specific flow
        nodes = []
        edges = []

        # Group messages by topic
        topic_messages = defaultdict(list)
        for msg in trace.messages:
            topic_messages[msg.topic].append(msg)

        # Create nodes for topics in this trace
        for topic in trace.topics:
            messages = topic_messages[topic]
            nodes.append({
                'id': topic,
                'label': f"{topic}\n({len(messages)} msgs)",
                'type': 'topic',
                'message_count': len(messages),
                'messages': [msg.to_dict() for msg in messages[:5]]  # Limit to first 5 for performance
            })

        # Create edges based on message flow and topic graph
        message_flow = self._analyze_message_flow(trace)
        for source, destination, count in message_flow:
            edges.append({
                'source': source,
                'target': destination,
                'type': 'trace_flow',
                'message_count': count
            })

        return {
            'trace_id': trace_id,
            'nodes': nodes,
            'edges': edges,
            'timeline': [msg.to_dict() for msg in sorted(trace.messages, key=lambda m: m.timestamp)],
            'stats': {
                'total_messages': len(trace.messages),
                'topic_count': len(trace.topics),
                'duration_ms': self._calculate_duration(trace)
            }
        }

    def _analyze_message_flow(self, trace: TraceInfo) -> List[tuple]:
        """Analyze message flow within a trace"""
        # Sort messages by timestamp
        sorted_messages = sorted(trace.messages, key=lambda m: m.timestamp)

        flow_counts = defaultdict(int)
        topic_sequence = []

        # Build sequence of topics by timestamp
        for msg in sorted_messages:
            topic_sequence.append(msg.topic)

        # Count transitions between consecutive topics
        for i in range(len(topic_sequence) - 1):
            current_topic = topic_sequence[i]
            next_topic = topic_sequence[i + 1]
            
            # Only count if there's a defined edge in topic graph
            if next_topic in self.topic_graph.get_destinations(current_topic):
                flow_counts[(current_topic, next_topic)] += 1

        # Convert to list of tuples (source, destination, count)
        return [(source, dest, count) for (source, dest), count in flow_counts.items()]

    def cleanup_old_traces(self, max_age_hours: int = 24):
        """Clean up traces older than specified age"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        to_remove = []
        for trace_id, trace in self.traces.items():
            if trace.end_time and trace.end_time < cutoff_time:
                to_remove.append(trace_id)

        for trace_id in to_remove:
            del self.traces[trace_id]
            if trace_id in self.trace_order:
                self.trace_order.remove(trace_id)

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old traces")

        return len(to_remove)

    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics about traces and topics"""
        stats = {
            'traces': {
                'total': len(self.traces),
                'max_capacity': self.max_traces,
                'utilization': len(self.traces) / self.max_traces if self.max_traces > 0 else 0
            },
            'topics': {
                'total': len(self.topic_graph.get_all_topics()),
                'monitored': len(self.monitored_topics),
                'with_messages': 0
            },
            'messages': {
                'total': 0,
                'by_topic': {}
            },
            'time_range': {
                'earliest': None,
                'latest': None
            }
        }

        # Calculate message statistics
        earliest_time = None
        latest_time = None
        topics_with_messages = set()

        for trace in self.traces.values():
            stats['messages']['total'] += len(trace.messages)
            
            for msg in trace.messages:
                topics_with_messages.add(msg.topic)
                
                # Update message counts by topic
                if msg.topic not in stats['messages']['by_topic']:
                    stats['messages']['by_topic'][msg.topic] = 0
                stats['messages']['by_topic'][msg.topic] += 1
                
                # Update time range
                if earliest_time is None or msg.timestamp < earliest_time:
                    earliest_time = msg.timestamp
                if latest_time is None or msg.timestamp > latest_time:
                    latest_time = msg.timestamp

        stats['topics']['with_messages'] = len(topics_with_messages)
        
        if earliest_time:
            stats['time_range']['earliest'] = earliest_time.isoformat()
        if latest_time:
            stats['time_range']['latest'] = latest_time.isoformat()

        return stats