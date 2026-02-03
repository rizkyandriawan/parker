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
    description: "Main dashboard"  # deskripsi untuk manifest
    auth: true                   # requires authentication
    method: POST                 # HTTP method (default: GET)
    data:                        # POST body (JSON)
      key: value
    headers:                     # custom headers
      Authorization: "Bearer xxx"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | yes | URL to capture |
| `name` | string | no | Custom filename (auto dari URL path kalau kosong) |
| `description` | string | no | Deskripsi, masuk ke manifest.json |
| `auth` | boolean | no | Set `true` kalau butuh login dulu |
| `method` | string | no | HTTP method: GET (default) atau POST |
| `data` | object/string | no | POST body, otomatis jadi JSON kalau object |
| `headers` | object | no | Custom HTTP headers |

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

Selector menggunakan format CSS selector atau Playwright selector.

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
  # Public pages (no auth)
  - http://localhost:3000
  - http://localhost:3000/about
  - http://localhost:3000/pricing

  # Protected pages (need auth)
  - url: http://localhost:3000/dashboard
    auth: true
    name: dashboard
    description: "User dashboard"

  - url: http://localhost:3000/settings
    auth: true
    name: settings

  # POST request
  - url: http://localhost:3000/api/report/preview
    method: POST
    data:
      type: "monthly"
      format: "html"
    name: report-preview

  # POST with auth
  - url: http://localhost:3000/admin/stats
    auth: true
    method: POST
    data:
      period: "30d"
    headers:
      X-Admin: "true"
    name: admin-stats
    description: "Admin statistics page"
```

## Output

Filename auto-generated dari URL:

```
http://localhost:3000           → localhost-3000.png
http://localhost:3000/dashboard → localhost-3000-dashboard.png
http://localhost:3000/users/123 → localhost-3000-users-123.png
```

Kalau ada query params, ditambah hash:

```
http://localhost:3000/users?tab=active → localhost-3000-users-123456.png
```

Override dengan `name` field untuk custom filename.
