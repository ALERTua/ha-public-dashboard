# Public Dashboard Add-on Repository

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

Home Assistant add-on repository for Public Dashboard.

## Add-ons

This repository contains the following add-on:

### [📊 Public Dashboard](./public-dashboard)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

A secure, dynamic dashboard for building systems with multi-role admin entity management.

## Installation

Adding this add-ons repository to your Home Assistant instance is pretty straightforward. In the Home Assistant add-on store, a possibility to add a repository is provided.

Use the following URL to add this repository:

```txt
https://github.com/ALERTua/ha-public-dashboard
```

## Add-ons provided by this repository

### Public Dashboard

A mobile-first dashboard with advanced role-based access control that allows:

#### Public Access
- View building status without authentication
- Access to user-configured entities and sensors
- Real-time status updates every 30 seconds

#### Role-Based Access Control
- **User Role**: Public access to configured entities only
- **Admin Role**: Full access to admin dashboard, entity control, and basic management
- **Superadmin Role**: Complete system management including entity configuration and link management

#### Admin Features
- Toggle controllable entities (switches, lights, input_boolean)
- View admin-only entities with enhanced controls
- Search and manage Home Assistant entities
- Add/remove entities from user and admin dashboards
- Manage custom links and information sections

#### Security Features
- JWT-based authentication
- Role-based API endpoints
- Secure password hashing (SHA256)
- Configurable admin and superadmin passwords

## Access Methods

The add-on supports multiple access methods:

### 1. Home Assistant Ingress (Recommended)
- Access via Home Assistant sidebar panel
- Automatic authentication with Home Assistant
- No additional configuration required

### 2. Direct Port Access
- Access via `http://YOUR_HA_IP:8000`
- Useful for public dashboards or kiosks
- Enable port in add-on configuration

### 3. Reverse Proxy
- Point your reverse proxy to `http://YOUR_HA_IP:8000`
- Supports external domain access
- Compatible with nginx, Traefik, etc.

## Configuration

### Basic Configuration
```yaml
admin_password: "your_admin_password"
superadmin_password: "your_superadmin_password"
log_level: "info"
ssl: false
```

### Default Credentials
- **Admin**: username `admin`, password `admin123`
- **Superadmin**: username `superadmin`, password `superadmin123`

### Environment Variables
- `ADMIN_PASSWORD`: Admin password (default: admin123)
- `SUPERADMIN_PASSWORD`: Superadmin password (default: superadmin123)
- `HA_URL`: Home Assistant URL (default: http://supervisor/core)
- `JWT_EXPIRE_HOURS`: JWT token expiration (default: 24 hours)

## Development

### Local Development Setup
```bash
# Install frontend dependencies
just fe-install

# Start frontend development server
just fe-dev

# Build for production
just fe-build

# Combined setup and start
just start
```

### Backend Development
```bash
# Install backend dependencies
just be-install

# Start backend server
just be-start

# Start with development mode
just be-dev
```

### Available Commands
- `just start`: Complete setup with frontend and backend
- `just fe-clean`: Clean and reinstall frontend dependencies
- `just version <VERSION>`: Update version across all files
- `just lint`: Run pre-commit checks

## Support

Got questions?

You have several options to get them answered:

- The [Home Assistant Community Forum][forum]
- The Home Assistant [Discord Chat Server][discord] for general Home Assistant discussions and questions
- Join the [Reddit subreddit][reddit] in [/r/homeassistant][reddit]

You could also [open an issue here][issue] on GitHub.

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We have set up a separate document containing our
[contribution guidelines](CONTRIBUTING.md).

Thank you for being involved! 😍

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[commits-shield]: https://img.shields.io/github/commit-activity/y/ALERTua/ha-public-dashboard.svg
[commits]: https://github.com/ALERTua/ha-public-dashboard/commits/main
[discord]: https://discord.gg/c5DvZ4e
[forum]: https://community.home-assistant.io
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
[issue]: https://github.com/ALERTua/ha-public-dashboard/issues
[license-shield]: https://img.shields.io/github/license/ALERTua/ha-public-dashboard.svg
[reddit]: https://reddit.com/r/homeassistant
[releases-shield]: https://img.shields.io/github/release/ALERTua/ha-public-dashboard.svg
[releases]: https://github.com/ALERTua/ha-public-dashboard/releases
