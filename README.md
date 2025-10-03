# Marauder's Map

A real-time web application for visualizing Kafka message traces with gRPC integration, P10/P50/P95 metrics, and interactive topic graphs.

![Status](https://img.shields.io/badge/status-working-brightgreen) ![Backend](https://img.shields.io/badge/backend-FastAPI-blue) ![Frontend](https://img.shields.io/badge/frontend-React-blue) ![gRPC](https://img.shields.io/badge/gRPC-integrated-green)

## 🚀 Quick Start

### Container Environment (Recommended)
If you're in the Emergent platform container:

1. **Backend is already running on port 8001**
2. **Frontend is already running on port 3000**
3. **Access the application:**
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8001`
   - API Documentation: `http://localhost:8001/docs`

### Local Development with run_local.py

**Quick Setup:**
```bash
cd backend
python run_local.py  # Checks requirements and starts server
```

**run_local.py Features:**
- Validates Python 3.11+ and all dependencies
- Checks protoc installation for gRPC features
- Verifies configuration files exist
- Starts server with proper error handling
- Provides detailed setup status with emoji markers

**Manual Setup (if needed):**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify protoc for gRPC
protoc --version

# Start server
python run_local.py
```

## 🎯 Current Features

### Core Functionality
- **Real-time Kafka Message Consumption**: SASL/SCRAM SHA-512 authentication
- **P10/P50/P95 Message Age Metrics**: Millisecond precision across all topics
- **Interactive Graph Visualization**: Larger canvas (800-1200px) with zoom controls
- **gRPC Integration**: Dynamic proto loading, IngressServer & AssetStorageService
- **Trace Correlation**: Configurable trace headers across topics

### gRPC Integration
- **Services**: IngressServer (UpsertContent, BatchCreateAssets, BatchAddDownloadCounts, BatchAddRatings), AssetStorageService (BatchGetSignedUrls, BatchUpdateStatuses)
- **Environment Selection**: DEV, INT, LOAD, PROD, TEST environments
- **Dynamic Proto Loading**: Automatic protobuf compilation and module loading
- **Request Persistence**: Save/load request data with template variables
- **{{rand}} Variables**: Auto-replacement with random values

### User Interface
- **Traces Tab**: Browse traces with P10/P50/P95 age metrics
- **Topics Tab**: Enhanced with colored P10/P50/P95 displays (emerald/amber/red)
- **Graph Tab**: Larger visualization window for 14+ topics
- **gRPC Tab**: Interactive service testing with dynamic method discovery

## 🛠️ Troubleshooting

### Backend Won't Start
```bash
# Use the diagnostic script
cd backend
python run_local.py

# Manual checks
python --version  # Should be 3.11+
protoc --version   # Required for gRPC
ls config/         # Should exist with YAML files
```

### Common Issues

**1. "Configuration directory not found"**
```bash
# Run from backend/ directory
cd backend
python run_local.py
```

**2. "protoc: command not found"**
```bash
# macOS
brew install protobuf

# Ubuntu/Debian
sudo apt-get install protobuf-compiler
```

**3. "No module named 'confluent-kafka'"**
```bash
pip install -r requirements.txt
```

### IDE Setup (IntelliJ/PyCharm)
- **Working Directory**: MUST be `backend/` folder (not project root)
- **Script**: Use `run_local.py` for better error handling
- **Python**: 3.11+ with all dependencies from requirements.txt

## ⚙️ Configuration

### Mock Mode (Default)
```yaml
# config/kafka.yaml
mock_mode: true  # Generates sample data
```

### Real Kafka
```yaml
# config/kafka.yaml
bootstrap_servers: "your-kafka-broker:9092"
security_protocol: "SASL_SSL"
sasl_mechanism: "SCRAM-SHA-512"
sasl_username: "your_username"
sasl_password: "your_password"
mock_mode: false
```

### gRPC Services
Upload proto files to `backend/config/proto/` and configure environments in `backend/config/environments/`.

## 📊 Status

✅ **P10/P50/P95 Metrics**: Working across all topics with millisecond precision  
✅ **Enhanced Graph**: Larger visualization (800-1200px) with improved zoom  
✅ **gRPC Integration**: Full service support with message class resolution  
✅ **Mock Mode**: Generates realistic trace data  
✅ **Real-time Updates**: WebSocket integration  
✅ **API Complete**: All endpoints with proper error handling
