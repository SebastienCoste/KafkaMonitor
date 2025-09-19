import React, { useEffect, useRef } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Button } from '../../ui/button';
import { Badge } from '../../ui/badge';
import { Terminal, Trash2 } from 'lucide-react';

export default function ConsoleOutput() {
  const { buildOutput, buildStatus, setBuildOutput } = useBlueprintContext();
  const outputRef = useRef(null);

  // Auto-scroll to bottom when new output arrives
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [buildOutput]);

  const clearOutput = () => {
    setBuildOutput([]);
  };

  const getStatusColor = () => {
    switch (buildStatus) {
      case 'building':
        return 'text-blue-600';
      case 'success':
        return 'text-green-600';
      case 'failed':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Terminal className="h-5 w-5" />
            <span>Build Console</span>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className={getStatusColor()}>
              {buildStatus.charAt(0).toUpperCase() + buildStatus.slice(1)}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearOutput}
              disabled={buildOutput.length === 0}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <div
          ref={outputRef}
          className="h-full overflow-y-auto bg-gray-900 text-gray-100 font-mono text-sm p-4"
        >
          {buildOutput.length === 0 ? (
            <div className="text-gray-500 italic">
              No build output yet. Start a build to see console output here.
            </div>
          ) : (
            buildOutput.map((line, index) => (
              <div
                key={index}
                className={`mb-1 ${
                  line.toLowerCase().includes('error') 
                    ? 'text-red-400' 
                    : line.toLowerCase().includes('warning')
                    ? 'text-yellow-400'
                    : line.toLowerCase().includes('success')
                    ? 'text-green-400'
                    : 'text-gray-100'
                }`}
              >
                <span className="text-gray-500 mr-2">{index + 1:03d}</span>
                {line}
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}