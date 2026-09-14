# One Night Werewolf

A Vue 3 frontend and Django backend for playing One Night Werewolf with custom house rules. The backend uses SQLite; the frontend polls the HTTP API for game state.

## Prerequisites

- Python 3.12 or newer and `uv` for backend dependencies.
- Node.js 22 or newer and npm for the frontend.

Run the following commands from the repository root unless a step says otherwise.

## First-time setup

Install the backend dependencies and create your local configuration:

```sh
cd backend
uv sync
cp -n onw_backend/config-sample.py onw_backend/config.py
```

Edit `backend/onw_backend/config.py` (relative to the repository root):

- Replace `SECRET_KEY = "REPLACE_ME"` with a random secret. From `backend/`, generate one with `uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
- Keep `DEBUG = True` for local development.
- Set `OPS_DURATION` to the desired night-action duration. The sample uses `timedelta(seconds=60)`; use `timedelta(seconds=15)` for shorter rounds. Restart the backend after changing it.
- Leave the sample host and origin settings in place for the development proxy below.

The local configuration and SQLite database are ignored by Git. The copy command preserves an existing configuration.

Create the database, then install frontend dependencies:

```sh
# Still in backend/
uv run python manage.py migrate
cd ../frontend
npm ci
```

## Run development servers

Keep both servers running in separate terminals.

**Terminal 1 — backend**, starting from the repository root:

```sh
cd backend
uv run python manage.py runserver 8000
```

**Terminal 2 — frontend**, starting from the repository root:

```sh
cd frontend
npm run dev -- --port 5173 --strictPort
```

Open **http://localhost:5173**. Vite forwards `/api/` requests to Django at `http://localhost:8000`; no separate database service is needed. Stop either server with `Ctrl+C`.

For phones or other computers on the same network, open `http://<your-computer-LAN-IP>:5173`. Vite already listens on all interfaces. Allow incoming connections to port 5173 through your local firewall if needed; Django can stay on localhost because Vite proxies the requests.

## Try a game

1. Create a room, then join it from other browsers, private windows, or devices using different player IDs. Credentials are saved in localStorage, so ordinary tabs in the same browser share saved credentials.
2. Use 3–10 players. New rooms start with nine cards: two werewolves, two villagers, and one each of the other five supported roles.
3. The host adjusts the draft and clicks **提交板子** to publish it. The submitted deck must contain exactly the player count plus three center cards before starting; the default fits six players.
4. Start the game, submit night actions, then reveal and vote. Each room holds one game; create a new room for another round.

## Checks

From the repository root, after setup:

```sh
backend/.venv/bin/python backend/manage.py test room
backend/.venv/bin/python backend/checks/concurrency.py
npm --prefix frontend test
npm --prefix frontend run build
```

Backend tests use separate test databases. The frontend production build is written to `frontend/dist/`.

## Troubleshooting

- **Missing `onw_backend.config`:** complete the configuration copy in first-time setup.
- **Missing database tables:** run `uv run python manage.py migrate` from `backend/`.
- **API connection errors:** check that Django is running on port 8000 and open the app through Vite on port 5173.
- **CSRF rejection:** refresh the page and use the Vite URL consistently. If you changed ports or origins, check the proxy in `frontend/vite.config.js` and the origin settings in your backend configuration.
- **Schema errors with an older development database:** this project does not maintain compatibility with older development schemas. Stop Django, move `backend/db.sqlite3` to a backup location, and run migrations again to create an empty database. Existing rooms remain only in the backup.
