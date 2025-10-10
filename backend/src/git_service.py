"""
Git Service - Handles all Git operations for Blueprint Creator
"""

import subprocess
import asyncio
import os
import re
import logging
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Custom exceptions for better error handling
class GitError(Exception):
    """Base Git operation error"""
    pass


class GitAuthenticationError(GitError):
    """Git authentication failed"""
    pass


class GitNetworkError(GitError):
    """Network-related Git operation failed"""
    pass


class GitRepositoryError(GitError):
    """Repository-specific error"""
    pass


class GitCommandError(GitError):
    """Git command execution error"""
    pass


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
    """Service for handling Git operations with enhanced security and configuration"""
    
    def __init__(self, integrator_path: str, timeout: int = 300, config_path: Optional[str] = None):
        """
        Initialize Git service
        
        Args:
            integrator_path: Path to integrator directory
            timeout: Default timeout for Git operations in seconds
            config_path: Optional path to git.yaml configuration file
        """
        self.integrator_path = Path(integrator_path)
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from YAML if provided
        self.config = self._load_config(config_path) if config_path else {}
        
        # Get timeouts from config or use defaults
        self.timeouts = self.config.get('timeouts', {
            'clone': 600,
            'fetch': 120,
            'pull': 300,
            'push': 300,
            'default': 300
        })
        
        # Get allowed hosts from config
        self.allowed_hosts = self.config.get('allowed_hosts', [])
        
        # Security settings
        self.security_enabled = self.config.get('security', {}).get('whitelist_hosts', True)
        
        # Create integrator directory if it doesn't exist
        self.integrator_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git config
        self._initialize_git_config()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load Git configuration from YAML file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('git', {})
        except Exception as e:
            self.logger.warning(f"Could not load Git configuration from {config_path}: {e}")
            return {}
    
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
    
    def _validate_path_security(self, path: Path) -> bool:
        """
        Validate that path is within integrator directory (prevent directory traversal)
        
        Args:
            path: Path to validate
            
        Returns:
            True if path is safe, False otherwise
        """
        try:
            # Resolve to absolute path and check if it's within integrator
            resolved = path.resolve()
            integrator_resolved = self.integrator_path.resolve()
            return str(resolved).startswith(str(integrator_resolved))
        except Exception:
            return False
    
    def validate_git_url(self, url: str, allowed_hosts: Optional[List[str]] = None) -> bool:
        """
        Validate Git URL format and security with whitelist support
        
        Args:
            url: Git repository URL
            allowed_hosts: Optional list of allowed hosts (e.g., ['github.com', 'gitlab.com'])
            
        Returns:
            True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        # Prevent command injection attempts
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']
        if any(char in url for char in dangerous_chars):
            self.logger.warning(f"Rejected URL with dangerous characters: {url}")
            return False
        
        # Check for valid URL patterns
        # Support HTTPS and SSH formats with strict validation
        https_pattern = r'^https://[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*(/[a-zA-Z0-9._-]+)+(\.git)?$'
        ssh_pattern = r'^git@[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*:[a-zA-Z0-9/_.-]+(\.git)?$'
        
        is_valid_format = re.match(https_pattern, url) or re.match(ssh_pattern, url)
        
        if not is_valid_format:
            self.logger.warning(f"Invalid Git URL format: {url}")
            return False
        
        # Additional security checks
        parsed = urlparse(url)
        
        # Prevent local file system access
        if parsed.scheme in ['file', ''] or url.startswith('/') or url.startswith('.'):
            self.logger.warning(f"Rejected local file system URL: {url}")
            return False
        
        # Whitelist check if provided
        if allowed_hosts:
            if url.startswith('https://'):
                host = parsed.netloc.split('@')[-1]  # Remove any user info
                if not any(host.endswith(allowed) for allowed in allowed_hosts):
                    self.logger.warning(f"URL host not in whitelist: {host}")
                    return False
            elif url.startswith('git@'):
                host = url.split('@')[1].split(':')[0]
                if not any(host.endswith(allowed) for allowed in allowed_hosts):
                    self.logger.warning(f"URL host not in whitelist: {host}")
                    return False
        
        return True
    
    def sanitize_branch_name(self, branch: str) -> str:
        """
        Sanitize branch name to prevent command injection with strict validation
        
        Args:
            branch: Branch name
            
        Returns:
            Sanitized branch name
            
        Raises:
            GitCommandError: If branch name is invalid
        """
        if not branch or not isinstance(branch, str):
            raise GitCommandError("Branch name must be a non-empty string")
        
        # Whitelist-based validation: only allow alphanumeric, dash, underscore, slash, dot
        if not re.match(r'^[a-zA-Z0-9._/-]+$', branch):
            raise GitCommandError(f"Invalid branch name format: {branch}")
        
        # Prevent command injection sequences
        dangerous_sequences = ['..', '--', '|||', '&&', ';;']
        if any(seq in branch for seq in dangerous_sequences):
            raise GitCommandError(f"Branch name contains dangerous sequence: {branch}")
        
        # Additional safety: use shlex.quote for shell safety
        return branch
    
    async def _run_git_command(
        self,
        args: List[str],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout_override: Optional[int] = None
    ) -> Tuple[bool, str, str]:
        """
        Execute Git command safely with async subprocess and proper error handling
        
        Args:
            args: Git command arguments
            cwd: Working directory
            env: Environment variables
            timeout_override: Optional timeout override for specific operations
            
        Returns:
            Tuple of (success, stdout, stderr)
            
        Raises:
            GitCommandError: If command execution fails critically
        """
        if cwd is None:
            cwd = self.integrator_path
        
        # Validate working directory is within integrator path
        if not self._validate_path_security(Path(cwd)):
            raise GitCommandError("Working directory outside allowed path")
        
        try:
            # Prepare command - args are NOT shell-escaped here as we use exec, not shell
            cmd = ['git'] + args
            
            # Log command (sanitize for security - don't log credentials)
            safe_cmd = ' '.join(cmd)
            if env and ('GIT_USERNAME' in env or 'GIT_PASSWORD' in env):
                safe_cmd = safe_cmd.replace(env.get('GIT_PASSWORD', ''), '***')
            self.logger.info(f"Executing Git command: {safe_cmd} in {cwd}")
            
            # Create process with environment
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            # Use override timeout if provided, otherwise use default
            timeout = timeout_override if timeout_override is not None else self.timeout
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                self.logger.error(f"Git command timed out after {timeout} seconds")
                process.kill()
                await process.wait()
                raise GitCommandError(f"Git operation timed out after {timeout} seconds")
            except asyncio.CancelledError:
                self.logger.warning("Git command cancelled")
                process.kill()
                await process.wait()
                raise
            
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            success = process.returncode == 0
            
            # Provide specific error types based on stderr content
            if not success:
                # Sanitize error messages to avoid leaking sensitive info
                sanitized_error = self._sanitize_error_message(stderr_str)
                self.logger.error(f"Git command failed with return code {process.returncode}: {sanitized_error}")
                
                # Classify error type
                if 'authentication' in stderr_str.lower() or 'permission denied' in stderr_str.lower():
                    raise GitAuthenticationError(f"Authentication failed: {sanitized_error}")
                elif 'network' in stderr_str.lower() or 'could not resolve' in stderr_str.lower():
                    raise GitNetworkError(f"Network error: {sanitized_error}")
                elif 'not found' in stderr_str.lower() or 'does not exist' in stderr_str.lower():
                    raise GitRepositoryError(f"Repository error: {sanitized_error}")
            else:
                self.logger.info(f"Git command succeeded")
            
            return success, stdout_str, stderr_str
            
        except (GitAuthenticationError, GitNetworkError, GitRepositoryError, GitCommandError):
            # Re-raise specific Git errors
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error executing Git command: {e}")
            raise GitCommandError(f"Git command failed: {str(e)}")
    
    def _sanitize_error_message(self, error: str) -> str:
        """
        Sanitize error messages to prevent credential leakage
        
        Args:
            error: Raw error message
            
        Returns:
            Sanitized error message
        """
        # Remove any URLs with credentials
        sanitized = re.sub(r'https://[^@]+@', 'https://***@', error)
        # Remove password patterns
        sanitized = re.sub(r'password[=:]\s*\S+', 'password=***', sanitized, flags=re.IGNORECASE)
        # Remove token patterns
        sanitized = re.sub(r'token[=:]\s*\S+', 'token=***', sanitized, flags=re.IGNORECASE)
        return sanitized
    
    async def _initialize_submodules(self, env: Optional[Dict[str, str]] = None) -> str:
        """
        Initialize Git submodules according to configuration
        
        Args:
            env: Environment variables for Git operations
            
        Returns:
            String describing submodule initialization result
        """
        try:
            # Check if submodules are enabled in config
            submodule_config = self.config.get('submodules', {})
            if not submodule_config.get('enabled', True):
                self.logger.info("Submodule initialization disabled in config")
                return ""
            
            init_sequence = submodule_config.get('init_sequence', [])
            if not init_sequence:
                self.logger.info("No submodule init sequence configured")
                return ""
            
            continue_on_error = submodule_config.get('continue_on_error', True)
            log_operations = submodule_config.get('log_operations', True)
            timeout = submodule_config.get('timeout', 600)
            
            if log_operations:
                self.logger.info(f"Initializing submodules with {len(init_sequence)} step(s)")
            
            results = []
            env_copy = (env or os.environ).copy()
            
            for step_idx, step in enumerate(init_sequence, 1):
                step_path = step.get('path', '.')
                commands = step.get('commands', [])
                
                if not commands:
                    continue
                
                # Resolve step path relative to integrator_path (project root)
                work_dir = self.integrator_path / step_path
                
                if log_operations:
                    self.logger.info(f"Submodule step {step_idx}/{len(init_sequence)}:")
                    self.logger.info(f"  Config path: '{step_path}'")
                    self.logger.info(f"  Full path: {work_dir}")
                    self.logger.info(f"  Commands: {len(commands)}")
                
                if not work_dir.exists():
                    if log_operations:
                        self.logger.warning(f"  ⚠️ Path does not exist: {work_dir}")
                    if continue_on_error:
                        continue
                    else:
                        return f" (submodule init failed: path not found: {step_path})"
                
                for cmd_idx, command in enumerate(commands, 1):
                    try:
                        # Parse command safely
                        cmd_parts = shlex.split(command)
                        
                        if log_operations:
                            self.logger.info(f"  Command {cmd_idx}/{len(commands)}: {command}")
                        
                        # Run command with timeout
                        process = await asyncio.create_subprocess_exec(
                            *cmd_parts,
                            cwd=str(work_dir),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                            env=env_copy
                        )
                        
                        try:
                            stdout, stderr = await asyncio.wait_for(
                                process.communicate(),
                                timeout=timeout
                            )
                            
                            if process.returncode != 0:
                                error_msg = stderr.decode('utf-8', errors='ignore')
                                if log_operations:
                                    self.logger.warning(f"  Command failed (exit code {process.returncode}): {error_msg[:200]}")
                                
                                if not continue_on_error:
                                    return f" (submodule init failed: {command})"
                            else:
                                if log_operations:
                                    self.logger.info(f"  Command succeeded")
                        
                        except asyncio.TimeoutError:
                            process.kill()
                            if log_operations:
                                self.logger.error(f"  Command timed out after {timeout}s")
                            
                            if not continue_on_error:
                                return f" (submodule init timeout: {command})"
                    
                    except Exception as e:
                        if log_operations:
                            self.logger.error(f"  Error executing command: {e}")
                        
                        if not continue_on_error:
                            return f" (submodule init error: {str(e)})"
                
                results.append(f"step {step_idx}")
            
            if results:
                return f" and initialized submodules ({len(results)} steps)"
            else:
                return ""
        
        except Exception as e:
            self.logger.error(f"Unexpected error initializing submodules: {e}")
            return " (submodule init error)"
    
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
            # Validate URL with whitelist if security is enabled
            allowed = self.allowed_hosts if self.security_enabled else None
            if not self.validate_git_url(git_url, allowed_hosts=allowed):
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.CLONE,
                    message="Invalid or unauthorized Git URL",
                    error="URL validation failed. Please use an allowed Git host."
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
            
            # Prepare environment with credentials using Git credential helper
            # This is more secure than embedding credentials in URLs
            env = os.environ.copy()
            
            # Configure Git to use credentials from environment
            if credentials:
                if 'username' in credentials and 'password' in credentials:
                    # Set up Git credential helper with environment variables
                    env['GIT_USERNAME'] = credentials['username']
                    env['GIT_PASSWORD'] = credentials['password']
                    # Use Git askpass helper for credentials
                    env['GIT_ASKPASS'] = 'echo'
                    env['GIT_PASSWORD'] = credentials['password']
                elif 'token' in credentials:
                    # For token-based auth
                    env['GIT_USERNAME'] = credentials.get('username', 'oauth2')
                    env['GIT_PASSWORD'] = credentials['token']
                    env['GIT_ASKPASS'] = 'echo'
            
            # Clone repository without credentials in URL (more secure)
            # Use longer timeout for clone operations
            args = ['clone', '--branch', branch, '--single-branch', git_url, '.']
            try:
                success, stdout, stderr = await self._run_git_command(
                    args,
                    cwd=self.integrator_path,
                    env=env,
                    timeout_override=600  # 10 minutes for clone
                )
            except GitAuthenticationError as e:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.CLONE,
                    message="Authentication failed. Please check your credentials.",
                    error=str(e)
                )
            except GitNetworkError as e:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.CLONE,
                    message="Network error. Please check your connection and repository URL.",
                    error=str(e)
                )
            except GitCommandError as e:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.CLONE,
                    message="Clone operation failed.",
                    error=str(e)
                )
            
            if success:
                # Initialize submodules if configured
                submodule_result = await self._initialize_submodules(env)
                
                return GitOperationResult(
                    success=True,
                    operation=GitOperationType.CLONE,
                    message=f"Successfully cloned repository on branch '{branch}'{submodule_result}",
                    output=stdout,
                    details={'branch': branch, 'url': git_url, 'submodules_initialized': submodule_result != ''}
                )
            else:
                return GitOperationResult(
                    success=False,
                    operation=GitOperationType.CLONE,
                    message="Failed to clone repository. Please check the URL and credentials.",
                    error=stderr,
                    output=stdout
                )
        
        except (GitAuthenticationError, GitNetworkError, GitRepositoryError, GitCommandError) as e:
            # Already handled above, but catch here for safety
            return GitOperationResult(
                success=False,
                operation=GitOperationType.CLONE,
                message=str(e),
                error=str(e)
            )
        except Exception as e:
            self.logger.error(f"Unexpected error cloning repository: {e}")
            return GitOperationResult(
                success=False,
                operation=GitOperationType.CLONE,
                message="An unexpected error occurred during clone operation",
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