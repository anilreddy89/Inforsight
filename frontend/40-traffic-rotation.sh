#!/bin/sh
# nginx reopens the renamed file after rotation; never truncate a file being read.
# Only the frontend writes here. The analytics container mounts this volume read-only.
mkdir -p /var/log/inforsight
chmod 755 /var/log/inforsight
(
    while sleep 60; do
        logrotate -s /var/log/inforsight/rotation.state /etc/traffic-logrotate.conf
    done
) &
