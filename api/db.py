import sqlite3
from pathlib import Path
DB = Path(__file__).parent / "tinytravel.db"
def conn():
    c = sqlite3.connect(DB)
    c.execute("create table if not exists searches (id text primary key, request text, created_at text)")
    c.execute("create table if not exists offers (id text primary key, search_id text, body text)")
    return c
