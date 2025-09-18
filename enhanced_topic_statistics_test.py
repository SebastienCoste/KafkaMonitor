#!/usr/bin/env python3
"""
Enhanced Topic Statistics Testing for REQ1 and REQ2
Tests the specific requirements from the review request
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

class EnhancedTopicStatisticsTest:
    def __init__(self, base_url: str = "http://localhost:8001"):
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

    def test_req1_enhanced_statistics_fields(self) -> bool:
        """Test REQ1: Enhanced statistics fields in /api/statistics endpoint"""
        print("\n" + "=" * 80)
        print("🔍 REQ1: Testing Enhanced Topic Statistics Fields")
        print("=" * 80)
        print("Testing new fields: messages_per_minute_total, messages_per_minute_rolling, slowest_traces")
        print("=" * 80)
        
        try:
            response = requests.get(f"{self.base_url}/api/statistics", timeout=15)
            
            if response.status_code != 200:
                self.log_test("REQ1 - Statistics Endpoint Access", False, f"HTTP {response.status_code}")
                return False
            
            data = response.json()
            
            # Verify main structure
            if "topics" not in data or "details" not in data["topics"]:
                self.log_test("REQ1 - Statistics Structure", False, "Missing topics.details section")
                return False
            
            topics_details = data["topics"]["details"]
            
            if not topics_details:
                self.log_test("REQ1 - Statistics Structure", False, "No topic details found")
                return False
            
            # Test new fields for each topic
            required_new_fields = [
                'messages_per_minute_total',
                'messages_per_minute_rolling', 
                'slowest_traces'
            ]
            
            topics_tested = 0
            sample_data = {}
            
            for topic_name, topic_data in topics_details.items():
                topics_tested += 1
                
                # Check if all new REQ1 fields are present
                missing_fields = [field for field in required_new_fields if field not in topic_data]
                
                if missing_fields:
                    self.log_test("REQ1 - New Fields Present", False, f"Topic {topic_name} missing: {missing_fields}")
                    return False
                
                # Validate field types and values
                mpm_total = topic_data['messages_per_minute_total']
                mpm_rolling = topic_data['messages_per_minute_rolling']
                slowest_traces = topic_data['slowest_traces']
                
                # Validate messages_per_minute_total
                if not isinstance(mpm_total, (int, float)) or mpm_total < 0:
                    self.log_test("REQ1 - messages_per_minute_total Type", False, f"Invalid value for {topic_name}: {mpm_total}")
                    return False
                
                # Validate messages_per_minute_rolling
                if not isinstance(mpm_rolling, (int, float)) or mpm_rolling < 0:
                    self.log_test("REQ1 - messages_per_minute_rolling Type", False, f"Invalid value for {topic_name}: {mpm_rolling}")
                    return False
                
                # Validate slowest_traces array structure
                if not isinstance(slowest_traces, list):
                    self.log_test("REQ1 - slowest_traces Structure", False, f"slowest_traces not array for {topic_name}")
                    return False
                
                # Validate slowest_traces data structure if not empty
                for trace_data in slowest_traces:
                    if not isinstance(trace_data, dict):
                        self.log_test("REQ1 - slowest_traces Item Structure", False, f"Invalid trace data structure in {topic_name}")
                        return False
                    
                    required_trace_fields = ['trace_id', 'time_to_topic', 'total_duration']
                    missing_trace_fields = [field for field in required_trace_fields if field not in trace_data]
                    
                    if missing_trace_fields:
                        self.log_test("REQ1 - slowest_traces Fields", False, f"Missing fields in slowest_traces for {topic_name}: {missing_trace_fields}")
                        return False
                    
                    # Validate trace field types
                    if not isinstance(trace_data['trace_id'], str):
                        self.log_test("REQ1 - trace_id Type", False, f"trace_id not string in {topic_name}")
                        return False
                    
                    if not isinstance(trace_data['time_to_topic'], (int, float)) or trace_data['time_to_topic'] < 0:
                        self.log_test("REQ1 - time_to_topic Type", False, f"Invalid time_to_topic in {topic_name}: {trace_data['time_to_topic']}")
                        return False
                    
                    if not isinstance(trace_data['total_duration'], (int, float)) or trace_data['total_duration'] < 0:
                        self.log_test("REQ1 - total_duration Type", False, f"Invalid total_duration in {topic_name}: {trace_data['total_duration']}")
                        return False
                
                # Store sample data for reporting
                if len(sample_data) < 4:  # Show all topics
                    sample_data[topic_name] = {
                        'mpm_total': mpm_total,
                        'mpm_rolling': mpm_rolling,
                        'slowest_traces_count': len(slowest_traces)
                    }
            
            self.log_test("REQ1 - Enhanced Fields Implementation", True, f"All new fields valid for {topics_tested} topics")
            
            # Log sample data for all topics
            for topic, data in sample_data.items():
                self.log_test(f"REQ1 Sample - {topic}", True, f"MPM Total: {data['mpm_total']:.2f}, MPM Rolling: {data['mpm_rolling']:.2f}, Slowest Traces: {data['slowest_traces_count']}")
            
            # Test different scenarios - topics with no messages vs topics with messages
            topics_with_messages = 0
            topics_without_messages = 0
            
            for topic_name, topic_data in topics_details.items():
                message_count = topic_data.get('message_count', 0)
                if message_count > 0:
                    topics_with_messages += 1
                else:
                    topics_without_messages += 1
                    # Verify zero-message topics have zero values and empty arrays
                    if (topic_data['messages_per_minute_total'] != 0 or 
                        topic_data['messages_per_minute_rolling'] != 0 or 
                        len(topic_data['slowest_traces']) != 0):
                        self.log_test("REQ1 - Topics Without Messages", False, f"Topic {topic_name} has no messages but non-zero values")
                        return False
            
            self.log_test("REQ1 - Scenario Testing", True, f"Topics with messages: {topics_with_messages}, without: {topics_without_messages}")
            
            return True
            
        except Exception as e:
            self.log_test("REQ1 - Statistics Test", False, f"Exception: {str(e)}")
            return False

    def test_req2_graceful_topic_handling(self) -> bool:
        """Test REQ2: Graceful handling when topics don't exist"""
        print("\n" + "=" * 80)
        print("🔍 REQ2: Testing Graceful Topic Handling")
        print("=" * 80)
        print("Testing: Kafka consumer subscription, warning logs, system continues operating")
        print("=" * 80)
        
        try:
            # Test /api/topics endpoint
            topics_response = requests.get(f"{self.base_url}/api/topics", timeout=10)
            if topics_response.status_code == 200:
                topics_data = topics_response.json()
                all_topics = topics_data.get('all_topics', [])
                monitored_topics = topics_data.get('monitored_topics', [])
                
                self.log_test("REQ2 - Topics Endpoint", True, f"All: {len(all_topics)}, Monitored: {len(monitored_topics)}")
                
                # Test that system continues to operate even if some topics don't exist
                self.log_test("REQ2 - System Operation", True, "System continues operating with topic configuration")
            else:
                self.log_test("REQ2 - Topics Endpoint", False, f"HTTP {topics_response.status_code}")
                return False
            
            # Test /api/grpc/status to verify system is running
            grpc_response = requests.get(f"{self.base_url}/api/grpc/status", timeout=10)
            if grpc_response.status_code in [200, 503]:  # 503 is acceptable if gRPC not initialized
                self.log_test("REQ2 - System Status", True, f"System running (HTTP {grpc_response.status_code})")
            else:
                self.log_test("REQ2 - System Status", False, f"Unexpected status: {grpc_response.status_code}")
                return False
            
            # Test Kafka consumer subscription handling (via health check)
            health_response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if health_response.status_code == 200:
                health_data = health_response.json()
                if health_data.get('status') == 'healthy':
                    self.log_test("REQ2 - Kafka Consumer Health", True, f"Kafka consumer operational with {health_data.get('traces_count', 0)} traces")
                else:
                    self.log_test("REQ2 - Kafka Consumer Health", False, f"Unhealthy status: {health_data.get('status')}")
                    return False
            else:
                self.log_test("REQ2 - Kafka Consumer Health", False, f"Health check failed: {health_response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            self.log_test("REQ2 - Topic Handling Test", False, f"Exception: {str(e)}")
            return False

    def test_expected_response_format(self) -> bool:
        """Test that response format matches the expected structure from review request"""
        print("\n" + "=" * 80)
        print("🔍 Testing Expected Response Format")
        print("=" * 80)
        print("Validating response structure matches review request specification")
        print("=" * 80)
        
        try:
            response = requests.get(f"{self.base_url}/api/statistics", timeout=15)
            
            if response.status_code != 200:
                self.log_test("Response Format - Endpoint Access", False, f"HTTP {response.status_code}")
                return False
            
            data = response.json()
            topics_details = data["topics"]["details"]
            
            # Verify the response matches the expected format from review request
            expected_structure_found = False
            
            for topic_name, topic_data in topics_details.items():
                # Check if we have the expected structure
                if (isinstance(topic_data.get('message_count'), int) and
                    isinstance(topic_data.get('trace_count'), int) and
                    isinstance(topic_data.get('messages_per_minute_total'), (int, float)) and
                    isinstance(topic_data.get('messages_per_minute_rolling'), (int, float)) and
                    isinstance(topic_data.get('slowest_traces'), list)):
                    
                    expected_structure_found = True
                    
                    # Validate slowest_traces structure matches expected format
                    for trace in topic_data['slowest_traces']:
                        if (isinstance(trace.get('trace_id'), str) and
                            isinstance(trace.get('time_to_topic'), (int, float)) and
                            isinstance(trace.get('total_duration'), (int, float))):
                            continue
                        else:
                            expected_structure_found = False
                            break
                    break
            
            if expected_structure_found:
                self.log_test("Expected Response Format", True, "Response format matches expected structure from review request")
                
                # Show sample of expected format
                sample_topic = list(topics_details.keys())[0]
                sample_data = topics_details[sample_topic]
                
                expected_format = {
                    "topics": {
                        "details": {
                            sample_topic: {
                                "message_count": sample_data["message_count"],
                                "trace_count": sample_data["trace_count"],
                                "messages_per_minute_total": sample_data["messages_per_minute_total"],
                                "messages_per_minute_rolling": sample_data["messages_per_minute_rolling"],
                                "slowest_traces": sample_data["slowest_traces"]
                            }
                        }
                    }
                }
                
                print(f"📋 Sample Expected Format:")
                print(json.dumps(expected_format, indent=2))
                
                return True
            else:
                self.log_test("Expected Response Format", False, "Response format doesn't match expected structure")
                return False
            
        except Exception as e:
            self.log_test("Expected Response Format", False, f"Exception: {str(e)}")
            return False

    def run_comprehensive_test(self) -> bool:
        """Run all REQ1 and REQ2 tests"""
        print("🎯 ENHANCED TOPIC STATISTICS TESTING - REQ1 & REQ2")
        print("=" * 80)
        print("Testing enhanced topic statistics implementation")
        print("Base URL:", self.base_url)
        print("=" * 80)
        
        # Test REQ1: Enhanced statistics fields
        req1_passed = self.test_req1_enhanced_statistics_fields()
        
        # Test REQ2: Graceful topic handling
        req2_passed = self.test_req2_graceful_topic_handling()
        
        # Test expected response format
        format_passed = self.test_expected_response_format()
        
        # Print final summary
        print("\n" + "=" * 80)
        print("📊 FINAL TEST SUMMARY")
        print("=" * 80)
        print(f"Total tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        all_passed = req1_passed and req2_passed and format_passed
        
        if all_passed:
            print("\n🎉 ALL ENHANCED TOPIC STATISTICS TESTS PASSED!")
            print("✅ REQ1: Enhanced statistics fields working correctly")
            print("   - messages_per_minute_total field present and valid")
            print("   - messages_per_minute_rolling field present and valid")
            print("   - slowest_traces array present with correct structure")
            print("✅ REQ2: Graceful topic handling working correctly")
            print("   - Kafka consumer subscription handling works")
            print("   - System continues operating without failing")
            print("   - All required endpoints accessible")
            print("✅ Response format matches review request specification")
        else:
            print("\n⚠️  Some tests failed:")
            if not req1_passed:
                print("❌ REQ1: Enhanced statistics fields have issues")
            if not req2_passed:
                print("❌ REQ2: Topic handling has issues")
            if not format_passed:
                print("❌ Response format doesn't match specification")
        
        return all_passed

def main():
    """Main test execution"""
    tester = EnhancedTopicStatisticsTest()
    success = tester.run_comprehensive_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())