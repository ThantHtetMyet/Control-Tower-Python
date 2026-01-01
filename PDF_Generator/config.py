"""
PDF Generator Configuration
All changeable values in one place
"""
import os
from pathlib import Path

class Config:
    """Centralized configuration for PDF generation service"""
    
    # ============================================
    # API Configuration
    # ============================================
    API_BASE_URL = os.getenv('API_BASE_URL', 'https://localhost:7145')
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '60'))
    API_AUTH_EMAIL = os.getenv('API_AUTH_EMAIL', 'system@gmail.com')
    API_AUTH_PASSWORD = os.getenv('API_AUTH_PASSWORD', '12345')
    
    # ============================================
    # MQTT Configuration
    # ============================================
    MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'localhost')
    MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    MQTT_USERNAME = os.getenv('MQTT_USERNAME', None)
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
    MQTT_KEEPALIVE = int(os.getenv('MQTT_KEEPALIVE', '60'))
    
    # ============================================
    # MQTT Topics - Regular PDF Generation (while editing)
    # ============================================
    TOPIC_CM_REPORT = "cm_reportform_pdf"
    TOPIC_SERVER_PM_REPORT = "server_pm_reportform_pdf"
    TOPIC_RTU_PM_REPORT = "rtu_pm_reportform_pdf"
    
    # ============================================
    # MQTT Topics - Signature-based Final Report PDF (when CLOSE with signatures)
    # ============================================
    TOPIC_CM_SIGNATURE = "cm_reportform_signature_pdf"
    TOPIC_SERVER_PM_SIGNATURE = "server_pm_reportform_signature_pdf"
    TOPIC_RTU_PM_SIGNATURE = "rtu_pm_reportform_signature_pdf"
    
    # ============================================
    # Database Configuration
    # ============================================
    DB_SERVER = os.getenv('DB_SERVER', 'WGN-009-530\\SQLEXPRESS2022')
    DB_NAME = os.getenv('DB_NAME', 'ControlTowerDatabase')
    DB_USERNAME = os.getenv('DB_USERNAME', 'opmadmin')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'Willowglen@12345')
    DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    
    @property
    def DATABASE_CONFIG(self):
        """Database connection configuration"""
        return {
            'server': self.DB_SERVER,
            'database': self.DB_NAME,
            'username': self.DB_USERNAME,
            'password': self.DB_PASSWORD,
            'driver': self.DB_DRIVER
        }
    
    # ============================================
    # File Paths
    # ============================================
    BASE_DIR = Path(__file__).parent
    
    # PDF Output Directory (ONE folder for ALL PDFs)
    PDF_OUTPUT_DIR = os.getenv(
        'PDF_OUTPUT_DIR',
        str(BASE_DIR / 'PDF_File')
    )
    
    # Image Base Path (where report images are stored)
    IMAGE_BASE_PATH = os.getenv(
        'IMAGE_BASE_PATH',
        'C:\\Temp\\ReportFormImages'
    )
    
    # Resources Directories
    RESOURCES_DIR = BASE_DIR / 'resources'
    CM_RESOURCES_DIR = BASE_DIR / 'CM_Report'
    SERVER_PM_RESOURCES_DIR = BASE_DIR / 'Server_PM_Report' / 'resources'
    RTU_PM_RESOURCES_DIR = BASE_DIR / 'RTU_PM_Report'
    
    # ============================================
    # PDF Generation Settings
    # ============================================
    PDF_PAGE_SIZE = 'A4'
    PDF_TIMEOUT_SECONDS = int(os.getenv('PDF_TIMEOUT_SECONDS', '120'))
    
    # ============================================
    # Logging Configuration
    # ============================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'pdf_service.log')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ============================================
    # Helper Methods
    # ============================================
    def get_pdf_path(self, job_no: str, report_type: str) -> str:
        """
        Generate PDF file path.
        
        Args:
            job_no: Job number
            report_type: Type of report (CM, Server_PM, RTU_PM, CM_FinalReport, etc.)
            
        Returns:
            Full path to PDF file
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_Report_{job_no}_{timestamp}.pdf"
        
        # Ensure output directory exists
        Path(self.PDF_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        return str(Path(self.PDF_OUTPUT_DIR) / filename)
    
    def get_mqtt_topics(self, report_type: str, is_signature: bool = False):
        """
        Get MQTT topics for a report type.
        
        Args:
            report_type: 'cm', 'server_pm', or 'rtu_pm'
            is_signature: Whether this is for signature-based final report
            
        Returns:
            dict with 'request_topic' and 'status_topic'
        """
        topic_map = {
            'cm': self.TOPIC_CM_SIGNATURE if is_signature else self.TOPIC_CM_REPORT,
            'server_pm': self.TOPIC_SERVER_PM_SIGNATURE if is_signature else self.TOPIC_SERVER_PM_REPORT,
            'rtu_pm': self.TOPIC_RTU_PM_SIGNATURE if is_signature else self.TOPIC_RTU_PM_REPORT,
        }
        
        base_topic = topic_map.get(report_type.lower())
        if not base_topic:
            raise ValueError(f"Unknown report type: {report_type}")
        
        return {
            'request_pattern': f"controltower/{base_topic}/+",
            'status_pattern': f"controltower/{base_topic}_status/{{report_id}}"
        }
    
    def get_api_endpoint(self, report_type: str, report_id: str):
        """
        Get API endpoint for fetching report data.
        
        Args:
            report_type: 'cm', 'server_pm', or 'rtu_pm'
            report_id: Report ID (GUID)
            
        Returns:
            API endpoint path
        """
        endpoint_map = {
            'cm': f'/api/ReportForm/CMReportForm/{report_id}',
            'server_pm': f'/api/PMReportFormServer/{report_id}',
            'rtu_pm': f'/api/ReportForm/RTUPMReportForm/{report_id}',
        }
        
        return endpoint_map.get(report_type.lower(), f'/api/ReportForm/{report_id}')
    
    def __repr__(self):
        return (
            f"Config(\n"
            f"  API: {self.API_BASE_URL}\n"
            f"  MQTT: {self.MQTT_BROKER_HOST}:{self.MQTT_BROKER_PORT}\n"
            f"  DB: {self.DB_SERVER}/{self.DB_NAME}\n"
            f"  PDF Output: {self.PDF_OUTPUT_DIR}\n"
            f"  Images: {self.IMAGE_BASE_PATH}\n"
            f")"
        )


# Global config instance
config = Config()


if __name__ == "__main__":
    # Print configuration for verification
    print("=" * 60)
    print("PDF Generator Configuration")
    print("=" * 60)
    print(config)
    print("\n" + "=" * 60)
    print("MQTT Topics:")
    print("=" * 60)
    
    for report_type in ['cm', 'server_pm', 'rtu_pm']:
        print(f"\n{report_type.upper()} Reports:")
        
        # Regular topics
        regular_topics = config.get_mqtt_topics(report_type, is_signature=False)
        print(f"  Regular PDF:")
        print(f"    Request: {regular_topics['request_pattern']}")
        print(f"    Status:  {regular_topics['status_pattern']}")
        
        # Signature topics
        sig_topics = config.get_mqtt_topics(report_type, is_signature=True)
        print(f"  Signature PDF:")
        print(f"    Request: {sig_topics['request_pattern']}")
        print(f"    Status:  {sig_topics['status_pattern']}")
    
    print("\n" + "=" * 60)
    print("API Endpoints:")
    print("=" * 60)
    for report_type in ['cm', 'server_pm', 'rtu_pm']:
        endpoint = config.get_api_endpoint(report_type, '{report_id}')
        print(f"  {report_type.upper()}: {endpoint}")
    
    print("\n" + "=" * 60)

