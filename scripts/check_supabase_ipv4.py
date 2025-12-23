"""
Check if Supabase URL resolves to IPv4 addresses
This ensures compatibility with Render's IPv4-only network
"""

import os
import socket
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.shared.config import SUPABASE_URL

def check_ipv4_compatibility(url: str):
    """
    Check if a URL resolves to IPv4 addresses.
    
    Args:
        url: The URL to check (e.g., https://xxx.supabase.co)
    
    Returns:
        dict with results
    """
    if not url:
        return {
            'success': False,
            'error': 'URL is empty'
        }
    
    # Parse URL to get hostname
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        return {
            'success': False,
            'error': 'Could not parse hostname from URL'
        }
    
    print(f"Checking hostname: {hostname}")
    print(f"Full URL: {url}")
    print()
    
    # Get all IP addresses for this hostname
    try:
        # Get all address info (both IPv4 and IPv6)
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        
        ipv4_addresses = []
        ipv6_addresses = []
        
        for info in addr_info:
            ip_address = info[4][0]
            if ':' in ip_address:
                # IPv6 address
                ipv6_addresses.append(ip_address)
            else:
                # IPv4 address
                ipv4_addresses.append(ip_address)
        
        # Remove duplicates
        ipv4_addresses = list(set(ipv4_addresses))
        ipv6_addresses = list(set(ipv6_addresses))
        
        result = {
            'success': True,
            'hostname': hostname,
            'ipv4_addresses': ipv4_addresses,
            'ipv6_addresses': ipv6_addresses,
            'has_ipv4': len(ipv4_addresses) > 0,
            'has_ipv6': len(ipv6_addresses) > 0,
            'ipv4_compatible': len(ipv4_addresses) > 0  # Compatible if has IPv4
        }
        
        return result
        
    except socket.gaierror as e:
        return {
            'success': False,
            'error': f'DNS lookup failed: {e}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {e}'
        }


def main():
    """Main function to check Supabase URL IPv4 compatibility"""
    print("=" * 60)
    print("Supabase IPv4 Compatibility Check")
    print("=" * 60)
    print()
    
    # Get Supabase URL from environment
    supabase_url = SUPABASE_URL or os.getenv('SUPABASE_URL')
    
    if not supabase_url:
        print("❌ Error: SUPABASE_URL not found in environment variables")
        print("   Please set SUPABASE_URL in your .env file")
        sys.exit(1)
    
    # Check IPv4 compatibility
    result = check_ipv4_compatibility(supabase_url)
    
    if not result['success']:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    # Display results
    print("DNS Resolution Results:")
    print(f"  Hostname: {result['hostname']}")
    print()
    
    if result['ipv4_addresses']:
        print(f"✅ IPv4 Addresses ({len(result['ipv4_addresses'])}):")
        for ip in result['ipv4_addresses']:
            print(f"   - {ip}")
    else:
        print("❌ No IPv4 addresses found")
    
    print()
    
    if result['ipv6_addresses']:
        print(f"ℹ️  IPv6 Addresses ({len(result['ipv6_addresses'])}):")
        for ip in result['ipv6_addresses']:
            print(f"   - {ip}")
    else:
        print("ℹ️  No IPv6 addresses found")
    
    print()
    print("=" * 60)
    
    # Final verdict
    if result['ipv4_compatible']:
        print("✅ COMPATIBLE: Supabase URL resolves to IPv4 addresses")
        print("   Render (IPv4-only) can connect to this Supabase instance")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ NOT COMPATIBLE: No IPv4 addresses found")
        print("   Render (IPv4-only) may not be able to connect")
        print("   Consider using a different Supabase region or contact support")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

