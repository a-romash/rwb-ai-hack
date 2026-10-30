# Prototype runtime implementation plan

**Goal:** Starting a pipeline in Studio produces a working prototype link on the same host.

**Architecture:** Keep the platform running and replace one prototype in a prepared Compose runtime. Build and tests use the existing tool containers; the runtime contains only PostGIS, ASP.NET processes and nginx serving compiled frontends. No runtime image builds or package installation during deployment.

**Constraints:** Work in `claude/review-docs-branches-48sc58`. One active pipeline globally when prototype publishing is enabled. Reset only prototype data. Keep previous run artifacts. Return a relative URL from the backend, never embed the VPS address in frontend code. Default publishing off for existing installations and tests.

- [x] Add failing lifecycle tests: publish ready assets without building images; delete only prototype data; hide obsolete links; preserve unrelated files; deployment failure never returns a link.
- [x] Add trusted backend publish command and reuse compiled frontend output; route smoke/E2E to prepared runtime. Preserve ordinary sandbox behavior when publishing is disabled.
- [x] Integrate runtime cleanup at pipeline start and publication into verify. Serialize active runs and retries using the existing PostgreSQL advisory lock pattern.
- [x] Expose current run prototype URL through RunRead and report; show an accessible link in Studio. Add frontend scenario with an arbitrary server-provided URL and absent URL.
- [x] Coordinate VPS runtime/nginx with the existing VM chat. It owns `infra/prototype/`, VM setup and local LLM compatibility.
- [ ] Run focused tests, existing Python suites and Studio build/E2E; review the diff; verify prepared runtime and two replacements on the VPS. Record any real-model limitation.
