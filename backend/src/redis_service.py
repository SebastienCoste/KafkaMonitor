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
        """Get or create Redis connection for environment (always cluster)"""
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
            # Always try cluster first since user confirmed it's always a cluster
            logger.info(f"🔗 Creating Redis cluster connection for {environment}")
            connection = self._create_cluster_connection(config)
            self.connections[environment] = connection
            logger.info(f"✅ Connected to Redis Cluster in {environment} environment - connection type: {type(connection)}")
            return connection
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis cluster in {environment}: {e}")
            logger.error(f"❌ Error details: {str(e)}")
            raise
    
    def _create_cluster_connection(self, config: RedisConfig):
        """Try to create Redis cluster connection"""
        try:
            # For Redis cluster, use the correct format for startup nodes
            # Option 1: Use host and port directly (redis-py 4.x+ format)
            logger.info(f"🔗 Attempting cluster connection to {config.host}:{config.port}")
            
            connection = RedisCluster(
                host=config.host,  # Use direct host/port parameters
                port=config.port,
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
            logger.info(f"🔗 Redis cluster connection successful - type: {type(connection)}")
            return connection
            
        except Exception as e:
            logger.error(f"❌ Redis cluster connection failed with direct host/port: {e}")
            
            # Option 2: Try with startup_nodes list format
            try:
                logger.info(f"🔗 Attempting cluster connection with startup_nodes format")
                
                # Create startup nodes in the correct format for older redis-py versions
                startup_nodes = [f"{config.host}:{config.port}"]
                
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
                    skip_full_coverage_check=True,
                    health_check_interval=30
                )
                
                # Test cluster connection
                connection.ping()
                logger.info(f"🔗 Redis cluster connection successful with startup_nodes - type: {type(connection)}")
                return connection
                
            except Exception as e2:
                logger.error(f"❌ Redis cluster connection failed with startup_nodes: {e2}")
                
                # Option 3: Try creating a regular Redis connection that might auto-detect cluster
                try:
                    logger.info(f"🔗 Attempting regular Redis connection (may auto-detect cluster)")
                    
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
                        decode_responses=True
                    )
                    
                    # Test connection
                    connection.ping()
                    logger.info(f"🔗 Regular Redis connection successful - type: {type(connection)}")
                    return connection
                    
                except Exception as e3:
                    logger.error(f"❌ All Redis connection attempts failed: {e3}")
                    raise Exception(f"Failed to connect to Redis cluster: direct ({e}), startup_nodes ({e2}), regular ({e3})")
    
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
            
            # Use multiple search strategies to ensure we find all keys
            files = []
            found_keys = set()  # Use set to avoid duplicates
            
            logger.info(f"🔍 Scanning Redis keys for namespace '{namespace}' in {environment}")
            
            # Strategy 1: Direct pattern match
            files_found = await self._scan_with_pattern(connection, f"*{namespace}*")
            for file in files_found:
                if file.key not in found_keys:
                    files.append(file)
                    found_keys.add(file.key)
            
            # Strategy 2: Try different patterns to catch edge cases
            additional_patterns = [
                f"{namespace}*",     # Starting with namespace
                f"*{namespace}",     # Ending with namespace
                f"*{namespace.lower()}*",  # Lowercase version
                f"*{namespace.upper()}*",  # Uppercase version
            ]
            
            for pattern in additional_patterns:
                if pattern != f"*{namespace}*":  # Skip if same as strategy 1
                    additional_files = await self._scan_with_pattern(connection, pattern)
                    for file in additional_files:
                        # Client-side filter to ensure namespace is actually in the key
                        if namespace.lower() in file.key.lower() and file.key not in found_keys:
                            files.append(file)
                            found_keys.add(file.key)
            
            # Sort files by key for consistent ordering
            files.sort(key=lambda f: f.key)
            
            logger.info(f"✅ Found {len(files)} total files containing namespace '{namespace}' in {environment}")
            
            # Log first few keys for debugging
            if files:
                sample_keys = [f.key for f in files[:5]]
                logger.info(f"📝 Sample keys found: {sample_keys}")
            else:
                logger.warning(f"⚠️ No keys found for namespace '{namespace}' in {environment}")
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to get files for namespace '{namespace}' in {environment}: {e}")
            raise
    
    async def _scan_with_pattern(self, connection, pattern: str) -> List[RedisFile]:
        """Scan Redis with a specific pattern (cluster-aware)"""
        files = []
        
        logger.info(f"🔍 Scanning with pattern: '{pattern}'")
        
        # Check if this is a Redis Cluster connection - improved detection
        is_cluster = (
            isinstance(connection, RedisCluster) or 
            hasattr(connection, 'get_nodes') or 
            hasattr(connection, 'nodes') or
            str(type(connection)).find('cluster') != -1
        )
        
        if is_cluster:
            # Redis Cluster mode - scan all nodes
            logger.info(f"🔗 Detected Redis Cluster, scanning all nodes")
            files = await self._scan_cluster_nodes(connection, pattern)
        else:
            # Force cluster mode since user confirmed it's always a cluster
            logger.info(f"⚠️ Forcing cluster mode - user confirmed it's always a cluster")
            files = await self._scan_cluster_nodes(connection, pattern)
        
        logger.info(f"📊 Pattern '{pattern}' completed: {len(files)} files found")
        return files
    
    async def _scan_cluster_nodes(self, connection, pattern: str) -> List[RedisFile]:
        """Scan all nodes in a Redis cluster"""
        files = []
        total_scanned = 0
        
        try:
            # Try different approaches to get cluster nodes
            nodes = []
            
            # Method 1: Direct get_nodes() call
            if hasattr(connection, 'get_nodes') and callable(getattr(connection, 'get_nodes')):
                try:
                    nodes = connection.get_nodes()
                    logger.info(f"🔗 Method 1: Found {len(nodes)} nodes via get_nodes()")
                except Exception as e:
                    logger.debug(f"Method 1 failed: {e}")
            
            # Method 2: Try accessing nodes attribute
            if not nodes and hasattr(connection, 'nodes'):
                try:
                    if hasattr(connection.nodes, 'all_nodes'):
                        nodes = list(connection.nodes.all_nodes())
                    elif hasattr(connection.nodes, 'nodes_cache'):
                        nodes = list(connection.nodes.nodes_cache.values())
                    logger.info(f"🔗 Method 2: Found {len(nodes)} nodes via nodes attribute")
                except Exception as e:
                    logger.debug(f"Method 2 failed: {e}")
            
            # Method 3: Use cluster info to discover nodes
            if not nodes:
                try:
                    cluster_info = connection.cluster_nodes()
                    # Parse cluster nodes output to get individual nodes
                    lines = cluster_info.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 2:
                            node_info = parts[1].split('@')[0]  # Remove port info
                            if ':' in node_info:
                                host, port = node_info.rsplit(':', 1)
                                nodes.append({'host': host, 'port': int(port)})
                    logger.info(f"🔗 Method 3: Found {len(nodes)} nodes via cluster_nodes()")
                except Exception as e:
                    logger.debug(f"Method 3 failed: {e}")
            
            if not nodes:
                logger.error("❌ Could not discover cluster nodes, using connection directly")
                return await self._scan_connection_directly(connection, pattern)
            
            logger.info(f"🔗 Scanning {len(nodes)} cluster nodes for pattern '{pattern}'")
            
            # Scan each node
            for i, node in enumerate(nodes):
                try:
                    if hasattr(node, 'host') and hasattr(node, 'port'):
                        node_host = node.host
                        node_port = node.port
                    elif isinstance(node, dict):
                        node_host = node.get('host', 'unknown')
                        node_port = node.get('port', 'unknown')
                    else:
                        node_host = str(node)
                        node_port = 'unknown'
                    
                    logger.debug(f"📡 Scanning node {i+1}/{len(nodes)}: {node_host}:{node_port}")
                    
                    # Use SCAN_ITER for cluster nodes - this is more reliable
                    node_files = 0
                    
                    try:
                        # Try to scan with target_nodes parameter
                        for key in connection.scan_iter(match=pattern, count=1000, target_nodes=[node]):
                            try:
                                size = connection.strlen(key)
                                files.append(RedisFile(
                                    key=key,
                                    content="",
                                    size_bytes=size
                                ))
                                node_files += 1
                                total_scanned += 1
                            except redis.exceptions.ResponseError as e:
                                if "MOVED" in str(e) or "ASK" in str(e):
                                    logger.debug(f"Redirect handled by cluster client for key {key}")
                                    continue
                                else:
                                    logger.warning(f"Redis error processing key {key}: {e}")
                                    continue
                            except Exception as e:
                                logger.warning(f"Failed to process key {key}: {e}")
                                continue
                    
                    except Exception as scan_error:
                        logger.debug(f"scan_iter with target_nodes failed: {scan_error}")
                        # Fallback: try regular scan_iter (may miss some keys)
                        logger.debug(f"Trying fallback scan for node")
                        
                    logger.debug(f"✅ Node {i+1}/{len(nodes)} completed: {node_files} keys found")
                    
                except Exception as e:
                    logger.error(f"❌ Error scanning node {i+1}: {e}")
                    continue
            
            logger.info(f"🎉 Cluster scan completed: {len(nodes)} nodes, {total_scanned} total keys scanned, {len(files)} files found")
            
        except Exception as e:
            logger.error(f"❌ Error during cluster scan: {e}")
            logger.info(f"⚠️ Falling back to direct connection scan")
            files = await self._scan_connection_directly(connection, pattern)
        
        return files
    
    async def _scan_connection_directly(self, connection, pattern: str) -> List[RedisFile]:
        """Scan using the connection directly (handles cluster redirects)"""
        files = []
        
        try:
            logger.info(f"🔍 Direct scan with pattern: '{pattern}'")
            
            # Use scan_iter which should handle cluster redirects automatically
            key_count = 0
            processed_count = 0
            
            for key in connection.scan_iter(match=pattern, count=1000):
                key_count += 1
                logger.debug(f"🔑 Found key: {key}")
                
                try:
                    # Try to get the key size - this will trigger redirect handling
                    size = connection.strlen(key)
                    
                    files.append(RedisFile(
                        key=key,
                        content="",
                        size_bytes=size
                    ))
                    processed_count += 1
                    logger.debug(f"✅ Successfully processed key: {key} (size: {size})")
                    
                except redis.exceptions.ResponseError as e:
                    if "MOVED" in str(e) or "ASK" in str(e):
                        logger.debug(f"🔄 Retry after redirect for key: {key}")
                        # Try again - the cluster client should have updated its slot mapping
                        try:
                            size = connection.strlen(key)
                            files.append(RedisFile(
                                key=key,
                                content="",
                                size_bytes=size
                            ))
                            processed_count += 1
                            logger.debug(f"✅ Successfully processed after retry: {key} (size: {size})")
                        except Exception as retry_e:
                            logger.warning(f"❌ Failed even after retry for key {key}: {retry_e}")
                            # Add key anyway with size 0 so it shows up
                            files.append(RedisFile(
                                key=key,
                                content="",
                                size_bytes=0
                            ))
                            processed_count += 1
                            logger.info(f"⚠️ Added key with unknown size: {key}")
                    else:
                        logger.warning(f"❌ Redis error processing key {key}: {e}")
                        # Add key anyway with size 0
                        files.append(RedisFile(
                            key=key,
                            content="",
                            size_bytes=0
                        ))
                        processed_count += 1
                        logger.info(f"⚠️ Added key despite error: {key}")
                        
                except Exception as e:
                    logger.warning(f"❌ Failed to process key {key}: {e}")
                    # Add key anyway with size 0
                    files.append(RedisFile(
                        key=key,
                        content="",
                        size_bytes=0
                    ))
                    processed_count += 1
                    logger.info(f"⚠️ Added key despite processing error: {key}")
            
            logger.info(f"📊 Direct scan completed: {key_count} keys found, {processed_count} keys processed, {len(files)} files in result")
            
        except Exception as e:
            logger.error(f"❌ Direct scan failed: {e}")
        
        return files
    
    async def _scan_single_instance(self, connection, pattern: str) -> List[RedisFile]:
        """Scan a single Redis instance"""
        files = []
        cursor = 0
        total_scanned = 0
        scan_iterations = 0
        
        while True:
            try:
                cursor, keys = connection.scan(
                    cursor=cursor,
                    match=pattern,
                    count=1000
                )
                
                scan_iterations += 1
                total_scanned += len(keys)
                logger.debug(f"Single instance scan - Iteration {scan_iterations}: cursor={cursor}, found {len(keys)} keys")
                
                for key in keys:
                    try:
                        # Get content size without fetching content
                        size = connection.strlen(key)
                        
                        files.append(RedisFile(
                            key=key,
                            content="",
                            size_bytes=size
                        ))
                        
                    except redis.exceptions.ResponseError as e:
                        if "MOVED" in str(e) or "ASK" in str(e):
                            logger.debug(f"Redis cluster redirect for key {key}: {e}")
                            continue
                        else:
                            logger.warning(f"Redis error processing key {key}: {e}")
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to process key {key}: {e}")
                        continue
                
                if cursor == 0:
                    break
                    
            except Exception as e:
                logger.error(f"Error during single instance scan: {e}")
                break
        
        logger.info(f"📊 Single instance scan completed: {scan_iterations} iterations, {total_scanned} keys scanned, {len(files)} files found")
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
            
        except redis.exceptions.ResponseError as e:
            if "MOVED" in str(e) or "ASK" in str(e):
                logger.error(f"Redis cluster redirect error for key '{key}': {e}")
                raise ValueError(f"Redis cluster configuration issue - key moved: {key}")
            else:
                logger.error(f"Redis error getting content for key '{key}': {e}")
                raise
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