import React, { useState, useEffect } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { toast } from 'sonner';
import { Save, RotateCcw } from 'lucide-react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-markdown';
import 'prismjs/themes/prism-tomorrow.css';

export default function CodeEditor({ filePath }) {
  const { fileContent, saveFileContent, loading } = useBlueprintContext();
  const [currentContent, setCurrentContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  // Always in edit mode - removed isEditing state

  // Update content when file changes
  useEffect(() => {
    setCurrentContent(fileContent || '');
    setHasChanges(false);
  }, [fileContent]);

  const handleContentChange = (newContent) => {
    // react-simple-code-editor passes the value directly, not an event object
    setCurrentContent(newContent);
    setHasChanges(newContent !== fileContent);
  };

  const getFileExtension = (filePath) => {
    return filePath?.split('.').pop()?.toLowerCase() || '';
  };

  const getFileMode = (filename) => {
    const ext = getFileExtension(filename);
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
      case 'sh':
        return 'Shell Script';
      case 'md':
        return 'Markdown';
      case 'js':
        return 'JavaScript';
      case 'py':
        return 'Python';
      default:
        return 'Text';
    }
  };

  const getPrismLanguage = (filePath) => {
    const ext = getFileExtension(filePath);
    switch (ext) {
      case 'json':
        return languages.json;
      case 'jslt':
      case 'js':
        return languages.javascript;
      case 'yaml':
      case 'yml':
        return languages.yaml;
      case 'sh':
        return languages.bash;
      case 'md':
        return languages.markdown;
      case 'py':
        return languages.python;
      default:
        return languages.javascript; // Fallback
    }
  };
  
  const highlightWithPrism = (code) => {
    try {
      return highlight(code, getPrismLanguage(filePath), getFileExtension(filePath));
    } catch (error) {
      return code;
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
          {/* Removed Edit/Preview toggle - always in edit mode now */}
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

      {/* Editor Area - Always in edit mode with syntax highlighting */}
      <div className="flex-1 overflow-hidden relative">
        <div className="h-full overflow-auto" style={{ background: '#2d2d2d' }}>
          <Editor
            value={currentContent}
            onValueChange={handleContentChange}
            highlight={highlightWithPrism}
            padding={16}
            style={{
              fontFamily: '"Fira Code", "Cascadia Code", Monaco, "Courier New", monospace',
              fontSize: 14,
              lineHeight: 1.6,
              minHeight: 'calc(100vh - 250px)',
              background: '#2d2d2d',
              color: '#ccc',
              caretColor: '#ffffff',
            }}
            textareaClassName="editor-textarea"
            preClassName="editor-pre"
            placeholder="File content will appear here..."
          />
        </div>
      </div>
    </div>
  );
}