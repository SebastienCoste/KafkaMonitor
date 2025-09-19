import React, { useEffect } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { FileArchive, Download, RefreshCw } from 'lucide-react';

export default function OutputFiles() {
  const { outputFiles, loadOutputFiles, rootPath, loading } = useBlueprintContext();

  // Only load output files when component mounts or rootPath changes
  useEffect(() => {
    if (rootPath) {
      loadOutputFiles();
    }
  }, [rootPath]); // Removed loadOutputFiles dependency to prevent frequent reloads


  const formatFileSize = (bytes) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${Math.round(bytes / Math.pow(1024, i) * 100) / 100} ${sizes[i]}`;
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const handleDownload = (file) => {
    // In a real implementation, this would trigger a file download
    console.log('Download file:', file);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileArchive className="h-5 w-5" />
            <span>Output Files</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={loadOutputFiles}
            disabled={loading || !rootPath}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!rootPath ? (
          <p className="text-sm text-gray-500 text-center py-4">
            Set a root path to see output files
          </p>
        ) : outputFiles.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">
            No output files found. Build a blueprint to generate .tgz files.
          </p>
        ) : (
          <div className="space-y-3">
            {outputFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border"
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <FileArchive className="h-4 w-4 text-blue-500" />
                    <span className="font-medium text-sm">{file.name}</span>
                    <Badge variant="outline" className="text-xs">
                      {formatFileSize(file.size)}
                    </Badge>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    <span>Modified: {formatDate(file.modified)}</span>
                    <span className="ml-3">Directory: {file.directory}</span>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDownload(file)}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}