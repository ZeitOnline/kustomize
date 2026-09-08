---
name: harden-k8s-workloads
description: Adopt the ZeitOnline kustomize 'security-config' component in a project's k8s overlays - harden every Deployment/Job/CronJob of an environment (fsGroup, dropped capabilities, read-only root filesystem), move sidecars off privileged ports, and fix the label/ordering traps that make kustomize apply hardening to the wrong container. Use when asked to harden a project's Kubernetes setup, to roll out 'security-config', or when a hardened workload crash-loops after such a change.
---

# Hardening a project's Kubernetes workloads

Assumes a repo shaped like ours: kustomize overlays in `k8s/{base,staging,production}`, components
pinned as `github.com/ZeitOnline/kustomize/components/<name>?ref=<tag>`. The reference
implementation is `ZeitOnline/merkl` — its `k8s/base/security-baseline/` and `k8s/base/postgrest/`
are worth reading before starting.

Work in the order below and **commit each step separately**. Render and diff after every step;
most mistakes here are invisible in the source and obvious in the output.

## First: four kustomize rules that cause every trap

1. **Components are accumulated in list order, and a component only patches what came before it.**
   A component listed after `security-config` is never hardened. Put `security-config` **last**.
2. **An overlay's own `labels:` and `patches:` run after all of its `components:`.** A label added
   in `patches:` is invisible to a component's `labelSelector` — it silently does nothing. Per-container
   extras, on the other hand, *must* go there, because they have to land after the component.
3. **`labelSelector` matches `metadata.labels` only** — never `spec.template.metadata.labels`.
   A hardening label on the pod template is a no-op.
4. **A strategic-merge patch listing containers reorders them to match itself.** An overlay patching
   a sidecar can move it to `containers[0]`, where index-based hardening then lands. Prefer
   `replacements` with `containers.[name=x]` paths, or the `hardened-all` level.

## Steps

### 1. Inventory before touching anything

Render every overlay and record what each workload has today (`inventory.sh` in this skill
directory does it). Keep the output; it is the baseline for every later diff. Build a pre-change
copy from git (`git worktree add`) so you can diff renders, not sources.

If a component is pinned to a branch, check the branch still exists — merged branches get deleted
and the overlay then fails to build for reasons unrelated to your change.

### 2. Fix the labels first

- Move any hardening label from `spec.template.metadata.labels` to the resource's own
  `metadata.labels` (rule 3). Workloads that looked hardened were not.
- Take it **out of `commonLabels`/`labels:`**: those stamp every resource in the kustomization,
  including ConfigMaps and Services, and inject into `spec.selector` — which is **immutable** on a
  Deployment. A later change of the label value then needs the Deployment deleted and recreated.
  Put it on the workload with a small merge patch instead.
- While there, migrate deprecated `commonLabels:` to `labels: [{pairs: {...}, includeSelectors: true}]`.

### 3. Baseline for the whole environment

Add a component (not `labels:`, see rule 2) that labels everything unlabelled, and list it
immediately before `security-config`, both **last** in `components:`:

```yaml
# k8s/base/security-baseline/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component
patches:
- target:
    kind: Deployment          # repeat for Job and CronJob
    labelSelector: "!security-config"
  patch: |-
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: ignored           # the target selector decides what is patched
      labels:
        security-config: required
```

`!security-config` matches resources without the label, so workloads that ask for a stronger level
keep it. A plain `labels:` block would overwrite them — a silent downgrade. Per-workload upgrades
go in the same component *before* the generic patches, which then skip them (selectors are
evaluated against the current state).

Roll this out in `staging` first; `production` picks the same component up later with one line.

### 4. Pick a level per workload

- `required` — `fsGroup: 10000` only. No prerequisites, safe everywhere.
- `hardened` — plus the three flags on `containers[0]` and a `/tmp` emptyDir. Needs
  `volumeMounts: []` on that container. Single-container workloads only (rule 4).
- `hardened-all` — the three flags on **every** container, nothing else. Use it whenever there is a
  sidecar.

A workload can take the flags if it writes nowhere outside the paths you give it and needs no
capabilities. Check the container's own start-up behaviour, not just the app: entrypoints that
render config (nginx templates), tools that want a cache (`uv` without `UV_NO_CACHE`), and
anything writing a pid file all fail on a read-only root filesystem.

### 5. Give each container its writable paths

`hardened-all` sets flags only. Add an `emptyDir` per path the container writes, mounted by
container **name**, in the base (mounts are a property of the container, not of an environment).
For an nginx sidecar that is exactly three: `/etc/nginx/conf.d` (the entrypoint renders
`/etc/nginx/templates/*.template` into it), `/var/run` (pid file), `/var/cache/nginx` (temp files).
`fsGroup` makes those writable for a non-root uid.

### 6. Move sidecars off privileged ports

`capabilities.drop: [ALL]` removes `NET_BIND_SERVICE`, and a root master cannot setuid its workers
either, so an nginx sidecar needs port 8080 **and** `runAsUser: <image uid>` (101 for the official
nginx image). The uid goes in the overlay's `patches:` (rule 2), or into the image with a `USER`
line if you would otherwise repeat it per environment.

**Grep for the old port across the whole repo** — it hides in more places than expected:

| where | what |
| --- | --- |
| `nginx.conf` | `listen 80` |
| `Service` | `targetPort` (the published `port` stays 80) |
| container | `readinessProbe`/`livenessProbe` `port` |
| `HealthCheckPolicy` (networking.gke.io) | `httpHealthCheck.port` — easy to miss, breaks the LB health check |
| `BackendConfig`, `HTTPRoute`, Ingress | backend/service ports |
| tests | a fixture rewriting the config; `'listen 80'` is a prefix of `'listen 8080'`, so use a pattern |

### 7. Verify

Diff renders, never sources: the output diff should contain only rows you can name. Re-run the
inventory and check every workload's level, pod `securityContext`, per-container `securityContext`
and mounts. Then say plainly what a build cannot prove — whether a container can still read its
secret and start with a read-only root filesystem is decided in staging, so roll out there first
and watch for `CrashLoopBackOff`.

## Pitfalls, condensed

- Hardening applied to a sidecar instead of the app → container reordering (rule 4).
- Label ignored → in `patches:` (rule 2) or on the pod template (rule 3).
- Workload not covered at all → its component is listed after `security-config` (rule 1).
- `Deployment.spec.selector` immutable error on apply → the label went through `commonLabels`.
- `allowPrivilegeEscalation: "false"` (a string) → `replacements` stringify scalars; copy the whole
  `securityContext` map instead of single fields.
- Two components appending to `volumes` → the earlier one still needs the list to exist.
