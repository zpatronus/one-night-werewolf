# Backend

From this directory:

```sh
uv sync
cp onw_backend/config-sample.py onw_backend/config.py
uv run python manage.py migrate
uv run python manage.py runserver
```

Set the local secret and `OPS_DURATION` in `onw_backend/config.py`.

The development schema has one initial migration. Old development databases
must be deleted and recreated when switching to this schema; no historical
migration compatibility is maintained.

From the repository root, run the checks with:

```sh
backend/.venv/bin/python backend/manage.py test room
backend/.venv/bin/python backend/checks/concurrency.py
npm --prefix frontend test
npm --prefix frontend run build
```

Tests use separate temporary databases; they do not alter the development DB.
