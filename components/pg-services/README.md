# 'pg-services' component

This component sets up the [PostgreSQL service definition file](https://www.postgresql.org/docs/current/libpq-pgservice.html) for database clients in Kubernetes. It uses the Vault agent injector to mount the service file and configures the `PGSERVICEFILE` and `PGSERVICE` environment variables accordingly.

It targets any `Deployment`, `Job`, or `CronJob` that carries the `pg-services=required` label. The `pg-service` secret (provided by `tf:cloudsql_credentials`) is mounted at `/vault/secrets/pg`.

## Setup

Add the `pg-services=required` label to the resources that need database access and include the component:

**`k8s/staging/kustomization.yaml`**
```yaml
resources:
- ../base/myapp

components:
- github.com/ZeitOnline/kustomize/components/pg-services?ref=1.22.0
```

**`k8s/base/myapp/deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    pg-services: required
```

This component is commonly used together with the [`migrator`](../migrator/) and [`postgrest`](../postgrest/) components.
