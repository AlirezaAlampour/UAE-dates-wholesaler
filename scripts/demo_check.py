#!/usr/bin/env python3
"""Check the minimum local configuration and webhook path needed for the demo."""

import argparse
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv


DEFAULT_WEBHOOK_URL = "http://127.0.0.1:18080/webhook"
REQUIRED_ENV_VARS = (
    "WA_TOKEN",
    "WA_PHONE_NUMBER_ID",
    "WA_VERIFY_TOKEN",
    "ANTHROPIC_API_KEY",
)
PLACEHOLDER_VALUES = {"replace-with-a-random-secret"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check demo environment variables and webhook verification.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_WEBHOOK_URL,
        help=f"webhook URL to check (default: {DEFAULT_WEBHOOK_URL})",
    )
    return parser


def check_environment() -> bool:
    invalid = [
        name
        for name in REQUIRED_ENV_VARS
        if not os.getenv(name) or os.getenv(name) in PLACEHOLDER_VALUES
    ]
    if invalid:
        print(f"FAIL environment: not configured: {', '.join(invalid)}")
        return False

    print("OK environment: required variables are set")
    return True


def check_webhook(url: str) -> bool:
    verify_token = os.getenv("WA_VERIFY_TOKEN")
    if not verify_token:
        print("SKIP webhook: WA_VERIFY_TOKEN is missing")
        return False

    query = urllib.parse.urlencode(
        {
            "hub.mode": "subscribe",
            "hub.verify_token": verify_token,
            "hub.challenge": "demo-ready",
        }
    )
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(f"{url}{separator}{query}", method="GET")

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        print(f"FAIL webhook: {url} returned HTTP {exc.code}")
        return False
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, ValueError) as exc:
        reason = getattr(exc, "reason", type(exc).__name__)
        print(f"FAIL webhook: cannot reach {url} ({reason})")
        return False

    if status != 200 or body != "demo-ready":
        print(f"FAIL webhook: unexpected response from {url}")
        return False

    print(f"OK webhook: {url} verified")
    return True


def main() -> int:
    args = build_parser().parse_args()
    load_dotenv()

    environment_ok = check_environment()
    webhook_ok = check_webhook(args.url)
    if environment_ok and webhook_ok:
        print("DEMO CHECK PASSED")
        return 0

    print("DEMO CHECK FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
