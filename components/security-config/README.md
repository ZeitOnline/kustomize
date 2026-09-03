# 'security-config' component

This component provides two levels of pod hardening, selected via the value of the `security-config` label on a `Deployment`, `Job`, or `CronJob`:

- **`security-config: required`** — sets `fsGroup: 10000` at the pod level, so mounted volumes are readable by the `app` user used across our container images. No other changes to the manifest are needed.
- **`security-config: hardened`** — everything `required` does, plus on the first container: `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `readOnlyRootFilesystem: true`, and a memory-backed `emptyDir` mounted at `/tmp` so the now-read-only container has somewhere to write.

Use `hardened` for containers that don't need to write anywhere but `/tmp` (most application workloads). Use `required` alone for containers that need broader filesystem access (e.g. writing migration state, or reasons that already justify a custom `runAsUser`).

## Setup

**`hardened` also patches into existing arrays/objects**, so the target's first container must already declare `securityContext`, `volumeMounts`, and the pod's `volumes`, even if empty — the same convention used by [`pg-services`](../pg-services/). `required` alone has no such prerequisite, since it only adds the pod-level `securityContext` key.

```yaml
components:
- github.com/ZeitOnline/kustomize/components/security-config?ref=1.23.0
```

**`k8s/base/myapp/deployment.yaml`** (using `hardened`)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    security-config: hardened
spec:
  template:
    spec:
      containers:
        - name: myapp
          securityContext: {}
          volumeMounts: []
      volumes: []
```

If the container already needs its own `securityContext` fields (e.g. `runAsUser: 0` to read a mounted cert), keep them — `hardened` only adds the fields it owns and leaves the rest untouched.

`required` is used by the `migrator` Job and `postgrest` Deployment; `hardened` is used by the various `helpers`/`node`-image workloads (e.g. `categories-import`, `categories-updater`, `mediasync-importer`, `nodejs`). Any resource carrying either label picks up the matching patch — no changes to this component are needed to add more.
