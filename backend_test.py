#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Blueprint Configuration API
Tests all Blueprint Configuration API endpoints with focus on error handling and HTTP status codes
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

class BlueprintConfigurationTester:
    def __init__(self, base_url: str = "https://blueprint-creator-2.preview.emergentagent.com"):
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
    
    def test_entity_definitions_api(self):
        """Test GET /api/blueprint/config/entity-definitions"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/config/entity-definitions", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for required structure
                if "entityTypes" in data:
                    entity_types = data["entityTypes"]
                    if len(entity_types) >= 11:  # Should have 11 entity types
                        # Verify some expected entity types
                        expected_types = ["access", "storages", "inferenceServiceConfigs", "messageStorage", "discoveryStorage"]
                        found_types = [et.get("name") for et in entity_types if et.get("name") in expected_types]
                        
                        if len(found_types) >= 3:
                            self.log_test("Entity Definitions API", True, f"Found {len(entity_types)} entity types including: {found_types}")
                            return data
                        else:
                            self.log_test("Entity Definitions API", False, f"Missing expected entity types. Found: {[et.get('name') for et in entity_types]}")
                            return None
                    else:
                        self.log_test("Entity Definitions API", False, f"Expected 11+ entity types, found {len(entity_types)}")
                        return None
                else:
                    self.log_test("Entity Definitions API", False, "Missing 'entityTypes' field in response")
                    return None
            else:
                self.log_test("Entity Definitions API", False, f"HTTP {response.status_code}")
                return None
        except Exception as e:
            self.log_test("Entity Definitions API", False, f"Exception: {str(e)}")
            return None
    
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

    def run_blueprint_configuration_tests(self):
        """Run comprehensive Blueprint Configuration API tests"""
        print("🚀 Starting Blueprint Configuration API Comprehensive Testing")
        print("=" * 70)
        
        # First, set up blueprint root path
        self.setup_blueprint_root_path()
        
        # Test 1: Entity Definitions API
        print("\n1️⃣ Testing Entity Definitions API")
        print("-" * 40)
        entity_definitions = self.test_entity_definitions_api()
        
        # Test 2: UI Configuration API  
        print("\n2️⃣ Testing UI Configuration API")
        print("-" * 40)
        ui_config = self.test_ui_configuration_api()
        
        # Test 3: Schema Creation API
        print("\n3️⃣ Testing Schema Creation API")
        print("-" * 40)
        schema_id = self.test_schema_creation_api()
        
        # Test 4: Entity Creation API (Success and Error Cases)
        print("\n4️⃣ Testing Entity Creation API")
        print("-" * 40)
        entity_id = self.test_entity_creation_api()
        
        # Test 5: Entity Update API (Success and Error Cases)
        print("\n5️⃣ Testing Entity Update API")
        print("-" * 40)
        if entity_id:
            self.test_entity_update_api(entity_id)
        
        # Test 6: Environment Overrides API (Success and Error Cases)
        print("\n6️⃣ Testing Environment Overrides API")
        print("-" * 40)
        if entity_id:
            self.test_environment_overrides_api(entity_id)
        
        # Test 7: File Generation API
        print("\n7️⃣ Testing File Generation API")
        print("-" * 40)
        if schema_id:
            self.test_file_generation_api(schema_id)
        
        # Test 8: Configuration Validation API
        print("\n8️⃣ Testing Configuration Validation API")
        print("-" * 40)
        self.test_configuration_validation_api()
        
        # Test 9: Entity Deletion API (Success and Error Cases)
        print("\n9️⃣ Testing Entity Deletion API")
        print("-" * 40)
        if entity_id:
            self.test_entity_deletion_api(entity_id)
        
        # Test 10: Error Handling Verification
        print("\n🔟 Testing Error Handling Verification")
        print("-" * 40)
        self.test_error_handling_verification()
        
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
        
        # Final assessment
        if success_rate >= 90:
            print(f"\n🎉 EXCELLENT: Blueprint Configuration API is working well!")
        elif success_rate >= 75:
            print(f"\n✅ GOOD: Blueprint Configuration API is mostly functional with minor issues")
        elif success_rate >= 50:
            print(f"\n⚠️ NEEDS ATTENTION: Blueprint Configuration API has significant issues")
        else:
            print(f"\n❌ CRITICAL: Blueprint Configuration API has major problems")

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
    
    def cleanup_test_entity(self, entity_id):
        """Clean up test entity"""
        if entity_id:
            try:
                requests.delete(f"{self.base_url}/api/blueprint/config/entities/{entity_id}", timeout=10)
                self.log_test("Cleanup Test Entity", True, f"Cleaned up entity {entity_id}")
            except:
                pass  # Ignore cleanup errors
    
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
                "configuration": {
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
                            entity_config = entity.get("configuration", {})
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
        base_url = "https://blueprint-creator-2.preview.emergentagent.com"
    
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