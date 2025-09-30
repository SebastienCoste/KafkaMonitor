import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Alert, AlertDescription } from '../../ui/alert';
import { toast } from 'sonner';

// Section components
import MessageConfigurationSection from './sections/MessageConfigurationSection';
import GlobalConfigurationSection from './sections/GlobalConfigurationSection';
import SearchExperienceSection from './sections/SearchExperienceSection';
import BlueprintCNFBuilder from './sections/BlueprintCNFBuilder';
import ConfigurationAPI from './ConfigurationAPI';

// Icons
import { 
  Settings, 
  Database, 
  Search,
  FileText,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  FlaskConical
} from 'lucide-react';

export default function ConfigurationManager() {
  // State management
  const [entityDefinitions, setEntityDefinitions] = useState(null);
  const [uiConfig, setUiConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [validationResult, setValidationResult] = useState(null);
  const [activeSection, setActiveSection] = useState('message-configs');

  // Initialize configuration
  useEffect(() => {
    loadConfiguration();
  }, []);

  const loadConfiguration = async () => {
    setLoading(true);
    try {
      // Load entity definitions
      const definitions = await ConfigurationAPI.getEntityDefinitions();
      setEntityDefinitions(definitions);

      // Load UI configuration
      const uiConfigData = await ConfigurationAPI.getUIConfig();
      setUiConfig(uiConfigData.config);

      if (uiConfigData.warnings && uiConfigData.warnings.length > 0) {
        uiConfigData.warnings.forEach(warning => {
          toast.warning(warning);
        });
      }

      toast.success('Configuration loaded successfully');
    } catch (error) {
      console.error('Failed to load configuration:', error);
      toast.error(`Failed to load configuration: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const validateConfiguration = async () => {
    setLoading(true);
    try {
      const result = await ConfigurationAPI.validateConfiguration();
      setValidationResult(result);

      if (result.valid) {
        toast.success('Configuration is valid');
      } else {
        toast.error(`Configuration has ${result.errors.length} errors`);
      }
    } catch (error) {
      console.error('Failed to validate configuration:', error);
      toast.error(`Failed to validate configuration: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  const generateAllFiles = async () => {
    setLoading(true);
    try {
      const result = await ConfigurationAPI.generateAllFiles();
      
      if (result.success) {
        toast.success(`Generated ${result.filesGenerated} configuration files across all schemas`);
      } else {
        // Handle specific error types
        if (result.error && result.error.includes('permission')) {
          toast.error(`Permission Error: ${result.error}. Please close any applications that might have these files open and ensure you have write permissions.`, {
            duration: 8000
          });
        } else {
          toast.error(result.error || 'Failed to generate files');
        }
      }
    } catch (error) {
      console.error('Failed to generate all files:', error);
      
      // Handle HTTP error responses
      if (error.message.includes('403') || error.message.includes('permission')) {
        toast.error('Permission denied: Please close any applications that have the blueprint files open and ensure you have write permissions to the directory.', {
          duration: 8000
        });
      } else if (error.message.includes('404')) {
        toast.error('Directory not found: Please check that the blueprint directory exists and is accessible.');
      } else {
        toast.error(`Failed to generate files: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading && !entityDefinitions) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Card className="w-full max-w-md mx-4">
          <CardContent className="p-8 text-center">
            <RefreshCw className="h-8 w-8 mx-auto mb-4 animate-spin text-blue-500" />
            <h3 className="text-lg font-semibold mb-2">Loading Configuration</h3>
            <p className="text-gray-600">Initializing blueprint configuration...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-slate-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <Settings className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Blueprint Configuration Manager</h1>
              <p className="text-sm text-gray-600">
                Manage configuration schemas, global settings, search experience, and blueprint composition
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={validateConfiguration}
              disabled={loading}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Validate All
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={generateAllFiles}
              disabled={loading}
            >
              <FileText className="h-4 w-4 mr-2" />
              Generate Files
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={loadConfiguration}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Validation Results */}
      {validationResult && (
        <div className="p-4">
          {validationResult.errors.length > 0 && (
            <Alert className="mb-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>Validation Errors:</strong>
                <ul className="mt-1 list-disc list-inside">
                  {validationResult.errors.map((error, index) => (
                    <li key={index} className="text-sm">{error}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {validationResult.warnings.length > 0 && (
            <Alert className="mb-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>Warnings:</strong>
                <ul className="mt-1 list-disc list-inside">
                  {validationResult.warnings.map((warning, index) => (
                    <li key={index} className="text-sm">{warning}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}

      {/* Main Configuration Sections */}
      <div className="flex-1 overflow-hidden">
        <Tabs value={activeSection} onValueChange={setActiveSection} className="h-full">
          <div className="bg-white border-b border-gray-200 px-4">
            <TabsList className="grid w-full grid-cols-4 max-w-2xl">
              <TabsTrigger value="message-configs" className="flex items-center space-x-2">
                <Settings className="h-4 w-4" />
                <span className="hidden sm:inline">Message Configs</span>
              </TabsTrigger>
              <TabsTrigger value="global-config" className="flex items-center space-x-2">
                <Database className="h-4 w-4" />
                <span className="hidden sm:inline">Global Config</span>
              </TabsTrigger>
              <TabsTrigger value="search-experience" className="flex items-center space-x-2">
                <Search className="h-4 w-4" />
                <span className="hidden sm:inline">Search Experience</span>
              </TabsTrigger>
              <TabsTrigger value="blueprint-builder" className="flex items-center space-x-2">
                <FileText className="h-4 w-4" />
                <span className="hidden sm:inline">Blueprint CNF</span>
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="message-configs" className="h-full m-0">
            <MessageConfigurationSection
              entityDefinitions={entityDefinitions}
              uiConfig={uiConfig}
              onConfigurationChange={loadConfiguration}
            />
          </TabsContent>

          <TabsContent value="global-config" className="h-full m-0">
            <GlobalConfigurationSection
              entityDefinitions={entityDefinitions}
              uiConfig={uiConfig}
              onConfigurationChange={loadConfiguration}
            />
          </TabsContent>

          <TabsContent value="search-experience" className="h-full m-0">
            <SearchExperienceSection
              entityDefinitions={entityDefinitions}
              uiConfig={uiConfig}
              onConfigurationChange={loadConfiguration}
            />
          </TabsContent>

          <TabsContent value="blueprint-builder" className="h-full m-0">
            <BlueprintCNFBuilder
              entityDefinitions={entityDefinitions}
              uiConfig={uiConfig}
              onConfigurationChange={loadConfiguration}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}