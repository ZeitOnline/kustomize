# 'wait-for-migrations' component

This component holds a `Deployment`'s pods back until the database migrations are done. It adds an init container that asks the migration tool every 10 seconds whether the schema is up to date, and only lets the application start once it is. It works together with the [`migrator`](../migrator/) component: the job migrates, everything else waits for it.

It targets any `Deployment` that carries the `wait-for-migrations=required` label, which the [`postgrest`](../postgrest/) component declares.

## Setup

**`k8s/base/myapp/kustomization.yaml`**
```yaml
components:
- github.com/ZeitOnline/kustomize/components/wait-for-migrations?ref=2.11.0
```

**`k8s/base/myapp/deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  labels:
    wait-for-migrations: required
spec:
  template:
    spec:
      containers:
      - name: myapp
        envFrom:
        - configMapRef:
            name: myapp-config
```

The init container runs the project's `migrator` image, which already brings the migration tool and the migrations, so the overlay's `images:` mapping for `migrator` covers it, too.

## What it does

- adds the init container `wait-for-migrations` with the `migrator` image, running `/helpers/wait.sh` from the `wait-for-migrations` config map,
- copies the `envFrom` of the first container (`containers[0]`) to it, so the helper reaches the database the same way the application does — that container therefore needs an `envFrom` list,
- labels the `Deployment` `pg-services-init: required`, so that [`pg-services`](../pg-services/) mounts the connection service file into the init container, too,
- gives the init container a read-only mount for the helper and its own memory-backed `/tmp` (16Mi), so it keeps working under [`security-config: hardened`](../security-config/), which hardens this init container along with the rest of the pod.

## alembic

By default the helper waits until `alembic current` reports `(head)`. Its command is `pipenv run sh /helpers/wait.sh`, so a project using [uv](https://docs.astral.sh/uv/) replaces it in its own `patches:`:

```yaml
- target:
    kind: Deployment
    labelSelector: wait-for-migrations=required
  patch: |-
    - op: replace
      path: /spec/template/spec/initContainers/0/command
      value:
        - uv
        - run
        - --no-sync
        - sh
        - /helpers/wait.sh
```

`UV_NO_CACHE` is already set, since the root filesystem is read-only.

## goose

The [`migrator`](../migrator/#goose)'s nested `goose` layer switches the helper over: it waits as long as `goose status` lists a migration as `Pending`, runs it with plain `sh` and adds the `migrator-config` config map with the `GOOSE_*` settings to the init container. Nothing else to patch.

## Order

Components are accumulated in list order, and a component only patches what came before it:

- **after** whatever adds the `wait-for-migrations: required` label — a base, or [`postgrest`](../postgrest/),
- **before** [`pg-services`](../pg-services/), which selects on the `pg-services-init` label added here, and before [`security-config`](../security-config/),
- **before** the `goose` layer of [`migrator`](../migrator/), which patches the helper this component creates.
