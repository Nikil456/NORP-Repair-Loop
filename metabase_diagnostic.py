#!/usr/bin/env python3
"""
Quick Metabase connectivity diagnostic for NORP Repair Loop.
Tests if the Georgia Tech VPN is required to access the Metabase server.
"""

import requests
import time
import sys

def test_connectivity():
    """Test basic connectivity to Metabase server."""
    print("🔍 NORP Metabase Connectivity Test")
    print("=" * 50)
    print("Server: 130.207.3.31 (Georgia Tech)")
    print("Purpose: Test if GT VPN connection is required")
    print()

    # Test 1: Basic HTTP connectivity
    print("📡 Test 1: Basic HTTP connection (port 80)")
    try:
        start = time.time()
        response = requests.get('http://130.207.3.31', timeout=5)
        elapsed = time.time() - start
        print(f"   ✅ SUCCESS: Connected in {elapsed:.2f}s")
        print(f"   Status: {response.status_code}")
    except requests.exceptions.Timeout:
        print("   ❌ TIMEOUT: Server unreachable (5s timeout)")
    except requests.exceptions.ConnectionError as e:
        error_msg = str(e).split(": ")[0] if ": " in str(e) else str(e)
        print(f"   ❌ CONNECTION ERROR: {error_msg}")
    except Exception as e:
        print(f"   ❌ UNEXPECTED ERROR: {e}")

    print()

    # Test 2: Metabase API endpoint
    print("🔐 Test 2: Metabase API endpoint")
    try:
        start = time.time()
        response = requests.get('http://130.207.3.31/norpmetabase/api', timeout=3)
        elapsed = time.time() - start
        print(f"   ✅ SUCCESS: API reachable in {elapsed:.2f}s")
        print(f"   Status: {response.status_code}")
    except requests.exceptions.Timeout:
        print("   ❌ TIMEOUT: API unreachable (3s timeout)")
    except requests.exceptions.ConnectionError as e:
        error_msg = str(e).split(": ")[0] if ": " in str(e) else str(e)
        print(f"   ❌ CONNECTION ERROR: {error_msg}")
    except Exception as e:
        print(f"   ❌ UNEXPECTED ERROR: {e}")

    print()
    print("📋 DIAGNOSIS:")
    print("If both tests fail with connection errors:")
    print("   💡 You need to connect to Georgia Tech VPN")
    print("   💡 The Metabase server (130.207.3.31) is behind GT firewall")
    print()
    print("🔧 NEXT STEPS:")
    print("1. Connect to Georgia Tech VPN")
    print("2. Re-run this script: python3 metabase_diagnostic.py")
    print("3. If successful, run: python3 test_metabase_connection.py")
    print("4. Your repair loop will then use Metabase datasets!")

    return 0

if __name__ == "__main__":
    sys.exit(test_connectivity())