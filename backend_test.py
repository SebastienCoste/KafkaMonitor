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

def main():
    """Main function to run tests"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://blueprint-creator-2.preview.emergentagent.com"
    
    print(f"🔧 Testing Blueprint Configuration API at: {base_url}")
    
    tester = BlueprintConfigurationTester(base_url)
    tester.run_blueprint_configuration_tests()

if __name__ == "__main__":
    main()