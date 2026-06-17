#!/bin/sh
set -e

# LinuxServer.io-style runtime UID/GID remapping.
#
# The container starts as root so we can align the in-container "appuser" with
# the ownership of the bind-mounted /app/userdata directory, then drop back to
# that unprivileged user before launching the app. This lets Linux hosts set
# PUID/PGID (in docker-compose `environment:` or `docker run -e`) to match the
# owner of their bind-mounted userdata dir and avoid permission errors.

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

echo "[entrypoint] Applying PUID=${PUID} PGID=${PGID} to appuser/appgroup"

# Remap the group and user to the requested ids. -o allows non-unique ids in
# the (harmless) case where the target id already exists.
groupmod -o -g "$PGID" appuser
usermod  -o -u "$PUID" -g "$PGID" appuser

# Only chown the writable runtime data dir — never recurse over all of /app
# (the app code is owned as built and a full recursive chown on every start is
# slow and unnecessary). /app/userdata is the bind-mounted volume the app
# writes to (config, creds, db, logs, uploads).
if [ -d /app/userdata ]; then
    chown -R appuser:appuser /app/userdata
    chmod -R 755 /app/userdata
fi

# Drop privileges and exec the CMD as appuser.
exec gosu appuser "$@"
