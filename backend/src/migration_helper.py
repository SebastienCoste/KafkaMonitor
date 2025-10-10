"""
Migration Helper - Handles migration from single-project to multi-project setup
"""

import logging
import shutil
import json
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from src.integration_models import ProjectInfo, ProjectStatus
from src.git_service import GitService

logger = logging.getLogger(__name__)


class IntegrationMigration:
    """Handles migration from single integrator/ folder to multi-project integration/ folder"""
    
    def __init__(self, old_integrator_path: str = "./integrator", new_integration_path: str = "./integration"):
        """
        Initialize migration helper
        
        Args:
            old_integrator_path: Path to old integrator directory
            new_integration_path: Path to new integration directory
        """
        self.old_path = Path(old_integrator_path)
        self.new_path = Path(new_integration_path)
        self.migrated_folder_name = "migrated-project-main"
    
    def detect_legacy_setup(self) -> bool:
        """
        Check if old integrator folder exists with Git repository
        
        Returns:
            True if legacy setup detected
        """
        if not self.old_path.exists():
            logger.info("No legacy integrator folder found")
            return False
        
        # Check if it's a Git repository
        git_dir = self.old_path / '.git'
        if not git_dir.exists():
            logger.info("Legacy integrator folder exists but is not a Git repository")
            return False
        
        # Check if it has any content
        items = list(self.old_path.iterdir())
        if len(items) == 0:
            logger.info("Legacy integrator folder is empty")
            return False
        
        logger.info("Legacy setup detected: integrator/ folder with Git repository")
        return True
    
    async def migrate_existing_setup(self) -> Tuple[bool, Optional[ProjectInfo], Optional[str]]:
        """
        Migrate existing integrator folder to new integration structure
        
        Returns:
            Tuple of (success, ProjectInfo, error_message)
        """
        try:
            if not self.detect_legacy_setup():
                return False, None, "No legacy setup to migrate"
            
            logger.info("Starting migration from integrator/ to integration/")
            
            # Create new integration directory
            self.new_path.mkdir(parents=True, exist_ok=True)
            
            # Destination for migrated project
            migrated_path = self.new_path / self.migrated_folder_name
            
            # Check if destination already exists
            if migrated_path.exists():
                logger.warning(f"Migration destination already exists: {migrated_path}")
                return False, None, f"Migration destination already exists: {self.migrated_folder_name}"
            
            # Get Git info from old repository before moving
            old_git_service = GitService(str(self.old_path), timeout=60)
            git_status = await old_git_service.get_status()
            
            if not git_status.is_repo:
                logger.error("Old integrator is not a valid Git repository")
                return False, None, "Old integrator is not a valid Git repository"
            
            # Extract project information
            git_url = git_status.remote_url or "unknown"
            branch = git_status.current_branch or "main"
            
            # Try to get namespace from blueprint_cnf.json
            namespace = ""
            try:
                blueprint_cnf = self.old_path / "blueprint_cnf.json"
                if blueprint_cnf.exists():
                    with open(blueprint_cnf, 'r') as f:
                        cnf_data = json.load(f)
                        namespace = cnf_data.get('namespace', '')
            except Exception as e:
                logger.warning(f"Could not read namespace from blueprint_cnf.json: {e}")
            
            # Move directory
            logger.info(f"Moving {self.old_path} to {migrated_path}")
            shutil.move(str(self.old_path), str(migrated_path))
            
            # Create ProjectInfo
            project_info = ProjectInfo(
                id=self.migrated_folder_name,
                name=self._extract_repo_name(git_url),
                git_url=git_url,
                branch=branch,
                namespace=namespace,
                path=self.migrated_folder_name,
                absolute_path=str(migrated_path.resolve()),  # Full absolute path
                status=ProjectStatus.CLEAN if not git_status.has_uncommitted_changes else ProjectStatus.DIRTY,
                last_sync=datetime.utcnow().isoformat(),
                uncommitted_changes=len(git_status.uncommitted_files),
                ahead_commits=git_status.ahead_commits,
                behind_commits=git_status.behind_commits,
                last_commit=git_status.last_commit,
                last_commit_author=git_status.last_commit_author,
                last_commit_date=git_status.last_commit_date
            )
            
            logger.info(f"Successfully migrated project: {project_info.name}")
            logger.info(f"  - URL: {git_url}")
            logger.info(f"  - Branch: {branch}")
            logger.info(f"  - Namespace: {namespace}")
            logger.info(f"  - New path: {migrated_path}")
            
            return True, project_info, None
        
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False, None, str(e)
    
    def _extract_repo_name(self, git_url: str) -> str:
        """Extract repository name from Git URL"""
        if not git_url or git_url == "unknown":
            return "migrated-project"
        
        repo_name = git_url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return repo_name
    
    async def create_integration_structure(self) -> bool:
        """
        Create new integration directory structure
        
        Returns:
            True if created successfully
        """
        try:
            self.new_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created integration directory: {self.new_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create integration structure: {e}")
            return False
    
    def cleanup_old_structure(self) -> bool:
        """
        Clean up old integrator directory (only if empty)
        
        Returns:
            True if cleaned up successfully
        """
        try:
            if self.old_path.exists():
                # Only remove if empty
                items = list(self.old_path.iterdir())
                if len(items) == 0:
                    self.old_path.rmdir()
                    logger.info(f"Removed empty integrator directory: {self.old_path}")
                    return True
                else:
                    logger.warning(f"Integrator directory not empty, skipping cleanup")
                    return False
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup old structure: {e}")
            return False
