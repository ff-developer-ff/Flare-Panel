#!/usr/bin/env python3
"""
Fix server issues script
This script helps fix common server issues on Ubuntu VPS
"""

import json
import os
import subprocess
import sys

def run_command(command, description=""):
    """Run a command and return the result"""
    print(f"Running: {command}")
    if description:
        print(f"Description: {description}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Exception: {e}")
        return False

def fix_servers_json():
    """Fix servers.json to use python3 instead of python"""
    servers_file = 'servers.json'
    
    if not os.path.exists(servers_file):
        print(f"Servers file {servers_file} not found")
        return False
    
    try:
        with open(servers_file, 'r') as f:
            servers = json.load(f)
        
        updated = False
        for server_name, server_data in servers.items():
            if 'command' in server_data and 'python ' in server_data['command']:
                old_command = server_data['command']
                new_command = server_data['command'].replace('python ', 'python3 ')
                server_data['command'] = new_command
                updated = True
                print(f"Updated {server_name}: {old_command} -> {new_command}")
        
        if updated:
            with open(servers_file, 'w') as f:
                json.dump(servers, f, indent=2)
            print("Servers.json updated successfully")
        else:
            print("No commands needed updating")
        
        return True
    except Exception as e:
        print(f"Error updating servers.json: {e}")
        return False

def install_required_packages():
    """Install commonly required Python packages"""
    packages = [
        'protobuf',
        'requests',
        'flask',
        'gunicorn',
        'pycryptodome'
    ]
    
    print("Installing required packages...")
    for package in packages:
        success = run_command(f"pip3 install {package}", f"Installing {package}")
        if not success:
            print(f"Warning: Failed to install {package}")

def check_python_versions():
    """Check available Python versions"""
    print("Checking Python versions...")
    run_command("python3 --version", "Python 3 version")
    run_command("python --version", "Python version")
    run_command("which python3", "Python 3 location")
    run_command("which python", "Python location")

def main():
    print("=== Server Issues Fix Script ===")
    print("This script will help fix common server issues on Ubuntu VPS")
    print()
    
    # Check Python versions
    check_python_versions()
    print()
    
    # Install required packages
    install_required_packages()
    print()
    
    # Fix servers.json
    fix_servers_json()
    print()
    
    print("=== Fix Complete ===")
    print("Please restart your server manager and try starting servers again.")
    print("If you still have issues, check the console logs for specific error messages.")

if __name__ == "__main__":
    main() 