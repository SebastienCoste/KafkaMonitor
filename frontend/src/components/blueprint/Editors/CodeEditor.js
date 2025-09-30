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

  const handleContentChange = (event) => {
    const newContent = event.target.value;
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

  const getSyntaxLanguage = (filePath) => {
    const ext = getFileExtension(filePath);
    switch (ext) {
      case 'json':
        return 'json';
      case 'jslt':
        return 'javascript'; // JSLT is JavaScript-like
      case 'yaml':
      case 'yml':
        return 'yaml';
      case 'proto':
        return 'protobuf';
      case 'sh':
        return 'bash';
      case 'md':
        return 'markdown';
      case 'js':
        return 'javascript';
      case 'py':
        return 'python';
      case 'html':
        return 'html';
      case 'css':
        return 'css';
      case 'xml':
        return 'xml';
      default:
        return 'text';
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

      {/* Editor Area - Always in edit mode with preview-style colors */}
      <div className="flex-1 overflow-hidden relative">
        <div className="h-full overflow-auto" style={{ background: '#1e1e1e' }}>
          <textarea
            value={currentContent}
            onChange={handleContentChange}
            className="h-full w-full border-0 resize-none focus:outline-none font-mono text-sm"
            style={{ 
              minHeight: 'calc(100vh - 250px)',
              fontSize: '14px',
              fontFamily: '"Cascadia Code", "Fira Code", Monaco, "Lucida Console", monospace',
              background: '#1e1e1e',
              color: '#d4d4d4',
              padding: '16px',
              lineHeight: '1.6',
              tabSize: '2',
              outline: 'none',
              border: 'none',
              caretColor: '#ffffff',
              letterSpacing: '0.5px',
              textShadow: 'none',
              // Apply VS Code Dark+ color scheme for common syntax elements
              WebkitFontSmoothing: 'antialiased',
              MozOsxFontSmoothing: 'grayscale'
            }}
            placeholder="File content will appear here..."
            spellCheck={false}
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
          />
        </div>
      </div>
    </div>
  );
}