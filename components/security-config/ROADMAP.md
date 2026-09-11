# Hardening: what's left

Where we stopped after `security-config`, `nginx-sidecar` and merkl as the first consumer. Rough
order; the first item gates the rest.

## Once production runs the current state

- **Release the components and repin.** merkl pins `postgrest` and `nginx-sidecar` to
  `?ref=feat/nginx-sidecar`, `migrator`/`pg-services`/`security-config` to other refs. One release
  tag, one commit in the project.

## Next

- **`seccompProfile: RuntimeDefault` and `runAsNonRoot: true`,** merged into the pod-level patch.
  The two pieces of Pod Security Standards `restricted` we don't have yet. `seccompProfile` can go
  in on its own; `runAsNonRoot` cannot, because the kubelet refuses to verify a *named* image user
  (`USER app`) — the images have to end on `USER 10000` (or the manifests on an explicit
  `runAsUser`) first.
- **`initContainers`.** Exempt today: the `replacements` only cover `containers.*`. Expect the same
  writable-path questions as for the containers -- merkl's `wait-for-migrations` runs `uv run`,
  which wants a cache directory unless `UV_NO_CACHE` is set.
- **Pod Security Admission on the namespace.** `pod-security.kubernetes.io/warn=restricted` and
  `audit=restricted` first: they report violations without breaking anything, and the report tells
  us exactly what the two items above still owe. `enforce=restricted` afterwards is what makes the
  hardening non-regressable -- a new workload can no longer quietly skip the component.

## Later

- **`automountServiceAccountToken: false`** for workloads that never call the API. Removes a real
  credential from the container and the `/var/run` mount question for nginx along with it. Not
  `nightwatch`, which needs the projected token for Workload Identity.
- **`sizeLimit` on the `/tmp` volumes.** They are `medium: Memory` and count against the pod's
  memory limit, so an unbounded write there is an OOM rather than a full disk.
- **A level for the remaining components** -- `oauth2-proxy`, `gcs-bucket-proxy`, `db-sync`,
  `db-upgrade`, `testrunner`. Each is a question about what that container writes at run time, so
  decide it in staging rather than on paper.
- **The nginx sidecar's probe** still defaults to PostgREST's `/rpc/health`. If a second consumer
  fronts something else, that default should probably go. Switching the image to a hardened nginx
  (non-root and an unprivileged port out of the box) would also shrink the requirements the README lists.

## Loose ends found on the way

- The `/tmp` mount of `hardened` is the one thing still addressed by container **index**. Harmless
  -- a spare `/tmp` is not a hazard -- but it is why a `volumeMounts:` list is still a prerequisite.
- merkl: `k8s/production` adds the `migrator` label in `patches:`, i.e. too late for the component
  to select on it. Now redundant, since the component carries the label -- worth deleting.
- merkl: `k8s/local` refers to a `base/postgresql` that no longer exists, so that overlay does not
  build. Restore it or drop the overlay.
