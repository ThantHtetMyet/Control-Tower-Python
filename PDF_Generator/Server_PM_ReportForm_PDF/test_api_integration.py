import asyncio
import json
import uuid
from datetime import datetime
from main import ServerPMPDFService

async def test_api_integration():
    """Test the API integration for saving PDF request logs"""
    
    # Create service instance
    service = ServerPMPDFService()
    
    # Test data
    test_report_id = str(uuid.uuid4())  # Generate a test GUID
    test_requested_by = str(uuid.uuid4())  # Generate a test user GUID
    test_timestamp = datetime.now().isoformat()
    
    print(f"Testing API integration with:")
    print(f"Report ID: {test_report_id}")
    print(f"Requested By: {test_requested_by}")
    print(f"Timestamp: {test_timestamp}")
    print("-" * 50)
    
    # Test 1: Valid GUID format
    print("Test 1: Testing with valid GUID format...")
    await service.save_pdf_request_to_api(test_report_id, test_requested_by, test_timestamp)
    
    # Test 2: Invalid requested_by (should be skipped)
    print("\nTest 2: Testing with invalid requested_by (should be skipped)...")
    await service.save_pdf_request_to_api(test_report_id, "unknown", test_timestamp)
    
    # Test 3: Invalid report_id (should be skipped)
    print("\nTest 3: Testing with invalid report_id (should be skipped)...")
    await service.save_pdf_request_to_api("invalid-guid", test_requested_by, test_timestamp)
    
    # Test 4: Test GUID validation
    print("\nTest 4: Testing GUID validation...")
    valid_guid = str(uuid.uuid4())
    invalid_guid = "not-a-guid"
    
    print(f"Valid GUID '{valid_guid}': {service.is_valid_guid(valid_guid)}")
    print(f"Invalid GUID '{invalid_guid}': {service.is_valid_guid(invalid_guid)}")
    
    print("\nAPI integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_api_integration())