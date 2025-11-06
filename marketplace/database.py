import sqlite3
import threading
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parent / "marketplace.db"
_thread_local = threading.local()


def get_connection():
    conn = getattr(_thread_local, "connection", None)
    if conn is None:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        setattr(_thread_local, "connection", conn)
    return conn


def close_connection():
    conn = getattr(_thread_local, "connection", None)
    if conn is not None:
        conn.close()
        setattr(_thread_local, "connection", None)


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('homeowner', 'contractor', 'admin')),
            tier TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS homeowner_profiles (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            location TEXT,
            bio TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS contractor_profiles (
            user_id INTEGER PRIMARY KEY,
            business_name TEXT,
            license_number TEXT,
            insurance_info TEXT,
            service_areas TEXT,
            specialties TEXT,
            background_check_status TEXT DEFAULT 'pending',
            verification_badge INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tier TEXT NOT NULL,
            billing_cycle TEXT NOT NULL,
            price REAL NOT NULL,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            homeowner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            project_type TEXT NOT NULL,
            description TEXT NOT NULL,
            budget_min REAL,
            budget_max REAL,
            desired_start_date TEXT,
            location TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(homeowner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS project_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            contractor_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            cost_breakdown TEXT,
            timeline TEXT,
            materials TEXT,
            payment_schedule TEXT,
            status TEXT NOT NULL DEFAULT 'submitted',
            submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            accepted_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(contractor_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(recipient_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            homeowner_id INTEGER NOT NULL,
            contractor_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY(homeowner_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(contractor_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            quote_id INTEGER,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(quote_id) REFERENCES quotes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            processor TEXT,
            transaction_reference TEXT,
            status TEXT NOT NULL DEFAULT 'initiated',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()

