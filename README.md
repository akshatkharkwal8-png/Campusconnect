# CampusConnect — Campus Events & Clubs Portal

A polished Flask + SQLite website for discovering campus events, exploring clubs, registering for events, and managing events through a simple admin dashboard.

## Features
- Responsive landing page with dashboard-style statistics
- Event listing with search and category filters
- Club directory
- Registration form with duplicate-registration prevention
- SQLite relational database created automatically
- Admin page to add events and update event status
- Registration list page
- ER diagram supplied in `docs/er_diagram.svg`

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create a virtual environment (recommended):
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the website: `python app.py`
6. Open `http://127.0.0.1:5000`

The database file `campusconnect.db` is created in this folder the first time the app runs. Sample clubs, events, students, and registrations are inserted automatically on first run.

## Pages
- `/` — Home
- `/events` — Events and registration
- `/clubs` — Club directory
- `/admin` — Add events and manage event status (demo admin; not password-protected)
- `/registrations` — Registration list

## Database design
- `clubs` 1-to-many `events`
- `students` many-to-many `events` through `registrations`
- `registrations` has a composite uniqueness rule on `(student_id, event_id)` so a student cannot register twice for the same event.
- Foreign keys maintain referential integrity.

## Important for submission
This is a classroom/demo project. The admin route is intentionally simple and is **not production-secure**. For a real deployment, add login/authentication, CSRF protection, environment-based secrets, and stronger validation.
