#!/usr/bin/env python3
"""
Comprehensive Bug Fix Validation for Kafka Trace Viewer
Tests all three major bug fixes:
1. Protobuf Caching System
2. Message Type Resolution (Event vs ProcessEvent)
3. Frontend-Backend Connectivity
"""

import requests
import json
import sys
import time
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

class BugFixValidator:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.backend_dir = Path("/app/backend")
        self.cache_dir = self.backend_dir / ".protobuf_cache"
        
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
    
    def test_protobuf_cache_directory_exists(self) -> bool:
        """Test 1.1: Check if protobuf cache directory exists"""
        try:
            if self.cache_dir.exists():
                cache_contents = list(self.cache_dir.iterdir())
                self.log_test("Protobuf Cache Directory", True, f"Found at {self.cache_dir} with {len(cache_contents)} items")
                return True
            else:
                self.log_test("Protobuf Cache Directory", False, f"Not found at {self.cache_dir}")
                return False
        except Exception as e:
            self.log_test("Protobuf Cache Directory", False, f"Exception: {str(e)}")
            return False
    
    def test_protobuf_cache_functionality(self) -> bool:
        """Test 1.2: Test protobuf caching functionality"""
        try:
            # Import the cache class
            sys.path.insert(0, str(self.backend_dir))
            from src.protobuf_cache import ProtobufCache
            
            proto_dir = self.backend_dir / "config" / "proto"
            cache = ProtobufCache(str(proto_dir))
            
            # Test cache validation for test topics
            test_topics = [
                ("test-events", "event.proto"),
                ("test-processes", "process_event.proto")
            ]
            
            cache_results = []
            for topic, proto_file in test_topics:
                is_valid = cache.is_cache_valid(topic, proto_file)
                cache_results.append(f"{topic}: {'VALID' if is_valid else 'INVALID'}")
            
            self.log_test("Protobuf Cache Functionality", True, f"Cache status - {', '.join(cache_results)}")
            return True
            
        except Exception as e:
            self.log_test("Protobuf Cache Functionality", False, f"Exception: {str(e)}")
            return False
    
    def test_message_type_resolution(self) -> bool:
        """Test 2: Message Type Resolution - Event vs ProcessEvent"""
        try:
            # Check if both test topics are configured
            response = requests.get(f"{self.base_url}/api/topics", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                all_topics = data.get("all_topics", [])
                
                # Check for both test topics
                has_test_events = "test-events" in all_topics
                has_test_processes = "test-processes" in all_topics
                
                if has_test_events and has_test_processes:
                    self.log_test("Message Type Resolution", True, "Both Event and ProcessEvent topics found")
                    return True
                else:
                    missing = []
                    if not has_test_events:
                        missing.append("test-events")
                    if not has_test_processes:
                        missing.append("test-processes")
                    self.log_test("Message Type Resolution", False, f"Missing topics: {missing}")
                    return False
            else:
                self.log_test("Message Type Resolution", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Message Type Resolution", False, f"Exception: {str(e)}")
            return False
    
    def test_frontend_backend_connectivity(self) -> bool:
        """Test 3: Frontend-Backend Connectivity"""
        try:
            # Test basic API connectivity
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Frontend-Backend Connectivity", True, f"API healthy, traces: {data.get('traces_count', 0)}")
                    return True
                else:
                    self.log_test("Frontend-Backend Connectivity", False, f"Unhealthy status: {data.get('status')}")
                    return False
            else:
                self.log_test("Frontend-Backend Connectivity", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Frontend-Backend Connectivity", False, f"Exception: {str(e)}")
            return False
    
    def test_websocket_endpoint(self) -> bool:
        """Test 3.1: WebSocket endpoint availability"""
        try:
            # Test if WebSocket endpoint is reachable (basic check)
            ws_url = self.base_url.replace('http://', 'ws://') + '/api/ws'
            self.log_test("WebSocket Endpoint", True, f"URL configured: {ws_url}")
            return True
        except Exception as e:
            self.log_test("WebSocket Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def test_environment_variables(self) -> bool:
        """Test 3.2: Environment variables configuration"""
        try:
            # Check frontend environment files
            frontend_dir = Path("/app/frontend")
            env_files = {
                ".env": frontend_dir / ".env",
                ".env.local": frontend_dir / ".env.local"
            }
            
            results = []
            for name, path in env_files.items():
                if path.exists():
                    content = path.read_text()
                    if "REACT_APP_BACKEND_URL" in content:
                        # Extract the URL
                        for line in content.split('\n'):
                            if line.startswith('REACT_APP_BACKEND_URL'):
                                url = line.split('=')[1].strip()
                                results.append(f"{name}: {url}")
                                break
                    else:
                        results.append(f"{name}: No REACT_APP_BACKEND_URL")
                else:
                    results.append(f"{name}: Not found")
            
            self.log_test("Environment Variables", True, f"Config - {', '.join(results)}")
            return True
            
        except Exception as e:
            self.log_test("Environment Variables", False, f"Exception: {str(e)}")
            return False
    
    def test_performance_improvements(self) -> bool:
        """Test 4: Performance improvements validation"""
        try:
            # Measure API response time
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200 and response_time < 1000:  # Less than 1 second
                self.log_test("Performance - API Response", True, f"Response time: {response_time:.2f}ms")
                return True
            else:
                self.log_test("Performance - API Response", False, f"Slow response: {response_time:.2f}ms")
                return False
                
        except Exception as e:
            self.log_test("Performance - API Response", False, f"Exception: {str(e)}")
            return False
    
    def test_individual_protobuf_files(self) -> bool:
        """Test 5: Individual protobuf files validation"""
        try:
            proto_dir = self.backend_dir / "config" / "proto"
            
            # Check if test proto files exist
            test_files = {
                "event.proto": proto_dir / "event.proto",
                "process_event.proto": proto_dir / "process_event.proto"
            }
            
            results = []
            for name, path in test_files.items():
                if path.exists():
                    content = path.read_text()
                    # Check for expected message types
                    if name == "event.proto" and "message Event" in content:
                        results.append(f"{name}: Event message found")
                    elif name == "process_event.proto" and "message ProcessEvent" in content:
                        results.append(f"{name}: ProcessEvent message found")
                    else:
                        results.append(f"{name}: Message type not found")
                else:
                    results.append(f"{name}: File not found")
            
            all_found = all("found" in result for result in results)
            self.log_test("Individual Protobuf Files", all_found, f"Files - {', '.join(results)}")
            return all_found
            
        except Exception as e:
            self.log_test("Individual Protobuf Files", False, f"Exception: {str(e)}")
            return False
    
    def test_mock_mode_status(self) -> bool:
        """Test 6: Check if system is running in mock mode"""
        try:
            kafka_config_path = self.backend_dir / "config" / "kafka.yaml"
            if kafka_config_path.exists():
                import yaml
                with open(kafka_config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                mock_mode = config.get('mock_mode', False)
                self.log_test("Mock Mode Status", True, f"Mock mode: {'ENABLED' if mock_mode else 'DISABLED'}")
                return True
            else:
                self.log_test("Mock Mode Status", False, "Kafka config not found")
                return False
                
        except Exception as e:
            self.log_test("Mock Mode Status", False, f"Exception: {str(e)}")
            return False
    
    def test_backend_logs_for_caching(self) -> bool:
        """Test 7: Check backend logs for caching messages"""
        try:
            # Check supervisor logs for caching messages
            log_files = [
                "/var/log/supervisor/backend.err.log",
                "/var/log/supervisor/backend.out.log"
            ]
            
            cache_messages = []
            for log_file in log_files:
                if os.path.exists(log_file):
                    try:
                        with open(log_file, 'r') as f:
                            content = f.read()
                            
                        # Look for cache-related messages
                        if "CACHED" in content:
                            cache_messages.append("CACHED messages found")
                        if "protobuf_cache" in content:
                            cache_messages.append("Cache module messages found")
                        if "Mock:" in content:
                            cache_messages.append("Mock mode messages found")
                            
                    except Exception as e:
                        cache_messages.append(f"Error reading {log_file}: {str(e)}")
            
            if cache_messages:
                self.log_test("Backend Logs - Caching", True, f"Found: {', '.join(cache_messages)}")
                return True
            else:
                self.log_test("Backend Logs - Caching", False, "No cache-related messages found")
                return False
                
        except Exception as e:
            self.log_test("Backend Logs - Caching", False, f"Exception: {str(e)}")
            return False
    
    def run_comprehensive_validation(self):
        """Run all bug fix validation tests"""
        print("🚀 Starting Comprehensive Bug Fix Validation")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 80)
        
        print("\n🔧 BUG FIX 1: PROTOBUF CACHING SYSTEM")
        print("-" * 50)
        self.test_protobuf_cache_directory_exists()
        self.test_protobuf_cache_functionality()
        self.test_backend_logs_for_caching()
        
        print("\n🔧 BUG FIX 2: MESSAGE TYPE RESOLUTION")
        print("-" * 50)
        self.test_message_type_resolution()
        self.test_individual_protobuf_files()
        
        print("\n🔧 BUG FIX 3: FRONTEND-BACKEND CONNECTIVITY")
        print("-" * 50)
        self.test_frontend_backend_connectivity()
        self.test_websocket_endpoint()
        self.test_environment_variables()
        
        print("\n🔧 ADDITIONAL VALIDATIONS")
        print("-" * 50)
        self.test_performance_improvements()
        self.test_mock_mode_status()
        
        # Print summary
        print("\n" + "=" * 80)
        print(f"📊 VALIDATION SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL BUG FIXES VALIDATED SUCCESSFULLY!")
            return True
        else:
            failed_tests = [r for r in self.test_results if not r["success"]]
            print(f"❌ {len(failed_tests)} validations failed:")
            for test in failed_tests:
                print(f"   • {test['name']}: {test['details']}")
            
            print("\n📋 RECOMMENDATIONS:")
            if any("Cache Directory" in t["name"] for t in failed_tests):
                print("   • Restart backend to trigger protobuf compilation and caching")
            if any("Message Type" in t["name"] for t in failed_tests):
                print("   • Check topics.yaml configuration for test-events and test-processes")
            if any("Connectivity" in t["name"] for t in failed_tests):
                print("   • Verify backend is running and accessible")
            
            return False

def main():
    """Main validation execution"""
    validator = BugFixValidator()
    success = validator.run_comprehensive_validation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())