# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
# https://contributors.home-assistant.io/blog/2026/04/02/builder-migration/
FROM ghcr.io/home-assistant/base:latest

LABEL \
    io.hass.type="addon" \
    io.hass.name="Public Dashboard" \
    io.hass.description="A secure, dynamic dashboard for building systems with admin entity management" \
    io.hass.url="https://github.com/ALERTua/ha-public-dashboard/tree/main/public-dashboard" \
    org.opencontainers.image.title="Public Dashboard" \
    org.opencontainers.image.description="A secure, dynamic dashboard for building systems with admin entity management" \
    org.opencontainers.image.source="https://github.com/ALERTua/ha-public-dashboard" \
    org.opencontainers.image.licenses="MIT"

# Install requirements for add-on
RUN \
    apk add --no-cache \
#        python3 \
        nginx \
        nodejs \
        npm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy root filesystem
COPY rootfs /

# Build React app
WORKDIR /var/www
# Set environment variables for Vite build
ENV VITE_BASE_PATH="/"
ENV VITE_API_URL="."
RUN npm install && npm run build

# Set execute permissions for service scripts
RUN chmod +x /etc/services.d/*/run

# Install Python requirements
ENV \
    UV_NO_DEV=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /app
RUN uv sync --frozen --no-dev

WORKDIR /
