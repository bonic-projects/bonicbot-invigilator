#!/usr/bin/env python3
"""
Database Manager for Exam Monitoring System
Handles SQLite database operations for violation logging and data management
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
import threading

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for the exam monitoring system"""
    
    def __init__(self, db_path='exam_violations.db'):
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self.setup_database()
        
    def get_connection(self):
        return sqlite3.connect(self.db_path)
            
    def setup_database(self):
        """Initialize SQLite database with required tables"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Create violations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS violations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        violation_type TEXT NOT NULL,
                        description TEXT,
                        confidence REAL,
                        image_path TEXT,
                        session_id TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Create sessions table for tracking monitoring sessions
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        total_violations INTEGER DEFAULT 0,
                        camera_method TEXT,
                        config_snapshot TEXT
                    )
                ''')
                
                # Create system_events table for logging system events
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        description TEXT,
                        severity TEXT DEFAULT 'INFO',
                        metadata TEXT
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON violations(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_type ON violations(violation_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_violations_session ON violations(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp)')
                
                conn.commit()
                conn.close()
                
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            raise
    
    def log_violation(self, violation_type: str, description: str, confidence: float = 0.0, 
                     image_path: str = None, session_id: str = None, metadata: Dict = None) -> int:
        """Log a violation to the database"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                timestamp = datetime.now().isoformat()
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT INTO violations (timestamp, violation_type, description, confidence, 
                                          image_path, session_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, violation_type, description, confidence, image_path, session_id, metadata_json))
                
                violation_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                
            logger.info(f"Violation logged: {violation_type} (ID: {violation_id})")
            return violation_id
            
        except Exception as e:
            logger.error(f"Failed to log violation: {e}")
            return -1
    
    def get_violations(self, limit: int = 50, offset: int = 0, session_id: str = None, 
                      violation_type: str = None, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get violations from database with filtering options"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Build query with filters
                query = "SELECT * FROM violations WHERE 1=1"
                params = []
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if violation_type:
                    query += " AND violation_type = ?"
                    params.append(violation_type)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to dictionaries
                columns = [description[0] for description in cursor.description]
                violations = []
                
                for row in rows:
                    violation = dict(zip(columns, row))
                    # Parse metadata if present
                    if violation['metadata']:
                        try:
                            violation['metadata'] = json.loads(violation['metadata'])
                        except:
                            pass
                    violations.append(violation)
                
                conn.close()
                return violations
                
        except Exception as e:
            logger.error(f"Failed to get violations: {e}")
            return []
            
        
    
    def get_violations_summary(self, session_id: str = None, days: int = None) -> List[Dict]:
        """Get violation summary grouped by type"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = '''
                    SELECT violation_type, COUNT(*) as count, 
                           AVG(confidence) as avg_confidence,
                           MAX(timestamp) as last_occurrence
                    FROM violations WHERE 1=1
                '''
                params = []
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if days:
                    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                    query += " AND timestamp >= ?"
                    params.append(cutoff_date)
                
                query += " GROUP BY violation_type ORDER BY count DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                summary = [dict(zip(columns, row)) for row in rows]
                
                conn.close()
                return summary
                
        except Exception as e:
            logger.error(f"Failed to get violations summary: {e}")
            return []
    
    def create_session(self, session_id: str, camera_method: str = None, 
                      config_snapshot: Dict = None) -> bool:
        """Create a new monitoring session"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                timestamp = datetime.now().isoformat()
                config_json = json.dumps(config_snapshot) if config_snapshot else None
                
                cursor.execute('''
                    INSERT OR REPLACE INTO sessions (session_id, start_time, camera_method, config_snapshot)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, timestamp, camera_method, config_json))
                
                conn.commit()
                conn.close()
                
            logger.info(f"Session created: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False
    
    def end_session(self, session_id: str) -> bool:
        """End a monitoring session"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get violation count for this session
                cursor.execute('SELECT COUNT(*) FROM violations WHERE session_id = ?', (session_id,))
                violation_count = cursor.fetchone()[0]
                
                # Update session
                timestamp = datetime.now().isoformat()
                cursor.execute('''
                    UPDATE sessions 
                    SET end_time = ?, total_violations = ?
                    WHERE session_id = ?
                ''', (timestamp, violation_count, session_id))
                
                conn.commit()
                conn.close()
                
            logger.info(f"Session ended: {session_id} ({violation_count} violations)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return False
    
    def get_sessions(self, limit: int = 20) -> List[Dict]:
        """Get monitoring sessions"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM sessions 
                    ORDER BY start_time DESC 
                    LIMIT ?
                ''', (limit,))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                sessions = []
                
                for row in rows:
                    session = dict(zip(columns, row))
                    # Parse config snapshot if present
                    if session['config_snapshot']:
                        try:
                            session['config_snapshot'] = json.loads(session['config_snapshot'])
                        except:
                            pass
                    sessions.append(session)
                
                conn.close()
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to get sessions: {e}")
            return []
    
    def log_system_event(self, event_type: str, description: str, 
                        severity: str = 'INFO', metadata: Dict = None):
        """Log a system event"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                timestamp = datetime.now().isoformat()
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT INTO system_events (timestamp, event_type, description, severity, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (timestamp, event_type, description, severity, metadata_json))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    def get_system_events(self, limit: int = 100, severity: str = None) -> List[Dict]:
        """Get system events"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                query = "SELECT * FROM system_events"
                params = []
                
                if severity:
                    query += " WHERE severity = ?"
                    params.append(severity)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                events = []
                
                for row in rows:
                    event = dict(zip(columns, row))
                    if event['metadata']:
                        try:
                            event['metadata'] = json.loads(event['metadata'])
                        except:
                            pass
                    events.append(event)
                
                conn.close()
                return events
                
        except Exception as e:
            logger.error(f"Failed to get system events: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                stats = {}
                
                # Total violations
                cursor.execute('SELECT COUNT(*) FROM violations')
                stats['total_violations'] = cursor.fetchone()[0]
                
                # Total sessions
                cursor.execute('SELECT COUNT(*) FROM sessions')
                stats['total_sessions'] = cursor.fetchone()[0]
                
                # Active sessions (no end_time)
                cursor.execute('SELECT COUNT(*) FROM sessions WHERE end_time IS NULL')
                stats['active_sessions'] = cursor.fetchone()[0]
                
                # Violations today
                today = datetime.now().date().isoformat()
                cursor.execute('SELECT COUNT(*) FROM violations WHERE DATE(timestamp) = ?', (today,))
                stats['violations_today'] = cursor.fetchone()[0]
                
                # Most common violation type
                cursor.execute('''
                    SELECT violation_type, COUNT(*) as count 
                    FROM violations 
                    GROUP BY violation_type 
                    ORDER BY count DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                if result:
                    stats['most_common_violation'] = {'type': result[0], 'count': result[1]}
                
                # Database size
                db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
                stats['database_size_mb'] = round(db_size / (1024 * 1024), 2)
                
                conn.close()
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """Clean up old data beyond specified days"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
                
                # Delete old violations
                cursor.execute('DELETE FROM violations WHERE timestamp < ?', (cutoff_date,))
                violations_deleted = cursor.rowcount
                
                # Delete old system events
                cursor.execute('DELETE FROM system_events WHERE timestamp < ?', (cutoff_date,))
                events_deleted = cursor.rowcount
                
                # Delete old sessions (but only ended ones)
                cursor.execute('DELETE FROM sessions WHERE start_time < ? AND end_time IS NOT NULL', (cutoff_date,))
                sessions_deleted = cursor.rowcount
                
                # Vacuum database to reclaim space
                cursor.execute('VACUUM')
                
                conn.commit()
                conn.close()
                
                total_deleted = violations_deleted + events_deleted + sessions_deleted
                logger.info(f"Cleaned up old data: {violations_deleted} violations, "
                           f"{events_deleted} events, {sessions_deleted} sessions")
                
                return total_deleted
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0
    
    def export_data(self, export_path: str, session_id: str = None, 
                   start_date: str = None, end_date: str = None) -> bool:
        """Export data to JSON file"""
        try:
            data = {
                'export_timestamp': datetime.now().isoformat(),
                'violations': self.get_violations(limit=10000, session_id=session_id, 
                                                start_date=start_date, end_date=end_date),
                'sessions': self.get_sessions(limit=1000),
                'summary': self.get_violations_summary(session_id=session_id),
                'statistics': self.get_statistics()
            }
            
            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Data exported to: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False
    
    def close(self):
        """Close database connections (cleanup)"""
        logger.info("Database manager closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
