"""
Connection Diagnostic Script
Run this to find out why localhost:8001 is not accessible
"""

import socket
import requests
import sys

print("="*80)
print("VOICE GUIDE - CONNECTION DIAGNOSTIC")
print("="*80)

# Test 1: Check if port 8001 is open
print("\n1. Checking if port 8001 is open...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
result = sock.connect_ex(('localhost', 8001))
if result == 0:
    print("   ✅ Port 8001 is OPEN")
else:
    print("   ❌ Port 8001 is CLOSED or BLOCKED")
    print("   This means:")
    print("   - Backend might not be running")
    print("   - Or Windows Firewall is blocking it")
sock.close()

# Test 2: Try connecting to 127.0.0.1
print("\n2. Testing connection to 127.0.0.1:8001...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(2)
result = sock.connect_ex(('127.0.0.1', 8001))
if result == 0:
    print("   ✅ Can connect to 127.0.0.1:8001")
else:
    print("   ❌ Cannot connect to 127.0.0.1:8001")
sock.close()

# Test 3: Try with requests library
print("\n3. Testing HTTP request to http://localhost:8001/api/health...")
try:
    response = requests.get("http://localhost:8001/api/health", timeout=5)
    print(f"   ✅ Success! Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except requests.exceptions.Timeout:
    print("   ❌ Request TIMED OUT")
    print("   Backend is not responding")
except requests.exceptions.ConnectionError as e:
    print(f"   ❌ CONNECTION ERROR: {e}")
    print("   Backend might be running but not accessible")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

# Test 4: Try with 127.0.0.1
print("\n4. Testing HTTP request to http://127.0.0.1:8001/api/health...")
try:
    response = requests.get("http://127.0.0.1:8001/api/health", timeout=5)
    print(f"   ✅ Success! Status: {response.status_code}")
    print(f"   Response: {response.json()}")
except requests.exceptions.Timeout:
    print("   ❌ Request TIMED OUT")
except requests.exceptions.ConnectionError as e:
    print(f"   ❌ CONNECTION ERROR: {e}")
except Exception as e:
    print(f"   ❌ ERROR: {e}")

print("\n" + "="*80)
print("DIAGNOSIS:")
print("="*80)

# Check if backend is running
import subprocess
try:
    result = subprocess.run(
        ['netstat', '-ano', '|', 'findstr', ':8001'],
        capture_output=True,
        text=True,
        shell=True
    )
    if '8001' in result.stdout:
        print("\n✅ Backend process is running and listening on port 8001")
        print("\nProblem: Connection is blocked by firewall or network settings")
        print("\nSOLUTION:")
        print("1. Stop backend (Ctrl+C)")
        print("2. Run this command instead:")
        print("   uvicorn server:app --host 127.0.0.1 --port 8001 --reload")
        print("\n   OR")
        print("\n3. Add Windows Firewall exception:")
        print("   - Control Panel → Windows Defender Firewall")
        print("   - Advanced Settings → Inbound Rules → New Rule")
        print("   - Port → TCP → 8001 → Allow")
    else:
        print("\n❌ No process listening on port 8001")
        print("\nSOLUTION: Make sure backend is running!")
except Exception as e:
    print(f"\n⚠️ Could not check port status: {e}")

print("\n" + "="*80)
