import os
from pathlib import Path
from datetime import datetime

class Config:
    """Configuration class for Server PM PDF Generator"""
    
    def __init__(self):
        # API Configuration - same as web application
        self.API_BASE_URL = os.getenv('API_BASE_URL', 'https://localhost:7145')
        self.API_TIMEOUT = int(os.getenv('API_TIMEOUT', 10))  # Reduced timeout for faster debugging
        
        # API Authentication Configuration
        self.API_AUTH_EMAIL = os.getenv('API_AUTH_EMAIL', 'system@gmail.com')  # Default admin email
        self.API_AUTH_PASSWORD = os.getenv('API_AUTH_PASSWORD', '12345')  # Default admin password
        
        # MQTT Configuration
        self.MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'localhost')
        self.MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', 1883))
        self.MQTT_CLIENT_ID = os.getenv('MQTT_CLIENT_ID', 'ServerPM_PDF_Generator')
        self.MQTT_TOPIC_PREFIX = os.getenv('MQTT_TOPIC_PREFIX', 'controltower')
        self.MQTT_USERNAME = os.getenv('MQTT_USERNAME', None)  # Optional username
        self.MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)  # Optional password
        
        # Database Configuration
        self.DATABASE_CONFIG = {
            'server': os.getenv('DB_SERVER', 'WGN-009-530\\SQLEXPRESS2022'),
            'database': os.getenv('DB_NAME', 'ControlTowerDatabase'),
            'trusted_connection': os.getenv('DB_TRUSTED_CONNECTION', 'yes').lower() == 'yes',
            'driver': os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server'),
            'trust_server_certificate': os.getenv('DB_TRUST_CERTIFICATE', 'yes').lower() == 'yes'
        }
        
        # PDF Output Configuration
        self.PDF_OUTPUT_DIR = Path(os.getenv('PDF_OUTPUT_DIR', './PDF_File'))
        self.PDF_OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Template Configuration
        self.TEMPLATE_DIR = Path(os.getenv('TEMPLATE_DIR', './templates'))
        self.TEMPLATE_DIR.mkdir(exist_ok=True)
        
        # Company Information
        self.COMPANY_INFO = {
            'name': 'WILLOWGLEN',
            'full_name': 'Willowglen Services Pte Ltd',
            'address': '103 Defu Lane 10, #05-01 Singapore 539223',
            'phone': 'Tel: (65) 6280 0432',
            'fax': 'Fax: (65) 6286 2002',
            'email': 'Company E-Mail: willowglen.com.sg'
        }
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'server_pm_pdf_generator.log')
        
        # Add lowercase aliases for compatibility
        self.mqtt_broker_host = self.MQTT_BROKER_HOST
        self.mqtt_broker_port = self.MQTT_BROKER_PORT
        self.mqtt_client_id = self.MQTT_CLIENT_ID
        self.mqtt_topic_prefix = self.MQTT_TOPIC_PREFIX
        self.db_server = self.DATABASE_CONFIG['server']
        self.db_database = self.DATABASE_CONFIG['database']
        self.db_trusted_connection = self.DATABASE_CONFIG['trusted_connection']
        self.db_driver = self.DATABASE_CONFIG['driver']
        self.db_trust_server_certificate = self.DATABASE_CONFIG['trust_server_certificate']
        self.pdf_output_dir = self.PDF_OUTPUT_DIR
        self.template_dir = self.TEMPLATE_DIR
        self.api_base_url = self.API_BASE_URL
        
    def get_pdf_filename(self, job_no, report_type="Server_PM"):
        """Generate PDF filename based on job number and report type"""
        timestamp = os.getenv('INCLUDE_TIMESTAMP', 'true').lower() == 'true'
        if timestamp:
            from datetime import datetime
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{report_type}_Report_{job_no}_{timestamp_str}.pdf"
        else:
            return f"{report_type}_Report_{job_no}.pdf"
            
    def get_pdf_path(self, job_no, report_type="Server_PM"):
        """Get full path for PDF file"""
        filename = self.get_pdf_filename(job_no, report_type)
        return self.PDF_OUTPUT_DIR / filename