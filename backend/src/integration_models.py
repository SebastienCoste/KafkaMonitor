"""
Integration Models - Data models for multi-project Git integration
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime


class ProjectStatus(str, Enum):
    """Project status enumeration"""
    CLEAN = "clean"
    DIRTY = "dirty"
    CLONING = "cloning"
    ERROR = "error"
    SYNCING = "syncing"


class ProjectInfo(BaseModel):
    """Information about a Git project in the integration directory"""
    id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project display name")
    git_url: str = Field(..., description="Git repository URL")
    branch: str = Field(..., description="Current branch")
    namespace: Optional[str] = Field("", description="Blueprint namespace from blueprint_cnf.json")
    last_sync: Optional[str] = Field(None, description="Last synchronization timestamp (ISO format)")
    status: ProjectStatus = Field(ProjectStatus.CLEAN, description="Project status")
    path: str = Field(..., description="Relative path within integration directory")
    absolute_path: Optional[str] = Field("", description="Full absolute path to project directory")
    uncommitted_changes: int = Field(0, description="Number of uncommitted changes")
    ahead_commits: int = Field(0, description="Number of commits ahead of remote")
    behind_commits: int = Field(0, description="Number of commits behind remote")
    last_commit: Optional[str] = Field("", description="Last commit hash (short)")
    last_commit_author: Optional[str] = Field("", description="Last commit author")
    last_commit_date: Optional[str] = Field("", description="Last commit date")
    
    @validator('id')
    def validate_id(cls, v):
        """Ensure ID is safe for file system"""
        if not v or not isinstance(v, str):
            raise ValueError("ID must be a non-empty string")
        # Only allow alphanumeric, dash, underscore
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("ID must contain only alphanumeric characters, dashes, and underscores")
        return v
    
    class Config:
        use_enum_values = True


class AddProjectRequest(BaseModel):
    """Request to add a new Git project"""
    git_url: str = Field(..., description="Git repository URL")
    branch: str = Field("main", description="Branch to clone")
    credentials: Optional[Dict[str, str]] = Field(None, description="Optional Git credentials")
    
    @validator('git_url')
    def validate_git_url(cls, v):
        """Basic Git URL validation"""
        if not v or not isinstance(v, str):
            raise ValueError("Git URL must be a non-empty string")
        # Basic format check
        if not (v.startswith('https://') or v.startswith('git@')):
            raise ValueError("Git URL must start with https:// or git@")
        return v
    
    @validator('branch')
    def validate_branch(cls, v):
        """Basic branch name validation"""
        if not v:
            return "main"
        import re
        if not re.match(r'^[a-zA-Z0-9._/-]+$', v):
            raise ValueError("Invalid branch name format")
        return v


class RemoveProjectRequest(BaseModel):
    """Request to remove a project"""
    project_id: str = Field(..., description="Project ID to remove")
    force: bool = Field(False, description="Force removal even with uncommitted changes")


class IntegrationManifest(BaseModel):
    """Integration manifest file structure"""
    version: str = Field("1.0", description="Manifest version")
    projects: Dict[str, ProjectInfo] = Field(default_factory=dict, description="Map of project_id to ProjectInfo")
    created_at: Optional[str] = Field(None, description="Manifest creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    
    def add_project(self, project: ProjectInfo):
        """Add or update a project in the manifest"""
        self.projects[project.id] = project
        self.updated_at = datetime.utcnow().isoformat()
    
    def remove_project(self, project_id: str) -> bool:
        """Remove a project from the manifest"""
        if project_id in self.projects:
            del self.projects[project_id]
            self.updated_at = datetime.utcnow().isoformat()
            return True
        return False
    
    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        """Get project by ID"""
        return self.projects.get(project_id)
    
    def list_projects(self) -> List[ProjectInfo]:
        """List all projects"""
        return list(self.projects.values())


class ProjectGitStatusRequest(BaseModel):
    """Request to get Git status for a specific project"""
    project_id: str = Field(..., description="Project ID")


class SwitchProjectRequest(BaseModel):
    """Request to switch active project"""
    project_id: str = Field(..., description="Project ID to switch to")


class ProjectOperationResponse(BaseModel):
    """Response for project operations"""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    project: Optional[ProjectInfo] = Field(None, description="Project information")
    error: Optional[str] = Field(None, description="Error message if failed")