# AI Log Analysis System — Design Spec
**Date:** 2026-05-21  
**Author:** IT Admin / Sysadmin  
**Status:** Approved

---

## 1. Goal

Build an AI-powered log analysis system that helps IT admins diagnose problematic devices in the organization. Given a device name and problem description, the system autonomously collects diagnostic data by executing NinjaOne scripts on the device, analyzes the results against a knowledge base of past incidents and known fixes, and returns a structured diagnosis with recommended remediation steps.

**The AI never executes fixes. All remediation is performed manually by the IT Admin. Scripts run by the system are diagnostic/read-only only.**

---

## 2. Users

- **Primary:** IT Admin / Sysadmin — triggers analysis, reads report, acts on recommendations, asks follow-up questions
- **Future:** IT Helpdesk staff — simplified view of the same system

---

## 3. Problem Types

Primarily software installation failures and patching failures. Mixed in general — the AI reasons about the problem description and decides which diagnostic scripts to run.

---

## 4. Architecture Overview

### AWS Services Used
| Service | Role |
|---|---|
| API Gateway | REST endpoints for trigger and follow-up |
| Lambda (Orchestrator) | Creates incident, enqueues SQS job |
| Lambda (Worker) | Invokes Bedrock Agent |
| Lambda (Action Group) | Executes NinjaOne scripts — device lookup, script fire, poll, S3 read |
| Lambda (Device Sync) | Syncs NinjaOne device list to DynamoDB cache |
| SQS | Async job buffer — handles scale and Patch Tuesday spikes |
| AWS Bedrock Agent | AI orchestrator — manages tool calls, session state, KB queries |
| Bedrock Knowledge Base | RAG store — past incidents, known fixes, error code library |
| S3 | Script config (scripts.json), log outputs, KB source documents |
| DynamoDB | Incident records, Device cache |
| EventBridge | Scheduled trigger for Device Sync Lambda |
| Lambda (KB Ingestion) | Triggered by S3 event on knowledge-base/ prefix — ingests new documents into Bedrock Knowledge Base |

---

## 5. Components

### 5.1 API Gateway

Two endpoints:

```
POST /analyze
  Body: { device_name: string, problem: string }
  Returns: { incident_id: string, status: "PENDING" }

POST /followup/{incident_id}
  Body: { message: string }
  Returns: { response: string }
```

### 5.2 Orchestrator Lambda

Triggered by `POST /analyze`:
1. Generates `incident_id` — format: `INC-{YYYYMMDD}-{device_name}-{seq}`
2. Writes incident record to DynamoDB with `status: PENDING`
3. Enqueues message to SQS: `{ incident_id, device_name, problem }`
4. Returns `{ incident_id, status: "PENDING" }` immediately — no blocking wait

### 5.3 SQS Queue

- Decouples API response from long-running analysis (Bedrock Agent can take 2-5 minutes with multiple tool calls)
- Absorbs burst submissions during Patch Tuesday or bulk investigations
- Automatic retry on Worker Lambda failure — job is not lost
- Dead Letter Queue (DLQ) for messages that fail after max retries

### 5.4 Worker Lambda

Triggered by SQS message:
1. Sets incident `status: IN_PROGRESS` in DynamoDB
2. Calls `InvokeAgent` on Bedrock Agents:
   ```json
   {
     "agentId": "<bedrock_agent_id>",
     "agentAliasId": "<alias_id>",
     "sessionId": "<incident_id>",
     "inputText": "Device: {device_name}. Problem: {problem}."
   }
   ```
3. Streams response from Agent
4. Stores final analysis report in DynamoDB under the incident record
5. Updates incident `status: COMPLETE` (or `FAILED` with error message in `analysis_report` on exception)

For `POST /followup/{incident_id}`, the request goes directly Lambda → `InvokeAgent` with the same `sessionId`. Bedrock Agents maintains full conversation history natively — no re-analysis needed.

### 5.5 Bedrock Agent

**System Prompt:**
```
You are an expert IT diagnostic AI for a large organization (1000+ devices running Windows).
Your job is to investigate why a device is problematic by running diagnostic scripts and analyzing their output.

Rules:
- Always investigate before concluding. Run scripts to gather evidence.
- Cite specific log entries or script outputs as evidence for your conclusions.
- Never recommend that a script fix something — only human IT admins perform remediation.
- If a script fails, note it and try an alternative approach.
- Cross-reference findings with the knowledge base — cite matching past incidents when relevant.
- Structure your final answer as:
  ROOT CAUSE: <one sentence>
  EVIDENCE: <bullet points from logs/scripts>
  KB MATCH: <similar past incidents if any>
  RECOMMENDED STEPS: <numbered list for human to execute>
```

**Action Group:** `NinjaOneScriptRunner`  
- Single function: `run_ninja_script(script_name, device_name, incident_id)`  
- Backed by the Action Group Lambda (see 5.6)

**Knowledge Base:** Attached directly to the Agent. Auto-queried during reasoning. Backed by S3 documents — past incident resolutions, known error codes, software-specific fix guides.

**Session Management:** Native to Bedrock Agents. `sessionId = incident_id`. Follow-up questions continue the same session with full context.

### 5.6 Action Group Lambda

Executes in three steps every time the Agent calls `run_ninja_script`:

#### Step 1 — Device ID Lookup
1. Query DynamoDB `device-cache` table by `device_name` (partition key)
2. If found → use `ninja_device_id`
3. If not found (new device) → call `GET /v2/devices-details`, find device by name, write to cache, use ID

#### Step 2 — Script Execution
1. Read `scripts.json` from S3 → find entry matching `script_name`
2. Generate pre-signed S3 PUT URL for output path:
   ```
   s3://org-log-analysis/logs/{ninja_device_id}/{incident_id}/{script_name}/output.txt
   ```
3. Build NinjaOne POST body, injecting `output_url` and `incident_id` as parameters:
   ```json
   {
     "type": "ACTION",
     "id": <ninja_script_id>,
     "uid": "<ninja_script_uid>",
     "parameters": "output_url=<presigned_url>&incident_id=<incident_id>",
     "runAs": "SYSTEM"
   }
   ```
4. Call `POST /v2/device/{ninja_device_id}/script/run` → receive `job_id`

#### Step 3 — Poll + Read Output
1. Poll NinjaOne job status using `job_id` — exponential backoff, max 2 minutes (120s default)
2. On `SUCCESS` → read `output.txt` from S3 at the known path
3. On `FAILED` → return error message to Agent: `"Script {script_name} failed on {device_name}: {error}"`
4. Return output content to Bedrock Agent → Agent continues reasoning

**NinjaOne script contract** — every script in `scripts.json` must be authored to accept parameters and upload output to the presigned URL:
```powershell
param([string]$output_url, [string]$incident_id)
# --- run your diagnostics ---
$output = "... diagnostic results ..."
# --- upload output to S3 via presigned URL ---
$bytes = [System.Text.Encoding]::UTF8.GetBytes($output)
Invoke-WebRequest -Uri $output_url -Method PUT -Body $bytes -ContentType "text/plain"
```
Scripts that don't follow this pattern will produce no S3 output, causing the poller to timeout and the Agent to receive a timeout message instead of real data.

### 5.7 Device Cache

| Component | Detail |
|---|---|
| DynamoDB table | `device-cache` — PK: `device_name`, attributes: `ninja_device_id`, `last_synced` |
| Sync Lambda | Calls `GET /v2/devices-details`, upserts all devices to DynamoDB |
| EventBridge rule | Triggers Sync Lambda every 4-6 hours |
| Cache miss fallback | Action Group Lambda calls live API, updates cache entry |

**Why cache and not live lookup every time:** `GET /v2/devices-details` returns the full device list (1000+). Calling it on every script execution during analysis would be slow and wasteful. The cache gives instant lookup (< 10ms) and is kept fresh by the scheduled sync.

### 5.8 S3 Bucket Structure

```
org-log-analysis/
├── config/
│   └── scripts.json                          ← script library config
├── logs/
│   └── {ninja_device_id}/
│       └── {incident_id}/
│           └── {script_name}/
│               └── output.txt                ← script output, written by device
└── knowledge-base/
    ├── incidents/
    │   └── {incident_id}-resolution.md       ← resolved incident summaries (fed to KB)
    ├── error-codes/
    │   └── msi-error-codes.md
    └── fix-guides/
        └── adobe-cc-install.md
```

### 5.9 DynamoDB Tables

**`incidents` table**
```
PK: incident_id (string)
Attributes:
  device_name       string
  problem           string
  status            string  (PENDING | IN_PROGRESS | COMPLETE | FAILED)
  triggered_by      string
  created_at        ISO8601
  completed_at      ISO8601
  analysis_report   string  (full Agent response)
  scripts_run       list    (script names executed during analysis)
```

**`device-cache` table**
```
PK: device_name (string)
Attributes:
  ninja_device_id   string
  last_synced       ISO8601
```

### 5.10 scripts.json Config

Stored at `s3://org-log-analysis/config/scripts.json`. Each entry:

```json
{
  "scripts": [
    {
      "name": "get_install_logs",
      "description": "Collects MSI installer logs and application installation event logs. Use for software installation failures.",
      "ninja_body": {
        "type": "ACTION",
        "id": 1087,
        "uid": "def456uvw",
        "parameters": "",
        "runAs": "SYSTEM"
      }
    },
    {
      "name": "check_connectivity",
      "description": "Tests DNS resolution, gateway ping, and port 443/80 reachability to common endpoints. Use when install or update failures may be network-related.",
      "ninja_body": {
        "type": "ACTION",
        "id": 1042,
        "uid": "abc123xyz",
        "parameters": "",
        "runAs": "SYSTEM"
      }
    },
    {
      "name": "check_firewall_rules",
      "description": "Lists active Windows Firewall rules and recent blocked connections.",
      "ninja_body": {
        "type": "ACTION",
        "id": 1093,
        "uid": "ghi789rst",
        "parameters": "",
        "runAs": "SYSTEM"
      }
    },
    {
      "name": "check_windows_update_logs",
      "description": "Exports Windows Update history and error logs. Use for patching failures.",
      "ninja_body": {
        "type": "ACTION",
        "id": 1101,
        "uid": "jkl012mno",
        "parameters": "",
        "runAs": "SYSTEM"
      }
    },
    {
      "name": "get_running_services",
      "description": "Lists all running and stopped Windows services with their status.",
      "ninja_body": {
        "type": "ACTION",
        "id": 1055,
        "uid": "pqr345stu",
        "parameters": "",
        "runAs": "SYSTEM"
      }
    },
    {
      "name": "check_disk_space",
      "description": "Reports available disk space on all drives. Use when installs fail due to insufficient storage.",
      "ninja_body": {
        "type": "ACTION",
        "id": 1060,
        "uid": "vwx678yza",
        "parameters": "",
        "runAs": "SYSTEM"
      }
    },
    {
      "name": "check_proxy_settings",
      "description": "Reports current proxy configuration including WinHTTP and browser proxy settings.",
      "ninja_body": {
        "type": "ACTION",
        "id": 1075,
        "uid": "bcd901efg",
        "parameters": "",
        "runAs": "SYSTEM"
      }
    }
  ]
}
```

**Adding a new script** = add one JSON entry. No Lambda redeployment. Agent picks it up on next invocation because Action Group Lambda reads the file at runtime.

---

## 6. Data Flow

### Phase 1 — Initiation
1. IT Admin submits `POST /analyze { device_name, problem }`
2. Orchestrator Lambda creates `incident_id`, writes `PENDING` to DynamoDB, enqueues SQS
3. UI receives `{ incident_id }` immediately, begins polling

### Phase 2 — Agent Invocation
4. Worker Lambda picks up SQS message → calls `InvokeAgent` with `sessionId = incident_id`
5. Bedrock Agent starts reasoning, auto-queries Knowledge Base for similar past incidents

### Phase 3 — Tool Use Loop (managed by Bedrock Agents)
The Agent calls `run_ninja_script` as many times as needed:
- A. Agent issues tool call: `run_ninja_script("get_install_logs", "WIN-PC-0042", "INC-001")`
- B. Action Group Lambda: lookup device ID → read scripts.json → generate pre-signed URL → POST to NinjaOne → poll job status → read S3 → return output
- C. Agent receives output, reasons, may call another script
- D. Loop repeats until Agent has sufficient evidence

### Phase 4 — Report Delivery
6. Agent issues final structured response
7. Worker Lambda stores report in DynamoDB, sets `status: COMPLETE`
8. UI displays report to IT Admin

### Phase 5 — Follow-up (optional)
9. IT Admin asks follow-up: `POST /followup/{incident_id} { message }`
10. Lambda calls `InvokeAgent` with same `sessionId` — Agent has full prior context, continues conversation

### Phase 6 — Knowledge Base Growth
11. After resolution, IT Admin uploads fix summary to `s3://org-log-analysis/knowledge-base/incidents/`
12. S3 event triggers KB ingestion → document indexed into Bedrock Knowledge Base vector store
13. Future analyses benefit from this resolved incident

---

## 7. Error Handling

| Scenario | Handling |
|---|---|
| NinjaOne script execution fails | Action Group Lambda returns `"Script {name} failed: {error}"` to Agent. Agent notes it and tries alternative script or concludes with available data. |
| Script job timeout (> 5 min) | Lambda returns timeout error to Agent. Agent reasons without that data. |
| Device not found in NinjaOne | Action Group Lambda returns `"Device {name} not found in NinjaOne"` to Agent. Agent reports back to IT Admin. |
| Bedrock Agent invocation fails | Worker Lambda catches exception, sets incident `status: FAILED` in DynamoDB with error message in `analysis_report`, UI shows error with details. |
| SQS message fails after retries | Message moved to Dead Letter Queue. DynamoDB incident stays `PENDING`. CloudWatch Alarm fires on DLQ depth ≥ 1 → SNS topic alert for manual review. |
| S3 output not written by script | Lambda polls for file, times out, returns error to Agent indicating script produced no output. |

---

## 8. Security

- **IAM roles with least privilege** — each Lambda has its own role scoped to exactly the resources it needs
- **NinjaOne API key** stored in AWS Secrets Manager — never in code or environment variables
- **S3 pre-signed URLs** — time-limited (15 min TTL), scoped to exact output path per incident
- **scripts.json** contains only diagnostic scripts — no remediation scripts ever added to the library
- **Script execution cap** — max 4 tool calls per Agent session (enforced via system prompt instruction); keeps total Worker Lambda runtime well within 900s limit
- **API authentication** — API Gateway API key required; distribute via AWS Console to authorized IT Admin accounts only (Cognito User Pool can replace this for multi-user rollout)
- **DynamoDB encryption at rest** — enabled on both tables
- **S3 bucket** — private, no public access, server-side encryption enabled

---

## 9. Knowledge Base Strategy

**Initial seed documents:**
- Common Windows MSI error codes and meanings
- Windows Update error code reference
- Known software-specific installation guides (Adobe CC, Office, etc.)
- Any past incident resolution summaries already documented

**Ongoing growth:**
- After each resolved incident, IT Admin saves a short resolution summary (what was wrong, what fixed it) to `s3://org-log-analysis/knowledge-base/incidents/`
- S3 event triggers automatic ingestion into Bedrock Knowledge Base
- Over time the KB becomes the org's institutional memory for device issues

---

## 10. Future Considerations

- **Helpdesk access** — simplified UI with same backend, restricted to read-only incident view and basic queries
- **Automated triggering** — NinjaOne alert webhook → API Gateway, removing need for manual submission
- **Notification** — SNS/SES email or Slack notification when analysis completes
- **Dashboard** — DynamoDB → QuickSight for incident trends per device, failure patterns, recurring issues
