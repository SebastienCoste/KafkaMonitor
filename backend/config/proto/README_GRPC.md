# Proto Files Management

**IMPORTANT**: Proto files are NOT committed to this repository. They must be provided by users at runtime.

## Directory Structure

Place your proto files in this directory following this structure:

```
/app/backend/config/protos/
├── ingress_server/
│   ├── ingress_server.proto          # Main service definition
│   └── common/                       # Common message types
│       ├── types.proto
│       └── errors.proto
├── asset_storage/
│   ├── asset_storage.proto           # Main service definition
│   └── common/                       # Common message types
│       ├── asset_types.proto
│       └── metadata.proto
└── common/                           # Shared common types
    ├── base.proto
    └── timestamps.proto
```

## Required Services

### IngressServer Service
- **Service Name**: `IngressServer`
- **Proto File**: `ingress_server/ingress_server.proto`
- **Required Methods**:
  - `UpsertContent(UpsertContentRequest) returns (UpsertContentResponse)`
  - `BatchCreateAssets(BatchCreateAssetsRequest) returns (BatchCreateAssetsResponse)`
  - `BatchAddDownloadCounts(BatchAddDownloadCountsRequest) returns (BatchAddDownloadCountsResponse)`
  - `BatchAddRatings(BatchAddRatingsRequest) returns (BatchAddRatingsResponse)`

### AssetStorageService Service
- **Service Name**: `AssetStorageService`
- **Proto File**: `asset_storage/asset_storage.proto`
- **Required Methods**:
  - `BatchGetSignedUrls(BatchGetSignedUrlsRequest) returns (BatchGetSignedUrlsResponse)`
  - `BatchUpdateStatuses(BatchUpdateStatusesRequest) returns (BatchUpdateStatusesResponse)`

## Loading Process

1. **User Responsibility**: Users must place the required proto files in the appropriate directories
2. **Runtime Compilation**: Proto files are compiled to Python modules at runtime
3. **Validation**: The system validates that all required services and methods are available
4. **Error Handling**: Clear error messages are provided if proto files are missing or invalid

## Security Notes

- Proto files may contain sensitive service definitions
- Never commit proto files to version control
- Proto files are loaded from local filesystem only
- No network fetching of proto definitions

## Environment Setup

Each environment (DEV/TEST/INT/LOAD/PROD) may require different proto file versions. Ensure you have the correct proto files for your target environment.

## Troubleshooting

### Common Issues:

1. **Proto files not found**: Ensure files are placed in correct directory structure
2. **Import errors**: Check that all imported proto files are present
3. **Compilation errors**: Verify proto syntax and dependencies
4. **Service not found**: Ensure service names match exactly

### Debug Mode:

Set `GRPC_DEBUG=true` in environment to enable detailed proto loading logs.