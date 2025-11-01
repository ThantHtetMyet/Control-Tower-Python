#!/usr/bin/env python3
"""
Test setup script for Server PM Report PDF Generator
This script verifies that all dependencies and configurations are properly set up.
"""

import sys
import os
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import pyodbc
        print("✓ pyodbc imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import pyodbc: {e}")
        return False
        
    try:
        import paho.mqtt.client as mqtt
        print("✓ paho-mqtt imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import paho-mqtt: {e}")
        return False
        
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate
        print("✓ reportlab imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import reportlab: {e}")
        return False
        
    try:
        from PIL import Image
        print("✓ Pillow imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Pillow: {e}")
        return False
        
    return True

def test_config():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from config import Config
        config = Config()
        print("✓ Configuration loaded successfully")
        print(f"  - MQTT Broker: {config.mqtt_broker_host}:{config.mqtt_broker_port}")
        print(f"  - Database Server: {config.db_server}")
        print(f"  - PDF Output Directory: {config.pdf_output_dir}")
        return True
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from database_manager import DatabaseManager
        from config import Config
        
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Try to connect
        if db_manager.connect():
            print("✓ Database connection successful")
            db_manager.close()
            return True
        else:
            print("✗ Database connection failed")
            return False
    except Exception as e:
        print(f"✗ Database connection error: {e}")
        return False

def test_pdf_generator():
    """Test PDF generator initialization"""
    print("\nTesting PDF generator...")
    
    try:
        from pdf_generator import ServerPMPDFGenerator
        
        generator = ServerPMPDFGenerator()
        print("✓ PDF generator initialized successfully")
        return True
    except Exception as e:
        print(f"✗ PDF generator initialization failed: {e}")
        return False

def test_directories():
    """Test required directories"""
    print("\nTesting directories...")
    
    current_dir = Path(__file__).parent
    resources_dir = current_dir / "resources"
    
    if resources_dir.exists():
        print("✓ Resources directory exists")
    else:
        print("✗ Resources directory not found")
        return False
        
    # Check for logo
    logo_path = resources_dir / "willowglen_letterhead.png"
    if logo_path.exists():
        print("✓ Company logo found")
    else:
        print("⚠ Company logo not found (will use text header)")
        
    # Check for ServerPMReportForm images
    server_pm_dir = resources_dir / "ServerPMReportForm"
    if server_pm_dir.exists():
        print("✓ ServerPMReportForm images directory exists")
        image_count = len(list(server_pm_dir.glob("*.png")))
        print(f"  - Found {image_count} PNG images")
    else:
        print("⚠ ServerPMReportForm images directory not found")
        
    return True

def main():
    """Run all tests"""
    print("Server PM Report PDF Generator - Setup Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config),
        ("Database Connection Test", test_database_connection),
        ("PDF Generator Test", test_pdf_generator),
        ("Directory Test", test_directories)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The setup is ready.")
        print("\nTo start the PDF generator service, run:")
        print("python main.py")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please check the issues above.")
        print("\nCommon solutions:")
        print("1. Install missing packages: pip install -r requirements.txt")
        print("2. Check database connection settings in config.py")
        print("3. Ensure SQL Server is running and accessible")
    
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()