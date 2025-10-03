# Marauder's Map - Troubleshooting Guide

This document contains solutions to common issues encountered with the Marauder's Map application.

## 🔧 Issues Fixed

### 1. Application Shutdown Issues ✅ RESOLVED

**Problem**: Application was shutting down unexpectedly without clear error messages.

**Root Cause**: Missing `protoc` (Protocol Buffers compiler) binary and insufficient logging.

**Solution**:
- **Added extensive logging** throughout all components with detailed debug information
- **Installed protobuf compiler**: `apt-get install protobuf-compiler`
- **Enhanced error handling** with detailed stack traces and error context

**Prevention**: The application now provides clear error messages and extensive logs to help diagnose startup issues.

### 2. Protobuf Subfolder Import Issues ✅ RESOLVED

**Problem**: When protobuf messages are in subfolders and reference other messages in other subfolders, the application couldn't find the imported dependencies.

**Root Cause**: 
- Protoc compilation wasn't handling subfolder dependencies correctly
- Python import paths weren't configured for generated protobuf modules
- Generated protobuf files couldn't find their imported dependencies

**Solution**:
- **Enhanced protobuf decoder** to handle subfolder structure and imports
- **Compile all dependencies** at once to resolve cross-references
- **Dynamic Python path management** during module loading
- **Proper temporary directory structure** that preserves the original proto layout

**Example Structure Supported**:
```
proto/
├── common/
│   ├── base.proto      # Contains BaseHeader, Status, etc.
│   └── address.proto   # Contains Address, ContactInfo
├── events/
│   └── user_events.proto    # Imports from common/
├── processing/
│   └── processed_events.proto  # Imports from common/
├── notifications.proto
└── analytics.proto
```

**Files with Cross-References**:
- `events/user_events.proto` imports `common/base.proto` and `common/address.proto`
- `processing/processed_events.proto` imports `common/base.proto` and `common/address.proto`

## 🚀 System Requirements

### Required System Packages
```bash
# Protocol Buffers compiler (REQUIRED)
apt-get install protobuf-compiler

# Verify installation
protoc --version
```

### Python Dependencies
All required Python packages are listed in `requirements.txt`:
- `confluent-kafka>=2.11.1` - Kafka client
- `protobuf>=6.32.0` - Protocol Buffers support
- `PyYAML>=6.0.2` - YAML configuration parsing
- `websockets>=15.0.1` - WebSocket support for real-time updates
- `structlog>=25.4.0` - Structured logging

## 🔍 Debugging with Enhanced Logging

The application now provides extensive logging at multiple levels:

### Log Levels Available
- **DEBUG**: Detailed execution flow, variable values, file operations
- **INFO**: Major operations, initialization steps, successful operations  
- **ERROR**: Failures with full stack traces and context

### Key Log Markers
- 🔄 Starting operations
- ✅ Successful completions
- 💥 Errors and failures
- 🎯 Important values and paths
- 📄 File operations
- 🔗 Connection and import operations

### Example Debug Flow for Protobuf Loading
```
INFO:src.protobuf_decoder:🔄 Loading protobuf for topic: user-events
INFO:src.protobuf_decoder:📄 Proto file: events/user_events.proto
INFO:src.protobuf_decoder:🎯 Message type: UserEvent
INFO:src.protobuf_decoder:📂 Proto directory: /app/backend/config/proto
DEBUG:src.protobuf_decoder:✅ Found proto file at direct path: /app/backend/config/proto/events/user_events.proto
INFO:src.protobuf_decoder:🔄 Starting protobuf compilation for: /app/backend/config/proto/events/user_events.proto
INFO:src.protobuf_decoder:🚀 Running protoc command: protoc --python_out=/tmp/tmp5nwa --proto_path=/tmp/tmp5nwa/proto events/user_events.proto common/base.proto common/address.proto
INFO:src.protobuf_decoder:✅ Protoc compilation successful!
INFO:src.protobuf_decoder:✅ Successfully loaded message class: UserEvent
```

## 🔧 Common Issues and Solutions

### Issue: "No module named 'protoc'"
**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'protoc'`

**Solution**:
```bash
apt-get update
apt-get install protobuf-compiler
```

### Issue: "No module named 'common'"
**Error**: `ModuleNotFoundError: No module named 'common'`

**Solution**: This is resolved by the enhanced protobuf decoder that compiles all dependencies together. The issue occurs when protobuf files import from subfolders but the dependencies aren't compiled first.

### Issue: Application starts but no traces appear
**Symptoms**: 
- API returns `{"traces_count": 0}`
- WebSocket shows "Disconnected"
- No error messages

**Debugging Steps**:
1. Check backend logs: `tail -f /var/log/supervisor/backend.*.log`
2. Verify mock mode is enabled in `config/kafka.yaml`: `mock_mode: true`
3. Check topic monitoring configuration: `curl http://localhost:8001/api/topics`
4. Verify graph builder initialization in logs

### Issue: Protobuf compilation fails
**Symptoms**: `ProtobufDecodingError: Protobuf loading failed`

**Debugging Steps**:
1. Verify all `.proto` files exist in the configured paths
2. Check protobuf import statements match file structure
3. Ensure protoc is installed: `protoc --version`
4. Check logs for detailed compilation output

### Issue: Real Kafka connection fails
**Symptoms**: Connection refused, authentication errors

**Expected Behavior**: In production mode (`mock_mode: false`), connection failures are expected without a real Kafka cluster.

**Solution**:
1. For development: Set `mock_mode: true` in `config/kafka.yaml`
2. For production: Update `config/kafka.yaml` with real Kafka cluster details:
   ```yaml
   bootstrap_servers: "your-kafka-broker:9092"
   sasl_username: "your_username"
   sasl_password: "your_password"
   mock_mode: false
   ```

## 📊 Health Check Endpoints

### Application Health
```bash
curl http://localhost:8001/api/health
# Expected: {"status": "healthy", "timestamp": "...", "traces_count": N}
```

### Component Status
```bash
# Check traces
curl http://localhost:8001/api/traces | jq '.total_traces'

# Check topics
curl http://localhost:8001/api/topics | jq '.all_topics'

# Check statistics
curl http://localhost:8001/api/statistics | jq '.traces.total'
```

## 🔄 Service Management

### Restart Services
```bash
# Restart backend only
sudo supervisorctl restart backend

# Restart frontend only  
sudo supervisorctl restart frontend

# Restart all services
sudo supervisorctl restart all

# Check service status
sudo supervisorctl status
```

### View Logs
```bash
# Backend logs (most recent)
tail -n 50 /var/log/supervisor/backend.*.log

# Frontend logs
tail -n 50 /var/log/supervisor/frontend.*.log

# Follow live logs
tail -f /var/log/supervisor/backend.*.log
```

## 🧪 Testing Configuration

### Test Protobuf Compilation
```bash
cd /app/backend/config/proto
protoc --python_out=/tmp --proto_path=. events/user_events.proto common/base.proto common/address.proto
ls /tmp/*_pb2.py
```

### Test API Endpoints
```bash
# Health check
curl -f http://localhost:8001/api/health

# Get traces (should return valid JSON)
curl -f http://localhost:8001/api/traces | jq .

# Test WebSocket (should connect)
websocat ws://localhost:8001/api/ws
```

## 📝 Development Notes

### Adding New Protobuf Files
1. Place `.proto` files in appropriate subdirectories under `config/proto/`
2. Update `config/topics.yaml` with new topic configuration
3. Ensure all imports use correct relative paths
4. Test compilation manually first
5. Restart backend service

### Protobuf Import Guidelines
- Use relative imports: `import "common/base.proto"`
- Maintain consistent package structure
- Reference types with full package names: `kafka_trace.common.BaseHeader`

### Mock Data Customization
Edit `src/protobuf_decoder.py` in the `MockProtobufDecoder` class to modify generated test data.

## 🚨 Emergency Recovery

### Reset to Working State
```bash
# Switch to mock mode
sed -i 's/mock_mode: false/mock_mode: true/' /app/backend/config/kafka.yaml

# Restart services
sudo supervisorctl restart backend

# Verify health
curl http://localhost:8001/api/health
```

### Clear Generated Files
```bash
# Remove temporary protobuf files (automatic cleanup)
find /tmp -name "*_pb2.py" -delete

# Restart backend to regenerate
sudo supervisorctl restart backend
```

This troubleshooting guide resolves the major issues identified and provides comprehensive debugging support for future problems.