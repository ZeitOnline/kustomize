# 'barbacane-sidecar' component

This component adds a [Barbacane](https://github.com/barbacane-dev/barbacane) gateway to a `Deployment`, in front of whatever the pod serves. It validates every request against the project's OpenAPI contract and forwards what passes. It listens on **8080** — the outermost port of the pod, in front of [`nginx-sidecar`](../nginx-sidecar/) on 8000 — and needs no writable paths, so it works under [`security-config: hardened`](../security-config/) as it is.

It targets any `Deployment` that carries the `barbacane-sidecar=required` label, which the [`postgrest`](../postgrest/) component declares.

## What the project supplies

**The image.** Barbacane serves a sealed artifact rather than the spec, so the contract is compiled into an image of the project's own and mounted nowhere: the component expects it at `/config/api.bca`. A stage that produces one, given the upstream `barbacane` image and the plugins the spec uses:

```dockerfile
FROM app AS gateway
COPY --from=barbacane-dist /barbacane /bin/barbacane
COPY plugins plugins
COPY barbacane.yaml ./
COPY api.yaml specs/api.yaml
RUN barbacane compile --manifest barbacane.yaml --spec specs/api.yaml --output /tmp/api.bca

FROM barbacane-dist AS barbacane
COPY --from=gateway /tmp/api.bca /config/api.bca
```

Map the `barbacane` image name to it in the overlay's `images:`, the way `postgrest` and `nginx` are, and add the target to the CI build. The upstream image ships only the binary, so the plugins the spec dispatches through have to come from the matching release — check them in rather than downloading at build time, and refresh them whenever the image is bumped. Renovate moves the image and not the plugins.

**The Service.** The gateway is the front door, so point the `Service` at it — as with `nginx-sidecar`, the component stays out of the Service so that two components never fight over one field:

```yaml
- target:
    kind: Service
    name: myapp
  patch: |-
    - op: replace
      path: /spec/ports/0/targetPort
      value: barbacane   # the name of its port, see 'nginx-sidecar'
```

**Everything else naming the port.** A `HealthCheckPolicy` especially: pointed at anything behind the gateway, the load balancer keeps a pod whose gateway is dead in rotation. Use `portSpecification: USE_SERVING_PORT` there rather than a number, as described for [`nginx-sidecar`](../nginx-sidecar/#point-at-the-port-by-name).

## Defaults worth overriding

| what | default | when to change it |
| --- | --- | --- |
| `BARBACANE_UPSTREAM` | `http://127.0.0.1:8000` | no nginx sidecar — point it at the application port directly |
| readiness probe | `GET /rpc/health` | anything that is not one of our [PostgREST](../postgrest/) deployments |
| `preStop` sleep | 20 s | never alone: every container of the pod has to wait as long, see [shutting down](../postgrest/#shutting-down) |

Both are ordinary container fields, so a project changes them in its own `patches:`, by container name:

```yaml
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
          - name: myapp       # first, so the merge does not reorder `containers`
          - name: barbacane
            env:
            - name: BARBACANE_UPSTREAM
              value: http://127.0.0.1:3000
```

## Order

List this component **before** [`security-config`](../security-config/), so the container it adds is hardened along with the rest of the pod. A component only patches the resources accumulated before it.

Relative to [`nginx-sidecar`](../nginx-sidecar/) the order does not matter — neither touches the other's container — but both must come before `security-config`.

## What it does not do

The gateway routes from the contract: a path the spec does not declare is a 404 and a method it does not declare a 405, before the upstream sees the request. Adopting it in a project whose spec is narrower than its traffic takes an audit first; the [`barbacane-migration`](../../plugins/barbacane-migration/) skill walks through it.

It validates **requests only** — there is no response validation.
