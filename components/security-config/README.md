# 'security-config' component

This component hardens the `Deployment`s, `Job`s and `CronJob`s of everything it is applied to. There are two levels, selected via the value of the `security-config` label:

- **`security-config: required`** — sets `fsGroup: 10000` at the pod level, so mounted volumes are readable by the `app` user used across our container images. This is the **default**: anything that doesn't ask for a level itself is labelled `required` by the component, so including it covers a whole environment rather than the workloads someone remembered to label.
- **`security-config: hardened`** — everything `required` does, plus `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]` and `readOnlyRootFilesystem: true` on **every** container, and a memory-backed `emptyDir` mounted at `/tmp` on the first one.

Use `hardened` for a workload that writes nowhere but `/tmp` — most application workloads. Stay with `required` where a container needs broader filesystem access (a database writing its data directory, say) or any capability at all.

The flags are set through `replacements`, whose field paths can say `containers.*` — neither a JSON patch (needs a position) nor a strategic merge (needs a container name) can express that. This matters more than it sounds: a strategic-merge patch that lists containers reorders them to match itself, so an overlay patching a sidecar can quietly move it to `containers[0]`. Anything addressing the app container by index would then harden the sidecar instead. The `/tmp` mount is the one exception, and a harmless one — a spare `/tmp` is not a hazard.

## Our own components

Components that ship a workload declare their own level, the way they already declare `pg-services: required`, and bring the writable paths their containers need — they are the only ones who know their container names. So a project usually only includes this component and is done:

| component | level | why |
| --- | --- | --- |
| [`postgrest`](../postgrest/) | `hardened` | writes nothing outside `/tmp` |
| [`migrator`](../migrator/) | `hardened` | migration state lives in the database |
| [`nightwatch`](../nightwatch/) | `hardened` | writes its reports to `/tmp` |

The others carry no label yet and therefore get `required`. Adding one is a per-component decision about what that container writes at run time — worth checking in staging rather than guessing.

A declared label does nothing on its own: without this component included, nothing acts on it.

## Setup

```yaml
components:
- github.com/ZeitOnline/kustomize/components/security-config?ref=1.23.0
```

It has to come **last** in `components:`, since a component only patches the resources accumulated before it.

**`k8s/base/myapp/deployment.yaml`** (asking for `hardened`)
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

The label has to sit on the resource's own `metadata.labels` — kustomize's `labelSelector` does not look at `spec.template.metadata.labels`. Nor can it be applied by the overlay's `labels:` or `patches:`, which are both applied *after* its `components:`.

`hardened` mounts `/tmp` into the first container, and [JSON patches](https://datatracker.ietf.org/doc/html/rfc6902) cannot append to a list that doesn't exist, so that container needs to declare a `volumeMounts:` list — an empty one is enough, as above. The pod-level `volumes:` list does **not** have to be declared; the component creates it when it is missing. `required` has no prerequisites at all.
### `securityContext` settings on the target

The pod-level `securityContext` is *merged*, so anything the target sets there is kept. The **container-level** `securityContext`, however, is owned by this component and gets replaced wholesale, on every container. It cannot merge: the values have to be copied out of a resource (see `flags/template.yaml`), and `replacements` turn single values into strings on the way — `allowPrivilegeEscalation: "false"`, which the API server rejects — so the whole map is copied at once.

Mostly that costs nothing: the three fields exist *only* at the container level, and every field a workload might reasonably want on top can also be set at the pod level, where the component leaves it alone:

| pod level only | both levels (container wins) | container level only |
| --- | --- | --- |
| `fsGroup`, `fsGroupChangePolicy`, `supplementalGroups`, `sysctls` | `runAsUser`, `runAsGroup`, `runAsNonRoot`, `seLinuxOptions`, `seccompProfile`, `appArmorProfile` | `allowPrivilegeEscalation`, `capabilities`, `readOnlyRootFilesystem`, `privileged`, `procMount` |

So a workload that needs e.g. `runAsUser: 0` to read a mounted cert declares it on `spec.template.spec.securityContext`. See the [Kubernetes docs](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) for the full set.

It does cost something when two containers of a pod need *different* settings — a sidecar under its own uid, which a pod-level `runAsUser` cannot express. Those go into the consuming overlay's `patches:`, which are applied after all of its `components:` and therefore merge on top of what this component set:

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

### Writable paths

`hardened` gives the first container a `/tmp`, and nothing else. Every other path a container writes to at run time needs an `emptyDir` of its own, mounted by container name — next to where that container is defined, since that is the only place its name is known. An nginx sidecar, for instance, needs three: `/etc/nginx/conf.d` (its entrypoint renders `/etc/nginx/templates/*.template` into it), `/var/run` (pid file) and `/var/cache/nginx` (temp files). `fsGroup` makes them writable for a non-root uid.

Also mind the ports: `capabilities.drop: [ALL]` takes `NET_BIND_SERVICE` with it, so a container that binds a port below 1024 has to move up — and if its image starts as root and setuids its workers (nginx again), it needs to run as its own uid instead, since `CAP_SETUID` is gone too.

`initContainers` are not touched at all.

## Making `hardened` the default

`required` is the default this component applies. To harden a whole environment instead, a project can stamp `hardened` on everything unlabelled from a component of its own, listed *before* this one:

**`k8s/base/security-baseline/kustomization.yaml`**
```yaml
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
      name: ignored
      labels:
        security-config: hardened
```

The `!security-config` selector matches resources that carry no label at all, so workloads that ask for `required` themselves — because they cannot take more — keep it. A plain `labels:` block would overwrite them, and silently harden something that then fails to start.
