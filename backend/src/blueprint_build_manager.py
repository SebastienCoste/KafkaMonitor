"""
Blueprint Build Manager - Handles blueprint building and deployment operations.
"""

import os
import asyncio
import time
import json
import httpx
from pathlib import Path
from typing import List, Optional, Dict, Any, AsyncIterator
from fastapi import WebSocket

from .blueprint_models import (
    BuildResult, BuildStatus, DeploymentResult, DeploymentAction,
    EnvironmentConfig, WebSocketMessage
)


class BlueprintBuildManager:
    """Manages blueprint build and deployment operations"""
    
    def __init__(self):
        self.current_build_process = None
        self.build_status = BuildStatus.IDLE
        self.last_build_result = None
    
    async def execute_build(self, root_path: str, script_name: str = "buildBlueprint.sh", 
                          websocket: Optional[WebSocket] = None) -> BuildResult:
        """Execute blueprint build script with real-time output streaming"""
        
        if self.build_status == BuildStatus.BUILDING:
            return BuildResult(
                success=False,
                output="Build already in progress",
                status=BuildStatus.BUILDING,
                error_message="Another build is currently running"
            )
        
        self.build_status = BuildStatus.BUILDING
        start_time = time.time()
        output_lines = []
        
        try:
            # Validate build script exists
            script_path = os.path.join(root_path, script_name)
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Build script not found: {script_name}")
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Send build start message
            if websocket:
                await self._send_websocket_message(
                    websocket, "build_started", 
                    {"script": script_name, "root_path": root_path}
                )
            
            # Execute build script
            self.current_build_process = await asyncio.create_subprocess_exec(
                'bash', script_path,
                cwd=root_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=dict(os.environ, PWD=root_path)
            )
            
            # Stream output in real-time
            async for line in self._read_process_output(self.current_build_process.stdout):
                output_lines.append(line)
                
                # Send to WebSocket if connected
                if websocket:
                    await self._send_websocket_message(
                        websocket, "build_output", {"content": line}
                    )
            
            # Wait for process completion
            return_code = await self.current_build_process.wait()
            execution_time = time.time() - start_time
            
            # Find generated files
            generated_files = self._find_generated_files(root_path)
            
            # Determine success
            success = return_code == 0
            status = BuildStatus.SUCCESS if success else BuildStatus.FAILED
            self.build_status = status
            
            # Create result
            result = BuildResult(
                success=success,
                output="\n".join(output_lines),
                generated_files=generated_files,
                execution_time=execution_time,
                status=status,
                error_message=None if success else f"Build failed with exit code {return_code}"
            )
            
            # Send completion message
            if websocket:
                await self._send_websocket_message(
                    websocket, "build_complete", {
                        "success": success,
                        "execution_time": execution_time,
                        "generated_files": generated_files
                    }
                )
            
            self.last_build_result = result
            return result
            
        except FileNotFoundError as e:
            error_msg = str(e)
            self.build_status = BuildStatus.FAILED
            
            result = BuildResult(
                success=False,
                output="\n".join(output_lines) + f"\nError: {error_msg}",
                status=BuildStatus.FAILED,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
            
            if websocket:
                await self._send_websocket_message(
                    websocket, "build_error", {"error": error_msg}
                )
            
            self.last_build_result = result
            return result
            
        except Exception as e:
            error_msg = f"Build execution error: {str(e)}"
            self.build_status = BuildStatus.FAILED
            
            result = BuildResult(
                success=False,
                output="\n".join(output_lines) + f"\nError: {error_msg}",
                status=BuildStatus.FAILED,
                error_message=error_msg,
                execution_time=time.time() - start_time
            )
            
            if websocket:
                await self._send_websocket_message(
                    websocket, "build_error", {"error": error_msg}
                )
            
            self.last_build_result = result
            return result
        
        finally:
            self.current_build_process = None
            if self.build_status == BuildStatus.BUILDING:
                self.build_status = BuildStatus.IDLE
    
    async def _read_process_output(self, stdout) -> AsyncIterator[str]:
        """Read process output line by line"""
        try:
            while True:
                line = await stdout.readline()
                if not line:
                    break
                
                decoded_line = line.decode('utf-8').rstrip()
                if decoded_line:  # Only yield non-empty lines
                    yield decoded_line
        except Exception as e:
            yield f"Error reading output: {str(e)}"
    
    def _find_generated_files(self, root_path: str) -> List[str]:
        """Find generated .tgz files in the output directory"""
        generated_files = []
        
        # Look for .tgz files in common output directories
        output_dirs = ['out', 'output', 'build', 'dist', '.']
        
        for dir_name in output_dirs:
            output_dir = os.path.join(root_path, dir_name)
            if os.path.exists(output_dir) and os.path.isdir(output_dir):
                try:
                    for filename in os.listdir(output_dir):
                        if filename.endswith('.tgz') or filename.endswith('.tar.gz'):
                            file_path = os.path.join(dir_name, filename)
                            generated_files.append(file_path)
                except PermissionError:
                    continue
        
        return sorted(generated_files)
    
    async def _send_websocket_message(self, websocket: WebSocket, message_type: str, data: Dict[str, Any]):
        """Send message via WebSocket"""
        try:
            message = WebSocketMessage(type=message_type, data=data)
            await websocket.send_text(message.json())
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")
    
    def get_build_status(self) -> Dict[str, Any]:
        """Get current build status"""
        return {
            "status": self.build_status.value,
            "is_building": self.build_status == BuildStatus.BUILDING,
            "last_result": self.last_build_result.dict() if self.last_build_result else None
        }
    
    async def cancel_build(self) -> bool:
        """Cancel current build process"""
        if self.current_build_process and self.build_status == BuildStatus.BUILDING:
            try:
                self.current_build_process.terminate()
                await asyncio.sleep(2)  # Give it time to terminate gracefully
                
                if self.current_build_process.returncode is None:
                    self.current_build_process.kill()  # Force kill if needed
                
                self.build_status = BuildStatus.IDLE
                self.current_build_process = None
                return True
            except Exception as e:
                print(f"Error canceling build: {e}")
                return False
        
        return False
    
    async def deploy_blueprint(self, root_path: str, tgz_file: str, environment: str, 
                             action: DeploymentAction, env_config: EnvironmentConfig, 
                             namespace: str = None) -> DeploymentResult:
        """Deploy blueprint to blueprint server"""
        
        try:
            # Validate .tgz file exists
            if not tgz_file.startswith('/'):
                # Relative path - resolve from root_path
                full_tgz_path = os.path.join(root_path, tgz_file)
            else:
                full_tgz_path = tgz_file
            
            if not os.path.exists(full_tgz_path):
                raise FileNotFoundError(f"Blueprint file not found: {tgz_file}")
            
            # Determine API endpoint with namespace substitution
            if action == DeploymentAction.VALIDATE:
                endpoint_path = env_config.validate_path
            else:
                endpoint_path = env_config.activate_path
            
            # Replace namespace placeholder if provided
            if namespace and '{namespace}' in endpoint_path:
                endpoint_path = endpoint_path.replace('{namespace}', namespace)
            
            endpoint = env_config.base_url + endpoint_path
            
            # Prepare headers
            headers = {
                env_config.auth_header_name: env_config.auth_header_value,
                'Content-Type': 'application/octet-stream'
            }
            
            # Read blueprint file
            with open(full_tgz_path, 'rb') as f:
                blueprint_data = f.read()
            
            # Make HTTP request
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    endpoint,
                    content=blueprint_data,
                    headers=headers
                )
                
                return DeploymentResult(
                    success=response.status_code == 200,
                    status_code=response.status_code,
                    response=response.text,
                    environment=environment,
                    action=action,
                    error_message=None if response.status_code == 200 else f"HTTP {response.status_code}: {response.text}"
                )
        
        except FileNotFoundError as e:
            return DeploymentResult(
                success=False,
                status_code=404,
                response="",
                environment=environment,
                action=action,
                error_message=str(e)
            )
        
        except httpx.TimeoutException:
            return DeploymentResult(
                success=False,
                status_code=408,
                response="",
                environment=environment,
                action=action,
                error_message="Request timeout"
            )
        
        except Exception as e:
            return DeploymentResult(
                success=False,
                status_code=500,
                response="",
                environment=environment,
                action=action,
                error_message=f"Deployment error: {str(e)}"
            )
    
    async def list_output_files(self, root_path: str) -> List[Dict[str, Any]]:
        """List all generated output files with metadata"""
        output_files = []
        
        # Look for files in output directories
        output_dirs = ['out', 'output', 'build', 'dist']
        
        for dir_name in output_dirs:
            output_dir = os.path.join(root_path, dir_name)
            if os.path.exists(output_dir) and os.path.isdir(output_dir):
                try:
                    for filename in os.listdir(output_dir):
                        if filename.endswith(('.tgz', '.tar.gz', '.zip')):
                            file_path = os.path.join(output_dir, filename)
                            stat = os.stat(file_path)
                            
                            output_files.append({
                                'name': filename,
                                'path': os.path.join(dir_name, filename),
                                'size': stat.st_size,
                                'modified': stat.st_mtime,
                                'directory': dir_name
                            })
                except PermissionError:
                    continue
        
        # Sort by modification time (newest first)
        output_files.sort(key=lambda x: x['modified'], reverse=True)
        return output_files
    
    def cleanup_old_builds(self, root_path: str, keep_count: int = 5):
        """Clean up old build artifacts, keeping only the most recent ones"""
        try:
            output_dirs = ['out', 'output', 'build', 'dist']
            
            for dir_name in output_dirs:
                output_dir = os.path.join(root_path, dir_name)
                if os.path.exists(output_dir) and os.path.isdir(output_dir):
                    # Get all .tgz files with their modification times
                    files_with_times = []
                    
                    for filename in os.listdir(output_dir):
                        if filename.endswith(('.tgz', '.tar.gz')):
                            file_path = os.path.join(output_dir, filename)
                            stat = os.stat(file_path)
                            files_with_times.append((file_path, stat.st_mtime))
                    
                    # Sort by modification time (oldest first)
                    files_with_times.sort(key=lambda x: x[1])
                    
                    # Remove old files, keeping only the most recent ones
                    files_to_remove = files_with_times[:-keep_count] if len(files_with_times) > keep_count else []
                    
                    for file_path, _ in files_to_remove:
                        try:
                            os.unlink(file_path)
                        except Exception as e:
                            print(f"Error removing old build file {file_path}: {e}")
        
        except Exception as e:
            print(f"Error cleaning up old builds: {e}")