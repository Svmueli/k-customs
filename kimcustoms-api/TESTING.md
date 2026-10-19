# Payment integration tests

The default focused suite can run with a temporary SQLite database, but it does
not prove PostgreSQL row-locking or partial-unique-index behaviour:

```bash
venv/bin/python manage.py test payments orders --settings=config.settings_test
```

Run PostgreSQL integration tests only against an isolated database:

```bash
export DB_NAME=kimcustoms_test
export DB_USER=...
export DB_PASSWORD=...
export DB_HOST=127.0.0.1
export DB_PORT=5432
venv/bin/python manage.py test payments.tests.PostgreSQLPaymentIntegrationTests
```

The database role must be allowed to create and drop the Django test database.
