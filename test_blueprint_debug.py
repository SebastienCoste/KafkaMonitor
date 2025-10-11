#!/usr/bin/env python3
"""
Debug Blueprint Creator Issues
"""

import requests
import json
import time

base_url = "https://git-project-mgr.preview.emergentagent.com"

def test_blueprint_config():
    print("🔧 Testing Blueprint Configuration...")
    
    # Test 1: Get current config
    print("1. Getting current config...")
    response = requests.get(f"{base_url}/api/blueprint/config")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Current root_path: {data.get('root_path')}")
    else:
        print(f"   Error: {response.text}")
    
    # Test 2: Set root path
    print("2. Setting root path to /app...")
    response = requests.put(
        f"{base_url}/api/blueprint/config",
        json={"root_path": "/app"},
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {data}")
    else:
        print(f"   Error: {response.text}")
    
    # Test 3: Get config again to verify persistence
    print("3. Getting config again to verify...")
    response = requests.get(f"{base_url}/api/blueprint/config")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Root path after set: {data.get('root_path')}")
    else:
        print(f"   Error: {response.text}")
    
    # Test 4: Try file tree
    print("4. Testing file tree...")
    response = requests.get(f"{base_url}/api/blueprint/file-tree")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Files found: {len(data.get('files', []))}")
    else:
        print(f"   Error: {response.text}")
    
    # Test 5: Try create directory
    print("5. Testing create directory...")
    response = requests.post(
        f"{base_url}/api/blueprint/create-directory",
        json={"path": "test_debug_dir"},
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {data}")
    else:
        print(f"   Error: {response.text}")

def test_script_endpoints():
    print("\n🔧 Testing Script Endpoints...")
    
    # Test validate-script endpoint
    print("1. Testing validate-script endpoint...")
    response = requests.post(
        f"{base_url}/api/blueprint/validate-script/test.tgz",
        json={
            "tgz_file": "test-data",
            "environment": "DEV",
            "action": "validate"
        },
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {data}")
    else:
        print(f"   Error: {response.text}")
    
    # Test activate-script endpoint
    print("2. Testing activate-script endpoint...")
    response = requests.post(
        f"{base_url}/api/blueprint/activate-script/test.tgz",
        json={
            "tgz_file": "test-data",
            "environment": "DEV",
            "action": "activate"
        },
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {data}")
    else:
        print(f"   Error: {response.text}")

if __name__ == "__main__":
    print("🏗️ Blueprint Creator Debug Testing")
    print("=" * 50)
    
    test_blueprint_config()
    test_script_endpoints()
    
    print("\n✅ Debug testing completed")