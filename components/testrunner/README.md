# 'testrunner' component

This component runs a project's test suite once as a Kubernetes `Job`, against the services deployed next to it. It is meant for development setups, typically a `k8s/devel` overlay driven by [Tilt](https://docs.zeit.de/ops/kubernetes/configure-tilt/), not for staging or production.

## Setup

The project provides the `testrunner` image, usually a test stage of its `Dockerfile`, and maps it in the overlay's `images:`. The job's settings go into an optional `testrunner-config` config map, which becomes its environment:

**`k8s/devel/kustomization.yaml`**
```yaml
resources:
- ../base/postgrest
- testrunner-config.yaml

components:
- github.com/ZeitOnline/kustomize/components/postgresql?ref=2.11.0
- github.com/ZeitOnline/kustomize/components/migrator?ref=2.11.0
- github.com/ZeitOnline/kustomize/components/testrunner?ref=2.11.0

images:
- name: testrunner
  newName: myapp/testrunner
```

**`k8s/devel/testrunner-config.yaml`**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: testrunner-config
data:
  PGHOST: postgresql
  PGDATABASE: testing
  PGUSER: postgres
  PGPASSWORD: postgres
```

With Tilt, let the tests wait for the migrations:

```python
k8s_resource(workload='testrunner', resource_deps=['migrator'])
```

## What it does

- adds the `Job` `testrunner` with a single container of the same name, running the image's entrypoint,
- never retries (`backoffLimit: 0`, `restartPolicy: Never`): a failed run should be looked at, not repeated,
- labels the job `pg-services: required`, so that [`pg-services`](../pg-services/), if included, hands it the connection service file. Without that component the label does nothing, and the database settings come from `testrunner-config`, as above. The container declares the empty `volumeMounts` list that `pg-services` needs.

A `Job` cannot be changed once it exists: to run the tests again, delete it first (Tilt does that on every rebuild).
