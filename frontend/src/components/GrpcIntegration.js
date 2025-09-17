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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
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
  EyeOff,
  Save,
  Trash2
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
  const [availableServices, setAvailableServices] = useState({}); // Dynamic services and methods
  const [dynamicInputs, setDynamicInputs] = useState({}); // Track textarea values for dynamic methods
  const [savedRequests, setSavedRequests] = useState({}); // Saved request data for persistence
  const [namedSaves, setNamedSaves] = useState({}); // Named saved examples
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [selectedSaveToLoad, setSelectedSaveToLoad] = useState('');

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

  // Load saved requests on component mount
  useEffect(() => {
    const savedData = localStorage.getItem('grpcSavedRequests');
    const namedSavedData = localStorage.getItem('grpcNamedSaves');
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        setSavedRequests(parsed);
        setDynamicInputs(parsed);
      } catch (error) {
        console.error('Error loading saved requests:', error);
      }
    }
    if (namedSavedData) {
      try {
        const parsed = JSON.parse(namedSavedData);
        setNamedSaves(parsed);
      } catch (error) {
        console.error('Error loading named saves:', error);
      }
    }
  }, []);

  // Load example data for a method
  const loadMethodExample = async (serviceName, methodName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/grpc/${serviceName}/example/${methodName}`);
      if (response.data.example) {
        setDynamicInputs(prev => ({
          ...prev,
          [`${serviceName}_${methodName}`]: JSON.stringify(response.data.example, null, 2)
        }));
        toast.success(`Example loaded for ${methodName}`);
      }
    } catch (error) {
      console.error(`Error loading example for ${methodName}:`, error);
      toast.error(`Failed to load example for ${methodName}`);
    }
  };

  // Load default values for a method (REQ2)
  const loadMethodDefault = async (serviceName, methodName) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/grpc/${serviceName}/example/${methodName}`);
      if (response.data.example) {
        setDynamicInputs(prev => ({
          ...prev,
          [`${serviceName}_${methodName}`]: JSON.stringify(response.data.example, null, 2)
        }));
        toast.success(`Default values loaded for ${methodName}`);
      }
    } catch (error) {
      console.error(`Error loading default for ${methodName}:`, error);
      toast.error(`Failed to load default for ${methodName}`);
    }
  };

  // Save named example (REQ3)
  const saveNamedExample = (serviceName, methodName) => {
    if (!saveName.trim()) {
      toast.error('Please enter a name for this save');
      return;
    }
    
    try {
      const key = `${serviceName}_${methodName}`;
      const currentData = dynamicInputs[key] || '{}';
      
      const newNamedSaves = {
        ...namedSaves,
        [key]: {
          ...namedSaves[key],
          [saveName]: {
            data: currentData,
            timestamp: new Date().toISOString(),
            serviceName,
            methodName
          }
        }
      };
      
      localStorage.setItem('grpcNamedSaves', JSON.stringify(newNamedSaves));
      setNamedSaves(newNamedSaves);
      setSaveName('');
      setSaveDialogOpen(false);
      toast.success(`Saved example as "${saveName}"`);
    } catch (error) {
      console.error('Error saving named example:', error);
      toast.error('Failed to save named example');
    }
  };

  // Load named example (REQ3)
  const loadNamedExample = (serviceName, methodName, saveName) => {
    try {
      const key = `${serviceName}_${methodName}`;
      const namedSave = namedSaves[key]?.[saveName];
      
      if (namedSave) {
        setDynamicInputs(prev => ({
          ...prev,
          [key]: namedSave.data
        }));
        toast.success(`Loaded example "${saveName}"`);
      } else {
        toast.error('Named example not found');
      }
    } catch (error) {
      console.error('Error loading named example:', error);
      toast.error('Failed to load named example');
    }
  };

  // Delete named example
  const deleteNamedExample = (serviceName, methodName, saveName) => {
    try {
      const key = `${serviceName}_${methodName}`;
      const newNamedSaves = { ...namedSaves };
      
      if (newNamedSaves[key]) {
        delete newNamedSaves[key][saveName];
        if (Object.keys(newNamedSaves[key]).length === 0) {
          delete newNamedSaves[key];
        }
      }
      
      localStorage.setItem('grpcNamedSaves', JSON.stringify(newNamedSaves));
      setNamedSaves(newNamedSaves);
      toast.success(`Deleted example "${saveName}"`);
    } catch (error) {
      console.error('Error deleting named example:', error);
      toast.error('Failed to delete named example');
    }
  };

  // Save current request data
  const saveRequestData = () => {
    try {
      localStorage.setItem('grpcSavedRequests', JSON.stringify(dynamicInputs));
      setSavedRequests(dynamicInputs);
      toast.success('Request data saved successfully');
    } catch (error) {
      console.error('Error saving request data:', error);
      toast.error('Failed to save request data');
    }
  };

  // Clear saved data
  const clearSavedData = () => {
    try {
      localStorage.removeItem('grpcSavedRequests');
      setSavedRequests({});
      setDynamicInputs({});
      toast.success('Saved data cleared');
    } catch (error) {
      console.error('Error clearing saved data:', error);
      toast.error('Failed to clear saved data');
    }
  };

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
      
      // If already initialized, fetch available services
      if (response.data.initialized) {
        try {
          const servicesResponse = await axios.post(`${API_BASE_URL}/api/grpc/initialize`);
          if (servicesResponse.data.success && servicesResponse.data.available_services) {
            setAvailableServices(servicesResponse.data.available_services);
          }
        } catch (error) {
          console.error('Error fetching available services:', error);
        }
      }
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
        setAvailableServices(response.data.available_services || {});
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
  
  // Generic gRPC method call
  const callGrpcMethod = async (serviceName, methodName) => {
    setLoading(true);
    try {
      // Get the input value for this specific method
      const inputKey = `${serviceName}_${methodName}`;
      const textareaValue = dynamicInputs[inputKey] || '{}';
      
      let requestData;
      try {
        requestData = JSON.parse(textareaValue);
      } catch (e) {
        toast.error('Invalid JSON in request data');
        setLoading(false);
        return;
      }

      const response = await axios.post(`${API_BASE_URL}/api/grpc/${serviceName}/${methodName}`, requestData);
      
      setResults(prev => ({ ...prev, [`${serviceName}_${methodName}`]: response.data }));
      
      if (response.data.success) {
        toast.success(`${methodName} called successfully`);
      } else {
        toast.error(`${methodName} failed: ${response.data.error}`);
      }
    } catch (error) {
      console.error(`Error calling ${methodName}:`, error);
      toast.error(`Failed to call ${methodName}: ${error.response?.data?.error || error.message}`);
      setResults(prev => ({ ...prev, [`${serviceName}_${methodName}`]: { success: false, error: error.message } }));
    } finally {
      setLoading(false);
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
      {initialized && Object.keys(availableServices).length > 0 ? (
        <div className="space-y-6">
          {/* Global Controls */}
          <Card>
            <CardHeader>
              <CardTitle>Request Data Management</CardTitle>
              <CardDescription>
                Save and manage your gRPC request data across app reloads
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Button 
                  variant="outline"
                  onClick={saveRequestData}
                  disabled={loading}
                >
                  <Save className="mr-2 h-4 w-4" />
                  Save All Requests
                </Button>
                
                <Button 
                  variant="outline"
                  onClick={clearSavedData}
                  disabled={loading}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear Saved Data
                </Button>
                
                <Badge variant="secondary">
                  {Object.keys(savedRequests).length} requests saved
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Tabs defaultValue={Object.keys(availableServices)[0]} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            {Object.keys(availableServices).map(serviceName => (
              <TabsTrigger key={serviceName} value={serviceName}>
                {serviceName === 'ingress_server' ? 'IngressServer' : 
                 serviceName === 'asset_storage' ? 'AssetStorageService' : 
                 serviceName}
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Dynamic Service Tabs */}
          {Object.entries(availableServices).map(([serviceName, methods]) => (
            <TabsContent key={serviceName} value={serviceName} className="space-y-6">
              <h3 className="text-xl font-semibold mb-4">
                {serviceName === 'ingress_server' ? 'IngressServer' : 
                 serviceName === 'asset_storage' ? 'AssetStorageService' : 
                 serviceName} Methods
              </h3>
              
              {methods && methods.length > 0 ? (
                methods.map(methodName => (
                  <Card key={methodName}>
                    <CardHeader>
                      <CardTitle className="flex items-center justify-between">
                        {methodName}
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => loadMethodDefault(serviceName, methodName)}
                          >
                            Load Default
                          </Button>
                          
                          {/* Load Named Examples Dropdown */}
                          {namedSaves[`${serviceName}_${methodName}`] && 
                           Object.keys(namedSaves[`${serviceName}_${methodName}`]).length > 0 && (
                            <Select
                              value={selectedSaveToLoad}
                              onValueChange={(value) => {
                                setSelectedSaveToLoad(value);
                                loadNamedExample(serviceName, methodName, value);
                              }}
                            >
                              <SelectTrigger className="w-32 h-8">
                                <SelectValue placeholder="Load Save" />
                              </SelectTrigger>
                              <SelectContent>
                                {Object.keys(namedSaves[`${serviceName}_${methodName}`] || {}).map((saveName) => (
                                  <SelectItem key={saveName} value={saveName}>
                                    {saveName}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          )}
                        </div>
                      </CardTitle>
                      <CardDescription>
                        {serviceName} service method
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <Label>Request Data (JSON)</Label>
                        <Textarea
                          rows={8}
                          className="font-mono text-sm"
                          placeholder={`Enter ${methodName} request parameters as JSON`}
                          value={dynamicInputs[`${serviceName}_${methodName}`] || '{}'}
                          onChange={(e) => setDynamicInputs(prev => ({
                            ...prev,
                            [`${serviceName}_${methodName}`]: e.target.value
                          }))}
                        />
                        <div className="text-xs text-gray-500 mt-1">
                          Use <code>{"{{rand}}"}</code> for random values in your JSON
                        </div>
                      </div>
                      
                      <div className="flex gap-2">
                        <Button 
                          onClick={() => callGrpcMethod(serviceName, methodName)}
                          disabled={loading}
                          className="flex-1"
                        >
                          {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                          Call {methodName}
                        </Button>
                        
                        <Button 
                          variant="outline"
                          onClick={saveRequestData}
                          disabled={loading}
                        >
                          <Save className="mr-2 h-4 w-4" />
                          Save
                        </Button>
                      </div>
                      
                      {results[`${serviceName}_${methodName}`] && 
                        renderResult(`${serviceName}_${methodName}`, results[`${serviceName}_${methodName}`])
                      }
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-gray-500">No methods available for this service.</p>
              )}
            </TabsContent>
          ))}
        </Tabs>
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-8">
            <p className="text-gray-500 mb-4">
              {!initialized 
                ? "Initialize the gRPC client to see available services and methods." 
                : "No services available. Please check your configuration."}
            </p>
            {!initialized && (
              <Button onClick={initializeGrpc} disabled={loading}>
                {loading && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
                Initialize gRPC Client
              </Button>
            )}
          </CardContent>
        </Card>
      )}

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