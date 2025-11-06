# 'db-sync' component

This component is meant to help with syncing databases, typically from 'staging' to the 'devel' environment.

It uses [pgcopydb](https://pgcopydb.readthedocs.io/) and a service named "staging" as its source. The corresponding [definition](https://www.postgresql.org/docs/17/libpq-pgservice.html) needs to be created separately.

## Setup

The component defines a [cronjob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) that runs the synchronization process. The used helper script (`run.sh`) first upgrades the PostgreSQL client and then runs `pgcopydb`. It can be used directly in your `kustomization.yaml`, but using a separate `base/` resource allows for only applying the [pg-services](../pg-services) component patches to the "sync" job. This is helpful if CloudSQL is not used for the target database:

**`k8s/base/db-sync/kustomization.yaml`**
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

components:
- github.com/ZeitOnline/kustomize/components/db-sync?ref=1.22.0
- github.com/ZeitOnline/kustomize/components/pg-services?ref=1.22.0
```

With that the "sync" can simply be manually triggered:
```bash
kubectl create job --from=cronjob/db-sync test-sync
```
