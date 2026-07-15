#!/usr/bin/env python3
"""
FileMaker Unified CLI
=====================
Reliability: STABLE
Last validated: 2026-02-19
Known limitations:
- OData PATCH fails with 57-digit IDs (uses Data API for updates instead)
- Data API sessions timeout after 15 minutes (auto-reconnects)
- Large result sets may need pagination (default limit: 100)

Dependencies:
- requests (required)
- FM_*_SERVER, FM_*_DATABASE, FM_*_USERNAME, FM_*_PASSWORD in .env

Single entry point for all FileMaker operations. Uses OData for queries
(fast, supports filtering) and Data API for creates/updates (handles
large IDs correctly). Reads credentials from .env with profile support.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py test
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py tables
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py schema <table>
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py query <table> [--filter "..."] [--select "..."] [--limit N]
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py get <table> <record_id>
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py create <table> --data '{"field": "value"}'
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py update <table> <record_id> --data '{"field": "value"}'
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py delete <table> <record_id>
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py find <table> <field> <value> [--op contains]
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/fm-connections/scripts/fm.py count <table> [--filter "..."]

Credentials (first match wins):
    1. CLI overrides:  --server HOST --database DB --username USER --password PASS
    2. Profile vars:   FM_DEFAULT_SERVER, FM_DEFAULT_DATABASE, ... (or --profile NAME → FM_NAME_*)
    3. Project vars:   FM_HOST / FM_DATABASE / FM_USERNAME / FM_PASSWORD
                       (the same .env the rest of this project uses; FM_HOST may include https://)

    TLS: verification is ON by default. Set FM_SSL_VERIFY=false for dev servers
    with self-signed certificates — never in production.
"""

import argparse
import json
import os
import sys
import base64
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

# Load .env from the project root: search the working directory, then its
# parents, then this script's own tree. Shell environment always wins (setdefault).
def load_env():
    """Load the nearest .env into os.environ."""
    candidates = [Path.cwd()] + list(Path.cwd().parents)
    candidates += [p for p in Path(__file__).resolve().parents if p not in candidates]
    for folder in candidates:
        env_path = folder / '.env'
        if env_path.is_file():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return

load_env()

# TLS verification is ON by default; FM_SSL_VERIFY=false opts out for dev
# servers with self-signed certificates — never in production.
VERIFY_SSL = os.getenv('FM_SSL_VERIFY', 'true').strip().lower() not in ('false', '0', 'no')

try:
    import requests
    import urllib3
    if not VERIFY_SSL:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print(json.dumps({
        "status": "fatal",
        "error": {"type": "missing_dependency", "message": "pip install requests"}
    }, indent=2))
    sys.exit(1)


# Auto-managed fields that FileMaker sets automatically - never send these
AUTO_MANAGED_FIELDS = {
    'CreationAccount', 'ModifyAccount',
    'CreationTimestamp', 'ModifyTimestamp',
    'creationaccount', 'modifyaccount',
    'creationtimestamp', 'modifytimestamp',
}


def get_credentials(profile: str = 'DEFAULT', **overrides) -> dict:
    """Get FileMaker credentials from env vars or overrides."""
    prefix = f"FM_{profile.upper()}_"
    creds = {
        'server': overrides.get('server') or os.getenv(f'{prefix}SERVER'),
        'database': overrides.get('database') or os.getenv(f'{prefix}DATABASE'),
        'username': overrides.get('username') or os.getenv(f'{prefix}USERNAME'),
        'password': overrides.get('password') or os.getenv(f'{prefix}PASSWORD'),
    }

    missing = [k for k, v in creds.items() if not v]
    if missing:
        # Fall back to the project-wide bare vars (same .env as fm_client.py).
        for key in missing:
            fallback = os.getenv(f'FM_{key.upper()}')
            if not fallback and key == 'server':
                # Project convention: FM_HOST, which may include the scheme.
                fallback = (os.getenv('FM_HOST', '')
                            .replace('https://', '').replace('http://', '')
                            .strip().rstrip('/'))
            if fallback:
                creds[key] = fallback

        still_missing = [k for k, v in creds.items() if not v]
        if still_missing:
            print(json.dumps({
                "status": "fatal",
                "error": {
                    "type": "missing_config",
                    "message": f"Missing credentials for profile '{profile}': {', '.join(still_missing)}",
                    "suggestion": "Set FM_HOST, FM_DATABASE, FM_USERNAME, FM_PASSWORD in the project .env "
                                  f"(or profile-scoped FM_{profile.upper()}_SERVER, FM_{profile.upper()}_DATABASE, ...), "
                                  "or pass --server/--file/--account/--password or --config <file>."
                }
            }, indent=2))
            sys.exit(1)

    return creds


def load_creds_file(path: str) -> dict:
    """Read server/file/account/password from a hostedFile.md-style key-value
    file (`server - host`, `file - x.fmp12`, `account - user`, `pass - secret`)
    or a JSON object. Returns override kwargs for get_credentials()."""
    import re
    text = open(path, encoding='utf-8').read()
    if text.lstrip().startswith('{'):
        d = json.loads(text)
        server = d.get('server')
        file_ = d.get('file') or d.get('database')
        account = d.get('account') or d.get('username')
        password = d.get('password') or d.get('pass')
    else:
        def grab(key):
            m = re.search(rf'^\s*{key}\s*-\s*(.+?)\s*$', text, re.MULTILINE | re.IGNORECASE)
            return m.group(1).strip() if m else None
        server, file_, account, password = grab('server'), grab('file'), grab('account'), grab('pass')
    out = {}
    if server:
        out['server'] = server.replace('https://', '').replace('http://', '').strip().rstrip('/')
    if file_:
        out['database'] = re.sub(r'\.fmp12$', '', file_, flags=re.IGNORECASE)
    if account:
        out['username'] = account
    if password:
        out['password'] = password
    return out


def resolve_overrides(args) -> dict:
    """Merge credential sources into get_credentials overrides.
    Precedence (low→high): --config file < --file/--account aliases < explicit flags."""
    import re
    overrides = {}
    if getattr(args, 'config', None):
        overrides.update(load_creds_file(args.config))
    if getattr(args, 'file', None):
        overrides['database'] = re.sub(r'\.fmp12$', '', args.file, flags=re.IGNORECASE)
    if getattr(args, 'account', None):
        overrides['username'] = args.account
    for key, val in (('server', args.server), ('database', args.database),
                     ('username', args.username), ('password', args.password)):
        if val:
            overrides[key] = val
    return overrides


def strip_auto_managed(data: dict) -> dict:
    """Remove auto-managed fields that FileMaker won't let you set."""
    stripped = {}
    removed = []
    for key, value in data.items():
        if key.lower().replace(' ', '') in {f.lower() for f in AUTO_MANAGED_FIELDS}:
            removed.append(key)
        else:
            stripped[key] = value
    if removed:
        print(f"Note: Removed auto-managed fields: {', '.join(removed)}", file=sys.stderr)
    return stripped


def stringify_ids(data: dict) -> dict:
    """Convert large integer values to strings to prevent precision loss."""
    result = {}
    for key, value in data.items():
        if isinstance(value, int) and (len(str(abs(value))) > 15 or 'id' in key.lower() or 'ID' in key):
            result[key] = str(value)
        else:
            result[key] = value
    return result


class ODataClient:
    """Lightweight OData client for queries."""

    def __init__(self, server, database, username, password):
        self.base_url = f"https://{server}/fmi/odata/v4/{database}"
        cred = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.headers = {
            'Authorization': f'Basic {cred}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def request(self, method, endpoint, params=None, data=None):
        url = f"{self.base_url}/{endpoint}" if endpoint else self.base_url
        if params:
            parts = []
            for k, v in params.items():
                ek = quote(str(k), safe="$")
                ev = quote(str(v), safe="'(), ")
                parts.append(f"{ek}={ev}")
            url = f"{url}?{'&'.join(parts)}"

        resp = requests.request(
            method, url, headers=self.headers, json=data,
            verify=VERIFY_SSL, timeout=30
        )

        if resp.status_code == 401:
            return {"status": "fatal", "error": {"type": "auth_failure", "message": "Authentication failed"}}
        if resp.status_code == 404:
            return {"status": "skip", "error": {"type": "not_found", "message": f"Not found: {endpoint}"}}
        if resp.status_code >= 400:
            detail = resp.text[:500] if resp.text else "Unknown error"
            return {"status": "retry" if resp.status_code >= 500 else "skip",
                    "error": {"type": "api_error", "message": f"HTTP {resp.status_code}: {detail}"}}

        if resp.content:
            result = resp.json()
            return {"status": "success", "data": result.get("value", result)}
        return {"status": "success", "data": None}


class DataAPIClient:
    """Lightweight Data API client for creates/updates."""

    def __init__(self, server, database, username, password):
        self.base_url = f"https://{server}/fmi/data/v1/databases/{database}"
        self.username = username
        self.password = password
        self.token = None

    def _auth(self):
        if self.token:
            return
        cred = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        resp = requests.post(
            f"{self.base_url}/sessions",
            headers={'Authorization': f'Basic {cred}', 'Content-Type': 'application/json'},
            json={}, verify=VERIFY_SSL, timeout=15
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Data API auth failed: {resp.text[:300]}")
        self.token = resp.json()['response']['token']

    def request(self, method, endpoint, data=None):
        self._auth()
        resp = requests.request(
            method, f"{self.base_url}{endpoint}",
            headers={'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'},
            json=data, verify=VERIFY_SSL, timeout=30
        )
        result = resp.json()
        msgs = result.get('messages', [{}])
        if msgs and msgs[0].get('code', '0') != '0':
            return {"status": "skip", "error": {"type": "api_error",
                    "message": msgs[0].get('message', f"Error {msgs[0].get('code')}")}}
        return {"status": "success", "data": result.get('response', result)}

    def logout(self):
        if self.token:
            try:
                requests.delete(f"{self.base_url}/sessions/{self.token}", verify=VERIFY_SSL, timeout=5)
            except Exception:
                pass
            self.token = None


# --- Command Handlers ---

def cmd_test(odata, dataapi, args):
    result = odata.request('GET', '')
    if result['status'] == 'success':
        result['data'] = {"connected": True, "server": args._server, "database": args._database}
    return result


def cmd_tables(odata, dataapi, args):
    result = odata.request('GET', '')
    if result['status'] == 'success':
        data = result['data']
        tables = []
        if isinstance(data, list):
            tables = sorted(item.get('name') for item in data if isinstance(item, dict) and item.get('kind') == 'EntitySet')
        elif isinstance(data, dict):
            tables = sorted(k for k, v in data.items() if isinstance(v, dict) and v.get('$Kind') == 'EntitySet')
        result['data'] = tables
    return result


def cmd_schema(odata, dataapi, args):
    result = odata.request('GET', args.table, params={'$top': '1'})
    if result['status'] == 'success' and result['data']:
        if isinstance(result['data'], list) and len(result['data']) > 0:
            fields = list(result['data'][0].keys())
            result['data'] = {"table": args.table, "fields": fields, "field_count": len(fields)}
    return result


def cmd_query(odata, dataapi, args):
    params = {}
    if args.filter:
        params['$filter'] = args.filter
    if args.select:
        params['$select'] = args.select
    if args.orderby:
        params['$orderby'] = args.orderby
    if args.limit:
        params['$top'] = str(args.limit)
    if args.skip:
        params['$skip'] = str(args.skip)

    result = odata.request('GET', args.table, params=params)
    if result['status'] == 'success' and isinstance(result['data'], list):
        count = len(result['data'])
        result['meta'] = {"count": count, "table": args.table}
    return result


def cmd_get(odata, dataapi, args):
    return odata.request('GET', f"{args.table}('{args.record_id}')")


def cmd_create(odata, dataapi, args):
    data = json.loads(args.data)
    data = strip_auto_managed(data)
    data = stringify_ids(data)

    # Use Data API for creates (handles large IDs correctly)
    layout = args.table
    result = dataapi.request('POST', f"/layouts/{quote(layout)}/records", {"fieldData": data})
    if result['status'] == 'success':
        record_id = result['data'].get('recordId')
        result['data'] = {"recordId": record_id, "layout": layout, "created": True}
    return result


def cmd_update(odata, dataapi, args):
    data = json.loads(args.data)
    data = strip_auto_managed(data)
    data = stringify_ids(data)

    # Use Data API for updates (simple recordID, no large ID issues)
    layout = args.table
    result = dataapi.request('PATCH', f"/layouts/{quote(layout)}/records/{args.record_id}",
                             {"fieldData": data})
    if result['status'] == 'success':
        result['data'] = {"recordId": args.record_id, "layout": layout, "updated": True}
    return result


def cmd_delete(odata, dataapi, args):
    # Use Data API for deletes
    layout = args.table
    result = dataapi.request('DELETE', f"/layouts/{quote(layout)}/records/{args.record_id}")
    if result['status'] == 'success':
        result['data'] = {"recordId": args.record_id, "layout": layout, "deleted": True}
    return result


def cmd_find(odata, dataapi, args):
    op = args.op
    field = args.field
    value = args.value

    if op == 'contains':
        filter_expr = f"contains({field}, '{value}')"
    elif op in ('startswith', 'endswith'):
        filter_expr = f"{op}({field}, '{value}')"
    else:
        try:
            float(value)
            filter_expr = f"{field} {op} {value}"
        except ValueError:
            filter_expr = f"{field} {op} '{value}'"

    result = odata.request('GET', args.table, params={'$filter': filter_expr})
    if result['status'] == 'success' and isinstance(result['data'], list):
        result['meta'] = {"count": len(result['data']), "filter": filter_expr}
    return result


def cmd_count(odata, dataapi, args):
    params = {'$count': 'true', '$top': '0'}
    if args.filter:
        params['$filter'] = args.filter
    result = odata.request('GET', args.table, params=params)
    if result['status'] == 'success':
        data = result['data'] if isinstance(result['data'], dict) else {}
        count = data.get('@odata.count', 0)
        result['data'] = {"table": args.table, "count": count}
    return result


def main():
    parser = argparse.ArgumentParser(
        description="FileMaker Unified CLI - Query, create, update, delete records",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Connection options — a parent parser so credentials work AFTER the subcommand
    # (e.g. `fm.py test --server h --file f.fmp12 --account a --password p`), matching fm_odata.
    creds = argparse.ArgumentParser(add_help=False)
    creds.add_argument('--profile', default='DEFAULT', help='Credential profile: FM_<PROFILE>_* env vars, falling back to bare FM_HOST/FM_DATABASE/... (default: DEFAULT)')
    creds.add_argument('--server', help='FileMaker Server host')
    creds.add_argument('--database', help='Database name (or use --file)')
    creds.add_argument('--username', help='Account (or use --account)')
    creds.add_argument('--password', help='Password')
    creds.add_argument('--file', help='Database file, e.g. MyFile.fmp12 (alias for --database; .fmp12 stripped)')
    creds.add_argument('--account', help='Account name (alias for --username)')
    creds.add_argument('--config', help='Path to a hostedFile.md-style or .json credentials file')

    subs = parser.add_subparsers(dest='command', help='Commands')

    # test
    subs.add_parser('test', parents=[creds], help='Test connection')

    # tables
    subs.add_parser('tables', parents=[creds], help='List tables')

    # schema
    p = subs.add_parser('schema', parents=[creds], help='Get table schema')
    p.add_argument('table', help='Table name')

    # query
    p = subs.add_parser('query', parents=[creds], help='Query records (OData)')
    p.add_argument('table', help='Table name')
    p.add_argument('--filter', help='OData $filter expression')
    p.add_argument('--select', help='Fields to return (comma-separated)')
    p.add_argument('--orderby', help='Sort expression')
    p.add_argument('--limit', type=int, help='Max records')
    p.add_argument('--skip', type=int, help='Skip N records')

    # get
    p = subs.add_parser('get', parents=[creds], help='Get single record')
    p.add_argument('table', help='Table name')
    p.add_argument('record_id', help='Record ID')

    # create
    p = subs.add_parser('create', parents=[creds], help='Create record (Data API)')
    p.add_argument('table', help='Table/layout name')
    p.add_argument('--data', required=True, help='JSON field data')

    # update
    p = subs.add_parser('update', parents=[creds], help='Update record (Data API)')
    p.add_argument('table', help='Table/layout name')
    p.add_argument('record_id', help='Record ID (simple integer)')
    p.add_argument('--data', required=True, help='JSON field data')

    # delete
    p = subs.add_parser('delete', parents=[creds], help='Delete record (Data API)')
    p.add_argument('table', help='Table/layout name')
    p.add_argument('record_id', help='Record ID')

    # find
    p = subs.add_parser('find', parents=[creds], help='Find by field value')
    p.add_argument('table', help='Table name')
    p.add_argument('field', help='Field name')
    p.add_argument('value', help='Value to search')
    p.add_argument('--op', default='eq', help='Operator: eq, ne, contains, startswith, endswith, gt, lt')

    # count
    p = subs.add_parser('count', parents=[creds], help='Count records')
    p.add_argument('table', help='Table name')
    p.add_argument('--filter', help='OData $filter expression')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Get credentials — inline flags / --file/--account aliases / --config file / .env profile
    creds = get_credentials(args.profile, **resolve_overrides(args))

    # Stash for use in handlers
    args._server = creds['server']
    args._database = creds['database']

    # Initialize clients
    odata = ODataClient(creds['server'], creds['database'], creds['username'], creds['password'])
    dataapi = DataAPIClient(creds['server'], creds['database'], creds['username'], creds['password'])

    # Dispatch
    commands = {
        'test': cmd_test, 'tables': cmd_tables, 'schema': cmd_schema,
        'query': cmd_query, 'get': cmd_get, 'create': cmd_create,
        'update': cmd_update, 'delete': cmd_delete, 'find': cmd_find,
        'count': cmd_count,
    }

    try:
        handler = commands[args.command]
        result = handler(odata, dataapi, args)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result.get('status') == 'success' else 1)

    except json.JSONDecodeError as e:
        print(json.dumps({"status": "fatal", "error": {"type": "invalid_json", "message": str(e)}}, indent=2))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "fatal", "error": {"type": "unknown", "message": str(e)}}, indent=2))
        sys.exit(1)
    finally:
        dataapi.logout()


if __name__ == '__main__':
    main()
