"""Minimal FileMaker OData client — talks to a hosted .fmp12 directly over HTTPS.

No MCP, no plugin, no local file. Just the FileMaker Server OData v4 REST API,
which is the one live connection that can change *schema* (add tables + fields)
on a running hosted file.

Connection details are read from a sibling `hostedFile.md` (see load_config), so
credentials live in exactly one place — the file the workshop hands you.

FileMaker OData reference:
  Service root : GET  {base}/                      -> list of entity sets (tables)
  Metadata     : GET  {base}/$metadata             -> full CSDL schema (XML)
  Create table : POST {base}/FileMaker_Tables       {"tableName":..,"fields":[..]}
  Add field(s) : POST {base}/FileMaker_Tables/{tbl} {"fields":[..]}
  Create record: POST {base}/{table}                {field: value, ..}
  Read records : GET  {base}/{table}?$top=..&$filter=..
"""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# FileMaker OData create-table field types are SQL DDL type names, optionally
# sized (VARCHAR(200)) or with repetitions (INT[4]). The base word must be one
# of these; see https://help.claris.com/en/odata-guide/content/create-table.html
SQL_TYPES = {
    "NUMERIC", "DECIMAL", "INT", "DATE", "TIME", "TIMESTAMP", "VARCHAR",
    "CHARACTER VARYING", "BLOB", "VARBINARY", "LONGVARBINARY", "BINARY VARYING",
}


def _base_sql_type(type_str: str) -> str:
    """Strip size/repetition modifiers: 'VARCHAR(200)' -> 'VARCHAR', 'INT[4]' -> 'INT'."""
    return re.split(r"[(\[]", type_str, maxsplit=1)[0].strip().upper()


class ODataError(RuntimeError):
    """An OData request came back non-2xx. Carries status + parsed body."""

    def __init__(self, status: int, url: str, body: str):
        self.status = status
        self.url = url
        self.body = body
        super().__init__(f"HTTP {status} on {url}\n{body}")


def load_config(md_path: str | Path | None = None) -> dict:
    """Parse connection details out of hostedFile.md.

    Expected lines (order-independent):
        server  - your-server.example.com
        file    - YourFile.fmp12
        account - apiuser
        pass    - your-password
    """
    if md_path is None:
        md_path = Path(__file__).resolve().parent.parent / "hostedFile.md"
    md_path = Path(md_path)
    text = md_path.read_text()

    def grab(key: str) -> str:
        m = re.search(rf"^\s*{key}\s*-\s*(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE)
        if not m:
            raise ValueError(f"Could not find '{key}' in {md_path}")
        return m.group(1).strip()

    server = grab("server")
    file = grab("file")
    account = grab("account")
    password = grab("pass")

    # OData uses the database name without the .fmp12 extension.
    database = re.sub(r"\.fmp12$", "", file, flags=re.IGNORECASE)
    base_url = f"https://{server}/fmi/odata/v4/{database}"
    return {
        "server": server,
        "database": database,
        "account": account,
        "password": password,
        "base_url": base_url,
    }


def _config_from_parts(server: str, file: str, account: str, password: str) -> dict:
    """Build an OData config dict from explicit connection parts."""
    database = re.sub(r"\.fmp12$", "", file, flags=re.IGNORECASE)
    return {
        "server": server,
        "database": database,
        "account": account,
        "password": password,
        "base_url": f"https://{server}/fmi/odata/v4/{database}",
    }


def load_config_file(path: str | Path) -> dict:
    """Read connection details from a key-value file (the hostedFile.md shape:
    `server - host`, `file - x.fmp12`, `account - user`, `pass - secret`) or a
    JSON object with server/file/account/password (or `pass`) keys."""
    path = Path(path)
    text = path.read_text()
    if text.lstrip().startswith("{"):
        d = json.loads(text)
        return _config_from_parts(
            d["server"], d.get("file") or d["database"],
            d["account"], d.get("password") or d.get("pass"),
        )
    return load_config(path)  # markdown key-value — reuse the existing parser


def resolve_config(server: str | None = None, file: str | None = None,
                   account: str | None = None, password: str | None = None,
                   config_path: str | Path | None = None) -> dict:
    """Resolve OData connection config. Precedence: inline parts (all four
    required together) > --config file > a sibling hostedFile.md (legacy)."""
    if server and file and account and password:
        return _config_from_parts(server, file, account, password)
    if config_path:
        return load_config_file(config_path)
    default = Path(__file__).resolve().parent.parent / "hostedFile.md"
    if default.exists():
        return load_config(default)
    raise ValueError(
        "No credentials. Pass --server/--file/--account/--password, or "
        "--config <file> (server/file/account/pass keys)."
    )


class ODataClient:
    def __init__(self, config: dict | None = None):
        self.config = config or load_config()
        self.base_url = self.config["base_url"].rstrip("/")
        token = f"{self.config['account']}:{self.config['password']}".encode()
        self._auth = "Basic " + base64.b64encode(token).decode()

    # ---- low-level request ------------------------------------------------
    def _request(self, method: str, path: str, body: dict | None = None,
                 accept: str = "application/json") -> tuple[int, object]:
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", self._auth)
        req.add_header("Accept", accept)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode()
                status = resp.status
        except urllib.error.HTTPError as e:
            raise ODataError(e.code, url, e.read().decode()) from None

        if accept == "application/json" and raw.strip():
            return status, json.loads(raw)
        return status, raw

    # ---- schema discovery -------------------------------------------------
    def list_tables(self) -> list[str]:
        """Names of every entity set (table + relationship occurrence) exposed."""
        _, data = self._request("GET", "/")
        return [item["name"] for item in data.get("value", [])]

    def metadata_xml(self) -> str:
        """Raw CSDL ($metadata) — full field-level schema as XML."""
        _, raw = self._request("GET", "/$metadata", accept="application/xml")
        return raw

    # Edm (OData) types -> the FileMaker field type they came from.
    _EDM_TO_FM = {
        "Edm.String": "string",
        "Edm.Decimal": "numeric",
        "Edm.Double": "numeric",
        "Edm.Int64": "numeric",
        "Edm.Date": "date",
        "Edm.TimeOfDay": "time",
        "Edm.DateTimeOffset": "timestamp",
        "Edm.Stream": "container",
        "Edm.Binary": "container",
    }

    def table_fields(self, table: str) -> list[dict]:
        """Field name + type for one table, parsed from $metadata.

        The entity *set* (e.g. "CAT") maps to an entity *type* with a trailing
        underscore ("CAT_") via the EntityContainer, so resolve that first.
        """
        xml = self.metadata_xml()
        set_decl = re.search(
            rf'<EntitySet Name="{re.escape(table)}"\s+EntityType="([^"]+)"', xml
        )
        if not set_decl:
            return []
        type_name = set_decl.group(1).rsplit(".", 1)[-1]  # short name, e.g. CAT_
        block = re.search(
            rf'<EntityType Name="{re.escape(type_name)}".*?</EntityType>', xml, re.DOTALL
        )
        if not block:
            return []
        fields = []
        for m in re.finditer(r'<Property Name="([^"]+)" Type="([^"]+)"', block.group(0)):
            edm = m.group(2)
            fields.append({
                "name": m.group(1),
                "type": self._EDM_TO_FM.get(edm, edm),
            })
        return fields

    # ---- schema changes ---------------------------------------------------
    def create_table(self, table: str, fields: list[dict]) -> object:
        """Create a table. fields = [{"name": "Name", "type": "VARCHAR(255)"}, ...].

        Types are SQL DDL names (VARCHAR, DATE, TIMESTAMP, INT, NUMERIC, ...),
        optionally sized VARCHAR(200) or repeated INT[4].
        """
        for f in fields:
            base = _base_sql_type(str(f.get("type", "")))
            if base not in SQL_TYPES:
                raise ValueError(
                    f"field {f.get('name')!r}: type {f.get('type')!r} "
                    f"(base {base!r}) not in {sorted(SQL_TYPES)}"
                )
        _, data = self._request(
            "POST", "/FileMaker_Tables", {"tableName": table, "fields": fields}
        )
        return data

    def add_fields(self, table: str, fields: list[dict]) -> object:
        """Add one or more fields to an existing table."""
        _, data = self._request("POST", f"/FileMaker_Tables/{table}", {"fields": fields})
        return data

    def delete_table(self, table: str) -> int:
        """Drop a table (cleanup)."""
        status, _ = self._request("DELETE", f"/FileMaker_Tables/{table}")
        return status

    # ---- records ----------------------------------------------------------
    def create_record(self, table: str, values: dict) -> object:
        _, data = self._request("POST", f"/{table}", values)
        return data

    def get_records(self, table: str, top: int | None = None,
                    filter_: str | None = None) -> list[dict]:
        query = []
        if top is not None:
            query.append(f"$top={top}")
        if filter_:
            query.append(f"$filter={urllib.parse.quote(filter_)}")
        path = f"/{table}" + ("?" + "&".join(query) if query else "")
        _, data = self._request("GET", path)
        return data.get("value", [])
