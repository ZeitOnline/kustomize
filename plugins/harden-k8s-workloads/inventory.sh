#!/bin/bash
# What every workload of a rendered overlay has, security-wise. Pass rendered
# manifests (`kustomize build k8s/staging > out.yaml`), one file per call, and
# diff the output before/after a change.
#
#   ./inventory.sh out.yaml
#   Deployment/postgrest  hardened  pod={"fsGroup":10000}
#     postgrest: {"allowPrivilegeEscalation":false,...}  mounts=/tmp /vault/secrets/pg
#
# Needs `yq` (the jq wrapper) on PATH.
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: $(basename "$0") <rendered-manifests.yaml>" >&2; exit 2; }

yq -r '
  select(.kind == "Deployment" or .kind == "Job" or .kind == "CronJob") |
  (if .kind == "CronJob"
     then .spec.jobTemplate.spec.template.spec
     else .spec.template.spec end) as $p |
  "\(.kind)/\(.metadata.name)  \(.metadata.labels."security-config" // "-")  " +
  "pod=\($p.securityContext // {} | tojson)" +
  ([ ($p.initContainers // [])[] | "\n  init \(.name): \((.securityContext // {}) | tojson)" ] | join("")) +
  ([ $p.containers[] |
     "\n  \(.name): \((.securityContext // {}) | tojson)" +
     "  mounts=\(((.volumeMounts // []) | map(.mountPath) | join(" ")))" ] | join(""))
' "$1"
