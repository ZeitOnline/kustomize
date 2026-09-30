#!/bin/sh
#
# Mark the migrations up to a given version as applied, for a database that
# already carries the schema.  goose has no `stamp` command, so the rows go in
# directly.  Everything after the given version is left for `goose up`.
#
#   ./stamp.sh migrations 20230915134643
#
# Connects like any other libpq client, i.e. via `PGSERVICE`/`PG*`.

set -e

directory=${1:?usage: $(basename "$0") <migrations-dir> <last-applied-version>}
applied=${2:?usage: $(basename "$0") <migrations-dir> <last-applied-version>}

psql --quiet --set=ON_ERROR_STOP=on <<'SQL'
CREATE TABLE IF NOT EXISTS goose_db_version (
    id serial PRIMARY KEY,
    version_id bigint NOT NULL,
    is_applied boolean NOT NULL,
    tstamp timestamp DEFAULT now()
);
INSERT INTO goose_db_version (version_id, is_applied)
    SELECT 0, true
    WHERE NOT EXISTS (SELECT 1 FROM goose_db_version WHERE version_id = 0);
SQL

for file in "$directory"/*.sql; do
    version=$(basename "$file" | sed -E 's/^([0-9]+)_.*/\1/')
    [ "$version" -le "$applied" ] || continue
    psql --quiet --set=ON_ERROR_STOP=on -c "
        INSERT INTO goose_db_version (version_id, is_applied)
            SELECT $version, true WHERE NOT EXISTS (
                SELECT 1 FROM goose_db_version WHERE version_id = $version);"
    echo "stamped $version"
done
