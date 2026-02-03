# Parker

Auto screenshot tool for documentation. Captures screenshots from a list of URLs using Playwright.

### Why "Parker"? 🕷️

You know Peter Parker — the guy who swings around New York with his *web shooter* 🕸️, capturing whatever he needs. That's what this tool does: it captures the **web** 🌐.

But Peter Parker is also a photographer 📸. He doesn't just swing around; he takes photos — sharp, well-timed shots that tell a story. That's exactly what Parker (this tool) does: it takes **screenshots** of your app, one page at a time.

And then there's the Parker pen 🖊️ — a classic tool for **writing**. Because at the end of the day, those screenshots aren't just images. They're the foundation for your documentation 📝.

*Web shooter. Photographer. Pen. Parker.* ✨

**Key Features:**
- YAML-based configuration
- Authentication support (login flows)
- Multi-device capture (desktop, tablet, mobile)
- Wait for elements (for SPAs/dynamic content)
- HTML gallery output
- Manifest with rich metadata for LLM-powered doc generation
- CI-friendly exit codes

## Installation

```bash
git clone https://github.com/rizkyandriawan/parker.git
cd parker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Quick Start

1. Create a config file `urls.yaml`:

```yaml
urls:
  - http://localhost:3000
  - http://localhost:3000/about
  - url: http://localhost:3000/dashboard
    name: dashboard
    description: "Main dashboard page"
```

2. Run Parker:

```bash
python parker.py -c urls.yaml
```

3. Screenshots saved to `./screenshots/`

## Usage

```bash
python parker.py -c <config.yaml> [options]
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-c, --config` | YAML config file (required) | - |
| `-o, --output` | Output directory | `./screenshots` |
| `--viewport` | Viewport size (WIDTHxHEIGHT) | `1280x720` |
| `--wait` | Extra wait time in ms | `0` |
| `--wait-for` | Wait for CSS selector | - |
| `--full-page` | Capture full scrollable page | `false` |
| `--manifest` | Generate manifest.json | `false` |
| `--html` | Generate HTML gallery | `false` |

### Examples

```bash
# Basic
python parker.py -c urls.yaml

# Custom output directory
python parker.py -c urls.yaml -o ./docs/images

# Wait for element before capture (useful for SPAs)
python parker.py -c urls.yaml --wait-for "#app-loaded"

# Full page with HTML gallery
python parker.py -c urls.yaml --full-page --html

# CI mode with manifest
python parker.py -c urls.yaml --manifest
echo "Exit code: $?"
```

## Configuration

See **[CONFIG.md](CONFIG.md)** for full configuration reference.

### Basic Config

```yaml
urls:
  - http://localhost:3000
  - http://localhost:3000/about
```

### With Metadata

```yaml
urls:
  - url: http://localhost:3000/dashboard
    name: dashboard
    description: "Analytics dashboard with charts"
    wait_for: "#charts-loaded"
```

### With Authentication

```yaml
auth:
  url: http://localhost:3000/login
  steps:
    - fill: "#email"
      value: "admin@example.com"
    - fill: "#password"
      value: "secret"
    - click: "button[type=submit]"
    - wait: 2000

urls:
  - http://localhost:3000           # public
  - url: http://localhost:3000/dashboard
    auth: true                       # requires login
```

### Multi-Device Capture

```yaml
urls:
  - url: http://localhost:3000/landing
    name: landing
    devices:
      - desktop   # 1280x720
      - tablet    # 768x1024
      - mobile    # 375x667
```

Output: `landing-desktop.png`, `landing-tablet.png`, `landing-mobile.png`

### POST Requests

```yaml
urls:
  - url: http://localhost:3000/api/preview
    method: POST
    data:
      template: "invoice"
      id: 123
    name: invoice-preview
```

## Output

### Screenshots

Auto-named from URL path:

```
http://localhost:3000/dashboard → localhost-3000-dashboard.png
http://localhost:3000/users     → localhost-3000-users.png
```

### Manifest (`--manifest`)

JSON file with rich metadata:

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "viewport": "1280x720",
  "screenshots": [
    {
      "url": "http://localhost:3000/dashboard",
      "filename": "dashboard.png",
      "status": "ok",
      "title": "Dashboard - MyApp",
      "page_description": "View your analytics and metrics",
      "hash": "a1b2c3d4e5f6",
      "description": "Main dashboard"
    }
  ]
}
```

**Manifest fields for LLM context:**
- `title` - Page title from `<title>` tag
- `page_description` - Auto-extracted from meta description or first paragraph
- `description` - Custom description from config
- `hash` - For diff detection in CI

### HTML Gallery (`--html`)

Interactive gallery with:
- Thumbnail grid
- Click to view fullscreen
- Auth/device badges
- Success/failure summary

## Exit Codes

| Code | Meaning | CI Action |
|------|---------|-----------|
| `0` | All screenshots captured | Pass |
| `1` | Partial success (some failed) | Warning |
| `2` | Critical error | Fail |

## Use Cases

### Documentation Generation

```bash
# Capture screenshots
python parker.py -c docs-urls.yaml --manifest --html

# Feed to LLM for doc generation
# manifest.json contains: URLs, titles, descriptions, screenshots
```

### Visual Regression Testing

```bash
# Capture baseline
python parker.py -c urls.yaml -o ./baseline --manifest

# Capture current
python parker.py -c urls.yaml -o ./current --manifest

# Compare hashes in manifest.json
```

### CI/CD Integration

```bash
#!/bin/bash
python parker.py -c urls.yaml --manifest
exit_code=$?

if [ $exit_code -eq 0 ]; then
  echo "All screenshots captured"
elif [ $exit_code -eq 1 ]; then
  echo "Warning: Some screenshots failed"
else
  echo "Error: Critical failure"
  exit 1
fi
```

## License

MIT
