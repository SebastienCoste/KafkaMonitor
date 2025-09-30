#!/usr/bin/env python3
"""
Backend Testing for Blueprint Configuration APIs - Critical Routing Fix Verification
Testing the critical Blueprint Configuration APIs to verify the backend routing fix is working
"""

import requests
import json
import sys
import time
import asyncio
import websockets
from datetime import datetime
from typing import Dict, Any, List

class BackendRoutingTester:
    def __init__(self, base_url: str = "https://portable-config-ui.preview.emergentagent.com"):
        self.base_url = base_url
        self.ws_base_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    # Test Suite A - Core APIs
    def test_health_endpoint(self):
        """Test Suite A.1: GET /api/health - Health check"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.log_test("Health Check", True, f"Status: {data.get('status')}")
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected status: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False
    
    def test_app_config_endpoint(self):
        """Test Suite A.2: GET /api/app-config - Application configuration"""
        try:
            response = requests.get(f"{self.base_url}/api/app-config", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected fields
                expected_fields = ["app_name", "version", "environment", "tabs"]
                found_fields = [field for field in expected_fields if field in data]
                
                if len(found_fields) >= 3:  # At least 3 of 4 expected fields
                    self.log_test("App Config", True, f"Found fields: {found_fields}")
                    
                    # Check tabs structure
                    if "tabs" in data and isinstance(data["tabs"], dict):
                        tab_count = len(data["tabs"])
                        self.log_test("App Config - Tabs", True, f"Found {tab_count} tabs: {list(data['tabs'].keys())}")
                    
                    return True
                else:
                    self.log_test("App Config", False, f"Missing expected fields. Found: {list(data.keys())}")
                    return False
            else:
                self.log_test("App Config", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("App Config", False, f"Exception: {str(e)}")
            return False
    
    def test_environments_endpoint(self):
        """Test Suite A.3: GET /api/environments - Environment list"""
        try:
            response = requests.get(f"{self.base_url}/api/environments", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for environments list
                environments = data.get("environments", []) or data.get("available_environments", [])
                expected_envs = ["DEV", "TEST", "INT", "LOAD", "PROD"]
                
                if environments and isinstance(environments, list):
                    found_expected = [env for env in expected_envs if env in environments]
                    if len(found_expected) >= 3:  # At least 3 of 5 expected environments
                        self.log_test("Environments", True, f"Found environments: {environments}")
                        return True
                    else:
                        self.log_test("Environments", False, f"Missing expected environments. Found: {environments}")
                        return False
                else:
                    self.log_test("Environments", False, f"No valid environments list found: {data}")
                    return False
            else:
                self.log_test("Environments", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Environments", False, f"Exception: {str(e)}")
            return False
    
    def test_file_tree_endpoint(self):
        """Test Suite A.4: GET /api/blueprint/file-tree - File tree browsing"""
        try:
            # First set up root path
            self.setup_blueprint_root_path()
            
            response = requests.get(f"{self.base_url}/api/blueprint/file-tree", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "files" in data and isinstance(data["files"], list):
                    file_count = len(data["files"])
                    self.log_test("File Tree", True, f"Found {file_count} files/directories")
                    
                    # Show sample files
                    if file_count > 0:
                        sample_files = []
                        for i, f in enumerate(data["files"][:3]):  # First 3 files
                            if isinstance(f, dict):
                                sample_files.append(f.get("name", "unknown"))
                            else:
                                sample_files.append(str(f))
                        self.log_test("File Tree - Sample", True, f"Sample files: {sample_files}")
                    
                    return True
                else:
                    self.log_test("File Tree", False, f"Invalid response structure: {data}")
                    return False
            else:
                self.log_test("File Tree", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("File Tree", False, f"Exception: {str(e)}")
            return False
    
    # Test Suite B - Blueprint Configuration
    def test_entity_definitions_endpoint(self):
        """Test Suite B.5: GET /api/blueprint/config/entity-definitions - Entity definitions schema"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/config/entity-definitions", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for entity types
                if "entityTypes" in data:
                    entity_types = data["entityTypes"]
                    if isinstance(entity_types, list) and len(entity_types) >= 5:  # Expect at least 5 entity types
                        self.log_test("Entity Definitions", True, f"Found {len(entity_types)} entity types")
                        
                        # Check for environments
                        environments = data.get("environments", [])
                        if environments:
                            self.log_test("Entity Definitions - Environments", True, f"Environments: {environments}")
                        
                        return True
                    else:
                        self.log_test("Entity Definitions", False, f"Invalid entity types: {entity_types}")
                        return False
                else:
                    self.log_test("Entity Definitions", False, f"Missing entityTypes field: {list(data.keys())}")
                    return False
            else:
                self.log_test("Entity Definitions", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Entity Definitions", False, f"Exception: {str(e)}")
            return False
    
    def test_namespace_endpoint(self):
        """Test Suite B.6: GET /api/blueprint/namespace - Namespace detection"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/namespace", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for namespace field
                if "namespace" in data and "source" in data:
                    namespace = data.get("namespace", "")
                    source = data.get("source", "")
                    
                    if source == "blueprint_cnf.json" and namespace:
                        self.log_test("Namespace Detection", True, f"Found namespace: {namespace} from {source}")
                    elif source == "not_found":
                        self.log_test("Namespace Detection", True, f"No blueprint_cnf.json found (expected for new projects)")
                    else:
                        self.log_test("Namespace Detection", True, f"Namespace: '{namespace}' from {source}")
                    
                    return True
                else:
                    self.log_test("Namespace Detection", False, f"Missing expected fields: {data}")
                    return False
            else:
                self.log_test("Namespace Detection", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Namespace Detection", False, f"Exception: {str(e)}")
            return False
    
    def test_blueprint_cnf_file_content(self):
        """Test Suite B.7: GET /api/blueprint/file-content/blueprint_cnf.json - File content reading"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "content" in data:
                    content = data["content"]
                    
                    # Try to parse JSON content
                    try:
                        parsed_content = json.loads(content)
                        
                        # Check for expected blueprint structure
                        expected_fields = ["namespace", "version"]
                        found_fields = [field for field in expected_fields if field in parsed_content]
                        
                        if found_fields:
                            self.log_test("Blueprint CNF Content", True, f"Valid JSON with fields: {list(parsed_content.keys())}")
                            
                            # Show key details
                            namespace = parsed_content.get("namespace", "N/A")
                            version = parsed_content.get("version", "N/A")
                            self.log_test("Blueprint CNF Details", True, f"Namespace: {namespace}, Version: {version}")
                        else:
                            self.log_test("Blueprint CNF Content", True, f"Valid JSON but missing expected fields: {list(parsed_content.keys())}")
                        
                        return True
                    except json.JSONDecodeError:
                        self.log_test("Blueprint CNF Content", False, f"Invalid JSON content")
                        return False
                else:
                    self.log_test("Blueprint CNF Content", False, f"Missing content field: {data}")
                    return False
            elif response.status_code == 404:
                self.log_test("Blueprint CNF Content", True, "File not found (404) - acceptable for new projects")
                return True
            else:
                self.log_test("Blueprint CNF Content", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Blueprint CNF Content", False, f"Exception: {str(e)}")
            return False
    
    # Test Suite C - WebSocket
    async def test_websocket_connection(self, path: str, test_name: str):
        """Test WebSocket connection to a specific path"""
        try:
            ws_url = f"{self.ws_base_url}{path}"
            
            # Try to connect with a timeout
            async with websockets.connect(ws_url, timeout=10) as websocket:
                # Send a ping and wait for response
                await websocket.send(json.dumps({"type": "test_ping"}))
                
                # Wait for any response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    self.log_test(test_name, True, f"Connected successfully, received: {response[:100]}")
                    return True
                except asyncio.TimeoutError:
                    # Connection established but no immediate response - still success
                    self.log_test(test_name, True, f"Connected successfully (no immediate response)")
                    return True
                    
        except websockets.exceptions.ConnectionClosed:
            self.log_test(test_name, False, "WebSocket connection closed unexpectedly")
            return False
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 403:
                self.log_test(test_name, False, f"WebSocket connection forbidden (403)")
            else:
                self.log_test(test_name, False, f"WebSocket invalid status: {e.status_code}")
            return False
        except Exception as e:
            self.log_test(test_name, False, f"WebSocket error: {str(e)}")
            return False
    
    def test_websocket_main(self):
        """Test Suite C.8: Test WebSocket connection to /api/ws"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.test_websocket_connection("/api/ws", "WebSocket Main"))
            loop.close()
            return result
        except Exception as e:
            self.log_test("WebSocket Main", False, f"Async error: {str(e)}")
            return False
    
    def test_websocket_blueprint(self):
        """Test Suite C.9: Test WebSocket connection to /api/ws/blueprint"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.test_websocket_connection("/api/ws/blueprint", "WebSocket Blueprint"))
            loop.close()
            return result
        except Exception as e:
            self.log_test("WebSocket Blueprint", False, f"Async error: {str(e)}")
            return False
    
    def setup_blueprint_root_path(self):
        """Set up blueprint root path for testing"""
        try:
            response = requests.put(
                f"{self.base_url}/api/blueprint/config",
                json={"root_path": "/app"},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Setup Blueprint Root Path", True, f"Root path set to: {data.get('root_path')}")
                    return True
                else:
                    self.log_test("Setup Blueprint Root Path", False, "Failed to set root path")
                    return False
            else:
                self.log_test("Setup Blueprint Root Path", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Setup Blueprint Root Path", False, f"Exception: {str(e)}")
            return False
    
    def test_entity_definitions_environments(self):
        """Test 1: Verify /api/blueprint/config/entity-definitions returns environments [DEV, TEST, INT, LOAD, PROD] and entityTypes presence"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/config/entity-definitions", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for environments
                environments = data.get("environments", [])
                expected_envs = ["DEV", "TEST", "INT", "LOAD", "PROD"]
                
                if all(env in environments for env in expected_envs):
                    self.log_test("Entity Definitions - Environments", True, f"✅ Found all expected environments: {environments}")
                else:
                    missing_envs = [env for env in expected_envs if env not in environments]
                    self.log_test("Entity Definitions - Environments", False, f"❌ Missing environments: {missing_envs}. Found: {environments}")
                
                # Check for entityTypes presence
                if "entityTypes" in data:
                    entity_types = data["entityTypes"]
                    if len(entity_types) >= 11:  # Should have 11 entity types
                        self.log_test("Entity Definitions - EntityTypes", True, f"✅ Found {len(entity_types)} entity types")
                        
                        # Show some entity type names for verification
                        type_names = []
                        for i, et in enumerate(entity_types):
                            if i >= 5:  # Only show first 5
                                break
                            if isinstance(et, dict):
                                type_names.append(et.get("name", "unknown"))
                            else:
                                type_names.append(str(et))
                        self.log_test("Entity Definitions - Sample Types", True, f"Sample types: {type_names}")
                        
                        return True
                    else:
                        self.log_test("Entity Definitions - EntityTypes", False, f"❌ Expected 11+ entity types, found {len(entity_types)}")
                        return False
                else:
                    self.log_test("Entity Definitions - EntityTypes", False, "❌ Missing 'entityTypes' field in response")
                    return False
            else:
                self.log_test("Entity Definitions API", False, f"❌ HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Entity Definitions API", False, f"❌ Exception: {str(e)}")
            return False
    
    def test_blueprint_cnf_file_content(self):
        """Test 2: Verify /api/blueprint/file-content/blueprint_cnf.json (if exists) parses OK"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "content" in data:
                    content = data["content"]
                    
                    # Try to parse the JSON content
                    try:
                        parsed_content = json.loads(content)
                        
                        # Check for expected blueprint_cnf.json structure
                        expected_fields = ["namespace", "version"]
                        found_fields = [field for field in expected_fields if field in parsed_content]
                        
                        self.log_test("Blueprint CNF File Content - Parse", True, f"✅ JSON parses OK. Found fields: {list(parsed_content.keys())}")
                        
                        if found_fields:
                            self.log_test("Blueprint CNF File Content - Structure", True, f"✅ Found expected fields: {found_fields}")
                            
                            # Show some content details
                            namespace = parsed_content.get("namespace", "N/A")
                            version = parsed_content.get("version", "N/A")
                            self.log_test("Blueprint CNF File Content - Details", True, f"Namespace: {namespace}, Version: {version}")
                        else:
                            self.log_test("Blueprint CNF File Content - Structure", False, f"❌ Missing expected fields. Found: {list(parsed_content.keys())}")
                        
                        return True
                    except json.JSONDecodeError as je:
                        self.log_test("Blueprint CNF File Content - Parse", False, f"❌ JSON parse error: {str(je)}")
                        self.log_test("Blueprint CNF File Content - Raw", True, f"Raw content (first 200 chars): {content[:200]}")
                        return False
                else:
                    self.log_test("Blueprint CNF File Content", False, "❌ Missing 'content' field in response")
                    return False
            elif response.status_code == 404:
                self.log_test("Blueprint CNF File Content", True, "ℹ️ blueprint_cnf.json file does not exist (404) - this is OK")
                return True
            else:
                self.log_test("Blueprint CNF File Content", False, f"❌ HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Blueprint CNF File Content", False, f"❌ Exception: {str(e)}")
            return False
    
    def test_file_tree_apis(self):
        """Test 3: Verify file-tree APIs for transformSpecs and searchExperience/templates"""
        # Test transformSpecs path
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/file-tree?path=example_config/src/transformSpecs", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "files" in data:
                    files = data["files"]
                    
                    # Look for .jslt files (transform specification files)
                    jslt_files = [f for f in files if isinstance(f, dict) and f.get("name", "").endswith(".jslt")]
                    
                    if jslt_files:
                        self.log_test("File Tree - TransformSpecs", True, f"✅ Found {len(jslt_files)} .jslt files: {[f.get('name') for f in jslt_files]}")
                    else:
                        self.log_test("File Tree - TransformSpecs", True, f"ℹ️ No .jslt files found. Total files: {len(files)}")
                        if files:
                            sample_files = [f.get("name", "unknown") if isinstance(f, dict) else str(f) for f in files[:3]]
                            self.log_test("File Tree - TransformSpecs Sample", True, f"Sample files: {sample_files}")
                else:
                    self.log_test("File Tree - TransformSpecs", False, "❌ Missing 'files' field in response")
            else:
                self.log_test("File Tree - TransformSpecs", False, f"❌ HTTP {response.status_code}")
        except Exception as e:
            self.log_test("File Tree - TransformSpecs", False, f"❌ Exception: {str(e)}")
        
        # Test searchExperience/templates path
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/file-tree?path=example_config/src/searchExperience/templates", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "files" in data:
                    files = data["files"]
                    
                    # Look for .json/.js files (search experience template files)
                    template_files = [f for f in files if isinstance(f, dict) and (f.get("name", "").endswith(".json") or f.get("name", "").endswith(".js"))]
                    
                    if template_files:
                        self.log_test("File Tree - SearchExperience Templates", True, f"✅ Found {len(template_files)} template files: {[f.get('name') for f in template_files]}")
                    else:
                        self.log_test("File Tree - SearchExperience Templates", True, f"ℹ️ No template files found. Total files: {len(files)}")
                        if files:
                            sample_files = [f.get("name", "unknown") if isinstance(f, dict) else str(f) for f in files[:3]]
                            self.log_test("File Tree - SearchExperience Sample", True, f"Sample files: {sample_files}")
                else:
                    self.log_test("File Tree - SearchExperience Templates", False, "❌ Missing 'files' field in response")
            else:
                self.log_test("File Tree - SearchExperience Templates", False, f"❌ HTTP {response.status_code}")
        except Exception as e:
            self.log_test("File Tree - SearchExperience Templates", False, f"❌ Exception: {str(e)}")
    
    def test_environments_api(self):
        """Test 4: Verify /api/environments returns current and available"""
        try:
            response = requests.get(f"{self.base_url}/api/environments", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for current environment
                if "current_environment" in data:
                    current_env = data["current_environment"]
                    if current_env:
                        self.log_test("Environments API - Current", True, f"✅ Current environment: {current_env}")
                    else:
                        self.log_test("Environments API - Current", True, f"ℹ️ No current environment set (null)")
                else:
                    self.log_test("Environments API - Current", False, "❌ Missing 'current_environment' field in response")
                
                # Check for available environments
                if "available_environments" in data:
                    available_envs = data["available_environments"]
                    if isinstance(available_envs, list) and len(available_envs) > 0:
                        self.log_test("Environments API - Available", True, f"✅ Available environments: {available_envs}")
                        
                        # Check if expected environments are present
                        expected_envs = ["DEV", "TEST", "INT", "LOAD", "PROD"]
                        found_expected = [env for env in expected_envs if env in available_envs]
                        if found_expected:
                            self.log_test("Environments API - Expected Envs", True, f"✅ Found expected environments: {found_expected}")
                        else:
                            self.log_test("Environments API - Expected Envs", False, f"❌ No expected environments found in: {available_envs}")
                        
                        return True
                    else:
                        self.log_test("Environments API - Available", False, f"❌ Available environments is not a valid list: {available_envs}")
                        return False
                else:
                    self.log_test("Environments API - Available", False, "❌ Missing 'available_environments' field in response")
                    return False
            else:
                self.log_test("Environments API", False, f"❌ HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Environments API", False, f"❌ Exception: {str(e)}")
            return False
    
    def test_blueprint_create_file_overwrite(self):
        """Test 5: Verify /api/blueprint/create-file can overwrite blueprint_cnf.json with sample content"""
        try:
            # Sample blueprint_cnf.json content
            sample_content = {
                "namespace": "com.test.blueprint.sanity.check",
                "version": "1.0.0",
                "description": "Sample blueprint configuration for sanity testing",
                "owner": "sanity-test",
                "transformSpecs": ["test_transform.jslt"],
                "searchExperience": {
                    "name": "test_search",
                    "templates": ["test_template.json"]
                }
            }
            
            # Test creating/overwriting blueprint_cnf.json
            payload = {
                "path": "blueprint_cnf.json",
                "content": json.dumps(sample_content, indent=2),
                "overwrite": True
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    self.log_test("Blueprint Create File - Overwrite", True, "✅ Successfully created/overwritten blueprint_cnf.json")
                    
                    # Verify the content was written correctly
                    time.sleep(1)  # Brief pause to ensure file is written
                    
                    verify_response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
                    
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        
                        if "content" in verify_data:
                            try:
                                written_content = json.loads(verify_data["content"])
                                
                                # Check if key fields match
                                if (written_content.get("namespace") == sample_content["namespace"] and 
                                    written_content.get("version") == sample_content["version"]):
                                    self.log_test("Blueprint Create File - Content Verification", True, "✅ File content matches expected sample")
                                    
                                    # Show content snippet
                                    self.log_test("Blueprint Create File - Content Sample", True, f"Namespace: {written_content.get('namespace')}, Version: {written_content.get('version')}")
                                    
                                    return True
                                else:
                                    self.log_test("Blueprint Create File - Content Verification", False, f"❌ Content mismatch. Expected namespace: {sample_content['namespace']}, Got: {written_content.get('namespace')}")
                                    return False
                            except json.JSONDecodeError:
                                self.log_test("Blueprint Create File - Content Verification", False, "❌ Written content is not valid JSON")
                                return False
                        else:
                            self.log_test("Blueprint Create File - Content Verification", False, "❌ No content in verification response")
                            return False
                    else:
                        self.log_test("Blueprint Create File - Content Verification", False, f"❌ Verification failed with HTTP {verify_response.status_code}")
                        return False
                else:
                    self.log_test("Blueprint Create File - Overwrite", False, f"❌ Create file failed: {data}")
                    return False
            elif response.status_code == 409:
                # Try again with overwrite=true explicitly
                self.log_test("Blueprint Create File - First Attempt", True, "ℹ️ File exists (409), testing overwrite functionality")
                
                # Retry with explicit overwrite
                retry_response = requests.post(
                    f"{self.base_url}/api/blueprint/create-file",
                    json=payload,  # payload already has overwrite=True
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if retry_response.status_code == 200:
                    retry_data = retry_response.json()
                    if retry_data.get("success"):
                        self.log_test("Blueprint Create File - Overwrite Retry", True, "✅ Successfully overwritten existing file")
                        return True
                    else:
                        self.log_test("Blueprint Create File - Overwrite Retry", False, f"❌ Overwrite failed: {retry_data}")
                        return False
                else:
                    self.log_test("Blueprint Create File - Overwrite Retry", False, f"❌ Overwrite retry failed with HTTP {retry_response.status_code}")
                    return False
            else:
                self.log_test("Blueprint Create File - Overwrite", False, f"❌ HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Blueprint Create File - Overwrite", False, f"❌ Exception: {str(e)}")
            return False

    def run_backend_sanity_tests(self):
        """Run backend sanity check tests as per review request"""
        print("🚀 Starting Backend Sanity Check Testing")
        print("=" * 70)
        
        # First, set up blueprint root path
        self.setup_blueprint_root_path()
        
        # Test 1: Entity Definitions API - Check environments and entityTypes
        print("\n1️⃣ Testing Entity Definitions API")
        print("-" * 40)
        self.test_entity_definitions_environments()
        
        # Test 2: Blueprint CNF File Content API
        print("\n2️⃣ Testing Blueprint CNF File Content API")
        print("-" * 40)
        self.test_blueprint_cnf_file_content()
        
        # Test 3: File Tree API for Transform Specs and Search Experience Templates
        print("\n3️⃣ Testing File Tree API")
        print("-" * 40)
        self.test_file_tree_apis()
        
        # Test 4: Environments API
        print("\n4️⃣ Testing Environments API")
        print("-" * 40)
        self.test_environments_api()
        
        # Test 5: Blueprint Create File API with Overwrite
        print("\n5️⃣ Testing Blueprint Create File API")
        print("-" * 40)
        self.test_blueprint_create_file_overwrite()
        
        # Print final summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 BACKEND SANITY CHECK TEST SUMMARY")
        print("=" * 70)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Categorize results
        critical_failures = []
        minor_issues = []
        successes = []
        
        for result in self.test_results:
            if not result["success"]:
                if any(keyword in result["name"].lower() for keyword in ["api", "environments", "entity", "file", "content"]):
                    critical_failures.append(result)
                else:
                    minor_issues.append(result)
            else:
                successes.append(result)
        
        if critical_failures:
            print(f"\n❌ CRITICAL FAILURES ({len(critical_failures)}):")
            for failure in critical_failures:
                print(f"   • {failure['name']}: {failure['details']}")
        
        if minor_issues:
            print(f"\n⚠️ MINOR ISSUES ({len(minor_issues)}):")
            for issue in minor_issues:
                print(f"   • {issue['name']}: {issue['details']}")
        
        print(f"\n✅ SUCCESSFUL TESTS ({len(successes)}):")
        for success in successes:
            print(f"   • {success['name']}")
        
        # Final assessment
        if success_rate >= 90:
            print(f"\n🎉 EXCELLENT: Backend APIs are working well!")
        elif success_rate >= 75:
            print(f"\n✅ GOOD: Backend APIs are mostly functional with minor issues")
        elif success_rate >= 50:
            print(f"\n⚠️ NEEDS ATTENTION: Backend APIs have significant issues")
        else:
            print(f"\n❌ CRITICAL: Backend APIs have major problems")

if __name__ == "__main__":
    tester = BackendSanityTester()
    tester.run_backend_sanity_tests()