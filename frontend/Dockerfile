FROM node:22-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Track nginx's supported stable branch; versioned branch tags stop receiving
# updates about a year after release. `make public-rebuild` pulls the latest.
FROM nginx:stable-alpine
LABEL com.inforsight.traffic.version="2"
RUN apk add --no-cache logrotate && mkdir -p /var/log/inforsight
COPY frontend/traffic-logrotate.conf /etc/traffic-logrotate.conf
COPY frontend/40-traffic-rotation.sh /docker-entrypoint.d/40-traffic-rotation.sh
RUN chmod +x /docker-entrypoint.d/40-traffic-rotation.sh
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1
