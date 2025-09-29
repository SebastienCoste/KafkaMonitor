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

      if (remainingKeys.length &gt; 0) {
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

      if (remainingKeys.length &gt; 0) {
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
            <div key={fullPath} className="space-y-2"&gt;
              <Label className="text-sm font-medium"&gt;{title}</Label&gt;
              {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
              <Select
                value={(currentValue ?? '')}
                onValueChange={(value) =&gt; updateEnvironmentConfig(env, fullPath, value)}
              &gt;
                <SelectTrigger&gt;
                  <SelectValue placeholder={`Select ${title.toLowerCase()}`} /&gt;
                </SelectTrigger&gt;
                <SelectContent&gt;
                  {fieldDef.options.map((opt) =&gt; (
                    <SelectItem key={opt} value={opt}&gt;{opt}</SelectItem&gt;
                  ))}
                </SelectContent&gt;
              </Select&gt;
            </div&gt;
          );
        }
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <Label className="text-sm font-medium"&gt;{title}</Label&gt;
            {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
            <Input
              value={(currentValue ?? '')}
              onChange={(e) =&gt; updateEnvironmentConfig(env, fullPath, e.target.value)}
              placeholder={fieldDef.default?.toString() || ''}
            /&gt;
          </div&gt;
        );
      }

      case 'select': {
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <Label className="text-sm font-medium"&gt;{title}</Label&gt;
            {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
            <Select
              value={(currentValue ?? fieldDef.default ?? '')}
              onValueChange={(value) =&gt; updateEnvironmentConfig(env, fullPath, value)}
            &gt;
              <SelectTrigger&gt;
                <SelectValue placeholder={`Select ${title.toLowerCase()}`} /&gt;
              </SelectTrigger&gt;
              <SelectContent&gt;
                {fieldDef.options?.map((opt) =&gt; (
                  <SelectItem key={opt} value={opt}&gt;{opt}</SelectItem&gt;
                ))}
              </SelectContent&gt;
            </Select&gt;
          </div&gt;
        );
      }

      case 'integer':
      case 'number': {
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <Label className="text-sm font-medium"&gt;{title}</Label&gt;
            {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
            <Input
              type="number"
              value={(currentValue ?? '')}
              onChange={(e) =&gt; updateEnvironmentConfig(env, fullPath, fieldDef.type === 'integer' ? parseInt(e.target.value) || 0 : parseFloat(e.target.value) || 0)}
              min={fieldDef.min}
              max={fieldDef.max}
              placeholder={fieldDef.default?.toString() || ''}
            /&gt;
          </div&gt;
        );
      }

      case 'boolean': {
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <div className="flex items-center space-x-2"&gt;
              <Switch
                checked={!!currentValue}
                onCheckedChange={(checked) =&gt; updateEnvironmentConfig(env, fullPath, checked)}
              /&gt;
              <Label className="text-sm font-medium"&gt;{title}</Label&gt;
            </div&gt;
            {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
          </div&gt;
        );
      }

      case 'array': {
        const arrayValue = Array.isArray(currentValue) ? currentValue : [];
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <div className="flex items-center justify-between"&gt;
              <Label className="text-sm font-medium"&gt;{title}</Label&gt;
              <Button
                variant="ghost"
                size="sm"
                onClick={() =&gt; {
                  const newArray = [...arrayValue, fieldDef.items?.type === 'string' ? '' : {}];
                  updateEnvironmentConfig(env, fullPath, newArray);
                }}
              &gt;
                <Plus className="h-4 w-4" /&gt;
              </Button&gt;
            </div&gt;
            {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
            <div className="space-y-2"&gt;
              {arrayValue.map((item, index) =&gt; (
                <div key={index} className="flex items-center space-x-2"&gt;
                  {fieldDef.items?.type === 'string' ? (
                    <Input
                      value={item}
                      onChange={(e) =&gt; {
                        const newArray = [...arrayValue];
                        newArray[index] = e.target.value;
                        updateEnvironmentConfig(env, fullPath, newArray);
                      }}
                      className="flex-1"
                    /&gt;
                  ) : fieldDef.items?.type === 'object' &amp;&amp; fieldDef.items?.fields ? (
                    <Card className="flex-1"&gt;
                      <CardContent className="p-3 space-y-2"&gt;
                        {Object.entries(fieldDef.items.fields).map(([subFieldName, subFieldDef]) =&gt;
                          renderField(env, subFieldName, subFieldDef, `${fullPath}.${index}`)
                        )}
                      </CardContent&gt;
                    </Card&gt;
                  ) : (
                    <Textarea
                      value={typeof item === 'object' ? JSON.stringify(item, null, 2) : item}
                      onChange={(e) =&gt; {
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
                    /&gt;
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =&gt; {
                      const newArray = arrayValue.filter((_, i) =&gt; i !== index);
                      updateEnvironmentConfig(env, fullPath, newArray);
                    }}
                  &gt;
                    <Minus className="h-4 w-4" /&gt;
                  </Button&gt;
                </div&gt;
              ))}
            </div&gt;
          </div&gt;
        );
      }

      case 'map': {
        const mapValue = (currentValue &amp;&amp; typeof currentValue === 'object') ? currentValue : {};
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <div className="flex items-center justify-between"&gt;
              <Label className="text-sm font-medium"&gt;{title}</Label&gt;
              <Button
                variant="ghost"
                size="sm"
                onClick={() =&gt; {
                  const key = prompt('Enter key name:');
                  if (key) {
                    updateEnvironmentConfig(env, `${fullPath}.${key}`, fieldDef.valueType?.default || '');
                  }
                }}
              &gt;
                <Plus className="h-4 w-4" /&gt;
              </Button&gt;
            </div&gt;
            {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
            <div className="space-y-2"&gt;
              {Object.entries(mapValue).map(([key, value]) =&gt; (
                <Card key={key}&gt;
                  <CardContent className="p-3"&gt;
                    <div className="flex items-center justify-between mb-2"&gt;
                      <Label className="text-sm font-semibold"&gt;{key}</Label&gt;
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =&gt; {
                          const newMap = { ...mapValue };
                          delete newMap[key];
                          updateEnvironmentConfig(env, fullPath, newMap);
                        }}
                      &gt;
                        <Trash2 className="h-3 w-3" /&gt;
                      </Button&gt;
                    </div&gt;
                    {fieldDef.valueType &amp;&amp; fieldDef.valueType.fields ? (
                      <div className="space-y-2"&gt;
                        {Object.entries(fieldDef.valueType.fields).map(([subFieldName, subFieldDef]) =&gt;
                          renderField(env, subFieldName, subFieldDef, `${fullPath}.${key}`)
                        )}
                      </div&gt;
                    ) : (
                      <Textarea
                        value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
                        onChange={(e) =&gt; {
                          try {
                            updateEnvironmentConfig(env, `${fullPath}.${key}`, JSON.parse(e.target.value));
                          } catch {
                            updateEnvironmentConfig(env, `${fullPath}.${key}`, e.target.value);
                          }
                        }}
                        rows={3}
                        className="font-mono text-sm"
                      /&gt;
                    )}
                  </CardContent&gt;
                </Card&gt;
              ))}
            </div&gt;
          </div&gt;
        );
      }

      case 'object': {
        if (fieldDef.fields) {
          return (
            <div key={fullPath} className="space-y-4"&gt;
              <Label className="text-sm font-medium"&gt;{title}</Label&gt;
              {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
              <Card&gt;
                <CardContent className="p-4 space-y-4"&gt;
                  {Object.entries(fieldDef.fields).map(([subFieldName, subFieldDef]) =&gt;
                    renderField(env, subFieldName, subFieldDef, fullPath)
                  )}
                </CardContent&gt;
              </Card&gt;
            </div&gt;
          );
        }
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <Label className="text-sm font-medium"&gt;{title}</Label&gt;
            {description &amp;&amp; <p className="text-xs text-gray-600"&gt;{description}</p&gt;}
            <Textarea
              value={typeof currentValue === 'object' ? JSON.stringify(currentValue, null, 2) : (currentValue ?? '')}
              onChange={(e) =&gt; {
                try {
                  updateEnvironmentConfig(env, fullPath, JSON.parse(e.target.value));
                } catch {
                  updateEnvironmentConfig(env, fullPath, e.target.value);
                }
              }}
              rows={4}
              className="font-mono text-sm"
            /&gt;
          </div&gt;
        );
      }

      default: {
        return (
          <div key={fullPath} className="space-y-2"&gt;
            <Label className="text-sm font-medium"&gt;{title}</Label&gt;
            <Alert&gt;
              <AlertTriangle className="h-4 w-4" /&gt;
              <AlertDescription&gt;Unsupported field type: {fieldDef.type}</AlertDescription&gt;
            </Alert&gt;
          </div&gt;
        );
      }
    }
  };

  const renderEditor = (env) =&gt; {
    if (!env) return null;
    if (!fields || Object.keys(fields).length === 0) {
      return (
        <div className="text-center py-8"&gt;
          <AlertTriangle className="h-8 w-8 mx-auto text-gray-400 mb-2" /&gt;
          <p className="text-gray-600"&gt;No entity definition available</p&gt;
        </div&gt;
      );
    }

    return (
      <div className="space-y-6"&gt;
        <div className="flex items-center justify-between"&gt;
          <h4 className="font-medium"&gt;{env} Configuration</h4&gt;
          <div className="flex space-x-2"&gt;
            <Button variant="outline" size="sm" onClick={() =&gt; copyFromBaseConfig(env)}&gt;
              <Copy className="h-4 w-4 mr-2" /&gt;Copy Base Config
            </Button&gt;
            <Select onValueChange={(sourceEnv) =&gt; copyFromAnotherEnvironment(sourceEnv, env)}&gt;
              <SelectTrigger className="w-48"&gt;
                <SelectValue placeholder="Copy from environment" /&gt;
              </SelectTrigger&gt;
              <SelectContent&gt;
                {Object.keys(overrides)
                  .filter((e) =&gt; e !== env)
                  .map((envName) =&gt; (
                    <SelectItem key={envName} value={envName}&gt;Copy from {envName}</SelectItem&gt;
                  ))}
              </SelectContent&gt;
            </Select&gt;
          </div&gt;
        </div&gt;

        <div className="space-y-4"&gt;
          {Object.entries(fields).map(([fieldName, fieldDef]) =&gt; renderField(env, fieldName, fieldDef))}
        </div&gt;
      </div&gt;
    );
  };

  return (
    <div className="h-full flex"&gt;
      {/* Environment List */}
      <div className="w-64 border-r border-gray-200 bg-gray-50"&gt;
        <div className="p-4 border-b border-gray-200"&gt;
          <h3 className="font-semibold text-gray-900 mb-3"&gt;Environment Overrides</h3&gt;

          {availableEnvironments.length &gt; 0 ? (
            <div className="space-y-2"&gt;
              <Select value={selectedEnv} onValueChange={setSelectedEnv}&gt;
                <SelectTrigger&gt;
                  <SelectValue placeholder="Select environment" /&gt;
                </SelectTrigger&gt;
                <SelectContent&gt;
                  {availableEnvironments.map((env) =&gt; (
                    <SelectItem key={env} value={env}&gt;{env}</SelectItem&gt;
                  ))}
                </SelectContent&gt;
              </Select&gt;

              <Button size="sm" onClick={addEnvironmentOverride} disabled={!selectedEnv} className="w-full"&gt;
                <Plus className="h-4 w-4 mr-2" /&gt;Add Override
              </Button&gt;
            </div&gt;
          ) : (
            <div className="text-xs text-gray-500"&gt;All environments added</div&gt;
          )}
        </div&gt;

        <div className="p-2"&gt;
          {Object.keys(overrides).length === 0 ? (
            <div className="text-center py-8"&gt;
              <Globe className="h-8 w-8 mx-auto text-gray-300 mb-2" /&gt;
              <div className="text-sm text-gray-500 mb-1"&gt;No environment overrides</div&gt;
              <div className="text-xs text-gray-400"&gt;Add overrides for specific environments</div&gt;
            </div&gt;
          ) : (
            <div className="space-y-1"&gt;
              {Object.keys(overrides).map((env) =&gt; (
                <div
                  key={env}
                  className={`p-3 rounded cursor-pointer transition-colors ${
                    editingEnv === env
                      ? 'bg-blue-100 border border-blue-300'
                      : 'bg-white border border-gray-200 hover:bg-gray-50'
                  }`}
                  onClick={() =&gt; setEditingEnv(env)}
                &gt;
                  <div className="flex items-center justify-between"&gt;
                    <div&gt;
                      <div className="font-medium text-sm"&gt;{env}</div&gt;
                      <div className="text-xs text-gray-600"&gt;
                        {Object.keys(overrides[env] || {}).length} fields
                      </div&gt;
                    </div&gt;
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) =&gt; {
                        e.stopPropagation();
                        removeEnvironmentOverride(env);
                      }}
                      className="h-6 w-6 p-0 text-gray-400 hover:text-red-600"
                    &gt;
                      <Trash2 className="h-3 w-3" /&gt;
                    </Button&gt;
                  </div&gt;
                </div&gt;
              ))}
            </div&gt;
          )}
        </div&gt;
      </div&gt;

      {/* Editor */}
      <div className="flex-1 p-4 overflow-y-auto"&gt;
        {!editingEnv ? (
          <div className="h-full flex items-center justify-center"&gt;
            <div className="text-center max-w-md"&gt;
              <Globe className="h-10 w-10 mx-auto text-gray-300 mb-3" /&gt;
              <div className="text-sm text-gray-700 mb-1"&gt;Select an environment to edit overrides</div&gt;
              <div className="text-xs text-gray-500"&gt;You can add overrides for any of: DEV, TEST, INT, LOAD, PROD</div&gt;
            </div&gt;
          </div&gt;
        ) : (
          renderEditor(editingEnv)
        )}

        {/* Explicit note: full per-environment config snapshots */}
        <div className="mt-6"&gt;
          <Alert&gt;
            <AlertDescription&gt;
              Each environment section contains the full configuration for that environment. The service will interpret it directly.
            </AlertDescription&gt;
          </Alert&gt;
        </div&gt;
      </div&gt;
    </div&gt;
  );
}