import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription } from '../ui/alert';
import { toast } from 'sonner';

// Blueprint Creator Components
import { useBlueprintContext } from './Common/BlueprintContext';
import FileTree from './FileExplorer/FileTree';
import FileBrowser from './FileExplorer/FileBrowser';
import FileUpload from './FileExplorer/FileUpload';
import CodeEditor from './Editors/CodeEditor';
import BuildControls from './BuildPanel/BuildControls';
import ConsoleOutput from './BuildPanel/ConsoleOutput';
import OutputFiles from './BuildPanel/OutputFiles';
import EnvironmentSelector from './Deployment/EnvironmentSelector';
import DeploymentPanel from './Deployment/DeploymentPanel';

// Icons
import { 
  FolderOpen, 
  FileText, 
  Settings, 
  Play, 
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react';

export default function BlueprintCreator() {
  const {
    rootPath,
    fileTree,
    selectedFile,
    fileContent,
    autoRefresh,
    setAutoRefresh,
    loading,
    refreshFileTree,
    loadOutputFiles,
    setRootPath: setBlueprintRootPath
  } = useBlueprintContext();

  const [activeTab, setActiveTab] = useState('files');

  // Load output files when root path changes
  useEffect(() => {
    if (rootPath) {
      loadOutputFiles();
    }
  }, [rootPath, loadOutputFiles]);

  // Status indicator component
  const StatusIndicator = () => {
    if (loading) {
      return (
        <div className="flex items-center space-x-2 text-blue-600">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      );
    }
    
    if (!rootPath) {
      return (
        <div className="flex items-center space-x-2 text-gray-500">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm">No root path selected</span>
        </div>
      );
    }
    
    return (
      <div className="flex items-center space-x-2 text-green-600">
        <CheckCircle className="h-4 w-4" />
        <span className="text-sm">Ready</span>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-slate-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FolderOpen className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Blueprint Creator</h1>
              <p className="text-sm text-gray-600">
                {rootPath || 'Select a blueprint root directory to get started'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <StatusIndicator />
            
            {rootPath && (
              <>
                <div className="flex items-center space-x-2">
                  <Label htmlFor="auto-refresh" className="text-sm">Auto-refresh</Label>
                  <input
                    id="auto-refresh"
                    type="checkbox"
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                    className="rounded"
                  />
                </div>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={refreshFileTree}
                  disabled={loading}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {!rootPath ? (
          // Initial setup view
          <div className="flex-1 flex items-center justify-center">
            <Card className="w-full max-w-2xl mx-4">
              <CardHeader className="text-center">
                <CardTitle className="flex items-center justify-center space-x-2">
                  <Settings className="h-6 w-6" />
                  <span>Setup Blueprint Creator</span>
                </CardTitle>
                <CardDescription>
                  Select your blueprint project root directory to begin managing blueprints
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FileBrowser />
                
                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-medium text-blue-900 mb-2">Expected Structure:</h4>
                  <pre className="text-xs text-blue-800 font-mono">
{`<root>/
├── blueprint_cnf.json
├── src/
│   ├── configs/
│   ├── transformSpecs/
│   └── protobuf/
└── out/`}
                  </pre>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          // Main blueprint interface
          <>
            {/* Left Sidebar - File Explorer */}
            <div className="w-80 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-semibold text-gray-900">Project Files</h2>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      // Allow changing the blueprint folder
                      const newPath = prompt('Enter new blueprint directory path:', rootPath || '');
                      if (newPath && newPath !== rootPath) {
                        setBlueprintRootPath(newPath).catch(error => {
                          toast.error(`Failed to change directory: ${error.message}`);
                        });
                      }
                    }}
                    title="Change Blueprint Directory"
                  >
                    <Settings className="h-4 w-4" />
                  </Button>
                </div>
                
                {rootPath && (
                  <div className="text-xs text-gray-600 bg-gray-50 p-2 rounded mb-3">
                    <strong>Current:</strong> {rootPath}
                  </div>
                )}
              </div>
              
              <div className="flex-1 overflow-hidden">
                <FileTree files={fileTree} />
              </div>
              
              <div className="p-4 border-t border-gray-200">
                <FileUpload />
              </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
              <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
                <div className="border-b border-gray-200 px-4">
                  <TabsList className="h-12">
                    <TabsTrigger value="files" className="flex items-center space-x-2">
                      <FileText className="h-4 w-4" />
                      <span>Files</span>
                    </TabsTrigger>
                    <TabsTrigger value="build" className="flex items-center space-x-2">
                      <Play className="h-4 w-4" />
                      <span>Build</span>
                    </TabsTrigger>
                    <TabsTrigger value="deploy" className="flex items-center space-x-2">
                      <Settings className="h-4 w-4" />
                      <span>Deploy</span>
                    </TabsTrigger>
                  </TabsList>
                </div>

                <div className="flex-1 overflow-hidden">
                  <TabsContent value="files" className="h-full m-0">
                    <div className="h-full flex flex-col">
                      {selectedFile ? (
                        <div className="flex-1 overflow-hidden">
                          <div className="h-full border-l border-gray-200">
                            <div className="p-4 bg-gray-50 border-b border-gray-200">
                              <div className="flex items-center justify-between">
                                <div>
                                  <h3 className="font-medium text-gray-900">{selectedFile}</h3>
                                  <p className="text-sm text-gray-600">
                                    {getFileExtension(selectedFile)} file
                                  </p>
                                </div>
                                <Badge variant="outline">
                                  {getFileType(selectedFile)}
                                </Badge>
                              </div>
                            </div>
                            <div className="flex-1">
                              <CodeEditor filePath={selectedFile} />
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="flex-1 flex items-center justify-center">
                          <div className="text-center">
                            <FileText className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                            <h3 className="text-lg font-medium text-gray-900 mb-2">
                              No file selected
                            </h3>
                            <p className="text-gray-600">
                              Select a file from the project tree to view and edit its contents
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="build" className="h-full m-0">
                    <div className="h-full grid grid-cols-1 lg:grid-cols-2">
                      <div className="p-4 border-r border-gray-200">
                        <BuildControls />
                        <div className="mt-6">
                          <OutputFiles />
                        </div>
                      </div>
                      <div className="p-4">
                        <ConsoleOutput />
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="deploy" className="h-full m-0">
                    <div className="h-full grid grid-cols-1 lg:grid-cols-2">
                      <div className="p-4 border-r border-gray-200">
                        <EnvironmentSelector />
                      </div>
                      <div className="p-4">
                        <DeploymentPanel />
                      </div>
                    </div>
                  </TabsContent>
                </div>
              </Tabs>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// Helper functions
function getFileExtension(filename) {
  return filename.split('.').pop()?.toLowerCase() || '';
}

function getFileType(filename) {
  const ext = getFileExtension(filename);
  switch (ext) {
    case 'json':
      return 'JSON';
    case 'jslt':
      return 'JSLT';
    case 'proto':
      return 'Protocol Buffer';
    case 'yaml':
    case 'yml':
      return 'YAML';
    case 'sh':
      return 'Shell Script';
    default:
      return 'Text';
  }
}