import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

// Shadcn UI components
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Separator } from './ui/separator';
import { Alert, AlertDescription } from './ui/alert';
import { Progress } from './ui/progress';
import { toast } from 'sonner';

// Icons
import { 
  RefreshCw, 
  Filter, 
  BarChart3, 
  Zap, 
  Clock, 
  Activity,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Layers
} from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function EnhancedGraphVisualization() {
  // State management
  const [disconnectedGraphs, setDisconnectedGraphs] = useState([]);
  const [filteredData, setFilteredData] = useState(null);
  const [currentFilter, setCurrentFilter] = useState('all');
  const [customMinutes, setCustomMinutes] = useState(30);
  const [loading, setLoading] = useState(false);
  const [networkInstances, setNetworkInstances] = useState({});
  const [selectedComponent, setSelectedComponent] = useState(null);
  const [realTimeEnabled, setRealTimeEnabled] = useState(true);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(null);

  // Refs for network containers
  const networkRefs = useRef({});

  useEffect(() => {
    loadDisconnectedGraphs();
    
    // Set up auto-refresh if real-time is enabled
    if (realTimeEnabled) {
      const interval = setInterval(() => {
        loadDisconnectedGraphs(true); // Silent refresh
      }, 10000); // Refresh every 10 seconds
      
      setAutoRefreshInterval(interval);
      
      return () => clearInterval(interval);
    }
  }, [realTimeEnabled]);

  useEffect(() => {
    return () => {
      // Cleanup intervals on unmount
      if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
      }
      
      // Cleanup network instances
      Object.values(networkInstances).forEach(network => {
        if (network && network.destroy) {
          network.destroy();
        }
      });
    };
  }, []);

  const loadDisconnectedGraphs = async (silent = false) => {
    if (!silent) setLoading(true);
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/graph/disconnected`);
      
      if (response.data.success) {
        setDisconnectedGraphs(response.data.components);
        
        // Render networks after state update
        setTimeout(() => {
          response.data.components.forEach((component, index) => {
            renderComponentNetwork(component, index);
          });
        }, 100);
        
        if (!silent) {
          toast.success(`Loaded ${response.data.total_components} graph components`);
        }
      }
    } catch (error) {
      console.error('Error loading disconnected graphs:', error);
      if (!silent) {
        toast.error('Failed to load graph components');
      }
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const applyTimeFilter = async (filter, minutes = null) => {
    setLoading(true);
    try {
      const params = { time_filter: filter };
      if (filter === 'custom' && minutes) {
        params.custom_minutes = minutes;
      }
      
      const response = await axios.get(`${API_BASE_URL}/api/graph/filtered`, { params });
      
      if (response.data.success) {
        setFilteredData(response.data);
        setCurrentFilter(filter);
        
        // Render filtered graphs
        setTimeout(() => {
          response.data.disconnected_graphs.forEach((component, index) => {
            renderComponentNetwork(component, `filtered-${index}`);
          });
        }, 100);
        
        toast.success(`Applied ${filter} filter`);
      }
    } catch (error) {
      console.error('Error applying filter:', error);
      toast.error('Failed to apply time filter');
    } finally {
      setLoading(false);
    }
  };

  const applyMockData = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/graph/apply-mock`);
      
      if (response.data.success) {
        toast.success('Mock graph data applied successfully');
        // Reload graphs after applying mock data
        setTimeout(() => {
          loadDisconnectedGraphs();
        }, 1000);
      }
    } catch (error) {
      console.error('Error applying mock data:', error);
      toast.error('Failed to apply mock data');
    } finally {
      setLoading(false);
    }
  };

  const renderComponentNetwork = (component, containerKey) => {
    const containerId = `network-component-${containerKey}`;
    const container = document.getElementById(containerId);
    
    if (!container || !component.nodes || !component.edges) {
      return;
    }

    // Destroy existing network if it exists
    if (networkInstances[containerKey]) {
      networkInstances[containerKey].destroy();
    }

    try {
      // Prepare nodes with enhanced styling
      const nodes = new DataSet(component.nodes.map(node => ({
        id: node.id,
        label: node.label,
        shape: 'box',
        color: node.color || {
          background: node.monitored ? '#10b981' : '#6b7280',
          border: node.monitored ? '#059669' : '#4b5563'
        },
        font: { 
          color: 'white', 
          size: 12,
          face: 'Inter, system-ui, sans-serif'
        },
        margin: 10,
        size: node.size || 30,
        borderWidth: 2,
        shadow: {
          enabled: true,
          color: 'rgba(0,0,0,0.2)',
          size: 5,
          x: 2,
          y: 2
        },
        title: `Topic: ${node.id}\nMessages: ${node.statistics?.message_count || 0}\nRate: ${node.statistics?.rate?.toFixed(1) || 0}/min\nMedian Age: ${Math.round(node.statistics?.median_trace_age || 0)}s`
      })));

      // Prepare edges with enhanced styling
      const edges = new DataSet(component.edges.map((edge, index) => ({
        id: `edge_${containerKey}_${index}`,
        from: edge.source,
        to: edge.target,
        arrows: { to: { enabled: true, scaleFactor: 1.2 } },
        color: { 
          color: edge.flow_count > 10 ? '#10b981' : '#6b7280',
          highlight: '#3b82f6'
        },
        width: edge.width || Math.max(2, Math.min(8, edge.flow_count || 2)),
        smooth: { type: 'curvedCW', roundness: 0.2 },
        label: edge.flow_count > 0 ? `${edge.flow_count}` : '',
        font: { size: 10, color: '#4b5563' },
        title: `Flow: ${edge.source} → ${edge.target}\nMessages: ${edge.flow_count}\nRate: ${edge.message_rate?.toFixed(1) || 0}/min`
      })));

      const data = { nodes, edges };
      
      // Configure network options based on component size and type
      const options = {
        layout: component.layout_type === 'hierarchical' ? {
          hierarchical: {
            enabled: true,
            direction: 'UD',
            sortMethod: 'directed',
            nodeSpacing: 200,
            levelSeparation: 250,
            treeSpacing: 400,
            blockShifting: true,
            edgeMinimization: true,
            parentCentralization: true
          }
        } : {
          improvedLayout: true,
          randomSeed: component.component_id // Consistent layout
        },
        physics: {
          enabled: component.layout_type !== 'hierarchical',
          stabilization: { 
            iterations: 150,
            updateInterval: 25
          },
          barnesHut: {
            gravitationalConstant: -8000,
            centralGravity: 0.3,
            springLength: 120,
            springConstant: 0.04,
            damping: 0.09
          }
        },
        interaction: { 
          dragNodes: true, 
          zoomView: true,
          selectConnectedEdges: false,
          hover: true,
          multiselect: true,
          tooltipDelay: 200,
          zoomSpeed: 1
        },
        configure: {
          enabled: false
        },
        autoResize: true,
        nodes: {
          borderWidth: 2,
          shadow: true,
          font: {
            face: 'Inter, system-ui, sans-serif'
          }
        },
        edges: {
          shadow: true,
          smooth: {
            enabled: true,
            type: 'curvedCW',
            roundness: 0.2
          },
          arrows: {
            to: {
              enabled: true,
              scaleFactor: 1.2
            }
          }
        }
      };

      // Create network
      const network = new Network(container, data, options);
      
      // Store network instance
      setNetworkInstances(prev => ({
        ...prev,
        [containerKey]: network
      }));

      // Auto-fit the network after stabilization for better visibility
      network.once("stabilizationIterationsDone", function() {
        network.fit({
          animation: {
            duration: 1000,
            easingFunction: "easeInOutQuad"
          }
        });
      });

      // Add event listeners
      network.on("click", function (params) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0];
          const nodeData = component.nodes.find(n => n.id === nodeId);
          setSelectedComponent({ ...component, selectedNode: nodeData });
          console.log(`Selected node: ${nodeId}`, nodeData);
        }
      });

      network.on("hoverNode", function (params) {
        container.style.cursor = 'pointer';
      });

      network.on("blurNode", function (params) {
        container.style.cursor = 'default';
      });

    } catch (error) {
      console.error(`Error rendering component ${containerKey}:`, error);
    }
  };

  const getHealthScoreColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthScoreIcon = (score) => {
    if (score >= 80) return CheckCircle;
    if (score >= 60) return AlertTriangle;
    return AlertTriangle;
  };

  const formatAge = (seconds) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const dataToDisplay = filteredData ? filteredData.disconnected_graphs : disconnectedGraphs;

  return (
    <div className="p-6 space-y-6">
      {/* Header Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <Layers className="h-6 w-6" />
                <span>Enhanced Graph Visualization</span>
              </CardTitle>
              <CardDescription>
                Multiple disconnected graph components with real-time statistics and filtering
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRealTimeEnabled(!realTimeEnabled)}
              >
                <Activity className={`h-4 w-4 mr-2 ${realTimeEnabled ? 'text-green-500' : 'text-gray-400'}`} />
                {realTimeEnabled ? 'Real-time ON' : 'Real-time OFF'}
              </Button>
              <Button variant="outline" size="sm" onClick={() => loadDisconnectedGraphs()}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4">
            {/* Time Filter */}
            <div className="flex items-center space-x-2">
              <Filter className="h-4 w-4" />
              <Select value={currentFilter} onValueChange={(value) => applyTimeFilter(value, customMinutes)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Time filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Time</SelectItem>
                  <SelectItem value="last_5min">Last 5 Minutes</SelectItem>
                  <SelectItem value="last_15min">Last 15 Minutes</SelectItem>
                  <SelectItem value="last_30min">Last 30 Minutes</SelectItem>
                  <SelectItem value="last_hour">Last Hour</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Custom minutes input */}
            {currentFilter === 'custom' && (
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  value={customMinutes}
                  onChange={(e) => setCustomMinutes(parseInt(e.target.value) || 30)}
                  className="w-20 px-2 py-1 border rounded text-sm"
                  min="1"
                  max="1440"
                />
                <span className="text-sm text-gray-600">minutes</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => applyTimeFilter('custom', customMinutes)}
                >
                  Apply
                </Button>
              </div>
            )}

            <Separator orientation="vertical" className="h-8" />

            {/* Mock Data Button */}
            <Button variant="outline" size="sm" onClick={applyMockData} disabled={loading}>
              <Zap className="h-4 w-4 mr-2" />
              Apply Mock Data
            </Button>

            {/* Statistics */}
            {dataToDisplay.length > 0 && (
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <BarChart3 className="h-4 w-4" />
                  <span>{dataToDisplay.length} components</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Activity className="h-4 w-4" />
                  <span>{dataToDisplay.reduce((sum, comp) => sum + comp.topic_count, 0)} topics</span>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {loading && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center space-x-2">
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span>Loading graph components...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No Data State */}
      {!loading && dataToDisplay.length === 0 && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            No graph components found. Try applying mock data or check your topic monitoring settings.
          </AlertDescription>
        </Alert>
      )}

      {/* Graph Components */}
      {dataToDisplay.map((component, index) => {
        const HealthIcon = getHealthScoreIcon(component.statistics?.health_score || 0);
        
        return (
          <Card key={`component-${component.component_id}-${index}`} className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center space-x-2">
                    <span>Component {component.component_id + 1}</span>
                    <Badge variant="secondary">
                      {component.topic_count} topics
                    </Badge>
                    <HealthIcon className={`h-4 w-4 ${getHealthScoreColor(component.statistics?.health_score || 0)}`} />
                  </CardTitle>
                  <CardDescription>
                    {component.topics.join(', ')}
                  </CardDescription>
                </div>
                <div className="flex items-center space-x-4 text-sm">
                  <div className="text-center">
                    <div className="font-medium">{component.statistics?.total_messages || 0}</div>
                    <div className="text-gray-500">Messages</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">{component.statistics?.active_traces || 0}</div>
                    <div className="text-gray-500">Traces</div>
                  </div>
                  <div className="text-center">
                    <div className="font-medium">{Math.round(component.statistics?.health_score || 0)}%</div>
                    <div className="text-gray-500">Health</div>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Statistics Panel */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4 p-4 bg-gray-50 rounded-lg">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {formatAge(component.statistics?.median_trace_age || 0)}
                  </div>
                  <div className="text-sm text-gray-600">Median Age</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {formatAge(component.statistics?.p95_trace_age || 0)}
                  </div>
                  <div className="text-sm text-gray-600">P95 Age</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {component.statistics?.total_messages || 0}
                  </div>
                  <div className="text-sm text-gray-600">Total Messages</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {component.statistics?.active_traces || 0}
                  </div>
                  <div className="text-sm text-gray-600">Active Traces</div>
                </div>
              </div>

              {/* Network Visualization */}
              <div className="relative">
                <div
                  id={`network-component-${filteredData ? 'filtered-' : ''}${index}`}
                  style={{
                    height: Math.max(800, Math.min(1200, component.topics.length * 60 + 400)) + 'px',
                    width: '100%',
                    border: '2px solid #e2e8f0',
                    borderRadius: '12px',
                    background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)'
                  }}
                />
                
                {/* Zoom Controls */}
                <div className="absolute bottom-4 right-4 flex flex-col space-y-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="bg-white shadow-lg"
                    onClick={() => {
                      const network = networkInstances[`component-${index}`];
                      if (network) {
                        const scale = network.getScale() * 1.2;
                        network.moveTo({ scale });
                      }
                    }}
                  >
                    🔍+
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="bg-white shadow-lg"
                    onClick={() => {
                      const network = networkInstances[`component-${index}`];
                      if (network) {
                        const scale = network.getScale() * 0.8;
                        network.moveTo({ scale });
                      }
                    }}
                  >
                    🔍-
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="bg-white shadow-lg"
                    onClick={() => {
                      const network = networkInstances[`component-${index}`];
                      if (network) {
                        network.fit();
                      }
                    }}
                  >
                    ⊞
                  </Button>
                </div>
                
                {/* Legend */}
                <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-lg text-sm">
                  <div className="font-medium mb-2">Node Colors</div>
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 bg-green-500 rounded"></div>
                      <span>Fresh (&lt;30s)</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 bg-amber-500 rounded"></div>
                      <span>Mid-age (30s-5m)</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 bg-red-500 rounded"></div>
                      <span>Old (&gt;5m)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Component Details */}
              <div className="mt-4 text-xs text-gray-500 bg-blue-50 p-3 rounded">
                💡 Tip: Node sizes reflect message counts, edge widths show flow volumes. 
                Hover over nodes and edges for detailed statistics. Use mouse wheel to zoom and drag to pan.
              </div>
            </CardContent>
          </Card>
        );
      })}

      {/* Selected Component Details */}
      {selectedComponent && (
        <Card>
          <CardHeader>
            <CardTitle>Selected Node Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium">Topic Information</h4>
                <p className="text-sm text-gray-600">Topic: {selectedComponent.selectedNode?.id}</p>
                <p className="text-sm text-gray-600">Component: {selectedComponent.component_id + 1}</p>
                <p className="text-sm text-gray-600">Monitored: {selectedComponent.selectedNode?.monitored ? 'Yes' : 'No'}</p>
              </div>
              <div>
                <h4 className="font-medium">Statistics</h4>
                <p className="text-sm text-gray-600">Messages: {selectedComponent.selectedNode?.statistics?.message_count || 0}</p>
                <p className="text-sm text-gray-600">Rate: {selectedComponent.selectedNode?.statistics?.rate?.toFixed(1) || 0} msg/min</p>
                <p className="text-sm text-gray-600">Median Age: {formatAge(selectedComponent.selectedNode?.statistics?.median_trace_age || 0)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default EnhancedGraphVisualization;