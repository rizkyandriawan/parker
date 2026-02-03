# Parker

Auto screenshot tool for documentation. Captures screenshots from a list of URLs using Playwright.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python parker.py -c urls.yaml
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-c, --config` | YAML config file (required) | - |
| `-o, --output` | Output directory | `./screenshots` |
| `--viewport` | Viewport size (WIDTHxHEIGHT) | `1280x720` |
| `--wait` | Extra wait time in ms after page load | `0` |
| `--full-page` | Capture full scrollable page | `false` |
| `--manifest` | Generate manifest.json | `false` |

### Examples

```bash
# Basic
python parker.py -c urls.yaml

# Custom output and viewport
python parker.py -c urls.yaml -o ./docs/images --viewport 1920x1080

# Full page screenshots with manifest
python parker.py -c urls.yaml --full-page --manifest
```

## Config Format

```yaml
urls:
  # Simple URL - filename auto-generated from path
  - http://localhost:3000/dashboard

  # With metadata
  - url: http://localhost:3000/users
    name: user-list                    # custom filename
    description: "List of all users"   # included in manifest

  # POST request
  - url: http://localhost:3000/api/preview
    method: POST
    data:
      template: "invoice"
      id: 123
    name: invoice-preview

  # POST with custom headers
  - url: http://localhost:3000/admin/report
    method: POST
    data:
      report_type: "summary"
    headers:
      Authorization: "Bearer token"
    name: admin-report
```

## Output

Screenshots are saved to the output directory with auto-generated filenames based on URL path:

```
http://localhost:3000/dashboard  →  localhost-3000-dashboard.png
http://localhost:3000/users      →  localhost-3000-users.png
```

With `--manifest` flag, a `manifest.json` is generated:

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "screenshots": [
    {
      "url": "http://localhost:3000/dashboard",
      "file": "screenshots/localhost-3000-dashboard.png",
      "filename": "localhost-3000-dashboard.png",
      "status": "ok",
      "description": "Main dashboard"
    }
  ]
}
```

## License

MIT
