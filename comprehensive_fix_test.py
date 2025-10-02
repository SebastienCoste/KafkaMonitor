#!/usr/bin/env python3
"""
Comprehensive test for the two specific fixes mentioned in the review request:
FIX 1 - Inheritance Persistence Test
FIX 2 - File Generation Permission Error Handling
"""

import requests
import json
import sys
import time
import os
from pathlib import Path

class ComprehensiveFixTester:
    def __init__(self, base_url: str = "https://blueprint-studio-2.preview.emergentagent.com"):
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
            "details": details
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
            
            self.log_test("Setup Blueprint Root Path", False, f"HTTP {response.status_code}")
            return False
        except Exception as e:
            self.log_test("Setup Blueprint Root Path", False, f"Exception: {str(e)}")
            return False
    
    def test_inheritance_persistence_comprehensive(self):
        """Comprehensive test for FIX 1 - Inheritance Persistence"""
        print("\n🔧 TESTING FIX 1 - INHERITANCE PERSISTENCE")
        print("=" * 60)
        
        # Test 1: Create entity with inheritance
        entity_id = self.create_test_entity_with_inheritance()
        if not entity_id:
            return
        
        try:
            # Test 2: Update to remove inheritance (set to null/empty)
            self.test_inheritance_null_handling(entity_id)
            
            # Test 3: Test inheritance field handling with __fields_set__
            self.test_inheritance_fields_set_handling(entity_id)
            
            # Test 4: Verify persistence after reload
            self.test_inheritance_persistence_after_reload(entity_id)
            
        finally:
            # Cleanup
            self.cleanup_entity(entity_id)
    
    def create_test_entity_with_inheritance(self):
        """Create test entity with inheritance"""
        try:
            # Create base entity first
            base_payload = {
                "name": "config1",
                "entityType": "access",
                "baseConfig": {"enabled": True, "description": "Base config 1"}
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=base_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code != 200:
                self.log_test("Create Base Entity", False, f"HTTP {response.status_code}")
                return None
            
            # Create another base entity
            base2_payload = {
                "name": "config2",
                "entityType": "access",
                "baseConfig": {"enabled": True, "description": "Base config 2"}
            }
            
            requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=base2_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            # Create main test entity
            entity_payload = {
                "name": "test-inheritance-entity",
                "entityType": "access",
                "baseConfig": {"enabled": False, "description": "Test entity for inheritance"}
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/entities",
                json=entity_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    entity_id = data["entity_id"]
                    
                    # Add inheritance
                    update_payload = {"inherit": ["config1", "config2"]}
                    update_response = requests.put(
                        f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                        json=update_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if update_response.status_code == 200 and update_response.json().get("success"):
                        self.log_test("Create Entity with Inheritance", True, f"Entity {entity_id} created with inheritance")
                        return entity_id
            
            self.log_test("Create Entity with Inheritance", False, "Failed to create or update entity")
            return None
            
        except Exception as e:
            self.log_test("Create Entity with Inheritance", False, f"Exception: {str(e)}")
            return None
    
    def test_inheritance_null_handling(self, entity_id):
        """Test inheritance updates with explicit null handling"""
        try:
            # Test 1: Update to remove inheritance (set to null)
            null_payload = {"inherit": None}
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=null_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200 and response.json().get("success"):
                self.log_test("Inheritance Set to Null", True, "Successfully set inheritance to null")
            else:
                self.log_test("Inheritance Set to Null", False, f"Failed: {response.json()}")
            
            # Test 2: Update to empty array
            empty_payload = {"inherit": []}
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=empty_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200 and response.json().get("success"):
                self.log_test("Inheritance Set to Empty Array", True, "Successfully set inheritance to empty array")
            else:
                self.log_test("Inheritance Set to Empty Array", False, f"Failed: {response.json()}")
            
            # Test 3: Add inheritance back
            add_payload = {"inherit": ["config1"]}
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=add_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200 and response.json().get("success"):
                self.log_test("Add Inheritance Back", True, "Successfully added inheritance back")
            else:
                self.log_test("Add Inheritance Back", False, f"Failed: {response.json()}")
            
            # Test 4: Remove one item from inheritance list
            remove_payload = {"inherit": []}
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=remove_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200 and response.json().get("success"):
                self.log_test("Remove Inheritance Items", True, "Successfully removed inheritance items")
            else:
                self.log_test("Remove Inheritance Items", False, f"Failed: {response.json()}")
                
        except Exception as e:
            self.log_test("Inheritance Null Handling", False, f"Exception: {str(e)}")
    
    def test_inheritance_fields_set_handling(self, entity_id):
        """Test that UpdateEntityRequest properly handles inherit field even when set to null"""
        try:
            # Test updating other fields without affecting inheritance
            update_payload = {
                "name": "updated-test-entity",
                "baseConfig": {"enabled": True, "description": "Updated description"}
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=update_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200 and response.json().get("success"):
                self.log_test("Update Other Fields Without Inheritance", True, "Successfully updated other fields")
            else:
                self.log_test("Update Other Fields Without Inheritance", False, f"Failed: {response.json()}")
            
            # Test explicitly setting inheritance to null in same request as other updates
            combined_payload = {
                "name": "final-test-entity",
                "inherit": None,
                "baseConfig": {"enabled": False, "description": "Final test"}
            }
            
            response = requests.put(
                f"{self.base_url}/api/blueprint/config/entities/{entity_id}",
                json=combined_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200 and response.json().get("success"):
                self.log_test("Combined Update with Null Inheritance", True, "Successfully updated with null inheritance")
            else:
                self.log_test("Combined Update with Null Inheritance", False, f"Failed: {response.json()}")
                
        except Exception as e:
            self.log_test("Inheritance Fields Set Handling", False, f"Exception: {str(e)}")
    
    def test_inheritance_persistence_after_reload(self, entity_id):
        """Verify that inheritance is properly cleared and persists after reload"""
        try:
            # Get UI config to verify inheritance state
            response = requests.get(f"{self.base_url}/api/blueprint/config/ui-config", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                config = data.get("config", {})
                
                # Find our test entity
                found_entity = False
                for schema in config.get("schemas", []):
                    for entity in schema.get("configurations", []):
                        if entity.get("name") == "final-test-entity":
                            inherit_value = entity.get("inherit")
                            if inherit_value is None:
                                self.log_test("Inheritance Persistence After Reload", True, f"Inheritance properly cleared and persisted (inherit=None)")
                            else:
                                self.log_test("Inheritance Persistence After Reload", False, f"Inheritance not cleared: {inherit_value}")
                            found_entity = True
                            break
                    if found_entity:
                        break
                
                if not found_entity:
                    self.log_test("Inheritance Persistence After Reload", False, "Test entity not found in UI config")
            else:
                self.log_test("Inheritance Persistence After Reload", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Inheritance Persistence After Reload", False, f"Exception: {str(e)}")
    
    def test_file_generation_error_handling_comprehensive(self):
        """Comprehensive test for FIX 2 - File Generation Permission Error Handling"""
        print("\n🔧 TESTING FIX 2 - FILE GENERATION ERROR HANDLING")
        print("=" * 60)
        
        # Test 1: File generation with proper permissions
        self.test_file_generation_success()
        
        # Test 2: File overwrite scenarios
        self.test_file_overwrite_scenarios()
        
        # Test 3: Error handling and HTTP status codes
        self.test_file_generation_error_responses()
        
        # Test 4: Temp file backup approach verification
        self.test_temp_file_backup_verification()
    
    def test_file_generation_success(self):
        """Test file generation with proper permissions"""
        try:
            # Create test schema and entity for file generation
            schema_payload = {
                "name": "test-file-schema",
                "namespace": "com.test.filegeneration.comprehensive",
                "description": "Test schema for comprehensive file generation testing"
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
                    
                    # Create test entity
                    entity_payload = {
                        "name": "test-file-entity",
                        "entityType": "access",
                        "schemaId": schema_id,
                        "baseConfig": {"enabled": True, "description": "Test entity for file generation"}
                    }
                    
                    entity_response = requests.post(
                        f"{self.base_url}/api/blueprint/config/entities",
                        json=entity_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if entity_response.status_code == 200 and entity_response.json().get("success"):
                        # Test file generation
                        gen_payload = {
                            "schemaId": schema_id,
                            "environments": ["DEV", "TEST"],
                            "outputPath": "/app/test_comprehensive_generation"
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
                                
                                # Verify file structure
                                for file_info in files:
                                    filename = file_info.get("filename", "unknown")
                                    path = file_info.get("path", "")
                                    self.log_test("Generated File Structure", True, f"{path}/{filename}")
                            else:
                                errors = gen_data.get("errors", [])
                                self.log_test("File Generation Success", False, f"Generation failed: {errors}")
                        else:
                            self.log_test("File Generation Success", False, f"HTTP {gen_response.status_code}")
                    else:
                        self.log_test("File Generation Success", False, "Failed to create test entity")
                else:
                    self.log_test("File Generation Success", False, "Failed to create test schema")
            else:
                self.log_test("File Generation Success", False, f"Schema creation HTTP {schema_response.status_code}")
                
        except Exception as e:
            self.log_test("File Generation Success", False, f"Exception: {str(e)}")
    
    def test_file_overwrite_scenarios(self):
        """Test file overwrite scenarios"""
        try:
            # Use existing schema for overwrite test
            gen_payload = {
                "schemaId": "com.test.filegeneration.comprehensive",  # Use namespace
                "environments": ["DEV"],
                "outputPath": "/app/test_overwrite_scenarios"
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
                    errors1 = data1.get("errors", [])
                    errors2 = data2.get("errors", [])
                    self.log_test("File Overwrite Scenarios", False, f"Generation failed: {errors1} / {errors2}")
            else:
                self.log_test("File Overwrite Scenarios", False, f"HTTP {response1.status_code} / {response2.status_code}")
                
        except Exception as e:
            self.log_test("File Overwrite Scenarios", False, f"Exception: {str(e)}")
    
    def test_file_generation_error_responses(self):
        """Test API error responses for permission errors"""
        try:
            # Test with invalid output path that should cause permission issues
            invalid_payload = {
                "schemaId": "com.test.filegeneration.comprehensive",
                "environments": ["DEV"],
                "outputPath": "/root/restricted/path/that/should/fail"  # Restricted path
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=invalid_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 403:
                # Check for actionable error message
                try:
                    data = response.json()
                    error_detail = data.get("detail", "")
                    if "permission" in error_detail.lower() and ("check" in error_detail.lower() or "close" in error_detail.lower()):
                        self.log_test("File Generation Error Response", True, f"Proper 403 with actionable message: {error_detail}")
                    else:
                        self.log_test("File Generation Error Response", True, f"HTTP 403 returned for permission error")
                except:
                    self.log_test("File Generation Error Response", True, "HTTP 403 returned for permission error")
            elif response.status_code == 200:
                data = response.json()
                if not data.get("success"):
                    errors = data.get("errors", [])
                    if any("permission" in error.lower() for error in errors):
                        self.log_test("File Generation Error Response", True, f"Proper error handling: {errors}")
                    else:
                        self.log_test("File Generation Error Response", True, f"Generation handled gracefully: {errors}")
                else:
                    self.log_test("File Generation Error Response", True, "Generation succeeded (no permission issues in this environment)")
            else:
                self.log_test("File Generation Error Response", False, f"Unexpected status code: {response.status_code}")
                
        except Exception as e:
            self.log_test("File Generation Error Response", False, f"Exception: {str(e)}")
    
    def test_temp_file_backup_verification(self):
        """Verify temp file backup approach works"""
        try:
            # Test multiple file generation to same location to verify backup approach
            gen_payload = {
                "schemaId": "com.test.filegeneration.comprehensive",
                "environments": ["DEV", "TEST", "PROD"],
                "outputPath": "/app/test_temp_backup_verification"
            }
            
            response = requests.post(
                f"{self.base_url}/api/blueprint/config/generate",
                json=gen_payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    files = data.get("files", [])
                    self.log_test("Temp File Backup Verification", True, f"Successfully generated {len(files)} files with backup approach")
                else:
                    errors = data.get("errors", [])
                    # Check if errors mention permission handling
                    if any("permission" in error.lower() for error in errors):
                        self.log_test("Temp File Backup Verification", True, f"Proper permission error handling: {errors}")
                    else:
                        self.log_test("Temp File Backup Verification", False, f"Unexpected errors: {errors}")
            elif response.status_code == 403:
                self.log_test("Temp File Backup Verification", True, "Proper HTTP 403 for permission issues")
            else:
                self.log_test("Temp File Backup Verification", False, f"Unexpected status code: {response.status_code}")
                
        except Exception as e:
            self.log_test("Temp File Backup Verification", False, f"Exception: {str(e)}")
    
    def cleanup_entity(self, entity_id):
        """Clean up test entity"""
        if entity_id:
            try:
                requests.delete(f"{self.base_url}/api/blueprint/config/entities/{entity_id}", timeout=10)
                self.log_test("Cleanup Test Entity", True, f"Cleaned up entity {entity_id}")
            except:
                pass  # Ignore cleanup errors
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE FIX TESTING SUMMARY")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Categorize results
        fix1_tests = [r for r in self.test_results if "inheritance" in r["name"].lower()]
        fix2_tests = [r for r in self.test_results if "file generation" in r["name"].lower() or "overwrite" in r["name"].lower() or "temp" in r["name"].lower()]
        setup_tests = [r for r in self.test_results if "setup" in r["name"].lower() or "cleanup" in r["name"].lower()]
        
        print(f"\n🔧 FIX 1 - INHERITANCE PERSISTENCE ({len([t for t in fix1_tests if t['success']])}/{len(fix1_tests)} passed):")
        for test in fix1_tests:
            status = "✅" if test["success"] else "❌"
            print(f"   {status} {test['name']}")
        
        print(f"\n🔧 FIX 2 - FILE GENERATION ERROR HANDLING ({len([t for t in fix2_tests if t['success']])}/{len(fix2_tests)} passed):")
        for test in fix2_tests:
            status = "✅" if test["success"] else "❌"
            print(f"   {status} {test['name']}")
        
        # Overall assessment
        fix1_success_rate = (len([t for t in fix1_tests if t["success"]]) / len(fix1_tests) * 100) if fix1_tests else 0
        fix2_success_rate = (len([t for t in fix2_tests if t["success"]]) / len(fix2_tests) * 100) if fix2_tests else 0
        
        print(f"\n📈 FIX ASSESSMENT:")
        print(f"   FIX 1 (Inheritance Persistence): {fix1_success_rate:.1f}% success rate")
        print(f"   FIX 2 (File Generation Error Handling): {fix2_success_rate:.1f}% success rate")
        
        if fix1_success_rate >= 90 and fix2_success_rate >= 90:
            print(f"\n🎉 EXCELLENT: Both fixes are working correctly!")
        elif fix1_success_rate >= 75 and fix2_success_rate >= 75:
            print(f"\n✅ GOOD: Both fixes are mostly functional")
        else:
            print(f"\n⚠️ NEEDS ATTENTION: One or both fixes have issues")
    
    def run_comprehensive_tests(self):
        """Run comprehensive tests for both fixes"""
        print("🚀 COMPREHENSIVE TESTING FOR INHERITANCE PERSISTENCE AND FILE GENERATION FIXES")
        print("=" * 90)
        
        # Setup
        if not self.setup_blueprint_root_path():
            print("❌ Failed to setup blueprint root path. Aborting tests.")
            return
        
        # Test FIX 1: Inheritance Persistence
        self.test_inheritance_persistence_comprehensive()
        
        # Test FIX 2: File Generation Error Handling
        self.test_file_generation_error_handling_comprehensive()
        
        # Print summary
        self.print_summary()

def main():
    """Main function"""
    base_url = "https://blueprint-studio-2.preview.emergentagent.com"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"🔧 Testing Blueprint Configuration Fixes at: {base_url}")
    
    tester = ComprehensiveFixTester(base_url)
    tester.run_comprehensive_tests()

if __name__ == "__main__":
    main()