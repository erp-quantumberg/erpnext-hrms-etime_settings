import frappe
import requests
import base64
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

        auth_string = settings.get_password("auth_string")

        headers = {
            "Authorization": "Basic "
            + base64.b64encode(auth_string.encode()).decode()
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        frappe.logger().info(f"Records Found: {len(data.get('InOutPunchData', []))}")

        for row in data.get("InOutPunchData", []):

            process_log(row, "INTime", "IN")
            process_log(row, "OUTTime", "OUT")

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "eTime Attendance Sync"
        )


def process_log(row, time_field, log_type):

    punch_time = row.get(time_field)

    if not punch_time or punch_time == "--:--":
        return

    employee = frappe.db.get_value(
        "Employee",
        {"attendance_device_id": row["Empcode"]},
        "name"
    )

    if not employee:
        frappe.log_error(
            f"Employee not found for Empcode {row['Empcode']}",
            "eTime Employee Mapping"
        )
        return

    timestamp = datetime.strptime(
        f"{row['DateString']} {punch_time}",
        "%d/%m/%Y %H:%M"
    )

    if frappe.db.exists(
        "Employee Checkin",
        {
            "employee": employee,
            "time": timestamp,
            "log_type": log_type
        }
    ):
        return

    frappe.get_doc({
        "doctype": "Employee Checkin",
        "employee": employee,
        "time": timestamp,
        "log_type": log_type,
        "device_id": "eTime Office"
    }).insert(ignore_permissions=True)