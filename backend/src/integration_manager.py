"""
Integration Manager - Manages multiple Git repositories in integration directory
"""

import json
import logging
import shutil
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.integration_models import (
    ProjectInfo,
    ProjectStatus,
    IntegrationManifest,
    AddProjectRequest
)
from src.git_service import GitService, GitStatus

logger = logging.getLogger(__name__)


class IntegrationManager:
    """Manages multiple Git repositories in the integration directory"""
    
    def __init__(self, integration_root: str = "./integration", git_config_path: Optional[str] = None):
        """
        Initialize Integration Manager
        
        Args:
            integration_root: Root directory for all Git projects
            git_config_path: Optional path to git.yaml configuration
        """
        self.integration_root = Path(integration_root)
        self.git_config_path = git_config_path
        self.manifest_file = self.integration_root / ".integration-manifest.json"
        self.git_services: Dict[str, GitService] = {}  # project_id -> GitService instance
        
        # Create integration directory if it doesn't exist
        self.integration_root.mkdir(parents=True, exist_ok=True)
        
        # Load or create manifest
        self.manifest = self._load_or_create_manifest()
        
        logger.info(f"IntegrationManager initialized with root: {self.integration_root}")
    
    def _load_or_create_manifest(self) -> IntegrationManifest:
        """
        Load existing manifest or create new one
        
        Returns:
            IntegrationManifest instance
        """
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    data = json.load(f)
                    manifest = IntegrationManifest(**data)
                    logger.info(f"Loaded integration manifest with {len(manifest.projects)} projects")
                    return manifest
            except Exception as e:
                logger.error(f"Failed to load manifest, creating new one: {e}")
        
        # Create new manifest
        manifest = IntegrationManifest(
            version="1.0",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        self._save_manifest(manifest)
        return manifest
    
    def _save_manifest(self, manifest: IntegrationManifest) -> bool:
        """
        Save manifest to file
        
        Args:
            manifest: IntegrationManifest to save
            
        Returns:
            True if saved successfully
        """
        try:
            manifest.updated_at = datetime.utcnow().isoformat()
            with open(self.manifest_file, 'w') as f:
                json.dump(manifest.dict(), f, indent=2)
            logger.info("Saved integration manifest")
            return True
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
            return False
    
    def _sanitize_folder_name(self, git_url: str, branch: str) -> str:
        """
        Generate safe folder name from Git URL and branch
        
        Format: {sanitized-repo-name}-{sanitized-branch}
        Example: my-awesome-project-feature-xyz
        
        Args:
            git_url: Git repository URL
            branch: Branch name
            
        Returns:
            Sanitized folder name
        """
        # Extract repository name from URL
        # https://github.com/user/repo.git -> repo
        # git@github.com:user/repo.git -> repo
        repo_name = git_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        # Sanitize: lowercase, replace special chars with hyphens
        repo_name = re.sub(r'[^a-zA-Z0-9]+', '-', repo_name).strip('-').lower()
        branch_clean = re.sub(r'[^a-zA-Z0-9]+', '-', branch).strip('-').lower()
        
        folder_name = f"{repo_name}-{branch_clean}"
        
        # Ensure uniqueness if folder already exists
        base_folder = folder_name
        counter = 1
        while (self.integration_root / folder_name).exists():
            # Check if it's the same project (same URL and branch)
            existing_project = self._find_project_by_path(folder_name)
            if existing_project and existing_project.git_url == git_url and existing_project.branch == branch:
                # It's the same project, reuse the folder
                return folder_name
            # Different project, add counter
            folder_name = f"{base_folder}-{counter}"
            counter += 1
        
        return folder_name
    
    def _find_project_by_path(self, path: str) -> Optional[ProjectInfo]:
        """Find project by path"""
        for project in self.manifest.projects.values():
            if project.path == path:
                return project
        return None
    
    def _get_or_create_git_service(self, project_id: str, project_path: Path) -> GitService:
        """
        Get or create GitService instance for a project
        
        Args:
            project_id: Project identifier
            project_path: Path to project directory
            
        Returns:
            GitService instance
        """
        if project_id not in self.git_services:
            self.git_services[project_id] = GitService(
                str(project_path),
                timeout=300,
                config_path=self.git_config_path
            )
            logger.info(f"Created GitService for project {project_id}")
        return self.git_services[project_id]
    
    async def discover_projects(self) -> List[ProjectInfo]:
        """
        Scan integration directory and discover existing Git projects
        
        Returns:
            List of discovered projects
        """
        discovered = []
        
        try:
            # Scan all subdirectories
            for item in self.integration_root.iterdir():
                if not item.is_dir():
                    continue
                
                # Skip manifest file and hidden directories
                if item.name.startswith('.'):
                    continue
                
                # Check if it's a Git repository
                if not (item / '.git').exists():
                    logger.info(f"Skipping {item.name}: not a Git repository")
                    continue
                
                # Check if already in manifest
                project = self._find_project_by_path(item.name)
                if project:
                    # Update status
                    await self._update_project_status(project)
                    discovered.append(project)
                else:
                    # New project, add to manifest
                    logger.info(f"Discovered new Git project: {item.name}")
                    git_service = self._get_or_create_git_service(item.name, item)
                    status = await git_service.get_status()
                    
                    if status.is_repo:
                        project_info = ProjectInfo(
                            id=item.name,
                            name=item.name,
                            git_url=status.remote_url or "",
                            branch=status.current_branch or "main",
                            path=item.name,
                            absolute_path=str(item.resolve()),  # Full absolute path
                            status=ProjectStatus.CLEAN if not status.has_uncommitted_changes else ProjectStatus.DIRTY,
                            uncommitted_changes=len(status.uncommitted_files),
                            ahead_commits=status.ahead_commits,
                            behind_commits=status.behind_commits,
                            last_commit=status.last_commit,
                            last_commit_author=status.last_commit_author,
                            last_commit_date=status.last_commit_date
                        )
                        
                        # Try to get namespace from blueprint_cnf.json
                        try:
                            blueprint_cnf = item / "blueprint_cnf.json"
                            if blueprint_cnf.exists():
                                with open(blueprint_cnf, 'r') as f:
                                    cnf_data = json.load(f)
                                    project_info.namespace = cnf_data.get('namespace', '')
                        except Exception:
                            pass
                        
                        self.manifest.add_project(project_info)
                        discovered.append(project_info)
            
            # Save updated manifest
            self._save_manifest(self.manifest)
            
            logger.info(f"Discovered {len(discovered)} projects")
            return discovered
        
        except Exception as e:
            logger.error(f"Error discovering projects: {e}")
            return []
    
    async def _update_project_status(self, project: ProjectInfo) -> ProjectInfo:
        """
        Update project status from Git
        
        Args:
            project: ProjectInfo to update
            
        Returns:
            Updated ProjectInfo
        """
        try:
            project_path = self.integration_root / project.path
            git_service = self._get_or_create_git_service(project.id, project_path)
            status = await git_service.get_status()
            
            if status.is_repo:
                project.status = ProjectStatus.CLEAN if not status.has_uncommitted_changes else ProjectStatus.DIRTY
                project.uncommitted_changes = len(status.uncommitted_files)
                project.ahead_commits = status.ahead_commits
                project.behind_commits = status.behind_commits
                project.last_commit = status.last_commit
                project.last_commit_author = status.last_commit_author
                project.last_commit_date = status.last_commit_date
                project.last_sync = datetime.utcnow().isoformat()
                
                # Update absolute_path if not set (for backward compatibility with old manifests)
                if not project.absolute_path:
                    project.absolute_path = str(project_path.resolve())
            else:
                project.status = ProjectStatus.ERROR
            
            return project
        except Exception as e:
            logger.error(f"Error updating project status: {e}")
            project.status = ProjectStatus.ERROR
            return project
    
    async def get_or_create_project(
        self,
        request: AddProjectRequest
    ) -> Tuple[Optional[ProjectInfo], Optional[str]]:
        """
        Get existing project or clone new one
        
        Args:
            request: AddProjectRequest with git_url, branch, and optional credentials
            
        Returns:
            Tuple of (ProjectInfo, error_message)
        """
        try:
            # Check if project already exists
            for project in self.manifest.projects.values():
                if project.git_url == request.git_url and project.branch == request.branch:
                    logger.info(f"Project already exists: {project.id}")
                    # Update status
                    await self._update_project_status(project)
                    return project, None
            
            # Generate folder name
            folder_name = self._sanitize_folder_name(request.git_url, request.branch)
            project_path = self.integration_root / folder_name
            
            # Create GitService for cloning
            git_service = GitService(
                str(project_path),
                timeout=600,
                config_path=self.git_config_path
            )
            
            # Clone repository
            logger.info(f"Cloning {request.git_url} branch {request.branch} to {folder_name}")
            
            # Use credentials from environment if not provided
            credentials = request.credentials
            if not credentials:
                import os
                git_username = os.environ.get('GIT_USERNAME')
                git_password = os.environ.get('GIT_PASSWORD')
                if git_username and git_password:
                    credentials = {
                        'username': git_username,
                        'password': git_password
                    }
            
            result = await git_service.clone_repository(
                request.git_url,
                request.branch,
                credentials=credentials
            )
            
            if not result.success:
                logger.error(f"Failed to clone repository: {result.error}")
                return None, result.message or result.error
            
            # Get project status
            status = await git_service.get_status()
            
            # Create project info
            project_id = folder_name
            project_info = ProjectInfo(
                id=project_id,
                name=self._extract_repo_name(request.git_url),
                git_url=request.git_url,
                branch=request.branch,
                path=folder_name,
                absolute_path=str(project_path.resolve()),  # Full absolute path
                status=ProjectStatus.CLEAN,
                last_sync=datetime.utcnow().isoformat(),
                uncommitted_changes=0,
                ahead_commits=0,
                behind_commits=0,
                last_commit=status.last_commit,
                last_commit_author=status.last_commit_author,
                last_commit_date=status.last_commit_date
            )
            
            # Try to get namespace from blueprint_cnf.json
            try:
                blueprint_cnf = project_path / "blueprint_cnf.json"
                if blueprint_cnf.exists():
                    with open(blueprint_cnf, 'r') as f:
                        cnf_data = json.load(f)
                        project_info.namespace = cnf_data.get('namespace', '')
            except Exception:
                pass
            
            # Add to manifest
            self.manifest.add_project(project_info)
            self._save_manifest(self.manifest)
            
            # Store GitService
            self.git_services[project_id] = git_service
            
            logger.info(f"Successfully added project {project_id}")
            return project_info, None
        
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            return None, str(e)
    
    def _extract_repo_name(self, git_url: str) -> str:
        """Extract repository name from Git URL"""
        repo_name = git_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return repo_name
    
    async def remove_project(self, project_id: str, force: bool = False) -> Tuple[bool, Optional[str]]:
        """
        Remove project from integration directory (hard delete)
        
        Args:
            project_id: Project ID to remove
            force: Force removal even with uncommitted changes
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            project = self.manifest.get_project(project_id)
            if not project:
                return False, f"Project not found: {project_id}"
            
            project_path = self.integration_root / project.path
            
            # Check for uncommitted changes
            if not force and project.status == ProjectStatus.DIRTY:
                return False, "Project has uncommitted changes. Use force=True to remove anyway."
            
            # Remove directory
            if project_path.exists():
                shutil.rmtree(project_path)
                logger.info(f"Removed project directory: {project_path}")
            
            # Remove from manifest
            self.manifest.remove_project(project_id)
            self._save_manifest(self.manifest)
            
            # Remove GitService
            if project_id in self.git_services:
                del self.git_services[project_id]
            
            logger.info(f"Successfully removed project {project_id}")
            return True, None
        
        except Exception as e:
            logger.error(f"Error removing project: {e}")
            return False, str(e)
    
    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """Get project by ID"""
        return self.manifest.get_project(project_id)
    
    def list_projects(self) -> List[ProjectInfo]:
        """List all projects"""
        return self.manifest.list_projects()
    
    def get_project_path(self, project_id: str) -> Optional[Path]:
        """Get full path to project directory"""
        project = self.manifest.get_project(project_id)
        if project:
            return self.integration_root / project.path
        return None
    
    def get_git_service(self, project_id: str) -> Optional[GitService]:
        """Get GitService for a project"""
        project = self.manifest.get_project(project_id)
        if not project:
            return None
        
        project_path = self.integration_root / project.path
        if not project_path.exists():
            logger.error(f"Project path does not exist: {project_path}")
            return None
        
        return self._get_or_create_git_service(project_id, project_path)
    
    async def get_project_git_status(self, project_id: str) -> Optional[GitStatus]:
        """Get Git status for a specific project"""
        git_service = self.get_git_service(project_id)
        if not git_service:
            return None
        
        try:
            status = await git_service.get_status()
            # Update project in manifest
            project = self.manifest.get_project(project_id)
            if project:
                await self._update_project_status(project)
                self._save_manifest(self.manifest)
            return status
        except Exception as e:
            logger.error(f"Error getting Git status for project {project_id}: {e}")
            return None
