import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import base64
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

logger = logging.getLogger(__name__)

class ServerPMPDFGenerator:
    """PDF Generator for Server PM Reports"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        self.resources_dir = Path(__file__).parent / "resources"
        
    def setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1976d2')
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#424242')
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#1976d2'),
            borderWidth=1,
            borderColor=colors.HexColor('#1976d2'),
            borderPadding=5
        ))
        
        # Table header style
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.white
        ))
        
        # Table cell style
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT
        ))
        
        # Company info style
        self.styles.add(ParagraphStyle(
            name='CompanyInfo',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_RIGHT,
            textColor=colors.HexColor('#666666')
        ))
        
    async def generate_pdf(self, report_data: Dict, job_no: str) -> Optional[str]:
        """Generate PDF report from report data"""
        try:
            logger.info(f"Starting PDF generation for Job No: {job_no}")
            
            # Create output directory if it doesn't exist
            output_dir = Path("./generated_pdfs")
            output_dir.mkdir(exist_ok=True)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Server_PM_Report_{job_no}_{timestamp}.pdf"
            pdf_path = output_dir / filename
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # Build PDF content
            story = []
            
            # Add header and company info
            self.add_header(story, report_data)
            
            # Add report title and basic info
            self.add_report_info(story, report_data)
            
            # Add sign-off information
            self.add_sign_off_section(story, report_data)
            
            # Add all technical sections
            self.add_server_health_section(story, report_data)
            self.add_hard_drive_health_section(story, report_data)
            self.add_disk_usage_section(story, report_data)
            self.add_cpu_ram_usage_section(story, report_data)
            self.add_network_health_section(story, report_data)
            self.add_willowlynx_sections(story, report_data)
            self.add_database_sections(story, report_data)
            self.add_system_maintenance_sections(story, report_data)
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF generated successfully: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return None
            
    def add_header(self, story: List, report_data: Dict):
        """Add company header with logo"""
        try:
            # Add company logo if available
            logo_path = self.resources_dir / "willowglen_letterhead.png"
            if logo_path.exists():
                logo = Image(str(logo_path), width=150*mm, height=40*mm)
                story.append(logo)
                story.append(Spacer(1, 10*mm))
            else:
                # Fallback company header
                company_info = [
                    "WILLOWGLEN",
                    "Willowglen Services Pte Ltd",
                    "103 Defu Lane 10, #05-01 Singapore 539223",
                    "Tel: (65) 6280 0432  Fax: (65) 6286 2002",
                    "Company E-Mail: willowglen.com.sg"
                ]
                
                for line in company_info:
                    if line == "WILLOWGLEN":
                        p = Paragraph(f"<b>{line}</b>", self.styles['CustomTitle'])
                    else:
                        p = Paragraph(line, self.styles['CompanyInfo'])
                    story.append(p)
                
                story.append(Spacer(1, 10*mm))
                
        except Exception as e:
            logger.warning(f"Error adding header: {str(e)}")
            
    def add_report_info(self, story: List, report_data: Dict):
        """Add basic report information"""
        story.append(Paragraph("Preventative Maintenance (SERVER)", self.styles['CustomTitle']))
        story.append(Spacer(1, 10*mm))
        
        # Basic info table
        basic_info = [
            ['System Description:', report_data.get('SystemDescription', 'N/A')],
            ['Station Name:', report_data.get('StationName', 'N/A')],
            ['Customer:', report_data.get('Customer', 'N/A')],
            ['Project No:', report_data.get('ProjectNo', 'N/A')],
            ['Job No:', report_data.get('JobNo', 'N/A')],
            ['Date of Service:', self.format_date(report_data.get('DateOfService'))]
        ]
        
        table = Table(basic_info, colWidths=[40*mm, 120*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 15*mm))
        
    def add_sign_off_section(self, story: List, report_data: Dict):
        """Add sign-off information section"""
        story.append(Paragraph("Sign Off Information", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        sign_off_data = [
            ['Attended By:', report_data.get('AttendedBy', 'N/A')],
            ['Witnessed By:', report_data.get('WitnessedBy', 'N/A')],
            ['Start Date:', self.format_datetime(report_data.get('StartDate'))],
            ['Completion Date:', self.format_datetime(report_data.get('CompletionDate'))],
            ['Approved By:', report_data.get('ApprovedBy', 'N/A')],
            ['Remarks:', report_data.get('SignOffRemarks', 'N/A')]
        ]
        
        table = Table(sign_off_data, colWidths=[40*mm, 120*mm])
        table.setStyle(self.get_basic_table_style())
        story.append(table)
        story.append(Spacer(1, 10*mm))
        
    def add_server_health_section(self, story: List, report_data: Dict):
        """Add server health check section"""
        server_health_data = report_data.get('server_health_data', [])
        if not server_health_data:
            return
            
        story.append(Paragraph("Server Health Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        # Add section image if available
        self.add_section_image(story, "ServerHealth.png")
        
        # Create table
        headers = ['Server Name', 'Result', 'Remarks']
        table_data = [headers]
        
        for item in server_health_data:
            row = [
                item.get('ServerName', 'N/A'),
                item.get('Result', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:  # Has data beyond headers
            table = Table(table_data, colWidths=[50*mm, 40*mm, 70*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No server health data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_hard_drive_health_section(self, story: List, report_data: Dict):
        """Add hard drive health check section"""
        hard_drive_data = report_data.get('hard_drive_health_data', [])
        if not hard_drive_data:
            return
            
        story.append(Paragraph("Hard Drive Health Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        self.add_section_image(story, "HardDriveHealth.png")
        
        headers = ['Server Name', 'Hard Drive', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in hard_drive_data:
            row = [
                item.get('ServerName', 'N/A'),
                item.get('HardDrive', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[40*mm, 40*mm, 30*mm, 50*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No hard drive health data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_disk_usage_section(self, story: List, report_data: Dict):
        """Add disk usage section"""
        disk_usage_data = report_data.get('disk_usage_data', [])
        if not disk_usage_data:
            return
            
        story.append(Paragraph("Disk Usage Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Server Name', 'Disk', 'Total Size', 'Used Size', 'Free Size', 'Usage %', 'Status']
        table_data = [headers]
        
        for item in disk_usage_data:
            row = [
                item.get('ServerName', 'N/A'),
                item.get('Disk', 'N/A'),
                item.get('TotalSize', 'N/A'),
                item.get('UsedSize', 'N/A'),
                item.get('FreeSize', 'N/A'),
                f"{item.get('UsagePercentage', 0)}%" if item.get('UsagePercentage') else 'N/A',
                item.get('Status', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[25*mm, 20*mm, 25*mm, 25*mm, 25*mm, 20*mm, 20*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No disk usage data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_cpu_ram_usage_section(self, story: List, report_data: Dict):
        """Add CPU and RAM usage section"""
        cpu_ram_data = report_data.get('cpu_ram_usage_data', [])
        if not cpu_ram_data:
            return
            
        story.append(Paragraph("CPU and RAM Usage Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        self.add_section_image(story, "CPUAndRamUsage.png")
        
        headers = ['Server Name', 'CPU Usage (%)', 'RAM Usage (%)', 'Remarks']
        table_data = [headers]
        
        for item in cpu_ram_data:
            row = [
                item.get('ServerName', 'N/A'),
                f"{item.get('CPUUsage', 0)}%" if item.get('CPUUsage') else 'N/A',
                f"{item.get('RAMUsage', 0)}%" if item.get('RAMUsage') else 'N/A',
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[40*mm, 35*mm, 35*mm, 50*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No CPU and RAM usage data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_network_health_section(self, story: List, report_data: Dict):
        """Add network health section"""
        network_data = report_data.get('network_health_data', [])
        if not network_data:
            return
            
        story.append(Paragraph("Network Health Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Server Name', 'Network Interface', 'Status', 'IP Address', 'Remarks']
        table_data = [headers]
        
        for item in network_data:
            row = [
                item.get('ServerName', 'N/A'),
                item.get('NetworkInterface', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('IPAddress', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[30*mm, 35*mm, 25*mm, 35*mm, 35*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No network health data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_willowlynx_sections(self, story: List, report_data: Dict):
        """Add all Willowlynx-related sections"""
        # Willowlynx Process Status
        self.add_willowlynx_process_status(story, report_data)
        
        # Willowlynx Network Status
        self.add_willowlynx_network_status(story, report_data)
        
        # Willowlynx RTU Status
        self.add_willowlynx_rtu_status(story, report_data)
        
        # Willowlynx Historical Trend
        self.add_willowlynx_historical_trend(story, report_data)
        
        # Willowlynx Historical Report
        self.add_willowlynx_historical_report(story, report_data)
        
        # Willowlynx CCTV Camera
        self.add_willowlynx_cctv_camera(story, report_data)
        
    def add_willowlynx_process_status(self, story: List, report_data: Dict):
        """Add Willowlynx process status section"""
        process_data = report_data.get('willowlynx_process_status_data', [])
        if not process_data:
            return
            
        story.append(Paragraph("Willowlynx Process Status Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        self.add_section_image(story, "WillowlynxProcessStatus.png")
        
        headers = ['Process Name', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in process_data:
            row = [
                item.get('ProcessName', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[50*mm, 40*mm, 70*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No Willowlynx process status data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_willowlynx_network_status(self, story: List, report_data: Dict):
        """Add Willowlynx network status section"""
        network_data = report_data.get('willowlynx_network_status_data', [])
        if not network_data:
            return
            
        story.append(Paragraph("Willowlynx Network Status Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        self.add_section_image(story, "WillowlynxNetworkStatus.png")
        
        headers = ['Network Component', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in network_data:
            row = [
                item.get('NetworkComponent', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[50*mm, 40*mm, 70*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No Willowlynx network status data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_willowlynx_rtu_status(self, story: List, report_data: Dict):
        """Add Willowlynx RTU status section"""
        rtu_data = report_data.get('willowlynx_rtu_status_data', [])
        if not rtu_data:
            return
            
        story.append(Paragraph("Willowlynx RTU Status Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        self.add_section_image(story, "WillowlynxRTUStatus.png")
        
        headers = ['RTU Name', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in rtu_data:
            row = [
                item.get('RTUName', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[50*mm, 40*mm, 70*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No Willowlynx RTU status data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_willowlynx_historical_trend(self, story: List, report_data: Dict):
        """Add Willowlynx historical trend section"""
        trend_data = report_data.get('willowlynx_historical_trend_data', [])
        if not trend_data:
            return
            
        story.append(Paragraph("Willowlynx Historical Trend Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Trend Name', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in trend_data:
            row = [
                item.get('TrendName', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[50*mm, 40*mm, 70*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No Willowlynx historical trend data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_willowlynx_historical_report(self, story: List, report_data: Dict):
        """Add Willowlynx historical report section"""
        report_data_items = report_data.get('willowlynx_historical_report_data', [])
        if not report_data_items:
            return
            
        story.append(Paragraph("Willowlynx Historical Report Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        self.add_section_image(story, "WillowlynxHistoricalReport.png")
        
        headers = ['Report Name', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in report_data_items:
            row = [
                item.get('ReportName', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[50*mm, 40*mm, 70*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No Willowlynx historical report data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_willowlynx_cctv_camera(self, story: List, report_data: Dict):
        """Add Willowlynx CCTV camera section"""
        cctv_data = report_data.get('willowlynx_cctv_camera_data', [])
        if not cctv_data:
            return
            
        story.append(Paragraph("Willowlynx Sump Pit CCTV Camera Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        self.add_section_image(story, "WillowlynxSumpPitCCTVCamera.png")
        
        headers = ['Camera Name', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in cctv_data:
            row = [
                item.get('CameraName', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[50*mm, 40*mm, 70*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No Willowlynx CCTV camera data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_database_sections(self, story: List, report_data: Dict):
        """Add database-related sections"""
        # Monthly Database Creation
        self.add_monthly_database_creation(story, report_data)
        
        # Database Backup
        self.add_database_backup(story, report_data)
        
    def add_monthly_database_creation(self, story: List, report_data: Dict):
        """Add monthly database creation section"""
        db_creation_data = report_data.get('monthly_database_creation_data', [])
        if not db_creation_data:
            return
            
        story.append(Paragraph("Monthly Database Creation Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Database Name', 'Creation Date', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in db_creation_data:
            row = [
                item.get('DatabaseName', 'N/A'),
                self.format_date(item.get('CreationDate')),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[40*mm, 35*mm, 30*mm, 55*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No monthly database creation data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_database_backup(self, story: List, report_data: Dict):
        """Add database backup section"""
        backup_data = report_data.get('database_backup_data', [])
        if not backup_data:
            return
            
        story.append(Paragraph("Database Backup Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Database Name', 'Backup Date', 'Backup Size', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in backup_data:
            row = [
                item.get('DatabaseName', 'N/A'),
                self.format_date(item.get('BackupDate')),
                item.get('BackupSize', 'N/A'),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[30*mm, 30*mm, 25*mm, 25*mm, 50*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No database backup data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_system_maintenance_sections(self, story: List, report_data: Dict):
        """Add system maintenance sections"""
        # Time Sync
        self.add_time_sync(story, report_data)
        
        # Hot Fixes
        self.add_hot_fixes(story, report_data)
        
        # Auto Fail Over
        self.add_auto_fail_over(story, report_data)
        
        # ASA Firewall
        self.add_asa_firewall(story, report_data)
        
        # Software Patch
        self.add_software_patch(story, report_data)
        
    def add_time_sync(self, story: List, report_data: Dict):
        """Add time sync section"""
        time_sync_data = report_data.get('time_sync_data', [])
        if not time_sync_data:
            return
            
        story.append(Paragraph("Time Sync Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Server Name', 'Time Sync Status', 'Last Sync Time', 'Remarks']
        table_data = [headers]
        
        for item in time_sync_data:
            row = [
                item.get('ServerName', 'N/A'),
                item.get('TimeSyncStatus', 'N/A'),
                self.format_datetime(item.get('LastSyncTime')),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[35*mm, 35*mm, 40*mm, 50*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No time sync data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_hot_fixes(self, story: List, report_data: Dict):
        """Add hot fixes section"""
        hot_fixes_data = report_data.get('hot_fixes_data', [])
        if not hot_fixes_data:
            return
            
        story.append(Paragraph("Hot Fixes Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Hot Fix ID', 'Description', 'Installation Date', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in hot_fixes_data:
            row = [
                item.get('HotFixID', 'N/A'),
                item.get('Description', 'N/A'),
                self.format_date(item.get('InstallationDate')),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[25*mm, 40*mm, 30*mm, 25*mm, 40*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No hot fixes data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_auto_fail_over(self, story: List, report_data: Dict):
        """Add auto fail over section"""
        fail_over_data = report_data.get('auto_fail_over_data', [])
        if not fail_over_data:
            return
            
        story.append(Paragraph("Auto Fail Over Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Component Name', 'Fail Over Status', 'Last Test Date', 'Remarks']
        table_data = [headers]
        
        for item in fail_over_data:
            row = [
                item.get('ComponentName', 'N/A'),
                item.get('FailOverStatus', 'N/A'),
                self.format_date(item.get('LastTestDate')),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[40*mm, 35*mm, 35*mm, 50*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No auto fail over data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_asa_firewall(self, story: List, report_data: Dict):
        """Add ASA firewall section"""
        firewall_data = report_data.get('asa_firewall_data', [])
        if not firewall_data:
            return
            
        story.append(Paragraph("ASA Firewall Check", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Firewall Name', 'Status', 'Last Update Date', 'Remarks']
        table_data = [headers]
        
        for item in firewall_data:
            row = [
                item.get('FirewallName', 'N/A'),
                item.get('Status', 'N/A'),
                self.format_date(item.get('LastUpdateDate')),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[40*mm, 30*mm, 40*mm, 50*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No ASA firewall data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_software_patch(self, story: List, report_data: Dict):
        """Add software patch section"""
        patch_data = report_data.get('software_patch_data', [])
        if not patch_data:
            return
            
        story.append(Paragraph("Software Patch Summary", self.styles['SectionHeader']))
        story.append(Spacer(1, 5*mm))
        
        headers = ['Patch Name', 'Installation Date', 'Status', 'Remarks']
        table_data = [headers]
        
        for item in patch_data:
            row = [
                item.get('PatchName', 'N/A'),
                self.format_date(item.get('InstallationDate')),
                item.get('Status', 'N/A'),
                item.get('Remarks', 'N/A')
            ]
            table_data.append(row)
            
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[40*mm, 35*mm, 30*mm, 55*mm])
            table.setStyle(self.get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph("No software patch data available.", self.styles['Normal']))
            
        story.append(Spacer(1, 10*mm))
        
    def add_section_image(self, story: List, image_filename: str):
        """Add section image if available"""
        try:
            image_path = self.resources_dir / "ServerPMReportForm" / image_filename
            if image_path.exists():
                img = Image(str(image_path), width=80*mm, height=60*mm)
                story.append(img)
                story.append(Spacer(1, 5*mm))
        except Exception as e:
            logger.warning(f"Could not add image {image_filename}: {str(e)}")
            
    def get_basic_table_style(self):
        """Get basic table style"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ])
        
    def get_data_table_style(self):
        """Get data table style with header formatting"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ])
        
    def format_date(self, date_value):
        """Format date value for display"""
        if not date_value:
            return 'N/A'
        try:
            if isinstance(date_value, str):
                # Try to parse string date
                date_obj = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                return date_obj.strftime('%Y-%m-%d')
            elif hasattr(date_value, 'strftime'):
                return date_value.strftime('%Y-%m-%d')
            else:
                return str(date_value)
        except:
            return str(date_value) if date_value else 'N/A'
            
    def format_datetime(self, datetime_value):
        """Format datetime value for display"""
        if not datetime_value:
            return 'N/A'
        try:
            if isinstance(datetime_value, str):
                # Try to parse string datetime
                dt_obj = datetime.fromisoformat(datetime_value.replace('Z', '+00:00'))
                return dt_obj.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(datetime_value, 'strftime'):
                return datetime_value.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return str(datetime_value)
        except:
            return str(datetime_value) if datetime_value else 'N/A'
    
    async def generate_comprehensive_pdf(self, report_data: Dict, report_id: str, message_data: Dict) -> Optional[str]:
        """
        Generate comprehensive PDF report following the React component structure
        This method creates one page for each component in sequence, matching ServerPMReportFormDetails.js
        """
        try:
            logger.info(f"Starting comprehensive PDF generation for Report ID: {report_id}")
            
            # Get report form data
            report_form = report_data.get('report_form', {})
            job_no = report_form.get('jobNo', report_id)
            
            # Create PDF file path
            from config import Config
            config = Config()
            pdf_filename = config.get_pdf_filename(job_no, "Server_PM")
            pdf_path = config.get_pdf_path(job_no, "Server_PM")
            
            # Create PDF document
            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                rightMargin=20*mm,
                leftMargin=20*mm,
                topMargin=20*mm,
                bottomMargin=20*mm
            )
            
            # Build story (content) following React component sequence
            story = []
            
            # 1. First Page - Report Information (like ServerPMReportForm_FirstPage_PDF)
            story.extend(self._create_first_page(report_form, message_data))
            story.append(PageBreak())
            
            # 2. Sign Off Section (like ServerPMSignOff_PDF)
            story.extend(self._create_signoff_section(report_form))
            story.append(PageBreak())
            
            # Component sections following the steps order from ServerPMReportFormDetails.js
            component_sections = [
                ('serverHealth', 'Server Health Check', 'serverHealthData'),
                ('hardDriveHealth', 'Hard Drive Health Check', 'hardDriveHealthData'),
                ('diskUsage', 'Disk Usage Check', 'diskUsageData'),
                ('cpuAndRamUsage', 'CPU and RAM Usage Check', 'cpuAndRamUsageData'),
                ('networkHealth', 'Network Health Check', 'networkHealthData'),
                ('willowlynxProcessStatus', 'Willowlynx Process Status', 'willowlynxProcessStatusData'),
                ('willowlynxNetworkStatus', 'Willowlynx Network Status', 'willowlynxNetworkStatusData'),
                ('willowlynxRTUStatus', 'Willowlynx RTU Status', 'willowlynxRTUStatusData'),
                ('willowlynxHistorialTrend', 'Willowlynx Historical Trend', 'willowlynxHistorialTrendData'),
                ('willowlynxHistoricalReport', 'Willowlynx Historical Report', 'willowlynxHistoricalReportData'),
                ('willowlynxSumpPitCCTVCamera', 'Willowlynx Sump Pit CCTV Camera', 'willowlynxSumpPitCCTVCameraData'),
                ('monthlyDatabaseCreation', 'Monthly Database Creation', 'monthlyDatabaseCreationData'),
                ('databaseBackup', 'Database Backup', 'databaseBackupData'),
                ('timeSync', 'Time Sync', 'timeSyncData'),
                ('hotFixes', 'Hot Fixes', 'hotFixesData'),
                ('autoFailOver', 'Auto Fail Over', 'autoFailOverData'),
                ('asaFirewall', 'ASA Firewall', 'asaFirewallData'),
                ('softwarePatch', 'Software Patch', 'softwarePatchData')
            ]
            
            # Generate each component section
            for section_key, section_title, data_key in component_sections:
                section_data = report_data.get(data_key, [])
                if section_data or True:  # Include all sections even if empty for completeness
                    story.extend(self._create_component_section(section_title, section_data, section_key))
                    story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF generated successfully: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Error generating comprehensive PDF: {str(e)}")
            return None
    
    def _create_first_page(self, report_form: Dict, message_data: Dict) -> List:
        """Create first page with report information"""
        story = []
        
        # Company header
        story.append(Paragraph("WILLOWGLEN SERVICES PTE LTD", self.styles['CustomTitle']))
        story.append(Paragraph("Server Preventive Maintenance Report", self.styles['CustomSubtitle']))
        story.append(Spacer(1, 20))
        
        # Report information table
        report_info = [
            ['Report Information', ''],
            ['Job No:', report_form.get('jobNo', 'N/A')],
            ['System Description:', report_form.get('systemDescription', 'N/A')],
            ['Station Name:', report_form.get('stationName', 'N/A')],
            ['Project No:', report_form.get('projectNo', 'N/A')],
            ['Customer:', report_form.get('customer', 'N/A')],
            ['Date of Service:', self.format_date(report_form.get('dateOfService'))],
            ['Generated By:', message_data.get('requested_by', 'System')],
            ['Generated At:', self.format_datetime(message_data.get('timestamp'))]
        ]
        
        table = Table(report_info, colWidths=[3*inch, 4*inch])
        table.setStyle(self._get_info_table_style())
        story.append(table)
        
        return story
    
    def _create_signoff_section(self, report_form: Dict) -> List:
        """Create sign-off section"""
        story = []
        
        story.append(Paragraph("Sign-off Information", self.styles['SectionHeader']))
        story.append(Spacer(1, 10))
        
        sign_off_data = report_form.get('signOffData', {})
        
        signoff_info = [
            ['Sign-off Details', ''],
            ['Attended By:', sign_off_data.get('attendedBy', 'N/A')],
            ['Witnessed By:', sign_off_data.get('witnessedBy', 'N/A')],
            ['Start Date:', self.format_datetime(sign_off_data.get('startDate'))],
            ['Completion Date:', self.format_datetime(sign_off_data.get('completionDate'))],
            ['Remarks:', sign_off_data.get('remarks', 'N/A')]
        ]
        
        table = Table(signoff_info, colWidths=[3*inch, 4*inch])
        table.setStyle(self._get_info_table_style())
        story.append(table)
        
        return story
    
    def _create_component_section(self, section_title: str, section_data: List, section_key: str) -> List:
        """Create a component section with data table"""
        story = []
        
        story.append(Paragraph(section_title, self.styles['SectionHeader']))
        story.append(Spacer(1, 10))
        
        if not section_data:
            story.append(Paragraph("No data available for this section.", self.styles['Normal']))
            return story
        
        # Create data table based on section type
        if section_key == 'serverHealth':
            story.extend(self._create_server_health_table(section_data))
        elif section_key == 'hardDriveHealth':
            story.extend(self._create_hard_drive_table(section_data))
        elif section_key == 'diskUsage':
            story.extend(self._create_disk_usage_table(section_data))
        elif section_key == 'cpuAndRamUsage':
            story.extend(self._create_cpu_ram_table(section_data))
        elif section_key == 'networkHealth':
            story.extend(self._create_network_health_table(section_data))
        else:
            # Generic table for other sections
            story.extend(self._create_generic_data_table(section_data, section_key))
        
        return story
    
    def _create_server_health_table(self, data: List) -> List:
        """Create server health data table"""
        story = []
        
        if not data:
            return [Paragraph("No server health data available.", self.styles['Normal'])]
        
        # Table headers
        headers = ['Component', 'Status', 'Details', 'Checked At']
        table_data = [headers]
        
        for item in data:
            row = [
                item.get('component', 'N/A'),
                item.get('status', 'N/A'),
                item.get('details', 'N/A'),
                self.format_datetime(item.get('checkedAt'))
            ]
            table_data.append(row)
        
        table = Table(table_data, colWidths=[1.5*inch, 1*inch, 2.5*inch, 1.5*inch])
        table.setStyle(self._get_data_table_style())
        story.append(table)
        
        return story
    
    def _create_hard_drive_table(self, data: List) -> List:
        """Create hard drive health data table"""
        story = []
        
        if not data:
            return [Paragraph("No hard drive health data available.", self.styles['Normal'])]
        
        headers = ['Drive', 'Status', 'Capacity', 'Free Space', 'Health']
        table_data = [headers]
        
        for item in data:
            row = [
                item.get('drive', 'N/A'),
                item.get('status', 'N/A'),
                item.get('capacity', 'N/A'),
                item.get('freeSpace', 'N/A'),
                item.get('health', 'N/A')
            ]
            table_data.append(row)
        
        table = Table(table_data, colWidths=[1*inch, 1*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(self._get_data_table_style())
        story.append(table)
        
        return story
    
    def _create_disk_usage_table(self, data: List) -> List:
        """Create disk usage data table"""
        story = []
        
        if not data:
            return [Paragraph("No disk usage data available.", self.styles['Normal'])]
        
        headers = ['Drive', 'Total Size', 'Used Space', 'Free Space', 'Usage %']
        table_data = [headers]
        
        for item in data:
            row = [
                item.get('drive', 'N/A'),
                item.get('totalSize', 'N/A'),
                item.get('usedSpace', 'N/A'),
                item.get('freeSpace', 'N/A'),
                item.get('usagePercentage', 'N/A')
            ]
            table_data.append(row)
        
        table = Table(table_data, colWidths=[1*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1*inch])
        table.setStyle(self._get_data_table_style())
        story.append(table)
        
        return story
    
    def _create_cpu_ram_table(self, data: List) -> List:
        """Create CPU and RAM usage data table"""
        story = []
        
        if not data:
            return [Paragraph("No CPU and RAM usage data available.", self.styles['Normal'])]
        
        headers = ['Component', 'Usage %', 'Status', 'Checked At']
        table_data = [headers]
        
        for item in data:
            row = [
                item.get('component', 'N/A'),
                item.get('usagePercentage', 'N/A'),
                item.get('status', 'N/A'),
                self.format_datetime(item.get('checkedAt'))
            ]
            table_data.append(row)
        
        table = Table(table_data, colWidths=[1.5*inch, 1*inch, 1.5*inch, 2*inch])
        table.setStyle(self._get_data_table_style())
        story.append(table)
        
        return story
    
    def _create_network_health_table(self, data: List) -> List:
        """Create network health data table"""
        story = []
        
        if not data:
            return [Paragraph("No network health data available.", self.styles['Normal'])]
        
        headers = ['Interface', 'Status', 'IP Address', 'Speed', 'Checked At']
        table_data = [headers]
        
        for item in data:
            row = [
                item.get('interface', 'N/A'),
                item.get('status', 'N/A'),
                item.get('ipAddress', 'N/A'),
                item.get('speed', 'N/A'),
                self.format_datetime(item.get('checkedAt'))
            ]
            table_data.append(row)
        
        table = Table(table_data, colWidths=[1.2*inch, 1*inch, 1.5*inch, 1*inch, 1.8*inch])
        table.setStyle(self._get_data_table_style())
        story.append(table)
        
        return story
    
    def _create_generic_data_table(self, data: List, section_key: str) -> List:
        """Create generic data table for other sections"""
        story = []
        
        if not data:
            return [Paragraph(f"No {section_key} data available.", self.styles['Normal'])]
        
        # Try to determine columns from first item
        if data and isinstance(data[0], dict):
            keys = list(data[0].keys())
            # Limit to first 5 columns for readability
            display_keys = keys[:5]
            
            headers = [key.replace('_', ' ').title() for key in display_keys]
            table_data = [headers]
            
            for item in data:
                row = []
                for key in display_keys:
                    value = item.get(key, 'N/A')
                    # Format datetime fields
                    if 'date' in key.lower() or 'time' in key.lower():
                        value = self.format_datetime(value)
                    row.append(str(value))
                table_data.append(row)
            
            # Calculate column widths
            col_width = 6.5 * inch / len(display_keys)
            col_widths = [col_width] * len(display_keys)
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(self._get_data_table_style())
            story.append(table)
        else:
            story.append(Paragraph(f"Data format not supported for {section_key}.", self.styles['Normal']))
        
        return story
    
    def _get_info_table_style(self):
        """Get info table style for report information"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('SPAN', (0, 0), (-1, 0)),  # Merge header row
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
        ])