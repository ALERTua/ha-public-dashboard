# Configuration

Add-on configuration:

```yaml
admin_password: admin123
log_level: info
ssl: false
certfile: fullchain.pem
keyfile: privkey.pem
```

## Access Methods

The Public Dashboard add-on supports multiple access methods:

### 1. Home Assistant Ingress (Recommended)
- Access via Home Assistant sidebar panel
- Automatic authentication with Home Assistant
- No additional configuration required
- Most secure option

### 2. Direct Port Access
- Access via `http://YOUR_HA_IP:8000`
- Enable port 8000 in the "Network" section of the add-on configuration
- Useful for public dashboards, kiosks, or direct access
- No Home Assistant authentication required

### 3. Reverse Proxy
- Point your reverse proxy to `http://YOUR_HA_IP:8000`
- Enable port 8000 in the "Network" section of the add-on configuration
- Supports external domain access
- Compatible with nginx, Traefik, Caddy, etc.

## Configuration Options

### Option: `admin_password` (required)

The password for the admin user who can manage dashboard entities and controls.

**Note**: This should be a strong, unique password.

### Option: `log_level` (optional)

Controls the level of log output the add-on will produce. Valid options are:

- `trace`: Shows every detail, very verbose
- `debug`: Shows detailed debug information
- `info`: Normal (default) log level
- `notice`: Show only notices and warnings
- `warning`: Show only warnings and errors
- `error`: Show only errors
- `fatal`: Show only fatal errors

### Option: `ssl` (optional)

Enables/Disables SSL (HTTPS) for the add-on. Set to `true` to enable.

**Note**: SSL is handled by Home Assistant's ingress by default.

### Option: `certfile` (optional)

The certificate file to use for SSL. Only used when `ssl` is enabled.

**Note**: The file MUST be stored in `/ssl/`, which is the default for Home Assistant.

### Option: `keyfile` (optional)

The private key file to use for SSL. Only used when `ssl` is enabled.

**Note**: The file MUST be stored in `/ssl/`, which is the default for Home Assistant.

## Example configurations

### Basic configuration (Ingress only)

```yaml
admin_password: mySecurePassword123
```

### Configuration with direct port access

```yaml
admin_password: mySecurePassword123
# Enable port 8000 in Network section
```

### Advanced configuration with SSL

```yaml
admin_password: mySecurePassword123
log_level: debug
ssl: true
certfile: fullchain.pem
keyfile: privkey.pem
```

### Minimal logging

```yaml
admin_password: mySecurePassword123
log_level: error
```
