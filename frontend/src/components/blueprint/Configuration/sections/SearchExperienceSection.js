import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../ui/card';
import { Button } from '../../../ui/button';
import { Input } from '../../../ui/input';
import { Label } from '../../../ui/label';
import { Badge } from '../../../ui/badge';
import { toast } from 'sonner';

import EntityEditor from '../EntityEditor';
import ConfigurationAPI from '../ConfigurationAPI';

// Icons
import { 
  Plus, 
  Search, 
  FileText,
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react';

export default function SearchExperienceSection({ entityDefinitions, uiConfig, onConfigurationChange }) {
  const [selectedSchema, setSelectedSchema] = useState(null);
  const [selectedEntity, setSelectedEntity] = useState(null);
  const [showCreateEntityForm, setShowCreateEntityForm] = useState(false);
  const [newEntityName, setNewEntityName] = useState('');
  const [saving, setSaving] = useState(false);

  // Get search experience entity types
  const searchEntityTypes = entityDefinitions?.fileMappings?.searchExperience?.entities || [];
  const schemas = uiConfig?.schemas || [];

  // Filter entities for search experience configurations
  const getSearchEntities = (schema) => {
    return schema.configurations.filter(entity => 
      searchEntityTypes.includes(entity.entityType)
    );
  };

  const createEntity = async () => {
    if (!newEntityName.trim() || !selectedSchema) {
      toast.error('Please enter an entity name');
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.createEntity({
        entityType: 'queries', // Search experience primarily uses queries
        name: newEntityName.trim(),
        baseConfig: {
          queries: {}
        },
        schemaId: selectedSchema.id
      });

      if (result.success) {
        toast.success(`Search entity "${newEntityName}" created successfully`);
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
        toast.success('Search entity updated successfully');
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
    if (!confirm('Are you sure you want to delete this search entity?')) {
      return;
    }

    setSaving(true);
    try {
      const result = await ConfigurationAPI.deleteEntity(entityId);

      if (result.success) {
        toast.success('Search entity deleted successfully');
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

  const generateSearchFiles = async () => {
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
        const searchFiles = result.files.filter(file => file.path.includes('searchExperience'));
        toast.success(`Generated ${searchFiles.length} search experience files`);
        console.log('Generated search files:', searchFiles);
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

  return (
    <div className="h-full flex">
      {/* Left Panel - Schema and Entity Management */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Schema Management */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900">Search Experience Schemas</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={generateSearchFiles}
              disabled={!selectedSchema || saving}
              title="Generate search experience files"
            >
              <Search className="h-4 w-4" />
            </Button>
          </div>

          <div className="mb-3 p-3 bg-green-50 rounded-lg">
            <div className="text-xs text-green-700 font-medium mb-1">Search Experience</div>
            <div className="text-xs text-green-600">
              Define search queries (lexical, vector, mixed) and search experience configurations.
            </div>
          </div>

          {/* Schema List */}
          <div className="space-y-2">
            {schemas.map(schema => {
              const searchEntities = getSearchEntities(schema);
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
                    {searchEntities.length} search entities
                  </div>
                  <div className="text-xs text-green-600 mt-1">
                    → searchExperience.json
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
                <h4 className="font-medium text-gray-900">Search Entities</h4>
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
                      <Label className="text-xs">Search Experience Name</Label>
                      <Input
                        placeholder="Enter search experience name"
                        value={newEntityName}
                        onChange={(e) => setNewEntityName(e.target.value)}
                        className="h-8"
                      />
                      <div className="text-xs text-gray-500 mt-1">
                        This will create a queries entity for defining search queries
                      </div>
                    </div>

                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        onClick={createEntity}
                        disabled={!newEntityName.trim() || saving}
                        className="h-7 text-xs"
                      >
                        Create
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setShowCreateEntityForm(false);
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
              {getSearchEntities(selectedSchema).map(entity => (
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
                        <Search className="h-4 w-4" />
                        <span className="font-medium text-sm truncate">
                          {entity.name}
                        </span>
                        {!entity.enabled && (
                          <EyeOff className="h-3 w-3 text-gray-400" />
                        )}
                      </div>
                      
                      <Badge 
                        variant="secondary" 
                        className="text-xs bg-cyan-100 text-cyan-800"
                      >
                        {entityDefinitions?.entityTypes[entity.entityType]?.title || entity.entityType}
                      </Badge>

                      {/* Query Count */}
                      {entity.baseConfig?.queries && (
                        <div className="mt-2 text-xs text-gray-600">
                          <div className="font-medium">
                            {Object.keys(entity.baseConfig.queries).length} queries defined
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

              {getSearchEntities(selectedSchema).length === 0 && (
                <div className="text-center py-8">
                  <Search className="h-8 w-8 mx-auto text-gray-300 mb-2" />
                  <div className="text-sm text-gray-500 mb-1">No search entities yet</div>
                  <div className="text-xs text-gray-400">
                    Click the + button to create your first search experience
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
              availableEntities={selectedSchema ? getSearchEntities(selectedSchema) : []}
            />
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Search className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No search entity selected
              </h3>
              <p className="text-gray-600 mb-4">
                {selectedSchema 
                  ? 'Select a search entity from the left panel to configure queries and search experience'
                  : 'Select a schema first, then choose a search entity to configure'
                }
              </p>
              {selectedSchema && (
                <div className="text-sm text-gray-500 space-y-1">
                  <p>Search entities define:</p>
                  <p>• Lexical queries (text-based search)</p>
                  <p>• Vector queries (semantic search)</p>
                  <p>• Mixed queries (hybrid search)</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}