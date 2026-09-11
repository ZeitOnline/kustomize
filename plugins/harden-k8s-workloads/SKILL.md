---
name: harden-k8s-workloads
description: Adopt the ZeitOnline kustomize 'security-config' and 'nginx-sidecar' components in a project's k8s overlays - harden every Deployment/Job/CronJob of an environment (fsGroup, dropped capabilities, read-only root filesystem), move sidecars off privileged ports, and fix the label/ordering traps that make kustomize apply hardening to the wrong container. Use when asked to harden a project's Kubernetes setup, to roll out 'security-config', or when a hardened workload crash-loops after such a change.
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
   `replacements` with a `containers.*` path -- which is how this component sets its flags.

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

### 3. Include the component, last

```yaml
components:
- ...                                                                # everything else first
- github.com/ZeitOnline/kustomize/components/security-config?ref=…   # then this
```

It labels every workload that does not ask for a level itself `security-config: required`,
so including it covers the whole overlay (rule 1: only what came before it). Our own
components -- `postgrest`, `migrator`, `nightwatch` -- declare `hardened` themselves and
bring the writable paths their containers need, so there is usually nothing else to do.

Roll it out in `staging` first; `production` gets the same line later.

To harden *everything* by default instead, add a project component that stamps `hardened` on
unlabelled workloads and list it before this one -- see the component README. Use
`labelSelector: "!security-config"` there, never `labels:`, which would overwrite the
workloads that asked for `required` because they cannot take more.

### 4. Check the level of each workload

- `required` — `fsGroup: 10000` only. No prerequisites, safe everywhere.
- `hardened` — plus `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]` and
  `readOnlyRootFilesystem: true` on **every** container, and a `/tmp` emptyDir on the first
  one, which therefore needs a `volumeMounts:` list (an empty one will do).

A workload can take `hardened` if it writes nowhere outside the paths you give it and needs
no capabilities. Check each container's start-up behaviour, not just the app: entrypoints
that render config (nginx templates), tools that want a cache (`uv` without `UV_NO_CACHE`)
and anything writing a pid file all fail on a read-only root filesystem.

### 5. Give each container its writable paths

Beyond the `/tmp` of the first container, add an `emptyDir` per path a container writes, mounted by
container **name**, in the base (mounts are a property of the container, not of an environment).
An `emptyDir` belongs to `root:root` unless the pod sets `fsGroup`, so a non-root container can
only write to it once something does — `security-config` at any level, or the component that owns
the container.

For an nginx sidecar this is `/etc/nginx/conf.d` (the entrypoint renders
`/etc/nginx/templates/*.template` into it), `/var/run` (pid file) and `/var/cache/nginx` (temp
files) — but that one is already done: the [`nginx-sidecar`](https://github.com/ZeitOnline/kustomize/tree/main/components/nginx-sidecar)
component brings the container, the port, those three paths and the `fsGroup` for them. List it
**before** `security-config`, or the container it adds arrives too late to be hardened (rule 1).

### 6. Move sidecars off privileged ports

`capabilities.drop: [ALL]` removes `NET_BIND_SERVICE`, and a root master cannot setuid its workers
either, so an nginx sidecar needs an unprivileged port **and** a non-root uid. Put the uid in the **image**
(`USER 101` for the official nginx images): a container-level `runAsUser` is owned by
`security-config`, which replaces that map, so in the manifests it can only live in the overlay's
`patches:` — once per environment, and quietly load-bearing.

**Grep for the old port across the whole repo** — it hides in more places than expected:

| where | what |
| --- | --- |
| `nginx.conf` | `listen 80` |
| `Service` | `targetPort` (the published `port` stays 80) |
| container | `readinessProbe`/`livenessProbe` `port` |
| `HealthCheckPolicy` (networking.gke.io) | `httpHealthCheck.port` — easy to miss, breaks the LB health check |
| `BackendConfig`, `HTTPRoute`, Ingress | backend/service ports |
| tests | a fixture rewriting the config; `'listen 80'` is a prefix of `'listen 8000'`, so use a pattern |

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
- A non-root container cannot write its `emptyDir` → nothing set `fsGroup` for that pod. Shows up
  in the overlay that doesn't include `security-config`, e.g. `devel`.
- `replace operation does not apply: doc is missing key` → `op: replace` needs the key to exist,
  which kustomize enforces from 5.5 on. `op: add` creates or replaces.
