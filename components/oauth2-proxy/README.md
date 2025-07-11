# 'oauth2-proxy' component

This component is meant to help setting up [OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) instances in Kubernetes which authenticate against [Keycloak](https://www.keycloak.org) to protect API endpoints and other resources.

It can be used directly in your `kustomization.yaml`, but oftentimes additional configuration is shared between the various environments (e.g. 'staging' and 'production') so it might be more convenient to set up a "base" resource first:

**`k8s/base/oauth/kustomization.yaml`**
```yaml
components:
- github.com/ZeitOnline/kustomize/components/oauth2-proxy

patches:
- patch: |-
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: oauth2-proxy-config
    data:
      OAUTH2_PROXY_COOKIE_NAME: "zeit_oidc_xyz_production"
      OAUTH2_PROXY_REDIRECT_URL: "https://xyz.zon.zeit.de/oauth2/callback"
      OAUTH2_PROXY_UPSTREAMS: "http://postgrest/"
- target:
    kind: Ingress
    name: oauth2-proxy
  patch: |-
    - op: replace
      path: /spec/rules/0/http/paths/0/path
      value: /(oauth2|api/protected/path)
```

This can then be used in the respective environment:

**`k8s/staging/kustomization.yaml`**
```yaml
resources:
- ../base/oauth

patches:
- target:
    group: networking.k8s.io
    kind: Ingress
    name: oauth2-proxy
  patch: |-
    - op: replace
      path: /spec/rules/0/host
      value: xyz.zon.zeit.de
```
