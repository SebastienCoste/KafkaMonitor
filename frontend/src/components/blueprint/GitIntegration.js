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
  const { blueprints, activeBlueprint } = useBlueprintContext();
  
  // Get current blueprint and project ID
  const currentBlueprint = blueprints.find(bp => bp.id === activeBlueprint);
  const projectId = currentBlueprint?.projectId;
  
  // Git repository state
  const [commitMessage, setCommitMessage] = useState('');
  const [forcePush, setForcePush] = useState(false);
  
  // Git status state
  const [gitStatus, setGitStatus] = useState(null);
  const [branches, setBranches] = useState([]);
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [operation, setOperation] = useState('');

  // Load Git status on mount and periodically, only if we have a project ID
  useEffect(() => {
    if (projectId) {
      loadGitStatus();
      const interval = setInterval(loadGitStatus, 10000); // Every 10 seconds
      return () => clearInterval(interval);
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

    setLoading(true);
    setOperation('push');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/integration/projects/${projectId}/git/push`, {
        commit_message: commitMessage,
        force: forcePush
      });

      if (response.data.success) {
        toast.success(response.data.message);
        await loadGitStatus();
        // Clear commit message
        setCommitMessage('');
        setForcePush(false);
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

  const handleResetChanges = async () => {
    if (!window.confirm('Are you sure you want to reset all local changes? This cannot be undone.')) {
      return;
    }

    setLoading(true);
    setOperation('reset');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/git/reset`);

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
    if (gitStatus?.has_uncommitted_changes) {
      const confirm = window.confirm(
        'You have uncommitted changes. Switching branches may lose these changes. Continue?'
      );
      if (!confirm) return;
    }

    setLoading(true);
    setOperation('switch');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/blueprint/git/switch-branch`, {
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

  const renderCloneForm = () => (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <GitBranch className="h-5 w-5" />
          <span>Clone Repository</span>
        </CardTitle>
        <CardDescription>
          Enter a Git repository URL to clone it into the integrator folder
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <Label htmlFor="git-url">Git Repository URL</Label>
            <Input
              id="git-url"
              placeholder="https://github.com/user/repo.git"
              value={gitUrl}
              onChange={(e) => setGitUrl(e.target.value)}
              disabled={loading}
            />
          </div>

          <div>
            <Label htmlFor="branch">Branch Name</Label>
            <Input
              id="branch"
              placeholder="main"
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
              disabled={loading}
            />
          </div>

          <Button
            onClick={handleCloneRepository}
            disabled={loading || !gitUrl}
            className="w-full"
          >
            {loading && operation === 'clone' ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Cloning...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Clone Repository
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );

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

  return (
    <div className="git-integration space-y-4">
      {renderGitStatus()}
      {showCloneForm && renderCloneForm()}
      {renderGitOperations()}
    </div>
  );
}