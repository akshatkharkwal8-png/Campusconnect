
import os
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg
from psycopg.rows import dict_row
from psycopg import IntegrityError

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "change-this-development-secret-key"
)

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    """Connect to PostgreSQL."""
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set in your environment variables."
        )
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    """Create database tables and add demo records."""
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS clubs (
                club_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                accent TEXT NOT NULL DEFAULT '#7c5cff'
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id SERIAL PRIMARY KEY,
                club_id INTEGER NOT NULL
                    REFERENCES clubs(club_id) ON DELETE RESTRICT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                event_date DATE NOT NULL,
                event_time TIME NOT NULL,
                venue TEXT NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 100
                    CHECK (capacity > 0),
                status TEXT NOT NULL DEFAULT 'Upcoming'
                    CHECK (status IN (
                        'Upcoming', 'Completed', 'Cancelled'
                    )),
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                course TEXT NOT NULL,
                year_of_study INTEGER NOT NULL
                    CHECK (year_of_study BETWEEN 1 AND 6)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                registration_id SERIAL PRIMARY KEY,
                student_id INTEGER NOT NULL
                    REFERENCES students(student_id) ON DELETE CASCADE,
                event_id INTEGER NOT NULL
                    REFERENCES events(event_id) ON DELETE CASCADE,
                registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                attendance_status TEXT NOT NULL DEFAULT 'Registered'
                    CHECK (attendance_status IN (
                        'Registered', 'Attended', 'No-show', 'Cancelled'
                    )),
                UNIQUE (student_id, event_id)
            )
        """)

        club_count = db.execute(
            "SELECT COUNT(*) AS count FROM clubs"
        ).fetchone()["count"]

        if club_count == 0:
            db.executemany("""
                INSERT INTO clubs (name, category, description, accent)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """, [
                (
                    "The Culture Collective",
                    "Culture",
                    "Music, dance, theatre and the moments that bring campus together.",
                    "#8b5cf6"
                ),
                (
                    "Tech & Innovation Society",
                    "Technology",
                    "Build, experiment, learn and turn ideas into useful projects.",
                    "#06b6d4"
                ),
                (
                    "Green Campus Network",
                    "Sustainability",
                    "Small actions, greener spaces and a more responsible campus.",
                    "#22c55e"
                ),
                (
                    "The Speaker's Forum",
                    "Debate & Ideas",
                    "A space for sharp arguments, thoughtful dialogue and public speaking.",
                    "#f97316"
                ),
            ])

        event_count = db.execute(
            "SELECT COUNT(*) AS count FROM events"
        ).fetchone()["count"]

        if event_count == 0:
            clubs = {
                row["name"]: row["club_id"]
                for row in db.execute(
                    "SELECT club_id, name FROM clubs"
                ).fetchall()
            }

            db.executemany("""
                INSERT INTO events
                    (club_id, title, description, event_date,
                     event_time, venue, capacity, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                (
                    clubs["The Culture Collective"],
                    "Afterglow: Open-Air Music Night",
                    "An evening of live sets, student performers and campus energy. Bring your friends and discover your next favourite artist.",
                    "2026-10-24", "19:00", "Central Lawn", 250, "Upcoming"
                ),
                (
                    clubs["Tech & Innovation Society"],
                    "Buildathon: Ideas to Interface",
                    "A hands-on sprint where teams prototype a solution to a real student-life problem. Beginners are welcome.",
                    "2026-10-28", "10:00", "Innovation Lab", 80, "Upcoming"
                ),
                (
                    clubs["Green Campus Network"],
                    "Green Miles Campus Walk",
                    "A guided campus walk with quick sustainability challenges and a community clean-up.",
                    "2026-11-02", "07:30", "Main Gate", 60, "Upcoming"
                ),
                (
                    clubs["The Speaker's Forum"],
                    "The Great Campus Debate",
                    "Two teams, one motion, and a room full of arguments. Come compete or cheer from the audience.",
                    "2026-11-06", "17:00", "Seminar Hall 2", 120, "Upcoming"
                ),
                (
                    clubs["The Culture Collective"],
                    "Monsoon Memories: Jam Session",
                    "An informal acoustic jam for singers, instrumentalists and anyone who loves live music.",
                    "2026-09-18", "18:30", "Amphitheatre", 100, "Completed"
                ),
            ])

        db.executemany("""
            INSERT INTO students
                (full_name, email, course, year_of_study)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """, [
            ("Aarav Mehta", "aarav.demo@example.com", "IPM", 2),
            ("Diya Rao", "diya.demo@example.com", "BA LLB", 3),
            ("Kabir Sharma", "kabir.demo@example.com", "IPM", 1),
        ])

        students = {
            row["email"]: row["student_id"]
            for row in db.execute("""
                SELECT student_id, email FROM students
                WHERE email = ANY(%s)
            """, [[
                "aarav.demo@example.com",
                "diya.demo@example.com",
                "kabir.demo@example.com",
            ]]).fetchall()
        }

        events = {
            row["title"]: row["event_id"]
            for row in db.execute("""
                SELECT event_id, title FROM events
                WHERE title = ANY(%s)
            """, [[
                "Afterglow: Open-Air Music Night",
                "Buildathon: Ideas to Interface",
                "The Great Campus Debate",
            ]]).fetchall()
        }

        if len(students) == 3 and len(events) == 3:
            db.executemany("""
                INSERT INTO registrations
                    (student_id, event_id, attendance_status)
                VALUES (%s, %s, %s)
                ON CONFLICT (student_id, event_id) DO NOTHING
            """, [
                (
                    students["aarav.demo@example.com"],
                    events["Afterglow: Open-Air Music Night"],
                    "Registered"
                ),
                (
                    students["diya.demo@example.com"],
                    events["Buildathon: Ideas to Interface"],
                    "Registered"
                ),
                (
                    students["kabir.demo@example.com"],
                    events["The Great Campus Debate"],
                    "Registered"
                ),
            ])
