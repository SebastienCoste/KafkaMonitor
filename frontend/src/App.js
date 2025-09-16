import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import './App.css';

// Components
import GrpcIntegration from './components/GrpcIntegration';
import EnhancedGraphVisualization from './components/EnhancedGraphVisualization';

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
import { Search, Activity, Network as NetworkIcon, Settings, Play, Pause, RotateCcw, Server, RefreshCw } from 'lucide-react';

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
  const [currentPage, setCurrentPage] = useState('traces'); // New state for page navigation
  const [activeTab, setActiveTab] = useState('traces'); // New state for tracking active tab
  // Environment management
  const [environments, setEnvironments] = useState([]);
  const [currentEnvironment, setCurrentEnvironment] = useState('');
  const [environmentLoading, setEnvironmentLoading] = useState(false);

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
  }, []);

  const handleWebSocketMessage = (data) => {
    if (data.type === 'trace_update') {
      // Refresh traces and statistics when new messages arrive
      loadTraces();
      loadStatistics();
      // Also update topics data to reflect latest topic info
      loadTopics();
    } else if (data.type === 'environment_change') {
      // Handle environment change from server
      setCurrentEnvironment(data.environment);
      toast.info(`Environment changed to ${data.environment}`);
      loadInitialData();
    }
  };

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      await Promise.all([
        loadEnvironments(),
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
  const loadEnvironments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/environments`);
      setEnvironments(response.data.available_environments || []);
      setCurrentEnvironment(response.data.current_environment || '');
    } catch (error) {
      console.error('Error loading environments:', error);
    }
  };

  const switchEnvironment = async (environment) => {
    setEnvironmentLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/environments/switch`, {
        environment
      });
      
      if (response.data.success) {
        setCurrentEnvironment(environment);
        toast.success(`Switched to ${environment} environment`);
        
        // Clear existing data and reload
        setTraces([]);
        setSelectedTrace(null);
        setTraceFlow(null);
        setTopicGraph(null);
        setStatistics(null);
        
        // Reload all data for new environment
        await loadInitialData();
  const loadKafkaSubscriptionStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/kafka/subscription-status`);
      return response.data;
    } catch (error) {
      console.error('Error loading Kafka subscription status:', error);
      return null;
    }
  };

  const refreshKafkaSubscription = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/kafka/refresh-subscription`);
      if (response.data.success) {
        toast.success('Kafka subscription refreshed');
        return response.data;
      } else {
        toast.error('Failed to refresh Kafka subscription');
        return null;
      }
    } catch (error) {
      console.error('Error refreshing Kafka subscription:', error);
      toast.error('Failed to refresh Kafka subscription');
      return null;
    }
  };
      } else {
        toast.error(`Failed to switch environment: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error switching environment:', error);
      toast.error('Failed to switch environment');
    } finally {
      setEnvironmentLoading(false);
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
              <h1 className="text-2xl font-bold text-gray-900">Kafka Monitor</h1>
            </div>
            <div className="flex items-center space-x-4">
              {/* Page Navigation */}
              <div className="flex items-center space-x-2">
                <Button
                  variant={currentPage === 'traces' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCurrentPage('traces')}
                >
                  <Activity className="h-4 w-4 mr-2" />
                  Trace Viewer
                </Button>
                <Button
                  variant={currentPage === 'grpc' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCurrentPage('grpc')}
                >
                  <Server className="h-4 w-4 mr-2" />
                  gRPC Integration
                </Button>
              </div>
              
              {/* Status indicators - only for trace viewer */}
              {currentPage === 'traces' && (
                <>
                  {/* Environment Switcher */}
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-gray-600">Environment:</span>
                    <select
                      value={currentEnvironment}
                      onChange={(e) => switchEnvironment(e.target.value)}
                      disabled={environmentLoading}
                      className="text-sm border rounded px-2 py-1 bg-white"
                    >
                      {environments.map(env => (
                        <option key={env} value={env}>{env}</option>
                      ))}
                    </select>
                    {environmentLoading && (
                      <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />
                    )}
                  </div>
                  
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
                  
                  {/* Kafka Topic Status Indicator */}
                  <button
                    onClick={async () => {
                      try {
                        const response = await axios.get(`${API_BASE_URL}/api/kafka/subscription-status`);
                        const status = response.data;
                        if (status && status.success) {
                          const subscribed = status.subscribed_topics ? status.subscribed_topics.length : 0;
                          const missing = status.missing_topics ? status.missing_topics.length : 0;
                          const message = missing > 0 
                            ? `Subscribed to ${subscribed} topics (${missing} missing)`
                            : `Subscribed to ${subscribed} topics (all available)`;
                          toast.info(message);
                        } else {
                          toast.warning('Unable to get Kafka subscription status');
                        }
                      } catch (error) {
                        console.error('Error checking Kafka status:', error);
                        toast.error('Failed to check Kafka subscription status');
                      }
                    }}
                    className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                    title="Click to check Kafka topic status"
                  >
                    📡 Topics
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      {currentPage === 'traces' ? (
        // Existing Kafka Trace Viewer Content
        <div className="max-w-full mx-auto p-4">
          {/* Tab Navigation */}
          <div className="mb-4">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-3 max-w-md">
                <TabsTrigger value="traces">Traces</TabsTrigger>
                <TabsTrigger value="topics">Topics</TabsTrigger>
                <TabsTrigger value="graph">Graph</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>

          {/* Dynamic Layout Based on Active Tab */}
          {activeTab === 'graph' ? (
            // Full-width Graph Layout
            <div className="w-full">
              <EnhancedGraphVisualization />
            </div>
          ) : (
            // Original 4-column Layout for Traces and Topics
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-4">
              {/* Sidebar */}
              <div className="xl:col-span-1">
                {activeTab === 'traces' && (
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
                                      <div className="text-xs text-gray-600">
                                        {trace.message_count} messages • {trace.topics.length} topics
                                      </div>
                                      <div className="flex items-center space-x-2">
                                        <div className="flex flex-wrap gap-1">
                                          {trace.topics.slice(0, 3).map((topic, idx) => (
                                            <Badge key={idx} variant="outline" className="text-xs px-1.5 py-0.5">
                                              {topic}
                                            </Badge>
                                          ))}
                                          {trace.topics.length > 3 && (
                                            <Badge variant="outline" className="text-xs px-1.5 py-0.5">
                                              +{trace.topics.length - 3}
                                            </Badge>
                                          )}
                                        </div>
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
                )}

                {activeTab === 'topics' && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Topic Monitoring</CardTitle>
                      <CardDescription>
                        Configure which topics to monitor for traces
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex space-x-2">
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
                        
                        <Separator />
                        
                        <div className="space-y-2 max-h-96 overflow-y-auto">
                          {availableTopics.map((topic) => (
                            <div key={topic} className="flex items-center space-x-2">
                              <Checkbox
                                id={topic}
                                checked={monitoredTopics.includes(topic)}
                                onCheckedChange={(checked) => {
                                  if (checked) {
                                    updateMonitoredTopics([...monitoredTopics, topic]);
                                  } else {
                                    updateMonitoredTopics(monitoredTopics.filter(t => t !== topic));
                                  }
                                }}
                              />
                              <label
                                htmlFor={topic}
                                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                              >
                                {topic}
                              </label>
                            </div>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Main Content */}
              <div className="xl:col-span-3">
                {activeTab === 'topics' ? (
                  // Topic Statistics Display
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-xl">Topic Statistics</CardTitle>
                      <CardDescription>
                        Real-time statistics and metrics per monitored topic
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-6">
                        {monitoredTopics.length === 0 ? (
                          <div className="text-center py-12">
                            <Activity className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">
                              No Topics Monitored
                            </h3>
                            <p className="text-gray-600 mb-4">
                              Select topics from the sidebar to view their statistics
                            </p>
                          </div>
                        ) : (
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {monitoredTopics.map((topic) => {
                              const topicDetails = statistics?.topics?.details?.[topic];
                              const topicStats = topicDetails?.message_count || 0;
                              const topicTraces = topicDetails?.trace_count || 0;
                              const topicStatus = topicDetails?.status || 'No messages';
                              
                              return (
                                <Card key={topic} className="border-l-4 border-l-blue-500">
                                  <CardHeader className="pb-3">
                                    <div className="flex items-center justify-between">
                                      <CardTitle className="text-lg font-mono">{topic}</CardTitle>
                                      <Badge variant={topicStats > 0 ? "default" : "outline"}>
                                        {topicStats > 0 ? "Active" : "Inactive"}
                                      </Badge>
                                    </div>
                                  </CardHeader>
                                  <CardContent>
                                    <div className="grid grid-cols-2 gap-4">
                                      <div className="text-center">
                                        <div className="text-3xl font-bold text-blue-600">
                                          {topicStats}
                                        </div>
                                        <div className="text-sm text-gray-600">Messages</div>
                                      </div>
                                      <div className="text-center">
                                        <div className="text-3xl font-bold text-green-600">
                                          {topicTraces}
                                        </div>
                                        <div className="text-sm text-gray-600">Traces</div>
                                      </div>
                                    </div>
                                    
                                    <div className="mt-4 pt-4 border-t border-gray-200">
                                      <div className="text-sm space-y-2">
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Status:</span>
                                          <span className={`font-medium ${topicStats > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                                            {topicStats > 0 ? 'Receiving messages' : 'No recent activity'}
                                          </span>
                                        </div>
                                        <div className="flex justify-between">
                                          <span className="text-gray-600">Monitored:</span>
                                          <span className="font-medium text-blue-600">Yes</span>
                                        </div>
                                      </div>
                                    </div>
                                  </CardContent>
                                </Card>
                              );
                            })}
                          </div>
                        )}
                        
                        {/* Overall Statistics */}
                        {statistics && monitoredTopics.length > 0 && (
                          <Card className="bg-gradient-to-r from-blue-50 to-purple-50">
                            <CardHeader>
                              <CardTitle className="text-lg">Overall Statistics</CardTitle>
                            </CardHeader>
                            <CardContent>
                              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div className="text-center">
                                  <div className="text-2xl font-bold text-blue-600">
                                    {statistics.topics?.total || 0}
                                  </div>
                                  <div className="text-sm text-gray-600">Total Topics</div>
                                </div>
                                <div className="text-center">
                                  <div className="text-2xl font-bold text-green-600">
                                    {statistics.topics?.monitored || 0}
                                  </div>
                                  <div className="text-sm text-gray-600">Monitored</div>
                                </div>
                                <div className="text-center">
                                  <div className="text-2xl font-bold text-purple-600">
                                    {statistics.messages?.total || 0}
                                  </div>
                                  <div className="text-sm text-gray-600">Total Messages</div>
                                </div>
                                <div className="text-center">
                                  <div className="text-2xl font-bold text-orange-600">
                                    {statistics.traces?.total || 0}
                                  </div>
                                  <div className="text-sm text-gray-600">Active Traces</div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  // Trace Content
                  selectedTrace ? (
                    <div className="space-y-6">
                      {/* Trace Header */}
                      <Card>
                        <CardHeader>
                          <div className="flex justify-between items-start">
                            <div>
                              <CardTitle className="text-xl">Trace Details</CardTitle>
                              <CardDescription>
                                Trace ID: {selectedTrace.trace_id}
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
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <span className="text-gray-600">Messages:</span>
                              <span className="ml-2 font-medium">{selectedTrace.messages?.length || 0}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Topics:</span>
                              <span className="ml-2 font-medium">
                                {[...new Set(selectedTrace.messages?.map(m => m.topic) || [])].length}
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-600">Status:</span>
                              <span className="ml-2 font-medium text-green-600">Active</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      {/* Messages Display */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Messages by Topic</CardTitle>
                          <CardDescription>
                            All messages in this trace, organized by topic
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          {selectedTrace.messages && selectedTrace.messages.length > 0 ? (
                            <div className="space-y-4">
                              {Object.entries(
                                selectedTrace.messages.reduce((acc, message, index) => {
                                  const topic = message.topic || 'unknown';
                                  if (!acc[topic]) acc[topic] = [];
                                  acc[topic].push({ ...message, index });
                                  return acc;
                                }, {})
                              ).map(([topic, messages]) => (
                                <div key={topic} className="border rounded-lg p-4">
                                  <div className="flex items-center justify-between mb-3">
                                    <h4 className="font-medium text-lg">
                                      📡 {topic}
                                    </h4>
                                    <Badge variant="secondary">
                                      {messages.length} message{messages.length !== 1 ? 's' : ''}
                                    </Badge>
                                  </div>
                                  
                                  <div className="space-y-2">
                                    {messages.map((message) => (
                                      <div key={message.index} className="border rounded p-3 bg-gray-50">
                                        <div className="flex justify-between items-start mb-2">
                                          <div className="text-sm text-gray-600">
                                            Message #{message.index + 1}
                                          </div>
                                          <div className="text-xs text-gray-500">
                                            {new Date(message.timestamp).toLocaleString()}
                                          </div>
                                        </div>
                                        
                                        <div className="space-y-2">
                                          {message.headers && Object.keys(message.headers).length > 0 && (
                                            <div>
                                              <div className="text-sm font-medium text-gray-700 mb-1">Headers:</div>
                                              <div className="text-xs bg-blue-50 p-2 rounded font-mono">
                                                {Object.entries(message.headers).map(([key, value]) => (
                                                  <div key={key}>
                                                    <span className="text-blue-600">{key}:</span> {value}
                                                  </div>
                                                ))}
                                              </div>
                                            </div>
                                          )}
                                          
                                          {message.decoded_content && (
                                            <div>
                                              <div className="text-sm font-medium text-gray-700 mb-1">Content:</div>
                                              <div className="text-xs bg-green-50 p-2 rounded font-mono whitespace-pre-wrap">
                                                {typeof message.decoded_content === 'object' 
                                                  ? JSON.stringify(message.decoded_content, null, 2)
                                                  : message.decoded_content
                                                }
                                              </div>
                                            </div>
                                          )}
                                          
                                          {message.raw_content && !message.decoded_content && (
                                            <div>
                                              <div className="text-sm font-medium text-gray-700 mb-1">Raw Content:</div>
                                              <div className="text-xs bg-gray-100 p-2 rounded font-mono">
                                                {message.raw_content}
                                              </div>
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-center py-8">
                              <Activity className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                              <h3 className="text-lg font-medium text-gray-900 mb-2">
                                No Messages
                              </h3>
                              <p className="text-gray-600">
                                This trace doesn't contain any messages yet.
                              </p>
                            </div>
                          )}
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
                  )
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        // gRPC Integration Page
        <GrpcIntegration />
      )}
      <Toaster />
    </div>
  );
}

export default App;
