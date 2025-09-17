"""
gRPC Client for IngressServer and AssetStorageService

Handles gRPC communication with multiple environments and credential management.
Supports unlimited retries and comprehensive error handling.
"""
import os
import logging
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import grpc
import yaml
import random
import string

from .grpc_proto_loader import GrpcProtoLoader

logger = logging.getLogger(__name__)

class GrpcClient:
    """Main gRPC client for Kafka Monitor services"""
    
    def __init__(self, proto_root_dir: str, environments_dir: str):
        self.proto_loader = GrpcProtoLoader(proto_root_dir)
        self.environments_dir = Path(environments_dir)
        self.channels = {}
        self.stubs = {}
        self.credentials = {}  # Stored in memory only
        self.selected_asset_storage_type = 'reader'  # Default to reader
        
        # Load default environment config (DEV) on startup
        self.environment_config = None
        self.current_environment = 'DEV'  # Default environment
        self._load_default_environment()
        
        # Initialize call statistics
        self.call_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_counts': {},
            'last_reset': datetime.now()
        }
        
        logger.info("🚀 GrpcClient initialized")
    
    def _load_default_environment(self):
        """Load default environment configuration"""
        try:
            default_env_file = self.environments_dir / 'dev.yaml'
            if default_env_file.exists():
                with open(default_env_file, 'r') as f:
                    self.environment_config = yaml.safe_load(f)
                logger.info(f"📋 Loaded default environment: {self.current_environment}")
            else:
                logger.warning("⚠️  Default environment file not found, using minimal config")
                self.environment_config = {
                    'grpc_services': {
                        'ingress_server': {
                            'url': 'localhost:50051',
                            'secure': False,
                            'timeout': 30,
                            'service_proto': 'eadp/cadie/ingressserver/v1/ingress_service.proto'
                        },
                        'asset_storage': {
                            'urls': {
                                'reader': 'localhost:50052',
                                'writer': 'localhost:50053'
                            },
                            'secure': False,
                            'timeout': 30,
                            'service_proto': 'eadp/cadie/shared/storageinterface/v1/storage_service_admin.proto'
                        }
                    }
                }
        except Exception as e:
            logger.error(f"❌ Error loading default environment: {e}")
            self.environment_config = {
                'grpc_services': {}
            }
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the gRPC client and load proto files"""
        logger.info("🔄 Initializing gRPC client...")
        
        try:
            # Validate proto files with environment configuration
            validation = self.proto_loader.validate_proto_files(self.environment_config)
            if not validation['all_present']:
                return {
                    'success': False,
                    'error': 'Required proto files are missing',
                    'validation': validation
                }
            
            # Compile proto files
            if not self.proto_loader.compile_proto_files():
                return {
                    'success': False,
                    'error': 'Failed to compile proto files'
                }
            
            # Load service modules with environment configuration
            if not self.proto_loader.load_service_modules(self.environment_config):
                return {
                    'success': False,
                    'error': 'Failed to load service modules'
                }
            
            logger.info("✅ gRPC client initialized successfully")
            return {
                'success': True,
                'available_services': self.proto_loader.list_available_services(),
                'environments': self.list_environments()
            }
            
        except Exception as e:
            error_msg = f"Failed to initialize gRPC client: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def list_environments(self) -> List[str]:
        """Get list of available environments"""
        environments = []
        if self.environments_dir.exists():
            for env_file in self.environments_dir.glob("*.yaml"):
                environments.append(env_file.stem.upper())
        return sorted(environments)
    
    def set_environment(self, environment: str) -> Dict[str, Any]:
        """Set the current environment and load its configuration"""
        logger.info(f"🌍 Setting environment to: {environment}")
        
        try:
            env_file = self.environments_dir / f"{environment.lower()}.yaml"
            if not env_file.exists():
                return {
                    'success': False,
                    'error': f'Environment configuration not found: {environment}'
                }
            
            # Load environment configuration
            with open(env_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Reset state when changing environments
            self._reset_environment_state()
            
            self.current_environment = environment
            self.environment_config = config
            
            logger.info(f"✅ Environment set to: {environment}")
            return {
                'success': True,
                'environment': environment,
                'config': {
                    'name': config.get('name'),
                    'description': config.get('description'),
                    'services': list(config.get('grpc_services', {}).keys())
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to set environment {environment}: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def set_credentials(self, authorization: str, x_pop_token: str) -> Dict[str, Any]:
        """Set credentials for the current environment (stored in memory only)"""
        logger.info("🔐 Setting credentials (memory only)")
        
        if not self.current_environment:
            return {
                'success': False,
                'error': 'No environment selected'
            }
        
        self.credentials = {
            'authorization': authorization,
            'x_pop_token': x_pop_token,
            'set_at': datetime.now()
        }
        
        logger.info("✅ Credentials set successfully")
        return {
            'success': True,
            'message': 'Credentials stored in memory'
        }
    
    
    def get_asset_storage_urls(self) -> Dict[str, Any]:
        """Get available asset-storage URLs for current environment"""
        if not self.current_environment or not self.environment_config:
            return {
                'success': False,
                'error': 'No environment selected'
            }
        
        asset_config = self.environment_config.get('grpc_services', {}).get('asset_storage', {})
        
        if 'urls' in asset_config:
            return {
                'success': True,
                'urls': asset_config['urls'],
                'current_selection': getattr(self, 'selected_asset_storage_type', 'reader')
            }
        else:
            # Backward compatibility
            url = asset_config.get('url', '')
            return {
                'success': True,
                'urls': {'reader': url, 'writer': url},
                'current_selection': 'reader'
            }
    
    def set_asset_storage_url(self, url_type: str) -> Dict[str, Any]:
        """Set which asset-storage URL to use (reader or writer)"""
        logger.info(f"🔗 Setting asset-storage URL type to: {url_type}")
        
        if not self.current_environment or not self.environment_config:
            return {
                'success': False,
                'error': 'No environment selected'
            }
        
        asset_config = self.environment_config.get('grpc_services', {}).get('asset_storage', {})
        
        if 'urls' in asset_config:
            available_types = list(asset_config['urls'].keys())
            if url_type not in available_types:
                return {
                    'success': False,
                    'error': f'Invalid URL type. Available: {available_types}'
                }
        elif url_type not in ['reader', 'writer']:
            return {
                'success': False,
                'error': 'Invalid URL type. Must be reader or writer'
            }
        
        # Set the selected type
        self.selected_asset_storage_type = url_type
        
        # Clear asset_storage channel to force recreation with new URL
        if 'asset_storage' in self.channels:
            try:
                self.channels['asset_storage'].close()
            except:
                pass
            del self.channels['asset_storage']
        
        # Clear asset_storage stub to force recreation
        if 'asset_storage' in self.stubs:
            del self.stubs['asset_storage']
        
        logger.info(f"✅ Asset-storage URL type set to: {url_type}")
        return {
            'success': True,
            'url_type': url_type,
            'message': f'Asset-storage URL type set to {url_type}'
        }
    async def _get_service_stub(self, service_name: str):
        """Get or create a gRPC service stub"""
        try:
            if service_name in self.stubs:
                return self.stubs[service_name]
            
            # Get service configuration
            if service_name not in self.environment_config.get('grpc_services', {}):
                logger.error(f"❌ Service {service_name} not found in configuration")
                return None
            
            service_config = self.environment_config['grpc_services'][service_name]
            
            # Create channel if not exists
            if service_name not in self.channels:
                await self._create_channel(service_name, service_config)
            
            channel = self.channels.get(service_name)
            if not channel:
                logger.error(f"❌ Failed to create channel for {service_name}")
                return None
            
            # Get the stub class from compiled modules
            grpc_module = self.proto_loader.compiled_modules.get(service_name, {}).get('grpc')
            if not grpc_module:
                logger.error(f"❌ gRPC module not found for {service_name}")
                return None
            
            # Find the stub class
            stub_class = None
            for attr_name in dir(grpc_module):
                if attr_name.endswith('Stub') and not attr_name.startswith('_'):
                    stub_class = getattr(grpc_module, attr_name)
                    break
            
            if not stub_class:
                logger.error(f"❌ Stub class not found for {service_name}")
                return None
            
            # Create and cache the stub
            stub = stub_class(channel)
            self.stubs[service_name] = stub
            
            logger.info(f"✅ Created stub for {service_name}")
            return stub
            
        except Exception as e:
            logger.error(f"❌ Error creating stub for {service_name}: {e}")
            return None

    async def _create_channel(self, service_name: str, service_config: Dict[str, Any]):
        """Create a gRPC channel for a service"""
        try:
            # Get the service URL
            if service_name == 'asset_storage' and 'urls' in service_config:
                # Handle asset storage with multiple URLs
                url_type = self.selected_asset_storage_type or 'reader'
                service_url = service_config['urls'].get(url_type)
            else:
                service_url = service_config.get('url')
            
            if not service_url:
                raise ValueError(f"No URL configured for service {service_name}")
            
            # Create channel based on security settings
            if service_config.get('secure', False):
                channel = grpc.aio.secure_channel(service_url, grpc.ssl_channel_credentials())
            else:
                channel = grpc.aio.insecure_channel(service_url)
            
            self.channels[service_name] = channel
            logger.info(f"✅ Created channel for {service_name} -> {service_url}")
            
        except Exception as e:
            logger.error(f"❌ Error creating channel for {service_name}: {e}")
            raise

    def _reset_environment_state(self):
        """Reset all environment-specific state"""
        logger.info("🔄 Resetting environment state...")
        
        # Close existing channels
        for channel in self.channels.values():
            try:
                channel.close()
            except:
                pass
        
        # Clear state
        self.channels.clear()
        self.stubs.clear()
        self.credentials.clear()
        
        # Reset statistics
        self.call_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_counts': {},
            'last_reset': datetime.now()
        }
        
        logger.info("✅ Environment state reset")
    
    def _get_channel(self, service_name: str) -> Optional[grpc.Channel]:
        """Get or create a gRPC channel for a service"""
        if service_name in self.channels:
            return self.channels[service_name]
        
        if not self.environment_config:
            logger.error("❌ No environment configuration loaded")
            return None
        
        service_config = self.environment_config.get('grpc_services', {}).get(service_name)
        if not service_config:
            logger.error(f"❌ Service configuration not found: {service_name}")
            return None
        
        try:
            # Handle multiple URLs for asset_storage (reader/writer)
            if service_name == 'asset_storage' and 'urls' in service_config:
                # For asset_storage, use the selected URL or default to reader
                selected_type = getattr(self, 'selected_asset_storage_type', 'reader')
                url = service_config['urls'].get(selected_type, service_config['urls']['reader'])
                logger.info(f"🔗 Using {selected_type} asset_storage URL: {url}")
            else:
                # For other services or backward compatibility
                url = service_config.get('url', '')
            
            secure = service_config.get('secure', True)
            
            logger.info(f"🔗 Creating channel for {service_name}: {url} (secure: {secure})")
            
            if secure:
                credentials = grpc.ssl_channel_credentials()
                channel = grpc.secure_channel(url, credentials)
            else:
                channel = grpc.insecure_channel(url)
            
            self.channels[service_name] = channel
            return channel
            
        except Exception as e:
            logger.error(f"💥 Failed to create channel for {service_name}: {str(e)}")
            return None
    
    def _get_stub(self, service_name: str):
        """Get or create a service stub"""
        if service_name in self.stubs:
            return self.stubs[service_name]
        
        # Auto-initialize if not already done
        if not self.proto_loader.compiled_modules:
            logger.info("🔄 Auto-initializing gRPC client...")
            try:
                # Compile and load proto files
                if not self.proto_loader.compile_proto_files():
                    logger.error("❌ Failed to compile proto files")
                    return None
                
                if not self.proto_loader.load_service_modules():
                    logger.error("❌ Failed to load service modules")
                    return None
                    
                logger.info("✅ Auto-initialization completed")
            except Exception as e:
                logger.error(f"❌ Auto-initialization failed: {str(e)}")
                return None
        
        channel = self._get_channel(service_name)
        if not channel:
            return None
        
        stub = self.proto_loader.create_service_stub(service_name, channel)
        if stub:
            self.stubs[service_name] = stub
        
        return stub
    
    def _create_metadata(self) -> List[Tuple[str, str]]:
        """Create gRPC metadata from credentials"""
        metadata = []
        
        if self.credentials.get('authorization'):
            metadata.append(('authorization', self.credentials['authorization']))
        
        if self.credentials.get('x_pop_token'):
            metadata.append(('x-pop-token', self.credentials['x_pop_token']))
        
        return metadata
    
    async def _call_with_retry(self, service_name: str, method_name: str, request, max_retries: int = None) -> Dict[str, Any]:
        """Call a gRPC method with limited retries and timeout"""
        logger.info(f"📞 Calling {service_name}.{method_name}")
        
        stub = self._get_stub(service_name)
        if not stub:
            return {
                'success': False,
                'error': f'Failed to get stub for {service_name}'
            }
        
        metadata = self._create_metadata()
        # Use shorter timeout to prevent hanging (configurable, default 10 seconds)
        timeout = self.environment_config.get('grpc_services', {}).get(service_name, {}).get('timeout', 10)
        
        # Set maximum retry limit (default 3, configurable)
        max_retry_limit = max_retries if max_retries is not None else 3
        retry_count = 0
        method_key = f"{service_name}.{method_name}"
        
        while retry_count <= max_retry_limit:
            try:
                self.call_stats['total_calls'] += 1
                
                # Get the method from stub
                grpc_method = getattr(stub, method_name, None)
                if not grpc_method:
                    return {
                        'success': False,
                        'error': f'Method {method_name} not found on {service_name}'
                    }
                
                # Make the call
                logger.debug(f"🔄 Attempt {retry_count + 1} for {method_key}")
                
                # Debug: Log the actual request message content
                try:
                    from google.protobuf.json_format import MessageToDict
                    request_dict = MessageToDict(request)
                    logger.debug(f"📤 Sending request payload: {request_dict}")
                except Exception as debug_error:
                    logger.debug(f"📤 Could not serialize request for debug: {debug_error}")
                    logger.debug(f"📤 Request type: {type(request)}")
                
                response = grpc_method(request, metadata=metadata, timeout=timeout)
                
                # Success
                self.call_stats['successful_calls'] += 1
                if method_key not in self.call_stats['retry_counts']:
                    self.call_stats['retry_counts'][method_key] = []
                self.call_stats['retry_counts'][method_key].append(retry_count)
                
                logger.info(f"✅ {method_key} succeeded after {retry_count} retries")
                
                return {
                    'success': True,
                    'response': response,
                    'retry_count': retry_count,
                    'method': method_key
                }
                
            except grpc.RpcError as e:
                retry_count += 1
                self.call_stats['failed_calls'] += 1
                
                error_details = {
                    'code': e.code().name,
                    'details': e.details(),
                    'retry_count': retry_count
                }
                
                logger.warning(f"⚠️  {method_key} failed (attempt {retry_count}): {error_details}")
                
                # Check if we've exceeded maximum retries
                if retry_count > max_retry_limit:
                    logger.error(f"❌ {method_key} failed after {max_retry_limit} retries: {error_details}")
                    return {
                        'success': False,
                        'error': f'gRPC call failed after {max_retry_limit} retries: {error_details["details"]}',
                        'retry_count': retry_count - 1,
                        'grpc_code': error_details['code']
                    }
                
                # Wait before retry (exponential backoff with jitter)
                wait_time = min(60, 2 ** min(retry_count, 6)) + random.uniform(0, 1)
                logger.debug(f"⏳ Waiting {wait_time:.2f}s before retry...")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                retry_count += 1
                logger.error(f"💥 Unexpected error in {method_key} (attempt {retry_count}): {str(e)}")
                
                # Check if we've exceeded maximum retries for general exceptions
                if retry_count > max_retry_limit:
                    logger.error(f"❌ {method_key} failed after {max_retry_limit} retries due to unexpected error: {str(e)}")
                    return {
                        'success': False,
                        'error': f'gRPC call failed after {max_retry_limit} retries: {str(e)}',
                        'retry_count': retry_count - 1
                    }
                
                # Wait before retry
                await asyncio.sleep(min(30, retry_count * 2))
        
        # This should never be reached due to the retry limit, but safety fallback
        logger.error(f"❌ {method_key} exhausted all {max_retry_limit} retries")
        return {
            'success': False,
            'error': f'gRPC call exhausted all {max_retry_limit} retries',
            'retry_count': max_retry_limit
        }
    
    # IngressServer Methods
    
    async def upsert_content(self, content_data: Dict[str, Any], random_field: Optional[str] = None) -> Dict[str, Any]:
        """Call IngressServer.UpsertContent"""
        logger.info("📝 Preparing UpsertContent request")
        
        try:
            # Get message class
            request_class = self.proto_loader.get_message_class('ingress_server', 'UpsertContentRequest')
            if not request_class:
                return {'success': False, 'error': 'UpsertContentRequest class not found'}
            
            # Create request with provided data
            request_data = content_data.copy()
            
            # Inject random string if requested
            if random_field and random_field in request_data:
                random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                request_data[random_field] = f"{request_data[random_field]}_{random_string}"
                logger.info(f"🎲 Injected random string into field '{random_field}': {random_string}")
            
            # Create request
            request = request_class(**request_data)
            
            # Make the call
            result = await self._call_with_retry('ingress_server', 'UpsertContent', request)
            
            if result['success']:
                response = result['response']
                return {
                    'success': True,
                    'id': getattr(response, 'id', None),
                    'event_time': getattr(response, 'event_time', None),
                    'retry_count': result['retry_count'],
                    'response_data': self._message_to_dict(response)
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to create UpsertContent request: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {'success': False, 'error': error_msg}
    
    async def call_dynamic_method(self, service_name: str, method_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamically call any gRPC service method"""
        try:
            logger.info(f"📞 Dynamic gRPC call: {service_name}.{method_name}")
            
            # Get the service stub
            stub = await self._get_service_stub(service_name)
            if not stub:
                return {
                    'success': False,
                    'error': f'Service stub not available for {service_name}'
                }
            
            # Get the method from the stub
            if not hasattr(stub, method_name):
                return {
                    'success': False,
                    'error': f'Method {method_name} not found in service {service_name}'
                }
            
            grpc_method = getattr(stub, method_name)
            
            # Get the request message class
            request_class = self.proto_loader.get_message_class(service_name, f"{method_name}Request")
            if not request_class:
                return {
                    'success': False,
                    'error': f'Request message class not found for {method_name}'
                }
            
            # Process the request data (handle {{rand}} replacement)
            processed_data = self._process_template_variables(request_data)
            
            # Create the request message
            try:
                request_message = self._create_request_message(request_class, processed_data)
            except Exception as e:
                return {
                    'success': False,
                    'error': f'Failed to create request message: {str(e)}'
                }
            
            # Make the gRPC call with retry
            try:
                response = await self._call_with_retry(service_name, method_name, request_message)
                
                # Convert response to dict
                response_dict = {}
                if hasattr(response, 'ListFields'):
                    for field, value in response.ListFields():
                        response_dict[field.name] = self._convert_proto_value(value)
                
                return {
                    'success': True,
                    'data': response_dict
                }
                
            except Exception as e:
                logger.error(f"❌ gRPC call failed: {str(e)}")
                return {
                    'success': False,
                    'error': f'gRPC call failed: {str(e)}'
                }
                
        except Exception as e:
            logger.error(f"❌ Dynamic method call error: {str(e)}")
            return {
                'success': False,
                'error': f'Dynamic method call error: {str(e)}'
            }
    
    def _process_template_variables(self, data: Dict[str, Any], variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process template variables like {{rand}} in request data"""
        import json
        import random
        import string
        
        # Convert to JSON string and back to handle nested structures
        json_str = json.dumps(data)
        
        # Replace {{rand}} with random values
        import re
        def replace_rand(match):
            # Generate random string of 8 characters
            return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        json_str = re.sub(r'\{\{rand\}\}', replace_rand, json_str)
        
        # Handle custom variables if provided
        if variables:
            for key, value in variables.items():
                json_str = json_str.replace(f'{{{{{key}}}}}', str(value))
        
        return json.loads(json_str)
    
    def _create_request_message(self, request_class, data: Dict[str, Any]):
        """Create a protobuf message from dictionary data with support for nested messages and oneof fields"""
        try:
            # Create the message instance
            message = request_class()
            logger.debug(f"🏗️  Creating message of type: {request_class.__name__}")

            
            # Fill the message fields
            for field_name, field_value in data.items():
                if hasattr(message, field_name):
                    try:
                        # Get field descriptor to understand the field type
                        field_descriptor = message.DESCRIPTOR.fields_by_name.get(field_name)
                        
                        if field_descriptor:

                            success = self._set_field_value(message, field_descriptor, field_name, field_value)
                            if success:
                                logger.debug(f"✅ Successfully set field {field_name}")
                            else:
                                logger.warning(f"⚠️  Failed to set field {field_name} using descriptor, trying direct assignment")

                                setattr(message, field_name, field_value)
                        else:
                            # Fallback to direct assignment
                            setattr(message, field_name, field_value)
                            logger.debug(f"✅ Set field {field_name} via direct assignment")

                    except Exception as field_error:
                        logger.warning(f"⚠️  Failed to set field {field_name}: {field_error}")
                        # Try simple assignment as fallback
                        try:
                            setattr(message, field_name, field_value)
                            logger.debug(f"✅ Set field {field_name} via fallback assignment")
                        except Exception as fallback_error:
                            logger.warning(f"⚠️  Fallback assignment also failed for {field_name}: {fallback_error}")
                else:
                    logger.warning(f"⚠️  Field {field_name} not found in message class")
            
            logger.debug(f"🏁 Message creation completed for {request_class.__name__}")

            return message
            
        except Exception as e:
            logger.error(f"❌ Failed to create request message: {e}")
            raise

    def _set_field_value(self, message, field_descriptor, field_name: str, field_value):
        """Set a field value on a protobuf message based on field descriptor"""
        try:
            from google.protobuf.descriptor import FieldDescriptor
            
            if field_descriptor.type == FieldDescriptor.TYPE_MESSAGE:
                # This is a message field, need to create nested message
                if isinstance(field_value, dict):
                    nested_message = self._create_nested_message(field_descriptor.message_type, field_value)
                    
                    # Check if this field is part of a oneof group
                    if field_descriptor.containing_oneof:
                        logger.debug(f"🔄 Setting oneof field {field_name} in group {field_descriptor.containing_oneof.name}")
                        # For oneof fields, we need to use CopyFrom or direct field access
                        field_obj = getattr(message, field_name)
                        field_obj.CopyFrom(nested_message)
                        return True
                    else:
                        setattr(message, field_name, nested_message)
                        return True
                else:
                    logger.warning(f"⚠️  Expected dict for message field {field_name}, got {type(field_value)}")
                    return False
            elif field_descriptor.type == FieldDescriptor.TYPE_STRING:
                setattr(message, field_name, str(field_value))
                return True
            elif field_descriptor.type in [FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_INT64]:
                setattr(message, field_name, int(field_value))
                return True
            elif field_descriptor.type == FieldDescriptor.TYPE_BOOL:
                setattr(message, field_name, bool(field_value))
                return True
            elif field_descriptor.type in [FieldDescriptor.TYPE_DOUBLE, FieldDescriptor.TYPE_FLOAT]:
                setattr(message, field_name, float(field_value))
                return True
            else:
                # Try direct assignment for other types
                setattr(message, field_name, field_value)
                return True
                
        except Exception as e:
            logger.debug(f"🔍 Field setting failed for {field_name}: {e}")
            return False
    
    def _create_nested_message(self, message_descriptor, data: Dict[str, Any]):
        """Create a nested protobuf message from dictionary data"""
        try:
            # Get the message class from the descriptor
            message_class = message_descriptor._concrete_class
            message = message_class()

            logger.debug(f"🏗️  Creating nested message: {message_descriptor.name}")
            
            # Fill the nested message fields recursively
            for field_name, field_value in data.items():
                if hasattr(message, field_name):
                    # Get field descriptor for nested field
                    field_descriptor = message.DESCRIPTOR.fields_by_name.get(field_name)
                    if field_descriptor:
                        success = self._set_field_value(message, field_descriptor, field_name, field_value)
                        if success:
                            logger.debug(f"✅ Set nested field {field_name}")
                        else:
                            # Fallback to direct assignment
                            setattr(message, field_name, field_value)
                            logger.debug(f"✅ Set nested field {field_name} via fallback")
                    else:
                        setattr(message, field_name, field_value)
                        logger.debug(f"✅ Set nested field {field_name} directly")

                else:
                    logger.debug(f"🔍 Field {field_name} not found in nested message {message_descriptor.name}")
            
            return message
            
        except Exception as e:
            logger.error(f"❌ Failed to create nested message: {e}")
            raise
    
    def _convert_proto_value(self, value):
        """Convert protobuf values to JSON-serializable types"""
        from google.protobuf.message import Message
        from google.protobuf.pyext._message import RepeatedCompositeContainer, RepeatedScalarContainer
        
        if isinstance(value, Message):
            # Convert message to dict
            result = {}
            for field, field_value in value.ListFields():
                result[field.name] = self._convert_proto_value(field_value)
            return result
        elif isinstance(value, (RepeatedCompositeContainer, RepeatedScalarContainer)):
            # Convert repeated fields to list
            return [self._convert_proto_value(item) for item in value]
        else:
            # Return primitive values as-is
            return value

    async def get_method_example(self, service_name: str, method_name: str) -> Dict[str, Any]:
        """Generate example request data for a specific method with full depth"""

        try:
            # Get the request message class
            request_class = self.proto_loader.get_message_class(service_name, f"{method_name}Request")
            if not request_class:
                return {}
            
            # Create a temporary instance to inspect fields
            temp_instance = request_class()
            
            # Generate example with full depth recursively
            example = self._generate_message_example(temp_instance.DESCRIPTOR, visited_types=set())
            
            return example
            
        except Exception as e:
            logger.error(f"❌ Error generating example for {service_name}.{method_name}: {e}")
            return {}

    def _generate_message_example(self, message_descriptor, visited_types: set = None, depth: int = 0) -> Dict[str, Any]:
        """Recursively generate example data for a protobuf message with full depth"""
        if visited_types is None:
            visited_types = set()
        
        # Prevent infinite recursion for circular references
        message_type_name = message_descriptor.full_name
        if message_type_name in visited_types or depth > 5:  # Max depth of 5 levels
            return {}
        
        visited_types.add(message_type_name)
        example = {}
        
        try:
            # Get field descriptors
            for field in message_descriptor.fields:
                field_name = field.name
                field_type = field.type
                
                # Generate example values based on field type
                if field_type == field.TYPE_STRING:
                    if 'id' in field_name.lower():
                        example[field_name] = f"example-{field_name}-{{{{rand}}}}"
                    elif 'name' in field_name.lower() or 'title' in field_name.lower():
                        example[field_name] = f"Example {field_name.replace('_', ' ').title()}"
                    elif 'content' in field_name.lower():
                        if field_name.endswith('_data'):
                            example[field_name] = '{"key": "value", "data": "{{rand}}"}'
                        else:
                            example[field_name] = "Example content with {{rand}} template"
                    elif 'url' in field_name.lower():
                        example[field_name] = f"https://example.com/{field_name}/{{{{rand}}}}"
                    elif 'email' in field_name.lower():
                        example[field_name] = "user-{{rand}}@example.com"
                    elif 'token' in field_name.lower():
                        example[field_name] = "eyJhbGciOiJIUzI1NiIs-{{rand}}"
                    elif 'schema' in field_name.lower():
                        example[field_name] = "ea.example.schema.v1"
                    else:
                        example[field_name] = f"example_{field_name}_{{{{rand}}}}"
                        
                elif field_type == field.TYPE_INT32:
                    if 'count' in field_name.lower():
                        example[field_name] = 5
                    elif 'size' in field_name.lower():
                        example[field_name] = 1024
                    elif 'port' in field_name.lower():
                        example[field_name] = 8080
                    else:
                        example[field_name] = 123
                        
                elif field_type == field.TYPE_INT64:
                    if 'time' in field_name.lower() or 'timestamp' in field_name.lower():
                        import time
                        example[field_name] = int(time.time() * 1000)  # milliseconds
                    else:
                        example[field_name] = 1234567890
                        
                elif field_type == field.TYPE_BOOL:
                    example[field_name] = True
                    
                elif field_type == field.TYPE_DOUBLE or field_type == field.TYPE_FLOAT:
                    if 'rate' in field_name.lower() or 'ratio' in field_name.lower():
                        example[field_name] = 0.75
                    else:
                        example[field_name] = 1.23
                        
                elif field_type == field.TYPE_BYTES:
                    example[field_name] = "ZXhhbXBsZSBieXRlcyBkYXRh"  # base64 encoded "example bytes data"
                    
                elif field_type == field.TYPE_MESSAGE:
                    # Recursively generate nested message example
                    if field.message_type:
                        nested_example = self._generate_message_example(
                            field.message_type, 
                            visited_types.copy(), 
                            depth + 1
                        )
                        example[field_name] = nested_example
                    else:
                        example[field_name] = {}
                        
                elif field_type == field.TYPE_ENUM:
                    # Get first enum value (skip the first one if it's 0/UNKNOWN)
                    if field.enum_type and field.enum_type.values:
                        enum_values = field.enum_type.values
                        if len(enum_values) > 1:
                            example[field_name] = enum_values[1].name  # Skip first (usually UNKNOWN)
                        else:
                            example[field_name] = enum_values[0].name
                    else:
                        example[field_name] = "EXAMPLE_ENUM_VALUE"
                        
                else:
                    example[field_name] = f"example_{field_name}"
            
            # Handle repeated fields (arrays)
            for field in message_descriptor.fields:
                if field.label == field.LABEL_REPEATED:
                    field_name = field.name
                    if field_name in example:
                        # Convert single values to arrays with 1-2 examples
                        single_value = example[field_name]
                        if field.type == field.TYPE_MESSAGE:
                            # For message arrays, create 2 different examples
                            if single_value:
                                second_example = self._generate_message_example(
                                    field.message_type, 
                                    visited_types.copy(), 
                                    depth + 1
                                )
                                # Modify some values in second example
                                for key in second_example:
                                    if isinstance(second_example[key], str) and "{{rand}}" in second_example[key]:
                                        second_example[key] = second_example[key].replace("{{rand}}", "{{rand}}")
                                example[field_name] = [single_value, second_example]
                            else:
                                example[field_name] = [{}]
                        else:
                            # For primitive arrays
                            if isinstance(single_value, str):
                                example[field_name] = [single_value, single_value.replace("{{rand}}", "{{rand}}")]
                            elif isinstance(single_value, (int, float)):
                                example[field_name] = [single_value, single_value + 1]
                            else:
                                example[field_name] = [single_value, single_value]
        
        except Exception as e:
            logger.error(f"❌ Error generating message example for {message_descriptor.name}: {e}")
        
        finally:
            visited_types.discard(message_type_name)
        
        return example

    async def batch_create_assets(self, assets_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call IngressServer.BatchCreateAssets"""
        logger.info(f"📦 Preparing BatchCreateAssets request for {len(assets_data)} assets")
        
        try:
            request_class = self.proto_loader.get_message_class('ingress_server', 'BatchCreateAssetsRequest')
            if not request_class:
                return {'success': False, 'error': 'BatchCreateAssetsRequest class not found'}
            
            request = request_class(assets=assets_data)
            result = await self._call_with_retry('ingress_server', 'BatchCreateAssets', request)
            
            if result['success']:
                response = result['response']
                # Extract upload URLs for UI display
                upload_urls = getattr(response, 'upload_urls', [])
                
                return {
                    'success': True,
                    'upload_urls': [{'asset_id': url.asset_id, 'upload_url': url.upload_url} for url in upload_urls],
                    'retry_count': result['retry_count'],
                    'response_data': self._message_to_dict(response)
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to create BatchCreateAssets request: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {'success': False, 'error': error_msg}
    
    async def batch_add_download_counts(self, player_id: str, content_ids: List[str]) -> Dict[str, Any]:
        """Call IngressServer.BatchAddDownloadCounts"""
        logger.info(f"📊 Preparing BatchAddDownloadCounts for player {player_id} with {len(content_ids)} content IDs")
        
        try:
            request_class = self.proto_loader.get_message_class('ingress_server', 'BatchAddDownloadCountsRequest')
            if not request_class:
                return {'success': False, 'error': 'BatchAddDownloadCountsRequest class not found'}
            
            # Create download count entries (always increment by 1)
            download_counts = [{'content_id': cid, 'player_id': player_id, 'count': 1} for cid in content_ids]
            
            request = request_class(download_counts=download_counts)
            result = await self._call_with_retry('ingress_server', 'BatchAddDownloadCounts', request)
            
            if result['success']:
                return {
                    'success': True,
                    'retry_count': result['retry_count'],
                    'response_data': self._message_to_dict(result['response'])
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to create BatchAddDownloadCounts request: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {'success': False, 'error': error_msg}
    
    async def batch_add_ratings(self, rating_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call IngressServer.BatchAddRatings"""
        logger.info("⭐ Preparing BatchAddRatings request")
        
        try:
            request_class = self.proto_loader.get_message_class('ingress_server', 'BatchAddRatingsRequest')
            if not request_class:
                return {'success': False, 'error': 'BatchAddRatingsRequest class not found'}
            
            request = request_class(**rating_data)
            result = await self._call_with_retry('ingress_server', 'BatchAddRatings', request)
            
            if result['success']:
                return {
                    'success': True,
                    'retry_count': result['retry_count'],
                    'response_data': self._message_to_dict(result['response'])
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to create BatchAddRatings request: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {'success': False, 'error': error_msg}
    
    # AssetStorageService Methods
    
    async def batch_get_signed_urls(self, asset_ids: List[str]) -> Dict[str, Any]:
        """Call AssetStorageService.BatchGetSignedUrls"""
        logger.info(f"🔗 Preparing BatchGetSignedUrls for {len(asset_ids)} assets")
        
        try:
            request_class = self.proto_loader.get_message_class('asset_storage', 'BatchGetSignedUrlsRequest')
            if not request_class:
                return {'success': False, 'error': 'BatchGetSignedUrlsRequest class not found'}
            
            request = request_class(asset_ids=asset_ids)
            result = await self._call_with_retry('asset_storage', 'BatchGetSignedUrls', request)
            
            if result['success']:
                response = result['response']
                signed_urls = getattr(response, 'signed_urls', [])
                
                return {
                    'success': True,
                    'signed_urls': [{'asset_id': url.asset_id, 'signed_url': url.signed_url} for url in signed_urls],
                    'retry_count': result['retry_count'],
                    'response_data': self._message_to_dict(response)
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to create BatchGetSignedUrls request: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {'success': False, 'error': error_msg}
    
    async def batch_update_statuses(self, asset_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call AssetStorageService.BatchUpdateStatuses"""
        logger.info(f"🔄 Preparing BatchUpdateStatuses for {len(asset_updates)} assets")
        
        try:
            request_class = self.proto_loader.get_message_class('asset_storage', 'BatchUpdateStatusesRequest')
            if not request_class:
                return {'success': False, 'error': 'BatchUpdateStatusesRequest class not found'}
            
            request = request_class(asset_updates=asset_updates)
            result = await self._call_with_retry('asset_storage', 'BatchUpdateStatuses', request)
            
            if result['success']:
                return {
                    'success': True,
                    'retry_count': result['retry_count'],
                    'response_data': self._message_to_dict(result['response'])
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to create BatchUpdateStatuses request: {str(e)}"
            logger.error(f"💥 {error_msg}")
            return {'success': False, 'error': error_msg}
    
    def _message_to_dict(self, message) -> Dict[str, Any]:
        """Convert protobuf message to dictionary"""
        try:
            # This is a simplified conversion - in practice you might need MessageToDict from google.protobuf.json_format
            if hasattr(message, 'DESCRIPTOR'):
                result = {}
                for field in message.DESCRIPTOR.fields:
                    value = getattr(message, field.name, None)
                    if value is not None:
                        result[field.name] = str(value)  # Simple string conversion
                return result
            else:
                return {'raw_response': str(message)}
        except Exception as e:
            logger.error(f"Failed to convert message to dict: {str(e)}")
            return {'error': 'Failed to convert response', 'raw': str(message)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current client status"""
        return {
            'initialized': len(self.proto_loader.compiled_modules) > 0,
            'current_environment': self.current_environment,
            'credentials_set': bool(self.credentials),
            'active_channels': list(self.channels.keys()),
            'active_stubs': list(self.stubs.keys()),
            'proto_status': self.proto_loader.get_proto_status(),
            'statistics': self.call_stats.copy()
        }
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up gRPC client...")
        
        # Close channels
        for channel in self.channels.values():
            try:
                channel.close()
            except:
                pass
        
        # Clear state
        self.channels.clear()
        self.stubs.clear()
        self.credentials.clear()
        
        # Cleanup proto loader
        self.proto_loader.cleanup()
        
        logger.info("✅ gRPC client cleanup completed")