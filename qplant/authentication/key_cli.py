#!/usr/bin/env python3
"""
CLI tool for QPLANT API key management.

Usage::

    python key_cli.py generate --name "Production API" --days 365
    python key_cli.py validate --key "qplant_..."
    python key_cli.py revoke --key-id "key_abc123"
    python key_cli.py rotate --key-id "key_abc123"
    python key_cli.py list
    python key_cli.py info --key-id "key_abc123"
"""

from __future__ import annotations

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_key_manager import APIKeyManager


def cmd_generate(args: argparse.Namespace, mgr: APIKeyManager) -> None:
    """Generate a new API key."""
    key_id, api_key = mgr.generate_key(
        name=args.name,
        expiry_days=args.days,
        rate_limit=args.rate_limit,
    )
    print(f"✅ API Key generated successfully")
    print(f"   Key ID:   {key_id}")
    print(f"   API Key:  {api_key}")
    print(f"   Name:     {args.name}")
    print(f"   Expires:  {args.days} days")
    print(f"   Rate:     {args.rate_limit} req/hour")
    print()
    print("⚠️  Store the API Key securely — it cannot be retrieved later.")

    if args.output:
        # Write key to env-style output file
        with open(args.output, "a") as f:
            f.write(f"QPLANT_API_KEY={api_key}\n")
            f.write(f"QPLANT_KEY_ID={key_id}\n")
        print(f"   Written to {args.output}")


def cmd_validate(args: argparse.Namespace, mgr: APIKeyManager) -> None:
    """Validate an API key."""
    result = mgr.validate_key(args.key)
    if result["valid"]:
        print(f"✅ Valid API key")
        print(f"   Key ID: {result['key_id']}")
        print(f"   Name:   {result['name']}")
        print(f"   Rate:   {result['rate_limit']} req/hour")
    else:
        print(f"❌ Invalid: {result['reason']}")
        sys.exit(1)


def cmd_revoke(args: argparse.Namespace, mgr: APIKeyManager) -> None:
    """Revoke an API key."""
    if mgr.revoke_key(args.key_id):
        print(f"✅ Revoked key: {args.key_id}")
    else:
        print(f"❌ Key not found: {args.key_id}")
        sys.exit(1)


def cmd_rotate(args: argparse.Namespace, mgr: APIKeyManager) -> None:
    """Rotate an API key."""
    result = mgr.rotate_key(args.key_id)
    if result:
        new_key_id, new_api_key = result
        print(f"✅ Key rotated")
        print(f"   Old Key ID:   {args.key_id} (revoked)")
        print(f"   New Key ID:   {new_key_id}")
        print(f"   New API Key:  {new_api_key}")
        print()
        print("⚠️  Store the new API Key securely.")
    else:
        print(f"❌ Key not found: {args.key_id}")
        sys.exit(1)


def cmd_list(args: argparse.Namespace, mgr: APIKeyManager) -> None:
    """List all API keys."""
    keys = mgr.list_keys()
    if not keys:
        print("No API keys found.")
        return

    print(f"{'Key ID':<22} {'Name':<25} {'Status':<10} {'Uses':<8} {'Expires'}")
    print("─" * 95)
    for key_id, meta in keys.items():
        expires = meta.get("expires_at", "N/A")[:10]
        print(
            f"{key_id:<22} {meta['name']:<25} {meta['status']:<10} "
            f"{meta['usage_count']:<8} {expires}"
        )


def cmd_info(args: argparse.Namespace, mgr: APIKeyManager) -> None:
    """Show detailed info for a specific key."""
    info = mgr.get_key_info(args.key_id)
    if info:
        print(json.dumps(info, indent=2, default=str))
    else:
        print(f"❌ Key not found: {args.key_id}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QPLANT API Key Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        default="/home/ubuntu/authentication/api_keys.json",
        help="Path to API keys database (default: %(default)s)",
    )

    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # generate
    gen = sub.add_parser("generate", help="Generate a new API key")
    gen.add_argument("--name", required=True, help="Key name / description")
    gen.add_argument("--days", type=int, default=365, help="Expiry in days")
    gen.add_argument("--rate-limit", type=int, default=1000, help="Requests per hour")
    gen.add_argument("--output", help="Write key to file (.env format)")

    # validate
    val = sub.add_parser("validate", help="Validate an API key")
    val.add_argument("--key", required=True, help="API key to validate")

    # revoke
    rev = sub.add_parser("revoke", help="Revoke an API key")
    rev.add_argument("--key-id", required=True, help="Key ID to revoke")

    # rotate
    rot = sub.add_parser("rotate", help="Rotate an API key")
    rot.add_argument("--key-id", required=True, help="Key ID to rotate")

    # list
    sub.add_parser("list", help="List all API keys")

    # info
    inf = sub.add_parser("info", help="Show key details")
    inf.add_argument("--key-id", required=True, help="Key ID to inspect")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    mgr = APIKeyManager(keys_db_path=args.db)

    dispatch = {
        "generate": cmd_generate,
        "validate": cmd_validate,
        "revoke": cmd_revoke,
        "rotate": cmd_rotate,
        "list": cmd_list,
        "info": cmd_info,
    }
    dispatch[args.command](args, mgr)


if __name__ == "__main__":
    main()
