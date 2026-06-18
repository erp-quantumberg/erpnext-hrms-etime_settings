import frappe
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime


def sync_etime_attendance():
    try:
        settings = frappe.get_single("ETime Settings")

        date_str = datetime.now().strftime("%d/%m/%Y")

        url = (
            f"{settings.api_url}"
            f"?Empcode=ALL"
            f"&FromDate={date_str}"
            f"&ToDate={date_str}"
        )

        response = requests.get(
            url,
            auth=HTTPBasicAuth(
                settings.api_username,
                settings.get_password("api_password")
            ),
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        last_sync = settings.last_sync_time
        latest_processed = last_sync

        for row in data.get("InOutPunchData", []):

            latest_processed = process_log(
                row=row,
                time_field="INTime",
                log_type="IN",
                latest_processed=latest_processed,
                last_sync=last_sync
            )

            latest_processed = process_log(
                row=row,
                time_field="OUTTime",
                log_type="OUT",
                latest_processed=latest_processed,
                last_sync=last_sync
            )

        if latest_processed:
            settings.last_sync_time = latest_processed
            settings.save(ignore_permissions=True)

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "eTime Attendance Sync"
        )


def process_log(
    row,
    time_field,
    log_type,
    latest_processed,
    last_sync
):

    punch_time = row.get(time_field)

    if not punch_time:
        return latest_processed

    if punch_time == "--:--":
        return latest_processed

    timestamp = datetime.strptime(
        f"{row['DateString']} {punch_time}",
        "%d/%m/%Y %H:%M"
    )

    if last_sync and timestamp <= last_sync:
        return latest_processed

    employee = frappe.db.get_value(
        "Employee",
        {
            "attendance_device_id": str(row["Empcode"])
        },
        "name"
    )

    if not employee:
        frappe.log_error(
            f"Employee not found for Empcode {row['Empcode']}",
            "eTime Employee Mapping"
        )
        return latest_processed

    exists = frappe.db.exists(
        "Employee Checkin",
        {
            "employee": employee,
            "time": timestamp
        }
    )

    if exists:
        return latest_processed

    doc = frappe.get_doc(
        {
            "doctype": "Employee Checkin",
            "employee": employee,
            "time": timestamp,
            "log_type": log_type,
            "device_id": "eTime Office"
        }
    )

    doc.insert(ignore_permissions=True)

    if not latest_processed or timestamp > latest_processed:
        latest_processed = timestamp

    return latest_processed