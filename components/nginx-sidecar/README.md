# 'nginx-sidecar' component

This component adds an nginx sidecar to a `Deployment`, which translates the `zeit_sso` cookie into an `Authorization` header so that a [PostgREST](https://docs.postgrest.org/) service behind it sees a bearer token. It listens on **8080** and brings the writable paths nginx needs, so it works under [`security-config: hardened`](../security-config/).

It targets any `Deployment` that carries the `nginx-sidecar=required` label.

## Setup

The nginx configuration itself stays with the project — it is the part that knows the service's routes. Provide it as a `nginx-config` ConfigMap with a `default.conf.template` key; the image's entrypoint renders it into `/etc/nginx/conf.d/` on startup, substituting `${AUTH_COOKIE_NAME}`.

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
# the sidecar listens on 8080, so point the Service at it
- target:
    kind: Service
    name: myapp
  patch: |-
    - op: replace
      path: /spec/ports/0/targetPort
      value: 8080
```

The `nginx` image name has to be mapped to the project's own image (`images:` in the overlay), the way `postgrest` and `migrator` are.

## Two requirements the image has to meet

**A non-root uid.** `security-config: hardened` drops all capabilities, `CAP_SETUID` included, so an nginx master started as root cannot hand its workers over to the `nginx` user and gives up. Set it in the image rather than in the manifests — `USER 101` for the official Debian-based images — which also keeps it out of reach of the container-level `securityContext` that 'security-config' owns:

```dockerfile
FROM nginx:1.31.3 AS nginx
USER 101
```

**A port above 1024**, for the same reason: `NET_BIND_SERVICE` is gone. The configuration therefore says `listen 8080`, and everything pointing at it — the `Service`'s `targetPort`, a `HealthCheckPolicy`'s `httpHealthCheck.port`, an `Ingress` backend — has to agree. It hides in more places than one expects.

## Order

List this component **before** [`security-config`](../security-config/), so that the sidecar it adds is still hardened along with the rest of the pod. A component only patches the resources accumulated before it.

The readiness probe defaults to PostgREST's `/rpc/health`; a project fronting something else overrides it in its own `patches:`.
