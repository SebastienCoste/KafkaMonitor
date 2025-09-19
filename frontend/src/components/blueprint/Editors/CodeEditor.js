import React, { useState, useEffect } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { toast } from 'sonner';
import { Save, RotateCcw } from 'lucide-react';

export default function CodeEditor({ filePath }) {
  const { fileContent, saveFileContent, loading } = useBlueprintContext();
  const [currentContent, setCurrentContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);

  // Update content when file changes
  useEffect(() => {
    setCurrentContent(fileContent);
    setHasChanges(false);
  }, [fileContent]);

  const getFileMode = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'json':
        return 'JSON';
      case 'jslt':
        return 'JSLT'; 
      case 'yaml':
      case 'yml':
        return 'YAML';
      case 'proto':
        return 'Protocol Buffer';
      default:
        return 'Text';
    }
  };

  const handleSave = async () => {
    try {
      await saveFileContent(filePath, currentContent);
      setHasChanges(false);
      toast.success('File saved successfully');
    } catch (error) {
      toast.error(`Failed to save file: ${error.message}`);
    }
  };

  const handleRevert = () => {
    setCurrentContent(fileContent);
    setHasChanges(false);
    toast.info('Changes reverted');
  };

  const handleKeyDown = (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
  };

  if (!filePath) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        <p>No file selected</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Editor Header */}
      <div className="flex items-center justify-between p-3 bg-gray-50 border-b border-gray-200">
        <div className="flex items-center space-x-3">
          <h3 className="font-medium text-gray-900">{filePath}</h3>
          <Badge variant="secondary">
            {getFileMode(filePath)}
          </Badge>
          {hasChanges && (
            <Badge variant="outline" className="text-orange-600 border-orange-200">
              Modified
            </Badge>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRevert}
            disabled={!hasChanges || loading}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            Revert
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || loading}
          >
            <Save className="h-4 w-4 mr-1" />
            Save
          </Button>
        </div>
      </div>

      {/* Simple Text Editor */}
      <div className="flex-1 overflow-hidden">
        <textarea
          value={currentContent}
          onChange={(e) => {
            setCurrentContent(e.target.value);
            setHasChanges(e.target.value !== fileContent);
          }}
          onKeyDown={handleKeyDown}
          className="w-full h-full p-4 font-mono text-sm border-none resize-none focus:outline-none focus:ring-0 bg-white"
          style={{ 
            fontFamily: 'Monaco, "Lucida Console", monospace',
            minHeight: '100%',
            height: '100%'
          }}

          spellCheck={false}
        />
      </div>
    </div>
  );
}