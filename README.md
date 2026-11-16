# Smart Greenhouse

A small web app to record and watch temperature and humidity readings in a greenhouse.
It was made as the Final Project for the ICT course by **Kozhabayev Almaz** (individual project).

The sensors are **simulated**: readings are typed in by a person, plus 120 generated readings in the test database.

## What it does

- Log in with email and password (two roles: `admin` and `user`).
- See the 50 latest readings, and filter by device.
- Add a new reading. The server checks the values.
- Get a red warning (banner, icon and text) when a value is out of range:
  - temperature above 30 °C or below 15 °C
  - humidity above 85 % or below 40 %
- Admin only: delete a reading.
- Optional sound alert (off by default).
- Works on phones: the table becomes cards on small screens.

## Tech

- Python 3 and Flask
- SQLite (file `greenhouse.db`)
- HTML, CSS, a little JavaScript
- Optimised images (WebP), SVG icons, MP3/WAV sound

## Folder structure

```
app.py
greenhouse.db
requirements.txt
static/
  style.css
  app.js
  favicon.svg
  icons.svg
  logo.svg
  img/
    hero-480.webp
    hero-960.webp
    hero_original.jpg
  audio/
    alert.mp3
    alert.wav
```

The images must be in `static/img/` and the sounds in `static/audio/`, or the pages will not find them.

## How to run

1. Install Python 3.9 or newer.
2. Install Flask:

   ```
   pip install -r requirements.txt
   ```

3. Start the app:

   ```
   python app.py
   ```

   If `greenhouse.db` does not exist, it is created with test data.
   Use `python app.py`. The command `flask run` does **not** create the database.

4. Open <http://127.0.0.1:5000> in your browser.

## Test accounts

| Role  | Email                 | Password |
|-------|-----------------------|----------|
| Admin | admin@greenhouse.kz   | admin123 |
| User  | user@greenhouse.kz    | user123  |

Eight more users exist (`yerzhan`, `aigerim`, `maksat`, `saltanat`, `timur`, `zhanar`, `nurlan`, `dana` at `@greenhouse.kz`). Their password is `pass1234`.

**Change these passwords before any real use.**

## Quick check

1. Log in as the user and open **Add reading**.
2. Save temperature `31` and humidity `60`. A red warning must appear.
3. Save temperature `22` and humidity `60`. No warning must appear.
4. Log in as the admin. A **Delete** button is visible next to each reading. The user does not see it.

## Image test mode

The login page can show the heavy original image, to compare page speed:

- Windows PowerShell: `$env:MEDIA_MODE="before"; python app.py`
- Windows cmd: `set MEDIA_MODE=before` and then `python app.py`
- Mac or Linux: `MEDIA_MODE=before python app.py`

Without `MEDIA_MODE`, the optimised WebP images are used.

## Security notes

- Passwords are stored as hashes.
- All SQL queries use parameters.
- Values are checked in the browser, on the server, and by database rules.
- Delete is allowed only for the admin (other users get error 403).

## Known limits

- No real sensors (simulated data only).
- No HTTPS and no CSRF protection.
- All users see all devices. The table `user_devices` exists but is not used yet.
- The secret key changes at every start, so users are logged out after a restart.
- Flask development server and SQLite are not meant for many users.

## Author

Kozhabayev Almaz, ICT course, Final Project (individual, agreed with the instructor).
