#!/usr/bin/env python3
"""
Student Manager for Exam Monitoring System
Handles student registration, face encoding, and student data management
"""

import os
import cv2
import pickle
import logging
import sqlite3
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json

# Face recognition imports
try:
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False

logger = logging.getLogger(__name__)

class StudentManager:
    """Manages student registration and face recognition data"""
    
    def __init__(self, database_manager, students_dir='students'):
        self.database_manager = database_manager
        self.students_dir = students_dir
        self.db_lock = threading.Lock()
        
        # Face recognition data
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_student_ids = []
        self.face_data_loaded = False
        
        # Create directories
        os.makedirs(students_dir, exist_ok=True)
        os.makedirs(os.path.join(students_dir, 'photos'), exist_ok=True)
        
        # Initialize database tables
        self.setup_database()
        
        # Load existing face data
        if FACE_RECOGNITION_AVAILABLE:
            self.load_face_data()
        else:
            logger.warning("face_recognition library not available - face recognition disabled")
    
    def setup_database(self):
        """Setup database tables for student management"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                # Create students table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id TEXT UNIQUE NOT NULL,
                        first_name TEXT NOT NULL,
                        last_name TEXT NOT NULL,
                        email TEXT,
                        phone TEXT,
                        course TEXT,
                        semester TEXT,
                        registration_date TEXT NOT NULL,
                        photo_path TEXT,
                        face_encoding_path TEXT,
                        is_active BOOLEAN DEFAULT 1,
                        metadata TEXT
                    )
                ''')
                
                # Create attendance table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        student_id TEXT NOT NULL,
                        session_id TEXT,
                        exam_date TEXT NOT NULL,
                        check_in_time TEXT,
                        check_out_time TEXT,
                        status TEXT DEFAULT 'present',
                        confidence REAL,
                        photo_path TEXT,
                        notes TEXT,
                        FOREIGN KEY (student_id) REFERENCES students (student_id)
                    )
                ''')
                
                # Create face_recognition_log table for debugging
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS face_recognition_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        recognized_student_id TEXT,
                        confidence REAL,
                        session_id TEXT,
                        image_path TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_exam_date ON attendance(exam_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_face_log_timestamp ON face_recognition_log(timestamp)')
                
                conn.commit()
                conn.close()
                
            logger.info("Student database tables initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup student database: {e}")
            raise
    
    def register_student(self, student_data: Dict[str, Any], photo_file) -> Tuple[bool, str]:
        """Register a new student with face encoding"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return False, "Face recognition library not available"
            
            student_id = student_data['student_id']
            
            # Check if student already exists
            if self.get_student(student_id):
                return False, f"Student {student_id} already registered"
            
            # Save photo
            photo_filename = f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_path = os.path.join(self.students_dir, 'photos', photo_filename)
            
            # Read and save image
            if hasattr(photo_file, 'read'):
                # File upload object
                image_data = photo_file.read()
                with open(photo_path, 'wb') as f:
                    f.write(image_data)
            else:
                # File path or numpy array
                if isinstance(photo_file, str):
                    import shutil
                    shutil.copy2(photo_file, photo_path)
                else:
                    cv2.imwrite(photo_path, photo_file)
            
            # Load image for face encoding
            image = face_recognition.load_image_file(photo_path)
            face_encodings = face_recognition.face_encodings(image)
            
            if len(face_encodings) == 0:
                os.remove(photo_path)  # Clean up
                return False, "No face detected in the photo"
            
            if len(face_encodings) > 1:
                logger.warning(f"Multiple faces detected for student {student_id}, using first one")
            
            # Save face encoding
            face_encoding = face_encodings[0]
            encoding_filename = f"{student_id}_encoding.pkl"
            encoding_path = os.path.join(self.students_dir, encoding_filename)
            
            with open(encoding_path, 'wb') as f:
                pickle.dump(face_encoding, f)
            
            # Save to database
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                registration_date = datetime.now().isoformat()
                metadata = json.dumps({
                    'registration_method': 'web_upload',
                    'face_encoding_quality': 'high',
                    'photo_resolution': f"{image.shape[1]}x{image.shape[0]}"
                })
                
                cursor.execute('''
                    INSERT INTO students (student_id, first_name, last_name, email, phone, 
                                        course, semester, registration_date, photo_path, 
                                        face_encoding_path, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    student_id,
                    student_data.get('first_name', ''),
                    student_data.get('last_name', ''),
                    student_data.get('email', ''),
                    student_data.get('phone', ''),
                    student_data.get('course', ''),
                    student_data.get('semester', ''),
                    registration_date,
                    photo_path,
                    encoding_path,
                    metadata
                ))
                
                conn.commit()
                conn.close()
            
            # Update in-memory face data
            self.known_face_encodings.append(face_encoding)
            self.known_face_names.append(f"{student_data.get('first_name', '')} {student_data.get('last_name', '')}")
            self.known_student_ids.append(student_id)
            
            logger.info(f"Student {student_id} registered successfully")
            return True, f"Student {student_id} registered successfully"
            
        except Exception as e:
            logger.error(f"Failed to register student: {e}")
            return False, f"Registration failed: {str(e)}"
    
    def get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get student information by ID"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
                row = cursor.fetchone()
                
                if row:
                    columns = [description[0] for description in cursor.description]
                    student = dict(zip(columns, row))
                    
                    # Parse metadata if present
                    if student['metadata']:
                        try:
                            student['metadata'] = json.loads(student['metadata'])
                        except:
                            pass
                    
                    conn.close()
                    return student
                
                conn.close()
                return None
                
        except Exception as e:
            logger.error(f"Failed to get student {student_id}: {e}")
            return None
    
    def get_all_students(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all students"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                query = 'SELECT * FROM students'
                params = []
                
                if active_only:
                    query += ' WHERE is_active = 1'
                
                query += ' ORDER BY last_name, first_name'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                columns = [description[0] for description in cursor.description]
                students = []
                
                for row in rows:
                    student = dict(zip(columns, row))
                    if student['metadata']:
                        try:
                            student['metadata'] = json.loads(student['metadata'])
                        except:
                            pass
                    students.append(student)
                
                conn.close()
                return students
                
        except Exception as e:
            logger.error(f"Failed to get students: {e}")
            return []
    
    def load_face_data(self):
        """Load all face encodings into memory"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return False
            
            students = self.get_all_students()
            
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_student_ids = []
            
            for student in students:
                encoding_path = student.get('face_encoding_path')
                if encoding_path and os.path.exists(encoding_path):
                    try:
                        with open(encoding_path, 'rb') as f:
                            encoding = pickle.load(f)
                        
                        self.known_face_encodings.append(encoding)
                        self.known_face_names.append(f"{student['first_name']} {student['last_name']}")
                        self.known_student_ids.append(student['student_id'])
                        
                    except Exception as e:
                        logger.warning(f"Failed to load encoding for student {student['student_id']}: {e}")
            
            self.face_data_loaded = True
            logger.info(f"Loaded face data for {len(self.known_face_encodings)} students")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load face data: {e}")
            return False
    
    def recognize_face(self, face_encoding, tolerance: float = 0.6) -> Tuple[Optional[str], float]:
        """Recognize a face encoding against known students"""
        try:
            if not FACE_RECOGNITION_AVAILABLE or not self.face_data_loaded:
                return None, 0.0
            
            if len(self.known_face_encodings) == 0:
                return None, 0.0
            
            # Compare face encodings
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            
            if face_distances[best_match_index] <= tolerance:
                student_id = self.known_student_ids[best_match_index]
                confidence = 1.0 - face_distances[best_match_index]  # Convert distance to confidence
                return student_id, confidence
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            return None, 0.0
    
    def recognize_faces_in_frame(self, frame, tolerance: float = 0.6) -> List[Tuple[str, float, Tuple[int, int, int, int]]]:
        """Recognize all faces in a frame"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return []
            
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find face locations and encodings
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            recognized_faces = []
            
            for face_encoding, face_location in zip(face_encodings, face_locations):
                student_id, confidence = self.recognize_face(face_encoding, tolerance)
                
                if student_id:
                    # Convert face_recognition coordinates to OpenCV format
                    top, right, bottom, left = face_location
                    recognized_faces.append((student_id, confidence, (left, top, right - left, bottom - top)))
                    
                    # Log recognition
                    self.log_face_recognition(student_id, confidence)
            
            return recognized_faces
            
        except Exception as e:
            logger.error(f"Error recognizing faces in frame: {e}")
            return []
    
    def log_face_recognition(self, student_id: str, confidence: float, session_id: str = None):
        """Log face recognition event"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                timestamp = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT INTO face_recognition_log (timestamp, recognized_student_id, confidence, session_id)
                    VALUES (?, ?, ?, ?)
                ''', (timestamp, student_id, confidence, session_id))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            logger.error(f"Failed to log face recognition: {e}")
    
    def mark_attendance(self, student_id: str, session_id: str = None, 
                       check_in_time: str = None, confidence: float = 0.0) -> bool:
        """Mark attendance for a student"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                exam_date = datetime.now().date().isoformat()
                check_in_time = check_in_time or datetime.now().isoformat()
                
                # Check if attendance already marked for today
                cursor.execute('''
                    SELECT id FROM attendance 
                    WHERE student_id = ? AND exam_date = ?
                ''', (student_id, exam_date))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing attendance
                    cursor.execute('''
                        UPDATE attendance 
                        SET check_in_time = ?, confidence = ?, session_id = ?
                        WHERE student_id = ? AND exam_date = ?
                    ''', (check_in_time, confidence, session_id, student_id, exam_date))
                    logger.info(f"Updated attendance for student {student_id}")
                else:
                    # Insert new attendance record
                    cursor.execute('''
                        INSERT INTO attendance (student_id, session_id, exam_date, check_in_time, 
                                              status, confidence)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (student_id, session_id, exam_date, check_in_time, 'present', confidence))
                    logger.info(f"Marked attendance for student {student_id}")
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            logger.error(f"Failed to mark attendance for {student_id}: {e}")
            return False
    
    def get_attendance_for_date(self, exam_date: str = None) -> List[Dict[str, Any]]:
        """Get attendance for a specific date"""
        try:
            exam_date = exam_date or datetime.now().date().isoformat()
            
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT a.*, s.first_name, s.last_name, s.course, s.semester
                    FROM attendance a
                    JOIN students s ON a.student_id = s.student_id
                    WHERE a.exam_date = ?
                    ORDER BY a.check_in_time
                ''', (exam_date,))
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                attendance = [dict(zip(columns, row)) for row in rows]
                
                conn.close()
                return attendance
                
        except Exception as e:
            logger.error(f"Failed to get attendance for {exam_date}: {e}")
            return []
    
    def get_attendance_summary(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get attendance summary"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                # Build query
                query = '''
                    SELECT 
                        COUNT(DISTINCT a.student_id) as present_students,
                        COUNT(*) as total_attendance_records,
                        AVG(a.confidence) as avg_confidence,
                        a.exam_date
                    FROM attendance a
                    WHERE 1=1
                '''
                params = []
                
                if start_date:
                    query += ' AND a.exam_date >= ?'
                    params.append(start_date)
                
                if end_date:
                    query += ' AND a.exam_date <= ?'
                    params.append(end_date)
                
                query += ' GROUP BY a.exam_date ORDER BY a.exam_date DESC'
                
                cursor.execute(query, params)
                daily_summary = cursor.fetchall()
                
                # Get total registered students
                cursor.execute('SELECT COUNT(*) FROM students WHERE is_active = 1')
                total_students = cursor.fetchone()[0]
                
                # Get overall stats
                cursor.execute('''
                    SELECT 
                        COUNT(DISTINCT student_id) as unique_attendees,
                        COUNT(*) as total_records,
                        MIN(exam_date) as first_exam,
                        MAX(exam_date) as last_exam
                    FROM attendance
                ''')
                overall_stats = cursor.fetchone()
                
                conn.close()
                
                return {
                    'total_registered_students': total_students,
                    'unique_attendees': overall_stats[0] if overall_stats else 0,
                    'total_attendance_records': overall_stats[1] if overall_stats else 0,
                    'first_exam_date': overall_stats[2] if overall_stats else None,
                    'last_exam_date': overall_stats[3] if overall_stats else None,
                    'daily_summary': [
                        {
                            'exam_date': row[3],
                            'present_students': row[0],
                            'attendance_percentage': round((row[0] / total_students) * 100, 1) if total_students > 0 else 0,
                            'avg_confidence': round(row[2], 3) if row[2] else 0
                        }
                        for row in daily_summary
                    ]
                }
                
        except Exception as e:
            logger.error(f"Failed to get attendance summary: {e}")
            return {}
    
    def update_student(self, student_id: str, updates: Dict[str, Any]) -> bool:
        """Update student information"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                # Build update query
                set_clauses = []
                params = []
                
                allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'course', 'semester', 'is_active']
                
                for field, value in updates.items():
                    if field in allowed_fields:
                        set_clauses.append(f"{field} = ?")
                        params.append(value)
                
                if not set_clauses:
                    return False
                
                params.append(student_id)
                query = f"UPDATE students SET {', '.join(set_clauses)} WHERE student_id = ?"
                
                cursor.execute(query, params)
                rows_affected = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                if rows_affected > 0:
                    logger.info(f"Updated student {student_id}")
                    # Reload face data if name changed
                    if 'first_name' in updates or 'last_name' in updates:
                        self.load_face_data()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to update student {student_id}: {e}")
            return False
    
    def delete_student(self, student_id: str) -> bool:
        """Delete a student (soft delete by setting is_active = 0)"""
        try:
            return self.update_student(student_id, {'is_active': 0})
        except Exception as e:
            logger.error(f"Failed to delete student {student_id}: {e}")
            return False
    
    def export_students(self, export_path: str) -> bool:
        """Export student data to JSON"""
        try:
            students = self.get_all_students(active_only=False)
            
            # Remove sensitive file paths from export
            for student in students:
                student.pop('photo_path', None)
                student.pop('face_encoding_path', None)
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_students': len(students),
                'students': students
            }
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Students exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export students: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get student management statistics"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.database_manager.db_path)
                cursor = conn.cursor()
                
                stats = {}
                
                # Student counts
                cursor.execute('SELECT COUNT(*) FROM students WHERE is_active = 1')
                stats['active_students'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM students')
                stats['total_students'] = cursor.fetchone()[0]
                
                # Attendance stats
                cursor.execute('SELECT COUNT(*) FROM attendance')
                stats['total_attendance_records'] = cursor.fetchone()[0]
                
                today = datetime.now().date().isoformat()
                cursor.execute('SELECT COUNT(DISTINCT student_id) FROM attendance WHERE exam_date = ?', (today,))
                stats['students_present_today'] = cursor.fetchone()[0]
                
                # Face recognition stats
                cursor.execute('SELECT COUNT(*) FROM face_recognition_log')
                stats['total_face_recognitions'] = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM face_recognition_log WHERE DATE(timestamp) = ?', (today,))
                stats['face_recognitions_today'] = cursor.fetchone()[0]
                
                # Average confidence
                cursor.execute('SELECT AVG(confidence) FROM attendance WHERE confidence > 0')
                avg_conf = cursor.fetchone()[0]
                stats['average_recognition_confidence'] = round(avg_conf, 3) if avg_conf else 0
                
                conn.close()
                
                # Memory stats
                stats['face_encodings_loaded'] = len(self.known_face_encodings)
                stats['face_recognition_available'] = FACE_RECOGNITION_AVAILABLE
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
