---
name: barbacane-migration
description: Replace Wiretap with Barbacane as a contract-validating API gateway in a PostgREST project, in the test suite and as a production sidecar in front of nginx. Use when a project runs PostgREST behind nginx with Wiretap for test-only contract validation, or when asked to add Barbacane, migrate off Wiretap, or validate requests against api.yaml at the gateway.
---

# Migrating a PostgREST project from Wiretap to Barbacane

Reference implementations: `ZeitOnline/freebies` and `ZeitOnline/merkl`, both running it.
The k8s side is the [`barbacane-sidecar`](../../components/barbacane-sidecar/) component; what
stays per-project is the contract, the image that compiles it, and the header declarations.
Verified against **Barbacane 0.12.2**. Re-check the facts below if the version differs — it is
pre-1.0, it breaks things between minors, and these are mostly undocumented behaviours found by
experiment. Read its CHANGELOG before any upgrade: 0.11 and 0.12 each changed what reaches the
upstream, and each requires every `.bca` artifact to be recompiled.

## What this migration is

`client → barbacane → nginx → postgrest`

Barbacane validates every request against `api.yaml` and forwards it. It replaces Wiretap in
the test suite and runs as an extra sidecar in staging and production.

**nginx stays.** Barbacane cannot read cookies, so it cannot do the `zeit_sso` →
`Authorization` mapping that nginx's `map` block does. There is no way around this short of a
custom WASM plugin — see "Dropping nginx" at the end. Do not propose removing nginx as part
of this work.

## The one thing that breaks production

**Barbacane routes from the spec.** An undeclared path is a 404, an undeclared method a 405,
before PostgREST ever sees the request. Wiretap passed everything through, so a project's
`api.yaml` is almost certainly narrower than its live traffic.

Do this audit **before** touching k8s, and report the findings to the user:

1. Every `location` in `nginx.conf` — prefixes it strips, aliases it serves, guards it applies.
2. Every URL constant in the frontend **and the methods used with each** (`grep -rn "fetch(" -A 3`).
   In freebies this found `/api/...` (a prefix nginx strips), `/me` (a real view, never specced),
   `/health` (an nginx alias), and `GET /allowances` (declared POST-only, but the admin UI GETs it).
3. Smoketest / nightwatch paths.
4. Anything internal calling the service hostname directly.

Then diff that surface against `api.yaml`. Everything missing has to be declared or the gateway
will 404 it. **Undeclared query params ride along fine** — only paths and methods are routed —
so PostgREST filters (`select=`, `id=in.(...)`, `valid_through=gt.`) need no declaration.

## Barbacane facts that drive the design

- Every operation needs `x-barbacane-dispatch`. A YAML anchor keeps this to one line each.
- `url: "env://VAR"` in the dispatch config resolves at startup. This is what lets the test
  harness point the gateway at an ephemeral nginx port.
- **`BARBACANE_ALLOW_INTERNAL_EGRESS=1` is required for loopback upstreams.** Without it the
  plugin sandbox's SSRF guard refuses to connect and every request is a bare 502 with only
  `target blocked by SSRF policy` in the log. This costs an hour if you don't know it.
- `barbacane dev` compiles and serves in one step and always allows plaintext upstreams — right
  for tests. `barbacane serve --artifact` plus `--allow-plaintext-upstream` — right for production.
- **OpenAPI 3.0 `nullable: true` is ignored.** The validator is plain JSON Schema, so
  `{type: string, nullable: true}` rejects `null`. Drop the `type` to allow null.
- `$ref`, `pattern` and `format` inside declared schemas *are* enforced.
- Validation is **request-only**. There is no response validation.
- The distroless image ships only the binary — plugins must be vendored separately. **Renovate
  bumps the image and not the checked-in `.wasm`**, so the two drift apart silently; refresh the
  plugin in the same PR. A plugin a few minors behind still loaded fine at 0.12, so drift is
  invisible until it is not.

## Only declared headers reach the upstream (0.11+)

Since 0.11 a request carries only the headers its operation admits: a small baseline, plus the
`in: header` parameters it declares, `cookie` when it declares an `in: cookie` parameter, and the
credential header named by its `security` requirement. Everything else is dropped **before nginx
or the upstream sees it**, and the symptom is not an error — every request simply arrives
anonymous, which looks like a broken auth backend.

Declare, at path-item level so it is one line per path:

- `security` + `components.securitySchemes` — this and nothing else is what admits `authorization`
- an `in: cookie` parameter — admits the whole `cookie` header
- an `in: header` parameter per custom header (`Prefer`, entitlements, anything the edge adds)

`serve --dev` and `barbacane dev` log every dropped header by name, and
`barbacane_request_headers_dropped_total` counts them. Run the suite once and read the log rather
than guessing — that list is the exact set to declare.

## Dead ends — do not retry these

Three plausible ways to map a prefix like `/api` onto existing paths. All fail:

- **`servers:` entries are documentation-only.** Adding `- url: /api` compiles the same route
  count and `/api/x` still 404s. In the source, `servers` is merged only for the
  `/__barbacane/specs` endpoint (`crates/barbacane/src/main.rs:211`); the router never reads it.
- **Path-item `$ref` to another file is silently ignored.** `validate` reports the spec as valid
  and compiles nothing from it.
- **YAML-aliasing a path item fails compilation** with `E1055: duplicate operationId`.

The way that works: **generate** the prefixed spec from `api.yaml` at image build time, suffixing
each `operationId`. See `api-alias.py` next to this file — it is generic, copy it in.

Check whether the prefix is still used before carrying it over, though. In both projects so far
it is a transitional alias that may have no callers left, and the metrics say so more cheaply
than a mirrored contract maintains it. If it is dead, drop the prefix instead of generating it.

## Getting the suite runnable

The suite drives real processes, so expect to spend time here before anything can be verified.
Common blockers and their fixes:

**No `postgrest` binary.** Take the version from the `FROM postgrest/postgrest:vX.Y.Z` line in
the Dockerfile and fetch that exact one — the suite is pinned to it:

```bash
curl -sSLO https://github.com/PostgREST/postgrest/releases/download/v13.0.8/postgrest-v13.0.8-ubuntu-aarch64.tar.xz
tar xJf postgrest-*.tar.xz     # assets: {ubuntu,macos}-aarch64, linux-static-x86-64, macos-x86-64
```

Point the suite at it with `POSTGREST=/path/to/postgrest` (already in tox `passenv`). Barbacane
comes from its own release as `barbacane-<arch>-unknown-linux-gnu`; pass it as `BARBACANE`.

**No PostgreSQL running, and the system cluster needs root.** Run your own as the current user:

```bash
export PATH=/usr/lib/postgresql/18/bin:$PATH
initdb -D "$PGDATA" -U "$(whoami)" --auth=trust
pg_ctl -D "$PGDATA" -o "-k $SOCK -c listen_addresses=''" -l "$PGDATA/server.log" start
export PGHOST="$SOCK"          # also in tox passenv
```

`--auth=trust` matters: PostgREST connects as `authenticator` with a dummy password, and
`tox.sql` creates that role.

**nginx cannot start as non-root.** It fails with
`[emerg] mkdir() "/var/lib/nginx/body" failed (13: Permission denied)`, because its temp paths
are compiled in as absolute. The test failure is the misleading
`RuntimeError: The port N on host localhost didn't become accessible` — the real cause is only in
pytest's captured stdout, so look there first. `nginx -p` does not help.

Do **not** patch `setup_nginx` for this; it is an environment problem, not a repo one. Put a shim
named `nginx` on `PATH` ahead of the real one that rewrites the generated config:

```bash
#!/bin/bash
TMP=${NGINX_TMP:-/tmp/nginx-test}; mkdir -p "$TMP"
args=(); cfg=""
while [ $# -gt 0 ]; do
  if [ "$1" = "-c" ]; then cfg="$2"; shift 2; else args+=("$1"); shift; fi
done
if [ -n "$cfg" ]; then
  new="$TMP/$(basename "$cfg")"
  { echo "pid $TMP/nginx.pid;"; echo "error_log stderr;"
    sed "s|http {|http { client_body_temp_path $TMP/body; proxy_temp_path $TMP/proxy;\
 fastcgi_temp_path $TMP/fastcgi; uwsgi_temp_path $TMP/uwsgi; scgi_temp_path $TMP/scgi;|" "$cfg"
  } > "$new"
  args+=(-c "$new")
fi
exec /usr/sbin/nginx "${args[@]}"
```

**`dropdb` fails with "being accessed by other users".** An aborted run left PostgREST or Barbacane
holding connections; the session-scoped fixture never tore them down. Kill the strays and re-run.
Beware that a `pkill -f` pattern matching your own command line kills the invoking shell — split
the literal (`pkill -f "post""grest"`) or match on the absolute path.

**Run `tox`, not `pytest` directly.** The `PGRST_*` settings live in tox's `setenv`, and missing
them produces failures that look real but are not — without `PGRST_PRE_REQUEST=public.set_role`
every role resolves to `anon` and the auth tests fail on plausible-looking assertions. If you do
drive the stack yourself for an end-to-end check, copy `setenv` across, and note that
`PGRST_DB_AGGREGATES_ENABLED=true` lives in the k8s ConfigMap rather than `tox.ini` — without it
frontend queries using `select=...count()` return PGRST123 and look like a gateway fault.

## Commit authorship

The checkout may be mapped into a container that has no git identity at all — `git config
user.name` and `user.email` both empty, locally and globally — so commits need explicit
`-c user.name=... -c user.email=...` or git refuses them.

Take the name from the repository's own history, not from the shape of the email address:

```bash
git log --all --format="%an <%ae>" | sort -u | grep <local-part>
```

`firstname.lastname@` is a convention, not a rule; it breaks on double-barrelled names, on
people who go by a middle name, and on anyone whose display name carries a character the
address flattened. Guessing wrong writes a subtly incorrect author into every commit, and
nobody notices until someone runs `git shortlog`.

## Procedure

### 1. Test harness

- `backend/barbacane.yaml` — manifest declaring the `http-upstream` plugin path. Replaces `wiretap.yaml`.
- Vendor `plugins/http-upstream.wasm` from the matching release so a checkout plus the binary is
  enough to run the tests. Verify against the release's `plugin-checksums.txt`.
- Add the anchor to `api.yaml` and one `x-barbacane-dispatch: *dispatch` line per operation.
  Name the anchor holder something *other* than `x-barbacane-*` or the compiler warns `E1015`:

```yaml
x-dispatch-defaults:
  dispatch: &dispatch
    name: http-upstream
    config:
      url: "env://BARBACANE_UPSTREAM"
```

- Replace `setup_wiretap` with `setup_barbacane` in `tests/utils.py`:

```python
p = Popen([executable, 'dev', '--listen', f'127.0.0.1:{port}',
           '--manifest', manifest, '--admin-bind', 'off', *args],
          env=dict(environ, BARBACANE_UPSTREAM=url,
                   BARBACANE_ALLOW_INTERNAL_EGRESS='1'))
```

- The test-only spec (`tests/api.yaml`) holds routes that must **not** exist in production —
  in freebies `/rpc/role` and `/_/__test__`. Compile it only for tests.
- Add `BARBACANE` to tox `passenv`.

Expect the suite to pass **unchanged**. If a test fails, the contract is usually wrong, not the test.
Two relaxations were needed in freebies, both worth checking for:

- A `required: true` query param whose absence nginx already rejects with a PostgREST-shaped body.
  Barbacane would answer first with RFC 9457 and break the assertion — set `required: false`
  and let nginx keep enforcing it.
- A `nullable` request field, per the `nullable` note above.

### 2. Production sidecar

- Dockerfile: a builder stage running `barbacane compile`, then a final stage
  `FROM <barbacane image> AS barbacane` with `COPY --from=... /api.bca /config/api.bca`.
  Compile **only** the production specs — never the test-only ones.
- Register the image (`k8s/base/registry`), add tags to both `versions` components, add the target
  to CI and the Tiltfile.
- Include the [`barbacane-sidecar`](../../components/barbacane-sidecar/) component, which brings
  the container, its port and its probe. List it **before** `security-config`. The project still
  repoints the `Service` at 8080 itself, so that two components never own one field.
- **Move every health check onto the gateway port.** A GKE `HealthCheckPolicy`, an ingress or
  load balancer probe, anything addressing PostgREST or nginx directly, now bypasses the
  component most likely to fail — a pod whose gateway is dead stays in rotation. Grep the
  overlays for a `port:` sitting next to a health path. Easy to dismiss as a pre-existing
  inconsistency; it stops being one the moment the gateway becomes the front door.
- **Every overlay including the postgrest base inherits the sidecar**, non-deployed ones
  (devel/local, driven by Tilt) included. Each needs its own `images:` entry or it points at an
  image that does not exist: a bare `barbacane` resolves to `docker.io/library/barbacane`,
  unlike `nginx`, which happens to be a real public image and so silently keeps working. Those
  overlays also have to build the gateway, and Tilt's `docker_build` cannot pass a named build
  context — any target using `COPY --from=project` needs `custom_build` with an explicit
  `docker build --build-context project=...` instead.

## Verify

- `tox` green, unchanged.
- `kustomize build` for each environment; diff against the pre-change output and confirm the only
  changes are the sidecar and the `targetPort`.
- Run the **compiled production artifact** against the real `nginx.conf` and PostgREST, and walk
  the audit list from step 1 — every path the frontend and the site actually call, with the auth
  each really sends. This is what catches the 405s. In freebies the `/api/*` callers send their own
  `Authorization` header because nginx's `location /api` has no `proxy_set_header`; a cookie alone
  returns 401 and looks like a gateway bug when it is not.

## Stop and ask

- **The contract-scope decision.** Once the audit shows undeclared live traffic, the options
  (declare it / generate it / catch-all / gateway behind nginx instead) trade validation coverage
  against contract size. That is the user's call. Do not pick silently — getting it wrong is a
  production outage, not a failed test.
- Anything that would change existing tests.

## Say this out loud

- **Response validation is gone.** Wiretap's `hardValidation` checked responses; Barbacane does
  not. This is a real regression, not an oversight.
- New endpoints must now be added to `api.yaml` or they 404. This changes how the team works.

## Dropping nginx — still not possible (checked at 0.12.2)

Since 0.10 `request-transformer` reads cookies, and the documented example is exactly the case
this migration has:

```yaml
headers:
  set:                                  # set = only when absent
    Authorization: "Bearer $cookie.sso_token"
```

It is still not enough, because nothing in the chain is conditional:

- **`set` cannot be skipped when the value interpolates to empty.** An absent cookie resolves to
  an empty string, so every *anonymous* request leaves with `Authorization: Bearer `, and
  PostgREST answers **401 PGRST301 "Empty JWT"**. Anonymous traffic breaks entirely — the
  opposite of a subtle regression, but only visible if a test covers logged-out access.
- **A malformed `Authorization` no longer falls back to the cookie.** nginx's `map` prefers a
  usable `Bearer`, then the cookie; `set` keeps whatever arrived, so a caller sending
  `Authorization: Bearer ` or `null` alongside a valid cookie becomes anonymous. PostgREST treats
  `null` and other junk as anonymous but an empty bearer as an error, so the two differ.
- `cel` can match on the cookie but `on_match.set_context` writes **literal** strings, so it
  cannot carry a captured value to the transformer.
- Header operations run add, set, remove, rename **in that order**, so remove-then-set is out.

What would unblock it: a `set` that skips an empty interpolation (or any conditional at all). That
is a small, well-shaped feature request — the maintainer added `$cookie` from one.

A custom WASM middleware remains the other route — `on_request` gets `req.headers` as a plain
`BTreeMap` and `barbacane-plugin-sdk` is on crates.io — but it is authentication code against a
pre-1.0 ABI, and the AGPL dual-license needs a look.

If it ever happens: nginx adds `Vary` and `Cache-Control` unconditionally, Fastly's caching depends
on them, and **no test would catch their absence.**
