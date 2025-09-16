# Proto Files Management

**MERGED STRUCTURE**: Proto files for both Kafka and gRPC services are now in the unified `/app/backend/config/proto/` directory.

## Directory Structure

The proto directory now contains both Kafka protobuf files and gRPC service definitions:

```
/app/backend/config/proto/
├── grpc/                             # gRPC service proto files
│   ├── common/                       # Common gRPC types
│   │   ├── base.proto                # Base response types
│   │   └── types.proto               # Common data types
│   ├── ingress_server/
│   │   └── ingress_server.proto      # IngressServer service definition
│   └── asset_storage/
│       └── asset_storage.proto       # AssetStorageService service definition
├── common/                           # Kafka common types
│   ├── address.proto
│   └── base.proto
├── events/                           # Kafka event types
│   └── user_events.proto
├── processing/                       # Kafka processing types
│   └── processed_events.proto
├── analytics.proto                   # Kafka analytics events
├── event.proto                       # Kafka events
├── notifications.proto               # Kafka notifications
├── process_event.proto               # Kafka process events
├── processed_events.proto            # Kafka processed events
└── user_events.proto                 # Kafka user events
```

## gRPC Services (Now Committed)

### IngressServer Service
- **Service Name**: `IngressServer`
- **Proto File**: `grpc/ingress_server/ingress_server.proto`
- **Required Methods**:
  - `UpsertContent(UpsertContentRequest) returns (UpsertContentResponse)`
  - `BatchCreateAssets(BatchCreateAssetsRequest) returns (BatchCreateAssetsResponse)`
  - `BatchAddDownloadCounts(BatchAddDownloadCountsRequest) returns (BatchAddDownloadCountsResponse)`
  - `BatchAddRatings(BatchAddRatingsRequest) returns (BatchAddRatingsResponse)`

### AssetStorageService Service
- **Service Name**: `AssetStorageService`
- **Proto File**: `grpc/asset_storage/asset_storage.proto`
- **Required Methods**:
  - `BatchGetSignedUrls(BatchGetSignedUrlsRequest) returns (BatchGetSignedUrlsResponse)`
  - `BatchUpdateStatuses(BatchUpdateStatusesRequest) returns (BatchUpdateStatusesResponse)`

## Loading Process

1. **Unified Directory**: Both Kafka and gRPC proto files are now in the same directory tree
2. **Runtime Compilation**: All proto files are compiled to Python modules at runtime
3. **Automatic Detection**: The system automatically detects and validates gRPC service definitions
4. **Improved Error Handling**: Clear error messages for missing or invalid proto files

## Key Changes

- ✅ **Proto files are now committed** to the repository (as requested)
- ✅ **Unified directory structure** under `/config/proto/`
- ✅ **Complete gRPC service definitions** with all required methods
- ✅ **Common types shared** between services
- ✅ **Proper protobuf structure** with imports and packages

## Environment Setup

Each environment (DEV/TEST/INT/LOAD/PROD) uses the same committed proto files. The gRPC client dynamically compiles these at runtime.

## Troubleshooting

### Common Issues:

1. **Import errors**: All proto files now use proper import paths (e.g., `grpc/common/base.proto`)
2. **Service compilation**: The system validates that all required services and methods are available
3. **Directory structure**: Ensure the proto directory structure matches the documented layout

### Debug Mode:

Set `GRPC_DEBUG=true` in environment to enable detailed proto loading logs.