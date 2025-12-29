"""
Test script to verify /api/gdd/sections endpoint works
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_sections_endpoint():
    """Test the sections endpoint"""
    print("=" * 60)
    print("Testing /api/gdd/sections endpoint")
    print("=" * 60)
    
    # Test 1: Check if endpoint exists (should return error for missing doc_id)
    print("\nTest 1: GET without doc_id (should return error)")
    try:
        response = requests.get(f"{BASE_URL}/api/gdd/sections")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text (first 500 chars): {response.text[:500]}")
        if response.status_code == 200:
            print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 1b: Try with trailing slash
    print("\nTest 1b: GET without doc_id with trailing slash")
    try:
        response = requests.get(f"{BASE_URL}/api/gdd/sections/")
        print(f"Status Code: {response.status_code}")
        print(f"Response Text (first 500 chars): {response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: GET with doc_id
    print("\nTest 2: GET with doc_id")
    doc_id = "Asset_UI_Tank_War_Reward_Screen_Design"
    try:
        url = f"{BASE_URL}/api/gdd/sections?doc_id={doc_id}"
        print(f"URL: {url}")
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response Text (first 500 chars): {response.text[:500]}")
        if response.status_code == 200:
            print(f"Response JSON: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Try other GDD endpoints to see if they work
    print("\nTest 3: Try /api/gdd/documents (should work)")
    try:
        response = requests.get(f"{BASE_URL}/api/gdd/documents")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Documents endpoint works! Got {len(data.get('documents', []))} documents")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Health check
    print("\nTest 4: Health check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check - Status Code: {response.status_code}")
        print(f"Health check - Response: {response.json()}")
    except Exception as e:
        print(f"Error accessing health endpoint: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_sections_endpoint()

