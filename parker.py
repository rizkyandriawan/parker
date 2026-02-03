#!/usr/bin/env python3
"""
Parker - Auto Screenshot Tool for Documentation
Captures screenshots from a list of URLs using Playwright.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml
from playwright.sync_api import sync_playwright

# Exit codes
EXIT_SUCCESS = 0
EXIT_PARTIAL = 1  # Some screenshots failed
EXIT_FAILURE = 2  # All failed or critical error

# Device presets
DEVICES = {
    "desktop": {"width": 1280, "height": 720, "device_scale_factor": 1, "is_mobile": False},
    "laptop": {"width": 1440, "height": 900, "device_scale_factor": 1, "is_mobile": False},
    "tablet": {"width": 768, "height": 1024, "device_scale_factor": 2, "is_mobile": True},
    "mobile": {"width": 375, "height": 667, "device_scale_factor": 2, "is_mobile": True},
}


def sanitize_filename(url: str) -> str:
    """Convert URL to safe filename."""
    parsed = urlparse(url)
    host = parsed.netloc.replace(":", "-")
    path = parsed.path.strip("/").replace("/", "-") or "index"

    if parsed.query:
        query_hash = str(hash(parsed.query))[-6:]
        path = f"{path}-{query_hash}"

    filename = f"{host}-{path}" if path != "index" else host
    filename = re.sub(r"[^a-zA-Z0-9\-_]", "-", filename)
    filename = re.sub(r"-+", "-", filename)
    return filename.strip("-")


def file_hash(filepath: Path) -> str:
    """Calculate MD5 hash of file for diff detection."""
    if not filepath.exists():
        return ""
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:12]


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


def capture_single(page, url: str, filepath: Path, entry: dict, global_wait: int,
                   global_wait_for: str, full_page: bool) -> dict:
    """Capture a single screenshot."""
    method = entry.get("method", "GET").upper() if isinstance(entry, dict) else "GET"
    post_data = entry.get("data") if isinstance(entry, dict) else None
    headers = entry.get("headers") if isinstance(entry, dict) else None
    wait_for = entry.get("wait_for") if isinstance(entry, dict) else None
    wait_ms = entry.get("wait") if isinstance(entry, dict) else None

    try:
        # Handle POST requests
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

        # Wait for selector (per-URL or global)
        selector_to_wait = wait_for or global_wait_for
        if selector_to_wait:
            page.wait_for_selector(selector_to_wait, timeout=10000)

        # Extra wait time (per-URL or global)
        wait_time = wait_ms if wait_ms is not None else global_wait
        if wait_time > 0:
            page.wait_for_timeout(wait_time)

        # Get page title
        title = page.title()

        # Get page meta description or first paragraph
        meta_desc = page.evaluate("""() => {
            const meta = document.querySelector('meta[name="description"]');
            if (meta) return meta.content;
            const p = document.querySelector('p');
            if (p) return p.textContent.slice(0, 200);
            return '';
        }""")

        # Take screenshot
        page.screenshot(path=str(filepath), full_page=full_page)

        return {
            "status": "ok",
            "title": title,
            "page_description": meta_desc.strip() if meta_desc else "",
            "hash": file_hash(filepath)
        }

    except Exception as e:
        error_msg = str(e)
        # Classify error
        if "timeout" in error_msg.lower():
            return {"status": "timeout", "error": error_msg}
        elif "net::" in error_msg.lower():
            return {"status": "network_error", "error": error_msg}
        else:
            return {"status": "error", "error": error_msg}


def capture_screenshots(config: dict, output_dir: Path, default_viewport: tuple,
                        global_wait: int, global_wait_for: str, full_page: bool):
    """Capture screenshots for all URLs in config."""
    urls = config.get("urls", [])
    auth_config = config.get("auth")

    if not urls:
        print("Error: No URLs found in config")
        sys.exit(EXIT_FAILURE)

    output_dir.mkdir(parents=True, exist_ok=True)

    needs_auth = any(
        (isinstance(entry, dict) and entry.get("auth"))
        for entry in urls
    )

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Create default context
        default_context = browser.new_context(
            viewport={"width": default_viewport[0], "height": default_viewport[1]}
        )
        default_page = default_context.new_page()

        # Perform auth if needed
        if needs_auth:
            if not auth_config:
                print("Error: URLs require auth but no 'auth' config defined")
                sys.exit(EXIT_FAILURE)
            print("Authenticating...")
            if not perform_auth(default_page, auth_config):
                print("Error: Authentication failed")
                sys.exit(EXIT_FAILURE)
            print()

        # Store auth cookies for device contexts
        auth_cookies = default_context.cookies() if needs_auth else []

        for i, entry in enumerate(urls, 1):
            if isinstance(entry, str):
                url = entry
                name = None
                description = None
                requires_auth = False
                devices = None
            else:
                url = entry.get("url")
                name = entry.get("name")
                description = entry.get("description")
                requires_auth = entry.get("auth", False)
                devices = entry.get("devices")

            if not url:
                print(f"  [{i}/{len(urls)}] Skipping invalid entry")
                continue

            # Determine which devices to capture
            device_list = devices if devices else ["default"]

            for device_name in device_list:
                if device_name == "default":
                    page = default_page
                    context = default_context
                    suffix = ""
                    viewport_info = f"{default_viewport[0]}x{default_viewport[1]}"
                else:
                    device_config = DEVICES.get(device_name)
                    if not device_config:
                        print(f"  Warning: Unknown device '{device_name}', skipping")
                        continue
                    context = browser.new_context(
                        viewport={"width": device_config["width"], "height": device_config["height"]},
                        device_scale_factor=device_config["device_scale_factor"],
                        is_mobile=device_config["is_mobile"]
                    )
                    if auth_cookies:
                        context.add_cookies(auth_cookies)
                    page = context.new_page()
                    suffix = f"-{device_name}"
                    viewport_info = device_name

                base_filename = name or sanitize_filename(url)
                filename = f"{base_filename}{suffix}"
                filepath = output_dir / f"{filename}.png"

                method = entry.get("method", "GET").upper() if isinstance(entry, dict) else "GET"
                method_str = f" [{method}]" if method != "GET" else ""
                auth_str = " [AUTH]" if requires_auth else ""
                device_str = f" [{viewport_info}]" if device_name != "default" else ""

                print(f"  [{i}/{len(urls)}] {url}{method_str}{auth_str}{device_str}")
                print(f"          -> {filepath}")

                result = capture_single(page, url, filepath, entry, global_wait,
                                       global_wait_for, full_page)

                result_entry = {
                    "url": url,
                    "file": str(filepath),
                    "filename": f"{filename}.png",
                    "status": result["status"],
                    "auth": requires_auth,
                    "device": device_name if device_name != "default" else None,
                }

                if result["status"] == "ok":
                    result_entry["title"] = result.get("title", "")
                    result_entry["hash"] = result.get("hash", "")
                    if result.get("page_description"):
                        result_entry["page_description"] = result["page_description"]
                else:
                    result_entry["error"] = result.get("error", "")
                    print(f"          Error: {result.get('error', 'Unknown error')}")

                if description:
                    result_entry["description"] = description

                results.append(result_entry)

                # Close device-specific context
                if device_name != "default":
                    context.close()

        browser.close()

    return results


def generate_html_report(results: list, output_dir: Path, manifest: dict):
    """Generate HTML gallery report."""
    ok_results = [r for r in results if r["status"] == "ok"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Parker Screenshots</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }}
        .header {{
            background: #1a1a2e; color: white; padding: 20px; border-radius: 8px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .meta {{ font-size: 14px; opacity: 0.8; }}
        .grid {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: white; border-radius: 8px; overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .card img {{
            width: 100%; height: 250px; object-fit: cover; object-position: top;
            cursor: pointer; transition: transform 0.2s;
        }}
        .card img:hover {{ transform: scale(1.02); }}
        .card-body {{ padding: 15px; }}
        .card-title {{ font-weight: 600; margin: 0 0 5px 0; font-size: 14px; }}
        .card-url {{
            font-size: 12px; color: #666; word-break: break-all;
            margin-bottom: 8px;
        }}
        .card-meta {{ font-size: 11px; color: #999; }}
        .badge {{
            display: inline-block; padding: 2px 6px; border-radius: 4px;
            font-size: 10px; margin-right: 4px;
        }}
        .badge-auth {{ background: #ffeeba; color: #856404; }}
        .badge-device {{ background: #d4edda; color: #155724; }}
        .modal {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.9); z-index: 1000; cursor: pointer;
        }}
        .modal img {{
            max-width: 95%; max-height: 95%; position: absolute;
            top: 50%; left: 50%; transform: translate(-50%, -50%);
        }}
        .modal.active {{ display: block; }}
        .summary {{
            display: flex; gap: 20px; margin-top: 10px;
        }}
        .summary-item {{ font-size: 14px; }}
        .summary-item strong {{ color: #4CAF50; }}
        .summary-item.error strong {{ color: #f44336; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Parker Screenshots</h1>
        <div class="meta">
            Generated: {manifest.get('generated_at', '')} &bull;
            Viewport: {manifest.get('viewport', '')}
        </div>
        <div class="summary">
            <div class="summary-item"><strong>{len(ok_results)}</strong> captured</div>
            <div class="summary-item error"><strong>{len(results) - len(ok_results)}</strong> failed</div>
        </div>
    </div>
    <div class="grid">
"""

    for r in ok_results:
        filename = r.get("filename", "")
        title = r.get("title", "") or r.get("description", "") or filename
        badges = ""
        if r.get("auth"):
            badges += '<span class="badge badge-auth">AUTH</span>'
        if r.get("device"):
            badges += f'<span class="badge badge-device">{r["device"]}</span>'

        html += f"""
        <div class="card">
            <img src="{filename}" alt="{title}" onclick="showModal(this.src)">
            <div class="card-body">
                <h3 class="card-title">{title}</h3>
                <div class="card-url">{r.get('url', '')}</div>
                <div class="card-meta">
                    {badges}
                    <span style="opacity:0.5">hash: {r.get('hash', '')[:8]}</span>
                </div>
            </div>
        </div>
"""

    html += """
    </div>
    <div class="modal" id="modal" onclick="hideModal()">
        <img id="modal-img" src="">
    </div>
    <script>
        function showModal(src) {
            document.getElementById('modal-img').src = src;
            document.getElementById('modal').classList.add('active');
        }
        function hideModal() {
            document.getElementById('modal').classList.remove('active');
        }
        document.addEventListener('keydown', e => { if(e.key === 'Escape') hideModal(); });
    </script>
</body>
</html>
"""

    html_path = output_dir / "index.html"
    with open(html_path, "w") as f:
        f.write(html)
    return html_path


def main():
    parser = argparse.ArgumentParser(
        description="Parker - Auto Screenshot Tool for Documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  parker -c urls.yaml                         # Basic usage
  parker -c urls.yaml -o ./docs/images        # Custom output dir
  parker -c urls.yaml --wait-for "#app"       # Wait for element
  parker -c urls.yaml --html                  # Generate HTML gallery

Exit codes:
  0 - All screenshots captured successfully
  1 - Some screenshots failed (partial success)
  2 - Critical error (auth failed, no URLs, etc.)
        """
    )

    parser.add_argument("-c", "--config", required=True, help="YAML config file with URLs")
    parser.add_argument("-o", "--output", default="./screenshots", help="Output directory")
    parser.add_argument("--viewport", default="1280x720", help="Viewport size WIDTHxHEIGHT")
    parser.add_argument("--wait", type=int, default=0, help="Extra wait time in ms after page load")
    parser.add_argument("--wait-for", dest="wait_for", help="Wait for CSS selector before capture")
    parser.add_argument("--full-page", action="store_true", help="Capture full page screenshot")
    parser.add_argument("--manifest", action="store_true", help="Generate manifest.json")
    parser.add_argument("--html", action="store_true", help="Generate HTML gallery report")

    args = parser.parse_args()

    # Parse viewport
    try:
        width, height = map(int, args.viewport.lower().split("x"))
    except ValueError:
        print(f"Error: Invalid viewport format '{args.viewport}'")
        sys.exit(EXIT_FAILURE)

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(EXIT_FAILURE)

    print(f"Parker - Auto Screenshot Tool")
    print(f"Config: {config_path}")
    print(f"Output: {args.output}")
    print(f"Viewport: {width}x{height}")
    if args.wait_for:
        print(f"Wait for: {args.wait_for}")
    print()

    config = load_config(str(config_path))
    output_dir = Path(args.output)

    results = capture_screenshots(
        config=config,
        output_dir=output_dir,
        default_viewport=(width, height),
        global_wait=args.wait,
        global_wait_for=args.wait_for,
        full_page=args.full_page
    )

    # Build manifest
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "config": str(config_path),
        "output_dir": str(output_dir),
        "viewport": f"{width}x{height}",
        "screenshots": results
    }

    # Write manifest if requested
    if args.manifest or args.html:
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"Manifest: {manifest_path}")

    # Generate HTML report if requested
    if args.html:
        html_path = generate_html_report(results, output_dir, manifest)
        print(f"HTML Report: {html_path}")

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    timeout_count = sum(1 for r in results if r["status"] == "timeout")
    error_count = len(results) - ok_count

    print()
    print(f"Done! {ok_count}/{len(results)} screenshots captured.")
    if timeout_count > 0:
        print(f"  Timeouts: {timeout_count}")
    if error_count > 0:
        print(f"  Errors: {error_count}")

    # Exit code based on results
    if ok_count == 0 and len(results) > 0:
        sys.exit(EXIT_FAILURE)
    elif ok_count < len(results):
        sys.exit(EXIT_PARTIAL)
    else:
        sys.exit(EXIT_SUCCESS)


if __name__ == "__main__":
    main()
