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
  FilePlus
} from 'lucide-react';

export default function FileTree({ files }) {
  const {
    selectedFile,
    loadFileContent,
    createFile,
    createDirectory,
    deleteFile
  } = useBlueprintContext();
  
  const [expandedFolders, setExpandedFolders] = useState(new Set(['']));
  const [creatingIn, setCreatingIn] = useState(null);
  const [createType, setCreateType] = useState(null); // 'file' or 'folder'
  const [createName, setCreateName] = useState('');

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

  const handleDelete = async (itemPath) => {
    if (!window.confirm(`Are you sure you want to delete "${itemPath}"?`)) {
      return;
    }

    try {
      await deleteFile(itemPath);
      toast.success(`Deleted: ${itemPath}`);
    } catch (error) {
      toast.error(`Failed to delete: ${error.message}`);
    }
  };

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'json':
      case 'jslt':
        return <FileText className="h-4 w-4 text-blue-500" />;
      case 'proto':
        return <Settings className="h-4 w-4 text-purple-500" />;
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
              depth > 0 ? `ml-${depth * 4}` : ''
            }`}
            onClick={() => toggleFolder(item.path)}
          >
            <div className="flex items-center space-x-1 flex-1">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              )}
              <Folder className="h-4 w-4 text-yellow-500" />
              <span className="text-sm font-medium text-gray-700">{item.name}</span>
            </div>
          </div>
          
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
        className={`flex items-center p-2 hover:bg-gray-100 cursor-pointer select-none ${
          isSelected ? 'bg-blue-50 border-r-2 border-blue-500' : ''
        } ${depth > 0 ? `ml-${depth * 4}` : ''}`}
        onClick={() => handleFileClick(item.path)}
      >
        <div className="flex items-center space-x-2 flex-1">
          {getFileIcon(item.name)}
          <span className={`text-sm ${isSelected ? 'text-blue-700 font-medium' : 'text-gray-600'}`}>
            {item.name}
          </span>
        </div>
        <div className="text-xs text-gray-400">
          {item.size && formatFileSize(item.size)}
        </div>
      </div>
    );
  };

  if (!files || files.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <Folder className="h-8 w-8 mx-auto mb-2 text-gray-300" />
        <p className="text-sm">No files found</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      {files.map(item => renderFileTreeItem(item))}
    </div>
  );
}

function formatFileSize(bytes) {
  const sizes = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 B';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
}