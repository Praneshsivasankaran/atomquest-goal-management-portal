# Deployment

## Option A: Render

1. Push this repo to a public GitHub repository.
2. In Render, create a new Web Service from the repo.
3. Render can detect `render.yaml`; otherwise use:
   - Runtime: Python
   - Build command: leave blank
   - Start command: `python app/server.py --host 0.0.0.0 --port $PORT`
4. Set `APP_SECRET` to any long random value.

The demo uses SQLite so it can run cheaply with no database setup. For a longer-lived hosted app, move the schema to PostgreSQL and set a persistent `DATABASE_URL`.

## Option B: Railway

1. Create a new project from the GitHub repo.
2. Use the included `Procfile`.
3. Add `APP_SECRET` in environment variables.
4. Deploy and use the generated public URL.

## Local Reset

```powershell
python app/server.py --seed-only
python app/server.py --port 8000
```

