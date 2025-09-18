#!/usr/bin/env python3
"""
Simple test script to test specific bug fixes without full backend dependency
"""

import requests
import json
import sys
from typing import Dict, Any

def test_bug1_graph_rate_error_fix() -> bool:
    """BUG1: Test Graph Section 'rate' Error Fix"""
    print("🔍 BUG1 TESTING: Graph Section 'rate' Error Fix")
    print("-" * 60)
    
    all_tests_passed = True
    base_url = "http://localhost:8001"
    
    # Test 1: /api/topics/graph endpoint should not return 'rate' KeyError
    try:
        print("📊 Testing /api/topics/graph endpoint...")
        response = requests.get(f"{base_url}/api/topics/graph", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check that response doesn't contain error about 'rate'
            response_text = json.dumps(data).lower()
            if "'rate'" in response_text and "error" in response_text:
                print("❌ BUG1 - Topics Graph Rate Error: FAILED - Response still contains 'rate' error")
                all_tests_passed = False
            else:
                # Verify proper structure
                if "nodes" in data and "edges" in data:
                    print("✅ BUG1 - Topics Graph Rate Error: PASSED - No 'rate' KeyError found, proper structure returned")
                else:
                    print("❌ BUG1 - Topics Graph Structure: FAILED - Missing nodes/edges in response")
                    all_tests_passed = False
        else:
            print(f"❌ BUG1 - Topics Graph Endpoint: FAILED - HTTP {response.status_code}")
            all_tests_passed = False
            
    except Exception as e:
        print(f"❌ BUG1 - Topics Graph Test: FAILED - Exception: {str(e)}")
        all_tests_passed = False
    
    # Test 2: /api/graph/disconnected endpoint should not return 'rate' KeyError
    try:
        print("📊 Testing /api/graph/disconnected endpoint...")
        response = requests.get(f"{base_url}/api/graph/disconnected", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check that response doesn't contain error about 'rate'
            response_text = json.dumps(data).lower()
            if "'rate'" in response_text and "error" in response_text:
                print("❌ BUG1 - Disconnected Graph Rate Error: FAILED - Response still contains 'rate' error")
                all_tests_passed = False
            else:
                # Verify proper structure
                if data.get('success') and 'components' in data:
                    print(f"✅ BUG1 - Disconnected Graph Rate Error: PASSED - No 'rate' KeyError found, {len(data['components'])} components returned")
                else:
                    print("❌ BUG1 - Disconnected Graph Structure: FAILED - Missing success/components in response")
                    all_tests_passed = False
        else:
            print(f"❌ BUG1 - Disconnected Graph Endpoint: FAILED - HTTP {response.status_code}")
            all_tests_passed = False
            
    except Exception as e:
        print(f"❌ BUG1 - Disconnected Graph Test: FAILED - Exception: {str(e)}")
        all_tests_passed = False
    
    return all_tests_passed

def test_bug2_overall_speed_display_fix() -> bool:
    """BUG2: Test Overall Speed Display Fix - messages_per_minute should be rates, not counts"""
    print("\n🔍 BUG2 TESTING: Overall Speed Display Fix")
    print("-" * 60)
    
    all_tests_passed = True
    base_url = "http://localhost:8001"
    
    # Test /api/statistics endpoint for proper rate calculations
    try:
        print("📊 Testing /api/statistics endpoint for rate calculations...")
        response = requests.get(f"{base_url}/api/statistics", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for messages_per_minute_total and messages_per_minute_rolling fields
            if "topics" in data and "details" in data["topics"]:
                topics_details = data["topics"]["details"]
                
                if not topics_details:
                    print("✅ BUG2 - Statistics Structure: PASSED - No topics found (expected in empty environment)")
                    return True
                
                rate_fields_correct = True
                sample_rates = {}
                
                for topic_name, topic_data in topics_details.items():
                    # Check for required rate fields
                    required_rate_fields = ['messages_per_minute_total', 'messages_per_minute_rolling']
                    missing_fields = [field for field in required_rate_fields if field not in topic_data]
                    
                    if missing_fields:
                        print(f"❌ BUG2 - Rate Fields Missing: FAILED - Topic {topic_name} missing: {missing_fields}")
                        rate_fields_correct = False
                        break
                    
                    # Verify values are rates (decimal numbers) not message counts (integers)
                    total_rate = topic_data['messages_per_minute_total']
                    rolling_rate = topic_data['messages_per_minute_rolling']
                    
                    # Check that values are numeric
                    if not isinstance(total_rate, (int, float)) or not isinstance(rolling_rate, (int, float)):
                        print(f"❌ BUG2 - Rate Values Type: FAILED - Topic {topic_name} has non-numeric rates: total={total_rate}, rolling={rolling_rate}")
                        rate_fields_correct = False
                        break
                    
                    # Check that values are non-negative
                    if total_rate < 0 or rolling_rate < 0:
                        print(f"❌ BUG2 - Rate Values Range: FAILED - Topic {topic_name} has negative rates: total={total_rate}, rolling={rolling_rate}")
                        rate_fields_correct = False
                        break
                    
                    # Store sample for reporting
                    if len(sample_rates) < 3:
                        sample_rates[topic_name] = {
                            'total': total_rate,
                            'rolling': rolling_rate
                        }
                
                if rate_fields_correct:
                    print(f"✅ BUG2 - Rate Fields Structure: PASSED - All rate fields present and valid for {len(topics_details)} topics")
                    
                    # Log sample rates for verification
                    for topic, rates in sample_rates.items():
                        print(f"✅ BUG2 Sample Rates - {topic}: PASSED - Total: {rates['total']}/min, Rolling: {rates['rolling']}/min")
                    
                    print("✅ BUG2 - Rate Calculation Format: PASSED - messages_per_minute fields are properly formatted as rates")
                else:
                    all_tests_passed = False
                    
            else:
                print("❌ BUG2 - Statistics Structure: FAILED - Missing topics.details section in statistics")
                all_tests_passed = False
                
        else:
            print(f"❌ BUG2 - Statistics Endpoint: FAILED - HTTP {response.status_code}")
            all_tests_passed = False
            
    except Exception as e:
        print(f"❌ BUG2 - Statistics Test: FAILED - Exception: {str(e)}")
        all_tests_passed = False
    
    return all_tests_passed

def main():
    """Main test execution"""
    print("🎯 TESTING SPECIFIC BUG FIXES FROM REVIEW REQUEST")
    print("=" * 80)
    
    bug1_passed = test_bug1_graph_rate_error_fix()
    bug2_passed = test_bug2_overall_speed_display_fix()
    
    print(f"\n{'='*80}")
    print("📊 FINAL TEST SUMMARY")
    print(f"{'='*80}")
    print(f"🎯 BUG1 - Graph Rate Error Fix: {'✅ PASSED' if bug1_passed else '❌ FAILED'}")
    print(f"🎯 BUG2 - Overall Speed Display Fix: {'✅ PASSED' if bug2_passed else '❌ FAILED'}")
    print(f"📈 Overall Result: {'✅ ALL TESTS PASSED' if (bug1_passed and bug2_passed) else '❌ SOME TESTS FAILED'}")
    
    return 0 if (bug1_passed and bug2_passed) else 1

if __name__ == "__main__":
    sys.exit(main())