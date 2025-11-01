import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt
import aiohttp
from pdf_generator import ServerPMPDFGenerator
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_pm_pdf_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServerPMPDFService:
    def __init__(self):
        self.config = Config()
        self.pdf_generator = ServerPMPDFGenerator()
        self.mqtt_client = None
        self.setup_mqtt_client()
        
        # Create request log file
        self.request_log_file = self.config.PDF_OUTPUT_DIR / "pdf_requests.log"
        
    def setup_mqtt_client(self):
        """Setup MQTT client with callbacks"""
        self.mqtt_client = mqtt.Client(client_id=self.config.MQTT_CLIENT_ID)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the client receives a CONNACK response from the server"""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            # Subscribe to the topic pattern for server PM PDF requests
            topic = f"{self.config.MQTT_TOPIC_PREFIX}/server_pm_reportform_pdf/+"
            client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker, return code {rc}")
            
    def on_disconnect(self, client, userdata, rc):
        """Callback for when the client disconnects from the server"""
        logger.info(f"Disconnected from MQTT broker with result code {rc}")
        
    def on_message(self, client, userdata, msg):
        """Callback for when a PUBLISH message is received from the server"""
        try:
            # Extract report ID from topic
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 3:
                report_id = topic_parts[-1]  # Last part should be the report ID (GUID)
                
                logger.info(f"Received PDF generation request for Report ID: {report_id}")
                
                # Decode message payload - expecting new format
                try:
                    message_data = json.loads(msg.payload.decode())
                    
                    # Extract the three fields from the new message format
                    report_id_from_msg = message_data.get('report_id', report_id)
                    requested_by = message_data.get('requested_by', 'unknown')
                    timestamp = message_data.get('timestamp', datetime.now().isoformat())
                    
                    # Log the incoming request with all three fields
                    self.log_request(report_id_from_msg, requested_by, timestamp, message_data)
                    
                    # Save PDF request to database via API
                    asyncio.create_task(self.save_pdf_request_to_api(report_id_from_msg, requested_by, timestamp))
                    
                    logger.info(f"Message data - Report ID: {report_id_from_msg}, Requested by: {requested_by}, Timestamp: {timestamp}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON message: {e}")
                    # Fallback for non-JSON messages
                    message_data = {"request": msg.payload.decode()}
                    requested_by = 'unknown'
                    timestamp = datetime.now().isoformat()
                    self.log_request(report_id, requested_by, timestamp, message_data)
                    
                    # Save PDF request to database via API (fallback)
                    asyncio.create_task(self.save_pdf_request_to_api(report_id, requested_by, timestamp))
                
                # Generate PDF asynchronously
                asyncio.create_task(self.generate_pdf_async(report_id_from_msg, message_data))
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {str(e)}")
            
    async def save_pdf_request_to_api(self, report_id, requested_by, timestamp):
        """Save PDF request data to the PMServerReportFormPDFRequestLog table via API"""
        try:
            # Parse timestamp if it's a string
            if isinstance(timestamp, str):
                try:
                    # Try to parse ISO format timestamp
                    parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    # Fallback to current time if parsing fails
                    parsed_timestamp = datetime.now()
            else:
                parsed_timestamp = timestamp
            
            # Validate report_id is a valid GUID format
            if not self.is_valid_guid(report_id):
                logger.error(f"Invalid report_id format: {report_id}")
                return
            
            # Handle requested_by - if it's 'unknown' or not a valid GUID, skip the API call
            if requested_by == 'unknown' or not self.is_valid_guid(requested_by):
                logger.warning(f"Skipping API call - invalid requested_by: {requested_by}")
                return
            
            # Prepare the request data
            request_data = {
                "pmReportFormServerID": report_id,
                "requestedBy": requested_by,
                "requestedDate": parsed_timestamp.isoformat()
            }
            
            # API endpoint URL
            api_url = f"{self.config.API_BASE_URL}/api/PMServerReportFormPDFRequestLog"
            
            logger.info(f"Saving PDF request to API: {api_url}")
            logger.debug(f"Request data: {request_data}")
            
            # Make the API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    json=request_data,
                    headers={'Content-Type': 'application/json'},
                    ssl=False  # Disable SSL verification for localhost
                ) as response:
                    if response.status == 201:  # Created
                        response_data = await response.json()
                        logger.info(f"PDF request saved to database: ID={response_data.get('id', 'unknown')}")
                    elif response.status == 400:  # Bad Request
                        error_text = await response.text()
                        logger.warning(f"Failed to save PDF request - validation error: {error_text}")
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to save PDF request - HTTP {response.status}: {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error while saving PDF request: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving PDF request: {str(e)}")
    
    def is_valid_guid(self, guid_string):
        """Check if a string is a valid GUID format"""
        try:
            uuid.UUID(str(guid_string))
            return True
        except (ValueError, TypeError):
            return False
            
    def log_request(self, report_id, requested_by, timestamp, full_message):
        """Log incoming PDF generation requests to a separate log file"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'report_id': report_id,
                'requested_by': requested_by,
                'request_timestamp': timestamp,
                'full_message': full_message
            }
            
            # Write to request log file
            with open(self.request_log_file, 'a', encoding='utf-8') as f:
                f.write(f"{json.dumps(log_entry)}\n")
                
            logger.info(f"Request logged: Report ID={report_id}, Requested by={requested_by}")
            
        except Exception as e:
            logger.error(f"Failed to log request: {str(e)}")
            
    async def save_pdf_request_to_api(self, report_id, requested_by, timestamp):
        """Save PDF request data to the PMServerReportFormPDFRequestLog table via API"""
        try:
            # Parse timestamp if it's a string
            if isinstance(timestamp, str):
                try:
                    # Try to parse ISO format timestamp
                    parsed_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except ValueError:
                    # Fallback to current time if parsing fails
                    parsed_timestamp = datetime.now()
            else:
                parsed_timestamp = timestamp
            
            # Prepare the request data
            request_data = {
                "pmReportFormServerID": report_id,
                "requestedBy": requested_by,
                "requestedDate": parsed_timestamp.isoformat()
            }
            
            # API endpoint URL
            api_url = f"{self.config.API_BASE_URL}/api/PMServerReportFormPDFRequestLog"
            
            # Make the API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_url,
                    json=request_data,
                    headers={'Content-Type': 'application/json'},
                    ssl=False  # Disable SSL verification for localhost
                ) as response:
                    if response.status == 201:  # Created
                        response_data = await response.json()
                        logger.info(f"PDF request saved to database: ID={response_data.get('id', 'unknown')}")
                    elif response.status == 400:  # Bad Request
                        error_text = await response.text()
                        logger.warning(f"Failed to save PDF request - validation error: {error_text}")
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to save PDF request - HTTP {response.status}: {error_text}")
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error while saving PDF request: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while saving PDF request: {str(e)}")
            
    async def generate_pdf_async(self, report_id, message_data):
        """Generate PDF asynchronously"""
        try:
            logger.info(f"Starting PDF generation for Report ID: {report_id}")
            
            # Send processing status update
            await self.send_status_update(report_id, "processing", "Fetching report data from API...")
            
            # Fetch report data from API
            report_data = await self.retrieve_data_from_api(report_id)
            
            if not report_data:
                logger.error(f"No report data found for Report ID: {report_id}")
                await self.send_status_update(report_id, "error", "No report data found")
                return
                
            # Send processing status update
            await self.send_status_update(report_id, "processing", "Generating PDF report...")
            
            # Generate PDF with comprehensive data
            pdf_path = await self.pdf_generator.generate_comprehensive_pdf(report_data, report_id, message_data)
            
            if pdf_path and os.path.exists(pdf_path):
                logger.info(f"PDF generated successfully: {pdf_path}")
                await self.send_status_update(report_id, "completed", f"PDF generated: {os.path.basename(pdf_path)}")
            else:
                logger.error(f"Failed to generate PDF for Report ID: {report_id}")
                await self.send_status_update(report_id, "error", "PDF generation failed")
                
        except Exception as e:
            logger.error(f"Error generating PDF for Report ID {report_id}: {str(e)}")
            await self.send_status_update(report_id, "error", f"PDF generation error: {str(e)}")
    async def retrieve_data_from_api(self, report_id):
        """Retrieve all data from API endpoint - same as web application"""
        try:
            # Construct API URL - same endpoint as web application
            api_url = f"{self.config.API_BASE_URL}/api/PMReportFormServer/{report_id}"
            
            logger.info(f"Fetching data from API: {api_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    if response.status == 200:
                        api_data = await response.json()
                        logger.info("Successfully retrieved data from API")
                        
                        # Transform API response to match PDF generator expectations
                        # Following the same structure as ServerPMReportFormDetails.js
                        transformed_data = {
                            'report_form': {
                                'reportTitle': api_data.get('pmReportFormServer', {}).get('reportTitle', ''),
                                'jobNo': api_data.get('reportForm', {}).get('jobNo', '') or api_data.get('pmReportFormServer', {}).get('jobNo', ''),
                                'systemDescription': api_data.get('systemNameWarehouseName', '') or api_data.get('pmReportFormServer', {}).get('systemDescription', ''),
                                'stationName': api_data.get('stationNameWarehouseName', '') or api_data.get('pmReportFormServer', {}).get('stationName', ''),
                                'projectNo': api_data.get('pmReportFormServer', {}).get('projectNo', ''),
                                'customer': api_data.get('pmReportFormServer', {}).get('customer', ''),
                                'dateOfService': api_data.get('pmReportFormServer', {}).get('dateOfService', ''),
                                'signOffData': api_data.get('pmReportFormServer', {}).get('signOffData', {}),
                                'reportFormTypeID': api_data.get('reportForm', {}).get('reportFormTypeID'),
                                'reportFormTypeName': api_data.get('reportForm', {}).get('reportFormTypeName'),
                                'systemNameWarehouseID': api_data.get('reportForm', {}).get('systemNameWarehouseID'),
                                'stationNameWarehouseID': api_data.get('reportForm', {}).get('stationNameWarehouseID')
                            },
                            # Component data following ServerPMReportFormDetails.js structure
                            'serverHealthData': api_data.get('pmServerHealths', []),
                            'hardDriveHealthData': api_data.get('pmServerHardDriveHealths', []),
                            'diskUsageData': api_data.get('pmServerDiskUsageHealths', []),
                            'cpuAndRamUsageData': api_data.get('pmServerCPUAndMemoryUsages', []),
                            'networkHealthData': api_data.get('pmServerNetworkHealths', []),
                            'willowlynxProcessStatusData': api_data.get('pmServerWillowlynxProcessStatuses', []),
                            'willowlynxNetworkStatusData': api_data.get('pmServerWillowlynxNetworkStatuses', []),
                            'willowlynxRTUStatusData': api_data.get('pmServerWillowlynxRTUStatuses', []),
                            'willowlynxHistorialTrendData': api_data.get('pmServerWillowlynxHistoricalTrends', []),
                            'willowlynxHistoricalReportData': api_data.get('pmServerWillowlynxHistoricalReports', []),
                            'willowlynxSumpPitCCTVCameraData': api_data.get('pmServerWillowlynxCCTVCameras', []),
                            'monthlyDatabaseCreationData': api_data.get('pmServerMonthlyDatabaseCreations', []),
                            'databaseBackupData': api_data.get('pmServerDatabaseBackups', []),
                            'timeSyncData': api_data.get('pmServerTimeSyncs', []),
                            'hotFixesData': api_data.get('pmServerHotFixes', []),
                            'autoFailOverData': api_data.get('pmServerFailOvers', []),
                            'asaFirewallData': api_data.get('pmServerASAFirewalls', []),
                            'softwarePatchData': api_data.get('pmServerSoftwarePatchSummaries', []),
                            # Store original API response for reference
                            'raw_api_data': api_data
                        }
                        
                        return transformed_data
                        
                    elif response.status == 404:
                        logger.error(f"Report not found: {report_id}")
                        return None
                    else:
                        logger.error(f"API request failed with status {response.status}: {await response.text()}")
                        return None
                        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving data from API: {e}")
            return None
            
    async def send_status_update(self, report_id, status, message):
        """Send status update back via MQTT"""
        try:
            # Use the correct status topic format matching the web application
            status_topic = f"{self.config.MQTT_TOPIC_PREFIX}/server_pm_reportform_pdf_status/{report_id}"
            status_data = {
                "report_id": report_id,
                "status": status,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            self.mqtt_client.publish(status_topic, json.dumps(status_data))
            logger.info(f"Status update sent for Report ID {report_id}: {status}")
            
        except Exception as e:
            logger.error(f"Error sending status update: {str(e)}")
            
    def start_service(self):
        """Start the MQTT service"""
        try:
            logger.info("Starting Server PM PDF Generation Service...")
            
            # Connect to MQTT broker
            self.mqtt_client.connect(
                self.config.MQTT_BROKER_HOST, 
                self.config.MQTT_BROKER_PORT, 
                60
            )
            
            # Start the loop
            self.mqtt_client.loop_forever()
            
        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.error(f"Error starting service: {str(e)}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            logger.info("Service cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

def main():
    """Main entry point"""
    service = ServerPMPDFService()
    service.start_service()

if __name__ == "__main__":
    main()