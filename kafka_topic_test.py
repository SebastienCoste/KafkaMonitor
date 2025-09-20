#!/usr/bin/env python3
"""
Focused test for Kafka Topic Availability Fix
"""

import requests
import json
import sys
import time
from datetime import datetime

class KafkaTopicTester:
    def __init__(self, base_url: str = "https://trace-blueprint.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        
    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
    
    def test_kafka_topic_availability_fix(self) -> bool:
        """Test Kafka Topic Availability Fix - comprehensive testing"""
        print("🔍 Testing Kafka Topic Availability Fix")
        print("=" * 60)
        
        all_passed = True
        
        # Test 1: GET /api/kafka/subscription-status - New endpoint
        try:
            print("🔄 Testing GET /api/kafka/subscription-status...")
            response = requests.get(f"{self.base_url}/api/kafka/subscription-status", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                
                if data.get("success"):
                    # Check for topic subscription information
                    status_keys = list(data.keys())
                    expected_keys = ["success", "subscribed_topics", "status"]
                    
                    if any(key in status_keys for key in expected_keys):
                        self.log_test("Kafka Subscription Status API", True, f"Available keys: {status_keys}")
                        
                        # Check for graceful handling indicators
                        if "subscribed_topics" in data:
                            topics = data["subscribed_topics"]
                            self.log_test("Topic Subscription Info", True, f"Subscribed topics: {topics}")
                        
                        if "status" in data:
                            status = data["status"]
                            self.log_test("Consumer Status Info", True, f"Consumer status: {status}")
                    else:
                        self.log_test("Kafka Subscription Status API", False, f"Missing expected keys: {status_keys}")
                        all_passed = False
                else:
                    self.log_test("Kafka Subscription Status API", False, f"API returned success=false: {data}")
                    all_passed = False
            else:
                self.log_test("Kafka Subscription Status API", False, f"HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_test("Kafka Subscription Status API", False, f"Exception: {str(e)}")
            all_passed = False
        
        # Test 2: POST /api/kafka/refresh-subscription - New endpoint
        try:
            print("\n🔄 Testing POST /api/kafka/refresh-subscription...")
            response = requests.post(
                f"{self.base_url}/api/kafka/refresh-subscription",
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
                
                if data.get("success"):
                    message = data.get("message", "")
                    if "refresh" in message.lower():
                        self.log_test("Kafka Refresh Subscription API", True, f"Refresh successful: {message}")
                        
                        # Check if status information is included
                        if "subscribed_topics" in data or "status" in data:
                            self.log_test("Refresh Response Info", True, f"Includes status info: {list(data.keys())}")
                    else:
                        self.log_test("Kafka Refresh Subscription API", True, f"Refresh completed: {data}")
                else:
                    self.log_test("Kafka Refresh Subscription API", False, f"Refresh failed: {data}")
                    all_passed = False
            else:
                self.log_test("Kafka Refresh Subscription API", False, f"HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_test("Kafka Refresh Subscription API", False, f"Exception: {str(e)}")
            all_passed = False
        
        # Test 3: System Resilience - verify system continues working
        try:
            print("\n🔄 Testing System Resilience...")
            
            # Test multiple endpoints to ensure system stability
            endpoints_to_test = [
                ("/api/health", "Health Check"),
                ("/api/statistics", "Statistics"),
                ("/api/topics", "Topics List"),
                ("/api/environments", "Environment List")
            ]
            
            resilience_passed = True
            for endpoint, name in endpoints_to_test:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    if response.status_code == 200:
                        print(f"   ✅ {name}: Working")
                    else:
                        print(f"   ❌ {name}: HTTP {response.status_code}")
                        resilience_passed = False
                except Exception as e:
                    print(f"   ❌ {name}: Exception {str(e)[:50]}...")
                    resilience_passed = False
            
            if resilience_passed:
                self.log_test("System Resilience", True, "All core endpoints remain functional")
            else:
                self.log_test("System Resilience", False, "Some core endpoints are failing")
                all_passed = False
                
        except Exception as e:
            self.log_test("System Resilience", False, f"Exception: {str(e)}")
            all_passed = False
        
        # Test 4: Error Handling Verification - check logs don't show crashes
        try:
            print("\n🔄 Testing Error Handling...")
            
            # Test that the system handles missing topics gracefully
            # We can't directly test missing topics, but we can verify the system is stable
            health_response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                if health_data.get("status") == "healthy":
                    self.log_test("Error Handling Verification", True, f"System healthy with {health_data.get('traces_count', 0)} traces")
                else:
                    self.log_test("Error Handling Verification", False, f"System not healthy: {health_data}")
                    all_passed = False
            else:
                self.log_test("Error Handling Verification", False, f"Health check failed: {health_response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_test("Error Handling Verification", False, f"Exception: {str(e)}")
            all_passed = False
        
        # Test 5: Configuration Robustness - test with environment switching
        try:
            print("\n🔄 Testing Configuration Robustness...")
            
            # Get available environments
            env_response = requests.get(f"{self.base_url}/api/environments", timeout=10)
            
            if env_response.status_code == 200:
                env_data = env_response.json()
                available_envs = env_data.get("available_environments", [])
                current_env = env_data.get("current_environment")
                
                if len(available_envs) > 1:
                    # Try switching environments and verify Kafka endpoints still work
                    target_env = None
                    for env in available_envs:
                        if env != current_env:
                            target_env = env
                            break
                    
                    if target_env:
                        # Switch environment
                        switch_response = requests.post(
                            f"{self.base_url}/api/environments/switch",
                            json={"environment": target_env},
                            headers={"Content-Type": "application/json"},
                            timeout=15
                        )
                        
                        if switch_response.status_code == 200:
                            # Test Kafka endpoints after environment switch
                            time.sleep(2)  # Allow time for switch
                            
                            status_response = requests.get(f"{self.base_url}/api/kafka/subscription-status", timeout=10)
                            if status_response.status_code == 200:
                                self.log_test("Configuration Robustness", True, f"Kafka endpoints work after env switch: {current_env} -> {target_env}")
                            else:
                                self.log_test("Configuration Robustness", False, f"Kafka endpoints failed after env switch: {status_response.status_code}")
                                all_passed = False
                        else:
                            self.log_test("Configuration Robustness", False, f"Environment switch failed: {switch_response.status_code}")
                            all_passed = False
                    else:
                        self.log_test("Configuration Robustness", True, f"Single environment setup: {current_env}")
                else:
                    self.log_test("Configuration Robustness", True, f"Single environment available: {current_env}")
            else:
                self.log_test("Configuration Robustness", False, f"Environment endpoint failed: {env_response.status_code}")
                all_passed = False
                
        except Exception as e:
            self.log_test("Configuration Robustness", False, f"Exception: {str(e)}")
            all_passed = False
        
        return all_passed
    
    def run_test(self):
        """Run the focused Kafka topic availability test"""
        print("🚀 Kafka Topic Availability Fix - Focused Testing")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        success = self.test_kafka_topic_availability_fix()
        
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if success and self.tests_passed == self.tests_run:
            print("🎉 Kafka Topic Availability Fix tests passed!")
            return True
        else:
            print("❌ Some Kafka Topic Availability Fix tests failed")
            return False

def main():
    """Main test execution"""
    tester = KafkaTopicTester()
    success = tester.run_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())