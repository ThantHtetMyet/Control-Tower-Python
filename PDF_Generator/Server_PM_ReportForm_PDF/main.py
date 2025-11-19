import asyncio
import json
import logging
import os
import sys
import threading
import urllib3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import aiohttp
import ssl

import paho.mqtt.client as mqtt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings for localhost development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import local modules
from config import Config
from database_manager import DatabaseManager
from pdf_generator import ServerPMPDFGenerator
from cm_pdf_generator import CMReportPDFGenerator
from rtu_pdf_generator import RTUPMPDFGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_pm_pdf_service.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

SERVER_REPORT_TOPIC = "server_pm_reportform_pdf"
CM_REPORT_TOPIC = "cm_reportform_pdf"
RTU_REPORT_TOPIC = "rtu_pm_reportform_pdf"

class ServerPMPDFService:
    """Main service class for Server PM Report PDF generation via MQTT"""
    
    def __init__(self):
        self.config = Config()
        self.mqtt_client = None
        self.db_manager = None
        self.pdf_generator = None
        self.cm_pdf_generator = None
        self.rtu_pdf_generator = None
        self.session = None
        self.jwt_token = None  # Store JWT token for API authentication
        self.token_expires_at = None  # Track token expiration
        self.setup_http_session()
        
    def setup_http_session(self):
        """Setup HTTP session with retry strategy"""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    async def authenticate_api(self):
        """Authenticate with the API and get JWT token"""
        try:
            logger.info("")
            logger.info("[AUTH] Authenticating with API...")
            
            auth_url = f"{self.config.API_BASE_URL}/api/Auth/signin"
            auth_data = {
                "email": self.config.API_AUTH_EMAIL,
                "password": self.config.API_AUTH_PASSWORD
            }
            
            # Create SSL context that ignores certificate verification for localhost
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                logger.info(f"[AUTH] POST {auth_url}")
                logger.info(f"[AUTH] Email: {self.config.API_AUTH_EMAIL}")
                
                async with session.post(auth_url, json=auth_data) as response:
                    logger.info("")
                    logger.info(f"[AUTH] Response Status: {response.status}")
                    
                    if response.status == 200:
                        auth_response = await response.json()
                        self.jwt_token = auth_response.get('token')
                        expires_at = auth_response.get('expiresAt')
                        
                        if self.jwt_token:
                            logger.info("")
                            logger.info("[AUTH] Authentication successful")
                            logger.info(f"[AUTH] Token expires at: {expires_at}")
                            self.token_expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00')) if expires_at else None
                            return True
                        else:
                            logger.info("")
                            logger.error("[AUTH] No token received in response")
                            return False
                    else:
                        error_text = await response.text()
                        logger.info("")
                        logger.error(f"[AUTH] Authentication failed: Status {response.status}")
                        logger.error(f"[AUTH] Response: {error_text}")
                        return False
                        
        except Exception as e:
            logger.info("")
            logger.error(f"[AUTH] Authentication error: {str(e)}")
            return False
    
    def is_token_valid(self):
        """Check if current JWT token is still valid"""
        if not self.jwt_token:
            return False
        
        if self.token_expires_at and datetime.now(timezone.utc) >= self.token_expires_at:
            logger.info("")
            logger.info("[AUTH] Token has expired")
            return False
            
        return True
        
    def setup_mqtt_client(self):
        """Setup MQTT client with callbacks"""
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        # Set MQTT credentials if provided
        if self.config.MQTT_USERNAME and self.config.MQTT_PASSWORD:
            self.mqtt_client.username_pw_set(
                self.config.MQTT_USERNAME, 
                self.config.MQTT_PASSWORD
            )
            
    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Callback for MQTT connection"""
        if reason_code == 0:
            logger.info("")
            logger.info("Connected to MQTT broker successfully")
            topic = f"controltower/{SERVER_REPORT_TOPIC}/+"
            client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")

            cm_topic = f"controltower/{CM_REPORT_TOPIC}/+"
            client.subscribe(cm_topic)
            logger.info(f"Subscribed to topic: {cm_topic}")

            rtu_topic = f"controltower/{RTU_REPORT_TOPIC}/+"
            client.subscribe(rtu_topic)
            logger.info(f"Subscribed to topic: {rtu_topic}")
        else:
            logger.info("")
            logger.error(f"Failed to connect to MQTT broker. Return code: {reason_code}")
            
    def on_mqtt_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        """Callback for MQTT disconnection"""
        if reason_code != 0:
            logger.warning("Unexpected MQTT disconnection. Attempting to reconnect...")
        else:
            logger.info("MQTT client disconnected")
            
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            # Extract report_id from topic
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 3:
                report_type_key = topic_parts[-2]
                report_id = topic_parts[-1]  # Last part of the topic
            else:
                logger.info("")
                logger.error(f"Invalid topic format: {msg.topic}")
                return
                
            # Parse message payload
            try:
                message_data = json.loads(msg.payload.decode('utf-8'))
                logger.info("")
                logger.info(f"[STEP 1] Received MQTT message for report_id: {report_id}")
                logger.info(f"[DATA] Message data: {message_data}")
            except json.JSONDecodeError as e:
                logger.info("")
                logger.error(f"[ERROR] Failed to parse MQTT message JSON: {e}")
                return
                
            # Extract required fields
            requested_by = message_data.get('requested_by', 'Unknown')
            timestamp = message_data.get('timestamp', datetime.now().isoformat())
            
            # Process the PDF generation request in a separate thread
            import threading
            thread = threading.Thread(
                target=self._run_async_process,
                args=(report_id, requested_by, timestamp, message_data, report_type_key)
            )
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.info("")
            logger.error(f"Error processing MQTT message: {str(e)}")
            
    def _run_async_process(self, report_id: str, requested_by: str, 
                          timestamp: str, message_data: Dict[str, Any], report_topic_key: str):
        """Helper method to run async process in a new event loop"""
        try:
            asyncio.run(self.process_pdf_request(report_id, requested_by, timestamp, message_data, report_topic_key))
        except Exception as e:
            logger.error(f"Error in async process: {str(e)}")

    async def process_pdf_request(self, report_id: str, requested_by: str,
                          timestamp: str, message_data: Dict[str, Any], report_topic_key: str):
        """Process PDF generation request"""
        try:
            topic_key = (report_topic_key or SERVER_REPORT_TOPIC).lower()
            logger.info("")
            logger.info(f"[STEP 2] Starting PDF processing for report_id: {report_id} ({topic_key})")

            if topic_key not in (SERVER_REPORT_TOPIC, CM_REPORT_TOPIC, RTU_REPORT_TOPIC):
                await self.send_status_update(report_id, "failed", f"Unsupported report type: {topic_key}", topic_key=topic_key)
                return

            await self.send_status_update(report_id, "processing", "PDF generation started", topic_key=topic_key)

            if not self.db_manager:
                logger.info("")
                logger.info(f"[STEP 3] Initializing database manager...")
                self.db_manager = DatabaseManager(self.config.DATABASE_CONFIG)

            if topic_key == SERVER_REPORT_TOPIC and not self.pdf_generator:
                logger.info("")
                logger.info(f"[STEP 4] Initializing Server PM PDF generator...")
                self.pdf_generator = ServerPMPDFGenerator()
            elif topic_key == CM_REPORT_TOPIC and not self.cm_pdf_generator:
                logger.info("")
                logger.info(f"[STEP 4] Initializing CM PDF generator...")
                self.cm_pdf_generator = CMReportPDFGenerator()
            elif topic_key == RTU_REPORT_TOPIC and not self.rtu_pdf_generator:
                logger.info("")
                logger.info(f"[STEP 4] Initializing RTU PM PDF generator...")
                self.rtu_pdf_generator = RTUPMPDFGenerator()

            if topic_key == SERVER_REPORT_TOPIC:
                api_path = f"/api/PMReportFormServer/{report_id}"
            elif topic_key == CM_REPORT_TOPIC:
                api_path = f"/api/ReportForm/CMReportForm/{report_id}"
            else:
                api_path = f"/api/ReportForm/RTUPMReportForm/{report_id}"

            logger.info("")
            logger.info(f"[STEP 5] Calling API endpoint {api_path}")
            api_data = await self.retrieve_data_from_api(api_path)
            if not api_data:
                logger.error("[STEP 5 FAILED] No data received from API")
                await self.send_status_update(report_id, "failed", "Failed to retrieve data from API", topic_key=topic_key)
                return

            logger.info("")
            logger.info(f"[STEP 6] Transforming API data for report type {topic_key}...")
            if topic_key == SERVER_REPORT_TOPIC:
                report_data = self.transform_api_data(api_data)
            elif topic_key == CM_REPORT_TOPIC:
                report_data = self.transform_cm_api_data(api_data)
            else:
                report_data = self.transform_rtu_api_data(api_data)

            job_no = (
                report_data.get('reportForm', {}).get('jobNo')
                or report_data.get('reportForm', {}).get('JobNo')
                or report_id
            )
            logger.info("")
            logger.info(f"[STEP 7] Using job number: {job_no}")

            logger.info("")
            logger.info(f"[STEP 8] Generating PDF output...")
            if topic_key == SERVER_REPORT_TOPIC:
                pdf_path = self.pdf_generator.generate_comprehensive_pdf(
                    report_data, job_no, "Server_PM"
                )
            elif topic_key == CM_REPORT_TOPIC:
                pdf_path = self.cm_pdf_generator.generate_pdf(
                    report_data, job_no, "CM"
                )
            else:
                pdf_path = self.rtu_pdf_generator.generate_pdf(
                    report_data, job_no, "RTU_PM"
                )

            if pdf_path and os.path.exists(pdf_path):
                logger.info("")
                logger.info(f"[STEP 8 SUCCESS] PDF generated successfully at: {pdf_path}")
                await self.send_status_update(
                    report_id,
                    "completed",
                    f"PDF generated successfully: {os.path.basename(pdf_path)}",
                    file_name=os.path.basename(pdf_path),
                    topic_key=topic_key,
                )
            else:
                logger.error("[STEP 8 FAILED] PDF generation failed")
                await self.send_status_update(report_id, "failed", "PDF generation failed", topic_key=topic_key)

        except Exception as e:
            logger.error(f"Error processing PDF request for {report_id}: {str(e)}")
            await self.send_status_update(report_id, "failed", f"Error: {str(e)}", topic_key=topic_key)
            
    async def retrieve_data_from_api(self, api_path: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from API endpoint with JWT authentication"""
        try:
            # Ensure we have a valid token
            if not self.is_token_valid():
                logger.info("")
                logger.info("[API] Token invalid or expired, authenticating...")
                if not await self.authenticate_api():
                    logger.info("")
                    logger.error("[API] Failed to authenticate")
                    return None
            
            api_url = f"{self.config.API_BASE_URL}{api_path}"
            logger.info("")
            logger.info(f"[API] URL: {api_url}")
            
            # Create SSL context that ignores certificate verification for localhost
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=self.config.API_TIMEOUT)
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.jwt_token}'
            }
            
            logger.info("")
            logger.info(f"[API] Making authenticated HTTP GET request...")
            logger.info(f"[API] Request timeout: {self.config.API_TIMEOUT} seconds")
            logger.info(f"[API] SSL verification disabled for localhost")
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(api_url, headers=headers) as response:
                    logger.info("")
                    logger.info(f"[API] Response Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info("")
                        logger.info(f"[API SUCCESS] Data retrieved successfully (Size: {len(str(data))} chars)")
                        logger.info(f"[API] Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dictionary'}")
                        return data
                    elif response.status == 401:
                        logger.info("")
                        logger.warning("[API] Unauthorized - token may be invalid, re-authenticating...")
                        if await self.authenticate_api():
                            # Retry with new token
                            headers['Authorization'] = f'Bearer {self.jwt_token}'
                            async with session.get(api_url, headers=headers) as retry_response:
                                if retry_response.status == 200:
                                    data = await retry_response.json()
                                    logger.info("")
                                    logger.info(f"[API SUCCESS] Data retrieved successfully after re-auth")
                                    return data
                                else:
                                    error_text = await retry_response.text()
                                    logger.info("")
                                    logger.error(f"[API FAILED] Status code {retry_response.status} after re-auth")
                                    logger.error(f"[API] Response: {error_text[:500]}...")
                                    return None
                        else:
                            logger.info("")
                            logger.error("[API] Re-authentication failed")
                            return None
                    else:
                        error_text = await response.text()
                        logger.info("")
                        logger.error(f"[API FAILED] Status code {response.status}")
                        logger.error(f"[API] Response: {error_text[:500]}...")  # First 500 chars
                        return None
                
        except asyncio.TimeoutError:
            logger.info("")
            logger.error(f"[API TIMEOUT] Request timed out after {self.config.API_TIMEOUT} seconds")
            return None
        except aiohttp.ClientError as e:
            logger.info("")
            logger.error(f"[API REQUEST ERROR] {str(e)}")
            return None
        except Exception as e:
            logger.info("")
            logger.error(f"[UNEXPECTED API ERROR] {str(e)}")
            return None
            
    def transform_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform API data to match PDF generator expectations"""
        try:
            # The API data structure should match what the PDF generator expects
            # Based on the database_manager structure, we expect the following keys:
            transformed_data = {
                'reportForm': api_data.get('reportForm', {}),
                'pmReportFormServer': api_data.get('pmReportFormServer', {}),
                'signOffData': {
                    'attendedBy': api_data.get('pmReportFormServer', {}).get('attendedBy', ''),
                    'witnessedBy': api_data.get('pmReportFormServer', {}).get('witnessedBy', ''),
                    'attendedDate': api_data.get('pmReportFormServer', {}).get('startDate', ''),
                    'witnessedDate': api_data.get('pmReportFormServer', {}).get('completionDate', ''),
                    'remarks': api_data.get('pmReportFormServer', {}).get('remarks', '')
                },
                
                # Component data - map from API response to expected structure
                'serverHealthData': api_data.get('pmServerHealths', []),
                'hardDriveHealthData': api_data.get('pmServerHardDriveHealths', []),
                'diskUsageData': api_data.get('pmServerDiskUsageHealths', []),
                'cpuAndMemoryData': api_data.get('pmServerCPUAndMemoryUsages', []),
                'networkHealthData': api_data.get('pmServerNetworkHealths', []),
                'willowlynxProcessData': api_data.get('pmServerWillowlynxProcessStatuses', []),
                'willowlynxNetworkData': api_data.get('pmServerWillowlynxNetworkStatuses', []),
                'willowlynxRTUData': api_data.get('pmServerWillowlynxRTUStatuses', []),
                'willowlynxHistoricalTrendData': api_data.get('pmServerWillowlynxHistoricalTrends', []),
                'willowlynxHistoricalReportData': api_data.get('pmServerWillowlynxHistoricalReports', []),
                'willowlynxCCTVData': api_data.get('pmServerWillowlynxCCTVCameras', []),
                'monthlyDatabaseData': api_data.get('pmServerMonthlyDatabaseCreations', []),
                'databaseBackupData': api_data.get('pmServerDatabaseBackups', []),
                'timeSyncData': api_data.get('pmServerTimeSyncs', []),
                'hotFixesData': api_data.get('pmServerHotFixes', []),
                'failOverData': api_data.get('pmServerFailOvers', []),
                'asaFirewallData': api_data.get('pmServerASAFirewalls', []),
                'softwarePatchData': api_data.get('pmServerSoftwarePatchSummaries', [])
            }
            
            logger.debug("API data transformed successfully")
            return transformed_data
            
        except Exception as e:
            logger.error(f"Error transforming API data: {str(e)}")
            return api_data  # Return original data if transformation fails

    def _get_value(self, data: Any, *keys):
        """Safely fetch a value from a dict regardless of casing"""
        if not isinstance(data, dict):
            return None
        for key in keys:
            if not key:
                continue
            variations = {
                key,
                key.lower(),
                key.upper(),
                key[:1].lower() + key[1:] if len(key) > 1 else key.lower(),
                key[:1].upper() + key[1:] if len(key) > 1 else key.upper(),
            }
            for variant in variations:
                if variant in data:
                    return data[variant]
        return None

    def transform_cm_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize CM API response for PDF generation"""
        try:
            cm_form_raw = self._get_value(api_data, 'cmReportForm', 'CMReportForm') or {}
            report_form = {
                'jobNo': self._get_value(api_data, 'jobNo', 'JobNo'),
                'customer': self._get_value(cm_form_raw, 'customer', 'Customer'),
                'projectNo': self._get_value(cm_form_raw, 'projectNo', 'ProjectNo'),
                'systemName': self._get_value(api_data, 'systemNameWarehouseName', 'SystemNameWarehouseName'),
                'stationName': self._get_value(api_data, 'stationNameWarehouseName', 'StationNameWarehouseName'),
                'reportFormTypeName': self._get_value(api_data, 'reportFormTypeName', 'ReportFormTypeName'),
            }

            cm_form = {
                'customer': self._get_value(cm_form_raw, 'customer', 'Customer'),
                'projectNo': self._get_value(cm_form_raw, 'projectNo', 'ProjectNo'),
                'reportTitle': self._get_value(cm_form_raw, 'reportTitle', 'ReportTitle'),
                'issueReportedDescription': self._get_value(cm_form_raw, 'issueReportedDescription', 'IssueReportedDescription'),
                'issueFoundDescription': self._get_value(cm_form_raw, 'issueFoundDescription', 'IssueFoundDescription'),
                'actionTakenDescription': self._get_value(cm_form_raw, 'actionTakenDescription', 'ActionTakenDescription'),
                'failureDetectedDate': self._get_value(cm_form_raw, 'failureDetectedDate', 'FailureDetectedDate'),
                'responseDate': self._get_value(cm_form_raw, 'responseDate', 'ResponseDate'),
                'arrivalDate': self._get_value(cm_form_raw, 'arrivalDate', 'ArrivalDate'),
                'completionDate': self._get_value(cm_form_raw, 'completionDate', 'CompletionDate'),
                'attendedBy': self._get_value(cm_form_raw, 'attendedBy', 'AttendedBy'),
                'approvedBy': self._get_value(cm_form_raw, 'approvedBy', 'ApprovedBy'),
                'remark': self._get_value(cm_form_raw, 'remark', 'Remark'),
                'furtherActionTakenName': self._get_value(cm_form_raw, 'furtherActionTakenName', 'FurtherActionTakenName'),
                'formStatusName': self._get_value(cm_form_raw, 'formStatusName', 'FormStatusName'),
            }

            return {
                'reportForm': report_form,
                'cmReportForm': cm_form,
                'materialUsed': self._get_value(api_data, 'materialUsed', 'MaterialUsed') or [],
                'beforeIssueImages': self._get_value(api_data, 'beforeIssueImages', 'BeforeIssueImages') or [],
                'afterActionImages': self._get_value(api_data, 'afterActionImages', 'AfterActionImages') or [],
                'materialUsedOldSerialImages': self._get_value(api_data, 'materialUsedOldSerialImages', 'MaterialUsedOldSerialImages') or [],
                'materialUsedNewSerialImages': self._get_value(api_data, 'materialUsedNewSerialImages', 'MaterialUsedNewSerialImages') or [],
            }

        except Exception as e:
            logger.error(f"Error transforming CM API data: {str(e)}")
            return api_data

    def transform_rtu_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize RTU PM API response for PDF generation"""
        try:
            report_form = {
                'jobNo': self._get_value(api_data, 'jobNo', 'JobNo'),
                'stationName': self._get_value(api_data, 'stationNameWarehouseName', 'StationNameWarehouseName'),
                'systemName': self._get_value(api_data, 'systemNameWarehouseName', 'SystemNameWarehouseName'),
                'reportFormTypeName': self._get_value(api_data, 'reportFormTypeName', 'ReportFormTypeName'),
            }

            rtu_form = self._get_value(api_data, 'pmReportFormRTU', 'PMReportFormRTU') or {}

            def _list_value(key: str):
                return (
                    self._get_value(api_data, key)
                    or self._get_value(api_data, key[:1].upper() + key[1:] if key else key)
                    or []
                )

            images = {
                'mainCabinet': (
                    self._get_value(api_data, 'pmMainRtuCabinetImages', 'PMMainRtuCabinetImages')
                    or []
                ),
                'chamber': (
                    self._get_value(api_data, 'pmChamberMagneticContactImages', 'PMChamberMagneticContactImages')
                    or []
                ),
                'cooling': (
                    self._get_value(api_data, 'pmrtuCabinetCoolingImages', 'PMRTUCabinetCoolingImages')
                    or []
                ),
                'dvr': (
                    self._get_value(api_data, 'pmdvrEquipmentImages', 'PMDVREquipmentImages')
                    or []
                ),
            }

            return {
                'reportForm': report_form,
                'pmReportFormRTU': rtu_form,
                'pmMainRtuCabinet': _list_value('pmMainRtuCabinet'),
                'pmChamberMagneticContact': _list_value('pmChamberMagneticContact'),
                'pmRTUCabinetCooling': _list_value('pmrtuCabinetCooling'),
                'pmDVREquipment': _list_value('pmdvrEquipment'),
                'images': images,
            }

        except Exception as e:
            logger.error(f"Error transforming RTU API data: {str(e)}")
            return api_data
            
    async def send_status_update(self, report_id: str, status: str, message: str,
                                 file_name: Optional[str] = None, topic_key: str = SERVER_REPORT_TOPIC):
        """Send status update via MQTT"""
        try:
            if topic_key == SERVER_REPORT_TOPIC:
                topic_prefix = SERVER_REPORT_TOPIC
            elif topic_key == CM_REPORT_TOPIC:
                topic_prefix = CM_REPORT_TOPIC
            elif topic_key == RTU_REPORT_TOPIC:
                topic_prefix = RTU_REPORT_TOPIC
            else:
                topic_prefix = SERVER_REPORT_TOPIC
            status_topic = f"controltower/{topic_prefix}_status/{report_id}"
            status_message = {
                'report_id': report_id,
                'status': status,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            if file_name:
                status_message['file_name'] = file_name
            
            if self.mqtt_client and self.mqtt_client.is_connected():
                self.mqtt_client.publish(
                    status_topic, 
                    json.dumps(status_message),
                    qos=1
                )
                logger.info(f"[STATUS UPDATE] {report_id} -> {status.upper()} - {message}")
                logger.info(f"[MQTT] Published to topic: {status_topic}")
            else:
                logger.info("")
                logger.warning("[WARNING] MQTT client not connected, cannot send status update")
                
        except Exception as e:
            logger.info("")
            logger.error(f"[ERROR] sending status update: {str(e)}")
            
    async def start_service(self):
        """Start the PDF service"""
        try:
            logger.info("")
            logger.info("Starting Server PM PDF Service...")
            
            # Ensure PDF output directory exists
            pdf_dir = Path(self.config.PDF_OUTPUT_DIR)
            pdf_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"PDF output directory: {pdf_dir.absolute()}")
            
            # Authenticate with API first
            logger.info("Authenticating with API...")
            if not await self.authenticate_api():
                logger.error("Failed to authenticate with API. Service cannot start.")
                return False
            
            # Setup and connect MQTT client
            self.setup_mqtt_client()
            
            logger.info(f"Connecting to MQTT broker: {self.config.MQTT_BROKER_HOST}:{self.config.MQTT_BROKER_PORT}")
            self.mqtt_client.connect(
                self.config.MQTT_BROKER_HOST, 
                self.config.MQTT_BROKER_PORT, 
                60  # keepalive timeout
            )
            
            # Start MQTT loop
            self.mqtt_client.loop_start()
            
            logger.info("")
            logger.info("Server PM PDF Service started successfully")
            logger.info("Waiting for MQTT messages...")
            
            # Keep the service running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("")
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.info("")
            logger.error(f"Error starting service: {str(e)}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Cleanup resources"""
        try:
            logger.info("")
            logger.info("Cleaning up resources...")
            
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
                
            if self.db_manager:
                await self.db_manager.disconnect()
                
            if self.session:
                self.session.close()
                
            logger.info("")
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.info("")
            logger.error(f"Error during cleanup: {str(e)}")

async def main():
    """Main entry point"""
    try:
        service = ServerPMPDFService()
        await service.start_service()
    except Exception as e:
        logger.info("")
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

def start_refresh_listener():
    """Listen for keyboard input to refresh the service"""
    def _listener():
        logger.info("")
        logger.info("Press 'r' + Enter at any time to refresh the PDF service.")
        for line in sys.stdin:
            if line.strip().lower() == 'r':
                logger.info("")
                logger.info("[REFRESH] Refresh command received. Restarting service...")
                try:
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                except Exception as exc:
                    logger.error(f"Failed to restart service: {exc}")
    thread = threading.Thread(target=_listener, daemon=True)
    thread.start()

if __name__ == "__main__":
    # Run the service
    start_refresh_listener()
    asyncio.run(main())
