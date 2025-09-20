# Blueprint Creator Technical Design Document

## Project Overview

This document outlines the technical specifications for adding a **Blueprint Creator** tab to the existing KafkaMonitor application. The Blueprint Creator will provide a comprehensive UI for managing blueprint definitions, building them using the existing `buildBlueprint.sh` script, and deploying them to blueprint servers across different environments.

## Architecture Overview

### Existing Infrastructure
- **Frontend**: React application running on port 3000
- **Backend**: FastAPI Python server on port 8001
- **Current Tabs**: "Trace Viewer" and "gRPC Integration"
- **WebSocket**: Already implemented for real-time communication

### New Addition
- **Blueprint Creator Tab**: Complete blueprint management interface integrated seamlessly with existing architecture

## Blueprint Structure Definition

### File Organization
The blueprint system organizes files in a structured hierarchy:

```
<user-selected-root>/
├── blueprint_cnf.json          # Root configuration file
├── src/
│   ├── configs/
│   │   ├── global/            # Global configuration JSON files
│   │   │   └── global.json    # Example: environments, services, storage configs
│   │   └── messages/          # Message configuration JSON files
│   │       ├── configModeration.json
│   │       └── configTransformation.json
│   ├── searchExperience/      # Search experience definitions
│   │   ├── searchExperience.json
│   │   └── templates/         # Search query templates
│   │       ├── knnteamsearchid.json
│   │       └── teambycityandratingid.json
│   ├── transformSpecs/        # JSLT transformation files
│   │   └── userPost_transform.jslt
│   └── protobuf/             # Protocol buffer definitions
│       └── com/path/to/      # Namespace-based folder structure
│           └── MyMessage.proto
└── out/                      # Build output directory
    └── blueprintXXX.tgz      # Generated blueprint archives
```

### Configuration Examples

**blueprint_cnf.json Structure:**
```json
{
  "namespace": "ea.cadie.fy26.veewan",
  "version": "git_version",
  "owner": "scoste@ea.com", 
  "description": "Usage example for development",
  "schemas": [{
    "namespace": "ea.cadie.fy26.veewan.internal.v2",
    "global": ["global.json"],
    "messages": ["configModeration.json", "configTransformation.json"]
  }],
  "transformSpecs": ["moderation_transform.jslt"],
  "searchExperience": {
    "configs": ["searchExperience.json", "searchExperience2.json"],
    "templates": ["knnteamsearchid.json", "teambycityandratingid.json"]
  }
}
```

## Backend Implementation

### FastAPI Extensions

#### New Endpoints

```python
# File System Operations
GET /api/blueprint/browse-folder          # Directory browser for root selection
GET /api/blueprint/file-tree             # Current blueprint file structure  
GET /api/blueprint/file-content/{path}   # Read file content
PUT /api/blueprint/file-content/{path}   # Save file content
POST /api/blueprint/create-file          # Create new file
DELETE /api/blueprint/delete-file/{path} # Delete file
POST /api/blueprint/upload-file          # Upload file with drag-and-drop

# Blueprint Operations  
GET /api/blueprint/config                # Get current blueprint root path
PUT /api/blueprint/config                # Set blueprint root path
POST /api/blueprint/build                # Execute buildBlueprint.sh
GET /api/blueprint/build-status          # Get build status and logs
GET /api/blueprint/output-files          # List generated .tgz files

# Environment & Deployment
GET /api/blueprint/environments          # List available environments
POST /api/blueprint/validate/{filename}  # Validate .tgz with blueprint server
POST /api/blueprint/activate/{filename}  # Activate .tgz with blueprint server

# File Watching
GET /api/blueprint/refresh               # Manual refresh file system
PUT /api/blueprint/auto-refresh          # Enable/disable auto-refresh
```

#### WebSocket Extensions

```python
# Extend existing WebSocket for real-time features
@router.websocket("/ws/blueprint")
async def blueprint_websocket(websocket: WebSocket):
    # Real-time build console output
    # File system change notifications  
    # Auto-refresh updates every 30 seconds
```

#### Configuration Integration

**Environment Files Enhancement (`backend/config/environments/*.yaml`):**
```yaml
# Add to existing dev.yaml, prod.yaml, test.yaml, int.yaml, load.yaml
blueprint_server:
  base_url: "https://blueprint-server.example.com"
  validate_path: "/api/v1/blueprint/validate"
  activate_path: "/api/v1/blueprint/activate"
  auth_header_name: "X-API-Key"
  auth_header_value: "your-api-key-here"
```

#### File Operations Implementation

```python
# backend/app/blueprint/file_manager.py
class BlueprintFileManager:
    def __init__(self, root_path: str):
        self.root_path = root_path
        
    def read_file(self, relative_path: str) -> str:
        # Read file content with proper encoding
        
    def write_file(self, relative_path: str, content: str):
        # Write file with atomic operations
        
    def create_directory(self, relative_path: str):
        # Create directory structure
        
    def delete_file(self, relative_path: str):
        # Safe file deletion
        
    def list_directory(self, relative_path: str = "") -> List[FileInfo]:
        # Return file tree structure
        
    def watch_changes(self) -> AsyncIterator[FileChangeEvent]:
        # File system monitoring for auto-refresh
```

#### Build Process Implementation

```python
# backend/app/blueprint/build_manager.py
class BlueprintBuildManager:
    async def execute_build(self, root_path: str, websocket: WebSocket = None):
        # Execute buildBlueprint.sh from root_path
        # Stream output to WebSocket if provided
        # Return build status and generated files
        
    async def deploy_blueprint(self, tgz_file: str, environment: str, action: str):
        # action: "validate" or "activate"  
        # Use environment config for API calls
        # Return deployment result
```

### Data Models

```python
# backend/app/models/blueprint.py
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class FileInfo(BaseModel):
    name: str
    path: str
    type: str  # "file" | "directory"  
    size: Optional[int]
    modified: datetime
    
class BlueprintConfig(BaseModel):
    namespace: str
    version: str
    owner: str
    description: str
    schemas: List[Dict[str, Any]]
    transformSpecs: List[str]
    searchExperience: Dict[str, Any]
    
class BuildResult(BaseModel):
    success: bool
    output: str
    generated_files: List[str]
    execution_time: float
    
class DeploymentResult(BaseModel):
    success: bool
    status_code: int
    response: str
    environment: str
    action: str  # "validate" | "activate"
```

## Frontend Implementation

### React Component Structure

```
frontend/src/components/blueprint/
├── BlueprintCreator.js           # Main tab component
├── FileExplorer/
│   ├── FileTree.js              # Left sidebar file browser
│   ├── FileUpload.js            # Drag-and-drop upload
│   └── DirectoryPicker.js       # Root folder selection
├── Editors/
│   ├── JsonEditor.js            # JSON file editor with syntax highlighting  
│   ├── JsltEditor.js            # JSLT transformation editor
│   ├── ProtoEditor.js           # Protocol buffer editor
│   └── TextEditor.js            # Generic text editor
├── BuildPanel/
│   ├── BuildControls.js         # Build trigger and settings
│   ├── ConsoleOutput.js         # Real-time build console
│   └── OutputFiles.js           # Generated .tgz file list
├── Deployment/
│   ├── EnvironmentSelector.js   # Environment dropdown
│   ├── DeploymentPanel.js       # Validate/Activate controls
│   └── DeploymentResults.js     # API response display
└── Common/
    ├── BlueprintContext.js      # State management
    └── WebSocketManager.js      # Real-time communication
```

### Main Blueprint Creator Component

```jsx
// frontend/src/components/blueprint/BlueprintCreator.js
import React, { useState, useEffect, useContext } from 'react';
import { BlueprintContext } from './Common/BlueprintContext';

export function BlueprintCreator() {
  const { 
    rootPath, 
    setRootPath,
    fileTree, 
    refreshFileTree,
    autoRefresh, 
    setAutoRefresh 
  } = useContext(BlueprintContext);
  
  return (
    <div className="blueprint-creator">
      <div className="blueprint-header">
        <DirectoryPicker onPathChange={setRootPath} currentPath={rootPath} />
        <div className="controls">
          <button onClick={refreshFileTree}>🔄 Refresh</button>
          <label>
            <input 
              type="checkbox" 
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (30s)
          </label>
        </div>
      </div>
      
      <div className="blueprint-layout">
        <div className="sidebar">
          <FileTree files={fileTree} />
        </div>
        
        <div className="main-content">
          <div className="editor-panel">
            <FileEditor />
          </div>
          
          <div className="console-panel">
            <BuildControls />
            <ConsoleOutput />
          </div>
        </div>
        
        <div className="deployment-panel">
          <EnvironmentSelector />
          <DeploymentPanel />
        </div>
      </div>
    </div>
  );
}
```

### File Tree Implementation

```jsx
// frontend/src/components/blueprint/FileExplorer/FileTree.js
export function FileTree({ files, onFileSelect, onFileAction }) {
  const renderTreeNode = (file, level = 0) => (
    <div key={file.path} className={`tree-node level-${level}`}>
      <div className="node-content" onClick={() => onFileSelect(file)}>
        <span className="icon">
          {file.type === 'directory' ? '📁' : getFileIcon(file.name)}
        </span>
        <span className="name">{file.name}</span>
        <div className="actions">
          <button onClick={(e) => handleAction(e, 'edit', file)}>✏️</button>
          <button onClick={(e) => handleAction(e, 'delete', file)}>🗑️</button>
        </div>
      </div>
      {file.type === 'directory' && file.children && (
        <div className="children">
          {file.children.map(child => renderTreeNode(child, level + 1))}
        </div>
      )}
    </div>
  );
  
  return (
    <div className="file-tree">
      <div className="tree-header">
        <h3>Blueprint Files</h3>
        <button onClick={() => onFileAction('create')}>➕ New File</button>
      </div>
      <div className="tree-content">
        {files.map(file => renderTreeNode(file))}
      </div>
      <FileUpload onUpload={onFileAction} />
    </div>
  );
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'json': return '📄';
    case 'jslt': return '🔧';  
    case 'proto': return '📋';
    default: return '📃';
  }
}
```

### Code Editor Integration

```jsx
// frontend/src/components/blueprint/Editors/JsonEditor.js
import { Controlled as CodeMirror } from 'react-codemirror2';
import 'codemirror/mode/javascript/javascript';
import 'codemirror/theme/material.css';

export function JsonEditor({ value, onChange, readOnly = false }) {
  return (
    <CodeMirror
      value={value}
      options={{
        mode: { name: 'javascript', json: true },
        theme: 'material',
        lineNumbers: true,
        readOnly: readOnly,
        autoCloseBrackets: true,
        matchBrackets: true,
        indentUnit: 2,
        tabSize: 2
      }}
      onBeforeChange={(editor, data, value) => {
        onChange(value);
      }}
    />
  );
}
```

### Build Console Implementation

```jsx
// frontend/src/components/blueprint/BuildPanel/ConsoleOutput.js
export function ConsoleOutput() {
  const [logs, setLogs] = useState([]);
  const [isBuilding, setIsBuilding] = useState(false);
  const { websocket } = useContext(BlueprintContext);
  
  useEffect(() => {
    if (websocket) {
      websocket.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'build_output') {
          setLogs(prev => [...prev, data.content]);
        }
        if (data.type === 'build_complete') {
          setIsBuilding(false);
        }
      });
    }
  }, [websocket]);
  
  return (
    <div className="console-output">
      <div className="console-header">
        <h4>Build Console</h4>
        <div className="status">
          {isBuilding ? <span className="building">🔄 Building...</span> : <span className="idle">⚪ Ready</span>}
        </div>
      </div>
      <div className="console-content">
        {logs.map((log, index) => (
          <div key={index} className="log-line">
            <span className="timestamp">{new Date().toISOString()}</span>
            <span className="content">{log}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### State Management

```jsx
// frontend/src/components/blueprint/Common/BlueprintContext.js
const BlueprintContext = createContext();

export function BlueprintProvider({ children }) {
  const [rootPath, setRootPath] = useState('');
  const [fileTree, setFileTree] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [environments, setEnvironments] = useState([]);
  const [selectedEnvironment, setSelectedEnvironment] = useState('dev');
  const [websocket, setWebsocket] = useState(null);
  
  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8001/ws/blueprint');
    ws.onopen = () => setWebsocket(ws);
    ws.onclose = () => setWebsocket(null);
    return () => ws.close();
  }, []);
  
  // Auto-refresh logic
  useEffect(() => {
    if (autoRefresh && rootPath) {
      const interval = setInterval(() => {
        refreshFileTree();
      }, 30000); // 30 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh, rootPath]);
  
  const refreshFileTree = async () => {
    if (rootPath) {
      const response = await fetch('/api/blueprint/file-tree');
      const tree = await response.json();
      setFileTree(tree);
    }
  };
  
  return (
    <BlueprintContext.Provider value={{
      rootPath, setRootPath,
      fileTree, setFileTree, refreshFileTree,
      selectedFile, setSelectedFile,
      autoRefresh, setAutoRefresh,
      environments, selectedEnvironment, setSelectedEnvironment,
      websocket
    }}>
      {children}
    </BlueprintContext.Provider>
  );
}
```

## Integration with Existing App

### Tab Navigation Update

```jsx
// frontend/src/components/Navigation.js (existing file to modify)
export function Navigation({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'traces', label: 'Trace Viewer', icon: '📊' },
    { id: 'grpc', label: 'gRPC Integration', icon: '🔌' },
    { id: 'blueprint', label: 'Blueprint Creator', icon: '🏗️' }  // NEW TAB
  ];
  
  return (
    <nav className="main-navigation">
      {tabs.map(tab => (
        <button
          key={tab.id}
          className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          <span className="icon">{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
```

### Main App Update

```jsx
// frontend/src/App.js (existing file to modify)  
import { BlueprintCreator } from './components/blueprint/BlueprintCreator';
import { BlueprintProvider } from './components/blueprint/Common/BlueprintContext';

function App() {
  const [activeTab, setActiveTab] = useState('traces');
  
  return (
    <div className="App">
      <Navigation activeTab={activeTab} onTabChange={setActiveTab} />
      
      <div className="content">
        {activeTab === 'traces' && <TraceViewer />}
        {activeTab === 'grpc' && <GrpcIntegration />}
        {activeTab === 'blueprint' && (
          <BlueprintProvider>
            <BlueprintCreator />
          </BlueprintProvider>
        )}
      </div>
    </div>
  );
}
```

## Development Dependencies

### Backend Requirements
```python
# Add to backend/requirements.txt
watchdog>=2.1.9      # File system monitoring
aiofiles>=0.8.0      # Async file operations  
```

### Frontend Requirements
```json
// Add to frontend/package.json dependencies
{
  "react-codemirror2": "^7.2.1",
  "codemirror": "^5.65.2",
  "react-dropzone": "^14.2.3"
}
```

## File Type Support

### Syntax Highlighting Configuration
```jsx
// File type to CodeMirror mode mapping
const FILE_MODES = {
  '.json': { name: 'javascript', json: true },
  '.jslt': { name: 'javascript' },
  '.proto': { name: 'protobuf' },
  '.yaml': { name: 'yaml' },
  '.yml': { name: 'yaml' }
};
```

### File Templates
```javascript
// Default content for new files
const FILE_TEMPLATES = {
  'blueprint_cnf.json': {
    namespace: "",
    version: "git_version", 
    owner: "",
    description: "",
    schemas: [],
    transformSpecs: [],
    searchExperience: { configs: [], templates: [] }
  },
  
  'global.json': {
    environments: {
      dev: {},
      test: {},
      int: {},
      load: {},
      prod: {}
    }
  },
  
  'transform.jslt': '{\n  "realId": ._system.id,\n  * - content, access, assets: .\n}',
  
  'Message.proto': 'syntax = "proto3";\n\npackage your.package.name;\n\nmessage YourMessage {\n  string id = 1;\n}'
};
```

## Error Handling & Validation

### Build Error Handling
```python
# backend/app/blueprint/build_manager.py
async def execute_build(self, root_path: str, websocket: WebSocket = None):
    try:
        # Validate prerequisites
        script_path = os.path.join(root_path, 'buildBlueprint.sh')
        if not os.path.exists(script_path):
            raise FileNotFoundError("buildBlueprint.sh not found")
            
        # Execute build with real-time output streaming
        process = await asyncio.create_subprocess_exec(
            'bash', script_path,
            cwd=root_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        # Stream output to WebSocket
        async for line in process.stdout:
            output = line.decode('utf-8').strip()
            if websocket:
                await websocket.send_json({
                    'type': 'build_output',
                    'content': output
                })
                
        # Wait for completion and return result
        await process.wait()
        return BuildResult(
            success=process.returncode == 0,
            output=output,
            generated_files=self._find_generated_files(root_path),
            execution_time=time.time() - start_time
        )
        
    except Exception as e:
        return BuildResult(
            success=False,
            output=str(e),
            generated_files=[],
            execution_time=0
        )
```

### File Validation
```jsx
// Frontend file validation
const validateJsonFile = (content) => {
  try {
    JSON.parse(content);
    return { valid: true };
  } catch (error) {
    return { 
      valid: false, 
      error: error.message,
      line: error.lineNumber || 0
    };
  }
};

const validateBlueprintConfig = (config) => {
  const required = ['namespace', 'version', 'owner'];
  const missing = required.filter(field => !config[field]);
  
  return {
    valid: missing.length === 0,
    errors: missing.map(field => `Missing required field: ${field}`)
  };
};
```

## Security Considerations

### File System Access Control
```python
# Restrict file operations to selected root directory
def validate_path(root_path: str, requested_path: str) -> bool:
    absolute_root = os.path.abspath(root_path)
    absolute_requested = os.path.abspath(os.path.join(root_path, requested_path))
    return absolute_requested.startswith(absolute_root)
```

### Upload Restrictions
```python
# File upload validation  
ALLOWED_EXTENSIONS = {'.json', '.jslt', '.proto', '.yaml', '.yml'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_upload(file):
    if file.size > MAX_FILE_SIZE:
        raise ValueError("File too large")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type {ext} not allowed")
```

## Testing Strategy

### Backend Tests
```python
# tests/test_blueprint_api.py
def test_file_tree_endpoint():
    # Test file system browsing
    
def test_build_execution():
    # Test buildBlueprint.sh execution
    
def test_deployment_api():
    # Test blueprint server integration
    
def test_file_operations():
    # Test CRUD operations on files
```

### Frontend Tests  
```jsx
// tests/blueprint/BlueprintCreator.test.js
describe('Blueprint Creator', () => {
  test('renders file tree correctly', () => {
    // Component rendering tests
  });
  
  test('handles file editing', () => {
    // File editing workflow tests
  });
  
  test('executes build process', () => {
    // Build process integration tests  
  });
});
```

## Performance Considerations

### File System Optimization
- Implement file system caching for large directories
- Use debounced refresh to avoid excessive API calls
- Lazy loading for deep directory structures

### WebSocket Optimization
- Buffer console output to avoid overwhelming the UI
- Implement connection recovery for interrupted builds
- Rate limiting for auto-refresh notifications

### Code Editor Performance
- Implement virtual scrolling for large files
- Lazy load editor modes and themes
- Debounced auto-save functionality

## Deployment Instructions

### Development Setup
1. **Backend**: Add new blueprint endpoints to existing FastAPI server
2. **Frontend**: Install new dependencies and add Blueprint tab components  
3. **Configuration**: Update environment files with blueprint server configurations
4. **Database**: No database changes required (file-system based)

### Environment Configuration
Each environment needs blueprint server configuration in `backend/config/environments/<env>.yaml`:
```yaml
blueprint_server:
  base_url: "https://blueprint-<env>.company.com"
  validate_path: "/api/v1/blueprint/validate"
  activate_path: "/api/v1/blueprint/activate"
  auth_header_name: "Authorization" 
  auth_header_value: "Bearer <env-specific-token>"
```

### Launch Procedure
1. Start backend with existing `run_local.py` script
2. Frontend automatically includes new Blueprint Creator tab
3. No additional services required - integrates with existing infrastructure

## Future Enhancements

### Version 1.0 Scope (Current Implementation)
- Complete file management system
- Build process integration  
- Blueprint server deployment
- Real-time console output
- Multi-environment support

### Future Considerations
- Git integration for version control
- Blueprint templates and wizards
- Visual protobuf schema designer
- Collaborative editing features
- Blueprint testing and validation framework
- Integration with CI/CD pipelines

---

This technical design provides a complete specification for implementing the Blueprint Creator as a seamless extension to the existing KafkaMonitor application. The design maintains consistency with existing patterns while providing comprehensive blueprint management capabilities.