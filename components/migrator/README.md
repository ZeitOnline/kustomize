# 'migrator' component

This component runs database migrations as a Kubernetes `Job` before the rest of a deployment goes live. The job runs the `migrator` image, which the project provides, and is recreated on every reconciliation (`kustomize.toolkit.fluxcd.io/force`). It does not retry: a failed migration should be looked at, not repeated.

Database credentials come from the [`pg-services`](../pg-services/) component, which the job asks for via `pg-services: required`.

**`k8s/staging/kustomization.yaml`**
```yaml
components:
- github.com/ZeitOnline/kustomize/components/migrator?ref=2.5.0
- github.com/ZeitOnline/kustomize/components/pg-services?ref=2.5.0
```

Anything the migration tool needs beyond that goes into the `migrator-config` config map:

```yaml
patches:
- target:
    kind: ConfigMap
    labelSelector: migrator=required
  patch: |-
    - op: add
      path: /data/PGOPTIONS
      value: "-c statement_timeout=0"
```

## alembic

By default the job runs whatever the image's entrypoint is, which for an [alembic](https://alembic.sqlalchemy.org) project is typically a small script doing `alembic upgrade head`:

```dockerfile
FROM app AS migrator
COPY migrations migrations
WORKDIR migrations
ENTRYPOINT ["uv", "run", "--no-sync", "sh", "migrate.sh"]
```

## goose

For [goose](https://pressly.github.io/goose/) add the nested `goose` layer **after** this one. It sets the job's command and puts the `GOOSE_*` settings into the config map, so the image needs nothing but the binary and the migrations:

```yaml
components:
- github.com/ZeitOnline/kustomize/components/migrator?ref=2.5.0
- github.com/ZeitOnline/kustomize/components/migrator/goose?ref=2.5.0
- github.com/ZeitOnline/kustomize/components/pg-services?ref=2.5.0
```

```dockerfile
FROM ghcr.io/kukymbr/goose-docker:3.27.2 AS migrator
COPY migrations /migrations
```

`GOOSE_MIGRATION_DIR` defaults to `/migrations`, `GOOSE_DBSTRING` to `postgres://` — goose picks up `PGSERVICEFILE` and `PGSERVICE` from 'pg-services' by itself. Both can be overridden in the config map as shown above.

The layer also teaches [`wait-for-migrations`](../wait-for-migrations/) to ask goose instead of alembic, so the two work together without further patching. It only does so when that component is included, and it has to come after it — see below.

## Ordering

Components are accumulated in list order, and a component only patches what came before it. The `goose` layer therefore has to be listed **after** `migrator`, and after `wait-for-migrations` if that one is used too. A label added in an overlay's own `patches:` runs after all components and is invisible to their `labelSelector` — which is why the `migrator: required` label lives in this component rather than in the project.
