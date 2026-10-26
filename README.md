# URL Shortener API

A small FastAPI URL-shortening service backed by SQLite and SQLAlchemy.

## Features
- `POST /links`: create a short link; optional custom alias and timezone-aware expiry.
- `GET /{code}`: HTTP 302 redirect; unknown codes return 404, expired links return 410.
- `GET /links/{code}/stats`: click count and last-click timestamp.
- URL scheme/hostname validation, unique aliases, helpful errors.
- Pytest automated tests.

## Run locally

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for interactive API docs.

## Run tests

```bash
pytest -q
```

The test suite uses a temporary SQLite database, separate from the development database.

## Example requests

Create a link:

```bash
curl -X POST http://127.0.0.1:8000/links ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://example.com/products?id=123\",\"custom_alias\":\"product-123\"}"
```

Create with expiry (expiry must be in the future and include a timezone):

```json
{
  "url": "https://example.com",
  "expires_at": "2030-01-01T00:00:00+00:00"
}
```

Get stats:

```bash
curl http://127.0.0.1:8000/links/product-123/stats
```

## API contract

### `POST /links` — 201 Created

Request body:

```json
{
  "url": "https://example.com/article",
  "custom_alias": "my-article",
  "expires_at": "2030-01-01T00:00:00+00:00"
}
```

`custom_alias` and `expires_at` are optional. Alias characters: letters, digits, `_`, `-`; length 3–64.

Response body includes `code`, `short_url`, `original_url`, and `expires_at`.

Errors:
- `422`: invalid URL, invalid alias, or expiry not in the future / missing timezone.
- `409`: alias already exists.
- `503`: random code generation collision could not be resolved.

### `GET /{code}` — 302 Found
- Known and active: redirects to original URL and increments click count.
- Unknown: `404 Not Found`.
- Expired: `410 Gone`.

### `GET /links/{code}/stats` — 200 OK
Returns `code`, `original_url`, `total_clicks`, and `last_clicked_at` (null before the first click). Unknown code returns 404.

## Notes for production
For a production deployment, consider Postgres, migrations (Alembic), rate limiting, abuse/malware URL screening, structured logging, and atomic click increments for high concurrency. This demo validates URL shape but does not fetch or verify that a destination is safe or reachable.
