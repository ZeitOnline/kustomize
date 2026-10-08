# 'postgrest' component

This component is meant to set up [PostgREST](https://postgrest.org/) instances in Kubernetes. It can be used either directly in your `kustomization.yaml`, but oftentimes additional configuration is shared between the various environment (e.g. 'staging' and 'production') so it might be more convenient to set up a `base/` resource first:

**`k8s/base/postgrest/kustomization.yaml`**
```yaml
components:
- github.com/ZeitOnline/kustomize/components/postgrest?ref=1.11
- github.com/ZeitOnline/kustomize/components/wait-for-migrations?ref=1.11

patches:
- path: config.yaml
```

**`k8s/base/postgrest/config.yaml`**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgrest-config
data:
  PGRST_MAX_ROWS: "5000"
  PGRST_JWT_SECRET: "{\"kty\": \"RSA\", \"n\": \"…\", \"e\": \"AQAB\"}"
```

Now this can in turn be used in the respective environment, typically together with the ['migrator'](../migrator/) and ['pg-services'](../pg-services/) components also available from this repository:

**`k8s/staging/kustomization.yaml`**
```yaml
resources:
- ../base/postgrest

components:
- github.com/ZeitOnline/kustomize/components/migrator?ref=1.11
- github.com/ZeitOnline/kustomize/components/pg-services?ref=1.11
```

The deployment also asks for the [`nginx-sidecar`](../nginx-sidecar/) and [`security-config: hardened`](../security-config/) components. Both labels do nothing unless those components are included.

## Shutting down

Every container waits 20 seconds (`lifecycle.preStop.sleep`) before it gets its `SIGTERM`. A Google load balancer only drops a pod from its network endpoint group after the pod is marked as terminating, which took 12 seconds in a merkl rollout; without the wait, PostgREST stops at once and the requests still arriving meanwhile are answered with a 503. The [`nginx-sidecar`](../nginx-sidecar/) and [`barbacane-sidecar`](../barbacane-sidecar/) components wait the same time, since each container gets its own signal — one that stops early leaves the others without an upstream.

The 20 seconds come out of the default `terminationGracePeriodSeconds` of 30, which leaves 10 for requests in flight. A project with longer requests raises the grace period, not the sleep.
