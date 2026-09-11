# 'nginx-sidecar' component

This component adds an nginx sidecar to a `Deployment`, in front of whatever the pod serves — rewriting requests, translating headers, terminating something. It listens on **8000** and brings the writable paths nginx needs, so it works under [`security-config: hardened`](../security-config/).

It targets any `Deployment` that carries the `nginx-sidecar=required` label.

## Setup

What the sidecar actually does stays with the project: provide the configuration as a `nginx-config` ConfigMap with a `default.conf.template` key. The image's entrypoint renders it into `/etc/nginx/conf.d/` on startup, substituting any `${VARIABLE}` from the container's environment — which the project adds to the container in its own `patches:`, since only it knows what its configuration reads.

**`k8s/base/myapp/kustomization.yaml`**
```yaml
configMapGenerator:
- name: nginx-config
  files:
  - default.conf.template=nginx.conf
generatorOptions:
  disableNameSuffixHash: true

components:
- github.com/ZeitOnline/kustomize/components/nginx-sidecar?ref=1.23.0

patches:
- target:
    kind: Deployment
    name: myapp
  patch: |-
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: myapp
      labels:
        nginx-sidecar: required
# the sidecar listens on 8000, so point the Service at it
- target:
    kind: Service
    name: myapp
  patch: |-
    - op: replace
      path: /spec/ports/0/targetPort
      value: 8000
# whatever the configuration substitutes
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
          - name: myapp    # first, so the merge does not reorder `containers`
          - name: nginx
            env:
            - name: UPSTREAM_TIMEOUT
              value: "5s"
```

Mind the first entry of that last patch: a strategic merge reorders `containers` to match itself, and moving the sidecar to index 0 is how it ends up with the `/tmp` meant for the application container.

The `nginx` image name has to be mapped to the project's own image (`images:` in the overlay), the way `postgrest` and `migrator` are.

## Two requirements the image has to meet

**A non-root uid.** `security-config: hardened` drops all capabilities, `CAP_SETUID` included, so an nginx master started as root cannot hand its workers over to the `nginx` user and gives up. Set it in the image rather than in the manifests — `USER 101` for the official Debian-based images — which also keeps it out of reach of the container-level `securityContext` that 'security-config' owns:

```dockerfile
FROM nginx:1.31.3 AS nginx
USER 101
```

And since an `emptyDir` belongs to `root:root` unless the pod asks otherwise, the component sets `fsGroup: 10000` — the same value [`security-config`](../security-config/) uses — so that uid can write to the scratch volumes it gets. Both patches merge, so a pod-level `securityContext` of your own survives either way.

**A port above 1024**, for the same reason: `NET_BIND_SERVICE` is gone. It is 8000 rather than the more obvious 8080 so that the port stays free for whatever fronts the sidecar — a validating gateway, say, which is the outermost thing in the pod and the one an operator expects on 8080. The configuration therefore says `listen 8000`, and everything pointing at it — the `Service`'s `targetPort`, a `HealthCheckPolicy`'s `httpHealthCheck.port`, an `Ingress` backend — has to agree. It hides in more places than one expects.

## Order

List this component **before** [`security-config`](../security-config/), so that the sidecar it adds is still hardened along with the rest of the pod. A component only patches the resources accumulated before it.

The readiness probe defaults to `/rpc/health`, which is what our [PostgREST](../postgrest/) deployments answer; anything else overrides it in its own `patches:`.
