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
    
    def __init__(self, proto_root_dir: str):
        """Initialize the gRPC proto loader with the entire proto root directory"""
        self.proto_root = Path(proto_root_dir)
        self.proto_dir = self.proto_root / "grpc"  # gRPC proto files subdirectory
        self.temp_dir = None
        self.compiled_modules: Dict[str, Any] = {}
        self.service_stubs: Dict[str, Any] = {}
        self.service_definitions: Dict[str, Dict] = {}  # Store parsed service definitions
        
        # Ensure proto root exists
        self.proto_root.mkdir(parents=True, exist_ok=True)
        self.proto_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔧 Initialized GrpcProtoLoader with proto directory: {self.proto_dir}")
        logger.info(f"🔧 Proto root for imports: {self.proto_root}")
    
    def validate_proto_files(self, environment_config: dict = None) -> Dict[str, bool]:
        """Validate that required proto files are present based on environment configuration"""
        logger.info("🔍 Validating proto files...")
        
        validation_results = {
            'ingress_server': False,
            'asset_storage': False,
            'all_present': False
        }
        
        # Use service_proto paths from environment configuration if available
        if environment_config and 'grpc_services' in environment_config:
            grpc_services = environment_config['grpc_services']
            
            # Check ingress_server
            if 'ingress_server' in grpc_services and 'service_proto' in grpc_services['ingress_server']:
                ingress_proto_path = self.proto_root / grpc_services['ingress_server']['service_proto']
                validation_results['ingress_server'] = ingress_proto_path.exists()
                logger.debug(f"🔍 Checking ingress_server proto: {ingress_proto_path} -> {validation_results['ingress_server']}")
            
            # Check asset_storage
            if 'asset_storage' in grpc_services and 'service_proto' in grpc_services['asset_storage']:
                asset_proto_path = self.proto_root / grpc_services['asset_storage']['service_proto']
                validation_results['asset_storage'] = asset_proto_path.exists()
                logger.debug(f"🔍 Checking asset_storage proto: {asset_proto_path} -> {validation_results['asset_storage']}")
        else:
            # Fallback to default paths
            logger.info("🔄 Using default proto paths for validation")
            ingress_proto = self.proto_root / "eadp/cadie/ingressserver/v1/ingress_service.proto"
            asset_proto = self.proto_root / "eadp/cadie/shared/storageinterface/v1/storage_service_admin.proto"
            
            validation_results['ingress_server'] = ingress_proto.exists()
            validation_results['asset_storage'] = asset_proto.exists()
            logger.debug(f"🔍 Default paths - ingress: {ingress_proto.exists()}, asset: {asset_proto.exists()}")
        
        validation_results['all_present'] = validation_results['ingress_server'] and validation_results['asset_storage']
        
        logger.info(f"📋 Proto validation results: {validation_results}")
        
        if not validation_results['all_present']:
            missing_services = []
            if not validation_results['ingress_server']:
                missing_services.append("ingress_server")
            if not validation_results['asset_storage']:
                missing_services.append("asset_storage")
            
            logger.warning(f"⚠️  Missing proto files for services: {missing_services}")
            logger.info("💡 Proto files should be configured in environment service_proto paths")
        
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
            
            # Find all proto files in the entire proto root directory (not just grpc subdir)
            proto_files = list(self.proto_root.rglob("*.proto"))
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
            
            # Create missing utilities module for gRPC version checking
            self._create_utilities_module()
            
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
    
    def _rename_grpc_to_proto_gen(self):
        """Move all generated files to proto_gen directory to avoid conflicts with system grpc package"""
        logger.debug("🔄 Moving generated files to proto_gen directory...")
        
        temp_path = Path(self.temp_dir)
        proto_gen_dir = temp_path / "proto_gen"
        
        # Create proto_gen directory
        proto_gen_dir.mkdir(exist_ok=True)
        
        # Create __init__.py for proto_gen
        (proto_gen_dir / "__init__.py").touch()
        
        # Move all generated directories and files to proto_gen
        for item in temp_path.iterdir():
            if item.name == 'proto_gen':
                continue  # Skip the proto_gen directory itself
                
            target_path = proto_gen_dir / item.name
            
            try:
                if target_path.exists():
                    # If target exists, remove it first
                    import shutil
                    if target_path.is_dir():
                        shutil.rmtree(target_path)
                    else:
                        target_path.unlink()
                
                # Move the item
                item.rename(target_path)
                logger.debug(f"📁 Moved {item.name} to proto_gen/{item.name}")
                
            except Exception as e:
                logger.warning(f"⚠️  Failed to move {item.name}: {e}")
        
        # Update all Python import statements in the generated files
        for py_file in proto_gen_dir.rglob("*.py"):
            if py_file.name != "__init__.py":
                self._update_imports_in_file(py_file)
        
        logger.debug("✅ Directory restructuring completed")
    
    def list_available_services(self) -> Dict[str, List[str]]:
        """List all available services and their methods from parsed service definitions"""
        services = {}
        
        for service_name, service_data in self.service_definitions.items():
            service_methods = []
            
            # Extract methods from all services in the definition
            for svc_name, svc_def in service_data.items():
                if 'methods' in svc_def:
                    for method in svc_def['methods']:
                        service_methods.append(method['name'])
            
            services[service_name] = service_methods
        
        logger.debug(f"📋 Available services: {services}")
        return services
    
    def get_message_class(self, service_name: str, message_name: str):
        """Get a message class from the compiled modules"""
        logger.debug(f"📝 Getting message class: {service_name}.{message_name}")
        
        if service_name not in self.compiled_modules:
            logger.error(f"❌ Service not found: {service_name}")
            return None
        
        # Try to find the message in pb2 module first (direct access)
        pb2_module = self.compiled_modules[service_name].get('pb2')
        if pb2_module and hasattr(pb2_module, message_name):
            logger.debug(f"✅ Found message class directly: {message_name}")
            return getattr(pb2_module, message_name)
        
        # If not found directly, search in imported sub-modules
        if pb2_module:
            # Look for imported modules that might contain the message
            for attr_name in dir(pb2_module):
                if not attr_name.startswith('_') and 'pb2' in attr_name:
                    imported_module = getattr(pb2_module, attr_name)
                    
                    # Check if this module has the message class we need
                    if hasattr(imported_module, message_name):
                        logger.debug(f"✅ Found message class in imported module {attr_name}: {message_name}")
                        return getattr(imported_module, message_name)
                    
                    # For ingress server, try to find message classes by pattern
                    if service_name == 'ingress_server':
                        # Convert method name to module pattern
                        method_base = message_name.replace('Request', '').replace('Response', '')
                        if method_base.lower() in attr_name.lower():
                            # This might be the right module, check all its attributes
                            for msg_attr in dir(imported_module):
                                if msg_attr == message_name:
                                    logger.debug(f"✅ Found message class by pattern matching: {message_name}")
                                    return getattr(imported_module, msg_attr)
        
        logger.error(f"❌ Message class not found: {message_name}")
        return None
    
    def _create_utilities_module(self):
        """Create missing _utilities.py module for gRPC version checking"""
        logger.debug("🔧 Creating _utilities.py module...")
        
        proto_gen_dir = Path(self.temp_dir) / "proto_gen"
        if proto_gen_dir.exists():
            utilities_file = proto_gen_dir / "_utilities.py"
            
            utilities_code = '''# Generated utilities for gRPC version checking
def first_version_is_lower(version1, version2):
    """Compare two version strings to check if version1 < version2"""
    try:
        from packaging import version
        return version.parse(version1) < version.parse(version2)
    except ImportError:
        # Fallback to simple string comparison if packaging is not available
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Pad with zeros to make same length
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        return v1_parts < v2_parts
'''
            
            with open(utilities_file, 'w') as f:
                f.write(utilities_code)
            
            logger.debug(f"📝 Created utilities module: {utilities_file}")
        
        logger.debug("✅ Utilities module created")
    
    def _update_imports_in_file(self, py_file: Path):
        """Update import statements in generated Python files"""
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Replace imports to add proto_gen prefix for all relevant imports
            updated_content = content
            
            # Replace imports from 'grpc.' to 'proto_gen.'
            updated_content = updated_content.replace('from grpc.', 'from proto_gen.')
            updated_content = updated_content.replace('import grpc.', 'import proto_gen.')
            
            # Replace imports from 'eadp.' to 'proto_gen.eadp.'
            updated_content = updated_content.replace('from eadp.', 'from proto_gen.eadp.')
            updated_content = updated_content.replace('import eadp.', 'import proto_gen.eadp.')
            
            # Replace imports from 'common.' to 'proto_gen.common.'
            updated_content = updated_content.replace('from common.', 'from proto_gen.common.')
            updated_content = updated_content.replace('import common.', 'import proto_gen.common.')
            
            # Replace imports from 'events.' to 'proto_gen.events.'
            updated_content = updated_content.replace('from events.', 'from proto_gen.events.')
            updated_content = updated_content.replace('import events.', 'import proto_gen.events.')
            
            if content != updated_content:
                with open(py_file, 'w') as f:
                    f.write(updated_content)
                logger.debug(f"📝 Updated imports in {py_file.name}")
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to update imports in {py_file}: {e}")
        
        logger.debug("✅ Imports updated")
    
    def load_service_modules(self, environment_config: dict = None) -> bool:
        """Load gRPC service modules based on environment configuration"""
        try:
            # Clear existing modules
            self.compiled_modules.clear()
            self.service_definitions.clear()
            
            if not self.temp_dir or not Path(self.temp_dir).exists():
                logger.error("❌ Proto files not compiled yet - call compile_proto_files() first")
                return False
            
            # Load service definitions from environment config if provided
            if environment_config and 'grpc_services' in environment_config:
                return self._load_services_from_config(environment_config['grpc_services'])
            else:
                # Fallback to default service loading
                return self._load_default_services()
                
        except Exception as e:
            logger.error(f"💥 Failed to load service modules: {str(e)}")
            logger.error(f"🔴 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"🔴 Traceback: {traceback.format_exc()}")
            return False
    
    def _load_services_from_config(self, grpc_services_config: dict) -> bool:
        """Load services based on configuration with service_proto paths"""
        try:
            for service_name, service_config in grpc_services_config.items():
                if 'service_proto' not in service_config:
                    logger.warning(f"⚠️  No service_proto defined for {service_name}, skipping")
                    continue
                
                service_proto_path = service_config['service_proto']
                logger.info(f"📦 Loading {service_name} from {service_proto_path}")
                
                # Parse the service definition to extract methods
                service_def = self._parse_service_definition(service_proto_path)
                if service_def:
                    self.service_definitions[service_name] = service_def
                
                # Load the compiled modules
                if not self._load_service_modules_for_service(service_name, service_proto_path):
                    logger.error(f"❌ Failed to load modules for {service_name}")
                    return False
            
            logger.info(f"✅ Successfully loaded {len(self.compiled_modules)} services")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load services from config: {str(e)}")
            return False
    
    def _load_default_services(self) -> bool:
        """Fallback method for loading services without configuration"""
        logger.info("🔄 Loading services with default paths...")
        
        # Try to load from standard paths
        default_services = {
            'ingress_server': 'eadp/cadie/ingressserver/v1/ingress_service.proto',
            'asset_storage': 'eadp/cadie/shared/storageinterface/v1/storage_service_admin.proto'
        }
        
        success = True
        for service_name, proto_path in default_services.items():
            logger.info(f"📦 Loading {service_name} from default path {proto_path}")
            
            # Parse the service definition
            service_def = self._parse_service_definition(proto_path)
            if service_def:
                self.service_definitions[service_name] = service_def
                
            # Load the compiled modules
            if not self._load_service_modules_for_service(service_name, proto_path):
                logger.warning(f"⚠️  Failed to load modules for {service_name} from default path")
                success = False
        
        return success
    
    
    def _parse_service_definition(self, service_proto_path: str) -> Optional[Dict]:
        """Parse a proto file to extract service definition and methods"""
        try:
            proto_file_path = self.proto_root / service_proto_path
            if not proto_file_path.exists():
                logger.warning(f"⚠️  Proto file not found: {proto_file_path}")
                return None
            
            logger.debug(f"📖 Parsing service definition from: {proto_file_path}")
            
            # Read and parse the proto file
            with open(proto_file_path, 'r') as f:
                proto_content = f.read()
            
            # Extract service definitions using simple regex
            import re
            service_pattern = r'service\s+(\w+)\s*\{([^}]+)\}'
            method_pattern = r'rpc\s+(\w+)\s*\(([^)]+)\)\s*returns\s*\(([^)]+)\)'
            
            services = {}
            for service_match in re.finditer(service_pattern, proto_content, re.DOTALL):
                service_name = service_match.group(1)
                service_body = service_match.group(2)
                
                methods = []
                for method_match in re.finditer(method_pattern, service_body):
                    method_name = method_match.group(1)
                    request_type = method_match.group(2).strip()
                    response_type = method_match.group(3).strip()
                    
                    methods.append({
                        'name': method_name,
                        'request_type': request_type,
                        'response_type': response_type
                    })
                
                services[service_name] = {
                    'methods': methods,
                    'proto_path': service_proto_path
                }
            
            logger.debug(f"✅ Parsed {len(services)} services from {proto_file_path}")
            return services
            
        except Exception as e:
            logger.error(f"❌ Failed to parse service definition from {service_proto_path}: {str(e)}")
            return None
    
    def _load_service_modules_for_service(self, service_name: str, service_proto_path: str) -> bool:
        """Load compiled modules for a specific service"""
        try:
            logger.debug(f"📦 Loading modules for service: {service_name}")
            
            # Convert proto path to module path
            # e.g., eadp/cadie/ingressserver/v1/ingress_service.proto -> proto_gen.eadp.cadie.ingressserver.v1.ingress_service_pb2
            proto_path_parts = Path(service_proto_path).with_suffix('').parts
            module_base = 'proto_gen.' + '.'.join(proto_path_parts)
            
            pb2_module_name = f"{module_base}_pb2"
            grpc_module_name = f"{module_base}_pb2_grpc"
            
            logger.debug(f"🔍 Attempting to load: {pb2_module_name} and {grpc_module_name}")
            
            # Try to import the modules
            pb2_module = self._import_module(pb2_module_name)
            grpc_module = self._import_module(grpc_module_name)
            
            if pb2_module and grpc_module:
                self.compiled_modules[service_name] = {
                    'pb2': pb2_module,
                    'grpc': grpc_module
                }
                logger.info(f"✅ Successfully loaded modules for {service_name}")
                return True
            else:
                logger.error(f"❌ Failed to load one or both modules for {service_name}")
                # Try fallback paths for backward compatibility
                return self._try_fallback_module_loading(service_name)
                
        except Exception as e:
            logger.error(f"❌ Error loading modules for {service_name}: {str(e)}")
            return False
    
    def _try_fallback_module_loading(self, service_name: str) -> bool:
        """Try fallback module loading with known service module mappings"""
        logger.debug(f"🔄 Attempting fallback loading for {service_name}")
        
        # Known module mappings for the new structure
        service_module_mappings = {
            'ingress_server': {
                'pb2': 'proto_gen.eadp.cadie.ingressserver.v1.ingress_service_pb2',
                'grpc': 'proto_gen.eadp.cadie.ingressserver.v1.ingress_service_pb2_grpc'
            },
            'asset_storage': {
                'pb2': 'proto_gen.eadp.cadie.shared.storageinterface.v1.storage_service_admin_pb2',
                'grpc': 'proto_gen.eadp.cadie.shared.storageinterface.v1.storage_service_admin_pb2_grpc'
            }
        }
        
        if service_name not in service_module_mappings:
            logger.warning(f"⚠️  No fallback mapping for service: {service_name}")
            return False
        
        mapping = service_module_mappings[service_name]
        
        try:
            # Try to load the mapped modules
            pb2_module = self._import_module(mapping['pb2'])
            grpc_module = self._import_module(mapping['grpc'])
            
            if pb2_module and grpc_module:
                self.compiled_modules[service_name] = {
                    'pb2': pb2_module,
                    'grpc': grpc_module
                }
                logger.info(f"✅ Fallback loading successful for {service_name}")
                return True
            else:
                logger.error(f"❌ Failed to load fallback modules for {service_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Fallback loading failed for {service_name}: {str(e)}")
            return False
    def _import_module(self, module_name: str) -> Optional[Any]:
        """Import a compiled module with simplified import handling"""
        try:
            logger.debug(f"📦 Importing module: {module_name}")
            
            # Simply try to import the module directly since temp_dir is in sys.path
            import importlib
            module = importlib.import_module(module_name)
            logger.debug(f"✅ Successfully imported: {module_name}")
            return module
            
        except Exception as e:
            logger.error(f"❌ Failed to import {module_name}: {str(e)}")
            logger.error(f"🔴 Error type: {type(e).__name__}")
            import traceback
            logger.error(f"🔴 Traceback: {traceback.format_exc()}")
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