# Prototype runtime

One disposable prototype, isolated from Studio. Runtime requires the published artifacts
in `current/{backend,worker,admin,mobile}` below the host `.prototype` directory.
The frontend builds use base paths `/agent-prototype/` and `/agent-prototype/mobile/`.
The directories are mounted read-only; replace them only after stopping the runtime.

On the VM `PROTOTYPE_DIR=/srv/rwb/project/workspaces/.prototype`. The same directory
is visible in worker-build at `/app/workspaces/.prototype`, but Docker bind mounts
must use the host path. The trusted compose.yaml and nginx.conf are stored there.

For every new publication, remove the previous prototype and its database:

```sh
export PROTOTYPE_DIR=/srv/rwb/project/workspaces/.prototype
docker compose -p rwb-prototype -f "$PROTOTYPE_DIR/compose.yaml" down -v
# Publish current/{backend,worker,admin,mobile} here.
docker compose -p rwb-prototype -f "$PROTOTYPE_DIR/compose.yaml" up -d --no-build --pull never --wait --wait-timeout 120
```

The internal database has disposable prototype-only credentials and no host port.
Never store real secrets or production data in this runtime. The host Nginx routes
`/agent-prototype/` to 127.0.0.1:18080; while the runtime is down it returns 503.
