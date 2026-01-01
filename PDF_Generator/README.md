# PDF Generator Service

Clean, organized PDF generation service for Control Tower Report Management System.

## 📁 Folder Structure

```
PDF_Generator/
├── main.py                     # Main service - handles all report types
├── config.py                   # Centralized configuration (ALL changeable values)
├── database_manager.py         # Shared database utilities
├── requirements.txt            # Python dependencies
│
├── PDF_File/                   # Output folder for ALL generated PDFs
│
├── CM_Report/                  # Corrective Maintenance Reports
│   └── cm_pdf_generator.py     # CM PDF generator logic
│
├── Server_PM_Report/           # Server Preventive Maintenance Reports
│   ├── server_pm_pdf_generator.py
│   └── resources/              # Server PM specific resources
│       └── ServerPMReportForm/
│
├── RTU_PM_Report/              # RTU Preventive Maintenance Reports
│   └── rtu_pm_pdf_generator.py
│
└── resources/                  # Shared resources
    └── willowglen_letterhead.png
```

## 🎯 Key Features

### One Main Service
- **Single `main.py`** controls all PDF generation logic
- Handles 3 report types: CM, Server PM, RTU PM
- Supports 2 modes per report type:
  - Regular PDF (while editing reports)
  - Signature-based Final Report PDF (when closing with signatures)

### Centralized Configuration
- **All changeable values in `config.py`**:
  - API URLs and credentials
  - MQTT broker settings
  - Topic names (regular + signature)
  - Database connection
  - File paths
  - PDF output directory
  - Image storage paths

### Clean Separation
- Each report type has its own folder
- PDF generators are isolated by type
- **ONE shared PDF_File output folder** for all PDFs
- Shared resources (letterhead) in common folder

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# API Configuration
API_BASE_URL=https://localhost:7240
API_AUTH_EMAIL=admin@willowglen.com
API_AUTH_PASSWORD=Admin@123

# MQTT Configuration
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883

# Database Configuration
DB_SERVER=localhost
DB_NAME=ControlTower

# File Paths
PDF_OUTPUT_DIR=C:\ControlTower\PDFs
IMAGE_BASE_PATH=C:\Temp\ReportFormImages
```

### MQTT Topics

#### Regular PDF Generation (while editing)
- `controltower/cm_reportform_pdf/{report_id}`
- `controltower/server_pm_reportform_pdf/{report_id}`
- `controltower/rtu_pm_reportform_pdf/{report_id}`

#### Signature-based Final Report PDF (when closing with signatures)
- `controltower/cm_reportform_signature_pdf/{report_id}`
- `controltower/server_pm_reportform_signature_pdf/{report_id}`
- `controltower/rtu_pm_reportform_signature_pdf/{report_id}`

## 🚀 Installation

```bash
# Navigate to PDF_Generator folder
cd ControlTower_Python/PDF_Generator

# Install dependencies
pip install -r requirements.txt
```

## ▶️ Running the Service

```bash
# Run the main service
python main.py
```

The service will:
1. Connect to MQTT broker
2. Subscribe to all 6 topics (3 regular + 3 signature)
3. Listen for PDF generation requests
4. Generate PDFs and save to `PDF_File/` folder
5. Publish status updates via MQTT

## 📝 How It Works

### Regular PDF Generation Flow

```
User clicks "Download Report" while editing
    ↓
Frontend calls API: POST /api/CMReportForm/{id}/generate-pdf
    ↓
API publishes MQTT: controltower/cm_reportform_pdf/{id}
    ↓
Python main.py receives message
    ↓
Fetches report data from API
    ↓
Calls CM PDF generator
    ↓
Generates PDF → saves to PDF_File/
    ↓
Publishes status: controltower/cm_reportform_pdf_status/{id}
    ↓
API receives PDF bytes and returns to frontend
```

### Signature-based Final Report Flow

```
User closes report with signatures
    ↓
Frontend uploads signatures to database
    ↓
Frontend calls API: POST /api/CMReportForm/{id}/generate-final-report-pdf
    ↓
API publishes MQTT: controltower/cm_reportform_signature_pdf/{id}
    ↓
Python main.py receives message
    ↓
Fetches report data from API
    ↓
Fetches signature images from database
    ↓
Calls CM PDF generator with signatures
    ↓
Generates PDF with embedded signatures → saves to PDF_File/
    ↓
Publishes status: controltower/cm_reportform_signature_pdf_status/{id}
    ↓
API saves PDF to database as final report
```

## 🧩 Components

### main.py
- Central orchestrator for all PDF generation
- MQTT client management
- API authentication and data fetching
- Database queries for signature images
- Routes requests to appropriate PDF generators
- Handles both regular and signature-based PDFs

### config.py
- **Single source of truth** for all configuration
- Helper methods for:
  - `get_pdf_path(job_no, report_type)` - Generate output path
  - `get_mqtt_topics(report_type, is_signature)` - Get topic patterns
  - `get_api_endpoint(report_type, report_id)` - Get API endpoint
- Run `python config.py` to verify configuration

### CM_Report/cm_pdf_generator.py
- Generates Corrective Maintenance report PDFs
- Supports signature rendering for final reports
- Includes sections:
  - Basic information
  - Timeline
  - Issue details
  - Action taken
  - Material used
  - Before/after images
  - Signatures (for final reports)

### Server_PM_Report/server_pm_pdf_generator.py
- Generates Server Preventive Maintenance report PDFs
- Comprehensive server health data
- Multiple component sections
- TODO: Add signature support

### RTU_PM_Report/rtu_pdf_generator.py
- Generates RTU Preventive Maintenance report PDFs
- RTU cabinet checks
- Equipment inspections
- TODO: Add signature support

### database_manager.py
- Shared database utilities
- Connection pooling
- Query execution helpers

## 📊 PDF Output

All PDFs are saved to: `PDF_File/`

Filename format:
- Regular: `{ReportType}_Report_{JobNo}_{Timestamp}.pdf`
  - Example: `CM_Report_10010001_20251208_150000.pdf`
- Final Report: `{ReportType}_FinalReport_{JobNo}_{Timestamp}.pdf`
  - Example: `CM_FinalReport_10010001_20251208_150000.pdf`

## 🔍 Troubleshooting

### Service won't start
```bash
# Check config
python config.py

# Verify MQTT broker is running
# Test connection: telnet localhost 1883

# Check database connection
# Ensure ODBC Driver 17 for SQL Server is installed
```

### PDFs not generating
```bash
# Check logs in console output
# Look for:
#   - MQTT connection status
#   - API authentication success
#   - Report data fetched
#   - PDF generation started/completed

# Check PDF_File directory permissions
# Ensure folder exists and is writable
```

### Signatures not appearing
```bash
# Verify signatures exist in database:
SELECT * FROM ReportFormImages 
WHERE ReportFormID = 'your-guid' 
  AND ReportImageTypeID IN (
    SELECT ID FROM ReportFormImageTypes 
    WHERE ImageTypeName IN ('AttendedBySignature', 'ApprovedBySignature')
  )

# Check IMAGE_BASE_PATH in config.py
# Verify files exist at the paths in database
```

## 🛠️ Development

### Adding a New Report Type

1. Create new folder: `NewReport/`
2. Add PDF generator: `NewReport/new_report_pdf_generator.py`
3. Update `config.py`:
   - Add topic constants
   - Add to `get_mqtt_topics()` method
   - Add to `get_api_endpoint()` method
4. Update `main.py`:
   - Import new PDF generator
   - Add topic subscription
   - Add generator initialization
   - Add to routing logic

### Adding Signature Support to Server PM / RTU PM

Follow the pattern from `cm_pdf_generator.py`:

1. Add `_build_signature_section()` method
2. In `generate_pdf()`, check for `signatureImages` in `report_data`
3. If signatures exist, call `_build_signature_section()`
4. Render signatures in a professional table format

## 📦 Dependencies

See `requirements.txt`:
- `paho-mqtt` - MQTT client
- `reportlab` - PDF generation
- `Pillow` - Image processing
- `pyodbc` - Database connectivity
- `aiohttp` - Async HTTP client
- `python-dotenv` - Environment variables

## 🎓 Best Practices

1. **Always use `config` object** - Never hardcode values
2. **One PDF_File folder** - All PDFs in single location
3. **Centralized logging** - Use logger, not print()
4. **Error handling** - Graceful failures, informative messages
5. **Status updates** - Always publish MQTT status (success/failure)
6. **Resource cleanup** - Close connections, free memory

## 📞 Support

For issues or questions:
1. Check this README
2. Review `SIGNATURE_PDF_IMPLEMENTATION_SUMMARY.md`
3. Check logs in console output
4. Verify configuration with `python config.py`

## 📜 License

Internal use only - Willowglen Control Tower Project

