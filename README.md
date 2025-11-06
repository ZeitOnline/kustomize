# 'kustomize' components

This repository contains reusable [kustomize](https://kustomize.io/) components for Kubernetes deployments. Below is a list of the available components:

- [cloud-sql-proxy](components/cloud-sql-proxy/): deploys a [Cloud SQL Proxy](https://github.com/GoogleCloudPlatform/cloud-sql-proxy) for secure database connections
- [db-sync](components/db-sync/): handles PostgreSQL database "syncs", typically between 'staging' and 'devel'
- [db-upgrade](components/db-upgrade/): handles PostgreSQL upgrades and migrations between instances
- [gcs-bucket-proxy](components/gcs-bucket-proxy/): provides a proxy for easy access to Google Cloud Storage buckets
- [migrator](components/migrator/): runs database migration jobs using [alembic](https://alembic.sqlalchemy.org)
- [nightwatch](components/nightwatch/): integrates our "[Nachtwache](https://docs.zeit.de/monitoring/howto/nightwatch/)" tests
- [oauth2-proxy](components/oauth2-proxy/): integrates [OAuth2 Proxy](https://oauth2-proxy.github.io/oauth2-proxy/) to authenticate against [Keycloak](https://docs.zeit.de/keycloak/)
- [pg-services](components/pg-services/): provides database credentials as PostgreSQL "[connection service files](https://www.postgresql.org/docs/17/libpq-pgservice.html)"
- [postgresql](components/postgresql/): provides PostgreSQL database deployments intended for testing
- [postgrest](components/postgrest/): provides [PostgREST](https://docs.postgrest.org/) deployments
- [testrunner](components/testrunner/): run project test suites in Kubernetes
- [wait-for-migrations](components/wait-for-migrations/): waits for database migrations to complete before starting dependent services

Each component is located in its dedicated subdirectory under [`components/`](components/).
