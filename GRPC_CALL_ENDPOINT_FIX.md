# gRPC Call Endpoint Missing - Fix

## Issue
When trying to make gRPC calls from the frontend (e.g., calling `BatchCreateAssets` on `ingress_server`), the API was returning **405 Method Not Allowed**:

```
POST /api/grpc/ingress_server/BatchCreateAssets HTTP/1.1" 405 Method Not Allowed
```

## Root Cause
The backend had endpoints for:
- ✅ `/api/grpc/status` - Get gRPC client status
- ✅ `/api/grpc/environments` - Get available environments
- ✅ `/api/grpc/initialize` - Initialize gRPC client

But was **MISSING** the actual endpoint to make gRPC service calls:
- ❌ `/api/grpc/{service_name}/{method_name}` - Call gRPC methods

## Investigation
Looking at the logs, the gRPC client was successfully:
1. Loading proto files ✅
2. Compiling services ✅
3. Discovering methods ✅
4. Initializing successfully ✅

But when the frontend tried to call a method, there was no endpoint to handle it.

## Solution
Created the missing endpoint to handle dynamic gRPC method calls:

```python
@api_router.post("/grpc/{service_name}/{method_name}")
async def call_grpc_method(service_name: str, method_name: str, request_data: Dict[str, Any]):
    """Call a gRPC service method dynamically"""
    logger.info("="*80)
    logger.info(f"📞 [gRPC CALL] Endpoint HIT!")
    logger.info(f"📞 [gRPC CALL] Service: {service_name}")
    logger.info(f"📞 [gRPC CALL] Method: {method_name}")
    logger.info(f"📞 [gRPC CALL] Request data keys: {list(request_data.keys())}")
    logger.info("="*80)
    
    try:
        # Check if gRPC client is initialized
        if not hasattr(app.state, 'grpc_client') or app.state.grpc_client is None:
            logger.error("❌ gRPC client not initialized")
            return {
                "success": False,
                "error": "gRPC client not initialized. Please initialize first."
            }
        
        # Call the dynamic method
        result = await app.state.grpc_client.call_dynamic_method(
            service_name=service_name,
            method_name=method_name,
            request_data=request_data
        )
        
        logger.info(f"✅ gRPC call completed - Success: {result.get('success', False)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error calling gRPC method: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
```

## How It Works

### 1. URL Pattern
```
POST /api/grpc/{service_name}/{method_name}
```

**Examples**:
- `POST /api/grpc/ingress_server/BatchCreateAssets`
- `POST /api/grpc/ingress_server/UpsertContent`
- `POST /api/grpc/asset_storage/BatchGetSignedUrls`

### 2. Request Body
The request body contains the data for the gRPC request:
```json
{
  "field1": "value1",
  "field2": "value2",
  "nested": {
    "field3": "value3"
  }
}
```

### 3. Processing Flow
1. **Validation**: Check if gRPC client is initialized
2. **Dynamic Call**: Use `grpc_client.call_dynamic_method()` which:
   - Gets the service stub
   - Gets the method from the stub
   - Creates the request message from the data
   - Makes the gRPC call with retry logic
   - Returns the response
3. **Response**: Return success/failure with data or error

### 4. Error Handling
- Client not initialized → Clear error message
- Invalid service → Error from client
- Invalid method → Error from client
- Request validation → Error from client
- Network errors → Handled with retry logic
- All errors logged with full traceback

## Testing Results

### Test 1: Endpoint Registration
```bash
tail backend.err.log | grep grpc
```
**Result**:
```
✅ ['POST'] /api/grpc/{service_name}/{method_name}
```

### Test 2: Endpoint Call (Not Initialized)
```bash
curl -X POST "http://localhost:8001/api/grpc/ingress_server/TestMethod" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```
**Response**:
```json
{
  "success": false,
  "error": "gRPC client not initialized. Please initialize first."
}
```
✅ Proper error handling

### Test 3: Logging
**Logs show**:
```
📞 [gRPC CALL] Endpoint HIT!
📞 [gRPC CALL] Service: ingress_server
📞 [gRPC CALL] Method: TestMethod
📞 [gRPC CALL] Request data keys: ['test']
```
✅ Comprehensive logging for debugging

## Frontend Integration

The frontend can now make calls like:

```javascript
const response = await axios.post(
  `${API_BASE_URL}/api/grpc/ingress_server/BatchCreateAssets`,
  {
    // Request data matching the proto definition
    assets: [...],
    options: {...}
  }
);

if (response.data.success) {
  console.log('gRPC call successful:', response.data.response);
} else {
  console.error('gRPC call failed:', response.data.error);
}
```

## Available Services and Methods

Based on the initialization logs, the following services and methods are available:

### ingress_server
- UpsertContent
- DeleteContent
- BatchCreateAssets ← The method being called
- BatchAddDownloadCounts
- BatchAddRatings

### asset_storage
- BatchGetSignedUrls
- BatchGetUnsignedUrls
- BatchGetEmbargoStatus
- BatchUpdateStatuses
- BatchDeleteAssets
- BatchCreateAssets
- BatchFinalizeAssets

## Benefits

1. **Dynamic**: Automatically works with any service/method from loaded proto files
2. **Type Safe**: Uses proto definitions for validation
3. **Debuggable**: Comprehensive logging at every step
4. **Error Handling**: Clear error messages for all failure cases
5. **Retry Logic**: Built-in retry mechanism for transient failures
6. **Template Support**: Supports template variables like `{{rand}}` in requests

## Files Modified

1. `backend/server.py` - Added `/api/grpc/{service_name}/{method_name}` endpoint

## Usage Flow

1. **Initialize** (one time):
   ```
   POST /api/grpc/initialize
   ```

2. **Make Calls** (as needed):
   ```
   POST /api/grpc/{service}/{method}
   Body: { request data }
   ```

3. **Check Status** (optional):
   ```
   GET /api/grpc/status
   ```

## Notes

- The endpoint uses the existing `GrpcClient.call_dynamic_method()` which has full retry logic, error handling, and response parsing
- No changes needed to frontend - it should already be trying to call this endpoint
- The gRPC client must be initialized before making calls (frontend should do this on component mount)
- All proto definitions are loaded from `backend/config/proto/`
- Environment-specific settings (URLs, credentials) come from `backend/config/environments/{env}.yaml`

## Conclusion

The missing endpoint has been added. gRPC calls from the frontend should now work correctly. The 405 error will be replaced with actual gRPC responses (success or failure based on the actual call).
