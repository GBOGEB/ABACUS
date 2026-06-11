import pathlib
import sqlite3
import pytest

pytestmark = [pytest.mark.db, pytest.mark.integration]

SCHEMA_PATH = pathlib.Path("testdata/db_schema.sql")


def apply_schema(conn):
    """Apply database schema from testdata/db_schema.sql."""
    if not SCHEMA_PATH.exists():
        pytest.skip(f"Schema file not found: {SCHEMA_PATH}")
    sql = SCHEMA_PATH.read_text()
    conn.executescript(sql)
    conn.commit()


def test_db_schema_applies_and_insert_works(tmp_path):
    """Test that database schema applies and basic insert/select works."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    try:
        apply_schema(conn)
        conn.execute(
            "INSERT INTO runs (name, created_at) VALUES (?, ?)",
            ("test-run", "2025-01-01T00:00:00Z"),
        )
        conn.commit()

        cur = conn.execute("SELECT name, created_at FROM runs")
        rows = cur.fetchall()
        assert rows == [("test-run", "2025-01-01T00:00:00Z")]
    finally:
        conn.close()


def test_db_schema_has_required_tables(tmp_path):
    """Verify schema creates expected tables."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    try:
        apply_schema(conn)
        
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cur.fetchall()]
        
        expected_tables = ["runs", "phases", "metrics"]
        for table in expected_tables:
            assert table in tables, f"Expected table '{table}' not found in schema"
    finally:
        conn.close()


def test_db_transaction_rollback(tmp_path):
    """Test transaction rollback functionality."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    try:
        apply_schema(conn)
        
        conn.execute(
            "INSERT INTO runs (name, created_at) VALUES (?, ?)",
            ("rollback-test", "2025-01-01T00:00:00Z"),
        )
        conn.rollback()
        
        cur = conn.execute("SELECT COUNT(*) FROM runs")
        count = cur.fetchone()[0]
        assert count == 0, "Rollback should have prevented insert"
    finally:
        conn.close()


def test_db_foreign_key_constraints(tmp_path):
    """Test foreign key constraints are enforced."""
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        apply_schema(conn)
        
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO phases (run_id, name, status) VALUES (?, ?, ?)",
                (999, "test-phase", "pending"),
            )
            conn.commit()
    finally:
        conn.close()
