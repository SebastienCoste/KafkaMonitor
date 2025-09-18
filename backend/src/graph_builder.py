"""
Topic graph builder and trace management with FIFO eviction
Enhanced for Phase 2: Multiple disconnected graphs, real-time statistics, trace age analysis
"""
import logging
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
import yaml
import numpy as np
from src.models import KafkaMessage, TraceInfo, TopicGraph

# Set up extensive logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TraceGraphBuilder:
    """Manages topic graph and trace collection with FIFO eviction"""

    def __init__(self, topics_config_path: str, max_traces: int = 1000, settings: dict = None):
        logger.info("🔄 Initializing TraceGraphBuilder")
        logger.info(f"📄 Topics config path: {topics_config_path}")
        logger.info(f"📊 Max traces: {max_traces}")
        
        self.topics_config_path = topics_config_path
        self.max_traces = max_traces
        self.settings = settings or {}
        self.topic_graph = TopicGraph()
        self.traces: Dict[str, TraceInfo] = {}
        self.trace_order = deque()  # For FIFO eviction
        self.monitored_topics: Set[str] = set()
        self._load_topic_graph()
        
        logger.info("✅ TraceGraphBuilder initialized successfully")

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
            
            # Check if we should activate all topics on startup (from settings.yaml)
            activate_all = self.settings.get('topic_monitoring', {}).get('activate_all_on_startup', True)
            
            if activate_all:
                # Monitor all configured topics
                all_topics = self.topic_graph.get_all_topics()
                self.monitored_topics = set(all_topics)
                logger.info(f"🔄 Activating all topics on startup: {self.monitored_topics}")
            else:
                # Use only default topics
                self.monitored_topics = set(default_topics)
                logger.info(f"📋 Using default monitored topics only: {self.monitored_topics}")

            logger.info(f"Loaded topic graph with {len(self.topic_graph.edges)} edges")
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
        trace_existed = message.trace_id in self.traces
        if not trace_existed:
            self._create_new_trace(message.trace_id)
        else:
            logger.debug(f"Adding to existing trace {message.trace_id}: {message.topic}")

        # Add message to trace
        trace = self.traces[message.trace_id]
        trace.add_message(message)

        if not trace_existed:
            logger.info(f"Created new trace: {message.trace_id}")
        
        logger.debug(f"Added message to trace {message.trace_id}: {message.topic}")

        # Update trace order for FIFO (always move to end when active)
        if message.trace_id in self.trace_order:
            self.trace_order.remove(message.trace_id)
        self.trace_order.append(message.trace_id)

        # Enforce max traces limit with improved logic
        self._enforce_trace_limit()

    def _create_new_trace(self, trace_id: str):
        """Create a new trace"""
        self.traces[trace_id] = TraceInfo(trace_id=trace_id)

    def _enforce_trace_limit(self):
        """Enforce maximum trace limit with intelligent eviction"""
        if len(self.traces) <= self.max_traces:
            return
            
        # Calculate how many traces to evict (evict in batches to avoid frequent evictions)
        traces_to_evict = min(100, len(self.traces) - self.max_traces)
        
        for _ in range(traces_to_evict):
            if len(self.trace_order) == 0:
                break
                
            oldest_trace_id = self.trace_order.popleft()
            if oldest_trace_id in self.traces:
                # Don't evict traces that have received messages in the last 30 seconds
                trace = self.traces[oldest_trace_id]
                if trace.messages:
                    latest_message_time = max(msg.timestamp for msg in trace.messages)
                    time_since_last_message = datetime.now() - latest_message_time
                    
                    if time_since_last_message.total_seconds() < 30:
                        # Put it back at the end and skip eviction
                        self.trace_order.append(oldest_trace_id)
                        continue
                
                del self.traces[oldest_trace_id]
                logger.debug(f"Evicted trace: {oldest_trace_id} (age: {time_since_last_message.total_seconds():.1f}s)")

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
        
        # Add detailed per-topic statistics
        stats['topics']['details'] = {}
        all_topics = self.topic_graph.get_all_topics()
        now = datetime.now()
        
        for topic in all_topics:
            topic_traces = []
            topic_message_count = stats['messages']['by_topic'].get(topic, 0)
            
            # Find traces that contain messages from this topic
            for trace_id, trace in self.traces.items():
                if any(msg.topic == topic for msg in trace.messages):
                    topic_traces.append(trace_id)
            
            # Calculate comprehensive topic statistics
            topic_stats = self._calculate_topic_statistics(topic, now)
            
            stats['topics']['details'][topic] = {
                'message_count': topic_message_count,
                'trace_count': len(topic_traces),
                'monitored': topic in self.monitored_topics,
                'status': 'Receiving messages' if topic_message_count > 0 else 'No messages',
                'traces': topic_traces,
                # P10/P50/P95 metrics in milliseconds
                'message_age_p10_ms': round(topic_stats['trace_age_p10'] * 1000, 2),
                'message_age_p50_ms': round(topic_stats['trace_age_p50'] * 1000, 2), 
                'message_age_p95_ms': round(topic_stats['trace_age_p95'] * 1000, 2),
                # Messages per minute rates
                'messages_per_minute_total': round(topic_stats['rate_total'], 2),
                'messages_per_minute_rolling': round(topic_stats['rate_rolling_60s'], 2),
                # Slowest traces for this topic
                'slowest_traces': topic_stats['slowest_traces']
            }
        
        if earliest_time:
            stats['time_range']['earliest'] = earliest_time.isoformat()
        if latest_time:
            stats['time_range']['latest'] = latest_time.isoformat()

        return stats

    # Phase 2: Enhanced Graph Visualization Methods
    
    def get_disconnected_graphs(self) -> List[Dict[str, Any]]:
        """Get all disconnected graph components, ordered by size"""
        logger.info("🔄 Building disconnected graph components...")
        
        # Find all connected components using DFS
        all_topics = set(self.topic_graph.get_all_topics())
        visited = set()
        components = []
        
        def dfs(topic: str, component: Set[str]):
            if topic in visited:
                return
            visited.add(topic)
            component.add(topic)
            
            # Find connected topics through edges
            for edge in self.topic_graph.edges:
                if edge.source == topic and edge.destination not in visited:
                    dfs(edge.destination, component)
                elif edge.destination == topic and edge.source not in visited:
                    dfs(edge.source, component)
        
        # Build components
        for topic in all_topics:
            if topic not in visited:
                component = set()
                dfs(topic, component)
                if component:
                    components.append(component)
        
        # Sort components by size (largest first)
        components.sort(key=len, reverse=True)
        
        # Build graph data for each component
        graph_components = []
        for i, component in enumerate(components):
            component_data = self._build_component_graph_data(component, i)
            graph_components.append(component_data)
        
        logger.info(f"✅ Found {len(graph_components)} disconnected graph components")
        return graph_components
    
    def _build_component_graph_data(self, component_topics: Set[str], component_index: int) -> Dict[str, Any]:
        """Build graph data for a single component"""
        nodes = []
        edges = []
        now = datetime.now()
        
        # Build nodes with enhanced statistics
        for topic in component_topics:
            node_stats = self._calculate_topic_statistics(topic, now)
            
            nodes.append({
                'id': topic,
                'label': f"{topic}\n{node_stats['message_count']} msgs\n{node_stats['rate']:.1f}/min",
                'type': 'topic',
                'component': component_index,
                'monitored': topic in self.monitored_topics,
                'statistics': node_stats,
                'color': self._get_node_color_by_age(node_stats['median_trace_age']),
                'size': max(20, min(80, node_stats['message_count'] / 10))  # Size based on message count
            })
        
        # Build edges within this component
        for edge in self.topic_graph.edges:
            if edge.source in component_topics and edge.destination in component_topics:
                edge_stats = self._calculate_edge_statistics(edge.source, edge.destination)
                
                edges.append({
                    'source': edge.source,
                    'target': edge.destination,
                    'type': 'flow',
                    'component': component_index,
                    'flow_count': edge_stats['flow_count'],
                    'message_rate': edge_stats['message_rate'],
                    'width': max(2, min(10, edge_stats['flow_count'] / 5))  # Width based on flow
                })
        
        # Calculate component statistics
        component_stats = self._calculate_component_statistics(component_topics, now)
        
        return {
            'component_id': component_index,
            'topics': list(component_topics),
            'topic_count': len(component_topics),
            'nodes': nodes,
            'edges': edges,
            'statistics': component_stats,
            'layout_type': 'hierarchical' if len(component_topics) > 10 else 'force_directed'
        }
    
    def _calculate_topic_statistics(self, topic: str, now: datetime) -> Dict[str, Any]:
        """Calculate comprehensive statistics for a topic"""
        messages = []
        trace_ages = []
        trace_slowest_data = []  # For tracking slowest traces
        
        # Collect all messages for this topic and trace timing data
        for trace_id, trace in self.traces.items():
            trace_messages_for_topic = []
            for msg in trace.messages:
                if msg.topic == topic:
                    messages.append(msg)
                    trace_messages_for_topic.append(msg)
            
            # Calculate trace timing metrics if this trace has messages for this topic
            if trace_messages_for_topic and trace.messages:
                # Find the oldest message in the entire trace (start of trace)
                oldest_message_time = min(msg.timestamp for msg in trace.messages)
                
                # Find when trace first reached this topic
                first_topic_message = min(trace_messages_for_topic, key=lambda m: m.timestamp)
                time_to_topic = (first_topic_message.timestamp - oldest_message_time).total_seconds()
                
                # Calculate total trace duration
                newest_message_time = max(msg.timestamp for msg in trace.messages)
                total_trace_duration = (newest_message_time - oldest_message_time).total_seconds()
                
                # Only include traces where time_to_topic > 0 (i.e., this topic wasn't the starting topic)
                # OR if time_to_topic is 0 but there are multiple topics, use the time within the topic
                if time_to_topic == 0 and len(trace.topics) > 1:
                    # If this is the starting topic, calculate internal processing time
                    if len(trace_messages_for_topic) > 1:
                        # Use the time between first and last message in this topic as processing time
                        last_topic_message = max(trace_messages_for_topic, key=lambda m: m.timestamp)
                        time_to_topic = (last_topic_message.timestamp - first_topic_message.timestamp).total_seconds()
                elif time_to_topic == 0 and len(trace.topics) == 1:
                    # If this is the only topic in the trace, use total processing time within topic
                    if len(trace_messages_for_topic) > 1:
                        last_topic_message = max(trace_messages_for_topic, key=lambda m: m.timestamp)
                        time_to_topic = (last_topic_message.timestamp - first_topic_message.timestamp).total_seconds()
                    else:
                        # Single message in single topic - use a small default time to avoid 0ms
                        time_to_topic = 0.001  # 1ms minimum
                
                # Store data for slowest traces calculation
                trace_slowest_data.append({
                    'trace_id': trace_id,
                    'time_to_topic': time_to_topic,
                    'total_duration': total_trace_duration
                })
                
                # For age percentile calculation - use time from start to each message in this topic
                for msg in trace_messages_for_topic:
                    age_seconds = (msg.timestamp - oldest_message_time).total_seconds()
                    trace_ages.append(age_seconds)
        
        if not messages:
            return {
                'message_count': 0,
                'rate_total': 0.0,
                'rate_rolling_60s': 0.0,
                'median_trace_age': 0,
                'trace_age_p10': 0,
                'trace_age_p50': 0,
                'trace_age_p95': 0,
                'last_message_time': None,
                'slowest_traces': []
            }
        
        # Sort messages by timestamp for rate calculations
        messages.sort(key=lambda m: m.timestamp)
        
        # Calculate total message rate (messages per minute over entire time span)
        rate_total = 0.0
        if len(messages) > 1:
            time_span_minutes = (messages[-1].timestamp - messages[0].timestamp).total_seconds() / 60
            rate_total = len(messages) / max(time_span_minutes, 1)  # Avoid division by zero
        
        # Calculate rolling 60-second message rate
        rate_rolling_60s = 0.0
        sixty_seconds_ago = now - timedelta(seconds=60)
        recent_messages = [msg for msg in messages if msg.timestamp >= sixty_seconds_ago]
        if recent_messages:
            # Messages per minute in the last 60 seconds
            rate_rolling_60s = len(recent_messages)  # Already per minute since we're looking at 60 seconds
        
        # Calculate trace age percentiles
        if trace_ages:
            p10 = np.percentile(trace_ages, 10)
            p50 = np.percentile(trace_ages, 50)  # median
            p95 = np.percentile(trace_ages, 95)
        else:
            p10 = p50 = p95 = 0
        
        # Find the 3 slowest traces (by time to reach this topic)
        slowest_traces = sorted(trace_slowest_data, key=lambda x: x['time_to_topic'], reverse=True)[:3]
        
        return {
            'message_count': len(messages),
            'rate_total': rate_total,
            'rate_rolling_60s': rate_rolling_60s,
            'median_trace_age': p50,
            'trace_age_p10': p10,
            'trace_age_p50': p50,
            'trace_age_p95': p95,
            'last_message_time': messages[-1].timestamp.isoformat() if messages else None,
            'slowest_traces': slowest_traces
        }
    
    def _calculate_edge_statistics(self, source_topic: str, dest_topic: str) -> Dict[str, Any]:
        """Calculate statistics for an edge between two topics"""
        flow_count = 0
        message_times = []
        
        for trace in self.traces.values():
            source_messages = [msg for msg in trace.messages if msg.topic == source_topic]
            dest_messages = [msg for msg in trace.messages if msg.topic == dest_topic]
            
            if source_messages and dest_messages:
                flow_count += 1
                message_times.extend([msg.timestamp for msg in source_messages + dest_messages])
        
        # Calculate message rate for this edge
        if len(message_times) > 1:
            message_times.sort()
            time_span = (message_times[-1] - message_times[0]).total_seconds() / 60
            message_rate = len(message_times) / max(time_span, 1)
        else:
            message_rate = 0.0
        
        return {
            'flow_count': flow_count,
            'message_rate': message_rate
        }
    
    def _calculate_component_statistics(self, component_topics: Set[str], now: datetime) -> Dict[str, Any]:
        """Calculate statistics for an entire component"""
        total_messages = 0
        all_trace_ages = []
        active_traces = 0
        
        for trace in self.traces.values():
            component_messages = [msg for msg in trace.messages if msg.topic in component_topics]
            if component_messages:
                total_messages += len(component_messages)
                active_traces += 1
                
                # Calculate trace age based on message timestamps within the trace
                if trace.messages:
                    # Find the oldest message in the entire trace (start of trace)
                    oldest_message_time = min(msg.timestamp for msg in trace.messages)
                    
                    # For component messages, calculate age from trace start
                    for msg in component_messages:
                        age_seconds = (msg.timestamp - oldest_message_time).total_seconds()
                        all_trace_ages.append(age_seconds)
        
        # Calculate overall statistics
        if all_trace_ages:
            median_age = np.percentile(all_trace_ages, 50)
            p95_age = np.percentile(all_trace_ages, 95)
        else:
            median_age = p95_age = 0
        
        return {
            'total_messages': total_messages,
            'active_traces': active_traces,
            'median_trace_age': median_age,
            'p95_trace_age': p95_age,
            'health_score': self._calculate_health_score(median_age, total_messages)
        }
    
    def _get_node_color_by_age(self, median_age_seconds: float) -> Dict[str, str]:
        """Get node color based on median trace age"""
        if median_age_seconds < 30:  # Less than 30 seconds - green (newest)
            return {
                'background': '#10b981',  # green-500
                'border': '#059669'       # green-600
            }
        elif median_age_seconds < 300:  # Less than 5 minutes - orange (mid-age)
            return {
                'background': '#f59e0b',  # amber-500
                'border': '#d97706'       # amber-600
            }
        else:  # Older than 5 minutes - red (old)
            return {
                'background': '#ef4444',  # red-500
                'border': '#dc2626'       # red-600
            }
    
    def _calculate_health_score(self, median_age: float, message_count: int) -> float:
        """Calculate a health score for the component (0-100)"""
        # Factor in trace age (newer is better) and message activity
        age_score = max(0, 100 - (median_age / 60))  # Decrease score as age increases
        activity_score = min(100, message_count / 10)  # Up to 100 for 1000+ messages
        
        return (age_score * 0.7 + activity_score * 0.3)  # Weighted average
    
    def get_filtered_graph_data(self, time_filter: str = "all", custom_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Get graph data with time-based filtering"""
        logger.info(f"🔄 Applying time filter: {time_filter}")
        
        # Determine filter datetime
        now = datetime.now()
        if time_filter == "all":
            filter_time = None
        elif time_filter == "last_hour":
            filter_time = now - timedelta(hours=1)
        elif time_filter == "last_30min":
            filter_time = now - timedelta(minutes=30)
        elif time_filter == "last_15min":
            filter_time = now - timedelta(minutes=15)
        elif time_filter == "last_5min":
            filter_time = now - timedelta(minutes=5)
        elif time_filter == "custom" and custom_minutes:
            filter_time = now - timedelta(minutes=custom_minutes)
        else:
            filter_time = now - timedelta(hours=24)  # Default to last 24 hours
        
        # Filter traces based on time
        filtered_traces = {}
        if filter_time:
            for trace_id, trace in self.traces.items():
                if trace.start_time and trace.start_time >= filter_time:
                    filtered_traces[trace_id] = trace
        else:
            filtered_traces = self.traces
        
        # Temporarily replace traces for calculation
        original_traces = self.traces
        self.traces = filtered_traces
        
        try:
            # Get disconnected graphs with filtered data
            disconnected_graphs = self.get_disconnected_graphs()
            
            # Calculate overall filtered statistics
            filtered_stats = {
                'total_traces': len(filtered_traces),
                'total_messages': sum(len(trace.messages) for trace in filtered_traces.values()),
                'time_filter': time_filter,
                'filter_start': filter_time.isoformat() if filter_time else None,
                'components_count': len(disconnected_graphs)
            }
            
            return {
                'disconnected_graphs': disconnected_graphs,
                'statistics': filtered_stats,
                'filter_applied': time_filter
            }
            
        finally:
            # Restore original traces
            self.traces = original_traces