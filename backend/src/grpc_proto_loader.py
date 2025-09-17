"""
gRPC Proto File Loader

Dynamically loads and compiles user-provided proto files for gRPC services.
Proto files are NOT committed to the repository and must be provided by users.
"""
import os
import sys
import logging
import importlib
import importlib.util
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import grpc
from grpc_tools import protoc
import grpc_tools
import yaml

logger = logging.getLogger(__name__)

class GrpcProtoLoader:
    """Manages loading and compilation of user-provided proto files"""
    
    def __init__(self, proto_dir: str):
        self.proto_dir = Path(proto_dir)
        # The actual proto root should be the parent directory to handle imports correctly
        self.proto_root = self.proto_dir.parent
        self.compiled_modules: Dict[str, Any] = {}
        self.service_stubs: Dict[str, Any] = {}
        self.temp_dir = None
        
        # Create proto directory if it doesn't exist
        self.proto_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔧 Initialized GrpcProtoLoader with proto directory: {self.proto_dir}")
        logger.info(f"🔧 Proto root for imports: {self.proto_root}")
    
    def validate_proto_files(self) -> Dict[str, bool]:
        """Validate that required proto files are present"""
        logger.info("🔍 Validating proto files...")
        
        validation_results = {
            'ingress_server': False,
            'asset_storage': False,
            'all_present': False
        }
        
        # Check for required proto files in the new structure
        ingress_proto = self.proto_dir / "ingress_server" / "ingress_server.proto"
        asset_proto = self.proto_dir / "asset_storage" / "asset_storage.proto"
        
        validation_results['ingress_server'] = ingress_proto.exists()
        validation_results['asset_storage'] = asset_proto.exists()
        validation_results['all_present'] = validation_results['ingress_server'] and validation_results['asset_storage']
        
        logger.info(f"📋 Proto validation results: {validation_results}")
        
        if not validation_results['all_present']:
            missing_files = []
            if not validation_results['ingress_server']:
                missing_files.append("ingress_server/ingress_server.proto")
            if not validation_results['asset_storage']:
                missing_files.append("asset_storage/asset_storage.proto")
            
            logger.warning(f"⚠️  Missing proto files: {missing_files}")
            logger.info("💡 Proto files are now located in the config/proto/grpc/ directory")
        
        return validation_results
    
    def compile_proto_files(self) -> bool:
        """Compile proto files to Python modules"""
        logger.info("🔨 Starting proto file compilation...")
        
        try:
            # Create temporary directory for compiled modules
            self.temp_dir = tempfile.mkdtemp(prefix="grpc_protos_")
            logger.info(f"📁 Created temp directory: {self.temp_dir}")
            
            # Add temp directory to Python path
            if self.temp_dir not in sys.path:
                sys.path.insert(0, self.temp_dir)
            
            # Find all proto files
            proto_files = list(self.proto_dir.rglob("*.proto"))
            logger.info(f"📄 Found {len(proto_files)} proto files")
            
            if not proto_files:
                logger.error("❌ No proto files found")
                return False
            
            # Compile each proto file
            for proto_file in proto_files:
                self._compile_single_proto(proto_file)
            
            # Create __init__.py files for Python package structure
            self._create_init_files()
            
            # Rename 'grpc' directory to 'proto_gen' to avoid conflicts with system grpc
            self._rename_grpc_to_proto_gen()
            
            logger.info("✅ Proto compilation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"💥 Proto compilation failed: {str(e)}")
            logger.error(f"🔴 Error type: {type(e).__name__}")
            return False
    
    def _compile_single_proto(self, proto_file: Path):
        """Compile a single proto file"""
        logger.debug(f"🔨 Compiling proto file: {proto_file}")
        
        # Calculate relative path from proto_root (not proto_dir)
        rel_path = proto_file.relative_to(self.proto_root)
        
        # Get the grpc_tools proto path for well-known types
        grpc_tools_proto_path = Path(grpc_tools.__file__).parent / "_proto"
        
        # Create a flattened module name to avoid conflicts
        # grpc/ingress_server/ingress_server.proto -> grpc_ingress_server_ingress_server
        module_name = str(rel_path).replace('/', '_').replace('.proto', '')
        
        # Prepare protoc arguments - use proto_root as the proto_path and include grpc_tools path
        args = [
            "grpc_tools.protoc",
            f"--proto_path={self.proto_root}",
            f"--proto_path={grpc_tools_proto_path}",
            f"--python_out={self.temp_dir}",
            f"--grpc_python_out={self.temp_dir}",
            str(rel_path)
        ]
        
        logger.debug(f"🛠️  Protoc command: {' '.join(args)}")
        logger.debug(f"🏷️  Module name will be: {module_name}")
        
        # Run protoc
        result = protoc.main(args)
        if result != 0:
            raise RuntimeError(f"protoc failed with exit code {result} for {proto_file}")
        
        logger.debug(f"✅ Successfully compiled: {proto_file}")
    
    def _create_init_files(self):
        """Create __init__.py files for Python package structure"""
        logger.debug("📦 Creating __init__.py files for package structure")
        
        # Create __init__.py files for all directories in the temp directory
        for root, dirs, files in os.walk(self.temp_dir):
            for dir_name in dirs:
                init_file = Path(root) / dir_name / "__init__.py"
                if not init_file.exists():
                    init_file.touch()
                    logger.debug(f"📄 Created: {init_file}")
        
        # Also create root __init__.py files
        grpc_init = Path(self.temp_dir) / "grpc" / "__init__.py"
        if not grpc_init.exists():
            grpc_init.parent.mkdir(parents=True, exist_ok=True)
            grpc_init.touch()
            logger.debug(f"📄 Created: {grpc_init}")
        
        logger.debug("✅ Package structure created")
    
    def load_service_modules(self) -> bool:
        """Load compiled service modules"""
        logger.info("📦 Loading service modules...")
        
        try:
            # Load IngressServer - use the actual compiled module paths
            ingress_pb2 = self._import_module("grpc.ingress_server.ingress_server_pb2")
            ingress_grpc = self._import_module("grpc.ingress_server.ingress_server_pb2_grpc")
            
            if ingress_pb2 and ingress_grpc:
                self.compiled_modules['ingress_server'] = {
                    'pb2': ingress_pb2,
                    'grpc': ingress_grpc
                }
                logger.info("✅ IngressServer modules loaded")
            else:
                logger.error("❌ Failed to load IngressServer modules")
                # Let's try to debug what's available
                self._debug_temp_directory()
                return False
            
            # Load AssetStorageService - use the actual compiled module paths
            asset_pb2 = self._import_module("grpc.asset_storage.asset_storage_pb2")
            asset_grpc = self._import_module("grpc.asset_storage.asset_storage_pb2_grpc")
            
            if asset_pb2 and asset_grpc:
                self.compiled_modules['asset_storage'] = {
                    'pb2': asset_pb2,
                    'grpc': asset_grpc
                }
                logger.info("✅ AssetStorageService modules loaded")
            else:
                logger.error("❌ Failed to load AssetStorageService modules")
                return False
            
            logger.info("🎉 All service modules loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"💥 Failed to load service modules: {str(e)}")
            logger.error(f"🔴 Error type: {type(e).__name__}")
            return False
    
    def _import_module(self, module_name: str) -> Optional[Any]:
        """Import a compiled module with enhanced import handling"""
        try:
            logger.debug(f"📦 Importing module: {module_name}")
            
            # If temp_dir is available, try loading from file path first to avoid conflicts
            if self.temp_dir:
                # Convert module name to file path
                file_path = Path(self.temp_dir) / f"{module_name.replace('.', '/')}.py"
                if file_path.exists():
                    logger.debug(f"📁 Loading from file: {file_path}")
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        
                        # Temporarily modify sys.modules to handle nested imports
                        old_modules = {}
                        temp_modules = {}
                        
                        # Save current modules that might conflict
                        conflicting_names = ['grpc.common', 'grpc.asset_storage', 'grpc.ingress_server']
                        for name in conflicting_names:
                            if name in sys.modules:
                                old_modules[name] = sys.modules[name]
                        
                        try:
                            # Load all our proto modules first
                            proto_modules = [
                                ('grpc.common.base_pb2', 'grpc/common/base_pb2.py'),
                                ('grpc.common.types_pb2', 'grpc/common/types_pb2.py'),
                                ('grpc.asset_storage.asset_storage_pb2', 'grpc/asset_storage/asset_storage_pb2.py'),
                                ('grpc.ingress_server.ingress_server_pb2', 'grpc/ingress_server/ingress_server_pb2.py'),
                                ('grpc.asset_storage.asset_storage_pb2_grpc', 'grpc/asset_storage/asset_storage_pb2_grpc.py'),
                                ('grpc.ingress_server.ingress_server_pb2_grpc', 'grpc/ingress_server/ingress_server_pb2_grpc.py'),
                            ]
                            
                            # Create parent modules
                            if 'grpc' not in sys.modules:
                                grpc_mod = importlib.util.module_from_spec(
                                    importlib.util.spec_from_loader('grpc', loader=None)
                                )
                                sys.modules['grpc'] = grpc_mod
                                temp_modules['grpc'] = grpc_mod
                            
                            if 'grpc.common' not in sys.modules:
                                common_mod = importlib.util.module_from_spec(
                                    importlib.util.spec_from_loader('grpc.common', loader=None)
                                )
                                sys.modules['grpc.common'] = common_mod
                                temp_modules['grpc.common'] = common_mod
                            
                            if 'grpc.ingress_server' not in sys.modules:
                                ingress_mod = importlib.util.module_from_spec(
                                    importlib.util.spec_from_loader('grpc.ingress_server', loader=None)
                                )
                                sys.modules['grpc.ingress_server'] = ingress_mod
                                temp_modules['grpc.ingress_server'] = ingress_mod
                            
                            if 'grpc.asset_storage' not in sys.modules:
                                asset_mod = importlib.util.module_from_spec(
                                    importlib.util.spec_from_loader('grpc.asset_storage', loader=None)
                                )
                                sys.modules['grpc.asset_storage'] = asset_mod
                                temp_modules['grpc.asset_storage'] = asset_mod
                            
                            # Load the specific modules
                            for mod_name, mod_path in proto_modules:
                                mod_file_path = Path(self.temp_dir) / mod_path
                                if mod_file_path.exists():
                                    mod_spec = importlib.util.spec_from_file_location(mod_name, mod_file_path)
                                    if mod_spec and mod_spec.loader:
                                        mod = importlib.util.module_from_spec(mod_spec)
                                        sys.modules[mod_name] = mod
                                        temp_modules[mod_name] = mod
                                        mod_spec.loader.exec_module(mod)
                            
                            # Now execute our target module
                            spec.loader.exec_module(module)
                            logger.debug(f"✅ Successfully loaded from file: {module_name}")
                            return module
                            
                        except Exception as e:
                            logger.error(f"❌ Error loading module {module_name}: {str(e)}")
                            # Restore original modules
                            for name, mod in old_modules.items():
                                sys.modules[name] = mod
                            # Remove temporary modules
                            for name in temp_modules:
                                if name in sys.modules:
                                    del sys.modules[name]
                            return None
            
            # Fall back to direct import
            try:
                module = importlib.import_module(module_name)
                logger.debug(f"✅ Successfully imported: {module_name}")
                return module
            except ImportError:
                pass
            
            logger.error(f"❌ Failed to import {module_name}: Module not found")
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to import {module_name}: {str(e)}")
            return None
    
    def _debug_temp_directory(self):
        """Debug what's in the temp directory"""
        logger.info(f"🔍 Debugging temp directory: {self.temp_dir}")
        if self.temp_dir and Path(self.temp_dir).exists():
            for root, dirs, files in os.walk(self.temp_dir):
                level = root.replace(self.temp_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                logger.info(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    logger.info(f"{subindent}{file}")
        
        # Also check what's in sys.path
        logger.info(f"🔍 Python path includes temp dir: {self.temp_dir in sys.path}")
        
        # Try to list what's importable
        try:
            import pkgutil
            logger.info("🔍 Available packages:")
            for importer, modname, ispkg in pkgutil.iter_modules():
                if 'grpc' in modname.lower():
                    logger.info(f"  {modname} (package: {ispkg})")
        except Exception as e:
            logger.error(f"Failed to list packages: {e}")
    
    def create_service_stub(self, service_name: str, channel: grpc.Channel) -> Optional[Any]:
        """Create a gRPC service stub"""
        logger.debug(f"🔗 Creating service stub for: {service_name}")
        
        try:
            if service_name == 'ingress_server':
                if 'ingress_server' not in self.compiled_modules:
                    logger.error("❌ IngressServer module not loaded")
                    return None
                
                grpc_module = self.compiled_modules['ingress_server']['grpc']
                stub = grpc_module.IngressServerStub(channel)
                self.service_stubs[service_name] = stub
                logger.info("✅ IngressServer stub created")
                return stub
                
            elif service_name == 'asset_storage':
                if 'asset_storage' not in self.compiled_modules:
                    logger.error("❌ AssetStorageService module not loaded")
                    return None
                
                grpc_module = self.compiled_modules['asset_storage']['grpc']
                stub = grpc_module.AssetStorageServiceStub(channel)
                self.service_stubs[service_name] = stub
                logger.info("✅ AssetStorageService stub created")
                return stub
                
            else:
                logger.error(f"❌ Unknown service: {service_name}")
                return None
                
        except Exception as e:
            logger.error(f"💥 Failed to create stub for {service_name}: {str(e)}")
            return None
    
    def get_message_class(self, service_name: str, message_name: str) -> Optional[Any]:
        """Get a protobuf message class"""
        logger.debug(f"📝 Getting message class: {service_name}.{message_name}")
        
        try:
            if service_name not in self.compiled_modules:
                logger.error(f"❌ Service module not loaded: {service_name}")
                logger.debug(f"Available modules: {list(self.compiled_modules.keys())}")
                return None
            
            pb2_module = self.compiled_modules[service_name]['pb2']
            
            # Try different variations of the message name
            possible_names = [
                message_name,
                f"{service_name}_{message_name}",
                f"{service_name.title()}{message_name}",
            ]
            
            message_class = None
            for name in possible_names:
                message_class = getattr(pb2_module, name, None)
                if message_class:
                    logger.debug(f"✅ Found message class with name: {name}")
                    break
            
            if message_class is None:
                logger.error(f"❌ Message class not found: {message_name}")
                logger.debug(f"Available attributes in {service_name} module: {dir(pb2_module)}")
                return None
            
            logger.debug(f"✅ Message class found: {message_name}")
            return message_class
            
        except Exception as e:
            logger.error(f"💥 Failed to get message class {message_name}: {str(e)}")
            return None
    
    def list_available_services(self) -> Dict[str, List[str]]:
        """List available services and their methods"""
        services = {}
        
        for service_name, modules in self.compiled_modules.items():
            try:
                grpc_module = modules['grpc']
                service_methods = []
                
                # Get service class name
                if service_name == 'ingress_server':
                    service_class_name = 'IngressServerStub'
                elif service_name == 'asset_storage':
                    service_class_name = 'AssetStorageServiceStub'
                else:
                    continue
                
                # Get service class and list methods
                service_class = getattr(grpc_module, service_class_name, None)
                if service_class:
                    # This is a simplified method listing - in practice you'd need to inspect the proto
                    if service_name == 'ingress_server':
                        service_methods = ['UpsertContent', 'BatchCreateAssets', 'BatchAddDownloadCounts', 'BatchAddRatings']
                    elif service_name == 'asset_storage':
                        service_methods = ['BatchGetSignedUrls', 'BatchUpdateStatuses']
                
                services[service_name] = service_methods
                
            except Exception as e:
                logger.error(f"Error listing methods for {service_name}: {str(e)}")
                services[service_name] = []
        
        return services
    
    def cleanup(self):
        """Cleanup temporary files and modules"""
        logger.info("🧹 Cleaning up proto loader...")
        
        # Remove temp directory from path
        if self.temp_dir and self.temp_dir in sys.path:
            sys.path.remove(self.temp_dir)
        
        # Clear compiled modules
        self.compiled_modules.clear()
        self.service_stubs.clear()
        
        # Note: We don't delete the temp directory here as it might still be needed
        # The OS will clean it up eventually
        
        logger.info("✅ Proto loader cleanup completed")
    
    def get_proto_status(self) -> Dict[str, Any]:
        """Get current status of proto loading"""
        validation = self.validate_proto_files()
        
        return {
            'proto_files_present': validation,
            'compiled_modules': list(self.compiled_modules.keys()),
            'service_stubs': list(self.service_stubs.keys()),
            'temp_directory': self.temp_dir,
            'proto_directory': str(self.proto_dir)
        }