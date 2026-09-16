#!/bin/sh
set -e

# Runs as root so setpriv can drop to the requested UID/GID before exec'ing
# the real command - lets PUID/PGID match whatever owns the bind-mounted
# cross-seed config directory on the host, instead of a baked-in user.
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

exec setpriv --reuid "$PUID" --regid "$PGID" --clear-groups "$@"
