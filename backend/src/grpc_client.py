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
    
    def __init__(self, proto_dir: str, environments_dir: str):
        self.proto_loader = GrpcProtoLoader(proto_dir)
        self.environments_dir = Path(environments_dir)
        
        # Runtime state
        self.current_environment = None
        self.environment_config = None
        self.credentials = {}  # Stored in memory only
        self.channels = {}
        self.stubs = {}
        
        # Statistics and state
        self.call_statistics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'retry_counts': {},
            'last_reset': datetime.now()
        }
        
        logger.info("🚀 GrpcClient initialized")
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the gRPC client and load proto files"""
        logger.info("🔄 Initializing gRPC client...")
        
        try:
            # Validate proto files
            validation = self.proto_loader.validate_proto_files()
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
            
            # Load service modules
            if not self.proto_loader.load_service_modules():
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
        self.call_statistics = {
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
                self.call_statistics['total_calls'] += 1
                
                # Get the method from stub
                grpc_method = getattr(stub, method_name, None)
                if not grpc_method:
                    return {
                        'success': False,
                        'error': f'Method {method_name} not found on {service_name}'
                    }
                
                # Make the call
                logger.debug(f"🔄 Attempt {retry_count + 1} for {method_key}")
                response = grpc_method(request, metadata=metadata, timeout=timeout)
                
                # Success
                self.call_statistics['successful_calls'] += 1
                if method_key not in self.call_statistics['retry_counts']:
                    self.call_statistics['retry_counts'][method_key] = []
                self.call_statistics['retry_counts'][method_key].append(retry_count)
                
                logger.info(f"✅ {method_key} succeeded after {retry_count} retries")
                
                return {
                    'success': True,
                    'response': response,
                    'retry_count': retry_count,
                    'method': method_key
                }
                
            except grpc.RpcError as e:
                retry_count += 1
                self.call_statistics['failed_calls'] += 1
                
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
            'statistics': self.call_statistics.copy()
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