import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { toast } from 'sonner';

// Icons
import {
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  FileText,
  Server,
  Folder,
  FolderOpen,
  Database
} from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL;

const VerifySection = () => {
  const [files, setFiles] = useState([]);
  const [fileTree, setFileTree] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [environment, setEnvironment] = useState('');
  const [namespace, setNamespace] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [availableEnvironments, setAvailableEnvironments] = useState([]);
  
  const contentRef = useRef(null);
  
  useEffect(() => {
    initializeComponent();
  }, []);

  useEffect(() => {
    if (namespace && environment) {
      refreshFiles();
    }
  }, [environment, namespace]);

  const initializeComponent = async () => {
    try {
      setLoading(true);
      
      // Get current environment from the main app or localStorage
      const getCurrentEnvironment = () => {
        // Try to get from localStorage (where gRPC stores it)
        const savedGrpcEnv = localStorage.getItem('grpcCurrentEnvironment');
        if (savedGrpcEnv) {
          return savedGrpcEnv;
        }
        
        // Try to get from main app's current environment API
        return null;
      };
      
      // Get available environments
      const envResponse = await fetch(`${API_BASE_URL}/api/redis/environments`);
      if (envResponse.ok) {
        const envData = await envResponse.json();
        setAvailableEnvironments(envData.environments || []);
        
        // Sync with current environment from app
        const currentEnv = getCurrentEnvironment();
        let defaultEnv = 'DEV'; // fallback
        
        if (currentEnv && envData.environments.includes(currentEnv)) {
          defaultEnv = currentEnv;
        } else if (envData.environments && envData.environments.length > 0) {
          // Try to get current environment from main app
          try {
            const appEnvResponse = await fetch(`${API_BASE_URL}/api/environments`);
            if (appEnvResponse.ok) {
              const appEnvData = await appEnvResponse.json();
              const appCurrentEnv = appEnvData.current_environment;
              if (appCurrentEnv && envData.environments.includes(appCurrentEnv)) {
                defaultEnv = appCurrentEnv;
              } else {
                defaultEnv = envData.environments.includes('DEV') ? 'DEV' : envData.environments[0];
              }
            } else {
              defaultEnv = envData.environments.includes('DEV') ? 'DEV' : envData.environments[0];
            }
          } catch (error) {
            console.warn('Could not sync with main app environment:', error);
            defaultEnv = envData.environments.includes('DEV') ? 'DEV' : envData.environments[0];
          }
        }
        
        setEnvironment(defaultEnv);
      }
      
      // Get blueprint namespace
      const namespaceResponse = await fetch(`${API_BASE_URL}/api/blueprint/namespace`);
      if (namespaceResponse.ok) {
        const namespaceData = await namespaceResponse.json();
        setNamespace(namespaceData.namespace);
      } else {
        setError('No blueprint namespace detected. Make sure blueprint_cnf.json is configured.');
        return;
      }
      
      // Test initial connection
      await testConnection(environment);
      
    } catch (error) {
      console.error('Failed to initialize Verify section:', error);
      setError('Failed to initialize Redis verification. Check your configuration.');
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (env) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/redis/test-connection`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ environment: env })
      });
      
      const data = await response.json();
      
      if (data.status === 'connected') {
        setConnectionStatus('connected');
        setError(null);
      } else {
        setConnectionStatus('failed');
        setError(data.error || 'Connection test failed');
      }
      
    } catch (error) {
      setConnectionStatus('failed');
      setError(`Connection test failed: ${error.message || 'Redis server not accessible'}`);
    }
  };

  const refreshFiles = async () => {
    if (!namespace) {
      setError('No blueprint namespace available');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/redis/files?environment=${encodeURIComponent(environment)}&namespace=${encodeURIComponent(namespace)}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      setFiles(data.files || []);
      setConnectionStatus('connected');
      
      // Create tree structure from flat keys using ":" as separator
      const tree = createTreeFromKeys(data.files || []);
      setFileTree(tree);
      
      if (data.files.length === 0) {
        setError(`No files found for namespace: ${namespace}`);
      }
      
    } catch (error) {
      console.error('Failed to fetch Redis files:', error);
      const errorMsg = error.message || 'Failed to fetch files';
      
      // Check if this is an expected Redis connection error (mock environment)
      if (errorMsg.includes('Name or service not known') || 
          errorMsg.includes('connection') || 
          errorMsg.includes('redis-')) {
        setError(`Redis connection unavailable: Mock environment detected. This is expected behavior when Redis cluster is not accessible.`);
      } else {
        setError(errorMsg);
      }
      
      setConnectionStatus('failed');
      setFiles([]);
      setFileTree({});
    } finally {
      setLoading(false);
    }
  };

  const createTreeFromKeys = (files) => {
    const tree = {};
    
    files.forEach(file => {
      const parts = file.key.split(':');
      let current = tree;
      
      // Build tree structure
      parts.forEach((part, index) => {
        if (index === parts.length - 1) {
          // This is a leaf (file)
          current[part] = {
            type: 'file',
            key: file.key,
            size_bytes: file.size_bytes
          };
        } else {
          // This is a folder
          if (!current[part] || current[part].type === 'file') {
            current[part] = {
              type: 'folder',
              children: {}
            };
          }
          current = current[part].children;
        }
      });
    });
    
    return tree;
  };

  const handleEnvironmentChange = async (newEnv) => {
    setEnvironment(newEnv);
    setSelectedFile(null);
    setFileContent('');
    setFiles([]);
    setFileTree({});
    
    // Test connection to new environment
    await testConnection(newEnv);
  };

  const handleFileSelect = async (fileKey) => {
    setSelectedFile(fileKey);
    setLoading(true);
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/redis/file-content?key=${encodeURIComponent(fileKey)}&environment=${encodeURIComponent(environment)}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setFileContent(data.content);
      
      // Apply JSON syntax highlighting
      if (contentRef.current) {
        highlightJSON(data.content);
      }
      
    } catch (error) {
      console.error('Failed to fetch file content:', error);
      setFileContent(`Error loading file content: ${error.message}`);
      toast.error(`Failed to load file: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const highlightJSON = (content) => {
    try {
      // Try to parse as JSON first
      const parsed = JSON.parse(content);
      const formatted = JSON.stringify(parsed, null, 2);
      
      if (contentRef.current) {
        contentRef.current.innerHTML = formatJSONWithColors(formatted);
      }
      
    } catch (error) {
      // If not valid JSON, try to format it as JSON-like content anyway
      try {
        // Attempt to make it look like JSON by adding proper formatting
        let formattedContent = content;
        
        // If it looks like it might be JSON-ish, try to format it
        if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
          // Try to fix common JSON formatting issues and parse again
          formattedContent = content
            .replace(/'/g, '"')  // Replace single quotes with double quotes
            .replace(/([{,]\s*)(\w+):/g, '$1"$2":')  // Quote unquoted keys
            .replace(/:\s*([^",{\[\]}\s]+)(?=[,}\]])/g, ': "$1"');  // Quote unquoted values
          
          try {
            const parsed = JSON.parse(formattedContent);
            const formatted = JSON.stringify(parsed, null, 2);
            if (contentRef.current) {
              contentRef.current.innerHTML = formatJSONWithColors(formatted);
            }
            return;
          } catch (e) {
            // Still not valid JSON, continue to plain formatting
          }
        }
        
        // Format as JSON-like content with syntax highlighting anyway
        if (contentRef.current) {
          contentRef.current.innerHTML = formatJSONWithColors(formattedContent);
        }
        
      } catch (e) {
        // Fallback to plain text with JSON-like styling
        if (contentRef.current) {
          contentRef.current.innerHTML = formatJSONWithColors(content);
        }
      }
    }
  };

  const formatJSONWithColors = (json) => {
    return json
      .replace(/("([^"\\]|\\.)*")\s*:/g, '<span class="text-blue-600 font-medium">$1</span>:')
      .replace(/:\s*("([^"\\]|\\.)*")/g, ': <span class="text-green-600">$1</span>')
      .replace(/:\s*(true|false)/g, ': <span class="text-purple-600 font-medium">$1</span>')
      .replace(/:\s*(null)/g, ': <span class="text-gray-500 italic">$1</span>')
      .replace(/:\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g, ': <span class="text-orange-600">$1</span>');
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const TreeNode = ({ node, name, path = '' }) => {
    const fullPath = path ? `${path}:${name}` : name;
    const [isExpanded, setIsExpanded] = useState(true);
    
    if (node.type === 'file') {
      return (
        <div
          key={node.key}
          className={`flex items-center justify-between p-2 hover:bg-gray-100 cursor-pointer rounded ${
            selectedFile === node.key ? 'bg-blue-100 border-l-4 border-blue-500' : ''
          }`}
          onClick={() => handleFileSelect(node.key)}
        >
          <div className="flex items-center space-x-2">
            <FileText className="h-4 w-4 text-gray-400" />
            <span className="text-sm font-mono text-gray-700">{name}</span>
          </div>
          <span className="text-xs text-gray-500">{formatFileSize(node.size_bytes)}</span>
        </div>
      );
    } else {
      // Folder
      return (
        <div key={fullPath} className="mb-1">
          <div
            className="flex items-center p-2 hover:bg-gray-50 cursor-pointer rounded"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <FolderOpen className="h-4 w-4 text-blue-500 mr-2" />
            ) : (
              <Folder className="h-4 w-4 text-gray-500 mr-2" />
            )}
            <span className="text-sm font-medium text-gray-800">{name}</span>
          </div>
          
          {isExpanded && node.children && (
            <div className="ml-6 border-l border-gray-200 pl-2">
              {Object.entries(node.children).map(([childName, childNode]) =>
                <TreeNode key={childName} node={childNode} name={childName} path={fullPath} />
              )}
            </div>
          )}
        </div>
      );
    }
  };

  const renderFileExplorer = () => {
    if (loading && files.length === 0) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 mx-auto mb-2 animate-spin text-blue-500" />
            <p className="text-sm text-gray-600">Loading files...</p>
          </div>
        </div>
      );
    }

    if (error && files.length === 0) {
      return (
        <div className="p-4">
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button 
            onClick={refreshFiles} 
            className="mt-3 w-full"
            variant="outline"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Retry
          </Button>
        </div>
      );
    }

    if (Object.keys(fileTree).length === 0) {
      return (
        <div className="p-4 text-center">
          <Database className="h-12 w-12 mx-auto mb-3 text-gray-300" />
          <p className="text-sm text-gray-600 mb-3">
            No files found for namespace: <strong>{namespace}</strong>
          </p>
          <Button onClick={refreshFiles} variant="outline" disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      );
    }

    return (
      <div className="p-2">
        {Object.entries(fileTree).map(([name, node]) =>
          <TreeNode key={name} node={node} name={name} />
        )}
      </div>
    );
  };

  const renderFileContent = () => {
    if (!selectedFile) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No file selected</h3>
            <p className="text-gray-600">Select a file from the tree to view its content</p>
          </div>
        </div>
      );
    }

    if (loading) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <RefreshCw className="h-8 w-8 mx-auto mb-2 animate-spin text-blue-500" />
            <p className="text-sm text-gray-600">Loading content...</p>
          </div>
        </div>
      );
    }

    const selectedFileInfo = files.find(f => f.key === selectedFile);

    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center justify-between p-4 border-b bg-gray-50">
          <div>
            <h3 className="font-medium text-gray-900 font-mono text-sm">{selectedFile}</h3>
            <p className="text-xs text-gray-600">
              {selectedFileInfo ? formatFileSize(selectedFileInfo.size_bytes) : ''} • JSON
            </p>
          </div>
          <Badge variant="outline" className="text-xs">
            {environment}
          </Badge>
        </div>
        
        <div className="flex-1 overflow-auto p-4 bg-white">
          <pre 
            ref={contentRef} 
            className="text-sm font-mono leading-relaxed text-gray-800 whitespace-pre-wrap break-words"
            style={{ minHeight: '100%' }}
          >
            {fileContent}
          </pre>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b p-4 bg-gray-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Database className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-gray-900">Redis Verification</h2>
            </div>
            
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">Environment:</label>
              <select 
                value={environment} 
                onChange={(e) => handleEnvironmentChange(e.target.value)}
                className="border border-gray-300 rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              >
                {availableEnvironments.map(env => (
                  <option key={env} value={env}>
                    {env}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-600">
              Namespace: <span className="font-mono font-medium">{namespace || 'Not detected'}</span>
            </div>
            
            <div className={`flex items-center space-x-1 text-sm ${
              connectionStatus === 'connected' ? 'text-green-600' : 
              connectionStatus === 'failed' ? 'text-red-600' : 'text-yellow-600'
            }`}>
              <Server className="h-4 w-4" />
              <span className="capitalize">{connectionStatus}</span>
            </div>
            
            <Button 
              onClick={refreshFiles} 
              variant="outline"
              size="sm"
              disabled={loading || !namespace}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer */}
        <div className="w-80 border-r bg-gray-50 overflow-y-auto">
          <div className="p-3 border-b bg-white">
            <h3 className="font-medium text-gray-900">
              Redis Files ({files.length})
            </h3>
          </div>
          {renderFileExplorer()}
        </div>

        {/* Content Viewer */}
        <div className="flex-1 overflow-hidden">
          {renderFileContent()}
        </div>
      </div>
    </div>
  );
};

export default VerifySection;