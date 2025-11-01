import asyncio
import logging
import pyodbc
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for Server PM Report data retrieval"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.connection = None
        
    def get_connection_string(self) -> str:
        """Build connection string from configuration"""
        if self.db_config.get('trusted_connection'):
            return (
                f"DRIVER={{{self.db_config['driver']}}};"
                f"SERVER={self.db_config['server']};"
                f"DATABASE={self.db_config['database']};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate={'yes' if self.db_config.get('trust_server_certificate') else 'no'};"
            )
        else:
            return (
                f"DRIVER={{{self.db_config['driver']}}};"
                f"SERVER={self.db_config['server']};"
                f"DATABASE={self.db_config['database']};"
                f"UID={self.db_config['username']};"
                f"PWD={self.db_config['password']};"
                f"TrustServerCertificate={'yes' if self.db_config.get('trust_server_certificate') else 'no'};"
            )
    
    async def connect(self):
        """Establish database connection"""
        try:
            connection_string = self.get_connection_string()
            self.connection = pyodbc.connect(connection_string)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
            
    async def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
            
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a query and return results as list of dictionaries"""
        if not self.connection:
            await self.connect()
            
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            # Get column names
            columns = [column[0] for column in cursor.description]
            
            # Fetch all rows and convert to dictionaries
            rows = cursor.fetchall()
            result = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[columns[i]] = value
                result.append(row_dict)
                
            cursor.close()
            return result
            
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            raise
            
    async def get_server_pm_report_data(self, job_no: str) -> Optional[Dict]:
        """Retrieve complete Server PM report data for given job number"""
        try:
            logger.info(f"Fetching Server PM report data for Job No: {job_no}")
            
            # Main report form query
            main_query = """
            SELECT 
                rf.ID as ReportFormID,
                rf.JobNo,
                rf.SystemNameWarehouseID,
                rf.StationNameWarehouseID,
                rf.CreatedDate,
                rf.UpdatedDate,
                sw_system.Name as SystemDescription,
                sw_station.Name as StationName,
                rft.Name as ReportFormTypeName,
                
                -- PM Report Form Server data
                pmrfs.ID as PMReportFormServerID,
                pmrfs.PMReportFormTypeID,
                pmrft.Name as PMReportFormTypeName,
                pmrfs.ProjectNo,
                pmrfs.Customer,
                pmrfs.ReportTitle,
                pmrfs.DateOfService,
                
                -- Sign Off Data
                pmrfs.AttendedBy,
                pmrfs.WitnessedBy,
                pmrfs.StartDate,
                pmrfs.CompletionDate,
                pmrfs.ApprovedBy,
                pmrfs.Remarks as SignOffRemarks
                
            FROM ReportForms rf
            LEFT JOIN PMReportFormServers pmrfs ON rf.ID = pmrfs.ReportFormID
            LEFT JOIN PMReportFormTypes pmrft ON pmrfs.PMReportFormTypeID = pmrft.ID
            LEFT JOIN ReportFormTypes rft ON rf.ReportFormTypeID = rft.ID
            LEFT JOIN SystemWarehouses sw_system ON rf.SystemNameWarehouseID = sw_system.ID
            LEFT JOIN SystemWarehouses sw_station ON rf.StationNameWarehouseID = sw_station.ID
            WHERE rf.JobNo = ?
            """
            
            main_data = await self.execute_query(main_query, (job_no,))
            
            if not main_data:
                logger.warning(f"No report found for Job No: {job_no}")
                return None
                
            report_data = main_data[0]
            pm_report_form_server_id = report_data.get('PMReportFormServerID')
            
            if not pm_report_form_server_id:
                logger.warning(f"No PM Report Form Server data found for Job No: {job_no}")
                return report_data
                
            # Fetch all related data
            report_data.update({
                'server_health_data': await self.get_server_health_data(pm_report_form_server_id),
                'hard_drive_health_data': await self.get_hard_drive_health_data(pm_report_form_server_id),
                'disk_usage_data': await self.get_disk_usage_data(pm_report_form_server_id),
                'cpu_ram_usage_data': await self.get_cpu_ram_usage_data(pm_report_form_server_id),
                'network_health_data': await self.get_network_health_data(pm_report_form_server_id),
                'willowlynx_process_status_data': await self.get_willowlynx_process_status_data(pm_report_form_server_id),
                'willowlynx_network_status_data': await self.get_willowlynx_network_status_data(pm_report_form_server_id),
                'willowlynx_rtu_status_data': await self.get_willowlynx_rtu_status_data(pm_report_form_server_id),
                'willowlynx_historical_trend_data': await self.get_willowlynx_historical_trend_data(pm_report_form_server_id),
                'willowlynx_historical_report_data': await self.get_willowlynx_historical_report_data(pm_report_form_server_id),
                'willowlynx_cctv_camera_data': await self.get_willowlynx_cctv_camera_data(pm_report_form_server_id),
                'monthly_database_creation_data': await self.get_monthly_database_creation_data(pm_report_form_server_id),
                'database_backup_data': await self.get_database_backup_data(pm_report_form_server_id),
                'time_sync_data': await self.get_time_sync_data(pm_report_form_server_id),
                'hot_fixes_data': await self.get_hot_fixes_data(pm_report_form_server_id),
                'auto_fail_over_data': await self.get_auto_fail_over_data(pm_report_form_server_id),
                'asa_firewall_data': await self.get_asa_firewall_data(pm_report_form_server_id),
                'software_patch_data': await self.get_software_patch_data(pm_report_form_server_id)
            })
            
            logger.info(f"Successfully retrieved complete report data for Job No: {job_no}")
            return report_data
            
        except Exception as e:
            logger.error(f"Error retrieving report data for Job No {job_no}: {str(e)}")
            raise
            
    async def get_server_health_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get server health check data"""
        query = """
        SELECT ServerName, Result, Remarks
        FROM PMServerHealths
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_hard_drive_health_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get hard drive health check data"""
        query = """
        SELECT ServerName, HardDrive, Status, Remarks
        FROM PMServerHardDriveHealths
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_disk_usage_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get disk usage data"""
        query = """
        SELECT ServerName, Disk, TotalSize, UsedSize, FreeSize, UsagePercentage, Status, Remarks
        FROM PMServerDiskUsages
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_cpu_ram_usage_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get CPU and RAM usage data"""
        query = """
        SELECT ServerName, CPUUsage, RAMUsage, Remarks
        FROM PMServerCPUAndRAMUsages
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_network_health_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get network health data"""
        query = """
        SELECT ServerName, NetworkInterface, Status, IPAddress, Remarks
        FROM PMServerNetworkHealths
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_willowlynx_process_status_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get Willowlynx process status data"""
        query = """
        SELECT ProcessName, Status, Remarks
        FROM PMServerWillowlynxProcessStatuses
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_willowlynx_network_status_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get Willowlynx network status data"""
        query = """
        SELECT NetworkComponent, Status, Remarks
        FROM PMServerWillowlynxNetworkStatuses
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_willowlynx_rtu_status_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get Willowlynx RTU status data"""
        query = """
        SELECT RTUName, Status, Remarks
        FROM PMServerWillowlynxRTUStatuses
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_willowlynx_historical_trend_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get Willowlynx historical trend data"""
        query = """
        SELECT TrendName, Status, Remarks
        FROM PMServerWillowlynxHistoricalTrends
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_willowlynx_historical_report_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get Willowlynx historical report data"""
        query = """
        SELECT ReportName, Status, Remarks
        FROM PMServerWillowlynxHistoricalReports
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_willowlynx_cctv_camera_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get Willowlynx CCTV camera data"""
        query = """
        SELECT CameraName, Status, Remarks
        FROM PMServerWillowlynxCCTVCameras
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_monthly_database_creation_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get monthly database creation data"""
        query = """
        SELECT DatabaseName, CreationDate, Status, Remarks
        FROM PMServerMonthlyDatabaseCreations
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_database_backup_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get database backup data"""
        query = """
        SELECT DatabaseName, BackupDate, BackupSize, Status, Remarks
        FROM PMServerDatabaseBackups
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_time_sync_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get time sync data"""
        query = """
        SELECT ServerName, TimeSyncStatus, LastSyncTime, Remarks
        FROM PMServerTimeSyncs
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_hot_fixes_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get hot fixes data"""
        query = """
        SELECT HotFixID, Description, InstallationDate, Status, Remarks
        FROM PMServerHotFixes
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_auto_fail_over_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get auto fail over data"""
        query = """
        SELECT ComponentName, FailOverStatus, LastTestDate, Remarks
        FROM PMServerFailOvers
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_asa_firewall_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get ASA firewall data"""
        query = """
        SELECT FirewallName, Status, LastUpdateDate, Remarks
        FROM PMServerASAFirewalls
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    async def get_software_patch_data(self, pm_report_form_server_id: int) -> List[Dict]:
        """Get software patch data"""
        query = """
        SELECT PatchName, InstallationDate, Status, Remarks
        FROM PMServerSoftwarePatchSummaries
        WHERE PMReportFormServerID = ?
        ORDER BY ID
        """
        return await self.execute_query(query, (pm_report_form_server_id,))
        
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None