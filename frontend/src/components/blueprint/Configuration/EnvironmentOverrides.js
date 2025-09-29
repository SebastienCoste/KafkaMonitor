import React, { useState } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Switch } from '../../ui/switch';
import { Textarea } from '../../ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Badge } from '../../ui/badge';
import { Alert, AlertDescription } from '../../ui/alert';

// Icons
import { 
  Plus, 
  Minus,
  Trash2, 
  Globe, 
  Settings,
  AlertTriangle,
  Copy
} from 'lucide-react';

export default function EnvironmentOverrides({ 
  entity, 
  environments, 
  entityDefinition,
  onUpdateOverrides 
}) {
  const [selectedEnv, setSelectedEnv] = useState('');
  const [editingEnv, setEditingEnv] = useState(null);

  // Helper functions for nested property handling (similar to EntityEditor)
  const setNestedProperty = (obj, path, value) => {
    const keys = path.split('.');
    let current = obj;
    
    // Handle map keys specially - if the path contains a map, don't split the key after the map
    const entityTypeFields = entityDefinition?.fields || {};
    let mapFieldFound = false;
    let mapFieldPath = '';
    let mapKey = '';
    
    // Check if we're dealing with a map field
    for (let i = 0; i < keys.length - 1; i++) {
      const currentPath = keys.slice(0, i + 1).join('.');
      const fieldDef = getFieldDefinitionByPath(entityTypeFields, currentPath);
      if (fieldDef?.type === 'map') {
        mapFieldFound = true;
        mapFieldPath = currentPath;
        // The next key after the map field is the map key
        if (i + 1 < keys.length) {
          mapKey = keys[i + 1];
        }
        break;
      }
    }
    
    if (mapFieldFound && mapKey) {
      // Navigate to the map object
      const mapKeys = mapFieldPath.split('.');
      for (let i = 0; i < mapKeys.length; i++) {
        const key = mapKeys[i];
        if (!(key in current) || typeof current[key] !== 'object') {
          current[key] = {};
        }
        current = current[key];
      }
      
      // Check if we have sub-fields after the map key
      const mapFieldPathLength = mapFieldPath.split('.').length;
      const mapKeyIndex = mapFieldPathLength; // Index of the map key in the path
      const remainingKeys = keys.slice(mapKeyIndex + 1); // Keys after the map key
      
      if (remainingKeys.length > 0) {
        // We have sub-fields, navigate into the map entry and set nested property
        if (!(mapKey in current) || typeof current[mapKey] !== 'object') {
          current[mapKey] = {};
        }
        
        let mapValueCurrent = current[mapKey];
        // Navigate through remaining path
        for (let i = 0; i < remainingKeys.length - 1; i++) {
          const key = remainingKeys[i];
          if (!(key in mapValueCurrent) || typeof mapValueCurrent[key] !== 'object') {
            mapValueCurrent[key] = {};
          }
          mapValueCurrent = mapValueCurrent[key];
        }
        // Set the final value
        mapValueCurrent[remainingKeys[remainingKeys.length - 1]] = value;
      } else {
        // No sub-fields, set the map key directly
        current[mapKey] = value;
      }
    } else {
      // Normal nested property setting
      for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        if (!(key in current) || typeof current[key] !== 'object') {
          current[key] = {};
        }
        current = current[key];
      }
      current[keys[keys.length - 1]] = value;
    }
  };

  const getNestedProperty = (obj, path, defaultValue = '') => {
    const keys = path.split('.');
    
    // Handle map keys specially - similar logic as setNestedProperty
    const entityTypeFields = entityDefinition?.fields || {};
    let mapFieldFound = false;
    let mapFieldPath = '';
    let mapKey = '';
    
    // Check if we're dealing with a map field
    for (let i = 0; i < keys.length - 1; i++) {
      const currentPath = keys.slice(0, i + 1).join('.');
      const fieldDef = getFieldDefinitionByPath(entityTypeFields, currentPath);
      if (fieldDef?.type === 'map') {
        mapFieldFound = true;
        mapFieldPath = currentPath;
        // The next key after the map field is the map key
        if (i + 1 < keys.length) {
          mapKey = keys[i + 1];
        }
        break;
      }
    }
    
    if (mapFieldFound && mapKey) {
      // Navigate to the map object
      const mapKeys = mapFieldPath.split('.');
      let current = obj;
      for (const key of mapKeys) {
        if (!current || current[key] === undefined) {
          return defaultValue;
        }
        current = current[key];
      }
      
      // Get the map entry
      if (!current || current[mapKey] === undefined) {
        return defaultValue;
      }
      
      // Check if we have sub-fields after the map key
      const mapFieldPathLength = mapFieldPath.split('.').length;
      const mapKeyIndex = mapFieldPathLength;
      const remainingKeys = keys.slice(mapKeyIndex + 1);
      
      if (remainingKeys.length > 0) {
        // Navigate through remaining path
        let mapValueCurrent = current[mapKey];
        for (const key of remainingKeys) {
          if (!mapValueCurrent || mapValueCurrent[key] === undefined) {
            return defaultValue;
          }
          mapValueCurrent = mapValueCurrent[key];
        }
        return mapValueCurrent;
      } else {
        // Return the map key value directly
        return current[mapKey];
      }
    } else {
      // Normal nested property getting
      return keys.reduce((current, key) => {
        return current && current[key] !== undefined ? current[key] : defaultValue;
      }, obj);
    }
  };

  const getFieldDefinitionByPath = (fields, path) => {
    const keys = path.split('.');
    let currentField = null;
    
    for (const key of keys) {
      if (!currentField) {
        currentField = fields[key];
      } else if (currentField.type === 'object' && currentField.fields) {
        currentField = currentField.fields[key];
      } else if (currentField.type === 'array' && currentField.items && currentField.items.fields) {
        currentField = currentField.items.fields[key];
      } else if (currentField.type === 'map' && currentField.valueType && currentField.valueType.fields) {
        currentField = currentField.valueType.fields[key];
      } else {
        return null;
      }
    }
    
    return currentField;
  };

  const addEnvironmentOverride = () => {
    if (!selectedEnv || entity.environmentOverrides[selectedEnv]) {
      return;
    }

    const newOverrides = {
      ...entity.environmentOverrides,
      [selectedEnv]: {}
    };

    onUpdateOverrides(newOverrides);
    setEditingEnv(selectedEnv);
    setSelectedEnv('');
  };

  const removeEnvironmentOverride = (env) => {
    const newOverrides = { ...entity.environmentOverrides };
    delete newOverrides[env];
    onUpdateOverrides(newOverrides);
  };

  // Render field dynamically based on field definition (similar to EntityEditor)
  const renderOverrideField = (env, fieldName, fieldDef, parentPath = '') => {
    const fullPath = parentPath ? `${parentPath}.${fieldName}` : fieldName;
    const overrideValue = getNestedProperty(entity.environmentOverrides[env] || {}, fullPath);

    const updateOverrideValue = (value) => {
      const newOverrides = { ...entity.environmentOverrides };
      if (!newOverrides[env]) {
        newOverrides[env] = {};
      }
      setNestedProperty(newOverrides[env], fullPath, value);
      onUpdateOverrides(newOverrides);
    };

    if (!fieldDef) {
      return null;
    }

    const commonProps = {
      value: overrideValue || '',
      onChange: (e) => updateOverrideValue(e.target.value),
      className: "w-full"
    };

    switch (fieldDef.type) {
      case 'string':
        if (fieldDef.options) {
          return (
            <Select value={overrideValue || ''} onValueChange={updateOverrideValue}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder={`Select ${fieldDef.displayName || fieldName}...`} />
              </SelectTrigger>
              <SelectContent>
                {fieldDef.options.map((option) => (
                  <SelectItem key={option} value={option}>
                    {option}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        }
        return fieldDef.multiline ? (
          <Textarea {...commonProps} placeholder={fieldDef.description} rows={3} />
        ) : (
          <Input {...commonProps} placeholder={fieldDef.description} />
        );

      case 'number':
        return (
          <Input
            {...commonProps}
            type="number"
            placeholder={fieldDef.description}
            onChange={(e) => updateOverrideValue(parseFloat(e.target.value) || 0)}
          />
        );

      case 'boolean':
        return (
          <Switch
            checked={overrideValue === true}
            onCheckedChange={updateOverrideValue}
          />
        );

      case 'array':
        const arrayValue = Array.isArray(overrideValue) ? overrideValue : [];
        return (
          <div className="space-y-2">
            {arrayValue.map((item, index) => (
              <div key={index} className="flex items-center space-x-2">
                {fieldDef.items && fieldDef.items.type === 'object' && fieldDef.items.fields ? (
                  <div className="flex-1 space-y-2 border rounded p-3">
                    {Object.entries(fieldDef.items.fields).map(([subFieldName, subFieldDef]) => (
                      <div key={subFieldName}>
                        <Label className="text-sm font-medium">
                          {subFieldDef.displayName || subFieldName}
                        </Label>
                        {renderOverrideField(env, subFieldName, subFieldDef, `${fullPath}.${index}`)}
                      </div>
                    ))}
                  </div>
                ) : (
                  <Input
                    value={typeof item === 'object' ? JSON.stringify(item) : item}
                    onChange={(e) => {
                      const newArray = [...arrayValue];
                      try {
                        newArray[index] = fieldDef.items?.type === 'number' ? parseFloat(e.target.value) : e.target.value;
                      } catch {
                        newArray[index] = e.target.value;
                      }
                      updateOverrideValue(newArray);
                    }}
                    className="flex-1"
                  />
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const newArray = arrayValue.filter((_, i) => i !== index);
                    updateOverrideValue(newArray);
                  }}
                >
                  <Minus className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const newArray = [...arrayValue, fieldDef.items?.type === 'object' ? {} : ''];
                updateOverrideValue(newArray);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add {fieldDef.displayName || fieldName}
            </Button>
          </div>
        );

      case 'map':
        const mapValue = overrideValue && typeof overrideValue === 'object' ? overrideValue : {};
        return (
          <div className="space-y-2">
            {Object.entries(mapValue).map(([key, value]) => (
              <div key={key} className="border rounded p-3">
                <div className="flex items-center justify-between mb-2">
                  <Label className="font-medium">{key}</Label>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const newMap = { ...mapValue };
                      delete newMap[key];
                      updateOverrideValue(newMap);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
                {fieldDef.valueType && fieldDef.valueType.fields ? (
                  <div className="space-y-2">
                    {Object.entries(fieldDef.valueType.fields).map(([subFieldName, subFieldDef]) => (
                      <div key={subFieldName}>
                        <Label className="text-sm font-medium">
                          {subFieldDef.displayName || subFieldName}
                        </Label>
                        {renderOverrideField(env, subFieldName, subFieldDef, `${fullPath}.${key}`)}
                      </div>
                    ))}
                  </div>
                ) : (
                  <Input
                    value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                    onChange={(e) => {
                      const newMap = { ...mapValue };
                      try {
                        newMap[key] = JSON.parse(e.target.value);
                      } catch {
                        newMap[key] = e.target.value;
                      }
                      updateOverrideValue(newMap);
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        );

      case 'object':
        if (!fieldDef.fields) {
          return (
            <Textarea
              value={JSON.stringify(overrideValue || {}, null, 2)}
              onChange={(e) => {
                try {
                  updateOverrideValue(JSON.parse(e.target.value));
                } catch {
                  // Keep raw value for invalid JSON
                }
              }}
              placeholder="Enter JSON object"
              rows={4}
            />
          );
        }
        return (
          <div className="space-y-3 border rounded p-3">
            {Object.entries(fieldDef.fields).map(([subFieldName, subFieldDef]) => (
              <div key={subFieldName}>
                <Label className="text-sm font-medium">
                  {subFieldDef.displayName || subFieldName}
                </Label>
                {renderOverrideField(env, subFieldName, subFieldDef, fullPath)}
              </div>
            ))}
          </div>
        );

      default:
        return (
          <Textarea
            value={JSON.stringify(overrideValue || '', null, 2)}
            onChange={(e) => {
              try {
                updateOverrideValue(JSON.parse(e.target.value));
              } catch {
                updateOverrideValue(e.target.value);
              }
            }}
            placeholder={fieldDef.description}
            rows={3}
          />
        );
    }
  };
    
    if (editingEnv === env) {
      setEditingEnv(null);
    }
  };

  const updateEnvironmentOverride = (env, overrideData) => {
    const newOverrides = {
      ...entity.environmentOverrides,
      [env]: overrideData
    };
    onUpdateOverrides(newOverrides);
  };

  const copyFromBaseConfig = (env) => {
    const newOverrides = {
      ...entity.environmentOverrides,
      [env]: { ...entity.baseConfig }
    };
    onUpdateOverrides(newOverrides);
  };

  const copyFromAnotherEnvironment = (sourceEnv, targetEnv) => {
    const newOverrides = {
      ...entity.environmentOverrides,
      [targetEnv]: { ...entity.environmentOverrides[sourceEnv] }
    };
    onUpdateOverrides(newOverrides);
  };

  const renderConfigurationBuilder = (env, data) => {
    if (!entityDefinition?.fields) {
      return (
        <div className="text-center py-8">
          <AlertTriangle className="h-8 w-8 mx-auto text-gray-400 mb-2" />
          <p className="text-gray-600">No entity definition available</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-6">
          {Object.entries(entityDefinition.fields).map(([fieldName, fieldDef]) => (
            <div key={fieldName} className="space-y-3">
              <div className="flex items-center space-between">
                <div>
                  <Label className="text-sm font-medium text-gray-900">
                    {fieldDef.displayName || fieldName}
                  </Label>
                  {fieldDef.description && (
                    <p className="text-xs text-gray-600 mt-1">{fieldDef.description}</p>
                  )}
                </div>
              </div>
              {renderOverrideField(env, fieldName, fieldDef)}
            </div>
          ))}
        </div>
      </div>
    );
  };
    // Helper functions from EntityEditor
    const updateEnvironmentConfig = (path, value) => {
      const newOverrides = { ...data };
      setNestedProperty(newOverrides, path, value);
      updateEnvironmentOverride(env, newOverrides);
    };

    const setNestedProperty = (obj, path, value) => {
      const keys = path.split('.');
      let current = obj;
      
      // Handle map keys specially - if the path contains a map, don't split the key after the map
      const entityTypeFields = entityDefinition?.fields || {};
      let mapFieldFound = false;
      let mapFieldPath = '';
      
      // Check if we're dealing with a map field
      for (let i = 0; i < keys.length - 1; i++) {
        const currentPath = keys.slice(0, i + 1).join('.');
        const fieldDef = getFieldDefinitionByPath(entityTypeFields, currentPath);
        if (fieldDef?.type === 'map') {
          mapFieldFound = true;
          mapFieldPath = currentPath;
          break;
        }
      }
      
      if (mapFieldFound) {
        // For map fields, don't split the key part
        const mapKeys = mapFieldPath.split('.');
        const remainingPath = path.substring(mapFieldPath.length + 1);
        
        // Navigate to the map object
        for (let i = 0; i < mapKeys.length; i++) {
          const key = mapKeys[i];
          if (!(key in current) || typeof current[key] !== 'object') {
            current[key] = {};
          }
          current = current[key];
        }
        
        // Set the value using the full remaining path as the key (don't split it)
        current[remainingPath] = value;
      } else {
        // Normal nested property setting
        for (let i = 0; i < keys.length - 1; i++) {
          const key = keys[i];
          if (!(key in current) || typeof current[key] !== 'object') {
            current[key] = {};
          }
          current = current[key];
        }
        current[keys[keys.length - 1]] = value;
      }
    };

    const getFieldDefinitionByPath = (fields, path) => {
      const keys = path.split('.');
      let currentFields = fields;
      let currentDef = null;
      
      for (const key of keys) {
        if (currentFields && currentFields[key]) {
          currentDef = currentFields[key];
          if (currentDef.type === 'object' && currentDef.fields) {
            currentFields = currentDef.fields;
          } else if (currentDef.type === 'map' && currentDef.valueType?.fields) {
            currentFields = currentDef.valueType.fields;
          } else {
            break;
          }
        } else {
          break;
        }
      }
      
      return currentDef;
    };

    const getNestedProperty = (obj, path, defaultValue = '') => {
      return path.split('.').reduce((current, key) => {
        return current && current[key] !== undefined ? current[key] : defaultValue;
      }, obj);
    };

    const renderField = (fieldName, fieldDef, parentPath = '') => {
      const fullPath = parentPath ? `${parentPath}.${fieldName}` : fieldName;
      const currentValue = getNestedProperty(data, fullPath, fieldDef.default);

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
                onChange={(e) => updateEnvironmentConfig(fullPath, e.target.value)}
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
                onChange={(e) => updateEnvironmentConfig(fullPath, fieldDef.type === 'integer' ? parseInt(e.target.value) || 0 : parseFloat(e.target.value) || 0)}
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
                  onCheckedChange={(checked) => updateEnvironmentConfig(fullPath, checked)}
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
                onValueChange={(value) => updateEnvironmentConfig(fullPath, value)}
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
                    updateEnvironmentConfig(fullPath, newArray);
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
                          updateEnvironmentConfig(fullPath, newArray);
                        }}
                        className="flex-1"
                      />
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
                          updateEnvironmentConfig(fullPath, newArray);
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
                        updateEnvironmentConfig(fullPath, newArray);
                      }}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
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
                      updateEnvironmentConfig(`${fullPath}.${key}`, fieldDef.valueType?.default || '');
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
                            updateEnvironmentConfig(fullPath, newMap);
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
                              updateEnvironmentConfig(`${fullPath}.${key}`, JSON.parse(e.target.value));
                            } catch {
                              updateEnvironmentConfig(`${fullPath}.${key}`, e.target.value);
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
          // Fallback to JSON editor for complex objects
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
                    updateEnvironmentConfig(fullPath, JSON.parse(e.target.value));
                  } catch {
                    updateEnvironmentConfig(fullPath, e.target.value);
                  }
                }}
                rows={4}
                className="font-mono text-sm"
              />
            </div>
          );

        default:
          // Fallback to JSON editor
          return (
            <div key={fullPath} className="space-y-2">
              <Label className="text-sm font-medium">{fieldDef.title}</Label>
              <Textarea
                value={typeof currentValue === 'object' ? JSON.stringify(currentValue, null, 2) : currentValue || ''}
                onChange={(e) => {
                  try {
                    updateEnvironmentConfig(fullPath, JSON.parse(e.target.value));
                  } catch {
                    updateEnvironmentConfig(fullPath, e.target.value);
                  }
                }}
                rows={3}
                className="font-mono text-sm"
              />
            </div>
          );
      }
    };

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h4 className="font-medium">Environment Configuration</h4>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => copyFromBaseConfig(env)}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy Base Config
            </Button>
            
            <Select onValueChange={(sourceEnv) => copyFromAnotherEnvironment(sourceEnv, env)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Copy from environment" />
              </SelectTrigger>
              <SelectContent>
                {Object.keys(entity.environmentOverrides)
                  .filter(e => e !== env)
                  .map(envName => (
                    <SelectItem key={envName} value={envName}>
                      Copy from {envName}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {entityDefinition?.fields && (
          <div className="space-y-4">
            {Object.entries(entityDefinition.fields).map(([fieldName, fieldDef]) =>
              renderField(fieldName, fieldDef)
            )}
          </div>
        )}

        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Environment overrides will be merged with the base configuration. 
            Only configure fields that need to differ from the base configuration for this environment.
          </AlertDescription>
        </Alert>
      </div>
    );
  };

  const availableEnvironments = environments.filter(env => !entity.environmentOverrides[env]);

  return (
    <div className="h-full flex">
      {/* Environment List */}
      <div className="w-64 border-r border-gray-200 bg-gray-50">
        <div className="p-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-3">Environment Overrides</h3>
          
          {availableEnvironments.length > 0 && (
            <div className="space-y-2">
              <Select value={selectedEnv} onValueChange={setSelectedEnv}>
                <SelectTrigger>
                  <SelectValue placeholder="Select environment" />
                </SelectTrigger>
                <SelectContent>
                  {availableEnvironments.map(env => (
                    <SelectItem key={env} value={env}>
                      {env}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              <Button
                size="sm"
                onClick={addEnvironmentOverride}
                disabled={!selectedEnv}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Override
              </Button>
            </div>
          )}
        </div>

        <div className="p-2">
          {Object.keys(entity.environmentOverrides).length === 0 ? (
            <div className="text-center py-8">
              <Globe className="h-8 w-8 mx-auto text-gray-300 mb-2" />
              <div className="text-sm text-gray-500 mb-1">No environment overrides</div>
              <div className="text-xs text-gray-400">
                Add overrides for specific environments
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {Object.keys(entity.environmentOverrides).map(env => (
                <div
                  key={env}
                  className={`p-3 rounded cursor-pointer transition-colors ${
                    editingEnv === env
                      ? 'bg-blue-100 border border-blue-300'
                      : 'bg-white border border-gray-200 hover:bg-gray-50'
                  }`}
                  onClick={() => setEditingEnv(env)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-sm">{env}</div>
                      <div className="text-xs text-gray-600">
                        {Object.keys(entity.environmentOverrides[env]).length} overrides
                      </div>
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeEnvironmentOverride(env);
                      }}
                      className="h-6 w-6 p-0 text-gray-400 hover:text-red-600"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Override Editor */}
      <div className="flex-1 p-4">
        {editingEnv ? (
          <div>
            <div className="flex items-center space-x-2 mb-4">
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">
                {editingEnv}
              </Badge>
              <span className="text-sm text-gray-600">Environment Override</span>
            </div>

            {renderConfigurationBuilder(editingEnv, entity.environmentOverrides[editingEnv])}
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Settings className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No environment selected
              </h3>
              <p className="text-gray-600 mb-4">
                Select an environment from the left panel to edit its overrides
              </p>
              <div className="text-sm text-gray-500">
                Environment overrides allow you to customize configuration for specific deployment environments
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}