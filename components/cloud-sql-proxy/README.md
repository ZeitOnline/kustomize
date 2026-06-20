# 'cloud-sql-proxy' component

This component injects a [Cloud SQL Proxy](https://github.com/GoogleCloudPlatform/cloud-sql-proxy)
sidecar into database clients so they can reach a Cloud SQL instance over `localhost`. The
proxy authenticates via service-account impersonation and IAM database authentication.

It targets any `Deployment`, `Job`, or `CronJob` that carries the `cloud-sql-proxy=required`
label. The connection details come from the `cloudsql-proxy-iam` secret as provided by the
[`cloudsql_credentials` Terraform module](https://github.com/ZeitOnline/terraform-modules/tree/main/cloudsql_credentials).

## What it does

For every labelled workload the component:

- sets the `baseproject` service account (workload identity for the proxy),
- appends the `cloud-sql-proxy` sidecar container, which consumes the **whole**
  `cloudsql-proxy-iam` secret (it needs `INSTANCE_CONNECTION` and
  `CLOUDSQL_PROXY_IMPERSONATION_SA`) and listens on `127.0.0.1`,
- injects **only** `PGUSER` (the instance's IAM SQL user) into the application container
  (`containers[0]`) via a `secretKeyRef`.

> **The application container must declare an `env:` list** – the component appends `PGUSER`
> to it with a JSON patch (`add` to `.../containers/0/env/-`), which fails if the list is
> absent.

## Setup

Add the `cloud-sql-proxy: required` label to the resources that need database access and
include the component:

**`k8s/staging/kustomization.yaml`**
```yaml
resources:
- ../base/myapp

components:
- github.com/ZeitOnline/kustomize/components/cloud-sql-proxy?ref=2.0.0
```

**`k8s/base/myapp/deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    cloud-sql-proxy: required
spec:
  template:
    spec:
      containers:
      - name: app
        # the component appends PGUSER here, so an env list must exist
        env:
        - name: PGHOST
          value: localhost
        - name: PGPORT
          value: "5432"
        - name: PGDATABASE
          value: myapp
        - name: PGSSLMODE
          value: disable
```

This component is commonly used together with the
[`migrator`](../migrator/) and [`wait-for-migrations`](../wait-for-migrations/) components.

## Breaking change in 2.0.0

Up to and including `1.x` the component imported the **entire** `cloudsql-proxy-iam` secret
into the application container's `envFrom`, handing the app every libpq variable
(`PGHOST`, `PGPORT`, `PGDATABASE`, `PGSSLMODE`, `PGUSER`, ...) the secret happened to carry.

From `2.0.0` the component injects **only `PGUSER`** into the application container. All other
connection settings must now be provided by the consuming project (typically a `ConfigMap`).
The proxy sidecar still receives the full secret, so the proxy itself is unaffected.

### Why

- The static libpq settings (`PGHOST=localhost`, `PGPORT`, `PGDATABASE`, `PGSSLMODE`) are
  identical for every instance and belong in the project's own configuration, not in a
  per-instance secret.
- Only `PGUSER` genuinely varies per instance (it is the IAM SQL user of that instance's
  proxy service account), so that is the single value worth injecting from the secret.
- This keeps the application container free of a blanket secret import and makes
  multi-instance setups (e.g. running two database variants side by side during a migration)
  straightforward: each variant patches the secret name and `PGUSER` source independently.

### How to migrate

1. Add the static libpq settings to your application container's configuration, e.g. a
   `ConfigMap`:

   ```yaml
   PGHOST: localhost
   PGPORT: "5432"
   PGDATABASE: myapp
   PGSSLMODE: disable
   ```

2. Make sure the application container declares an `env:` list (the component appends
   `PGUSER` to it).
3. Bump the component ref to `2.0.0`.

No change is required for the proxy sidecar or the `cloudsql-proxy-iam` secret itself.
