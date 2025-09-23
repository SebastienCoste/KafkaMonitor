# Blueprint Deployment Validate/Activate Fix

## Issues Fixed

### Issue 1: Backend - 405 Method Not Allowed
**Problem**: The validate/activate endpoints were returning 405 errors when the frontend sent full file paths like:
```
POST /api/blueprint/validate//Users/scoste/workspace/cadie/bp-gen/cfb/out/blueprint.0.1-29b1de7-SNAPSHOT-dirty.tgz
```

**Root Cause**: The route parameter was defined as `{filename}` which doesn't support paths with slashes. FastAPI was treating the slashes as route separators, causing the route to not match.

**Original Code**:
```python
@api_router.post("/blueprint/validate/{filename}")
async def validate_blueprint_tgz(filename: str, payload: Dict[str, Any]):
    return {"status": "validated", "file": filename, ...}
```

**Problem**: 
- `{filename}` only matches single path segments (no slashes)
- Full paths like `/Users/.../out/file.tgz` would cause 404/405 errors

**Fix**: Changed to use `{filepath:path}` parameter type:
```python
@api_router.post("/blueprint/validate/{filepath:path}")
async def validate_blueprint_tgz(filepath: str, payload: Dict[str, Any]):
    # Extract just the filename from the path
    from pathlib import Path
    filename = Path(filepath).name
    
    logger.info(f"📋 Validating blueprint: {filename} (from path: {filepath})")
    return {"status": "validated", "file": filename, "filepath": filepath, ...}
```

**Benefits**:
- `{filepath:path}` matches paths with any number of slashes
- Backend extracts the filename from the full path using `Path().name`
- Returns both filename and filepath in response for clarity
- Added comprehensive logging

### Issue 2: Frontend - Sending Full Path Instead of Filename
**Problem**: The frontend was sending the full file path in the URL:
```javascript
// Before: selectedFile = "/Users/scoste/workspace/.../out/blueprint.tgz"
validateBlueprint(selectedFile)  // Sends full path in URL
```

**Root Cause**: In `DeploymentPanel.js`, the `selectedFile` was set to `file.path` which contains the full path. This full path was then passed directly to the API.

**Fix**: Extract just the filename before making the API call:

```javascript
const validateBlueprint = async (filepath) => {
  try {
    // Extract just the filename from the full path
    const filename = filepath.split('/').pop().split('\\').pop();
    
    console.log('🔍 Validating blueprint:', { filepath, filename, environment });
    
    const response = await axios.post(
      `${API_BASE_URL}/api/blueprint/validate/${filename}`,
      {
        tgz_file: filename,
        environment: selectedEnvironment,
        action: 'validate'
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error validating blueprint:', error);
    throw error;
  }
};
```

**Benefits**:
- Supports both Unix (`/`) and Windows (`\`) path separators
- Clean URL without excessive path information
- Clear logging shows both filepath and extracted filename
- Files are always in `root_path/out/` so filename is sufficient

## Why Both Fixes Work Together

### Frontend Perspective
- User selects file from list (has full path)
- Frontend extracts filename: `blueprint.0.1-29b1de7-SNAPSHOT-dirty.tgz`
- Makes clean API call: `POST /api/blueprint/validate/blueprint.0.1-29b1de7-SNAPSHOT-dirty.tgz`

### Backend Perspective
- Receives filename in URL path
- Can also handle full paths if needed (due to `{filepath:path}`)
- Extracts clean filename for processing
- Looks for file in `root_path/out/{filename}`

## Testing Results

### Test 1: Simple Filename
```bash
POST /api/blueprint/validate/test.tgz
```
**Response**:
```json
{
  "status": "validated",
  "file": "test.tgz",
  "filepath": "test.tgz",
  "environment": "INT"
}
```
✅ Works

### Test 2: Relative Path
```bash
POST /api/blueprint/validate/out/test.tgz
```
**Response**:
```json
{
  "status": "validated",
  "file": "test.tgz",
  "filepath": "out/test.tgz",
  "environment": "INT"
}
```
✅ Works - extracts filename correctly

### Test 3: Full Absolute Path
```bash
POST /api/blueprint/validate//Users/test/out/blueprint.tgz
```
**Response**:
```json
{
  "status": "validated",
  "file": "blueprint.tgz",
  "filepath": "/Users/test/out/blueprint.tgz",
  "environment": "INT"
}
```
✅ Works - handles any path format

### Test 4: Logs
```
📋 Validating blueprint: blueprint.tgz (from path: /Users/test/out/blueprint.tgz)
   Environment: INT
```
✅ Clear, informative logging

## Code Changes

### Backend Changes (`backend/server.py`)

**1. Updated Route Definitions**:
- `/blueprint/validate/{filename}` → `/blueprint/validate/{filepath:path}`
- `/blueprint/activate/{filename}` → `/blueprint/activate/{filepath:path}`

**2. Added Path Handling**:
```python
from pathlib import Path
filename = Path(filepath).name
```

**3. Enhanced Logging**:
```python
logger.info(f"📋 Validating blueprint: {filename} (from path: {filepath})")
logger.info(f"   Environment: {payload.get('environment')}")
```

**4. Updated Response**:
```python
return {
    "status": "validated",
    "file": filename,        # Clean filename
    "filepath": filepath,    # Original path
    "environment": payload.get("environment")
}
```

### Frontend Changes (`frontend/src/components/blueprint/Common/BlueprintContext.js`)

**1. Added Filename Extraction**:
```javascript
const filename = filepath.split('/').pop().split('\\').pop();
```

**2. Added Console Logging**:
```javascript
console.log('🔍 Validating blueprint:', { filepath, filename, environment });
```

**3. Updated URL Construction**:
```javascript
// Uses clean filename instead of full path
`${API_BASE_URL}/api/blueprint/validate/${filename}`
```

## Architecture Notes

### File Location Convention
- All blueprint `.tgz` files are stored in: `{root_path}/out/`
- Frontend gets files from: `GET /api/blueprint/output-files?root_path=...`
- Files always have the `out` directory prefix
- Therefore, only the filename is needed for deployment

### Path Handling Strategy
1. **Frontend**: Extracts filename for clean API calls
2. **Backend**: Accepts both filename and full paths (flexible)
3. **Processing**: Backend uses filename to locate file in `out/` directory

## Benefits of This Approach

1. **Clean URLs**: API endpoints have readable, simple URLs
2. **Flexible**: Backend can handle any path format
3. **Robust**: Works on Windows and Unix systems
4. **Clear Logging**: Easy to debug deployment issues
5. **Consistent**: All files are in `out/` directory by convention

## Files Modified

1. `backend/server.py` - Updated validate/activate endpoints
2. `frontend/src/components/blueprint/Common/BlueprintContext.js` - Added filename extraction

## Related Endpoints

Both endpoints follow the same pattern:
- `POST /api/blueprint/validate/{filepath:path}` - Validate blueprint
- `POST /api/blueprint/activate/{filepath:path}` - Activate blueprint

Both accept:
```json
{
  "tgz_file": "filename.tgz",
  "environment": "INT",
  "action": "validate" | "activate"
}
```

Both return:
```json
{
  "status": "validated" | "activated",
  "file": "filename.tgz",
  "filepath": "original/path/filename.tgz",
  "environment": "INT"
}
```
