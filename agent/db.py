import fdb
from config.settings import get_fb_dsn, FB_USER, FB_PASSWORD

_connection = None

def get_connection():
    global _connection
    if _connection is None:
        dsn = get_fb_dsn()
        _connection = fdb.connect(
            dsn=dsn,
            user=FB_USER,
            password=FB_PASSWORD,
            charset="WIN1252",
        )
    return _connection

def close_connection():
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None

def query(sql, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params or [])
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    return columns, rows

def execute(sql, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(sql, params or [])
    conn.commit()
    cur.close()
