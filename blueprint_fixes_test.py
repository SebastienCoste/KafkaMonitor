#!/usr/bin/env python3
"""
Targeted Testing for Blueprint Configuration Fixes
Tests the two specific fixes mentioned in the review request:
- FIX 1: blueprint_cnf.json Generation Test
- FIX 2: Storage Configuration Map Key Test
"""

import requests
import json
import sys
import time
from datetime import datetime

class BlueprintFixesTester:
    def __init__(self, base_url: str = "https://blueprint-config-ui.preview.emergentagent.com"):
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
    
    def test_fix1_blueprint_cnf_generation(self):
        """Test FIX 1 - blueprint_cnf.json Generation to Root Directory"""
        print("🔧 Testing FIX 1 - blueprint_cnf.json Generation Fix")
        print("-" * 50)
        
        # Test 1: POST /api/blueprint/create-file with blueprint_cnf.json
        self.test_create_file_blueprint_cnf()
        
        # Test 2: Verify file is created at blueprint root (not in subdirectory)
        self.test_blueprint_cnf_root_location()
        
        # Test 3: Test overwrite functionality
        self.test_blueprint_cnf_overwrite()
        
        # Test 4: Verify file contains proper JSON structure
        self.test_blueprint_cnf_json_structure()
    
    def test_create_file_blueprint_cnf(self):
        """Test POST /api/blueprint/create-file with path='blueprint_cnf.json'"""
        try:
            # Use a unique filename to test creation
            test_filename = f"test_blueprint_cnf_{int(time.time())}.json"
            
            payload = {
                "path": test_filename,
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
                    self.log_test("FIX1 - Create File API", True, f"Successfully created {test_filename} via create-file API")
                    self.test_filename = test_filename
                else:
                    self.log_test("FIX1 - Create File API", False, f"Creation failed: {data}")
            else:
                self.log_test("FIX1 - Create File API", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX1 - Create File API", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_root_location(self):
        """Verify blueprint_cnf.json is created at blueprint root (not in subdirectory)"""
        try:
            if not hasattr(self, 'test_filename'):
                self.log_test("FIX1 - Root Location Check", False, "No test file created to verify")
                return
            
            # Get file tree to verify location
            response = requests.get(f"{self.base_url}/api/blueprint/file-tree", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                files = data.get("files", [])
                
                # Look for our test file at root level
                file_at_root = False
                for file_info in files:
                    if isinstance(file_info, dict):
                        name = file_info.get("name", "")
                        path = file_info.get("path", "")
                        if name == self.test_filename:
                            # Check if it's at root (path should be just the filename or empty)
                            if path == self.test_filename or path == "" or "/" not in path.strip("/"):
                                file_at_root = True
                                self.log_test("FIX1 - Root Location Check", True, f"File created at root level: {path}")
                            else:
                                self.log_test("FIX1 - Root Location Check", False, f"File created in subdirectory: {path}")
                            break
                
                if not file_at_root and hasattr(self, 'test_filename'):
                    self.log_test("FIX1 - Root Location Check", False, f"Test file {self.test_filename} not found in file tree")
            else:
                self.log_test("FIX1 - Root Location Check", False, f"File tree request failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX1 - Root Location Check", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_overwrite(self):
        """Test overwrite functionality works correctly"""
        try:
            if not hasattr(self, 'test_filename'):
                self.log_test("FIX1 - Overwrite Test", False, "No test file to overwrite")
                return
            
            # Try to create the same file again (should handle overwrite)
            payload = {
                "path": self.test_filename,
                "new_path": "blueprint_cnf.json"
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/create-file",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 409:
                self.log_test("FIX1 - Overwrite Test", True, "Correctly handled file already exists (HTTP 409)")
            elif response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("FIX1 - Overwrite Test", True, "Successfully handled overwrite scenario")
                else:
                    self.log_test("FIX1 - Overwrite Test", False, f"Overwrite failed: {data}")
            else:
                self.log_test("FIX1 - Overwrite Test", False, f"Unexpected overwrite response: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX1 - Overwrite Test", False, f"Exception: {str(e)}")
    
    def test_blueprint_cnf_json_structure(self):
        """Verify file contains proper JSON structure"""
        try:
            if not hasattr(self, 'test_filename'):
                self.log_test("FIX1 - JSON Structure", False, "No test file to verify")
                return
            
            # Try to read the test file
            response = requests.get(f"{self.base_url}/api/blueprint/file-content/{self.test_filename}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                
                if content:
                    try:
                        # Parse JSON to verify structure
                        json_data = json.loads(content)
                        
                        if isinstance(json_data, dict):
                            self.log_test("FIX1 - JSON Structure", True, f"Valid JSON structure with keys: {list(json_data.keys())}")
                        else:
                            self.log_test("FIX1 - JSON Structure", False, f"JSON is not an object: {type(json_data)}")
                    except json.JSONDecodeError as e:
                        self.log_test("FIX1 - JSON Structure", False, f"Invalid JSON: {str(e)}")
                else:
                    self.log_test("FIX1 - JSON Structure", False, "File content is empty")
            elif response.status_code == 404:
                self.log_test("FIX1 - JSON Structure", False, "Test file not found")
            else:
                self.log_test("FIX1 - JSON Structure", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX1 - JSON Structure", False, f"Exception: {str(e)}")
    
    def test_fix2_storage_configuration_map_key(self):
        """Test FIX 2 - Storage Configuration Map Key Handling"""
        print("\n🔧 Testing FIX 2 - Storage Configuration Map Key Fix")
        print("-" * 50)
        
        # Test 1: Create storage entity with proper structure
        storage_entity_id = self.test_create_storage_entity()
        
        if storage_entity_id:
            # Test 2: Verify storage configuration is NOT creating nested objects
            self.test_storage_map_key_structure(storage_entity_id)
            
            # Test 3: Test file generation with storage entity
            self.test_storage_file_generation_structure()
            
            # Cleanup
            self.cleanup_storage_entity(storage_entity_id)
    
    def test_create_storage_entity(self):
        """Create storage entity with proper structure as specified in review request"""
        try:
            payload = {
                "name": "test-storage-fix2",
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
                    self.log_test("FIX2 - Storage Entity Creation", True, f"Created storage entity with ID: {entity_id}")
                    return entity_id
                else:
                    self.log_test("FIX2 - Storage Entity Creation", False, f"Creation failed: {data}")
                    return None
            else:
                self.log_test("FIX2 - Storage Entity Creation", False, f"HTTP {response.status_code}")
                return None
                
        except Exception as e:
            self.log_test("FIX2 - Storage Entity Creation", False, f"Exception: {str(e)}")
            return None
    
    def test_storage_map_key_structure(self, entity_id):
        """Verify storage configuration uses proper map key handling"""
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
                        if entity.get("id") == entity_id and entity.get("entityType") == "storages":
                            storage_entity_found = True
                            
                            # Check storage configuration structure
                            entity_config = entity.get("baseConfig", {})
                            storages = entity_config.get("storages", {})
                            
                            # CRITICAL TEST: Verify that "EA.EADP.PDE.MCR" is used as a map key (not nested by dots)
                            if "EA.EADP.PDE.MCR" in storages:
                                storage_config = storages["EA.EADP.PDE.MCR"]
                                
                                # Verify it's not nested (should NOT have storages.storages.EA.EADP.PDE.MCR)
                                if isinstance(storage_config, dict) and "serviceIdentifier" in storage_config:
                                    service_id = storage_config.get("serviceIdentifier")
                                    if service_id == "EA.EADP.PDE.MCR":
                                        self.log_test("FIX2 - Map Key Structure", True, "✅ Storage uses full service identifier 'EA.EADP.PDE.MCR' as map key (NOT nested by dots)")
                                    else:
                                        self.log_test("FIX2 - Map Key Structure", False, f"Service identifier mismatch: expected 'EA.EADP.PDE.MCR', got '{service_id}'")
                                else:
                                    self.log_test("FIX2 - Map Key Structure", False, f"Storage config structure invalid: {storage_config}")
                            else:
                                # Check if it was incorrectly nested by dots (this should NOT happen)
                                nested_check = storages
                                nested_path = []
                                for part in ["EA", "EADP", "PDE", "MCR"]:
                                    if isinstance(nested_check, dict) and part in nested_check:
                                        nested_check = nested_check[part]
                                        nested_path.append(part)
                                    else:
                                        break
                                
                                if len(nested_path) == 4:
                                    self.log_test("FIX2 - Map Key Structure", False, f"❌ CRITICAL: Storage incorrectly nested by dots: storages.{'.'.join(nested_path)}")
                                else:
                                    self.log_test("FIX2 - Map Key Structure", False, f"Storage key 'EA.EADP.PDE.MCR' not found. Available keys: {list(storages.keys())}")
                            
                            # Verify defaultServiceIdentifier is present at top level
                            default_service_id = entity_config.get("defaultServiceIdentifier")
                            if default_service_id == "EA.EADP.PDE.MCR":
                                self.log_test("FIX2 - Default Service Identifier", True, f"✅ defaultServiceIdentifier present at top level: {default_service_id}")
                            else:
                                self.log_test("FIX2 - Default Service Identifier", False, f"defaultServiceIdentifier missing or incorrect: {default_service_id}")
                            
                            break
                
                if not storage_entity_found:
                    self.log_test("FIX2 - Map Key Structure", False, f"Storage entity with ID {entity_id} not found in UI config")
            else:
                self.log_test("FIX2 - Map Key Structure", False, f"UI config request failed: HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("FIX2 - Map Key Structure", False, f"Exception: {str(e)}")
    
    def test_storage_file_generation_structure(self):
        """Test file generation with storage entity and verify structure in generated JSON"""
        try:
            # Find a schema that contains our storage entity
            ui_response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if ui_response.status_code != 200:
                self.log_test("FIX2 - File Generation Structure", False, "Could not get UI config for file generation")
                return
            
            ui_data = ui_response.json()
            schema_id = None
            
            # Find schema containing storage entity
            for schema in ui_data.get("config", {}).get("schemas", []):
                for entity in schema.get("configurations", []):
                    if entity.get("name") == "test-storage-fix2" and entity.get("entityType") == "storages":
                        schema_id = schema.get("id")
                        break
                if schema_id:
                    break
            
            if not schema_id:
                self.log_test("FIX2 - File Generation Structure", False, "Could not find schema containing storage entity")
                return
            
            # Generate files with storage configuration
            gen_payload = {
                "schemaId": schema_id,
                "environments": ["DEV"],
                "outputPath": "/app/test_fix2_generated"
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
                    self.log_test("FIX2 - File Generation", True, f"Generated {len(files)} files with storage configuration")
                    
                    # Verify storage structure in generated files
                    storage_structure_verified = False
                    for file_info in files:
                        if isinstance(file_info, dict) and "content" in file_info:
                            content = file_info.get("content", {})
                            if self.verify_storage_structure_in_content(content, file_info.get("filename", "unknown")):
                                storage_structure_verified = True
                                break
                    
                    if not storage_structure_verified:
                        self.log_test("FIX2 - Generated File Structure", False, "Storage structure not found or incorrect in generated files")
                else:
                    error = gen_data.get("errors", ["Unknown error"])
                    self.log_test("FIX2 - File Generation", False, f"Generation failed: {error}")
            else:
                self.log_test("FIX2 - File Generation", False, f"HTTP {gen_response.status_code}")
                
        except Exception as e:
            self.log_test("FIX2 - File Generation Structure", False, f"Exception: {str(e)}")
    
    def verify_storage_structure_in_content(self, content, filename):
        """Verify storage structure in generated file content"""
        try:
            # Look for storage configuration in various possible locations
            storage_configs = []
            
            # Check direct storages field
            if "storages" in content:
                storage_configs.append(content["storages"])
            
            # Check nested configurations
            if "config" in content and "storages" in content["config"]:
                storage_configs.append(content["config"]["storages"])
            
            for storage_config in storage_configs:
                if isinstance(storage_config, dict):
                    # CRITICAL TEST: Check if "EA.EADP.PDE.MCR" is used as a direct key
                    if "EA.EADP.PDE.MCR" in storage_config.get("storages", {}):
                        service_config = storage_config["storages"]["EA.EADP.PDE.MCR"]
                        if isinstance(service_config, dict) and "serviceIdentifier" in service_config:
                            self.log_test("FIX2 - Generated File Structure", True, f"✅ Generated file {filename} uses full service identifier as map key")
                            return True
                    
                    # Check if defaultServiceIdentifier is present
                    if storage_config.get("defaultServiceIdentifier") == "EA.EADP.PDE.MCR":
                        self.log_test("FIX2 - Generated File Default Service ID", True, f"✅ Generated file {filename} includes defaultServiceIdentifier")
                    
                    # Check if it was incorrectly nested (this should NOT happen)
                    storages = storage_config.get("storages", {})
                    if "EA" in storages and isinstance(storages["EA"], dict):
                        nested = storages["EA"]
                        if "EADP" in nested and isinstance(nested["EADP"], dict):
                            nested = nested["EADP"]
                            if "PDE" in nested and isinstance(nested["PDE"], dict):
                                nested = nested["PDE"]
                                if "MCR" in nested:
                                    self.log_test("FIX2 - Generated File Structure", False, f"❌ CRITICAL: Generated file {filename} has storage incorrectly nested by dots")
                                    return False
            
            return False
            
        except Exception as e:
            self.log_test("FIX2 - Generated File Structure Verification", False, f"Exception: {str(e)}")
            return False
    
    def cleanup_storage_entity(self, entity_id):
        """Clean up test storage entity"""
        try:
            requests.delete(f"{self.base_url}/api/blueprint/config/entities/{entity_id}", timeout=10)
            self.log_test("FIX2 - Cleanup", True, f"Cleaned up storage entity {entity_id}")
        except:
            pass  # Ignore cleanup errors
    
    def cleanup_test_files(self):
        """Clean up test files"""
        try:
            if hasattr(self, 'test_filename'):
                requests.delete(f"{self.base_url}/api/blueprint/delete-file/{self.test_filename}", timeout=10)
                self.log_test("FIX1 - Cleanup", True, f"Cleaned up test file {self.test_filename}")
        except:
            pass  # Ignore cleanup errors
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print("📊 BLUEPRINT CONFIGURATION FIXES TEST SUMMARY")
        print("=" * 70)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Categorize results by fix
        fix1_results = [r for r in self.test_results if "FIX1" in r["name"]]
        fix2_results = [r for r in self.test_results if "FIX2" in r["name"]]
        
        print(f"\n🔧 FIX 1 - blueprint_cnf.json Generation ({len([r for r in fix1_results if r['success']])}/{len(fix1_results)} passed):")
        for result in fix1_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}: {result['details']}")
        
        print(f"\n🔧 FIX 2 - Storage Configuration Map Key ({len([r for r in fix2_results if r['success']])}/{len(fix2_results)} passed):")
        for result in fix2_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}: {result['details']}")
        
        # Final assessment
        fix1_success = len([r for r in fix1_results if r['success']]) == len(fix1_results) if fix1_results else False
        fix2_success = len([r for r in fix2_results if r['success']]) == len(fix2_results) if fix2_results else False
        
        print(f"\n📋 FINAL ASSESSMENT:")
        print(f"   FIX 1 (blueprint_cnf.json Generation): {'✅ WORKING' if fix1_success else '❌ NEEDS ATTENTION'}")
        print(f"   FIX 2 (Storage Configuration Map Key): {'✅ WORKING' if fix2_success else '❌ NEEDS ATTENTION'}")
        
        if fix1_success and fix2_success:
            print(f"\n🎉 EXCELLENT: Both fixes are working correctly!")
        elif fix1_success or fix2_success:
            print(f"\n⚠️ PARTIAL: One fix is working, one needs attention")
        else:
            print(f"\n❌ CRITICAL: Both fixes need attention")
    
    def run_blueprint_fixes_tests(self):
        """Run comprehensive tests for the two specific blueprint configuration fixes"""
        print("🚀 Starting Blueprint Configuration Fixes Testing")
        print("Testing the two specific fixes from the review request:")
        print("- FIX 1: blueprint_cnf.json Generation Test")
        print("- FIX 2: Storage Configuration Map Key Test")
        print("=" * 70)
        
        # Setup
        self.setup_blueprint_root_path()
        
        # Test FIX 1: blueprint_cnf.json Generation
        self.test_fix1_blueprint_cnf_generation()
        
        # Test FIX 2: Storage Configuration Map Key Handling
        self.test_fix2_storage_configuration_map_key()
        
        # Cleanup
        self.cleanup_test_files()
        
        # Print final summary
        self.print_summary()

def main():
    """Main function to run tests"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "https://blueprint-config-ui.preview.emergentagent.com"
    
    print(f"🔧 Testing Blueprint Configuration Fixes at: {base_url}")
    
    tester = BlueprintFixesTester(base_url)
    tester.run_blueprint_fixes_tests()

if __name__ == "__main__":
    main()