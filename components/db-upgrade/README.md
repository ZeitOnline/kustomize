# 'db-upgrade' component

This component is meant to help with upgrading [PostgreSQL](https://www.postgresql.org/) databases using [pgcopydb](https://pgcopydb.readthedocs.io/) in "[follow mode](https://pgcopydb.readthedocs.io/en/latest/tutorial.html#follow-mode-or-change-data-capture)".

## Setup

The component defines a [job](https://kubernetes.io/docs/concepts/workloads/controllers/job/) that runs the main migration process. The used helper script (`start.sh`) grants replication rights, runs `pgcopydb` and the necessary cleanup afterwards. It can be used directly in your `kustomization.yaml`, but oftentimes additional configuration is shared between the various environment (e.g. 'staging' and 'production') so it might be more convenient to set up a `base/` resource first:

**`k8s/base/db-upgrade/kustomization.yaml`**
```yaml
components:
- github.com/ZeitOnline/kustomize/components/db-upgrade?ref=1.15
- github.com/ZeitOnline/kustomize/components/pg-services?ref=1.15

patches:
- path: config.yaml
```

**`k8s/base/db-upgrade/config.yaml`**
```yaml apiVersion: v1
kind: ConfigMap
metadata:
  name: db-upgrade
data:
  PGCOPYDB_SOURCE_PGURI: "postgres://?service=db"
  PGCOPYDB_TARGET_PGURI: "postgres://?service=pg17"

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: db-upgrade-helper
data:
  readonly.sql: |
    revoke insert on api.likes from anon;
```

## Running a migration

Using "follow mode" implies that the process requires to receive a signal in order to exit in a controlled way. The `finish.sh` script is meant as a convenient way to send this signal once the migration is done and the logical replication has caught up with the source database.

The script also provides a hook to optionally revoke write access beforehand to prevent user changes from getting lost. To use it the `readonly.sql` item of the `db-upgrade-helper` configmap can be overwritten like in [the example above](#setup).

**Please note** that the `finish.sh` script [must be run using the same working directory](https://pgcopydb.readthedocs.io/en/latest/tutorial.html#follow-mode-or-change-data-capture) as the main `pgcopydb` process. Hence it needs to be started from a k8s shell or using "[exec](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_exec/)":

```bash
kubectl exec job/db-upgrade -- /migration/finish.sh
```

After the main `pgcopydb` process, i.e. the job, has exited, any deployments that directly use the database can be switched to the new instance or restarted. Due to the just stopped replication this can happen with very little downtime.

```bash
kubectl rollout restart deployments/postgrest
```
