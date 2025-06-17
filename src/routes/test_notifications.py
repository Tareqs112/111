#!/usr/bin/env python3
"""
Test script for the notification system
This script tests the notification functionality including admin notifications
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:5000/api"

def test_admin_settings():
    """Test admin settings endpoints"""
    print("Testing admin settings...")
    
    # Test getting admin settings
    response = requests.get(f"{BASE_URL}/notifications/admin-settings")
    print(f"GET admin settings: {response.status_code}")
    print(f"GET admin settings raw response: {response.text}") # Added for debugging
    if response.status_code == 200:
        try:
            print(f"Current settings: {response.json()}")
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e} - Response was: {response.text}")
    else:
        print(f"Error: {response.text}")
    
    # Test updating admin settings
    test_data = {
        "admin_phone_numbers": ["+905551234567", "+905559876543"]
    }
    response = requests.post(f"{BASE_URL}/notifications/admin-settings", 
                           json=test_data,
                           headers={"Content-Type": "application/json"})
    print(f"POST admin settings: {response.status_code}")
    print(f"POST admin settings raw response: {response.text}") # Added for debugging
    if response.status_code == 200:
        try:
            print("Admin settings updated successfully")
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e} - Response was: {response.text}")
    else:
        print(f"Error: {response.text}")

def test_notification_system():
    """Test notification system"""
    print("\nTesting notification system...")
    
    # Test admin notification
    response = requests.post(f"{BASE_URL}/notifications/test",
                           json={"type": "admin"},
                           headers={"Content-Type": "application/json"})
    print(f"Test admin notification: {response.status_code}")
    print(f"Test admin notification raw response: {response.text}") # Added for debugging
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"Result: {result["message"]}")
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e} - Response was: {response.text}")
    else:
        print(f"Error: {response.text}")

def test_schedule_notifications():
    """Test scheduled notifications"""
    print("\nTesting scheduled notifications...")
    
    response = requests.post(f"{BASE_URL}/notifications/schedule",
                           headers={"Content-Type": "application/json"})
    print(f"Schedule notifications: {response.status_code}")
    print(f"Schedule notifications raw response: {response.text}") # Added for debugging
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"Result: {result["message"]}")
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e} - Response was: {response.text}")
    else:
        print(f"Error: {response.text}")

def test_upcoming_services():
    """Test upcoming services endpoint"""
    print("\nTesting upcoming services...")
    
    response = requests.get(f"{BASE_URL}/notifications/upcoming")
    print(f"Get upcoming services: {response.status_code}")
    print(f"Get upcoming services raw response: {response.text}") # Added for debugging
    if response.status_code == 200:
        try:
            result = response.json()
            print(f"Upcoming 24h: {len(result["upcoming_24h"])} services")
            print(f"Upcoming 1h: {len(result["upcoming_1h"])} services")
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e} - Response was: {response.text}")
    else:
        print(f"Error: {response.text}")

def main():
    """Main test function"""
    print("=== Notification System Test ===")
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now()}")
    print("=" * 40)
    
    try:
        test_admin_settings()
        test_notification_system()
        test_schedule_notifications()
        test_upcoming_services()
        
        print("\n" + "=" * 40)
        print("Test completed successfully!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server.")
        print("Make sure the Flask application is running on localhost:5000")
    except Exception as e:
        print(f"Error during testing: {str(e)}")

if __name__ == "__main__":
    main()

