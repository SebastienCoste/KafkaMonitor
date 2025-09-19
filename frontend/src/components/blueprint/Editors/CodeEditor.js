import React, { useState, useEffect } from 'react';
import { UnControlled as CodeMirror } from 'react-codemirror2';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { toast } from 'sonner';
import { Save, RotateCcw } from 'lucide-react';

// Import CodeMirror and modes
import 'codemirror/lib/codemirror.css';
import 'codemirror/theme/default.css';
import 'codemirror/theme/material.css';
import 'codemirror/mode/javascript/javascript';
import 'codemirror/mode/yaml/yaml';
import 'codemirror/mode/protobuf/protobuf';
import 'codemirror/addon/edit/closebrackets';
import 'codemirror/addon/edit/matchbrackets';
import 'codemirror/addon/fold/foldcode';
import 'codemirror/addon/fold/foldgutter';
import 'codemirror/addon/fold/brace-fold';
import 'codemirror/addon/fold/foldgutter.css';

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
        return 'application/json';
      case 'jslt':
        return 'application/json'; // JSLT is JSON-like
      case 'yaml':
      case 'yml':
        return 'yaml';
      case 'proto':
        return 'protobuf';
      default:
        return 'text/plain';
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

  const options = {
    mode: getFileMode(filePath),
    theme: 'default',
    lineNumbers: true,
    lineWrapping: true,
    autoCloseBrackets: true,
    matchBrackets: true,
    foldGutter: true,
    gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'],
    indentUnit: 2,
    tabSize: 2,
    extraKeys: {
      'Ctrl-S': handleSave,
      'Cmd-S': handleSave
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
          <Badge variant={getFileMode(filePath) === 'application/json' ? 'default' : 'secondary'}>
            {getFileMode(filePath).split('/').pop().toUpperCase()}
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

      {/* Code Editor */}
      <div className="flex-1 overflow-hidden">
        <CodeMirror
          value={currentContent}
          options={options}
          onChange={(editor, data, value) => {
            setCurrentContent(value);
            setHasChanges(value !== fileContent);
          }}
          className="h-full"
        />
      </div>
    </div>
  );
}