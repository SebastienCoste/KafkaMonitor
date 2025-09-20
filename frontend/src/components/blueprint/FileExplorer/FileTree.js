import React, { useState } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { toast } from 'sonner';
import { 
  ChevronDown, 
  ChevronRight, 
  File, 
  Folder, 
  FileText,
  Settings,
  Plus,
  Trash2,
  FolderPlus,
  FilePlus,
  Edit,
  Check,
  X
} from 'lucide-react';

export default function FileTree({ files }) {
  const {
    selectedFile,
    loadFileContent,
    createFile,
    createDirectory,
    deleteFile,
    refreshFileTree
  } = useBlueprintContext();
  
  const [expandedFolders, setExpandedFolders] = useState(new Set(['']));
  const [creatingIn, setCreatingIn] = useState(null);
  const [createType, setCreateType] = useState(null); // 'file' or 'folder'
  const [createName, setCreateName] = useState('');
  const [draggedItem, setDraggedItem] = useState(null);
  const [dragOverItem, setDragOverItem] = useState(null);
  const [renamingItem, setRenamingItem] = useState(null);
  const [renameValue, setRenameValue] = useState('');

  const toggleFolder = (path) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedFolders(newExpanded);
  };

  const handleFileClick = async (filePath) => {
    try {
      await loadFileContent(filePath);
    } catch (error) {
      console.error('Error loading file:', error);
    }
  };

  const handleCreateFile = (parentPath) => {
    setCreatingIn(parentPath);
    setCreateType('file');
    setCreateName('');
  };

  const handleCreateFolder = (parentPath) => {
    setCreatingIn(parentPath);
    setCreateType('folder');
    setCreateName('');
  };

  const handleConfirmCreate = async () => {
    if (!createName.trim()) {
      toast.error('Please enter a name');
      return;
    }

    try {
      const fullPath = creatingIn ? `${creatingIn}/${createName}` : createName;
      
      if (createType === 'file') {
        await createFile(fullPath);
        toast.success(`Created file: ${createName}`);
      } else {
        await createDirectory(fullPath);
        toast.success(`Created folder: ${createName}`);
      }
      
      setCreatingIn(null);
      setCreateType(null);
      setCreateName('');
    } catch (error) {
      toast.error(`Failed to create ${createType}: ${error.message}`);
    }
  };

  const handleCancelCreate = () => {
    setCreatingIn(null);
    setCreateType(null);
    setCreateName('');
  };

  const handleDragStart = (e, item) => {
    setDraggedItem(item);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', ''); // Required for Firefox
  };

  const handleDragOver = (e, item) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    // Only allow dropping into directories
    if (item.type === 'directory') {
      setDragOverItem(item.path);
    }
  };

  const handleDragLeave = (e) => {
    // Only clear if leaving to a non-child element
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOverItem(null);
    }
  };

  const handleDrop = async (e, targetItem) => {
    e.preventDefault();
    setDragOverItem(null);
    
    if (!draggedItem || !targetItem || targetItem.type !== 'directory') {
      return;
    }
    
    // Don't allow dropping item into itself or its children
    if (draggedItem.path === targetItem.path || targetItem.path.startsWith(draggedItem.path + '/')) {
      toast.error('Cannot move item into itself or its children');
      return;
    }
    
    try {
      const sourcePath = draggedItem.path;
      const targetDir = targetItem.path;
      const fileName = draggedItem.name;
      const newPath = targetDir ? `${targetDir}/${fileName}` : fileName;
      
      // Use backend API to move the file/folder
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/blueprint/move-file`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_path: sourcePath,
            destination_path: newPath
          })
        }
      );
      
      if (response.ok) {
        toast.success(`Moved ${draggedItem.name} to ${targetItem.name}`);
        // Refresh file tree to show changes
        refreshFileTree();
      } else {
        throw new Error(`Failed to move item: ${response.status}`);
      }
    } catch (error) {
      toast.error(`Failed to move item: ${error.message}`);
    } finally {
      setDraggedItem(null);
    }
  };

  const handleDelete = async (itemPath, isDirectory = false) => {
    const itemType = isDirectory ? 'folder' : 'file';
    if (!window.confirm(`Are you sure you want to delete this ${itemType} "${itemPath}"?${isDirectory ? '\n\nThis will delete all contents permanently.' : ''}`)) {
      return;
    }

    try {
      await deleteFile(itemPath);
      toast.success(`Deleted ${itemType}: ${itemPath}`);
    } catch (error) {
      toast.error(`Failed to delete ${itemType}: ${error.message}`);
    }
  };

  const handleStartRename = (item) => {
    setRenamingItem(item.path);
    setRenameValue(item.name);
  };

  const handleConfirmRename = async () => {
    if (!renameValue.trim() || renameValue === renamingItem.split('/').pop()) {
      handleCancelRename();
      return;
    }

    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/blueprint/rename-file`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_path: renamingItem,
            new_name: renameValue.trim()
          })
        }
      );
      
      if (response.ok) {
        const result = await response.json();
        toast.success(`Renamed to: ${renameValue}`);
        // Refresh file tree to show changes
        refreshFileTree();
      } else {
        throw new Error(`Failed to rename: ${response.status}`);
      }
    } catch (error) {
      toast.error(`Failed to rename: ${error.message}`);
    } finally {
      handleCancelRename();
    }
  };

  const handleCancelRename = () => {
    setRenamingItem(null);
    setRenameValue('');
  };

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'json':
        return <FileText className="h-4 w-4 text-blue-500" />;
      case 'jslt':
        return <FileText className="h-4 w-4 text-indigo-500" />;
      case 'proto':
        return <Settings className="h-4 w-4 text-purple-500" />;
      case 'yaml':
      case 'yml':
        return <FileText className="h-4 w-4 text-orange-500" />;
      case 'js':
      case 'ts':
        return <FileText className="h-4 w-4 text-yellow-500" />;
      case 'sh':
        return <FileText className="h-4 w-4 text-green-600" />;
      case 'md':
        return <FileText className="h-4 w-4 text-blue-600" />;
      case 'xml':
        return <FileText className="h-4 w-4 text-red-500" />;
      case 'txt':
        return <FileText className="h-4 w-4 text-gray-600" />;
      case 'py':
        return <FileText className="h-4 w-4 text-green-500" />;
      case 'java':
        return <FileText className="h-4 w-4 text-red-600" />;
      case 'css':
        return <FileText className="h-4 w-4 text-blue-400" />;
      case 'html':
        return <FileText className="h-4 w-4 text-orange-600" />;
      default:
        return <File className="h-4 w-4 text-gray-400" />;
    }
  };

  const renderFileTreeItem = (item, depth = 0) => {
    const isExpanded = expandedFolders.has(item.path);
    const isSelected = selectedFile === item.path;

    if (item.type === 'directory') {
      return (
        <div key={item.path}>
          <div
            className={`flex items-center p-2 hover:bg-gray-100 cursor-pointer select-none ${
              dragOverItem === item.path ? 'bg-blue-100 border-l-4 border-blue-500' : ''
            } ${depth > 0 ? `ml-${depth * 4}` : ''}`}
            draggable
            onDragStart={(e) => handleDragStart(e, item)}
            onDragOver={(e) => handleDragOver(e, item)}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, item)}
          >
            <div className="flex items-center space-x-1 flex-1" onClick={() => toggleFolder(item.path)}>
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              )}
              <Folder className="h-4 w-4 text-yellow-500" />
              <span className="text-sm font-medium text-gray-700">{item.name}</span>
            </div>
            
            <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100">
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCreateFile(item.path);
                }}
                className="h-6 w-6 p-0"
                title="Create file"
              >
                <FilePlus className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleCreateFolder(item.path);
                }}
                className="h-6 w-6 p-0"
                title="Create folder"
              >
                <FolderPlus className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(item.path, true); // true indicates it's a directory
                }}
                className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
                title="Delete folder"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          </div>
          
          {/* Show create input if creating in this directory */}
          {creatingIn === item.path && (
            <div className={`flex items-center p-2 ml-${(depth + 1) * 4} bg-blue-50`}>
              <div className="flex items-center space-x-1 flex-1">
                {createType === 'file' ? (
                  <File className="h-4 w-4 text-gray-400" />
                ) : (
                  <Folder className="h-4 w-4 text-yellow-500" />
                )}
                <Input
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder={`Enter ${createType} name`}
                  className="h-6 text-sm"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleConfirmCreate();
                    } else if (e.key === 'Escape') {
                      handleCancelCreate();
                    }
                  }}
                />
                <Button size="sm" onClick={handleConfirmCreate} className="h-6">
                  ✓
                </Button>
                <Button size="sm" variant="ghost" onClick={handleCancelCreate} className="h-6">
                  ✕
                </Button>
              </div>
            </div>
          )}
          
          {isExpanded && item.children && (
            <div className="ml-4">
              {item.children.map(child => renderFileTreeItem(child, depth + 1))}
            </div>
          )}
        </div>
      );
    }

    return (
      <div
        key={item.path}
        className={`group flex items-center p-2 hover:bg-gray-100 cursor-pointer select-none ${
          isSelected ? 'bg-blue-50 border-r-2 border-blue-500' : ''
        } ${depth > 0 ? `ml-${depth * 4}` : ''}`}
        draggable
        onDragStart={(e) => handleDragStart(e, item)}
      >
        <div className="flex items-center space-x-2 flex-1" onClick={() => handleFileClick(item.path)}>
          {getFileIcon(item.name)}
          <span className={`text-sm ${isSelected ? 'text-blue-700 font-medium' : 'text-gray-600'}`}>
            {item.name}
          </span>
        </div>
        <div className="flex items-center space-x-1">
          <div className="text-xs text-gray-400">
            {item.size && formatFileSize(item.size)}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleDelete(item.path, false); // false indicates it's a file
            }}
            className="h-6 w-6 p-0 text-red-600 hover:text-red-700 opacity-0 group-hover:opacity-100"
            title="Delete file"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
    );
  };

  if (!files || files.length === 0) {
    return (
      <div className="p-4">
        <div className="text-center text-gray-500 mb-4">
          <Folder className="h-8 w-8 mx-auto mb-2 text-gray-300" />
          <p className="text-sm">No files found</p>
        </div>
        
        <div className="space-y-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleCreateFile('')}
            className="w-full justify-start"
          >
            <FilePlus className="h-4 w-4 mr-2" />
            Create File
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleCreateFolder('')}
            className="w-full justify-start"
          >
            <FolderPlus className="h-4 w-4 mr-2" />
            Create Folder
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      {/* Root level create input */}
      {creatingIn === '' && (
        <div className="flex items-center p-2 bg-blue-50 border-b">
          <div className="flex items-center space-x-1 flex-1">
            {createType === 'file' ? (
              <File className="h-4 w-4 text-gray-400" />
            ) : (
              <Folder className="h-4 w-4 text-yellow-500" />
            )}
            <Input
              value={createName}
              onChange={(e) => setCreateName(e.target.value)}
              placeholder={`Enter ${createType} name`}
              className="h-6 text-sm"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleConfirmCreate();
                } else if (e.key === 'Escape') {
                  handleCancelCreate();
                }
              }}
            />
            <Button size="sm" onClick={handleConfirmCreate} className="h-6">
              ✓
            </Button>
            <Button size="sm" variant="ghost" onClick={handleCancelCreate} className="h-6">
              ✕
            </Button>
          </div>
        </div>
      )}
      
      {files.map(item => renderFileTreeItem(item))}
      
      {/* Root level create buttons */}
      <div className="p-2 border-t space-y-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => handleCreateFile('')}
          className="w-full justify-start"
        >
          <FilePlus className="h-4 w-4 mr-2" />
          Create File
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => handleCreateFolder('')}
          className="w-full justify-start"
        >
          <FolderPlus className="h-4 w-4 mr-2" />
          Create Folder
        </Button>
      </div>
    </div>
  );
}

function formatFileSize(bytes) {
  const sizes = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 B';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
}