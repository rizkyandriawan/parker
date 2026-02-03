# Parker 🕷️

**Parker captures your app's UI as documentation artifacts — not test outputs.**

It shoots the web, takes screenshots, and turns them into something you can write with.

> *Named after Peter Parker's web shooter 🕸️, his camera 📸, and the Parker pen 🖊️.*
> *Web. Screenshots. Documentation.*

---

**Parker is not a testing framework.** It's a documentation tool that happens to use screenshots.

## What It Does

- 📸 Capture screenshots from a list of URLs
- 🔐 Handle authentication (login flows)
- 📱 Multi-device capture (desktop, tablet, mobile)
- ⏳ Wait for dynamic content (SPAs)

**Advanced:**
- 📄 Generate manifest.json (LLM-friendly metadata)
- 🖼️ Generate HTML gallery
- 🚦 CI-friendly exit codes

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

1. Create `urls.yaml`:

```yaml
urls:
  - http://localhost:3000
  - http://localhost:3000/about
  - url: http://localhost:3000/dashboard
    name: dashboard
    description: "Main dashboard page"
```

2. Run:

```bash
python parker.py -c urls.yaml
```

3. Screenshots saved to `./screenshots/`

> ⚠️ **For SPAs or authenticated pages**, use `wait_for` or `auth`. See [Configuration](#configuration).

## Usage

```bash
python parker.py -c <config.yaml> [options]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-c, --config` | YAML config file | (required) |
| `-o, --output` | Output directory | `./screenshots` |
| `--viewport` | Viewport size | `1280x720` |
| `--wait` | Extra wait time (ms) | `0` |
| `--wait-for` | Wait for CSS selector | - |
| `--full-page` | Full page screenshot | `false` |
| `--manifest` | Generate manifest.json | `false` |
| `--html` | Generate HTML gallery | `false` |

```bash
# Basic
python parker.py -c urls.yaml

# SPA with element wait
python parker.py -c urls.yaml --wait-for "#app"

# Full output
python parker.py -c urls.yaml --full-page --html --manifest
```

## Configuration

See **[CONFIG.md](CONFIG.md)** for full reference.

### Basic

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
    description: "Analytics dashboard"
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
    auth: true                       # needs login
```

### Multi-Device

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

Auto-named from URL:

```
http://localhost:3000/dashboard → localhost-3000-dashboard.png
```

### Manifest (`--manifest`)

JSON with metadata — designed to be easy to feed into documentation workflows:

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "screenshots": [
    {
      "url": "http://localhost:3000/dashboard",
      "filename": "dashboard.png",
      "title": "Dashboard - MyApp",
      "page_description": "View your analytics",
      "hash": "a1b2c3d4e5f6",
      "description": "Main dashboard"
    }
  ]
}
```

### HTML Gallery (`--html`)

Interactive gallery: thumbnails, fullscreen view, auth/device badges.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All captured |
| `1` | Partial (some failed) |
| `2` | Critical error |

## Use Cases

### 📝 Documentation Generation (Primary)

This is what Parker is built for:

```bash
python parker.py -c docs-urls.yaml --manifest --html

# manifest.json + screenshots → feed to LLM or doc generator
```

### Secondary: Visual Regression

```bash
python parker.py -c urls.yaml -o ./baseline --manifest
python parker.py -c urls.yaml -o ./current --manifest
# Compare hashes
```

### Secondary: CI/CD

```bash
python parker.py -c urls.yaml --manifest
if [ $? -eq 2 ]; then exit 1; fi
```

## License

MIT
