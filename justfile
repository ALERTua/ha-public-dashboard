# Windows local testing commands for Public Dashboard
# https://github.com/casey/just
set dotenv-load

# Set shell for non-Windows OSs:
set shell := ["powershell", "-c"]

# Set shell for Windows OSs:
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# Frontend project path alias
frontend_path := "public-dashboard/rootfs/var/www"
backend_path := "public-dashboard/rootfs/app"

# === FRONTEND COMMANDS ===

# Install frontend dependencies
fe-install:
    npm --prefix {{frontend_path}} install

# Start frontend development server
fe:
    npm --prefix {{frontend_path}} run dev

# Build frontend for production
fe-build:
    if (Test-Path "{{frontend_path}}/dist") { Remove-Item -Recurse -Force "{{frontend_path}}/dist" }
    npm --prefix {{frontend_path}} run build

# Clean node_modules and reinstall
fe-clean:
    if (Test-Path "{{frontend_path}}/node_modules") { Remove-Item -Recurse -Force "{{frontend_path}}/node_modules" }
    just fe-install

# Upgrade frontend npm packages to their latest versions and write them to package.json
fe-upgrade:
    npx --yes npm-check-updates --cwd {{frontend_path}} -u
    just fe-install

# === BACKEND COMMANDS ===

# Start backend with development mode (uses .env)
be:
    uv run python {{backend_path}}/addon_main.py

# Run pre-commit
lint:
    uv run ruff format .
    uv run ruff check --fix

pre:
    uv run pre-commit run --all-files

pre-update:
    uv run pre-commit autoupdate

# Install backend dependencies
be-install:
    uv --directory {{backend_path}} sync --dev

be-install-upgrade:
    uv --directory {{backend_path}} sync --dev --upgrade

# === COMBINED COMMANDS ===

# Combined setup command
start: fe-clean fe-install fe-build be-install
    Write-Host "Run 'just be' in one terminal and 'just fe' in another"

# === UTILITY COMMANDS ===

# Update version across all files
version VERSION:
    uv run python script/update_version.py {{VERSION}}
    just fe-install
    just fe-build
    just lint
    just pre || just pre

# Show available commands
help:
    @just --list
