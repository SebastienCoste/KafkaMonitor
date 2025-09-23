import React, { useState, useEffect } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Switch } from '../../ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Textarea } from '../../ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { Badge } from '../../ui/badge';
import { Alert, AlertDescription } from '../../ui/alert';

import EnvironmentOverrides from './EnvironmentOverrides';

// Icons
import { 
  Save, 
  Trash2, 
  Plus, 
  Minus, 
  Settings, 
  Globe,
  AlertTriangle,
  Info
} from 'lucide-react';

export default function EntityEditor({ 
  entity, 
  entityDefinition, 
  environments, 
  onUpdateEntity, 
  onDeleteEntity,
  availableEntities = [] // Add available entities prop
}) {
  const [localEntity, setLocalEntity] = useState(entity);
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  // Update local entity when prop changes
  useEffect(() => {
    setLocalEntity(entity);
    setHasChanges(false);
  }, [entity]);

  const updateLocalEntity = (updates) => {
    setLocalEntity({ ...localEntity, ...updates });
    setHasChanges(true);
  };

  const updateBaseConfig = (path, value) => {
    const newBaseConfig = { ...localEntity.baseConfig };
    setNestedProperty(newBaseConfig, path, value);
    updateLocalEntity({ baseConfig: newBaseConfig });
  };

  const setNestedProperty = (obj, path, value) => {
    const keys = path.split('.');
    let current = obj;
    
    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in current) || typeof current[key] !== 'object') {
        current[key] = {};
      }
      current = current[key];
    }
    
    current[keys[keys.length - 1]] = value;
  };

  const getNestedProperty = (obj, path, defaultValue = '') => {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : defaultValue;
    }, obj);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdateEntity(localEntity.id, {
        name: localEntity.name,
        baseConfig: localEntity.baseConfig,
        environmentOverrides: localEntity.environmentOverrides,
        inherit: localEntity.inherit,
        enabled: localEntity.enabled
      });
      setHasChanges(false);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    await onDeleteEntity(localEntity.id);
  };

  const renderField = (fieldName, fieldDef, parentPath = '') => {
    const fullPath = parentPath ? `${parentPath}.${fieldName}` : fieldName;
    const currentValue = getNestedProperty(localEntity.baseConfig, fullPath, fieldDef.default);

    switch (fieldDef.type) {
      case 'string':
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{fieldDef.title}</Label>
            {fieldDef.description && (
              <p className="text-xs text-gray-600">{fieldDef.description}</p>
            )}
            <Input
              value={currentValue || ''}
              onChange={(e) => updateBaseConfig(fullPath, e.target.value)}
              placeholder={fieldDef.default?.toString() || ''}
            />
          </div>
        );

      case 'integer':
      case 'number':
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{fieldDef.title}</Label>
            {fieldDef.description && (
              <p className="text-xs text-gray-600">{fieldDef.description}</p>
            )}
            <Input
              type="number"
              value={currentValue || ''}
              onChange={(e) => updateBaseConfig(fullPath, fieldDef.type === 'integer' ? parseInt(e.target.value) || 0 : parseFloat(e.target.value) || 0)}
              min={fieldDef.min}
              max={fieldDef.max}
              placeholder={fieldDef.default?.toString() || ''}
            />
          </div>
        );

      case 'boolean':
        return (
          <div key={fullPath} className="space-y-2">
            <div className="flex items-center space-x-2">
              <Switch
                checked={currentValue || false}
                onCheckedChange={(checked) => updateBaseConfig(fullPath, checked)}
              />
              <Label className="text-sm font-medium">{fieldDef.title}</Label>
            </div>
            {fieldDef.description && (
              <p className="text-xs text-gray-600">{fieldDef.description}</p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{fieldDef.title}</Label>
            {fieldDef.description && (
              <p className="text-xs text-gray-600">{fieldDef.description}</p>
            )}
            <Select 
              value={currentValue || fieldDef.default || ''} 
              onValueChange={(value) => updateBaseConfig(fullPath, value)}
            >
              <SelectTrigger>
                <SelectValue placeholder={`Select ${fieldDef.title.toLowerCase()}`} />
              </SelectTrigger>
              <SelectContent>
                {fieldDef.options?.map(option => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        );

      case 'array':
        const arrayValue = currentValue || [];
        return (
          <div key={fullPath} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">{fieldDef.title}</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const newArray = [...arrayValue, fieldDef.items?.type === 'string' ? '' : {}];
                  updateBaseConfig(fullPath, newArray);
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {fieldDef.description && (
              <p className="text-xs text-gray-600">{fieldDef.description}</p>
            )}
            <div className="space-y-2">
              {arrayValue.map((item, index) => (
                <div key={index} className="flex items-center space-x-2">
                  {fieldDef.items?.type === 'string' ? (
                    <Input
                      value={item}
                      onChange={(e) => {
                        const newArray = [...arrayValue];
                        newArray[index] = e.target.value;
                        updateBaseConfig(fullPath, newArray);
                      }}
                      className="flex-1"
                    />
                  ) : fieldDef.items?.type === 'object' && fieldDef.items?.fields ? (
                    <Card className="flex-1">
                      <CardContent className="p-3 space-y-2">
                        {Object.entries(fieldDef.items.fields).map(([subFieldName, subFieldDef]) => 
                          renderField(subFieldName, subFieldDef, `${fullPath}.${index}`)
                        )}
                      </CardContent>
                    </Card>
                  ) : (
                    <Textarea
                      value={typeof item === 'object' ? JSON.stringify(item, null, 2) : item}
                      onChange={(e) => {
                        const newArray = [...arrayValue];
                        try {
                          newArray[index] = JSON.parse(e.target.value);
                        } catch {
                          newArray[index] = e.target.value;
                        }
                        updateBaseConfig(fullPath, newArray);
                      }}
                      className="flex-1"
                      rows={2}
                    />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const newArray = arrayValue.filter((_, i) => i !== index);
                      updateBaseConfig(fullPath, newArray);
                    }}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        );

      case 'object':
        if (fieldDef.fields) {
          return (
            <div key={fullPath} className="space-y-4">
              <Label className="text-sm font-medium">{fieldDef.title}</Label>
              {fieldDef.description && (
                <p className="text-xs text-gray-600">{fieldDef.description}</p>
              )}
              <Card>
                <CardContent className="p-4 space-y-4">
                  {Object.entries(fieldDef.fields).map(([subFieldName, subFieldDef]) =>
                    renderField(subFieldName, subFieldDef, fullPath)
                  )}
                </CardContent>
              </Card>
            </div>
          );
        }
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{fieldDef.title}</Label>
            {fieldDef.description && (
              <p className="text-xs text-gray-600">{fieldDef.description}</p>
            )}
            <Textarea
              value={typeof currentValue === 'object' ? JSON.stringify(currentValue, null, 2) : currentValue || ''}
              onChange={(e) => {
                try {
                  updateBaseConfig(fullPath, JSON.parse(e.target.value));
                } catch {
                  updateBaseConfig(fullPath, e.target.value);
                }
              }}
              rows={4}
              className="font-mono text-sm"
            />
          </div>
        );

      case 'map':
        const mapValue = currentValue || {};
        return (
          <div key={fullPath} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">{fieldDef.title}</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const key = prompt('Enter key name:');
                  if (key) {
                    updateBaseConfig(`${fullPath}.${key}`, fieldDef.valueType?.default || '');
                  }
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {fieldDef.description && (
              <p className="text-xs text-gray-600">{fieldDef.description}</p>
            )}
            <div className="space-y-2">
              {Object.entries(mapValue).map(([key, value]) => (
                <Card key={key}>
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between mb-2">
                      <Label className="text-sm font-semibold">{key}</Label>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const newMap = { ...mapValue };
                          delete newMap[key];
                          updateBaseConfig(fullPath, newMap);
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                    {fieldDef.valueType && fieldDef.valueType.fields ? (
                      <div className="space-y-2">
                        {Object.entries(fieldDef.valueType.fields).map(([subFieldName, subFieldDef]) =>
                          renderField(subFieldName, subFieldDef, `${fullPath}.${key}`)
                        )}
                      </div>
                    ) : (
                      <Textarea
                        value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                        onChange={(e) => {
                          try {
                            updateBaseConfig(`${fullPath}.${key}`, JSON.parse(e.target.value));
                          } catch {
                            updateBaseConfig(`${fullPath}.${key}`, e.target.value);
                          }
                        }}
                        rows={3}
                        className="font-mono text-sm"
                      />
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        );

      default:
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{fieldDef.title}</Label>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Unsupported field type: {fieldDef.type}
              </AlertDescription>
            </Alert>
          </div>
        );
    }
  };

  if (!entityDefinition) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="h-8 w-8 mx-auto text-yellow-500 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Entity Definition Not Found
        </h3>
        <p className="text-gray-600">
          The entity type "{entity.entityType}" is not defined in the current entity definitions.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{localEntity.name}</h2>
            <p className="text-sm text-gray-600">{entityDefinition.title}</p>
          </div>
          
          <div className="flex items-center space-x-2">
            {hasChanges && (
              <Badge variant="outline" className="text-orange-600 border-orange-300">
                Unsaved changes
              </Badge>
            )}
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleSave}
              disabled={!hasChanges || saving}
            >
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : 'Save'}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleDelete}
              className="text-red-600 hover:bg-red-50"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <Tabs defaultValue="configuration" className="h-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="configuration">Configuration</TabsTrigger>
            <TabsTrigger value="environments">Environments</TabsTrigger>
            <TabsTrigger value="metadata">Metadata</TabsTrigger>
          </TabsList>

          <TabsContent value="configuration" className="p-4 space-y-6">
            {entityDefinition.description && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>{entityDefinition.description}</AlertDescription>
              </Alert>
            )}

            {Object.entries(entityDefinition.fields).map(([fieldName, fieldDef]) =>
              renderField(fieldName, fieldDef)
            )}
          </TabsContent>

          <TabsContent value="environments" className="h-full">
            <EnvironmentOverrides
              entity={localEntity}
              environments={environments}
              entityDefinition={entityDefinition}
              onUpdateOverrides={(overrides) => updateLocalEntity({ environmentOverrides: overrides })}
            />
          </TabsContent>

          <TabsContent value="metadata" className="p-4 space-y-6">
            <div className="space-y-4">
              <div>
                <Label className="text-sm font-medium">Entity Name</Label>
                <Input
                  value={localEntity.name}
                  onChange={(e) => updateLocalEntity({ name: e.target.value })}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  checked={localEntity.enabled}
                  onCheckedChange={(checked) => updateLocalEntity({ enabled: checked })}
                />
                <Label className="text-sm font-medium">Enabled</Label>
              </div>

              <div>
                <Label className="text-sm font-medium">Inheritance</Label>
                <div className="space-y-2">
                  {localEntity.inherit?.map((inheritName, index) => {
                    // Get available entities from the same schema/file for inheritance
                    const availableEntities = getAvailableEntitiesForInheritance();
                    
                    return (
                      <div key={index} className="flex items-center space-x-2">
                        <Select
                          value={inheritName}
                          onValueChange={(value) => {
                            const newInherit = [...(localEntity.inherit || [])];
                            newInherit[index] = value;
                            updateLocalEntity({ inherit: newInherit });
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select entity to inherit from" />
                          </SelectTrigger>
                          <SelectContent>
                            {availableEntities.map(entityName => (
                              <SelectItem key={entityName} value={entityName}>
                                {entityName}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const newInherit = localEntity.inherit.filter((_, i) => i !== index);
                            updateLocalEntity({ inherit: newInherit.length > 0 ? newInherit : null });
                          }}
                        >
                          <Minus className="h-4 w-4" />
                        </Button>
                      </div>
                    );
                  })}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const newInherit = [...(localEntity.inherit || []), ''];
                      updateLocalEntity({ inherit: newInherit });
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Inheritance
                  </Button>
                </div>
              </div>

              <div>
                <Label className="text-sm font-medium">Entity ID</Label>
                <Input value={localEntity.id} disabled className="bg-gray-50" />
              </div>

              <div>
                <Label className="text-sm font-medium">Entity Type</Label>
                <Input value={localEntity.entityType} disabled className="bg-gray-50" />
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}