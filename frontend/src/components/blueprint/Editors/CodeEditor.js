import React, { useState, useEffect, useRef } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { toast } from 'sonner';
import { Save, RotateCcw } from 'lucide-react';

// CodeMirror imports
import { EditorView } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { basicSetup } from 'codemirror';
import { json } from '@codemirror/lang-json';
import { javascript } from '@codemirror/lang-javascript';
import { yaml } from '@codemirror/lang-yaml';
import { oneDark } from '@codemirror/theme-one-dark';

export default function CodeEditor({ filePath }) {
  const { fileContent, saveFileContent, loading } = useBlueprintContext();
  const [currentContent, setCurrentContent] = useState('');
  const [hasChanges, setHasChanges] = useState(false);
  const editorRef = useRef(null);
  const viewRef = useRef(null);

  // Update content when file changes
  useEffect(() => {
    setCurrentContent(fileContent);
    setHasChanges(false);
    
    // Update CodeMirror editor if it exists
    if (viewRef.current) {
      const transaction = viewRef.current.state.update({
        changes: {
          from: 0,
          to: viewRef.current.state.doc.length,
          insert: fileContent
        }
      });
      viewRef.current.dispatch(transaction);
    }
  }, [fileContent]);

  // Initialize CodeMirror editor
  useEffect(() => {
    if (!editorRef.current || !filePath) return;

    const extensions = [
      basicSetup,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const content = update.state.doc.toString();
          setCurrentContent(content);
          setHasChanges(content !== fileContent);
        }
      }),
      EditorView.theme({
        '&': { height: '100%' },
        '.cm-scroller': { overflow: 'auto' },
        '.cm-editor': { height: '100%' },
        '.cm-focused': { outline: 'none' }
      })
    ];

    // Add language support based on file extension
    const ext = getFileExtension(filePath);
    switch (ext) {
      case 'json':
        extensions.push(json());
        break;
      case 'jslt':
        extensions.push(javascript()); // JSLT is JavaScript-like
        break;
      case 'yaml':
      case 'yml':
        extensions.push(yaml());
        break;
      case 'js':
      case 'sh':
        extensions.push(javascript());
        break;
      default:
        // Plain text, no special highlighting
        break;
    }

    const startState = EditorState.create({
      doc: currentContent,
      extensions
    });

    const view = new EditorView({
      state: startState,
      parent: editorRef.current
    });

    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, [filePath]);

  const getFileExtension = (filename) => {
    return filename.split('.').pop()?.toLowerCase() || '';
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
    
    // Update CodeMirror editor
    if (viewRef.current) {
      const transaction = viewRef.current.state.update({
        changes: {
          from: 0,
          to: viewRef.current.state.doc.length,
          insert: fileContent
        }
      });
      viewRef.current.dispatch(transaction);
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

      {/* CodeMirror Editor */}
      <div className="flex-1 overflow-hidden">
        <div 
          ref={editorRef} 
          className="h-full w-full"
          style={{ 
            minHeight: 'calc(100vh - 250px)',
            fontSize: '14px',
            fontFamily: 'Monaco, "Lucida Console", monospace'
          }} 
        />
      </div>
    </div>
  );
}