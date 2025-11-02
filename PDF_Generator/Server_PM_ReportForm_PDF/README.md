# Server PM Report PDF Generator

This Python service generates PDF reports for Server PM (Preventive Maintenance) reports by listening to MQTT messages and retrieving data from the API.

## Features

- **MQTT Integration**: Listens to `controltower/server_pm_reportform_pdf/+` topic for PDF generation requests
- **API Data Retrieval**: Fetches comprehensive report data from `/api/PMReportFormServer/{id}` endpoint
- **Comprehensive PDF Generation**: Creates multi-page PDFs with each component on separate pages
- **Component Coverage**: Includes all Server PM components like Server Health, Hard Drive Health, CPU/RAM Usage, Willowlynx statuses, Database operations, etc.
- **Status Updates**: Sends real-time status updates via MQTT to `controltower/server_pm_reportform_pdf_status/{report_id}`

## Architecture

### Components

1. **main.py**: Main service that handles MQTT communication, API calls, and orchestrates PDF generation
2. **config.py**: Configuration management for API, MQTT, database, and PDF settings
3. **pdf_generator.py**: PDF generation logic with separate pages for each component
4. **database_manager.py**: Database operations for retrieving report data (if needed)

### MQTT Message Flow

1. **Web Application** publishes to: `controltower/server_pm_reportform_pdf/{report_id}`
   ```json
   {
     "report_id": "12345",
     "requested_by": "user@example.com",
     "timestamp": "2024-01-15T10:30:00"
   }
   ```

2. **Service** processes the request and publishes status updates to: `controltower/server_pm_reportform_pdf_status/{report_id}`
   ```json
   {
     "report_id": "12345",
     "status": "processing|completed|failed",
     "message": "Status description",
     "timestamp": "2024-01-15T10:30:05"
   }
   ```

## Installation

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables** (optional):
   Create a `.env` file or set environment variables:
   ```
   API_BASE_URL=http://localhost:5000
   MQTT_BROKER=localhost
   MQTT_PORT=1883
   PDF_OUTPUT_DIR=./PDF_File
   INCLUDE_TIMESTAMP=true
   ```

## Configuration

The service uses `config.py` for configuration. Key settings include:

- **API Configuration**: Base URL, timeout settings
- **MQTT Configuration**: Broker, port, credentials, topics
- **Database Configuration**: Connection settings for SQL Server
- **PDF Configuration**: Output directory, filename patterns
- **Logging Configuration**: Log levels and file locations

## Usage

### Running the Service

```bash
python main.py
```

The service will:
1. Connect to the MQTT broker
2. Subscribe to `controltower/server_pm_reportform_pdf/+`
3. Wait for incoming PDF generation requests
4. Process requests asynchronously
5. Generate PDFs and save to the `PDF_File` folder
6. Send status updates via MQTT

### Testing

The service integrates with your web application. When you trigger a PDF generation request from the web interface, it will:

1. Publish an MQTT message to `controltower/server_pm_reportform_pdf/{report_id}`
2. The Python service will receive the message
3. Process the request and generate the PDF
4. Send status updates back via MQTT to `controltower/server_pm_reportform_pdf_status/{report_id}`
5. The web application will receive the status updates

To test the complete workflow:
1. Start the Python service: `python main.py`
2. Use your web application to request a PDF generation
3. Monitor the service logs to see the processing
4. Check the `PDF_File` folder for the generated PDF

## PDF Structure

The generated PDF includes the following pages:

1. **Cover Page**: Report information, job details, company information
2. **Sign-off Page**: Attendance and witness information
3. **Component Pages** (each on separate page):
   - Server Health Check
   - Hard Drive Health Check
   - Disk Usage Check
   - CPU and RAM Usage Check
   - Network Health Check
   - Willowlynx Process Status
   - Willowlynx Network Status
   - Willowlynx RTU Status
   - Willowlynx Historical Trend
   - Willowlynx Historical Report
   - Willowlynx CCTV Camera
   - Monthly Database Creation
   - Database Backup
   - Time Sync
   - Hot Fixes
   - Auto Fail Over
   - ASA Firewall
   - Software Patch Summary

## API Integration

The service calls the API endpoint: `GET /api/PMReportFormServer/{report_id}`

Expected API response structure:
```json
{
  "reportForm": { ... },
  "pmReportFormServer": { ... },
  "pmServerHealths": [ ... ],
  "pmServerHardDriveHealths": [ ... ],
  "pmServerDiskUsages": [ ... ],
  "pmServerCPUAndRAMUsages": [ ... ],
  // ... other component data arrays
}
```

## Error Handling

- **API Errors**: Logged and status updates sent via MQTT
- **PDF Generation Errors**: Detailed logging and error status updates
- **MQTT Connection Issues**: Automatic reconnection attempts
- **Database Errors**: Graceful handling with fallback options

## Logging

Logs are written to:
- **Console**: Real-time status information
- **File**: `server_pm_pdf_service.log` for detailed logging

Log levels can be configured in the main.py file.

## File Structure