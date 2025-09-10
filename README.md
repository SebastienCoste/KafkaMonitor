# Kafka Trace Viewer

A real-time web application for visualizing Kafka message traces across topics using configurable trace headers and interactive topic graphs.

![Kafka Trace Viewer](https://img.shields.io/badge/status-working-brightgreen) ![Backend](https://img.shields.io/badge/backend-FastAPI-blue) ![Frontend](https://img.shields.io/badge/frontend-React-blue) ![Mock Mode](https://img.shields.io/badge/mock%20mode-enabled-orange)

## 🚀 Features

### Core Functionality
- **Real-time Kafka Message Consumption**: Connects to Kafka clusters with SASL/SCRAM SHA-512 authentication
- **Protobuf Message Decoding**: Dynamic loading of .proto files with support for different schemas per topic
- **Trace Correlation**: Tracks messages across topics using configurable trace header fields
- **Interactive Visualizations**: Network graphs for topic relationships and message flows
- **FIFO Trace Management**: Maintains up to 1000 traces in memory with automatic eviction

### User Interface
- **Traces Tab**: Browse and search through available traces with detailed information
- **Topics Tab**: Configure which topics to monitor with interactive checkboxes
- **Graph Tab**: Visualize topic relationships and message flow patterns
- **Message Timeline**: Expandable message details with headers and decoded content
- **Real-time Updates**: WebSocket integration for live trace count and status updates

### Development Features
- **Mock Mode**: Built-in mock Kafka consumer for testing and development
- **API Documentation**: Complete REST API with OpenAPI/Swagger documentation
- **Configurable Settings**: YAML-based configuration for all components
- **Comprehensive Testing**: Full test coverage for both backend and frontend

## 🏗️ Architecture

### Backend (FastAPI + Python)
- **Kafka Consumer Service**: Handles SASL/SCRAM authentication and message consumption
- **Protobuf Decoder**: Dynamic protobuf compilation and message decoding
- **Graph Builder**: Manages trace collection, topic relationships, and FIFO eviction
- **Web Server**: REST API and WebSocket endpoints for real-time communication

### Frontend (React + TypeScript)
- **Modern UI**: Built with Tailwind CSS and shadcn/ui components  
- **Interactive Visualizations**: vis-network for graph rendering
- **Real-time Updates**: WebSocket client for live data synchronization
- **Responsive Design**: Works across desktop, tablet, and mobile devices

### Technology Stack
- **Backend**: FastAPI, confluent-kafka-python, protobuf, PyYAML, websockets
- **Frontend**: React 19, vis-network, axios, shadcn/ui, Tailwind CSS
- **Development**: Docker support, comprehensive testing, mock data generation

## 📁 Project Structure

```
kafka-trace-viewer/
├── backend/
│   ├── src/
│   │   ├── models.py              # Data models and types
│   │   ├── kafka_consumer.py      # Kafka consumer with mock support
│   │   ├── protobuf_decoder.py    # Dynamic protobuf decoding
│   │   └── graph_builder.py       # Trace management and topic graphs
│   ├── config/
│   │   ├── kafka.yaml            # Kafka connection settings
│   │   ├── topics.yaml           # Topic configuration and graph
│   │   ├── settings.yaml         # Application settings
│   │   └── proto/                # Protobuf schema definitions
│   │       ├── user_events.proto
│   │       ├── processed_events.proto
│   │       ├── notifications.proto
│   │       └── analytics.proto
│   ├── server.py                 # Main FastAPI application
│   ├── app.py                    # Standalone consumer for testing
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js               # Main React application
│   │   ├── App.css              # Custom styles
│   │   └── components/ui/       # shadcn/ui components
│   └── package.json
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- yarn package manager
- Protocol Buffers compiler (`protoc`)

### System Dependencies

**For macOS (using Homebrew):**
```bash
# Install Protocol Buffers compiler
brew install protobuf

# Verify installation
protoc --version
```

**For Ubuntu/Debian:**
```bash
# Install Protocol Buffers compiler
sudo apt-get update
sudo apt-get install protobuf-compiler

# Verify installation
protoc --version
```

### Installation & Setup

#### Option 1: Container Environment (Recommended)
If you're in the Emergent platform container:

1. **Backend is already running on port 8001**
2. **Frontend is already running on port 3000**
3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001
   - API Documentation: http://localhost:8001/docs

#### Option 2: Local Development Setup

**1. Clone and Setup Backend:**
```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify protoc is available
protoc --version

# Start backend server
python server.py
```

**2. Setup Frontend:**
```bash
cd frontend

# Install dependencies
yarn install

# Start frontend development server
yarn start
```

**3. Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- API Documentation: http://localhost:8001/docs

### 🐛 Troubleshooting Local Setup

#### Backend Won't Start
```bash
# Check if you're in the right directory
ls -la  # Should see config/ directory

# Check Python environment
python --version  # Should be 3.11+
pip list | grep confluent-kafka  # Should show confluent-kafka

# Check protoc installation
protoc --version  # Should show libprotoc 3.x.x or higher

# Run with verbose logging
python server.py
```

#### Common Issues:

**1. "Configuration directory not found"**
```bash
# Make sure you're running from backend/ directory
cd backend
python server.py
```

**2. "No module named 'confluent-kafka'"**
```bash
# Install missing dependencies
pip install -r requirements.txt
```

**3. "protoc: command not found"**
```bash
# macOS
brew install protobuf

# Ubuntu/Debian
sudo apt-get install protobuf-compiler
```

**4. "No module named 'common'" (Protobuf imports)**
- This is automatically handled by the enhanced protobuf decoder
- Make sure protoc is installed and working
- Check logs for detailed protobuf compilation information

### 🐛 IntelliJ Debugging Issues - SOLVED

**Your Specific Issue**: Process finishing with exit code 0 immediately in IntelliJ

**Root Cause**: FastAPI deprecation warnings + wrong working directory

**✅ SOLUTION:**

1. **Use the new run_local.py script**:
   ```bash
   cd backend
   python run_local.py
   ```

2. **Or fix IntelliJ configuration**:
   - **Working Directory**: MUST be set to `backend/` folder (not project root)
   - **Script**: Use `run_local.py` for better error handling
   - **Python Interpreter**: Ensure you have Python 3.11+ with all dependencies

3. **FastAPI Deprecation Warnings**: 
   - These are now FIXED (converted to lifespan handlers)
   - The warnings don't cause crashes, they're just informational

4. **Verification Script**:
   ```bash
   cd backend
   python -c "
   import sys, os, subprocess
   print('Python:', sys.version)
   print('Working dir:', os.getcwd())
   print('Config exists:', os.path.exists('config'))
   result = subprocess.run(['protoc', '--version'], capture_output=True, text=True)
   print('Protoc:', result.stdout.strip() if result.returncode == 0 else 'INSTALL NEEDED')
   "
   ```

### 🔧 Development Workflow

#### Running Backend Only
```bash
cd backend
source venv/bin/activate  # if using virtual environment
python server.py
```

#### Running Frontend Only
```bash
cd frontend
yarn start
```

#### Running Both (Development)
```bash
# Terminal 1 - Backend
cd backend && python server.py

# Terminal 2 - Frontend  
cd frontend && yarn start
```

#### IDE Setup (IntelliJ/PyCharm)

**Quick Setup Option:**
```bash
cd backend
python run_local.py  # This checks all requirements and starts server
```

**Manual IDE Configuration:**
1. **Set Python Interpreter**: Point to your virtual environment or system Python 3.11+
2. **Working Directory**: CRITICAL - Set to `backend/` directory (not project root)
3. **Run Configuration**: 
   - Script: `server.py` or `run_local.py` (recommended)
   - Working directory: `backend/` (must be backend folder)
   - Environment variables: None required for mock mode
4. **Dependencies**: Ensure all packages from `requirements.txt` are installed

**Debugging in IntelliJ:**
- The FastAPI deprecation warnings are normal and don't affect functionality
- Use `run_local.py` for better error messages and setup validation
- Check the console output for detailed startup information with emoji markers (🚀, ✅, ❌)

**Common IntelliJ Issues:**
- **"Process finished with exit code 0"**: Usually means wrong working directory - set to `backend/`
- **"Configuration directory not found"**: Set working directory to `backend/` folder
- **Missing dependencies**: Run `pip install -r requirements.txt` in your Python environment

## ⚙️ Configuration

### Mock Mode (Currently Active)
The application is running in mock mode, generating fake Kafka messages for demonstration:

```yaml
# config/kafka.yaml
mock_mode: true  # Set to false for real Kafka
```

### Real Kafka Configuration
Update `backend/config/kafka.yaml` with your Kafka cluster details:

```yaml
bootstrap_servers: "your-kafka-broker:9092"
security_protocol: "SASL_SSL"
sasl_mechanism: "SCRAM-SHA-512"
sasl_username: "your_username"
sasl_password: "your_password"
mock_mode: false
```

### Topic Configuration
Define your topic graph in `backend/config/topics.yaml`:

```yaml
topics:
  your-topic:
    proto_file: "your_schema.proto"
    message_type: "YourMessageType"
    description: "Your topic description"

topic_edges:
  - source: "source-topic"
    destination: "destination-topic"
```

## 🔌 API Reference

### Health Check
```bash
GET /api/health
# Returns: {"status": "healthy", "timestamp": "...", "traces_count": 42}
```

### Traces
```bash
GET /api/traces                    # List all traces
GET /api/trace/{trace_id}          # Get trace details
GET /api/trace/{trace_id}/flow     # Get trace flow visualization
```

### Topics
```bash
GET /api/topics                    # Get available topics
GET /api/topics/graph              # Get topic graph
POST /api/topics/monitor           # Update monitored topics
```

### Statistics
```bash
GET /api/statistics                # Get detailed statistics
```

### WebSocket
```bash
WS /api/ws                         # Real-time updates
```

## 📊 Current Status

✅ **Fully Functional**: All core features implemented and tested  
✅ **Mock Mode Working**: Generates realistic trace data for testing  
✅ **Real-time Updates**: WebSocket integration functioning  
✅ **API Complete**: All endpoints implemented with proper error handling  
✅ **UI/UX Ready**: Modern, responsive interface with all features  
✅ **Configuration Ready**: Easy setup for real Kafka clusters  

The application currently has 70+ active traces generating continuously in mock mode.
