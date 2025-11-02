import os
import json
import logging
from datetime import datetime
from pathlib import Path

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
            textColor=colors.black
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=15,
            spaceBefore=15,
            alignment=TA_LEFT,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.darkblue,
            borderPadding=5
        ))
        
        # Component title style
        self.styles.add(ParagraphStyle(
            name='ComponentTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            spaceBefore=10,
            alignment=TA_CENTER,
            textColor=colors.darkred
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
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),  # Job No row bold
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
        """Create server health page with specified layout: title → instruction → image → table → remarks"""
        story = []
        
        # 1. Simple Section Title (left-aligned, bold, black, no icons)
        title_text = title
        title_style = ParagraphStyle(
            'SimpleTitle',
            parent=self.styles['ComponentTitle'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=colors.black,
            alignment=TA_LEFT,
            spaceAfter=15
        )
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 10))
        
        # 2. Add instructions
        instructions_text = """
        <b>Server Health Check Instructions:</b><br/>
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
                story.append(Spacer(1, 15))
            except Exception as e:
                logger.warning(f"Could not load server health reference image: {e}")
        
        # 4. Create data table
        if not data:
            # No data message
            no_data_table = Table([["No server health data available"]], colWidths=[6*inch])
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
        
        # Create table headers
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
                    server_name = detail.get('serverName', 'N/A')
                    status = detail.get('resultStatusName', 'N/A')
                    
                    # Format status without square box indicators (plain text only)
                    table_data.append([server_name, status])
        
        # Create table with improved styling
        if len(table_data) > 1:
            col_widths = [3*inch, 3*inch]
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e0e0e0')),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 20))
        else:
            # No records message
            no_records_table = Table([["No server health records available"]], colWidths=[6*inch])
            no_records_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ]))
            story.append(no_records_table)
            story.append(Spacer(1, 20))
        
        # 5. Remarks Section with title outside the box
        if remarks_text:
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
            remarks_content = Paragraph(remarks_text, remarks_text_style)
            
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
        
        return story

    def _create_hard_drive_page(self, title, data, report_data):
        """Create hard drive health page matching web component structure"""
        story = []
        
        # Add component image if available
        image_path = Path(f"resources/ServerPMReportForm/HardDriveHealth.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=4*inch, height=2.5*inch)
                img.hAlign = 'CENTER'
                
                # Create a bordered frame for the image
                image_table = Table([[img]], colWidths=[4.5*inch])
                image_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(image_table)
                story.append(Spacer(1, 12))
            except Exception as e:
                print(f"Could not load hard drive reference image: {e}")
                pass
        
        # Component title with icon
        title_text = f"💾 {title}"
        story.append(Paragraph(title_text, self.styles['ComponentTitle']))
        story.append(Spacer(1, 20))
        
        # Add instructions
        instructions_text = """
        <b>Hard Drive Health Check Instructions:</b><br/>
        1. Check the health status of all hard drives in the server<br/>
        2. Verify SMART status and any error indicators<br/>
        3. Document any drives showing warning or failure status<br/>
        4. Note any performance degradation or unusual behavior
        """
        story.append(Paragraph(instructions_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        if not data:
            story.append(Paragraph("No hard drive health data available.", self.styles['Normal']))
            return story
        
        # Create table headers
        headers = ['Server Name', 'Hard Drive Name', 'Result Status', 'Remarks', 'Created Date']
        table_data = [headers]
        
        # Handle the nested structure from API response
        for health_record in data:
            if isinstance(health_record, dict) and 'details' in health_record:
                # Add remarks section if available
                if health_record.get('remarks'):
                    story.append(Paragraph(f"📝 <b>Remarks:</b> {health_record['remarks']}", self.styles['Normal']))
                    story.append(Spacer(1, 10))
                
                # Process details
                for detail in health_record['details']:
                    server_name = detail.get('serverName', 'N/A')
                    hard_drive_name = detail.get('hardDriveName', 'N/A')
                    status = detail.get('resultStatusName', 'N/A')
                    remarks = detail.get('remarks', 'N/A')
                    created_date = self._format_date(detail.get('createdDate'))
                    
                    # Format status with indicators
                    if status and status.lower() in ['pass', 'ok', 'good', 'healthy']:
                        status_display = f"✅ {status}"
                    elif status and status.lower() in ['fail', 'error', 'bad', 'unhealthy']:
                        status_display = f"❌ {status}"
                    elif status and status.lower() in ['warning', 'caution']:
                        status_display = f"⚠️ {status}"
                    else:
                        status_display = status
                    
                    table_data.append([server_name, hard_drive_name, status_display, remarks, created_date])
        
        # Create table with improved styling
        if len(table_data) > 1:
            col_widths = [1.5*inch, 1.5*inch, 1.5*inch, 1.8*inch, 1.2*inch]
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1976d2')),
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("No hard drive health records available.", self.styles['Normal']))
        
        return story

    def _create_disk_usage_page(self, title, data, report_data):
        """Create disk usage check page matching DiskUsage_Details.js structure"""
        story = []
        
        # Add component image if available
        image_path = Path(f"resources/ServerPMReportForm/CPUAndRamUsage.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=4*inch, height=2.5*inch)
                img.hAlign = 'CENTER'
                
                # Create a bordered frame for the image
                image_table = Table([[img]], colWidths=[4.5*inch])
                image_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(image_table)
                story.append(Spacer(1, 12))
            except Exception as e:
                print(f"Could not load CPU and RAM usage reference image: {e}")
                pass
        
        # Section title with icon
        title_text = "💾 Server Disk Usage Check"
        story.append(Paragraph(title_text, self.styles['ComponentTitle']))
        story.append(Spacer(1, 12))
        
        # Add instructions matching the web component
        instructions_title = "Using Computer Management"
        story.append(Paragraph(instructions_title, self.styles['SectionHeader']))
        story.append(Spacer(1, 6))
        
        instructions_list = """
        • From Control Panel→Administration Tools→Computer Management.<br/>
        • Click on the Storage→Disk Management. Check the Status for all the hard disk<br/>
        • Remove old windows event logs to meet the target disk usage limit.
        """
        story.append(Paragraph(instructions_list, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Add important note matching web component
        note_text = """
        <b>* Note:</b> The HDSRS servers with SQL Server Database keep the historical data and daily/weekly/monthly 
        backups. The disk space usage can be up to 90%, which is considered as normal.
        """
        story.append(Paragraph(note_text, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Process disk usage data
        if not data:
            story.append(Paragraph("No disk usage data available", self.styles['Normal']))
            return story
        
        # Handle nested structure from API response
        all_disks = []
        for usage_record in data:
            if isinstance(usage_record, dict):
                # Add remarks section if available
                if usage_record.get('remarks'):
                    story.append(Paragraph(f"📝 <b>Remarks:</b> {usage_record['remarks']}", self.styles['Normal']))
                    story.append(Spacer(1, 10))
                
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
                server_header = f"🖥️ {server_name} ({len(disks)} disk{'s' if len(disks) != 1 else ''})"
                story.append(Paragraph(server_header, self.styles['SectionHeader']))
                story.append(Spacer(1, 6))
                
                # Create disk table for this server
                table_data = [['Disk', 'Total Size', 'Used Size', 'Free Size', 'Usage %', 'Result Status']]
                
                for disk in disks:
                    disk_name = disk.get('diskName', 'N/A')
                    total_size = disk.get('totalSize', 'N/A')
                    used_size = disk.get('usedSize', 'N/A')
                    free_size = disk.get('freeSize', 'N/A')
                    usage_percentage = disk.get('usagePercentage', 'N/A')
                    result_status = disk.get('resultStatusName', 'N/A')
                    
                    # Format result status with indicators
                    if result_status and result_status.lower() in ['pass', 'ok', 'good']:
                        result_display = f"✅ {result_status}"
                    elif result_status and result_status.lower() in ['fail', 'error', 'bad']:
                        result_display = f"❌ {result_status}"
                    elif result_status and result_status.lower() in ['warning', 'caution']:
                        result_display = f"⚠️ {result_status}"
                    else:
                        result_display = str(result_status)
                    
                    table_data.append([
                        str(disk_name), str(total_size), str(used_size), 
                        str(free_size), str(usage_percentage), result_display
                    ])
                
                # Create table with improved styling
                col_width = 6.5 * inch / 6
                table = Table(table_data, colWidths=[col_width] * 6)
                table.setStyle(TableStyle([
                    # Header styling
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    
                    # Data rows styling
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('TOPPADDING', (0, 1), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    
                    # Grid and borders
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                story.append(table)
                story.append(Spacer(1, 12))
        else:
            story.append(Paragraph("No disk usage records available", self.styles['Normal']))
        
        return story

    def _create_cpu_memory_page(self, title, data, report_data):
        """Create CPU and memory usage page matching CPUAndRamUsage_Details.js structure"""
        story = []
        
        # Add component image if available
        image_path = Path(f"resources/ServerPMReportForm/{title.replace(' ', '')}.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=3*inch, height=2*inch)
                story.append(img)
                story.append(Spacer(1, 20))
            except:
                pass
        
        # Component title with icon
        title_text = "🧠 Server CPU and RAM Usage Check"
        story.append(Paragraph(title_text, self.styles['ComponentTitle']))
        story.append(Spacer(1, 20))
        
        # Add instructions matching the web component
        instructions_text = """
        <b>Using Task Manager, and go to Performance Tab</b><br/>
        ○ Right click on the task bar and select task manager
        """
        story.append(Paragraph(instructions_text, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Add important note matching web component
        note_text = """
        <b>* Note:</b> The SQL Server Database on HDSRS Servers use as much memory as it needs to provide best performance, 
        we limit the memory usage so the overall server memory usage can be up to 90%
        """
        story.append(Paragraph(note_text, self.styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Process CPU and memory data
        if data and len(data) > 0:
            # Handle nested structure from API response
            all_records = []
            for usage_record in data:
                if isinstance(usage_record, dict):
                    # Add remarks section if available
                    if usage_record.get('remarks'):
                        story.append(Paragraph(f"📝 <b>Remarks:</b> {usage_record['remarks']}", self.styles['Normal']))
                        story.append(Spacer(1, 10))
                    
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
                        story.append(Spacer(1, 12))
                    
                    # Memory Usage Details Section
                    memory_details = record.get('memoryUsageDetails', [])
                    if memory_details:
                        memory_title = "💾 Memory Usage Check:"
                        story.append(Paragraph(memory_title, self.styles['SectionHeader']))
                        story.append(Spacer(1, 6))
                        
                        # Create memory usage table
                        memory_table_data = [['S/N', 'Machine Name', 'Memory Size', 'Memory In Use (%)', 'Memory In Used < 90%? *Historical server < 90%?']]
                        
                        for detail_index, detail in enumerate(memory_details):
                            serial_no = detail.get('serialNo', str(detail_index + 1))
                            server_name = detail.get('serverName', 'N/A')
                            memory_size = detail.get('memorySize', 'N/A')
                            memory_usage = detail.get('memoryUsagePercentage', 'N/A')
                            result_status = detail.get('resultStatusName', 'N/A')
                            
                            # Format result status with indicators
                            if result_status and result_status.lower() in ['pass', 'ok', 'good', 'yes']:
                                result_display = f"✅ {result_status}"
                            elif result_status and result_status.lower() in ['fail', 'error', 'bad', 'no']:
                                result_display = f"❌ {result_status}"
                            elif result_status and result_status.lower() in ['warning', 'caution']:
                                result_display = f"⚠️ {result_status}"
                            else:
                                result_display = result_status
                            
                            memory_usage_display = f"{memory_usage}%" if memory_usage != 'N/A' else 'N/A'
                            
                            memory_table_data.append([
                                serial_no, server_name, memory_size, memory_usage_display, result_display
                            ])
                        
                        # Create memory table with improved styling
                        memory_table = Table(memory_table_data, colWidths=[0.7*inch, 1.5*inch, 1.2*inch, 1.3*inch, 2.3*inch])
                        memory_table.setStyle(TableStyle([
                            # Header styling
                            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('TOPPADDING', (0, 0), (-1, 0), 8),
                            
                            # Data rows styling
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 8),
                            ('TOPPADDING', (0, 1), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                            ('LEFTPADDING', (0, 0), (-1, -1), 6),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                            
                            # Grid and borders
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ]))
                        story.append(memory_table)
                        story.append(Spacer(1, 12))
                    
                    # CPU Usage Details Section
                    cpu_details = record.get('cpuUsageDetails', [])
                    if cpu_details:
                        cpu_title = "⚡ CPU Usage Check:"
                        story.append(Paragraph(cpu_title, self.styles['SectionHeader']))
                        story.append(Spacer(1, 6))
                        
                        # Create CPU usage table
                        cpu_table_data = [['S/N', 'Machine Name', 'CPU Usage (%)', 'CPU Usage < 50%?']]
                        
                        for detail_index, detail in enumerate(cpu_details):
                            serial_no = detail.get('serialNo', str(detail_index + 1))
                            server_name = detail.get('serverName', 'N/A')
                            cpu_usage = detail.get('cpuUsagePercentage', 'N/A')
                            result_status = detail.get('resultStatusName', 'N/A')
                            
                            # Format result status with indicators
                            if result_status and result_status.lower() in ['pass', 'ok', 'good', 'yes']:
                                result_display = f"✅ {result_status}"
                            elif result_status and result_status.lower() in ['fail', 'error', 'bad', 'no']:
                                result_display = f"❌ {result_status}"
                            elif result_status and result_status.lower() in ['warning', 'caution']:
                                result_display = f"⚠️ {result_status}"
                            else:
                                result_display = result_status
                            
                            cpu_usage_display = f"{cpu_usage}%" if cpu_usage != 'N/A' else 'N/A'
                            
                            cpu_table_data.append([
                                serial_no, server_name, cpu_usage_display, result_display
                            ])
                        
                        # Create CPU table with improved styling
                        cpu_table = Table(cpu_table_data, colWidths=[1*inch, 2*inch, 1.5*inch, 2.5*inch])
                        cpu_table.setStyle(TableStyle([
                            # Header styling
                            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 10),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('TOPPADDING', (0, 0), (-1, 0), 8),
                            
                            # Data rows styling
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 9),
                            ('TOPPADDING', (0, 1), (-1, -1), 6),
                            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                            ('LEFTPADDING', (0, 0), (-1, -1), 8),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                            
                            # Grid and borders
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ]))
                        story.append(cpu_table)
                        story.append(Spacer(1, 12))
                    
                    # No details message if neither CPU nor memory data available
                    if not memory_details and not cpu_details:
                        no_details_text = "No CPU or memory usage details available for this record"
                        story.append(Paragraph(no_details_text, self.styles['Normal']))
                        story.append(Spacer(1, 12))
        else:
            no_data_text = "No CPU and memory usage data available"
            story.append(Paragraph(no_data_text, self.styles['Normal']))
        
        # Add remarks section
        remarks = ""
        if data and len(data) > 0:
            # Get remarks from the first record (already handled above in nested structure processing)
            pass  # Remarks are already added above when processing nested structure
        
        return story

    def _create_network_health_page(self, title, data, report_data):
        """Create network health page"""
        return self._create_generic_component_page(title, data, [
            'serverName', 'networkInterface', 'ipAddress', 'status', 'resultStatusName', 'remarks'
        ])

    def _create_willowlynx_process_page(self, title, data, report_data):
        """Create Willowlynx process status page"""
        return self._create_generic_component_page(title, data, [
            'processName', 'status', 'cpuUsage', 'memoryUsage', 'resultStatusName', 'remarks'
        ])

    def _create_willowlynx_network_page(self, title, data, report_data):
        """Create Willowlynx network status page"""
        return self._create_generic_component_page(title, data, [
            'networkName', 'status', 'latency', 'packetLoss', 'resultStatusName', 'remarks'
        ])

    def _create_willowlynx_rtu_page(self, title, data, report_data):
        """Create Willowlynx RTU status page"""
        return self._create_generic_component_page(title, data, [
            'rtuName', 'status', 'lastCommunication', 'resultStatusName', 'remarks'
        ])

    def _create_willowlynx_trend_page(self, title, data, report_data):
        """Create Willowlynx historical trend page"""
        return self._create_generic_component_page(title, data, [
            'trendName', 'dataPoints', 'startDate', 'endDate', 'resultStatusName', 'remarks'
        ])

    def _create_willowlynx_report_page(self, title, data, report_data):
        """Create Willowlynx historical report page"""
        return self._create_generic_component_page(title, data, [
            'reportName', 'reportType', 'generatedDate', 'resultStatusName', 'remarks'
        ])

    def _create_willowlynx_cctv_page(self, title, data, report_data):
        """Create Willowlynx CCTV camera page"""
        return self._create_generic_component_page(title, data, [
            'cameraName', 'location', 'status', 'resolution', 'resultStatusName', 'remarks'
        ])

    def _create_monthly_database_page(self, title, data, report_data):
        """Create monthly database creation page"""
        return self._create_generic_component_page(title, data, [
            'databaseName', 'creationDate', 'size', 'status', 'resultStatusName', 'remarks'
        ])

    def _create_database_backup_page(self, title, data, report_data):
        """Create Database Backup page"""
        story = []
        
        # Add section title with icon
        story.append(Paragraph(f"💾 {title}", self.styles['ComponentTitle']))
        story.append(Spacer(1, 20))
        
        # Add instructions
        instructions = """
        <b>Database Backup</b><br/>
        Check <b>D:\\MSSQLSERVER-BACKUP\\Monthly</b> make sure the database is backup in this directory.
        """
        story.append(Paragraph(instructions, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Handle data structure - data is already the list from API response
        database_backups = data if isinstance(data, list) else []
        
        if database_backups:
            for backup_index, backup in enumerate(database_backups):
                # MSSQL Database Backup Table
                if backup.get('mssqlDatabaseBackupDetails'):
                    story.append(Paragraph("🗄️ MSSQL Database Backup Check", self.styles['SectionHeader']))
                    story.append(Spacer(1, 10))
                    
                    # Create table data
                    table_data = [['S/N', 'Item', 'Monthly DB Backup are Created']]
                    
                    for detail_index, detail in enumerate(backup['mssqlDatabaseBackupDetails']):
                        # Get status
                        status = self._get_status_label(detail.get('yesNoStatusID'))
                        if status.lower() == 'yes':
                            status_text = f"✅ {status}"
                        elif status.lower() == 'no':
                            status_text = f"❌ {status}"
                        else:
                            status_text = f"⚠️ {status}"
                        
                        table_data.append([
                            str(detail_index + 1),
                            detail.get('serverName', 'N/A'),
                            status_text
                        ])
                    
                    # Create table
                    table = Table(table_data, colWidths=[0.8*inch, 3*inch, 2.5*inch])
                    table.setStyle(TableStyle([
                        # Header styling
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('TOPPADDING', (0, 0), (-1, 0), 10),
                        
                        # Data styling
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('TOPPADDING', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        
                        # Grid and borders
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1976d2')),
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 15))
                
                # SCADA Database Backup Table
                if backup.get('scadaDataBackupDetails'):
                    story.append(Paragraph("📊 SCADA Database Backup Check", self.styles['SectionHeader']))
                    story.append(Spacer(1, 10))
                    
                    # Create table data
                    table_data = [['S/N', 'Item', 'SCADA DB Backup are Created']]
                    
                    for detail_index, detail in enumerate(backup['scadaDataBackupDetails']):
                        # Get status
                        status = self._get_status_label(detail.get('yesNoStatusID'))
                        if status.lower() == 'yes':
                            status_text = f"✅ {status}"
                        elif status.lower() == 'no':
                            status_text = f"❌ {status}"
                        else:
                            status_text = f"⚠️ {status}"
                        
                        table_data.append([
                            str(detail_index + 1),
                            detail.get('serverName', 'N/A'),
                            status_text
                        ])
                    
                    # Create table
                    table = Table(table_data, colWidths=[0.8*inch, 3*inch, 2.5*inch])
                    table.setStyle(TableStyle([
                        # Header styling
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('TOPPADDING', (0, 0), (-1, 0), 10),
                        
                        # Data styling
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('TOPPADDING', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        
                        # Grid and borders
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1976d2')),
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 15))
                
                # Latest Backup File Name
                if backup.get('latestBackupFileName'):
                    story.append(Paragraph("📁 Latest Backup File Name", self.styles['SectionHeader']))
                    story.append(Spacer(1, 10))
                    story.append(Paragraph(backup['latestBackupFileName'], self.styles['Normal']))
                    story.append(Spacer(1, 15))
                
                # Remarks section
                if backup.get('remarks'):
                    story.append(Paragraph("📝 Remarks", self.styles['SectionHeader']))
                    story.append(Spacer(1, 10))
                    story.append(Paragraph(backup['remarks'], self.styles['Normal']))
                    story.append(Spacer(1, 15))
        else:
            # No data available
            story.append(Paragraph("No database backup data available", self.styles['Normal']))
        
        return story

    def _create_time_sync_page(self, title, data, report_data):
        """Create Time Sync page"""
        story = []
        
        # Add section title with icon
        story.append(Paragraph(f"🕐 {title}", self.styles['ComponentTitle']))
        story.append(Spacer(1, 20))
        
        # Add instructions
        instructions = """
        To check the time sync for SCADA server, Historical server, and HMIs by using command line w32tm /query /status. To be within 5 minutes tolerance
        """
        story.append(Paragraph(instructions, self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Handle data structure
        time_sync_data = []
        remarks = ''
        
        if isinstance(data, list) and data:
            # Handle case where data is the pmServerTimeSyncs array directly
            for record in data:
                if record.get('details'):
                    for detail in record['details']:
                        time_sync_data.append({
                            'serialNo': detail.get('serialNo', ''),
                            'machineName': detail.get('serverName', ''),
                            'timeSyncResult': detail.get('resultStatusID', ''),
                            'resultStatusName': detail.get('resultStatusName', '')
                        })
                # Get remarks from the first record
                if not remarks and record.get('remarks'):
                    remarks = record['remarks']
        elif isinstance(data, dict) and data.get('timeSyncData'):
            time_sync_data = data['timeSyncData']
            remarks = data.get('remarks', '')
        
        if time_sync_data:
            # Create table data
            table_data = [['S/N', 'Machine Name', 'Time Sync Result']]
            
            for row in time_sync_data:
                # Get status
                status = row.get('resultStatusName') or self._get_status_label(row.get('timeSyncResult'))
                if status and status.lower() in ['pass', 'ok', 'good', 'success']:
                    status_text = f"✅ {status}"
                elif status and status.lower() in ['fail', 'error', 'bad', 'critical']:
                    status_text = f"❌ {status}"
                elif status and status.lower() in ['warning', 'caution', 'pending']:
                    status_text = f"⚠️ {status}"
                else:
                    status_text = status or 'N/A'
                
                table_data.append([
                    row.get('serialNo', 'N/A'),
                    row.get('machineName', 'N/A'),
                    status_text
                ])
            
            # Create table
            table = Table(table_data, colWidths=[0.8*inch, 3*inch, 2.5*inch])
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                
                # Data styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1976d2')),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 15))
        else:
            # No data available
            story.append(Paragraph("No time sync data available", self.styles['Normal']))
            story.append(Spacer(1, 15))
        
        # Remarks section
        if remarks:
            story.append(Paragraph("📝 Remarks", self.styles['SectionHeader']))
            story.append(Spacer(1, 10))
            story.append(Paragraph(remarks, self.styles['Normal']))
            story.append(Spacer(1, 15))
        
        return story

    def _create_hot_fixes_page(self, title, data, report_data):
        """Create hot fixes page"""
        return self._create_generic_component_page(title, data, [
            'hotfixId', 'description', 'installDate', 'status', 'resultStatusName', 'remarks'
        ])

    def _create_fail_over_page(self, title, data, report_data):
        """Create auto fail over page"""
        return self._create_generic_component_page(title, data, [
            'serviceName', 'primaryServer', 'secondaryServer', 'status', 'resultStatusName', 'remarks'
        ])

    def _create_asa_firewall_page(self, title, data, report_data):
        """Create ASA firewall page"""
        return self._create_generic_component_page(title, data, [
            'firewallName', 'version', 'status', 'lastUpdate', 'resultStatusName', 'remarks'
        ])

    def _create_software_patch_page(self, title, data, report_data):
        """Create software patch summary page"""
        return self._create_generic_component_page(title, data, [
            'patchName', 'version', 'installDate', 'status', 'resultStatusName', 'remarks'
        ])

    def _create_generic_component_page(self, title, data, columns, icon="🔧"):
        """Create a generic component page with improved formatting matching web component structure"""
        story = []
        
        # Add component image if available
        image_path = Path(f"resources/ServerPMReportForm/{title.replace(' ', '')}.png")
        if image_path.exists():
            try:
                img = Image(str(image_path), width=3*inch, height=2*inch)
                img.hAlign = 'CENTER'
                story.append(img)
                story.append(Spacer(1, 20))
            except:
                pass
        
        # Component title with icon
        title_with_icon = f"{icon} {title}"
        story.append(Paragraph(title_with_icon, self.styles['ComponentTitle']))
        story.append(Spacer(1, 20))
        
        if not data:
            story.append(Paragraph("No data available for this component.", self.styles['Normal']))
            return story
        
        # Define common column mappings for better display
        column_mappings = {
            'serverName': 'Server Name',
            'resultStatusName': 'Result Status',
            'resultStatusID': 'Status ID',
            'remarks': 'Remarks',
            'createdDate': 'Created Date',
            'updatedDate': 'Updated Date',
            'processName': 'Process Name',
            'processStatus': 'Process Status',
            'networkStatus': 'Network Status',
            'rtuName': 'RTU Name',
            'rtuStatus': 'RTU Status',
            'trendName': 'Trend Name',
            'trendStatus': 'Trend Status',
            'reportName': 'Report Name',
            'reportStatus': 'Report Status',
            'cameraName': 'Camera Name',
            'cameraStatus': 'Camera Status',
            'databaseName': 'Database Name',
            'databaseStatus': 'Database Status',
            'backupStatus': 'Backup Status',
            'syncStatus': 'Sync Status',
            'hotfixName': 'Hotfix Name',
            'hotfixStatus': 'Hotfix Status',
            'failoverStatus': 'Failover Status',
            'firewallStatus': 'Firewall Status',
            'patchName': 'Patch Name',
            'patchStatus': 'Patch Status'
        }
        
        # Create table headers with proper display names
        headers = [column_mappings.get(col, col.replace('_', ' ').title()) for col in columns]
        table_data = [headers]
        
        # Add data rows
        for item in data:
            if isinstance(item, dict):
                # Handle nested structure with details array
                if 'details' in item and isinstance(item['details'], list):
                    # Add remarks section if available
                    if item.get('remarks'):
                        story.append(Paragraph(f"📝 <b>Remarks:</b> {item['remarks']}", self.styles['Normal']))
                        story.append(Spacer(1, 10))
                    
                    # Process details
                    for detail in item['details']:
                        if isinstance(detail, dict):
                            row = []
                            for col in columns:
                                value = detail.get(col, 'N/A')
                                
                                # Format specific columns
                                if col == 'resultStatusName' and value and value != 'N/A':
                                    # Add status indicators
                                    if value.lower() in ['pass', 'ok', 'good', 'active', 'running', 'online']:
                                        value = f"✅ {value}"
                                    elif value.lower() in ['fail', 'error', 'bad', 'inactive', 'stopped', 'offline']:
                                        value = f"❌ {value}"
                                    elif value.lower() in ['warning', 'caution', 'pending']:
                                        value = f"⚠️ {value}"
                                elif col.endswith('Date') and value and value != 'N/A':
                                    value = self._format_date(value)
                                
                                row.append(str(value) if value is not None else 'N/A')
                            table_data.append(row)
                else:
                    # Handle direct item structure (backward compatibility)
                    row = []
                    for col in columns:
                        value = item.get(col, 'N/A')
                        
                        # Format specific columns
                        if col == 'resultStatusName' and value and value != 'N/A':
                            # Add status indicators
                            if value.lower() in ['pass', 'ok', 'good', 'active', 'running', 'online']:
                                value = f"✅ {value}"
                            elif value.lower() in ['fail', 'error', 'bad', 'inactive', 'stopped', 'offline']:
                                value = f"❌ {value}"
                            elif value.lower() in ['warning', 'caution', 'pending']:
                                value = f"⚠️ {value}"
                        elif col.endswith('Date') and value and value != 'N/A':
                            value = self._format_date(value)
                        
                        row.append(str(value) if value is not None else 'N/A')
                    table_data.append(row)
            else:
                # Handle non-dict data
                table_data.append([str(item)] + ['N/A'] * (len(columns) - 1))
        
        # Create table
        if len(table_data) > 1:  # Has data beyond headers
            # Calculate column widths dynamically
            num_columns = len(columns)
            if num_columns <= 2:
                col_widths = [3*inch, 3*inch][:num_columns]
            elif num_columns <= 4:
                col_widths = [1.5*inch] * num_columns
            else:
                col_widths = [6.5*inch / num_columns] * num_columns
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                
                # Data rows styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                
                # Grid and borders
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
                ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#1976d2')),
                
                # Alternating row colors for better readability
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.HexColor('#ffffff')]),
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("No data available for this component.", self.styles['Normal']))
        
        return story

    def _get_status_label(self, status_id):
        """Get status label from status ID"""
        if not status_id:
            return 'N/A'
        
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