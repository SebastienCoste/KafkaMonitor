"""
Blueprint-related data models for the Blueprint Creator feature.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """File type enumeration"""
    FILE = "file"
    DIRECTORY = "directory"


class FileInfo(BaseModel):
    """Information about a file or directory"""
    name: str
    path: str
    type: FileType
    size: Optional[int] = None
    modified: Optional[datetime] = None
    children: Optional[List['FileInfo']] = None
    
    class Config:
        use_enum_values = True


class BlueprintConfig(BaseModel):
    """Blueprint configuration structure based on blueprint_cnf.json"""
    namespace: str
    version: str = "git_version"
    owner: str
    description: str
    schemas: List[Dict[str, Any]] = []
    transformSpecs: List[str] = []
    searchExperience: Dict[str, Any] = Field(default_factory=lambda: {"configs": [], "templates": []})


class BuildStatus(str, Enum):
    """Build status enumeration"""
    IDLE = "idle"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"


class BuildResult(BaseModel):
    """Result of a blueprint build operation"""
    success: bool
    output: str = ""
    generated_files: List[str] = []
    execution_time: float = 0.0
    status: BuildStatus = BuildStatus.IDLE
    error_message: Optional[str] = None


class DeploymentAction(str, Enum):
    """Deployment action type"""
    VALIDATE = "validate"
    ACTIVATE = "activate"


class DeploymentResult(BaseModel):
    """Result of a blueprint deployment operation"""
    success: bool
    status_code: int
    response: str
    environment: str
    action: DeploymentAction
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True


class BlueprintSettings(BaseModel):
    """Blueprint creator settings"""
    root_path: Optional[str] = None
    auto_refresh: bool = True
    auto_refresh_interval: int = 30  # seconds
    selected_environment: str = "dev"


class FileOperationRequest(BaseModel):
    """Request for file operations"""
    path: str
    content: Optional[str] = None
    new_path: Optional[str] = None
    overwrite: Optional[bool] = False


class DirectoryListingRequest(BaseModel):
    """Request for directory listing"""
    path: str
    include_hidden: bool = False


class BuildRequest(BaseModel):
    """Request to build blueprints"""
    root_path: str
    script_name: str = "buildBlueprint.sh"


class DeploymentRequest(BaseModel):
    """Request to deploy blueprint"""
    tgz_file: str
    environment: str
    action: DeploymentAction
    
    class Config:
        use_enum_values = True


class WebSocketMessage(BaseModel):
    """WebSocket message structure for real-time updates"""
    type: str
    data: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)


class FileChangeEvent(BaseModel):
    """File system change event"""
    event_type: str  # created, modified, deleted, moved
    file_path: str
    is_directory: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class EnvironmentConfig(BaseModel):
    """Blueprint server configuration for environments"""
    base_url: str
    validate_path: str = "/api/v1/blueprint/validate"
    activate_path: str = "/api/v1/blueprint/activate"
    auth_header_name: str = "Authorization"
    auth_header_value: str


class FileTemplate(BaseModel):
    """Template for creating new files"""
    name: str
    extension: str
    content: str
    description: str


# File extension to content type mapping
FILE_CONTENT_TYPES = {
    '.json': 'application/json',
    '.jslt': 'application/json',
    '.proto': 'text/plain',
    '.yaml': 'application/x-yaml',
    '.yml': 'application/x-yaml',
    '.txt': 'text/plain',
    '.md': 'text/markdown'
}

# Default file templates
DEFAULT_TEMPLATES = {
    'blueprint_cnf.json': {
        "namespace": "",
        "version": "git_version", 
        "owner": "",
        "description": "",
        "schemas": [],
        "transformSpecs": [],
        "searchExperience": {
            "configs": [],
            "templates": []
        }
    },
    'global.json': {
        "environments": {
            "dev": {},
            "test": {},
            "int": {},
            "load": {},
            "prod": {}
        }
    },
    'transform.jslt': '{\n  "realId": ._system.id,\n  * - content, access, assets: .\n}',
    'Message.proto': 'syntax = "proto3";\n\npackage your.package.name;\n\nmessage YourMessage {\n  string id = 1;\n}'
}

# Allowed file extensions for security
ALLOWED_EXTENSIONS = {'.json', '.jslt', '.proto', '.yaml', '.yml', '.txt', '.md'}

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024