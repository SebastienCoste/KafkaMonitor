import React, { useState } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Badge } from '../../ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';

// Icons
import { 
  Plus, 
  Settings, 
  Database, 
  FileText, 
  Trash2,
  Eye,
  EyeOff
} from 'lucide-react';

export default function SchemaManager({ 
  schema, 
  entityDefinitions, 
  selectedEntity, 
  onSelectEntity, 
  onCreateEntity, 
  onDeleteEntity 
}) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newEntityType, setNewEntityType] = useState('');
  const [newEntityName, setNewEntityName] = useState('');

  const handleCreateEntity = async () => {
    if (!newEntityType || !newEntityName.trim()) {
      return;
    }

    await onCreateEntity(newEntityType, newEntityName.trim());
    
    // Reset form
    setNewEntityType('');
    setNewEntityName('');
    setShowCreateForm(false);
  };

  const getEntityTypeIcon = (entityType) => {
    switch (entityType) {
      case 'storages':
      case 'messageStorage':
      case 'discoveryStorage':
        return <Database className="h-4 w-4" />;
      case 'access':
      case 'discoveryFeatures':
        return <Settings className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getEntityTypeColor = (entityType) => {
    switch (entityType) {
      case 'access':
        return 'bg-red-100 text-red-800';
      case 'storages':
        return 'bg-blue-100 text-blue-800';
      case 'inferenceServiceConfigs':
        return 'bg-purple-100 text-purple-800';
      case 'messageStorage':
      case 'discoveryStorage':
        return 'bg-green-100 text-green-800';
      case 'binaryAssets':
        return 'bg-orange-100 text-orange-800';
      case 'imageModeration':
      case 'textModeration':
        return 'bg-yellow-100 text-yellow-800';
      case 'transformation':
        return 'bg-indigo-100 text-indigo-800';
      case 'discoveryFeatures':
        return 'bg-pink-100 text-pink-800';
      case 'queries':
        return 'bg-cyan-100 text-cyan-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!schema) {
    return (
      <div className="p-4 text-center">
        <div className="text-gray-500 mb-2">No schema selected</div>
        <div className="text-sm text-gray-400">
          Create or select a schema to manage entities
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-gray-900">Entities</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowCreateForm(!showCreateForm)}
            disabled={!entityDefinitions}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {showCreateForm && (
          <Card className="mb-3">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">Create New Entity</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label className="text-xs">Entity Type</Label>
                <Select value={newEntityType} onValueChange={setNewEntityType}>
                  <SelectTrigger className="h-8">
                    <SelectValue placeholder="Select entity type" />
                  </SelectTrigger>
                  <SelectContent>
                    {entityDefinitions && Object.entries(entityDefinitions.entityTypes).map(([type, definition]) => (
                      <SelectItem key={type} value={type}>
                        <div className="flex items-center space-x-2">
                          {getEntityTypeIcon(type)}
                          <span>{definition.title}</span>
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
                  onClick={handleCreateEntity}
                  disabled={!newEntityType || !newEntityName.trim()}
                  className="h-7 text-xs"
                >
                  Create
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowCreateForm(false);
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
      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-2">
          {schema.configurations.map(entity => (
            <div
              key={entity.id}
              className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                selectedEntity?.id === entity.id
                  ? 'bg-blue-50 border-blue-300 shadow-sm'
                  : 'bg-white border-gray-200 hover:bg-gray-50'
              }`}
              onClick={() => onSelectEntity(entity)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2 mb-1">
                    {getEntityTypeIcon(entity.entityType)}
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
                    onDeleteEntity(entity.id);
                  }}
                  className="h-6 w-6 p-0 text-gray-400 hover:text-red-600"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          ))}

          {schema.configurations.length === 0 && (
            <div className="text-center py-8">
              <FileText className="h-8 w-8 mx-auto text-gray-300 mb-2" />
              <div className="text-sm text-gray-500 mb-1">No entities yet</div>
              <div className="text-xs text-gray-400">
                Click the + button to create your first entity
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}