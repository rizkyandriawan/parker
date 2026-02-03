# Parker Config Spec

YAML configuration file untuk Parker.

## Structure

```yaml
auth:        # optional - authentication config
  url: ...
  steps: [...]

urls:        # required - list of URLs to capture
  - ...
```

## URLs

List of URLs bisa dalam 2 format:

### Simple String

```yaml
urls:
  - http://localhost:3000
  - http://localhost:3000/about
```

### Object dengan Options

```yaml
urls:
  - url: http://localhost:3000/dashboard
    name: dashboard              # custom filename (tanpa .png)
    description: "Main dashboard"  # deskripsi untuk manifest/LLM context
    auth: true                   # requires authentication
    wait_for: "#app"             # wait for element before capture
    wait: 2000                   # extra wait time (ms)
    method: POST                 # HTTP method (default: GET)
    data:                        # POST body (JSON)
      key: value
    headers:                     # custom headers
      Authorization: "Bearer xxx"
    devices:                     # capture multiple viewports
      - desktop
      - mobile
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | URL to capture |
| `name` | string | no | Custom filename (auto dari URL path kalau kosong) |
| `description` | string | no | Deskripsi, masuk ke manifest (untuk LLM context) |
| `auth` | boolean | no | Set `true` kalau butuh login dulu |
| `wait_for` | string | no | CSS selector, tunggu element muncul sebelum capture |
| `wait` | number | no | Extra wait time dalam ms setelah page load |
| `method` | string | no | HTTP method: GET (default) atau POST |
| `data` | object/string | no | POST body, otomatis jadi JSON kalau object |
| `headers` | object | no | Custom HTTP headers |
| `devices` | array | no | List devices untuk multi-viewport capture |

## Devices

Device presets yang tersedia:

| Name | Viewport | Scale | Mobile |
|------|----------|-------|--------|
| `desktop` | 1280x720 | 1x | no |
| `laptop` | 1440x900 | 1x | no |
| `tablet` | 768x1024 | 2x | yes |
| `mobile` | 375x667 | 2x | yes |

Contoh:

```yaml
urls:
  - url: http://localhost:3000/landing
    devices:
      - desktop
      - mobile
```

Output: `landing-desktop.png`, `landing-mobile.png`

## Auth

Config untuk authentication. Diperlukan kalau ada URL dengan `auth: true`.

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
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | Login page URL |
| `steps` | array | yes | List of auth steps |

### Auth Steps

| Step | Description | Example |
|------|-------------|---------|
| `fill` | Isi input field (clear dulu) | `fill: "#email"` + `value: "x"` |
| `type` | Ketik ke input (dengan key events) | `type: "#search"` + `value: "x"` |
| `click` | Klik element | `click: "button.submit"` |
| `press` | Tekan keyboard key | `press: "Enter"` |
| `wait` | Tunggu N milliseconds | `wait: 2000` |
| `wait_for` | Tunggu element muncul | `wait_for: ".dashboard"` |
| `goto` | Navigate ke URL | `goto: "http://..."` |

## CLI Options

```bash
parker -c urls.yaml [options]
```

| Flag | Description | Default |
|------|-------------|---------|
| `-c, --config` | YAML config file | (required) |
| `-o, --output` | Output directory | `./screenshots` |
| `--viewport` | Default viewport (WIDTHxHEIGHT) | `1280x720` |
| `--wait` | Global extra wait (ms) | `0` |
| `--wait-for` | Global wait selector | - |
| `--full-page` | Capture full scrollable page | `false` |
| `--manifest` | Generate manifest.json | `false` |
| `--html` | Generate HTML gallery | `false` |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All screenshots captured successfully |
| `1` | Partial success (some failed) |
| `2` | Critical error (auth failed, no URLs, etc) |

## Output

### Filenames

Auto-generated dari URL:

```
http://localhost:3000           → localhost-3000.png
http://localhost:3000/dashboard → localhost-3000-dashboard.png
```

Dengan devices:

```
localhost-3000-dashboard.png          # default viewport
localhost-3000-dashboard-mobile.png   # mobile device
localhost-3000-dashboard-tablet.png   # tablet device
```

### Manifest (manifest.json)

```json
{
  "generated_at": "2024-01-15T10:30:00",
  "config": "urls.yaml",
  "output_dir": "./screenshots",
  "viewport": "1280x720",
  "screenshots": [
    {
      "url": "http://localhost:3000/dashboard",
      "file": "screenshots/dashboard.png",
      "filename": "dashboard.png",
      "status": "ok",
      "auth": true,
      "device": null,
      "title": "Dashboard - MyApp",
      "page_description": "View your analytics and metrics",
      "hash": "a1b2c3d4e5f6",
      "description": "Main dashboard"
    }
  ]
}
```

Fields per screenshot:

| Field | Description |
|-------|-------------|
| `url` | Source URL |
| `file` | Full path to screenshot |
| `filename` | Filename only |
| `status` | `ok`, `error`, `timeout`, `network_error` |
| `auth` | Whether auth was required |
| `device` | Device name jika multi-device, null jika default |
| `title` | Page title dari `<title>` tag |
| `page_description` | Auto-extracted dari meta description atau first paragraph |
| `hash` | MD5 hash (12 char) untuk diff detection |
| `description` | Custom description dari config |
| `error` | Error message jika status bukan `ok` |

### HTML Report (index.html)

Gallery view dengan:
- Thumbnail grid
- Click untuk fullscreen
- Badge untuk AUTH dan device type
- Summary (captured vs failed)

## Full Example

```yaml
auth:
  url: http://localhost:3000/login
  steps:
    - fill: "#email"
      value: "admin@example.com"
    - fill: "#password"
      value: "password123"
    - click: "button[type=submit]"
    - wait_for: ".dashboard-header"

urls:
  # Public pages
  - http://localhost:3000
  - http://localhost:3000/about
  - http://localhost:3000/pricing

  # Protected pages
  - url: http://localhost:3000/dashboard
    auth: true
    wait_for: "#charts-loaded"
    name: dashboard
    description: "Analytics dashboard with real-time charts"

  # Multi-device responsive
  - url: http://localhost:3000/landing
    name: landing
    description: "Landing page hero section"
    devices:
      - desktop
      - tablet
      - mobile

  # SPA with loading state
  - url: http://localhost:3000/reports
    auth: true
    wait_for: ".report-table"
    wait: 1000
    name: reports
    description: "Monthly reports with data tables"

  # POST request
  - url: http://localhost:3000/preview
    method: POST
    data:
      template: "invoice"
      id: 123
    name: invoice-preview
    description: "Invoice preview from template"
```

Usage:

```bash
# Basic
parker -c urls.yaml

# Full output with HTML gallery
parker -c urls.yaml -o ./docs/screenshots --html --full-page

# CI mode with wait
parker -c urls.yaml --wait-for "#app" --manifest
echo "Exit code: $?"  # 0=success, 1=partial, 2=failure
```
