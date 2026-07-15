#!/usr/bin/env python3
"""fm_odata — direct OData CLI for a hosted FileMaker file (no MCP).

Connects straight to the FileMaker Server OData v4 REST endpoint with the
credentials you supply — never the fixed-connection MCP. Give it a server,
file, account, and password (inline or via --config) and it just connects.

Credentials (any subcommand):
  --server HOST --file DB.fmp12 --account USER --password PASS
  --config PATH        # a hostedFile.md-style file (server/file/account/pass) or .json

Usage:
  python3 fm_odata.py connect --server h --file f.fmp12 --account a --password p
  python3 fm_odata.py tables [--all]
  python3 fm_odata.py schema <table>
  python3 fm_odata.py create-table <name> [--field Name:VARCHAR(255) --field Due:DATE ...]
  python3 fm_odata.py add-record <table> --data '{"Name":"x"}'   (or --name/--status/--due/--notes)
  python3 fm_odata.py get <table> [--top N]
  python3 fm_odata.py drop-table <name>

Field types are SQL DDL names (VARCHAR(255), DATE, NUMERIC, INT, TIMESTAMP, BLOB),
NOT FileMaker types (string/date). Error 8310 = an unrecognized field type.
"""

import argparse
import json
import sys

from odata_client import ODataClient, ODataError, resolve_config

# Default demo shape when create-table is called with no --field (a task table).
DEFAULT_FIELDS = [
    {"name": "Name", "type": "VARCHAR(255)"},
    {"name": "Status", "type": "VARCHAR(100)"},
    {"name": "DueDate", "type": "DATE"},
    {"name": "Notes", "type": "VARCHAR(4000)"},
]


def cmd_connect(client, args):
    cfg = client.config
    tables = client.list_tables()
    print(f"✅ Connected to {cfg['database']} on {cfg['server']} as {cfg['account']}")
    print(f"   {cfg['base_url']}")
    print(f"   {len(tables)} entity sets exposed over OData")


def _base_tables(tables):
    # Relationship occurrences show up as entity sets too (they contain '|').
    return [t for t in tables if "|" not in t]


def cmd_tables(client, args):
    tables = client.list_tables()
    shown = tables if args.all else _base_tables(tables)
    for t in sorted(shown):
        print(t)
    hidden = len(tables) - len(shown)
    if hidden and not args.all:
        print(f"\n(+{hidden} relationship occurrences hidden — pass --all to see them)")


def cmd_schema(client, args):
    fields = client.table_fields(args.table)
    if not fields:
        print(f"No fields found for {args.table!r} (does the table exist?)")
        return
    width = max(len(f["name"]) for f in fields)
    for f in fields:
        print(f"  {f['name']:<{width}}  {f['type']}")


def _parse_fields(pairs):
    """['Name:VARCHAR(255)', 'Due:DATE'] -> [{'name','type'}, ...]."""
    fields = []
    for pair in pairs:
        if ":" not in pair:
            raise ValueError(f"--field must be NAME:TYPE (got {pair!r})")
        name, type_ = pair.split(":", 1)
        fields.append({"name": name.strip(), "type": type_.strip()})
    return fields


def cmd_create_table(client, args):
    fields = _parse_fields(args.field) if args.field else DEFAULT_FIELDS
    print(f"Creating table {args.name!r} with fields: "
          f"{', '.join(f['name'] + ' ' + f['type'] for f in fields)} ...")
    result = client.create_table(args.name, fields)
    print("✅ created")
    print(json.dumps(result, indent=2))


def cmd_add_record(client, args):
    if args.data:
        values = json.loads(args.data)
    else:
        values = {}
        if args.name:
            values["Name"] = args.name
        if args.status:
            values["Status"] = args.status
        if args.due:
            values["DueDate"] = args.due
        if args.notes:
            values["Notes"] = args.notes
    if not values:
        raise ValueError("add-record needs --data JSON or at least --name")
    result = client.create_record(args.table, values)
    print(f"✅ record created in {args.table}")
    print(json.dumps(result, indent=2))


def cmd_get(client, args):
    records = client.get_records(args.table, top=args.top)
    print(f"{len(records)} record(s) in {args.table}:")
    print(json.dumps(records, indent=2))


def cmd_drop_table(client, args):
    status = client.delete_table(args.name)
    print(f"✅ dropped {args.name} (HTTP {status})")


def _creds_parser():
    """Shared credential flags, attached to every subcommand as a parent."""
    cp = argparse.ArgumentParser(add_help=False)
    cp.add_argument("--server", help="FileMaker Server host, e.g. fms.example.com")
    cp.add_argument("--file", help="database file, e.g. MyFile.fmp12")
    cp.add_argument("--account", help="account name")
    cp.add_argument("--password", help="password")
    cp.add_argument("--config", help="path to a hostedFile.md-style or .json creds file")
    return cp


def build_parser():
    creds = _creds_parser()
    p = argparse.ArgumentParser(prog="fm_odata", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("connect", parents=[creds]).set_defaults(func=cmd_connect)

    pt = sub.add_parser("tables", parents=[creds])
    pt.add_argument("--all", action="store_true", help="include relationship occurrences")
    pt.set_defaults(func=cmd_tables)

    ps = sub.add_parser("schema", parents=[creds])
    ps.add_argument("table")
    ps.set_defaults(func=cmd_schema)

    pc = sub.add_parser("create-table", parents=[creds])
    pc.add_argument("name")
    pc.add_argument("--field", action="append", metavar="NAME:SQLTYPE",
                    help="repeatable; SQL DDL type e.g. Name:VARCHAR(255). Omit for a default task table.")
    pc.set_defaults(func=cmd_create_table)

    pa = sub.add_parser("add-record", parents=[creds])
    pa.add_argument("table")
    pa.add_argument("--data", help="record as a JSON object")
    pa.add_argument("--name")
    pa.add_argument("--status")
    pa.add_argument("--due", help="date as MM/DD/YYYY")
    pa.add_argument("--notes")
    pa.set_defaults(func=cmd_add_record)

    pg = sub.add_parser("get", parents=[creds])
    pg.add_argument("table")
    pg.add_argument("--top", type=int)
    pg.set_defaults(func=cmd_get)

    pd = sub.add_parser("drop-table", parents=[creds])
    pd.add_argument("name")
    pd.set_defaults(func=cmd_drop_table)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        config = resolve_config(args.server, args.file, args.account,
                                args.password, args.config)
        client = ODataClient(config)
        args.func(client, args)
    except ODataError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001 - surface a clean message to the operator
        print(f"❌ {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
