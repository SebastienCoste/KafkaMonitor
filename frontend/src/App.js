import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import './App.css';

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
import { Search, Activity, Network as NetworkIcon, Settings, Play, Pause, RotateCcw } from 'lucide-react';

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

    const nodes = new DataSet(graphData.nodes.map(node => ({
      id: node.id,
      label: node.label,
      shape: 'box',
      color: {
        background: node.monitored ? '#10b981' : '#6b7280',
        border: node.monitored ? '#059669' : '#4b5563'
      },
      font: { color: 'white', size: 12 }
    })));

    const edges = new DataSet(graphData.edges.map(edge => ({
      from: edge.source,
      to: edge.target,
      arrows: 'to',
      color: { color: '#6b7280' },
      width: Math.max(1, edge.flow_count || 1)
    })));

    const data = { nodes, edges };
    const options = {
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'UD',
          sortMethod: 'directed'
        }
      },
      physics: { enabled: false },
      interaction: { dragNodes: false, zoomView: true }
    };

    const network = new Network(container, data, options);
    setTopicNetwork(network);
  };

  const renderTraceFlowGraph = (flowData) => {
    const container = document.getElementById('trace-flow-graph');
    if (!container || !flowData) return;

    const nodes = new DataSet(flowData.nodes.map(node => ({
      id: node.id,
      label: node.label,
      shape: 'box',
      color: {
        background: '#3b82f6',
        border: '#1d4ed8'
      },
      font: { color: 'white', size: 12 }
    })));

    const edges = new DataSet(flowData.edges.map((edge, index) => ({
      id: index,
      from: edge.source,
      to: edge.target,
      arrows: 'to',
      color: { color: '#10b981' },
      width: Math.max(2, edge.message_count || 2)
    })));

    const data = { nodes, edges };
    const options = {
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'LR',
          sortMethod: 'directed'
        }
      },
      physics: { enabled: false }
    };

    const network = new Network(container, data, options);
    setFlowNetwork(network);
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

                      <ScrollArea className="h-96">
                        <div className="space-y-2">
                          {filteredTraces.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                              <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                              <p>No traces available</p>
                            </div>
                          ) : (
                            filteredTraces.map((trace) => (
                              <Card
                                key={trace.trace_id}
                                className={`cursor-pointer transition-colors hover:bg-slate-50 ${
                                  selectedTrace?.trace_id === trace.trace_id ? 'ring-2 ring-blue-500' : ''
                                }`}
                                onClick={() => selectTrace(trace.trace_id)}
                              >
                                <CardContent className="p-3">
                                  <div className="font-medium text-sm mb-1">
                                    {trace.trace_id}
                                  </div>
                                  <div className="flex flex-wrap gap-1 mb-2">
                                    {trace.topics.map((topic) => (
                                      <Badge key={topic} variant="outline" className="text-xs">
                                        {topic}
                                      </Badge>
                                    ))}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {trace.message_count} messages
                                    {trace.duration_ms && (
                                      <> • {formatDuration(trace.duration_ms)}</>
                                    )}
                                    {trace.start_time && (
                                      <> • {formatTime(trace.start_time)}</>
                                    )}
                                  </div>
                                </CardContent>
                              </Card>
                            ))
                          )}
                        </div>
                      </ScrollArea>
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
                    <CardTitle className="text-lg">Topic Graph</CardTitle>
                    <CardDescription>
                      Visualizes topic relationships
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div id="topic-graph" style={{ height: '300px', border: '1px solid #e5e7eb', borderRadius: '6px' }} />
                    {topicGraph && (
                      <div className="mt-4 text-sm text-gray-600">
                        {topicGraph.stats.topic_count} topics • {topicGraph.stats.edge_count} connections
                      </div>
                    )}
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

                {/* Flow Visualization */}
                {traceFlow && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Message Flow</CardTitle>
                      <CardDescription>
                        Visual representation of message flow through topics
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div id="trace-flow-graph" style={{ height: '400px', border: '1px solid #e5e7eb', borderRadius: '6px' }} />
                      {traceFlow.stats && (
                        <div className="mt-4 text-sm text-gray-600">
                          Duration: {formatDuration(traceFlow.stats.duration_ms)} • 
                          {traceFlow.stats.total_messages} messages across {traceFlow.stats.topic_count} topics
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Message Timeline */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle>Message Timeline</CardTitle>
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
                  <CardContent>
                    <ScrollArea className="h-96">
                      <div className="space-y-2">
                        {selectedTrace.messages.map((message, index) => (
                          <Card key={index} className="border border-slate-200">
                            <CardContent className="p-0">
                              <div
                                className="p-4 cursor-pointer hover:bg-slate-50 transition-colors"
                                onClick={() => toggleMessage(index)}
                              >
                                <div className="flex items-center justify-between">
                                  <div>
                                    <div className="font-medium">
                                      {message.topic}[{message.partition}]:{message.offset}
                                    </div>
                                    <div className="text-sm text-gray-500">
                                      {formatTime(message.timestamp)}
                                      {message.trace_id && <> • Trace: {message.trace_id}</>}
                                    </div>
                                  </div>
                                  <div className="text-gray-400">
                                    {expandedMessages.has(index) ? '▼' : '▶'}
                                  </div>
                                </div>
                              </div>

                              {expandedMessages.has(index) && (
                                <div className="border-t border-slate-200 p-4 bg-slate-50">
                                  <div className="space-y-3">
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                      <div><strong>Key:</strong> {message.key || '(null)'}</div>
                                      <div><strong>Partition:</strong> {message.partition}</div>
                                      <div><strong>Offset:</strong> {message.offset}</div>
                                      <div><strong>Timestamp:</strong> {formatTime(message.timestamp)}</div>
                                    </div>

                                    {message.headers && Object.keys(message.headers).length > 0 && (
                                      <div>
                                        <strong className="text-sm">Headers:</strong>
                                        <div className="mt-1 space-y-1">
                                          {Object.entries(message.headers).map(([key, value]) => (
                                            <div key={key} className="text-sm text-gray-600 ml-4">
                                              <strong>{key}:</strong> {value}
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {message.decoded_value && (
                                      <div>
                                        <strong className="text-sm">Decoded Message:</strong>
                                        <pre className="mt-1 text-xs bg-white p-3 rounded border overflow-x-auto">
                                          {JSON.stringify(message.decoded_value, null, 2)}
                                        </pre>
                                      </div>
                                    )}
                                  </div>
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </ScrollArea>
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
