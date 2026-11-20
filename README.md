# ETime Settings

ETime Settings integrates an eTime attendance device/API with Frappe HRMS. It fetches punch data from the configured eTime endpoint and creates HRMS Employee Checkin records.

## Features

- Provides an **ETime Settings** single DocType with fields for API Username, Auth String, API URL, and Last Sync Time.
- Runs an attendance sync daily through a Frappe scheduler event.
- Requests punch data for all employees for the current date and the previous three days.
- Sends IN and OUT punches to HRMS using each record's employee code as the `attendance_device_id`.
- Saves the most recent successfully processed punch time in **Last Sync Time**.
- Logs API and punch-processing errors in the Frappe Error Log.

## Requirements

- A Frappe Bench and site using the `version-16` branch.
- Python 3.14 or newer.
- The Frappe Framework app (`frappe`).
- The ERPNext app (`erpnext`) and Frappe HRMS app (`hrms`) installed on the site. The sync calls HRMS's Employee Checkin helper and requires its Employee Checkin functionality.
- The Python `requests` library in the Bench environment.
- An accessible eTime API endpoint and credentials with permission to retrieve attendance data.

Install ERPNext and HRMS before installing this app. Also install any additional apps required by your chosen HRMS release.

## Installation

From the Bench directory, fetch this app and install it on the target site:

```bash
cd ~/frappe-bench
bench get-app --branch version-16 https://github.com/frappe/erpnext.git
bench get-app --branch version-16 https://github.com/frappe/hrms.git
bench get-app --branch version-16 https://github.com/erp-quantumberg/erpnext-hrms-etime_settings.git
bench --site your-site.example install-app erpnext
bench --site your-site.example install-app hrms
bench --site your-site.example install-app etime_settings
```

Replace `your-site.example` with the name of your Frappe site. Ensure ERPNext and a `version-16`-compatible Frappe HRMS release, along with any apps HRMS requires, are installed on the site before installing ETime Settings.

After installation, run migrations and build assets if your deployment process requires them:

```bash
bench --site your-site.example migrate
bench build
```

## Setup

1. Sign in to the site as a user with the **System Manager** role.
2. Open **ETime Settings** from the Desk search.
3. Configure the fields:
   - **API URL**: the eTime endpoint that accepts `Empcode`, `FromDate`, and `ToDate` query parameters.
   - **Auth String**: the credential string expected by the eTime API's HTTP Basic authentication. The app Base64-encodes this value for the `Authorization` header. Keep it secret and use an HTTPS API URL.
   - **API Username**: available as a settings field, but the current sync implementation does not read or send it.
   - **Last Sync Time**: maintained by the sync; it is not used as the API query's starting date.
4. Save the settings and confirm the API URL and credentials work from the Bench host.
5. Ensure the Frappe scheduler is enabled and workers are running. The app schedules the sync daily; no separate cron entry is needed.

The API response is expected to be JSON with an `InOutPunchData` array. Each punch record should include `Empcode`, `DateString` (`DD/MM/YYYY`), `INTime`, and `OUTTime`. Punch times should use `HH:MM`; empty values and `--:--` are skipped. The employee code must match an employee's `attendance_device_id` in HRMS.

To run a sync manually for diagnosis:

```bash
bench --site your-site.example execute etime_settings.attendance.sync_etime_attendance
```

## Configuration notes

- Each run requests data for all employees (`Empcode=ALL`) from the current date and the previous three days. **Last Sync Time** is recorded for reference but does not narrow the requested date range.
- The API request has a 60-second timeout. The response must have a successful HTTP status and valid JSON.
- Punches are sent to `hrms.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field` with `employee_fieldname="attendance_device_id"` and `device_id="Office Log"`.
- Check the Frappe Error Log for API failures and errors processing individual employee records.

## Troubleshooting

| Problem                             | Checks                                                                                                                                                                                              |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No check-ins are created            | Confirm HRMS is installed, the scheduler and workers are running, the API response contains `InOutPunchData`, and each `Empcode` matches an employee's `attendance_device_id`.                      |
| API request fails                   | Verify the endpoint URL, network access from the Bench host, Basic authentication credentials, and that the endpoint responds within 60 seconds. Review the Frappe Error Log for the request error. |
| Punches are skipped                 | Check `DateString` uses `DD/MM/YYYY`, punch fields use `HH:MM`, and the values are not blank or `--:--`.                                                                                            |
| A manual run fails                  | Run the `bench execute` command above and inspect **Error Log** in Desk for the `eTime Attendance Sync` or `Employee Sync Error` entries.                                                           |
| Updated settings appear ineffective | Confirm the saved **ETime Settings** record and verify the site scheduler is enabled. The **API Username** field is currently not used by the sync.                                                 |

## Contributing

Contributions are welcome. Keep changes focused, follow the existing Frappe app conventions, and include tests for behavior changes where appropriate.

Install and enable the repository's pre-commit hooks before submitting changes:

```bash
cd apps/etime_settings
pre-commit install
```

The configured checks include Ruff, ESLint, Prettier, and pyupgrade. To run the app tests from the Bench directory:

```bash
bench --site your-site.example run-tests --app etime_settings
```

## License

This project is licensed under the MIT License. See [license.txt](license.txt).
