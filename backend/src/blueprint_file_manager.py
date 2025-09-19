"""
Blueprint File Manager - Handles file system operations for blueprint management.
"""

import os
import json
import asyncio
import aiofiles
from pathlib import Path  
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .blueprint_models import (
    FileInfo, FileType, FileChangeEvent, FileOperationRequest,
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE, DEFAULT_TEMPLATES
)


class BlueprintFileSystemEventHandler(FileSystemEventHandler):
    """File system event handler for blueprint directory monitoring"""
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def on_any_event(self, event: FileSystemEvent):
        if not event.is_directory and not event.src_path.startswith('.'):
            change_event = FileChangeEvent(
                event_type=event.event_type,
                file_path=event.src_path,
                is_directory=event.is_directory
            )
            asyncio.create_task(self.callback(change_event))


class BlueprintFileManager:
    """Manages file operations for blueprint projects"""
    
    def __init__(self, root_path: Optional[str] = None):
        self.root_path = root_path
        self.observer = None
        self.change_callbacks = []
    
    def set_root_path(self, root_path: str):
        """Set the root path for blueprint operations"""
        self.root_path = os.path.abspath(root_path)
        if not os.path.exists(self.root_path):
            raise FileNotFoundError(f"Root path does not exist: {self.root_path}")
    
    def validate_path(self, relative_path: str) -> str:
        """Validate and resolve a relative path within the root directory"""
        if not self.root_path:
            raise ValueError("Root path not set")
        
        # Remove leading slash and resolve path
        relative_path = relative_path.lstrip('/')
        full_path = os.path.abspath(os.path.join(self.root_path, relative_path))
        
        # Security check: ensure path is within root directory
        if not full_path.startswith(self.root_path):
            raise ValueError(f"Path outside root directory: {relative_path}")
        
        return full_path
    
    async def get_file_tree(self, relative_path: str = "") -> List[FileInfo]:
        """Get file tree structure starting from relative_path"""
        if not self.root_path:
            return []
        
        try:
            start_path = self.validate_path(relative_path)
            if not os.path.exists(start_path):
                return []
            
            return await self._build_file_tree(start_path, relative_path)
        except Exception as e:
            print(f"Error getting file tree: {e}")
            return []
    
    async def _build_file_tree(self, full_path: str, relative_path: str) -> List[FileInfo]:
        """Recursively build file tree structure"""
        items = []
        
        try:
            for item_name in sorted(os.listdir(full_path)):
                # Skip hidden files and common ignore patterns
                if item_name.startswith('.') or item_name in ['__pycache__', 'node_modules']:
                    continue
                
                item_full_path = os.path.join(full_path, item_name)
                item_relative_path = os.path.join(relative_path, item_name) if relative_path else item_name
                
                stat = os.stat(item_full_path)
                
                if os.path.isdir(item_full_path):
                    # Directory
                    children = await self._build_file_tree(item_full_path, item_relative_path)
                    file_info = FileInfo(
                        name=item_name,
                        path=item_relative_path,
                        type=FileType.DIRECTORY,
                        size=None,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        children=children
                    )
                else:
                    # File
                    file_info = FileInfo(
                        name=item_name,
                        path=item_relative_path,
                        type=FileType.FILE,
                        size=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime)
                    )
                
                items.append(file_info)
        except PermissionError:
            pass  # Skip directories we can't read
        
        return items
    
    async def read_file(self, relative_path: str) -> str:
        """Read file content"""
        full_path = self.validate_path(relative_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {relative_path}")
        
        if not os.path.isfile(full_path):
            raise ValueError(f"Path is not a file: {relative_path}")
        
        # Check file size
        if os.path.getsize(full_path) > MAX_FILE_SIZE:
            raise ValueError(f"File too large: {relative_path}")
        
        async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def write_file(self, relative_path: str, content: str, create_dirs: bool = True):
        """Write content to file"""
        full_path = self.validate_path(relative_path)
        
        # Check file extension
        ext = os.path.splitext(relative_path)[1].lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension not allowed: {ext}")
        
        # Create directories if needed
        if create_dirs:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Validate content size
        if len(content.encode('utf-8')) > MAX_FILE_SIZE:
            raise ValueError("Content too large")
        
        # Atomic write using temporary file
        temp_path = full_path + ".tmp"
        try:
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            # Move temp file to final location
            os.rename(temp_path, full_path)
        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    async def create_file(self, relative_path: str, template_name: Optional[str] = None):
        """Create a new file with optional template content"""
        full_path = self.validate_path(relative_path)
        
        if os.path.exists(full_path):
            raise FileExistsError(f"File already exists: {relative_path}")
        
        # Get template content
        content = ""
        if template_name and template_name in DEFAULT_TEMPLATES:
            template_content = DEFAULT_TEMPLATES[template_name]
            if isinstance(template_content, dict):
                content = json.dumps(template_content, indent=2)
            else:
                content = template_content
        
        await self.write_file(relative_path, content)
    
    async def delete_file(self, relative_path: str):
        """Delete a file or directory"""
        full_path = self.validate_path(relative_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {relative_path}")
        
        if os.path.isdir(full_path):
            # Remove directory and all contents
            import shutil
            shutil.rmtree(full_path)
        else:
            # Remove file
            os.unlink(full_path)
    
    async def create_directory(self, relative_path: str):
        """Create a directory"""
        full_path = self.validate_path(relative_path)
        os.makedirs(full_path, exist_ok=True)
    
    async def copy_file(self, src_relative_path: str, dst_relative_path: str):
        """Copy a file"""
        src_path = self.validate_path(src_relative_path)
        dst_path = self.validate_path(dst_relative_path)
        
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source file not found: {src_relative_path}")
        
        if os.path.exists(dst_path):
            raise FileExistsError(f"Destination file already exists: {dst_relative_path}")
        
        # Create destination directory if needed
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        # Copy file
        import shutil
        shutil.copy2(src_path, dst_path)
    
    async def move_file(self, src_relative_path: str, dst_relative_path: str):
        """Move/rename a file"""
        src_path = self.validate_path(src_relative_path)
        dst_path = self.validate_path(dst_relative_path)
        
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"Source file not found: {src_relative_path}")
        
        if os.path.exists(dst_path):
            raise FileExistsError(f"Destination file already exists: {dst_relative_path}")
        
        # Create destination directory if needed
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        # Move file
        os.rename(src_path, dst_path)
    
    def start_watching(self, callback):
        """Start watching for file system changes"""
        if not self.root_path or self.observer:
            return
        
        self.change_callbacks.append(callback)
        
        event_handler = BlueprintFileSystemEventHandler(self._handle_file_change)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.root_path, recursive=True)
        self.observer.start()
    
    def stop_watching(self):
        """Stop watching for file system changes"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.change_callbacks.clear()
    
    async def _handle_file_change(self, event: FileChangeEvent):
        """Handle file system change events"""
        for callback in self.change_callbacks:
            try:
                await callback(event)
            except Exception as e:
                print(f"Error in file change callback: {e}")
    
    def get_available_templates(self) -> Dict[str, Any]:
        """Get list of available file templates"""
        templates = {}
        for name, content in DEFAULT_TEMPLATES.items():
            templates[name] = {
                'name': name,
                'extension': os.path.splitext(name)[1],
                'description': f"Template for {name}",
                'content': content if isinstance(content, str) else json.dumps(content, indent=2)
            }
        return templates
    
    async def validate_blueprint_config(self, relative_path: str = "blueprint_cnf.json") -> Dict[str, Any]:
        """Validate blueprint configuration file"""
        try:
            content = await self.read_file(relative_path)
            config_data = json.loads(content)
            
            # Basic validation
            required_fields = ['namespace', 'version', 'owner']
            errors = []
            warnings = []
            
            for field in required_fields:
                if field not in config_data or not config_data[field]:
                    errors.append(f"Missing required field: {field}")
            
            # Validate schemas structure
            if 'schemas' in config_data:
                if not isinstance(config_data['schemas'], list):
                    errors.append("'schemas' must be an array")
                else:
                    for i, schema in enumerate(config_data['schemas']):
                        if not isinstance(schema, dict):
                            errors.append(f"Schema at index {i} must be an object")
            
            # Check for referenced files
            if 'transformSpecs' in config_data:
                for spec in config_data['transformSpecs']:
                    spec_path = os.path.join('src/transformSpecs', spec)
                    try:
                        await self.read_file(spec_path)
                    except FileNotFoundError:
                        warnings.append(f"Transform spec file not found: {spec_path}")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'config': config_data
            }
        
        except FileNotFoundError:
            return {
                'valid': False,
                'errors': ['Blueprint configuration file not found'],
                'warnings': [],
                'config': None
            }
        except json.JSONDecodeError as e:
            return {
                'valid': False, 
                'errors': [f'Invalid JSON: {str(e)}'],
                'warnings': [],
                'config': None
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}'],
                'warnings': [],
                'config': None
            }