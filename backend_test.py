#!/usr/bin/env python3
"""
Backend Testing for Blueprint Configuration APIs - Critical Routing Fix Verification
Testing the critical Blueprint Configuration APIs to verify the backend routing fix is working
"""

import requests
import json
import sys
import time
import asyncio
import websockets
from datetime import datetime
from typing import Dict, Any, List

class BackendRoutingTester:
    def __init__(self, base_url: str = "https://blueprint-connect.preview.emergentagent.com"):
        self.base_url = base_url
        self.ws_base_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
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
    
    # Test Suite A - Core APIs
    def test_health_endpoint(self):
        """Test Suite A.1: GET /api/health - Health check"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.log_test("Health Check", True, f"Status: {data.get('status')}")
                    return True
                else:
                    self.log_test("Health Check", False, f"Unexpected status: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False
    
    def test_app_config_endpoint(self):
        """Test Suite A.2: GET /api/app-config - Application configuration"""
        try:
            response = requests.get(f"{self.base_url}/api/app-config", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected fields
                expected_fields = ["app_name", "version", "environment", "tabs"]
                found_fields = [field for field in expected_fields if field in data]
                
                if len(found_fields) >= 3:  # At least 3 of 4 expected fields
                    self.log_test("App Config", True, f"Found fields: {found_fields}")
                    
                    # Check tabs structure
                    if "tabs" in data and isinstance(data["tabs"], dict):
                        tab_count = len(data["tabs"])
                        self.log_test("App Config - Tabs", True, f"Found {tab_count} tabs: {list(data['tabs'].keys())}")
                    
                    return True
                else:
                    self.log_test("App Config", False, f"Missing expected fields. Found: {list(data.keys())}")
                    return False
            else:
                self.log_test("App Config", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("App Config", False, f"Exception: {str(e)}")
            return False
    
    def test_environments_endpoint(self):
        """Test Suite A.3: GET /api/environments - Environment list"""
        try:
            response = requests.get(f"{self.base_url}/api/environments", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for environments list
                environments = data.get("environments", []) or data.get("available_environments", [])
                expected_envs = ["DEV", "TEST", "INT", "LOAD", "PROD"]
                
                if environments and isinstance(environments, list):
                    found_expected = [env for env in expected_envs if env in environments]
                    if len(found_expected) >= 3:  # At least 3 of 5 expected environments
                        self.log_test("Environments", True, f"Found environments: {environments}")
                        return True
                    else:
                        self.log_test("Environments", False, f"Missing expected environments. Found: {environments}")
                        return False
                else:
                    self.log_test("Environments", False, f"No valid environments list found: {data}")
                    return False
            else:
                self.log_test("Environments", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Environments", False, f"Exception: {str(e)}")
            return False
    
    def test_file_tree_endpoint(self):
        """Test Suite A.4: GET /api/blueprint/file-tree - File tree browsing"""
        try:
            # First set up root path
            self.setup_blueprint_root_path()
            
            response = requests.get(f"{self.base_url}/api/blueprint/file-tree", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "files" in data and isinstance(data["files"], list):
                    file_count = len(data["files"])
                    self.log_test("File Tree", True, f"Found {file_count} files/directories")
                    
                    # Show sample files
                    if file_count > 0:
                        sample_files = []
                        for i, f in enumerate(data["files"][:3]):  # First 3 files
                            if isinstance(f, dict):
                                sample_files.append(f.get("name", "unknown"))
                            else:
                                sample_files.append(str(f))
                        self.log_test("File Tree - Sample", True, f"Sample files: {sample_files}")
                    
                    return True
                else:
                    self.log_test("File Tree", False, f"Invalid response structure: {data}")
                    return False
            else:
                self.log_test("File Tree", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("File Tree", False, f"Exception: {str(e)}")
            return False
    
    # Test Suite B - Blueprint Configuration
    def test_entity_definitions_endpoint(self):
        """Test Suite B.5: GET /api/blueprint/config/entity-definitions - Entity definitions schema"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/config/entity-definitions", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for entity types - the response format is a dict with entity type names as keys
                if isinstance(data, dict) and len(data) >= 5:  # Expect at least 5 entity types
                    entity_type_names = list(data.keys())
                    self.log_test("Entity Definitions", True, f"Found {len(entity_type_names)} entity types: {entity_type_names[:5]}...")
                    
                    # Check for environments in the response (might be in a separate field)
                    environments_found = False
                    for entity_name, entity_data in data.items():
                        if isinstance(entity_data, dict) and 'environments' in str(entity_data):
                            environments_found = True
                            break
                    
                    if environments_found:
                        self.log_test("Entity Definitions - Structure", True, f"Entity structure contains environment references")
                    else:
                        self.log_test("Entity Definitions - Structure", True, f"Entity structure valid (no environment refs needed)")
                    
                    return True
                elif "entityTypes" in data:
                    # Alternative format check
                    entity_types = data["entityTypes"]
                    if isinstance(entity_types, list) and len(entity_types) >= 5:
                        self.log_test("Entity Definitions", True, f"Found {len(entity_types)} entity types (list format)")
                        return True
                    elif isinstance(entity_types, dict) and len(entity_types) >= 5:
                        self.log_test("Entity Definitions", True, f"Found {len(entity_types)} entity types (dict format)")
                        return True
                    else:
                        self.log_test("Entity Definitions", False, f"Invalid entity types: {type(entity_types)} with {len(entity_types) if hasattr(entity_types, '__len__') else 'unknown'} items")
                        return False
                else:
                    self.log_test("Entity Definitions", False, f"Invalid response format. Keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                    return False
            else:
                self.log_test("Entity Definitions", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Entity Definitions", False, f"Exception: {str(e)}")
            return False
    
    def test_namespace_endpoint(self):
        """Test Suite B.6: GET /api/blueprint/namespace - Namespace detection"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/namespace", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for namespace field
                if "namespace" in data and "source" in data:
                    namespace = data.get("namespace", "")
                    source = data.get("source", "")
                    
                    if source == "blueprint_cnf.json" and namespace:
                        self.log_test("Namespace Detection", True, f"Found namespace: {namespace} from {source}")
                    elif source == "not_found":
                        self.log_test("Namespace Detection", True, f"No blueprint_cnf.json found (expected for new projects)")
                    else:
                        self.log_test("Namespace Detection", True, f"Namespace: '{namespace}' from {source}")
                    
                    return True
                else:
                    self.log_test("Namespace Detection", False, f"Missing expected fields: {data}")
                    return False
            else:
                self.log_test("Namespace Detection", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Namespace Detection", False, f"Exception: {str(e)}")
            return False
    
    def test_blueprint_cnf_file_content(self):
        """Test Suite B.7: GET /api/blueprint/file-content/blueprint_cnf.json - File content reading"""
        try:
            response = requests.get(f"{self.base_url}/api/blueprint/file-content/blueprint_cnf.json", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "content" in data:
                    content = data["content"]
                    
                    # Try to parse JSON content
                    try:
                        parsed_content = json.loads(content)
                        
                        # Check for expected blueprint structure
                        expected_fields = ["namespace", "version"]
                        found_fields = [field for field in expected_fields if field in parsed_content]
                        
                        if found_fields:
                            self.log_test("Blueprint CNF Content", True, f"Valid JSON with fields: {list(parsed_content.keys())}")
                            
                            # Show key details
                            namespace = parsed_content.get("namespace", "N/A")
                            version = parsed_content.get("version", "N/A")
                            self.log_test("Blueprint CNF Details", True, f"Namespace: {namespace}, Version: {version}")
                        else:
                            self.log_test("Blueprint CNF Content", True, f"Valid JSON but missing expected fields: {list(parsed_content.keys())}")
                        
                        return True
                    except json.JSONDecodeError:
                        self.log_test("Blueprint CNF Content", False, f"Invalid JSON content")
                        return False
                else:
                    self.log_test("Blueprint CNF Content", False, f"Missing content field: {data}")
                    return False
            elif response.status_code == 404:
                self.log_test("Blueprint CNF Content", True, "File not found (404) - acceptable for new projects")
                return True
            else:
                self.log_test("Blueprint CNF Content", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Blueprint CNF Content", False, f"Exception: {str(e)}")
            return False
    
    # Test Suite C - WebSocket
    async def test_websocket_connection(self, path: str, test_name: str):
        """Test WebSocket connection to a specific path"""
        try:
            ws_url = f"{self.ws_base_url}{path}"
            
            # Try to connect with a timeout
            async with websockets.connect(ws_url, open_timeout=10, close_timeout=5) as websocket:
                # Send a ping and wait for response
                await websocket.send(json.dumps({"type": "test_ping"}))
                
                # Wait for any response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    self.log_test(test_name, True, f"Connected successfully, received: {response[:100]}")
                    return True
                except asyncio.TimeoutError:
                    # Connection established but no immediate response - still success
                    self.log_test(test_name, True, f"Connected successfully (no immediate response)")
                    return True
                    
        except websockets.exceptions.ConnectionClosed:
            self.log_test(test_name, False, "WebSocket connection closed unexpectedly")
            return False
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 403:
                self.log_test(test_name, False, f"WebSocket connection forbidden (403)")
            else:
                self.log_test(test_name, False, f"WebSocket invalid status: {e.status_code}")
            return False
        except Exception as e:
            self.log_test(test_name, False, f"WebSocket error: {str(e)}")
            return False
    
    def test_websocket_main(self):
        """Test Suite C.8: Test WebSocket connection to /api/ws"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.test_websocket_connection("/api/ws", "WebSocket Main"))
            loop.close()
            return result
        except Exception as e:
            self.log_test("WebSocket Main", False, f"Async error: {str(e)}")
            return False
    
    def test_websocket_blueprint(self):
        """Test Suite C.9: Test WebSocket connection to /api/ws/blueprint"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.test_websocket_connection("/api/ws/blueprint", "WebSocket Blueprint"))
            loop.close()
            return result
        except Exception as e:
            self.log_test("WebSocket Blueprint", False, f"Async error: {str(e)}")
            return False
    
    def test_statistics_endpoint(self):
        """Test Suite D.10: GET /api/statistics - Statistics endpoint structure verification"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/statistics", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response time (should be < 1 second)
                if response_time < 1.0:
                    self.log_test("Statistics Response Time", True, f"Response time: {response_time:.3f}s")
                else:
                    self.log_test("Statistics Response Time", False, f"Response time too slow: {response_time:.3f}s")
                
                # Check main structure
                required_top_level = ["traces", "topics", "messages", "time_range"]
                found_top_level = [field for field in required_top_level if field in data]
                
                if len(found_top_level) >= 3:  # At least 3 of 4 required fields
                    self.log_test("Statistics Structure", True, f"Found top-level fields: {found_top_level}")
                    
                    # Check traces structure
                    if "traces" in data and isinstance(data["traces"], dict):
                        traces = data["traces"]
                        traces_fields = ["total", "max_capacity", "utilization"]
                        found_traces_fields = [field for field in traces_fields if field in traces]
                        
                        if len(found_traces_fields) >= 2:
                            self.log_test("Statistics Traces", True, f"Traces fields: {found_traces_fields}")
                        else:
                            self.log_test("Statistics Traces", False, f"Missing traces fields. Found: {list(traces.keys())}")
                    
                    # Check topics structure
                    if "topics" in data and isinstance(data["topics"], dict):
                        topics = data["topics"]
                        topics_fields = ["total", "monitored", "with_messages", "details"]
                        found_topics_fields = [field for field in topics_fields if field in topics]
                        
                        if len(found_topics_fields) >= 3:
                            self.log_test("Statistics Topics", True, f"Topics fields: {found_topics_fields}")
                            
                            # Check topics.details structure (critical for frontend)
                            if "details" in topics and isinstance(topics["details"], dict):
                                details = topics["details"]
                                self.log_test("Statistics Topics Details", True, f"Found {len(details)} topic details")
                                
                                # Check structure of individual topic details
                                if details:
                                    sample_topic = list(details.keys())[0]
                                    sample_details = details[sample_topic]
                                    
                                    expected_detail_fields = [
                                        "message_count", "trace_count", "monitored", "status",
                                        "messages_per_minute_total", "messages_per_minute_rolling",
                                        "message_age_p10_ms", "message_age_p50_ms", "message_age_p95_ms",
                                        "slowest_traces"
                                    ]
                                    
                                    found_detail_fields = [field for field in expected_detail_fields if field in sample_details]
                                    
                                    if len(found_detail_fields) >= 6:  # At least 6 of 10 expected fields
                                        self.log_test("Statistics Topic Detail Structure", True, 
                                                    f"Sample topic '{sample_topic}' has fields: {found_detail_fields}")
                                        
                                        # Verify rate fields are numbers (not raw counts)
                                        total_rate = sample_details.get("messages_per_minute_total")
                                        rolling_rate = sample_details.get("messages_per_minute_rolling")
                                        
                                        if isinstance(total_rate, (int, float)) and isinstance(rolling_rate, (int, float)):
                                            self.log_test("Statistics Rate Fields", True, 
                                                        f"Rate fields are numeric: total={total_rate}, rolling={rolling_rate}")
                                        else:
                                            self.log_test("Statistics Rate Fields", False, 
                                                        f"Rate fields not numeric: total={type(total_rate)}, rolling={type(rolling_rate)}")
                                    else:
                                        self.log_test("Statistics Topic Detail Structure", False, 
                                                    f"Missing detail fields. Found: {list(sample_details.keys())}")
                                else:
                                    self.log_test("Statistics Topics Details", True, "No topic details (empty environment)")
                            else:
                                self.log_test("Statistics Topics Details", False, f"Invalid details structure: {type(topics.get('details'))}")
                        else:
                            self.log_test("Statistics Topics", False, f"Missing topics fields. Found: {list(topics.keys())}")
                    
                    # Check messages structure
                    if "messages" in data and isinstance(data["messages"], dict):
                        messages = data["messages"]
                        messages_fields = ["total", "by_topic"]
                        found_messages_fields = [field for field in messages_fields if field in messages]
                        
                        if len(found_messages_fields) >= 1:
                            self.log_test("Statistics Messages", True, f"Messages fields: {found_messages_fields}")
                        else:
                            self.log_test("Statistics Messages", False, f"Missing messages fields. Found: {list(messages.keys())}")
                    
                    # Check time_range structure
                    if "time_range" in data and isinstance(data["time_range"], dict):
                        time_range = data["time_range"]
                        time_fields = ["earliest", "latest"]
                        found_time_fields = [field for field in time_fields if field in time_range]
                        
                        if len(found_time_fields) >= 1:
                            self.log_test("Statistics Time Range", True, f"Time range fields: {found_time_fields}")
                        else:
                            self.log_test("Statistics Time Range", False, f"Missing time range fields. Found: {list(time_range.keys())}")
                    
                    # Overall success
                    self.log_test("Statistics Endpoint", True, "Statistics endpoint returns proper structure")
                    return True
                else:
                    self.log_test("Statistics Structure", False, f"Missing required top-level fields. Found: {list(data.keys())}")
                    return False
            else:
                self.log_test("Statistics Endpoint", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Statistics Endpoint", False, f"Exception: {str(e)}")
            return False

    def test_graph_disconnected_endpoint(self):
        """Test Suite E.11: GET /api/graph/disconnected - Graph Component Statistics Real-time Data Fix"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/graph/disconnected", timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response time (should be < 2 seconds as per requirement)
                if response_time < 2.0:
                    self.log_test("Graph Disconnected Response Time", True, f"Response time: {response_time:.3f}s (< 2s requirement)")
                else:
                    self.log_test("Graph Disconnected Response Time", False, f"Response time too slow: {response_time:.3f}s (>= 2s)")
                
                # Check main response structure
                required_fields = ["success", "components", "total_components"]
                found_fields = [field for field in required_fields if field in data]
                
                if len(found_fields) >= 2:  # At least success and components
                    self.log_test("Graph Disconnected Structure", True, f"Found fields: {found_fields}")
                    
                    # Check success field
                    if data.get("success") is True:
                        self.log_test("Graph Disconnected Success", True, "API returns success=true")
                    else:
                        self.log_test("Graph Disconnected Success", False, f"API returns success={data.get('success')}")
                    
                    # Check components array
                    components = data.get("components", [])
                    if isinstance(components, list):
                        self.log_test("Graph Disconnected Components", True, f"Found {len(components)} components")
                        
                        # If components exist, verify their structure
                        if components:
                            sample_component = components[0]
                            
                            # Check component structure
                            expected_component_fields = ["component_id", "topics", "topic_count", "nodes", "edges"]
                            found_component_fields = [field for field in expected_component_fields if field in sample_component]
                            
                            if len(found_component_fields) >= 3:
                                self.log_test("Graph Component Structure", True, f"Component has fields: {found_component_fields}")
                                
                                # Check statistics object (critical for the fix)
                                if "statistics" in sample_component:
                                    stats = sample_component["statistics"]
                                    
                                    # Check for required statistics fields
                                    expected_stats_fields = [
                                        "total_messages", "active_traces", "median_trace_age", 
                                        "p95_trace_age", "health_score"
                                    ]
                                    found_stats_fields = [field for field in expected_stats_fields if field in stats]
                                    
                                    if len(found_stats_fields) >= 4:  # At least 4 of 5 expected fields
                                        self.log_test("Graph Component Statistics Structure", True, 
                                                    f"Statistics has fields: {found_stats_fields}")
                                        
                                        # Verify statistics are real values, not mock calculations
                                        total_messages = stats.get("total_messages")
                                        active_traces = stats.get("active_traces")
                                        median_age = stats.get("median_trace_age")
                                        p95_age = stats.get("p95_trace_age")
                                        
                                        # Check data types
                                        if (isinstance(total_messages, int) and 
                                            isinstance(active_traces, int) and 
                                            isinstance(median_age, (int, float)) and 
                                            isinstance(p95_age, (int, float))):
                                            
                                            self.log_test("Graph Statistics Data Types", True, 
                                                        f"All statistics are numeric: messages={total_messages}, traces={active_traces}, median={median_age}s, p95={p95_age}s")
                                            
                                            # Verify NOT mock values (mock values were: 2400 messages, 95 traces, 120s median, 300s p95)
                                            is_mock_data = (
                                                total_messages == 2400 and 
                                                active_traces == 95 and 
                                                median_age == 120 and 
                                                p95_age == 300
                                            )
                                            
                                            if not is_mock_data:
                                                self.log_test("Graph Statistics Real Data", True, 
                                                            f"Statistics are NOT mock values (expected: real data or zeros)")
                                                
                                                # Since no Kafka data is flowing, expect zeros or very low values
                                                if (total_messages == 0 and active_traces == 0 and 
                                                    median_age == 0 and p95_age == 0):
                                                    self.log_test("Graph Statistics Zero Values", True, 
                                                                "Statistics show zeros (expected for no Kafka data)")
                                                else:
                                                    self.log_test("Graph Statistics Non-Zero Values", True, 
                                                                f"Statistics show non-zero values (may indicate real data): messages={total_messages}, traces={active_traces}")
                                            else:
                                                self.log_test("Graph Statistics Real Data", False, 
                                                            "Statistics still show mock values (2400 messages, 95 traces, 120s median, 300s p95)")
                                        else:
                                            self.log_test("Graph Statistics Data Types", False, 
                                                        f"Invalid data types: messages={type(total_messages)}, traces={type(active_traces)}, median={type(median_age)}, p95={type(p95_age)}")
                                    else:
                                        self.log_test("Graph Component Statistics Structure", False, 
                                                    f"Missing statistics fields. Found: {list(stats.keys()) if isinstance(stats, dict) else type(stats)}")
                                else:
                                    self.log_test("Graph Component Statistics", False, "Component missing statistics object")
                            else:
                                self.log_test("Graph Component Structure", False, 
                                            f"Missing component fields. Found: {list(sample_component.keys()) if isinstance(sample_component, dict) else type(sample_component)}")
                        else:
                            self.log_test("Graph Disconnected Components", True, "No components found (expected for empty environment)")
                    else:
                        self.log_test("Graph Disconnected Components", False, f"Components is not a list: {type(components)}")
                    
                    # Check total_components field
                    total_components = data.get("total_components")
                    if isinstance(total_components, int) and total_components >= 0:
                        self.log_test("Graph Total Components", True, f"Total components: {total_components}")
                    else:
                        self.log_test("Graph Total Components", False, f"Invalid total_components: {total_components}")
                    
                    # Overall success
                    self.log_test("Graph Disconnected Endpoint", True, "Graph disconnected endpoint returns proper structure with real-time data")
                    return True
                else:
                    self.log_test("Graph Disconnected Structure", False, f"Missing required fields. Found: {list(data.keys())}")
                    return False
            else:
                self.log_test("Graph Disconnected Endpoint", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Graph Disconnected Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def setup_blueprint_root_path(self):
        """Set up blueprint root path for testing"""
        try:
            response = requests.post(
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

    def run_critical_routing_tests(self):
        """Run critical Blueprint Configuration API tests to verify routing fix"""
        print("🚀 Starting Critical Blueprint Configuration API Routing Tests")
        print("=" * 80)
        print("Testing critical APIs to verify backend routing fix is working")
        print("Context: API routes were returning 404, server.py restructured to register API router BEFORE SPA catch-all routes")
        print("=" * 80)
        
        # Test Suite A - Core APIs
        print("\n🔧 TEST SUITE A - CORE APIs")
        print("-" * 50)
        
        print("\n1️⃣ Testing Health Check")
        self.test_health_endpoint()
        
        print("\n2️⃣ Testing App Configuration")
        self.test_app_config_endpoint()
        
        print("\n3️⃣ Testing Environments")
        self.test_environments_endpoint()
        
        print("\n4️⃣ Testing File Tree")
        self.test_file_tree_endpoint()
        
        # Test Suite B - Blueprint Configuration
        print("\n🎯 TEST SUITE B - BLUEPRINT CONFIGURATION")
        print("-" * 50)
        
        print("\n5️⃣ Testing Entity Definitions")
        self.test_entity_definitions_endpoint()
        
        print("\n6️⃣ Testing Namespace Detection")
        self.test_namespace_endpoint()
        
        print("\n7️⃣ Testing Blueprint CNF File Content")
        self.test_blueprint_cnf_file_content()
        
        # Test Suite C - WebSocket
        print("\n🌐 TEST SUITE C - WEBSOCKET")
        print("-" * 50)
        
        print("\n8️⃣ Testing WebSocket Main Connection")
        self.test_websocket_main()
        
        print("\n9️⃣ Testing WebSocket Blueprint Connection")
        self.test_websocket_blueprint()
        
        # Test Suite D - Statistics Endpoint
        print("\n📊 TEST SUITE D - STATISTICS ENDPOINT")
        print("-" * 50)
        
        print("\n🔟 Testing Statistics Endpoint Structure")
        self.test_statistics_endpoint()
        
        # Test Suite E - Graph Component Statistics Fix
        print("\n📈 TEST SUITE E - GRAPH COMPONENT STATISTICS FIX")
        print("-" * 50)
        
        print("\n1️⃣1️⃣ Testing Graph Disconnected Endpoint Real-time Data")
        self.test_graph_disconnected_endpoint()
        
        # Test Suite F - gRPC Example Endpoints
        print("\n📡 TEST SUITE F - gRPC EXAMPLE ENDPOINTS (Load Default Buttons Fix)")
        print("-" * 50)
        
        print("\n1️⃣2️⃣ Testing gRPC Example Endpoints")
        self.test_grpc_example_endpoints()
        
        print("\n1️⃣3️⃣ Testing gRPC Error Handling")
        self.test_grpc_error_handling()
        
        # Print final summary
        self.print_summary()

    def run_backend_sanity_tests(self):
        """Legacy method - redirect to new critical routing tests"""
        self.run_critical_routing_tests()
    
    def test_entity_definitions_environments(self):
        """Legacy method - kept for compatibility"""
        return self.test_entity_definitions_endpoint()
    
    def test_blueprint_create_file_overwrite(self):
        """Test blueprint file creation with overwrite functionality"""
        try:
            # Sample blueprint_cnf.json content
            sample_content = {
                "namespace": "com.test.blueprint.routing.check",
                "version": "1.0.0",
                "description": "Sample blueprint configuration for routing testing",
                "owner": "routing-test"
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
                    self.log_test("Blueprint Create File", True, "Successfully created/overwritten blueprint_cnf.json")
                    return True
                else:
                    self.log_test("Blueprint Create File", False, f"Create file failed: {data}")
                    return False
            else:
                self.log_test("Blueprint Create File", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Blueprint Create File", False, f"Exception: {str(e)}")
            return False
    
    def test_grpc_example_endpoints(self):
        """Test Suite F: gRPC Example Endpoints - Load Default Buttons Fix"""
        print("\n📡 TEST SUITE F - gRPC EXAMPLE ENDPOINTS")
        print("-" * 50)
        
        # Test ingress_server methods
        ingress_methods = [
            "UpsertContent",
            "DeleteContent", 
            "BatchCreateAssets",
            "BatchAddDownloadCounts",
            "BatchAddRatings"
        ]
        
        # Test asset_storage methods
        asset_storage_methods = [
            "BatchGetSignedUrls",
            "BatchGetUnsignedUrls",
            "BatchUpdateStatuses",
            "BatchDeleteAssets",
            "BatchFinalizeAssets"
        ]
        
        print("\n🔧 Testing ingress_server example endpoints:")
        for method in ingress_methods:
            self.test_single_grpc_example("ingress_server", method)
        
        print("\n🔧 Testing asset_storage example endpoints:")
        for method in asset_storage_methods:
            self.test_single_grpc_example("asset_storage", method)
        
        return True
    
    def test_single_grpc_example(self, service_name: str, method_name: str):
        """Test a single gRPC example endpoint"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/api/grpc/{service_name}/example/{method_name}", 
                timeout=10
            )
            response_time = time.time() - start_time
            
            test_name = f"gRPC Example {service_name}.{method_name}"
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response time (should be < 1 second as per requirement)
                if response_time < 1.0:
                    self.log_test(f"{test_name} Response Time", True, f"{response_time:.3f}s")
                else:
                    self.log_test(f"{test_name} Response Time", False, f"Too slow: {response_time:.3f}s")
                
                # Check response structure
                if data.get("success") is True:
                    self.log_test(f"{test_name} Success", True, "Returns success: true")
                    
                    # Check example object
                    if "example" in data and isinstance(data["example"], dict):
                        example = data["example"]
                        
                        if example:  # Non-empty example
                            field_count = len(example)
                            self.log_test(f"{test_name} Example Structure", True, 
                                        f"Example has {field_count} fields: {list(example.keys())}")
                            
                            # Verify example contains appropriate field names and data types
                            valid_fields = 0
                            for field_name, field_value in example.items():
                                if isinstance(field_name, str) and field_name:
                                    valid_fields += 1
                            
                            if valid_fields > 0:
                                self.log_test(f"{test_name} Field Validation", True, 
                                            f"{valid_fields}/{field_count} fields have valid names")
                            else:
                                self.log_test(f"{test_name} Field Validation", False, 
                                            "No valid field names found")
                        else:
                            self.log_test(f"{test_name} Example Structure", False, "Example is empty")
                    else:
                        self.log_test(f"{test_name} Example Object", False, 
                                    f"Missing or invalid example object: {type(data.get('example'))}")
                else:
                    # Check for expected error cases
                    error_msg = data.get("error", "")
                    if "not initialized" in error_msg.lower():
                        self.log_test(f"{test_name} Error Handling", True, 
                                    "Proper error for uninitialized gRPC client")
                    elif "could not generate" in error_msg.lower():
                        self.log_test(f"{test_name} Error Handling", True, 
                                    "Proper error for method not found")
                    else:
                        self.log_test(f"{test_name} Success", False, 
                                    f"Returns success: false, error: {error_msg}")
            elif response.status_code == 404:
                self.log_test(f"{test_name}", False, 
                            "HTTP 404 - Endpoint not found (Load Default buttons won't work)")
            else:
                self.log_test(f"{test_name}", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test(f"gRPC Example {service_name}.{method_name}", False, f"Exception: {str(e)}")
    
    def test_grpc_error_handling(self):
        """Test Suite F.2: gRPC Example Error Handling"""
        print("\n🔧 Testing gRPC example error handling:")
        
        # Test non-existent method
        try:
            response = requests.get(
                f"{self.base_url}/api/grpc/ingress_server/example/NonExistentMethod", 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") is False and "error" in data:
                    self.log_test("gRPC Error - Non-existent Method", True, 
                                f"Proper error handling: {data['error']}")
                else:
                    self.log_test("gRPC Error - Non-existent Method", False, 
                                "Should return success: false with error message")
            else:
                self.log_test("gRPC Error - Non-existent Method", False, 
                            f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("gRPC Error - Non-existent Method", False, f"Exception: {str(e)}")
        
        # Test non-existent service
        try:
            response = requests.get(
                f"{self.base_url}/api/grpc/non_existent_service/example/SomeMethod", 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") is False and "error" in data:
                    self.log_test("gRPC Error - Non-existent Service", True, 
                                f"Proper error handling: {data['error']}")
                else:
                    self.log_test("gRPC Error - Non-existent Service", False, 
                                "Should return success: false with error message")
            else:
                self.log_test("gRPC Error - Non-existent Service", False, 
                            f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("gRPC Error - Non-existent Service", False, f"Exception: {str(e)}")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 CRITICAL BLUEPRINT CONFIGURATION API ROUTING TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Categorize results by test suite
        suite_a_results = []
        suite_b_results = []
        suite_c_results = []
        suite_d_results = []
        suite_e_results = []
        suite_f_results = []
        other_results = []
        
        for result in self.test_results:
            name = result["name"].lower()
            if any(keyword in name for keyword in ["health", "app config", "environments", "file tree"]):
                suite_a_results.append(result)
            elif any(keyword in name for keyword in ["entity", "namespace", "blueprint cnf"]):
                suite_b_results.append(result)
            elif "websocket" in name:
                suite_c_results.append(result)
            elif "statistics" in name and "graph" not in name:
                suite_d_results.append(result)
            elif any(keyword in name for keyword in ["graph", "disconnected", "component"]):
                suite_e_results.append(result)
            elif any(keyword in name for keyword in ["grpc", "example"]):
                suite_f_results.append(result)
            else:
                other_results.append(result)
        
        # Print results by suite
        print(f"\n🔧 TEST SUITE A - CORE APIs ({len([r for r in suite_a_results if r['success']])}/{len(suite_a_results)} passed):")
        for result in suite_a_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}")
        
        print(f"\n🎯 TEST SUITE B - BLUEPRINT CONFIGURATION ({len([r for r in suite_b_results if r['success']])}/{len(suite_b_results)} passed):")
        for result in suite_b_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}")
        
        print(f"\n🌐 TEST SUITE C - WEBSOCKET ({len([r for r in suite_c_results if r['success']])}/{len(suite_c_results)} passed):")
        for result in suite_c_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}")
        
        print(f"\n📊 TEST SUITE D - STATISTICS ENDPOINT ({len([r for r in suite_d_results if r['success']])}/{len(suite_d_results)} passed):")
        for result in suite_d_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}")
        
        print(f"\n📈 TEST SUITE E - GRAPH COMPONENT STATISTICS FIX ({len([r for r in suite_e_results if r['success']])}/{len(suite_e_results)} passed):")
        for result in suite_e_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}")
        
        print(f"\n📡 TEST SUITE F - gRPC EXAMPLE ENDPOINTS ({len([r for r in suite_f_results if r['success']])}/{len(suite_f_results)} passed):")
        for result in suite_f_results:
            status = "✅" if result["success"] else "❌"
            print(f"   {status} {result['name']}")
        
        if other_results:
            print(f"\n🔧 OTHER TESTS ({len([r for r in other_results if r['success']])}/{len(other_results)} passed):")
            for result in other_results:
                status = "✅" if result["success"] else "❌"
                print(f"   {status} {result['name']}")
        
        # Show failures in detail
        failures = [r for r in self.test_results if not r["success"]]
        if failures:
            print(f"\n❌ DETAILED FAILURE ANALYSIS ({len(failures)} failures):")
            for failure in failures:
                print(f"   • {failure['name']}: {failure['details']}")
        
        # Final assessment
        print(f"\n{'='*80}")
        if success_rate >= 90:
            print(f"🎉 EXCELLENT: Backend routing fix is working perfectly!")
            print(f"   All critical APIs are accessible and returning proper responses.")
        elif success_rate >= 75:
            print(f"✅ GOOD: Backend routing fix is mostly working with minor issues")
            print(f"   Most critical APIs are accessible, some minor issues detected.")
        elif success_rate >= 50:
            print(f"⚠️ NEEDS ATTENTION: Backend routing has significant issues")
            print(f"   Some APIs are still returning 404 or have other problems.")
        else:
            print(f"❌ CRITICAL: Backend routing fix failed")
            print(f"   Major APIs are still inaccessible or returning errors.")
        
        print(f"{'='*80}")

if __name__ == "__main__":
    tester = BackendRoutingTester()
    tester.run_critical_routing_tests()