# Backend

From this directory:

```sh
uv sync
cp onw_backend/config-sample.py onw_backend/config.py
uv run python manage.py migrate
uv run python manage.py runserver
```

Set the local secret and `OPS_DURATION` in `onw_backend/config.py`.

Apply schema updates with `uv run python manage.py migrate`. The hunter
shooting phase adds a nullable `shot_target` field; existing games retain
their original roles and votes.

From the repository root, run the checks with:

```sh
backend/.venv/bin/python backend/manage.py test room
backend/.venv/bin/python backend/checks/concurrency.py
npm --prefix frontend test
npm --prefix frontend run build
```

Tests use separate temporary databases; they do not alter the development DB.
