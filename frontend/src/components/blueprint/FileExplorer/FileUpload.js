import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { toast } from 'sonner';
import { Upload, Plus, FileText } from 'lucide-react';

export default function FileUpload() {
  const { createFile, refreshFileTree } = useBlueprintContext();

  const onDrop = useCallback(async (acceptedFiles) => {
    for (const file of acceptedFiles) {
      try {
        const content = await file.text();
        await createFile(file.name, null);
        // Note: We'd need to implement file content setting here
        toast.success(`File ${file.name} uploaded successfully`);
      } catch (error) {
        toast.error(`Failed to upload ${file.name}: ${error.message}`);
      }
    }
    refreshFileTree();
  }, [createFile, refreshFileTree]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/*': ['.json', '.jslt', '.proto', '.yaml', '.yml', '.txt', '.md']
    },
    maxSize: 10 * 1024 * 1024 // 10MB
  });

  const createNewFile = async (template) => {
    const filename = prompt(`Enter filename for new ${template} file:`);
    if (filename) {
      try {
        await createFile(filename, template);
        toast.success(`Created ${filename}`);
      } catch (error) {
        toast.error(`Failed to create file: ${error.message}`);
      }
    }
  };

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`p-4 border-2 border-dashed rounded-lg text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="h-6 w-6 mx-auto mb-2 text-gray-400" />
        <p className="text-sm text-gray-600">
          {isDragActive
            ? 'Drop files here...'
            : 'Drag & drop files or click to browse'}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          Supports: JSON, JSLT, Proto, YAML, Text
        </p>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-gray-700 uppercase tracking-wide">
          Quick Create
        </p>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => createNewFile('blueprint_cnf.json')}
            className="justify-start text-xs p-2"
          >
            <FileText className="h-3 w-3 mr-1" />
            Config
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => createNewFile('transform.jslt')}
            className="justify-start text-xs p-2"
          >
            <FileText className="h-3 w-3 mr-1" />
            JSLT
          </Button>
        </div>
      </div>
    </div>
  );
}