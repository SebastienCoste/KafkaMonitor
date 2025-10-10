import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Textarea } from '../ui/textarea';
import { Checkbox } from '../ui/checkbox';
import { toast } from 'sonner';
import { useBlueprintContext } from './Common/BlueprintContext';
import { 
  GitBranch, 
  GitPullRequest, 
  GitCommit, 
  Download, 
  Upload, 
  RotateCcw, 
  GitMerge,
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
  Loader2
} from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

export default function GitIntegration() {
  const { blueprints, activeBlueprint, loadIntegrationProjects, removeBlueprint } = useBlueprintContext();
  
  // Get current blueprint and project ID
  const currentBlueprint = blueprints.find(bp => bp.id === activeBlueprint);
  const projectId = currentBlueprint?.projectId;
  
  // Debug logging
  useEffect(() => {
    console.log('🔄 GitIntegration: Blueprint changed', {
      activeBlueprint,
      projectId,
      currentBlueprint: currentBlueprint ? {
        id: currentBlueprint.id,
        name: currentBlueprint.name,
        projectId: currentBlueprint.projectId
      } : null
    });
  }, [activeBlueprint, projectId, currentBlueprint]);
  
  // Git repository state
  const [commitMessage, setCommitMessage] = useState('');
  const [forcePush, setForcePush] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]); // Files selected for commit
  
  // Git status state
  const [gitStatus, setGitStatus] = useState(null);
  const [branches, setBranches] = useState([]);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [operation, setOperation] = useState('');
  const [showFileSelection, setShowFileSelection] = useState(false);

  // Load Git status on mount and periodically, only if we have a project ID
  useEffect(() => {
    if (projectId) {
      // Reset state when project changes
      setGitStatus(null);
      setBranches([]);
      setCommitMessage('');
      setForcePush(false);
      setSelectedFiles([]);
      setShowFileSelection(false);
      
      // Load new project's Git status
      loadGitStatus();
      const interval = setInterval(loadGitStatus, 10000); // Every 10 seconds
      return () => clearInterval(interval);
    } else {
      // Clear state when no project selected
      setGitStatus(null);
      setBranches([]);
    }
  }, [projectId]);

  // Load branches when status changes
  useEffect(() => {
    if (gitStatus?.is_repo && projectId) {
      loadBranches();
    }
  }, [gitStatus?.is_repo, projectId]);

  const loadGitStatus = async () => {
    if (!projectId) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}/git/status`);
      if (response.data.success) {
        setGitStatus(response.data.status);
      }
    } catch (error) {
      console.error('Error loading Git status:', error);
      // Don't show toast for status check failures
    }
  };

  const loadBranches = async () => {
    if (!projectId) return;
    
    try {
      const response = await axios.get(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}/git/branches`);
      if (response.data.success) {
        setBranches(response.data.branches);
      }
    } catch (error) {
      console.error('Error loading branches:', error);
    }
  };

  const handlePullChanges = async () => {
    if (!projectId) {
      toast.error('No Git project selected');
      return;
    }
    
    setLoading(true);
    setOperation('pull');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}/git/pull`);

      if (response.data.success) {
        toast.success(response.data.message);
        await loadGitStatus();
      } else {
        toast.error(response.data.message || 'Failed to pull changes');
        if (response.data.error) {
          console.error('Pull error:', response.data.error);
        }
      }
    } catch (error) {
      console.error('Error pulling changes:', error);
      toast.error(error.response?.data?.detail || 'Failed to pull changes');
    } finally {
      setLoading(false);
      setOperation('');
    }
  };

  const handlePushChanges = async () => {
    if (!projectId) {
      toast.error('No Git project selected');
      return;
    }
    
    if (!commitMessage || !commitMessage.trim()) {
      toast.error('Please enter a commit message');
      return;
    }

    // Check if we have uncommitted files and none selected
    if (showFileSelection && gitStatus?.uncommitted_files?.length > 0 && selectedFiles.length === 0) {
      toast.error('Please select at least one file to commit');
      return;
    }

    setLoading(true);
    setOperation('push');

    try {
      const requestBody = {
        commit_message: commitMessage,
        force: forcePush
      };
      
      // Add selected files if file selection is enabled and files are selected
      if (showFileSelection && selectedFiles.length > 0) {
        requestBody.selected_files = selectedFiles;
      }
      
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}/git/push`, requestBody);

      if (response.data.success) {
        toast.success(response.data.message);
        await loadGitStatus();
        // Clear commit message, force push, and selected files after successful push
        setCommitMessage('');
        setForcePush(false);
        setSelectedFiles([]);
        setShowFileSelection(false);
      } else {
        toast.error(response.data.message || 'Failed to push changes');
        if (response.data.error) {
          console.error('Push error:', response.data.error);
        }
      }
    } catch (error) {
      console.error('Error pushing changes:', error);
      toast.error(error.response?.data?.detail || 'Failed to push changes');
    } finally {
      setLoading(false);
      setOperation('');
    }
  };
  
  const handleFileSelection = (file, checked) => {
    if (checked) {
      setSelectedFiles(prev => [...prev, file]);
    } else {
      setSelectedFiles(prev => prev.filter(f => f !== file));
    }
  };
  
  const handleSelectAllFiles = () => {
    if (gitStatus?.uncommitted_files) {
      setSelectedFiles([...gitStatus.uncommitted_files]);
    }
  };
  
  const handleDeselectAllFiles = () => {
    setSelectedFiles([]);
  };

  const handleResetChanges = async () => {
    if (!projectId) {
      toast.error('No Git project selected');
      return;
    }
    
    if (!window.confirm('Are you sure you want to reset all local changes? This cannot be undone.')) {
      return;
    }

    setLoading(true);
    setOperation('reset');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}/git/reset`);

      if (response.data.success) {
        toast.success(response.data.message);
        await loadGitStatus();
      } else {
        toast.error(response.data.message || 'Failed to reset changes');
      }
    } catch (error) {
      console.error('Error resetting changes:', error);
      toast.error(error.response?.data?.detail || 'Failed to reset changes');
    } finally {
      setLoading(false);
      setOperation('');
    }
  };

  const handleSwitchBranch = async (branchName) => {
    if (!projectId) {
      toast.error('No Git project selected');
      return;
    }
    
    if (gitStatus?.has_uncommitted_changes) {
      const confirm = window.confirm(
        'You have uncommitted changes. Switching branches may lose these changes. Continue?'
      );
      if (!confirm) return;
    }

    setLoading(true);
    setOperation('switch');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}/git/switch-branch`, {
        branch_name: branchName
      });

      if (response.data.success) {
        toast.success(response.data.message);
        await loadGitStatus();
        await loadBranches();
      } else {
        toast.error(response.data.message || 'Failed to switch branch');
      }
    } catch (error) {
      console.error('Error switching branch:', error);
      toast.error(error.response?.data?.detail || 'Failed to switch branch');
    } finally {
      setLoading(false);
      setOperation('');
    }
  };

  const handleWipeInstallation = async () => {
    if (!projectId) {
      toast.error('No Git project selected');
      return;
    }

    const confirmMessage = `⚠️ WARNING: This will permanently delete the entire project from the server!\n\nProject: ${currentBlueprint?.name}\nPath: ${projectId}\n\nThis action CANNOT be undone. The project will be removed from:\n- Local integration directory\n- Project manifest\n- All associated data\n\nAre you absolutely sure you want to proceed?`;
    
    if (!window.confirm(confirmMessage)) {
      return;
    }

    // Second confirmation for safety
    const finalConfirm = window.prompt(
      `Type the project name "${currentBlueprint?.name}" to confirm deletion:`
    );
    
    if (finalConfirm !== currentBlueprint?.name) {
      toast.error('Project name did not match. Deletion cancelled.');
      return;
    }

    setLoading(true);
    setOperation('wipe');

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}`, {
        params: { force: true }
      });

      if (response.data.success) {
        toast.success('Project wiped successfully from server!');
        
        // Remove blueprint from context
        if (removeBlueprint && currentBlueprint) {
          removeBlueprint(currentBlueprint.id);
        }
        
        // Reload integration projects to update the list
        if (loadIntegrationProjects) {
          await loadIntegrationProjects();
        }
        
        // Clear local state
        setGitStatus(null);
        setBranches([]);
        
        // Show success message
        toast.info('Project removed. Please select another project to continue.');
      } else {
        toast.error(response.data.message || 'Failed to wipe project');
      }
    } catch (error) {
      console.error('Error wiping project:', error);
      toast.error(error.response?.data?.detail || 'Failed to wipe project');
    } finally {
      setLoading(false);
      setOperation('');
    }
  };

  const renderCloneForm = () => null; // Remove clone form since we use GitProjectSelector now

  const renderGitStatus = () => {
    if (!gitStatus || !gitStatus.is_repo) {
      return (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No Git repository found in integrator folder. Clone a repository to get started.
          </AlertDescription>
        </Alert>
      );
    }

    return (
      <Card className="mb-4">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span>Repository Status</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadGitStatus}
              disabled={loading}
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs text-gray-600">Current Branch</Label>
              <div className="flex items-center space-x-2 mt-1">
                <GitBranch className="h-4 w-4 text-blue-600" />
                <Badge variant="outline">{gitStatus.current_branch}</Badge>
              </div>
            </div>

            <div>
              <Label className="text-xs text-gray-600">Status</Label>
              <div className="mt-1">
                {gitStatus.has_uncommitted_changes ? (
                  <Badge variant="destructive">
                    {gitStatus.uncommitted_files?.length || 0} uncommitted changes
                  </Badge>
                ) : (
                  <Badge variant="success" className="bg-green-100 text-green-800">
                    Clean working tree
                  </Badge>
                )}
              </div>
            </div>
          </div>

          {(gitStatus.ahead_commits > 0 || gitStatus.behind_commits > 0) && (
            <div className="flex items-center space-x-4 text-sm">
              {gitStatus.ahead_commits > 0 && (
                <span className="text-orange-600">
                  ↑ {gitStatus.ahead_commits} ahead
                </span>
              )}
              {gitStatus.behind_commits > 0 && (
                <span className="text-blue-600">
                  ↓ {gitStatus.behind_commits} behind
                </span>
              )}
            </div>
          )}

          {gitStatus.last_commit && (
            <div className="text-xs text-gray-600 border-t pt-2">
              <div className="flex items-center space-x-2">
                <Clock className="h-3 w-3" />
                <span>Last commit: {gitStatus.last_commit} by {gitStatus.last_commit_author}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderGitOperations = () => {
    if (!gitStatus || !gitStatus.is_repo) {
      return null;
    }

    return (
      <>
        {/* Branch Management */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <GitMerge className="h-5 w-5" />
              <span>Branch Management</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Label>Switch Branch</Label>
              <select
                className="w-full border rounded px-3 py-2"
                value={gitStatus.current_branch}
                onChange={(e) => handleSwitchBranch(e.target.value)}
                disabled={loading}
              >
                {branches.map((branchName) => (
                  <option key={branchName} value={branchName}>
                    {branchName}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Pull Changes */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Download className="h-5 w-5" />
              <span>Pull Changes</span>
            </CardTitle>
            <CardDescription>
              Pull the latest changes from the remote repository
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handlePullChanges}
              disabled={loading}
              variant="outline"
              className="w-full"
            >
              {loading && operation === 'pull' ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Pulling...
                </>
              ) : (
                <>
                  <GitPullRequest className="h-4 w-4 mr-2" />
                  Pull Changes
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Push Changes */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Upload className="h-5 w-5" />
              <span>Commit & Push</span>
            </CardTitle>
            <CardDescription>
              Commit all changes and push to remote repository
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* File Selection Toggle */}
            {gitStatus?.uncommitted_files && gitStatus.uncommitted_files.length > 0 && (
              <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium text-blue-900">
                    {gitStatus.uncommitted_files.length} file(s) changed
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowFileSelection(!showFileSelection);
                    if (!showFileSelection) {
                      // Auto-select all files when opening
                      handleSelectAllFiles();
                    }
                  }}
                  disabled={loading}
                >
                  {showFileSelection ? 'Hide Files' : 'Select Files to Commit'}
                </Button>
              </div>
            )}
            
            {/* File Selection List */}
            {showFileSelection && gitStatus?.uncommitted_files && gitStatus.uncommitted_files.length > 0 && (
              <Card className="bg-gray-50">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold">Select Files to Commit</CardTitle>
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleSelectAllFiles}
                        disabled={loading}
                        className="text-xs"
                      >
                        Select All
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDeselectAllFiles}
                        disabled={loading}
                        className="text-xs"
                      >
                        Deselect All
                      </Button>
                    </div>
                  </div>
                  <CardDescription className="text-xs">
                    Selected: {selectedFiles.length} of {gitStatus.uncommitted_files.length} files
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {gitStatus.uncommitted_files.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center space-x-2 p-2 hover:bg-white rounded transition-colors"
                      >
                        <Checkbox
                          id={`file-${index}`}
                          checked={selectedFiles.includes(file)}
                          onCheckedChange={(checked) => handleFileSelection(file, checked)}
                          disabled={loading}
                        />
                        <Label
                          htmlFor={`file-${index}`}
                          className="flex-1 text-sm font-mono cursor-pointer text-gray-700"
                        >
                          {file}
                        </Label>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
            
            <div>
              <Label htmlFor="commit-message">Commit Message *</Label>
              <Textarea
                id="commit-message"
                placeholder="Enter commit message..."
                value={commitMessage}
                onChange={(e) => setCommitMessage(e.target.value)}
                disabled={loading}
                rows={3}
              />
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="force-push"
                checked={forcePush}
                onCheckedChange={setForcePush}
                disabled={loading}
              />
              <Label htmlFor="force-push" className="text-sm font-normal cursor-pointer">
                Force push (use with caution)
              </Label>
            </div>

            <Button
              onClick={handlePushChanges}
              disabled={loading || !commitMessage.trim()}
              className="w-full"
            >
              {loading && operation === 'push' ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Pushing...
                </>
              ) : (
                <>
                  <GitCommit className="h-4 w-4 mr-2" />
                  Commit & Push
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Reset Changes */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <RotateCcw className="h-5 w-5" />
              <span>Reset Changes</span>
            </CardTitle>
            <CardDescription>
              Discard all local changes and reset to last commit
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleResetChanges}
              disabled={loading}
              variant="destructive"
              className="w-full"
            >
              {loading && operation === 'reset' ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Resetting...
                </>
              ) : (
                <>
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Reset All Changes
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </>
    );
  };

  // Show message if no project is selected
  if (!projectId || !currentBlueprint) {
    return (
      <div className="p-6">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No Git project selected. Please select or add a Git project from the Blueprint Creator setup.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const renderProjectInfo = () => (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <GitBranch className="h-5 w-5" />
            <span>Current Project</span>
          </div>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleWipeInstallation}
            disabled={loading}
            className="bg-red-600 hover:bg-red-700"
          >
            <AlertCircle className="h-4 w-4 mr-2" />
            Wipe Installation
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div>
            <span className="text-sm font-medium text-gray-600">Name:</span>
            <span className="ml-2 text-sm">{currentBlueprint.name}</span>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-600">URL:</span>
            <span className="ml-2 text-sm break-all">{currentBlueprint.gitUrl}</span>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-600">Branch:</span>
            <span className="ml-2 text-sm">{currentBlueprint.branch}</span>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-600">Project ID:</span>
            <span className="ml-2 text-sm text-gray-500">{projectId}</span>
          </div>
        </div>
        
        <Alert className="mt-4 bg-red-50 border-red-200">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-xs text-red-800">
            <strong>Warning:</strong> "Wipe Installation" permanently deletes this project from the server. This action cannot be undone.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );

  return (
    <div className="git-integration space-y-4">
      {renderProjectInfo()}
      {renderGitStatus()}
      {renderGitOperations()}
    </div>
  );
}