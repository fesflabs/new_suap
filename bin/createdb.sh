#!/usr/bin/env bash
set -axe
DATABASE_NAME="${1:-suap_dev}"
python manage.py test --nocoverage --noinput --failfast comum.tests.CreateDatabaseTestCase --keepdb
psql -U postgres -c "alter database test_suap_dev rename to $DATABASE_NAME"
python manage.py migrate --fake