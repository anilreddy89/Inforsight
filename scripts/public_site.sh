#!/bin/zsh
# Start, stop, or inspect the Mac-hosted public preview without deleting data.
set -euo pipefail

cd "${0:A:h}/.."

host='https://inforsight.aniljonnala.fyi'
tunnel_plist='/Library/LaunchDaemons/com.cloudflare.cloudflared.plist'
tunnel_target='system/com.cloudflare.cloudflared'
maintenance_plist="$HOME/Library/LaunchAgents/com.inforsight.inforsight-public.maintenance.plist"
maintenance_target="gui/$(id -u)/com.inforsight.inforsight-public.maintenance"

loaded() {
  launchctl print "$1" >/dev/null 2>&1
}

case "${1:-}" in
  stop)
    # Disable launchd jobs as well as unloading them so a reboot stays offline.
    sudo launchctl disable "$tunnel_target"
    if loaded "$tunnel_target"; then
      sudo launchctl bootout system "$tunnel_plist"
    fi
    launchctl disable "$maintenance_target"
    if loaded "$maintenance_target"; then
      launchctl bootout "gui/$(id -u)" "$maintenance_plist"
    fi
    python3 scripts/public_demo.py down
    print 'Public demo stopped. Docker volumes and secrets were preserved.'
    ;;
  start)
    docker info >/dev/null
    test -f "$tunnel_plist"
    test -f "$maintenance_plist"
    sudo -v
    python3 scripts/public_demo.py up --no-build
    launchctl enable "$maintenance_target"
    if ! loaded "$maintenance_target"; then
      launchctl bootstrap "gui/$(id -u)" "$maintenance_plist"
    fi
    sudo launchctl enable "$tunnel_target"
    if ! loaded "$tunnel_target"; then
      sudo launchctl bootstrap system "$tunnel_plist"
    fi
    for attempt in {1..15}; do
      if curl --fail --silent --output /dev/null --max-time 5 "$host/api/v1/demo/session"; then
        print "Public demo ready: $host"
        exit 0
      fi
      sleep 2
    done
    print -u2 "Services started, but $host did not pass the public health check."
    exit 1
    ;;
  status)
    print "Tunnel: $([[ -f "$tunnel_plist" ]] && loaded "$tunnel_target" && print loaded || print stopped)"
    print "Maintenance: $([[ -f "$maintenance_plist" ]] && loaded "$maintenance_target" && print loaded || print stopped)"
    if docker info >/dev/null 2>&1; then
      python3 scripts/public_demo.py status
    else
      print 'Docker: unavailable'
    fi
    for attempt in {1..3}; do
      if curl --fail --silent --output /dev/null --max-time 5 "$host/api/v1/demo/session"; then
        print "Public URL: ready ($host)"
        exit 0
      fi
      sleep 1
    done
    print "Public URL: unavailable ($host)"
    ;;
  *)
    print -u2 'Usage: scripts/public_site.sh {start|stop|status}'
    exit 2
    ;;
esac
