## 'nightwatch' runner component

This component can be used to define a 'nightwatch' deployment running in Kubernetes, for example with a ``nightwatch/kustomization.yaml`` file like this:
```yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

components:
- github.com/ZeitOnline/kustomize/components/nightwatch

images:
- name: nightwatch
  newName: europe-west3-docker.pkg.dev/org/docker/my-project-nightwatch
  newTag: "20230427170105"

patches:
- target:
    kind: Deployment
    name: nightwatch
  patch: |-
    - op: replace
      path: /spec/template/spec/containers/0/env/0/value
      value: production
```

Note that the ``patches`` section is (optionally) used to replace the default environment (`staging`) that the 'nightwatch' image is testing.
