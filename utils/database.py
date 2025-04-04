import sqlite3
import json
from typing import List, Dict, Optional
from pathlib import Path
from utils.config import Config

class DatabaseManager:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self._initialize_database()
        
    def _initialize_database(self):
        Path(Path(self.db_path).parent).mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create candidates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    cv_path TEXT NOT NULL,
                    extracted_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create matches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    candidate_id INTEGER NOT NULL,
                    match_score REAL NOT NULL,
                    is_shortlisted BOOLEAN DEFAULT FALSE,
                    interview_scheduled BOOLEAN DEFAULT FALSE,
                    interview_date TEXT,
                    feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id),
                    FOREIGN KEY (candidate_id) REFERENCES candidates (id)
                )
            """)
            
            conn.commit()
    
    def add_job(self, title: str, description: str, summary: str = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO jobs (title, description, summary) VALUES (?, ?, ?)",
                (title, description, summary))
            conn.commit()
            return cursor.lastrowid
    
    def get_jobs(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_job(self, job_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_candidate(self, name: str, cv_path: str, extracted_data: str = None, email: str = None, phone: str = None) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO candidates (name, email, phone, cv_path, extracted_data) VALUES (?, ?, ?, ?, ?)",
                (name, email, phone, cv_path, extracted_data))
            conn.commit()
            return cursor.lastrowid
    
    def get_candidates(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidates ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_candidate(self, candidate_id: int) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_match(self, job_id: int, candidate_id: int, match_score: float) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO matches (job_id, candidate_id, match_score) VALUES (?, ?, ?)",
                (job_id, candidate_id, match_score))
            conn.commit()
            return cursor.lastrowid
    
    def get_matches(self, job_id: int = None, candidate_id: int = None) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if job_id and candidate_id:
                cursor.execute(
                    "SELECT * FROM matches WHERE job_id = ? AND candidate_id = ?",
                    (job_id, candidate_id))
            elif job_id:
                cursor.execute(
                    """SELECT m.*, c.name as candidate_name, c.email as candidate_email 
                    FROM matches m JOIN candidates c ON m.candidate_id = c.id 
                    WHERE m.job_id = ? ORDER BY m.match_score DESC""",
                    (job_id,))
            elif candidate_id:
                cursor.execute(
                    """SELECT m.*, j.title as job_title 
                    FROM matches m JOIN jobs j ON m.job_id = j.id 
                    WHERE m.candidate_id = ? ORDER BY m.match_score DESC""",
                    (candidate_id,))
            else:
                cursor.execute(
                    """SELECT m.*, j.title as job_title, c.name as candidate_name 
                    FROM matches m 
                    JOIN jobs j ON m.job_id = j.id 
                    JOIN candidates c ON m.candidate_id = c.id 
                    ORDER BY m.created_at DESC""")
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_shortlist_status(self, match_id: int, is_shortlisted: bool) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE matches SET is_shortlisted = ? WHERE id = ?",
                (is_shortlisted, match_id))
            conn.commit()
    
    def schedule_interview(self, match_id: int, interview_date: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE matches SET interview_scheduled = TRUE, interview_date = ? WHERE id = ?",
                (interview_date, match_id))
            conn.commit()
    
    def add_feedback(self, match_id: int, feedback: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE matches SET feedback = ? WHERE id = ?",
                (feedback, match_id))
            conn.commit()