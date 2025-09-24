import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../ui/card';
import { Button } from '../../../ui/button';
import { Input } from '../../../ui/input';
import { Label } from '../../../ui/label';
import { Badge } from '../../../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../ui/select';
import { toast } from 'sonner';

import EntityEditor from '../EntityEditor';
import EnvironmentOverrides from '../EnvironmentOverrides';
import ConfigurationAPI from '../ConfigurationAPI';

// Icons
import { 
  Plus, 
  Settings, 
  FileText, 
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react';

export default function MessageConfigurationSection({ entityDefinitions, uiConfig, onConfigurationChange }) {
  const [selectedSchema, setSelectedSchema] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [showCreateSchemaForm, setShowCreateSchemaForm] = useState(false);
  const [showCreateEntityForm, setShowCreateEntityForm] = useState(false);
  const [newSchemaNamespace, setNewSchemaNamespace] = useState('');
  const [newEntityType, setNewEntityType] = useState('');
  const [newEntityName, setNewEntityName] = useState('');
  const [saving, setSaving] = useState(false);

  // Get message config entity types
  const messageEntityTypes = entityDefinitions?.fileMappings?.messageConfigs?.entities || [];
  const schemas = uiConfig?.schemas || [];

  // Filter entities for message configurations
  const getMessageEntities = (schema) => {
    return schema.configurations.filter(entity => 
      messageEntityTypes.includes(entity.entityType)
    );
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
        setShowCreateSchemaForm(false);
        await onConfigurationChange(); // Reload configuration
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

  const createEntity = async () => {
    if (!newEntityType || !newEntityName.trim() || !selectedSchema) {
      toast.error('Please fill all required fields');
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.createEntity({
        entityType: newEntityType,
        name: newEntityName.trim(),
        baseConfig: {},
        schemaId: selectedSchema.id
      });

      if (result.success) {
        toast.success(`Entity "${newEntityName}" created successfully`);
        setNewEntityType('');
        setNewEntityName('');
        setShowCreateEntityForm(false);
        await onConfigurationChange(); // Reload configuration
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
        await onConfigurationChange(); // Reload configuration
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
        await onConfigurationChange(); // Reload configuration
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

  const generateMessageFiles = async () => {
    if (!selectedSchema) {
      toast.error('Please select a schema first');
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.generateFiles({
        schemaId: selectedSchema.id,
        environments: entityDefinitions?.environments || []
      });

      if (result.success) {
        const messageFiles = result.files.filter(file => 
          file.path.includes('configs/messages') || file.filename.startsWith('config')
        );
        toast.success(`Generated ${messageFiles.length} message configuration files`);
        console.log('Generated message files:', messageFiles);
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

  const createRootConfiguration = async () => {
    if (!selectedSchema) {
      toast.error('No schema selected');
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.createEntity({
        entityType: 'transformation', // Use transformation as default for message root config
        name: 'Root Configuration',
        baseConfig: {},
        schemaId: selectedSchema.id
      });

      if (result.success) {
        toast.success('Root Configuration created successfully');
        await onConfigurationChange(); // Reload configuration
      } else {
        toast.error('Failed to create Root Configuration');
      }
    } catch (error) {
      console.error('Failed to create Root Configuration:', error);
      toast.error(`Failed to create Root Configuration: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  const getEntityTypeColor = (entityType) => {
    switch (entityType) {
      case 'binaryAssets':
        return 'bg-orange-100 text-orange-800';
      case 'imageModeration':
      case 'textModeration':
        return 'bg-yellow-100 text-yellow-800';
      case 'transformation':
        return 'bg-indigo-100 text-indigo-800';
      case 'discoveryFeatures':
        return 'bg-pink-100 text-pink-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="h-full flex">
      {/* Left Panel - Schema and Entity Management */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Schema Management */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900">Message Configuration Schemas</h3>
            <div className="flex space-x-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={generateMessageFiles}
                disabled={!selectedSchema || saving}
                title="Generate message configuration files"
              >
                <FileText className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowCreateSchemaForm(!showCreateSchemaForm)}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {showCreateSchemaForm && (
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
                    setShowCreateSchemaForm(false);
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
            {schemas.map(schema => {
              const messageEntities = getMessageEntities(schema);
              return (
                <div
                  key={schema.id}
                  className={`p-2 rounded cursor-pointer transition-colors ${
                    selectedSchema?.id === schema.id
                      ? 'bg-blue-100 border border-blue-300'
                      : 'hover:bg-gray-100'
                  }`}
                  onClick={() => setSelectedSchema(schema)}
                >
                  <div className="font-medium text-sm">{schema.namespace}</div>
                  <div className="text-xs text-gray-600">
                    {messageEntities.length} message entities
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Entity Management */}
        {selectedSchema && (
          <div className="flex-1 overflow-hidden">
            <div className="p-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">Message Entities</h4>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCreateEntityForm(!showCreateEntityForm)}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>

              {showCreateEntityForm && (
                <Card className="mb-3">
                  <CardContent className="p-3 space-y-3">
                    <div>
                      <Label className="text-xs">Entity Type</Label>
                      <Select value={newEntityType} onValueChange={setNewEntityType}>
                        <SelectTrigger className="h-8">
                          <SelectValue placeholder="Select entity type" />
                        </SelectTrigger>
                        <SelectContent>
                          {messageEntityTypes.map((type) => (
                            <SelectItem key={type} value={type}>
                              <div className="flex items-center space-x-2">
                                <FileText className="h-4 w-4" />
                                <span>{entityDefinitions?.entityTypes[type]?.title || type}</span>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <Label className="text-xs">Entity Name</Label>
                      <Input
                        placeholder="Enter entity name"
                        value={newEntityName}
                        onChange={(e) => setNewEntityName(e.target.value)}
                        className="h-8"
                      />
                    </div>

                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        onClick={createEntity}
                        disabled={!newEntityType || !newEntityName.trim() || saving}
                        className="h-7 text-xs"
                      >
                        Create
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={createRootConfiguration}
                        disabled={!selectedSchema || saving}
                        className="h-7 text-xs"
                      >
                        Add Root Config
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setShowCreateEntityForm(false);
                          setNewEntityType('');
                          setNewEntityName('');
                        }}
                        className="h-7 text-xs"
                      >
                        Cancel
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>

            {/* Entity List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {getMessageEntities(selectedSchema).map(entity => (
                <div
                  key={entity.id}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedEntity?.id === entity.id
                      ? 'bg-blue-50 border-blue-300 shadow-sm'
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}
                  onClick={() => setSelectedEntity(entity)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <Settings className="h-4 w-4" />
                        <span className="font-medium text-sm truncate">
                          {entity.name}
                        </span>
                        {!entity.enabled && (
                          <EyeOff className="h-3 w-3 text-gray-400" />
                        )}
                      </div>
                      
                      <Badge 
                        variant="secondary" 
                        className={`text-xs ${getEntityTypeColor(entity.entityType)}`}
                      >
                        {entityDefinitions?.entityTypes[entity.entityType]?.title || entity.entityType}
                      </Badge>

                      {/* Inheritance */}
                      {entity.inherit && entity.inherit.length > 0 && (
                        <div className="mt-2 text-xs text-gray-600">
                          <div className="font-medium">Inherits from:</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {entity.inherit.map(inherit => (
                              <Badge key={inherit} variant="outline" className="text-xs">
                                {inherit}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Environment Overrides */}
                      {entity.environmentOverrides && Object.keys(entity.environmentOverrides).length > 0 && (
                        <div className="mt-2 text-xs text-gray-600">
                          <div className="font-medium">Environment overrides:</div>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {Object.keys(entity.environmentOverrides).map(env => (
                              <Badge key={env} variant="outline" className="text-xs">
                                {env}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteEntity(entity.id);
                      }}
                      className="h-6 w-6 p-0 text-gray-400 hover:text-red-600"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}

              {getMessageEntities(selectedSchema).length === 0 && (
                <div className="text-center py-8">
                  <FileText className="h-8 w-8 mx-auto text-gray-300 mb-2" />
                  <div className="text-sm text-gray-500 mb-1">No message entities yet</div>
                  <div className="text-xs text-gray-400">
                    Click the + button to create your first message entity
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
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
              availableEntities={selectedSchema ? getMessageEntities(selectedSchema) : []}
            />
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Settings className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No entity selected
              </h3>
              <p className="text-gray-600 mb-4">
                {selectedSchema 
                  ? 'Select a message entity from the left panel to view and edit its configuration'
                  : 'Select a schema first, then choose an entity to configure'
                }
              </p>
              {selectedSchema && (
                <p className="text-sm text-gray-500">
                  Or create a new message entity using the + button
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}