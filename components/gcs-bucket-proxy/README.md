## GCS bucket proxy component

Currently [GCS buckets](https://cloud.google.com/storage) are [not yet natively supported](https://stackoverflow.com/a/67773859) as a backend service by [Google Cloud CDN](https://cloud.google.com/cdn), at least not when trying to mix other Kubernetes services in the Ingress definition.

To conveniently use them to serve static content nevertheless this [Kustomize component](https://kubectl.docs.kubernetes.io/guides/config_management/components/) provides a simple [nginx-based proxy k8s deployment](https://blog.meain.io/2020/dynamic-reverse-proxy-kubernetes/) to be used as such a service. Once the bucket itself has been set up your k8s overlay definition (i.e. ``kustomization.yaml``) simply needs to be modified so that its name is provided as an environment variable to the proxy deployment:
```yaml
components:
- github.com/ZeitOnline/kustomize/components/gcs-bucket-proxy

patches:
- target:
    kind: Deployment
    labelSelector: app=gcs-bucket-proxy
  patch: |-
    - op: add
      path: /spec/template/spec/containers/0/env
      value:
      - name: BUCKET_NAME
        value: assets-my-project-staging
```

Now your ingress definition can refer to the proxy as a backend:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    kubernetes.io/ingress.class: gce
  name: my-project
spec:
  rules:
  - host: my-project.staging.svc.zon.zeit.de
    http:
      paths:
      - backend:
          service:
            name: gcs-bucket-proxy
            port:
              number: 80
        path: /assets/*
        pathType: ImplementationSpecific
```
