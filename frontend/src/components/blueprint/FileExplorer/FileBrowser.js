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

  const handleBrowseFiles = () => {
    // Create a hidden file input element for directory selection
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true; // Enable directory selection
    input.multiple = true;
    
    input.onchange = (event) => {
      const files = event.target.files;
      if (files && files.length > 0) {
        // Get the directory path from the first file
        const firstFile = files[0];
        const pathParts = firstFile.webkitRelativePath.split('/');
        if (pathParts.length > 1) {
          // For security reasons, we can't get the full system path
          // So we'll ask the user to confirm the directory name and enter full path
          const dirName = pathParts[0];
          const fullPath = prompt(
            `Selected directory: "${dirName}"\n\nPlease enter the full path to this directory:`,
            `/path/to/${dirName}`
          );
          
          if (fullPath) {
            setInputPath(fullPath);
            handleSetPathDirectly(fullPath);
          }
        }
      }
    };
    
    input.click();
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