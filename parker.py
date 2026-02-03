#!/usr/bin/env python3
"""
Parker - Auto Screenshot Tool for Documentation
Captures screenshots from a list of URLs using Playwright.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml
from playwright.sync_api import sync_playwright


def sanitize_filename(url: str) -> str:
    """Convert URL to safe filename."""
    parsed = urlparse(url)

    # Build filename from host and path
    host = parsed.netloc.replace(":", "-")  # localhost:3000 -> localhost-3000
    path = parsed.path.strip("/").replace("/", "-") or "index"

    # Add query params hash if present
    if parsed.query:
        query_hash = str(hash(parsed.query))[-6:]
        path = f"{path}-{query_hash}"

    filename = f"{host}-{path}" if path != "index" else host

    # Sanitize: keep only alphanumeric, dash, underscore
    filename = re.sub(r"[^a-zA-Z0-9\-_]", "-", filename)
    filename = re.sub(r"-+", "-", filename)  # collapse multiple dashes
    filename = filename.strip("-")

    return filename


def load_config(config_path: str) -> dict:
    """Load YAML config file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def perform_auth(page, auth_config: dict) -> bool:
    """Perform authentication steps."""
    auth_url = auth_config.get("url")
    steps = auth_config.get("steps", [])

    if not auth_url:
        print("  Error: auth.url is required")
        return False

    print(f"  Navigating to {auth_url}")
    page.goto(auth_url, wait_until="networkidle")

    for step in steps:
        try:
            if "fill" in step:
                selector = step["fill"]
                value = step.get("value", "")
                print(f"    Fill: {selector}")
                page.fill(selector, value)

            elif "click" in step:
                selector = step["click"]
                print(f"    Click: {selector}")
                page.click(selector)

            elif "wait" in step:
                ms = step["wait"]
                print(f"    Wait: {ms}ms")
                page.wait_for_timeout(ms)

            elif "wait_for" in step:
                selector = step["wait_for"]
                print(f"    Wait for: {selector}")
                page.wait_for_selector(selector)

            elif "type" in step:
                selector = step["type"]
                value = step.get("value", "")
                print(f"    Type: {selector}")
                page.type(selector, value)

            elif "press" in step:
                key = step["press"]
                print(f"    Press: {key}")
                page.keyboard.press(key)

            elif "goto" in step:
                url = step["goto"]
                print(f"    Goto: {url}")
                page.goto(url, wait_until="networkidle")

        except Exception as e:
            print(f"    Error in auth step: {e}")
            return False

    print("  Auth completed")
    return True


def capture_screenshots(config: dict, output_dir: Path, viewport: tuple, wait: int, full_page: bool):
    """Capture screenshots for all URLs in config."""
    urls = config.get("urls", [])
    auth_config = config.get("auth")

    if not urls:
        print("Error: No URLs found in config")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if any URL needs auth
    needs_auth = any(
        (isinstance(entry, dict) and entry.get("auth"))
        for entry in urls
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": viewport[0], "height": viewport[1]}
        )
        page = context.new_page()

        # Perform auth if needed
        auth_done = False
        if needs_auth:
            if not auth_config:
                print("Error: URLs require auth but no 'auth' config defined")
                sys.exit(1)
            print("Authenticating...")
            auth_done = perform_auth(page, auth_config)
            if not auth_done:
                print("Error: Authentication failed")
                sys.exit(1)
            print()

        results = []

        for i, entry in enumerate(urls, 1):
            # Support both string URLs and dict with url + metadata
            if isinstance(entry, str):
                url = entry
                name = None
                description = None
                method = "GET"
                post_data = None
                headers = None
                requires_auth = False
            else:
                url = entry.get("url")
                name = entry.get("name")
                description = entry.get("description")
                method = entry.get("method", "GET").upper()
                post_data = entry.get("data")  # POST body
                headers = entry.get("headers")
                requires_auth = entry.get("auth", False)

            if not url:
                print(f"  [{i}/{len(urls)}] Skipping invalid entry")
                continue

            filename = name or sanitize_filename(url)
            filepath = output_dir / f"{filename}.png"

            method_str = f" [{method}]" if method != "GET" else ""
            auth_str = " [AUTH]" if requires_auth else ""
            print(f"  [{i}/{len(urls)}] {url}{method_str}{auth_str}")
            print(f"          -> {filepath}")

            try:
                # Handle POST requests via route interception
                if method == "POST" and post_data:
                    def handle_route(route):
                        route.continue_(
                            method="POST",
                            post_data=json.dumps(post_data) if isinstance(post_data, dict) else post_data,
                            headers={**(headers or {}), "Content-Type": "application/json"} if isinstance(post_data, dict) else headers
                        )
                    page.route(url, handle_route)
                    page.goto(url, wait_until="networkidle")
                    page.unroute(url)
                else:
                    page.goto(url, wait_until="networkidle")
                if wait > 0:
                    page.wait_for_timeout(wait)
                page.screenshot(path=str(filepath), full_page=full_page)
                result = {
                    "url": url,
                    "file": str(filepath),
                    "filename": f"{filename}.png",
                    "status": "ok",
                    "auth": requires_auth
                }
                if description:
                    result["description"] = description
                results.append(result)
            except Exception as e:
                print(f"          Error: {e}")
                results.append({"url": url, "file": str(filepath), "filename": f"{filename}.png", "status": "error", "error": str(e)})

        browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Parker - Auto Screenshot Tool for Documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  parker -c urls.yaml                    # Basic usage
  parker -c urls.yaml -o ./docs/images   # Custom output dir
  parker -c urls.yaml --viewport 1920x1080 --full-page
        """
    )

    parser.add_argument("-c", "--config", required=True, help="YAML config file with URLs")
    parser.add_argument("-o", "--output", default="./screenshots", help="Output directory (default: ./screenshots)")
    parser.add_argument("--viewport", default="1280x720", help="Viewport size WIDTHxHEIGHT (default: 1280x720)")
    parser.add_argument("--wait", type=int, default=0, help="Extra wait time in ms after page load (default: 0)")
    parser.add_argument("--full-page", action="store_true", help="Capture full page screenshot")
    parser.add_argument("--manifest", action="store_true", help="Generate manifest.json with screenshot metadata")

    args = parser.parse_args()

    # Parse viewport
    try:
        width, height = map(int, args.viewport.lower().split("x"))
    except ValueError:
        print(f"Error: Invalid viewport format '{args.viewport}'. Use WIDTHxHEIGHT (e.g., 1280x720)")
        sys.exit(1)

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    print(f"Parker - Auto Screenshot Tool")
    print(f"Config: {config_path}")
    print(f"Output: {args.output}")
    print(f"Viewport: {width}x{height}")
    print()

    config = load_config(str(config_path))
    output_dir = Path(args.output)

    results = capture_screenshots(
        config=config,
        output_dir=output_dir,
        viewport=(width, height),
        wait=args.wait,
        full_page=args.full_page
    )

    # Write manifest if requested
    if args.manifest:
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "config": str(config_path),
            "output_dir": str(output_dir),
            "viewport": f"{width}x{height}",
            "screenshots": [r for r in results if r["status"] == "ok"]
        }
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest: {manifest_path}")

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    print()
    print(f"Done! {ok_count}/{len(results)} screenshots captured.")

    if ok_count < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
