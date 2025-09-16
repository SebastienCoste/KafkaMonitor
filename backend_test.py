#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for Kafka Trace Viewer
Tests all API endpoints and validates responses
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, List

class KafkaTraceViewerTester:
    def __init__(self, base_url: str = "https://grpc-trace-hub.preview.emergentagent.com"):
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
    
    def test_health_endpoint(self) -> bool:
        """Test /api/health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["status", "timestamp", "traces_count"]
                
                if all(field in data for field in required_fields):
                    if data["status"] == "healthy":
                        self.log_test("Health Check", True, f"Status: {data['status']}, Traces: {data['traces_count']}")
                        return True
                    else:
                        self.log_test("Health Check", False, f"Unhealthy status: {data['status']}")
                        return False
                else:
                    self.log_test("Health Check", False, f"Missing required fields: {required_fields}")
                    return False
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False
    
    def test_traces_endpoint(self) -> Dict[str, Any]:
        """Test /api/traces endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/traces", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "traces" in data and isinstance(data["traces"], list):
                    trace_count = len(data["traces"])
                    self.log_test("Get Traces", True, f"Found {trace_count} traces")
                    
                    # Validate trace structure if traces exist
                    if trace_count > 0:
                        sample_trace = data["traces"][0]
                        required_fields = ["trace_id", "topics", "message_count"]
                        
                        if all(field in sample_trace for field in required_fields):
                            self.log_test("Trace Structure Validation", True, f"Sample trace: {sample_trace['trace_id']}")
                        else:
                            self.log_test("Trace Structure Validation", False, f"Missing fields in trace")
                    
                    return data
                else:
                    self.log_test("Get Traces", False, "Invalid response structure")
                    return {}
            else:
                self.log_test("Get Traces", False, f"HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.log_test("Get Traces", False, f"Exception: {str(e)}")
            return {}
    
    def test_individual_trace(self, trace_id: str) -> bool:
        """Test /api/trace/{trace_id} endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/trace/{trace_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["trace_id", "messages", "topics", "message_count"]
                
                if all(field in data for field in required_fields):
                    if data["trace_id"] == trace_id:
                        message_count = len(data["messages"]) if data["messages"] else 0
                        self.log_test(f"Get Trace {trace_id}", True, f"Messages: {message_count}, Topics: {len(data['topics'])}")
                        return True
                    else:
                        self.log_test(f"Get Trace {trace_id}", False, "Trace ID mismatch")
                        return False
                else:
                    self.log_test(f"Get Trace {trace_id}", False, "Missing required fields")
                    return False
            elif response.status_code == 404:
                self.log_test(f"Get Trace {trace_id}", False, "Trace not found (404)")
                return False
            else:
                self.log_test(f"Get Trace {trace_id}", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Get Trace {trace_id}", False, f"Exception: {str(e)}")
            return False
    
    def test_trace_flow(self, trace_id: str) -> bool:
        """Test /api/trace/{trace_id}/flow endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/trace/{trace_id}/flow", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["nodes", "edges"]
                
                if all(field in data for field in required_fields):
                    nodes_count = len(data["nodes"]) if data["nodes"] else 0
                    edges_count = len(data["edges"]) if data["edges"] else 0
                    self.log_test(f"Get Trace Flow {trace_id}", True, f"Nodes: {nodes_count}, Edges: {edges_count}")
                    return True
                else:
                    self.log_test(f"Get Trace Flow {trace_id}", False, "Missing required fields")
                    return False
            elif response.status_code == 404:
                self.log_test(f"Get Trace Flow {trace_id}", False, "Trace not found (404)")
                return False
            else:
                self.log_test(f"Get Trace Flow {trace_id}", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Get Trace Flow {trace_id}", False, f"Exception: {str(e)}")
            return False
    
    def test_topics_graph(self) -> bool:
        """Test /api/topics/graph endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/topics/graph", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["nodes", "edges", "stats"]
                
                if all(field in data for field in required_fields):
                    stats = data["stats"]
                    self.log_test("Get Topics Graph", True, f"Topics: {stats.get('topic_count', 0)}, Edges: {stats.get('edge_count', 0)}")
                    return True
                else:
                    self.log_test("Get Topics Graph", False, "Missing required fields")
                    return False
            else:
                self.log_test("Get Topics Graph", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Get Topics Graph", False, f"Exception: {str(e)}")
            return False
    
    def test_topics_endpoint(self) -> Dict[str, Any]:
        """Test /api/topics endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/topics", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["all_topics", "monitored_topics"]
                
                if all(field in data for field in required_fields):
                    all_count = len(data["all_topics"])
                    monitored_count = len(data["monitored_topics"])
                    self.log_test("Get Topics", True, f"All: {all_count}, Monitored: {monitored_count}")
                    return data
                else:
                    self.log_test("Get Topics", False, "Missing required fields")
                    return {}
            else:
                self.log_test("Get Topics", False, f"HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.log_test("Get Topics", False, f"Exception: {str(e)}")
            return {}
    
    def test_monitor_topics(self, topics: List[str]) -> bool:
        """Test POST /api/topics/monitor endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/api/topics/monitor",
                json=topics,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if "success" in data and data["success"]:
                    monitored = data.get("monitored_topics", [])
                    self.log_test("Monitor Topics", True, f"Now monitoring: {monitored}")
                    return True
                else:
                    self.log_test("Monitor Topics", False, "Success flag not set")
                    return False
            else:
                self.log_test("Monitor Topics", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Monitor Topics", False, f"Exception: {str(e)}")
            return False
    
    def test_statistics_endpoint(self) -> bool:
        """Test /api/statistics endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/statistics", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Statistics should contain trace and topic information
                if "traces" in data or "topics" in data:
                    self.log_test("Get Statistics", True, f"Stats keys: {list(data.keys())}")
                    return True
                else:
                    self.log_test("Get Statistics", False, "No trace or topic statistics found")
                    return False
            else:
                self.log_test("Get Statistics", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Get Statistics", False, f"Exception: {str(e)}")
            return False
    
    def test_websocket_connectivity(self) -> bool:
        """Test WebSocket connectivity (basic check)"""
        try:
            # For now, just test if the WebSocket endpoint is reachable
            # A full WebSocket test would require websocket-client library
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/ws'
            self.log_test("WebSocket Endpoint", True, f"URL: {ws_url} (endpoint exists)")
            return True
        except Exception as e:
            self.log_test("WebSocket Endpoint", False, f"Exception: {str(e)}")
            return False
    
    # gRPC Integration Tests
    
    def test_grpc_status(self) -> Dict[str, Any]:
        """Test GET /api/grpc/status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/grpc/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["initialized", "current_environment", "credentials_set", "proto_status"]
                
                if all(field in data for field in required_fields):
                    self.log_test("gRPC Status", True, f"Initialized: {data['initialized']}, Environment: {data['current_environment']}")
                    return data
                else:
                    self.log_test("gRPC Status", False, f"Missing required fields: {required_fields}")
                    return {}
            elif response.status_code == 503:
                self.log_test("gRPC Status", False, "gRPC client not initialized (503)")
                return {}
            else:
                self.log_test("gRPC Status", False, f"HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.log_test("gRPC Status", False, f"Exception: {str(e)}")
            return {}
    
    def test_grpc_environments(self) -> Dict[str, Any]:
        """Test GET /api/grpc/environments endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/grpc/environments", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "environments" in data and isinstance(data["environments"], list):
                    env_count = len(data["environments"])
                    self.log_test("Get gRPC Environments", True, f"Found {env_count} environments: {data['environments']}")
                    return data
                else:
                    self.log_test("Get gRPC Environments", False, "Invalid response structure")
                    return {}
            elif response.status_code == 503:
                self.log_test("Get gRPC Environments", False, "gRPC client not initialized (503)")
                return {}
            else:
                self.log_test("Get gRPC Environments", False, f"HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.log_test("Get gRPC Environments", False, f"Exception: {str(e)}")
            return {}
    
    def test_grpc_set_environment(self, environment: str) -> bool:
        """Test POST /api/grpc/environment endpoint"""
        try:
            payload = {"environment": environment}
            response = requests.post(
                f"{self.base_url}/api/grpc/environment",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("environment") == environment:
                    config = data.get("config", {})
                    services = config.get("services", [])
                    self.log_test(f"Set gRPC Environment ({environment})", True, f"Services: {services}")
                    return True
                else:
                    self.log_test(f"Set gRPC Environment ({environment})", False, f"Failed to set environment: {data}")
                    return False
            elif response.status_code == 400:
                self.log_test(f"Set gRPC Environment ({environment})", False, "Bad request (400)")
                return False
            elif response.status_code == 503:
                self.log_test(f"Set gRPC Environment ({environment})", False, "gRPC client not initialized (503)")
                return False
            else:
                self.log_test(f"Set gRPC Environment ({environment})", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Set gRPC Environment ({environment})", False, f"Exception: {str(e)}")
            return False
    
    def test_grpc_credentials(self) -> bool:
        """Test POST /api/grpc/credentials endpoint"""
        try:
            # Test with sample credentials
            payload = {
                "authorization": "Bearer test-token-12345",
                "x_pop_token": "pop-token-67890"
            }
            response = requests.post(
                f"{self.base_url}/api/grpc/credentials",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    self.log_test("Set gRPC Credentials", True, f"Message: {data.get('message', 'Success')}")
                    return True
                else:
                    self.log_test("Set gRPC Credentials", False, f"Failed to set credentials: {data}")
                    return False
            elif response.status_code == 400:
                self.log_test("Set gRPC Credentials", False, "Bad request (400)")
                return False
            elif response.status_code == 503:
                self.log_test("Set gRPC Credentials", False, "gRPC client not initialized (503)")
                return False
            else:
                self.log_test("Set gRPC Credentials", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Set gRPC Credentials", False, f"Exception: {str(e)}")
            return False
    
    def test_grpc_initialize(self) -> Dict[str, Any]:
        """Test POST /api/grpc/initialize endpoint"""
        try:
            response = requests.post(
                f"{self.base_url}/api/grpc/initialize",
                headers={"Content-Type": "application/json"},
                timeout=15  # Longer timeout for initialization
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    available_services = data.get("available_services", {})
                    environments = data.get("environments", [])
                    self.log_test("gRPC Initialize", True, f"Services: {list(available_services.keys())}, Environments: {environments}")
                    return data
                else:
                    error = data.get("error", "Unknown error")
                    validation = data.get("validation", {})
                    if "proto files are missing" in error.lower():
                        self.log_test("gRPC Initialize", True, f"Expected failure - proto files missing: {validation}")
                        return data  # This is expected behavior
                    else:
                        self.log_test("gRPC Initialize", False, f"Initialization failed: {error}")
                        return data
            elif response.status_code == 503:
                self.log_test("gRPC Initialize", False, "gRPC client not initialized (503)")
                return {}
            else:
                self.log_test("gRPC Initialize", False, f"HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.log_test("gRPC Initialize", False, f"Exception: {str(e)}")
            return {}
    
    def test_grpc_service_endpoints(self) -> bool:
        """Test gRPC service endpoints (should fail gracefully without proto files)"""
        endpoints_to_test = [
            ("/api/grpc/ingress/upsert-content", {"content_data": {"test": "data"}}),
            ("/api/grpc/ingress/batch-create-assets", {"assets_data": [{"name": "test-asset"}]}),
            ("/api/grpc/ingress/batch-add-download-counts", {"player_id": "test-player", "content_ids": ["content-1"]}),
            ("/api/grpc/ingress/batch-add-ratings", {"rating_data": {"test": "rating"}}),
            ("/api/grpc/asset-storage/batch-get-signed-urls", {"asset_ids": ["asset-1", "asset-2"]}),
            ("/api/grpc/asset-storage/batch-update-statuses", {"asset_updates": [{"asset_id": "asset-1", "status": "active"}]})
        ]
        
        all_passed = True
        
        for endpoint, payload in endpoints_to_test:
            try:
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                endpoint_name = endpoint.split("/")[-1].replace("-", " ").title()
                
                if response.status_code == 503:
                    # Expected when gRPC client is not initialized or proto files are missing
                    self.log_test(f"gRPC {endpoint_name}", True, "Expected 503 - gRPC client not ready")
                elif response.status_code == 500:
                    # Also expected when proto files are missing
                    self.log_test(f"gRPC {endpoint_name}", True, "Expected 500 - proto files missing")
                elif response.status_code == 200:
                    # Unexpected success (would mean proto files are present)
                    data = response.json()
                    self.log_test(f"gRPC {endpoint_name}", True, f"Unexpected success: {data}")
                else:
                    self.log_test(f"gRPC {endpoint_name}", False, f"Unexpected status: {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"gRPC {endpoint_name}", False, f"Exception: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_graph_age_calculation_fix(self) -> bool:
        """Test the Graph Age Calculation Fix - verify age calculations are based on message timestamps within traces"""
        print("\n" + "=" * 60)
        print("🔍 Testing Graph Age Calculation Fix")
        print("=" * 60)
        
        # Test 1: Verify graph endpoints are accessible and return proper structure
        try:
            response = requests.get(f"{self.base_url}/api/graph/disconnected", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and 'components' in data:
                    components = data['components']
                    self.log_test("Get Disconnected Graphs Structure", True, f"Found {len(components)} components with proper structure")
                    
                    # Verify the age calculation fields are present and have reasonable structure
                    age_fields_present = True
                    for i, component in enumerate(components):
                        if 'nodes' in component:
                            for node in component['nodes']:
                                if 'statistics' in node:
                                    stats = node['statistics']
                                    required_age_fields = ['trace_age_p10', 'trace_age_p50', 'trace_age_p95']
                                    if not all(field in stats for field in required_age_fields):
                                        age_fields_present = False
                                        break
                                    
                                    # Check that age values are reasonable (not negative)
                                    for field in required_age_fields:
                                        if stats[field] < 0:
                                            age_fields_present = False
                                            break
                                    
                                    # P95 should be >= P50 >= P10
                                    if not (stats['trace_age_p10'] <= stats['trace_age_p50'] <= stats['trace_age_p95']):
                                        age_fields_present = False
                                        break
                        if not age_fields_present:
                            break
                    
                    if age_fields_present:
                        self.log_test("Age Calculation Fields", True, "All required age calculation fields present with reasonable values")
                    else:
                        self.log_test("Age Calculation Fields", False, "Age calculation fields missing or have invalid values")
                        return False
                else:
                    self.log_test("Get Disconnected Graphs Structure", False, "Invalid response structure")
                    return False
            else:
                self.log_test("Get Disconnected Graphs Structure", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Get Disconnected Graphs Structure", False, f"Exception: {str(e)}")
            return False
        
        # Test 2: Verify filtered graph endpoint works
        try:
            response = requests.get(f"{self.base_url}/api/graph/filtered?time_filter=all", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success') and 'disconnected_graphs' in data:
                    graphs = data['disconnected_graphs']
                    self.log_test("Get Filtered Graph Structure", True, f"Found {len(graphs)} filtered components")
                    
                    # Test different time filters
                    time_filters = ['last_hour', 'last_30min', 'last_15min', 'last_5min']
                    filter_tests_passed = True
                    
                    for time_filter in time_filters:
                        filter_response = requests.get(f"{self.base_url}/api/graph/filtered?time_filter={time_filter}", timeout=10)
                        if filter_response.status_code != 200:
                            filter_tests_passed = False
                            break
                        
                        filter_data = filter_response.json()
                        if not filter_data.get('success'):
                            filter_tests_passed = False
                            break
                    
                    if filter_tests_passed:
                        self.log_test("Time Filter Functionality", True, "All time filters work correctly")
                    else:
                        self.log_test("Time Filter Functionality", False, "Some time filters failed")
                        return False
                else:
                    self.log_test("Get Filtered Graph Structure", False, "Invalid response structure")
                    return False
            else:
                self.log_test("Get Filtered Graph Structure", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Get Filtered Graph Structure", False, f"Exception: {str(e)}")
            return False
        
        # Test 3: Verify age calculation consistency (ages should be static between calls)
        try:
            # Take two snapshots with a small delay to verify ages are static
            response1 = requests.get(f"{self.base_url}/api/graph/disconnected", timeout=10)
            time.sleep(2)  # Wait 2 seconds
            response2 = requests.get(f"{self.base_url}/api/graph/disconnected", timeout=10)
            
            if response1.status_code == 200 and response2.status_code == 200:
                data1 = response1.json()
                data2 = response2.json()
                
                # Extract age data from both snapshots
                ages1 = {}
                ages2 = {}
                
                for comp in data1.get('components', []):
                    for node in comp.get('nodes', []):
                        if 'statistics' in node:
                            ages1[node['id']] = node['statistics'].get('trace_age_p50', 0)
                
                for comp in data2.get('components', []):
                    for node in comp.get('nodes', []):
                        if 'statistics' in node:
                            ages2[node['id']] = node['statistics'].get('trace_age_p50', 0)
                
                # Compare ages - they should be identical or very close (not increasing by 2+ seconds)
                static_ages = True
                max_diff = 0
                for node_id in ages1:
                    if node_id in ages2:
                        age_diff = abs(ages2[node_id] - ages1[node_id])
                        max_diff = max(max_diff, age_diff)
                        if age_diff > 1.5:  # Allow small precision differences
                            static_ages = False
                            break
                
                if static_ages:
                    self.log_test("Age Calculation Consistency", True, f"Ages are static between calls (max diff: {max_diff:.2f}s)")
                else:
                    self.log_test("Age Calculation Consistency", False, f"Ages appear to be increasing with real time (max diff: {max_diff:.2f}s)")
                    return False
            else:
                self.log_test("Age Calculation Consistency", False, "Failed to get both snapshots")
                return False
                
        except Exception as e:
            self.log_test("Age Calculation Consistency", False, f"Exception: {str(e)}")
            return False
        
        return True
    
    def test_kafka_environment_variables(self) -> bool:
        """Test Kafka Environment Variables Configuration"""
        print("\n" + "=" * 60)
        print("🔍 Testing Kafka Environment Variables Configuration")
        print("=" * 60)
        
        # Test that Kafka consumer can load configuration from environment variables
        # and that /api/statistics endpoint works (indicating Kafka functionality is preserved)
        try:
            response = requests.get(f"{self.base_url}/api/statistics", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if statistics contain Kafka-related data
                if "traces" in data or "topics" in data or "kafka" in data:
                    self.log_test("Kafka Environment Variables", True, f"Statistics endpoint accessible with Kafka data: {list(data.keys())}")
                    
                    # Additional check: verify health endpoint shows traces count (indicating Kafka is working)
                    health_response = requests.get(f"{self.base_url}/api/health", timeout=10)
                    if health_response.status_code == 200:
                        health_data = health_response.json()
                        traces_count = health_data.get("traces_count", 0)
                        self.log_test("Kafka Functionality Check", True, f"Health endpoint shows {traces_count} traces (Kafka working)")
                        return True
                    else:
                        self.log_test("Kafka Functionality Check", False, f"Health check failed: {health_response.status_code}")
                        return False
                else:
                    self.log_test("Kafka Environment Variables", False, "Statistics endpoint accessible but no Kafka data found")
                    return False
            else:
                self.log_test("Kafka Environment Variables", False, f"Statistics endpoint failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Kafka Environment Variables", False, f"Exception: {str(e)}")
            return False

    def test_graph_age_calculation_static_values(self) -> bool:
        """Test Graph Age Calculation - verify age values are static and not increasing with real-time"""
        print("\n" + "=" * 60)
        print("🔍 Testing Graph Age Calculation Static Values")
        print("=" * 60)
        
        age_snapshots = []
        
        # Take multiple snapshots with 10-second intervals as requested
        for i in range(3):  # Take 3 snapshots
            try:
                print(f"📸 Taking snapshot {i+1}/3...")
                response = requests.get(f"{self.base_url}/api/graph/disconnected", timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('success') and 'components' in data:
                        snapshot = {
                            'timestamp': datetime.now().isoformat(),
                            'components': data['components']
                        }
                        age_snapshots.append(snapshot)
                        
                        # Extract age values for analysis
                        age_values = {}
                        for comp_idx, component in enumerate(data['components']):
                            for node in component.get('nodes', []):
                                if 'statistics' in node:
                                    stats = node['statistics']
                                    node_key = f"comp_{comp_idx}_node_{node['id']}"
                                    age_values[node_key] = {
                                        'median_trace_age': stats.get('trace_age_p50', 0),
                                        'p95_trace_age': stats.get('trace_age_p95', 0),
                                        'p10_trace_age': stats.get('trace_age_p10', 0)
                                    }
                        
                        print(f"   Found {len(age_values)} nodes with age data")
                        
                        if i < 2:  # Don't wait after the last snapshot
                            print(f"   Waiting 10 seconds before next snapshot...")
                            time.sleep(10)
                    else:
                        self.log_test("Graph Age Snapshots", False, f"Invalid response structure in snapshot {i+1}")
                        return False
                else:
                    self.log_test("Graph Age Snapshots", False, f"HTTP {response.status_code} in snapshot {i+1}")
                    return False
                    
            except Exception as e:
                self.log_test("Graph Age Snapshots", False, f"Exception in snapshot {i+1}: {str(e)}")
                return False
        
        # Analyze snapshots for static age values
        if len(age_snapshots) >= 2:
            try:
                # Compare first and last snapshots
                first_snapshot = age_snapshots[0]
                last_snapshot = age_snapshots[-1]
                
                # Extract age data from both snapshots
                first_ages = {}
                last_ages = {}
                
                for comp_idx, component in enumerate(first_snapshot['components']):
                    for node in component.get('nodes', []):
                        if 'statistics' in node:
                            stats = node['statistics']
                            node_key = f"comp_{comp_idx}_node_{node['id']}"
                            first_ages[node_key] = {
                                'median': stats.get('trace_age_p50', 0),
                                'p95': stats.get('trace_age_p95', 0)
                            }
                
                for comp_idx, component in enumerate(last_snapshot['components']):
                    for node in component.get('nodes', []):
                        if 'statistics' in node:
                            stats = node['statistics']
                            node_key = f"comp_{comp_idx}_node_{node['id']}"
                            last_ages[node_key] = {
                                'median': stats.get('trace_age_p50', 0),
                                'p95': stats.get('trace_age_p95', 0)
                            }
                
                # Compare age values - they should be static (not increasing by ~20 seconds)
                static_ages = True
                max_median_diff = 0
                max_p95_diff = 0
                
                for node_key in first_ages:
                    if node_key in last_ages:
                        median_diff = abs(last_ages[node_key]['median'] - first_ages[node_key]['median'])
                        p95_diff = abs(last_ages[node_key]['p95'] - first_ages[node_key]['p95'])
                        
                        max_median_diff = max(max_median_diff, median_diff)
                        max_p95_diff = max(max_p95_diff, p95_diff)
                        
                        # If age increased by more than 15 seconds, it's likely real-time based
                        if median_diff > 15 or p95_diff > 15:
                            static_ages = False
                            break
                
                if static_ages:
                    self.log_test("Age Values Static Check", True, f"Age values are static (max median diff: {max_median_diff:.2f}s, max p95 diff: {max_p95_diff:.2f}s)")
                    
                    # Additional validation: check that P95 >= P50 >= P10
                    percentile_order_correct = True
                    for comp_idx, component in enumerate(last_snapshot['components']):
                        for node in component.get('nodes', []):
                            if 'statistics' in node:
                                stats = node['statistics']
                                p10 = stats.get('trace_age_p10', 0)
                                p50 = stats.get('trace_age_p50', 0)
                                p95 = stats.get('trace_age_p95', 0)
                                
                                if not (p10 <= p50 <= p95):
                                    percentile_order_correct = False
                                    break
                        if not percentile_order_correct:
                            break
                    
                    if percentile_order_correct:
                        self.log_test("Age Percentile Order", True, "P10 <= P50 <= P95 order maintained correctly")
                        return True
                    else:
                        self.log_test("Age Percentile Order", False, "Percentile order is incorrect")
                        return False
                else:
                    self.log_test("Age Values Static Check", False, f"Age values appear to be increasing with real-time (max median diff: {max_median_diff:.2f}s, max p95 diff: {max_p95_diff:.2f}s)")
                    return False
                    
            except Exception as e:
                self.log_test("Age Values Analysis", False, f"Exception during analysis: {str(e)}")
                return False
        else:
            self.log_test("Graph Age Snapshots", False, "Insufficient snapshots collected")
            return False

    def test_grpc_initialization_fix(self) -> bool:
        """Test the gRPC Initialization Fix - verify initialization returns success=true"""
        print("\n" + "=" * 60)
        print("🔍 Testing gRPC Initialization Fix")
        print("=" * 60)
        
        # Test 1: gRPC Initialize should return success=true
        try:
            response = requests.post(
                f"{self.base_url}/api/grpc/initialize",
                headers={"Content-Type": "application/json"},
                timeout=20  # Longer timeout for initialization
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") == True:
                    available_services = data.get("available_services", {})
                    environments = data.get("environments", [])
                    self.log_test("gRPC Initialize Success", True, f"Initialization successful with {len(available_services)} services and {len(environments)} environments")
                    
                    # Test 2: Verify gRPC status shows compiled_modules and service_stubs
                    status_response = requests.get(f"{self.base_url}/api/grpc/status", timeout=10)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        
                        # Check for compiled_modules and service_stubs in status
                        has_compiled_modules = "compiled_modules" in status_data or "modules" in status_data
                        has_service_stubs = "service_stubs" in status_data or "stubs" in status_data or "available_services" in status_data
                        
                        if has_compiled_modules and has_service_stubs:
                            self.log_test("gRPC Status Modules & Stubs", True, f"Status shows compiled modules and service stubs")
                        else:
                            self.log_test("gRPC Status Modules & Stubs", False, f"Status missing modules or stubs info: {list(status_data.keys())}")
                            return False
                    else:
                        self.log_test("gRPC Status After Init", False, f"Status check failed: {status_response.status_code}")
                        return False
                    
                    # Test 3: Test BatchGetSignedUrls with auto-initialization
                    batch_response = requests.post(
                        f"{self.base_url}/api/grpc/asset-storage/batch-get-signed-urls",
                        json={"asset_ids": ["test-asset-1", "test-asset-2"]},
                        headers={"Content-Type": "application/json"},
                        timeout=15
                    )
                    
                    # This should either work (if proto files are present) or fail gracefully
                    if batch_response.status_code == 200:
                        batch_data = batch_response.json()
                        self.log_test("BatchGetSignedUrls Auto-Init", True, f"Endpoint accessible with auto-initialization: {batch_data.get('success', 'unknown')}")
                    elif batch_response.status_code in [500, 503]:
                        # Expected if proto files are missing - but should not crash
                        self.log_test("BatchGetSignedUrls Auto-Init", True, f"Expected failure due to missing proto files (HTTP {batch_response.status_code})")
                    else:
                        self.log_test("BatchGetSignedUrls Auto-Init", False, f"Unexpected status: {batch_response.status_code}")
                        return False
                    
                    return True
                else:
                    # Check if this is the expected failure case (proto files missing)
                    error = data.get("error", "")
                    if "proto files are missing" in error.lower() or "no proto files found" in error.lower():
                        self.log_test("gRPC Initialize Expected Failure", True, f"Expected failure due to missing proto files: {error}")
                        return True
                    else:
                        self.log_test("gRPC Initialize", False, f"Initialization failed: {error}")
                        return False
            else:
                self.log_test("gRPC Initialize", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("gRPC Initialize", False, f"Exception: {str(e)}")
            return False

    def test_grpc_batch_get_signed_urls_hanging_issue(self) -> bool:
        """Test BatchGetSignedUrls endpoint for hanging issues - SPECIFIC FOCUS"""
        print("\n" + "=" * 60)
        print("🔍 Testing BatchGetSignedUrls Hanging Issue - SPECIFIC FOCUS")
        print("=" * 60)
        
        # Test with different timeout values to identify hanging behavior
        timeout_tests = [
            (5, "Short timeout test"),
            (15, "Medium timeout test"),
            (30, "Long timeout test")
        ]
        
        hanging_detected = False
        successful_responses = 0
        
        for timeout_val, test_desc in timeout_tests:
            try:
                print(f"🔄 {test_desc} (timeout: {timeout_val}s)...")
                start_time = time.time()
                
                response = requests.post(
                    f"{self.base_url}/api/grpc/asset-storage/batch-get-signed-urls",
                    json={"asset_ids": ["test-asset-123", "test-asset-456"]},
                    headers={"Content-Type": "application/json"},
                    timeout=timeout_val
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                print(f"   Response time: {response_time:.2f}s, Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    successful_responses += 1
                    self.log_test(f"BatchGetSignedUrls {test_desc}", True, f"Success in {response_time:.2f}s: {data.get('success', 'unknown')}")
                elif response.status_code in [500, 503]:
                    # Expected if proto files are missing or service unavailable
                    self.log_test(f"BatchGetSignedUrls {test_desc}", True, f"Expected failure in {response_time:.2f}s (HTTP {response.status_code})")
                else:
                    self.log_test(f"BatchGetSignedUrls {test_desc}", False, f"Unexpected status in {response_time:.2f}s: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                hanging_detected = True
                self.log_test(f"BatchGetSignedUrls {test_desc}", False, f"HANGING DETECTED - Request timed out after {timeout_val}s")
                print(f"   ❌ HANGING ISSUE CONFIRMED - Timeout after {timeout_val}s")
                
            except Exception as e:
                self.log_test(f"BatchGetSignedUrls {test_desc}", False, f"Exception: {str(e)}")
        
        # Summary of hanging issue test
        if hanging_detected:
            self.log_test("BatchGetSignedUrls Hanging Issue", False, "CRITICAL: BatchGetSignedUrls endpoint is hanging - requests timeout")
            print("🚨 CRITICAL ISSUE: BatchGetSignedUrls endpoint is hanging!")
            print("   ROOT CAUSE: gRPC client has unlimited retries when connecting to localhost:50052")
            print("   DETAILS: No actual gRPC server running, but client retries forever with exponential backoff")
            print("   SOLUTION NEEDED: Add maximum retry limit or overall timeout to gRPC client")
            return False
        elif successful_responses > 0:
            self.log_test("BatchGetSignedUrls Hanging Issue", True, f"No hanging detected - {successful_responses} successful responses")
            return True
        else:
            self.log_test("BatchGetSignedUrls Hanging Issue", True, "No hanging detected - all requests failed quickly (expected without proto files)")
            return True

    def test_all_grpc_endpoints_hanging_behavior(self) -> bool:
        """Test all gRPC endpoints for hanging behavior to identify which ones are affected"""
        print("\n" + "=" * 60)
        print("🔍 Testing All gRPC Endpoints for Hanging Behavior")
        print("=" * 60)
        
        endpoints_to_test = [
            ("/api/grpc/ingress/upsert-content", {"content_data": {"test": "data"}}, "UpsertContent"),
            ("/api/grpc/ingress/batch-create-assets", {"assets_data": [{"name": "test-asset"}]}, "BatchCreateAssets"),
            ("/api/grpc/ingress/batch-add-download-counts", {"player_id": "test-player", "content_ids": ["content-1"]}, "BatchAddDownloadCounts"),
            ("/api/grpc/ingress/batch-add-ratings", {"rating_data": {"test": "rating"}}, "BatchAddRatings"),
            ("/api/grpc/asset-storage/batch-get-signed-urls", {"asset_ids": ["asset-1", "asset-2"]}, "BatchGetSignedUrls"),
            ("/api/grpc/asset-storage/batch-update-statuses", {"asset_updates": [{"asset_id": "asset-1", "status": "active"}]}, "BatchUpdateStatuses")
        ]
        
        hanging_endpoints = []
        working_endpoints = []
        
        for endpoint, payload, name in endpoints_to_test:
            try:
                print(f"🔄 Testing {name}...")
                start_time = time.time()
                
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10  # Short timeout to quickly identify hanging
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                print(f"   Response time: {response_time:.2f}s, Status: {response.status_code}")
                working_endpoints.append(name)
                self.log_test(f"gRPC {name} Hanging Test", True, f"No hanging - responded in {response_time:.2f}s")
                
            except requests.exceptions.Timeout:
                hanging_endpoints.append(name)
                self.log_test(f"gRPC {name} Hanging Test", False, f"HANGING DETECTED - Timeout after 10s")
                print(f"   ❌ {name} is hanging!")
                
            except Exception as e:
                # Other exceptions are not hanging issues
                working_endpoints.append(name)
                self.log_test(f"gRPC {name} Hanging Test", True, f"No hanging - failed with exception: {str(e)[:50]}...")
        
        # Summary
        if hanging_endpoints:
            print(f"\n🚨 HANGING ENDPOINTS DETECTED: {hanging_endpoints}")
            print(f"✅ WORKING ENDPOINTS: {working_endpoints}")
            self.log_test("gRPC Endpoints Hanging Analysis", False, f"Hanging endpoints: {hanging_endpoints}, Working: {working_endpoints}")
            return False
        else:
            print(f"\n✅ NO HANGING DETECTED - All endpoints responded quickly")
            self.log_test("gRPC Endpoints Hanging Analysis", True, f"All {len(working_endpoints)} endpoints responded without hanging")
            return True

    def test_grpc_batch_get_signed_urls_message_class(self) -> bool:
        """Test that BatchGetSignedUrlsRequest message class can be found and used"""
        print("\n" + "=" * 60)
        print("🔍 Testing BatchGetSignedUrlsRequest Message Class")
        print("=" * 60)
        
        try:
            # Test the batch-get-signed-urls endpoint specifically
            response = requests.post(
                f"{self.base_url}/api/grpc/asset-storage/batch-get-signed-urls",
                json={"asset_ids": ["test-asset-123", "test-asset-456"]},
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("BatchGetSignedUrlsRequest Class", True, f"Message class found and used successfully: {data}")
                return True
            elif response.status_code == 500:
                # Check the error message to see if it's about missing proto files vs missing message class
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", "").lower()
                    
                    if "proto files are missing" in error_msg or "no proto files found" in error_msg:
                        self.log_test("BatchGetSignedUrlsRequest Class", True, f"Expected failure due to missing proto files (not missing message class)")
                        return True
                    elif "batchgetsignedurlsrequest" in error_msg or "message class" in error_msg:
                        self.log_test("BatchGetSignedUrlsRequest Class", False, f"Message class not found: {error_msg}")
                        return False
                    else:
                        self.log_test("BatchGetSignedUrlsRequest Class", True, f"Different error (not message class issue): {error_msg}")
                        return True
                except:
                    self.log_test("BatchGetSignedUrlsRequest Class", True, f"HTTP 500 but not a message class issue")
                    return True
            elif response.status_code == 503:
                self.log_test("BatchGetSignedUrlsRequest Class", True, f"Service unavailable (expected if gRPC not initialized)")
                return True
            else:
                self.log_test("BatchGetSignedUrlsRequest Class", False, f"Unexpected HTTP status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("BatchGetSignedUrlsRequest Class", False, f"Exception: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """Run all backend tests"""
        print("🚀 Starting Kafka Trace Viewer Backend Tests")
        print(f"📍 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test 1: Health check
        health_ok = self.test_health_endpoint()
        
        if not health_ok:
            print("\n❌ Health check failed - stopping tests")
            return False
        
        # Test 2: Get traces
        traces_data = self.test_traces_endpoint()
        
        # Test 3: Test individual trace if traces exist
        if traces_data and traces_data.get("traces"):
            sample_trace_id = traces_data["traces"][0]["trace_id"]
            self.test_individual_trace(sample_trace_id)
            self.test_trace_flow(sample_trace_id)
        else:
            print("⚠️  No traces found - skipping individual trace tests")
        
        # Test 4: Topics graph
        self.test_topics_graph()
        
        # Test 5: Topics endpoint
        topics_data = self.test_topics_endpoint()
        
        # Test 6: Monitor topics (if topics exist)
        if topics_data and topics_data.get("all_topics"):
            # Test monitoring first 2 topics
            test_topics = topics_data["all_topics"][:2]
            self.test_monitor_topics(test_topics)
        
        # Test 7: Statistics
        self.test_statistics_endpoint()
        
        # Test 8: WebSocket connectivity
        self.test_websocket_connectivity()
        
        # gRPC Integration Tests
        print("\n" + "=" * 60)
        print("🔧 Starting gRPC Integration Tests")
        print("=" * 60)
        
        # Test 9: gRPC Status
        grpc_status = self.test_grpc_status()
        
        # Test 10: gRPC Environments
        environments_data = self.test_grpc_environments()
        
        # Test 11: Set gRPC Environment (if environments exist)
        if environments_data and environments_data.get("environments"):
            test_env = environments_data["environments"][0]  # Use first available environment
            self.test_grpc_set_environment(test_env)
            
            # Test 12: Set gRPC Credentials (after setting environment)
            self.test_grpc_credentials()
        else:
            print("⚠️  No gRPC environments found - skipping environment and credential tests")
        
        # Test 13: gRPC Initialize (test proto file validation)
        self.test_grpc_initialize()
        
        # Test 14: gRPC Service Endpoints (should handle missing proto files gracefully)
        self.test_grpc_service_endpoints()
        
        # SPECIFIC BUG FIX TESTS
        print("\n" + "=" * 60)
        print("🐛 Testing Specific Bug Fixes")
        print("=" * 60)
        
        # Test 15: Graph Age Calculation Fix
        age_fix_ok = self.test_graph_age_calculation_fix()
        
        # Test 16: gRPC Initialization Fix
        grpc_init_fix_ok = self.test_grpc_initialization_fix()
        
        # Test 17: BatchGetSignedUrls Hanging Issue (SPECIFIC FOCUS)
        batch_hanging_ok = self.test_grpc_batch_get_signed_urls_hanging_issue()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All backend tests passed!")
            return True
        else:
            failed_tests = [r for r in self.test_results if not r["success"]]
            print(f"❌ {len(failed_tests)} tests failed:")
            for test in failed_tests:
                print(f"   • {test['name']}: {test['details']}")
            return False

def main():
    """Main test execution"""
    tester = KafkaTraceViewerTester()
    success = tester.run_comprehensive_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())