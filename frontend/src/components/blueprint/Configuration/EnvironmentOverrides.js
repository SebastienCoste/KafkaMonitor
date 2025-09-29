import React, { useState, useMemo } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Switch } from '../../ui/switch';
import { Textarea } from '../../ui/textarea';
import { Card, CardContent } from '../../ui/card';
import { Alert, AlertDescription } from '../../ui/alert';

// Icons
import { Plus, Minus, Trash2, Globe, Copy, AlertTriangle } from 'lucide-react';

// EnvironmentOverrides renders a schema-driven form for each selected environment override
// It mirrors EntityEditor field rendering but writes/reads from entity.environmentOverrides[ENV]
export default function EnvironmentOverrides({
  entity,
  environments = ['DEV', 'TEST', 'INT', 'LOAD', 'PROD'],
  entityDefinition,
  onUpdateOverrides
}) {
  const [selectedEnv, setSelectedEnv] = useState('');
  const [editingEnv, setEditingEnv] = useState(null);

  const overrides = entity?.environmentOverrides || {};
  const fields = entityDefinition?.fields || {};

  const availableEnvironments = useMemo(
    () => environments.filter((env) => !overrides[env]),
    [environments, overrides]
  );

  // Helpers copied/adapted from EntityEditor to correctly handle map keys with dots
  const getFieldDefinitionByPath = (allFields, path) => {
    const keys = path.split('.');
    let currentFields = allFields;
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

  const setNestedProperty = (obj, path, value) => {
    const keys = path.split('.');
    let current = obj;

    // Detect if we are inside a map field (next segment after the map is map key – can contain dots)
    const entityTypeFields = fields;
    let mapFieldFound = false;
    let mapFieldPath = '';
    let mapKey = '';

    for (let i = 0; i < keys.length - 1; i++) {
      const currentPath = keys.slice(0, i + 1).join('.');
      const fieldDef = getFieldDefinitionByPath(entityTypeFields, currentPath);
      if (fieldDef?.type === 'map') {
        mapFieldFound = true;
        mapFieldPath = currentPath;
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

      // Remaining keys after the map key
      const mapFieldPathLength = mapFieldPath.split('.').length;
      const remainingKeys = keys.slice(mapFieldPathLength + 1);

      if (remainingKeys.length > 0) {
        if (!(mapKey in current) || typeof current[mapKey] !== 'object') {
          current[mapKey] = {};
        }
        let mapValueCurrent = current[mapKey];
        for (let i = 0; i < remainingKeys.length - 1; i++) {
          const key = remainingKeys[i];
          if (!(key in mapValueCurrent) || typeof mapValueCurrent[key] !== 'object') {
            mapValueCurrent[key] = {};
          }
          mapValueCurrent = mapValueCurrent[key];
        }
        mapValueCurrent[remainingKeys[remainingKeys.length - 1]] = value;
      } else {
        current[mapKey] = value;
      }
    } else {
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

    const entityTypeFields = fields;
    let mapFieldFound = false;
    let mapFieldPath = '';
    let mapKey = '';

    for (let i = 0; i < keys.length - 1; i++) {
      const currentPath = keys.slice(0, i + 1).join('.');
      const fieldDef = getFieldDefinitionByPath(entityTypeFields, currentPath);
      if (fieldDef?.type === 'map') {
        mapFieldFound = true;
        mapFieldPath = currentPath;
        if (i + 1 < keys.length) {
          mapKey = keys[i + 1];
        }
        break;
      }
    }

    if (mapFieldFound && mapKey) {
      const mapKeys = mapFieldPath.split('.');
      let current = obj;
      for (const key of mapKeys) {
        if (!current || current[key] === undefined) {
          return defaultValue;
        }
        current = current[key];
      }

      if (!current || current[mapKey] === undefined) {
        return defaultValue;
      }

      const mapFieldPathLength = mapFieldPath.split('.').length;
      const remainingKeys = keys.slice(mapFieldPathLength + 1);

      if (remainingKeys.length > 0) {
        let mapValueCurrent = current[mapKey];
        for (const key of remainingKeys) {
          if (!mapValueCurrent || mapValueCurrent[key] === undefined) {
            return defaultValue;
          }
          mapValueCurrent = mapValueCurrent[key];
        }
        return mapValueCurrent;
      } else {
        return current[mapKey];
      }
    }

    return keys.reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : defaultValue;
    }, obj);
  };

  const addEnvironmentOverride = () => {
    if (!selectedEnv || overrides[selectedEnv]) return;
    const newOverrides = { ...overrides, [selectedEnv]: {} };
    onUpdateOverrides(newOverrides);
    setEditingEnv(selectedEnv);
    setSelectedEnv('');
  };

  const removeEnvironmentOverride = (env) => {
    const newOverrides = { ...overrides };
    delete newOverrides[env];
    onUpdateOverrides(newOverrides);
    if (editingEnv === env) setEditingEnv(null);
  };

  const copyFromBaseConfig = (env) => {
    const newOverrides = { ...overrides, [env]: { ...(entity.baseConfig || {}) } };
    onUpdateOverrides(newOverrides);
  };

  const copyFromAnotherEnvironment = (sourceEnv, targetEnv) => {
    const newOverrides = {
      ...overrides,
      [targetEnv]: { ...(overrides[sourceEnv] || {}) }
    };
    onUpdateOverrides(newOverrides);
  };

  const updateEnvironmentConfig = (env, path, value) => {
    const envData = { ...(overrides[env] || {}) };
    setNestedProperty(envData, path, value);
    onUpdateOverrides({ ...overrides, [env]: envData });
  };

  const renderField = (env, fieldName, fieldDef, parentPath = '') => {
    const fullPath = parentPath ? `${parentPath}.${fieldName}` : fieldName;
    const currentValue = getNestedProperty(overrides[env] || {}, fullPath, fieldDef.default);

    const title = fieldDef.title || fieldDef.displayName || fieldName;
    const description = fieldDef.description;

    switch (fieldDef.type) {
      case 'string': {
        if (fieldDef.options) {
          return (
            <div key={fullPath} className="space-y-2">
              <Label className="text-sm font-medium">{title}</Label>
              {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
              <Select
                value={(currentValue ?? '')}
                onValueChange={(value) => updateEnvironmentConfig(env, fullPath, value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder={`Select ${title.toLowerCase()}`} />
                </SelectTrigger>
                <SelectContent>
                  {fieldDef.options.map((opt) => (
                    <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        }
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{title}</Label>
            {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
            <Input
              value={(currentValue ?? '')}
              onChange={(e) => updateEnvironmentConfig(env, fullPath, e.target.value)}
              placeholder={fieldDef.default?.toString() || ''}
            />
          </div>
        );
      }

      case 'select': {
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{title}</Label>
            {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
            <Select
              value={(currentValue ?? fieldDef.default ?? '')}
              onValueChange={(value) => updateEnvironmentConfig(env, fullPath, value)}
            >
              <SelectTrigger>
                <SelectValue placeholder={`Select ${title.toLowerCase()}`} />
              </SelectTrigger>
              <SelectContent>
                {fieldDef.options?.map((opt) => (
                  <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        );
      }

      case 'integer':
      case 'number': {
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{title}</Label>
            {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
            <Input
              type="number"
              value={(currentValue ?? '')}
              onChange={(e) => updateEnvironmentConfig(env, fullPath, fieldDef.type === 'integer' ? parseInt(e.target.value) || 0 : parseFloat(e.target.value) || 0)}
              min={fieldDef.min}
              max={fieldDef.max}
              placeholder={fieldDef.default?.toString() || ''}
            />
          </div>
        );
      }

      case 'boolean': {
        return (
          <div key={fullPath} className="space-y-2">
            <div className="flex items-center space-x-2">
              <Switch
                checked={!!currentValue}
                onCheckedChange={(checked) => updateEnvironmentConfig(env, fullPath, checked)}
              />
              <Label className="text-sm font-medium">{title}</Label>
            </div>
            {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
          </div>
        );
      }

      case 'array': {
        const arrayValue = Array.isArray(currentValue) ? currentValue : [];
        return (
          <div key={fullPath} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">{title}</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const newArray = [...arrayValue, fieldDef.items?.type === 'string' ? '' : {}];
                  updateEnvironmentConfig(env, fullPath, newArray);
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
            <div className="space-y-2">
              {arrayValue.map((item, index) => (
                <div key={index} className="flex items-center space-x-2">
                  {fieldDef.items?.type === 'string' ? (
                    <Input
                      value={item}
                      onChange={(e) => {
                        const newArray = [...arrayValue];
                        newArray[index] = e.target.value;
                        updateEnvironmentConfig(env, fullPath, newArray);
                      }}
                      className="flex-1"
                    />
                  ) : fieldDef.items?.type === 'object' &amp;&amp; fieldDef.items?.fields ? (
                    <Card className="flex-1">
                      <CardContent className="p-3 space-y-2">
                        {Object.entries(fieldDef.items.fields).map(([subFieldName, subFieldDef]) =>
                          renderField(env, subFieldName, subFieldDef, `${fullPath}.${index}`)
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
                        updateEnvironmentConfig(env, fullPath, newArray);
                      }}
                      className="flex-1 font-mono text-sm"
                      rows={2}
                    />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const newArray = arrayValue.filter((_, i) => i !== index);
                      updateEnvironmentConfig(env, fullPath, newArray);
                    }}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        );
      }

      case 'map': {
        const mapValue = (currentValue &amp;&amp; typeof currentValue === 'object') ? currentValue : {};
        return (
          <div key={fullPath} className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">{title}</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const key = prompt('Enter key name:');
                  if (key) {
                    updateEnvironmentConfig(env, `${fullPath}.${key}`, fieldDef.valueType?.default || '');
                  }
                }}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
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
                          updateEnvironmentConfig(env, fullPath, newMap);
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                    {fieldDef.valueType &amp;&amp; fieldDef.valueType.fields ? (
                      <div className="space-y-2">
                        {Object.entries(fieldDef.valueType.fields).map(([subFieldName, subFieldDef]) =>
                          renderField(env, subFieldName, subFieldDef, `${fullPath}.${key}`)
                        )}
                      </div>
                    ) : (
                      <Textarea
                        value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                        onChange={(e) => {
                          try {
                            updateEnvironmentConfig(env, `${fullPath}.${key}`, JSON.parse(e.target.value));
                          } catch {
                            updateEnvironmentConfig(env, `${fullPath}.${key}`, e.target.value);
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
      }

      case 'object': {
        if (fieldDef.fields) {
          return (
            <div key={fullPath} className="space-y-4">
              <Label className="text-sm font-medium">{title}</Label>
              {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
              <Card>
                <CardContent className="p-4 space-y-4">
                  {Object.entries(fieldDef.fields).map(([subFieldName, subFieldDef]) =>
                    renderField(env, subFieldName, subFieldDef, fullPath)
                  )}
                </CardContent>
              </Card>
            </div>
          );
        }
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{title}</Label>
            {description &amp;&amp; <p className="text-xs text-gray-600">{description}</p>}
            <Textarea
              value={typeof currentValue === 'object' ? JSON.stringify(currentValue, null, 2) : (currentValue ?? '')}
              onChange={(e) => {
                try {
                  updateEnvironmentConfig(env, fullPath, JSON.parse(e.target.value));
                } catch {
                  updateEnvironmentConfig(env, fullPath, e.target.value);
                }
              }}
              rows={4}
              className="font-mono text-sm"
            />
          </div>
        );
      }

      default: {
        return (
          <div key={fullPath} className="space-y-2">
            <Label className="text-sm font-medium">{title}</Label>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>Unsupported field type: {fieldDef.type}</AlertDescription>
            </Alert>
          </div>
        );
      }
    }
  };

  const renderEditor = (env) => {
    if (!env) return null;
    if (!fields || Object.keys(fields).length === 0) {
      return (
        <div className="text-center py-8">
          <AlertTriangle className="h-8 w-8 mx-auto text-gray-400 mb-2" />
          <p className="text-gray-600">No entity definition available</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h4 className="font-medium">{env} Configuration</h4>
          <div className="flex space-x-2">
            <Button variant="outline" size="sm" onClick={() => copyFromBaseConfig(env)}>
              <Copy className="h-4 w-4 mr-2" />Copy Base Config
            </Button>
            <Select onValueChange={(sourceEnv) => copyFromAnotherEnvironment(sourceEnv, env)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Copy from environment" />
              </SelectTrigger>
              <SelectContent>
                {Object.keys(overrides)
                  .filter((e) => e !== env)
                  .map((envName) => (
                    <SelectItem key={envName} value={envName}>Copy from {envName}</SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-4">
          {Object.entries(fields).map(([fieldName, fieldDef]) => renderField(env, fieldName, fieldDef))}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex">
      {/* Environment List */}
      <div className="w-64 border-r border-gray-200 bg-gray-50">
        <div className="p-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-3">Environment Overrides</h3>

          {availableEnvironments.length > 0 ? (
            <div className="space-y-2">
              <Select value={selectedEnv} onValueChange={setSelectedEnv}>
                <SelectTrigger>
                  <SelectValue placeholder="Select environment" />
                </SelectTrigger>
                <SelectContent>
                  {availableEnvironments.map((env) => (
                    <SelectItem key={env} value={env}>{env}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button size="sm" onClick={addEnvironmentOverride} disabled={!selectedEnv} className="w-full">
                <Plus className="h-4 w-4 mr-2" />Add Override
              </Button>
            </div>
          ) : (
            <div className="text-xs text-gray-500">All environments added</div>
          )}
        </div>

        <div className="p-2">
          {Object.keys(overrides).length === 0 ? (
            <div className="text-center py-8">
              <Globe className="h-8 w-8 mx-auto text-gray-300 mb-2" />
              <div className="text-sm text-gray-500 mb-1">No environment overrides</div>
              <div className="text-xs text-gray-400">Add overrides for specific environments</div>
            </div>
          ) : (
            <div className="space-y-1">
              {Object.keys(overrides).map((env) => (
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
                        {Object.keys(overrides[env] || {}).length} fields
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

      {/* Editor */}
      <div className="flex-1 p-4 overflow-y-auto">
        {!editingEnv ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center max-w-md">
              <Globe className="h-10 w-10 mx-auto text-gray-300 mb-3" />
              <div className="text-sm text-gray-700 mb-1">Select an environment to edit overrides</div>
              <div className="text-xs text-gray-500">You can add overrides for any of: DEV, TEST, INT, LOAD, PROD</div>
            </div>
          </div>
        ) : (
          renderEditor(editingEnv)
        )}

        {/* Explicit note: full per-environment config snapshots */}
        <div className="mt-6">
          <Alert>
            <AlertDescription>
              Each environment section contains the full configuration for that environment. The service will interpret it directly.
            </AlertDescription>
          </Alert>
        </div>
      </div>
    </div>
  );
}