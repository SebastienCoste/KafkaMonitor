"""
Redis Service for Blueprint Verification

Manages Redis connections and operations for accessing blueprint-related files
across different environments with TLS security.
"""

import redis
from redis.cluster import RedisCluster
import ssl
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from .environment_manager import EnvironmentManager

logger = logging.getLogger(__name__)

@dataclass
class RedisConfig:
    """Redis connection configuration"""
    host: str
    port: int
    token: str
    ca_cert_path: str
    environment: str
    connection_timeout: int = 10
    socket_timeout: int = 10

@dataclass
class RedisFile:
    """Redis file representation"""
    key: str
    content: str = ""
    size_bytes: int = 0
    last_modified: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "key": self.key,
            "content": self.content,
            "size_bytes": self.size_bytes,
            "last_modified": self.last_modified
        }

class RedisService:
    """Service for connecting to Redis instances across environments"""
    
    def __init__(self, environment_manager: EnvironmentManager):
        self.environment_manager = environment_manager
        self.connections: Dict[str, redis.Redis] = {}
        self.ca_cert_path = Path(__file__).parent.parent / "config" / "redis-ca.pem"
        
        # Verify CA certificate exists
        if not self.ca_cert_path.exists():
            logger.warning(f"Redis CA certificate not found: {self.ca_cert_path}")
            logger.info("Redis functionality will be limited without TLS certificate")
    
    def _get_redis_config(self, environment: str) -> RedisConfig:
        """Get Redis configuration for specific environment"""
        try:
            env_config_result = self.environment_manager.get_environment_config(environment)
            
            if not env_config_result.get('success'):
                raise ValueError(f"Environment {environment} not found: {env_config_result.get('error')}")
            
            env_config = env_config_result['config']
            redis_config = env_config.get("redis", {})
            
            if not redis_config:
                raise ValueError(f"No Redis configuration found for environment: {environment}")
            
            required_fields = ["host", "port", "token"]
            missing_fields = [field for field in required_fields if field not in redis_config]
            if missing_fields:
                raise ValueError(f"Missing Redis config fields for {environment}: {missing_fields}")
            
            return RedisConfig(
                host=redis_config["host"],
                port=int(redis_config["port"]),
                token=redis_config["token"],
                ca_cert_path=str(self.ca_cert_path),
                environment=environment,
                connection_timeout=redis_config.get("connection_timeout", 10),
                socket_timeout=redis_config.get("socket_timeout", 10)
            )
            
        except Exception as e:
            logger.error(f"Failed to load Redis config for {environment}: {e}")
            raise
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with AWS CA certificate"""
        try:
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            # Load AWS CA certificate if available
            if self.ca_cert_path.exists():
                context.load_verify_locations(cafile=str(self.ca_cert_path))
                logger.debug("AWS CA certificate loaded for Redis TLS")
            else:
                logger.warning("AWS CA certificate not found, using system certificates")
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise
    
    def _get_connection(self, environment: str):
        """Get or create Redis connection for environment (supports both single and cluster)"""
        if environment in self.connections:
            # Test existing connection
            try:
                self.connections[environment].ping()
                return self.connections[environment]
            except Exception:
                # Connection is stale, remove it
                logger.debug(f"Removing stale Redis connection for {environment}")
                del self.connections[environment]
        
        # Create new connection
        config = self._get_redis_config(environment)
        
        try:
            # Try Redis cluster first, fallback to single instance
            connection = self._create_cluster_connection(config)
            if connection:
                self.connections[environment] = connection
                logger.info(f"✅ Connected to Redis Cluster in {environment} environment")
                return connection
            
            # Fallback to single Redis instance
            connection = self._create_single_connection(config)
            self.connections[environment] = connection
            logger.info(f"✅ Connected to Redis (single instance) in {environment} environment")
            
            return connection
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis in {environment}: {e}")
            raise
    
    def _create_cluster_connection(self, config: RedisConfig):
        """Try to create Redis cluster connection"""
        try:
            # For cluster, we only need the startup node
            startup_nodes = [{"host": config.host, "port": config.port}]
            
            connection = RedisCluster(
                startup_nodes=startup_nodes,
                password=config.token,
                ssl=True,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=str(self.ca_cert_path) if self.ca_cert_path.exists() else None,
                ssl_check_hostname=True,
                socket_connect_timeout=config.connection_timeout,
                socket_timeout=config.socket_timeout,
                retry_on_timeout=True,
                decode_responses=True,
                skip_full_coverage_check=True,  # Allow partial cluster coverage
                health_check_interval=30
            )
            
            # Test cluster connection
            connection.ping()
            logger.info("🔗 Redis cluster connection successful")
            return connection
            
        except Exception as e:
            logger.debug(f"Redis cluster connection failed: {e}")
            return None
    
    def _create_single_connection(self, config: RedisConfig):
        """Create single Redis instance connection"""
        connection = redis.Redis(
            host=config.host,
            port=config.port,
            password=config.token,
            ssl=True,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=str(self.ca_cert_path) if self.ca_cert_path.exists() else None,
            ssl_check_hostname=True,
            socket_connect_timeout=config.connection_timeout,
            socket_timeout=config.socket_timeout,
            retry_on_timeout=True,
            health_check_interval=30,
            decode_responses=True  # Automatically decode bytes to strings
        )
        
        # Test connection
        connection.ping()
        
        return connection
    
    async def get_files_by_namespace(self, environment: str, namespace: str) -> List[RedisFile]:
        """Get all Redis files containing the namespace in their key"""
        try:
            connection = self._get_connection(environment)
            
            # Use SCAN to find keys containing namespace
            files = []
            cursor = 0
            
            logger.info(f"🔍 Scanning Redis keys for namespace '{namespace}' in {environment}")
            
            while True:
                cursor, keys = connection.scan(
                    cursor=cursor,
                    match=f"*{namespace}*",
                    count=100
                )
                
                for key in keys:
                    try:
                        # Get content size without fetching content
                        size = connection.strlen(key)
                        
                        files.append(RedisFile(
                            key=key,
                            content="",  # Content loaded separately
                            size_bytes=size
                        ))
                        
                    except redis.exceptions.ResponseError as e:
                        if "MOVED" in str(e) or "ASK" in str(e):
                            logger.debug(f"Redis cluster redirect for key {key}: {e}")
                            # The cluster client should handle redirects automatically
                            # If we get here, there might be a cluster configuration issue
                            continue
                        else:
                            logger.warning(f"Redis error processing key {key}: {e}")
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to process key {key}: {e}")
                        continue
                
                if cursor == 0:
                    break
            
            # Sort files by key for consistent ordering
            files.sort(key=lambda f: f.key)
            
            logger.info(f"Found {len(files)} files for namespace '{namespace}' in {environment}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to get files for namespace '{namespace}' in {environment}: {e}")
            raise
    
    async def get_file_content(self, environment: str, key: str) -> str:
        """Get content of specific Redis key"""
        try:
            connection = self._get_connection(environment)
            
            # Get raw content
            content = connection.get(key)
            
            if content is None:
                raise ValueError(f"Key not found: {key}")
            
            # Content is already decoded due to decode_responses=True
            logger.debug(f"Retrieved content for key '{key}' ({len(content)} bytes)")
            
            # Try to validate JSON for better error reporting
            try:
                json.loads(content)
                logger.debug(f"Content of key '{key}' is valid JSON")
            except json.JSONDecodeError as e:
                logger.debug(f"Content of key '{key}' is not valid JSON: {e}")
                # Return content anyway for display
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to get content for key '{key}' in {environment}: {e}")
            raise
    
    async def test_connection(self, environment: str) -> Dict[str, Any]:
        """Test Redis connection for environment"""
        try:
            connection = self._get_connection(environment)
            
            # Test connection with info command
            info = connection.info()
            
            return {
                "status": "connected",
                "environment": environment,
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "host": self._get_redis_config(environment).host
            }
            
        except Exception as e:
            logger.error(f"Connection test failed for {environment}: {e}")
            return {
                "status": "failed",
                "environment": environment,
                "error": str(e)
            }
    
    def close_all_connections(self):
        """Close all Redis connections"""
        for env, connection in self.connections.items():
            try:
                connection.close()
                logger.info(f"Closed Redis connection for {env}")
            except Exception as e:
                logger.warning(f"Error closing Redis connection for {env}: {e}")
        
        self.connections.clear()
    
    def get_available_environments(self) -> List[str]:
        """Get list of environments with Redis configuration"""
        environments = []
        
        for env in self.environment_manager.list_environments():
            try:
                env_config_result = self.environment_manager.get_environment_config(env)
                if env_config_result.get('success'):
                    env_config = env_config_result['config']
                    if env_config.get('redis'):
                        environments.append(env)
            except Exception:
                continue
        
        return environments