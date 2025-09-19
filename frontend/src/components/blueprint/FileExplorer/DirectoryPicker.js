import React, { useState } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Card, CardContent } from '../../ui/card';
import { toast } from 'sonner';
import { FolderOpen, Check, X } from 'lucide-react';

export default function DirectoryPicker() {
  const { setRootPath, loading } = useBlueprintContext();
  const [inputPath, setInputPath] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  const handleSetPath = async () => {
    if (!inputPath.trim()) {
      toast.error('Please enter a valid directory path');
      return;
    }

    try {
      await setRootPath(inputPath.trim());
      setIsEditing(false);
      toast.success('Blueprint root path set successfully');
    } catch (error) {
      toast.error(`Failed to set root path: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleCancel = () => {
    setInputPath('');
    setIsEditing(false);
  };

  if (!isEditing) {
    return (
      <Button
        variant="outline"
        onClick={() => setIsEditing(true)}
        className="w-full justify-start"
        disabled={loading}
      >
        <FolderOpen className="h-4 w-4 mr-2" />
        Select Blueprint Directory
      </Button>
    );
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="space-y-3">
          <div>
            <label className="text-sm font-medium text-gray-700 mb-1 block">
              Blueprint Root Directory
            </label>
            <Input
              placeholder="Enter full path (e.g., /home/user/blueprints)"
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
          
          <div className="text-xs text-gray-500">
            <p>Enter the full path to your blueprint project directory.</p>
            <p>The directory should contain blueprint_cnf.json and other blueprint files.</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}