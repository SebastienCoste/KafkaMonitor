"""
Git Service - Handles all Git operations for Blueprint Creator
"""

import subprocess
import asyncio
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitOperationType(Enum):
    """Git operation types"""
    CLONE = "clone"
    PULL = "pull"
    PUSH = "push"
    RESET = "reset"
    SWITCH_BRANCH = "switch_branch"
    STATUS = "status"
    FETCH = "fetch"


@dataclass
class GitOperationResult:
    """Result of a Git operation"""
    success: bool
    operation: GitOperationType
    message: str
    output: str = ""
    error: str = ""
    details: Optional[Dict[str, Any]] = None


@dataclass
class GitRepository:
    """Git repository information"""
    url: str
    branch: str
    local_path: Path
    credentials: Optional[Dict[str, str]] = None


@dataclass
class GitStatus:
    """Current Git repository status"""
    is_repo: bool
    current_branch: str = ""
    remote_url: str = ""
    has_uncommitted_changes: bool = False
    uncommitted_files: List[str] = None
    ahead_commits: int = 0
    behind_commits: int = 0
    last_commit: str = ""
    last_commit_author: str = ""
    last_commit_date: str = ""
    
    def __post_init__(self):
        if self.uncommitted_files is None:
            self.uncommitted_files = []


class GitService:
    """Service for handling Git operations"""
    
    def __init__(self, integrator_path: str, timeout: int = 300):
        """
        Initialize Git service
        
        Args:
            integrator_path: Path to integrator directory
            timeout: Timeout for Git operations in seconds
        """
        self.integrator_path = Path(integrator_path)
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Create integrator directory if it doesn't exist
        self.integrator_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git config
        self._initialize_git_config()
    
    def _initialize_git_config(self):
        """Initialize basic Git configuration"""
        try:
            # Set default Git config if not set
            subprocess.run(
                ['git', 'config', '--global', 'user.name'],
                capture_output=True,
                text=True,
                timeout=5
            )
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            self.logger.warning(f"Could not check Git config: {e}")
    
    def validate_git_url(self, url: str) -> bool:
        """
        Validate Git URL format and security
        
        Args:
            url: Git repository URL
            
        Returns:
            True if valid, False otherwise
        """
        if not url:
            return False
        
        # Check for valid URL patterns
        # Support HTTPS and SSH formats
        https_pattern = r'^https?://[a-zA-Z0-9-._~:/?#\[\]@!$&\'()*+,;=]+\.git$|^https?://[a-zA-Z0-9-._~:/?#\[\]@!$&\'()*+,;=]+$'
        ssh_pattern = r'^git@[a-zA-Z0-9.-]+:[a-zA-Z0-9/_.-]+\.git$|^git@[a-zA-Z0-9.-]+:[a-zA-Z0-9/_.-]+$'
        
        if re.match(https_pattern, url) or re.match(ssh_pattern, url):
            # Additional security: prevent local file system access
            parsed = urlparse(url)
            if parsed.scheme in ['file', '']:
                return False
            return True
        
        return False
    
    def sanitize_branch_name(self, branch: str) -> str:
        """
        Sanitize branch name to prevent command injection
        
        Args:
            branch: Branch name
            
        Returns:
            Sanitized branch name
        """
        # Remove dangerous characters
        sanitized = re.sub(r'[^a-zA-Z0-9._/-]', '', branch)
        return sanitized
    
    async def _run_git_command(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str, str]:
        """
        Execute Git command safely with async subprocess
        
        Args:
            args: Git command arguments
            cwd: Working directory
            env: Environment variables
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        if cwd is None:
            cwd = self.integrator_path
        
        try:
            # Prepare command
            cmd = ['git'] + args
            self.logger.info(f"Executing Git command: {' '.join(cmd)} in {cwd}")
            
            # Create process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False, "", f"Git command timed out after {self.timeout} seconds"
            
            stdout_str = stdout.decode('utf-8') if stdout else ""
            stderr_str = stderr.decode('utf-8') if stderr else ""
            
            success = process.returncode == 0
            
            if not success:
                self.logger.error(f"Git command failed: {stderr_str}")
            else:
                self.logger.info(f"Git command succeeded")
            
            return success, stdout_str, stderr_str
            
        except Exception as e:
            self.logger.error(f"Error executing Git command: {e}")
            return False, "", str(e)
    
    async def clone_repository(
        self,
        git_url: str,
        branch: str,
        credentials: Optional[Dict[str, str]] = None
    ) -> GitOperationResult:
        """
        Clone repository into integrator folder
        
        Args:
            git_url: Git repository URL
            branch: Branch to clone
            credentials: Optional credentials (username, password/token)
            
        Returns:
            GitOperationResult
        """
        try:
            # Validate URL
            if not self.validate_git_url(git_url):
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.CLONE,
                    message="Invalid Git URL",
                    error="URL validation failed"
                )
            
            # Sanitize branch name
            branch = self.sanitize_branch_name(branch)
            if not branch:
                branch = "main"
            
            # Check if integrator folder is empty
            if list(self.integrator_path.iterdir()):
                # Directory not empty - check if it's already a git repo
                git_dir = self.integrator_path / '.git'
                if git_dir.exists():
                    return GitOperationResult(
                        success=False,
                        operation=GitOperationType.CLONE,
                        message="Integrator directory already contains a Git repository",
                        error="Directory not empty. Use pull to update or reset to start fresh."
                    )
            
            # Prepare environment with credentials if provided
            env = os.environ.copy()
            modified_url = git_url
            
            if credentials and 'username' in credentials and 'password' in credentials:
                # Inject credentials into HTTPS URL
                if git_url.startswith('https://'):
                    parsed = urlparse(git_url)
                    modified_url = f"https://{credentials['username']}:{credentials['password']}@{parsed.netloc}{parsed.path}"
            elif credentials and 'token' in credentials:
                # Use token authentication
                if git_url.startswith('https://'):
                    parsed = urlparse(git_url)
                    modified_url = f"https://{credentials['token']}@{parsed.netloc}{parsed.path}"
            
            # Clone repository
            args = ['clone', '--branch', branch, '--single-branch', modified_url, '.']
            success, stdout, stderr = await self._run_git_command(
                args,
                cwd=self.integrator_path,
                env=env
            )
            
            if success:
                return GitOperationResult(
                    success=True,
                    operation=GitOperationType.CLONE,
                    message=f"Successfully cloned repository on branch '{branch}'",
                    output=stdout,
                    details={'branch': branch, 'url': git_url}
                )
            else:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.CLONE,
                    message="Failed to clone repository",
                    error=stderr,
                    output=stdout
                )
        
        except Exception as e:
            self.logger.error(f"Error cloning repository: {e}")
            return GitOperationResult(
                success=False,
                operation=GitOperationType.CLONE,
                message="Error during clone operation",
                error=str(e)
            )
    
    async def pull_changes(self) -> GitOperationResult:
        """
        Pull latest changes from remote
        
        Returns:
            GitOperationResult
        """
        try:
            # Check if directory is a Git repository
            if not (self.integrator_path / '.git').exists():
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PULL,
                    message="Not a Git repository",
                    error="Integrator directory is not a Git repository"
                )
            
            # Fetch changes first
            success, stdout, stderr = await self._run_git_command(['fetch'])
            if not success:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PULL,
                    message="Failed to fetch changes",
                    error=stderr
                )
            
            # Pull changes
            success, stdout, stderr = await self._run_git_command(['pull'])
            
            if success:
                return GitOperationResult(
                    success=True,
                    operation=GitOperationType.PULL,
                    message="Successfully pulled latest changes",
                    output=stdout
                )
            else:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PULL,
                    message="Failed to pull changes",
                    error=stderr,
                    output=stdout
                )
        
        except Exception as e:
            self.logger.error(f"Error pulling changes: {e}")
            return GitOperationResult(
                success=False,
                operation=GitOperationType.PULL,
                message="Error during pull operation",
                error=str(e)
            )
    
    async def push_changes(
        self,
        commit_message: str,
        force: bool = False
    ) -> GitOperationResult:
        """
        Add all changes, commit, and push to remote
        
        Args:
            commit_message: Commit message
            force: Whether to force push
            
        Returns:
            GitOperationResult
        """
        try:
            # Check if directory is a Git repository
            if not (self.integrator_path / '.git').exists():
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PUSH,
                    message="Not a Git repository",
                    error="Integrator directory is not a Git repository"
                )
            
            # Validate commit message
            if not commit_message or not commit_message.strip():
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PUSH,
                    message="Commit message is required",
                    error="Please provide a commit message"
                )
            
            # Add all changes
            success, stdout, stderr = await self._run_git_command(['add', '-A'])
            if not success:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PUSH,
                    message="Failed to stage changes",
                    error=stderr
                )
            
            # Check if there are changes to commit
            success, stdout, stderr = await self._run_git_command(['diff', '--cached', '--quiet'])
            if success:
                # No changes to commit
                return GitOperationResult(
                    success=True,
                    operation=GitOperationType.PUSH,
                    message="No changes to commit",
                    output="Working tree is clean"
                )
            
            # Commit changes
            success, stdout, stderr = await self._run_git_command(['commit', '-m', commit_message])
            if not success:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PUSH,
                    message="Failed to commit changes",
                    error=stderr,
                    output=stdout
                )
            
            # Push changes
            push_args = ['push']
            if force:
                push_args.append('--force')
            
            success, stdout, stderr = await self._run_git_command(push_args)
            
            if success:
                return GitOperationResult(
                    success=True,
                    operation=GitOperationType.PUSH,
                    message="Successfully pushed changes to remote",
                    output=stdout + "\n" + stderr,
                    details={'force': force, 'commit_message': commit_message}
                )
            else:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.PUSH,
                    message="Failed to push changes",
                    error=stderr,
                    output=stdout
                )
        
        except Exception as e:
            self.logger.error(f"Error pushing changes: {e}")
            return GitOperationResult(
                success=False,
                operation=GitOperationType.PUSH,
                message="Error during push operation",
                error=str(e)
            )
    
    async def reset_changes(self) -> GitOperationResult:
        """
        Reset all local changes to HEAD
        
        Returns:
            GitOperationResult
        """
        try:
            # Check if directory is a Git repository
            if not (self.integrator_path / '.git').exists():
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.RESET,
                    message="Not a Git repository",
                    error="Integrator directory is not a Git repository"
                )
            
            # Reset all changes
            success, stdout, stderr = await self._run_git_command(['reset', '--hard', 'HEAD'])
            if not success:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.RESET,
                    message="Failed to reset changes",
                    error=stderr
                )
            
            # Clean untracked files
            success2, stdout2, stderr2 = await self._run_git_command(['clean', '-fd'])
            
            combined_output = stdout + "\n" + stdout2
            
            return GitOperationResult(
                success=True,
                operation=GitOperationType.RESET,
                message="Successfully reset all local changes",
                output=combined_output
            )
        
        except Exception as e:
            self.logger.error(f"Error resetting changes: {e}")
            return GitOperationResult(
                success=False,
                operation=GitOperationType.RESET,
                message="Error during reset operation",
                error=str(e)
            )
    
    async def switch_branch(self, branch_name: str) -> GitOperationResult:
        """
        Switch to a different branch
        
        Args:
            branch_name: Name of branch to switch to
            
        Returns:
            GitOperationResult
        """
        try:
            # Check if directory is a Git repository
            if not (self.integrator_path / '.git').exists():
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.SWITCH_BRANCH,
                    message="Not a Git repository",
                    error="Integrator directory is not a Git repository"
                )
            
            # Sanitize branch name
            branch_name = self.sanitize_branch_name(branch_name)
            if not branch_name:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.SWITCH_BRANCH,
                    message="Invalid branch name",
                    error="Branch name is invalid"
                )
            
            # Fetch latest branches
            await self._run_git_command(['fetch'])
            
            # Check if branch exists locally
            success, stdout, stderr = await self._run_git_command(['rev-parse', '--verify', branch_name])
            
            if success:
                # Branch exists locally, just checkout
                success, stdout, stderr = await self._run_git_command(['checkout', branch_name])
            else:
                # Try to checkout remote branch
                success, stdout, stderr = await self._run_git_command(
                    ['checkout', '-b', branch_name, f'origin/{branch_name}']
                )
            
            if success:
                return GitOperationResult(
                    success=True,
                    operation=GitOperationType.SWITCH_BRANCH,
                    message=f"Successfully switched to branch '{branch_name}'",
                    output=stdout,
                    details={'branch': branch_name}
                )
            else:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.SWITCH_BRANCH,
                    message=f"Failed to switch to branch '{branch_name}'",
                    error=stderr,
                    output=stdout
                )
        
        except Exception as e:
            self.logger.error(f"Error switching branch: {e}")
            return GitOperationResult(
                success=False,
                operation=GitOperationType.SWITCH_BRANCH,
                message="Error during branch switch operation",
                error=str(e)
            )
    
    async def get_status(self) -> GitStatus:
        """
        Get current Git repository status
        
        Returns:
            GitStatus object
        """
        try:
            # Check if directory is a Git repository
            if not (self.integrator_path / '.git').exists():
                return GitStatus(is_repo=False)
            
            status = GitStatus(is_repo=True)
            
            # Get current branch
            success, stdout, stderr = await self._run_git_command(['branch', '--show-current'])
            if success:
                status.current_branch = stdout.strip()
            
            # Get remote URL
            success, stdout, stderr = await self._run_git_command(['remote', 'get-url', 'origin'])
            if success:
                status.remote_url = stdout.strip()
            
            # Check for uncommitted changes
            success, stdout, stderr = await self._run_git_command(['status', '--porcelain'])
            if success:
                status.has_uncommitted_changes = bool(stdout.strip())
                if status.has_uncommitted_changes:
                    status.uncommitted_files = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
            
            # Get ahead/behind commits
            success, stdout, stderr = await self._run_git_command(['rev-list', '--left-right', '--count', 'HEAD...@{u}'])
            if success and stdout.strip():
                parts = stdout.strip().split()
                if len(parts) == 2:
                    status.ahead_commits = int(parts[0])
                    status.behind_commits = int(parts[1])
            
            # Get last commit info
            success, stdout, stderr = await self._run_git_command(
                ['log', '-1', '--pretty=format:%H|%an|%ad', '--date=iso']
            )
            if success and stdout.strip():
                parts = stdout.strip().split('|')
                if len(parts) == 3:
                    status.last_commit = parts[0][:8]  # Short hash
                    status.last_commit_author = parts[1]
                    status.last_commit_date = parts[2]
            
            return status
        
        except Exception as e:
            self.logger.error(f"Error getting Git status: {e}")
            return GitStatus(is_repo=False)
    
    async def list_branches(self) -> List[str]:
        """
        List all branches (local and remote)
        
        Returns:
            List of branch names
        """
        try:
            if not (self.integrator_path / '.git').exists():
                return []
            
            # Fetch latest
            await self._run_git_command(['fetch'])
            
            # Get all branches
            success, stdout, stderr = await self._run_git_command(['branch', '-a'])
            if success:
                branches = []
                for line in stdout.split('\n'):
                    line = line.strip()
                    if line:
                        # Remove markers and remote prefixes
                        branch = line.replace('*', '').strip()
                        if branch.startswith('remotes/origin/'):
                            branch = branch.replace('remotes/origin/', '')
                        if branch and branch != 'HEAD' and branch not in branches:
                            branches.append(branch)
                return branches
            
            return []
        
        except Exception as e:
            self.logger.error(f"Error listing branches: {e}")
            return []