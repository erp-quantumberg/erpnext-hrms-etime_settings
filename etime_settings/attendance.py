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

        frappe.logger().info(
            f"Records Found: {len(data.get('InOutPunchData', []))}"
        )

        for row in data.get("InOutPunchData", []):

            try:
                process_log(row, "INTime", "IN")
                process_log(row, "OUTTime", "OUT")

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"Employee Sync Error : {row.get('Empcode')}"
                )

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "eTime Attendance Sync"
        )


def process_log(row, time_field, log_type):

    punch_time = row.get(time_field)

    if not punch_time:
        return

    if punch_time == "--:--":
        return

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

    except Exception:

        frappe.log_error(
            frappe.get_traceback(),
            f"Failed Employee {row['Empcode']}"
        )