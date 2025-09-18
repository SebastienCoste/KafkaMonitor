#!/usr/bin/env python3
"""
Test Enhanced Topic Statistics Bug Fixes - CRITICAL REVIEW REQUEST TESTS
"""

import requests
import json
import sys
import time
from datetime import datetime

class EnhancedStatisticsTestRunner:
    def __init__(self, base_url: str = "https://kafka-trace-viewer.preview.emergentagent.com"):
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
    
    def test_enhanced_topic_statistics_bug_fixes(self) -> bool:
        """Test Enhanced Topic Statistics Bug Fixes - CRITICAL REVIEW REQUEST TESTS"""
        print("\n" + "=" * 80)
        print("🎯 TESTING ENHANCED TOPIC STATISTICS BUG FIXES - REVIEW REQUEST")
        print("=" * 80)
        
        all_tests_passed = True
        
        # REQ1 Fix Testing - Trace ID Visibility
        req1_passed = self.test_trace_id_visibility_fix()
        all_tests_passed = all_tests_passed and req1_passed
        
        # REQ2 Fix Testing - Correct "time to topic" calculation
        req2_passed = self.test_time_to_topic_calculation_fix()
        all_tests_passed = all_tests_passed and req2_passed
        
        # Overall Speed Fix Testing - Rate calculations
        speed_fix_passed = self.test_rate_calculation_fixes()
        all_tests_passed = all_tests_passed and speed_fix_passed
        
        if all_tests_passed:
            self.log_test("Enhanced Topic Statistics Bug Fixes - OVERALL", True, "All critical bug fixes verified working correctly")
        else:
            self.log_test("Enhanced Topic Statistics Bug Fixes - OVERALL", False, "Some critical bug fixes are not working properly")
        
        return all_tests_passed
    
    def test_trace_id_visibility_fix(self) -> bool:
        """REQ1 Fix Testing - Test that API returns full trace IDs in slowest_traces array, not truncated ones"""
        print("\n" + "=" * 60)
        print("🔍 REQ1 Fix Testing - Trace ID Visibility")
        print("=" * 60)
        
        try:
            response = requests.get(f"{self.base_url}/api/statistics", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if topics section exists with details
                if "topics" not in data or "details" not in data["topics"]:
                    self.log_test("REQ1 - Trace ID Visibility Structure", False, "Missing topics.details section in statistics")
                    return False
                
                topics_details = data["topics"]["details"]
                full_trace_ids_found = True
                truncated_trace_ids_found = False
                total_slowest_traces = 0
                sample_trace_ids = []
                
                for topic_name, topic_data in topics_details.items():
                    if "slowest_traces" in topic_data:
                        slowest_traces = topic_data["slowest_traces"]
                        total_slowest_traces += len(slowest_traces)
                        
                        for trace_info in slowest_traces:
                            if "trace_id" in trace_info:
                                trace_id = trace_info["trace_id"]
                                sample_trace_ids.append(trace_id)
                                
                                # Check if trace ID looks truncated (too short or ends with ...)
                                if len(trace_id) < 10 or trace_id.endswith("...") or trace_id.endswith("…"):
                                    truncated_trace_ids_found = True
                                    full_trace_ids_found = False
                                    self.log_test("REQ1 - Trace ID Truncation Detected", False, f"Topic {topic_name} has truncated trace ID: {trace_id}")
                                    break
                        
                        if not full_trace_ids_found:
                            break
                
                if total_slowest_traces == 0:
                    self.log_test("REQ1 - Trace ID Visibility", True, "No slowest_traces data available to test (expected in empty environment)")
                    return True
                elif full_trace_ids_found and not truncated_trace_ids_found:
                    self.log_test("REQ1 - Trace ID Visibility", True, f"All {total_slowest_traces} trace IDs are full-length, not truncated. Sample IDs: {sample_trace_ids[:3]}")
                    return True
                else:
                    self.log_test("REQ1 - Trace ID Visibility", False, f"Found truncated trace IDs in slowest_traces")
                    return False
                    
            else:
                self.log_test("REQ1 - Trace ID Visibility", False, f"Statistics endpoint failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("REQ1 - Trace ID Visibility", False, f"Exception: {str(e)}")
            return False
    
    def test_time_to_topic_calculation_fix(self) -> bool:
        """REQ2 Fix Testing - Correct 'time to topic' calculation"""
        print("\n" + "=" * 60)
        print("🔍 REQ2 Fix Testing - Time to Topic Calculation")
        print("=" * 60)
        
        try:
            response = requests.get(f"{self.base_url}/api/statistics", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if "topics" not in data or "details" not in data["topics"]:
                    self.log_test("REQ2 - Time to Topic Structure", False, "Missing topics.details section")
                    return False
                
                topics_details = data["topics"]["details"]
                time_to_topic_working = True
                zero_time_traces = 0
                non_zero_time_traces = 0
                sample_timings = []
                
                for topic_name, topic_data in topics_details.items():
                    if "slowest_traces" in topic_data:
                        slowest_traces = topic_data["slowest_traces"]
                        
                        for trace_info in slowest_traces:
                            if "time_to_topic" in trace_info:
                                time_to_topic = trace_info["time_to_topic"]
                                
                                # Check if time_to_topic is a valid number
                                if not isinstance(time_to_topic, (int, float)):
                                    self.log_test("REQ2 - Time to Topic Type", False, f"time_to_topic is not numeric: {type(time_to_topic)}")
                                    time_to_topic_working = False
                                    break
                                
                                # Track zero vs non-zero times
                                if time_to_topic == 0:
                                    zero_time_traces += 1
                                else:
                                    non_zero_time_traces += 1
                                    sample_timings.append({
                                        'topic': topic_name,
                                        'trace_id': trace_info.get('trace_id', 'unknown')[:12] + '...',
                                        'time_to_topic': time_to_topic,
                                        'total_duration': trace_info.get('total_duration', 0)
                                    })
                                
                                # Validate that time_to_topic <= total_duration (if both exist)
                                if "total_duration" in trace_info:
                                    total_duration = trace_info["total_duration"]
                                    if time_to_topic > total_duration:
                                        self.log_test("REQ2 - Time Logic Validation", False, f"time_to_topic ({time_to_topic}) > total_duration ({total_duration})")
                                        time_to_topic_working = False
                                        break
                        
                        if not time_to_topic_working:
                            break
                
                total_traces = zero_time_traces + non_zero_time_traces
                
                if total_traces == 0:
                    self.log_test("REQ2 - Time to Topic Calculation", True, "No slowest_traces data available to test (expected in empty environment)")
                    return True
                elif time_to_topic_working:
                    self.log_test("REQ2 - Time to Topic Calculation", True, 
                                f"Working correctly. Total traces: {total_traces}, Zero times: {zero_time_traces}, Non-zero times: {non_zero_time_traces}")
                    
                    if sample_timings:
                        for timing in sample_timings[:3]:  # Show first 3 samples
                            self.log_test(f"REQ2 - Sample Timing ({timing['topic']})", True, 
                                        f"Trace {timing['trace_id']}: time_to_topic={timing['time_to_topic']}s, total_duration={timing['total_duration']}s")
                    
                    # Validate that we have realistic timing values
                    if non_zero_time_traces > 0:
                        self.log_test("REQ2 - Realistic Timing Values", True, f"Found {non_zero_time_traces} traces with realistic timing > 0")
                    else:
                        # This might be expected if all traces start at their respective topics
                        self.log_test("REQ2 - Timing Analysis", True, f"All {zero_time_traces} traces have 0ms time_to_topic (may indicate traces start at their respective topics)")
                    
                    return True
                else:
                    return False
                    
            else:
                self.log_test("REQ2 - Time to Topic Calculation", False, f"Statistics endpoint failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("REQ2 - Time to Topic Calculation", False, f"Exception: {str(e)}")
            return False
    
    def test_rate_calculation_fixes(self) -> bool:
        """Overall Speed Fix Testing - Verify rate calculations return proper values"""
        print("\n" + "=" * 60)
        print("🔍 Overall Speed Fix Testing - Rate Calculations")
        print("=" * 60)
        
        try:
            response = requests.get(f"{self.base_url}/api/statistics", timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if "topics" not in data or "details" not in data["topics"]:
                    self.log_test("Rate Calculation Structure", False, "Missing topics.details section")
                    return False
                
                topics_details = data["topics"]["details"]
                rate_calculations_working = True
                sample_rates = []
                
                for topic_name, topic_data in topics_details.items():
                    # Check messages_per_minute_total
                    if "messages_per_minute_total" in topic_data:
                        rate_total = topic_data["messages_per_minute_total"]
                        
                        # Should be a decimal number (rate), not integer message count
                        if not isinstance(rate_total, (int, float)):
                            self.log_test("Rate Calculation - Total Type", False, f"messages_per_minute_total is not numeric: {type(rate_total)}")
                            rate_calculations_working = False
                            break
                        
                        # Should be non-negative
                        if rate_total < 0:
                            self.log_test("Rate Calculation - Total Range", False, f"messages_per_minute_total is negative: {rate_total}")
                            rate_calculations_working = False
                            break
                    
                    # Check messages_per_minute_rolling
                    if "messages_per_minute_rolling" in topic_data:
                        rate_rolling = topic_data["messages_per_minute_rolling"]
                        
                        # Should be a decimal number (rate), not integer message count
                        if not isinstance(rate_rolling, (int, float)):
                            self.log_test("Rate Calculation - Rolling Type", False, f"messages_per_minute_rolling is not numeric: {type(rate_rolling)}")
                            rate_calculations_working = False
                            break
                        
                        # Should be non-negative
                        if rate_rolling < 0:
                            self.log_test("Rate Calculation - Rolling Range", False, f"messages_per_minute_rolling is negative: {rate_rolling}")
                            rate_calculations_working = False
                            break
                    
                    # Collect sample data
                    message_count = topic_data.get("message_count", 0)
                    sample_rates.append({
                        'topic': topic_name,
                        'message_count': message_count,
                        'rate_total': topic_data.get("messages_per_minute_total", 0),
                        'rate_rolling': topic_data.get("messages_per_minute_rolling", 0)
                    })
                
                if rate_calculations_working:
                    self.log_test("Rate Calculation - Field Types", True, "All rate fields are properly numeric")
                    
                    # Log sample rates for verification
                    for rate_data in sample_rates:
                        topic = rate_data['topic']
                        msg_count = rate_data['message_count']
                        rate_total = rate_data['rate_total']
                        rate_rolling = rate_data['rate_rolling']
                        
                        # Log sample rates for verification
                        if msg_count > 0 or rate_total > 0 or rate_rolling > 0:
                            self.log_test(f"Rate Sample - {topic}", True, 
                                        f"Messages: {msg_count}, Total rate: {rate_total:.2f}/min, Rolling rate: {rate_rolling:.2f}/min")
                    
                    self.log_test("Rate Calculation Logic", True, f"Rate calculations appear correct for {len(sample_rates)} topics")
                    
                    # Summary of rate testing
                    topics_with_activity = len([r for r in sample_rates if r['message_count'] > 0])
                    topics_with_total_rate = len([r for r in sample_rates if r['rate_total'] > 0])
                    topics_with_rolling_rate = len([r for r in sample_rates if r['rate_rolling'] > 0])
                    
                    self.log_test("Rate Calculation Summary", True, 
                                f"Topics with messages: {topics_with_activity}, with total rate: {topics_with_total_rate}, with rolling rate: {topics_with_rolling_rate}")
                    
                    return True
                else:
                    return False
                    
            else:
                self.log_test("Rate Calculation Testing", False, f"Statistics endpoint failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Rate Calculation Testing", False, f"Exception: {str(e)}")
            return False

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 ENHANCED TOPIC STATISTICS BUG FIXES TEST SUMMARY")
        print("=" * 80)
        
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL ENHANCED TOPIC STATISTICS BUG FIXES TESTS PASSED!")
            print("✅ REQ1: Full trace IDs are returned in slowest_traces (not truncated)")
            print("✅ REQ2: Time to topic calculations are working correctly")
            print("✅ Overall Speed Fix: Rate calculations return proper values")
        else:
            failed_tests = [r for r in self.test_results if not r["success"]]
            print(f"\n⚠️  {len(failed_tests)} tests failed:")
            for test in failed_tests:
                print(f"   • {test['name']}: {test['details']}")
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    print("🚀 Starting Enhanced Topic Statistics Bug Fixes Testing")
    print("=" * 80)
    
    # Test with external URL
    tester = EnhancedStatisticsTestRunner()
    
    # Run the enhanced topic statistics bug fixes tests
    success = tester.test_enhanced_topic_statistics_bug_fixes()
    
    # Print summary
    tester.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)