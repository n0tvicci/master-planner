# NinjaOne Diagnostic Script Library

28 PowerShell scripts for AI-assisted log analysis on problematic Windows devices.
Each script accepts `$output_url` (presigned S3 PUT URL) and `$incident_id` as parameters,
runs its diagnostics, and uploads a plain-text report to S3.

---

## System Health

| Script | Description |
|---|---|
| `get_system_info.ps1` | OS version, CPU, RAM, disk space, uptime |
| `get_top_processes.ps1` | Top 15 processes by CPU and memory usage |
| `get_disk_health.ps1` | SMART status, disk error events from Event Viewer |
| `get_disk_space_all.ps1` | Free/used space across all drives, not just C: |
| `get_performance_snapshot.ps1` | Live CPU %, memory %, disk I/O, page file usage |
| `get_crash_dumps.ps1` | List minidump files with timestamps (indicates BSODs/crashes) |

## Event Logs

| Script | Description |
|---|---|
| `get_event_logs_system.ps1` | Last 50 errors/warnings from System log |
| `get_event_logs_application.ps1` | Last 50 errors/warnings from Application log |
| `get_event_logs_security.ps1` | Failed logins, account lockouts, privilege escalations |
| `get_application_crashes.ps1` | Windows Error Reporting — crashed apps with timestamps |
| `get_install_logs.ps1` | MSI/installer temp logs + MsiInstaller Event Viewer entries |

## Windows Health

| Script | Description |
|---|---|
| `get_windows_update_history.ps1` | Last 30 installed updates + any pending/failed updates |
| `get_services_failed.ps1` | Services in stopped/failed state that are set to auto-start |
| `get_startup_programs.ps1` | All startup entries (registry + Task Scheduler) |
| `get_device_manager_errors.ps1` | Hardware devices with error codes (code 10, 43, etc.) |
| `get_drivers_recent.ps1` | Drivers installed or changed in the last 30 days |
| `get_windows_activation.ps1` | License activation status |

## Network

| Script | Description |
|---|---|
| `check_connectivity.ps1` | Gateway ping, DNS resolution, port 80/443 reachability |
| `get_network_config.ps1` | IP, subnet, DNS servers, default gateway, MAC per adapter |
| `get_active_connections.ps1` | Active TCP/UDP connections with process names (netstat) |
| `get_firewall_rules.ps1` | Inbound/outbound block rules that could affect app traffic |
| `get_proxy_settings.ps1` | System and IE proxy config (common cause of app failures) |
| `get_wifi_info.ps1` | SSID, signal strength, auth type, channel (laptops) |

## Software & Security

| Script | Description |
|---|---|
| `get_installed_software.ps1` | Full list of installed programs with version and install date |
| `get_recent_software_changes.ps1` | Software installed/removed in last 7 days |
| `get_antivirus_status.ps1` | Defender real-time protection, last scan time, definition age |
| `get_bitlocker_status.ps1` | BitLocker encryption status per drive |
| `get_group_policy_results.ps1` | Applied GPO results — useful for policy-blocked apps |

## User & Profile

| Script | Description |
|---|---|
| `get_logged_on_users.ps1` | Currently and recently logged on users |
| `get_user_profile_size.ps1` | Profile folder sizes — bloated profiles cause login slowness |
