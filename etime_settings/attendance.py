import frappe
import requests
import base64
from datetime import datetime, timedelta


def sync_etime_attendance():
    try:
        settings = frappe.get_single("ETime Settings")

        to_date = datetime.now()
        from_date = to_date - timedelta(days=3)

        url = (
            f"{settings.api_url}"
            f"?Empcode=ALL"
            f"&FromDate={from_date.strftime('%d/%m/%Y')}"
            f"&ToDate={to_date.strftime('%d/%m/%Y')}"
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

        latest_timestamp = settings.last_sync_time

        for row in data.get("InOutPunchData", []):

            try:
                ts1 = process_log(row, "INTime", "IN")
                ts2 = process_log(row, "OUTTime", "OUT")

                if ts1 and (not latest_timestamp or ts1 > latest_timestamp):
                    latest_timestamp = ts1

                if ts2 and (not latest_timestamp or ts2 > latest_timestamp):
                    latest_timestamp = ts2

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Employee Sync Error : {row.get('Empcode')}"
                )

        if latest_timestamp:
            settings.last_sync_time = latest_timestamp
            settings.save(ignore_permissions=True)

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "eTime Attendance Sync"
        )


def process_log(row, time_field, log_type):

    punch_time = row.get(time_field)

    if not punch_time or punch_time == "--:--":
        return None

    timestamp = datetime.strptime(
        f"{row['DateString']} {punch_time}",
        "%d/%m/%Y %H:%M"
    )

    try:

        frappe.call(
            "hrms.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field",
            employee_field_value=row["Empcode"],
            timestamp=timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            device_id="Office Log",
            log_type=log_type,
            employee_fieldname="attendance_device_id"
        )

        return timestamp

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            f"Failed Employee {row['Empcode']}"
        )

        return None