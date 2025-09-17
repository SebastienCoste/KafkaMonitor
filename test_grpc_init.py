#!/usr/bin/env python3

import sys
import os
import requests
import json

# Test the gRPC initialization endpoint
def test_grpc_init():
    print("🔧 Testing gRPC initialization endpoint...")
    
    url = "http://localhost:8001/api/grpc/initialize"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, headers=headers, timeout=30)
        print(f"📡 Response status: {response.status_code}")
        print(f"📝 Response content: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ gRPC initialization successful!")
            else:
                print(f"❌ gRPC initialization failed: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Request failed: {e}")

if __name__ == "__main__":
    test_grpc_init()