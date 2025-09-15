import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import './App.css';

// Components
import GrpcIntegration from './components/GrpcIntegration';

// Shadcn UI components
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Input } from './components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { ScrollArea } from './components/ui/scroll-area';
import { Separator } from './components/ui/separator';
import { Alert, AlertDescription } from './components/ui/alert';
import { Checkbox } from './components/ui/checkbox';
import { toast } from 'sonner';
import { Toaster } from './components/ui/sonner';

// Icons
import { Search, Activity, Network as NetworkIcon, Settings, Play, Pause, RotateCcw, Server } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  // State management
  const [traces, setTraces] = useState([]);
  const [selectedTrace, setSelectedTrace] = useState(null);
  const [traceFlow, setTraceFlow] = useState(null);
  const [topicGraph, setTopicGraph] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [availableTopics, setAvailableTopics] = useState([]);
  const [monitoredTopics, setMonitoredTopics] = useState([]);
  const [expandedMessages, setExpandedMessages] = useState(new Set());

  // Network instances
  const [topicNetwork, setTopicNetwork] = useState(null);
  const [flowNetwork, setFlowNetwork] = useState(null);

  // WebSocket connection
  const [websocket, setWebsocket] = useState(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/ws`;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        toast.success('Connected to Kafka trace viewer');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        toast.error('Disconnected from server');
        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnected(false);
      };

      setWebsocket(ws);
    };

    connectWebSocket();

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []); // eslint-disable-line

  const handleWebSocketMessage = (data) => {
    if (data.type === 'trace_update') {
      // Refresh traces if new ones are available
      loadTraces();
    }
  };

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      await Promise.all([
        loadTraces(),
        loadTopicGraph(),
        loadTopics(),
        loadStatistics()
      ]);
    } catch (error) {
      console.error('Error loading initial data:', error);
      toast.error('Failed to load initial data');
    }
  };

  const loadTraces = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/traces`);
      setTraces(response.data.traces || []);
    } catch (error) {
      console.error('Error loading traces:', error);
      toast.error('Failed to load traces');
    }
  };

  const loadTopicGraph = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/topics/graph`);
      setTopicGraph(response.data);
      renderTopicGraph(response.data);
    } catch (error) {
      console.error('Error loading topic graph:', error);
    }
  };

  const loadTopics = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/topics`);
      setAvailableTopics(response.data.all_topics || []);
      setMonitoredTopics(response.data.monitored_topics || []);
    } catch (error) {
      console.error('Error loading topics:', error);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/statistics`);
      setStatistics(response.data);
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  };

  const selectTrace = async (traceId) => {
    setLoading(true);
    try {
      const [traceResponse, flowResponse] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/trace/${traceId}`),
        axios.get(`${API_BASE_URL}/api/trace/${traceId}/flow`)
      ]);

      setSelectedTrace(traceResponse.data);
      setTraceFlow(flowResponse.data);
      renderTraceFlowGraph(flowResponse.data);
      setExpandedMessages(new Set()); // Reset expanded messages
    } catch (error) {
      console.error('Error loading trace details:', error);
      toast.error('Failed to load trace details');
    } finally {
      setLoading(false);
    }
  };

  const updateMonitoredTopics = async (newTopics) => {
    try {
      await axios.post(`${API_BASE_URL}/api/topics/monitor`, newTopics);
      setMonitoredTopics(newTopics);
      toast.success(`Now monitoring ${newTopics.length} topics`);
      // Reload data to reflect changes
      loadTraces();
      loadTopicGraph();
    } catch (error) {
      console.error('Error updating monitored topics:', error);
      toast.error('Failed to update monitored topics');
    }
  };

  const renderTopicGraph = (graphData) => {
    const container = document.getElementById('topic-graph');
    if (!container || !graphData) return;

    // Clear previous network
    if (topicNetwork) {
      topicNetwork.destroy();
    }

    try {
      const nodes = new DataSet(graphData.nodes.map(node => ({
        id: node.id,
        label: node.label,
        shape: 'box',
        color: {
          background: node.monitored ? '#10b981' : '#6b7280',
          border: node.monitored ? '#059669' : '#4b5563'
        },
        font: { color: 'white', size: 12 },
        margin: 10
      })));

      const edges = new DataSet(graphData.edges.map((edge, index) => ({
        id: `edge_${index}`,
        from: edge.source,
        to: edge.target,
        arrows: { to: { enabled: true, scaleFactor: 1 } },
        color: { color: '#6b7280' },
        width: Math.max(2, edge.flow_count || 2),
        smooth: { type: 'curvedCW', roundness: 0.2 }
      })));

      const data = { nodes, edges };
      
      // Check if graph has multiple components
      const components = findGraphComponents(graphData);
      
      const options = {
        layout: components.length > 1 ? {
          // Use force-directed layout for multiple components
          improvedLayout: true,
          hierarchical: false
        } : {
          // Use hierarchical layout for single component
          hierarchical: {
            enabled: true,
            direction: 'UD',
            sortMethod: 'directed',
            nodeSpacing: 200,
            levelSeparation: 150
          }
        },
        physics: {
          enabled: components.length > 1,
          stabilization: { iterations: 100 }
        },
        interaction: { 
          dragNodes: true, 
          zoomView: true,
          selectConnectedEdges: false
        },
        nodes: {
          borderWidth: 2,
          shadow: true
        },
        edges: {
          shadow: true,
          smooth: true
        }
      };

      const network = new Network(container, data, options);
      setTopicNetwork(network);

      // Add click handlers
      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          console.log(`Clicked on topic: ${nodeId}`);
        }
      });

    } catch (error) {
      console.error('Error rendering topic graph:', error);
    }
  };

  const findGraphComponents = (graphData) => {
    // Simple component detection
    const visited = new Set();
    const components = [];
    
    const dfs = (nodeId, component) => {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);
      component.push(nodeId);
      
      // Find connected nodes
      graphData.edges.forEach(edge => {
        if (edge.source === nodeId && !visited.has(edge.target)) {
          dfs(edge.target, component);
        }
        if (edge.target === nodeId && !visited.has(edge.source)) {
          dfs(edge.source, component);
        }
      });
    };
    
    graphData.nodes.forEach(node => {
      if (!visited.has(node.id)) {
        const component = [];
        dfs(node.id, component);
        components.push(component);
      }
    });
    
    return components;
  };

  const renderTraceFlowGraph = (flowData) => {
    const container = document.getElementById('trace-flow-graph');
    if (!container || !flowData) return;

    // Clear previous network
    if (flowNetwork) {
      flowNetwork.destroy();
    }

    try {
      const nodes = new DataSet(flowData.nodes.map(node => ({
        id: node.id,
        label: node.label,
        shape: 'box',
        color: {
          background: '#3b82f6',
          border: '#1d4ed8'
        },
        font: { color: 'white', size: 12 },
        margin: 10
      })));

      const edges = new DataSet(flowData.edges.map((edge, index) => ({
        id: `flow_edge_${index}`,
        from: edge.source,
        to: edge.target,
        arrows: { to: { enabled: true, scaleFactor: 1 } },
        color: { color: '#10b981' },
        width: Math.max(3, edge.message_count || 3),
        smooth: { type: 'curvedCW', roundness: 0.1 }
      })));

      const data = { nodes, edges };
      const options = {
        layout: {
          hierarchical: {
            enabled: true,
            direction: 'LR',
            sortMethod: 'directed',
            nodeSpacing: 150,
            levelSeparation: 200
          }
        },
        physics: { enabled: false },
        interaction: { 
          dragNodes: true, 
          zoomView: true 
        },
        nodes: {
          borderWidth: 2,
          shadow: true
        },
        edges: {
          shadow: true,
          smooth: true
        }
      };

      const network = new Network(container, data, options);
      setFlowNetwork(network);

    } catch (error) {
      console.error('Error rendering trace flow graph:', error);
    }
  };

  const toggleMessage = (index) => {
    setExpandedMessages(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const expandAllMessages = () => {
    if (selectedTrace?.messages) {
      setExpandedMessages(new Set(Array.from({ length: selectedTrace.messages.length }, (_, i) => i)));
    }
  };

  const collapseAllMessages = () => {
    setExpandedMessages(new Set());
  };

  const filteredTraces = traces.filter(trace =>
    trace.trace_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (ms) => {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <NetworkIcon className="h-8 w-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-gray-900">Kafka Trace Viewer</h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-sm text-gray-600">
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              {statistics && (
                <Badge variant="secondary">
                  {statistics.traces.total} traces
                </Badge>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-full mx-auto p-4">
        <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
          {/* Sidebar */}
          <div className="xl:col-span-1">
            <Tabs defaultValue="traces" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="traces">Traces</TabsTrigger>
                <TabsTrigger value="topics">Topics</TabsTrigger>
                <TabsTrigger value="graph">Graph</TabsTrigger>
              </TabsList>

              <TabsContent value="traces" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Available Traces</CardTitle>
                    <CardDescription>
                      Select a trace to view its message flow
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="relative">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                        <Input
                          placeholder="Search traces..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          className="pl-10"
                        />
                      </div>

                      <div className="h-96 overflow-y-auto message-scroll">
                        <div className="space-y-2 p-1">
                          {filteredTraces.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                              <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                              <p>No traces available</p>
                              <p className="text-xs mt-1">Check your topic monitoring settings</p>
                            </div>
                          ) : (
                            filteredTraces.map((trace) => (
                              <Card
                                key={trace.trace_id}
                                className={`cursor-pointer transition-all duration-200 hover:shadow-md message-card ${
                                  selectedTrace?.trace_id === trace.trace_id 
                                    ? 'ring-2 ring-blue-500 bg-blue-50' 
                                    : 'hover:bg-slate-50'
                                }`}
                                onClick={() => selectTrace(trace.trace_id)}
                              >
                                <CardContent className="p-4">
                                  <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                      <div className="font-medium text-sm font-mono">
                                        {trace.trace_id}
                                      </div>
                                      {trace.duration_ms && (
                                        <Badge variant="secondary" className="text-xs">
                                          {formatDuration(trace.duration_ms)}
                                        </Badge>
                                      )}
                                    </div>
                                    
                                    <div className="flex flex-wrap gap-1">
                                      {trace.topics.map((topic) => (
                                        <Badge key={topic} variant="outline" className="text-xs">
                                          {topic}
                                        </Badge>
                                      ))}
                                    </div>
                                    
                                    <div className="flex items-center justify-between text-xs text-gray-500">
                                      <span>{trace.message_count} messages</span>
                                      {trace.start_time && (
                                        <span>{formatTime(trace.start_time)}</span>
                                      )}
                                    </div>
                                  </div>
                                </CardContent>
                              </Card>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="topics" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Topic Monitoring</CardTitle>
                    <CardDescription>
                      Select which topics to monitor for traces
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Select All/None Buttons */}
                      <div className="flex gap-2">
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => updateMonitoredTopics(availableTopics)}
                        >
                          Select All
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => updateMonitoredTopics([])}
                        >
                          Select None
                        </Button>
                      </div>
                      
                      <div className="space-y-2">
                        {availableTopics.map((topic) => (
                          <div key={topic} className="flex items-center space-x-2">
                            <Checkbox
                              id={topic}
                              checked={monitoredTopics.includes(topic)}
                              onCheckedChange={(checked) => {
                                const newTopics = checked
                                  ? [...monitoredTopics, topic]
                                  : monitoredTopics.filter(t => t !== topic);
                                updateMonitoredTopics(newTopics);
                              }}
                            />
                            <label htmlFor={topic} className="text-sm font-medium">
                              {topic}
                            </label>
                          </div>
                        ))}
                      </div>

                      <Separator />

                      <div className="text-sm text-gray-600">
                        Monitoring {monitoredTopics.length} of {availableTopics.length} topics
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="graph" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Topic Graph Visualization</CardTitle>
                    <CardDescription>
                      Interactive network showing topic relationships and message flows
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div id="topic-graph" style={{ 
                        height: '400px',
                        width: '100%',
                        border: '2px solid #e2e8f0', 
                        borderRadius: '12px',
                        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)'
                      }} />
                      
                      {topicGraph && (
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div className="space-y-2">
                            <div className="font-medium text-gray-700">Graph Statistics</div>
                            <div className="text-gray-600">
                              {topicGraph.stats.topic_count} topics • {topicGraph.stats.edge_count} connections
                            </div>
                            <div className="text-gray-600">
                              {topicGraph.stats.monitored_count} monitored topics
                            </div>
                          </div>
                          <div className="space-y-2">
                            <div className="font-medium text-gray-700">Legend</div>
                            <div className="flex items-center space-x-4">
                              <div className="flex items-center space-x-2">
                                <div className="w-3 h-3 bg-green-500 rounded"></div>
                                <span className="text-xs">Monitored</span>
                              </div>
                              <div className="flex items-center space-x-2">
                                <div className="w-3 h-3 bg-gray-500 rounded"></div>
                                <span className="text-xs">Not Monitored</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                      
                      <div className="text-xs text-gray-500 bg-blue-50 p-2 rounded">
                        💡 Tip: Drag nodes to rearrange the graph. Multiple disconnected components may be shown if topics aren't all connected.
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </div>

          {/* Main Content */}
          <div className="xl:col-span-3">
            {selectedTrace ? (
              <div className="space-y-6">
                {/* Trace Header */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-xl">{selectedTrace.trace_id}</CardTitle>
                        <CardDescription>
                          Trace details and message flow
                        </CardDescription>
                      </div>
                      <div className="flex space-x-2">
                        <Badge variant="secondary">
                          {selectedTrace.message_count} messages
                        </Badge>
                        <Badge variant="secondary">
                          {selectedTrace.topics.length} topics
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                </Card>

                {/* Flow Visualization - Enhanced */}
                {traceFlow && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-xl">Message Flow Visualization</CardTitle>
                      <CardDescription>
                        Interactive trace showing how messages flow through topics over time
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div id="trace-flow-graph" style={{ 
                          height: '450px',
                          width: '100%',
                          border: '2px solid #e2e8f0', 
                          borderRadius: '12px',
                          background: 'linear-gradient(135deg, #fefefe 0%, #f0f9ff 100%)'
                        }} />
                        
                        {traceFlow.stats && (
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-blue-50 rounded-lg">
                            <div className="text-center">
                              <div className="text-2xl font-bold text-blue-600">
                                {formatDuration(traceFlow.stats.duration_ms)}
                              </div>
                              <div className="text-sm text-gray-600">Total Duration</div>
                            </div>
                            <div className="text-center">
                              <div className="text-2xl font-bold text-green-600">
                                {traceFlow.stats.total_messages}
                              </div>
                              <div className="text-sm text-gray-600">Messages</div>
                            </div>
                            <div className="text-center">
                              <div className="text-2xl font-bold text-purple-600">
                                {traceFlow.stats.topic_count}
                              </div>
                              <div className="text-sm text-gray-600">Topics</div>
                            </div>
                          </div>
                        )}
                        
                        <div className="text-xs text-gray-500 bg-amber-50 p-2 rounded">
                          💡 This shows the actual path messages took through your topic graph for this specific trace.
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Message Timeline - Enhanced for Better Readability */}
                <Card className="min-h-0 flex flex-col">
                  <CardHeader className="flex-shrink-0">
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-xl">Message Timeline</CardTitle>
                        <CardDescription>
                          Chronological view of all messages in this trace
                        </CardDescription>
                      </div>
                      <div className="flex space-x-2">
                        <Button size="sm" variant="outline" onClick={expandAllMessages}>
                          Expand All
                        </Button>
                        <Button size="sm" variant="outline" onClick={collapseAllMessages}>
                          Collapse All
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="flex-1 min-h-0 p-0">
                    <div className="h-[600px] overflow-y-auto p-4">
                      <div className="space-y-3">
                        {selectedTrace.messages.map((message, index) => (
                          <Card key={index} className="border border-slate-200 shadow-sm">
                            <CardContent className="p-0">
                              {/* Message Header - Always Visible */}
                              <div
                                className="p-4 cursor-pointer hover:bg-slate-50 transition-colors border-b border-slate-100"
                                onClick={() => toggleMessage(index)}
                              >
                                <div className="flex items-start justify-between">
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center space-x-2 mb-2">
                                      <Badge variant="outline" className="text-xs font-mono">
                                        {message.topic}
                                      </Badge>
                                      <span className="text-xs text-gray-500">
                                        [{message.partition}]:{message.offset}
                                      </span>
                                    </div>
                                    <div className="text-sm text-gray-600">
                                      <div className="flex items-center space-x-4">
                                        <span>{formatTime(message.timestamp)}</span>
                                        {message.trace_id && (
                                          <Badge variant="secondary" className="text-xs">
                                            {message.trace_id}
                                          </Badge>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex-shrink-0 ml-4">
                                    <div className="text-gray-400 text-lg">
                                      {expandedMessages.has(index) ? '▼' : '▶'}
                                    </div>
                                  </div>
                                </div>
                              </div>

                              {/* Expanded Message Content */}
                              {expandedMessages.has(index) && (
                                <div className="bg-slate-50">
                                  <div className="p-4 space-y-4">
                                    {/* Metadata Grid */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                                      <div className="space-y-2">
                                        <div className="font-semibold text-gray-700">Message Info</div>
                                        <div><span className="font-medium">Key:</span> {message.key || '(null)'}</div>
                                        <div><span className="font-medium">Partition:</span> {message.partition}</div>
                                        <div><span className="font-medium">Offset:</span> {message.offset}</div>
                                      </div>
                                      <div className="space-y-2">
                                        <div className="font-semibold text-gray-700">Timing</div>
                                        <div><span className="font-medium">Timestamp:</span> {formatTime(message.timestamp)}</div>
                                        <div><span className="font-medium">Topic:</span> {message.topic}</div>
                                      </div>
                                      <div className="space-y-2">
                                        <div className="font-semibold text-gray-700">Tracing</div>
                                        <div><span className="font-medium">Trace ID:</span> {message.trace_id || '(none)'}</div>
                                      </div>
                                    </div>

                                    {/* Headers Section */}
                                    {message.headers && Object.keys(message.headers).length > 0 && (
                                      <div>
                                        <div className="flex items-center space-x-2 mb-2">
                                          <h4 className="font-semibold text-gray-700">Headers</h4>
                                          <Badge variant="outline" className="text-xs">
                                            {Object.keys(message.headers).length} items
                                          </Badge>
                                        </div>
                                        <div className="bg-white p-3 rounded border">
                                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                            {Object.entries(message.headers).map(([key, value]) => (
                                              <div key={key} className="text-sm flex items-start">
                                                <span className="font-medium text-blue-600 mr-2 flex-shrink-0">{key}:</span>
                                                <span className="text-gray-700 break-all">{value}</span>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      </div>
                                    )}

                                    {/* Decoded Message - Priority Focus */}
                                    {message.decoded_value && (
                                      <div>
                                        <div className="flex items-center space-x-2 mb-2">
                                          <h4 className="font-semibold text-gray-700">Decoded Message</h4>
                                          <Button 
                                            size="sm" 
                                            variant="outline"
                                            onClick={() => {
                                              navigator.clipboard.writeText(JSON.stringify(message.decoded_value, null, 2));
                                              toast.success('Message copied to clipboard');
                                            }}
                                          >
                                            Copy JSON
                                          </Button>
                                        </div>
                                        <div className="bg-white border rounded-lg overflow-hidden">
                                          <div className="max-h-96 overflow-auto">
                                            <pre className="p-4 text-sm font-mono leading-relaxed whitespace-pre-wrap break-words">
                                              {JSON.stringify(message.decoded_value, null, 2)}
                                            </pre>
                                          </div>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card className="h-96 flex items-center justify-center">
                <CardContent className="text-center">
                  <Activity className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    Welcome to Kafka Trace Viewer
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Select a trace from the sidebar to view its message flow and details
                  </p>
                  <div className="text-sm text-gray-500">
                    <div>• Traces are automatically collected as messages arrive</div>
                    <div>• Click on a trace ID to view its details</div>
                    <div>• Use the topic monitoring tab to select which topics to trace</div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
      <Toaster />
    </div>
  );
}

export default App;
