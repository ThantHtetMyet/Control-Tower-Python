import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, BaseDocTemplate, PageTemplate, Frame, PageBreak
from reportlab.lib.utils import ImageReader

from config import Config

logger = logging.getLogger(__name__)


class CMReportPDFGenerator:
    """PDF generator for Corrective Maintenance report forms."""

    def __init__(self) -> None:
        self.config = Config()
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            "CMTitle",
            parent=self.styles["Heading1"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1976d2"),
            fontSize=18,
            fontName="Helvetica-Bold",
            spaceAfter=18,
        )
        self.header_image_path = Path(__file__).parent / "resources" / "willowglen_letterhead.png"
        self.section_header = ParagraphStyle(
            "CMSectionHeader",
            parent=self.styles["Heading2"],
            fontSize=14,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1976d2"),
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=12,
        )
        self.subsection_header = ParagraphStyle(
            "CMSubHeader",
            parent=self.styles["Heading3"],
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0d47a1"),
            alignment=TA_LEFT,
            spaceBefore=4,
            spaceAfter=6,
        )
        self.label_style = ParagraphStyle(
            "CMLabel",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#0d47a1"),
            fontName="Helvetica-Bold",
        )
        self.value_style = ParagraphStyle(
            "CMValue",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.black,
        )
        self.card_label_style = ParagraphStyle(
            "CMCardLabel",
            parent=self.styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#546e7a"),
            leading=12,
        )
        self.card_value_style = ParagraphStyle(
            "CMCardValue",
            parent=self.styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#263238"),
            leading=14,
        )
        self.box_label_style = ParagraphStyle(
            "CMBoxLabel",
            parent=self.styles["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#37474f"),
            spaceBefore=6,
            spaceAfter=4,
        )
        self.box_value_style = ParagraphStyle(
            "CMBoxValue",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#263238"),
        )
        self.muted_text_style = ParagraphStyle(
            "CMMuted",
            parent=self.styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Oblique",
            textColor=colors.HexColor("#6b7280"),
        )
        self.image_caption_style = ParagraphStyle(
            "CMImageCaption",
            parent=self.styles["Normal"],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#37474f"),
        )
        self.image_note_style = ParagraphStyle(
            "CMImageNote",
            parent=self.styles["Normal"],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6b7280"),
        )

    def _create_header_canvas(self, canvas, doc):
        try:
            if self.header_image_path.exists():
                page_width, page_height = A4
                img_width = page_width - 144
                img_height = 80
                x_position = 72
                y_position = page_height - 100
                canvas.setFillColor(colors.white)
                canvas.rect(x_position, y_position, img_width, img_height, fill=1, stroke=0)
                canvas.drawImage(
                    str(self.header_image_path),
                    x_position,
                    y_position,
                    width=img_width,
                    height=img_height,
                    preserveAspectRatio=True,
                )
        except Exception as exc:
            logger.warning("Failed to render CM header image: %s", exc)

        self._draw_footer(canvas)

    def _draw_footer(self, canvas):
        page_width, _ = A4
        footer_y = 50
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1)
        canvas.line(72, footer_y + 20, page_width - 72, footer_y + 20)

        canvas.setFillColor(colors.black)
        canvas.setFont("Helvetica-Bold", 12)
        company_text = "WILLOWGLEN SERVICES PTE LTD"
        text_width = canvas.stringWidth(company_text, "Helvetica-Bold", 12)
        canvas.drawString((page_width - text_width) / 2, footer_y, company_text)

        canvas.setFont("Helvetica", 10)
        copyright_text = "Copyright©2023. All rights reserved."
        copyright_width = canvas.stringWidth(copyright_text, "Helvetica", 10)
        canvas.drawString((page_width - copyright_width) / 2, footer_y - 15, copyright_text)

    def _build_document(self, pdf_path: Path):
        doc = BaseDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=120,
            bottomMargin=100,
        )
        frame = Frame(
            72,
            100,
            A4[0] - 144,
            A4[1] - 220,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        template = PageTemplate(id="cm_default", frames=[frame], onPage=self._create_header_canvas)
        doc.addPageTemplates([template])
        return doc

    def generate_pdf(self, report_data: dict, job_no: str, report_type: str = "CM") -> Path:
        pdf_path = self.config.get_pdf_path(job_no, report_type)
        doc = self._build_document(pdf_path)

        story = []

        report_form = report_data.get("reportForm", {})
        cm_form = report_data.get("cmReportForm", {})
        report_title = cm_form.get("reportTitle") or "Corrective Maintenance Report"
        story.append(Spacer(1, 80))
        story.append(Paragraph(report_title, self.title_style))
        story.extend(self._build_basic_info(report_form, cm_form, job_no))
        story.append(Spacer(1, 60))
        story.append(PageBreak())

        story.extend(self._build_timeline_section(cm_form))
        story.append(PageBreak())

        story.extend(self._build_issue_section(cm_form, report_data.get("beforeIssueImages", [])))
        story.append(PageBreak())

        story.extend(self._build_action_section(cm_form, report_data.get("afterActionImages", [])))
        story.append(PageBreak())

        story.extend(
            self._build_material_section(
                report_data.get("materialUsed", []),
                report_data.get("materialUsedOldSerialImages", []),
                report_data.get("materialUsedNewSerialImages", []),
            )
        )
        story.append(PageBreak())

        story.extend(self._build_status_section(cm_form))
        story.extend(self._build_attendance_section(cm_form))

        doc.build(story)
        logger.info("[CM PDF] Generated CM report at %s", pdf_path)
        return Path(pdf_path)

    def _build_basic_info(self, report_form: dict, cm_form: dict, job_no: str):
        info_items = [
            ("Job Number", job_no or "N/A"),
            ("Customer", cm_form.get("customer") or "Not specified"),
            ("Project No", cm_form.get("projectNo") or "Not specified"),
            ("Station Name", report_form.get("stationName") or report_form.get("stationNameWarehouseName") or "Not specified"),
            ("System Description", report_form.get("systemName") or report_form.get("systemNameWarehouseName") or "Not specified"),
            ("Report Form Type", report_form.get("reportFormTypeName") or "Corrective Maintenance"),
            ("Report Title", cm_form.get("reportTitle") or "Corrective Maintenance Report"),
        ]

        rows = []
        for label, value in info_items:
            rows.append(
                [
                    Paragraph(label, self.label_style),
                    Paragraph(value or "Not specified", self.value_style),
                ]
            )

        table = Table(rows, colWidths=[2.1 * inch, 4.2 * inch])
        table.hAlign = "CENTER"
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fb")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d1d9e6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e6ef")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        return [
            table,
            Spacer(1, 20),
        ]

    def _build_issue_section(self, cm_form: dict, before_images: list):
        section = [
            Paragraph("Issue Details", self.section_header),
        ]
        section.extend(self._build_image_gallery("Before Issue Images", before_images))
        for label, value in [
            ("Issue Reported Description", cm_form.get("issueReportedDescription") or "Not specified"),
            ("Issue Found Description", cm_form.get("issueFoundDescription") or "Not specified"),
        ]:
            section.extend(self._build_text_box(label, value))
            section.append(Spacer(1, 6))
        section.append(Spacer(1, 14))
        return section

    def _build_action_section(self, cm_form: dict, after_images: list):
        section = [
            Paragraph("Action Taken", self.section_header),
        ]
        section.extend(self._build_text_box("Action Taken Description", cm_form.get("actionTakenDescription") or "Not specified"))
        section.append(Spacer(1, 10))
        section.extend(self._build_image_gallery("After Action Images", after_images))
        section.append(Spacer(1, 10))
        return section

    def _build_timeline_section(self, cm_form: dict):
        timeline_items = [
            ("Failure Detected Date", self._format_datetime(cm_form.get("failureDetectedDate")) or "N/A"),
            ("Response Date", self._format_datetime(cm_form.get("responseDate")) or "N/A"),
            ("Arrival Date", self._format_datetime(cm_form.get("arrivalDate")) or "N/A"),
            ("Completion Date", self._format_datetime(cm_form.get("completionDate")) or "N/A"),
        ]

        cards = self._build_cards(timeline_items, cards_per_row=2)
        rows = []
        for label, value in timeline_items:
            rows.append(
                [
                    Paragraph(label, self.card_label_style),
                    Paragraph(value or "N/A", self.card_value_style),
                ]
            )
        table = Table(rows, colWidths=[2.4 * inch, 3.6 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fb")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d1d9e6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e6ef")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return [Paragraph("Timeline Information", self.section_header), table, Spacer(1, 14)]

    def _build_attendance_section(self, cm_form: dict):
        items = [
            ("Attended By", cm_form.get("attendedBy") or "Not specified"),
            ("Approved By", cm_form.get("approvedBy") or "Not specified"),
        ]
        remarks = cm_form.get("remark")
        if remarks:
            items.append(("Remarks", remarks))
        section = [
            Paragraph("Approval Information", self.section_header),
            self._build_label_value_table(items),
        ]
        section.append(Spacer(1, 18))
        section.append(self._build_signature_row(cm_form))
        section.append(Spacer(1, 12))
        return section

    def _build_material_section(self, materials: list, old_serial_images: list, new_serial_images: list):
        section = [Paragraph("Material Used Information", self.section_header)]
        if not materials:
            section.append(self._build_placeholder_box("No material used data recorded."))
            section.append(Spacer(1, 10))
        else:
            rows = [["#", "Material Description", "Old Serial No", "New Serial No", "Remarks"]]
            for index, item in enumerate(materials, start=1):
                rows.append(
                    [
                        str(index),
                        Paragraph(item.get("materialDescription") or item.get("MaterialDescription") or "Not specified", self.value_style),
                        Paragraph(item.get("oldSerialNo") or item.get("OldSerialNo") or "-", self.value_style),
                        Paragraph(item.get("newSerialNo") or item.get("NewSerialNo") or "-", self.value_style),
                        Paragraph(item.get("remarks") or item.get("Remarks") or "-", self.value_style),
                    ]
                )

            table = Table(rows, colWidths=[0.4 * inch, 2.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976d2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            section.append(table)
            section.append(Spacer(1, 12))

        section.extend(self._build_image_gallery("Old Serial No Images", old_serial_images))
        section.extend(self._build_image_gallery("New Serial No Images", new_serial_images))
        section.append(Spacer(1, 10))
        return section

    def _build_status_section(self, cm_form: dict):
        cards = [
            (
                "Further Action Taken",
                cm_form.get("furtherActionTakenName")
                or cm_form.get("FurtherActionTakenName")
                or "Not specified",
            ),
            (
                "Form Status",
                cm_form.get("formStatusName")
                or cm_form.get("FormStatusName")
                or "Not specified",
            ),
        ]
        table = self._build_label_value_table(cards)
        return [
            Paragraph("Status Information", self.section_header),
            table,
            Spacer(1, 12),
        ]

    def _build_signature_row(self, cm_form: dict):
        blocks = [
            self._build_signature_block("Attended By Signature", cm_form.get("attendedBy")),
            self._build_signature_block("Approved By Signature", cm_form.get("approvedBy")),
        ]
        table = Table([blocks], colWidths=[3.0 * inch, 3.0 * inch])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
        return table

    def _build_signature_block(self, label: str, name: Optional[str]):
        name_text = name if name else ""
        block = Table(
            [
                [""],
                [Paragraph(name_text if name_text else "&nbsp;", self.card_value_style)],
                [Paragraph(label, self.card_label_style)],
            ],
            colWidths=[2.8 * inch],
        )
        block.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, 0), 60),
                    ("LINEABOVE", (0, 1), (-1, 1), 0.8, colors.HexColor("#9aa4b1")),
                    ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                    ("TOPPADDING", (0, 1), (-1, 1), 6),
                    ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                    ("ALIGN", (0, 2), (-1, 2), "CENTER"),
                    ("TOPPADDING", (0, 2), (-1, 2), 6),
                ]
            )
        )
        return block

    def _build_cards(self, items, cards_per_row=2):
        if not items:
            return self._build_placeholder_box("No data available.")

        card_width = 5.7 * inch if cards_per_row == 1 else 2.75 * inch
        cards = []
        for label, value in items:
            if isinstance(value, Paragraph):
                value_flowable = value
            else:
                text_value = ""
                if isinstance(value, str):
                    text_value = value.strip()
                elif value is not None:
                    text_value = str(value).strip()
                if not text_value:
                    text_value = "Not specified"
                value_flowable = Paragraph(text_value, self.card_value_style)

            card = Table(
                [
                    [Paragraph(label, self.card_label_style)],
                    [value_flowable],
                ],
                colWidths=[card_width],
            )
            card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dbe3ed")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            cards.append(card)

        rows = []
        row = []
        for card in cards:
            row.append(card)
            if len(row) == cards_per_row:
                rows.append(row)
                row = []
        if row:
            while len(row) < cards_per_row:
                row.append(Spacer(1, 0))
            rows.append(row)

        container = Table(rows, colWidths=[card_width] * cards_per_row, hAlign="LEFT")
        container.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return container

    def _build_text_box(self, title: str, value: str):
        box = Table([[Paragraph(value or "Not specified", self.box_value_style)]], colWidths=[5.7 * inch])
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fefefe")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dbe3ed")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return [Paragraph(title, self.box_label_style), box]

    def _build_label_value_table(self, items):
        rows = []
        for label, value in items:
            rows.append(
                [
                    Paragraph(label, self.card_label_style),
                    Paragraph((value or "Not specified"), self.card_value_style),
                ]
            )
        table = Table(rows, colWidths=[2.4 * inch, 3.6 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fb")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d1d9e6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e6ef")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _build_placeholder_box(self, message: str):
        table = Table([[Paragraph(message, self.muted_text_style)]], colWidths=[5.7 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f7fb")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dbe3ed")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return table

    def _build_image_gallery(self, title: str, images: list):
        gallery = [Paragraph(title, self.subsection_header)]
        paths = self._prepare_image_metadata(images)
        if not paths:
            gallery.append(self._build_placeholder_box("No images uploaded for this section."))
            gallery.append(Spacer(1, 10))
            return gallery

        cards = []
        for img_path in paths:
            img_flow = self._create_image_flowable(img_path)
            if not img_flow:
                cards.append(self._build_placeholder_box("Image unavailable."))
                continue

            card = Table([[img_flow]], colWidths=[2.8 * inch])
            card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dfe3eb")),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            cards.append(card)

        rows = []
        row = []
        cards_per_row = 2
        for card in cards:
            row.append(card)
            if len(row) == cards_per_row:
                rows.append(row)
                row = []
        if row:
            while len(row) < cards_per_row:
                row.append(Spacer(1, 0))
            rows.append(row)

        gallery_table = Table(rows, colWidths=[2.95 * inch] * cards_per_row, hAlign="LEFT")
        gallery_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        gallery.append(gallery_table)
        gallery.append(Spacer(1, 12))
        return gallery

    def _prepare_image_metadata(self, images: list):
        metadata = []
        if not images:
            return metadata

        for index, item in enumerate(images, start=1):
            directory = item.get("storedDirectory") or item.get("StoredDirectory")
            image_name = item.get("imageName") or item.get("ImageName")
            if not directory or not image_name:
                continue
            image_path = Path(directory) / image_name
            if not image_path.exists():
                logger.warning("CM PDF image path not found: %s", image_path)
                continue
            metadata.append(image_path)

        return metadata

    def _create_image_flowable(self, image_path: Path, max_width=2.6 * inch, max_height=1.7 * inch):
        try:
            reader = ImageReader(str(image_path))
            width, height = reader.getSize()
            scale = min(max_width / width, max_height / height, 1)
            adjusted_width = width * scale
            adjusted_height = height * scale
            return Image(str(image_path), width=adjusted_width, height=adjusted_height)
        except Exception as exc:
            logger.warning("Unable to render CM image %s: %s", image_path, exc)
            return None

    def _format_datetime(self, date_value):
        if not date_value:
            return None
        if isinstance(date_value, datetime):
            return date_value.strftime("%d/%m/%Y %H:%M")
        try:
            return datetime.fromisoformat(str(date_value).replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
        except Exception:
            try:
                return datetime.strptime(str(date_value), "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y %H:%M")
            except Exception:
                return str(date_value)

    def _format_uploaded_text(self, uploaded_date):
        formatted = self._format_datetime(uploaded_date)
        return f"Uploaded {formatted}" if formatted else ""
