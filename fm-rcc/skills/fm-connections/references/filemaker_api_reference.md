# FileMaker API Reference — DataAPI & OData

Quick reference for connecting to FileMaker Server programmatically. Covers both the Data API (record CRUD + scripts) and OData (schema modification + record access).

---

## Connection Basics

Both APIs use HTTPS with Basic Auth (OData) or session tokens (DataAPI).

```
Base URLs:
  DataAPI:  https://{host}/fmi/data/v1/databases/{database}
  OData:    https://{host}/fmi/odata/v4/{database}
```

**SSL Note:** Hosted FMP servers often use self-signed certs. In Python, use `verify=False` and suppress warnings:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

---

## Data API

Session-based. Authenticate first, get a token, use it for all requests, release when done.

### Authenticate

```
POST /fmi/data/v1/databases/{database}/sessions
Authorization: Basic {base64(username:password)}
Content-Type: application/json
Body: {}
```

```python
resp = requests.post(
    f"{BASE}/sessions",
    auth=(username, password),
    headers={"Content-Type": "application/json"},
    json={},
    verify=False
)
token = resp.json()["response"]["token"]
```

### Release Token

```
DELETE /fmi/data/v1/databases/{database}/sessions/{token}
Authorization: Bearer {token}
```

### List Layouts

```
GET /fmi/data/v1/databases/{database}/layouts
Authorization: Bearer {token}
```

Response: `resp.json()["response"]["layouts"]` → list of `{"name": "LayoutName"}`

### Get Layout Metadata (Field Info)

```
GET /fmi/data/v1/databases/{database}/layouts/{layout}
Authorization: Bearer {token}
```

Response: `resp.json()["response"]["fieldMetaData"]` → list of field objects with `name`, `type`, `result`

**Important:** Only fields placed on the layout are returned. Fields that exist in the table but aren't on the layout won't appear.

### Get Records

```
GET /fmi/data/v1/databases/{database}/layouts/{layout}/records
Authorization: Bearer {token}
```

Optional query params: `_limit`, `_offset`, `_sort`

Response: `resp.json()["response"]["data"]` → list of record objects:
```python
{
    "recordId": "1",
    "modId": "0",
    "fieldData": {
        "Name": "Jane Doe",
        "Email": "jane@example.com",
        ...
    }
}
```

### Find Records

```
POST /fmi/data/v1/databases/{database}/layouts/{layout}/_find
Authorization: Bearer {token}
Content-Type: application/json
Body: {"query": [{"FieldName": "value"}]}
```

```python
resp = requests.post(
    f"{BASE}/layouts/{layout}/_find",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={"query": [{"Status": "pending"}]},
    verify=False
)
records = resp.json()["response"]["data"]
```

**No results:** Returns error code `"401"` (not HTTP 401) — check `resp.json()["messages"][0]["code"]`.

### Create Record

```
POST /fmi/data/v1/databases/{database}/layouts/{layout}/records
Authorization: Bearer {token}
Content-Type: application/json
Body: {"fieldData": {"Name": "Jane", "Email": "jane@example.com"}}
```

Response: `resp.json()["response"]["recordId"]` → the new record's internal ID

### Update Record

```
PATCH /fmi/data/v1/databases/{database}/layouts/{layout}/records/{recordId}
Authorization: Bearer {token}
Content-Type: application/json
Body: {"fieldData": {"Status": "complete"}}
```

Optional: include `"modId": "5"` in the body for optimistic locking (prevents overwriting concurrent changes).

### Delete Record

```
DELETE /fmi/data/v1/databases/{database}/layouts/{layout}/records/{recordId}
Authorization: Bearer {token}
```

### Run Script

```
GET /fmi/data/v1/databases/{database}/layouts/{layout}/script/{scriptName}?script.param={param}
Authorization: Bearer {token}
```

Or attach to any request with query params: `script={name}&script.param={value}`

### Python Pattern — Full Session Lifecycle

```python
import requests, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST = "https://server.fmphost.com"
DATABASE = "MyDatabase"
LAYOUT = "MyLayout"
BASE = f"{HOST}/fmi/data/v1/databases/{DATABASE}"

# Authenticate
resp = requests.post(f"{BASE}/sessions", auth=("user", "pass"),
    headers={"Content-Type": "application/json"}, json={}, verify=False)
token = resp.json()["response"]["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

try:
    # Do work...
    resp = requests.get(f"{BASE}/layouts/{LAYOUT}/records", headers=headers, verify=False)
    records = resp.json()["response"]["data"]
finally:
    # Always release the token
    requests.delete(f"{BASE}/sessions/{token}", headers=headers, verify=False)
```

---

## OData API

Uses Basic Auth on every request (no session tokens). Primarily useful for **schema modification** — creating tables and adding fields without opening FileMaker.

### Get Schema Metadata

```
GET /fmi/odata/v4/{database}/$metadata
Authorization: Basic {base64(username:password)}
```

Returns XML with all entity types (tables), their properties (fields), and field types.

### Query Records

```
GET /fmi/odata/v4/{database}/{TableName}
Authorization: Basic {base64(username:password)}
```

**Important:** OData entity names may differ from table names. Check `$metadata` — FileMaker often appends an underscore (e.g., table `Integration` becomes entity `Integration_`).

### Create Table

```
POST /fmi/odata/v4/{database}/FileMaker_Tables
Authorization: Basic {base64(username:password)}
Content-Type: application/json
```

```python
resp = requests.post(
    f"{HOST}/fmi/odata/v4/{DATABASE}/FileMaker_Tables",
    auth=(username, password),
    headers={"Content-Type": "application/json"},
    json={
        "tableName": "MyNewTable",
        "fields": [
            {"name": "ID", "type": "int", "primary": True},
            {"name": "Name", "type": "varchar(100)", "nullable": False},
            {"name": "Notes", "type": "varchar(2000)"},
            {"name": "Created", "type": "timestamp", "default": "CURRENT_TIMESTAMP"}
        ]
    },
    verify=False
)
```

### Add Fields to Existing Table

```
PATCH /fmi/odata/v4/{database}/FileMaker_Tables/{tableName}
Authorization: Basic {base64(username:password)}
Content-Type: application/json
```

```python
resp = requests.patch(
    f"{HOST}/fmi/odata/v4/{DATABASE}/FileMaker_Tables/Integration",
    auth=(username, password),
    headers={"Content-Type": "application/json"},
    json={
        "fields": [
            {"name": "ResponseJSON", "type": "varchar(1000000)"},
            {"name": "Score", "type": "int"},
            {"name": "SubmittedAt", "type": "timestamp"}
        ]
    },
    verify=False
)
```

**Key endpoint:** `FileMaker_Tables/{tableName}` — NOT `_schema` or the entity name. This is easy to get wrong.

**Partial success:** If one field fails (e.g., name conflict), others in the array may still be created.

### Delete Table

```
DELETE /fmi/odata/v4/{database}/FileMaker_Tables/{tableName}
Authorization: Basic {base64(username:password)}
```

### Delete Field

```
DELETE /fmi/odata/v4/{database}/FileMaker_Tables/{tableName}/{fieldName}
Authorization: Basic {base64(username:password)}
```

### Supported Field Types

| OData Type | FileMaker Equivalent | Notes |
|-----------|---------------------|-------|
| `INT` | Number | Integer |
| `NUMERIC` | Number | |
| `DECIMAL` | Number | Can specify precision: `DECIMAL(10,2)` |
| `VARCHAR` or `VARCHAR(n)` | Text | `n` = max length; omit for default |
| `CHARACTER VARYING` | Text | Same as VARCHAR |
| `DATE` | Date | |
| `TIME` | Time | |
| `TIMESTAMP` | Timestamp | |
| `BLOB` | Container | |
| `VARBINARY` | Container | |
| `LONGVARBINARY` | Container | |
| `BINARY VARYING` | Container | |

### Field Options

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | **Required.** Field name |
| `type` | string | **Required.** OData type from table above |
| `primary` | boolean | Primary key |
| `unique` | boolean | Unique validation |
| `nullable` | boolean | Allow null (default: true) |
| `global` | boolean | Global storage |
| `default` | string | Auto-enter keyword (see below) |
| `externalSecurePath` | string | Container external storage path |

### Default Value Keywords

| Keyword | What It Does |
|---------|-------------|
| `USER` / `CURRENT_USER` | Account name |
| `USERNAME` | Account name |
| `CURRENT_DATE` / `CURDATE` | Current date |
| `CURRENT_TIME` / `CURTIME` | Current time |
| `CURRENT_TIMESTAMP` / `CURTIMESTAMP` | Current timestamp |

---

## DataAPI vs OData — When to Use Which

| Task | DataAPI | OData |
|------|---------|-------|
| Read/write records | ✅ Primary choice | ✅ Works but less flexible |
| Find records (queries) | ✅ Full query support | ⚠️ Limited filtering |
| Run scripts | ✅ Yes | ❌ No |
| Create tables | ❌ No | ✅ Yes |
| Add/delete fields | ❌ No | ✅ Yes |
| Delete tables | ❌ No | ✅ Yes |
| Schema metadata | ✅ Layout fields only | ✅ Full table schema |
| Auth method | Session token | Basic auth per request |
| Portal data | ✅ Yes | ❌ No |

**Rule of thumb:** DataAPI for runtime operations (records, scripts, app logic). OData for schema operations (tables, fields, metadata) and quick one-off queries.

---

## Layout Gotcha

The DataAPI only sees fields **placed on the layout**. If you add a field via OData, you must also place it on a layout before DataAPI can read/write it. This doesn't apply to OData record access — OData sees all fields regardless of layout placement.

When adding fields via OData for use with DataAPI:
1. Add the field via OData (`PATCH FileMaker_Tables/{table}`)
2. Open the file in FileMaker and add the field to the relevant layout
3. Now DataAPI can access it

---

## Claris Documentation

- [Data API Guide](https://help.claris.com/en/data-api-guide/)
- [OData Guide](https://help.claris.com/en/odata-guide/)
- [Add Fields (OData)](https://help.claris.com/en/odata-guide/content/add-fields-into-table.html)
- [Create Table (OData)](https://help.claris.com/en/odata-guide/content/create-table.html)
