import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    BaseDocTemplate,
    PageTemplate,
    Frame,
    PageBreak,
    Image,
)
from reportlab.lib.utils import ImageReader

from config import Config

logger = logging.getLogger(__name__)


class RTUPMPDFGenerator:
    """PDF generator for RTU Preventative Maintenance report forms."""

    def __init__(self) -> None:
        self.config = Config()
        self.styles = getSampleStyleSheet()

        self.title_style = ParagraphStyle(
            "RTUTitle",
            parent=self.styles["Heading1"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1976d2"),
            fontSize=18,
            fontName="Helvetica-Bold",
            spaceAfter=18,
        )
        self.section_header = ParagraphStyle(
            "RTUSectionHeader",
            parent=self.styles["Heading2"],
            fontSize=14,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1976d2"),
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=10,
            keepWithNext=True,
        )
        self.subsection_header = ParagraphStyle(
            "RTUSubHeader",
            parent=self.styles["Heading3"],
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0d47a1"),
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True,
        )
        self.card_label_style = ParagraphStyle(
            "RTUCardLabel",
            parent=self.styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#546e7a"),
            leading=12,
        )
        self.card_value_style = ParagraphStyle(
            "RTUCardValue",
            parent=self.styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#263238"),
            leading=14,
        )
        self.box_label_style = ParagraphStyle(
            "RTUBoxLabel",
            parent=self.styles["Normal"],
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#37474f"),
            spaceBefore=6,
            spaceAfter=4,
        )
        self.box_value_style = ParagraphStyle(
            "RTUBoxValue",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#263238"),
        )
        self.muted_text_style = ParagraphStyle(
            "RTUMuted",
            parent=self.styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Oblique",
            textColor=colors.HexColor("#6b7280"),
        )
        self.image_caption_style = ParagraphStyle(
            "RTUImageCaption",
            parent=self.styles["Normal"],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#37474f"),
        )
        self.header_image_path = Path(__file__).parent / "resources" / "willowglen_letterhead.png"

    def generate_pdf(self, report_data: dict, job_no: str, report_type: str = "RTU_PM") -> Path:
        pdf_path = self.config.get_pdf_path(job_no, report_type)
        doc = self._build_document(pdf_path)

        story = []
        rtu_form = report_data.get("pmReportFormRTU") or {}
        raw_title = self._safe_get(rtu_form, "reportTitle")
        title = raw_title if raw_title else "RTU Preventative Maintenance Report"

        story.extend(self._build_cover_page(report_data, title))
        story.append(PageBreak())

        story.extend(self._build_summary_page(rtu_form))
        story.append(PageBreak())

        story.extend(
            self._build_main_cabinet_section(
                report_data.get("pmMainRtuCabinet", []),
                report_data.get("images", {}).get("mainCabinet", []),
            )
        )

        story.extend(
            self._build_chamber_section(
                report_data.get("pmChamberMagneticContact", []),
                report_data.get("images", {}).get("chamber", []),
            )
        )

        story.extend(
            self._build_cooling_section(
                report_data.get("pmRTUCabinetCooling", []),
                report_data.get("images", {}).get("cooling", []),
            )
        )

        story.extend(
            self._build_dvr_section(
                report_data.get("pmDVREquipment", []),
                report_data.get("images", {}).get("dvr", []),
            )
        )

        doc.build(story)
        logger.info("[RTU PDF] Generated RTU PM report at %s", pdf_path)
        return Path(pdf_path)

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
        template = PageTemplate(id="rtu_default", frames=[frame], onPage=self._create_header_canvas)
        doc.addPageTemplates([template])
        return doc

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
            logger.warning("Failed to render RTU header image: %s", exc)

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
        copyright_text = "CopyrightAc2023. All rights reserved."
        copyright_width = canvas.stringWidth(copyright_text, "Helvetica", 10)
        canvas.drawString((page_width - copyright_width) / 2, footer_y - 15, copyright_text)

    def _build_cover_page(self, report_data: dict, title: str):
        cover = [
            Spacer(1, 110),
            Paragraph(self._as_text(title), self.title_style),
            Spacer(1, 35),
        ]
        cover.extend(self._build_basic_info(report_data, title))
        cover.append(Spacer(1, 80))
        return cover

    def _build_basic_info(self, report_data: dict, report_title: str):
        report_form = report_data.get("reportForm", {})
        rtu_form = report_data.get("pmReportFormRTU", {})
        rows = [
            ("Job Number", self._safe_get(report_form, "jobNo")),
            ("Report Form Type", self._safe_get(report_form, "reportFormTypeName")),
            ("System Description", self._safe_get(report_form, "systemName")),
            ("Station Name", self._safe_get(report_form, "stationName")),
            ("Project No", self._safe_get(rtu_form, "projectNo")),
            ("Customer", self._safe_get(rtu_form, "customer")),
            ("Report Title", self._safe_get(rtu_form, "reportTitle") or report_title),
        ]
        table = Table(
            [
                [Paragraph(label, self.card_label_style), Paragraph(self._as_text(value), self.card_value_style)]
                for label, value in rows
            ],
            colWidths=[2.2 * inch, 4.1 * inch],
        )
        table.hAlign = "CENTER"
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fb")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#d1d9e6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e6ef")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return [table, Spacer(1, 18)]

    def _build_summary_page(self, rtu_form: dict):
        summary = self._build_summary_section(rtu_form)
        summary.append(Spacer(1, 40))
        summary.append(self._build_signature_row(rtu_form))
        summary.append(Spacer(1, 20))
        return summary

    def _build_summary_section(self, rtu_form: dict):
        rows = [
            ("Date of Service", self._format_datetime(self._safe_get(rtu_form, "dateOfService"))),
            ("Cleaning of Cabinet", self._safe_get(rtu_form, "cleaningOfCabinet")),
            ("Attended By", self._safe_get(rtu_form, "attendedBy")),
            ("Approved By", self._safe_get(rtu_form, "approvedBy")),
            ("Remarks", self._safe_get(rtu_form, "remarks")),
        ]
        table = Table(
            [
                [Paragraph(label, self.card_label_style), Paragraph(self._as_text(value), self.card_value_style)]
                for label, value in rows
            ],
            colWidths=[2.4 * inch, 3.6 * inch],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fefefe")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dbe3ed")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e6ef")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return [Paragraph("RTU Maintenance Summary", self.section_header), table]

    def _build_signature_row(self, rtu_form: dict):
        blocks = [
            self._build_signature_block("Attended By Signature", self._safe_get(rtu_form, "attendedBy")),
            self._build_signature_block("Approved By Signature", self._safe_get(rtu_form, "approvedBy")),
        ]
        table = Table([blocks], colWidths=[3.0 * inch, 3.0 * inch])
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
        return table

    def _build_signature_block(self, label: str, name: Optional[str]):
        name_text = self._as_text(name)
        block = Table(
            [
                [""],
                [Paragraph(name_text if name_text != "N/A" else "&nbsp;", self.card_value_style)],
                [Paragraph(label, self.card_label_style)],
            ],
            colWidths=[2.8 * inch],
        )
        block.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, 0), 50),
                    ("LINEABOVE", (0, 1), (-1, 1), 0.8, colors.HexColor("#9aa4b1")),
                    ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                    ("TOPPADDING", (0, 1), (-1, 1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                    ("ALIGN", (0, 2), (-1, 2), "CENTER"),
                    ("TOPPADDING", (0, 2), (-1, 2), 6),
                ]
            )
        )
        return block

    def _build_main_cabinet_section(self, records: list, images: list):
        section = [Paragraph("Main RTU Cabinet Checks", self.section_header)]
        if not records:
            section.append(self._build_placeholder_box("No RTU cabinet data recorded."))
        else:
            for idx, item in enumerate(records, start=1):
                section.append(Paragraph(f"Cabinet #{idx}", self.subsection_header))
                rows = [
                    ("RTU Cabinet", item.get("rtuCabinet") or item.get("RTUCabinet")),
                    ("Equipment Rack", item.get("equipmentRack") or item.get("EquipmentRack")),
                    ("Monitor", item.get("monitor") or item.get("Monitor")),
                    ("Mouse / Keyboard", item.get("mouseKeyboard") or item.get("MouseKeyboard")),
                    ("CPU 6000 Card", item.get("cpU6000Card") or item.get("cpu6000Card") or item.get("CPU6000Card")),
                    ("Input Card", item.get("inputCard") or item.get("InputCard")),
                    ("Megapop NTU", item.get("megapopNTU") or item.get("MegapopNTU")),
                    ("Network Router", item.get("networkRouter") or item.get("NetworkRouter")),
                    ("Network Switch", item.get("networkSwitch") or item.get("NetworkSwitch")),
                    ("Digital Video Recorder", item.get("digitalVideoRecorder") or item.get("DigitalVideoRecorder")),
                    ("RTU Door Contact", item.get("rtuDoorContact") or item.get("RTUDoorContact")),
                    ("Power Supply Unit", item.get("powerSupplyUnit") or item.get("PowerSupplyUnit")),
                    ("UPS Taking Over Test", item.get("upsTakingOverTest") or item.get("UPSTakingOverTest")),
                    ("UPS Battery", item.get("upsBattery") or item.get("UPSBattery")),
                    ("Remarks", item.get("remarks") or item.get("Remarks")),
                ]
                section.append(self._build_label_value_table(rows))
                section.append(Spacer(1, 12))

        section.extend(self._build_image_gallery("RTU Cabinet Images", images))
        return section

    def _build_chamber_section(self, records: list, images: list):
        section = [Paragraph("Chamber Magnetic Contact", self.section_header)]
        if not records:
            section.append(self._build_placeholder_box("No chamber magnetic contact records available."))
        else:
            data = [["Chamber No.", "OG Box", "Contact 1", "Contact 2", "Contact 3", "Remarks"]]
            for item in records:
                data.append(
                    [
                        self._as_text(item.get("chamberNumber") or item.get("ChamberNumber")),
                        self._as_text(item.get("chamberOGBox") or item.get("ChamberOGBox")),
                        self._as_text(item.get("chamberContact1") or item.get("ChamberContact1")),
                        self._as_text(item.get("chamberContact2") or item.get("ChamberContact2")),
                        self._as_text(item.get("chamberContact3") or item.get("ChamberContact3")),
                        self._as_text(item.get("remarks") or item.get("Remarks")),
                    ]
                )
            table = Table(
                data,
                colWidths=[1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.2 * inch],
            )
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

        section.extend(self._build_image_gallery("Chamber Images", images))
        return section

    def _build_cooling_section(self, records: list, images: list):
        section = [Paragraph("RTU Cabinet Cooling", self.section_header)]
        if not records:
            section.append(self._build_placeholder_box("No cabinet cooling data recorded."))
        else:
            data = [["Fan Number", "Functional Status", "Remarks"]]
            for item in records:
                data.append(
                    [
                        self._as_text(item.get("fanNumber") or item.get("FanNumber")),
                        self._as_text(item.get("functionalStatus") or item.get("FunctionalStatus")),
                        self._as_text(item.get("remarks") or item.get("Remarks")),
                    ]
                )
            table = Table(data, colWidths=[1.2 * inch, 2.2 * inch, 2.2 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1976d2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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

        section.extend(self._build_image_gallery("Cabinet Cooling Images", images))
        return section

    def _build_dvr_section(self, records: list, images: list):
        section = [Paragraph("DVR Equipment Checks", self.section_header)]
        if not records:
            section.append(self._build_placeholder_box("No DVR equipment data recorded."))
        else:
            for idx, item in enumerate(records, start=1):
                section.append(Paragraph(f"DVR Set #{idx}", self.subsection_header))
                rows = [
                    ("DVR Communication", item.get("dvrComm") or item.get("DVRComm")),
                    ("DVR RAID Communication", item.get("dvrraidComm") or item.get("dvrRAIDComm") or item.get("DVRRAIDComm")),
                    ("Time Sync (NTP)", item.get("timeSyncNTPServer") or item.get("TimeSyncNTPServer")),
                    ("Recording 24 x 7", item.get("recording24x7") or item.get("Recording24x7")),
                    ("Remarks", item.get("remarks") or item.get("Remarks")),
                ]
                section.append(self._build_label_value_table(rows))
                section.append(Spacer(1, 12))

        section.extend(self._build_image_gallery("DVR Equipment Images", images))
        return section

    def _build_label_value_table(self, items):
        rows = [
            [Paragraph(label, self.card_label_style), Paragraph(self._as_text(value), self.card_value_style)]
            for label, value in items
        ]
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
        table = Table([[Paragraph(self._as_text(message), self.muted_text_style)]], colWidths=[5.7 * inch])
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
            gallery.append(Spacer(1, 8))
            return gallery

        cards: List = []
        for img_path in paths:
            img_flow = self._create_image_flowable(img_path)
            if not img_flow:
                continue
            card = Table([[img_flow]], colWidths=[2.8 * inch])
            card.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#dfe3eb")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]
                )
            )
            cards.append(card)

        if not cards:
            gallery.append(self._build_placeholder_box("Unable to display images for this section."))
            gallery.append(Spacer(1, 8))
            return gallery

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

        for item in images:
            directory = item.get("storedDirectory") or item.get("StoredDirectory")
            image_name = item.get("imageName") or item.get("ImageName")
            if not directory or not image_name:
                continue
            image_path = Path(directory) / image_name
            if not image_path.exists():
                logger.warning("RTU PDF image path not found: %s", image_path)
                continue
            metadata.append(image_path)

        return metadata

    def _create_image_flowable(self, image_path: Path, max_width=2.6 * inch, max_height=1.8 * inch):
        try:
            reader = ImageReader(str(image_path))
            width, height = reader.getSize()
            scale = min(max_width / width, max_height / height, 1)
            adjusted_width = width * scale
            adjusted_height = height * scale
            return Image(str(image_path), width=adjusted_width, height=adjusted_height)
        except Exception as exc:
            logger.warning("Unable to render RTU image %s: %s", image_path, exc)
            return None

    def _safe_get(self, data: dict, *keys: str):
        if not isinstance(data, dict):
            return None
        for key in keys:
            if not key:
                continue
            candidate = (
                data.get(key)
                or data.get(key[:1].upper() + key[1:])
                or data.get(key[:1].lower() + key[1:])
            )
            if candidate is not None:
                return candidate
        return None

    def _as_text(self, value):
        if value in (None, "", []):
            return "N/A"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, list):
            cleaned = [self._as_text(v) for v in value if v not in (None, "")]
            return ", ".join(cleaned) if cleaned else "N/A"
        if isinstance(value, dict):
            parts = []
            for k, v in value.items():
                formatted = self._as_text(v)
                if formatted and formatted != "N/A":
                    parts.append(f"{k}: {formatted}")
            return ", ".join(parts) if parts else "N/A"
        return str(value)

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
