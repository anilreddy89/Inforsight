# Anonymous public visitor preview

The public preview runs the real six-service journey in a separate
`inforsight-public` Docker Compose project. It does not reuse the local
`inforsight-demo` database, Kafka volumes, or development password. The only
published host port is the frontend gateway, bound to `127.0.0.1:3100`.

Internet HTTPS → Cloudflare → outbound `cloudflared` on the Mac → loopback
Nginx/React gateway → private Java control plane → private Kafka, PostgreSQL,
released-model HTTP inference and bounded Python demo runtime.

No paid resource, trial credit, paid plan, charge-enabling upgrade, or cloud VM
is required for this preview. Cloudflare Tunnel is available on the Free plan
and uses outbound connections. The Mac's other ports are not routed by the
tunnel. [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/)

## Availability and cost

The provisioned vendor hosting cost for the local preview is **$0**: no billable
cloud resources were created. No billing invoice was audited. This is not a measurement of the Mac's electric
power consumption or the user's existing internet subscription.

The preview goes offline if the Mac sleeps, loses power/network, Docker stops,
the Compose stack stops, or the tunnel stops. A Quick Tunnel also has no uptime
guarantee, changes hostname on restart, permits up to 200 concurrent requests,
and does not support SSE. The UI uses real HTTP polling, so the SSE limitation
does not change the workflow. It is a preview, not an always-on production
deployment. [Quick Tunnel limits](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)

Restarting a Quick Tunnel changes its hostname. Browser cookies do **not**
transfer to the new hostname, so an old run cannot be resumed there using its
correlation ID alone. This isolation is intentional. Restarting Docker while
the same tunnel URL stays alive preserves the hostname and browser session.
A named tunnel with a stable hostname avoids this address-change limitation.

The current URL is written to
`~/.local/share/inforsight-public/public-url.txt`. The deployment manifest in
the same directory records the commit, dirty paths, Compose digest, model
digest, image IDs/architectures, health and published ports. Run/test evidence
belongs in `artifacts/public-demo/`; the final qualification report records the
actual tested URL and run IDs.

## Public boundary

- The public gateway serves React assets, a minimal health response, and the
  explicit `/api/v1/demo/` session/scenario/run/decision/audit routes.
- A signed, HttpOnly, Secure, SameSite cookie owns each visitor's runs. A
  correlation ID is not authorization. The session lasts at most seven days.
  Keep the same browser session to resume;
  copying a run URL to another browser does not transfer access.
- Mutations require the session's CSRF token. No CORS permission is granted.
- Public visitors can act only as fictional reviewers. Server-side authority
  and external-execution flags remain false. No reset, CRM, telephony, direct
  Java actuator, Python diagnostics, PostgreSQL or Kafka endpoint is routed.
- Fictional source facts, model/rule/allocation evidence, bounded drafts,
  reviewer text and audit receipts are visible only to the owning session.
  Do not enter real policy, customer or contact information.
- Cloudflare terminates HTTPS and forwards traffic to the local gateway;
  it can process request/response traffic. Backend service networking is a
  Docker `internal` network; backend containers have no internet route.

Public Compose sets per-session/overall submissions to 12/120 per hour, polling
to 120/1,200 per minute, retries to 3/30 per hour, decisions to 30/180 per hour,
concurrent runs to 2/8, retained runs to 12/200, and new sessions to 100 per
hour overall. The backend, rather than browser counters, enforces these limits.
The UI preserves existing evidence when capacity or a dependency is unavailable.

Terminal runs expire after 24 hours. An abandoned review becomes expired only
after 48 hours and at least 24 hours without accessing that run; it is retained for
another 24 hours. Waiting/processing runs are not deleted. Audit entries are
deleted with the entire expired run under the protected retention operation,
not edited into a new successful history. Cleanup first verifies the complete
audit and preserves an integrity-failing run for investigation. A minimal
deletion receipt retains the verified head for seven days; it is not a complete
audit export. A purged run cannot be resumed.

Kafka has no unsafe time/size cutoff. Operator maintenance advances its log's
low watermark only before both the earliest retained run's broker evidence
and the consumer's committed offset. It never deletes unconsumed work. A long
retained run can delay physical broker cleanup; monitor disk usage. Kafka can
remove obsolete segments later, so deletion is not an immediate disk-space
guarantee. PostgreSQL retention runs inside the control plane.

## Deploy and update

From the repository root, after local API/browser and public security checks:

```sh
python3 scripts/public_demo.py init
python3 scripts/public_demo.py validate
python3 scripts/public_demo.py up
python3 scripts/public_demo.py maintenance-install
python3 scripts/public_demo.py tunnel-start
python3 scripts/public_demo.py status
```

`init` creates 256-bit random database and signing secrets as mode `0600`
files in a mode `0700` directory outside the repository. It preserves an
existing state directory. Secret values are neither printed nor placed in
container environment variables. A one-shot, no-network operator helper copies
them into the project's Docker secret volume as mode `0400`, owned by Java's
non-root UID/GID. The running services mount this volume read-only. This avoids
Docker Desktop's file-secret ownership mismatch while keeping host files
private. PostgreSQL reads `POSTGRES_PASSWORD_FILE`; Spring reads the same file
through `configtree:/run/secrets/`. Docker's local volume is not an encrypted
secret manager; it is protected by the operator's Docker/host access boundary.
Do not delete or
regenerate the database secret for an existing volume. Rotating the signing
secret invalidates browser sessions; use a deliberate migration/expiry plan.

`maintenance-install` installs an operator-owned macOS LaunchAgent to invoke
offset-aware cleanup every ten minutes while the user is logged in. This is
not a public endpoint. Containers use `restart: unless-stopped`, fixed memory
limits and bounded Docker logs. Automatic container restart still requires a
running Docker daemon. The temporary tunnel process is deliberately not a
permanent login service; run `tunnel-start` again if it exits and share the new
URL. Use a named tunnel for a stable address.

To update, stop public ingress, capture a backup, update to the reviewed commit,
rebuild the isolated project, rerun acceptance, then restart the tunnel:

```sh
python3 scripts/public_demo.py tunnel-stop
python3 scripts/public_demo.py backup "$HOME/inforsight-backups/before-update-2026-10-04"
python3 scripts/public_demo.py up
python3 scripts/public_demo.py manifest
python3 scripts/public_demo.py tunnel-start
```

The backup path must be new. In these example commands change the suffix for
each backup. Keep only the intended recovery window and remove older local
backups explicitly after verifying a newer restore; do not accumulate exports
indefinitely. Do not add the state directory or backups to source control.

The public configuration always uses Secure cookies. Local operator HTTP tests
may explicitly send the test session cookie to the loopback gateway; browser
acceptance uses the public HTTPS origin. Never weaken the public cookie flag
to make a local test pass.

## Backup and restore

The backup command stops all six services for a consistent cold snapshot of
both Kafka and PostgreSQL and resumes them in a `finally` block. In-flight work
resumes from durable state on startup. Visitors see an unavailable response
during this maintenance window. It also copies the matching database/signing
secrets and records SHA-256 checksums. Store this sensitive directory outside
the repository, protect it with FileVault/encrypted offline storage, and do not
upload it to a new paid service.

```sh
python3 scripts/public_demo.py backup "$HOME/inforsight-backups/preview-2026-10-04"
python3 scripts/public_demo.py --state-dir "$HOME/.local/share/inforsight-public-restore" init --project inforsight-public-restore --port 3102
python3 scripts/public_demo.py --state-dir "$HOME/.local/share/inforsight-public-restore" restore "$HOME/inforsight-backups/preview-2026-10-04"
python3 scripts/public_demo.py --state-dir "$HOME/.local/share/inforsight-public-restore" up
python3 scripts/check_public_backup.py --restore-state "$HOME/.local/share/inforsight-public-restore"
```

Restore refuses existing target volumes. This avoids overwriting the preview
or the previously verified local stack. It pins all six services to the
backup manifest's recorded local Docker image IDs, and refuses restoration if
an image is missing. Docker can replace an image index when only its build
attestation changes; the recorder accepts such an index only after verifying
its exact platform manifest matches the running container. It records both
identities. `up` then uses these recorded images without rebuilding.
For off-host recovery, separately retain Docker image archives (`docker save`
the recorded image IDs) and load them with `docker load` before restore. The
data backup alone does not archive image layers. A deliberate application
upgrade removes the restore-image override only after taking a new backup and
reviewing the new release.
Verify saved audit receipts and the
complete journey in the restored project before treating a backup as usable.
The exact-comparison command above assumes a quiet maintenance window: stop
public ingress, let submitted work settle, and avoid new writes to the source
until comparison finishes. Legitimate new source activity changes its
fingerprint. The qualification used nine terminal runs, verified their complete
restored evidence, and then ran a new case through restored Kafka/PostgreSQL.
For a backup containing in-flight work, separately verify its retained journal
prefix and the new recovery receipt; post-recovery timestamps can differ
between the original and restored copies.
Browser cookies are origin-scoped; an operator can verify the restored database
directly, while a browser session needs the same original hostname/cookie.
Cookies and CSRF tokens must not be copied into a public report.

## Stable named tunnel

No Cloudflare account certificate, tunnel credentials or domain configuration
was available at initial inspection. A stable hostname requires the user to
sign in securely and select a domain already on Cloudflare; never paste tokens
or credentials into chat. There is no need to purchase a domain for the Quick
Tunnel. Once a connected domain is confirmed, a named tunnel can map only a
chosen subdomain to `http://127.0.0.1:3100`.

The following are unexecuted setup templates. The login opens Cloudflare's
browser authentication; keep the generated certificate/credentials private.

```sh
cloudflared tunnel login
cloudflared tunnel create inforsight-preview
cloudflared tunnel route dns inforsight-preview demo.EXISTING-DOMAIN
cloudflared tunnel --config "$HOME/.cloudflared/inforsight-preview.yml" run inforsight-preview
```

Use a configuration with that tunnel UUID, its local credentials file, one
ingress rule for `demo.EXISTING-DOMAIN` to the loopback gateway, and a final
`http_status:404` rule. Do not add private-network routes or other local ports.
Validate with `cloudflared tunnel ingress validate` using the selected config,
then repeat public session-isolation and end-to-end tests before handing over
the stable URL. [Official named-tunnel procedure](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/)

## Stop and teardown

Stop exposure immediately without deleting data:

```sh
python3 scripts/public_demo.py tunnel-stop
python3 scripts/public_demo.py down
```

For full **destructive** removal of this isolated preview only, first retain a
verified private backup if needed, then remove its containers/volumes and its
operator schedule. These commands do not target `inforsight-demo`:

```sh
python3 scripts/public_demo.py compose down --volumes
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.inforsight.inforsight-public.maintenance.plist"
rm "$HOME/Library/LaunchAgents/com.inforsight.inforsight-public.maintenance.plist"
docker volume ls --filter label=com.docker.compose.project=inforsight-public
docker ps -a --filter label=com.docker.compose.project=inforsight-public
```

Remove the private state and backup directories only after deciding no recovery
is needed. If a named tunnel was created later, remove only its selected DNS
record and tunnel, never the shared Cloudflare zone. No paid resource exists
in this preview to leave accruing charges.
