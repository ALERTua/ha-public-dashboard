# Windows local testing commands for Public Dashboard
# https://github.com/casey/just
set shell := ["cmd.exe", "/c"]
set dotenv-load

# === FRONTEND COMMANDS ===

# Install frontend dependencies
fe-install:
    npm --prefix public-dashboard/rootfs/var/www install

# Start frontend development server
fe-dev:
    npm --prefix public-dashboard/rootfs/var/www start

# Build frontend for production
fe-build:
    npm --prefix public-dashboard/rootfs/var/www run build

# Build frontend for production (Windows with PUBLIC_URL)
fe-build-win:
    rmdir /s /q public-dashboard\rootfs\var\www\build 2>nul
    set PUBLIC_URL=.
    npm --prefix public-dashboard/rootfs/var/www run build

# Clean node_modules and reinstall
fe-clean:
    rmdir /s /q public-dashboard\rootfs\var\www\node_modules 2>nul
    just fe-install

# Test frontend build
fe-test: fe-build
    @echo "Frontend build completed successfully"

# === BACKEND COMMANDS ===

# Install backend dependencies
be-install:
    uv --directory public-dashboard/rootfs/app sync

# Start backend server
be-start:
    uv run public-dashboard/rootfs/app/addon_main.py

# Start backend with development mode (uses .env)
be-dev:
    uv run python public-dashboard/rootfs/app/addon_main.py

# Run pre-commit
lint:
    uv run pre-commit run --all-files

# Install pre-commit hooks
be-setup:
    uv --directory public-dashboard/rootfs/app sync --dev

# === COMBINED COMMANDS ===

# Combined setup command
start: fe-clean fe-install fe-build-win be-setup
    @echo Run 'just be-start' in one terminal and 'just fe-dev' in another

# === UTILITY COMMANDS ===

# Update version across all files
version VERSION:
    uv run python scripts/update_version.py {{VERSION}}

# Show available commands
help:
    @just --list
