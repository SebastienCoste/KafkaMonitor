import React from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { X, FileText, Settings, Code } from 'lucide-react';

export default function FileTabs() {
  const { openTabs, activeTab, setActiveTab, closeTab } = useBlueprintContext();

  if (openTabs.length === 0) {
    return null;
  }

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'json':
      case 'jslt':
        return <Code className="h-3 w-3 text-blue-500" />;
      case 'proto':
        return <Settings className="h-3 w-3 text-purple-500" />;
      case 'yaml':
      case 'yml':
        return <FileText className="h-3 w-3 text-green-500" />;
      case 'sh':
        return <FileText className="h-3 w-3 text-orange-500" />;
      default:
        return <FileText className="h-3 w-3 text-gray-400" />;
    }
  };

  const getFileName = (path) => {
    return path.split('/').pop() || path;
  };

  return (
    <div className="flex bg-gray-100 border-b border-gray-200 overflow-x-auto">
      {openTabs.map((tab) => (
        <div
          key={tab.path}
          className={`flex items-center px-3 py-2 border-r border-gray-200 cursor-pointer min-w-0 ${
            activeTab === tab.path
              ? 'bg-white border-b-2 border-blue-500'
              : 'hover:bg-gray-50'
          }`}
          onClick={() => setActiveTab(tab.path)}
        >
          <div className="flex items-center space-x-2 min-w-0">
            {getFileIcon(tab.path)}
            <span className="text-sm truncate max-w-32">
              {getFileName(tab.path)}
            </span>
            {tab.hasChanges && (
              <div className="w-2 h-2 bg-orange-400 rounded-full" title="Unsaved changes" />
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="ml-2 h-4 w-4 p-0 hover:bg-gray-200"
            onClick={(e) => {
              e.stopPropagation();
              closeTab(tab.path);
            }}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      ))}
    </div>
  );
}