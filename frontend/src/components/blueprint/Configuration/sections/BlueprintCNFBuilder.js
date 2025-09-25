import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../ui/card';
import { Button } from '../../../ui/button';
import { Input } from '../../../ui/input';
import { Label } from '../../../ui/label';
import { Textarea } from '../../../ui/textarea';
import { Switch } from '../../../ui/switch';
import { Badge } from '../../../ui/badge';
import { Separator } from '../../../ui/separator';
import { toast } from 'sonner';

// Icons
import { 
  FileText, 
  Plus, 
  Minus, 
  Download,
  Save,
  Eye,
  Settings
} from 'lucide-react';

export default function BlueprintCNFBuilder({ entityDefinitions, uiConfig, onConfigurationChange }) {
  const [blueprintConfig, setBlueprintConfig] = useState({
    namespace: '',
    version: 'git_version',
    owner: '',
    description: '',
    schemas: [],
    transformSpecs: [],
    searchExperience: {
      configs: [],
      templates: []
    }
  });
  const [showPreview, setShowPreview] = useState(false);
  const [previewWidth, setPreviewWidth] = useState(400); // Default width for preview panel

  const schemas = uiConfig?.schemas || [];

  useEffect(() => {
    // Initialize blueprint config from existing schemas
    if (schemas.length > 0) {
      const searchExperienceConfigs = getSearchExperienceFiles(schemas);
      
      setBlueprintConfig(prev => ({
        ...prev,
        namespace: prev.namespace || schemas[0]?.namespace || '',
        schemas: schemas.map(schema => ({
          id: schema.id,
          namespace: schema.namespace,
          enabled: true,
          global: getGlobalFiles(schema),
          messages: getMessageFiles(schema)
        })),
        searchExperience: {
          ...prev.searchExperience,
          configs: searchExperienceConfigs
        }
      }));
    }
  }, [uiConfig, entityDefinitions]);

  const getGlobalFiles = (schema) => {
    const globalEntities = schema.configurations.filter(entity => 
      entityDefinitions?.fileMappings?.global?.entities?.includes(entity.entityType)
    );
    
    if (globalEntities.length > 0) {
      const safeNamespace = schema.namespace.replace(/\./g, '_').replace(/-/g, '_');
      return [`global_${safeNamespace}.json`];
    }
    return [];
  };

  const getMessageFiles = (schema) => {
    const messageEntities = schema.configurations.filter(entity => 
      entityDefinitions?.fileMappings?.messageConfigs?.entities?.includes(entity.entityType)
    );
    
    const entityTypes = [...new Set(messageEntities.map(entity => entity.entityType))];
    return entityTypes.map(type => `config${type.charAt(0).toUpperCase() + type.slice(1)}.json`);
  };

  const getSearchExperienceFiles = (schemas) => {
    const searchFiles = [];
    
    schemas.forEach(schema => {
      schema.configurations.forEach(entity => {
        if (entityDefinitions?.fileMappings?.searchExperience?.entities?.includes(entity.entityType)) {
          // Use the entity name directly as the filename (without prefix)
          const fileName = `${entity.name || entity.entityType}.json`;
          if (!searchFiles.includes(fileName)) {
            searchFiles.push(fileName);
          }
        }
      });
    });
    
    // If no specific search experience entities found, check if there are any queries entities
    if (searchFiles.length === 0) {
      const hasQueriesEntities = schemas.some(schema =>
        schema.configurations.some(entity => entity.entityType === 'queries')
      );
      
      if (hasQueriesEntities) {
        searchFiles.push('searchExperience.json');
      }
    }
    
    return searchFiles;
  };

  const updateBlueprintConfig = (field, value) => {
    setBlueprintConfig(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const updateSchemaConfig = (schemaId, field, value) => {
    setBlueprintConfig(prev => ({
      ...prev,
      schemas: prev.schemas.map(schema =>
        schema.id === schemaId ? { ...schema, [field]: value } : schema
      )
    }));
  };

  const addTransformSpec = () => {
    setBlueprintConfig(prev => ({
      ...prev,
      transformSpecs: [...prev.transformSpecs, '']
    }));
  };

  const updateTransformSpec = (index, value) => {
    setBlueprintConfig(prev => ({
      ...prev,
      transformSpecs: prev.transformSpecs.map((spec, i) => i === index ? value : spec)
    }));
  };

  const removeTransformSpec = (index) => {
    setBlueprintConfig(prev => ({
      ...prev,
      transformSpecs: prev.transformSpecs.filter((_, i) => i !== index)
    }));
  };

  const addSearchTemplate = () => {
    setBlueprintConfig(prev => ({
      ...prev,
      searchExperience: {
        ...prev.searchExperience,
        templates: [...prev.searchExperience.templates, '']
      }
    }));
  };

  const addSearchConfig = () => {
    setBlueprintConfig(prev => ({
      ...prev,
      searchExperience: {
        ...prev.searchExperience,
        configs: [...prev.searchExperience.configs, '']
      }
    }));
  };

  const updateSearchConfig = (index, value) => {
    setBlueprintConfig(prev => ({
      ...prev,
      searchExperience: {
        ...prev.searchExperience,
        configs: prev.searchExperience.configs.map((config, i) => i === index ? value : config)
      }
    }));
  };

  const removeSearchConfig = (index) => {
    setBlueprintConfig(prev => ({
      ...prev,
      searchExperience: {
        ...prev.searchExperience,
        configs: prev.searchExperience.configs.filter((_, i) => i !== index)
      }
    }));
  };

  const updateSearchTemplate = (index, value) => {
    setBlueprintConfig(prev => ({
      ...prev,
      searchExperience: {
        ...prev.searchExperience,
        templates: prev.searchExperience.templates.map((template, i) => i === index ? value : template)
      }
    }));
  };

  const removeSearchTemplate = (index) => {
    setBlueprintConfig(prev => ({
      ...prev,
      searchExperience: {
        ...prev.searchExperience,
        templates: prev.searchExperience.templates.filter((_, i) => i !== index)
      }
    }));
  };

  const generateBlueprintCNF = () => {
    // Filter enabled schemas and clean up the structure
    const enabledSchemas = blueprintConfig.schemas
      .filter(schema => schema.enabled)
      .map(({ id, enabled, ...schema }) => schema);

    const finalConfig = {
      namespace: blueprintConfig.namespace,
      version: blueprintConfig.version,
      owner: blueprintConfig.owner,
      description: blueprintConfig.description,
      schemas: enabledSchemas,
      transformSpecs: blueprintConfig.transformSpecs.filter(spec => spec.trim()),
      searchExperience: {
        configs: blueprintConfig.searchExperience.configs,
        templates: blueprintConfig.searchExperience.templates.filter(template => template.trim())
      }
    };

    return finalConfig;
  };

  const downloadBlueprintCNF = () => {
    try {
      const config = generateBlueprintCNF();
      const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = 'blueprint_cnf.json';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      toast.success('Blueprint CNF downloaded successfully');
    } catch (error) {
      console.error('Failed to download blueprint CNF:', error);
      toast.error('Failed to download blueprint CNF');
    }
  };

  const saveBlueprintCNF = async () => {
    try {
      const config = generateBlueprintCNF();
      
      // Save to backend via the create-file API
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL}/api/blueprint/create-file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          path: 'blueprint_cnf.json',
          content: JSON.stringify(config, null, 2),
          overwrite: true
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          toast.success('Blueprint CNF saved to project root successfully');
        } else {
          throw new Error(result.message || 'Failed to save file');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || 'Failed to save file');
      }
    } catch (error) {
      console.error('Failed to save blueprint CNF:', error);
      toast.error(`Failed to save blueprint CNF to project: ${error.message}`);
    }
  };

  return (
    <div className="h-full flex">
      {/* Left Panel - Blueprint Configuration */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>Blueprint Information</span>
            </CardTitle>
            <CardDescription>
              Define the basic information for your blueprint configuration file
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Namespace</Label>
                <Input
                  value={blueprintConfig.namespace}
                  onChange={(e) => updateBlueprintConfig('namespace', e.target.value)}
                  placeholder="ea.example.namespace.v1"
                />
              </div>
              <div>
                <Label>Version</Label>
                <Input
                  value={blueprintConfig.version}
                  onChange={(e) => updateBlueprintConfig('version', e.target.value)}
                  placeholder="git_version"
                />
              </div>
            </div>
            <div>
              <Label>Owner</Label>
              <Input
                value={blueprintConfig.owner}
                onChange={(e) => updateBlueprintConfig('owner', e.target.value)}
                placeholder="Blueprint owner/maintainer"
              />
            </div>
            <div>
              <Label>Description</Label>
              <Textarea
                value={blueprintConfig.description}
                onChange={(e) => updateBlueprintConfig('description', e.target.value)}
                placeholder="Describe what this blueprint does..."
                rows={3}
              />
            </div>
          </CardContent>
        </Card>

        {/* Schemas Configuration */}
        <Card>
          <CardHeader>
            <CardTitle>Configuration Schemas</CardTitle>
            <CardDescription>
              Select which configuration schemas to include in the blueprint
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {blueprintConfig.schemas.map((schema, index) => (
              <div key={schema.id} className="p-4 border rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={schema.enabled}
                      onCheckedChange={(checked) => updateSchemaConfig(schema.id, 'enabled', checked)}
                    />
                    <div>
                      <div className="font-medium">{schema.namespace}</div>
                      <div className="text-sm text-gray-600">
                        Global: {schema.global.length} • Messages: {schema.messages.length}
                      </div>
                    </div>
                  </div>
                  <Badge variant={schema.enabled ? "default" : "secondary"}>
                    {schema.enabled ? "Included" : "Excluded"}
                  </Badge>
                </div>
                
                {schema.enabled && (
                  <div className="space-y-2">
                    <div>
                      <Label className="text-sm">Global Files</Label>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {schema.global.map((file, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {file}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <Label className="text-sm">Message Files</Label>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {schema.messages.map((file, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {file}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {blueprintConfig.schemas.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <Settings className="h-8 w-8 mx-auto mb-2 text-gray-300" />
                <div className="text-sm">No configuration schemas found</div>
                <div className="text-xs">Create schemas in the other sections first</div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Transform Specs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Transform Specifications</span>
              <Button variant="outline" size="sm" onClick={addTransformSpec}>
                <Plus className="h-4 w-4 mr-2" />
                Add Transform
              </Button>
            </CardTitle>
            <CardDescription>
              JSLT transformation files for data processing
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {blueprintConfig.transformSpecs.map((spec, index) => (
              <div key={index} className="flex items-center space-x-2">
                <Input
                  value={spec}
                  onChange={(e) => updateTransformSpec(index, e.target.value)}
                  placeholder="transform_file.jslt"
                  className="flex-1"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeTransformSpec(index)}
                >
                  <Minus className="h-4 w-4" />
                </Button>
              </div>
            ))}
            
            {blueprintConfig.transformSpecs.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                <div className="text-sm">No transform specifications</div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Search Experience */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Search Experience</span>
              <div className="flex space-x-2">
                <Button variant="outline" size="sm" onClick={addSearchConfig}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Config
                </Button>
                <Button variant="outline" size="sm" onClick={addSearchTemplate}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Template
                </Button>
              </div>
            </CardTitle>
            <CardDescription>
              Search experience configurations and templates
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-sm font-medium mb-2 flex items-center justify-between">
                Configuration Files
                <Button variant="ghost" size="sm" onClick={addSearchConfig}>
                  <Plus className="h-3 w-3" />
                </Button>
              </Label>
              
              {blueprintConfig.searchExperience.configs.length > 0 ? (
                <div className="space-y-2 mt-2">
                  {blueprintConfig.searchExperience.configs.map((config, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <Input
                        value={config}
                        onChange={(e) => updateSearchConfig(index, e.target.value)}
                        placeholder="searchExperience_config.json"
                        className="flex-1 text-xs"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeSearchConfig(index)}
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-gray-500 mt-1">
                  No search experience configuration files. Add files based on your Search Experience entities.
                </div>
              )}
            </div>

            <Separator />

            <div>
              <Label className="text-sm font-medium mb-2 flex items-center justify-between">
                Templates
                <Button variant="ghost" size="sm" onClick={addSearchTemplate}>
                  <Plus className="h-3 w-3" />
                </Button>
              </Label>
              <div className="space-y-2 mt-2">
                {blueprintConfig.searchExperience.templates.map((template, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <Input
                      value={template}
                      onChange={(e) => updateSearchTemplate(index, e.target.value)}
                      placeholder="template_file.json"
                      className="flex-1"
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeSearchTemplate(index)}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                
                {blueprintConfig.searchExperience.templates.length === 0 && (
                  <div className="text-center py-4 text-gray-500">
                    <div className="text-sm">No search templates</div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Panel - Actions and Preview */}
      {showPreview && (
        <>
          {/* Resize Handle */}
          <div 
            className="w-1 bg-gray-300 hover:bg-blue-500 cursor-col-resize flex-shrink-0"
            onMouseDown={(e) => {
              e.preventDefault();
              const startX = e.clientX;
              const startWidth = previewWidth;
              
              const handleMouseMove = (e) => {
                const newWidth = Math.max(300, Math.min(800, startWidth + (startX - e.clientX)));
                setPreviewWidth(newWidth);
              };
              
              const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
              };
              
              document.addEventListener('mousemove', handleMouseMove);
              document.addEventListener('mouseup', handleMouseUp);
            }}
          />
          
          {/* Preview Panel - Now Resizable */}
          <div className="bg-white border-l border-gray-200 flex flex-col" style={{ width: previewWidth }}>
            <div className="p-4 border-b border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-3">Blueprint CNF Actions</h3>
              
              <div className="space-y-2">
                <Button
                  className="w-full"
                  onClick={() => setShowPreview(!showPreview)}
                  variant="outline"
                >
                  <Eye className="h-4 w-4 mr-2" />
                  {showPreview ? 'Hide Preview' : 'Show Preview'}
                </Button>
                
                <Button
                  className="w-full"
                  onClick={saveBlueprintCNF}
                >
                  <Save className="h-4 w-4 mr-2" />
                  Save blueprint_cnf.json
                </Button>
                
                <Button
                  className="w-full"
                  onClick={downloadBlueprintCNF}
                  variant="outline"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download blueprint_cnf.json
                </Button>
              </div>
            </div>

            <div className="flex-1 overflow-hidden">
              <div className="p-4 h-full">
                <h4 className="font-medium text-gray-900 mb-3">Preview</h4>
                <div className="bg-gray-900 text-green-400 p-3 rounded text-xs font-mono overflow-auto h-full">
                  <pre>{JSON.stringify(generateBlueprintCNF(), null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Fixed Action Panel when Preview is Hidden */}
      {!showPreview && (
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-3">Blueprint CNF Actions</h3>
            
            <div className="space-y-2">
              <Button
                className="w-full"
                onClick={() => setShowPreview(!showPreview)}
                variant="outline"
              >
                <Eye className="h-4 w-4 mr-2" />
                {showPreview ? 'Hide Preview' : 'Show Preview'}
              </Button>
              
              <Button
                className="w-full"
                onClick={saveBlueprintCNF}
              >
                <Save className="h-4 w-4 mr-2" />
                Save blueprint_cnf.json
              </Button>
              
              <Button
                className="w-full"
                onClick={downloadBlueprintCNF}
                variant="outline"
              >
                <Download className="h-4 w-4 mr-2" />
                Download blueprint_cnf.json
              </Button>
            </div>
          </div>

          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <FileText className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <h4 className="text-lg font-medium text-gray-900 mb-2">
                Blueprint CNF Builder
              </h4>
              <p className="text-gray-600 text-sm mb-4">
                Configure your blueprint composition and generate the final blueprint_cnf.json file
              </p>
              <div className="text-xs text-gray-500 space-y-1">
                <p>• Select configuration schemas</p>
                <p>• Add transform specifications</p>
                <p>• Include search templates</p>
                <p>• Download final configuration</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}