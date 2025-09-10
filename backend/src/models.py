"""
Data models for the Kafka trace viewer application
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

@dataclass
class KafkaMessage:
    """Represents a decoded Kafka message"""
    topic: str
    partition: int
    offset: int
    key: Optional[str]
    timestamp: datetime
    headers: Dict[str, str]
    raw_value: bytes
    decoded_value: Dict[str, Any]
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'topic': self.topic,
            'partition': self.partition,
            'offset': self.offset,
            'key': self.key,
            'timestamp': self.timestamp.isoformat(),
            'headers': self.headers,
            'decoded_value': self.decoded_value,
            'trace_id': self.trace_id
        }

@dataclass
class TraceInfo:
    """Represents a complete trace with all its messages"""
    trace_id: str
    messages: List[KafkaMessage] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def add_message(self, message: KafkaMessage):
        """Add a message to this trace"""
        self.messages.append(message)
        if message.topic not in self.topics:
            self.topics.append(message.topic)

        # Update time bounds
        if self.start_time is None or message.timestamp < self.start_time:
            self.start_time = message.timestamp
        if self.end_time is None or message.timestamp > self.end_time:
            self.end_time = message.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'trace_id': self.trace_id,
            'message_count': len(self.messages),
            'topics': self.topics,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'messages': [msg.to_dict() for msg in self.messages]
        }

@dataclass
class TopicEdge:
    """Represents a connection between two topics"""
    source: str
    destination: str

@dataclass
class TopicGraph:
    """Represents the complete topic graph"""
    edges: List[TopicEdge] = field(default_factory=list)

    def add_edge(self, source: str, destination: str):
        """Add an edge to the graph"""
        edge = TopicEdge(source, destination)
        if edge not in self.edges:
            self.edges.append(edge)

    def get_destinations(self, source: str) -> List[str]:
        """Get all destination topics for a source topic"""
        return [edge.destination for edge in self.edges if edge.source == source]

    def get_sources(self, destination: str) -> List[str]:
        """Get all source topics for a destination topic"""
        return [edge.source for edge in self.edges if edge.destination == destination]

    def get_all_topics(self) -> List[str]:
        """Get all unique topics in the graph"""
        topics = set()
        for edge in self.edges:
            topics.add(edge.source)
            topics.add(edge.destination)
        return list(topics)

@dataclass
class TopicConfig:
    """Configuration for a single topic"""
    name: str
    proto_file: str
    message_type: str
    description: Optional[str] = None