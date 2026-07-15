"""
FileMaker Data API Client

A thin wrapper around the FileMaker Data API. Handles authentication,
session management, find requests, and record operations.

The agent imports this instead of writing FileMaker auth code from scratch.

Usage:
    from fm_client import FileMakerClient

    with FileMakerClient() as fm:
        records = fm.find("api_contacts", {"last_name": "Smith"})
        for r in records:
            print(r["fieldData"]["full_name"])
"""

import os
import json
import urllib.request
import urllib.error
import urllib.parse
import ssl

# Load .env with the stdlib — zero dependencies, works on any client machine.
# Searches the working directory, then its parents, then this script's own
# tree. Existing shell environment variables always win (setdefault).
def _load_env():
    from pathlib import Path
    candidates = [Path.cwd()] + list(Path.cwd().parents)
    candidates += [p for p in Path(__file__).resolve().parents if p not in candidates]
    for folder in candidates:
        env_path = folder / ".env"
        if env_path.is_file():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return


_load_env()


class FileMakerClient:
    """Context-managed FileMaker Data API client.

    Reads connection details from environment variables:
        FM_HOST       - Server URL (e.g., https://fms.example.com)
        FM_DATABASE   - Database name
        FM_USERNAME   - API account username
        FM_PASSWORD   - API account password

    Always use as a context manager to ensure session cleanup:
        with FileMakerClient() as fm:
            ...
    """

    def __init__(self, host=None, database=None, username=None, password=None, timeout=None):
        self.host = (host or os.environ.get("FM_HOST", "")).strip().rstrip("/")
        self.database = (database or os.environ.get("FM_DATABASE", "")).strip()
        self.username = (username or os.environ.get("FM_USERNAME", "")).strip()
        self.password = (password or os.environ.get("FM_PASSWORD", "")).strip()
        self.timeout = timeout if timeout is not None else float(os.environ.get("FM_TIMEOUT", "30"))
        self.token = None
        self._base_url = f"{self.host}/fmi/data/vLatest/databases/{self.database}"

        if not all([self.host, self.database, self.username, self.password]):
            raise ValueError(
                "Missing connection details. Set FM_HOST, FM_DATABASE, "
                "FM_USERNAME, and FM_PASSWORD environment variables."
            )

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logout()
        return False

    def _request(self, method, path, body=None, auth_header=None):
        """Make an HTTP request to the Data API."""
        url = f"{self._base_url}{path}"
        # Encode spaces and special chars in the URL path (e.g., layout names with spaces)
        url = urllib.parse.quote(url, safe=':/?&=.')
        headers = {"Content-Type": "application/json"}

        if auth_header:
            headers["Authorization"] = auth_header
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        # TLS verification is ON by default. For a dev server with a
        # self-signed certificate, set FM_SSL_VERIFY=false — never in production.
        ctx = ssl.create_default_context()
        if os.environ.get("FM_SSL_VERIFY", "").lower() in ("false", "0", "no"):
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(
                f"FileMaker API error {e.code}: {error_body}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot reach FileMaker server at {self.host}: {e.reason}. "
                "Check FM_HOST, the network, and that the Data API is enabled."
            ) from e

    def login(self):
        """Authenticate and store session token."""
        import base64
        credentials = base64.b64encode(
            f"{self.username}:{self.password}".encode()
        ).decode()
        result = self._request(
            "POST", "/sessions", body={},
            auth_header=f"Basic {credentials}"
        )
        self.token = result["response"]["token"]
        return self.token

    def logout(self):
        """Release the session token."""
        if self.token:
            try:
                self._request("DELETE", f"/sessions/{self.token}")
            except Exception:
                pass  # Best-effort cleanup
            finally:
                self.token = None

    def find(self, layout, query, sort=None, limit=None, offset=None):
        """Execute a find request.

        Args:
            layout: Layout name to query
            query: Dict of field/value pairs (AND'd), or list of dicts (OR'd)
            sort: Optional list of {"fieldName": ..., "sortOrder": ...}
            limit: Optional max records to return
            offset: Optional starting record (1-based)

        Returns:
            List of record dicts with fieldData and portalData
        """
        if isinstance(query, dict):
            query = [query]

        body = {"query": query}
        if sort:
            body["sort"] = sort
        if limit:
            body["limit"] = str(limit)
        if offset:
            body["offset"] = str(offset)

        result = self._request("POST", f"/layouts/{layout}/_find", body=body)
        return result.get("response", {}).get("data", [])

    def get_record(self, layout, record_id):
        """Fetch a single record by its FileMaker record ID."""
        result = self._request("GET", f"/layouts/{layout}/records/{record_id}")
        data = result.get("response", {}).get("data", [])
        return data[0] if data else None

    def get_records(self, layout, limit=100, offset=1):
        """Fetch records from a layout (paginated)."""
        result = self._request(
            "GET",
            f"/layouts/{layout}/records?_limit={limit}&_offset={offset}"
        )
        return result.get("response", {}).get("data", [])

    def get_all_records(self, layout, page_size=100, max_records=None):
        """Fetch ALL records from a layout, paginating automatically.

        Args:
            layout: Layout name
            page_size: Records per request (default 100)
            max_records: Optional safety cap; None fetches everything

        Returns:
            List of record dicts
        """
        records = []
        offset = 1
        while True:
            try:
                page = self.get_records(layout, limit=page_size, offset=offset)
            except RuntimeError as e:
                # FM error 401 = "No records match the request" — empty layout
                # or offset past the end, not an auth failure.
                if '"code":"401"' in str(e).replace(" ", ""):
                    break
                raise
            records.extend(page)
            if max_records is not None and len(records) >= max_records:
                return records[:max_records]
            if len(page) < page_size:
                break
            offset += page_size
        return records

    def create_record(self, layout, field_data, write=False):
        """Create a new record.

        Args:
            layout: Target layout
            field_data: Dict of field/value pairs
            write: Must be explicitly True — safety gate

        Returns:
            The new record's recordId
        """
        if not write:
            raise RuntimeError(
                "Write operations require write=True. "
                "This is a safety gate — confirm with the human first."
            )
        result = self._request(
            "POST", f"/layouts/{layout}/records",
            body={"fieldData": field_data}
        )
        return result.get("response", {}).get("recordId")

    def edit_record(self, layout, record_id, field_data, mod_id=None, write=False):
        """Edit an existing record.

        Args:
            layout: Target layout
            record_id: FileMaker record ID
            field_data: Dict of fields to update
            mod_id: Optional modification ID for optimistic locking
            write: Must be explicitly True — safety gate
        """
        if not write:
            raise RuntimeError(
                "Write operations require write=True. "
                "This is a safety gate — confirm with the human first."
            )
        body = {"fieldData": field_data}
        if mod_id is not None:
            body["modId"] = str(mod_id)
        return self._request(
            "PATCH", f"/layouts/{layout}/records/{record_id}",
            body=body
        )

    def delete_record(self, layout, record_id, write=False):
        """Delete a record.

        Args:
            layout: Target layout
            record_id: FileMaker record ID
            write: Must be explicitly True — safety gate
        """
        if not write:
            raise RuntimeError(
                "Write operations require write=True. "
                "This is a safety gate — confirm with the human first."
            )
        return self._request(
            "DELETE", f"/layouts/{layout}/records/{record_id}"
        )

    def run_script(self, layout, script_name, parameter=None):
        """Run a FileMaker script via the Data API.

        Args:
            layout: Any valid layout (required by the API even for scripts)
            script_name: Name of the FM script to run
            parameter: Optional script parameter (string)
        """
        path = f"/layouts/{layout}/script/{script_name}"
        if parameter is not None:
            path += f"?script.param={urllib.parse.quote(str(parameter))}"
        return self._request("GET", path)
