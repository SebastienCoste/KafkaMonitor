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
  const [blueprints, setBlueprints] = useState([]); // Multiple blueprints support
  const [activeBlueprint, setActiveBlueprint] = useState(null);
  const [integrationProjects, setIntegrationProjects] = useState([]); // NEW: Git integration projects
  const [showGitSelector, setShowGitSelector] = useState(false); // NEW: Git selector modal visibility

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
        console.log('🔄 Loading initial blueprint configuration...');
        console.log('📍 API_BASE_URL:', API_BASE_URL);
        setInitializing(true); // Set initializing to true at the start
        
        // Use fetch instead of axios for more reliable requests
        console.log('📡 Making config request...');
        const configResponse = await fetch(`${API_BASE_URL}/api/blueprint/config`);
        console.log('📡 Config response received, status:', configResponse.status);
        
        if (!configResponse.ok) {
          console.error('❌ Config request failed:', configResponse.status, configResponse.statusText);
          throw new Error(`Config request failed: ${configResponse.status} ${configResponse.statusText}`);
        }
        
        const config = await configResponse.json();
        console.log('📋 Loaded config:', config);
        console.log('📋 Config root_path:', config?.root_path);
        
        if (config && config.root_path) {
          console.log('✅ Config has root_path, initializing blueprint...');
          console.log('📂 Setting root path:', config.root_path);
          setRootPath(config.root_path);
          
          console.log('⚙️ Setting auto-refresh to false (FIX 4)');
          setAutoRefresh(false); // FIX 4: Always default to false, ignore backend config
          
          // Try to detect namespace
          console.log('🔍 Detecting namespace...');
          try {
            const namespaceResponse = await fetch(`${API_BASE_URL}/api/blueprint/namespace`);
            console.log('📡 Namespace response status:', namespaceResponse.status);
            
            if (namespaceResponse.ok) {
              const namespaceData = await namespaceResponse.json();
              console.log('📋 Namespace data received:', namespaceData);
              const detectedNamespace = namespaceData.namespace || '';
              console.log('🏷️ Detected namespace:', detectedNamespace);
              setNamespace(detectedNamespace);
              
              // Add to blueprints array
              const newBlueprint = {
                id: Date.now().toString(),
                rootPath: config.root_path,
                namespace: detectedNamespace,
                name: detectedNamespace || config.root_path.split('/').pop() || config.root_path
              };
              console.log('📚 Adding blueprint to array:', newBlueprint);
              setBlueprints([newBlueprint]);
              setActiveBlueprint(newBlueprint.id);
              console.log('✅ Blueprint added and activated');
            } else {
              console.warn('⚠️ Namespace request failed with status:', namespaceResponse.status);
            }
          } catch (error) {
            console.warn('⚠️ Could not detect namespace:', error);
          }
          
          // Auto-load file tree if root path is set (with timeout and non-blocking)
          console.log('📁 Loading file tree with timeout...');
          try {
            const fileTreeController = new AbortController();
            const fileTreeTimeout = setTimeout(() => {
              console.warn('⏰ File tree request timeout after 5 seconds');
              fileTreeController.abort();
            }, 5000);

            const fileTreeResponse = await fetch(`${API_BASE_URL}/api/blueprint/file-tree`, {
              signal: fileTreeController.signal
            });
            clearTimeout(fileTreeTimeout);
            console.log('📡 File tree response received, status:', fileTreeResponse.status);
            
            if (fileTreeResponse.ok) {
              const fileTreeData = await fileTreeResponse.json();
              console.log('📋 File tree response data length:', fileTreeData?.files?.length || 0);
              setFileTree(fileTreeData.files || []);
              console.log('✅ File tree loaded successfully');
            } else {
              console.warn('⚠️ File tree request failed:', fileTreeResponse.status, fileTreeResponse.statusText);
              // Don't block initialization for file tree failures
              setFileTree([]);
            }
          } catch (fileTreeError) {
            console.warn('⚠️ File tree loading failed (non-blocking):', fileTreeError.message);
            // Set empty file tree and continue initialization
            setFileTree([]);
          }
          
          console.log('🎉 Blueprint initialization completed!');
        } else {
          console.log('❌ No root path found in config, staying on setup screen');
          console.log('📋 Config object:', config);
        }
      } catch (error) {
        console.error('❌ Error loading initial config:', error);
        console.error('❌ Error details:', error.message);
        console.error('❌ Error stack:', error.stack);
      } finally {
        console.log('🏁 Setting initializing to false');
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

  // Load environments and integration projects on mount
  useEffect(() => {
    loadEnvironments();
    loadIntegrationProjects();
  }, []);

  const loadIntegrationProjects = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/integration/projects`);
      if (response.data.success) {
        setIntegrationProjects(response.data.projects || []);
        console.log(`✅ Loaded ${response.data.projects?.length || 0} integration projects`);
      }
    } catch (error) {
      console.error('❌ Failed to load integration projects:', error);
      setIntegrationProjects([]);
    }
  }, [API_BASE_URL]);

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
      
      const response = await fetch(`${API_BASE_URL}/api/blueprint/config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ root_path: path })
      });

      if (!response.ok) {
        throw new Error(`Failed to set blueprint path: ${response.status}`);
      }

      const data = await response.json();
      if (data.success) {
        // FIX 3: Reset all selections when path changes
        setSelectedFile(null);
        setOpenTabs([]);
        setActiveTab(null);
        setFileContent('');
        
        setRootPath(data.root_path);
        
        // Try to detect namespace
        let detectedNamespace = '';
        try {
          const namespaceResponse = await fetch(`${API_BASE_URL}/api/blueprint/namespace`);
          if (namespaceResponse.ok) {
            const namespaceData = await namespaceResponse.json();
            detectedNamespace = namespaceData.namespace || '';
            setNamespace(detectedNamespace);
          }
        } catch (error) {
          console.warn('Could not detect namespace:', error);
          setNamespace('');
        }

        // Add to blueprints array if not already present
        if (!blueprints.find(bp => bp.rootPath === data.root_path)) {
          const newBlueprint = {
            id: Date.now().toString(),
            rootPath: data.root_path,
            namespace: detectedNamespace,
            name: detectedNamespace || data.root_path.split('/').pop() || data.root_path
          };
          setBlueprints(prev => [...prev, newBlueprint]);
          setActiveBlueprint(newBlueprint.id);
        }
        
        // Immediately refresh file tree after setting path
        await refreshFileTree();
        
        console.log(`Blueprint path set to: ${data.root_path}`);
      } else {
        throw new Error('Failed to set blueprint path');
      }
    } catch (error) {
      console.error('Error setting blueprint path:', error);
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

  const validateBlueprint = async (filepath) => {
    try {
      setLoading(true);
      // Extract just the filename from the full path
      const filename = filepath.split('/').pop().split('\\').pop();
      
      console.log('🔍 Validating blueprint:', { filepath, filename, environment: selectedEnvironment });
      
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

  const activateBlueprint = async (filepath) => {
    try {
      setLoading(true);
      // Extract just the filename from the full path
      const filename = filepath.split('/').pop().split('\\').pop();
      
      console.log('🚀 Activating blueprint:', { filepath, filename, environment: selectedEnvironment });
      
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

  // Multi-blueprint management functions
  const addNewBlueprint = async () => {
    // Show Git project selector instead of file browser
    setShowGitSelector(true);
  };

  const handleGitProjectSelect = async (project) => {
    try {
      console.log('🔄 Handling Git project selection:', project);
      
      // Check if blueprint already exists for this project
      const existingBlueprint = blueprints.find(bp => bp.projectId === project.id);
      if (existingBlueprint) {
        console.log('✅ Blueprint already exists for this project, switching to it');
        switchBlueprint(existingBlueprint.id);
        setShowGitSelector(false);
        return;
      }

      // Create new blueprint from Git project
      // Use absolute_path from backend (works on all systems)
      const projectPath = project.absolute_path || project.path;
      const newBlueprint = {
        id: Date.now().toString(),
        projectId: project.id, // Link to Git project
        rootPath: projectPath,
        gitUrl: project.git_url,
        branch: project.branch,
        namespace: project.namespace || '',
        name: `${project.name} (${project.branch})`
      };

      console.log('📚 Adding new blueprint from Git project:', newBlueprint);

      // Add to blueprints list
      setBlueprints(prev => [...prev, newBlueprint]);
      
      // Set as active and load
      setActiveBlueprint(newBlueprint.id);
      await setBlueprintRootPath(projectPath);
      
      // Close Git selector modal
      setShowGitSelector(false);
      
      // Reload integration projects list
      await loadIntegrationProjects();
      
      console.log('✅ Blueprint added and activated');
    } catch (error) {
      console.error('❌ Error handling Git project selection:', error);
      throw error;
    }
  };

  const removeBlueprint = (blueprintId) => {
    setBlueprints(prev => {
      const filtered = prev.filter(bp => bp.id !== blueprintId);
      
      // If we're removing the active blueprint, switch to another or clear
      if (activeBlueprint === blueprintId) {
        if (filtered.length > 0) {
          const newActive = filtered[0];
          setActiveBlueprint(newActive.id);
          setBlueprintRootPath(newActive.rootPath);
        } else {
          setActiveBlueprint(null);
          setRootPath('');
          setNamespace('');
          setSelectedFile(null);
          setOpenTabs([]);
          setActiveTab(null);
          setFileContent('');
          setFileTree([]);
        }
      }
      
      return filtered;
    });
  };

  const switchBlueprint = async (blueprintId) => {
    const blueprint = blueprints.find(bp => bp.id === blueprintId);
    if (blueprint) {
      setActiveBlueprint(blueprintId);
      await setBlueprintRootPath(blueprint.rootPath);
    }
  };

  // Update namespace in blueprint when it changes
  useEffect(() => {
    if (activeBlueprint && namespace) {
      setBlueprints(prev => prev.map(bp => 
        bp.id === activeBlueprint 
          ? { ...bp, namespace, name: namespace || bp.name }
          : bp
      ));
    }
  }, [namespace, activeBlueprint]);

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
    blueprints,
    activeBlueprint,
    integrationProjects,
    showGitSelector,
    
    // Actions
    setRootPath: setBlueprintRootPath,
    setSelectedFile,
    setFileContent,
    setActiveTab,
    setAutoRefresh,
    setSelectedEnvironment,
    setBuildOutput,
    setNamespace,
    addBlueprint: addNewBlueprint,
    removeBlueprint,
    switchBlueprint,
    setShowGitSelector,
    handleGitProjectSelect,
    loadIntegrationProjects,
    
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