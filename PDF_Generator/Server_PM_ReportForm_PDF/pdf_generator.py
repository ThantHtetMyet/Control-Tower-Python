import os
import json
import logging
from datetime import datetime
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, BaseDocTemplate, PageTemplate, Frame
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from config import Config

# Configure logging
logger = logging.getLogger(__name__)

class ServerPMPDFGenerator:
    """PDF Generator for Server PM Reports with each component on separate pages"""
    
    def __init__(self):
        self.config = Config()
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
        # Set up header image path
        self.header_image_path = os.path.join(os.path.dirname(__file__), 'resources', 'willowglen_letterhead.png')
        # Known Yes/No GUID fallbacks from API responses
        self.yes_no_guid_map = {
            'b1b20965-91d2-428f-8cc0-292fec170515': 'Yes',
            'd2a176eb-272f-43e1-85e0-23f8b60fcb92': 'No'
        }
        
    def _create_header_canvas(self, canvas, doc):
        """Draw header image on every page with white background and footer"""
        try:
            if os.path.exists(self.header_image_path):
                # Calculate image dimensions and position
                page_width, page_height = A4
                
                # Load and scale the header image
                img = Image(self.header_image_path)
                img_width = page_width - 144  # Leave margins (72 points on each side)
                img_height = 80  # Fixed height for header
                
                # Position at top of page
                x_position = 72  # Left margin
                y_position = page_height - 100  # Top margin
                
                # Draw white background rectangle for header area
                canvas.setFillColor(colors.white)
                canvas.rect(x_position, y_position, img_width, img_height, fill=1, stroke=0)
                
                # Draw the image on top of white background
                canvas.drawImage(self.header_image_path, x_position, y_position, 
                               width=img_width, height=img_height, preserveAspectRatio=True)
                
        except Exception as e:
            logger.warning(f"Could not load header image: {str(e)}")
        
        # Add footer to every page
        self._draw_footer(canvas, doc)
            
    def _draw_footer(self, canvas, doc):
        """Draw footer at the bottom of every page"""
        page_width, page_height = A4
        
        # Footer position
        footer_y = 50  # 50 points from bottom
        
        # Draw horizontal line
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1)
        canvas.line(72, footer_y + 20, page_width - 72, footer_y + 20)
        
        # Company name
        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColor(colors.black)
        company_text = "WILLOWGLEN SERVICES PTE LTD"
        text_width = canvas.stringWidth(company_text, "Helvetica-Bold", 12)
        canvas.drawString((page_width - text_width) / 2, footer_y, company_text)
        
        # Copyright text
        canvas.setFont("Helvetica", 10)
        copyright_text = "Copyright©2023. All rights reserved."
        copyright_width = canvas.stringWidth(copyright_text, "Helvetica", 10)
        canvas.drawString((page_width - copyright_width) / 2, footer_y - 15, copyright_text)
            
    def _create_custom_doc_template(self, pdf_path):
        """Create a custom document template with header image on every page"""
        # Create base document template
        doc = BaseDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=120,  # Increased top margin to accommodate header
            bottomMargin=100  # Increased bottom margin to accommodate footer
        )
        
        # Create frame for content (below header, above footer)
        frame = Frame(
            72,  # left margin
            100,  # bottom margin (increased for footer)
            A4[0] - 144,  # width (page width - left and right margins)
            A4[1] - 220,  # height (page height - top and bottom margins - header and footer space)
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0
        )
        
        # Create page template with header
        page_template = PageTemplate(
            id='normal',
            frames=[frame],
            onPage=self._create_header_canvas
        )
        
        # Add template to document
        doc.addPageTemplates([page_template])
        
        return doc
        
    def setup_custom_styles(self):
        """Setup custom styles for the PDF"""
        # Title style - Blue color to match screenshot
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1976d2')  # Blue color
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1976d2')
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=15,
            spaceBefore=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1976d2'),
            borderWidth=1,
            borderColor=colors.HexColor('#1976d2'),
            borderPadding=5
        ))
        
        # Component title style
        self.styles.add(ParagraphStyle(
            name='ComponentTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            spaceBefore=10,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1976d2')
        ))

    def convert_to_json(self, data):
        """Convert data to JSON string format"""
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error converting data to JSON: {str(e)}")
            return None

    def parse_from_json(self, json_string):
        """Parse data from JSON string format"""
        try:
            return json.loads(json_string)
        except Exception as e:
            logger.error(f"Error parsing JSON string: {str(e)}")
            return None

    def generate_comprehensive_pdf(self, api_response, job_no, report_type="Server_PM"):
        """Generate comprehensive PDF with each component on separate pages matching API response structure"""
        try:
            # Convert API response data to JSON format and back for consistency
            logger.info("Converting API response data to JSON format...")
            json_string = self.convert_to_json(api_response)
            if not json_string:
                logger.error("Failed to convert API response to JSON")
                return None
            
            logger.info("Parsing JSON data for PDF generation...")
            processed_data = self.parse_from_json(json_string)
            if not processed_data:
                logger.error("Failed to parse JSON data")
                return None
            
            logger.info("JSON conversion and parsing completed successfully")
            
            # Get PDF file path
            pdf_path = self.config.get_pdf_path(job_no, report_type)
            
            # Create custom PDF document with header image on every page
            doc = self._create_custom_doc_template(pdf_path)
            
            # Build the story (content)
            story = []
            print ("******** API RESPONSE **************");
            print(processed_data);
            
            # Add first page with report information
            story.extend(self._create_first_page(processed_data))
            
            # Add page break before sign-off page
            story.append(PageBreak())
            
            # Add sign-off information page
            story.extend(self._create_signoff_page(processed_data))
            
            # Component sequence matching API response structure
            components = [
                ('Server Health Check', 'serverHealthData', self._create_server_health_page),
                ('Hard Drive Health Check', 'hardDriveHealthData', self._create_hard_drive_page),
                ('Disk Usage Check', 'diskUsageData', self._create_disk_usage_page),
                ('CPU and RAM Usage Check', 'cpuAndMemoryData', self._create_cpu_memory_page),
                ('Network Health Check', 'networkHealthData', self._create_network_health_page),
                ('Willowlynx Process Status Check', 'willowlynxProcessData', self._create_willowlynx_process_page),
                ('Willowlynx Network Status Check', 'willowlynxNetworkData', self._create_willowlynx_network_page),
                ('Willowlynx RTU Status Check', 'willowlynxRTUData', self._create_willowlynx_rtu_page),
                ('Willowlynx Historical Trend Check', 'willowlynxHistoricalTrendData', self._create_willowlynx_trend_page),
                ('Willowlynx Historical Report Check', 'willowlynxHistoricalReportData', self._create_willowlynx_report_page),
                ('Willowlynx Sump Pit CCTV Camera Check', 'willowlynxCCTVData', self._create_willowlynx_cctv_page),
                ('Monthly Database Creation Check', 'monthlyDatabaseData', self._create_monthly_database_page),
                ('Database Backup Check', 'databaseBackupData', self._create_database_backup_page),
                ('SCADA & Historical Time Sync Check', 'timeSyncData', self._create_time_sync_page),
                ('Hotfixes / Service Packs', 'hotFixesData', self._create_hot_fixes_page),
                ('Auto failover of SCADA server', 'failOverData', self._create_fail_over_page),
                ('ASA Firewall Maintenance', 'asaFirewallData', self._create_asa_firewall_page),
                ('Software Patch Summary', 'softwarePatchData', self._create_software_patch_page)
            ]
            
            for component_title, data_key, page_creator in components:
                component_data = processed_data.get(data_key, [])
                if component_data or True:  # Always create pages even if no data
                    story.append(PageBreak())
                    story.extend(page_creator(component_title, component_data, processed_data))
            
            # Build PDF
            doc.build(story)
            
            logger.info(f"PDF generated successfully: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            return None

    def _create_first_page(self, report_data):
        """Create the first page with report information matching the screenshot layout"""
        story = []
        
        # Get report title dynamically from API response data
        # Check both possible structures for compatibility
        pm_server = report_data.get('pmReportFormServer', {}) or report_data.get('PMReportFormServer', {})
        title_text = pm_server.get('ReportTitle', '') or pm_server.get('reportTitle', 'Preventative Maintenance (SERVER)')
        
        # Add more space to center content vertically on the page
        story.append(Spacer(1, 150))  # Increased spacing to push content to middle
        story.append(Paragraph(title_text, self.styles['CustomTitle']))
        story.append(Spacer(1, 80))   # Increased spacing between title and table
        
        # Get data from API response - using correct field names from terminal output
        report_form = report_data.get('reportForm', {}) or report_data.get('ReportForm', {})
        
        # Extract job number from the correct location in API response
        job_no = report_form.get('jobNo', '') or report_form.get('JobNo', '')
        
        # Merged table with Job No as first row and other information
        merged_data = [
            ['Job No:', job_no],
            ['System Description:', report_form.get('systemDescription', '')],
            ['Station Name:', report_form.get('stationName', '')],
            ['Customer:', pm_server.get('customer', '')],
            ['Project No:', pm_server.get('projectNo', '')]
        ]

        # Create single merged table
        merged_table = Table(merged_data, colWidths=[2.2*inch, 3.8*inch])
        merged_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),  # Labels column
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),  # Values column
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica'),  # Job No row bold
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEWIDTH', (0, 0), (-1, -1), 1),
        ]))

        # Center the table on the page
        merged_table.hAlign = 'CENTER'
        story.append(merged_table)
        story.append(Spacer(1, 150))  # Add space after table to balance the page

        return story

    def _create_signoff_page(self, report_data):
        """Create sign-off information page matching the screenshot layout"""
        story = []
        
        # Get sign-off data from the API response structure
        # The actual sign-off data is nested inside pmReportFormServer
        pm_report_form_server = report_data.get('pmReportFormServer', {})
        
        # Get the signOffData from inside pmReportFormServer (this has the actual data)
        signoff_data = pm_report_form_server.get('signOffData', {})
        
        # Extract sign-off information from the correct nested structure
        attended_by = signoff_data.get('attendedBy', '')
        witnessed_by = signoff_data.get('witnessedBy', '')
        start_date = signoff_data.get('startDate', '')  # Note: it's 'startDate', not 'attendedDate'
        completion_date = signoff_data.get('completionDate', '')  # Note: it's 'completionDate', not 'witnessedDate'
        remarks = signoff_data.get('remarks', '')
        
        # Add some top spacing
        story.append(Spacer(1, 40))
        
        # Personnel Information Section - Fixed alignment with single row tables
        attended_by_data = [
            ['ATTENDED BY', attended_by],
            ['(WILLOWGLEN)', '']
        ]
        
        attended_table = Table(attended_by_data, colWidths=[2*inch, 4*inch])
        attended_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Ensure vertical alignment
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),  # Underline for signature on first row
        ]))
        
        story.append(attended_table)
        story.append(Spacer(1, 30))
        
        witnessed_by_data = [
            ['WITNESSED BY', witnessed_by],
            ['(CUSTOMER)', '']
        ]
        
        witnessed_table = Table(witnessed_by_data, colWidths=[2*inch, 4*inch])
        witnessed_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Ensure vertical alignment
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),  # Underline for signature on first row
        ]))
        
        story.append(witnessed_table)
        story.append(Spacer(1, 40))
        
        # Schedule Information Section - Fixed alignment
        start_date_data = [
            ['START DATE/TIME', self._format_date(start_date)]
        ]
        
        start_date_table = Table(start_date_data, colWidths=[2*inch, 4*inch])
        start_date_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Ensure vertical alignment
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),  # Underline for date field
        ]))
        
        story.append(start_date_table)
        story.append(Spacer(1, 30))
        
        completion_date_data = [
            ['COMPLETION DATE/TIME', self._format_date(completion_date)]
        ]
        
        completion_date_table = Table(completion_date_data, colWidths=[2*inch, 4*inch])
        completion_date_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Ensure vertical alignment
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (1, 0), (1, 0), 1, colors.black),  # Underline for date field
        ]))
        
        story.append(completion_date_table)
        story.append(Spacer(1, 60))
        
        # Remarks Section with title outside the box
        if remarks:
            # Create a custom style for italic remark title - make it more prominent
            remark_title_style = ParagraphStyle(
                'RemarkTitle',
                parent=self.styles['Normal'],
                fontSize=12,  # Slightly larger font
                fontName='Helvetica-BoldOblique',  # Bold italic for better distinction
                textColor=colors.black,
                alignment=TA_LEFT,
                spaceAfter=8,  # Space after title before box
                spaceBefore=0,  # No space before title
                leftIndent=15,  # Match the left padding of the box
                rightIndent=0,
                leading=12  # Tight line spacing
            )
            
            # Create the remarks title (no underline)
            remark_title = Paragraph("Remark", remark_title_style)
            
            # Add title to story
            story.append(remark_title)
            
            # Create remarks text with some top margin to separate from title
            remarks_text_style = ParagraphStyle(
                'RemarksText',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceBefore=0,
                spaceAfter=0
            )
            remarks_content = Paragraph(remarks, remarks_text_style)
            
            # Create a container table for just the remarks content
            remarks_container = Table([
                [remarks_content]
            ], colWidths=[6*inch])
            
            remarks_container.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
            ]))
            
            story.append(remarks_container)
        story.append(Spacer(1, 60))

        return story

    def _create_server_health_page(self, title, data, report_data):
        """Create server health page matching the UI design"""
        story = []
        
        # 1. Create title section with consistent left alignment
        story.append(self._build_left_aligned_title("Server Health Check"))
        story.append(Spacer(1, 6))
        
        # 2. Add instructions
        instructions_text = """
        <b>Check Instructions:</b><br/><br/>
        Check Server Front Panel LED Number 2, as shown below. Check LED 2 in solid green, which indicates the server is healthy.
        """
        story.append(Paragraph(instructions_text, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # 3. Add component image (smaller size to prevent remarks from jumping to next page)
        image_path = Path(f"resources/ServerPMReportForm/ServerHealth.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=3.5*inch, height=2*inch)
                img.hAlign = 'CENTER'
                
                # Create a bordered frame for the image
                image_table = Table([[img]], colWidths=[4*inch])
                image_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e9ecef')),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(image_table)
                story.append(Spacer(1, 20))
            except Exception as e:
                logger.warning(f"Could not load server health reference image: {e}")
        
        # 4. Create data table with enhanced styling
        if not data:
            # No data message with proper styling
            no_data_box = Table([
                [
                    Paragraph(
                        "No server health data available",
                        ParagraphStyle(
                            'NoDataText',
                            parent=self.styles['Normal'],
                            textColor=colors.HexColor('#666666'),
                            alignment=TA_CENTER
                        )
                    )
                ]
            ], colWidths=[6*inch])
            no_data_box.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9f9f9')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('TOPPADDING', (0, 0), (-1, -1), 30),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 30),
            ]))
            story.append(no_data_box)
            return story
        
        # Data table structure
        table_data = [['Server Name', 'Result Status']]  # Headers
        remarks_text = ""
        
        # Process data
        for health_record in data:
            if isinstance(health_record, dict) and 'details' in health_record:
                # Store remarks
                if health_record.get('remarks'):
                    remarks_text = health_record['remarks']
                
                # Process server details
                for detail in health_record['details']:
                    server_name = detail.get('serverName', '')
                    status = detail.get('resultStatusName', '') or ''

                    # Sanitize status: remove any leading square/bullet characters, control chars and trim
                    # Common bullet/box chars: ■ □ ▪ • · and non-breaking spaces
                    if not isinstance(status, str):
                        status = str(status or '')
                    # Remove common box/bullet characters anywhere and non-breaking spaces
                    status = status.replace('\u00A0', ' ')
                    status = re.sub(r'[\u25A0\u25A1\u25AA\u2022\u2023\u00B7\u00A0\uFEFF\u2024\u2027•▪·]', '', status)
                    # Also strip any remaining leading non-alphanumeric characters (like stray boxes or bullets)
                    status = re.sub(r'^[^\w\d%]+', '', status).strip()

                    table_data.append([server_name, status or 'N/A'])
        
        # Create the styled table
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[3*inch, 3*inch])
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                
                # Borders
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ]))
            story.append(table)
            story.append(Spacer(1, 20))
        
        # 5. Remarks Section with enhanced styling
        if remarks_text:
            self._add_remarks_section(story, remarks_text)

        return story

    def _create_hard_drive_page(self, title, data, report_data):
        """Create hard drive health page matching ServerHealthCheck layout: title -> instruction -> image -> table -> remarks"""
        story = []
        
        # Section title matches other components (left aligned, blue)
        story.append(self._build_left_aligned_title(title))
        story.append(Spacer(1, 8))
        
        # 2. Add instructions aligned with title
        story.append(Paragraph(
            "Check Hard Drive Health Status LED, LED in solid/blinking green, which indicates healthy.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 8))
        
        # 3. Add component image with proper styling
        image_path = Path(f"resources/ServerPMReportForm/HardDriveHealth.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=4*inch, height=2.5*inch)
                img.hAlign = 'CENTER'
                
                # Create a bordered frame for the image matching the UI styling
                image_table = Table([[img]], colWidths=[6*inch])
                image_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e9ecef')),
                    ('TOPPADDING', (0, 0), (-1, -1), 15),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                    ('LEFTPADDING', (0, 0), (-1, -1), 15),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                    ('BOTTOMMARGIN', (0, 0), (-1, -1), 15),
                ]))
                story.append(image_table)
                story.append(Spacer(1, 15))
                
                # Add additional instruction after image
                post_image_text = Paragraph("<b>Check if the LED is in solid/blinking green</b>", self.styles['Normal'])
                story.append(post_image_text)
                story.append(Spacer(1, 15))
            except Exception as e:
                logger.warning(f"Could not load hard drive reference image: {e}")
        
        # 4. Create data table - matching ServerHealthCheck format
        if not data:
            # No data message - matching ServerHealthCheck
            no_data_table = Table([["No hard drive health data available"]], colWidths=[6*inch])
            no_data_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9f9f9')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cccccc')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ]))
            story.append(no_data_table)
            return story
        
        # Create table headers - matching ServerHealthCheck
        headers = ['Server Name', 'Result Status']
        table_data = [headers]
        
        # Handle the nested structure from API response
        remarks_text = ""
        for health_record in data:
            if isinstance(health_record, dict) and 'details' in health_record:
                # Store remarks for later display
                if health_record.get('remarks'):
                    remarks_text = health_record['remarks']
                
                # Process details (matching web component data structure)
                for detail in health_record['details']:
                    server_name = detail.get('serverName', '')
                    status = detail.get('resultStatusName', '')
                    
                    # Format status without square box indicators (plain text only) - matching ServerHealthCheck
                    table_data.append([server_name, status])
        
        # Create table with improved styling - matching ServerHealthCheck exactly
        if len(table_data) > 1:
            col_widths = [3*inch, 3*inch]
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                # Header styling - matching ServerHealthCheck
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling - matching ServerHealthCheck
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                
                # Grid and borders - matching ServerHealthCheck
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e0e0e0')),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
        else:
            # No records message - matching ServerHealthCheck
            no_records_table = Table([["No hard drive health records available"]], colWidths=[6*inch])
            no_records_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ]))
            story.append(no_records_table)
            story.append(Spacer(1, 20))
        
        # 5. Remarks Section with title outside the box - matching ServerHealthCheck exactly
        if remarks_text:
            # Create a custom style for italic remark title - matching ServerHealthCheck
            remark_title_style = ParagraphStyle(
                'RemarkTitle',
                parent=self.styles['Normal'],
                fontSize=12,  # Slightly larger font
                fontName='Helvetica-BoldOblique',  # Bold italic for better distinction
                textColor=colors.black,
                alignment=TA_LEFT,
                spaceAfter=8,  # Space after title before box
                spaceBefore=0,  # No space before title
                leftIndent=15,  # Match the left padding of the box
                rightIndent=0,
                leading=12  # Tight line spacing
            )
            
            # Create the remarks title (no underline) - matching ServerHealthCheck
            remark_title = Paragraph("Remark", remark_title_style)
            
            # Add title to story
            story.append(remark_title)
            
            # Create remarks text with some top margin to separate from title
            remarks_text_style = ParagraphStyle(
                'RemarksText',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceBefore=0,
                spaceAfter=0
            )
            remarks_content = Paragraph(remarks_text, remarks_text_style)
            
            # Create a container table for just the remarks content - matching ServerHealthCheck
            remarks_container = Table([
                [remarks_content]
            ], colWidths=[6*inch])
            
            remarks_container.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
            ]))
            
            story.append(remarks_container)
        
        return story

    def _create_disk_usage_page(self, title, data, report_data):
        """Create disk usage check page matching established UI flow pattern"""
        story = []
        
        # Section title
        story.append(self._build_left_aligned_title(title))
        story.append(Spacer(1, 8))
        
        # 2. Add instructions - matching Server Health Check format
        # 2. Add instructions section in a gray box with border
        instructions_box_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
        ])
        
        instructions_content = []
        instructions_content.append(Paragraph("<b>Using Computer Management</b>", self.styles['Normal']))
        instructions_content.append(Spacer(1, 6))
        instructions_text = """
        - From Control Panel -> Administration Tools -> Computer Management.<br/>
        - Click on the Storage -> Disk Management. Check the status for all the hard disks.<br/>
        - Remove old Windows event logs to meet the target disk usage limit.
        """
        instructions_content.append(Paragraph(instructions_text, self.styles['Normal']))
        
        instructions_table = Table([[instructions_content]], colWidths=[6*inch])
        instructions_table.setStyle(instructions_box_style)
        story.append(instructions_table)
        story.append(Spacer(1, 15))
        
        # Add important note in a yellow box with left border accent
        note_box_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff3cd')),  # Light yellow background
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#ffeaa7')),  # Border color
            ('LEFTBORDER', (0, 0), (0, -1), 4, colors.HexColor('#fdcb6e')),  # Left accent border
        ])
        
        note_text = """
        * Note: The HDSRS servers with SQL Server Database keep the historical data and daily/weekly/monthly backups. The disk space usage can be up to 90%, which is considered as normal.
        """
        note_table = Table([[Paragraph(note_text, self.styles['Normal'])]], colWidths=[6*inch])
        note_table.setStyle(note_box_style)
        story.append(note_table)
        story.append(Spacer(1, 15))
        
        # 3. Add component image (smaller size to prevent remarks from jumping to next page) - matching Server Health Check
        image_path = Path(f"resources/ServerPMReportForm/DiskUsage.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=3.5*inch, height=2*inch)
                img.hAlign = 'CENTER'
                
                # Create a bordered frame for the image - matching Server Health Check exactly
                image_frame = Table([[img]], colWidths=[4*inch])
                image_frame.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(image_frame)
                story.append(Spacer(1, 15))
            except Exception as e:
                print(f"Could not load disk usage reference image: {e}")
                pass
        
        # 4. Data Table - Process disk usage data matching DiskUsage component structure
        if not data:
            # No data message table (matching Server Health Check style)
            no_data_table = Table([["No disk usage data available"]], colWidths=[6*inch])
            no_data_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#666666')),
                ('TOPPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
            ]))
            story.append(no_data_table)
        else:
            # Handle nested structure from API response
            all_disks = []
            for usage_record in data:
                if isinstance(usage_record, dict):
                    # Process details
                    if 'details' in usage_record and isinstance(usage_record['details'], list):
                        all_disks.extend(usage_record['details'])
                    else:
                        # Handle direct structure for backward compatibility
                        all_disks.append(usage_record)
            
            # Group disks by server name (matching web component logic)
            grouped_by_server = {}
            for item in all_disks:
                if isinstance(item, dict):
                    server_name = item.get('serverName', 'Unknown Server')
                    if server_name not in grouped_by_server:
                        grouped_by_server[server_name] = []
                    grouped_by_server[server_name].append(item)
            
            if grouped_by_server:
                # Create tables for each server
                for server_name, disks in grouped_by_server.items():
                    # Server header
                    server_header = f"{server_name}: - Disk Capacity:"
                    story.append(Paragraph(server_header, self.styles['SectionHeader']))
                    story.append(Spacer(1, 6))
                    
                    # Create disk table for this server (matching DiskUsage component columns)
                    table_data = [['Disk', 'Status', 'Capacity', 'Free Space', 'Usage %', 'Check']]
                    
                    for disk in disks:
                        disk_name = disk.get('diskName', disk.get('disk', ''))
                        status = disk.get('serverDiskStatusName', disk.get('status', ''))
                        capacity = disk.get('capacity', disk.get('totalSize', ''))
                        free_space = disk.get('freeSpace', disk.get('freeSize', ''))
                        usage_percentage = disk.get('usage', disk.get('usagePercentage', ''))
                        check_result = disk.get('resultStatusName', disk.get('check', ''))
                        
                        table_data.append([
                            str(disk_name) if disk_name else '',
                            str(status) if status else '', 
                            str(capacity) if capacity else '',
                            str(free_space) if free_space else '', 
                            str(usage_percentage) if usage_percentage else '', 
                            str(check_result) if check_result else ''
                        ])
                    
                    # Create table with exact styling as Server Health Check
                    col_width = 6.5 * inch / 6
                    table = Table(table_data, colWidths=[col_width] * 6)
                    table.setStyle(TableStyle([
                        # Header styling - gray background, black text
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('TOPPADDING', (0, 0), (-1, 0), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        
                        # Data rows styling - white background, black text
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('TOPPADDING', (0, 1), (-1, -1), 6),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                        
                        # Grid and borders
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('BOX', (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))
            else:
                # No data message table
                no_data_table = Table([["No disk usage records available"]], colWidths=[6*inch])
                no_data_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#666666')),
                    ('TOPPADDING', (0, 0), (-1, -1), 20),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
                ]))
                story.append(no_data_table)
        
        story.append(Spacer(1, 12))
        
        # 5. Remarks Section - Extract remarks from data and display with consistent styling
        remarks_text = ""
        if data:
            for usage_record in data:
                if isinstance(usage_record, dict) and usage_record.get('remarks'):
                    remarks_text = usage_record['remarks']
                    break
        
        if not remarks_text:
            remarks_text = "No specific remarks for disk usage check."
        
        # Remarks title (matching Server Health Check - no colon, left-aligned)
        remarks_title_style = ParagraphStyle(
            'RemarkTitle',
            parent=self.styles['Normal'],
            fontName='Helvetica-BoldOblique',
            fontSize=11,
            leftIndent=15,
            spaceAfter=6,
            alignment=0  # Left alignment
        )
        story.append(Paragraph("Remark", remarks_title_style))
        
        # Remarks content styling
        remarks_text_style = ParagraphStyle(
            'RemarksText',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=0,
            alignment=0  # Left alignment
        )
        remarks_content = Paragraph(remarks_text, remarks_text_style)
        
        # Create a container table for just the remarks content - matching Server Health Check
        remarks_container = Table([
            [remarks_content]
        ], colWidths=[6*inch])
        
        remarks_container.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
        ]))
        
        story.append(remarks_container)
        
        return story

    def _create_cpu_memory_page(self, title, data, report_data):
        """Create CPU and memory usage page matching CPUAndRamUsage_Details.js structure"""
        story = []

        # Section title
        story.append(self._build_left_aligned_title(title))
        story.append(Spacer(1, 8))
        
        # 2. Add instructions section matching web component format
        instructions_text = """
        <b>Using Task Manager, go to Performance Tab</b><br/>
        - Right click on the task bar and select Task Manager.
        """
        story.append(Paragraph(instructions_text, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # 3. Reference image
        image_path = Path(f"resources/ServerPMReportForm/CPUAndRamUsage.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=3.5*inch, height=2*inch)
                img.hAlign = 'CENTER'
                
                # Create a bordered frame for the image - matching Server Health Check exactly
                image_frame = Table([[img]], colWidths=[4*inch])
                image_frame.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(image_frame)
                story.append(Spacer(1, 15))
            except Exception as e:
                print(f"Could not load CPU and RAM usage reference image: {e}")
                pass

        # Styles to support wrapped table headers/cells
        header_style = ParagraphStyle(
            'CPUTableHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            alignment=TA_CENTER
        )
        cell_left_style = ParagraphStyle(
            'CPUTableCellLeft',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            alignment=TA_LEFT
        )
        cell_center_style = ParagraphStyle(
            'CPUTableCellCenter',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=11,
            alignment=TA_CENTER
        )
        
        # 4. Data Table - Process CPU and memory data matching CPUAndRamUsage component structure
        if data and len(data) > 0:
            # Handle nested structure from API response
            all_records = []
            for usage_record in data:
                if isinstance(usage_record, dict):
                    # Process details
                    if 'details' in usage_record and isinstance(usage_record['details'], list):
                        all_records.extend(usage_record['details'])
                    else:
                        # Handle direct structure for backward compatibility
                        all_records.append(usage_record)
            
            for record_index, record in enumerate(all_records):
                if isinstance(record, dict):
                    # Add record separator if multiple records
                    if record_index > 0:
                        story.append(Spacer(1, 15))
                    
                    # Memory Usage Details Section
                    memory_details = record.get('memoryUsageDetails', [])
                    if memory_details:
                        memory_title = "Memory Usage Check:"
                        story.append(Paragraph(memory_title, self.styles['SectionHeader']))
                        story.append(Spacer(1, 6))
                        
                        header_row = [
                            Paragraph('S/N', header_style),
                            Paragraph('Machine Name', header_style),
                            Paragraph('Memory Size', header_style),
                            Paragraph('Memory In Use<br/>(%)', header_style),
                            Paragraph('Memory In Use < 90%?<br/><font size="8">Historical server < 90%?</font>', header_style)
                        ]
                        memory_table_data = [header_row]
                        
                        for detail_index, detail in enumerate(memory_details):
                            serial_no = detail.get('serialNo', str(detail_index + 1))
                            server_name = detail.get('serverName', '')
                            memory_size = detail.get('memorySize', '')
                            memory_usage = detail.get('memoryUsagePercentage', '')
                            result_status = detail.get('resultStatusName', '')
                            
                            memory_usage_display = f"{memory_usage}%" if memory_usage else ''
                            
                            memory_table_data.append([
                                Paragraph(str(serial_no) if serial_no else '', cell_center_style),
                                Paragraph(str(server_name) if server_name else '', cell_left_style),
                                Paragraph(str(memory_size) if memory_size else '', cell_center_style),
                                Paragraph(str(memory_usage_display) if memory_usage_display else '', cell_center_style),
                                Paragraph(str(result_status) if result_status else '', cell_center_style)
                            ])
                        
                        col_widths = [0.6*inch, 2.1*inch, 1.0*inch, 1.0*inch, 1.8*inch]
                        memory_table = Table(memory_table_data, colWidths=col_widths)
                        memory_table.setStyle(TableStyle([
                            # Header styling - gray background, black text
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('TOPPADDING', (0, 0), (-1, 0), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('LEFTPADDING', (0, 0), (-1, -1), 8),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                            
                            # Data rows styling - white background, black text
                            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 9),
                            ('TOPPADDING', (0, 1), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                            
                            # Grid and borders
                            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
                        ]))
                        story.append(memory_table)
                        story.append(Spacer(1, 15))
                    
                    # CPU Usage Details Section
                    cpu_details = record.get('cpuUsageDetails', [])
                    if cpu_details:
                        cpu_title = "CPU Usage Check:"
                        story.append(Paragraph(cpu_title, self.styles['SectionHeader']))
                        story.append(Spacer(1, 6))
                        
                        cpu_header_row = [
                            Paragraph('S/N', header_style),
                            Paragraph('Machine Name', header_style),
                            Paragraph('CPU Usage<br/>(%)', header_style),
                            Paragraph('CPU Usage < 50%?', header_style)
                        ]
                        cpu_table_data = [cpu_header_row]
                        
                        for detail_index, detail in enumerate(cpu_details):
                            serial_no = detail.get('serialNo', str(detail_index + 1))
                            server_name = detail.get('serverName', '')
                            cpu_usage = detail.get('cpuUsagePercentage', '')
                            result_status = detail.get('resultStatusName', '')
                            
                            cpu_usage_display = f"{cpu_usage}%" if cpu_usage else ''
                            
                            cpu_table_data.append([
                                Paragraph(str(serial_no) if serial_no else '', cell_center_style),
                                Paragraph(str(server_name) if server_name else '', cell_left_style),
                                Paragraph(str(cpu_usage_display) if cpu_usage_display else '', cell_center_style),
                                Paragraph(str(result_status) if result_status else '', cell_center_style)
                            ])
                        
                        col_widths = [0.6*inch, 2.5*inch, 1.1*inch, 2.3*inch]
                        cpu_table = Table(cpu_table_data, colWidths=col_widths)
                        cpu_table.setStyle(TableStyle([
                            # Header styling - gray background, black text
                            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('TOPPADDING', (0, 0), (-1, 0), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('LEFTPADDING', (0, 0), (-1, -1), 8),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                            
                            # Data rows styling - white background, black text
                            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 9),
                            ('TOPPADDING', (0, 1), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                            
                            # Grid and borders
                            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d0d0d0')),
                        ]))
                        story.append(cpu_table)
                        story.append(Spacer(1, 15))
                    
                    # No details message if neither CPU nor memory data available
                    if not memory_details and not cpu_details:
                        no_details_text = "No CPU or memory usage details available for this record"
                        story.append(Paragraph(no_details_text, self.styles['Normal']))
                        story.append(Spacer(1, 15))
        else:
            no_data_text = "No CPU and memory usage data available"
            story.append(Paragraph(no_data_text, self.styles['Normal']))
            story.append(Spacer(1, 15))
        
        # 6. Remarks section - matching previous sections pattern
        remarks = ""
        if data and len(data) > 0:
            for usage_record in data:
                if isinstance(usage_record, dict) and usage_record.get('remarks'):
                    remarks = usage_record['remarks']
                    break
        
        self._add_remarks_section(story, remarks)
        
        return story

    def _create_network_health_page(self, title, data, report_data):
        """Create a network health page that mirrors NetworkHealth_Details.js"""
        story = []

        # Section title aligned with other content
        story.append(self._build_left_aligned_title(title))
        story.append(Spacer(1, 6))

        record = self._extract_first_item(data)
        if not record:
            story.append(Paragraph("No network health data available", self.styles['Normal']))
            return story

        # Header row with Ring Network Check title and right-aligned date box
        header_label_style = ParagraphStyle(
            'NetworkHeaderLabel',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold'
        )
        date_label_style = ParagraphStyle(
            'NetworkDateLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        )
        date_value_style = ParagraphStyle(
            'NetworkDateValue',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER
        )

        formatted_date = self._format_date(record.get('dateChecked') or record.get('DateChecked')) or 'N/A'
        date_box = Table([[Paragraph(formatted_date, date_value_style)]], colWidths=[1.45*inch])
        date_box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1976d2')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f6ff')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        header_row = Table(
            [[
                Paragraph("Ring Network Check.", header_label_style),
                Paragraph("Date Checked:", date_label_style),
                date_box
            ]],
            colWidths=[3.75*inch, 1.0*inch, 1.45*inch]
        )
        header_row.hAlign = 'LEFT'
        header_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(header_row)
        story.append(Spacer(1, 6))

        # Procedure block
        label_style = ParagraphStyle('NetworkLabel', parent=self.styles['Normal'], fontName='Helvetica-Bold')
        indent_style = ParagraphStyle('NetworkIndent', parent=self.styles['Normal'], leftIndent=12)

        story.append(Paragraph("Procedure:", label_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Observe the ring and ring master LED on the network switch.", indent_style))
        story.append(Spacer(1, 10))

        # Result section with inline Yes/No box
        status_text = self._format_status_badge(
            record.get('yesNoStatusName') or record.get('result') or self._get_status_label(record.get('yesNoStatusID'))
        )
        story.append(Paragraph("Result:", label_style))
        story.append(Spacer(1, 4))

        description = Paragraph("Ring and ring master LED should be green (stable).", indent_style)
        status_box = Table([[Paragraph(status_text, date_value_style)]], colWidths=[1.3*inch], rowHeights=[0.35*inch])
        status_box.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1976d2')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8f1ff')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        result_table = Table([[description, status_box]], colWidths=[4.9*inch, 1.4*inch])
        result_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(result_table)
        story.append(Spacer(1, 6))

        story.append(Paragraph(
            "If the answer is 'No', please use topology viewer (Oring software) to check if any switch in the ring has connectivity problem.",
            indent_style
        ))
        story.append(Spacer(1, 12))

        self._add_remarks_section(story, record.get('remarks'))
        return story

    def _create_willowlynx_process_page(self, title, data, report_data):
        """Create Willowlynx process status page mirroring the web UI"""
        story = []
        story.append(self._build_left_aligned_title(title))
        story.append(Paragraph("Process Status", ParagraphStyle(
            'ProcessSubheading',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            spaceAfter=6
        )))

        record = self._extract_first_item(data)
        if not record:
            no_data_box = Table([[Paragraph(
                "No Willowlynx Process Status data available",
                ParagraphStyle('ProcessNoData', parent=self.styles['Normal'], alignment=TA_CENTER, textColor=colors.HexColor('#666666'))
            )]], colWidths=[6*inch])
            no_data_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9f9f9')),
                ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#dddddd')),
                ('TOPPADDING', (0, 0), (-1, -1), 18),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 18),
            ]))
            story.append(no_data_box)
            return story

        story.append(Paragraph(
            'Login into Willowlynx and navigate to the "Server Status" page, as shown below.',
            self.styles['Normal']
        ))
        story.append(Spacer(1, 10))
        self._add_reference_image(story, "WillowlynxProcessStatus.png")

        result_text = self._format_status_badge(
            record.get('yesNoStatusName') or record.get('resultStatusName') or record.get('result')
        )
        story.append(Paragraph("Result:", ParagraphStyle(
            'ProcessResultLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            spaceAfter=4
        )))
        result_description = Paragraph(
            "All process services should be online, either ACTIVE or STANDBY.",
            self.styles['Normal']
        )
        chip_bg, chip_text = self._get_status_chip_colors(result_text)
        chip = Table([[Paragraph(result_text or 'N/A', ParagraphStyle(
            'ProcessChipText',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=chip_text,
            fontName='Helvetica-Bold'
        ))]], colWidths=[1.2*inch])
        chip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), chip_bg),
            ('BOX', (0, 0), (-1, -1), 0.8, chip_text),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        result_row = Table([[result_description, chip]], colWidths=[4.8*inch, 1.3*inch])
        result_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(result_row)
        story.append(Spacer(1, 12))

        self._add_remarks_section(story, record.get('remarks'))
        return story

    def _create_willowlynx_network_page(self, title, data, report_data):
        """Create Willowlynx network status page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        record = self._extract_first_item(data)
        if not record:
            story.append(Paragraph("No Willowlynx network status data available", self.styles['Normal']))
            return story

        story.append(Paragraph(
            "Check the system overview page to ensure all servers, switches, and RTUs are green.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 10))
        self._add_reference_image(story, "WillowlynxNetworkStatus.png")

        status_text = self._format_status_badge(
            record.get('yesNoStatusName') or record.get('resultStatusName') or record.get('result')
        )
        story.append(Paragraph("Result:", ParagraphStyle(
            'WillowlynxNetworkResultLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            spaceAfter=4
        )))
        description = Paragraph("All servers, switches, and RTU are green.", self.styles['Normal'])
        chip_bg, chip_text = self._get_status_chip_colors(status_text)
        chip = Table([[Paragraph(status_text or 'N/A', ParagraphStyle(
            'WillowlynxNetworkChip',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=chip_text,
            fontName='Helvetica-Bold'
        ))]], colWidths=[1.1*inch])
        chip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), chip_bg),
            ('BOX', (0, 0), (-1, -1), 0.8, chip_text),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        result_row = Table([[description, chip]], colWidths=[4.9*inch, 1.3*inch])
        result_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(result_row)
        story.append(Spacer(1, 12))
        self._add_remarks_section(story, record.get('remarks'))
        return story

    def _create_willowlynx_rtu_page(self, title, data, report_data):
        """Create Willowlynx RTU status page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        record = self._extract_first_item(data)
        if not record:
            story.append(Paragraph("No Willowlynx RTU status data available", self.styles['Normal']))
            return story

        story.append(Paragraph("Instructions:", ParagraphStyle(
            'WillowlynxRTUInstructionLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold'
        )))
        story.append(Paragraph(
            "Check the RTU Device Status page. RTU status and PLC status shall be green.",
            ParagraphStyle('WillowlynxRTUInstruction', parent=self.styles['Normal'], leftIndent=12)
        ))
        story.append(Spacer(1, 10))
        self._add_reference_image(story, "WillowlynxRTUStatus.png")

        status_text = self._format_status_badge(
            record.get('YesNoStatusName') or record.get('yesNoStatusName') or record.get('result')
        )
        story.append(Paragraph("Result:", ParagraphStyle(
            'WillowlynxRTUResultLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            spaceAfter=4
        )))
        rtu_description = Paragraph("RTU status and PLC status are green.", self.styles['Normal'])
        chip_bg, chip_text = self._get_status_chip_colors(status_text)
        rtu_chip = Table([[Paragraph(status_text or 'N/A', ParagraphStyle(
            'WillowlynxRTUChip',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=chip_text,
            fontName='Helvetica-Bold'
        ))]], colWidths=[1.1*inch])
        rtu_chip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), chip_bg),
            ('BOX', (0, 0), (-1, -1), 0.8, chip_text),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        rtu_row = Table([[rtu_description, rtu_chip]], colWidths=[4.9*inch, 1.3*inch])
        rtu_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(rtu_row)
        story.append(Spacer(1, 12))
        self._add_remarks_section(story, record.get('remarks') or record.get('Remarks'))
        return story

    def _create_willowlynx_trend_page(self, title, data, report_data):
        """Create Willowlynx historical trend page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        record = self._extract_first_item(data)
        if not record:
            story.append(Paragraph("No Willowlynx historical trend data available", self.styles['Normal']))
            return story

        story.append(Paragraph("Instructions:", ParagraphStyle(
            'WillowlynxTrendInstructionLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold'
        )))
        story.append(Paragraph(
            "Randomly select some analog measurement points, open the trend view, and confirm the trend displays without errors.",
            ParagraphStyle('WillowlynxTrendInstruction', parent=self.styles['Normal'])
        ))
        story.append(Spacer(1, 12))

        status_text = self._format_status_badge(
            record.get('yesNoStatusName')
            or record.get('YesNoStatusID')
            or self._get_status_label(record.get('yesNoStatusID'))
        )
        story.append(Paragraph("Result:", ParagraphStyle(
            'WillowlynxTrendResultLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            spaceAfter=4
        )))
        trend_description = Paragraph("Trends can be displayed without issues.", self.styles['Normal'])
        chip_bg, chip_text = self._get_status_chip_colors(status_text)
        trend_chip = Table([[Paragraph(status_text or 'N/A', ParagraphStyle(
            'WillowlynxTrendChip',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=chip_text,
            fontName='Helvetica-Bold'
        ))]], colWidths=[1.1*inch])
        trend_chip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), chip_bg),
            ('BOX', (0, 0), (-1, -1), 0.8, chip_text),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        trend_row = Table([[trend_description, trend_chip]], colWidths=[4.9*inch, 1.3*inch])
        trend_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(trend_row)
        story.append(Spacer(1, 12))

        self._add_remarks_section(story, record.get('remarks') or record.get('Remarks'))
        return story

    def _create_willowlynx_report_page(self, title, data, report_data):
        """Create Willowlynx historical report page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        record = self._extract_first_item(data)
        if not record:
            story.append(Paragraph("No Willowlynx historical report data available", self.styles['Normal']))
            return story

        story.append(Paragraph(
            "Click the CTHistReport icon on an HMI, open the Historical Report module, and ensure analog, digital, and alarm reports can be displayed.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 10))
        self._add_reference_image(story, "WillowlynxHistoricalReport.png", width=3*inch, height=1.75*inch)

        status_text = self._format_status_badge(
            record.get('yesNoStatusName')
            or record.get('resultStatusName')
            or self._get_status_label(record.get('yesNoStatusID'))
        )
        story.append(Paragraph("Result:", ParagraphStyle(
            'WillowlynxReportResultLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            spaceAfter=4
        )))
        report_description = Paragraph("All reports can be displayed without issues.", self.styles['Normal'])
        chip_bg, chip_text = self._get_status_chip_colors(status_text)
        report_chip = Table([[Paragraph(status_text or 'N/A', ParagraphStyle(
            'WillowlynxReportChip',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=chip_text,
            fontName='Helvetica-Bold'
        ))]], colWidths=[1.1*inch])
        report_chip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), chip_bg),
            ('BOX', (0, 0), (-1, -1), 0.8, chip_text),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        report_row = Table([[report_description, report_chip]], colWidths=[4.9*inch, 1.3*inch])
        report_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(report_row)
        story.append(Spacer(1, 12))

        self._add_remarks_section(story, record.get('remarks') or record.get('Remarks'))
        return story

    def _create_willowlynx_cctv_page(self, title, data, report_data):
        """Create Willowlynx CCTV camera page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        record = self._extract_first_item(data)
        if not record:
            story.append(Paragraph("No Willowlynx CCTV camera data available", self.styles['Normal']))
            return story

        story.append(Paragraph(
            "Click the CCTV buttons from the PLUMB-SAN page to confirm the player window for each camera can be played.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 10))
        self._add_reference_image(story, "WillowlynxSumpPitCCTVCamera.png")

        status_text = self._format_status_badge(
            record.get('yesNoStatusName')
            or record.get('resultStatusName')
            or self._get_status_label(record.get('yesNoStatusID'))
        )
        story.append(Paragraph("Result:", ParagraphStyle(
            'WillowlynxCCTVResultLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            spaceAfter=4
        )))
        cctv_description = Paragraph("All CCTV cameras can be played without issues.", self.styles['Normal'])
        chip_bg, chip_text = self._get_status_chip_colors(status_text)
        cctv_chip = Table([[Paragraph(status_text or 'N/A', ParagraphStyle(
            'WillowlynxCCTVChip',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            textColor=chip_text,
            fontName='Helvetica-Bold'
        ))]], colWidths=[1.1*inch])
        cctv_chip.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), chip_bg),
            ('BOX', (0, 0), (-1, -1), 0.8, chip_text),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        cctv_row = Table([[cctv_description, cctv_chip]], colWidths=[4.9*inch, 1.3*inch])
        cctv_row.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(cctv_row)
        story.append(Spacer(1, 12))
        self._add_remarks_section(story, record.get('remarks') or record.get('Remarks'))
        return story

    def _create_monthly_database_page(self, title, data, report_data):
        """Create monthly database creation page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        story.append(Paragraph(
            "Willowlynx's historical database uses monthly partitions. Confirm MSSQL has the next six months created.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 10))

        if isinstance(data, dict):
            records = data.get('pmServerMonthlyDatabaseCreations', [])
        else:
            records = data if isinstance(data, list) else []

        if not records:
            story.append(Paragraph("No monthly database creation data available", self.styles['Normal']))
            return story

        remarks_text = ''
        subheader_style = ParagraphStyle(
            'MonthlyDBSubHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.HexColor('#1976d2'),
            spaceAfter=6
        )

        for record_index, record in enumerate(records, start=1):
            details = record.get('details') or []
            if record_index > 1:
                story.append(Spacer(1, 12))

            story.append(Paragraph("Monthly Database Creation", subheader_style))

            if details:
                rows = [['S/N', 'Server Name', 'Monthly DB are Created']]
                for detail_index, detail in enumerate(details, start=1):
                    status_text = self._resolve_yes_no_status(detail) or self._format_status_badge(
                        self._get_status_label(detail.get('yesNoStatusID'))
                    )
                    rows.append([
                        Paragraph(str(detail.get('serialNo') or detail_index), ParagraphStyle(
                            'MonthlyDBSN', parent=self.styles['Normal'], alignment=TA_CENTER
                        )),
                        Paragraph(detail.get('serverName', 'N/A'), self.styles['Normal']),
                        self._build_status_chip(status_text)
                    ])

                table = Table(rows, colWidths=[0.8*inch, 3.6*inch, 1.6*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('ALIGN', (0, 1), (1, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.6, colors.HexColor('#d0d0d0')),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(table)
            else:
                story.append(Paragraph("No detail records available for this monthly database creation check.", self.styles['Normal']))

            if not remarks_text and record.get('remarks'):
                remarks_text = record['remarks']

        self._add_remarks_section(story, remarks_text)
        return story

    def _create_database_backup_page(self, title, data, report_data):
        """Create Database Backup page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        story.append(Paragraph(
            "Check D:\\MSSQLSERVER-BACKUP\\Monthly and ensure the database backups exist in this directory.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 12))

        if isinstance(data, dict):
            database_backups = data.get('pmServerDatabaseBackups', [])
        else:
            database_backups = data if isinstance(data, list) else []

        if not database_backups:
            story.append(Paragraph("No database backup data available", self.styles['Normal']))
            return story

        remarks_text = ''
        latest_file_name = ''
        for index, backup in enumerate(database_backups, start=1):
            mssql_details = backup.get('mssqlDatabaseBackupDetails') or []
            scada_details = backup.get('scadaDataBackupDetails') or []

            if mssql_details:
                story.append(Paragraph("MSSQL Database Backup Check", self.styles['SectionHeader']))
                table = self._build_backup_table(mssql_details, "Monthly DB Backup are created")
                if table:
                    story.append(table)
                else:
                    story.append(Paragraph("No MSSQL database backup data available.", self.styles['Normal']))
                story.append(Spacer(1, 10))
            else:
                story.append(Paragraph("MSSQL Database Backup Check", self.styles['SectionHeader']))
                story.append(Paragraph("No MSSQL database backup data available.", self.styles['Normal']))
                story.append(Spacer(1, 10))

            if scada_details:
                story.append(Paragraph("SCADA Database Backup Check", self.styles['SectionHeader']))
                table = self._build_backup_table(scada_details, "SCADA DB Backup are created")
                if table:
                    story.append(table)
                else:
                    story.append(Paragraph("No SCADA database backup data available.", self.styles['Normal']))
                story.append(Spacer(1, 10))
            else:
                story.append(Paragraph("SCADA Database Backup Check", self.styles['SectionHeader']))
                story.append(Paragraph("No SCADA database backup data available.", self.styles['Normal']))
                story.append(Spacer(1, 10))

            if not remarks_text and backup.get('remarks'):
                remarks_text = backup['remarks']
            if not latest_file_name and backup.get('latestBackupFileName'):
                latest_file_name = backup['latestBackupFileName']

        if latest_file_name:
            file_table = Table([
                ['Latest Backup File Name:', latest_file_name]
            ], colWidths=[2.2*inch, 3.8*inch])
            file_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0f0f0')),
                ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#d0d0d0')),
            ]))
            story.append(file_table)
            story.append(Spacer(1, 10))

        self._add_remarks_section(story, remarks_text)

        return story

    def _create_time_sync_page(self, title, data, report_data):
        """Create Time Sync page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        story.append(Paragraph("Instructions:", ParagraphStyle(
            'TimeSyncInstructionLabel',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold'
        )))
        story.append(Paragraph(
            "Verify the SCADA server, historical server, and HMIs are time synchronised by running w32tm /query /status. The difference shall be within five minutes.",
            ParagraphStyle('TimeSyncInstruction', parent=self.styles['Normal'])
        ))
        story.append(Spacer(1, 12))

        records = []
        remarks = ''

        if isinstance(data, list) and data:
            for record in data:
                if record.get('details'):
                    for detail in record['details']:
                        status_text = detail.get('resultStatusName') or self._get_status_label(detail.get('resultStatusID'))
                        records.append({
                            'serialNo': detail.get('serialNo') or len(records) + 1,
                            'machineName': detail.get('serverName', 'N/A'),
                            'status': status_text
                        })
                if not remarks and record.get('remarks'):
                    remarks = record.get('remarks', '')
        elif isinstance(data, dict) and data.get('timeSyncData'):
            for row in data['timeSyncData']:
                status_text = row.get('resultStatusName') or self._get_status_label(row.get('timeSyncResult'))
                records.append({
                    'serialNo': row.get('serialNo') or len(records) + 1,
                    'machineName': row.get('machineName', 'N/A'),
                    'status': status_text
                })
            remarks = data.get('remarks', '')

        if records:
            rows = [['S/N', 'Machine Name', 'Time Sync Result']]
            for item in records:
                rows.append([
                    Paragraph(str(item['serialNo']), ParagraphStyle(
                        'TimeSyncSN', parent=self.styles['Normal'], alignment=TA_CENTER
                    )),
                    Paragraph(item['machineName'], self.styles['Normal']),
                    self._build_status_chip(item['status'])
                ])

            table = Table(rows, colWidths=[0.8*inch, 3.2*inch, 1.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.8, colors.HexColor('#e0e0e0')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))
        else:
            story.append(Paragraph("No time sync data available", self.styles['Normal']))
            story.append(Spacer(1, 12))

        self._add_remarks_section(story, remarks)
        return story

    def _create_hot_fixes_page(self, title, data, report_data):
        """Create hot fixes page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        story.append(Paragraph(
            "Review and apply the latest hotfixes or service packs on all applicable servers.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 12))

        if isinstance(data, dict):
            records = data.get('pmServerHotFixes', [])
        else:
            records = data if isinstance(data, list) else []

        details = []
        remarks = ''
        for record in records:
            if record.get('details'):
                details = record['details']
                remarks = record.get('remarks', '')
                break

        if not details:
            story.append(Paragraph("No hotfix data available", self.styles['Normal']))
            self._add_remarks_section(story, remarks)
            return story

        def _serial_key(item, fallback):
            value = item.get('serialNo')
            try:
                return int(value)
            except (TypeError, ValueError):
                return fallback

        details_sorted = sorted(
            enumerate(details, start=1),
            key=lambda pair: _serial_key(pair[1], pair[0])
        )
        table_data = [['S/N', 'Machine Name', 'Latest Hotfixes Applied', 'Done']]
        for idx, (fallback_index, detail) in enumerate(details_sorted, start=1):
            status_text = detail.get('resultStatusName') or self._get_status_label(detail.get('resultStatusID'))
            table_data.append([
                Paragraph(str(detail.get('serialNo') or fallback_index), ParagraphStyle(
                    'HotfixSN', parent=self.styles['Normal'], alignment=TA_CENTER
                )),
                Paragraph(detail.get('serverName', 'N/A'), self.styles['Normal']),
                Paragraph(detail.get('hotFixName') or detail.get('latestHotFixsApplied') or 'N/A', self.styles['Normal']),
                self._build_status_chip(status_text)
            ])

        table = Table(table_data, colWidths=[0.8*inch, 2.4*inch, 2.4*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (2, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        self._add_remarks_section(story, remarks)
        return story

    def _create_fail_over_page(self, title, data, report_data):
        """Create auto fail over page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        story.append(Paragraph(
            "Auto failover of SCADA server testing procedures:",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            "<i>Note: Make sure both SCADA servers are online after completing the test.</i>",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 12))

        details = []
        remarks = ''
        if isinstance(data, list):
            for record in data:
                if record.get('details'):
                    details.extend(record['details'])
                if not remarks and record.get('remarks'):
                    remarks = record['remarks']

        if not details:
            story.append(Paragraph("No auto failover data available", self.styles['Normal']))
            self._add_remarks_section(story, remarks)
            return story

        scenario_map = {
            ('SCA-SR1', 'SCA-SR2'): {
                'title': 'Failover from SCA-SR1 to SCA-SR2',
                'procedure': [
                    'Perform a system shutdown on SCA-SR1.',
                    'Check the System Server status page.'
                ],
                'expected': 'SCA-SR2 becomes master and RTUs continue reporting data to SCADA.'
            },
            ('SCA-SR2', 'SCA-SR1'): {
                'title': 'Failover from SCA-SR2 to SCA-SR1',
                'procedure': [
                    'Start SCA-SR1 and wait five minutes for it to boot.',
                    'Perform a system shutdown on SCA-SR2.',
                    'Check the System Server status page.'
                ],
                'expected': 'SCA-SR1 becomes master and RTUs continue reporting data to SCADA.'
            }
        }

        for detail in details:
            key = (detail.get('fromServer'), detail.get('toServer'))
            scenario = scenario_map.get(key, {
                'title': f"Failover from {detail.get('fromServer')} to {detail.get('toServer')}",
                'procedure': ['Verify failover behaviour.'],
                'expected': detail.get('expectedResult', 'RTUs continue reporting data to SCADA.')
            })

            steps = "<br/>".join(
                f"{idx + 1}. {step}" for idx, step in enumerate(scenario['procedure'])
            )
            result_text = self._format_status_badge(
                detail.get('resultStatusName') or detail.get('yesNoStatusName') or detail.get('result')
            )

            card_table = Table([
                [
                    Paragraph(f"<b>{scenario['title']}</b>", ParagraphStyle(
                        'FailoverCardTitle',
                        parent=self.styles['Normal'],
                        textColor=colors.HexColor('#0d47a1'),
                        fontSize=12
                    )),
                    ''
                ],
                [Paragraph(f"<b>Procedure:</b><br/>{steps}", self.styles['Normal']), ''],
                [
                    Paragraph(f"<b>Expected Result:</b><br/>{scenario['expected']}", self.styles['Normal']),
                    self._build_status_chip(result_text, width=1.0*inch)
                ]
            ], colWidths=[4.9*inch, 1.1*inch])
            card_table.setStyle(TableStyle([
                ('SPAN', (0, 0), (1, 0)),
                ('SPAN', (0, 1), (1, 1)),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#e6efff')),
                ('BACKGROUND', (0, 1), (1, 1), colors.white),
                ('BACKGROUND', (0, 2), (1, 2), colors.white),
                ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#d0d0d0')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('ALIGN', (1, 2), (1, 2), 'CENTER'),
                ('VALIGN', (1, 2), (1, 2), 'MIDDLE'),
            ]))
            story.append(card_table)
            story.append(Spacer(1, 12))

        self._add_remarks_section(story, remarks)
        return story

    def _create_asa_firewall_page(self, title, data, report_data):
        """Create ASA firewall page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        story.append(Paragraph(
            "To check ASA firewall health and backup the running configuration:",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            "1. Connect to the ASDM application from the SCADA server.<br/>"
            "2. Access the ASA firewall CLI and input the commands below.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 12))

        details = []
        remarks = ''
        if isinstance(data, list):
            details = data
            remarks = data[0].get('remarks', '') if data else ''
        elif isinstance(data, dict):
            if data.get('pmServerASAFirewalls'):
                details = data['pmServerASAFirewalls']
                remarks = data['pmServerASAFirewalls'][0].get('remarks', '')
            elif data.get('details'):
                details = data['details']
                remarks = data.get('remarks', '')

        if details:
            table_data = [['S/N', 'Command Input', 'Expected Result', 'Result Status']]
            for idx, item in enumerate(details, start=1):
                table_data.append([
                    Paragraph(str(item.get('serialNumber') or idx), ParagraphStyle(
                        'ASASeq', parent=self.styles['Normal'], alignment=TA_CENTER
                    )),
                    Paragraph(item.get('commandInput', 'N/A'), self.styles['Normal']),
                    Paragraph(item.get('asaFirewallStatusName', 'N/A'), self.styles['Normal']),
                    self._build_status_chip(item.get('resultStatusName'), width=1.3*inch)
                ])

            table = Table(table_data, colWidths=[0.6*inch, 2.3*inch, 2.3*inch, 1.4*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 1), (2, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No ASA firewall data available", self.styles['Normal']))

        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "3. Check the firewall overview to ensure everything is running properly.<br/>"
            "4. Backup the configuration to the D drive of SCADA SVR1.",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 10))

        self._add_remarks_section(story, remarks)
        return story

    def _create_software_patch_page(self, title, data, report_data):
        """Create software patch summary page"""
        story = []
        story.append(self._build_left_aligned_title(title))

        details = []
        remarks = ''
        if isinstance(data, list):
            for record in data:
                if record.get('details'):
                    details = record['details']
                    remarks = record.get('remarks', '')
                    break
        elif isinstance(data, dict):
            if data.get('pmServerSoftwarePatchSummaries'):
                summary = data['pmServerSoftwarePatchSummaries'][0]
                details = summary.get('details') or []
                remarks = summary.get('remarks', '')
            elif data.get('details'):
                details = data['details']
                remarks = data.get('remarks', '')

        if not details:
            story.append(Paragraph("No software patch data available", self.styles['Normal']))
            self._add_remarks_section(story, remarks)
            return story

        table_data = [['S/N', 'Server Name', 'Previous Patch', 'Current Patch']]
        for idx, item in enumerate(details, start=1):
            table_data.append([
                item.get('serialNo') or idx,
                item.get('serverName', 'N/A'),
                item.get('previousPatch', 'N/A'),
                item.get('currentPatch', 'N/A')
            ])

        table = Table(table_data, colWidths=[0.6*inch, 2.5*inch, 1.95*inch, 1.95*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        self._add_remarks_section(story, remarks)
        return story

    def _build_left_aligned_title(self, text):
        """Reusable left-aligned section title"""
        return Paragraph(text, ParagraphStyle(
            'LeftSectionTitle',
            parent=self.styles['ComponentTitle'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1976d2'),
            alignment=TA_LEFT,
            spaceAfter=12
        ))

    def _add_reference_image(self, story, image_name, width=4.5*inch, height=2.5*inch):
        """Add a reference image if it exists"""
        image_path = Path(f"resources/ServerPMReportForm/{image_name}")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=width, height=height)
                img.hAlign = 'CENTER'
                frame = Table([[img]], colWidths=[6*inch])
                frame.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
                    ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#e0e0e0')),
                    ('TOPPADDING', (0, 0), (-1, -1), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ]))
                story.append(frame)
                story.append(Spacer(1, 12))
            except Exception:
                pass

    def _build_result_table(self, description, status_text):
        """Create a two row table for result description and status"""
        table = Table([
            ['Result Description:', description],
            ['Reported Status:', status_text or 'N/A']
        ], colWidths=[1.9*inch, 4.1*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef2fb')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#0d47a1')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#d0d0d0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        return table

    def _build_status_chip(self, status_text, width=1.2*inch):
        """Render a chip-like table cell highlighting the status"""
        display_text = status_text or 'N/A'
        chip_bg, chip_text = self._get_status_chip_colors(display_text)
        chip_style = ParagraphStyle(
            'StatusChip',
            parent=self.styles['Normal'],
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=chip_text,
            fontSize=10
        )
        chip_table = Table([[Paragraph(display_text, chip_style)]], colWidths=[width])
        chip_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), chip_bg),
            ('BOX', (0, 0), (-1, -1), 0.8, chip_text),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        return chip_table

    def _get_status_chip_colors(self, status):
        """Return background/text colors for simple status chips"""
        if not status:
            return colors.HexColor('#f0f0f0'), colors.HexColor('#666666')

        status_lower = str(status).lower()
        positive = ['yes', 'pass', 'ok', 'good', 'success']
        negative = ['no', 'fail', 'bad', 'error']

        if any(keyword in status_lower for keyword in positive):
            return colors.HexColor('#e8f5e9'), colors.HexColor('#2e7d32')

        if any(keyword in status_lower for keyword in negative):
            return colors.HexColor('#ffebee'), colors.HexColor('#c62828')

        if 'warn' in status_lower or 'caution' in status_lower:
            return colors.HexColor('#fff8e1'), colors.HexColor('#f57c00')

        return colors.HexColor('#f0f0f0'), colors.HexColor('#666666')

    def _resolve_yes_no_status(self, source):
        """Resolve yes/no style statuses from various possible keys"""
        if not isinstance(source, dict):
            return ''
        name = self._get_value(
            source,
            'yesNoStatusName', 'YesNoStatusName',
            'resultStatusName', 'ResultStatusName',
            'statusName'
        )
        if name:
            return name

        status_id = self._get_value(source, 'yesNoStatusID', 'YesNoStatusID')
        if status_id:
            key = str(status_id).lower()
            if key in self.yes_no_guid_map:
                return self.yes_no_guid_map[key]
        return ''

    def _get_value(self, source, *keys):
        """Helper to read nested values using multiple possible casing"""
        if not isinstance(source, dict):
            return None
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]
        return None

    def _format_status_badge(self, status):
        """Return a text badge for status fields"""
        return str(status) if status else "N/A"

    def _add_remarks_section(self, story, remarks, label="Remarks", title_color=colors.black):
        """Render a remarks box if text is available"""
        if not remarks:
            return
        story.append(Paragraph(label, ParagraphStyle(
            'RemarksSectionTitle',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=title_color,
            spaceAfter=6
        )))
        remarks_box = Table([[Paragraph(remarks, self.styles['Normal'])]], colWidths=[6*inch])
        remarks_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#d0d0d0')),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(remarks_box)
        story.append(Spacer(1, 12))

    def _build_backup_table(self, details, status_header):
        """Build a backup verification table used by database backups"""
        if not details:
            return None

        rows = []
        for idx, detail in enumerate(details, start=1):
            status_text = self._resolve_yes_no_status(detail) or self._format_status_badge(
                self._get_status_label(detail.get('yesNoStatusID'))
            )
            rows.append([
                Paragraph(str(idx), ParagraphStyle('BackupSN', parent=self.styles['Normal'], alignment=TA_CENTER)),
                Paragraph(detail.get('serverName', 'N/A'), self.styles['Normal']),
                self._build_status_chip(status_text, width=1.6*inch)
            ])

        table = Table(
            [['S/N', 'Item', status_header]] + rows,
            colWidths=[0.8*inch, 3.4*inch, 1.8*inch]
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 0.8, colors.HexColor('#e0e0e0')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        return table

    def _extract_first_item(self, data):
        """Return the first dictionary item from list/dict data"""
        if isinstance(data, list) and data:
            return data[0] if isinstance(data[0], dict) else {}
        if isinstance(data, dict):
            return data
        return {}

    def _get_status_label(self, status_id):
        """Get status label from status ID"""
        if not status_id:
            return ''
        
        # Common status mappings (you may need to adjust based on your actual data)
        status_mappings = {
            1: 'Pass',
            2: 'Fail',
            3: 'Warning',
            4: 'Good',
            5: 'Bad',
            6: 'OK',
            7: 'Error',
            8: 'Yes',
            9: 'No'
        }
        
        return status_mappings.get(status_id, str(status_id))
    
    def _format_date(self, date_str):
        """Format date string for display"""
        if not date_str:
            return ''
        
        try:
            if isinstance(date_str, str):
                # Try different date formats
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(date_str.split('.')[0], fmt)
                        return dt.strftime('%d/%m/%Y %H:%M')
                    except ValueError:
                        continue
            return str(date_str)
        except:
            return str(date_str) if date_str else ''
