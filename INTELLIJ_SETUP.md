# IntelliJ/PyCharm Setup Guide for Kafka Trace Viewer

## 🚨 Your Issue - RESOLVED ✅

**Problem**: Getting `Process finished with exit code 0` when debugging from IntelliJ

**Root Causes Identified & Fixed**:
1. ✅ **FastAPI Deprecation Warnings** - Fixed by converting to lifespan handlers
2. ✅ **Missing protoc compiler** - Install instructions provided
3. ✅ **Wrong working directory** - Must be `backend/` folder
4. ✅ **Poor error messages** - Enhanced with detailed logging and `run_local.py`

## 🛠️ Quick Fix for IntelliJ

### Option 1: Use the Enhanced Startup Script (Recommended)
```bash
cd backend
python run_local.py
```

This script will:
- ✅ Check all system requirements (Python 3.11+, protoc)
- ✅ Verify project structure and dependencies
- ✅ Provide detailed error messages if anything is missing
- ✅ Start the server with comprehensive logging

### Option 2: Configure IntelliJ Properly

**⚠️ IMPORTANT: Handle Port Conflicts**

If you're running in the Emergent container, the supervisor might already be using port 8001. You have two options:

**Option A: Use Different Port**
1. **Script Path**: `backend/run_local.py`
2. **Working Directory**: `backend/`
3. **Parameters**: Add `--port 8002` to use a different port

**Option B: Stop Supervisor Backend** (Container only)
```bash
sudo supervisorctl stop backend
# Then run your script
```

**Run Configuration Settings:**
1. **Script Path**: `backend/run_local.py` (recommended) or `backend/server.py`
2. **Working Directory**: `backend/` ⚠️ **CRITICAL - Must be backend folder, not project root**
3. **Python Interpreter**: Your Python 3.11+ environment
4. **Parameters**: `--port 8002` (if port 8001 is occupied)

**Debug Configuration:**
- Same as above but use Debug instead of Run
- The enhanced logging will show detailed startup information

## 📋 Prerequisites Checklist

### System Requirements
```bash
# Check Python version (need 3.11+)
python --version

# Install protoc (Protocol Buffers compiler)
# macOS:
brew install protobuf

# Ubuntu/Debian:
sudo apt-get install protobuf-compiler

# Verify protoc installation
protoc --version
```

### Python Dependencies
```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Verify key packages
python -c "import confluent_kafka, google.protobuf, yaml; print('✅ All packages installed')"
```

## 🔧 IntelliJ Project Setup

### 1. Open Project
- Open the **entire project folder** (not just backend)
- IntelliJ should detect it as a Python project

### 2. Configure Python Interpreter
- Go to: File → Project Structure → Project Settings → Project
- Set Project SDK to your Python 3.11+ interpreter
- If using virtual environment, point to `venv/bin/python`

### 3. Create Run Configuration
1. Run → Edit Configurations
2. Click "+" → Python
3. Configure:
   - **Name**: "Kafka Trace Viewer"
   - **Script path**: `backend/run_local.py`
   - **Working directory**: `backend/` ⚠️ **MUST BE backend FOLDER**
   - **Python interpreter**: Your configured interpreter
   - **Environment variables**: None needed

### 4. Test the Configuration
- Click Run (or Debug)
- You should see:
  ```
  🚀 Kafka Trace Viewer - Local Development Setup
  ==================================================
  🔍 Checking system requirements...
  ✅ Python 3.11.x
  ✅ libprotoc 3.x.x
  ...
  ✅ All checks passed! Starting Kafka Trace Viewer...
  ```

## 🚨 Troubleshooting IntelliJ Issues

### Issue: "Process finished with exit code 0"
**Cause**: Wrong working directory or missing dependencies

**Solution**:
1. Use `run_local.py` script - it provides detailed error messages
2. Ensure working directory is set to `backend/` folder
3. Check the console output for specific error messages

### Issue: "Configuration directory not found"
**Cause**: Working directory not set to backend folder

**Solution**:
- Set Working Directory to `backend/` in run configuration
- Verify you can see `config/` folder from the working directory

### Issue: "protoc: command not found"
**Cause**: Protocol Buffers compiler not installed

**Solution**:
```bash
# macOS
brew install protobuf

# Ubuntu/Debian  
sudo apt-get install protobuf-compiler

# Verify
protoc --version
```

### Issue: Import errors or missing modules
**Cause**: Dependencies not installed in the Python environment

**Solution**:
```bash
cd backend
pip install -r requirements.txt

# Test key imports
python -c "import confluent_kafka, fastapi, yaml"
```

### Issue: FastAPI deprecation warnings
**Status**: ✅ **FIXED** - Converted to modern lifespan handlers

These warnings were causing confusion but are now resolved.

## 🧪 Testing Your Setup

### Quick Verification Script
```bash
cd backend
python -c "
import sys, os, subprocess
print('🐍 Python version:', sys.version.split()[0])
print('📁 Working directory:', os.getcwd())
print('📂 Config exists:', os.path.exists('config'))
print('📂 Proto exists:', os.path.exists('config/proto'))

# Test protoc
try:
    result = subprocess.run(['protoc', '--version'], capture_output=True, text=True)
    print('⚙️  Protoc:', result.stdout.strip() if result.returncode == 0 else '❌ NOT FOUND')
except:
    print('⚙️  Protoc: ❌ NOT FOUND')

# Test key imports
try:
    import confluent_kafka, fastapi, yaml
    print('📦 Dependencies: ✅ OK')
except ImportError as e:
    print('📦 Dependencies: ❌', str(e))
"
```

### Start Server and Test
```bash
cd backend
python run_local.py
```

Then in another terminal:
```bash
# Test API
curl http://localhost:8001/api/health

# Expected response:
# {"status": "healthy", "timestamp": "...", "traces_count": N}
```

## 📚 Additional Resources

- **Full Setup Guide**: See main `README.md`
- **Troubleshooting**: See `TROUBLESHOOTING.md`
- **API Documentation**: http://localhost:8001/docs (when server is running)

## 🎯 Summary

The key issues have been resolved:
1. ✅ **FastAPI deprecation warnings fixed**
2. ✅ **Enhanced error handling and logging**
3. ✅ **Better setup validation with `run_local.py`**
4. ✅ **Clear working directory requirements**
5. ✅ **Comprehensive dependency checking**

Your IntelliJ debugging should now work perfectly! 🎉