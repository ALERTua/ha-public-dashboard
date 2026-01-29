# https://developers.home-assistant.io/docs/add-ons/configuration#add-on-dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

# Execute during the build of the image
ARG TEMPIO_VERSION BUILD_ARCH
RUN \
    curl -sSLf -o /usr/bin/tempio \
    "https://github.com/home-assistant/tempio/releases/download/${TEMPIO_VERSION}/tempio_${BUILD_ARCH}" \
    && chmod a+x /usr/bin/tempio

# Install requirements for add-on
RUN \
    apk add --no-cache \
        python3 \
        py3-pip \
        nginx \
        nodejs \
        npm

# Copy root filesystem
COPY rootfs /

# Build React app
WORKDIR /var/www
RUN npm install && npm run build

# Set execute permissions for service scripts
RUN chmod +x /etc/services.d/*/run

# Install Python requirements
RUN pip3 install --no-cache-dir --break-system-packages -r /app/requirements.txt

WORKDIR /