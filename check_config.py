#!/usr/bin/env python3
"""Check Uptrace MCP server configuration."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def check_config() -> bool:
    """Check if all required configuration is present."""
    errors = []

    uptrace_url = os.getenv("UPTRACE_URL")
    project_id = os.getenv("UPTRACE_PROJECT_ID")
    api_token = os.getenv("UPTRACE_API_TOKEN")

    if not uptrace_url:
        errors.append("❌ UPTRACE_URL is not set")
    else:
        print(f"✅ UPTRACE_URL: {uptrace_url}")

    if not project_id:
        errors.append("❌ UPTRACE_PROJECT_ID is not set")
    else:
        print(f"✅ UPTRACE_PROJECT_ID: {project_id}")

    if not api_token:
        errors.append("❌ UPTRACE_API_TOKEN is not set")
    else:
        masked_token = api_token[:8] + "..." if len(api_token) > 8 else "***"
        print(f"✅ UPTRACE_API_TOKEN: {masked_token}")

    if errors:
        print("\nConfiguration errors:")
        for error in errors:
            print(f"  {error}")
        return False

    print("\n✅ All configuration variables are set!")
    return True


def check_poetry() -> bool:
    """Check if Poetry is available."""
    venv_poetry = Path(".venv/bin/poetry")
    if venv_poetry.exists():
        print(f"✅ Poetry found at: {venv_poetry.absolute()}")
        return True

    print("❌ Poetry not found in .venv/bin/poetry")
    print("   Run: poetry install")
    return False


def main() -> None:
    """Run configuration check."""
    print("Checking Uptrace MCP Server configuration...\n")

    config_ok = check_config()
    poetry_ok = check_poetry()

    print()

    if config_ok and poetry_ok:
        print("✅ Configuration is valid!")
        print("\nYou can test the server with:")
        print("  .venv/bin/poetry run uptrace-mcp")
        sys.exit(0)
    else:
        print("❌ Configuration check failed")
        print("\nPlease fix the errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()

