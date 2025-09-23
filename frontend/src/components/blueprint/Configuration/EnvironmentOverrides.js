import React, { useState } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { Textarea } from '../../ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../ui/card';
import { Badge } from '../../ui/badge';
import { Alert, AlertDescription } from '../../ui/alert';

// Icons
import { 
  Plus, 
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
    // Helper functions from EntityEditor
    const updateEnvironmentConfig = (path, value) => {
      const newOverrides = { ...data };
      setNestedProperty(newOverrides, path, value);
      updateEnvironmentOverride(env, newOverrides);
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

            {renderJsonEditor(editingEnv, entity.environmentOverrides[editingEnv])}
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