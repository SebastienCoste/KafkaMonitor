import React, { useState } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { toast } from 'sonner';
import { FolderOpen, Check, X, HardDrive } from 'lucide-react';

export default function FileBrowser() {
  const { setRootPath, loading } = useBlueprintContext();
  const [inputPath, setInputPath] = useState('');
  const [showManualInput, setShowManualInput] = useState(false);

  const handleSetPath = async () => {
    if (!inputPath.trim()) {
      toast.error('Please enter a valid directory path');
      return;
    }

    try {
      await setRootPath(inputPath.trim());
      setShowManualInput(false);
      setInputPath('');
      toast.success('Blueprint root path set successfully');
    } catch (error) {
      toast.error(`Failed to set root path: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleCancel = () => {
    setInputPath('');
    setShowManualInput(false);
  };

  const handleBrowseFiles = async () => {
    try {
      // Use the File System Access API if available (modern browsers)
      if ('showDirectoryPicker' in window) {
        const directoryHandle = await window.showDirectoryPicker();
        
        // Try to get the path from the directory handle
        // Note: For security reasons, we can't get the full system path directly
        // We'll prompt the user to confirm the path
        const path = prompt(
          `Selected directory: "${directoryHandle.name}"\n\nPlease enter the full path to this directory:`,
          `/path/to/${directoryHandle.name}`
        );
        
        if (path) {
          await handleSetPathDirectly(path);
        }
      } else {
        // Fallback for older browsers: use hidden file input to browse directories
        const input = document.createElement('input');
        input.type = 'file';
        input.webkitdirectory = true;
        input.multiple = false; // We don't want to upload files
        
        input.onchange = (event) => {
          const files = event.target.files;
          if (files && files.length > 0) {
            // Get directory name from the first file's path
            const firstFile = files[0];
            const pathParts = firstFile.webkitRelativePath.split('/');
            if (pathParts.length > 1) {
              const dirName = pathParts[0];
              const path = prompt(
                `Selected directory: "${dirName}"\n\nPlease enter the full path to this directory:`,
                `/path/to/${dirName}`
              );
              
              if (path) {
                handleSetPathDirectly(path);
              }
            }
          }
          // Clear the input to avoid keeping file references
          input.value = '';
        };
        
        input.click();
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Error selecting directory:', error);
        toast.error('Failed to select directory. Please use manual entry instead.');
      }
    }
  };

  const handleSetPathDirectly = async (path) => {
    try {
      await setRootPath(path);
      toast.success('Blueprint root path set successfully');
    } catch (error) {
      toast.error(`Failed to set root path: ${error.response?.data?.detail || error.message}`);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <FolderOpen className="h-5 w-5" />
          <span>Select Blueprint Directory</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-3">
          <Button
            onClick={handleBrowseFiles}
            disabled={loading}
            className="w-full justify-start"
          >
            <HardDrive className="h-4 w-4 mr-2" />
            Browse for Directory
          </Button>
          
          <Button
            variant="outline"
            onClick={() => setShowManualInput(true)}
            disabled={loading}
            className="w-full justify-start"
          >
            <FolderOpen className="h-4 w-4 mr-2" />
            Enter Path Manually
          </Button>
        </div>

        {showManualInput && (
          <div className="space-y-3 p-4 bg-gray-50 rounded-lg">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">
                Blueprint Root Directory
              </label>
              <Input
                placeholder="Enter full path (e.g., /Users/username/projects/blueprints)"
                value={inputPath}
                onChange={(e) => setInputPath(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSetPath();
                  } else if (e.key === 'Escape') {
                    handleCancel();
                  }
                }}
                autoFocus
              />
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                onClick={handleSetPath}
                disabled={loading || !inputPath.trim()}
                size="sm"
              >
                <Check className="h-4 w-4 mr-1" />
                Set Path
              </Button>
              <Button
                variant="ghost"
                onClick={handleCancel}
                disabled={loading}
                size="sm"
              >
                <X className="h-4 w-4 mr-1" />
                Cancel
              </Button>
            </div>
          </div>
        )}
        
        <div className="text-xs text-gray-500 space-y-1">
          <p><strong>Browse:</strong> Select a directory containing your blueprint files</p>
          <p><strong>Manual:</strong> Enter the full path to your blueprint project directory</p>
          <p>The directory should contain blueprint_cnf.json and other blueprint files.</p>
        </div>
      </CardContent>
    </Card>
  );
}