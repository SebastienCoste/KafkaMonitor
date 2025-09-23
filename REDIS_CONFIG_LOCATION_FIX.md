# Redis Configuration Location Fix

## Issue
Redis endpoints were incorrectly reading configuration from `backend/config/settings.yaml` instead of the environment-specific configuration files in `backend/config/environments/<env>.yaml`.

## Root Cause
The application architecture uses environment-specific YAML files for per-environment configuration (Kafka, gRPC, Redis, Blueprint Server, etc.), but the Redis endpoints were hardcoded to read from the global `settings.yaml` file.

## Solution
Updated both Redis API endpoints to read configuration from the correct location:
- **Before**: `backend/config/settings.yaml` → `redis: { dev: {...}, test: {...}, ... }`
- **After**: `backend/config/environments/<env>.yaml` → `redis: { host, port, token, ... }`

## Changes Made

### 1. Updated `/api/redis/test-connection` endpoint
```python
# Changed from:
settings_yaml = ROOT_DIR / "config" / "settings.yaml"
redis_config = settings.get('redis', {}).get(environment.lower())

# Changed to:
env_file = ROOT_DIR / "config" / "environments" / f"{environment.lower()}.yaml"
redis_config = env_config.get('redis')
```

### 2. Updated `/api/redis/files` endpoint
Same change as above - now reads from environment-specific files.

### 3. Enhanced Redis Connection Handling
Both endpoints now support the full Redis configuration schema from environment files:
- `host` - Redis server hostname
- `port` - Redis server port
- `token` - Authentication token (preferred)
- `password` - Fallback authentication
- `db` - Database number (for local Redis)
- `ca_cert_path` - SSL certificate path
- `connection_timeout` - Connection timeout
- `socket_timeout` - Socket timeout
- `retry_on_timeout` - Retry flag
- `health_check_interval` - Health check interval

### 4. Added SSL/TLS Support
If `ca_cert_path` is specified in the environment config, the connection will use SSL/TLS with certificate verification.

### 5. Cleaned up settings.yaml
Removed the Redis configuration block from `settings.yaml` and added a note pointing to the environment files.

## Environment File Structure
Each environment file (`dev.yaml`, `test.yaml`, `int.yaml`, `load.yaml`, `prod.yaml`) contains:

```yaml
# INT Environment Configuration
name: "INT"
description: "Integration Environment"

# Redis Configuration for Blueprint Verification
redis:
  host: "redis-int.example.com"
  port: 6380
  token: "int-redis-auth-token-here"
  ca_cert_path: "config/redis-ca.pem"
  connection_timeout: 10
  socket_timeout: 10
  retry_on_timeout: true
  health_check_interval: 30
```

## Testing Results

### Test 1: Connection Test (INT environment)
```bash
curl -X POST "http://localhost:8001/api/redis/test-connection" \
  -H "Content-Type: application/json" \
  -d '{"environment": "INT"}'
```

**Logs show**:
```
📁 Environment config file: /app/backend/config/environments/int.yaml
🔧 Looking for redis configuration in INT environment file...
✅ Found Redis config - Host: redis-int.example.com, Port: 6380
🔌 Attempting connection...
🔒 Using SSL with CA cert: /app/backend/config/redis-ca.pem
```

✅ **Result**: Correctly reads from INT environment file and attempts SSL connection

### Test 2: Files Endpoint (INT environment)
```bash
curl "http://localhost:8001/api/redis/files?environment=INT&namespace=test.namespace"
```

✅ **Result**: Correctly reads from INT environment file and attempts connection

### Test 3: Different Environment (DEV)
```bash
curl -X POST "http://localhost:8001/api/redis/test-connection" \
  -H "Content-Type: application/json" \
  -d '{"environment": "DEV"}'
```

✅ **Result**: Correctly reads from DEV environment file with different configuration

## Benefits

1. **Consistency**: Redis configuration follows the same pattern as Kafka, gRPC, and Blueprint Server configs
2. **Separation**: Each environment has its own isolated configuration
3. **Security**: Environment-specific tokens and certificates are properly isolated
4. **Maintainability**: Configuration is organized by environment, not by service
5. **SSL Support**: Full SSL/TLS support with certificate verification
6. **Flexibility**: Supports both token-based and password-based authentication

## Files Modified

1. `backend/server.py` - Updated both Redis endpoints
2. `backend/config/settings.yaml` - Removed Redis config block, added note
3. Documentation - Created this file

## Notes

- Environment files already contained the correct Redis configuration
- No changes needed to environment files themselves
- The fix was entirely in the backend endpoint code
- Connection failures to actual Redis servers are expected (servers don't exist in this environment)
- All logging confirms the configuration is being read from the correct location
