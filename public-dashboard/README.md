# Public Dashboard - Home Assistant Addon

A secure, dynamic dashboard for building systems with admin entity management.

## Features

- 🏢 **Dynamic Entity Management** - Admins can add any HA entity to dashboards
- 📱 **Mobile-First Design** - Optimized for phones and tablets  
- 🔓 **Public Access** - View dashboard without login
- 🔐 **Admin Controls** - Secure entity management and controls
- 🔗 **Links Section** - Add custom links with optional URLs
- 🎨 **Clean Interface** - Ukrainian interface with emoji icons

## Installation

### Method 1: Add Repository (Recommended)

1. In Home Assistant: **Supervisor** → **Add-on Store**
2. Click **⋮** → **Repositories** 
3. Add: `https://github.com/ALERTua/ha-public-dashboard`
4. Install "Public Dashboard"

### Method 2: Manual Installation

1. Copy `addon/building-dashboard` to `/addons/`
2. Restart Supervisor
3. Install from Add-on Store

## Configuration

```yaml
admin_password: "your-secure-password"
```

**Note**: JWT secrets are auto-generated. No manual token setup required.

## Usage

1. **Start addon** and enable "Show in sidebar"
2. **View dashboard** - No login required for public access
3. **Admin login** - Use configured password for entity management
4. **Add entities** - Click "Редагувати картки" to add HA entities
5. **Add links** - Click "Посилання" to add custom links

### Dashboard Sections

- **📊 Мешканець** - Public entities (sensors, status)
- **🔧 Адмін** - Admin entities (controls, switches)  
- **🔗 Посилання** - Custom links and information

## Security

- ✅ Uses HA supervisor token (no manual setup)
- ✅ Entity whitelisting (only added entities accessible)
- ✅ Admin authentication for controls
- ✅ Action logging for all admin operations
- ✅ Auto-generated JWT secrets

## Troubleshooting

### Addon Won't Start
- Check addon logs for errors
- Verify admin password is set
- Ensure HA is running

### No Entities Showing
- Login as admin and add entities via "Редагувати картки"
- Verify entities exist in HA Developer Tools

### Can't Login
- Check admin_password in addon configuration
- View addon logs for authentication errors

## Development

The addon automatically:
- Generates secure JWT tokens
- Connects to HA via supervisor token
- Creates empty dashboard config
- Serves on HA ingress (no external ports needed)

## Support

- Check addon logs: Supervisor → Public Dashboard → Logs
- GitHub Issues: [Report problems](https://github.com/ALERTua/ha-public-dashboard/issues)
- HA Community: [Home Assistant Community](https://community.home-assistant.io)