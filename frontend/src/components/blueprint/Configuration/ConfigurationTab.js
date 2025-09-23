import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Alert, AlertDescription } from '../../ui/alert';
import { toast } from 'sonner';

// Configuration components
import EntityEditor from './EntityEditor';
import EnvironmentOverrides from './EnvironmentOverrides';
import ConfigurationAPI from './ConfigurationAPI';
import SchemaManager from './SchemaManager';

// Icons
import { 
  Settings, 
  Plus, 
  FileText, 
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Save,
  Eye,
  Cog
} from 'lucide-react';

export default function ConfigurationTab() {
  // State management
  const [entityDefinitions, setEntityDefinitions] = useState(null);
  const [uiConfig, setUiConfig] = useState(null);
  const [activeSchema, setActiveSchema] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  
  // Form states
  const [newSchemaNamespace, setNewSchemaNamespace] = useState('');
  const [showNewSchemaForm, setShowNewSchemaForm] = useState(false);
  const [selectedEnvironments, setSelectedEnvironments] = useState(['DEV', 'TEST', 'INT', 'LOAD', 'PROD']);

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
      
      // Set active schema to first one if available
      if (uiConfigData.config.schemas && uiConfigData.config.schemas.length > 0) {
        setActiveSchema(uiConfigData.config.schemas[0]);
      }

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

  const createSchema = async () => {
    if (!newSchemaNamespace.trim()) {
      toast.error('Please enter a namespace');
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.createSchema({
        namespace: newSchemaNamespace.trim()
      });

      if (result.success) {
        toast.success('Schema created successfully');
        setNewSchemaNamespace('');
        setShowNewSchemaForm(false);
        await loadConfiguration(); // Reload to get updated config
      } else {
        toast.error('Failed to create schema');
      }
    } catch (error) {
      console.error('Failed to create schema:', error);
      toast.error(`Failed to create schema: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const createEntity = async (entityType, name, baseConfig = {}) => {
    if (!activeSchema) {
      toast.error('No active schema selected');
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.createEntity({
        entityType,
        name,
        baseConfig,
        schemaId: activeSchema.id
      });

      if (result.success) {
        toast.success(`Entity "${name}" created successfully`);
        await loadConfiguration(); // Reload to get updated config
      } else {
        toast.error('Failed to create entity');
      }
    } catch (error) {
      console.error('Failed to create entity:', error);
      toast.error(`Failed to create entity: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const updateEntity = async (entityId, updates) => {
    setSaving(true);
    try {
      const result = await ConfigurationAPI.updateEntity(entityId, updates);

      if (result.success) {
        toast.success('Entity updated successfully');
        await loadConfiguration(); // Reload to get updated config
      } else {
        toast.error('Failed to update entity');
      }
    } catch (error) {
      console.error('Failed to update entity:', error);
      toast.error(`Failed to update entity: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const deleteEntity = async (entityId) => {
    if (!confirm('Are you sure you want to delete this entity?')) {
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.deleteEntity(entityId);

      if (result.success) {
        toast.success('Entity deleted successfully');
        setSelectedEntity(null);
        await loadConfiguration(); // Reload to get updated config
      } else {
        toast.error('Failed to delete entity');
      }
    } catch (error) {
      console.error('Failed to delete entity:', error);
      toast.error(`Failed to delete entity: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const generateFiles = async () => {
    if (!activeSchema) {
      toast.error('No active schema selected');
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.generateFiles({
        schemaId: activeSchema.id,
        environments: selectedEnvironments
      });

      if (result.success) {
        toast.success(`Generated ${result.files.length} configuration files`);
        console.log('Generated files:', result.files);
      } else {
        toast.error(`Failed to generate files: ${result.errors.join(', ')}`);
      }
    } catch (error) {
      console.error('Failed to generate files:', error);
      toast.error(`Failed to generate files: ${error.message}`);
    } finally {
      setSaving(false);
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
              <h1 className="text-xl font-bold text-gray-900">Blueprint Configuration</h1>
              <p className="text-sm text-gray-600">
                {activeSchema 
                  ? `Active Schema: ${activeSchema.namespace} (${activeSchema.configurations.length} entities)`
                  : 'No schema selected'
                }
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
              Validate
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={generateFiles}
              disabled={!activeSchema || saving}
            >
              <FileText className="h-4 w-4 mr-2" />
              {saving ? 'Generating...' : 'Generate Files'}
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

        {/* Environment Selection */}
        <div className="mt-4 flex items-center space-x-4">
          <Label className="text-sm font-medium">Target Environments:</Label>
          <div className="flex items-center space-x-2">
            {entityDefinitions?.environments?.map(env => (
              <div key={env} className="flex items-center space-x-1">
                <input
                  type="checkbox"
                  id={`env-${env}`}
                  checked={selectedEnvironments.includes(env)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedEnvironments([...selectedEnvironments, env]);
                    } else {
                      setSelectedEnvironments(selectedEnvironments.filter(e => e !== env));
                    }
                  }}
                  className="rounded"
                />
                <Label htmlFor={`env-${env}`} className="text-xs">{env}</Label>
              </div>
            ))}
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

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Schema and Entity Management */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          {/* Schema Management */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">Configuration Schemas</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowNewSchemaForm(!showNewSchemaForm)}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>

            {showNewSchemaForm && (
              <div className="mb-3 p-3 bg-gray-50 rounded-lg">
                <Input
                  placeholder="Schema namespace (e.g., ea.example.v1)"
                  value={newSchemaNamespace}
                  onChange={(e) => setNewSchemaNamespace(e.target.value)}
                  className="mb-2"
                />
                <div className="flex space-x-2">
                  <Button
                    size="sm"
                    onClick={createSchema}
                    disabled={saving || !newSchemaNamespace.trim()}
                  >
                    Create
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setShowNewSchemaForm(false);
                      setNewSchemaNamespace('');
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {/* Schema List */}
            <div className="space-y-2">
              {uiConfig?.schemas?.map(schema => (
                <div
                  key={schema.id}
                  className={`p-2 rounded cursor-pointer transition-colors ${
                    activeSchema?.id === schema.id
                      ? 'bg-blue-100 border border-blue-300'
                      : 'hover:bg-gray-100'
                  }`}
                  onClick={() => setActiveSchema(schema)}
                >
                  <div className="font-medium text-sm">{schema.namespace}</div>
                  <div className="text-xs text-gray-600">
                    {schema.configurations.length} entities
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Entity List */}
          <div className="flex-1 overflow-hidden">
            <SchemaManager
              schema={activeSchema}
              entityDefinitions={entityDefinitions}
              selectedEntity={selectedEntity}
              onSelectEntity={setSelectedEntity}
              onCreateEntity={createEntity}
              onDeleteEntity={deleteEntity}
            />
          </div>
        </div>

        {/* Right Panel - Entity Editor */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedEntity ? (
            <div className="h-full">
              <EntityEditor
                entity={selectedEntity}
                entityDefinition={entityDefinitions?.entityTypes[selectedEntity.entityType]}
                environments={entityDefinitions?.environments || []}
                onUpdateEntity={updateEntity}
                onDeleteEntity={deleteEntity}
              />
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <Cog className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No entity selected
                </h3>
                <p className="text-gray-600 mb-4">
                  Select an entity from the left panel to view and edit its configuration
                </p>
                {activeSchema && (
                  <p className="text-sm text-gray-500">
                    Or create a new entity using the + button in the entity list
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}