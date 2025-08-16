import pandas as pd
import pymssql
import warnings
import re
import math
import json
import traceback
import paho.mqtt.client as mqtt
from datetime import datetime

warnings.simplefilter("ignore")

# --- MQTT Config ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
UPLOAD_TOPIC = "servicereportsystem/upload"
STATUS_TOPIC = "servicereportsystem/status"

# --- DB Config ---
CONN_PARAMS = {
    'server': 'localhost',
    'database': 'ControlTowerDatabase',
    'user': 'opmadminuser',
    'password': 'Willowglen@12345',
}

EXPECTED_COLUMNS = [
    'S/N', 'Asset Report Number', 'Reported Date', 'Location',
    'Issue reported', 'Issue Found', 'Rectified Action',
    'Rectified Date', 'Status', 'Owner', 'Remark'
]

# ===================== EXCEL & DB FUNCTIONS =====================

def read_excel_file(file_path, expected_columns):
    xls = pd.ExcelFile(file_path)
    all_data = []
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
        df.columns = df.columns.str.replace(u'\xa0', ' ').str.strip()
        match_count = sum(1 for col in df.columns if col in expected_columns)
        if match_count >= len(expected_columns) // 2:
            df = df[[col for col in expected_columns if col in df.columns]]
            df = df.dropna(how='all')
            for record in df.to_dict('records'):
                record['_sheet'] = sheet_name
                all_data.append(record)
    return all_data

def process_location_warehouse(excel_data, user_id, conn):
    cursor = conn.cursor()
    location_map = {}
    newly_added = 0
    locations = set()
    for row in excel_data:
        loc = row.get('Location')
        if loc and str(loc).strip() and "grand total" not in str(loc).lower():
            locations.add(str(loc).strip())

    for loc in locations:
        cursor.execute("SELECT ID FROM LocationWarehouses WHERE Name=%s AND IsDeleted=0", (loc,))
        row = cursor.fetchone()
        if row:
            location_id = row[0]
        else:
            cursor.execute("""
                INSERT INTO LocationWarehouses
                (ID, Name, IsDeleted, CreatedDate, UpdatedDate, CreatedBy, UpdatedBy)
                VALUES (NEWID(), %s, 0, GETUTCDATE(), GETUTCDATE(), %s, %s)
            """, (loc, user_id, user_id))
            cursor.execute("SELECT ID FROM LocationWarehouses WHERE Name=%s AND IsDeleted=0", (loc,))
            location_id = cursor.fetchone()[0]
            newly_added += 1
        location_map[loc.lower()] = location_id

    conn.commit()
    for row in excel_data:
        loc = row.get('Location')
        if loc and str(loc).strip():
            row['LocationID'] = location_map.get(loc.strip().lower())
            row.pop('Location', None)

    return newly_added

def process_form_status_warehouse(excel_data, user_id, conn):
    cursor = conn.cursor()
    status_map = {}
    newly_added = 0
    statuses = set()
    for row in excel_data:
        status = row.get('Status')
        if status and str(status).strip():
            statuses.add(str(status).strip())

    for status in statuses:
        cursor.execute("SELECT ID FROM FormStatusWarehouses WHERE Name=%s AND IsDeleted=0", (status,))
        row = cursor.fetchone()
        if row:
            status_id = row[0]
        else:
            cursor.execute("""
                INSERT INTO FormStatusWarehouses
                (ID, Name, IsDeleted, CreatedDate, UpdatedDate, CreatedBy, UpdatedBy)
                VALUES (NEWID(), %s, 0, GETUTCDATE(), GETUTCDATE(), %s, %s)
            """, (status, user_id, user_id))
            cursor.execute("SELECT ID FROM FormStatusWarehouses WHERE Name=%s AND IsDeleted=0", (status,))
            status_id = cursor.fetchone()[0]
            newly_added += 1
        status_map[status.lower()] = status_id

    conn.commit()
    for row in excel_data:
        status = row.get('Status')
        if status and str(status).strip():
            row['FormStatusID'] = status_map.get(status.strip().lower())
            row.pop('Status', None)

    return newly_added

def prepare_pf_data(excel_data):
    key_map = {
        'Asset Report Number': 'JobNumber',
        'Reported Date': 'FailureDetectedDate',
        'Rectified Date': 'CompletionDate',
        'Owner': 'Customer',
        'Remark': 'FormStatusRemark',
        'Issue reported': 'IssueReported',
        'Issue Found': 'IssueFound',
        'Rectified Action': 'RectifiedAction',
    }
    pf_data = []
    for row in excel_data:
        pf_row = {}
        for old_key, new_key in key_map.items():
            value = row.get(old_key)
            if value is None or (isinstance(value, float) and math.isnan(value)):
                value = '' if new_key == 'FormStatusRemark' else None
            if new_key == 'Customer' and (value is None or str(value).strip() in ['', 'N.A', 'SP']):
                value = row.get('_sheet')
            pf_row[new_key] = value
        for date_key in ['FailureDetectedDate', 'CompletionDate']:
            if pd.isnull(pf_row.get(date_key)):
                pf_row[date_key] = None
        pf_row['LocationID'] = row.get('LocationID')
        pf_row['FormStatusID'] = row.get('FormStatusID')
        pf_data.append(pf_row)
    return pf_data

def insert_service_report_forms(pf_data, conn, user_id):
    cursor = conn.cursor()
    inserted_count = 0
    cursor.execute("SELECT MAX(JobNumber) FROM ServiceReportForms")
    row = cursor.fetchone()
    max_job_num = row[0] if row and row[0] else None

    def next_job_number(latest):
        if latest is None:
            return "M001"
        match = re.match(r'M(\d+)', latest)
        if match:
            num = int(match.group(1)) + 1
            return f"M{num:03d}"
        return "M001"

    service_report_map = {}
    for row in pf_data:
        job_num = row.get('JobNumber')
        if not job_num or str(job_num).strip() in ['', 'N.A', None]:
            job_num = next_job_number(max_job_num)
            max_job_num = job_num
        row['JobNumber'] = job_num

        cursor.execute("SELECT COUNT(1) FROM ServiceReportForms WHERE JobNumber=%s", (job_num,))
        if cursor.fetchone()[0]:
            cursor.execute("SELECT ID FROM ServiceReportForms WHERE JobNumber=%s", (job_num,))
            service_report_id = cursor.fetchone()[0]
            service_report_map[job_num] = service_report_id
            continue

        cursor.execute("""
            INSERT INTO ServiceReportForms
            (ID, JobNumber, FailureDetectedDate, CompletionDate, Customer, LocationID,
             IsDeleted, CreatedDate, UpdatedDate, CreatedBy, UpdatedBy)
            VALUES (NEWID(), %s, %s, %s, %s, %s, 0, GETUTCDATE(), GETUTCDATE(), %s, %s)
        """, (
            job_num,
            row.get('FailureDetectedDate'),
            row.get('CompletionDate'),
            row.get('Customer'),
            row.get('LocationID'),
            user_id,
            user_id
        ))
        cursor.execute("SELECT ID FROM ServiceReportForms WHERE JobNumber=%s", (job_num,))
        service_report_map[job_num] = cursor.fetchone()[0]
        inserted_count += 1

    conn.commit()
    return inserted_count, service_report_map

def insert_related_tables(pf_data, service_report_map, conn, user_id):
    cursor = conn.cursor()
    for row in pf_data:
        job_num = row.get('JobNumber')
        service_report_id = service_report_map.get(job_num)
        if not service_report_id:
            continue
        if row.get('IssueReported'):
            cursor.execute("""
                INSERT INTO IssueReported
                (ID, Description, ServiceReportFormID, CreatedBy, IsDeleted, CreatedDate, UpdatedDate)
                VALUES (NEWID(), %s, %s, %s, 0, GETUTCDATE(), GETUTCDATE())
            """, (row['IssueReported'], service_report_id, user_id))
        if row.get('IssueFound'):
            cursor.execute("""
                INSERT INTO IssueFound
                (ID, Description, ServiceReportFormID, CreatedBy, IsDeleted, CreatedDate, UpdatedDate)
                VALUES (NEWID(), %s, %s, %s, 0, GETUTCDATE(), GETUTCDATE())
            """, (row['IssueFound'], service_report_id, user_id))
        if row.get('RectifiedAction'):
            cursor.execute("""
                INSERT INTO ActionTaken
                (ID, Description, ServiceReportFormID, CreatedBy, IsDeleted, CreatedDate, UpdatedDate)
                VALUES (NEWID(), %s, %s, %s, 0, GETUTCDATE(), GETUTCDATE())
            """, (row['RectifiedAction'], service_report_id, user_id))
        if row.get('FormStatusRemark') != '':
            cursor.execute("""
                INSERT INTO FormStatus
                (ID, Remark, FormStatusWarehouseID, ServiceReportFormID, CreatedBy, IsDeleted, CreatedDate, UpdatedDate)
                VALUES (NEWID(), %s, %s, %s, %s, 0, GETUTCDATE(), GETUTCDATE())
            """, (row['FormStatusRemark'], row.get('FormStatusID'), service_report_id, user_id))
    conn.commit()

def update_import_file_status(conn, file_id, user_id, status='success', error_msg=None):
    cursor = conn.cursor()
    imported_status = 'Success' if status=='success' else 'Fail'
    update_query = """
        UPDATE ImportFileRecords
        SET ImportedStatus=%s, UpdatedDate=GETUTCDATE(), UpdatedBy=%s
        WHERE ID=%s
    """
    cursor.execute(update_query, (imported_status, user_id, file_id))
    conn.commit()

# ===================== MQTT =====================

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code "+str(rc))
    client.subscribe(UPLOAD_TOPIC)

def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}")
    payload_json = msg.payload.decode()
    process_uploaded_file(payload_json)

def send_status(file_id, status='success', error_msg=None):
    message = {"fileId": file_id, "status": status}
    if error_msg:
        message["error"] = error_msg
    client.publish(STATUS_TOPIC, json.dumps(message))
    print("Published status:", message)

# ===================== MAIN PROCESS =====================

def process_uploaded_file(payload_json):
    payload = json.loads(payload_json)
    file_id = payload.get("fileId")
    file_path = payload.get("filePath")
    user_id = payload.get("uploadedBy")

    try:
        conn = pymssql.connect(**CONN_PARAMS)

        excel_data = read_excel_file(file_path, EXPECTED_COLUMNS)
        if not excel_data:
            raise ValueError("No data found in Excel.")

        loc_added = process_location_warehouse(excel_data, user_id, conn)
        status_added = process_form_status_warehouse(excel_data, user_id, conn)
        pf_data = prepare_pf_data(excel_data)
        sr_inserted, service_report_map = insert_service_report_forms(pf_data, conn, user_id)
        insert_related_tables(pf_data, service_report_map, conn, user_id)

        update_import_file_status(conn, file_id, user_id, status='success')
        send_status(file_id, status='success')

        print(f"Processing done. Locations added: {loc_added}, Statuses added: {status_added}, ServiceReports inserted: {sr_inserted}")

    except Exception as e:
        error_msg = traceback.format_exc()
        print("Error:", error_msg)
        try:
            if 'conn' in locals():
                update_import_file_status(conn, file_id, user_id, status='failed', error_msg=str(e))
        except:
            pass
        send_status(file_id, status='failed', error_msg=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

# ===================== RUN MQTT CLIENT =====================

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
