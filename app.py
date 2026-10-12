from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "campusconnect.db"
app = Flask(__name__)
app.secret_key = "replace-this-with-a-random-secret-key"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS clubs (
            club_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            accent TEXT NOT NULL DEFAULT '#7c5cff'
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            club_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            venue TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 100 CHECK(capacity > 0),
            status TEXT NOT NULL DEFAULT 'Upcoming' CHECK(status IN ('Upcoming','Completed','Cancelled')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            course TEXT NOT NULL,
            year_of_study INTEGER NOT NULL CHECK(year_of_study BETWEEN 1 AND 6)
        );
        CREATE TABLE IF NOT EXISTS registrations (
            registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            attendance_status TEXT NOT NULL DEFAULT 'Registered'
                CHECK(attendance_status IN ('Registered','Attended','No-show','Cancelled')),
            UNIQUE(student_id, event_id),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
        );
        """)
        if db.execute("SELECT COUNT(*) FROM clubs").fetchone()[0] == 0:
            db.executemany("INSERT INTO clubs(name,category,description,accent) VALUES(?,?,?,?)", [
                ("The Culture Collective","Culture","Music, dance, theatre and the moments that bring campus together.","#8b5cf6"),
                ("Tech & Innovation Society","Technology","Build, experiment, learn and turn ideas into useful projects.","#06b6d4"),
                ("Green Campus Network","Sustainability","Small actions, greener spaces and a more responsible campus.","#22c55e"),
                ("The Speaker's Forum","Debate & Ideas","A space for sharp arguments, thoughtful dialogue and public speaking.","#f97316")
            ])
            clubs = {r["name"]: r["club_id"] for r in db.execute("SELECT club_id,name FROM clubs")}
            db.executemany("""INSERT INTO events
                (club_id,title,description,event_date,event_time,venue,capacity,status)
                VALUES(?,?,?,?,?,?,?,?)""", [
                (clubs["The Culture Collective"],"Afterglow: Open-Air Music Night","An evening of live sets, student performers and campus energy. Bring your friends and discover your next favourite artist.","2026-10-24","19:00","Central Lawn",250,"Upcoming"),
                (clubs["Tech & Innovation Society"],"Buildathon: Ideas to Interface","A hands-on sprint where teams prototype a solution to a real student-life problem. Beginners are welcome.","2026-10-28","10:00","Innovation Lab",80,"Upcoming"),
                (clubs["Green Campus Network"],"Green Miles Campus Walk","A guided campus walk with quick sustainability challenges and a community clean-up.","2026-11-02","07:30","Main Gate",60,"Upcoming"),
                (clubs["The Speaker's Forum"],"The Great Campus Debate","Two teams, one motion, and a room full of arguments. Come compete or cheer from the audience.","2026-11-06","17:00","Seminar Hall 2",120,"Upcoming"),
                (clubs["The Culture Collective"],"Monsoon Memories: Jam Session","An informal acoustic jam for singers, instrumentalists and anyone who loves live music.","2026-09-18","18:30","Amphitheatre",100,"Completed")
            ])
            db.executemany("INSERT INTO students(full_name,email,course,year_of_study) VALUES(?,?,?,?)", [
                ("Aarav Mehta","aarav.demo@example.com","IPM",2),
                ("Diya Rao","diya.demo@example.com","BA LLB",3),
                ("Kabir Sharma","kabir.demo@example.com","IPM",1)
            ])
            students = {r["email"]: r["student_id"] for r in db.execute("SELECT student_id,email FROM students")}
            events = {r["title"]: r["event_id"] for r in db.execute("SELECT event_id,title FROM events")}
            db.executemany("INSERT OR IGNORE INTO registrations(student_id,event_id,attendance_status) VALUES(?,?,?)", [
                (students["aarav.demo@example.com"], events["Afterglow: Open-Air Music Night"], "Registered"),
                (students["diya.demo@example.com"], events["Buildathon: Ideas to Interface"], "Registered"),
                (students["kabir.demo@example.com"], events["The Great Campus Debate"], "Registered"),
            ])

@app.route("/")
def index():
    with get_db() as db:
        events = db.execute("""
            SELECT e.*, c.name AS club_name, c.accent,
            (SELECT COUNT(*) FROM registrations r WHERE r.event_id=e.event_id AND r.attendance_status!='Cancelled') AS registered
            FROM events e JOIN clubs c ON c.club_id=e.club_id
            WHERE e.status='Upcoming' ORDER BY e.event_date, e.event_time LIMIT 4
        """).fetchall()
        counts = {
            "events": db.execute("SELECT COUNT(*) FROM events WHERE status='Upcoming'").fetchone()[0],
            "clubs": db.execute("SELECT COUNT(*) FROM clubs").fetchone()[0],
            "students": db.execute("SELECT COUNT(*) FROM students").fetchone()[0],
            "registrations": db.execute("SELECT COUNT(*) FROM registrations WHERE attendance_status!='Cancelled'").fetchone()[0]
        }
        clubs = db.execute("SELECT * FROM clubs ORDER BY name").fetchall()
    return render_template("index.html", events=events, counts=counts, clubs=clubs)

@app.route("/events")
def events_page():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    with get_db() as db:
        sql = """SELECT e.*, c.name AS club_name, c.category, c.accent,
                 (SELECT COUNT(*) FROM registrations r WHERE r.event_id=e.event_id AND r.attendance_status!='Cancelled') AS registered
                 FROM events e JOIN clubs c ON c.club_id=e.club_id WHERE e.status != 'Cancelled'"""
        params = []
        if search:
            sql += " AND (e.title LIKE ? OR e.description LIKE ? OR e.venue LIKE ?)"
            params += [f"%{search}%"] * 3
        if category:
            sql += " AND c.category = ?"
            params.append(category)
        sql += " ORDER BY CASE WHEN e.status='Upcoming' THEN 0 ELSE 1 END, e.event_date"
        events = db.execute(sql, params).fetchall()
        categories = db.execute("SELECT DISTINCT category FROM clubs ORDER BY category").fetchall()
        clubs = db.execute("SELECT * FROM clubs ORDER BY name").fetchall()
    return render_template("events.html", events=events, categories=categories, clubs=clubs, search=search, selected_category=category)

@app.route("/clubs")
def clubs_page():
    with get_db() as db:
        clubs = db.execute("""SELECT c.*, COUNT(DISTINCT e.event_id) AS event_count
            FROM clubs c LEFT JOIN events e ON e.club_id=c.club_id GROUP BY c.club_id ORDER BY c.name""").fetchall()
    return render_template("clubs.html", clubs=clubs)

@app.route("/register/<int:event_id>", methods=["POST"])
def register(event_id):
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    course = request.form.get("course", "").strip()
    year = request.form.get("year", "").strip()
    if not all([name, email, course, year]):
        flash("Please complete every field before registering.", "error")
        return redirect(request.referrer or url_for("events_page"))
    try:
        year_num = int(year)
        if not 1 <= year_num <= 6:
            raise ValueError()
    except ValueError:
        flash("Year of study must be between 1 and 6.", "error")
        return redirect(request.referrer or url_for("events_page"))
    try:
        with get_db() as db:
            db.execute("INSERT OR IGNORE INTO students(full_name,email,course,year_of_study) VALUES(?,?,?,?)",
                       (name, email, course, year_num))
            student = db.execute("SELECT student_id FROM students WHERE email=?", (email,)).fetchone()
            event = db.execute("SELECT title,capacity,status FROM events WHERE event_id=?", (event_id,)).fetchone()
            if not event or event["status"] != "Upcoming":
                flash("This event is not open for registration.", "error")
            else:
                count = db.execute("SELECT COUNT(*) FROM registrations WHERE event_id=? AND attendance_status!='Cancelled'", (event_id,)).fetchone()[0]
                if count >= event["capacity"]:
                    flash("Sorry, this event has reached capacity.", "error")
                else:
                    cur = db.execute("INSERT OR IGNORE INTO registrations(student_id,event_id) VALUES(?,?)",
                                     (student["student_id"], event_id))
                    if cur.rowcount:
                        flash(f"You're on the list for {event['title']}! See you there.", "success")
                    else:
                        flash("That email is already registered for this event.", "error")
    except sqlite3.IntegrityError:
        flash("We couldn't complete the registration. Please check your details.", "error")
    return redirect(request.referrer or url_for("events_page"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        date = request.form.get("event_date", "")
        time = request.form.get("event_time", "")
        venue = request.form.get("venue", "").strip()
        club_id = request.form.get("club_id", "")
        capacity = request.form.get("capacity", "100")
        try:
            capacity = int(capacity)
            if not all([title, description, date, time, venue, club_id]) or capacity < 1:
                raise ValueError()
            with get_db() as db:
                db.execute("""INSERT INTO events(club_id,title,description,event_date,event_time,venue,capacity)
                    VALUES(?,?,?,?,?,?,?)""", (int(club_id), title, description, date, time, venue, capacity))
            flash("Event created successfully.", "success")
            return redirect(url_for("admin"))
        except (ValueError, sqlite3.IntegrityError):
            flash("Please check the event details and try again.", "error")
    with get_db() as db:
        clubs = db.execute("SELECT * FROM clubs ORDER BY name").fetchall()
        events = db.execute("""SELECT e.*, c.name AS club_name,
            (SELECT COUNT(*) FROM registrations r WHERE r.event_id=e.event_id AND r.attendance_status!='Cancelled') AS registered
            FROM events e JOIN clubs c ON c.club_id=e.club_id ORDER BY e.event_date DESC""").fetchall()
        registration_count = db.execute("SELECT COUNT(*) FROM registrations").fetchone()[0]
        student_count = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    return render_template("admin.html", clubs=clubs, events=events, registration_count=registration_count, student_count=student_count)

@app.route("/event/<int:event_id>/status", methods=["POST"])
def update_status(event_id):
    status = request.form.get("status")
    if status not in ("Upcoming", "Completed", "Cancelled"):
        flash("Invalid status.", "error")
    else:
        with get_db() as db:
            db.execute("UPDATE events SET status=? WHERE event_id=?", (status, event_id))
        flash("Event status updated.", "success")
    return redirect(url_for("admin"))

@app.route("/registrations")
def registrations_page():
    with get_db() as db:
        rows = db.execute("""SELECT r.registration_id, r.registered_at, r.attendance_status,
            s.full_name, s.email, s.course, s.year_of_study, e.title AS event_title, e.event_date
            FROM registrations r JOIN students s ON s.student_id=r.student_id
            JOIN events e ON e.event_id=r.event_id ORDER BY r.registered_at DESC""").fetchall()
    return render_template("registrations.html", rows=rows)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
