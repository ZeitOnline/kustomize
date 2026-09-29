---
name: adopt-goose-migrations
description: Move a project's database migrations from alembic to goose and run them in Kubernetes with the ZeitOnline kustomize 'migrator' component and its 'goose' layer - convert the revisions, shrink the migrator image, wire up the overlays, and get past the ordering, versioning and service-file traps that make the job fail only once it is in the cluster. Use when asked to convert migrations to goose, to adopt the 'migrator' or 'migrator/goose' component, to set up a migration job for a PostgREST project, or when a migrator job cannot reach the database or re-runs migrations that were already applied.
---

# Moving a project's migrations to goose

Assumes a repo shaped like ours: kustomize overlays in `k8s/{base,staging,production}`, components
pinned as `github.com/ZeitOnline/kustomize/components/<name>?ref=<tag>`, and a schema the project
keeps as SQL. `ZeitOnline/kickerticker` went through this end to end and is worth reading first —
`migrations/`, `migrate.sh` and `kickerticker/tests/test_migrations.py`.

Work in the order below and **commit each step separately**: the conversion, the version bump and
the overlay wiring fail in different ways, and a single commit makes it much harder to see which
one did. Render and diff after every step.

## First: four things that bite

1. **Components are accumulated in list order, and a component only patches what came before it.**
   The `goose` layer patches the job that `migrator` creates and the init container that
   `wait-for-migrations` creates, so it has to be listed after both.
2. **An overlay's own `labels:` and `patches:` run after all of its `components:`.** A label added
   there is invisible to a component's `labelSelector`. That is why the switch is the
   `migrator: required` label the component puts on its *own* resources — you never set it yourself.
   The flip side is useful: an overlay patch always wins over a component, which is how a project
   overrides the job's command (see below).
3. **goose runs through [pgx](https://github.com/jackc/pgx), not libpq.** They disagree about the
   connection service file, and only in the cluster — the test suites drive goose through `PG*`
   variables, so nothing catches it earlier.
4. **The migrations decide the schema, but only on an empty database.** Every existing database
   needs its bookkeeping seeded once, or goose replays everything from the start.

## Steps

### 1. Convert the revisions

If each alembic revision is the usual wrapper around a sibling `.sql` file, the conversion is
mechanical and `alembic-to-goose.py` in this skill directory does it: it walks the
`down_revision` chain, names each migration after the timestamp of the revision that introduced
it, and adds the goose annotations. Read its output before committing.

What changes per file:

- `-- +goose Up` as the header, and no `Down` section. Rolling a schema back is not something we
  do, and an empty `Down` is worse than none: goose would happily "apply" it.
- `BEGIN;`/`COMMIT;` go — goose runs each migration in a transaction of its own.
- Any statement containing a semicolon **before its end** — a `$$`-quoted function body, a
  `CREATE RULE` with a parenthesised statement list — must be wrapped in `-- +goose StatementBegin`
  and `-- +goose StatementEnd`, because goose splits on semicolons and would otherwise cut the
  statement in half.

Keep the timestamps in the order the revisions were actually applied. They are the only ordering
goose has, and a file that sorts before one already applied in production will never run.

Two things that are easy to miss when the project ran its SQL by hand rather than through alembic:

- **Roles are cluster-global**, so `CREATE ROLE` in a migration fails the second time the job runs
  against the same instance. Use the `do $$ ... if 'x' != all(select rolname from pg_roles) ...`
  pattern the schema files already use.
- **A migration that sets `search_path`** leaks into the migrations that follow, because goose
  keeps one connection. Reset it at the end.

### 2. Make the migrations reproduce the schema, and prove it

Adopt the schema-diff test from `ZeitOnline/freebies` (`backend/tests/test_migrations.py`): it
builds one database from the schema definition and one from the migrations, and compares the two
`pg_dump` outputs. Its `canonify()` sorts columns, ACLs and column lists, so the two dumps only
differ where the schema really differs.

Expect the first run to fail. Migrations written by hand drift from the schema file over the years
— a default nobody migrated, an index added straight in production, a function body that was
edited in place. Each difference the test reports is a real one; resolve it with a final
"catch up with the schema definition" migration rather than by adjusting history, so that existing
databases converge on the same state.

If the project's schema is split across several files and one of them changes `search_path`, apply
them in **separate `psql` invocations** in the test, or the later files land in the wrong schema.

Sanity-check that the test can actually fail: change a default in the schema file and confirm you
get a diff.

### 3. Shrink the image

The component supplies the command and the `GOOSE_*` settings, so the migrator image needs nothing
but the binary and the migrations:

```dockerfile
FROM ghcr.io/kukymbr/goose-docker:3.27.2 AS goose

FROM goose AS migrator
COPY migrations /migrations
```

`GOOSE_MIGRATION_DIR` defaults to `/migrations`, which is why the migrations go there and not
under `/app`. If a test image inherits from the migrator and runs the suite from the repo layout,
give it its own copy rather than moving this one.

**If the job does more than migrate** — recreating views and grants on every deploy, say — keep
that script and override the component's `goose up` from a small project component:

```yaml
# k8s/base/migrator/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

patches:
- target:
    kind: Job
    labelSelector: migrator=required
  patch: |-
    - op: replace
      path: /spec/template/spec/containers/0/command
      value: [sh, /migrations/migrate.sh]
```

listed after the `goose` layer. The layer still earns its place: the `GOOSE_*` settings and the
goose-aware wait helper come from it either way.

### 4. Wire up the overlays

```yaml
components:
- github.com/ZeitOnline/kustomize/components/migrator?ref=2.5.0
- github.com/ZeitOnline/kustomize/components/migrator/goose?ref=2.5.0
- ../base/migrator            # only if you override the command, see above
- github.com/ZeitOnline/kustomize/components/pg-services?ref=2.5.0
```

Add `migrator` to the registry mapping and to both `versions` overlays, and to the CI build
targets — a job pointing at an image nobody builds fails in a way that looks like a cluster
problem.

`wait-for-migrations` holds the dependent deployments back until the job is done. Include it where
that deployment is defined; the `goose` layer will find it as long as it is listed later.

### 5. Mind the version jump

The 2.x `migrator` relies on 2.x `pg-services` to create the pod's `volumes` list, so its
placeholder is gone and **mixed refs do not build**. Every component moves to the same tag at once,
in its own commit.

Coming from 1.x that bump carries one thing worth stating out loud in the pull request: 2.x moved
the container hardening out of `nightwatch` into
[`security-config`](../../components/security-config/). A project that does not include that
component **loses the hardening it had** — the deployment keeps the `security-config: hardened`
label with nothing acting on it. Adopting `security-config` is its own change with its own staging
soak; see the [`harden-k8s-workloads`](../harden-k8s-workloads/) skill.

### 6. Seed the bookkeeping of existing databases

goose records what it has applied in `goose_db_version`, and has no `stamp` command. Before its
first run against a database that already carries the schema, mark everything up to the last
hand-applied migration as done — `stamp.sh` in this skill directory does it. Getting this wrong is
loud rather than silent: goose tries to create tables that exist and the job fails.

Check the database really is at that state first, with the `PGDIFF` half of the migration test.

### 7. Verify

Diff renders, never sources: `kustomize build` each overlay before and after, and account for
every row. Then run the migration test.

What a build cannot prove is whether the job can reach the database, so watch the first run in
staging. The failure to expect is this one:

```
goose run: failed to connect to `user=X database=X`: /tmp/.s.PGSQL.5432 (/tmp): dial error
```

User and database are right, the host is missing: pgx has read the service file but not found a
host it understands. `hostaddr` is the usual reason — pgx neither uses it as an address nor
ignores it, but passes it to the server, which rejects it. `cloudsql_credentials` writes `host`
since 0.3.1; a project pinned to an older version needs to bump. Adding `host` *alongside*
`hostaddr` does not help, and neither does `PGHOST` — the stray parameter still goes out. If the
bump has to wait, resolve the service file into `PG*` variables in a wrapper and unset `PGSERVICE`
before handing over to goose.
