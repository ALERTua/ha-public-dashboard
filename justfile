# Windows local testing commands for Public Dashboard
# https://github.com/casey/just
set shell := ["cmd.exe", "/c"]
set dotenv-load

# === FRONTEND COMMANDS ===

# Install frontend dependencies
fe-install:
    pushd public-dashboard\rootfs\var\www && npm install & popd

# Start frontend development server
fe-dev:
    pushd public-dashboard\rootfs\var\www && npm start & popd

# Build frontend for production
fe-build:
    pushd public-dashboard\rootfs\var\www && npm run build & popd

# Clean node_modules and reinstall
fe-clean:
    rmdir /s /q public-dashboard\rootfs\var\www\node_modules 2>nul || echo "node_modules not found"
    del public-dashboard\rootfs\var\www\package-lock.json 2>nul || echo "package-lock.json not found"
    just fe-install

# Test frontend build
fe-test: fe-build
    @echo "Frontend build completed successfully"

# === BACKEND COMMANDS ===

# Install backend dependencies
be-install:
    uv sync --directory public-dashboard\rootfs\app

# Start backend server
be-start:
    uv run --directory public-dashboard\rootfs\app addon_main.py

# Start backend with development mode (uses .env)
be-dev:
    uv run --directory public-dashboard\rootfs\app addon_main.py

# === COMBINED COMMANDS ===

# Start both frontend and backend (requires two terminals)
start: fe-install be-install
    @echo "Run 'just be-start' in one terminal and 'just fe-dev' in another"

# === UTILITY COMMANDS ===

# Update version across all files
version VERSION:
    uv run python scripts\update_version.py {{VERSION}}

# Show available commands
help:
    @just --list