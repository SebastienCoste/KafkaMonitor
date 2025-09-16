import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

// Shadcn UI components
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Alert, AlertDescription } from './ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { Checkbox } from './ui/checkbox';
import { toast } from 'sonner';

// Icons
import { 
  Settings, 
  Server, 
  Upload, 
  Download, 
  Star, 
  Image, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle,
  Eye,
  EyeOff
} from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function GrpcIntegration() {
  // State management
  const [grpcStatus, setGrpcStatus] = useState(null);
  const [environments, setEnvironments] = useState([]);
  const [currentEnvironment, setCurrentEnvironment] = useState('');
  const [credentials, setCredentials] = useState({
    authorization: '',
    x_pop_token: ''
  });
  const [showCredentials, setShowCredentials] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initialized, setInitialized] = useState(false);

  // Form states for different operations
  const [upsertContentForm, setUpsertContentForm] = useState({
    content_data: '{\n  "title": "Sample Content",\n  "description": "Test content for upsert"\n}',
    random_field: ''
  });

  const [batchCreateAssetsForm, setBatchCreateAssetsForm] = useState({
    assets_data: '[\n  {\n    "name": "asset1.jpg",\n    "type": "image"\n  }\n]'
  });

  const [downloadCountsForm, setDownloadCountsForm] = useState({
    player_id: '',
    content_ids: ''
  });

  const [ratingsForm, setRatingsForm] = useState({
    rating_data: '{\n  "content_id": "test-content-123",\n  "rating": 5\n}'
  });

  const [signedUrlsForm, setSignedUrlsForm] = useState({
    asset_ids: ''
  });

  const [updateStatusesForm, setUpdateStatusesForm] = useState({
    asset_updates: '[\n  {\n    "asset_id": "asset-123",\n    "status": "ACTIVE"\n  }\n]'
  });

  // Results and uploads
  const [results, setResults] = useState({});
  const [uploadUrls, setUploadUrls] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState({});
  const [imageUrls, setImageUrls] = useState([]);
  
  // Asset-storage URL management
  const [assetStorageUrls, setAssetStorageUrls] = useState({});
  const [selectedAssetUrlType, setSelectedAssetUrlType] = useState('reader');

  // Load initial data
  useEffect(() => {
    loadGrpcStatus();
    loadEnvironments();
  }, []);

  const loadGrpcStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/grpc/status`);
      setGrpcStatus(response.data);
      setInitialized(response.data.initialized);
    } catch (error) {
      console.error('Error loading gRPC status:', error);
    }
  };

  const loadEnvironments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/grpc/environments`);
      setEnvironments(response.data.environments);
    } catch (error) {
      console.error('Error loading environments:', error);
      toast.error('Failed to load environments');
    }
  };

  const initializeGrpc = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/grpc/initialize`);
      
      if (response.data.success) {
        toast.success('gRPC client initialized successfully');
        setInitialized(true);
        loadGrpcStatus();
      } else {
        toast.error(`Initialization failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error initializing gRPC:', error);
      toast.error('Failed to initialize gRPC client');
    } finally {
      setLoading(false);
    }
  };

  const setEnvironment = async (environment) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/grpc/environment`, {
        environment
      });
      
      if (response.data.success) {
        setCurrentEnvironment(environment);
        toast.success(`Environment set to ${environment}`);
        // Reset credentials when environment changes
        setCredentials({ authorization: '', x_pop_token: '' });
        // Clear all results and state
        setResults({});
        setUploadUrls([]);
        setImageUrls([]);
        loadGrpcStatus();
        loadAssetStorageUrls();
      } else {
        toast.error(`Failed to set environment: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error setting environment:', error);
      toast.error('Failed to set environment');
    } finally {
      setLoading(false);
    }
  };

  const setGrpcCredentials = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/grpc/credentials`, credentials);
      
      if (response.data.success) {
        toast.success('Credentials set successfully');
        loadGrpcStatus();
      } else {
        toast.error(`Failed to set credentials: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error setting credentials:', error);
      toast.error('Failed to set credentials');
    }
  };

  const loadAssetStorageUrls = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/grpc/asset-storage/urls`);
      
      if (response.data.success) {
        setAssetStorageUrls(response.data.urls);
        setSelectedAssetUrlType(response.data.current_selection);
      }
    } catch (error) {
      console.error('Error loading asset-storage URLs:', error);
    }
  };

  const setAssetStorageUrl = async (urlType) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/grpc/asset-storage/set-url`, {
        url_type: urlType
      });
      
      if (response.data.success) {
        setSelectedAssetUrlType(urlType);
        toast.success(`Asset-storage URL set to ${urlType}`);
        loadGrpcStatus(); // Refresh status
      } else {
        toast.error(`Failed to set asset-storage URL: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error setting asset-storage URL:', error);
      toast.error('Failed to set asset-storage URL');
    }
  };
  // gRPC method calls
  const callUpsertContent = async () => {
    setLoading(true);
    try {
      const contentData = JSON.parse(upsertContentForm.content_data);
      const response = await axios.post(`${API_BASE_URL}/api/grpc/ingress/upsert-content`, {
        content_data: contentData,
        random_field: upsertContentForm.random_field || null
      });

      setResults(prev => ({ ...prev, upsertContent: response.data }));
      
      if (response.data.success) {
        toast.success(`Content upserted successfully! ID: ${response.data.id}`);
      } else {
        toast.error(`UpsertContent failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error calling UpsertContent:', error);
      toast.error('Failed to call UpsertContent');
      setResults(prev => ({ ...prev, upsertContent: { success: false, error: error.message } }));
    } finally {
      setLoading(false);
    }
  };

  const callBatchCreateAssets = async () => {
    setLoading(true);
    try {
      const assetsData = JSON.parse(batchCreateAssetsForm.assets_data);
      const response = await axios.post(`${API_BASE_URL}/api/grpc/ingress/batch-create-assets`, {
        assets_data: assetsData
      });

      setResults(prev => ({ ...prev, batchCreateAssets: response.data }));
      
      if (response.data.success && response.data.upload_urls) {
        setUploadUrls(response.data.upload_urls);
        toast.success(`Assets created! ${response.data.upload_urls.length} upload URLs generated`);
      } else {
        toast.error(`BatchCreateAssets failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error calling BatchCreateAssets:', error);
      toast.error('Failed to call BatchCreateAssets');
      setResults(prev => ({ ...prev, batchCreateAssets: { success: false, error: error.message } }));
    } finally {
      setLoading(false);
    }
  };

  const callBatchAddDownloadCounts = async () => {
    setLoading(true);
    try {
      const contentIds = downloadCountsForm.content_ids.split(',').map(id => id.trim()).filter(Boolean);
      const response = await axios.post(`${API_BASE_URL}/api/grpc/ingress/batch-add-download-counts`, {
        player_id: downloadCountsForm.player_id,
        content_ids: contentIds
      });

      setResults(prev => ({ ...prev, batchAddDownloadCounts: response.data }));
      
      if (response.data.success) {
        toast.success(`Download counts added for ${contentIds.length} content items`);
      } else {
        toast.error(`BatchAddDownloadCounts failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error calling BatchAddDownloadCounts:', error);
      toast.error('Failed to call BatchAddDownloadCounts');
      setResults(prev => ({ ...prev, batchAddDownloadCounts: { success: false, error: error.message } }));
    } finally {
      setLoading(false);
    }
  };

  const callBatchAddRatings = async () => {
    setLoading(true);
    try {
      const ratingData = JSON.parse(ratingsForm.rating_data);
      const response = await axios.post(`${API_BASE_URL}/api/grpc/ingress/batch-add-ratings`, {
        rating_data: ratingData
      });

      setResults(prev => ({ ...prev, batchAddRatings: response.data }));
      
      if (response.data.success) {
        toast.success('Rating added successfully');
      } else {
        toast.error(`BatchAddRatings failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error calling BatchAddRatings:', error);
      toast.error('Failed to call BatchAddRatings');
      setResults(prev => ({ ...prev, batchAddRatings: { success: false, error: error.message } }));
    } finally {
      setLoading(false);
    }
  };

  const callBatchGetSignedUrls = async () => {
    setLoading(true);
    try {
      const assetIds = signedUrlsForm.asset_ids.split(',').map(id => id.trim()).filter(Boolean);
      const response = await axios.post(`${API_BASE_URL}/api/grpc/asset-storage/batch-get-signed-urls`, {
        asset_ids: assetIds
      });

      setResults(prev => ({ ...prev, batchGetSignedUrls: response.data }));
      
      if (response.data.success && response.data.signed_urls) {
        setImageUrls(response.data.signed_urls);
        toast.success(`Retrieved ${response.data.signed_urls.length} signed URLs`);
      } else {
        toast.error(`BatchGetSignedUrls failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error calling BatchGetSignedUrls:', error);
      toast.error('Failed to call BatchGetSignedUrls');
      setResults(prev => ({ ...prev, batchGetSignedUrls: { success: false, error: error.message } }));
    } finally {
      setLoading(false);
    }
  };

  const callBatchUpdateStatuses = async () => {
    setLoading(true);
    try {
      const assetUpdates = JSON.parse(updateStatusesForm.asset_updates);
      const response = await axios.post(`${API_BASE_URL}/api/grpc/asset-storage/batch-update-statuses`, {
        asset_updates: assetUpdates
      });

      setResults(prev => ({ ...prev, batchUpdateStatuses: response.data }));
      
      if (response.data.success) {
        toast.success(`Updated statuses for ${assetUpdates.length} assets`);
      } else {
        toast.error(`BatchUpdateStatuses failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error('Error calling BatchUpdateStatuses:', error);
      toast.error('Failed to call BatchUpdateStatuses');
      setResults(prev => ({ ...prev, batchUpdateStatuses: { success: false, error: error.message } }));
    } finally {
      setLoading(false);
    }
  };

  // File upload handling
  const handleFileSelect = (assetId, file) => {
    setSelectedFiles(prev => ({
      ...prev,
      [assetId]: file
    }));
  };

  const uploadFile = async (uploadUrl, assetId) => {
    const file = selectedFiles[assetId];
    if (!file) {
      toast.error('No file selected');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      // Direct upload to signed URL
      const response = await fetch(uploadUrl, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type
        }
      });

      if (response.ok) {
        toast.success(`File uploaded successfully for asset ${assetId}`);
      } else {
        toast.error(`Upload failed for asset ${assetId}: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      toast.error(`Upload failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const renderResult = (key, result) => {
    if (!result) return null;

    return (
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            {result.success ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-red-500" />
            )}
            <span>{key} Result</span>
            {result.retry_count !== undefined && (
              <Badge variant="secondary">
                {result.retry_count} retries
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="bg-gray-50 p-3 rounded text-sm overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </CardContent>
      </Card>
    );
  };

  if (!initialized) {
    return (
      <div className="p-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Server className="h-6 w-6" />
              <span>gRPC Integration Setup</span>
            </CardTitle>
            <CardDescription>
              Initialize the gRPC client to start making service calls
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Proto files must be placed in <code>/backend/config/protos/</code> directory before initialization.
                See the README for detailed instructions.
              </AlertDescription>
            </Alert>
            
            <Button onClick={initializeGrpc} disabled={loading}>
              {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              Initialize gRPC Client
            </Button>
            
            {grpcStatus && (
              <div className="mt-4">
                <h4 className="font-medium mb-2">Current Status:</h4>
                <pre className="bg-gray-50 p-3 rounded text-sm">
                  {JSON.stringify(grpcStatus, null, 2)}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Environment and Credentials */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Settings className="h-6 w-6" />
            <span>Environment & Authentication</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <Label>Environment</Label>
              <Select value={currentEnvironment} onValueChange={setEnvironment}>
                <SelectTrigger>
                  <SelectValue placeholder="Select environment" />
                </SelectTrigger>
                <SelectContent>
                  {environments.map(env => (
                    <SelectItem key={env} value={env}>{env}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="flex items-end">
              <Badge variant={currentEnvironment ? "default" : "outline"}>
                {currentEnvironment || "No Environment Selected"}
              </Badge>
            </div>
          </div>
          
          {/* Asset-Storage URL Selection */}
          {Object.keys(assetStorageUrls).length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
              <div>
                <Label>Asset-Storage URL Type</Label>
                <Select value={selectedAssetUrlType} onValueChange={setAssetStorageUrl}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select URL type" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(assetStorageUrls).map(urlType => (
                      <SelectItem key={urlType} value={urlType}>
                        {urlType.charAt(0).toUpperCase() + urlType.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex items-end">
                <div className="text-sm">
                  <div className="font-medium">Current URL:</div>
                  <div className="text-gray-600 font-mono text-xs">
                    {assetStorageUrls[selectedAssetUrlType] || 'Not selected'}
                  </div>
                </div>
              </div>
            </div>
          )}

          <Separator />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <Label>Authorization Header</Label>
              <div className="relative">
                <Input
                  type={showCredentials ? "text" : "password"}
                  value={credentials.authorization}
                  onChange={(e) => setCredentials(prev => ({ ...prev, authorization: e.target.value }))}
                  placeholder="Bearer token or authorization header"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3"
                  onClick={() => setShowCredentials(!showCredentials)}
                >
                  {showCredentials ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            
            <div>
              <Label>X-POP-TOKEN</Label>
              <Input
                type={showCredentials ? "text" : "password"}
                value={credentials.x_pop_token}
                onChange={(e) => setCredentials(prev => ({ ...prev, x_pop_token: e.target.value }))}
                placeholder="X-POP-TOKEN value"
              />
            </div>
          </div>

          <Button onClick={setGrpcCredentials} disabled={!currentEnvironment}>
            Set Credentials
          </Button>
        </CardContent>
      </Card>

      {/* Service Operations */}
      <Tabs defaultValue="ingress" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="ingress">IngressServer</TabsTrigger>
          <TabsTrigger value="asset-storage">AssetStorageService</TabsTrigger>
        </TabsList>

        {/* IngressServer Tab */}
        <TabsContent value="ingress" className="space-y-6">
          {/* UpsertContent */}
          <Card>
            <CardHeader>
              <CardTitle>UpsertContent</CardTitle>
              <CardDescription>
                Insert or update content with optional random field injection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Content Data (JSON)</Label>
                <Textarea
                  value={upsertContentForm.content_data}
                  onChange={(e) => setUpsertContentForm(prev => ({ ...prev, content_data: e.target.value }))}
                  rows={5}
                  className="font-mono"
                />
              </div>
              
              <div>
                <Label>Random Field (optional)</Label>
                <Input
                  value={upsertContentForm.random_field}
                  onChange={(e) => setUpsertContentForm(prev => ({ ...prev, random_field: e.target.value }))}
                  placeholder="Field name to inject random string"
                />
              </div>
              
              <Button onClick={callUpsertContent} disabled={loading}>
                {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                Call UpsertContent
              </Button>
              
              {renderResult('UpsertContent', results.upsertContent)}
            </CardContent>
          </Card>

          {/* BatchCreateAssets */}
          <Card>
            <CardHeader>
              <CardTitle>BatchCreateAssets</CardTitle>
              <CardDescription>
                Create multiple assets and get upload URLs
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Assets Data (JSON Array)</Label>
                <Textarea
                  value={batchCreateAssetsForm.assets_data}
                  onChange={(e) => setBatchCreateAssetsForm(prev => ({ ...prev, assets_data: e.target.value }))}
                  rows={5}
                  className="font-mono"
                />
              </div>
              
              <Button onClick={callBatchCreateAssets} disabled={loading}>
                {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                Create Assets
              </Button>
              
              {/* Upload URLs Table */}
              {uploadUrls.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium mb-2">Upload URLs</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Asset ID</TableHead>
                        <TableHead>Upload URL</TableHead>
                        <TableHead>File</TableHead>
                        <TableHead>Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {uploadUrls.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell className="font-mono">{item.asset_id}</TableCell>
                          <TableCell className="max-w-xs truncate">{item.upload_url}</TableCell>
                          <TableCell>
                            <Input
                              type="file"
                              onChange={(e) => handleFileSelect(item.asset_id, e.target.files[0])}
                              className="w-full"
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              size="sm"
                              onClick={() => uploadFile(item.upload_url, item.asset_id)}
                              disabled={!selectedFiles[item.asset_id] || loading}
                            >
                              <Upload className="h-4 w-4 mr-1" />
                              Upload
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              
              {renderResult('BatchCreateAssets', results.batchCreateAssets)}
            </CardContent>
          </Card>

          {/* BatchAddDownloadCounts */}
          <Card>
            <CardHeader>
              <CardTitle>BatchAddDownloadCounts</CardTitle>
              <CardDescription>
                Add download counts for content (always increments by 1)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <Label>Player ID</Label>
                  <Input
                    value={downloadCountsForm.player_id}
                    onChange={(e) => setDownloadCountsForm(prev => ({ ...prev, player_id: e.target.value }))}
                    placeholder="player-123"
                  />
                </div>
                
                <div>
                  <Label>Content IDs (comma-separated)</Label>
                  <Input
                    value={downloadCountsForm.content_ids}
                    onChange={(e) => setDownloadCountsForm(prev => ({ ...prev, content_ids: e.target.value }))}
                    placeholder="content-1, content-2, content-3"
                  />
                </div>
              </div>
              
              <Button onClick={callBatchAddDownloadCounts} disabled={loading}>
                {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                Add Download Counts
              </Button>
              
              {renderResult('BatchAddDownloadCounts', results.batchAddDownloadCounts)}
            </CardContent>
          </Card>

          {/* BatchAddRatings */}
          <Card>
            <CardHeader>
              <CardTitle>BatchAddRatings</CardTitle>
              <CardDescription>
                Add ratings for content
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Rating Data (JSON)</Label>
                <Textarea
                  value={ratingsForm.rating_data}
                  onChange={(e) => setRatingsForm(prev => ({ ...prev, rating_data: e.target.value }))}
                  rows={4}
                  className="font-mono"
                />
              </div>
              
              <Button onClick={callBatchAddRatings} disabled={loading}>
                {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                <Star className="mr-2 h-4 w-4" />
                Add Rating
              </Button>
              
              {renderResult('BatchAddRatings', results.batchAddRatings)}
            </CardContent>
          </Card>
        </TabsContent>

        {/* AssetStorageService Tab */}
        <TabsContent value="asset-storage" className="space-y-6">
          {/* BatchGetSignedUrls */}
          <Card>
            <CardHeader>
              <CardTitle>BatchGetSignedUrls</CardTitle>
              <CardDescription>
                Get signed URLs for assets and display as thumbnails
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Asset IDs (comma-separated)</Label>
                <Input
                  value={signedUrlsForm.asset_ids}
                  onChange={(e) => setSignedUrlsForm(prev => ({ ...prev, asset_ids: e.target.value }))}
                  placeholder="asset-1, asset-2, asset-3"
                />
              </div>
              
              <Button onClick={callBatchGetSignedUrls} disabled={loading}>
                {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                <Download className="mr-2 h-4 w-4" />
                Get Signed URLs
              </Button>
              
              {/* Image Thumbnails */}
              {imageUrls.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-medium mb-2">Asset Images</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {imageUrls.map((item, index) => (
                      <Card key={index}>
                        <CardContent className="p-3">
                          <div className="aspect-square bg-gray-100 rounded mb-2 flex items-center justify-center overflow-hidden">
                            <img
                              src={item.signed_url}
                              alt={item.asset_id}
                              className="max-w-full max-h-full object-cover"
                              onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.parentNode.innerHTML = '<div class="flex items-center justify-center h-full"><Image class="h-8 w-8 text-gray-400" /></div>';
                              }}
                            />
                          </div>
                          <p className="text-xs font-mono truncate">{item.asset_id}</p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
              
              {renderResult('BatchGetSignedUrls', results.batchGetSignedUrls)}
            </CardContent>
          </Card>

          {/* BatchUpdateStatuses */}
          <Card>
            <CardHeader>
              <CardTitle>BatchUpdateStatuses</CardTitle>
              <CardDescription>
                Update statuses for multiple assets
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Asset Updates (JSON Array)</Label>
                <Textarea
                  value={updateStatusesForm.asset_updates}
                  onChange={(e) => setUpdateStatusesForm(prev => ({ ...prev, asset_updates: e.target.value }))}
                  rows={5}
                  className="font-mono"
                />
              </div>
              
              <Button onClick={callBatchUpdateStatuses} disabled={loading}>
                {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                Update Statuses
              </Button>
              
              {renderResult('BatchUpdateStatuses', results.batchUpdateStatuses)}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Status Display */}
      {grpcStatus && (
        <Card>
          <CardHeader>
            <CardTitle>Client Status</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-50 p-3 rounded text-sm overflow-auto">
              {JSON.stringify(grpcStatus, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default GrpcIntegration;