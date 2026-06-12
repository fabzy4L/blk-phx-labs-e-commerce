#!/usr/bin/env python3
"""
BLK PHX LABS — Webhook Setup Script
Registers all webhook endpoints with Shopify, Typeform, and Recharge.

Usage:
  python scripts/setup_webhooks.py           # register all missing webhooks
  python scripts/setup_webhooks.py --list    # show current webhook state per platform
  python scripts/setup_webhooks.py --clean   # delete stale webhooks, then re-register
  python scripts/setup_webhooks.py --dry-run # preview what would change, no API calls

Requirements:
  WEBHOOK_BASE_URL must be set in .env — the public URL of your webhook server.
  For local dev use ngrok: ngrok http 8000 → copy the https:// URL.
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()

console = Console()

# ── CONFIG ────────────────────────────────────────────────────────────────────

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "").rstrip("/")

SHOPIFY_STORE_URL = os.getenv("SHOPIFY_STORE_URL", "")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-01")

TYPEFORM_API_TOKEN = os.getenv("TYPEFORM_API_TOKEN", "")
TYPEFORM_QUIZ_FORM_ID = os.getenv("TYPEFORM_QUIZ_FORM_ID", "")
TYPEFORM_WEBHOOK_SECRET = os.getenv("TYPEFORM_WEBHOOK_SECRET", "")

RECHARGE_ACCESS_TOKEN = os.getenv("RECHARGE_ACCESS_TOKEN", "")

SHOPIFY_WEBHOOK_DEFS = [
    {"topic": "orders/paid",      "path": "/webhooks/shopify/orders-paid"},
    {"topic": "customers/create", "path": "/webhooks/shopify/customers-create"},
]

TYPEFORM_WEBHOOK_DEFS = [
    {"tag": "blkphx-quiz", "path": "/webhooks/typeform/quiz"},
]

RECHARGE_WEBHOOK_DEFS = [
    {"topic": "subscription/activated",  "path": "/webhooks/recharge/subscription-activated"},
    {"topic": "subscription/cancelled",  "path": "/webhooks/recharge/subscription-cancelled"},
]

_STATUS_STYLE = {
    "exists":       "green",
    "created":      "bold green",
    "would_create": "cyan",
    "stale":        "yellow",
    "failed":       "bold red",
}


# ── VALIDATION ────────────────────────────────────────────────────────────────

def validate_env() -> bool:
    ok = True

    if not WEBHOOK_BASE_URL:
        console.print("[bold red]ERROR:[/] WEBHOOK_BASE_URL is not set in .env")
        console.print("  Local dev  → start ngrok: [bold]ngrok http 8000[/]  then set the https:// URL")
        console.print("  Production → set your deployed service URL (Railway, Fly.io, etc.)")
        ok = False

    if not SHOPIFY_STORE_URL or not SHOPIFY_ACCESS_TOKEN:
        console.print("[bold red]ERROR:[/] SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set")
        ok = False

    if not TYPEFORM_API_TOKEN or not TYPEFORM_QUIZ_FORM_ID:
        console.print("[yellow]WARN:[/]  Typeform skipped — TYPEFORM_API_TOKEN or TYPEFORM_QUIZ_FORM_ID not set")

    if not RECHARGE_ACCESS_TOKEN:
        console.print("[yellow]WARN:[/]  Recharge skipped — RECHARGE_ACCESS_TOKEN not set")

    return ok


# ── SHOPIFY ───────────────────────────────────────────────────────────────────

def _shopify_headers() -> dict:
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }


def list_shopify_webhooks() -> list[dict]:
    base = f"{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}"
    resp = requests.get(f"{base}/webhooks.json", headers=_shopify_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("webhooks", [])


def setup_shopify_webhooks(dry_run: bool = False, clean: bool = False) -> list[dict]:
    base = f"{SHOPIFY_STORE_URL}/admin/api/{SHOPIFY_API_VERSION}"
    existing = list_shopify_webhooks()
    results = []

    for wh in SHOPIFY_WEBHOOK_DEFS:
        target = f"{WEBHOOK_BASE_URL}{wh['path']}"
        matched = next((e for e in existing if e["topic"] == wh["topic"] and e["address"] == target), None)
        stale = [e for e in existing if e["topic"] == wh["topic"] and e["address"] != target]

        if matched:
            results.append({"platform": "Shopify", "topic": wh["topic"], "status": "exists", "address": target})
            continue

        if stale and not clean:
            results.append({
                "platform": "Shopify", "topic": wh["topic"], "status": "stale",
                "address": stale[0]["address"],
                "note": "Points to a different URL — run --clean to replace",
            })
            continue

        if clean and stale and not dry_run:
            for s in stale:
                requests.delete(f"{base}/webhooks/{s['id']}.json", headers=_shopify_headers(), timeout=10)

        if dry_run:
            results.append({"platform": "Shopify", "topic": wh["topic"], "status": "would_create", "address": target})
            continue

        payload = {"webhook": {"topic": wh["topic"], "address": target, "format": "json"}}
        resp = requests.post(f"{base}/webhooks.json", headers=_shopify_headers(), json=payload, timeout=10)
        resp.raise_for_status()
        results.append({
            "platform": "Shopify", "topic": wh["topic"], "status": "created",
            "id": resp.json()["webhook"]["id"], "address": target,
        })

    return results


# ── TYPEFORM ──────────────────────────────────────────────────────────────────

def _typeform_headers() -> dict:
    return {"Authorization": f"Bearer {TYPEFORM_API_TOKEN}", "Content-Type": "application/json"}


def list_typeform_webhooks(form_id: str) -> list[dict]:
    resp = requests.get(
        f"https://api.typeform.com/forms/{form_id}/webhooks",
        headers=_typeform_headers(), timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def setup_typeform_webhooks(dry_run: bool = False, clean: bool = False) -> list[dict]:
    if not TYPEFORM_API_TOKEN or not TYPEFORM_QUIZ_FORM_ID:
        return []

    existing_map = {wh["tag"]: wh for wh in list_typeform_webhooks(TYPEFORM_QUIZ_FORM_ID)}
    results = []

    for wh in TYPEFORM_WEBHOOK_DEFS:
        target = f"{WEBHOOK_BASE_URL}{wh['path']}"
        tag = wh["tag"]
        current = existing_map.get(tag)

        if current and current.get("url") == target and current.get("enabled"):
            results.append({"platform": "Typeform", "topic": tag, "status": "exists", "address": target})
            continue

        if dry_run:
            results.append({"platform": "Typeform", "topic": tag, "status": "would_create", "address": target})
            continue

        # PUT is idempotent — creates or updates the webhook for this tag
        payload: dict = {"url": target, "enabled": True}
        if TYPEFORM_WEBHOOK_SECRET:
            payload["secret"] = TYPEFORM_WEBHOOK_SECRET

        resp = requests.put(
            f"https://api.typeform.com/forms/{TYPEFORM_QUIZ_FORM_ID}/webhooks/{tag}",
            headers=_typeform_headers(), json=payload, timeout=10,
        )
        resp.raise_for_status()
        results.append({"platform": "Typeform", "topic": tag, "status": "created", "address": target})

    return results


# ── RECHARGE ──────────────────────────────────────────────────────────────────

def _recharge_headers() -> dict:
    return {"X-Recharge-Access-Token": RECHARGE_ACCESS_TOKEN, "Content-Type": "application/json"}


def list_recharge_webhooks() -> list[dict]:
    resp = requests.get("https://api.rechargeapps.com/webhooks", headers=_recharge_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("webhooks", [])


def setup_recharge_webhooks(dry_run: bool = False, clean: bool = False) -> list[dict]:
    if not RECHARGE_ACCESS_TOKEN:
        return []

    existing = list_recharge_webhooks()
    results = []

    for wh in RECHARGE_WEBHOOK_DEFS:
        target = f"{WEBHOOK_BASE_URL}{wh['path']}"
        matched = next((e for e in existing if e["topic"] == wh["topic"] and e["address"] == target), None)
        stale = [e for e in existing if e["topic"] == wh["topic"] and e["address"] != target]

        if matched:
            results.append({"platform": "Recharge", "topic": wh["topic"], "status": "exists", "address": target})
            continue

        if stale and not clean:
            results.append({
                "platform": "Recharge", "topic": wh["topic"], "status": "stale",
                "address": stale[0]["address"],
                "note": "Run --clean to replace",
            })
            continue

        if clean and stale and not dry_run:
            for s in stale:
                requests.delete(
                    f"https://api.rechargeapps.com/webhooks/{s['id']}",
                    headers=_recharge_headers(), timeout=10,
                )

        if dry_run:
            results.append({"platform": "Recharge", "topic": wh["topic"], "status": "would_create", "address": target})
            continue

        resp = requests.post(
            "https://api.rechargeapps.com/webhooks",
            headers=_recharge_headers(),
            json={"topic": wh["topic"], "address": target},
            timeout=10,
        )
        resp.raise_for_status()
        results.append({
            "platform": "Recharge", "topic": wh["topic"], "status": "created",
            "id": resp.json().get("webhook", {}).get("id", ""),
            "address": target,
        })

    return results


# ── OUTPUT ────────────────────────────────────────────────────────────────────

def print_results(results: list[dict], title: str = "Webhook Registration") -> None:
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("Platform",  width=10)
    table.add_column("Topic / Tag", width=34)
    table.add_column("Status",    width=14)
    table.add_column("Address / Note")

    for r in results:
        status = r.get("status", "")
        style = _STATUS_STYLE.get(status, "")
        detail = r.get("note") or r.get("address", "")
        table.add_row(
            r.get("platform", ""),
            r.get("topic", ""),
            f"[{style}]{status}[/{style}]",
            detail,
        )

    console.print(table)


def print_list_mode() -> None:
    """Print all currently registered webhooks across every platform."""
    # Shopify
    try:
        rows = list_shopify_webhooks()
        t = Table(title="Shopify Webhooks", header_style="bold")
        t.add_column("ID",    style="dim", width=12)
        t.add_column("Topic", width=28)
        t.add_column("Address")
        for r in rows:
            t.add_row(str(r["id"]), r["topic"], r["address"])
        if not rows:
            t.add_row("—", "none registered", "")
        console.print(t)
    except Exception as e:
        console.print(f"[red]Shopify list failed:[/] {e}")

    # Typeform
    if TYPEFORM_API_TOKEN and TYPEFORM_QUIZ_FORM_ID:
        try:
            rows = list_typeform_webhooks(TYPEFORM_QUIZ_FORM_ID)
            t = Table(title="Typeform Webhooks", header_style="bold")
            t.add_column("Tag",     width=20)
            t.add_column("Enabled", width=8)
            t.add_column("URL")
            for r in rows:
                t.add_row(r["tag"], str(r.get("enabled", "")), r.get("url", ""))
            if not rows:
                t.add_row("—", "—", "none registered")
            console.print(t)
        except Exception as e:
            console.print(f"[red]Typeform list failed:[/] {e}")
    else:
        console.print("[dim]Typeform: skipped (credentials not configured)[/dim]")

    # Recharge
    if RECHARGE_ACCESS_TOKEN:
        try:
            rows = list_recharge_webhooks()
            t = Table(title="Recharge Webhooks", header_style="bold")
            t.add_column("ID",    style="dim", width=12)
            t.add_column("Topic", width=28)
            t.add_column("Address")
            for r in rows:
                t.add_row(str(r.get("id", "")), r.get("topic", ""), r.get("address", ""))
            if not rows:
                t.add_row("—", "none registered", "")
            console.print(t)
        except Exception as e:
            console.print(f"[red]Recharge list failed:[/] {e}")
    else:
        console.print("[dim]Recharge: skipped (RECHARGE_ACCESS_TOKEN not set)[/dim]")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register BLK PHX LABS webhook endpoints with Shopify, Typeform, and Recharge."
    )
    parser.add_argument("--list",    action="store_true", help="List currently registered webhooks")
    parser.add_argument("--clean",   action="store_true", help="Delete stale webhooks before re-registering")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Preview changes without making API calls")
    args = parser.parse_args()

    if not validate_env():
        sys.exit(1)

    if args.list:
        console.print()
        print_list_mode()
        return

    if args.dry_run:
        console.print("\n[cyan bold]DRY RUN — no changes will be made[/]\n")
    if args.clean:
        console.print("[yellow bold]CLEAN MODE — stale webhooks will be replaced[/]\n")

    console.print(f"[dim]Webhook base URL:[/] {WEBHOOK_BASE_URL}\n")

    results: list[dict] = []

    for label, fn in [
        ("Shopify",  lambda: setup_shopify_webhooks(args.dry_run, args.clean)),
        ("Typeform", lambda: setup_typeform_webhooks(args.dry_run, args.clean)),
        ("Recharge", lambda: setup_recharge_webhooks(args.dry_run, args.clean)),
    ]:
        try:
            results += fn()
        except Exception as e:
            console.print(f"[bold red]{label} setup failed:[/] {e}")

    print_results(results)

    created = sum(1 for r in results if r["status"] in ("created", "would_create"))
    already = sum(1 for r in results if r["status"] == "exists")
    stale   = sum(1 for r in results if r["status"] == "stale")

    parts = []
    if already:
        parts.append(f"[green]{already} already registered[/]")
    if created:
        verb = "would be created" if args.dry_run else "created"
        parts.append(f"[bold green]{created} {verb}[/]")
    if stale:
        parts.append(f"[yellow]{stale} stale (run --clean to replace)[/]")

    console.print("\n" + " · ".join(parts) if parts else "")

    if not args.dry_run and created > 0:
        console.print("\n[dim]Tip: verify delivery in each platform's webhook dashboard after your first live event.[/dim]")


if __name__ == "__main__":
    main()
