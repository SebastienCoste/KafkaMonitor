import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const BlueprintContext = createContext();

export const useBlueprintContext = () => {
  const context = useContext(BlueprintContext);
  if (!context) {
    throw new Error('useBlueprintContext must be used within a BlueprintProvider');
  }
  return context;
};

export function BlueprintProvider({ children }) {
  // State management
  const [rootPath, setRootPath] = useState('');
  const [fileTree, setFileTree] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [openTabs, setOpenTabs] = useState([]); // Array of {path, content, hasChanges}
  const [activeTab, setActiveTab] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false); // FIX 4: Default to false
  const [environments, setEnvironments] = useState([]);
  const [selectedEnvironment, setSelectedEnvironment] = useState('dev');
  const [websocket, setWebsocket] = useState(null);
  const [buildStatus, setBuildStatus] = useState('idle');
  const [buildOutput, setBuildOutput] = useState([]);
  const [outputFiles, setOutputFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [namespace, setNamespace] = useState('');

  const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

  // WebSocket connection and load config on mount
  useEffect(() => {
    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/ws/blueprint`;
      
      console.log('Connecting to WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('Blueprint WebSocket connected');
        setWebsocket(ws);
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          handleWebSocketMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.onclose = () => {
        console.log('Blueprint WebSocket disconnected');
        setWebsocket(null);
        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };
      
      ws.onerror = (error) => {
        console.error('Blueprint WebSocket error:', error);
        setWebsocket(null);
      };
    };

    // Load existing configuration on mount
    const loadInitialConfig = async () => {
      try {
        console.log('Loading initial blueprint configuration...');
        console.log('API_BASE_URL:', API_BASE_URL);
        
        // Use fetch instead of axios for more reliable requests
        console.log('Making config request...');
        const configResponse = await fetch(`${API_BASE_URL}/api/blueprint/config`);
        console.log('Config response received, status:', configResponse.status);
        
        if (!configResponse.ok) {
          throw new Error(`Config request failed: ${configResponse.status} ${configResponse.statusText}`);
        }
        
        const config = await configResponse.json();
        console.log('Loaded config:', config);
        
        if (config && config.root_path) {
          console.log('Setting root path:', config.root_path);
          setRootPath(config.root_path);
          setAutoRefresh(config.auto_refresh || true);
          
          // Auto-load file tree if root path is set
          console.log('Loading file tree...');
          const fileTreeResponse = await fetch(`${API_BASE_URL}/api/blueprint/file-tree`);
          console.log('File tree response received, status:', fileTreeResponse.status);
          
          if (!fileTreeResponse.ok) {
            throw new Error(`File tree request failed: ${fileTreeResponse.status} ${fileTreeResponse.statusText}`);
          }
          
          const fileTreeData = await fileTreeResponse.json();
          console.log('File tree response data:', fileTreeData);
          
          setFileTree(fileTreeData.files || []);
          console.log('File tree loaded successfully');
        } else {
          console.log('No root path found in config, staying on setup screen');
        }
      } catch (error) {
        console.error('Error loading initial config:', error);
        console.error('Error details:', error.message);
      } finally {
        console.log('Setting initializing to false');
        setInitializing(false);
      }
    };

    connectWebSocket();
    loadInitialConfig();

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, []); // Remove websocket dependency to avoid reconnection loops

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'build_output':
        setBuildOutput(prev => [...prev, data.data.content]);
        break;
      case 'build_started':
        setBuildStatus('building');
        setBuildOutput([]);
        break;
      case 'build_complete':
        setBuildStatus(data.data.success ? 'success' : 'failed');
        if (data.data.generated_files) {
          setOutputFiles(data.data.generated_files);
        }
        break;
      case 'build_error':
        setBuildStatus('failed');
        setBuildOutput(prev => [...prev, `Error: ${data.data.error}`]);
        break;
      case 'file_tree_update':
        if (data.files) {
          setFileTree(data.files);
        }
        break;
      case 'file_updated':
      case 'file_created':
      case 'file_deleted':
      case 'directory_created':
        // Refresh file tree when files change
        refreshFileTree();
        break;
      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  };

  // Load environments on mount
  useEffect(() => {
    loadEnvironments();
  }, []);

  const refreshFileTree = useCallback(async () => {
    if (!rootPath) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/file-tree`);
      setFileTree(response.data.files || []);
    } catch (error) {
      console.error('Error refreshing file tree:', error);
    }
  }, [API_BASE_URL, rootPath]);

  // Auto-refresh logic
  useEffect(() => {
    if (autoRefresh && rootPath) {
      const interval = setInterval(() => {
        refreshFileTree();
      }, 30000); // 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, rootPath, refreshFileTree]);

  const loadEnvironments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/environments`);
      if (response.data.available_environments) {
        setEnvironments(response.data.available_environments);
        if (response.data.current_environment) {
          setSelectedEnvironment(response.data.current_environment);
        }
      }
    } catch (error) {
      console.error('Error loading environments:', error);
    }
  };

  const setBlueprintRootPath = async (path) => {
    try {
      setLoading(true);
      const response = await axios.put(`${API_BASE_URL}/api/blueprint/config`, {
        root_path: path
      });
      
      if (response.data.success) {
        setRootPath(path);
        // Force immediate file tree refresh
        setTimeout(async () => {
          await refreshFileTree();
          console.log('✅ Auto-loaded file tree after setting root path');
        }, 500);
      }
    } catch (error) {
      console.error('Error setting root path:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async (filePath) => {
    try {
      setLoading(true);
      
      // Always load fresh content from server and update editor
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/file-content/${filePath}`);
      const content = response.data.content;
      
      // Check if file is already open in tabs
      const existingTab = openTabs.find(tab => tab.path === filePath);
      if (existingTab) {
        // Update existing tab with fresh content
        setOpenTabs(prev => prev.map(tab => 
          tab.path === filePath 
            ? { ...tab, content: content, originalContent: content }
            : tab
        ));
        setActiveTab(filePath);
        setSelectedFile(filePath);
        setFileContent(content);
      } else {
        // Add to open tabs
        const newTab = {
          path: filePath,
          content: content,
          hasChanges: false,
          originalContent: content
        };
        
        setOpenTabs(prev => [...prev, newTab]);
        setActiveTab(filePath);
        setFileContent(content);
        setSelectedFile(filePath);
      }
    } catch (error) {
      console.error('Error loading file content:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const switchToTab = (filePath) => {
    // Find the tab and update all related states
    const tab = openTabs.find(t => t.path === filePath);
    if (tab) {
      setActiveTab(filePath);
      setSelectedFile(filePath);
      setFileContent(tab.content);
    }
  };

  const closeTab = (filePath) => {
    setOpenTabs(prev => prev.filter(tab => tab.path !== filePath));
    
    // If closing active tab, switch to another tab or clear selection
    if (activeTab === filePath) {
      const remainingTabs = openTabs.filter(tab => tab.path !== filePath);
      if (remainingTabs.length > 0) {
        const newActiveTab = remainingTabs[remainingTabs.length - 1];
        switchToTab(newActiveTab.path);
      } else {
        setActiveTab(null);
        setSelectedFile(null);
        setFileContent('');
      }
    }
  };

  const updateTabContent = (filePath, content) => {
    setOpenTabs(prev => prev.map(tab => 
      tab.path === filePath 
        ? { ...tab, content, hasChanges: content !== tab.originalContent }
        : tab
    ));
    
    if (activeTab === filePath) {
      setFileContent(content);
    }
  };

  const saveFileContent = async (filePath, content) => {
    try {
      setLoading(true);
      await axios.put(`${API_BASE_URL}/api/blueprint/file-content/${filePath}`, {
        content: content
      });
      
      // Update tab content and mark as saved
      setOpenTabs(prev => prev.map(tab => 
        tab.path === filePath 
          ? { ...tab, content, hasChanges: false, originalContent: content }
          : tab
      ));
      
      if (activeTab === filePath) {
        setFileContent(content);
      }
    } catch (error) {
      console.error('Error saving file content:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const createFile = async (filePath, templateName = null) => {
    try {
      setLoading(true);
      await axios.post(`${API_BASE_URL}/api/blueprint/create-file`, {
        path: filePath,
        new_path: templateName // Using new_path field for template name
      });
      await refreshFileTree();
    } catch (error) {
      console.error('Error creating file:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (filePath) => {
    try {
      setLoading(true);
      await axios.delete(`${API_BASE_URL}/api/blueprint/delete-file/${filePath}`);
      
      // Clear selected file if it was deleted
      if (selectedFile === filePath) {
        setSelectedFile(null);
        setFileContent('');
      }
      
      await refreshFileTree();
    } catch (error) {
      console.error('Error deleting file:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const createDirectory = async (dirPath) => {
    try {
      setLoading(true);
      await axios.post(`${API_BASE_URL}/api/blueprint/create-directory`, {
        path: dirPath
      });
      await refreshFileTree();
    } catch (error) {
      console.error('Error creating directory:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const renameFile = async (sourcePath, newName) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/rename-file`, {
        source_path: sourcePath,
        new_name: newName
      });
      
      // If the renamed file was selected or in tabs, update the references
      if (selectedFile === sourcePath) {
        setSelectedFile(response.data.new_path);
      }
      
      // Update any open tabs with the old path
      setOpenTabs(prev => prev.map(tab => 
        tab.path === sourcePath 
          ? { ...tab, path: response.data.new_path }
          : tab
      ));
      
      if (activeTab === sourcePath) {
        setActiveTab(response.data.new_path);
      }
      
      await refreshFileTree();
      return response.data;
    } catch (error) {
      console.error('Error renaming file:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const buildBlueprint = async (scriptName = 'buildBlueprint.sh') => {
    try {
      setLoading(true);
      setBuildStatus('building');
      setBuildOutput([]);
      
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/build`, {
        root_path: rootPath,
        script_name: scriptName
      });
      
      // Build status will be updated via WebSocket messages
      return response.data;
    } catch (error) {
      console.error('Error building blueprint:', error);
      setBuildStatus('failed');
      setBuildOutput(prev => [...prev, `Build failed: ${error.message}`]);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const cancelBuild = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/blueprint/cancel-build`);
      setBuildStatus('idle');
    } catch (error) {
      console.error('Error canceling build:', error);
      throw error;
    }
  };

  const loadOutputFiles = useCallback(async () => {
    if (!rootPath) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/output-files?root_path=${encodeURIComponent(rootPath)}`);
      setOutputFiles(response.data.files || []);
    } catch (error) {
      console.error('Error loading output files:', error);
    }
  }, [API_BASE_URL, rootPath]);

  const validateBlueprint = async (filename) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/validate/${filename}`, {
        tgz_file: filename,
        environment: selectedEnvironment,
        action: 'validate'
      });
      return response.data;
    } catch (error) {
      console.error('Error validating blueprint:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const activateBlueprint = async (filename) => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/activate/${filename}`, {
        tgz_file: filename,
        environment: selectedEnvironment,
        action: 'activate'
      });
      return response.data;
    } catch (error) {
      console.error('Error activating blueprint:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const getBlueprintConfig = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/config`);
      return response.data;
    } catch (error) {
      console.error('Error getting blueprint config:', error);
      throw error;
    }
  };

  const validateBlueprintConfig = async (configPath = 'blueprint_cnf.json') => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/validate-config?path=${encodeURIComponent(configPath)}`);
      return response.data;
    } catch (error) {
      console.error('Error validating blueprint config:', error);
      throw error;
    }
  };

  const contextValue = {
    // State
    rootPath,
    fileTree,
    selectedFile,
    fileContent,
    openTabs,
    activeTab,
    autoRefresh,
    environments,
    selectedEnvironment,
    websocket,
    buildStatus,
    buildOutput,
    outputFiles,
    loading,
    initializing,
    namespace,
    
    // Actions
    setRootPath: setBlueprintRootPath,
    setSelectedFile,
    setFileContent,
    setActiveTab,
    setAutoRefresh,
    setSelectedEnvironment,
    setBuildOutput,
    setNamespace,
    
    // Tab Management
    switchToTab,
    closeTab,
    updateTabContent,
    
    // API Methods
    refreshFileTree,
    loadFileContent,
    saveFileContent,
    createFile,
    deleteFile,
    createDirectory,
    renameFile,
    buildBlueprint,
    cancelBuild,
    loadOutputFiles,
    validateBlueprint,
    activateBlueprint,
    getBlueprintConfig,
    validateBlueprintConfig,
    loadEnvironments
  };

  return (
    <BlueprintContext.Provider value={contextValue}>
      {children}
    </BlueprintContext.Provider>
  );
}

export default BlueprintContext;