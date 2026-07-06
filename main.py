"""
Local development entry point.

Run this file directly in PyCharm (Right-click -> Run 'main') or with:
    python main.py

This imports the Flask `app` object defined in api/index.py (the same
object Vercel uses in production) so behavior is identical locally and
in deployment. By default it uses a local SQLite database (local.db);
set the DATABASE_URL environment variable to point at your Neon
Postgres instance instead.
"""
import os
from dotenv import load_dotenv

# Load variables from a .env file in the project root, if present
load_dotenv()

from api.index import app  # noqa: E402  (import after load_dotenv on purpose)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
