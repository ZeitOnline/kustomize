# Changelog

## [1.22.1](https://github.com/ZeitOnline/kustomize/compare/1.22.0...1.22.1) (2025-11-20)


### Bug Fixes

* **nightwatch:** prepare `uv` to run on read-only file systems ([#25](https://github.com/ZeitOnline/kustomize/issues/25)) ([07fddf8](https://github.com/ZeitOnline/kustomize/commit/07fddf8735da06046713db1c68d85f186d85ccf3))

## [1.22.0](https://github.com/ZeitOnline/kustomize/compare/1.21.1...1.22.0) (2025-11-06)


### Features

* **cloudsql:** add component to sync databases via cronjob ([#23](https://github.com/ZeitOnline/kustomize/issues/23)) ([72ed219](https://github.com/ZeitOnline/kustomize/commit/72ed219ffb6c535fd672aa516d828c24981482a8))

## [1.21.1](https://github.com/ZeitOnline/kustomize/compare/1.21.0...1.21.1) (2025-11-05)


### Bug Fixes

* **oauth:** set caching headers for all response status codes & refresh cookie ([#21](https://github.com/ZeitOnline/kustomize/issues/21)) ([3288ea2](https://github.com/ZeitOnline/kustomize/commit/3288ea27e92a8e07d723fde7554f770e63aa275f))

## [1.21.0](https://github.com/ZeitOnline/kustomize/compare/1.20.0...1.21.0) (2025-10-14)


### Features

* add component to set up 'oauth2 proxy' instances ([#15](https://github.com/ZeitOnline/kustomize/issues/15)) ([877b4b0](https://github.com/ZeitOnline/kustomize/commit/877b4b0e9974240409fd12590053e71e341dceb4))

## [1.20.0](https://github.com/ZeitOnline/kustomize/compare/1.19.1...1.20.0) (2025-10-01)


### Features

* **cloudsql:** add component for 'cloud-sql-proxy' sidecar ([#18](https://github.com/ZeitOnline/kustomize/issues/18)) ([11523ae](https://github.com/ZeitOnline/kustomize/commit/11523aee2f19bec7637c60fd5c14b69fa8c37a50))

## [1.19.1](https://github.com/ZeitOnline/kustomize/compare/1.19.0...1.19.1) (2025-07-17)


### Bug Fixes

* **nightwatch:** disable pytest cache ([f79b877](https://github.com/ZeitOnline/kustomize/commit/f79b877e5ceb38900e2d40223b9bb323d4f89913))

## [1.19.0](https://github.com/ZeitOnline/kustomize/compare/1.18.0...1.19.0) (2025-07-17)


### Features

* **nightwatch:** run as non-root, with readonly filesystem ([cdc8278](https://github.com/ZeitOnline/kustomize/commit/cdc8278fc9b86dbe7a39d36390055c0fabec306e))

## [1.18.0](https://github.com/ZeitOnline/kustomize/compare/1.17.0...1.18.0) (2025-06-27)


### Features

* **nightwatch:** prefer `uv` to run the tests & helpers ([#14](https://github.com/ZeitOnline/kustomize/issues/14)) ([d221e17](https://github.com/ZeitOnline/kustomize/commit/d221e172aaf8aeba46a2d8552a74172ba9d49b34))


### Bug Fixes

* **postgresql:** GKE now requires a minimum PVC size of 8GB ([af1c222](https://github.com/ZeitOnline/kustomize/commit/af1c222df8cd9618b34515be9db4264a7aa4b7cf))

## [1.17.0](https://github.com/ZeitOnline/kustomize/compare/1.16.1...1.17.0) (2025-04-22)


### Features

* **k8s:** Do not set k8s resources in component postgrest ([fde4175](https://github.com/ZeitOnline/kustomize/commit/fde4175f46313a48e3af4ef8a342605c034a0125))

## [1.16.1](https://github.com/ZeitOnline/kustomize/compare/1.16.0...1.16.1) (2025-03-26)


### Bug Fixes

* correct syntax in nightwatch run.sh ([#10](https://github.com/ZeitOnline/kustomize/issues/10)) ([599dc48](https://github.com/ZeitOnline/kustomize/commit/599dc4814fae1e1fedf0c55ec538547c5a9bd95c))

## [1.16.0](https://github.com/ZeitOnline/kustomize/compare/1.15.0...1.16.0) (2025-03-06)


### Features

* **nightwatch:** upload test output to GCS instead of trying to log to stdout [ZO-5537] ([6a0e094](https://github.com/ZeitOnline/kustomize/commit/6a0e09413b8d38eb53d92c3c7e9e9a3dbadbe09e))


### Bug Fixes

* **postgrest:** reduce default log level to warnings ([2241534](https://github.com/ZeitOnline/kustomize/commit/2241534df5e698a57a61e736b9d34f8236edcc7f))

## [1.15.0](https://github.com/ZeitOnline/kustomize/compare/v1.14.0...1.15.0) (2025-02-13)


### Features

* activate gzip encoding and turn on access log for now ([d62fdd0](https://github.com/ZeitOnline/kustomize/commit/d62fdd00a7b67a35f62890b778ae138ab6558a3a))
* add empty env list to be spiele-deployment conform ([3a3d730](https://github.com/ZeitOnline/kustomize/commit/3a3d73023e21db936baa6bdf8b2bb7646dd82bcd))
* add kustomize component for 'migrator' job ([d97342e](https://github.com/ZeitOnline/kustomize/commit/d97342e77de688a6b67f8f33c0195af3248bc8ae))
* add kustomize component to set up 'postgrest' ([8e7215f](https://github.com/ZeitOnline/kustomize/commit/8e7215f50a4594fbe34b17f2dbded39437b651c9))
* add kustomize component to set up a simple 'nightwatch' cronjob ([35788a8](https://github.com/ZeitOnline/kustomize/commit/35788a87d370b39f6eeede74e6c9db08a5fa5361))
* add kustomize component to use PostgreSQL "service files" ([944ef5e](https://github.com/ZeitOnline/kustomize/commit/944ef5ef635949b95001c0a7421cd9c61893207b))
* add kustomize component to wait for 'alembic' migrations ([6a2bfc7](https://github.com/ZeitOnline/kustomize/commit/6a2bfc723b9eab6409a25deef7dc32e61bd3ab48))
* add kustomize components for development with 'Tilt' ([a315671](https://github.com/ZeitOnline/kustomize/commit/a315671150b33a4384b2bbec1c491e5591a9b271))
* add kustomize components to provide a proxy for GCS buckets ([6793a59](https://github.com/ZeitOnline/kustomize/commit/6793a59942d8f9eafe39d194fe15736d716eddec))
* allow 'testrunner' to use "pg services" ([61bb425](https://github.com/ZeitOnline/kustomize/commit/61bb425183a2da57819d68911a55d6bc7c8ecd76))
* **cloudsql:** add (shared) component for database upgrades ([bc8c05f](https://github.com/ZeitOnline/kustomize/commit/bc8c05fa2815f715df01b7800cffd3b98129c0be))
* **nightwatch:** configure staging/production via environment [ZO-5573] ([5f93fa3](https://github.com/ZeitOnline/kustomize/commit/5f93fa345048db093f002e9bb9cd5951a71b731b))
* **nightwatch:** provide namespace as env var, so we can set the prometheus label centrally instead of per-project ([11b4207](https://github.com/ZeitOnline/kustomize/commit/11b4207fa1e0b05161f21c94231f66b322c93333))
* turn 'nightwatch' cronjob into a (long-running) deployment ([97be890](https://github.com/ZeitOnline/kustomize/commit/97be8901824fc08a95a08bfaa51c003d9266b10c))
* Use json formatted output introduced in zeit.nightwatch-1.7 to get readable logs in kibana ([52d70a8](https://github.com/ZeitOnline/kustomize/commit/52d70a83c086f9c62c41bf08e428169ed3348cd9))


### Bug Fixes

* add 'readiness' probe and resource requests for GCS proxy ([9f40186](https://github.com/ZeitOnline/kustomize/commit/9f401869f5e90592f63f5b10c348113033c60ba3))
* **db-upgrade:** also try to clean up after errors ([82194e0](https://github.com/ZeitOnline/kustomize/commit/82194e0ffd4a8fa0d67b719a2bf90860fb8c2ade))
* **db-upgrade:** grant 'replication' role on source and target ([660ada7](https://github.com/ZeitOnline/kustomize/commit/660ada7c29f53bad1a0c1c15dbf665c4f3bd5b5e))
* go with the default browser & channel ([36ecea1](https://github.com/ZeitOnline/kustomize/commit/36ecea15a76617b2f0bac19907f8db2e1ccb3238))
* make configmap for 'testrunner' environment optional ([b34e017](https://github.com/ZeitOnline/kustomize/commit/b34e01715da0601482904bf6bd760366726cb1d0))
* the loop should be run using `bash` ([b1a67c2](https://github.com/ZeitOnline/kustomize/commit/b1a67c299eb543f07749becd2130ffad8c88ac2e))
* use 'baseproject' service account in order to access vault ([d882fdf](https://github.com/ZeitOnline/kustomize/commit/d882fdf2de54762552a1b8ca2f54078b053165da))
* use better name for the "nightwatch secrets" ([c2313de](https://github.com/ZeitOnline/kustomize/commit/c2313de34cf7e30f31a0396ce4cd31d2d7d3ccbc))
