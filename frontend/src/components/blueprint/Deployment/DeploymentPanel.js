import React, { useState } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Alert, AlertDescription } from '../../ui/alert';
import { toast } from 'sonner';
import { 
  CheckCircle, 
  Play, 
  FileArchive, 
  AlertTriangle,
  Clock,
  RefreshCw
} from 'lucide-react';

export default function DeploymentPanel() {
  const {
    outputFiles,
    selectedEnvironment,
    validateBlueprint,
    activateBlueprint,
    loading,
    loadOutputFiles
  } = useBlueprintContext();

  const [selectedFile, setSelectedFile] = useState('');
  const [deploymentResults, setDeploymentResults] = useState([]);
  const [deploymentLoading, setDeploymentLoading] = useState(false);

  const handleValidate = async () => {
    if (!selectedFile) {
      toast.error('Please select a blueprint file to validate');
      return;
    }

    setDeploymentLoading(true);
    try {
      const result = await validateBlueprint(selectedFile);
      setDeploymentResults([{
        action: 'validate',
        timestamp: new Date(),
        ...result
      }, ...deploymentResults]);
      
      if (result.success) {
        toast.success('Blueprint validation successful');
      } else {
        toast.error(`Blueprint validation failed: ${result.error_message}`);
      }
    } catch (error) {
      toast.error(`Validation failed: ${error.message}`);
    } finally {
      setDeploymentLoading(false);
    }
  };

  // Script functionality removed as per FIX 1 requirement

  const handleActivate = async () => {
    if (!selectedFile) {
      toast.error('Please select a blueprint file to activate');
      return;
    }

    setDeploymentLoading(true);
    try {
      const result = await activateBlueprint(selectedFile);
      setDeploymentResults([{
        action: 'activate',
        timestamp: new Date(),
        ...result
      }, ...deploymentResults]);
      
      if (result.success) {
        toast.success('Blueprint activation successful');
      } else {
        toast.error(`Blueprint activation failed: ${result.error_message}`);
      }
    } catch (error) {
      toast.error(`Activation failed: ${error.message}`);
    } finally {
      setDeploymentLoading(false);
    }
  };

  const getStatusIcon = (success) => {
    return success ? (
      <CheckCircle className="h-4 w-4 text-green-500" />
    ) : (
      <AlertTriangle className="h-4 w-4 text-red-500" />
    );
  };

  const getActionBadge = (action) => {
    if (action === 'validate') {
      return (
        <Badge variant="outline" className="text-blue-600 border-blue-200">
          Validate
        </Badge>
      );
    } else {
      return (
        <Badge className="bg-green-500">
          Activate
        </Badge>
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* File Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileArchive className="h-5 w-5" />
            <span>Blueprint Selection</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                Select Blueprint File:
              </label>
              
              {outputFiles.length === 0 ? (
                <div className="text-center py-8">
                  <FileArchive className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                  <p className="text-gray-500 mb-4">No blueprint files found</p>
                  <Button
                    variant="outline"
                    onClick={loadOutputFiles}
                    disabled={loading}
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh Files
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {outputFiles.map((file, index) => (
                    <div
                      key={index}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedFile === file.path
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => setSelectedFile(file.path)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="font-medium text-sm">{file.name}</span>
                          <div className="text-xs text-gray-500">
                            {file.directory} • {Math.round(file.size / 1024)} KB
                          </div>
                        </div>
                        <input
                          type="radio"
                          checked={selectedFile === file.path}
                          onChange={() => setSelectedFile(file.path)}
                          className="text-blue-600"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {selectedFile && (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Selected for deployment to <strong>{selectedEnvironment.toUpperCase()}</strong>: {selectedFile}
                </AlertDescription>
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Deployment Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Deployment Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                variant="outline"
                onClick={handleValidate}
                disabled={!selectedFile || deploymentLoading || loading}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Validate
              </Button>
              <Button
                onClick={handleActivate}
                disabled={!selectedFile || deploymentLoading || loading}
              >
                <Play className="h-4 w-4 mr-2" />
                Activate
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Deployment Results */}
      {deploymentResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Deployment History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {deploymentResults.slice(0, 5).map((result, index) => (
                <div
                  key={index}
                  className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                >
                  {getStatusIcon(result.success)}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      {getActionBadge(result.action)}
                      <Badge variant="outline">
                        {result.environment?.toUpperCase()}
                      </Badge>
                      <span className="text-xs text-gray-500">
                        {result.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-sm">
                      {result.success ? (
                        <span className="text-green-700">
                          {result.action === 'validate' ? 'Validation' : 'Activation'} successful
                        </span>
                      ) : (
                        <span className="text-red-700">
                          {result.error_message || 'Operation failed'}
                        </span>
                      )}
                    </div>
                    {result.response && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-600 cursor-pointer">
                          Show response
                        </summary>
                        <pre className="text-xs bg-white p-2 rounded mt-1 overflow-x-auto">
                          {result.response}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Script Console removed as per FIX 1 requirement */}
    </div>
  );
}