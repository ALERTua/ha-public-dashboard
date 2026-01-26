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
        nginx

# Copy root filesystem
COPY rootfs /

# Install Python requirements
RUN pip3 install --no-cache-dir -r /app/requirements.txt