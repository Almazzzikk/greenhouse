import sqlite3, os, random, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, g, request, session, redirect, url_for, render_template_string, abort, flash
from werkzeug.security import generate_password_hash, check_password_hash

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "greenhouse.db")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@_%._%'),
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin','user'))
);
CREATE TABLE devices (
  device_id INTEGER PRIMARY KEY AUTOINCREMENT,
  serial_no TEXT NOT NULL UNIQUE,
  plant_type TEXT NOT NULL,
  location TEXT NOT NULL
);
CREATE TABLE user_devices (
  user_id INTEGER NOT NULL,
  device_id INTEGER NOT NULL,
  PRIMARY KEY (user_id, device_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
CREATE TABLE readings (
  reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id INTEGER NOT NULL,
  recorded_at TEXT NOT NULL,
  temperature_c REAL NOT NULL CHECK (temperature_c BETWEEN -20 AND 60),
  humidity_pct REAL NOT NULL CHECK (humidity_pct BETWEEN 0 AND 100),
  FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);
"""

def init_db():
    if os.path.exists(DB):
        return
    random.seed(1)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    names = ["Aidar Serikbayev", "Dinara Akhmetova", "Yerzhan Nurtazin", "Aigerim Kenzhebek", "Maksat Omarov",
             "Saltanat Bekova", "Timur Zhumabayev", "Zhanar Abdrakhman", "Nurlan Sadykov", "Dana Ismailova"]
    emails = ["admin@greenhouse.kz", "user@greenhouse.kz", "yerzhan@greenhouse.kz", "aigerim@greenhouse.kz",
              "maksat@greenhouse.kz", "saltanat@greenhouse.kz", "timur@greenhouse.kz", "zhanar@greenhouse.kz",
              "nurlan@greenhouse.kz", "dana@greenhouse.kz"]
    for i, (n, e) in enumerate(zip(names, emails)):
        pw = "admin123" if i == 0 else "user123" if i == 1 else "pass1234"
        con.execute("INSERT INTO users(email, password_hash, full_name, role) VALUES (?,?,?,?)",
                    (e, generate_password_hash(pw), n, "admin" if i == 0 else "user"))
    plants = ["Tomatoes", "Cucumbers", "Peppers", "Strawberries", "Dill", "Lettuce", "Eggplants", "Basil", "Mint", "Radish"]
    for i, p in enumerate(plants, 1):
        con.execute("INSERT INTO devices(serial_no, plant_type, location) VALUES (?,?,?)",
                    (f"GH-{1000 + i}", p, f"Section {'ABCDE'[(i - 1) // 2]}"))
    pairs = set()
    while len(pairs) < 20:
        pairs.add((random.randint(1, 10), random.randint(1, 10)))
    con.executemany("INSERT INTO user_devices VALUES (?,?)", sorted(pairs))
    start = datetime(2026, 10, 1)
    for i in range(120):
        con.execute("INSERT INTO readings(device_id, recorded_at, temperature_c, humidity_pct) VALUES (?,?,?,?)",
                    (random.randint(1, 10), (start + timedelta(hours=i * 3)).strftime("%Y-%m-%d %H:%M"),
                     round(random.gauss(24, 3), 1), round(min(95, max(35, random.gauss(65, 10))), 1)))
    con.commit()
    con.close()

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()

def login_required(role=None):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            if "uid" not in session:
                return redirect(url_for("login"))
            if role and session["role"] != role:
                abort(403)
            return f(*a, **kw)
        return wrapper
    return deco

# MEDIA_MODE=before  -> serves the heavy 4000 px JPEG at 300 px (for the "before" measurement)
# MEDIA_MODE=after   -> serves optimised responsive WebP (default)
MEDIA_MODE = os.environ.get("MEDIA_MODE", "after")
TEMP_RANGE = (15, 30)   # degrees C, outside = warning
HUM_RANGE = (40, 85)    # percent, outside = warning

def flags(t, h):
    out = []
    if t > TEMP_RANGE[1]: out.append("Temperature high")
    if t < TEMP_RANGE[0]: out.append("Temperature low")
    if h > HUM_RANGE[1]: out.append("Humidity high")
    if h < HUM_RANGE[0]: out.append("Humidity low")
    return out

BASE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Smart Greenhouse</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="/static/style.css"></head><body>
{% macro ic(n) %}<svg class="icon" aria-hidden="true" focusable="false"><use href="/static/icons.svg#i-{{ n }}"></use></svg>{% endmacro %}
<a class="skip" href="#main">Skip to content</a>
<header class="bar"><div class="bar-in">
  <a class="brand" href="/"><img src="/static/logo.svg" alt="" width="32" height="32">Smart Greenhouse</a>
  {% if session.uid %}
  <nav class="nav" aria-label="Main">
    <a href="/readings">{{ ic('list') }}Readings</a>
    <a href="/add">{{ ic('plus') }}Add reading</a>
    <button type="button" id="sound-toggle" aria-pressed="false">{{ ic('bell-off') }}<span id="sound-label">Sound alerts: off</span></button>
    <a href="/logout">{{ ic('out') }}Logout</a>
  </nav>
  <p class="who">{{ session.name }} ({{ session.role }})</p>
  {% endif %}
</div></header>
<main id="main">
{% for cat, m in get_flashed_messages(with_categories=true) %}
  <p class="msg {{ 'warn' if cat != 'ok' }}" role="{{ 'status' if cat == 'ok' else 'alert' }}"{% if cat == 'alert' %} data-alert="1"{% endif %}>
    {{ ic('check' if cat == 'ok' else 'alert') }}<span>{{ m }}</span></p>
{% endfor %}
{% block body %}{% endblock %}
</main>
<audio id="alert-sound" preload="none"><source src="/static/audio/alert.mp3" type="audio/mpeg"><source src="/static/audio/alert.wav" type="audio/wav"></audio>
<script src="/static/app.js"></script>
</body></html>"""

def page(body, **ctx):
    return render_template_string(BASE.replace("{% block body %}{% endblock %}", body), **ctx)

@app.route("/")
def index():
    return redirect(url_for("readings"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT user_id, full_name, password_hash, role FROM users WHERE email = ?",
                         (request.form["email"].strip().lower(),)).fetchone()
        if u and check_password_hash(u["password_hash"], request.form["password"]):
            session.clear()
            session.update(uid=u["user_id"], name=u["full_name"], role=u["role"])
            return redirect(url_for("readings"))
        flash("Wrong email or password. Check both and try again.", "warn")
    return page("""
    <div class="hero{{ ' raw' if before }}">
      {% if before %}
      <img src="/static/img/hero_original.jpg" width="300" height="150"
           alt="Rows of green plants inside a greenhouse with a glass frame">
      {% else %}
      <img src="/static/img/hero-960.webp" srcset="/static/img/hero-480.webp 480w, /static/img/hero-960.webp 960w"
           sizes="(max-width: 1000px) 100vw, 928px" width="960" height="480"
           alt="Rows of green plants inside a greenhouse with a glass frame">
      {% endif %}
      <div class="hero-text"><strong>Temperature and humidity, section by section</strong>
      <span>Log in to see the latest readings.</span></div>
    </div>
    <h1>Log in</h1>
    <form method="post" class="card narrow">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" autocomplete="username" required>
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required>
      <button class="btn">{{ ic('out') }}Log in</button>
    </form>""", before=(MEDIA_MODE == "before"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/readings")
@login_required()
def readings():
    dev = request.args.get("device", type=int)
    sql = ("SELECT r.reading_id, d.serial_no, d.plant_type, r.recorded_at, r.temperature_c, r.humidity_pct "
           "FROM readings r JOIN devices d ON d.device_id = r.device_id ")
    params = ()
    if dev:
        sql += "WHERE r.device_id = ? "
        params = (dev,)
    rows = [dict(r, flags=flags(r["temperature_c"], r["humidity_pct"]))
            for r in db().execute(sql + "ORDER BY r.recorded_at DESC LIMIT 50", params).fetchall()]
    devices = db().execute("SELECT device_id, serial_no FROM devices").fetchall()
    return page("""
    <h1>Readings</h1>
    <form class="filter">
      <div><label for="device">Device</label>
      <select id="device" name="device"><option value="">All devices</option>
      {% for d in devices %}<option value="{{ d.device_id }}" {{ 'selected' if d.device_id == dev }}>{{ d.serial_no }}</option>{% endfor %}</select></div>
      <button class="btn">Filter</button>
    </form>
    <p class="sum">Showing {{ rows|length }} latest readings, {{ rows|selectattr('flags')|list|length }} need attention.</p>
    <table>
      <caption class="sr">Latest sensor readings</caption>
      <thead><tr><th scope="col">ID<th scope="col">Device<th scope="col">Plant<th scope="col">Time
        <th scope="col">{{ ic('temp') }} Temp &deg;C<th scope="col">{{ ic('drop') }} Humidity %<th scope="col">Status
        {% if session.role == 'admin' %}<th scope="col"><span class="sr">Actions</span>{% endif %}</tr></thead>
      <tbody>
      {% for r in rows %}<tr>
        <td data-label="ID">{{ r.reading_id }}
        <td data-label="Device">{{ r.serial_no }}
        <td data-label="Plant">{{ r.plant_type }}
        <td data-label="Time">{{ r.recorded_at }}
        <td data-label="Temp &deg;C">{{ r.temperature_c }}
        <td data-label="Humidity %">{{ r.humidity_pct }}
        <td data-label="Status">{% if r.flags %}<span class="badge">{{ ic('alert') }}{{ r.flags|join(', ') }}</span>{% else %}<span class="ok">{{ ic('check') }}OK</span>{% endif %}
        {% if session.role == 'admin' %}<td data-label="">
          <form method="post" action="/delete/{{ r.reading_id }}">
            <button class="btn danger" aria-label="Delete reading {{ r.reading_id }}">{{ ic('trash') }}Delete</button></form>{% endif %}
      </tr>{% endfor %}
      </tbody></table>""", rows=rows, devices=devices, dev=dev)

@app.route("/add", methods=["GET", "POST"])
@login_required()
def add():
    if request.method == "POST":
        try:
            dev = int(request.form["device"])
            t = float(request.form["t"])
            h = float(request.form["h"])
            if not (-20 <= t <= 60 and 0 <= h <= 100):
                raise ValueError
            db().execute("INSERT INTO readings(device_id, recorded_at, temperature_c, humidity_pct) "
                         "VALUES (?, datetime('now','localtime'), ?, ?)", (dev, t, h))
            db().commit()
            d = db().execute("SELECT serial_no FROM devices WHERE device_id = ?", (dev,)).fetchone()
            flash(f"Reading saved for {d['serial_no'] if d else 'device'}.", "ok")
            f = flags(t, h)
            if f:
                flash("Check the plants: " + ", ".join(f).lower() + f" ({t} \u00b0C, {h} %).", "alert")
            return redirect(url_for("readings"))
        except (ValueError, sqlite3.IntegrityError):
            flash("Invalid data. Temperature must be -20 to 60 \u00b0C and humidity 0 to 100 %.", "warn")
    devices = db().execute("SELECT device_id, serial_no FROM devices").fetchall()
    return page("""
    <h1>Add reading</h1>
    <form method="post" class="card narrow">
      <label for="device">Device</label>
      <select id="device" name="device">{% for d in devices %}<option value="{{ d.device_id }}">{{ d.serial_no }}</option>{% endfor %}</select>
      <label for="t">Temperature, &deg;C</label>
      <input id="t" name="t" type="number" step="0.1" min="-20" max="60" inputmode="decimal" required>
      <p class="hint">Warning above 30 or below 15.</p>
      <label for="h">Humidity, %</label>
      <input id="h" name="h" type="number" step="0.1" min="0" max="100" inputmode="decimal" required>
      <p class="hint">Warning above 85 or below 40.</p>
      <button class="btn">{{ ic('check') }}Save reading</button>
    </form>""", devices=devices)

@app.route("/delete/<int:rid>", methods=["POST"])
@login_required("admin")
def delete(rid):
    db().execute("DELETE FROM readings WHERE reading_id = ?", (rid,))
    db().commit()
    return redirect(url_for("readings"))

if __name__ == "__main__":
    init_db()
    app.run()
