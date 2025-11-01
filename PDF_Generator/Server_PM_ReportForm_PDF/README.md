# Server PM Report PDF Generator

A Python service that generates professional PDF reports for Server Preventive Maintenance (PM) reports. The service integrates with the ControlTower web application through MQTT messaging and retrieves data via REST API calls.

## Features

- **API Integration**: Retrieves data using the same REST API endpoints as the web application
- **MQTT Integration**: Listens for PDF generation requests via MQTT topics
- **Professional PDF Generation**: Creates formatted PDF reports with company branding
- **Asynchronous Processing**: Handles multiple requests concurrently
- **Real-time Status Updates**: Provides progress updates via MQTT
- **Comprehensive Reporting**: Includes all Server PM components and data

## Architecture

```
Web Application → MQTT Topic → Python Service → REST API → PDF Generation
```

1. **Web UI**: User clicks "Download PDF" button
2. **MQTT Message**: Web application publishes generation request
3. **Python Service**: Receives MQTT message and processes request
4. **API Call**: Service calls REST API to retrieve data (same endpoint as web app)
5. **PDF Generation**: Creates professional PDF report
6. **Status Updates**: Sends progress updates via MQTT

## Directory Structure

```
Server_PM_ReportForm_PDF/
├── main.py                 # Main service entry point
├── config.py              # Configuration management
├── pdf_generator.py       # PDF generation logic
├── requirements.txt       # Python dependencies
├── install_requirements.bat # Windows installation script
├── test_setup.py         # Setup verification script
├── README.md             # This file
├── generated_pdfs/       # Output directory for PDFs
├── resources/            # Images and assets
│   ├── willowglen_letterhead.png
│   └── ServerPMReportForm/
│       ├── ServerHealth.png
│       ├── HardDriveHealth.png
│       ├── CPUAndRamUsage.png
│       ├── WillowlynxProcessStatus.png
│       ├── WillowlynxNetworkStatus.png
│       ├── WillowlynxRTUStatus.png
│       ├── WillowlynxHistoricalReport.png
│       └── WillowlynxSumpPitCCTVCamera.png
└── templates/            # PDF templates (future use)
```

## Prerequisites

- Python 3.8 or higher
- ControlTower API server running
- MQTT broker (optional, for real-time updates)
- Required Python packages (see requirements.txt)

## Installation

### 1. Install Dependencies

**Option A: Using the batch script (Windows)**
```bash
cd Server_PM_ReportForm_PDF
install_requirements.bat
```

**Option B: Manual installation**
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create environment variables or modify `config.py`:

```bash
# API Configuration (matches web application)
API_BASE_URL=https://localhost:7145

# MQTT Configuration
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_TOPIC_PDF_GENERATE=server_pm/pdf/generate
MQTT_TOPIC_PDF_STATUS=server_pm/pdf/status

# PDF Output
PDF_OUTPUT_DIR=./generated_pdfs

# Company Information
COMPANY_NAME=Willowglen Systems Pte Ltd
COMPANY_ADDRESS=1 Kaki Bukit Road 1, #02-29 Enterprise One, Singapore 415934
COMPANY_PHONE=+65 6741 8879
COMPANY_EMAIL=info@willowglen.com
```

### 3. Verify Setup

```bash
python test_setup.py
```

This will test:
- Module imports (pyodbc, paho-mqtt, reportlab, Pillow, aiohttp)
- Configuration loading
- API connectivity
- PDF generator initialization
- Required directories and assets

## Usage

### 1. Start the Service

```bash
python main.py
```

The service will:
- Connect to the MQTT broker
- Subscribe to PDF generation topics
- Wait for requests from the web application

### 2. Generate PDF via MQTT

Send a JSON message to the MQTT topic `server_pm/pdf/generate`:

```json
{
  "pm_report_form_server_id": 123,
  "request_id": "unique-request-id"
}
```

### 3. Monitor Status

Listen to the MQTT topic `server_pm/pdf/status` for updates:

```json
{
  "request_id": "unique-request-id",
  "status": "processing|completed|error",
  "message": "Status description",
  "timestamp": "2024-01-15T10:30:00"
}
```

## API Integration

The service uses the same REST API endpoint as the web application:

**Endpoint**: `GET /api/PMReportFormServer/{id}`

**Response Structure**: Same as used by `ServerPMReportFormDetails.js`

```json
{
  "pmReportFormServer": { ... },
  "reportForm": { ... },
  "pmServerHealths": [ ... ],
  "pmServerHardDriveHealths": [ ... ],
  "pmServerDiskUsageHealths": [ ... ],
  "pmServerCPUAndMemoryUsages": [ ... ],
  "pmServerNetworkHealths": [ ... ],
  "pmServerWillowlynxProcessStatuses": [ ... ],
  "pmServerWillowlynxNetworkStatuses": [ ... ],
  "pmServerWillowlynxRTUStatuses": [ ... ],
  "pmServerWillowlynxHistoricalTrends": [ ... ],
  "pmServerWillowlynxHistoricalReports": [ ... ],
  "pmServerWillowlynxCCTVCameras": [ ... ],
  "pmServerMonthlyDatabaseCreations": [ ... ],
  "pmServerDatabaseBackups": [ ... ],
  "pmServerTimeSyncs": [ ... ],
  "pmServerHotFixes": [ ... ],
  "pmServerFailOvers": [ ... ],
  "pmServerASAFirewalls": [ ... ],
  "pmServerSoftwarePatchSummaries": [ ... ]
}
```

## MQTT Topics

| Topic | Direction | Purpose |
|-------|-----------|----------|
| `server_pm/pdf/generate` | Web → Python | Request PDF generation |
| `server_pm/pdf/status` | Python → Web | Status updates |

## PDF Generation Process

1. **Receive Request**: Service receives MQTT message with PM report ID
2. **API Call**: Retrieves data from `/api/PMReportFormServer/{id}`
3. **Data Transformation**: Converts API response to PDF generator format
4. **PDF Creation**: Generates professional PDF with all sections
5. **File Output**: Saves PDF to `generated_pdfs/` directory
6. **Status Update**: Sends completion status via MQTT

## Configuration Options

### API Settings
- `API_BASE_URL`: Base URL for the ControlTower API (default: https://localhost:7145)

### MQTT Settings
- `MQTT_BROKER_HOST`: MQTT broker hostname
- `MQTT_BROKER_PORT`: MQTT broker port (default: 1883)
- `MQTT_TOPIC_PDF_GENERATE`: Topic for PDF generation requests
- `MQTT_TOPIC_PDF_STATUS`: Topic for status updates

### PDF Settings
- `PDF_OUTPUT_DIR`: Directory for generated PDFs
- `COMPANY_NAME`: Company name for PDF header
- `COMPANY_ADDRESS`: Company address
- `COMPANY_PHONE`: Company phone number
- `COMPANY_EMAIL`: Company email

## PDF Report Sections

The generated PDF includes all sections from the Server PM report:

1. **Report Information**: Job number, system details, dates
2. **Sign-off Information**: Attended by, witnessed by, dates, remarks
3. **Server Health Check**: System status and health metrics
4. **Hard Drive Health Check**: Storage device status
5. **Disk Usage Check**: Storage utilization
6. **CPU and RAM Usage Check**: System performance metrics
7. **Network Health Check**: Network connectivity status
8. **Willowlynx Process Status**: Process monitoring
9. **Willowlynx Network Status**: Network service status
10. **Willowlynx RTU Status**: RTU device status
11. **Willowlynx Historical Trend**: Trend analysis
12. **Willowlynx Historical Report**: Historical data reports
13. **Willowlynx CCTV Camera**: Camera system status
14. **Monthly Database Creation**: Database maintenance
15. **Database Backup**: Backup status and schedules
16. **Time Sync**: Time synchronization status
17. **Hot Fixes**: Applied system patches
18. **Auto Failover**: Failover system status
19. **ASA Firewall**: Firewall configuration and status
20. **Software Patch**: Software update summary

## Logging

The service logs all activities to:
- Console output (real-time monitoring)
- `pdf_generator.log` file (persistent logging)

Log levels: INFO, WARNING, ERROR

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Verify API server is running
   - Check `API_BASE_URL` configuration
   - Ensure network connectivity

2. **MQTT Connection Failed**
   - Verify MQTT broker is running
   - Check `MQTT_BROKER_HOST` and `MQTT_BROKER_PORT`
   - Verify network connectivity

3. **PDF Generation Failed**
   - Check if all required image assets exist
   - Verify write permissions to `generated_pdfs/` directory
   - Check log files for detailed error messages

4. **Missing Dependencies**
   - Run `pip install -r requirements.txt`
   - Verify Python version (3.8+)

### Debug Mode

Enable detailed logging by setting environment variable:
```bash
LOG_LEVEL=DEBUG
```

## Development

### Adding New Sections

1. Update the API data transformation in `main.py`
2. Add section generation method in `pdf_generator.py`
3. Update the main PDF generation flow
4. Add corresponding image assets if needed

### Testing

Run the setup test to verify configuration:
```bash
python test_setup.py
```

### Code Structure

- `main.py`: Service orchestration and MQTT handling
- `config.py`: Configuration management
- `pdf_generator.py`: PDF creation and formatting
- `test_setup.py`: Environment verification

## Integration with Web Application

The Python service integrates seamlessly with the ControlTower web application:

1. **Same Data Source**: Uses identical API endpoints
2. **Consistent Data**: Ensures PDF matches web display
3. **Real-time Updates**: MQTT provides immediate feedback
4. **Scalable**: Can handle multiple concurrent requests

### Web Application Changes Required

To integrate with the web application, add PDF download functionality:

```javascript
// Example: Add to ServerPMReportFormDetails.js
const handleDownloadPDF = async () => {
  const requestId = `pdf_${Date.now()}`;
  const message = {
    pm_report_form_server_id: id,
    request_id: requestId
  };
  
  // Publish MQTT message
  mqttClient.publish('server_pm/pdf/generate', JSON.stringify(message));
  
  // Listen for status updates
  mqttClient.subscribe('server_pm/pdf/status');
};
```

This architecture ensures maintainability, consistency, and scalability for the PDF generation system.