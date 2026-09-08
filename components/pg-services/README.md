# 'pg-services' component

This component is intended to help hooking up a [PostgreSQL service definition file](https://www.postgresql.org/docs/current/libpq-pgservice.html) as provided by the [`cloudsql_credentials` Terraform module](https://github.com/ZeitOnline/terraform-modules/tree/main/cloudsql_credentials) with database clients in Kubernetes. It mounts the service file and configures the `PGSERVICEFILE` and `PGSERVICE` environment variables accordingly.

It targets any `Deployment`, `Job`, or `CronJob` that carries the `pg-services=required` label. The `pg-service` secret is mounted at `/vault/secrets/pg`.

## Setup

Add the `pg-services: required` label to the resources that need database access and include the component:

**`k8s/staging/kustomization.yaml`**
```yaml
resources:
- ../base/myapp

components:
- github.com/ZeitOnline/kustomize/components/pg-services?ref=1.23.0
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

## Requirements on the targeted resources

The component appends the `pg-service` volume to the pod spec and mounts it into
the **first** container (`containers[0]`, plus `initContainers[0]` for
`pg-services-init`). Because [JSON patches](https://datatracker.ietf.org/doc/html/rfc6902)
cannot append to a list that doesn't exist, that container needs to declare a
`volumeMounts:` list — an empty one is enough:

```yaml
      containers:
        - name: myapp
          image: myapp
          volumeMounts: []
```

The pod-level `volumes:` list does **not** have to be declared; the component
creates it when it is missing.
