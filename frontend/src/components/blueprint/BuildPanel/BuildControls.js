import React, { useState } from 'react';
import { useBlueprintContext } from '../Common/BlueprintContext';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Badge } from '../../ui/badge';
import { toast } from 'sonner';
import { Play, Square, RefreshCw, Settings } from 'lucide-react';

export default function BuildControls() {
  const {
    rootPath,
    buildStatus,
    buildBlueprint,
    cancelBuild,
    loading
  } = useBlueprintContext();

  const [scriptName, setScriptName] = useState('buildBlueprint.sh');

  const handleBuild = async () => {
    if (!rootPath) {
      toast.error('No root path set');
      return;
    }

    try {
      await buildBlueprint(scriptName);
      toast.success('Build started');
    } catch (error) {
      toast.error(`Failed to start build: ${error.message}`);
    }
  };

  const handleCancel = async () => {
    try {
      await cancelBuild();
      toast.info('Build cancelled');
    } catch (error) {
      toast.error(`Failed to cancel build: ${error.message}`);
    }
  };

  const getStatusBadge = () => {
    switch (buildStatus) {
      case 'building':
        return <Badge className="bg-blue-500">Building</Badge>;
      case 'success':
        return <Badge className="bg-green-500">Success</Badge>;
      case 'failed':
        return <Badge className="bg-red-500">Failed</Badge>;
      default:
        return <Badge variant="outline">Idle</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings className="h-5 w-5" />
            <span>Build Controls</span>
          </div>
          {getStatusBadge()}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label htmlFor="script-name" className="text-sm font-medium">
            Build Script
          </Label>
          <Input
            id="script-name"
            value={scriptName}
            onChange={(e) => setScriptName(e.target.value)}
            placeholder="buildBlueprint.sh"
            disabled={buildStatus === 'building'}
          />
          <p className="text-xs text-gray-500 mt-1">
            Script should be located in the root directory
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {buildStatus === 'building' ? (
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={loading}
            >
              <Square className="h-4 w-4 mr-2" />
              Cancel Build
            </Button>
          ) : (
            <Button
              onClick={handleBuild}
              disabled={loading || !rootPath}
            >
              {buildStatus === 'building' ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              Start Build
            </Button>
          )}
        </div>

        {!rootPath && (
          <p className="text-sm text-amber-600 bg-amber-50 p-2 rounded">
            ⚠️ Set a root path first to enable building
          </p>
        )}
      </CardContent>
    </Card>
  );
}