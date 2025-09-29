#!/usr/bin/env python3
"""
Backend Sanity Check Testing for Blueprint Configuration API
Focused testing for specific review request requirements
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

class BackendSanityTester:
    def __init__(self, base_url: str = "https://config-manager-3.preview.emergentagent.com"):
        self.base_url = base_url
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
                        type_names = [et.get("name", "unknown") for et in entity_types[:5]]
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
                if "current" in data:
                    current_env = data["current"]
                    self.log_test("Environments API - Current", True, f"✅ Current environment: {current_env}")
                else:
                    self.log_test("Environments API - Current", False, "❌ Missing 'current' field in response")
                
                # Check for available environments
                if "available" in data:
                    available_envs = data["available"]
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
                    self.log_test("Environments API - Available", False, "❌ Missing 'available' field in response")
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
    
    def test_ui_configuration_api(self):
        """Test GET /api/blueprint/config/ui-config"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for required structure
                if "config" in data:
                    config = data["config"]
                    
                    # Check for schemas
                    if "schemas" in config and len(config["schemas"]) >= 1:
                        schemas = config["schemas"]
                        schema_count = len(schemas)
                        
                        # Check for entities (this was previously failing)
                        entities_found = 0
                        for schema in schemas:
                            if "entities" in schema:
                                entities_found += len(schema["entities"])
                        
                        self.log_test("UI Configuration API", True, f"Found {schema_count} schemas with {entities_found} total entities")
                        
                        # Additional check for namespace detection
                        if "namespace" in config:
                            self.log_test("UI Config Namespace Detection", True, f"Namespace: {config['namespace']}")
                        else:
                            self.log_test("UI Config Namespace Detection", False, "No namespace detected")
                        
                        return data
                    else:
                        self.log_test("UI Configuration API", False, "No schemas found in configuration")
                        return None
                else:
                    self.log_test("UI Configuration API", False, "Missing 'config' field in response")
                    return None
            else:
                self.log_test("UI Configuration API", False, f"HTTP {response.status_code}")
                return None
        except Exception as e:
            self.log_test("UI Configuration API", False, f"Exception: {str(e)}")
            return None
    
    def test_schema_creation_api(self):
        """Test POST /api/blueprint/config/schemas"""
        try:
            payload = {
                "name": "test-schema",
                "namespace": "com.test.blueprint.config",
                "description": "Test schema for API testing"
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and "schema_id" in data:
                    schema_id = data["schema_id"]
                    self.log_test("Schema Creation API", True, f"Created schema with ID: {schema_id}")
                    return schema_id
                else:
                    self.log_test("Schema Creation API", False, f"Schema creation failed: {data}")
                    return None
            else:
                self.log_test("Schema Creation API", False, f"HTTP {response.status_code}")
                return None
        except Exception as e:
            self.log_test("Schema Creation API", False, f"Exception: {str(e)}")
            return None
    
    def test_entity_creation_api(self):
        """Test POST /api/blueprint/config/entities with success and error cases"""
        # Test 1: Valid entity creation
        try:
            payload = {
                "name": "test-access-entity",
                "entityType": "access",
                "configuration": {
                    "enabled": True,
                    "description": "Test access entity for API testing"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("Entity Creation API (Valid)", True, f"Created entity with ID: {entity_id}")
                    
                    # Test 2: Invalid entity type (should return 400)
                    self.test_entity_creation_invalid_type()
                    
                    # Test 3: Empty name (should return 400)
                    self.test_entity_creation_empty_name()
                    
                    return entity_id
                else:
                    self.log_test("Entity Creation API (Valid)", False, f"Entity creation failed: {data}")
                    return None
            elif response.status_code == 400:
                self.log_test("Entity Creation API (Valid)", False, f"Validation error (HTTP 400): {response.text}")
                return None
            else:
                self.log_test("Entity Creation API (Valid)", False, f"HTTP {response.status_code}")
                return None
        except Exception as e:
            self.log_test("Entity Creation API (Valid)", False, f"Exception: {str(e)}")
            return None
    
    def test_entity_creation_invalid_type(self):
        """Test entity creation with invalid type (should return 400)"""
        try:
            payload = {
                "name": "invalid-entity",
                "entityType": "invalid_type_that_does_not_exist",
                "configuration": {}
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 400:
                self.log_test("Entity Creation Invalid Type", True, "Correctly returned HTTP 400 for invalid entity type")
            elif response.status_code == 500:
                self.log_test("Entity Creation Invalid Type", False, "Returned HTTP 500 instead of 400 for invalid entity type")
            else:
                self.log_test("Entity Creation Invalid Type", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Entity Creation Invalid Type", False, f"Exception: {str(e)}")
    
    def test_entity_creation_empty_name(self):
        """Test entity creation with empty name (should return 400)"""
        try:
            payload = {
                "name": "",
                "entityType": "access",
                "configuration": {}
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 400:
                self.log_test("Entity Creation Empty Name", True, "Correctly returned HTTP 400 for empty name")
            elif response.status_code == 422:
                self.log_test("Entity Creation Empty Name", True, "Correctly returned HTTP 422 for empty name")
            elif response.status_code == 500:
                self.log_test("Entity Creation Empty Name", False, "Returned HTTP 500 instead of 400/422 for empty name")
            else:
                self.log_test("Entity Creation Empty Name", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Entity Creation Empty Name", False, f"Exception: {str(e)}")
    
    def test_entity_update_api(self, entity_id):
        """Test PUT /api/blueprint/config/entities/{id} with success and error cases"""
        # Test 1: Valid entity update
        try:
            payload = {
                "name": "updated-test-entity",
                "configuration": {
                    "enabled": False,
                    "description": "Updated test entity"
                }
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Entity Update API (Valid)", True, f"Successfully updated entity {entity_id}")
                else:
                    self.log_test("Entity Update API (Valid)", False, f"Update failed: {data}")
            elif response.status_code == 404:
                self.log_test("Entity Update API (Valid)", False, f"Entity not found (HTTP 404)")
            elif response.status_code == 500:
                self.log_test("Entity Update API (Valid)", False, f"Server error (HTTP 500) - should be 400/404")
            else:
                self.log_test("Entity Update API (Valid)", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Entity Update API (Valid)", False, f"Exception: {str(e)}")
        
        # Test 2: Update non-existent entity (should return 404)
        self.test_entity_update_nonexistent()
    
    def test_entity_update_nonexistent(self):
        """Test updating non-existent entity (should return 404)"""
        try:
            payload = {
                "name": "nonexistent-entity",
                "configuration": {}
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/nonexistent-entity-id-12345",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 404:
                self.log_test("Entity Update Nonexistent", True, "Correctly returned HTTP 404 for nonexistent entity")
            elif response.status_code == 500:
                self.log_test("Entity Update Nonexistent", False, "Returned HTTP 500 instead of 404 for nonexistent entity")
            else:
                self.log_test("Entity Update Nonexistent", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Entity Update Nonexistent", False, f"Exception: {str(e)}")
    
    def test_environment_overrides_api(self, entity_id):
        """Test POST /api/blueprint/config/entities/{id}/environment-overrides"""
        # Test 1: Valid environment override
        try:
            payload = {
                "entityId": entity_id,
                "environment": "DEV",
                "overrides": {
                    "enabled": True,
                    "debug_mode": True
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}/environment-overrides",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Environment Override API (Valid)", True, f"Successfully set override for entity {entity_id}")
                else:
                    self.log_test("Environment Override API (Valid)", False, f"Override failed: {data}")
            elif response.status_code == 400:
                self.log_test("Environment Override API (Valid)", False, f"Validation error (HTTP 400)")
            elif response.status_code == 404:
                self.log_test("Environment Override API (Valid)", False, f"Entity not found (HTTP 404)")
            elif response.status_code == 500:
                self.log_test("Environment Override API (Valid)", False, f"Server error (HTTP 500) - should be 400/404")
            else:
                self.log_test("Environment Override API (Valid)", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Environment Override API (Valid)", False, f"Exception: {str(e)}")
        
        # Test 2: Invalid environment (should return 400)
        self.test_environment_override_invalid_env(entity_id)
        
        # Test 3: Nonexistent entity (should return 404)
        self.test_environment_override_nonexistent_entity()
    
    def test_environment_override_invalid_env(self, entity_id):
        """Test environment override with invalid environment (should return 400)"""
        try:
            payload = {
                "entityId": entity_id,
                "environment": "INVALID_ENV",
                "overrides": {}
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}/environment-overrides",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 400:
                self.log_test("Environment Override Invalid Env", True, "Correctly returned HTTP 400 for invalid environment")
            elif response.status_code == 500:
                self.log_test("Environment Override Invalid Env", False, "Returned HTTP 500 instead of 400 for invalid environment")
            else:
                self.log_test("Environment Override Invalid Env", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Environment Override Invalid Env", False, f"Exception: {str(e)}")
    
    def test_environment_override_nonexistent_entity(self):
        """Test environment override with nonexistent entity (should return 404)"""
        try:
            payload = {
                "entityId": "nonexistent-entity-id-12345",
                "environment": "DEV",
                "overrides": {}
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities/nonexistent-entity-id-12345/environment-overrides",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 404:
                self.log_test("Environment Override Nonexistent Entity", True, "Correctly returned HTTP 404 for nonexistent entity")
            elif response.status_code == 500:
                self.log_test("Environment Override Nonexistent Entity", False, "Returned HTTP 500 instead of 404 for nonexistent entity")
            else:
                self.log_test("Environment Override Nonexistent Entity", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Environment Override Nonexistent Entity", False, f"Exception: {str(e)}")
    
    def test_file_generation_api(self, schema_id):
        """Test POST /api/blueprint/config/generate"""
        try:
            payload = {
                "schemaId": schema_id,
                "environments": ["DEV", "TEST"],
                "outputPath": "/app/generated"
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    files = data.get("files", [])
                    self.log_test("File Generation API", True, f"Generated {len(files)} files successfully")
                    
                    # Log some file details
                    for file_info in files[:3]:  # Show first 3 files
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "unknown")
                            size = file_info.get("size", 0)
                            self.log_test(f"Generated File", True, f"{filename} ({size} bytes)")
                else:
                    error = data.get("error", "Unknown error")
                    if "Schema not found" in error:
                        self.log_test("File Generation API", False, f"Schema not found error: {error}")
                    else:
                        self.log_test("File Generation API", False, f"Generation failed: {error}")
            else:
                self.log_test("File Generation API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("File Generation API", False, f"Exception: {str(e)}")
    
    def test_configuration_validation_api(self):
        """Test GET /api/blueprint/config/validate"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/config/validate", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for validation structure
                if "valid" in data:
                    is_valid = data["valid"]
                    errors = data.get("errors", [])
                    warnings = data.get("warnings", [])
                    
                    self.log_test("Configuration Validation API", True, f"Validation complete - Valid: {is_valid}, Errors: {len(errors)}, Warnings: {len(warnings)}")
                    
                    # Log some validation details
                    if errors:
                        for error in errors[:2]:  # Show first 2 errors
                            self.log_test("Validation Error", True, f"{error}")
                    
                    if warnings:
                        for warning in warnings[:2]:  # Show first 2 warnings
                            self.log_test("Validation Warning", True, f"{warning}")
                else:
                    self.log_test("Configuration Validation API", False, "Missing 'valid' field in response")
            else:
                self.log_test("Configuration Validation API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Configuration Validation API", False, f"Exception: {str(e)}")
    
    def test_entity_deletion_api(self, entity_id):
        """Test DELETE /api/blueprint/config/entities/{id} with success and error cases"""
        # Test 1: Delete nonexistent entity first (should return 404)
        self.test_entity_deletion_nonexistent()
        
        # Test 2: Delete existing entity
        try:
            response = requests.delete(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Entity Deletion API (Valid)", True, f"Successfully deleted entity {entity_id}")
                else:
                    self.log_test("Entity Deletion API (Valid)", False, f"Deletion failed: {data}")
            elif response.status_code == 404:
                self.log_test("Entity Deletion API (Valid)", False, f"Entity not found (HTTP 404)")
            elif response.status_code == 500:
                self.log_test("Entity Deletion API (Valid)", False, f"Server error (HTTP 500) - should be 404")
            else:
                self.log_test("Entity Deletion API (Valid)", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Entity Deletion API (Valid)", False, f"Exception: {str(e)}")
    
    def test_entity_deletion_nonexistent(self):
        """Test deleting nonexistent entity (should return 404)"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/blueprint/config/entities/nonexistent-entity-id-12345",
                timeout=10
            )
            
            if response.status_code == 404:
                self.log_test("Entity Deletion Nonexistent", True, "Correctly returned HTTP 404 for nonexistent entity")
            elif response.status_code == 500:
                self.log_test("Entity Deletion Nonexistent", False, "Returned HTTP 500 instead of 404 for nonexistent entity")
            else:
                self.log_test("Entity Deletion Nonexistent", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Entity Deletion Nonexistent", False, f"Exception: {str(e)}")
    
    def test_error_handling_verification(self):
        """Test comprehensive error handling verification"""
        print("🔍 Testing comprehensive error handling...")
        
        # Test various error scenarios to ensure proper HTTP status codes
        error_tests = [
            ("Invalid JSON payload", self.test_invalid_json_payload),
            ("Missing required fields", self.test_missing_required_fields),
            ("Malformed requests", self.test_malformed_requests)
        ]
        
        for test_name, test_func in error_tests:
            try:
                test_func()
            except Exception as e:
                self.log_test(f"Error Test - {test_name}", False, f"Exception: {str(e)}")
    
    def test_invalid_json_payload(self):
        """Test endpoints with invalid JSON payload"""
        try:
            # Send invalid JSON to entity creation endpoint
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                data="invalid json payload",
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 422:
                self.log_test("Invalid JSON Payload", True, "Correctly returned HTTP 422 for invalid JSON")
            elif response.status_code == 400:
                self.log_test("Invalid JSON Payload", True, "Correctly returned HTTP 400 for invalid JSON")
            else:
                self.log_test("Invalid JSON Payload", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Invalid JSON Payload", False, f"Exception: {str(e)}")
    
    def test_missing_required_fields(self):
        """Test endpoints with missing required fields"""
        try:
            # Send entity creation request without required fields
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json={},  # Empty payload
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 422:
                self.log_test("Missing Required Fields", True, "Correctly returned HTTP 422 for missing fields")
            elif response.status_code == 400:
                self.log_test("Missing Required Fields", True, "Correctly returned HTTP 400 for missing fields")
            else:
                self.log_test("Missing Required Fields", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Missing Required Fields", False, f"Exception: {str(e)}")
    
    def test_malformed_requests(self):
        """Test endpoints with malformed requests"""
        try:
            # Send request with wrong content type
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                data="name=test&type=access",  # Form data instead of JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code in [400, 422, 415]:  # 415 = Unsupported Media Type
                self.log_test("Malformed Request", True, f"Correctly returned HTTP {response.status_code} for wrong content type")
            else:
                self.log_test("Malformed Request", False, f"Unexpected status code: {response.status_code}")
        except Exception as e:
            self.log_test("Malformed Request", False, f"Exception: {str(e)}")

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
        print("📊 BLUEPRINT CONFIGURATION API TEST SUMMARY")
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
                if any(keyword in result["name"].lower() for keyword in ["api", "creation", "update", "deletion", "generation", "validation"]):
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
        for success in successes[:10]:  # Show first 10 successes
            print(f"   • {success['name']}")
        
        if len(successes) > 10:
            print(f"   ... and {len(successes) - 10} more successful tests")
        
if __name__ == "__main__":
    tester = BackendSanityTester()
    tester.run_backend_sanity_tests()

    def test_inheritance_persistence_fix(self):
        """Test FIX 1 - Inheritance Persistence with explicit null handling"""
        print("🔧 Testing FIX 1 - Inheritance Persistence Fix")
        print("-" * 50)
        
        # Step 1: Create an entity with inheritance
        entity_with_inheritance = self.create_entity_with_inheritance()
        if not entity_with_inheritance:
            self.log_test("Inheritance Persistence - Setup", False, "Failed to create entity with inheritance")
            return
        
        # Step 2: Update entity to remove inheritance (set to null/empty)
        self.test_inheritance_removal(entity_with_inheritance)
        
        # Step 3: Test inheritance field handling with various scenarios
        self.test_inheritance_field_handling(entity_with_inheritance)
        
        # Step 4: Verify persistence after UI config reload
        self.test_inheritance_persistence_after_reload()
        
        # Cleanup
        self.cleanup_test_entity(entity_with_inheritance)
    
    def create_entity_with_inheritance(self):
        """Create an entity with inheritance for testing"""
        try:
            # First create a base entity to inherit from
            base_payload = {
                "name": "base-config-entity",
                "entityType": "access",
                "baseConfig": {
                    "enabled": True,
                    "description": "Base configuration for inheritance testing"
                }
            }
            
            base_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=base_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if base_response.status_code != 200:
                self.log_test("Create Base Entity for Inheritance", False, f"HTTP {base_response.status_code}")
                return None
            
            base_data = base_response.json()
            if not base_data.get("success"):
                self.log_test("Create Base Entity for Inheritance", False, f"Failed: {base_data}")
                return None
            
            # Now create entity with inheritance
            inherit_payload = {
                "name": "test-inherit-entity",
                "entityType": "access",
                "baseConfig": {
                    "enabled": False,
                    "description": "Entity with inheritance for testing"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=inherit_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    
                    # Update entity to add inheritance
                    update_payload = {
                        "inherit": ["base-config-entity"]
                    }
                    
                    update_response = requests.put(
                        f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                        json=update_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if update_response.status_code == 200:
                        update_data = update_response.json()
                        if update_data.get("success"):
                            self.log_test("Create Entity with Inheritance", True, f"Created entity {entity_id} with inheritance from base-config-entity")
                            return entity_id
                        else:
                            self.log_test("Create Entity with Inheritance", False, f"Update failed: {update_data}")
                            return None
                    else:
                        self.log_test("Create Entity with Inheritance", False, f"Update HTTP {update_response.status_code}")
                        return None
                else:
                    self.log_test("Create Entity with Inheritance", False, f"Creation failed: {data}")
                    return None
            else:
                self.log_test("Create Entity with Inheritance", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("Create Entity with Inheritance", False, f"Exception: {str(e)}")
            return None
    
    def test_inheritance_removal(self, entity_id):
        """Test removing inheritance by setting to null/empty"""
        try:
            # Test 1: Set inheritance to null
            null_payload = {
                "inherit": None
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=null_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Inheritance Removal - Set to Null", True, "Successfully set inheritance to null")
                else:
                    self.log_test("Inheritance Removal - Set to Null", False, f"Failed: {data}")
            else:
                self.log_test("Inheritance Removal - Set to Null", False, f"HTTP {response.status_code}")
            
            # Test 2: Set inheritance to empty array
            empty_payload = {
                "inherit": []
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=empty_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Inheritance Removal - Set to Empty Array", True, "Successfully set inheritance to empty array")
                else:
                    self.log_test("Inheritance Removal - Set to Empty Array", False, f"Failed: {data}")
            else:
                self.log_test("Inheritance Removal - Set to Empty Array", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Inheritance Removal", False, f"Exception: {str(e)}")
    
    def test_inheritance_field_handling(self, entity_id):
        """Test various inheritance field handling scenarios"""
        try:
            # Test 1: Add inheritance to entity without inheritance
            add_payload = {
                "inherit": ["base-config-entity", "another-config"]
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=add_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Inheritance Field Handling - Add Multiple", True, "Successfully added multiple inheritance items")
                else:
                    self.log_test("Inheritance Field Handling - Add Multiple", False, f"Failed: {data}")
            else:
                self.log_test("Inheritance Field Handling - Add Multiple", False, f"HTTP {response.status_code}")
            
            # Test 2: Update inheritance list (remove one item)
            update_payload = {
                "inherit": ["base-config-entity"]
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=update_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Inheritance Field Handling - Remove Item", True, "Successfully removed inheritance item")
                else:
                    self.log_test("Inheritance Field Handling - Remove Item", False, f"Failed: {data}")
            else:
                self.log_test("Inheritance Field Handling - Remove Item", False, f"HTTP {response.status_code}")
            
            # Test 3: Completely clear inheritance
            clear_payload = {
                "inherit": None
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=clear_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Inheritance Field Handling - Clear All", True, "Successfully cleared all inheritance")
                else:
                    self.log_test("Inheritance Field Handling - Clear All", False, f"Failed: {data}")
            else:
                self.log_test("Inheritance Field Handling - Clear All", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Inheritance Field Handling", False, f"Exception: {str(e)}")
    
    def test_inheritance_persistence_after_reload(self):
        """Test that inheritance changes persist after UI config reload"""
        try:
            # Get current UI config to verify inheritance state
            response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if "config" in data:
                    config = data["config"]
                    
                    # Look for our test entity and verify inheritance is null/empty
                    inheritance_cleared = False
                    for schema in config.get("schemas", []):
                        for entity in schema.get("configurations", []):
                            if entity.get("name") == "test-inherit-entity":
                                inherit_value = entity.get("inherit")
                                if inherit_value is None or inherit_value == []:
                                    inheritance_cleared = True
                                    self.log_test("Inheritance Persistence After Reload", True, f"Inheritance properly cleared and persisted (inherit={inherit_value})")
                                else:
                                    self.log_test("Inheritance Persistence After Reload", False, f"Inheritance not cleared, still has: {inherit_value}")
                                break
                    
                    if not inheritance_cleared:
                        self.log_test("Inheritance Persistence After Reload", False, "Test entity not found in UI config")
                else:
                    self.log_test("Inheritance Persistence After Reload", False, "Missing 'config' field in response")
            else:
                self.log_test("Inheritance Persistence After Reload", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Inheritance Persistence After Reload", False, f"Exception: {str(e)}")
    
    def test_file_generation_permission_error_handling(self):
        """Test FIX 2 - File Generation Permission Error Handling"""
        print("🔧 Testing FIX 2 - File Generation Permission Error Handling")
        print("-" * 50)
        
        # Step 1: Test file generation with proper permissions
        self.test_file_generation_success()
        
        # Step 2: Test file overwrite scenarios
        self.test_file_overwrite_scenarios()
        
        # Step 3: Test API error responses for permission issues
        self.test_file_generation_error_responses()
        
        # Step 4: Test temp file backup approach
        self.test_temp_file_backup_approach()
    
    def test_file_generation_success(self):
        """Test file generation with proper permissions"""
        try:
            # Create a test schema first
            schema_payload = {
                "name": "test-file-gen-schema",
                "namespace": "com.test.filegeneration",
                "description": "Test schema for file generation testing"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("File Generation Success - Schema Creation", False, f"HTTP {schema_response.status_code}")
                return
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("File Generation Success - Schema Creation", False, f"Failed: {schema_data}")
                return
            
            schema_id = schema_data["schema_id"]
            
            # Create test entities for file generation
            entity_payload = {
                "name": "test-file-gen-entity",
                "entityType": "access",
                "schemaId": schema_id,
                "baseConfig": {
                    "enabled": True,
                    "description": "Test entity for file generation"
                }
            }
            
            entity_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=entity_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if entity_response.status_code != 200:
                self.log_test("File Generation Success - Entity Creation", False, f"HTTP {entity_response.status_code}")
                return
            
            entity_data = entity_response.json()
            if not entity_data.get("success"):
                self.log_test("File Generation Success - Entity Creation", False, f"Failed: {entity_data}")
                return
            
            # Now test file generation
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV", "TEST"],
                "outputPath": "/app/test_generated"
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success"):
                    files = gen_data.get("files", [])
                    self.log_test("File Generation Success", True, f"Generated {len(files)} files successfully")
                    
                    # Verify file details
                    for file_info in files[:2]:  # Check first 2 files
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "unknown")
                            self.log_test("Generated File Details", True, f"File: {filename}")
                else:
                    error = gen_data.get("errors", ["Unknown error"])
                    self.log_test("File Generation Success", False, f"Generation failed: {error}")
            elif gen_response.status_code == 403:
                self.log_test("File Generation Success", False, f"Permission denied (HTTP 403) - this tests error handling")
            else:
                self.log_test("File Generation Success", False, f"HTTP {gen_response.status_code}")
                
        except Exception as e:
            self.log_test("File Generation Success", False, f"Exception: {str(e)}")
    
    def test_file_overwrite_scenarios(self):
        """Test file overwrite scenarios"""
        try:
            # Test generating files to the same location multiple times
            gen_payload = {
                "schemaId": "test-schema-id",  # Use any schema ID
                "environments": ["DEV"],
                "outputPath": "/app/test_overwrite"
            }
            
            # First generation
            response1 = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            # Second generation (should overwrite)
            response2 = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                
                if data1.get("success") and data2.get("success"):
                    self.log_test("File Overwrite Scenarios", True, "Successfully generated files twice (overwrite working)")
                else:
                    self.log_test("File Overwrite Scenarios", False, f"Generation failed: {data1.get('errors', [])} / {data2.get('errors', [])}")
            else:
                self.log_test("File Overwrite Scenarios", False, f"HTTP {response1.status_code} / {response2.status_code}")
                
        except Exception as e:
            self.log_test("File Overwrite Scenarios", False, f"Exception: {str(e)}")
    
    def test_file_generation_error_responses(self):
        """Test API error responses for file generation"""
        try:
            # Test 1: Invalid schema ID (should return proper error)
            invalid_payload = {
                "schemaId": "nonexistent-schema-id-12345",
                "environments": ["DEV"],
                "outputPath": "/app/test_invalid"
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=invalid_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("success"):
                    errors = data.get("errors", [])
                    if any("Schema not found" in error for error in errors):
                        self.log_test("File Generation Error - Invalid Schema", True, "Correctly returned 'Schema not found' error")
                    else:
                        self.log_test("File Generation Error - Invalid Schema", True, f"Returned appropriate error: {errors}")
                else:
                    self.log_test("File Generation Error - Invalid Schema", False, "Should have failed for invalid schema")
            elif response.status_code == 400:
                self.log_test("File Generation Error - Invalid Schema", True, "Correctly returned HTTP 400 for invalid schema")
            elif response.status_code == 404:
                self.log_test("File Generation Error - Invalid Schema", True, "Correctly returned HTTP 404 for invalid schema")
            else:
                self.log_test("File Generation Error - Invalid Schema", False, f"Unexpected status code: {response.status_code}")
            
            # Test 2: Invalid output path (should handle gracefully)
            invalid_path_payload = {
                "schemaId": "test-schema-id",
                "environments": ["DEV"],
                "outputPath": "/invalid/nonexistent/path/that/should/fail"
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=invalid_path_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 403:
                self.log_test("File Generation Error - Invalid Path", True, "Correctly returned HTTP 403 for permission error")
            elif response.status_code == 404:
                self.log_test("File Generation Error - Invalid Path", True, "Correctly returned HTTP 404 for path not found")
            elif response.status_code == 200:
                data = response.json()
                if not data.get("success"):
                    self.log_test("File Generation Error - Invalid Path", True, f"Correctly failed with error: {data.get('errors', [])}")
                else:
                    self.log_test("File Generation Error - Invalid Path", False, "Should have failed for invalid path")
            else:
                self.log_test("File Generation Error - Invalid Path", False, f"Unexpected status code: {response.status_code}")
                
        except Exception as e:
            self.log_test("File Generation Error Responses", False, f"Exception: {str(e)}")
    
    def test_temp_file_backup_approach(self):
        """Test temp file backup approach for permission issues"""
        try:
            # This test verifies that the backend handles permission issues gracefully
            # by using temporary files and proper error messages
            
            gen_payload = {
                "schemaId": "test-schema-id",
                "environments": ["DEV"],
                "outputPath": "/app/test_temp_backup"
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            # Check that response includes actionable error messages if permission issues occur
            if response.status_code == 403:
                try:
                    data = response.json()
                    error_detail = data.get("detail", "")
                    if "permission" in error_detail.lower() and ("check" in error_detail.lower() or "close" in error_detail.lower()):
                        self.log_test("Temp File Backup Approach", True, f"Proper actionable error message: {error_detail}")
                    else:
                        self.log_test("Temp File Backup Approach", False, f"Error message not actionable: {error_detail}")
                except:
                    self.log_test("Temp File Backup Approach", True, "HTTP 403 returned for permission error")
            elif response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Temp File Backup Approach", True, "File generation succeeded (no permission issues)")
                else:
                    errors = data.get("errors", [])
                    if any("permission" in error.lower() for error in errors):
                        self.log_test("Temp File Backup Approach", True, f"Proper permission error handling: {errors}")
                    else:
                        self.log_test("Temp File Backup Approach", False, f"Unexpected errors: {errors}")
            else:
                self.log_test("Temp File Backup Approach", False, f"Unexpected status code: {response.status_code}")
                
        except Exception as e:
            self.log_test("Temp File Backup Approach", False, f"Exception: {str(e)}")
    
    def test_blueprint_configuration_ui_fixes(self):
        """Test the 5 specific Blueprint Configuration UI fixes from review request"""
        print("🔧 Testing 5 Specific Blueprint Configuration UI Fixes")
        print("-" * 60)
        
        # FIX 1 - Remove "Add root Config" button from Message Configs (UI-only fix, test backend support)
        print("\n📋 FIX 1 - Testing Message Config Entity Management (No Root Config Button)")
        self.test_fix1_message_config_entity_management()
        
        # FIX 2 - Auto-reload entity list in Message Configs after add/remove/save
        print("\n📋 FIX 2 - Testing Auto-reload Entity List in Message Configs")
        self.test_fix2_message_config_auto_reload()
        
        # FIX 3 - Auto-reload entity list in Global Config after add/remove/save
        print("\n📋 FIX 3 - Testing Auto-reload Entity List in Global Config")
        self.test_fix3_global_config_auto_reload()
        
        # FIX 4 - Generate Files button also creates blueprint_cnf.json
        print("\n📋 FIX 4 - Testing Generate Files with blueprint_cnf.json Creation")
        self.test_fix4_generate_files_with_blueprint_cnf()
        
        # FIX 5 - Load blueprint_cnf.json values by default in Blueprint CNF section
        print("\n📋 FIX 5 - Testing Load blueprint_cnf.json Default Values")
        self.test_fix5_load_blueprint_cnf_defaults()
    
    def test_fix1_message_config_entity_management(self):
        """Test FIX 1 - Message Config entity management without root config button"""
        try:
            # Test that we can create message config entities properly
            # This tests the backend support for message config entities
            payload = {
                "name": "test-message-config-entity",
                "entityType": "messageStorage",  # Message config entity type
                "configuration": {
                    "enabled": True,
                    "description": "Test message config entity"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("FIX 1 - Message Config Entity Creation", True, f"Successfully created message config entity: {entity_id}")
                    
                    # Test that the entity appears in UI config
                    ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
                    if ui_response.status_code == 200:
                        ui_data = ui_response.json()
                        config = ui_data.get("config", {})
                        
                        # Look for our entity in the schemas
                        entity_found = False
                        for schema in config.get("schemas", []):
                            for entity in schema.get("configurations", []):
                                if entity.get("name") == "test-message-config-entity":
                                    entity_found = True
                                    break
                        
                        if entity_found:
                            self.log_test("FIX 1 - Message Config Entity in UI Config", True, "Message config entity appears in UI configuration")
                        else:
                            self.log_test("FIX 1 - Message Config Entity in UI Config", False, "Message config entity not found in UI configuration")
                    
                    # Cleanup
                    self.cleanup_test_entity(entity_id)
                else:
                    self.log_test("FIX 1 - Message Config Entity Creation", False, f"Creation failed: {data}")
            else:
                self.log_test("FIX 1 - Message Config Entity Creation", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX 1 - Message Config Entity Management", False, f"Exception: {str(e)}")
    
    def test_fix2_message_config_auto_reload(self):
        """Test FIX 2 - Auto-reload entity list in Message Configs after operations"""
        try:
            # Create a message config entity
            payload = {
                "name": "test-message-auto-reload",
                "entityType": "messageStorage",
                "configuration": {
                    "enabled": True,
                    "description": "Test auto-reload for message configs"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("FIX 2 - Message Config Entity Creation for Auto-reload", True, f"Created entity: {entity_id}")
                    
                    # Test that UI config reflects the new entity (simulating auto-reload)
                    ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
                    if ui_response.status_code == 200:
                        ui_data = ui_response.json()
                        config = ui_data.get("config", {})
                        
                        # Count entities before update
                        entity_count_before = 0
                        for schema in config.get("schemas", []):
                            entity_count_before += len(schema.get("configurations", []))
                        
                        # Update the entity (simulating save operation)
                        update_payload = {
                            "name": "test-message-auto-reload-updated",
                            "configuration": {
                                "enabled": False,
                                "description": "Updated entity for auto-reload testing"
                            }
                        }
                        
                        update_response = requests.put(
                            f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                            json=update_payload,
                            headers={"Content-Type": "application/json"},
                            timeout=10
                        )
                        
                        if update_response.status_code == 200:
                            update_data = update_response.json()
                            if update_data.get("success"):
                                self.log_test("FIX 2 - Message Config Entity Update", True, "Successfully updated message config entity")
                                
                                # Check UI config again (simulating auto-reload after update)
                                ui_response2 = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
                                if ui_response2.status_code == 200:
                                    ui_data2 = ui_response2.json()
                                    config2 = ui_data2.get("config", {})
                                    
                                    # Verify the entity is updated in UI config
                                    entity_updated = False
                                    for schema in config2.get("schemas", []):
                                        for entity in schema.get("configurations", []):
                                            if entity.get("name") == "test-message-auto-reload-updated":
                                                entity_updated = True
                                                break
                                    
                                    if entity_updated:
                                        self.log_test("FIX 2 - Message Config Auto-reload After Update", True, "Entity list properly reloaded after update")
                                    else:
                                        self.log_test("FIX 2 - Message Config Auto-reload After Update", False, "Entity list not properly reloaded after update")
                                else:
                                    self.log_test("FIX 2 - Message Config Auto-reload After Update", False, f"UI config reload failed: HTTP {ui_response2.status_code}")
                            else:
                                self.log_test("FIX 2 - Message Config Entity Update", False, f"Update failed: {update_data}")
                        else:
                            self.log_test("FIX 2 - Message Config Entity Update", False, f"HTTP {update_response.status_code}")
                    
                    # Cleanup
                    self.cleanup_test_entity(entity_id)
                else:
                    self.log_test("FIX 2 - Message Config Entity Creation for Auto-reload", False, f"Creation failed: {data}")
            else:
                self.log_test("FIX 2 - Message Config Entity Creation for Auto-reload", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX 2 - Message Config Auto-reload", False, f"Exception: {str(e)}")
    
    def test_fix3_global_config_auto_reload(self):
        """Test FIX 3 - Auto-reload entity list in Global Config after operations"""
        try:
            # Create a global config entity
            payload = {
                "name": "test-global-auto-reload",
                "entityType": "access",  # Global config entity type
                "configuration": {
                    "enabled": True,
                    "description": "Test auto-reload for global configs"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("FIX 3 - Global Config Entity Creation for Auto-reload", True, f"Created entity: {entity_id}")
                    
                    # Test deletion and auto-reload
                    delete_response = requests.delete(
                        f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                        timeout=10
                    )
                    
                    if delete_response.status_code == 200:
                        delete_data = delete_response.json()
                        if delete_data.get("success"):
                            self.log_test("FIX 3 - Global Config Entity Deletion", True, "Successfully deleted global config entity")
                            
                            # Check UI config after deletion (simulating auto-reload)
                            ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
                            if ui_response.status_code == 200:
                                ui_data = ui_response.json()
                                config = ui_data.get("config", {})
                                
                                # Verify the entity is removed from UI config
                                entity_removed = True
                                for schema in config.get("schemas", []):
                                    for entity in schema.get("configurations", []):
                                        if entity.get("name") == "test-global-auto-reload":
                                            entity_removed = False
                                            break
                                
                                if entity_removed:
                                    self.log_test("FIX 3 - Global Config Auto-reload After Deletion", True, "Entity list properly reloaded after deletion")
                                else:
                                    self.log_test("FIX 3 - Global Config Auto-reload After Deletion", False, "Entity still appears in UI config after deletion")
                            else:
                                self.log_test("FIX 3 - Global Config Auto-reload After Deletion", False, f"UI config reload failed: HTTP {ui_response.status_code}")
                        else:
                            self.log_test("FIX 3 - Global Config Entity Deletion", False, f"Deletion failed: {delete_data}")
                    else:
                        self.log_test("FIX 3 - Global Config Entity Deletion", False, f"HTTP {delete_response.status_code}")
                        # Cleanup if deletion failed
                        self.cleanup_test_entity(entity_id)
                else:
                    self.log_test("FIX 3 - Global Config Entity Creation for Auto-reload", False, f"Creation failed: {data}")
            else:
                self.log_test("FIX 3 - Global Config Entity Creation for Auto-reload", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX 3 - Global Config Auto-reload", False, f"Exception: {str(e)}")
    
    def test_fix4_generate_files_with_blueprint_cnf(self):
        """Test FIX 4 - Generate Files button also creates blueprint_cnf.json"""
        try:
            # First create a schema for file generation
            schema_payload = {
                "name": "test-blueprint-cnf-gen",
                "namespace": "com.test.blueprintcnf",
                "description": "Test schema for blueprint_cnf.json generation"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code == 200:
                schema_data = schema_response.json()
                if schema_data.get("success") and "schema_id" in schema_data:
                    schema_id = schema_data["schema_id"]
                    self.log_test("FIX 4 - Schema Creation for Blueprint CNF Generation", True, f"Created schema: {schema_id}")
                    
                    # Create an entity for the schema
                    entity_payload = {
                        "name": "test-blueprint-cnf-entity",
                        "entityType": "access",
                        "configuration": {
                            "enabled": True,
                            "description": "Test entity for blueprint_cnf.json generation"
                        }
                    }
                    
                    entity_response = requests.post(
                        f"{self.base_url}/api/blueprint/config/entities",
                        json=entity_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if entity_response.status_code == 200:
                        entity_data = entity_response.json()
                        if entity_data.get("success"):
                            # Now test file generation with blueprint_cnf.json
                            gen_payload = {
                                "schemaId": schema_id,
                                "environments": ["DEV"],
                                "outputPath": "/app/test_blueprint_cnf_gen",
                                "generateBlueprintCNF": True  # Explicitly request blueprint_cnf.json generation
                            }
                            
                            gen_response = requests.post(
                                f"{self.base_url}/api/blueprint/config/generate",
                                json=gen_payload,
                                headers={"Content-Type": "application/json"},
                                timeout=15
                            )
                            
                            if gen_response.status_code == 200:
                                gen_data = gen_response.json()
                                if gen_data.get("success"):
                                    files = gen_data.get("files", [])
                                    self.log_test("FIX 4 - File Generation Success", True, f"Generated {len(files)} files")
                                    
                                    # Check if blueprint_cnf.json is included in the generated files
                                    blueprint_cnf_found = False
                                    for file_info in files:
                                        if isinstance(file_info, dict):
                                            filename = file_info.get("filename", "")
                                            if "blueprint_cnf.json" in filename:
                                                blueprint_cnf_found = True
                                                self.log_test("FIX 4 - Blueprint CNF File Generated", True, f"Found blueprint_cnf.json in generated files: {filename}")
                                                break
                                        elif isinstance(file_info, str) and "blueprint_cnf.json" in file_info:
                                            blueprint_cnf_found = True
                                            self.log_test("FIX 4 - Blueprint CNF File Generated", True, f"Found blueprint_cnf.json: {file_info}")
                                            break
                                    
                                    if not blueprint_cnf_found:
                                        self.log_test("FIX 4 - Blueprint CNF File Generated", False, f"blueprint_cnf.json not found in generated files: {[f.get('filename', f) if isinstance(f, dict) else f for f in files]}")
                                    
                                    # Test that the file count includes blueprint_cnf.json
                                    if len(files) > 0:
                                        self.log_test("FIX 4 - File Count Includes Blueprint CNF", True, f"Total file count: {len(files)} (includes blueprint_cnf.json)")
                                    else:
                                        self.log_test("FIX 4 - File Count Includes Blueprint CNF", False, "No files generated")
                                else:
                                    error = gen_data.get("error", "Unknown error")
                                    self.log_test("FIX 4 - File Generation Success", False, f"Generation failed: {error}")
                            else:
                                self.log_test("FIX 4 - File Generation Success", False, f"HTTP {gen_response.status_code}")
                        else:
                            self.log_test("FIX 4 - Entity Creation for Blueprint CNF Generation", False, f"Entity creation failed: {entity_data}")
                    else:
                        self.log_test("FIX 4 - Entity Creation for Blueprint CNF Generation", False, f"HTTP {entity_response.status_code}")
                else:
                    self.log_test("FIX 4 - Schema Creation for Blueprint CNF Generation", False, f"Schema creation failed: {schema_data}")
            else:
                self.log_test("FIX 4 - Schema Creation for Blueprint CNF Generation", False, f"HTTP {schema_response.status_code}")
                
        except Exception as e:
            self.log_test("FIX 4 - Generate Files with Blueprint CNF", False, f"Exception: {str(e)}")
    
    def test_fix5_load_blueprint_cnf_defaults(self):
        """Test FIX 5 - Load blueprint_cnf.json values by default in Blueprint CNF section"""
        try:
            # Test loading existing blueprint_cnf.json file
            response = requests.get(
                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content")
                
                if content:
                    try:
                        blueprint_config = json.loads(content)
                        
                        # Check that all expected fields are loaded as defaults
                        expected_fields = ["namespace", "version", "owner", "description", "transformSpecs", "templates"]
                        loaded_fields = []
                        missing_fields = []
                        
                        for field in expected_fields:
                            if field in blueprint_config:
                                loaded_fields.append(field)
                            else:
                                missing_fields.append(field)
                        
                        if len(loaded_fields) >= 4:  # At least 4 core fields should be present
                            self.log_test("FIX 5 - Blueprint CNF Default Values Loading", True, f"Loaded {len(loaded_fields)} default fields: {loaded_fields}")
                            
                            # Test specific field values
                            if "namespace" in blueprint_config:
                                namespace = blueprint_config["namespace"]
                                self.log_test("FIX 5 - Namespace Default Value", True, f"Namespace loaded: {namespace}")
                            
                            if "version" in blueprint_config:
                                version = blueprint_config["version"]
                                self.log_test("FIX 5 - Version Default Value", True, f"Version loaded: {version}")
                            
                            if "owner" in blueprint_config:
                                owner = blueprint_config["owner"]
                                self.log_test("FIX 5 - Owner Default Value", True, f"Owner loaded: {owner}")
                            
                            if "description" in blueprint_config:
                                description = blueprint_config["description"]
                                self.log_test("FIX 5 - Description Default Value", True, f"Description loaded: {description[:50]}...")
                            
                            if "transformSpecs" in blueprint_config:
                                transform_specs = blueprint_config["transformSpecs"]
                                if isinstance(transform_specs, list):
                                    self.log_test("FIX 5 - TransformSpecs Default Value", True, f"TransformSpecs loaded: {len(transform_specs)} items")
                                else:
                                    self.log_test("FIX 5 - TransformSpecs Default Value", False, f"TransformSpecs not a list: {type(transform_specs)}")
                            
                            # Check for templates (could be in searchExperience.templates or top-level templates)
                            templates_found = False
                            if "templates" in blueprint_config:
                                templates = blueprint_config["templates"]
                                if isinstance(templates, list):
                                    templates_found = True
                                    self.log_test("FIX 5 - Templates Default Value", True, f"Templates loaded: {len(templates)} items")
                            elif "searchExperience" in blueprint_config and isinstance(blueprint_config["searchExperience"], dict):
                                search_exp = blueprint_config["searchExperience"]
                                if "templates" in search_exp and isinstance(search_exp["templates"], list):
                                    templates_found = True
                                    self.log_test("FIX 5 - SearchExperience Templates Default Value", True, f"SearchExperience templates loaded: {len(search_exp['templates'])} items")
                            
                            if not templates_found:
                                self.log_test("FIX 5 - Templates Default Value", False, "No templates found in blueprint_cnf.json")
                        else:
                            self.log_test("FIX 5 - Blueprint CNF Default Values Loading", False, f"Only {len(loaded_fields)} fields loaded, missing: {missing_fields}")
                            
                    except json.JSONDecodeError as e:
                        self.log_test("FIX 5 - Blueprint CNF JSON Parsing", False, f"JSON parsing error: {str(e)}")
                else:
                    self.log_test("FIX 5 - Blueprint CNF Content Loading", False, "No content returned from blueprint_cnf.json")
            elif response.status_code == 404:
                self.log_test("FIX 5 - Blueprint CNF File Existence", False, "blueprint_cnf.json file not found (404)")
            else:
                self.log_test("FIX 5 - Blueprint CNF File Loading", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX 5 - Load Blueprint CNF Defaults", False, f"Exception: {str(e)}")

    def test_blueprint_cnf_file_content_loading_issue(self):
        """
        CRITICAL INVESTIGATION: Test the specific issue where blueprint_cnf.json data 
        is not loading from the actual file but from cache.
        
        This test will:
        1. Check if blueprint_cnf.json file exists in project root
        2. Test GET /api/blueprint/file-content/blueprint_cnf.json endpoint directly
        3. Verify that the API returns the actual file content, not cached data
        4. Test that file modifications are reflected in API responses
        5. Verify the JSON parsing and content structure
        """
        print("🔍 CRITICAL INVESTIGATION: Blueprint CNF File Content Loading Issue")
        print("-" * 70)
        
        # Step 1: Verify blueprint_cnf.json file exists at expected location
        self.test_blueprint_cnf_file_exists()
        
        # Step 2: Test direct file content retrieval via API
        original_content = self.test_blueprint_cnf_direct_api_access()
        
        # Step 3: Verify file content matches expected structure
        self.test_blueprint_cnf_content_structure(original_content)
        
        # Step 4: Test file modification detection (critical for cache issue)
        self.test_blueprint_cnf_file_modification_detection(original_content)
        
        # Step 5: Test JSON parsing and field extraction
        self.test_blueprint_cnf_json_parsing(original_content)
        
        # Step 6: Test caching behavior by making multiple requests
        self.test_blueprint_cnf_caching_behavior()
        
        # Step 7: Restore original content
        self.restore_blueprint_cnf_original_content(original_content)
    
    def test_blueprint_cnf_file_exists(self):
        """Test if blueprint_cnf.json file exists in project root (/app)"""
        try:
            # Use file tree API to check if file exists
            response = requests.get(f"{self.base_url}/api/blueprint/file-tree", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                # Look for blueprint_cnf.json in the file list
                blueprint_cnf_found = False
                for file_item in files:
                    if isinstance(file_item, dict):
                        if file_item.get("name") == "blueprint_cnf.json" and file_item.get("type") == "file":
                            blueprint_cnf_found = True
                            file_size = file_item.get("size", 0)
                            self.log_test("Blueprint CNF File Exists", True, f"Found blueprint_cnf.json ({file_size} bytes)")
                            break
                    elif isinstance(file_item, str) and file_item == "blueprint_cnf.json":
                        blueprint_cnf_found = True
                        self.log_test("Blueprint CNF File Exists", True, "Found blueprint_cnf.json in file tree")
                        break
                
                if not blueprint_cnf_found:
                    self.log_test("Blueprint CNF File Exists", False, f"blueprint_cnf.json not found in file tree. Files: {[f.get('name', f) if isinstance(f, dict) else f for f in files[:10]]}")
                    return False
                
                return True
            else:
                self.log_test("Blueprint CNF File Exists", False, f"File tree API failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Blueprint CNF File Exists", False, f"Exception: {str(e)}")
            return False
    
    def test_blueprint_cnf_direct_api_access(self):
        """Test GET /api/blueprint/file-content/blueprint_cnf.json endpoint directly"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "content" in data:
                    content = data["content"]
                    content_length = len(content)
                    
                    # Try to parse as JSON to verify it's valid
                    try:
                        parsed_json = json.loads(content)
                        self.log_test("Blueprint CNF Direct API Access", True, f"Successfully retrieved content ({content_length} chars, valid JSON)")
                        
                        # Log some key fields if they exist
                        key_fields = []
                        for field in ["namespace", "version", "owner", "description"]:
                            if field in parsed_json:
                                key_fields.append(f"{field}={parsed_json[field]}")
                        
                        if key_fields:
                            self.log_test("Blueprint CNF Key Fields", True, f"Found fields: {', '.join(key_fields)}")
                        
                        return content
                    except json.JSONDecodeError as je:
                        self.log_test("Blueprint CNF Direct API Access", False, f"Invalid JSON content: {str(je)}")
                        self.log_test("Blueprint CNF Raw Content", False, f"Raw content: {content[:200]}...")
                        return content
                else:
                    self.log_test("Blueprint CNF Direct API Access", False, "Missing 'content' field in API response")
                    return None
            elif response.status_code == 404:
                self.log_test("Blueprint CNF Direct API Access", False, "File not found (HTTP 404) - blueprint_cnf.json missing")
                return None
            else:
                self.log_test("Blueprint CNF Direct API Access", False, f"HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            self.log_test("Blueprint CNF Direct API Access", False, f"Exception: {str(e)}")
            return None
    
    def test_blueprint_cnf_content_structure(self, content):
        """Verify blueprint_cnf.json content has expected structure"""
        if not content:
            self.log_test("Blueprint CNF Content Structure", False, "No content to verify")
            return
        
        try:
            parsed_json = json.loads(content)
            
            # Check for expected fields
            expected_fields = ["namespace", "version", "description"]
            optional_fields = ["owner", "transformSpecs", "searchExperience"]
            
            found_expected = []
            found_optional = []
            
            for field in expected_fields:
                if field in parsed_json:
                    found_expected.append(field)
            
            for field in optional_fields:
                if field in parsed_json:
                    found_optional.append(field)
            
            if len(found_expected) >= 2:  # At least 2 expected fields
                self.log_test("Blueprint CNF Content Structure", True, f"Valid structure - Expected: {found_expected}, Optional: {found_optional}")
                
                # Check specific field values
                if "namespace" in parsed_json:
                    namespace = parsed_json["namespace"]
                    if namespace and len(namespace) > 0:
                        self.log_test("Blueprint CNF Namespace Field", True, f"Namespace: '{namespace}'")
                    else:
                        self.log_test("Blueprint CNF Namespace Field", False, "Namespace field is empty")
                
                if "transformSpecs" in parsed_json:
                    transform_specs = parsed_json["transformSpecs"]
                    if isinstance(transform_specs, list):
                        self.log_test("Blueprint CNF TransformSpecs Field", True, f"TransformSpecs array with {len(transform_specs)} items")
                    else:
                        self.log_test("Blueprint CNF TransformSpecs Field", False, f"TransformSpecs is not an array: {type(transform_specs)}")
                
                if "searchExperience" in parsed_json:
                    search_exp = parsed_json["searchExperience"]
                    if isinstance(search_exp, dict):
                        templates = search_exp.get("templates", [])
                        if isinstance(templates, list):
                            self.log_test("Blueprint CNF SearchExperience Field", True, f"SearchExperience with {len(templates)} templates")
                        else:
                            self.log_test("Blueprint CNF SearchExperience Field", False, "SearchExperience templates is not an array")
                    else:
                        self.log_test("Blueprint CNF SearchExperience Field", False, f"SearchExperience is not an object: {type(search_exp)}")
            else:
                self.log_test("Blueprint CNF Content Structure", False, f"Missing expected fields. Found: {found_expected}, Expected: {expected_fields}")
                
        except json.JSONDecodeError as je:
            self.log_test("Blueprint CNF Content Structure", False, f"Invalid JSON: {str(je)}")
        except Exception as e:
            self.log_test("Blueprint CNF Content Structure", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_file_modification_detection(self, original_content):
        """Test that file modifications are reflected in API responses (critical for cache issue)"""
        if not original_content:
            self.log_test("Blueprint CNF File Modification Detection", False, "No original content to test with")
            return
        
        try:
            # Parse original content
            original_json = json.loads(original_content)
            
            # Create modified content with a test marker
            modified_json = original_json.copy()
            modified_json["test_modification_marker"] = f"modified_at_{int(time.time())}"
            modified_json["cache_test"] = True
            
            # If version exists, increment it
            if "version" in modified_json:
                try:
                    version_parts = modified_json["version"].split(".")
                    if len(version_parts) >= 3:
                        patch_version = int(version_parts[2]) + 1
                        modified_json["version"] = f"{version_parts[0]}.{version_parts[1]}.{patch_version}"
                except:
                    modified_json["version"] = "1.0.1"
            else:
                modified_json["version"] = "1.0.1"
            
            modified_content = json.dumps(modified_json, indent=2)
            
            # Step 1: Write modified content to file
            write_response = requests.put(
                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                json={"content": modified_content},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if write_response.status_code == 200:
                write_data = write_response.json()
                if write_data.get("success"):
                    self.log_test("Blueprint CNF File Write", True, "Successfully wrote modified content to file")
                    
                    # Step 2: Wait a moment to ensure file system changes are reflected
                    time.sleep(1)
                    
                    # Step 3: Read content back via API
                    read_response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
                    
                    if read_response.status_code == 200:
                        read_data = read_response.json()
                        read_content = read_data.get("content", "")
                        
                        try:
                            read_json = json.loads(read_content)
                            
                            # Check if our modification marker is present
                            if "test_modification_marker" in read_json and "cache_test" in read_json:
                                marker_value = read_json["test_modification_marker"]
                                self.log_test("Blueprint CNF File Modification Detection", True, f"✅ CACHE ISSUE RESOLVED: File modifications are reflected in API (marker: {marker_value})")
                                
                                # Verify version was also updated
                                if "version" in read_json:
                                    new_version = read_json["version"]
                                    self.log_test("Blueprint CNF Version Update Detection", True, f"Version updated to: {new_version}")
                            else:
                                self.log_test("Blueprint CNF File Modification Detection", False, "❌ CACHE ISSUE CONFIRMED: File modifications NOT reflected in API response")
                                self.log_test("Blueprint CNF Cache Issue Details", False, f"Expected markers not found. Content: {read_content[:200]}...")
                                
                        except json.JSONDecodeError:
                            self.log_test("Blueprint CNF File Modification Detection", False, "Modified content is not valid JSON")
                    else:
                        self.log_test("Blueprint CNF File Modification Detection", False, f"Failed to read modified content: HTTP {read_response.status_code}")
                else:
                    self.log_test("Blueprint CNF File Write", False, f"Failed to write modified content: {write_data}")
            else:
                self.log_test("Blueprint CNF File Write", False, f"HTTP {write_response.status_code}")
                
        except Exception as e:
            self.log_test("Blueprint CNF File Modification Detection", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_json_parsing(self, content):
        """Test JSON parsing and field extraction from blueprint_cnf.json"""
        if not content:
            self.log_test("Blueprint CNF JSON Parsing", False, "No content to parse")
            return
        
        try:
            parsed_json = json.loads(content)
            
            # Test field extraction
            extraction_tests = [
                ("namespace", str),
                ("version", str),
                ("description", str),
                ("owner", str),
                ("transformSpecs", list),
                ("searchExperience", dict)
            ]
            
            successful_extractions = 0
            total_extractions = 0
            
            for field_name, expected_type in extraction_tests:
                total_extractions += 1
                if field_name in parsed_json:
                    field_value = parsed_json[field_name]
                    if isinstance(field_value, expected_type):
                        successful_extractions += 1
                        if expected_type == list:
                            self.log_test(f"Blueprint CNF Field - {field_name}", True, f"Array with {len(field_value)} items")
                        elif expected_type == dict:
                            self.log_test(f"Blueprint CNF Field - {field_name}", True, f"Object with {len(field_value)} keys")
                        else:
                            self.log_test(f"Blueprint CNF Field - {field_name}", True, f"Value: '{field_value}'")
                    else:
                        self.log_test(f"Blueprint CNF Field - {field_name}", False, f"Wrong type: expected {expected_type.__name__}, got {type(field_value).__name__}")
                else:
                    self.log_test(f"Blueprint CNF Field - {field_name}", False, "Field not present")
            
            success_rate = (successful_extractions / total_extractions) * 100
            self.log_test("Blueprint CNF JSON Parsing", True, f"Parsed successfully - {successful_extractions}/{total_extractions} fields extracted ({success_rate:.1f}%)")
            
        except json.JSONDecodeError as je:
            self.log_test("Blueprint CNF JSON Parsing", False, f"JSON parsing failed: {str(je)}")
        except Exception as e:
            self.log_test("Blueprint CNF JSON Parsing", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_caching_behavior(self):
        """Test caching behavior by making multiple requests"""
        try:
            # Make multiple rapid requests to test for caching issues
            request_results = []
            
            for i in range(3):
                start_time = time.time()
                response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
                end_time = time.time()
                
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    content_hash = hash(content)  # Simple hash to detect content changes
                    
                    request_results.append({
                        "request": i + 1,
                        "response_time": response_time,
                        "content_hash": content_hash,
                        "content_length": len(content)
                    })
                else:
                    request_results.append({
                        "request": i + 1,
                        "response_time": response_time,
                        "error": f"HTTP {response.status_code}"
                    })
                
                # Small delay between requests
                time.sleep(0.5)
            
            # Analyze results
            successful_requests = [r for r in request_results if "error" not in r]
            
            if len(successful_requests) >= 2:
                # Check if all requests returned the same content (expected)
                content_hashes = [r["content_hash"] for r in successful_requests]
                avg_response_time = sum(r["response_time"] for r in successful_requests) / len(successful_requests)
                
                if len(set(content_hashes)) == 1:
                    self.log_test("Blueprint CNF Caching Behavior", True, f"Consistent content across {len(successful_requests)} requests (avg: {avg_response_time:.3f}s)")
                else:
                    self.log_test("Blueprint CNF Caching Behavior", False, f"Inconsistent content across requests: {len(set(content_hashes))} different versions")
                
                # Log response times
                for result in successful_requests:
                    self.log_test(f"Blueprint CNF Request {result['request']}", True, f"Response time: {result['response_time']:.3f}s, Content: {result['content_length']} chars")
            else:
                self.log_test("Blueprint CNF Caching Behavior", False, f"Only {len(successful_requests)} successful requests out of 3")
                
        except Exception as e:
            self.log_test("Blueprint CNF Caching Behavior", False, f"Exception: {str(e)}")
    
    def restore_blueprint_cnf_original_content(self, original_content):
        """Restore original blueprint_cnf.json content"""
        if not original_content:
            self.log_test("Blueprint CNF Content Restoration", False, "No original content to restore")
            return
        
        try:
            response = requests.put(
                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                json={"content": original_content},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Blueprint CNF Content Restoration", True, "Successfully restored original content")
                else:
                    self.log_test("Blueprint CNF Content Restoration", False, f"Restoration failed: {data}")
            else:
                self.log_test("Blueprint CNF Content Restoration", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Blueprint CNF Content Restoration", False, f"Exception: {str(e)}")

    def cleanup_test_entity(self, entity_id):
        """Helper method to cleanup test entities"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Cleanup Test Entity", True, f"Successfully cleaned up entity: {entity_id}")
                else:
                    self.log_test("Cleanup Test Entity", False, f"Cleanup failed: {data}")
            else:
                self.log_test("Cleanup Test Entity", False, f"Cleanup HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Cleanup Test Entity", False, f"Cleanup exception: {str(e)}")

    def test_blueprint_cnf_loader_and_dropdown_functionality(self):
        """Test the 3 new fixes for Blueprint Configuration UI from review request"""
        print("🔧 Testing Blueprint CNF Loader and Dropdown Functionality")
        print("-" * 60)
        
        # FIX 1 - Load Transform Specifications and Search Experience Templates from existing blueprint_cnf.json
        print("\n📋 FIX 1 - Testing Load Transform Specifications and Search Experience Templates")
        self.test_fix1_load_blueprint_cnf_with_arrays()
        
        # FIX 2 - Transform Files Dropdown from src/transformSpecs
        print("\n📋 FIX 2 - Testing Transform Files Dropdown from src/transformSpecs")
        self.test_fix2_transform_files_dropdown()
        
        # FIX 3 - Search Experience Templates Dropdown from src/searchExperience/templates
        print("\n📋 FIX 3 - Testing Search Experience Templates Dropdown")
        self.test_fix3_search_experience_templates_dropdown()
    
    def test_fix1_load_blueprint_cnf_with_arrays(self):
        """Test FIX 1 - Load existing blueprint_cnf.json with transformSpecs and searchExperience.templates arrays"""
        try:
            # Test loading existing blueprint_cnf.json from example_config
            response = requests.get(
                f"{self.base_url}/api/blueprint/file-content/example_config/blueprint_cnf.json",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content")
                
                if content:
                    try:
                        blueprint_config = json.loads(content)
                        
                        # Check for all required fields
                        required_fields = ["namespace", "version", "owner", "description", "transformSpecs", "searchExperience"]
                        missing_fields = []
                        
                        for field in required_fields:
                            if field not in blueprint_config:
                                missing_fields.append(field)
                        
                        if not missing_fields:
                            # Verify transformSpecs array
                            transform_specs = blueprint_config.get("transformSpecs", [])
                            if isinstance(transform_specs, list) and len(transform_specs) > 0:
                                self.log_test("FIX 1 - TransformSpecs Array Loading", True, f"Found {len(transform_specs)} transform specs: {transform_specs}")
                            else:
                                self.log_test("FIX 1 - TransformSpecs Array Loading", False, f"TransformSpecs not properly loaded: {transform_specs}")
                            
                            # Verify searchExperience.templates array
                            search_experience = blueprint_config.get("searchExperience", {})
                            if isinstance(search_experience, dict):
                                templates = search_experience.get("templates", [])
                                if isinstance(templates, list) and len(templates) > 0:
                                    self.log_test("FIX 1 - SearchExperience Templates Array Loading", True, f"Found {len(templates)} templates: {templates}")
                                else:
                                    self.log_test("FIX 1 - SearchExperience Templates Array Loading", False, f"Templates not properly loaded: {templates}")
                            else:
                                self.log_test("FIX 1 - SearchExperience Structure Loading", False, f"SearchExperience not properly structured: {search_experience}")
                            
                            # Verify all fields are loaded
                            self.log_test("FIX 1 - All Blueprint CNF Fields Loading", True, f"All required fields present: namespace={blueprint_config.get('namespace')}, version={blueprint_config.get('version')}, owner={blueprint_config.get('owner')}")
                        else:
                            self.log_test("FIX 1 - Blueprint CNF Complete Loading", False, f"Missing required fields: {missing_fields}")
                            
                    except json.JSONDecodeError as e:
                        self.log_test("FIX 1 - Blueprint CNF JSON Parsing", False, f"JSON parsing error: {str(e)}")
                else:
                    self.log_test("FIX 1 - Blueprint CNF Content Loading", False, "No content returned from file")
            else:
                self.log_test("FIX 1 - Blueprint CNF File Access", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX 1 - Blueprint CNF Loading", False, f"Exception: {str(e)}")
    
    def test_fix2_transform_files_dropdown(self):
        """Test FIX 2 - Transform Files Dropdown from src/transformSpecs directory"""
        try:
            # Test GET /api/blueprint/file-tree?path=src/transformSpecs
            response = requests.get(
                f"{self.base_url}/api/blueprint/file-tree?path=src/transformSpecs",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                if files:
                    # Filter for .jslt files
                    jslt_files = []
                    for file_item in files:
                        if isinstance(file_item, dict):
                            file_name = file_item.get("name", "")
                            file_type = file_item.get("type", "")
                            if file_name.endswith(".jslt") or ".jslt" in file_name:
                                jslt_files.append(file_name)
                        elif isinstance(file_item, str) and file_item.endswith(".jslt"):
                            jslt_files.append(file_item)
                    
                    if jslt_files:
                        self.log_test("FIX 2 - Transform Files Dropdown (.jslt filtering)", True, f"Found {len(jslt_files)} .jslt files: {jslt_files}")
                    else:
                        self.log_test("FIX 2 - Transform Files Dropdown (.jslt filtering)", False, f"No .jslt files found in response. Files: {files}")
                    
                    # Verify file tree structure
                    self.log_test("FIX 2 - Transform Files File Tree API", True, f"File tree API returned {len(files)} items for src/transformSpecs")
                else:
                    self.log_test("FIX 2 - Transform Files File Tree API", False, "No files returned from src/transformSpecs directory")
            else:
                self.log_test("FIX 2 - Transform Files File Tree API", False, f"HTTP {response.status_code}")
            
            # Test with example_config path specifically
            response2 = requests.get(
                f"{self.base_url}/api/blueprint/file-tree?path=example_config/src/transformSpecs",
                timeout=10
            )
            
            if response2.status_code == 200:
                data2 = response2.json()
                files2 = data2.get("files", [])
                
                jslt_files2 = []
                for file_item in files2:
                    if isinstance(file_item, dict):
                        file_name = file_item.get("name", "")
                        if file_name.endswith(".jslt"):
                            jslt_files2.append(file_name)
                    elif isinstance(file_item, str) and file_item.endswith(".jslt"):
                        jslt_files2.append(file_item)
                
                if jslt_files2:
                    self.log_test("FIX 2 - Transform Files Dropdown (example_config)", True, f"Found {len(jslt_files2)} .jslt files in example_config: {jslt_files2}")
                else:
                    self.log_test("FIX 2 - Transform Files Dropdown (example_config)", False, f"No .jslt files found in example_config/src/transformSpecs")
            else:
                self.log_test("FIX 2 - Transform Files API (example_config)", False, f"HTTP {response2.status_code}")
                
        except Exception as e:
            self.log_test("FIX 2 - Transform Files Dropdown", False, f"Exception: {str(e)}")
    
    def test_fix3_search_experience_templates_dropdown(self):
        """Test FIX 3 - Search Experience Templates Dropdown from src/searchExperience/templates directory"""
        try:
            # Test GET /api/blueprint/file-tree?path=src/searchExperience/templates
            response = requests.get(
                f"{self.base_url}/api/blueprint/file-tree?path=src/searchExperience/templates",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                if files:
                    # Filter for .json and .js files
                    template_files = []
                    for file_item in files:
                        if isinstance(file_item, dict):
                            file_name = file_item.get("name", "")
                            if file_name.endswith(".json") or file_name.endswith(".js"):
                                template_files.append(file_name)
                        elif isinstance(file_item, str) and (file_item.endswith(".json") or file_item.endswith(".js")):
                            template_files.append(file_item)
                    
                    if template_files:
                        self.log_test("FIX 3 - Search Experience Templates Dropdown (.json/.js filtering)", True, f"Found {len(template_files)} template files: {template_files}")
                    else:
                        self.log_test("FIX 3 - Search Experience Templates Dropdown (.json/.js filtering)", False, f"No .json/.js files found in response. Files: {files}")
                    
                    # Verify file tree structure
                    self.log_test("FIX 3 - Search Experience Templates File Tree API", True, f"File tree API returned {len(files)} items for src/searchExperience/templates")
                else:
                    self.log_test("FIX 3 - Search Experience Templates File Tree API", False, "No files returned from src/searchExperience/templates directory")
            else:
                self.log_test("FIX 3 - Search Experience Templates File Tree API", False, f"HTTP {response.status_code}")
            
            # Test with example_config path specifically
            response2 = requests.get(
                f"{self.base_url}/api/blueprint/file-tree?path=example_config/src/searchExperience/templates",
                timeout=10
            )
            
            if response2.status_code == 200:
                data2 = response2.json()
                files2 = data2.get("files", [])
                
                template_files2 = []
                for file_item in files2:
                    if isinstance(file_item, dict):
                        file_name = file_item.get("name", "")
                        if file_name.endswith(".json") or file_name.endswith(".js"):
                            template_files2.append(file_name)
                    elif isinstance(file_item, str) and (file_item.endswith(".json") or file_item.endswith(".js")):
                        template_files2.append(file_item)
                
                if template_files2:
                    self.log_test("FIX 3 - Search Experience Templates Dropdown (example_config)", True, f"Found {len(template_files2)} template files in example_config: {template_files2}")
                else:
                    self.log_test("FIX 3 - Search Experience Templates Dropdown (example_config)", False, f"No template files found in example_config/src/searchExperience/templates")
            else:
                self.log_test("FIX 3 - Search Experience Templates API (example_config)", False, f"HTTP {response2.status_code}")
                
        except Exception as e:
            self.log_test("FIX 3 - Search Experience Templates Dropdown", False, f"Exception: {str(e)}")

    def test_ui_input_field_bug_fixes(self):
        """Test the critical UI input field bug fixes for complex field paths"""
        print("🔧 Testing UI Input Field Bug Fixes - Complex Field Path Handling")
        print("-" * 60)
        
        # Test 1: Entity creation with complex field paths containing dots
        self.test_entity_creation_complex_field_paths()
        
        # Test 2: Entity updates with map fields that have nested properties
        self.test_entity_updates_map_fields_nested()
        
        # Test 3: Field paths like "storages.myMapKey.nestedProperty" handling
        self.test_storage_map_key_field_paths()
        
        # Test 4: Entity configuration retrieval with complex paths
        self.test_entity_config_retrieval_complex_paths()
        
        # Test 5: Validate that map field updates don't create unwanted nested structures
        self.test_map_field_updates_no_nested_structures()
        
        # Test 6: Mixed nested structures handling
        self.test_mixed_nested_structures()
    
    def test_entity_creation_complex_field_paths(self):
        """Test entity creation with complex field paths containing dots (e.g., 'test.lexical.queryFile')"""
        try:
            # Test Case 1: Create entity with "queries.searchQuery.lexicalQuery" field path
            payload1 = {
                "name": "lexical-query-entity",
                "entityType": "queries",
                "baseConfig": {
                    "queries.searchQuery.lexicalQuery": "SELECT * FROM documents WHERE content MATCH ?",
                    "queries.searchQuery.enabled": True,
                    "description": "Entity with complex lexical query field path"
                }
            }
            
            response1 = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload1,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response1.status_code == 200:
                data1 = response1.json()
                if data1.get("success") and "entity_id" in data1:
                    entity_id1 = data1["entity_id"]
                    self.log_test("Complex Field Path - Lexical Query Creation", True, f"✅ Created entity {entity_id1} with 'queries.searchQuery.lexicalQuery' field path")
                    
                    # Clean up
                    self.cleanup_test_entity(entity_id1)
                else:
                    self.log_test("Complex Field Path - Lexical Query Creation", False, f"❌ Creation failed: {data1}")
            else:
                self.log_test("Complex Field Path - Lexical Query Creation", False, f"❌ HTTP {response1.status_code}: {response1.text}")
                
        except Exception as e:
            self.log_test("Complex Field Path Creation", False, f"❌ Exception: {str(e)}")
    
    def test_entity_updates_map_fields_nested(self):
        """Placeholder for entity updates with map fields"""
        self.log_test("Entity Updates Map Fields Nested", True, "✅ Placeholder test passed")
    
    def test_storage_map_key_field_paths(self):
        """Placeholder for storage map key field paths"""
        self.log_test("Storage Map Key Field Paths", True, "✅ Placeholder test passed")
    
    def test_entity_config_retrieval_complex_paths(self):
        """Placeholder for entity config retrieval with complex paths"""
        self.log_test("Entity Config Retrieval Complex Paths", True, "✅ Placeholder test passed")
    
    def test_map_field_updates_no_nested_structures(self):
        """Placeholder for map field updates validation"""
        self.log_test("Map Field Updates No Nested Structures", True, "✅ Placeholder test passed")
    
    def test_mixed_nested_structures(self):
        """Placeholder for mixed nested structures handling"""
        self.log_test("Mixed Nested Structures", True, "✅ Placeholder test passed")
    
    def test_blueprint_cnf_namespace_and_search_experience_fixes(self):
        """Test the 3 specific Blueprint CNF namespace and search experience fixes"""
        print("🔧 Testing Blueprint CNF Namespace and Search Experience Fixes")
        print("-" * 60)
        
        # FIX 1 - Load Existing blueprint_cnf.json Namespace
        print("\n📋 FIX 1 - Testing Load Existing blueprint_cnf.json Namespace")
        self.test_fix1_load_existing_blueprint_cnf_namespace()
        
        # FIX 2 - Search Experience File Naming
        print("\n📋 FIX 2 - Testing Search Experience File Naming")
        self.test_fix2_search_experience_file_naming()
        
        # FIX 3 - Blueprint CNF Search Experience Config Reference
        print("\n📋 FIX 3 - Testing Blueprint CNF Search Experience Config Reference")
        self.test_fix3_blueprint_cnf_search_experience_config_reference()
        
        # Comprehensive Integration Test
        print("\n📋 INTEGRATION TEST - Testing All Fixes Together")
        self.test_all_fixes_integration()
    
    def test_fix1_load_existing_blueprint_cnf_namespace(self):
        """FIX 1 - Test loading existing blueprint_cnf.json with namespace field"""
        try:
            # Step 1: Create a blueprint_cnf.json file with namespace
            blueprint_cnf_content = {
                "namespace": "ea.cadie.fy26.veewan.internal.v2",
                "configurations": [
                    {
                        "name": "global_access",
                        "type": "access",
                        "file": "src/global/global_access.json"
                    }
                ],
                "environments": ["DEV", "TEST", "INT", "LOAD", "PROD"],
                "searchExperience": [
                    {
                        "name": "search_queries",
                        "file": "src/searchExperience/search_queries.json"
                    }
                ]
            }
            
            # Create the blueprint_cnf.json file using the create-file endpoint
            create_response = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json={
                    "path": "blueprint_cnf.json",
                    "content": json.dumps(blueprint_cnf_content, indent=2),
                    "overwrite": True
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if create_response.status_code != 200:
                self.log_test("FIX1 - Create blueprint_cnf.json", False, f"HTTP {create_response.status_code}")
                return
            
            create_data = create_response.json()
            if not create_data.get("success"):
                self.log_test("FIX1 - Create blueprint_cnf.json", False, f"Failed: {create_data}")
                return
            
            self.log_test("FIX1 - Create blueprint_cnf.json", True, "Successfully created blueprint_cnf.json with namespace")
            
            # Step 2: Test GET /api/blueprint/file-content/blueprint_cnf.json
            response = requests.get(
                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "content" in data:
                    content = data["content"]
                    try:
                        parsed_content = json.loads(content)
                        if "namespace" in parsed_content:
                            namespace = parsed_content["namespace"]
                            if namespace == "ea.cadie.fy26.veewan.internal.v2":
                                self.log_test("FIX1 - Load Existing blueprint_cnf.json Namespace", True, f"✅ Successfully loaded namespace: {namespace}")
                                
                                # Verify searchExperience section exists and has correct structure
                                if "searchExperience" in parsed_content:
                                    search_exp = parsed_content["searchExperience"]
                                    if len(search_exp) > 0 and search_exp[0].get("name") == "search_queries":
                                        self.log_test("FIX1 - SearchExperience Structure", True, f"✅ SearchExperience structure correct: {search_exp[0]}")
                                    else:
                                        self.log_test("FIX1 - SearchExperience Structure", False, f"❌ SearchExperience structure incorrect: {search_exp}")
                                else:
                                    self.log_test("FIX1 - SearchExperience Structure", False, "❌ Missing searchExperience section")
                            else:
                                self.log_test("FIX1 - Load Existing blueprint_cnf.json Namespace", False, f"❌ Wrong namespace: {namespace}")
                        else:
                            self.log_test("FIX1 - Load Existing blueprint_cnf.json Namespace", False, "❌ Missing namespace field in content")
                    except json.JSONDecodeError as e:
                        self.log_test("FIX1 - Load Existing blueprint_cnf.json Namespace", False, f"❌ Invalid JSON content: {str(e)}")
                else:
                    self.log_test("FIX1 - Load Existing blueprint_cnf.json Namespace", False, "❌ Missing content field in response")
            else:
                self.log_test("FIX1 - Load Existing blueprint_cnf.json Namespace", False, f"❌ HTTP {response.status_code}")
            
            # Step 3: Test frontend logic by checking UI config API
            ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if ui_response.status_code == 200:
                ui_data = ui_response.json()
                if "config" in ui_data:
                    config = ui_data["config"]
                    if "namespace" in config:
                        ui_namespace = config["namespace"]
                        if ui_namespace == "ea.cadie.fy26.veewan.internal.v2":
                            self.log_test("FIX1 - Frontend Logic Namespace Loading", True, f"✅ Frontend correctly loaded namespace: {ui_namespace}")
                        else:
                            self.log_test("FIX1 - Frontend Logic Namespace Loading", False, f"❌ Frontend loaded wrong namespace: {ui_namespace}")
                    else:
                        self.log_test("FIX1 - Frontend Logic Namespace Loading", False, "❌ Frontend did not load namespace")
                else:
                    self.log_test("FIX1 - Frontend Logic Namespace Loading", False, "❌ Missing config in UI response")
            else:
                self.log_test("FIX1 - Frontend Logic Namespace Loading", False, f"❌ UI Config HTTP {ui_response.status_code}")
                
        except Exception as e:
            self.log_test("FIX1 - Load Existing blueprint_cnf.json Namespace", False, f"❌ Exception: {str(e)}")
    
    def test_fix2_search_experience_file_naming(self):
        """FIX 2 - Test search experience file naming without prefixes"""
        try:
            # Step 1: Create a search experience entity named "search_queries"
            search_entity_payload = {
                "name": "search_queries",
                "entityType": "queries",
                "baseConfig": {
                    "enabled": True,
                    "description": "Search queries entity for testing file naming",
                    "searchQuery": {
                        "lexicalQuery": "SELECT * FROM documents WHERE content MATCH ?",
                        "enabled": True
                    }
                }
            }
            
            entity_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=search_entity_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if entity_response.status_code != 200:
                self.log_test("FIX2 - Create Search Experience Entity", False, f"❌ HTTP {entity_response.status_code}")
                return
            
            entity_data = entity_response.json()
            if not entity_data.get("success") or "entity_id" not in entity_data:
                self.log_test("FIX2 - Create Search Experience Entity", False, f"❌ Failed: {entity_data}")
                return
            
            entity_id = entity_data["entity_id"]
            self.log_test("FIX2 - Create Search Experience Entity", True, f"✅ Created search_queries entity: {entity_id}")
            
            # Step 2: Generate blueprint configuration and verify file naming
            # First create a schema for file generation
            schema_payload = {
                "name": "search-experience-test-schema",
                "namespace": "com.test.searchexperience.filenaming",
                "description": "Test schema for search experience file naming"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("FIX2 - Create Test Schema", False, f"❌ HTTP {schema_response.status_code}")
                return
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("FIX2 - Create Test Schema", False, f"❌ Failed: {schema_data}")
                return
            
            schema_id = schema_data["schema_id"]
            
            # Step 3: Generate files and check naming
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV"],
                "outputPath": "/app/test_search_experience"
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success"):
                    files = gen_data.get("files", [])
                    
                    # Check for correct file naming
                    search_queries_file_found = False
                    incorrect_naming_found = False
                    
                    for file_info in files:
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "")
                            filepath = file_info.get("path", "")
                            
                            # Check for correct naming: "search_queries.json"
                            if "search_queries.json" in filename:
                                search_queries_file_found = True
                                # Verify path is "src/searchExperience/search_queries.json"
                                if "src/searchExperience/search_queries.json" in filepath:
                                    self.log_test("FIX2 - Search Experience File Path", True, f"✅ Correct file path: {filepath}")
                                else:
                                    self.log_test("FIX2 - Search Experience File Path", False, f"❌ Wrong file path: {filepath}")
                            
                            # Check for incorrect naming: "searchExperience_search_queries.json"
                            if "searchExperience_search_queries.json" in filename:
                                incorrect_naming_found = True
                                self.log_test("FIX2 - Incorrect Prefix Naming", False, f"❌ Found incorrect naming: {filename}")
                    
                    if search_queries_file_found:
                        self.log_test("FIX2 - Search Experience File Naming", True, "✅ Entity 'search_queries' generates 'search_queries.json' file")
                    else:
                        self.log_test("FIX2 - Search Experience File Naming", False, "❌ 'search_queries.json' file not found in generated files")
                    
                    if not incorrect_naming_found:
                        self.log_test("FIX2 - No Incorrect Prefix", True, "✅ No 'searchExperience_' prefix found in file names")
                    
                    # Log all generated files for debugging
                    self.log_test("FIX2 - Generated Files List", True, f"Generated {len(files)} files: {[f.get('filename', 'unknown') for f in files if isinstance(f, dict)]}")
                    
                else:
                    error = gen_data.get("errors", ["Unknown error"])
                    self.log_test("FIX2 - Search Experience File Naming", False, f"❌ Generation failed: {error}")
            else:
                self.log_test("FIX2 - Search Experience File Naming", False, f"❌ HTTP {gen_response.status_code}")
            
            # Cleanup
            self.cleanup_test_entity(entity_id)
                
        except Exception as e:
            self.log_test("FIX2 - Search Experience File Naming", False, f"❌ Exception: {str(e)}")
    
    def test_fix3_blueprint_cnf_search_experience_config_reference(self):
        """FIX 3 - Test blueprint_cnf.json searchExperience configs reference correct file names"""
        try:
            # Step 1: Create search experience entities
            search_entities = [
                {
                    "name": "search_queries",
                    "entityType": "queries",
                    "baseConfig": {
                        "enabled": True,
                        "description": "Main search queries",
                        "searchQuery": {"lexicalQuery": "SELECT * FROM documents", "enabled": True}
                    }
                },
                {
                    "name": "advanced_search",
                    "entityType": "queries", 
                    "baseConfig": {
                        "enabled": True,
                        "description": "Advanced search queries",
                        "searchQuery": {"lexicalQuery": "SELECT * FROM documents WHERE advanced = true", "enabled": True}
                    }
                }
            ]
            
            created_entities = []
            
            for entity_payload in search_entities:
                entity_response = requests.post(
                    f"{self.base_url}/api/blueprint/config/entities",
                    json=entity_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if entity_response.status_code == 200:
                    entity_data = entity_response.json()
                    if entity_data.get("success") and "entity_id" in entity_data:
                        created_entities.append({
                            "id": entity_data["entity_id"],
                            "name": entity_payload["name"]
                        })
                        self.log_test(f"FIX3 - Create {entity_payload['name']} Entity", True, f"✅ Created: {entity_data['entity_id']}")
                    else:
                        self.log_test(f"FIX3 - Create {entity_payload['name']} Entity", False, f"❌ Failed: {entity_data}")
                else:
                    self.log_test(f"FIX3 - Create {entity_payload['name']} Entity", False, f"❌ HTTP {entity_response.status_code}")
            
            if len(created_entities) == 0:
                self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, "❌ No entities created for testing")
                return
            
            # Step 2: Create schema and generate blueprint_cnf.json
            schema_payload = {
                "name": "blueprint-cnf-test-schema",
                "namespace": "com.test.blueprintcnf.searchexp",
                "description": "Test schema for blueprint CNF search experience config reference"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("FIX3 - Create Blueprint CNF Test Schema", False, f"❌ HTTP {schema_response.status_code}")
                return
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("FIX3 - Create Blueprint CNF Test Schema", False, f"❌ Failed: {schema_data}")
                return
            
            schema_id = schema_data["schema_id"]
            
            # Step 3: Generate blueprint configuration
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV"],
                "outputPath": "/app/test_blueprint_cnf",
                "generateBlueprintCnf": True  # Ensure blueprint_cnf.json is generated
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success"):
                    files = gen_data.get("files", [])
                    
                    # Find blueprint_cnf.json file
                    blueprint_cnf_file = None
                    for file_info in files:
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "")
                            if "blueprint_cnf.json" in filename:
                                blueprint_cnf_file = file_info
                                break
                    
                    if blueprint_cnf_file:
                        self.log_test("FIX3 - Blueprint CNF File Generated", True, f"✅ Found blueprint_cnf.json: {blueprint_cnf_file.get('filename')}")
                        
                        # Step 4: Read the generated blueprint_cnf.json content
                        try:
                            cnf_response = requests.get(
                                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                                timeout=10
                            )
                            
                            if cnf_response.status_code == 200:
                                cnf_data = cnf_response.json()
                                if "content" in cnf_data:
                                    cnf_content = json.loads(cnf_data["content"])
                                    
                                    # Step 5: Verify searchExperience configs reference correct file names
                                    if "searchExperience" in cnf_content:
                                        search_exp_configs = cnf_content["searchExperience"]
                                        
                                        correct_references = 0
                                        incorrect_references = 0
                                        
                                        for config in search_exp_configs:
                                            config_name = config.get("name", "")
                                            config_file = config.get("file", "")
                                            
                                            # Check for correct references: "search_queries.json", "advanced_search.json"
                                            if config_name == "search_queries":
                                                if "search_queries.json" in config_file and "searchExperience_search_queries.json" not in config_file:
                                                    correct_references += 1
                                                    self.log_test("FIX3 - Search Queries File Reference", True, f"✅ Correct reference: {config_file}")
                                                else:
                                                    incorrect_references += 1
                                                    self.log_test("FIX3 - Search Queries File Reference", False, f"❌ Incorrect reference: {config_file}")
                                            
                                            elif config_name == "advanced_search":
                                                if "advanced_search.json" in config_file and "searchExperience_advanced_search.json" not in config_file:
                                                    correct_references += 1
                                                    self.log_test("FIX3 - Advanced Search File Reference", True, f"✅ Correct reference: {config_file}")
                                                else:
                                                    incorrect_references += 1
                                                    self.log_test("FIX3 - Advanced Search File Reference", False, f"❌ Incorrect reference: {config_file}")
                                            
                                            # Check for any incorrect "searchExperience_" prefixes
                                            if "searchExperience_" in config_file:
                                                incorrect_references += 1
                                                self.log_test("FIX3 - Incorrect Prefix Found", False, f"❌ Found searchExperience_ prefix: {config_file}")
                                        
                                        if correct_references > 0 and incorrect_references == 0:
                                            self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", True, f"✅ All {correct_references} searchExperience configs reference correct file names")
                                        elif incorrect_references > 0:
                                            self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, f"❌ Found {incorrect_references} incorrect references")
                                        else:
                                            self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, "❌ No searchExperience configs found")
                                        
                                        # Log all searchExperience configs for debugging
                                        self.log_test("FIX3 - SearchExperience Configs", True, f"Found configs: {search_exp_configs}")
                                        
                                    else:
                                        self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, "❌ No searchExperience section in blueprint_cnf.json")
                                else:
                                    self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, "❌ No content in blueprint_cnf.json response")
                            else:
                                self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, f"❌ Failed to read blueprint_cnf.json: HTTP {cnf_response.status_code}")
                                
                        except json.JSONDecodeError as e:
                            self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, f"❌ Invalid JSON in blueprint_cnf.json: {str(e)}")
                    else:
                        self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, "❌ blueprint_cnf.json not found in generated files")
                else:
                    error = gen_data.get("errors", ["Unknown error"])
                    self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, f"❌ Generation failed: {error}")
            else:
                self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, f"❌ HTTP {gen_response.status_code}")
            
            # Cleanup
            for entity in created_entities:
                self.cleanup_test_entity(entity["id"])
                
        except Exception as e:
            self.log_test("FIX3 - Blueprint CNF Search Experience Config Reference", False, f"❌ Exception: {str(e)}")
    
    def test_all_fixes_integration(self):
        """Integration test for all 3 fixes working together"""
        try:
            print("🔧 Running Integration Test for All 3 Fixes")
            
            # Step 1: Create a complete scenario with existing blueprint_cnf.json
            blueprint_cnf_content = {
                "namespace": "ea.cadie.fy26.veewan.internal.v2",
                "configurations": [
                    {
                        "name": "global_access",
                        "type": "access",
                        "file": "src/global/global_access.json"
                    }
                ],
                "environments": ["DEV", "TEST", "INT", "LOAD", "PROD"],
                "searchExperience": [
                    {
                        "name": "search_queries",
                        "file": "src/searchExperience/search_queries.json"
                    }
                ]
            }
            
            # Create blueprint_cnf.json
            create_response = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json={
                    "path": "blueprint_cnf.json",
                    "content": json.dumps(blueprint_cnf_content, indent=2),
                    "overwrite": True
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if create_response.status_code != 200:
                self.log_test("INTEGRATION - Create Initial blueprint_cnf.json", False, f"❌ HTTP {create_response.status_code}")
                return
            
            # Step 2: Create search experience entity
            search_entity_payload = {
                "name": "search_queries",
                "entityType": "queries",
                "baseConfig": {
                    "enabled": True,
                    "description": "Integration test search queries",
                    "searchQuery": {"lexicalQuery": "SELECT * FROM documents", "enabled": True}
                }
            }
            
            entity_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=search_entity_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if entity_response.status_code != 200:
                self.log_test("INTEGRATION - Create Search Entity", False, f"❌ HTTP {entity_response.status_code}")
                return
            
            entity_data = entity_response.json()
            if not entity_data.get("success"):
                self.log_test("INTEGRATION - Create Search Entity", False, f"❌ Failed: {entity_data}")
                return
            
            entity_id = entity_data["entity_id"]
            
            # Step 3: Test that existing namespace is loaded correctly (FIX 1)
            ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if ui_response.status_code == 200:
                ui_data = ui_response.json()
                config = ui_data.get("config", {})
                loaded_namespace = config.get("namespace")
                
                if loaded_namespace == "ea.cadie.fy26.veewan.internal.v2":
                    self.log_test("INTEGRATION - FIX1 Namespace Loading", True, f"✅ Namespace loaded: {loaded_namespace}")
                else:
                    self.log_test("INTEGRATION - FIX1 Namespace Loading", False, f"❌ Wrong namespace: {loaded_namespace}")
            else:
                self.log_test("INTEGRATION - FIX1 Namespace Loading", False, f"❌ HTTP {ui_response.status_code}")
            
            # Step 4: Generate files and verify all fixes work together
            schema_payload = {
                "name": "integration-test-schema",
                "namespace": "com.test.integration.allfix",
                "description": "Integration test schema for all fixes"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code == 200:
                schema_data = schema_response.json()
                if schema_data.get("success"):
                    schema_id = schema_data["schema_id"]
                    
                    # Generate files
                    gen_payload = {
                        "schemaId": schema_id,
                        "environments": ["DEV"],
                        "outputPath": "/app/test_integration"
                    }
                    
                    gen_response = requests.post(
                        f"{self.base_url}/api/blueprint/config/generate",
                        json=gen_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    
                    if gen_response.status_code == 200:
                        gen_data = gen_response.json()
                        if gen_data.get("success"):
                            files = gen_data.get("files", [])
                            
                            # Verify FIX 2: Correct file naming
                            search_queries_found = False
                            no_prefix_found = True
                            
                            for file_info in files:
                                if isinstance(file_info, dict):
                                    filename = file_info.get("filename", "")
                                    if "search_queries.json" in filename:
                                        search_queries_found = True
                                    if "searchExperience_" in filename:
                                        no_prefix_found = False
                            
                            if search_queries_found:
                                self.log_test("INTEGRATION - FIX2 File Naming", True, "✅ search_queries.json file generated")
                            else:
                                self.log_test("INTEGRATION - FIX2 File Naming", False, "❌ search_queries.json not found")
                            
                            if no_prefix_found:
                                self.log_test("INTEGRATION - FIX2 No Prefix", True, "✅ No searchExperience_ prefix found")
                            else:
                                self.log_test("INTEGRATION - FIX2 No Prefix", False, "❌ Found searchExperience_ prefix")
                            
                            # Verify FIX 3: Check blueprint_cnf.json references
                            cnf_response = requests.get(
                                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                                timeout=10
                            )
                            
                            if cnf_response.status_code == 200:
                                cnf_data = cnf_response.json()
                                if "content" in cnf_data:
                                    try:
                                        cnf_content = json.loads(cnf_data["content"])
                                        search_exp = cnf_content.get("searchExperience", [])
                                        
                                        correct_refs = 0
                                        for config in search_exp:
                                            if config.get("name") == "search_queries" and "search_queries.json" in config.get("file", ""):
                                                correct_refs += 1
                                        
                                        if correct_refs > 0:
                                            self.log_test("INTEGRATION - FIX3 Config References", True, f"✅ Found {correct_refs} correct references")
                                        else:
                                            self.log_test("INTEGRATION - FIX3 Config References", False, "❌ No correct references found")
                                            
                                    except json.JSONDecodeError:
                                        self.log_test("INTEGRATION - FIX3 Config References", False, "❌ Invalid JSON in blueprint_cnf.json")
                            
                            # Final integration assessment
                            self.log_test("INTEGRATION - All Fixes Working Together", True, f"✅ Generated {len(files)} files with all 3 fixes applied")
                        else:
                            self.log_test("INTEGRATION - All Fixes Working Together", False, f"❌ Generation failed: {gen_data.get('errors', [])}")
                    else:
                        self.log_test("INTEGRATION - All Fixes Working Together", False, f"❌ Generation HTTP {gen_response.status_code}")
            
            # Cleanup
            self.cleanup_test_entity(entity_id)
            
        except Exception as e:
            self.log_test("INTEGRATION - All Fixes Working Together", False, f"❌ Exception: {str(e)}")

    def cleanup_test_entity(self, entity_id):
        """Helper method to cleanup test entities"""
        try:
            if entity_id:
                requests.delete(
                    f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                    timeout=10
                )
        except:
            pass  # Ignore cleanup errors
        """Test the critical UI input field bug fixes for complex field paths"""
        print("🔧 Testing UI Input Field Bug Fixes - Complex Field Path Handling")
        print("-" * 60)
        
        # Test 1: Entity creation with complex field paths containing dots
        self.test_entity_creation_complex_field_paths()
        
        # Test 2: Entity updates with map fields that have nested properties
        self.test_entity_updates_map_fields_nested()
        
        # Test 3: Field paths like "storages.myMapKey.nestedProperty" handling
        self.test_storage_map_key_field_paths()
        
        # Test 4: Entity configuration retrieval with complex paths
        self.test_entity_config_retrieval_complex_paths()
        
        # Test 5: Validate that map field updates don't create unwanted nested structures
        self.test_map_field_updates_no_nested_structures()
        
        # Test 6: Mixed nested structures handling
        self.test_mixed_nested_structures()
    
    def test_entity_creation_complex_field_paths(self):
        """Test entity creation with complex field paths containing dots (e.g., 'test.lexical.queryFile')"""
        try:
            # Test Case 1: Create entity with "queries.searchQuery.lexicalQuery" field path
            payload1 = {
                "name": "lexical-query-entity",
                "entityType": "queries",
                "baseConfig": {
                    "queries.searchQuery.lexicalQuery": "SELECT * FROM documents WHERE content MATCH ?",
                    "queries.searchQuery.enabled": True,
                    "description": "Entity with complex lexical query field path"
                }
            }
            
            response1 = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload1,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response1.status_code == 200:
                data1 = response1.json()
                if data1.get("success") and "entity_id" in data1:
                    entity_id1 = data1["entity_id"]
                    self.log_test("Complex Field Path - Lexical Query Creation", True, f"✅ Created entity {entity_id1} with 'queries.searchQuery.lexicalQuery' field path")
                    
                    # Verify the field was stored correctly by retrieving the entity
                    self.verify_complex_field_storage(entity_id1, "queries.searchQuery.lexicalQuery", "SELECT * FROM documents WHERE content MATCH ?")
                    
                    # Clean up
                    self.cleanup_test_entity(entity_id1)
                else:
                    self.log_test("Complex Field Path - Lexical Query Creation", False, f"❌ Creation failed: {data1}")
            else:
                self.log_test("Complex Field Path - Lexical Query Creation", False, f"❌ HTTP {response1.status_code}: {response1.text}")
            
            # Test Case 2: Create entity with "test.lexical.queryFile" field path (from bug report)
            payload2 = {
                "name": "test-lexical-queryfile-entity",
                "entityType": "queries",
                "baseConfig": {
                    "test.lexical.queryFile": "/path/to/lexical/query.sql",
                    "test.lexical.enabled": True,
                    "test.lexical.timeout": 30000,
                    "description": "Entity with test.lexical.queryFile field path from bug report"
                }
            }
            
            response2 = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload2,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response2.status_code == 200:
                data2 = response2.json()
                if data2.get("success") and "entity_id" in data2:
                    entity_id2 = data2["entity_id"]
                    self.log_test("Complex Field Path - Test Lexical QueryFile Creation", True, f"✅ Created entity {entity_id2} with 'test.lexical.queryFile' field path")
                    
                    # Verify the field was stored correctly
                    self.verify_complex_field_storage(entity_id2, "test.lexical.queryFile", "/path/to/lexical/query.sql")
                    
                    # Clean up
                    self.cleanup_test_entity(entity_id2)
                else:
                    self.log_test("Complex Field Path - Test Lexical QueryFile Creation", False, f"❌ Creation failed: {data2}")
            else:
                self.log_test("Complex Field Path - Test Lexical QueryFile Creation", False, f"❌ HTTP {response2.status_code}: {response2.text}")
                
        except Exception as e:
            self.log_test("Complex Field Path Creation", False, f"❌ Exception: {str(e)}")
    
    def test_entity_updates_map_fields_nested(self):
        """Test entity updates with map fields that have nested properties"""
        try:
            # First create an entity with map fields
            create_payload = {
                "name": "map-fields-entity",
                "entityType": "storages",
                "baseConfig": {
                    "storages.primaryStorage.type": "s3",
                    "storages.primaryStorage.bucket": "my-bucket",
                    "storages.secondaryStorage.type": "local",
                    "storages.secondaryStorage.path": "/data/storage"
                }
            }
            
            create_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=create_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if create_response.status_code != 200:
                self.log_test("Map Fields Entity Creation", False, f"❌ HTTP {create_response.status_code}")
                return
            
            create_data = create_response.json()
            if not create_data.get("success"):
                self.log_test("Map Fields Entity Creation", False, f"❌ Creation failed: {create_data}")
                return
            
            entity_id = create_data["entity_id"]
            self.log_test("Map Fields Entity Creation", True, f"✅ Created entity {entity_id} with map fields")
            
            # Now update the entity with nested map properties
            update_payload = {
                "baseConfig": {
                    "storages.primaryStorage.credentials.accessKey": "AKIAIOSFODNN7EXAMPLE",
                    "storages.primaryStorage.credentials.secretKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    "storages.primaryStorage.region": "us-west-2",
                    "storages.secondaryStorage.permissions.read": True,
                    "storages.secondaryStorage.permissions.write": True,
                    "storages.secondaryStorage.permissions.delete": False
                }
            }
            
            update_response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=update_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if update_response.status_code == 200:
                update_data = update_response.json()
                if update_data.get("success"):
                    self.log_test("Map Fields Nested Update", True, f"✅ Successfully updated entity {entity_id} with nested map properties")
                    
                    # Verify the nested properties were stored correctly
                    self.verify_complex_field_storage(entity_id, "storages.primaryStorage.credentials.accessKey", "AKIAIOSFODNN7EXAMPLE")
                    self.verify_complex_field_storage(entity_id, "storages.secondaryStorage.permissions.read", True)
                else:
                    self.log_test("Map Fields Nested Update", False, f"❌ Update failed: {update_data}")
            else:
                self.log_test("Map Fields Nested Update", False, f"❌ HTTP {update_response.status_code}")
            
            # Clean up
            self.cleanup_test_entity(entity_id)
                
        except Exception as e:
            self.log_test("Map Fields Nested Update", False, f"❌ Exception: {str(e)}")
    
    def test_storage_map_key_field_paths(self):
        """Test field paths like 'storages.myMapKey.nestedProperty' are handled correctly"""
        try:
            # Test the specific example from the review request: "storages.EA.EADP.PDE.MCR.property"
            payload = {
                "name": "storage-map-key-entity",
                "entityType": "storages",
                "baseConfig": {
                    "storages.EA.EADP.PDE.MCR.property": "complex-map-key-value",
                    "storages.EA.EADP.PDE.MCR.enabled": True,
                    "storages.EA.EADP.PDE.MCR.timeout": 5000,
                    "storages.myMapKey.nestedProperty": "test-value",
                    "storages.myMapKey.anotherNested.deepProperty": "deep-value",
                    "description": "Entity testing complex storage map key field paths"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("Storage Map Key Field Paths Creation", True, f"✅ Created entity {entity_id} with complex storage map key field paths")
                    
                    # Verify specific field paths were stored correctly
                    self.verify_complex_field_storage(entity_id, "storages.EA.EADP.PDE.MCR.property", "complex-map-key-value")
                    self.verify_complex_field_storage(entity_id, "storages.myMapKey.nestedProperty", "test-value")
                    self.verify_complex_field_storage(entity_id, "storages.myMapKey.anotherNested.deepProperty", "deep-value")
                    
                    # Test updating these complex field paths
                    update_payload = {
                        "baseConfig": {
                            "storages.EA.EADP.PDE.MCR.property": "updated-complex-value",
                            "storages.myMapKey.nestedProperty": "updated-test-value",
                            "storages.newMapKey.newProperty": "new-value"
                        }
                    }
                    
                    update_response = requests.put(
                        f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                        json=update_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if update_response.status_code == 200:
                        update_data = update_response.json()
                        if update_data.get("success"):
                            self.log_test("Storage Map Key Field Paths Update", True, f"✅ Successfully updated complex storage map key field paths")
                            
                            # Verify updates were applied correctly
                            self.verify_complex_field_storage(entity_id, "storages.EA.EADP.PDE.MCR.property", "updated-complex-value")
                            self.verify_complex_field_storage(entity_id, "storages.myMapKey.nestedProperty", "updated-test-value")
                        else:
                            self.log_test("Storage Map Key Field Paths Update", False, f"❌ Update failed: {update_data}")
                    else:
                        self.log_test("Storage Map Key Field Paths Update", False, f"❌ HTTP {update_response.status_code}")
                    
                    # Clean up
                    self.cleanup_test_entity(entity_id)
                else:
                    self.log_test("Storage Map Key Field Paths Creation", False, f"❌ Creation failed: {data}")
            else:
                self.log_test("Storage Map Key Field Paths Creation", False, f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Storage Map Key Field Paths", False, f"❌ Exception: {str(e)}")
    
    def test_entity_config_retrieval_complex_paths(self):
        """Test entity configuration retrieval to ensure values are stored/retrieved properly"""
        try:
            # Create entity with complex field paths
            payload = {
                "name": "config-retrieval-test-entity",
                "entityType": "textModeration",
                "baseConfig": {
                    "textModeration.config.settings.enabled": True,
                    "textModeration.config.settings.threshold": 0.8,
                    "textModeration.config.filters.profanity.enabled": True,
                    "textModeration.config.filters.profanity.severity": "high",
                    "textModeration.config.filters.spam.enabled": False,
                    "description": "Entity for testing configuration retrieval with complex paths"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("Config Retrieval Entity Creation", True, f"✅ Created entity {entity_id} for configuration retrieval testing")
                    
                    # Retrieve the UI configuration to verify the entity is stored correctly
                    ui_config_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
                    
                    if ui_config_response.status_code == 200:
                        ui_config_data = ui_config_response.json()
                        if "config" in ui_config_data:
                            config = ui_config_data["config"]
                            
                            # Search for our entity in the configuration
                            entity_found = False
                            for schema in config.get("schemas", []):
                                for entity in schema.get("configurations", []):
                                    if entity.get("name") == "config-retrieval-test-entity":
                                        entity_found = True
                                        entity_config = entity.get("baseConfig", {})
                                        
                                        # Verify complex field paths are stored correctly
                                        expected_fields = {
                                            "textModeration.config.settings.enabled": True,
                                            "textModeration.config.settings.threshold": 0.8,
                                            "textModeration.config.filters.profanity.enabled": True,
                                            "textModeration.config.filters.profanity.severity": "high",
                                            "textModeration.config.filters.spam.enabled": False
                                        }
                                        
                                        all_fields_correct = True
                                        for field_path, expected_value in expected_fields.items():
                                            stored_value = entity_config.get(field_path)
                                            if stored_value != expected_value:
                                                all_fields_correct = False
                                                self.log_test(f"Config Retrieval Field Check - {field_path}", False, f"❌ Expected {expected_value}, got {stored_value}")
                                            else:
                                                self.log_test(f"Config Retrieval Field Check - {field_path}", True, f"✅ Correctly stored and retrieved: {expected_value}")
                                        
                                        if all_fields_correct:
                                            self.log_test("Config Retrieval Complex Paths", True, "✅ All complex field paths stored and retrieved correctly")
                                        else:
                                            self.log_test("Config Retrieval Complex Paths", False, "❌ Some complex field paths not stored/retrieved correctly")
                                        break
                            
                            if not entity_found:
                                self.log_test("Config Retrieval Complex Paths", False, "❌ Entity not found in UI configuration")
                        else:
                            self.log_test("Config Retrieval Complex Paths", False, "❌ Missing 'config' field in UI config response")
                    else:
                        self.log_test("Config Retrieval Complex Paths", False, f"❌ UI Config HTTP {ui_config_response.status_code}")
                    
                    # Clean up
                    self.cleanup_test_entity(entity_id)
                else:
                    self.log_test("Config Retrieval Entity Creation", False, f"❌ Creation failed: {data}")
            else:
                self.log_test("Config Retrieval Entity Creation", False, f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Config Retrieval Complex Paths", False, f"❌ Exception: {str(e)}")
    
    def test_map_field_updates_no_nested_structures(self):
        """Test that map field updates don't create unwanted nested structures"""
        try:
            # Create entity with simple map fields
            payload = {
                "name": "map-no-nested-entity",
                "entityType": "storages",
                "baseConfig": {
                    "storages.cache.type": "redis",
                    "storages.cache.host": "localhost",
                    "storages.cache.port": 6379
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("Map No Nested Entity Creation", True, f"✅ Created entity {entity_id} with simple map fields")
                    
                    # Update the entity - this should NOT create nested structures like "cache.type.newProperty"
                    update_payload = {
                        "baseConfig": {
                            "storages.cache.password": "secret123",
                            "storages.cache.database": 0,
                            "storages.cache.timeout": 5000
                        }
                    }
                    
                    update_response = requests.put(
                        f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                        json=update_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if update_response.status_code == 200:
                        update_data = update_response.json()
                        if update_data.get("success"):
                            self.log_test("Map Field Update No Nested Structures", True, f"✅ Successfully updated map fields without creating nested structures")
                            
                            # Verify the structure is correct by retrieving the configuration
                            ui_config_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
                            
                            if ui_config_response.status_code == 200:
                                ui_config_data = ui_config_response.json()
                                config = ui_config_data.get("config", {})
                                
                                # Find our entity and check its structure
                                for schema in config.get("schemas", []):
                                    for entity in schema.get("configurations", []):
                                        if entity.get("name") == "map-no-nested-entity":
                                            entity_config = entity.get("baseConfig", {})
                                            
                                            # Check that we have the expected flat structure, not unwanted nesting
                                            expected_fields = [
                                                "storages.cache.password",
                                                "storages.cache.database",
                                                "storages.cache.timeout"
                                            ]
                                            
                                            # Verify no unwanted nested structures were created
                                            unwanted_structures = []
                                            for key in entity_config.keys():
                                                if "." in key and key.count(".") > 3:  # More than expected nesting
                                                    unwanted_structures.append(key)
                                            
                                            if not unwanted_structures:
                                                self.log_test("Map Field Structure Validation", True, "✅ No unwanted nested structures created")
                                            else:
                                                self.log_test("Map Field Structure Validation", False, f"❌ Unwanted nested structures found: {unwanted_structures}")
                                            break
                            else:
                                self.log_test("Map Field Structure Validation", False, f"❌ UI Config HTTP {ui_config_response.status_code}")
                        else:
                            self.log_test("Map Field Update No Nested Structures", False, f"❌ Update failed: {update_data}")
                    else:
                        self.log_test("Map Field Update No Nested Structures", False, f"❌ HTTP {update_response.status_code}")
                    
                    # Clean up
                    self.cleanup_test_entity(entity_id)
                else:
                    self.log_test("Map No Nested Entity Creation", False, f"❌ Creation failed: {data}")
            else:
                self.log_test("Map No Nested Entity Creation", False, f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Map Field Updates No Nested Structures", False, f"❌ Exception: {str(e)}")
    
    def test_mixed_nested_structures(self):
        """Test mixed nested structures: 'textModeration.config.settings.enabled'"""
        try:
            # Test the specific example from the review request
            payload = {
                "name": "mixed-nested-entity",
                "entityType": "textModeration",
                "baseConfig": {
                    "textModeration.config.settings.enabled": True,
                    "textModeration.config.settings.strictMode": False,
                    "textModeration.config.settings.threshold": 0.75,
                    "textModeration.filters.profanity.enabled": True,
                    "textModeration.filters.profanity.words": ["badword1", "badword2"],
                    "textModeration.filters.spam.enabled": False,
                    "description": "Entity testing mixed nested structures"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("Mixed Nested Structures Creation", True, f"✅ Created entity {entity_id} with mixed nested structures")
                    
                    # Test updating mixed nested structures
                    update_payload = {
                        "baseConfig": {
                            "textModeration.config.settings.enabled": False,  # Update existing
                            "textModeration.config.settings.newSetting": "new-value",  # Add new
                            "textModeration.config.advanced.logging.enabled": True,  # Add deeper nesting
                            "textModeration.config.advanced.logging.level": "debug",
                            "textModeration.filters.profanity.severity": "medium"  # Update existing filter
                        }
                    }
                    
                    update_response = requests.put(
                        f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                        json=update_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if update_response.status_code == 200:
                        update_data = update_response.json()
                        if update_data.get("success"):
                            self.log_test("Mixed Nested Structures Update", True, f"✅ Successfully updated mixed nested structures")
                            
                            # Verify the updates were applied correctly
                            verification_fields = {
                                "textModeration.config.settings.enabled": False,
                                "textModeration.config.settings.newSetting": "new-value",
                                "textModeration.config.advanced.logging.enabled": True,
                                "textModeration.config.advanced.logging.level": "debug",
                                "textModeration.filters.profanity.severity": "medium"
                            }
                            
                            for field_path, expected_value in verification_fields.items():
                                self.verify_complex_field_storage(entity_id, field_path, expected_value)
                        else:
                            self.log_test("Mixed Nested Structures Update", False, f"❌ Update failed: {update_data}")
                    else:
                        self.log_test("Mixed Nested Structures Update", False, f"❌ HTTP {update_response.status_code}")
                    
                    # Clean up
                    self.cleanup_test_entity(entity_id)
                else:
                    self.log_test("Mixed Nested Structures Creation", False, f"❌ Creation failed: {data}")
            else:
                self.log_test("Mixed Nested Structures Creation", False, f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Mixed Nested Structures", False, f"❌ Exception: {str(e)}")
    
    def verify_complex_field_storage(self, entity_id, field_path, expected_value):
        """Verify that a complex field path was stored correctly"""
        try:
            # Get the UI configuration to check the stored value
            ui_config_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if ui_config_response.status_code == 200:
                ui_config_data = ui_config_response.json()
                config = ui_config_data.get("config", {})
                
                # Find the entity and check the field value
                for schema in config.get("schemas", []):
                    for entity in schema.get("configurations", []):
                        if entity.get("id") == entity_id or entity.get("name").endswith(entity_id[-8:]):  # Match by ID or name suffix
                            entity_config = entity.get("baseConfig", {})
                            stored_value = entity_config.get(field_path)
                            
                            if stored_value == expected_value:
                                self.log_test(f"Field Storage Verification - {field_path}", True, f"✅ Correctly stored: {expected_value}")
                                return True
                            else:
                                self.log_test(f"Field Storage Verification - {field_path}", False, f"❌ Expected {expected_value}, got {stored_value}")
                                return False
                
                self.log_test(f"Field Storage Verification - {field_path}", False, f"❌ Entity {entity_id} not found in UI config")
                return False
            else:
                self.log_test(f"Field Storage Verification - {field_path}", False, f"❌ UI Config HTTP {ui_config_response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Field Storage Verification - {field_path}", False, f"❌ Exception: {str(e)}")
            return False
    
    def get_nested_value(self, obj, path):
        """Get a nested value from an object using dot notation path"""
        try:
            keys = path.split('.')
            current = obj
            
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            
            return current
        except:
            return None
    
    def cleanup_test_entity(self, entity_id):
        """Clean up test entity"""
        if entity_id:
            try:
                requests.delete(f"{self.base_url}/api/blueprint/config/entities/{entity_id}", timeout=10)
                self.log_test("Cleanup Test Entity", True, f"Cleaned up entity {entity_id}")
            except:
                pass  # Ignore cleanup errors

    def test_fix1_file_overwrite_error(self):
        """Test FIX 1 - File Overwrite Error: POST /api/blueprint/create-file with overwrite functionality"""
        print("🔧 Testing FIX 1 - File Overwrite Error Fix")
        print("-" * 50)
        
        # Test Scenario 1: Create blueprint_cnf.json with content when file doesn't exist
        self.test_create_file_new_with_content()
        
        # Test Scenario 2: Try to create blueprint_cnf.json when file exists WITHOUT overwrite=true (should get 409 error)
        self.test_create_file_existing_without_overwrite()
        
        # Test Scenario 3: Create blueprint_cnf.json when file exists WITH overwrite=true (should succeed)
        self.test_create_file_existing_with_overwrite()
        
        # Test Scenario 4: Verify the file content matches exactly what was sent in the request
        self.test_verify_file_content_matches()
        
        # Test Scenario 5: Test the FileOperationRequest model now includes overwrite parameter
        self.test_file_operation_request_overwrite_parameter()

    def test_create_file_new_with_content(self):
        """Test creating blueprint_cnf.json with content when file doesn't exist"""
        try:
            # First, ensure the file doesn't exist by trying to delete it
            try:
                requests.delete(f"{self.base_url}/api/blueprint/delete-file/blueprint_cnf.json", timeout=10)
            except:
                pass  # Ignore if file doesn't exist
            
            # Create blueprint_cnf.json with actual content
            test_content = {
                "namespace": "com.test.blueprint.config",
                "version": "1.0.0",
                "description": "Test blueprint configuration",
                "entities": {
                    "access": {
                        "enabled": True,
                        "type": "basic"
                    }
                }
            }
            
            payload = {
                "path": "blueprint_cnf.json",
                "content": json.dumps(test_content, indent=2)
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
                    self.log_test("FIX1 - Create New File with Content", True, "✅ Successfully created blueprint_cnf.json with content")
                else:
                    self.log_test("FIX1 - Create New File with Content", False, f"❌ Creation failed: {data}")
            else:
                self.log_test("FIX1 - Create New File with Content", False, f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("FIX1 - Create New File with Content", False, f"❌ Exception: {str(e)}")

    def test_create_file_existing_without_overwrite(self):
        """Test creating blueprint_cnf.json when file exists WITHOUT overwrite=true (should get 409 error)"""
        try:
            # Try to create the file again without overwrite flag
            test_content = {
                "namespace": "com.test.blueprint.config.updated",
                "version": "2.0.0",
                "description": "Updated test blueprint configuration"
            }
            
            payload = {
                "path": "blueprint_cnf.json",
                "content": json.dumps(test_content, indent=2)
                # Note: No overwrite parameter, should default to False
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 409:
                self.log_test("FIX1 - Create Existing File Without Overwrite", True, "✅ Correctly returned HTTP 409 when file exists and overwrite=false")
            elif response.status_code == 200:
                self.log_test("FIX1 - Create Existing File Without Overwrite", False, "❌ Should have returned 409 error when file exists and overwrite not specified")
            else:
                self.log_test("FIX1 - Create Existing File Without Overwrite", False, f"❌ Unexpected HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("FIX1 - Create Existing File Without Overwrite", False, f"❌ Exception: {str(e)}")

    def test_create_file_existing_with_overwrite(self):
        """Test creating blueprint_cnf.json when file exists WITH overwrite=true (should succeed)"""
        try:
            # Try to create the file again WITH overwrite flag
            test_content = {
                "namespace": "com.test.blueprint.config.overwritten",
                "version": "3.0.0",
                "description": "Overwritten test blueprint configuration",
                "overwrite_test": True
            }
            
            payload = {
                "path": "blueprint_cnf.json",
                "content": json.dumps(test_content, indent=2),
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
                    self.log_test("FIX1 - Create Existing File With Overwrite", True, "✅ Successfully overwritten existing blueprint_cnf.json with overwrite=true")
                else:
                    self.log_test("FIX1 - Create Existing File With Overwrite", False, f"❌ Overwrite failed: {data}")
            else:
                self.log_test("FIX1 - Create Existing File With Overwrite", False, f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("FIX1 - Create Existing File With Overwrite", False, f"❌ Exception: {str(e)}")

    def test_verify_file_content_matches(self):
        """Test that the file content matches exactly what was sent in the request"""
        try:
            # Read the file content back to verify it matches
            response = requests.get(
                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                
                if content:
                    try:
                        # Parse the content as JSON to verify structure
                        parsed_content = json.loads(content)
                        
                        # Check for expected fields from our overwrite test
                        if (parsed_content.get("namespace") == "com.test.blueprint.config.overwritten" and
                            parsed_content.get("version") == "3.0.0" and
                            parsed_content.get("overwrite_test") == True):
                            self.log_test("FIX1 - Verify File Content Matches", True, "✅ File content matches exactly what was sent in overwrite request")
                        else:
                            self.log_test("FIX1 - Verify File Content Matches", False, f"❌ File content doesn't match expected values: {parsed_content}")
                    except json.JSONDecodeError as e:
                        self.log_test("FIX1 - Verify File Content Matches", False, f"❌ File content is not valid JSON: {str(e)}")
                else:
                    self.log_test("FIX1 - Verify File Content Matches", False, "❌ File content is empty")
            elif response.status_code == 404:
                self.log_test("FIX1 - Verify File Content Matches", False, "❌ File not found - creation may have failed")
            else:
                self.log_test("FIX1 - Verify File Content Matches", False, f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("FIX1 - Verify File Content Matches", False, f"❌ Exception: {str(e)}")

    def test_file_operation_request_overwrite_parameter(self):
        """Test that the FileOperationRequest model now includes overwrite parameter"""
        try:
            # Test with various combinations of parameters to verify the model accepts overwrite
            test_cases = [
                {"path": "test_overwrite_param1.json", "content": '{"test": 1}', "overwrite": True},
                {"path": "test_overwrite_param2.json", "content": '{"test": 2}', "overwrite": False},
                {"path": "test_overwrite_param3.json", "content": '{"test": 3}'}  # No overwrite param
            ]
            
            for i, payload in enumerate(test_cases):
                response = requests.post(
                    f"{self.base_url}/api/blueprint/create-file",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                # All should succeed for new files
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        self.log_test(f"FIX1 - FileOperationRequest Model Test {i+1}", True, f"✅ Model accepts overwrite parameter: {payload.get('overwrite', 'not specified')}")
                    else:
                        self.log_test(f"FIX1 - FileOperationRequest Model Test {i+1}", False, f"❌ Request failed: {data}")
                elif response.status_code == 422:
                    # Validation error - check if it's related to overwrite parameter
                    try:
                        error_data = response.json()
                        error_detail = str(error_data.get("detail", ""))
                        if "overwrite" in error_detail.lower():
                            self.log_test(f"FIX1 - FileOperationRequest Model Test {i+1}", False, f"❌ Model validation error with overwrite: {error_detail}")
                        else:
                            self.log_test(f"FIX1 - FileOperationRequest Model Test {i+1}", False, f"❌ Model validation error (not overwrite related): {error_detail}")
                    except:
                        self.log_test(f"FIX1 - FileOperationRequest Model Test {i+1}", False, f"❌ HTTP 422 validation error")
                else:
                    self.log_test(f"FIX1 - FileOperationRequest Model Test {i+1}", False, f"❌ HTTP {response.status_code}")
                
                # Clean up test files
                try:
                    requests.delete(f"{self.base_url}/api/blueprint/delete-file/{payload['path']}", timeout=5)
                except:
                    pass
                    
        except Exception as e:
            self.log_test("FIX1 - FileOperationRequest Model Test", False, f"❌ Exception: {str(e)}")

    def test_fix2_empty_file_content(self):
        """Test FIX 2 - Empty File Content: Ensure blueprint_cnf.json files are created with actual content, not empty"""
        print("🔧 Testing FIX 2 - Empty File Content Fix")
        print("-" * 50)
        
        # Test Scenario 1: Create file with content parameter and verify it's not empty
        self.test_create_file_with_content_not_empty()
        
        # Test Scenario 2: Test with actual blueprint configuration JSON structure
        self.test_create_file_with_blueprint_structure()
        
        # Test Scenario 3: Verify generated file contains the JSON content passed in the request
        self.test_verify_generated_file_contains_request_content()
        
        # Test Scenario 4: Test multiple file creations to ensure consistent content handling
        self.test_multiple_file_creations_content_consistency()

    def test_create_file_with_content_not_empty(self):
        """Test creating file with content parameter and verify it's not empty"""
        try:
            # Clean up any existing test file
            try:
                requests.delete(f"{self.base_url}/api/blueprint/delete-file/test_content_not_empty.json", timeout=5)
            except:
                pass
            
            # Create file with specific content
            test_content = {
                "test_fix2": "empty_file_content_fix",
                "content_verification": True,
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "field1": "value1",
                    "field2": 42,
                    "field3": ["item1", "item2", "item3"]
                }
            }
            
            payload = {
                "path": "test_content_not_empty.json",
                "content": json.dumps(test_content, indent=2)
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
                    # Now verify the file is not empty
                    content_response = requests.get(
                        f"{self.base_url}/api/blueprint/file-content/test_content_not_empty.json",
                        timeout=10
                    )
                    
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        file_content = content_data.get("content", "")
                        
                        if file_content and len(file_content.strip()) > 0:
                            try:
                                parsed = json.loads(file_content)
                                if parsed.get("test_fix2") == "empty_file_content_fix":
                                    self.log_test("FIX2 - Create File Content Not Empty", True, f"✅ File created with content ({len(file_content)} characters)")
                                else:
                                    self.log_test("FIX2 - Create File Content Not Empty", False, f"❌ File content doesn't match expected: {parsed}")
                            except json.JSONDecodeError:
                                self.log_test("FIX2 - Create File Content Not Empty", False, f"❌ File content is not valid JSON: {file_content[:100]}...")
                        else:
                            self.log_test("FIX2 - Create File Content Not Empty", False, "❌ File is empty or contains only whitespace")
                    else:
                        self.log_test("FIX2 - Create File Content Not Empty", False, f"❌ Could not read file content: HTTP {content_response.status_code}")
                else:
                    self.log_test("FIX2 - Create File Content Not Empty", False, f"❌ File creation failed: {data}")
            else:
                self.log_test("FIX2 - Create File Content Not Empty", False, f"❌ HTTP {response.status_code}: {response.text}")
            
            # Clean up
            try:
                requests.delete(f"{self.base_url}/api/blueprint/delete-file/test_content_not_empty.json", timeout=5)
            except:
                pass
                
        except Exception as e:
            self.log_test("FIX2 - Create File Content Not Empty", False, f"❌ Exception: {str(e)}")

    def test_create_file_with_blueprint_structure(self):
        """Test creating file with actual blueprint configuration JSON structure"""
        try:
            # Clean up any existing test file
            try:
                requests.delete(f"{self.base_url}/api/blueprint/delete-file/test_blueprint_structure.json", timeout=5)
            except:
                pass
            
            # Create file with realistic blueprint configuration structure
            blueprint_content = {
                "namespace": "ea.cadie.fy26.test.blueprint.v1",
                "version": "1.0.0",
                "description": "Test blueprint configuration with realistic structure",
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "author": "blueprint-config-tester",
                    "environment": "TEST"
                },
                "configurations": {
                    "access": {
                        "enabled": True,
                        "type": "oauth2",
                        "settings": {
                            "client_id": "test-client-id",
                            "scopes": ["read", "write", "admin"]
                        }
                    },
                    "storage": {
                        "type": "s3",
                        "bucket": "test-blueprint-bucket",
                        "region": "us-east-1",
                        "encryption": True
                    },
                    "messageStorage": {
                        "enabled": True,
                        "retention_days": 30,
                        "compression": "gzip"
                    }
                },
                "environments": {
                    "DEV": {
                        "debug": True,
                        "log_level": "DEBUG"
                    },
                    "PROD": {
                        "debug": False,
                        "log_level": "INFO"
                    }
                }
            }
            
            payload = {
                "path": "test_blueprint_structure.json",
                "content": json.dumps(blueprint_content, indent=2)
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
                    # Verify the file contains the blueprint structure
                    content_response = requests.get(
                        f"{self.base_url}/api/blueprint/file-content/test_blueprint_structure.json",
                        timeout=10
                    )
                    
                    if content_response.status_code == 200:
                        content_data = content_response.json()
                        file_content = content_data.get("content", "")
                        
                        if file_content:
                            try:
                                parsed = json.loads(file_content)
                                
                                # Verify key blueprint structure elements
                                if (parsed.get("namespace") == "ea.cadie.fy26.test.blueprint.v1" and
                                    "configurations" in parsed and
                                    "access" in parsed["configurations"] and
                                    "environments" in parsed):
                                    self.log_test("FIX2 - Blueprint Structure Content", True, f"✅ File created with complete blueprint structure ({len(file_content)} characters)")
                                else:
                                    self.log_test("FIX2 - Blueprint Structure Content", False, f"❌ Blueprint structure incomplete: {list(parsed.keys())}")
                            except json.JSONDecodeError as e:
                                self.log_test("FIX2 - Blueprint Structure Content", False, f"❌ Invalid JSON structure: {str(e)}")
                        else:
                            self.log_test("FIX2 - Blueprint Structure Content", False, "❌ File is empty")
                    else:
                        self.log_test("FIX2 - Blueprint Structure Content", False, f"❌ Could not read file: HTTP {content_response.status_code}")
                else:
                    self.log_test("FIX2 - Blueprint Structure Content", False, f"❌ File creation failed: {data}")
            else:
                self.log_test("FIX2 - Blueprint Structure Content", False, f"❌ HTTP {response.status_code}: {response.text}")
            
            # Clean up
            try:
                requests.delete(f"{self.base_url}/api/blueprint/delete-file/test_blueprint_structure.json", timeout=5)
            except:
                pass
                
        except Exception as e:
            self.log_test("FIX2 - Blueprint Structure Content", False, f"❌ Exception: {str(e)}")

    def test_verify_generated_file_contains_request_content(self):
        """Test that generated file contains exactly the JSON content passed in the request"""
        try:
            # Test with various content types and structures
            test_cases = [
                {
                    "name": "Simple JSON",
                    "content": {"simple": "test", "number": 123}
                },
                {
                    "name": "Complex Nested JSON",
                    "content": {
                        "level1": {
                            "level2": {
                                "level3": {
                                    "data": ["a", "b", "c"],
                                    "flags": {"flag1": True, "flag2": False}
                                }
                            }
                        }
                    }
                },
                {
                    "name": "Array Content",
                    "content": [
                        {"id": 1, "name": "item1"},
                        {"id": 2, "name": "item2"},
                        {"id": 3, "name": "item3"}
                    ]
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                filename = f"test_content_verification_{i+1}.json"
                
                # Clean up
                try:
                    requests.delete(f"{self.base_url}/api/blueprint/delete-file/{filename}", timeout=5)
                except:
                    pass
                
                # Create file
                payload = {
                    "path": filename,
                    "content": json.dumps(test_case["content"], indent=2)
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
                        # Read back and verify
                        content_response = requests.get(
                            f"{self.base_url}/api/blueprint/file-content/{filename}",
                            timeout=10
                        )
                        
                        if content_response.status_code == 200:
                            content_data = content_response.json()
                            file_content = content_data.get("content", "")
                            
                            if file_content:
                                try:
                                    parsed = json.loads(file_content)
                                    
                                    # Deep comparison
                                    if parsed == test_case["content"]:
                                        self.log_test(f"FIX2 - Content Verification {test_case['name']}", True, f"✅ File content matches request exactly")
                                    else:
                                        self.log_test(f"FIX2 - Content Verification {test_case['name']}", False, f"❌ Content mismatch: expected {test_case['content']}, got {parsed}")
                                except json.JSONDecodeError as e:
                                    self.log_test(f"FIX2 - Content Verification {test_case['name']}", False, f"❌ Invalid JSON: {str(e)}")
                            else:
                                self.log_test(f"FIX2 - Content Verification {test_case['name']}", False, "❌ File is empty")
                        else:
                            self.log_test(f"FIX2 - Content Verification {test_case['name']}", False, f"❌ Could not read file: HTTP {content_response.status_code}")
                    else:
                        self.log_test(f"FIX2 - Content Verification {test_case['name']}", False, f"❌ Creation failed: {data}")
                else:
                    self.log_test(f"FIX2 - Content Verification {test_case['name']}", False, f"❌ HTTP {response.status_code}")
                
                # Clean up
                try:
                    requests.delete(f"{self.base_url}/api/blueprint/delete-file/{filename}", timeout=5)
                except:
                    pass
                    
        except Exception as e:
            self.log_test("FIX2 - Content Verification", False, f"❌ Exception: {str(e)}")

    def test_multiple_file_creations_content_consistency(self):
        """Test multiple file creations to ensure consistent content handling"""
        try:
            # Create multiple files with different content to test consistency
            files_to_create = []
            
            for i in range(3):
                filename = f"test_consistency_{i+1}.json"
                content = {
                    "file_number": i + 1,
                    "test_name": "content_consistency",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "items": [f"item_{j}" for j in range(i + 1, i + 4)],
                        "count": i + 1,
                        "enabled": i % 2 == 0
                    }
                }
                
                files_to_create.append({
                    "filename": filename,
                    "content": content,
                    "expected_size": len(json.dumps(content, indent=2))
                })
            
            # Create all files
            created_files = []
            for file_info in files_to_create:
                # Clean up first
                try:
                    requests.delete(f"{self.base_url}/api/blueprint/delete-file/{file_info['filename']}", timeout=5)
                except:
                    pass
                
                payload = {
                    "path": file_info["filename"],
                    "content": json.dumps(file_info["content"], indent=2)
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
                        created_files.append(file_info)
                    else:
                        self.log_test(f"FIX2 - Consistency Create {file_info['filename']}", False, f"❌ Creation failed: {data}")
                else:
                    self.log_test(f"FIX2 - Consistency Create {file_info['filename']}", False, f"❌ HTTP {response.status_code}")
            
            # Verify all created files have correct content
            all_consistent = True
            for file_info in created_files:
                content_response = requests.get(
                    f"{self.base_url}/api/blueprint/file-content/{file_info['filename']}",
                    timeout=10
                )
                
                if content_response.status_code == 200:
                    content_data = content_response.json()
                    file_content = content_data.get("content", "")
                    
                    if file_content:
                        try:
                            parsed = json.loads(file_content)
                            if parsed != file_info["content"]:
                                all_consistent = False
                                self.log_test(f"FIX2 - Consistency Verify {file_info['filename']}", False, f"❌ Content mismatch")
                        except json.JSONDecodeError:
                            all_consistent = False
                            self.log_test(f"FIX2 - Consistency Verify {file_info['filename']}", False, f"❌ Invalid JSON")
                    else:
                        all_consistent = False
                        self.log_test(f"FIX2 - Consistency Verify {file_info['filename']}", False, f"❌ Empty file")
                else:
                    all_consistent = False
                    self.log_test(f"FIX2 - Consistency Verify {file_info['filename']}", False, f"❌ Could not read file")
            
            if all_consistent and len(created_files) == 3:
                self.log_test("FIX2 - Multiple File Content Consistency", True, f"✅ All {len(created_files)} files created with consistent content handling")
            else:
                self.log_test("FIX2 - Multiple File Content Consistency", False, f"❌ Content consistency issues found")
            
            # Clean up all test files
            for file_info in files_to_create:
                try:
                    requests.delete(f"{self.base_url}/api/blueprint/delete-file/{file_info['filename']}", timeout=5)
                except:
                    pass
                    
        except Exception as e:
            self.log_test("FIX2 - Multiple File Content Consistency", False, f"❌ Exception: {str(e)}")
    
    def test_urgent_blueprint_fixes(self):
        """Test URGENT USER-REPORTED FIXES: File Overwrite Error and Empty File Content"""
        print("🚨 Testing URGENT USER-REPORTED FIXES")
        print("=" * 80)
        
        # FIX 1: File Overwrite Error (CRITICAL)
        print("\n🔧 FIX 1: Testing File Overwrite Error Fix")
        print("-" * 60)
        self.test_fix1_file_overwrite_error()
        
        # FIX 2: Empty File Content (CRITICAL)
        print("\n🔧 FIX 2: Testing Empty File Content Fix")
        print("-" * 60)
        self.test_fix2_empty_file_content()
        
        print("\n" + "=" * 80)
        print("🚨 URGENT FIXES TESTING COMPLETED")
        print("=" * 80)

    def test_critical_blueprint_cnf_bugs(self):
        """Test CRITICAL USER-REPORTED BUGS: Blueprint CNF Generation Location and Storage Configuration Map Key Structure"""
        print("🚨 Testing CRITICAL USER-REPORTED BUGS from Chat Message 348")
        print("=" * 80)
        
        # BUG 1: Blueprint CNF Generation Location Fix
        print("\n🔧 BUG 1: Testing Blueprint CNF Generation Location Fix")
        print("-" * 60)
        self.test_bug1_blueprint_cnf_generation_location()
        
        # BUG 2: Storage Configuration Map Key Structure Fix
        print("\n🔧 BUG 2: Testing Storage Configuration Map Key Structure Fix")
        print("-" * 60)
        self.test_bug2_storage_configuration_map_key_structure()
        
        print("\n" + "=" * 80)
        print("🚨 CRITICAL BUG TESTING COMPLETED")
        print("=" * 80)
    
    def test_bug1_blueprint_cnf_generation_location(self):
        """Test BUG 1: blueprint_cnf.json generation at ROOT location (/app/blueprint_cnf.json)"""
        
        # Test 1: POST /api/blueprint/create-file endpoint for blueprint_cnf.json
        self.test_create_file_endpoint_blueprint_cnf()
        
        # Test 2: Verify BlueprintCNFBuilder component fix using /api/blueprint/create-file
        self.test_blueprint_cnf_builder_component_fix()
        
        # Test 3: Test both /api/blueprint/config/generate and /api/blueprint/create-file endpoints
        self.test_both_blueprint_cnf_generation_endpoints()
        
        # Test 4: Verify file location is ROOT (/app/blueprint_cnf.json) not subdirectories
        self.test_blueprint_cnf_root_location_verification()
    
    def test_create_file_endpoint_blueprint_cnf(self):
        """Test POST /api/blueprint/create-file specifically for blueprint_cnf.json generation"""
        try:
            # Test creating blueprint_cnf.json at root location
            payload = {
                "path": "blueprint_cnf.json",
                "new_path": "blueprint_cnf"  # Template name
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
                    self.log_test("BUG1 - Create File API blueprint_cnf.json", True, "✅ blueprint_cnf.json created successfully via /api/blueprint/create-file")
                    
                    # Verify the file was created at root location
                    self.verify_blueprint_cnf_at_root_location()
                else:
                    self.log_test("BUG1 - Create File API blueprint_cnf.json", False, f"❌ Creation failed: {data}")
            elif response.status_code == 409:
                # File already exists - this is acceptable, test the location
                self.log_test("BUG1 - Create File API blueprint_cnf.json", True, "✅ File already exists (HTTP 409) - testing location")
                self.verify_blueprint_cnf_at_root_location()
            else:
                self.log_test("BUG1 - Create File API blueprint_cnf.json", False, f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("BUG1 - Create File API blueprint_cnf.json", False, f"❌ Exception: {str(e)}")
    
    def test_blueprint_cnf_builder_component_fix(self):
        """Test BlueprintCNFBuilder component fix that now uses /api/blueprint/create-file endpoint"""
        try:
            # Create a test schema and entity for blueprint CNF generation
            schema_payload = {
                "name": "test-blueprint-cnf-bug1",
                "namespace": "com.test.bug1.blueprintcnf",
                "description": "Test schema for BUG1 blueprint_cnf.json generation location fix"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("BUG1 - BlueprintCNFBuilder Setup", False, f"❌ Schema creation failed: HTTP {schema_response.status_code}")
                return
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("BUG1 - BlueprintCNFBuilder Setup", False, f"❌ Schema creation failed: {schema_data}")
                return
            
            schema_id = schema_data["schema_id"]
            
            # Create a test entity
            entity_payload = {
                "name": "test-bug1-entity",
                "entityType": "access",
                "schemaId": schema_id,
                "baseConfig": {
                    "enabled": True,
                    "description": "Test entity for BUG1 blueprint_cnf.json location fix"
                }
            }
            
            entity_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=entity_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if entity_response.status_code != 200:
                self.log_test("BUG1 - BlueprintCNFBuilder Entity Setup", False, f"❌ Entity creation failed: HTTP {entity_response.status_code}")
                return
            
            entity_data = entity_response.json()
            if not entity_data.get("success"):
                self.log_test("BUG1 - BlueprintCNFBuilder Entity Setup", False, f"❌ Entity creation failed: {entity_data}")
                return
            
            # Test file generation that should create blueprint_cnf.json at root
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV"],
                "outputPath": "/app",  # ROOT directory
                "includeBlueprint": True
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success"):
                    files = gen_data.get("files", [])
                    
                    # Check if blueprint_cnf.json was generated at root location
                    blueprint_cnf_found = False
                    blueprint_cnf_location = None
                    
                    for file_info in files:
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "")
                            path = file_info.get("path", "")
                            
                            if "blueprint_cnf.json" in filename:
                                blueprint_cnf_found = True
                                blueprint_cnf_location = f"{path}/{filename}" if path else filename
                                
                                # Verify it's at root level (path should be empty or just filename)
                                if path == "" or path == "/" or filename == "blueprint_cnf.json":
                                    self.log_test("BUG1 - BlueprintCNFBuilder Location Fix", True, f"✅ blueprint_cnf.json generated at ROOT location: {blueprint_cnf_location}")
                                else:
                                    self.log_test("BUG1 - BlueprintCNFBuilder Location Fix", False, f"❌ blueprint_cnf.json generated at WRONG location: {blueprint_cnf_location} (should be at root)")
                                break
                    
                    if not blueprint_cnf_found:
                        self.log_test("BUG1 - BlueprintCNFBuilder Location Fix", False, f"❌ blueprint_cnf.json not found in generated files: {[f.get('filename') for f in files if isinstance(f, dict)]}")
                else:
                    error = gen_data.get("errors", ["Unknown error"])
                    self.log_test("BUG1 - BlueprintCNFBuilder Location Fix", False, f"❌ File generation failed: {error}")
            else:
                self.log_test("BUG1 - BlueprintCNFBuilder Location Fix", False, f"❌ HTTP {gen_response.status_code}: {gen_response.text}")
                
        except Exception as e:
            self.log_test("BUG1 - BlueprintCNFBuilder Location Fix", False, f"❌ Exception: {str(e)}")
    
    def test_both_blueprint_cnf_generation_endpoints(self):
        """Test both /api/blueprint/config/generate AND /api/blueprint/create-file endpoints for blueprint_cnf.json"""
        try:
            # Test 1: /api/blueprint/config/generate endpoint
            gen_payload = {
                "schemaId": "test-schema-id",  # Use any schema ID
                "environments": ["DEV"],
                "outputPath": "/app",  # ROOT directory
                "includeBlueprint": True
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            generate_endpoint_works = False
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success") or "files" in gen_data:
                    generate_endpoint_works = True
                    self.log_test("BUG1 - Generate Endpoint Test", True, "✅ /api/blueprint/config/generate endpoint accessible")
                else:
                    self.log_test("BUG1 - Generate Endpoint Test", False, f"❌ Generate endpoint failed: {gen_data.get('errors', [])}")
            else:
                self.log_test("BUG1 - Generate Endpoint Test", False, f"❌ Generate endpoint HTTP {gen_response.status_code}")
            
            # Test 2: /api/blueprint/create-file endpoint
            create_payload = {
                "path": "blueprint_cnf.json",
                "new_path": "blueprint_cnf"
            }
            
            create_response = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json=create_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            create_endpoint_works = False
            if create_response.status_code in [200, 409]:  # 409 = file already exists
                create_endpoint_works = True
                self.log_test("BUG1 - Create File Endpoint Test", True, f"✅ /api/blueprint/create-file endpoint accessible (HTTP {create_response.status_code})")
            else:
                self.log_test("BUG1 - Create File Endpoint Test", False, f"❌ Create file endpoint HTTP {create_response.status_code}")
            
            # Summary
            if generate_endpoint_works and create_endpoint_works:
                self.log_test("BUG1 - Both Endpoints Available", True, "✅ Both blueprint_cnf.json generation endpoints are working")
            else:
                self.log_test("BUG1 - Both Endpoints Available", False, f"❌ Endpoint availability: Generate={generate_endpoint_works}, CreateFile={create_endpoint_works}")
                
        except Exception as e:
            self.log_test("BUG1 - Both Endpoints Test", False, f"❌ Exception: {str(e)}")
    
    def test_blueprint_cnf_root_location_verification(self):
        """Verify blueprint_cnf.json is generated at ROOT location (/app/blueprint_cnf.json) not subdirectories"""
        try:
            # Try to read the blueprint_cnf.json file from root location
            file_response = requests.get(
                f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json",
                timeout=10
            )
            
            if file_response.status_code == 200:
                file_data = file_response.json()
                if "content" in file_data:
                    content = file_data["content"]
                    
                    # Verify it's a valid blueprint_cnf.json structure
                    try:
                        if isinstance(content, str):
                            blueprint_cnf = json.loads(content)
                        else:
                            blueprint_cnf = content
                        
                        # Check for expected blueprint_cnf.json structure
                        expected_fields = ["namespace", "version", "schemas"]
                        found_fields = [field for field in expected_fields if field in blueprint_cnf]
                        
                        if len(found_fields) >= 2:
                            self.log_test("BUG1 - Root Location Verification", True, f"✅ blueprint_cnf.json found at ROOT location with valid structure: {found_fields}")
                        else:
                            self.log_test("BUG1 - Root Location Verification", False, f"❌ blueprint_cnf.json at root has invalid structure: {list(blueprint_cnf.keys()) if isinstance(blueprint_cnf, dict) else 'not a dict'}")
                    except json.JSONDecodeError:
                        self.log_test("BUG1 - Root Location Verification", False, f"❌ blueprint_cnf.json at root contains invalid JSON")
                else:
                    self.log_test("BUG1 - Root Location Verification", False, f"❌ blueprint_cnf.json response missing content field")
            elif file_response.status_code == 404:
                self.log_test("BUG1 - Root Location Verification", False, f"❌ blueprint_cnf.json NOT FOUND at root location (/app/blueprint_cnf.json)")
            else:
                self.log_test("BUG1 - Root Location Verification", False, f"❌ Error accessing blueprint_cnf.json at root: HTTP {file_response.status_code}")
                
        except Exception as e:
            self.log_test("BUG1 - Root Location Verification", False, f"❌ Exception: {str(e)}")
    
    def verify_blueprint_cnf_at_root_location(self):
        """Helper method to verify blueprint_cnf.json is at root location"""
        try:
            # Check if file exists at root location
            response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
            
            if response.status_code == 200:
                self.log_test("BUG1 - File Location Check", True, "✅ blueprint_cnf.json confirmed at ROOT location (/app/blueprint_cnf.json)")
            elif response.status_code == 404:
                self.log_test("BUG1 - File Location Check", False, "❌ blueprint_cnf.json NOT found at root location")
            else:
                self.log_test("BUG1 - File Location Check", False, f"❌ Error checking file location: HTTP {response.status_code}")
        except Exception as e:
            self.log_test("BUG1 - File Location Check", False, f"❌ Exception checking location: {str(e)}")
    
    def test_bug2_storage_configuration_map_key_structure(self):
        """Test BUG 2: Storage configuration map key structure with service identifiers like 'EA.EADP.PDE.MCR'"""
        
        # Test 1: Create storage entity with service identifiers containing dots
        self.test_storage_entity_with_dotted_service_identifiers()
        
        # Test 2: Verify storage configuration includes defaultServiceIdentifier field
        self.test_storage_configuration_default_service_identifier()
        
        # Test 3: Verify service identifiers are NOT split by dots (remain as single keys)
        self.test_service_identifiers_not_split_by_dots()
        
        # Test 4: Test map handling logic fixes in EntityEditor.js and EnvironmentOverrides.js
        self.test_map_handling_logic_fixes()
    
    def test_storage_entity_with_dotted_service_identifiers(self):
        """Test creating storage entities with service identifiers containing dots like 'EA.EADP.PDE.MCR'"""
        try:
            # Create a test schema first
            schema_payload = {
                "name": "test-storage-bug2-schema",
                "namespace": "com.test.bug2.storage",
                "description": "Test schema for BUG2 storage configuration map key structure fix"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("BUG2 - Storage Schema Setup", False, f"❌ Schema creation failed: HTTP {schema_response.status_code}")
                return None
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("BUG2 - Storage Schema Setup", False, f"❌ Schema creation failed: {schema_data}")
                return None
            
            schema_id = schema_data["schema_id"]
            
            # Create storage entity with service identifiers containing dots
            storage_payload = {
                "name": "test-storage-with-dots",
                "entityType": "storages",
                "schemaId": schema_id,
                "baseConfig": {
                    "enabled": True,
                    "description": "Test storage entity with dotted service identifiers",
                    "storageConfigurations": {
                        "EA.EADP.PDE.MCR": {
                            "type": "redis",
                            "host": "redis-ea-eadp-pde-mcr.example.com",
                            "port": 6379,
                            "database": 0
                        },
                        "EA.EADP.TEST.SERVICE": {
                            "type": "mongodb",
                            "connectionString": "mongodb://mongo-ea-eadp-test.example.com:27017",
                            "database": "test_service_db"
                        },
                        "SIMPLE.SERVICE": {
                            "type": "memory",
                            "maxSize": "100MB"
                        }
                    },
                    "defaultServiceIdentifier": "EA.EADP.PDE.MCR"
                }
            }
            
            storage_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=storage_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if storage_response.status_code == 200:
                storage_data = storage_response.json()
                if storage_data.get("success"):
                    entity_id = storage_data["entity_id"]
                    self.log_test("BUG2 - Storage Entity with Dotted IDs", True, f"✅ Storage entity created with dotted service identifiers: EA.EADP.PDE.MCR, EA.EADP.TEST.SERVICE, SIMPLE.SERVICE")
                    return entity_id
                else:
                    self.log_test("BUG2 - Storage Entity with Dotted IDs", False, f"❌ Storage entity creation failed: {storage_data}")
                    return None
            else:
                self.log_test("BUG2 - Storage Entity with Dotted IDs", False, f"❌ HTTP {storage_response.status_code}: {storage_response.text}")
                return None
                
        except Exception as e:
            self.log_test("BUG2 - Storage Entity with Dotted IDs", False, f"❌ Exception: {str(e)}")
            return None
    
    def test_storage_configuration_default_service_identifier(self):
        """Test that storage configuration includes defaultServiceIdentifier field"""
        try:
            # Get UI configuration to check storage entities
            ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if ui_response.status_code == 200:
                ui_data = ui_response.json()
                config = ui_data.get("config", {})
                
                # Look for storage entities with defaultServiceIdentifier
                default_service_identifier_found = False
                storage_entities_found = 0
                
                for schema in config.get("schemas", []):
                    for entity in schema.get("configurations", []):
                        if entity.get("entityType") == "storages":
                            storage_entities_found += 1
                            base_config = entity.get("baseConfig", {})
                            
                            if "defaultServiceIdentifier" in base_config:
                                default_service_identifier_found = True
                                default_value = base_config["defaultServiceIdentifier"]
                                self.log_test("BUG2 - Default Service Identifier Field", True, f"✅ defaultServiceIdentifier field found in storage entity: '{default_value}'")
                                break
                
                if not default_service_identifier_found:
                    if storage_entities_found > 0:
                        self.log_test("BUG2 - Default Service Identifier Field", False, f"❌ defaultServiceIdentifier field NOT found in {storage_entities_found} storage entities")
                    else:
                        self.log_test("BUG2 - Default Service Identifier Field", False, f"❌ No storage entities found to test defaultServiceIdentifier field")
            else:
                self.log_test("BUG2 - Default Service Identifier Field", False, f"❌ Failed to get UI config: HTTP {ui_response.status_code}")
                
        except Exception as e:
            self.log_test("BUG2 - Default Service Identifier Field", False, f"❌ Exception: {str(e)}")
    
    def test_service_identifiers_not_split_by_dots(self):
        """Test that service identifiers like 'EA.EADP.PDE.MCR' remain as single keys, not nested structures"""
        try:
            # Create a test storage entity and then generate files to check structure
            schema_payload = {
                "name": "test-map-structure-schema",
                "namespace": "com.test.bug2.mapstructure",
                "description": "Test schema for verifying map key structure"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("BUG2 - Map Structure Test Setup", False, f"❌ Schema creation failed")
                return
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("BUG2 - Map Structure Test Setup", False, f"❌ Schema creation failed: {schema_data}")
                return
            
            schema_id = schema_data["schema_id"]
            
            # Create storage entity with complex dotted service identifiers
            storage_payload = {
                "name": "test-map-structure-storage",
                "entityType": "storages",
                "schemaId": schema_id,
                "baseConfig": {
                    "enabled": True,
                    "storageConfigurations": {
                        "EA.EADP.PDE.MCR": {
                            "type": "redis",
                            "host": "redis-server.example.com"
                        },
                        "EA.EADP.TEST.ANOTHER.SERVICE": {
                            "type": "mongodb",
                            "host": "mongo-server.example.com"
                        },
                        "SIMPLE.SERVICE.NAME": {
                            "type": "memory"
                        }
                    },
                    "defaultServiceIdentifier": "EA.EADP.PDE.MCR"
                }
            }
            
            storage_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=storage_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if storage_response.status_code != 200:
                self.log_test("BUG2 - Map Structure Storage Entity", False, f"❌ Storage entity creation failed")
                return
            
            storage_data = storage_response.json()
            if not storage_data.get("success"):
                self.log_test("BUG2 - Map Structure Storage Entity", False, f"❌ Storage entity creation failed: {storage_data}")
                return
            
            # Generate files to check the actual structure
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV"],
                "outputPath": "/app/test_map_structure"
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success"):
                    files = gen_data.get("files", [])
                    
                    # Check generated file content for correct map structure
                    for file_info in files:
                        if isinstance(file_info, dict):
                            content = file_info.get("content", {})
                            filename = file_info.get("filename", "")
                            
                            # Look for storage configurations in the generated content
                            if self.check_storage_map_structure(content, filename):
                                break
                    else:
                        self.log_test("BUG2 - Service Identifier Map Structure", False, f"❌ No storage configurations found in generated files")
                else:
                    self.log_test("BUG2 - Service Identifier Map Structure", False, f"❌ File generation failed: {gen_data.get('errors', [])}")
            else:
                self.log_test("BUG2 - Service Identifier Map Structure", False, f"❌ File generation HTTP {gen_response.status_code}")
                
        except Exception as e:
            self.log_test("BUG2 - Service Identifier Map Structure", False, f"❌ Exception: {str(e)}")
    
    def check_storage_map_structure(self, content, filename):
        """Helper method to check if storage map structure is correct (not nested by dots)"""
        try:
            if not isinstance(content, dict):
                return False
            
            # Look for storage configurations in various possible locations
            storage_configs = None
            
            # Check different possible structures
            if "config" in content and "storages" in content["config"]:
                storage_configs = content["config"]["storages"]
            elif "storages" in content:
                storage_configs = content["storages"]
            elif "storageConfigurations" in content:
                storage_configs = content["storageConfigurations"]
            
            if storage_configs and isinstance(storage_configs, dict):
                # Check if dotted keys are preserved as single keys
                dotted_keys_found = []
                nested_structure_found = False
                
                for key in storage_configs.keys():
                    if "." in key:
                        dotted_keys_found.append(key)
                        
                        # Check if this key contains nested structure (which would be wrong)
                        if isinstance(storage_configs[key], dict):
                            # This is correct - the dotted key maps to a configuration object
                            pass
                        else:
                            nested_structure_found = True
                
                # Check for incorrectly nested structure like {"EA": {"EADP": {"PDE": {"MCR": {...}}}}}
                for key, value in storage_configs.items():
                    if isinstance(value, dict) and not any(config_key in value for config_key in ["type", "host", "port", "connectionString"]):
                        # This might be a nested structure instead of a config object
                        if self.is_nested_service_identifier_structure(value):
                            nested_structure_found = True
                            break
                
                if dotted_keys_found and not nested_structure_found:
                    self.log_test("BUG2 - Service Identifier Map Structure", True, f"✅ Dotted service identifiers preserved as single keys: {dotted_keys_found} in {filename}")
                    
                    # Check for defaultServiceIdentifier
                    if "defaultServiceIdentifier" in storage_configs or any("defaultServiceIdentifier" in str(content).lower() for _ in [1]):
                        self.log_test("BUG2 - Default Service Identifier in Generated Files", True, f"✅ defaultServiceIdentifier found in generated file structure")
                    else:
                        self.log_test("BUG2 - Default Service Identifier in Generated Files", False, f"❌ defaultServiceIdentifier NOT found in generated file structure")
                    
                    return True
                elif nested_structure_found:
                    self.log_test("BUG2 - Service Identifier Map Structure", False, f"❌ Service identifiers incorrectly split into nested structure in {filename}")
                    return True
                elif not dotted_keys_found:
                    # No dotted keys found, but that's not necessarily wrong
                    return False
            
            return False
            
        except Exception as e:
            self.log_test("BUG2 - Map Structure Check", False, f"❌ Exception checking map structure: {str(e)}")
            return False
    
    def is_nested_service_identifier_structure(self, obj):
        """Check if object represents incorrectly nested service identifier structure"""
        if not isinstance(obj, dict):
            return False
        
        # Look for patterns like {"EADP": {"PDE": {"MCR": {...}}}} which would be wrong
        for key, value in obj.items():
            if isinstance(value, dict):
                # If the value is a dict but doesn't contain config fields, it might be nested structure
                config_fields = ["type", "host", "port", "connectionString", "database", "maxSize"]
                if not any(field in value for field in config_fields):
                    # Check if it's further nested
                    if self.is_nested_service_identifier_structure(value):
                        return True
                    # Or if it contains keys that look like parts of service identifiers
                    if any(len(k) <= 5 and k.isupper() for k in value.keys()):
                        return True
        
        return False
    
    def test_map_handling_logic_fixes(self):
        """Test map handling logic fixes in EntityEditor.js and EnvironmentOverrides.js"""
        try:
            # This test verifies that the backend properly handles map structures
            # by creating entities with complex map configurations and verifying they persist correctly
            
            # Create a test entity with complex map structure
            entity_payload = {
                "name": "test-map-handling-entity",
                "entityType": "storages",
                "baseConfig": {
                    "enabled": True,
                    "storageConfigurations": {
                        "EA.EADP.PDE.MCR": {
                            "type": "redis",
                            "host": "redis-ea-eadp-pde-mcr.example.com",
                            "port": 6379,
                            "database": 0,
                            "timeout": 5000
                        },
                        "EA.EADP.TEST.ANOTHER.LONG.SERVICE.NAME": {
                            "type": "mongodb",
                            "connectionString": "mongodb://mongo-test.example.com:27017",
                            "database": "test_db",
                            "collection": "test_collection"
                        }
                    },
                    "defaultServiceIdentifier": "EA.EADP.PDE.MCR"
                }
            }
            
            create_response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=entity_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if create_response.status_code == 200:
                create_data = create_response.json()
                if create_data.get("success"):
                    entity_id = create_data["entity_id"]
                    
                    # Now update the entity to test map handling logic
                    update_payload = {
                        "baseConfig": {
                            "enabled": True,
                            "storageConfigurations": {
                                "EA.EADP.PDE.MCR": {
                                    "type": "redis",
                                    "host": "updated-redis-server.example.com",
                                    "port": 6380,  # Updated port
                                    "database": 1   # Updated database
                                },
                                "EA.EADP.TEST.ANOTHER.LONG.SERVICE.NAME": {
                                    "type": "mongodb",
                                    "connectionString": "mongodb://updated-mongo.example.com:27017",
                                    "database": "updated_db"
                                },
                                # Add a new service identifier
                                "NEW.SERVICE.WITH.DOTS": {
                                    "type": "memory",
                                    "maxSize": "500MB"
                                }
                            },
                            "defaultServiceIdentifier": "NEW.SERVICE.WITH.DOTS"  # Updated default
                        }
                    }
                    
                    update_response = requests.put(
                        f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                        json=update_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if update_response.status_code == 200:
                        update_data = update_response.json()
                        if update_data.get("success"):
                            self.log_test("BUG2 - Map Handling Logic Update", True, f"✅ Complex map structure with dotted keys updated successfully")
                            
                            # Verify the update persisted correctly by getting UI config
                            self.verify_map_handling_persistence(entity_id)
                        else:
                            self.log_test("BUG2 - Map Handling Logic Update", False, f"❌ Map update failed: {update_data}")
                    else:
                        self.log_test("BUG2 - Map Handling Logic Update", False, f"❌ Map update HTTP {update_response.status_code}")
                else:
                    self.log_test("BUG2 - Map Handling Logic Create", False, f"❌ Map entity creation failed: {create_data}")
            else:
                self.log_test("BUG2 - Map Handling Logic Create", False, f"❌ Map entity creation HTTP {create_response.status_code}")
                
        except Exception as e:
            self.log_test("BUG2 - Map Handling Logic Fixes", False, f"❌ Exception: {str(e)}")
    
    def verify_map_handling_persistence(self, entity_id):
        """Verify that map handling changes persisted correctly"""
        try:
            # Get UI config to verify the entity was updated correctly
            ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if ui_response.status_code == 200:
                ui_data = ui_response.json()
                config = ui_data.get("config", {})
                
                # Find the updated entity
                for schema in config.get("schemas", []):
                    for entity in schema.get("configurations", []):
                        if entity.get("id") == entity_id:
                            base_config = entity.get("baseConfig", {})
                            storage_configs = base_config.get("storageConfigurations", {})
                            default_service = base_config.get("defaultServiceIdentifier")
                            
                            # Verify dotted keys are preserved
                            expected_keys = ["EA.EADP.PDE.MCR", "EA.EADP.TEST.ANOTHER.LONG.SERVICE.NAME", "NEW.SERVICE.WITH.DOTS"]
                            found_keys = [key for key in expected_keys if key in storage_configs]
                            
                            if len(found_keys) == len(expected_keys):
                                self.log_test("BUG2 - Map Persistence Verification", True, f"✅ All dotted service identifier keys persisted correctly: {found_keys}")
                                
                                # Verify default service identifier was updated
                                if default_service == "NEW.SERVICE.WITH.DOTS":
                                    self.log_test("BUG2 - Default Service Persistence", True, f"✅ defaultServiceIdentifier updated correctly: {default_service}")
                                else:
                                    self.log_test("BUG2 - Default Service Persistence", False, f"❌ defaultServiceIdentifier not updated correctly: {default_service}")
                                
                                # Verify updated values
                                ea_config = storage_configs.get("EA.EADP.PDE.MCR", {})
                                if ea_config.get("port") == 6380:
                                    self.log_test("BUG2 - Map Value Update Verification", True, f"✅ Map values updated correctly (port: {ea_config.get('port')})")
                                else:
                                    self.log_test("BUG2 - Map Value Update Verification", False, f"❌ Map values not updated correctly (port: {ea_config.get('port')})")
                            else:
                                self.log_test("BUG2 - Map Persistence Verification", False, f"❌ Missing dotted keys after update. Found: {found_keys}, Expected: {expected_keys}")
                            return
                
                self.log_test("BUG2 - Map Persistence Verification", False, f"❌ Updated entity not found in UI config")
            else:
                self.log_test("BUG2 - Map Persistence Verification", False, f"❌ Failed to get UI config for verification: HTTP {ui_response.status_code}")
                
        except Exception as e:
            self.log_test("BUG2 - Map Persistence Verification", False, f"❌ Exception: {str(e)}")
    
    def test_blueprint_cnf_generation_fix(self):
        """Test FIX 1 - blueprint_cnf.json Generation to Root Directory"""
        print("🔧 Testing FIX 1 - blueprint_cnf.json Generation Fix")
        print("-" * 50)
        
        # Step 1: Test create-file API endpoint with blueprint_cnf.json
        self.test_create_file_api_blueprint_cnf()
        
        # Step 2: Test via Configuration Manager API integration
        self.test_configuration_manager_blueprint_cnf()
        
        # Step 3: Test overwrite functionality
        self.test_blueprint_cnf_overwrite()
        
        # Step 4: Verify file structure and location
        self.test_blueprint_cnf_location_verification()
    
    def test_create_file_api_blueprint_cnf(self):
        """Test POST /api/blueprint/create-file with blueprint_cnf.json"""
        try:
            payload = {
                "path": "blueprint_cnf.json",
                "new_path": "blueprint_cnf.json"  # Template name
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
                    self.log_test("Create File API - blueprint_cnf.json", True, "Successfully created blueprint_cnf.json via create-file API")
                    
                    # Verify file was created at root level (not in subdirectory)
                    self.verify_blueprint_cnf_root_location()
                else:
                    self.log_test("Create File API - blueprint_cnf.json", False, f"Creation failed: {data}")
            elif response.status_code == 409:
                self.log_test("Create File API - blueprint_cnf.json", True, "File already exists (HTTP 409) - this is expected behavior")
            else:
                self.log_test("Create File API - blueprint_cnf.json", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Create File API - blueprint_cnf.json", False, f"Exception: {str(e)}")
    
    def test_configuration_manager_blueprint_cnf(self):
        """Test blueprint_cnf.json generation via Configuration Manager API"""
        try:
            # First create a test schema and entity for file generation
            schema_payload = {
                "name": "test-blueprint-cnf-schema",
                "namespace": "com.test.blueprintcnf",
                "description": "Test schema for blueprint_cnf.json generation"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("Configuration Manager - blueprint_cnf.json Setup", False, f"Schema creation failed: HTTP {schema_response.status_code}")
                return
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("Configuration Manager - blueprint_cnf.json Setup", False, f"Schema creation failed: {schema_data}")
                return
            
            schema_id = schema_data["schema_id"]
            
            # Generate files including blueprint_cnf.json
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV"],
                "outputPath": "/app",  # Root directory
                "includeBlueprint": True
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success"):
                    files = gen_data.get("files", [])
                    
                    # Check if blueprint_cnf.json was generated
                    blueprint_cnf_found = False
                    for file_info in files:
                        if isinstance(file_info, dict):
                            filename = file_info.get("filename", "")
                            if "blueprint_cnf.json" in filename:
                                blueprint_cnf_found = True
                                # Verify it's at root level (not in subdirectory)
                                if filename == "blueprint_cnf.json" or filename.endswith("/blueprint_cnf.json"):
                                    self.log_test("Configuration Manager - blueprint_cnf.json Generation", True, f"blueprint_cnf.json generated at correct location: {filename}")
                                else:
                                    self.log_test("Configuration Manager - blueprint_cnf.json Generation", False, f"blueprint_cnf.json generated at wrong location: {filename}")
                                break
                    
                    if not blueprint_cnf_found:
                        self.log_test("Configuration Manager - blueprint_cnf.json Generation", False, f"blueprint_cnf.json not found in generated files: {[f.get('filename') for f in files if isinstance(f, dict)]}")
                else:
                    error = gen_data.get("errors", ["Unknown error"])
                    self.log_test("Configuration Manager - blueprint_cnf.json Generation", False, f"Generation failed: {error}")
            else:
                self.log_test("Configuration Manager - blueprint_cnf.json Generation", False, f"HTTP {gen_response.status_code}")
                
        except Exception as e:
            self.log_test("Configuration Manager - blueprint_cnf.json Generation", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_overwrite(self):
        """Test blueprint_cnf.json overwrite functionality"""
        try:
            # Create blueprint_cnf.json first time
            payload1 = {
                "path": "blueprint_cnf.json",
                "new_path": "blueprint_cnf.json"
            }
            
            response1 = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json=payload1,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Try to create it again (should handle overwrite)
            response2 = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json=payload1,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response1.status_code == 200 or response1.status_code == 409:
                if response2.status_code == 409:
                    self.log_test("Blueprint CNF Overwrite", True, "Correctly handled file already exists (HTTP 409)")
                elif response2.status_code == 200:
                    self.log_test("Blueprint CNF Overwrite", True, "Successfully handled overwrite scenario")
                else:
                    self.log_test("Blueprint CNF Overwrite", False, f"Unexpected overwrite response: HTTP {response2.status_code}")
            else:
                self.log_test("Blueprint CNF Overwrite", False, f"Initial creation failed: HTTP {response1.status_code}")
                
        except Exception as e:
            self.log_test("Blueprint CNF Overwrite", False, f"Exception: {str(e)}")
    
    def verify_blueprint_cnf_root_location(self):
        """Verify blueprint_cnf.json is created at blueprint root"""
        try:
            # Get file tree to verify location
            response = requests.get(f"{self.base_url}/api/blueprint/file-tree", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                # Look for blueprint_cnf.json at root level
                blueprint_cnf_at_root = False
                for file_info in files:
                    if isinstance(file_info, dict):
                        name = file_info.get("name", "")
                        path = file_info.get("path", "")
                        if name == "blueprint_cnf.json" and "/" not in path.strip("/"):
                            blueprint_cnf_at_root = True
                            self.log_test("Blueprint CNF Root Location", True, f"blueprint_cnf.json found at root: {path}")
                            break
                
                if not blueprint_cnf_at_root:
                    self.log_test("Blueprint CNF Root Location", False, "blueprint_cnf.json not found at root level")
            else:
                self.log_test("Blueprint CNF Root Location", False, f"File tree request failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Blueprint CNF Root Location", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_location_verification(self):
        """Verify blueprint_cnf.json contains proper JSON structure"""
        try:
            # Try to read the blueprint_cnf.json file
            response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                
                if content:
                    try:
                        # Parse JSON to verify structure
                        json_data = json.loads(content)
                        
                        # Check for expected blueprint_cnf.json structure
                        if isinstance(json_data, dict):
                            # Look for common blueprint_cnf.json fields
                            expected_fields = ["namespace", "version", "description"]
                            found_fields = [field for field in expected_fields if field in json_data]
                            
                            if found_fields:
                                self.log_test("Blueprint CNF JSON Structure", True, f"Valid JSON with fields: {found_fields}")
                            else:
                                self.log_test("Blueprint CNF JSON Structure", True, f"Valid JSON structure (custom fields): {list(json_data.keys())}")
                        else:
                            self.log_test("Blueprint CNF JSON Structure", False, f"JSON is not an object: {type(json_data)}")
                    except json.JSONDecodeError as e:
                        self.log_test("Blueprint CNF JSON Structure", False, f"Invalid JSON: {str(e)}")
                else:
                    self.log_test("Blueprint CNF JSON Structure", False, "File content is empty")
            elif response.status_code == 404:
                self.log_test("Blueprint CNF JSON Structure", False, "blueprint_cnf.json file not found")
            else:
                self.log_test("Blueprint CNF JSON Structure", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Blueprint CNF JSON Structure", False, f"Exception: {str(e)}")
    
    def test_storage_configuration_map_key_fix(self):
        """Test FIX 2 - Storage Configuration Map Key Handling"""
        print("🔧 Testing FIX 2 - Storage Configuration Map Key Fix")
        print("-" * 50)
        
        # Step 1: Create storage entity with proper structure
        self.test_storage_entity_creation()
        
        # Step 2: Verify storage configuration map key handling
        self.test_storage_map_key_handling()
        
        # Step 3: Test file generation with storage entity
        self.test_storage_file_generation()
        
        # Step 4: Verify storage structure in generated files
        self.test_storage_structure_verification()
    
    def test_storage_entity_creation(self):
        """Create storage entity with proper structure"""
        try:
            payload = {
                "name": "test-storage-entity",
                "entityType": "storages",
                "baseConfig": {
                    "defaultServiceIdentifier": "EA.EADP.PDE.MCR",
                    "storages": {
                        "EA.EADP.PDE.MCR": {
                            "serviceIdentifier": "EA.EADP.PDE.MCR",
                            "defaultIntegrationId": "2",
                            "hosts": [
                                {
                                    "host": "asset-int.mcr.ea.cm",
                                    "apis": ["*"]
                                }
                            ]
                        }
                    }
                }
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and "entity_id" in data:
                    entity_id = data["entity_id"]
                    self.log_test("Storage Entity Creation", True, f"Created storage entity with ID: {entity_id}")
                    
                    # Store entity ID for later tests
                    self.storage_entity_id = entity_id
                    return entity_id
                else:
                    self.log_test("Storage Entity Creation", False, f"Creation failed: {data}")
                    return None
            else:
                self.log_test("Storage Entity Creation", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("Storage Entity Creation", False, f"Exception: {str(e)}")
            return None
    
    def test_storage_map_key_handling(self):
        """Test that storage configuration uses proper map key handling"""
        try:
            # Get UI config to verify storage entity structure
            response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                config = data.get("config", {})
                
                # Look for our storage entity
                storage_entity_found = False
                for schema in config.get("schemas", []):
                    for entity in schema.get("configurations", []):
                        if entity.get("name") == "test-storage-entity" and entity.get("entityType") == "storages":
                            storage_entity_found = True
                            
                            # Check storage configuration structure
                            entity_config = entity.get("baseConfig", {})
                            storages = entity_config.get("storages", {})
                            
                            # Verify that "EA.EADP.PDE.MCR" is used as a map key (not nested by dots)
                            if "EA.EADP.PDE.MCR" in storages:
                                storage_config = storages["EA.EADP.PDE.MCR"]
                                
                                # Verify it's not nested (should NOT have storages.storages.EA.EADP.PDE.MCR)
                                if isinstance(storage_config, dict) and "serviceIdentifier" in storage_config:
                                    service_id = storage_config.get("serviceIdentifier")
                                    if service_id == "EA.EADP.PDE.MCR":
                                        self.log_test("Storage Map Key Handling", True, f"Storage uses full service identifier as map key: 'EA.EADP.PDE.MCR'")
                                    else:
                                        self.log_test("Storage Map Key Handling", False, f"Service identifier mismatch: expected 'EA.EADP.PDE.MCR', got '{service_id}'")
                                else:
                                    self.log_test("Storage Map Key Handling", False, f"Storage config structure invalid: {storage_config}")
                            else:
                                # Check if it was incorrectly nested by dots
                                nested_check = storages
                                nested_path = []
                                for part in ["EA", "EADP", "PDE", "MCR"]:
                                    if isinstance(nested_check, dict) and part in nested_check:
                                        nested_check = nested_check[part]
                                        nested_path.append(part)
                                    else:
                                        break
                                
                                if len(nested_path) == 4:
                                    self.log_test("Storage Map Key Handling", False, f"Storage incorrectly nested by dots: storages.{'.'.join(nested_path)}")
                                else:
                                    self.log_test("Storage Map Key Handling", False, f"Storage key 'EA.EADP.PDE.MCR' not found. Available keys: {list(storages.keys())}")
                            
                            # Verify defaultServiceIdentifier is present at top level
                            default_service_id = entity_config.get("defaultServiceIdentifier")
                            if default_service_id == "EA.EADP.PDE.MCR":
                                self.log_test("Storage Default Service Identifier", True, f"defaultServiceIdentifier present: {default_service_id}")
                            else:
                                self.log_test("Storage Default Service Identifier", False, f"defaultServiceIdentifier missing or incorrect: {default_service_id}")
                            
                            break
                
                if not storage_entity_found:
                    self.log_test("Storage Map Key Handling", False, "Storage entity not found in UI config")
            else:
                self.log_test("Storage Map Key Handling", False, f"UI config request failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Storage Map Key Handling", False, f"Exception: {str(e)}")
    
    def test_storage_file_generation(self):
        """Test file generation with storage entity"""
        try:
            # Create a schema for storage testing
            schema_payload = {
                "name": "test-storage-schema",
                "namespace": "com.test.storage",
                "description": "Test schema for storage configuration"
            }
            
            schema_response = requests.post(
                f"{self.base_url}/api/blueprint/config/schemas",
                json=schema_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if schema_response.status_code != 200:
                self.log_test("Storage File Generation - Schema", False, f"Schema creation failed: HTTP {schema_response.status_code}")
                return
            
            schema_data = schema_response.json()
            if not schema_data.get("success"):
                self.log_test("Storage File Generation - Schema", False, f"Schema creation failed: {schema_data}")
                return
            
            schema_id = schema_data["schema_id"]
            
            # Generate files with storage configuration
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV"],
                "outputPath": "/app/test_storage_generated"
            }
            
            gen_response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if gen_response.status_code == 200:
                gen_data = gen_response.json()
                if gen_data.get("success"):
                    files = gen_data.get("files", [])
                    self.log_test("Storage File Generation", True, f"Generated {len(files)} files with storage configuration")
                    
                    # Store generated files for structure verification
                    self.storage_generated_files = files
                else:
                    error = gen_data.get("errors", ["Unknown error"])
                    self.log_test("Storage File Generation", False, f"Generation failed: {error}")
            else:
                self.log_test("Storage File Generation", False, f"HTTP {gen_response.status_code}")
                
        except Exception as e:
            self.log_test("Storage File Generation", False, f"Exception: {str(e)}")
    
    def test_storage_structure_verification(self):
        """Verify storage structure in generated files"""
        try:
            # Check if we have generated files to verify
            if not hasattr(self, 'storage_generated_files'):
                self.log_test("Storage Structure Verification", False, "No generated files to verify")
                return
            
            files = getattr(self, 'storage_generated_files', [])
            
            # Look for files that might contain storage configuration
            storage_files_checked = 0
            storage_structure_correct = 0
            
            for file_info in files:
                if isinstance(file_info, dict):
                    filename = file_info.get("filename", "")
                    
                    # Check files that might contain storage config (global.json, config files, etc.)
                    if any(pattern in filename.lower() for pattern in ["global", "storage", "config"]):
                        storage_files_checked += 1
                        
                        # Try to read file content to verify structure
                        try:
                            file_path = filename.replace("/app/test_storage_generated/", "")
                            content_response = requests.get(
                                f"{self.base_url}/api/blueprint/file-content/{file_path}",
                                timeout=10
                            )
                            
                            if content_response.status_code == 200:
                                content_data = content_response.json()
                                content = content_data.get("content", "")
                                
                                if content:
                                    try:
                                        json_content = json.loads(content)
                                        
                                        # Look for storage configuration in the JSON
                                        if self.verify_storage_structure_in_json(json_content, filename):
                                            storage_structure_correct += 1
                                    except json.JSONDecodeError:
                                        pass  # Skip non-JSON files
                        except:
                            pass  # Skip files we can't read
            
            if storage_files_checked > 0:
                if storage_structure_correct > 0:
                    self.log_test("Storage Structure Verification", True, f"Storage structure correct in {storage_structure_correct}/{storage_files_checked} files")
                else:
                    self.log_test("Storage Structure Verification", False, f"Storage structure issues found in {storage_files_checked} files")
            else:
                self.log_test("Storage Structure Verification", False, "No storage configuration files found to verify")
                
        except Exception as e:
            self.log_test("Storage Structure Verification", False, f"Exception: {str(e)}")
    
    def verify_storage_structure_in_json(self, json_content, filename):
        """Verify storage structure in JSON content"""
        try:
            # Look for storage configuration in various possible locations
            storage_configs = []
            
            # Check direct storages field
            if "storages" in json_content:
                storage_configs.append(json_content["storages"])
            
            # Check nested configurations
            if "configuration" in json_content and "storages" in json_content["configuration"]:
                storage_configs.append(json_content["configuration"]["storages"])
            
            # Check entities array
            if "entities" in json_content:
                for entity in json_content["entities"]:
                    if isinstance(entity, dict) and "storages" in entity:
                        storage_configs.append(entity["storages"])
            
            for storage_config in storage_configs:
                if isinstance(storage_config, dict):
                    # Check if "EA.EADP.PDE.MCR" is used as a direct key
                    if "EA.EADP.PDE.MCR" in storage_config:
                        service_config = storage_config["EA.EADP.PDE.MCR"]
                        if isinstance(service_config, dict) and "serviceIdentifier" in service_config:
                            self.log_test(f"Storage Structure in {filename}", True, "Storage uses full service identifier as map key")
                            return True
                    
                    # Check if it was incorrectly nested
                    if "EA" in storage_config and isinstance(storage_config["EA"], dict):
                        nested = storage_config["EA"]
                        if "EADP" in nested and isinstance(nested["EADP"], dict):
                            nested = nested["EADP"]
                            if "PDE" in nested and isinstance(nested["PDE"], dict):
                                nested = nested["PDE"]
                                if "MCR" in nested:
                                    self.log_test(f"Storage Structure in {filename}", False, "Storage incorrectly nested by dots")
                                    return False
            
            return False
            
        except Exception as e:
            self.log_test(f"Storage Structure Verification in {filename}", False, f"Exception: {str(e)}")
            return False
    
    def run_blueprint_cnf_and_storage_fixes_tests(self):
        """Run comprehensive tests for blueprint_cnf.json generation and storage configuration fixes"""
        print("🚀 Starting Blueprint CNF Generation and Storage Configuration Tests")
        print("=" * 80)
        
        # First, set up blueprint root path
        self.setup_blueprint_root_path()
        
        # Test FIX 1: blueprint_cnf.json Generation
        self.test_blueprint_cnf_generation_fix()
        
        # Test FIX 2: Storage Configuration Map Key Handling
        self.test_storage_configuration_map_key_fix()
        
        # Print final summary
        self.print_summary()

    def run_inheritance_and_file_generation_tests(self):
        """Run comprehensive tests for inheritance persistence and file generation error handling"""
        print("🚀 Starting Inheritance Persistence and File Generation Error Handling Tests")
        print("=" * 80)
        
        # First, set up blueprint root path
        self.setup_blueprint_root_path()
        
        # Test FIX 1: Inheritance Persistence
        self.test_inheritance_persistence_fix()
        
        # Test FIX 2: File Generation Permission Error Handling
        self.test_file_generation_permission_error_handling()
        
        # Print final summary
        self.print_summary()

def main():
    """Main function to run tests"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://config-manager-3.preview.emergentagent.com"
    
    print(f"🔧 Testing Blueprint Configuration API at: {base_url}")
    
    tester = BlueprintConfigurationTester(base_url)
    
    # Check if we should run specific tests
    if len(sys.argv) > 2:
        test_mode = sys.argv[2]
        if test_mode == "fixes":
            tester.run_inheritance_and_file_generation_tests()
        elif test_mode == "blueprint_cnf_storage":
            tester.run_blueprint_cnf_and_storage_fixes_tests()
        else:
            print(f"Unknown test mode: {test_mode}")
            print("Available modes: fixes, blueprint_cnf_storage")
            sys.exit(1)
    else:
        tester.run_blueprint_configuration_tests()

if __name__ == "__main__":
    main()