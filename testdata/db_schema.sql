PRAGMA foreign_keys = ON;

CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    phase_id INTEGER,
    name TEXT NOT NULL,
    value REAL,
    unit TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (phase_id) REFERENCES phases(id)
);
