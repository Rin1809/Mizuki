# Mizuki/db_writer.py
import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL_DASHBOARD')

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"[DB_WRITER][LOI] Ko the ket noi db: {e}")
        return None

def initialize_database():
    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS visits (
                    id SERIAL PRIMARY KEY,
                    ip_address VARCHAR(45),
                    visit_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    country VARCHAR(100),
                    city VARCHAR(100),
                    region VARCHAR(100),
                    isp VARCHAR(255)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS interaction_sessions (
                    id SERIAL PRIMARY KEY,
                    session_key VARCHAR(255) UNIQUE NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    location TEXT,
                    start_time TIMESTAMPTZ,
                    end_time TIMESTAMPTZ
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS interaction_events (
                    id SERIAL PRIMARY KEY,
                    session_id INTEGER REFERENCES interaction_sessions(id) ON DELETE CASCADE,
                    event_time TIMESTAMPTZ,
                    event_type VARCHAR(255),
                    details JSONB
                );
            """)
        conn.commit()
        print("[DB_WRITER] Khoi tao DB dashboard thanh cong.")
    except Exception as e:
        print(f"[DB_WRITER][LOI] Khoi tao table: {e}")
    finally:
        conn.close()

def log_visit(ip, user_agent, country, city, region, isp, timestamp):
    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO visits (ip_address, visit_time, user_agent, country, city, region, isp)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (ip, timestamp, user_agent, country, city, region, isp)
            )
        conn.commit()
    except Exception as e:
        print(f"[DB_WRITER][LOI] Ghi log visit: {e}")
    finally:
        conn.close()

def log_interaction_session(session_key, ip, user_agent, location, start_time, end_time, events):
    conn = get_db_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO interaction_sessions (session_key, ip_address, user_agent, location, start_time, end_time)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (session_key, ip, user_agent, location, start_time, end_time)
            )
            session_id = cur.fetchone()[0]

            for event in events:
                cur.execute(
                    """
                    INSERT INTO interaction_events (session_id, event_time, event_type, details)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (session_id, event['event_time'], event['event_type'], event['details'])
                )
        conn.commit()
    except Exception as e:
        print(f"[DB_WRITER][LOI] Ghi log interaction: {e}")
    finally:
        conn.close()