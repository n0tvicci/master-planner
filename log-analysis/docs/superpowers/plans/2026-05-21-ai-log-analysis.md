# AI Log Analysis System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an AWS-native AI log analysis system where IT admins submit a device name and problem description, Bedrock Agents autonomously runs NinjaOne diagnostic scripts on the device, analyzes the outputs, cross-references a knowledge base, and returns a structured diagnosis with recommended fix steps — all requiring human action to remediate.

**Architecture:** Bedrock Agents orchestrates the investigation loop via an Action Group Lambda that calls NinjaOne `POST /v2/device/{id}/script/run`, polls job status, and reads script output from S3. A DynamoDB device cache (kept fresh by a scheduled EventBridge sync) maps device names to NinjaOne IDs. All state flows through SQS for async scale, DynamoDB for incident records, and S3 for logs and config.

**Tech Stack:** Python 3.12 · AWS SAM · boto3 · requests · pytest · moto · responses

---

## File Map

```
log-analysis/
├── template.yaml                        # SAM — all AWS resources
├── samconfig.toml                       # SAM deploy config
├── requirements-dev.txt                 # Test dependencies
├── config/
│   └── scripts.json                     # Script library (uploaded to S3 on deploy)
├── layers/
│   └── shared/
│       └── python/
│           ├── db.py                    # DynamoDB get/put/update helpers
│           ├── s3_client.py             # S3 read + presigned PUT URL
│           └── ninja_client.py          # NinjaOne API — get devices, run script, poll job
├── lambdas/
│   ├── orchestrator/
│   │   └── handler.py                   # POST /analyze → incident + SQS
│   ├── worker/
│   │   └── handler.py                   # SQS → InvokeAgent → store result
│   ├── action_group/
│   │   ├── handler.py                   # Bedrock Action Group entry point
│   │   ├── device_lookup.py             # DynamoDB cache lookup + fallback
│   │   ├── script_executor.py           # Read scripts.json + fire NinjaOne POST
│   │   └── job_poller.py                # Poll job status + read S3 output
│   ├── device_sync/
│   │   └── handler.py                   # EventBridge → sync all devices to DynamoDB
│   ├── followup/
│   │   └── handler.py                   # POST /followup/{id} → InvokeAgent same session
│   └── kb_ingestion/
│       └── handler.py                   # S3 event → start KB ingestion job
└── tests/
    ├── conftest.py                       # Fixtures: mocked AWS, NinjaOne env vars
    ├── test_orchestrator.py
    ├── test_worker.py
    ├── test_device_lookup.py
    ├── test_script_executor.py
    ├── test_job_poller.py
    ├── test_action_group_handler.py
    ├── test_device_sync.py
    ├── test_followup.py
    └── test_kb_ingestion.py
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/conftest.py`
- Create: `lambdas/__init__.py`

- [ ] **Step 1: Create `requirements-dev.txt`**

```
boto3>=1.34.0
moto[s3,dynamodb,sqs,secretsmanager]>=4.2.14
pytest>=7.4.0
pytest-mock>=3.12.0
responses>=0.24.1
requests>=2.31.0
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r requirements-dev.txt
```

Expected: all packages install without error.

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import os
import json
import boto3
import pytest
from moto import mock_aws


INCIDENTS_TABLE = "incidents"
DEVICE_CACHE_TABLE = "device-cache"
S3_BUCKET = "org-log-analysis"
NINJA_SECRET_NAME = "ninja-api-key"
NINJA_BASE_URL = "https://test.ninjarmm.com/api"
BEDROCK_AGENT_ID = "TEST_AGENT_ID"
BEDROCK_AGENT_ALIAS_ID = "TEST_ALIAS_ID"
BEDROCK_KB_ID = "TEST_KB_ID"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("INCIDENTS_TABLE", INCIDENTS_TABLE)
    monkeypatch.setenv("DEVICE_CACHE_TABLE", DEVICE_CACHE_TABLE)
    monkeypatch.setenv("S3_BUCKET", S3_BUCKET)
    monkeypatch.setenv("NINJA_SECRET_NAME", NINJA_SECRET_NAME)
    monkeypatch.setenv("NINJA_BASE_URL", NINJA_BASE_URL)
    monkeypatch.setenv("BEDROCK_AGENT_ID", BEDROCK_AGENT_ID)
    monkeypatch.setenv("BEDROCK_AGENT_ALIAS_ID", BEDROCK_AGENT_ALIAS_ID)
    monkeypatch.setenv("BEDROCK_KB_ID", BEDROCK_KB_ID)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture
def aws_clients():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-1")
        s3 = boto3.client("s3", region_name="ap-southeast-1")
        sqs = boto3.client("sqs", region_name="ap-southeast-1")
        secretsmanager = boto3.client("secretsmanager", region_name="ap-southeast-1")

        # incidents table
        incidents_table = dynamodb.create_table(
            TableName=INCIDENTS_TABLE,
            KeySchema=[{"AttributeName": "incident_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "incident_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # device-cache table
        device_cache_table = dynamodb.create_table(
            TableName=DEVICE_CACHE_TABLE,
            KeySchema=[{"AttributeName": "device_name", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "device_name", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # S3 bucket
        s3.create_bucket(
            Bucket=S3_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"},
        )

        # SQS queue
        queue = sqs.create_queue(QueueName="analysis-queue")

        # Secrets Manager secret
        secretsmanager.create_secret(
            Name=NINJA_SECRET_NAME,
            SecretString=json.dumps({"api_key": "test-ninja-api-key"}),
        )

        yield {
            "dynamodb": dynamodb,
            "s3": s3,
            "sqs": sqs,
            "incidents_table": incidents_table,
            "device_cache_table": device_cache_table,
            "queue_url": queue["QueueUrl"],
        }


SAMPLE_SCRIPTS_JSON = {
    "scripts": [
        {
            "name": "get_install_logs",
            "description": "Collects MSI installer logs. Use for installation failures.",
            "ninja_body": {
                "type": "ACTION",
                "id": 1087,
                "uid": "def456uvw",
                "parameters": "",
                "runAs": "SYSTEM",
            },
        },
        {
            "name": "check_connectivity",
            "description": "Tests DNS and port reachability. Use for network-related failures.",
            "ninja_body": {
                "type": "ACTION",
                "id": 1042,
                "uid": "abc123xyz",
                "parameters": "",
                "runAs": "SYSTEM",
            },
        },
    ]
}
```

- [ ] **Step 4: Create `lambdas/__init__.py`** (empty — required so `import lambdas.xyz.handler` works in tests)

- [ ] **Step 5: Verify conftest loads without error**

```bash
pytest tests/ --collect-only
```

Expected: `no tests ran` (no test files yet) — no import errors.

- [ ] **Step 6: Commit**

```bash
git init
git add requirements-dev.txt tests/conftest.py lambdas/__init__.py
git commit -m "feat: project scaffolding and test fixtures"
```

---

## Task 2: Shared Layer — `ninja_client.py`

**Files:**
- Create: `layers/shared/python/ninja_client.py`
- Create: `tests/test_ninja_client.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_ninja_client.py`:

```python
import json
import pytest
import responses as resp_mock
from tests.conftest import NINJA_BASE_URL


@pytest.fixture
def ninja(aws_clients):
    import sys
    sys.path.insert(0, "layers/shared/python")
    from ninja_client import NinjaClient
    return NinjaClient()


@resp_mock.activate
def test_get_devices_returns_list(ninja):
    resp_mock.add(
        resp_mock.GET,
        f"{NINJA_BASE_URL}/v2/devices-details",
        json=[
            {"id": "42", "systemName": "WIN-PC-0042"},
            {"id": "99", "systemName": "WIN-PC-0099"},
        ],
        status=200,
    )
    devices = ninja.get_devices()
    assert len(devices) == 2
    assert devices[0]["systemName"] == "WIN-PC-0042"


@resp_mock.activate
def test_run_script_returns_job_id(ninja):
    resp_mock.add(
        resp_mock.POST,
        f"{NINJA_BASE_URL}/v2/device/42/script/run",
        json={"id": 9001},
        status=200,
    )
    body = {"type": "ACTION", "id": 1087, "uid": "def456uvw", "parameters": "", "runAs": "SYSTEM"}
    job_id = ninja.run_script(device_id="42", body=body)
    assert job_id == 9001


@resp_mock.activate
def test_get_job_status_returns_status(ninja):
    resp_mock.add(
        resp_mock.GET,
        f"{NINJA_BASE_URL}/v2/activities",
        json={"activities": [{"id": 9001, "status": "SUCCESS", "message": ""}]},
        status=200,
    )
    status, message = ninja.get_job_status(job_id=9001)
    assert status == "SUCCESS"
    assert message == ""


@resp_mock.activate
def test_get_job_status_returns_failed(ninja):
    resp_mock.add(
        resp_mock.GET,
        f"{NINJA_BASE_URL}/v2/activities",
        json={"activities": [{"id": 9001, "status": "FAILED", "message": "Script error"}]},
        status=200,
    )
    status, message = ninja.get_job_status(job_id=9001)
    assert status == "FAILED"
    assert message == "Script error"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ninja_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'ninja_client'`

- [ ] **Step 3: Implement `layers/shared/python/ninja_client.py`**

```python
import json
import os
import boto3
import requests


class NinjaClient:
    def __init__(self):
        self.base_url = os.environ["NINJA_BASE_URL"].rstrip("/")
        self._api_key = None

    def _get_api_key(self):
        if self._api_key:
            return self._api_key
        client = boto3.client("secretsmanager")
        secret = client.get_secret_value(SecretId=os.environ["NINJA_SECRET_NAME"])
        self._api_key = json.loads(secret["SecretString"])["api_key"]
        return self._api_key

    def _headers(self):
        return {"Authorization": f"Bearer {self._get_api_key()}", "Content-Type": "application/json"}

    def get_devices(self):
        response = requests.get(f"{self.base_url}/v2/devices-details", headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def run_script(self, device_id: str, body: dict) -> int:
        response = requests.post(
            f"{self.base_url}/v2/device/{device_id}/script/run",
            headers=self._headers(),
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["id"]

    def get_job_status(self, job_id: int) -> tuple:
        response = requests.get(
            f"{self.base_url}/v2/activities",
            headers=self._headers(),
            params={"id": job_id},
            timeout=30,
        )
        response.raise_for_status()
        activities = response.json().get("activities", [])
        for activity in activities:
            if activity["id"] == job_id:
                return activity["status"], activity.get("message", "")
        return "PENDING", ""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ninja_client.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add layers/shared/python/ninja_client.py tests/test_ninja_client.py
git commit -m "feat: NinjaOne API client with device list, script run, job status"
```

---

## Task 3: Shared Layer — `db.py` and `s3_client.py`

**Files:**
- Create: `layers/shared/python/db.py`
- Create: `layers/shared/python/s3_client.py`
- Create: `tests/test_shared.py`

> **Note:** `db.py` includes `append_script_run` for tracking which scripts the Agent ran per incident (required by spec §5.9).

- [ ] **Step 1: Write failing tests**

Create `tests/test_shared.py`:

```python
import json
import sys
import pytest
sys.path.insert(0, "layers/shared/python")


def test_db_put_and_get_incident(aws_clients):
    from db import put_incident, get_incident
    put_incident({
        "incident_id": "INC-001",
        "device_name": "WIN-PC-0042",
        "problem": "install failed",
        "status": "PENDING",
    })
    item = get_incident("INC-001")
    assert item["device_name"] == "WIN-PC-0042"
    assert item["status"] == "PENDING"


def test_db_update_incident_status(aws_clients):
    from db import put_incident, update_incident_status
    put_incident({"incident_id": "INC-002", "status": "PENDING", "device_name": "X", "problem": "Y"})
    update_incident_status("INC-002", "COMPLETE", analysis_report="Root cause: firewall")
    from db import get_incident
    item = get_incident("INC-002")
    assert item["status"] == "COMPLETE"
    assert item["analysis_report"] == "Root cause: firewall"


def test_db_get_device_id_hit(aws_clients):
    from db import cache_device, get_device_id
    cache_device("WIN-PC-0042", "42")
    assert get_device_id("WIN-PC-0042") == "42"


def test_db_get_device_id_miss(aws_clients):
    from db import get_device_id
    assert get_device_id("UNKNOWN-DEVICE") is None


def test_db_append_script_run(aws_clients):
    from db import put_incident, append_script_run, get_incident
    put_incident({"incident_id": "INC-003", "status": "IN_PROGRESS", "device_name": "X", "problem": "Y"})
    append_script_run("INC-003", "get_install_logs")
    append_script_run("INC-003", "check_connectivity")
    item = get_incident("INC-003")
    assert item["scripts_run"] == ["get_install_logs", "check_connectivity"]


def test_s3_read_scripts_json(aws_clients):
    from s3_client import read_scripts_config
    from tests.conftest import SAMPLE_SCRIPTS_JSON, S3_BUCKET
    aws_clients["s3"].put_object(
        Bucket=S3_BUCKET,
        Key="config/scripts.json",
        Body=json.dumps(SAMPLE_SCRIPTS_JSON),
    )
    config = read_scripts_config()
    assert len(config["scripts"]) == 2
    assert config["scripts"][0]["name"] == "get_install_logs"


def test_s3_generate_presigned_url(aws_clients):
    from s3_client import generate_output_presigned_url
    url = generate_output_presigned_url(device_id="42", incident_id="INC-001", script_name="get_install_logs")
    assert "org-log-analysis" in url
    assert "logs/42/INC-001/get_install_logs/output.txt" in url


def test_s3_read_script_output(aws_clients):
    from s3_client import read_script_output
    from tests.conftest import S3_BUCKET
    aws_clients["s3"].put_object(
        Bucket=S3_BUCKET,
        Key="logs/42/INC-001/get_install_logs/output.txt",
        Body="MSI error 1603 at 14:32",
    )
    output = read_script_output(device_id="42", incident_id="INC-001", script_name="get_install_logs")
    assert output == "MSI error 1603 at 14:32"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_shared.py -v
```

Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Implement `layers/shared/python/db.py`**

```python
import os
from datetime import datetime, timezone
import boto3


def _incidents_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.environ["INCIDENTS_TABLE"])


def _device_cache_table():
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(os.environ["DEVICE_CACHE_TABLE"])


def put_incident(item: dict):
    _incidents_table().put_item(Item=item)


def get_incident(incident_id: str) -> dict:
    response = _incidents_table().get_item(Key={"incident_id": incident_id})
    return response.get("Item")


def update_incident_status(incident_id: str, status: str, analysis_report: str = None):
    expr = "SET #s = :s, completed_at = :t"
    names = {"#s": "status"}
    values = {":s": status, ":t": datetime.now(timezone.utc).isoformat()}
    if analysis_report is not None:
        expr += ", analysis_report = :r"
        values[":r"] = analysis_report
    _incidents_table().update_item(
        Key={"incident_id": incident_id},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def cache_device(device_name: str, ninja_device_id: str):
    _device_cache_table().put_item(Item={
        "device_name": device_name,
        "ninja_device_id": ninja_device_id,
        "last_synced": datetime.now(timezone.utc).isoformat(),
    })


def get_device_id(device_name: str):
    response = _device_cache_table().get_item(Key={"device_name": device_name})
    item = response.get("Item")
    return item["ninja_device_id"] if item else None


def append_script_run(incident_id: str, script_name: str):
    _incidents_table().update_item(
        Key={"incident_id": incident_id},
        UpdateExpression="SET scripts_run = list_append(if_not_exists(scripts_run, :empty), :s)",
        ExpressionAttributeValues={":s": [script_name], ":empty": []},
    )
```

- [ ] **Step 4: Implement `layers/shared/python/s3_client.py`**

```python
import json
import os
import boto3
import botocore.exceptions


def _s3():
    return boto3.client("s3")


def _bucket():
    return os.environ["S3_BUCKET"]


def _output_key(device_id: str, incident_id: str, script_name: str) -> str:
    return f"logs/{device_id}/{incident_id}/{script_name}/output.txt"


def read_scripts_config() -> dict:
    response = _s3().get_object(Bucket=_bucket(), Key="config/scripts.json")
    return json.loads(response["Body"].read().decode("utf-8"))


def generate_output_presigned_url(device_id: str, incident_id: str, script_name: str) -> str:
    key = _output_key(device_id, incident_id, script_name)
    return _s3().generate_presigned_url(
        "put_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=900,
    )


def read_script_output(device_id: str, incident_id: str, script_name: str) -> str:
    key = _output_key(device_id, incident_id, script_name)
    response = _s3().get_object(Bucket=_bucket(), Key=key)
    return response["Body"].read().decode("utf-8")


def object_exists(device_id: str, incident_id: str, script_name: str) -> bool:
    key = _output_key(device_id, incident_id, script_name)
    try:
        _s3().head_object(Bucket=_bucket(), Key=key)
        return True
    except botocore.exceptions.ClientError:
        return False
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_shared.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add layers/shared/python/db.py layers/shared/python/s3_client.py tests/test_shared.py
git commit -m "feat: shared layer — DynamoDB helpers, S3 client, script run tracking"
```

---

## Task 4: Device Sync Lambda

**Files:**
- Create: `lambdas/device_sync/handler.py`
- Create: `tests/test_device_sync.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_device_sync.py`:

```python
import sys
import json
import pytest
import responses as resp_mock
sys.path.insert(0, "layers/shared/python")

from tests.conftest import NINJA_BASE_URL


def _handler():
    import importlib, lambdas.device_sync.handler as m
    importlib.reload(m)
    return m


@resp_mock.activate
def test_sync_upserts_all_devices(aws_clients):
    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/devices-details",
        json=[
            {"id": "42", "systemName": "WIN-PC-0042"},
            {"id": "99", "systemName": "WIN-PC-0099"},
        ],
        status=200,
    )
    mod = _handler()
    mod.lambda_handler({}, {})

    from db import get_device_id
    assert get_device_id("WIN-PC-0042") == "42"
    assert get_device_id("WIN-PC-0099") == "99"


@resp_mock.activate
def test_sync_overwrites_stale_entry(aws_clients):
    from db import cache_device, get_device_id
    cache_device("WIN-PC-0042", "OLD-ID")

    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/devices-details",
        json=[{"id": "42", "systemName": "WIN-PC-0042"}],
        status=200,
    )
    _handler().lambda_handler({}, {})
    assert get_device_id("WIN-PC-0042") == "42"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_device_sync.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `lambdas/device_sync/__init__.py`** (empty file)

- [ ] **Step 4: Implement `lambdas/device_sync/handler.py`**

```python
import sys
sys.path.insert(0, "/opt/python")

from ninja_client import NinjaClient
from db import cache_device


def lambda_handler(event, context):
    client = NinjaClient()
    devices = client.get_devices()
    synced = 0
    for device in devices:
        device_id = str(device.get("id", ""))
        name = device.get("systemName", "")
        if device_id and name:
            cache_device(name, device_id)
            synced += 1
    print(f"Device sync complete: {synced} devices upserted")
    return {"synced": synced}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_device_sync.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lambdas/device_sync/ tests/test_device_sync.py
git commit -m "feat: device sync lambda — EventBridge triggered NinjaOne→DynamoDB cache"
```

---

## Task 5: Action Group Lambda — `device_lookup.py`

**Files:**
- Create: `lambdas/action_group/device_lookup.py`
- Create: `tests/test_device_lookup.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_device_lookup.py`:

```python
import sys
import pytest
import responses as resp_mock
sys.path.insert(0, "layers/shared/python")
sys.path.insert(0, "lambdas/action_group")

from tests.conftest import NINJA_BASE_URL
from device_lookup import DeviceNotFoundError, resolve_device_id


@resp_mock.activate
def test_lookup_returns_id_from_cache(aws_clients):
    from db import cache_device
    cache_device("WIN-PC-0042", "42")
    assert resolve_device_id("WIN-PC-0042") == "42"


@resp_mock.activate
def test_lookup_falls_back_to_api_on_cache_miss(aws_clients):
    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/devices-details",
        json=[{"id": "99", "systemName": "WIN-PC-0099"}],
        status=200,
    )
    result = resolve_device_id("WIN-PC-0099")
    assert result == "99"


@resp_mock.activate
def test_lookup_caches_after_fallback(aws_clients):
    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/devices-details",
        json=[{"id": "77", "systemName": "WIN-PC-0077"}],
        status=200,
    )
    from db import get_device_id
    resolve_device_id("WIN-PC-0077")
    assert get_device_id("WIN-PC-0077") == "77"


@resp_mock.activate
def test_lookup_raises_when_device_not_found(aws_clients):
    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/devices-details",
        json=[{"id": "1", "systemName": "OTHER-PC"}],
        status=200,
    )
    with pytest.raises(DeviceNotFoundError):
        resolve_device_id("GHOST-PC")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_device_lookup.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Create `lambdas/action_group/__init__.py`** (empty)

- [ ] **Step 4: Implement `lambdas/action_group/device_lookup.py`**

```python
import sys
sys.path.insert(0, "/opt/python")

from db import get_device_id, cache_device
from ninja_client import NinjaClient


class DeviceNotFoundError(Exception):
    pass


def resolve_device_id(device_name: str) -> str:
    cached = get_device_id(device_name)
    if cached:
        return cached

    client = NinjaClient()
    devices = client.get_devices()
    for device in devices:
        name = device.get("systemName", "")
        device_id = str(device.get("id", ""))
        if name and device_id:
            cache_device(name, device_id)
        if name == device_name:
            return device_id

    raise DeviceNotFoundError(f"Device '{device_name}' not found in NinjaOne")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_device_lookup.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lambdas/action_group/device_lookup.py tests/test_device_lookup.py
git commit -m "feat: device lookup with DynamoDB cache and NinjaOne fallback"
```

---

## Task 6: Action Group Lambda — `script_executor.py`

**Files:**
- Create: `lambdas/action_group/script_executor.py`
- Create: `tests/test_script_executor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_script_executor.py`:

```python
import sys
import json
import pytest
import responses as resp_mock
sys.path.insert(0, "layers/shared/python")
sys.path.insert(0, "lambdas/action_group")

from tests.conftest import NINJA_BASE_URL, SAMPLE_SCRIPTS_JSON, S3_BUCKET


def _put_scripts_config(aws_clients):
    aws_clients["s3"].put_object(
        Bucket=S3_BUCKET,
        Key="config/scripts.json",
        Body=json.dumps(SAMPLE_SCRIPTS_JSON),
    )


@resp_mock.activate
def test_execute_script_returns_job_id(aws_clients):
    _put_scripts_config(aws_clients)
    resp_mock.add(
        resp_mock.POST,
        f"{NINJA_BASE_URL}/v2/device/42/script/run",
        json={"id": 9001},
        status=200,
    )
    from script_executor import execute_script
    job_id = execute_script(
        script_name="get_install_logs",
        device_id="42",
        incident_id="INC-001",
    )
    assert job_id == 9001


@resp_mock.activate
def test_execute_script_injects_output_url_in_params(aws_clients):
    _put_scripts_config(aws_clients)
    captured = []

    def callback(request):
        captured.append(json.loads(request.body))
        return (200, {}, json.dumps({"id": 9001}))

    resp_mock.add_callback(
        resp_mock.POST,
        f"{NINJA_BASE_URL}/v2/device/42/script/run",
        callback=callback,
        content_type="application/json",
    )
    from script_executor import execute_script
    execute_script("get_install_logs", "42", "INC-001")

    body = captured[0]
    assert body["type"] == "ACTION"
    assert body["id"] == 1087
    assert "output_url=" in body["parameters"]
    assert "incident_id=INC-001" in body["parameters"]


def test_execute_script_raises_on_unknown_script(aws_clients):
    _put_scripts_config(aws_clients)
    from script_executor import ScriptNotFoundError, execute_script
    with pytest.raises(ScriptNotFoundError):
        execute_script("nonexistent_script", "42", "INC-001")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_script_executor.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `lambdas/action_group/script_executor.py`**

```python
import sys
sys.path.insert(0, "/opt/python")

from s3_client import read_scripts_config, generate_output_presigned_url
from ninja_client import NinjaClient


class ScriptNotFoundError(Exception):
    pass


def _find_script(scripts_config: dict, script_name: str) -> dict:
    for script in scripts_config.get("scripts", []):
        if script["name"] == script_name:
            return script
    raise ScriptNotFoundError(f"Script '{script_name}' not found in scripts.json")


def execute_script(script_name: str, device_id: str, incident_id: str) -> int:
    config = read_scripts_config()
    script = _find_script(config, script_name)

    output_url = generate_output_presigned_url(
        device_id=device_id,
        incident_id=incident_id,
        script_name=script_name,
    )

    body = dict(script["ninja_body"])
    body["parameters"] = f"output_url={output_url}&incident_id={incident_id}"

    client = NinjaClient()
    return client.run_script(device_id=device_id, body=body)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_script_executor.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lambdas/action_group/script_executor.py tests/test_script_executor.py
git commit -m "feat: script executor — reads scripts.json, injects presigned URL, fires NinjaOne"
```

---

## Task 7: Action Group Lambda — `job_poller.py`

**Files:**
- Create: `lambdas/action_group/job_poller.py`
- Create: `tests/test_job_poller.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_job_poller.py`:

```python
import sys
import pytest
import responses as resp_mock
sys.path.insert(0, "layers/shared/python")
sys.path.insert(0, "lambdas/action_group")

from tests.conftest import NINJA_BASE_URL, S3_BUCKET


@resp_mock.activate
def test_poll_returns_output_on_success(aws_clients):
    aws_clients["s3"].put_object(
        Bucket=S3_BUCKET,
        Key="logs/42/INC-001/get_install_logs/output.txt",
        Body="MSI error 1603 — locked file handle",
    )
    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/activities",
        json={"activities": [{"id": 9001, "status": "SUCCESS", "message": ""}]},
        status=200,
    )
    from job_poller import poll_and_read
    output = poll_and_read(
        job_id=9001,
        device_id="42",
        incident_id="INC-001",
        script_name="get_install_logs",
        max_wait_seconds=5,
        poll_interval_seconds=0.1,
    )
    assert "MSI error 1603" in output


@resp_mock.activate
def test_poll_returns_error_message_on_failure(aws_clients):
    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/activities",
        json={"activities": [{"id": 9001, "status": "FAILED", "message": "Permission denied"}]},
        status=200,
    )
    from job_poller import poll_and_read
    output = poll_and_read(
        job_id=9001,
        device_id="42",
        incident_id="INC-001",
        script_name="get_install_logs",
        max_wait_seconds=5,
        poll_interval_seconds=0.1,
    )
    assert "FAILED" in output
    assert "Permission denied" in output


@resp_mock.activate
def test_poll_times_out_gracefully(aws_clients):
    resp_mock.add(
        resp_mock.GET, f"{NINJA_BASE_URL}/v2/activities",
        json={"activities": [{"id": 9001, "status": "PENDING", "message": ""}]},
        status=200,
    )
    from job_poller import poll_and_read
    output = poll_and_read(
        job_id=9001,
        device_id="42",
        incident_id="INC-001",
        script_name="get_install_logs",
        max_wait_seconds=0.3,
        poll_interval_seconds=0.1,
    )
    assert "timed out" in output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_job_poller.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `lambdas/action_group/job_poller.py`**

```python
import sys
import time
sys.path.insert(0, "/opt/python")

from ninja_client import NinjaClient
from s3_client import read_script_output


def poll_and_read(
    job_id: int,
    device_id: str,
    incident_id: str,
    script_name: str,
    max_wait_seconds: int = 120,
    poll_interval_seconds: int = 10,
) -> str:
    client = NinjaClient()
    elapsed = 0
    interval = poll_interval_seconds

    while elapsed < max_wait_seconds:
        status, message = client.get_job_status(job_id=job_id)

        if status == "SUCCESS":
            return read_script_output(
                device_id=device_id,
                incident_id=incident_id,
                script_name=script_name,
            )

        if status == "FAILED":
            return f"Script execution FAILED: {message}"

        time.sleep(interval)
        elapsed += interval
        interval = min(interval * 2, 30)

    return f"Script execution timed out after {max_wait_seconds}s — no output available"
```

No changes needed to `ninja_client.py` — `get_job_status` already returns `(status, message)` as a tuple from Task 2, so `job_poller` has everything it needs in a single API call.

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_job_poller.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lambdas/action_group/job_poller.py layers/shared/python/ninja_client.py tests/test_job_poller.py
git commit -m "feat: job poller — poll NinjaOne status with exponential backoff, read S3 output (max 120s default)"
```

---

## Task 8: Action Group Lambda — `handler.py`

**Files:**
- Create: `lambdas/action_group/handler.py`
- Create: `tests/test_action_group_handler.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_action_group_handler.py`:

```python
import sys
import json
import pytest
import responses as resp_mock
sys.path.insert(0, "layers/shared/python")
sys.path.insert(0, "lambdas/action_group")

from tests.conftest import NINJA_BASE_URL, SAMPLE_SCRIPTS_JSON, S3_BUCKET


def _seed(aws_clients):
    aws_clients["s3"].put_object(
        Bucket=S3_BUCKET, Key="config/scripts.json",
        Body=json.dumps(SAMPLE_SCRIPTS_JSON),
    )
    from db import cache_device
    cache_device("WIN-PC-0042", "42")


def _event(script_name="get_install_logs"):
    return {
        "actionGroup": "NinjaOneScriptRunner",
        "function": "run_ninja_script",
        "parameters": [
            {"name": "script_name", "type": "string", "value": script_name},
            {"name": "device_name", "type": "string", "value": "WIN-PC-0042"},
            {"name": "incident_id", "type": "string", "value": "INC-001"},
        ],
    }


@resp_mock.activate
def test_handler_returns_script_output(aws_clients):
    _seed(aws_clients)
    aws_clients["s3"].put_object(
        Bucket=S3_BUCKET,
        Key="logs/42/INC-001/get_install_logs/output.txt",
        Body="MSI error 1603",
    )
    resp_mock.add(resp_mock.POST, f"{NINJA_BASE_URL}/v2/device/42/script/run",
                  json={"id": 9001}, status=200)
    resp_mock.add(resp_mock.GET, f"{NINJA_BASE_URL}/v2/activities",
                  json={"activities": [{"id": 9001, "status": "SUCCESS", "message": ""}]},
                  status=200)

    from handler import lambda_handler
    result = lambda_handler(_event(), {})
    body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    assert "MSI error 1603" in body


@resp_mock.activate
def test_handler_returns_error_for_unknown_device(aws_clients):
    _seed(aws_clients)
    resp_mock.add(resp_mock.GET, f"{NINJA_BASE_URL}/v2/devices-details",
                  json=[], status=200)

    event = {
        "actionGroup": "NinjaOneScriptRunner",
        "function": "run_ninja_script",
        "parameters": [
            {"name": "script_name", "type": "string", "value": "get_install_logs"},
            {"name": "device_name", "type": "string", "value": "GHOST-PC"},
            {"name": "incident_id", "type": "string", "value": "INC-001"},
        ],
    }
    from handler import lambda_handler
    result = lambda_handler(event, {})
    body = result["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
    assert "not found" in body.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_action_group_handler.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `lambdas/action_group/handler.py`**

```python
import sys
sys.path.insert(0, "/opt/python")

from db import append_script_run
from device_lookup import DeviceNotFoundError, resolve_device_id
from script_executor import ScriptNotFoundError, execute_script
from job_poller import poll_and_read


def _build_response(action_group: str, function: str, body: str) -> dict:
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": action_group,
            "function": function,
            "functionResponse": {
                "responseBody": {"TEXT": {"body": body}}
            },
        },
    }


def lambda_handler(event, context):
    action_group = event["actionGroup"]
    function = event["function"]
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    script_name = params["script_name"]
    device_name = params["device_name"]
    incident_id = params["incident_id"]

    try:
        device_id = resolve_device_id(device_name)
    except DeviceNotFoundError as e:
        return _build_response(action_group, function, str(e))

    try:
        job_id = execute_script(
            script_name=script_name,
            device_id=device_id,
            incident_id=incident_id,
        )
    except ScriptNotFoundError as e:
        return _build_response(action_group, function, str(e))

    append_script_run(incident_id, script_name)

    output = poll_and_read(
        job_id=job_id,
        device_id=device_id,
        incident_id=incident_id,
        script_name=script_name,
    )

    return _build_response(action_group, function, output)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_action_group_handler.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lambdas/action_group/handler.py tests/test_action_group_handler.py
git commit -m "feat: action group handler — wires device lookup, script execution, job polling"
```

---

## Task 9: Orchestrator Lambda

**Files:**
- Create: `lambdas/orchestrator/__init__.py`
- Create: `lambdas/orchestrator/handler.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_orchestrator.py`:

```python
import sys
import json
import pytest
sys.path.insert(0, "layers/shared/python")


def _event(device="WIN-PC-0042", problem="Adobe CC fails with error 1603"):
    return {
        "body": json.dumps({"device_name": device, "problem": problem}),
        "requestContext": {"identity": {"cognitoIdentityId": "user-123"}},
    }


def test_orchestrator_creates_incident_and_returns_id(aws_clients, monkeypatch):
    monkeypatch.setenv("SQS_QUEUE_URL", aws_clients["queue_url"])

    import importlib
    import lambdas.orchestrator.handler as m
    importlib.reload(m)

    result = m.lambda_handler(_event(), {})
    body = json.loads(result["body"])

    assert result["statusCode"] == 202
    assert "incident_id" in body
    assert body["status"] == "PENDING"
    assert body["incident_id"].startswith("INC-")


def test_orchestrator_writes_to_dynamodb(aws_clients, monkeypatch):
    monkeypatch.setenv("SQS_QUEUE_URL", aws_clients["queue_url"])

    import importlib
    import lambdas.orchestrator.handler as m
    importlib.reload(m)

    result = m.lambda_handler(_event(), {})
    incident_id = json.loads(result["body"])["incident_id"]

    from db import get_incident
    item = get_incident(incident_id)
    assert item["device_name"] == "WIN-PC-0042"
    assert item["status"] == "PENDING"
    assert item["problem"] == "Adobe CC fails with error 1603"


def test_orchestrator_enqueues_sqs_message(aws_clients, monkeypatch):
    monkeypatch.setenv("SQS_QUEUE_URL", aws_clients["queue_url"])
    import boto3

    import importlib
    import lambdas.orchestrator.handler as m
    importlib.reload(m)

    m.lambda_handler(_event(), {})

    sqs = boto3.client("sqs", region_name="ap-southeast-1")
    msgs = sqs.receive_message(QueueUrl=aws_clients["queue_url"], MaxNumberOfMessages=1)
    body = json.loads(msgs["Messages"][0]["Body"])
    assert body["device_name"] == "WIN-PC-0042"
    assert "incident_id" in body
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `lambdas/orchestrator/handler.py`**

```python
import sys
import os
import json
import uuid
from datetime import datetime, timezone
sys.path.insert(0, "/opt/python")

import boto3
from db import put_incident


def _generate_incident_id(device_name: str) -> str:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    short = uuid.uuid4().hex[:6].upper()
    safe_device = device_name.replace(" ", "-").upper()
    return f"INC-{date}-{safe_device}-{short}"


def lambda_handler(event, context):
    body = json.loads(event.get("body", "{}"))
    device_name = body["device_name"]
    problem = body["problem"]
    triggered_by = (event.get("requestContext", {})
                    .get("identity", {})
                    .get("cognitoIdentityId", "unknown"))

    incident_id = _generate_incident_id(device_name)
    now = datetime.now(timezone.utc).isoformat()

    put_incident({
        "incident_id": incident_id,
        "device_name": device_name,
        "problem": problem,
        "status": "PENDING",
        "triggered_by": triggered_by,
        "created_at": now,
    })

    sqs = boto3.client("sqs")
    sqs.send_message(
        QueueUrl=os.environ["SQS_QUEUE_URL"],
        MessageBody=json.dumps({
            "incident_id": incident_id,
            "device_name": device_name,
            "problem": problem,
        }),
    )

    return {
        "statusCode": 202,
        "body": json.dumps({"incident_id": incident_id, "status": "PENDING"}),
        "headers": {"Content-Type": "application/json"},
    }
```

- [ ] **Step 4: Create `lambdas/orchestrator/__init__.py`** (empty)

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_orchestrator.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lambdas/orchestrator/ tests/test_orchestrator.py
git commit -m "feat: orchestrator lambda — creates incident, enqueues SQS job"
```

---

## Task 10: Worker Lambda

**Files:**
- Create: `lambdas/worker/__init__.py`
- Create: `lambdas/worker/handler.py`
- Create: `tests/test_worker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_worker.py`:

```python
import sys
import json
import pytest
sys.path.insert(0, "layers/shared/python")

from tests.conftest import BEDROCK_AGENT_ID, BEDROCK_AGENT_ALIAS_ID


def _sqs_event(incident_id="INC-001", device="WIN-PC-0042", problem="install fails"):
    return {
        "Records": [{
            "body": json.dumps({
                "incident_id": incident_id,
                "device_name": device,
                "problem": problem,
            })
        }]
    }


def test_worker_stores_report_on_success(aws_clients, mocker):
    from db import put_incident
    put_incident({
        "incident_id": "INC-001", "device_name": "WIN-PC-0042",
        "problem": "install fails", "status": "PENDING",
    })

    mock_invoke = mocker.patch("boto3.client")
    mock_client = mock_invoke.return_value
    mock_client.invoke_agent.return_value = {
        "completion": [{"chunk": {"bytes": b"ROOT CAUSE: firewall blocking port 443"}}]
    }

    import importlib
    import lambdas.worker.handler as m
    importlib.reload(m)

    m.lambda_handler(_sqs_event(), {})

    from db import get_incident
    item = get_incident("INC-001")
    assert item["status"] == "COMPLETE"
    assert "ROOT CAUSE" in item["analysis_report"]


def test_worker_sets_in_progress_before_invoke(aws_clients, mocker):
    from db import put_incident
    put_incident({
        "incident_id": "INC-003", "device_name": "WIN-PC-0042",
        "problem": "install fails", "status": "PENDING",
    })

    statuses = []

    def side_effect(*args, **kwargs):
        from db import get_incident
        statuses.append(get_incident("INC-003")["status"])
        return {"completion": [{"chunk": {"bytes": b"report"}}]}

    mock_invoke = mocker.patch("boto3.client")
    mock_client = mock_invoke.return_value
    mock_client.invoke_agent.side_effect = side_effect

    import importlib
    import lambdas.worker.handler as m
    importlib.reload(m)

    m.lambda_handler(_sqs_event(incident_id="INC-003"), {})
    assert statuses[0] == "IN_PROGRESS"


def test_worker_sets_failed_status_on_exception(aws_clients, mocker):
    from db import put_incident
    put_incident({
        "incident_id": "INC-002", "device_name": "WIN-PC-0042",
        "problem": "install fails", "status": "PENDING",
    })

    mock_invoke = mocker.patch("boto3.client")
    mock_client = mock_invoke.return_value
    mock_client.invoke_agent.side_effect = Exception("Bedrock unavailable")

    import importlib
    import lambdas.worker.handler as m
    importlib.reload(m)

    m.lambda_handler(_sqs_event(incident_id="INC-002"), {})

    from db import get_incident
    item = get_incident("INC-002")
    assert item["status"] == "FAILED"
    assert "Bedrock unavailable" in item["analysis_report"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_worker.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `lambdas/worker/handler.py`**

```python
import sys
import os
import json
sys.path.insert(0, "/opt/python")

import boto3
from db import get_incident, update_incident_status


def _invoke_agent(incident_id: str, device_name: str, problem: str) -> str:
    client = boto3.client("bedrock-agent-runtime")
    response = client.invoke_agent(
        agentId=os.environ["BEDROCK_AGENT_ID"],
        agentAliasId=os.environ["BEDROCK_AGENT_ALIAS_ID"],
        sessionId=incident_id,
        inputText=f"Device: {device_name}. Problem: {problem}.",
    )
    completion = ""
    for event in response.get("completion", []):
        if "chunk" in event:
            completion += event["chunk"]["bytes"].decode("utf-8")
    return completion


def lambda_handler(event, context):
    for record in event["Records"]:
        payload = json.loads(record["body"])
        incident_id = payload["incident_id"]
        device_name = payload["device_name"]
        problem = payload["problem"]

        try:
            update_incident_status(incident_id, "IN_PROGRESS")
            report = _invoke_agent(incident_id, device_name, problem)
            update_incident_status(incident_id, "COMPLETE", analysis_report=report)
        except Exception as exc:
            print(f"Agent invocation failed for {incident_id}: {exc}")
            update_incident_status(incident_id, "FAILED", analysis_report=f"Analysis failed: {exc}")
```

- [ ] **Step 4: Create `lambdas/worker/__init__.py`** (empty)

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_worker.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lambdas/worker/ tests/test_worker.py
git commit -m "feat: worker lambda — SQS→InvokeAgent→DynamoDB, IN_PROGRESS tracking, error details"
```

---

## Task 11: Follow-up Lambda

**Files:**
- Create: `lambdas/followup/__init__.py`
- Create: `lambdas/followup/handler.py`
- Create: `tests/test_followup.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_followup.py`:

```python
import sys
import json
import pytest
sys.path.insert(0, "layers/shared/python")


def _event(incident_id="INC-001", message="Could it be a group policy conflict?"):
    return {
        "pathParameters": {"incident_id": incident_id},
        "body": json.dumps({"message": message}),
    }


def test_followup_returns_agent_response(aws_clients, mocker):
    mock_invoke = mocker.patch("boto3.client")
    mock_client = mock_invoke.return_value
    mock_client.invoke_agent.return_value = {
        "completion": [{"chunk": {"bytes": b"Group policy conflict is unlikely given the firewall evidence."}}]
    }

    import importlib
    import lambdas.followup.handler as m
    importlib.reload(m)

    result = m.lambda_handler(_event(), {})
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert "Group policy" in body["response"]


def test_followup_uses_same_session_id(aws_clients, mocker):
    mock_invoke = mocker.patch("boto3.client")
    mock_client = mock_invoke.return_value
    mock_client.invoke_agent.return_value = {"completion": []}

    import importlib
    import lambdas.followup.handler as m
    importlib.reload(m)

    m.lambda_handler(_event(incident_id="INC-999"), {})

    call_kwargs = mock_client.invoke_agent.call_args[1]
    assert call_kwargs["sessionId"] == "INC-999"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_followup.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `lambdas/followup/handler.py`**

```python
import sys
import os
import json
sys.path.insert(0, "/opt/python")

import boto3


def lambda_handler(event, context):
    incident_id = event["pathParameters"]["incident_id"]
    message = json.loads(event.get("body", "{}"))["message"]

    client = boto3.client("bedrock-agent-runtime")
    response = client.invoke_agent(
        agentId=os.environ["BEDROCK_AGENT_ID"],
        agentAliasId=os.environ["BEDROCK_AGENT_ALIAS_ID"],
        sessionId=incident_id,
        inputText=message,
    )
    completion = ""
    for event_chunk in response.get("completion", []):
        if "chunk" in event_chunk:
            completion += event_chunk["chunk"]["bytes"].decode("utf-8")

    return {
        "statusCode": 200,
        "body": json.dumps({"response": completion}),
        "headers": {"Content-Type": "application/json"},
    }
```

- [ ] **Step 4: Create `lambdas/followup/__init__.py`** (empty)

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_followup.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add lambdas/followup/ tests/test_followup.py
git commit -m "feat: followup lambda — continues Bedrock Agent session by incident_id"
```

---

## Task 12: KB Ingestion Lambda

**Files:**
- Create: `lambdas/kb_ingestion/__init__.py`
- Create: `lambdas/kb_ingestion/handler.py`
- Create: `tests/test_kb_ingestion.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_kb_ingestion.py`:

```python
import sys
import pytest
sys.path.insert(0, "layers/shared/python")


def _s3_event(key="knowledge-base/incidents/INC-001-resolution.md"):
    return {
        "Records": [{
            "s3": {
                "bucket": {"name": "org-log-analysis"},
                "object": {"key": key},
            }
        }]
    }


def test_kb_ingestion_starts_sync_job(aws_clients, mocker):
    mock_boto = mocker.patch("boto3.client")
    mock_client = mock_boto.return_value
    mock_client.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    import importlib
    import lambdas.kb_ingestion.handler as m
    importlib.reload(m)

    m.lambda_handler(_s3_event(), {})

    mock_client.start_ingestion_job.assert_called_once()
    call_kwargs = mock_client.start_ingestion_job.call_args[1]
    assert call_kwargs["knowledgeBaseId"] == "TEST_KB_ID"


def test_kb_ingestion_skips_non_kb_prefix(aws_clients, mocker):
    mock_boto = mocker.patch("boto3.client")
    mock_client = mock_boto.return_value

    import importlib
    import lambdas.kb_ingestion.handler as m
    importlib.reload(m)

    m.lambda_handler(_s3_event(key="logs/42/INC-001/output.txt"), {})
    mock_client.start_ingestion_job.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_kb_ingestion.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement `lambdas/kb_ingestion/handler.py`**

```python
import sys
import os
sys.path.insert(0, "/opt/python")

import boto3


KB_PREFIX = "knowledge-base/"


def lambda_handler(event, context):
    for record in event["Records"]:
        key = record["s3"]["object"]["key"]
        if not key.startswith(KB_PREFIX):
            print(f"Skipping non-KB key: {key}")
            continue

        client = boto3.client("bedrock-agent")
        response = client.start_ingestion_job(
            knowledgeBaseId=os.environ["BEDROCK_KB_ID"],
            dataSourceId=os.environ["BEDROCK_KB_DATASOURCE_ID"],
        )
        job_id = response["ingestionJob"]["ingestionJobId"]
        print(f"KB ingestion started: {job_id} for key: {key}")
```

- [ ] **Step 4: Create `lambdas/kb_ingestion/__init__.py`** (empty)

- [ ] **Step 5: Add `BEDROCK_KB_DATASOURCE_ID` to conftest env**

In `tests/conftest.py`, add to `aws_env` fixture:
```python
monkeypatch.setenv("BEDROCK_KB_DATASOURCE_ID", "TEST_DATASOURCE_ID")
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_kb_ingestion.py -v
```

Expected: both tests PASS.

- [ ] **Step 7: Commit**

```bash
git add lambdas/kb_ingestion/ tests/test_kb_ingestion.py tests/conftest.py
git commit -m "feat: KB ingestion lambda — S3 event triggers Bedrock Knowledge Base sync"
```

---

## Task 13: SAM Infrastructure Template

**Files:**
- Create: `template.yaml`
- Create: `samconfig.toml`
- Create: `config/scripts.json`

> **Prerequisites — complete these before running `sam deploy`:**
>
> **A. Enable Bedrock model access** (one-time, per-account per-region)
> AWS Console → Bedrock → Model access → Request access for:
> - `Anthropic Claude 3 Sonnet` (`anthropic.claude-3-sonnet-20240229-v1:0`)
> - `Amazon Titan Embeddings V1` (`amazon.titan-embed-text-v1`)
> Wait for status = "Access granted" before deploying.
>
> **B. Create OpenSearch Serverless collection** (required by Bedrock Knowledge Base)
> ```bash
> # Create the collection
> aws opensearchserverless create-collection \
>   --name log-analysis \
>   --type VECTORSEARCH \
>   --region ap-southeast-1
>
> # Create encryption policy (required before collection is active)
> aws opensearchserverless create-security-policy \
>   --name log-analysis-enc \
>   --type encryption \
>   --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/log-analysis"]}],"AWSOwnedKey":true}' \
>   --region ap-southeast-1
>
> # Create network policy (allow public access for Bedrock)
> aws opensearchserverless create-security-policy \
>   --name log-analysis-net \
>   --type network \
>   --policy '[{"Rules":[{"ResourceType":"collection","Resource":["collection/log-analysis"]},{"ResourceType":"dashboard","Resource":["collection/log-analysis"]}],"AllowFromPublic":true}]' \
>   --region ap-southeast-1
>
> # Wait for ACTIVE status (~2-3 min)
> aws opensearchserverless get-collection --name log-analysis --region ap-southeast-1
> ```
> Copy the `collectionEndpoint` ARN — it's the value used in `template.yaml` StorageConfiguration.
>
> **C. NinjaOne script contract** — every script in your NinjaOne library must accept `output_url` and write its output there:
> ```powershell
> param([string]$output_url, [string]$incident_id)
> # --- run your diagnostics ---
> $output = "... diagnostic results ..."
> # --- upload output to S3 via presigned URL ---
> $bytes = [System.Text.Encoding]::UTF8.GetBytes($output)
> Invoke-WebRequest -Uri $output_url -Method PUT -Body $bytes -ContentType "text/plain"
> ```
> Without this pattern, `job_poller` will always timeout because S3 will never have the output file.

- [ ] **Step 1: Create `config/scripts.json`**

```json
{
  "scripts": [
    {
      "name": "get_install_logs",
      "description": "Collects MSI installer logs and application installation event logs. Use for software installation failures.",
      "ninja_body": { "type": "ACTION", "id": 0, "uid": "REPLACE_WITH_REAL_UID", "parameters": "", "runAs": "SYSTEM" }
    },
    {
      "name": "check_connectivity",
      "description": "Tests DNS resolution, gateway ping, and port 443/80 reachability. Use when installs or updates fail with network errors.",
      "ninja_body": { "type": "ACTION", "id": 0, "uid": "REPLACE_WITH_REAL_UID", "parameters": "", "runAs": "SYSTEM" }
    },
    {
      "name": "check_firewall_rules",
      "description": "Lists active Windows Firewall rules and recent blocked connections.",
      "ninja_body": { "type": "ACTION", "id": 0, "uid": "REPLACE_WITH_REAL_UID", "parameters": "", "runAs": "SYSTEM" }
    },
    {
      "name": "check_windows_update_logs",
      "description": "Exports Windows Update history and error logs. Use for patching failures.",
      "ninja_body": { "type": "ACTION", "id": 0, "uid": "REPLACE_WITH_REAL_UID", "parameters": "", "runAs": "SYSTEM" }
    },
    {
      "name": "get_running_services",
      "description": "Lists all running and stopped Windows services. Use when a required service may not be running.",
      "ninja_body": { "type": "ACTION", "id": 0, "uid": "REPLACE_WITH_REAL_UID", "parameters": "", "runAs": "SYSTEM" }
    },
    {
      "name": "check_disk_space",
      "description": "Reports available disk space on all drives. Use when installs fail due to insufficient storage.",
      "ninja_body": { "type": "ACTION", "id": 0, "uid": "REPLACE_WITH_REAL_UID", "parameters": "", "runAs": "SYSTEM" }
    },
    {
      "name": "check_proxy_settings",
      "description": "Reports WinHTTP and browser proxy configuration. Use when installs fail to reach internet endpoints.",
      "ninja_body": { "type": "ACTION", "id": 0, "uid": "REPLACE_WITH_REAL_UID", "parameters": "", "runAs": "SYSTEM" }
    }
  ]
}
```

> **Note:** Replace `id` (integer) and `uid` (string) values with real NinjaOne script IDs from your NinjaOne automation script library before deploying.

- [ ] **Step 2: Create `template.yaml`**

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: AI Log Analysis System

Parameters:
  NinjaBaseUrl:
    Type: String
    Description: NinjaOne API base URL e.g. https://org.ninjarmm.com/api
  NinjaSecretName:
    Type: String
    Default: ninja-api-key
  Environment:
    Type: String
    Default: prod

Globals:
  Function:
    Runtime: python3.12
    Timeout: 900
    MemorySize: 256
    Layers:
      - !Ref SharedLayer
    Environment:
  Api:
    Auth:
      ApiKeyRequired: true
      UsagePlan:
        CreateUsagePlan: PER_API
        Description: "IT Admin API access — distribute key to admins only"
      Variables:
        INCIDENTS_TABLE: !Ref IncidentsTable
        DEVICE_CACHE_TABLE: !Ref DeviceCacheTable
        S3_BUCKET: !Ref LogsBucket
        NINJA_SECRET_NAME: !Ref NinjaSecretName
        NINJA_BASE_URL: !Ref NinjaBaseUrl
        BEDROCK_AGENT_ID: !GetAtt DiagnosticAgent.AgentId
        BEDROCK_AGENT_ALIAS_ID: !GetAtt DiagnosticAgentAlias.AgentAliasId
        BEDROCK_KB_ID: !Ref DiagnosticKnowledgeBase
        BEDROCK_KB_DATASOURCE_ID: !GetAtt KBDataSource.DataSourceId

Resources:

  # ── Shared Lambda Layer ──────────────────────────────────────────────
  SharedLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: log-analysis-shared
      ContentUri: layers/shared/
      CompatibleRuntimes: [python3.12]

  # ── S3 Bucket ────────────────────────────────────────────────────────
  LogsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketEncryption:
        ServerSideEncryptionConfiguration:
          - ServerSideEncryptionByDefault:
              SSEAlgorithm: AES256
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true
      NotificationConfiguration:
        LambdaConfigurations:
          - Event: s3:ObjectCreated:*
            Filter:
              S3Key:
                Rules:
                  - Name: prefix
                    Value: knowledge-base/
            Function: !GetAtt KBIngestionFunction.Arn

  # ── DynamoDB Tables ──────────────────────────────────────────────────
  IncidentsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub incidents-${Environment}
      BillingMode: PAY_PER_REQUEST
      SSESpecification:
        SSEEnabled: true
      AttributeDefinitions:
        - AttributeName: incident_id
          AttributeType: S
      KeySchema:
        - AttributeName: incident_id
          KeyType: HASH

  DeviceCacheTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub device-cache-${Environment}
      BillingMode: PAY_PER_REQUEST
      SSESpecification:
        SSEEnabled: true
      AttributeDefinitions:
        - AttributeName: device_name
          AttributeType: S
      KeySchema:
        - AttributeName: device_name
          KeyType: HASH

  # ── SQS ──────────────────────────────────────────────────────────────
  AnalysisDLQ:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub analysis-dlq-${Environment}
      MessageRetentionPeriod: 1209600

  AnalysisQueue:
    Type: AWS::SQS::Queue
    Properties:
      QueueName: !Sub analysis-queue-${Environment}
      VisibilityTimeout: 5400  # 6× Lambda timeout (900s) — prevents duplicate processing if Worker runs long
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt AnalysisDLQ.Arn
        maxReceiveCount: 3

  # ── DLQ Monitoring ───────────────────────────────────────────────────
  DLQAlertTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: !Sub analysis-dlq-alerts-${Environment}

  DLQAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: !Sub analysis-dlq-messages-${Environment}
      AlarmDescription: "Messages in DLQ — failed incident analyses need manual review"
      Namespace: AWS/SQS
      MetricName: ApproximateNumberOfMessagesVisible
      Dimensions:
        - Name: QueueName
          Value: !GetAtt AnalysisDLQ.QueueName
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 1
      Threshold: 1
      ComparisonOperator: GreaterThanOrEqualToThreshold
      AlarmActions:
        - !Ref DLQAlertTopic
      TreatMissingData: notBreaching

  # ── Lambda Functions ─────────────────────────────────────────────────
  OrchestratorFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambdas/orchestrator/
      Handler: handler.lambda_handler
      Environment:
        Variables:
          SQS_QUEUE_URL: !Ref AnalysisQueue
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref IncidentsTable
        - SQSSendMessagePolicy:
            QueueName: !GetAtt AnalysisQueue.QueueName
      Events:
        AnalyzeApi:
          Type: Api
          Properties:
            Path: /analyze
            Method: post

  WorkerFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambdas/worker/
      Handler: handler.lambda_handler
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref IncidentsTable
        - Statement:
            - Effect: Allow
              Action: [bedrock:InvokeAgent]
              Resource: "*"
      Events:
        SQSTrigger:
          Type: SQS
          Properties:
            Queue: !GetAtt AnalysisQueue.Arn
            BatchSize: 1

  ActionGroupFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambdas/action_group/
      Handler: handler.lambda_handler
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref DeviceCacheTable
        - S3CrudPolicy:
            BucketName: !Ref LogsBucket
        - AWSSecretsManagerGetSecretValuePolicy:
            SecretArn: !Sub arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${NinjaSecretName}*

  DeviceSyncFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambdas/device_sync/
      Handler: handler.lambda_handler
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref DeviceCacheTable
        - AWSSecretsManagerGetSecretValuePolicy:
            SecretArn: !Sub arn:aws:secretsmanager:${AWS::Region}:${AWS::AccountId}:secret:${NinjaSecretName}*
      Events:
        Schedule:
          Type: Schedule
          Properties:
            Schedule: rate(6 hours)

  FollowupFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambdas/followup/
      Handler: handler.lambda_handler
      Policies:
        - Statement:
            - Effect: Allow
              Action: [bedrock:InvokeAgent]
              Resource: "*"
      Events:
        FollowupApi:
          Type: Api
          Properties:
            Path: /followup/{incident_id}
            Method: post

  KBIngestionFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambdas/kb_ingestion/
      Handler: handler.lambda_handler
      Policies:
        - Statement:
            - Effect: Allow
              Action: [bedrock:StartIngestionJob]
              Resource: "*"

  KBIngestionPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !GetAtt KBIngestionFunction.Arn
      Action: lambda:InvokeFunction
      Principal: s3.amazonaws.com
      SourceArn: !GetAtt LogsBucket.Arn

  # ── Bedrock Knowledge Base ────────────────────────────────────────────
  BedrockKBRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: KBAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: [s3:GetObject, s3:ListBucket]
                Resource:
                  - !GetAtt LogsBucket.Arn
                  - !Sub "${LogsBucket.Arn}/*"

  DiagnosticKnowledgeBase:
    Type: AWS::Bedrock::KnowledgeBase
    Properties:
      Name: !Sub log-analysis-kb-${Environment}
      RoleArn: !GetAtt BedrockKBRole.Arn
      KnowledgeBaseConfiguration:
        Type: VECTOR
        VectorKnowledgeBaseConfiguration:
          EmbeddingModelArn: !Sub arn:aws:bedrock:${AWS::Region}::foundation-model/amazon.titan-embed-text-v1
      StorageConfiguration:
        Type: OPENSEARCH_SERVERLESS
        OpensearchServerlessConfiguration:
          CollectionArn: !Sub arn:aws:aoss:${AWS::Region}:${AWS::AccountId}:collection/log-analysis
          VectorIndexName: bedrock-knowledge-base-default-index
          FieldMapping:
            VectorField: bedrock-knowledge-base-default-vector
            TextField: AMAZON_BEDROCK_TEXT_CHUNK
            MetadataField: AMAZON_BEDROCK_METADATA

  KBDataSource:
    Type: AWS::Bedrock::DataSource
    Properties:
      KnowledgeBaseId: !Ref DiagnosticKnowledgeBase
      Name: log-analysis-s3-source
      DataSourceConfiguration:
        Type: S3
        S3Configuration:
          BucketArn: !GetAtt LogsBucket.Arn
          InclusionPrefixes: ["knowledge-base/"]

  # ── Bedrock Agent ─────────────────────────────────────────────────────
  BedrockAgentRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service: bedrock.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: AgentAccess
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: [bedrock:InvokeModel]
                Resource: "*"
              - Effect: Allow
                Action: [bedrock:Retrieve]
                Resource: !GetAtt DiagnosticKnowledgeBase.KnowledgeBaseArn
              - Effect: Allow
                Action: [lambda:InvokeFunction]
                Resource: !GetAtt ActionGroupFunction.Arn

  DiagnosticAgent:
    Type: AWS::Bedrock::Agent
    Properties:
      AgentName: !Sub log-analysis-agent-${Environment}
      AgentResourceRoleArn: !GetAtt BedrockAgentRole.Arn
      FoundationModel: anthropic.claude-3-sonnet-20240229-v1:0
      Instruction: |
        You are an expert IT diagnostic AI for a large organization (1000+ devices running Windows).
        Your job is to investigate why a device is problematic by running diagnostic scripts and analyzing their output.

        Rules:
        - Always investigate before concluding. Run scripts to gather evidence.
        - Cite specific log entries or script outputs as evidence for your conclusions.
        - Never recommend that a script fix something — only human IT admins perform remediation.
        - If a script fails, note it and try an alternative approach.
        - Cross-reference findings with the knowledge base — cite matching past incidents when relevant.
        - You may run at most 4 diagnostic scripts per investigation. Prioritize the most relevant scripts first.
        - Structure your final answer as:
          ROOT CAUSE: <one sentence>
          EVIDENCE: <bullet points from logs/scripts>
          KB MATCH: <similar past incidents if any>
          RECOMMENDED STEPS: <numbered list for human to execute>
      ActionGroups:
        - ActionGroupName: NinjaOneScriptRunner
          ActionGroupExecutor:
            Lambda: !GetAtt ActionGroupFunction.Arn
          FunctionSchema:
            Functions:
              - Name: run_ninja_script
                Description: "Execute a NinjaOne diagnostic script on a Windows device and return its output"
                Parameters:
                  script_name:
                    Type: string
                    Description: "Script name from the library (e.g. check_connectivity, get_install_logs)"
                    Required: true
                  device_name:
                    Type: string
                    Description: "Windows device hostname as it appears in NinjaOne (e.g. WIN-PC-0042)"
                    Required: true
                  incident_id:
                    Type: string
                    Description: "Incident ID for S3 output path tracking"
                    Required: true
      KnowledgeBases:
        - KnowledgeBaseId: !Ref DiagnosticKnowledgeBase
          Description: "Past incident resolutions, known Windows error codes, and software-specific fix guides"
          KnowledgeBaseState: ENABLED

  DiagnosticAgentAlias:
    Type: AWS::Bedrock::AgentAlias
    Properties:
      AgentId: !GetAtt DiagnosticAgent.AgentId
      AgentAliasName: !Sub live-${Environment}

Outputs:
  ApiEndpoint:
    Value: !Sub https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod
  LogsBucketName:
    Value: !Ref LogsBucket
  AgentId:
    Value: !GetAtt DiagnosticAgent.AgentId
```

- [ ] **Step 3: Create `samconfig.toml`**

```toml
version = 0.1

[default.deploy.parameters]
stack_name = "log-analysis"
region = "ap-southeast-1"
confirm_changeset = true
capabilities = "CAPABILITY_IAM CAPABILITY_AUTO_EXPAND"
parameter_overrides = "NinjaBaseUrl=https://REPLACE_WITH_ORG.ninjarmm.com/api"
```

- [ ] **Step 4: Validate SAM template**

```bash
sam validate --lint
```

Expected: `template.yaml is a valid SAM Template`

- [ ] **Step 5: Commit**

```bash
git add template.yaml samconfig.toml config/scripts.json
git commit -m "feat: SAM infrastructure template — all AWS resources defined"
```

---

## Task 14: Full Test Suite Pass + Deploy

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests PASS. Fix any failures before proceeding.

- [ ] **Step 2: Store NinjaOne API key in Secrets Manager**

```bash
aws secretsmanager create-secret \
  --name ninja-api-key \
  --secret-string '{"api_key":"YOUR_NINJA_API_KEY_HERE"}' \
  --region ap-southeast-1
```

- [ ] **Step 3: Update `config/scripts.json` with real NinjaOne script IDs**

For each script entry, replace `id` (integer) and `uid` (string) with values from your NinjaOne automation script library. Find them via: NinjaOne → Administration → Library → Automation → select script → note the ID from the URL.

- [ ] **Step 4: Build SAM package**

```bash
sam build
```

Expected: `Build Succeeded` — all Lambda packages built.

- [ ] **Step 5: Deploy to AWS**

```bash
sam deploy --guided
```

Enter your NinjaOne base URL when prompted for `NinjaBaseUrl`.

Expected: `Successfully created/updated stack - log-analysis`

- [ ] **Step 6: Upload `scripts.json` to S3**

```bash
aws s3 cp config/scripts.json s3://$(aws cloudformation describe-stacks \
  --stack-name log-analysis \
  --query "Stacks[0].Outputs[?OutputKey=='LogsBucketName'].OutputValue" \
  --output text)/config/scripts.json
```

- [ ] **Step 7: Upload initial Knowledge Base seed documents**

```bash
aws s3 cp docs/kb-seeds/ s3://BUCKET_NAME/knowledge-base/ --recursive
```

Create at least one seed document at `docs/kb-seeds/msi-error-codes.md` with common MSI error codes before this step.

- [ ] **Step 8: Smoke test — submit an analysis**

```bash
curl -X POST https://API_ENDPOINT/Prod/analyze \
  -H "Content-Type: application/json" \
  -d '{"device_name": "WIN-PC-0042", "problem": "Adobe CC installation fails with error 1603"}'
```

Expected response:
```json
{ "incident_id": "INC-20260521-WIN-PC-0042-XXXXXX", "status": "PENDING" }
```

- [ ] **Step 9: Poll for result**

```bash
aws dynamodb get-item \
  --table-name incidents-prod \
  --key '{"incident_id": {"S": "INC-20260521-WIN-PC-0042-XXXXXX"}}' \
  --region ap-southeast-1
```

Wait 2-5 minutes. Expected: `status` = `COMPLETE`, `analysis_report` contains `ROOT CAUSE:` section.

- [ ] **Step 10: Commit final state**

```bash
git add .
git commit -m "feat: complete AI log analysis system — all lambdas, infrastructure, and initial KB seeds"
```
