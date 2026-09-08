# 'security-config' component

This component provides three levels of pod hardening, selected via the value of the `security-config` label on a `Deployment`, `Job`, or `CronJob`:

- **`security-config: required`** — sets `fsGroup: 10000` at the pod level, so mounted volumes are readable by the `app` user used across our container images. No other changes to the manifest are needed.
- **`security-config: hardened`** — everything `required` does, plus on the first container: `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `readOnlyRootFilesystem: true`, and a memory-backed `emptyDir` mounted at `/tmp` so the now-read-only container has somewhere to write.
- **`security-config: hardened-all`** — everything `required` does, plus those same three flags on **every** container, and nothing else: no `/tmp`, no assumptions about which container is the interesting one.

Use `hardened` for a single-container workload that writes nowhere but `/tmp` (most application workloads). Use `hardened-all` for a workload with sidecars, where hardening only `containers[0]` would leave the rest untouched — and where each container needs its own writable paths anyway. Use `required` alone for containers that need broader filesystem access.

`hardened` addresses the first container **by index**, which is worth knowing about: a strategic-merge patch that lists containers reorders them to match itself, so an overlay patching a sidecar can quietly move that sidecar to `containers[0]` and hardening then lands on it instead. `hardened-all` has no such failure mode — a `replacements` field path can say `containers.*`, which neither a JSON patch (needs a position) nor a strategic merge (needs a container name) can express.

## Setup

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
          image: myapp
          volumeMounts: []
```

The label has to sit on the resource's own `metadata.labels` — kustomize's `labelSelector` does not look at `spec.template.metadata.labels`.

`hardened` mounts `/tmp` into the first container, and [JSON patches](https://datatracker.ietf.org/doc/html/rfc6902) cannot append to a list that doesn't exist, so that container needs to declare a `volumeMounts:` list — an empty one is enough, as above. The pod-level `volumes:` list does **not** have to be declared; the component creates it when it is missing. `required` alone has no prerequisites at all.

### `securityContext` settings on the target

The pod-level `securityContext` is *merged*, so anything the target sets there is kept. The **container-level** `securityContext` of the first container, however, is owned by `hardened` and gets replaced wholesale — the component cannot merge into it, because a strategic merge would have to address the container by name and this component is applied to workloads with arbitrary container names.

That is not much of a restriction: the three fields `hardened` sets exist *only* at the container level, and every field that a workload might reasonably want on top can also be set at the pod level, where the component leaves it alone:

| pod level only | both levels (container wins) | container level only |
| --- | --- | --- |
| `fsGroup`, `fsGroupChangePolicy`, `supplementalGroups`, `sysctls` | `runAsUser`, `runAsGroup`, `runAsNonRoot`, `seLinuxOptions`, `seccompProfile`, `appArmorProfile` | `allowPrivilegeEscalation`, `capabilities`, `readOnlyRootFilesystem`, `privileged`, `procMount` |

So a `hardened` workload that needs e.g. `runAsUser: 0` to read a mounted cert declares it on `spec.template.spec.securityContext` rather than on the container. See the [Kubernetes docs](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) for the full set.

`hardened-all` replaces the container-level `securityContext` the same way, for every container. That is a real limit when two containers need *different* settings — a sidecar running under its own uid, say, which a pod-level `runAsUser` cannot express. Those go into the consuming overlay's `patches:`, which are applied after all of its `components:` and therefore merge on top of what this component set:

```yaml
patches:
- target:
    kind: Deployment
    name: myapp
  patch: |-
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: myapp
    spec:
      template:
        spec:
          containers:
          - name: sidecar        # by name, and merged, so the flags stay
            securityContext:
              runAsUser: 101
```

## Hardening a whole environment

Instead of labelling every workload, an overlay can apply the baseline to everything it contains. The label has to be in place *before* this component's patches run, which means it has to come from an earlier component — an overlay's own `labels:` and `patches:` are applied after all of its `components:`:

**`k8s/staging/security-config/kustomization.yaml`**
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

patches:
- target:
    kind: Deployment
    labelSelector: "!security-config"
  patch: |-
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: ignored
      labels:
        security-config: required
```

**`k8s/staging/kustomization.yaml`**
```yaml
components:
- security-config                                                    # labels what isn't labelled yet
- github.com/ZeitOnline/kustomize/components/security-config?ref=…   # and only then patches
```

The `!security-config` selector matches resources that don't carry the label at all, so workloads that ask for `hardened` themselves keep it. A plain `labels:` block would overwrite their value and silently downgrade them.

Note that a component's patches only see the resources accumulated before it, so this component belongs at the *end* of the `components:` list if everything in the overlay is meant to be covered.
