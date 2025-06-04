#!/usr/bin/env python3
"""
Attendance Manager for Exam Monitoring System
Handles real-time attendance tracking during exam sessions
"""

import cv2
import time
import logging
import threading
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

class AttendanceManager:
    """Manages real-time attendance tracking during exam sessions"""
    
    def __init__(self, student_manager, database_manager, config_manager):
        self.student_manager = student_manager
        self.database_manager = database_manager
        self.config_manager = config_manager
        
        # Attendance configuration
        self.attendance_config = config_manager.get('attendance', {
            'recognition_threshold': 0.6,
            'confirmation_frames': 3,
            'reconfirmation_interval': 300,  # 5 minutes
            'auto_mark_attendance': True,
            'save_recognition_photos': True
        })
        
        # Current session state
        self.current_session_id = None
        self.attendance_active = False
        self.attendance_mode = 'manual'  # 'manual', 'auto', 'continuous'
        
        # Real-time tracking
        self.recognized_students = {}  # student_id -> last_seen_time
        self.attendance_marked = set()  # Set of student_ids with marked attendance
        self.recognition_counts = defaultdict(int)  # student_id -> recognition_count
        self.attendance_lock = threading.Lock()
        
        # Statistics
        self.recognition_events = []
        self.attendance_events = []
        
        # Photo storage
        self.attendance_photos_dir = 'attendance_photos'
        import os
        os.makedirs(self.attendance_photos_dir, exist_ok=True)
    
    def start_attendance_session(self, session_id: str = None, mode: str = 'auto') -> bool:
        """Start attendance tracking for a session"""
        try:
            self.current_session_id = session_id or f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.attendance_mode = mode
            self.attendance_active = True
            
            # Reset tracking state
            with self.attendance_lock:
                self.recognized_students.clear()
                self.attendance_marked.clear()
                self.recognition_counts.clear()
                self.recognition_events.clear()
                self.attendance_events.clear()
            
            # Log session start
            self.database_manager.log_system_event(
                'attendance_session_start',
                f'Attendance session started in {mode} mode',
                'INFO',
                {'session_id': self.current_session_id, 'mode': mode}
            )
            
            logger.info(f"Attendance session started: {self.current_session_id} (mode: {mode})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start attendance session: {e}")
            return False
    
    def stop_attendance_session(self) -> Dict[str, Any]:
        """Stop attendance tracking and return session summary"""
        try:
            if not self.attendance_active:
                return {}
            
            self.attendance_active = False
            
            # Generate session summary
            summary = self.generate_attendance_summary()
            
            # Log session end
            self.database_manager.log_system_event(
                'attendance_session_end',
                f'Attendance session ended. {len(self.attendance_marked)} students marked present.',
                'INFO',
                {
                    'session_id': self.current_session_id,
                    'students_present': len(self.attendance_marked),
                    'recognition_events': len(self.recognition_events)
                }
            )
            
            logger.info(f"Attendance session ended: {self.current_session_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to stop attendance session: {e}")
            return {}
    
    def process_frame_for_attendance(self, frame) -> List[Dict[str, Any]]:
        """Process frame for attendance recognition"""
        if not self.attendance_active:
            return []
        
        try:
            # Recognize faces in frame
            recognized_faces = self.student_manager.recognize_faces_in_frame(
                frame, 
                tolerance=self.attendance_config.get('recognition_threshold', 0.6)
            )
            
            current_time = time.time()
            attendance_updates = []
            
            with self.attendance_lock:
                for student_id, confidence, bbox in recognized_faces:
                    # Update recognition tracking
                    self.recognized_students[student_id] = current_time
                    self.recognition_counts[student_id] += 1
                    
                    # Log recognition event
                    recognition_event = {
                        'timestamp': datetime.now().isoformat(),
                        'student_id': student_id,
                        'confidence': confidence,
                        'bbox': bbox,
                        'session_id': self.current_session_id
                    }
                    self.recognition_events.append(recognition_event)
                    
                    # Keep only recent events (last 1000)
                    if len(self.recognition_events) > 1000:
                        self.recognition_events = self.recognition_events[-1000:]
                    
                    # Check if we should mark attendance
                    should_mark = self._should_mark_attendance(student_id, confidence)
                    
                    if should_mark:
                        success = self._mark_student_attendance(student_id, confidence, frame, bbox)
                        if success:
                            attendance_updates.append({
                                'student_id': student_id,
                                'action': 'marked_present',
                                'confidence': confidence,
                                'timestamp': datetime.now().isoformat()
                            })
            
            return attendance_updates
            
        except Exception as e:
            logger.error(f"Error processing frame for attendance: {e}")
            return []
    
    def _should_mark_attendance(self, student_id: str, confidence: float) -> bool:
        """Determine if attendance should be marked for a student"""
        try:
            # Check if already marked today
            if student_id in self.attendance_marked:
                return False
            
            # Check confidence threshold
            min_confidence = self.attendance_config.get('recognition_threshold', 0.6)
            if confidence < min_confidence:
                return False
            
            # Check confirmation frames requirement
            min_confirmations = self.attendance_config.get('confirmation_frames', 3)
            if self.recognition_counts[student_id] < min_confirmations:
                return False
            
            # Check if auto-mark is enabled
            if not self.attendance_config.get('auto_mark_attendance', True):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking attendance marking criteria: {e}")
            return False
    
    def _mark_student_attendance(self, student_id: str, confidence: float, frame, bbox) -> bool:
        """Mark attendance for a student"""
        try:
            # Save recognition photo if enabled
            photo_path = None
            if self.attendance_config.get('save_recognition_photos', True):
                photo_path = self._save_attendance_photo(student_id, frame, bbox)
            
            # Mark attendance in database
            success = self.student_manager.mark_attendance(
                student_id=student_id,
                session_id=self.current_session_id,
                confidence=confidence
            )
            
            if success:
                self.attendance_marked.add(student_id)
                
                # Log attendance event
                attendance_event = {
                    'timestamp': datetime.now().isoformat(),
                    'student_id': student_id,
                    'confidence': confidence,
                    'photo_path': photo_path,
                    'session_id': self.current_session_id,
                    'method': 'automatic_recognition'
                }
                self.attendance_events.append(attendance_event)
                
                # Get student info for logging
                student = self.student_manager.get_student(student_id)
                student_name = f"{student['first_name']} {student['last_name']}" if student else student_id
                
                logger.info(f"Attendance marked for {student_name} (ID: {student_id}, confidence: {confidence:.3f})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to mark attendance for {student_id}: {e}")
            return False
    
    def _save_attendance_photo(self, student_id: str, frame, bbox) -> Optional[str]:
        """Save photo of student recognition for attendance"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"attendance_{student_id}_{timestamp}.jpg"
            filepath = f"{self.attendance_photos_dir}/{filename}"
            
            # Extract face region
            x, y, w, h = bbox
            face_region = frame[y:y+h, x:x+w]
            
            # Add some padding
            padding = 20
            y_start = max(0, y - padding)
            y_end = min(frame.shape[0], y + h + padding)
            x_start = max(0, x - padding)
            x_end = min(frame.shape[1], x + w + padding)
            
            cropped_frame = frame[y_start:y_end, x_start:x_end]
            
            # Save image
            cv2.imwrite(filepath, cropped_frame)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save attendance photo for {student_id}: {e}")
            return None
    
    def manual_mark_attendance(self, student_id: str, notes: str = "") -> Tuple[bool, str]:
        """Manually mark attendance for a student"""
        try:
            # Check if student exists
            student = self.student_manager.get_student(student_id)
            if not student:
                return False, f"Student {student_id} not found"
            
            # Check if already marked
            if student_id in self.attendance_marked:
                return False, f"Attendance already marked for {student_id}"
            
            # Mark attendance
            success = self.student_manager.mark_attendance(
                student_id=student_id,
                session_id=self.current_session_id,
                confidence=1.0  # Manual marking gets full confidence
            )
            
            if success:
                with self.attendance_lock:
                    self.attendance_marked.add(student_id)
                
                # Log attendance event
                attendance_event = {
                    'timestamp': datetime.now().isoformat(),
                    'student_id': student_id,
                    'confidence': 1.0,
                    'session_id': self.current_session_id,
                    'method': 'manual',
                    'notes': notes
                }
                self.attendance_events.append(attendance_event)
                
                student_name = f"{student['first_name']} {student['last_name']}"
                logger.info(f"Manual attendance marked for {student_name} (ID: {student_id})")
                return True, f"Attendance marked for {student_name}"
            
            return False, "Failed to mark attendance in database"
            
        except Exception as e:
            logger.error(f"Failed to manually mark attendance for {student_id}: {e}")
            return False, f"Error: {str(e)}"
    
    def unmark_attendance(self, student_id: str) -> Tuple[bool, str]:
        """Unmark attendance for a student (for corrections)"""
        try:
            # Remove from current session tracking
            with self.attendance_lock:
                self.attendance_marked.discard(student_id)
            
            # Update database - set status to 'absent' or delete record
            # For now, we'll update the status rather than delete
            today = datetime.now().date().isoformat()
            
            with self.database_manager.db_lock:
                conn = self.database_manager.get_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE attendance 
                    SET status = 'absent', notes = 'Unmarked by administrator'
                    WHERE student_id = ? AND exam_date = ?
                ''', (student_id, today))
                
                rows_affected = cursor.rowcount
                conn.commit()
                conn.close()
            
            if rows_affected > 0:
                student = self.student_manager.get_student(student_id)
                student_name = f"{student['first_name']} {student['last_name']}" if student else student_id
                logger.info(f"Attendance unmarked for {student_name} (ID: {student_id})")
                return True, f"Attendance unmarked for {student_name}"
            
            return False, "No attendance record found to unmark"
            
        except Exception as e:
            logger.error(f"Failed to unmark attendance for {student_id}: {e}")
            return False, f"Error: {str(e)}"
    
    def get_current_attendance_status(self) -> Dict[str, Any]:
        """Get current attendance session status"""
        try:
            with self.attendance_lock:
                # Get recent recognitions (last 60 seconds)
                recent_time = time.time() - 60
                recent_recognitions = {
                    student_id: last_seen 
                    for student_id, last_seen in self.recognized_students.items()
                    if last_seen > recent_time
                }
                
                status = {
                    'session_active': self.attendance_active,
                    'session_id': self.current_session_id,
                    'attendance_mode': self.attendance_mode,
                    'students_marked_present': len(self.attendance_marked),
                    'students_currently_visible': len(recent_recognitions),
                    'total_recognition_events': len(self.recognition_events),
                    'total_attendance_events': len(self.attendance_events),
                    'marked_students': list(self.attendance_marked),
                    'recently_seen_students': list(recent_recognitions.keys()),
                    'recognition_stats': dict(self.recognition_counts)
                }
                
                return status
                
        except Exception as e:
            logger.error(f"Error getting attendance status: {e}")
            return {}
    
    def generate_attendance_summary(self) -> Dict[str, Any]:
        """Generate comprehensive attendance summary"""
        try:
            # Get today's attendance
            today = datetime.now().date().isoformat()
            today_attendance = self.student_manager.get_attendance_for_date(today)
            
            # Get all registered students
            all_students = self.student_manager.get_all_students()
            
            present_students = [att for att in today_attendance if att['status'] == 'present']
            present_student_ids = {att['student_id'] for att in present_students}
            absent_students = [
                student for student in all_students 
                if student['student_id'] not in present_student_ids
            ]
            
            summary = {
                'session_id': self.current_session_id,
                'exam_date': today,
                'total_registered': len(all_students),
                'total_present': len(present_students),
                'total_absent': len(absent_students),
                'attendance_percentage': round((len(present_students) / len(all_students)) * 100, 1) if all_students else 0,
                'present_students': [
                    {
                        'student_id': att['student_id'],
                        'name': f"{att['first_name']} {att['last_name']}",
                        'check_in_time': att['check_in_time'],
                        'confidence': att['confidence'],
                        'course': att['course']
                    }
                    for att in present_students
                ],
                'absent_students': [
                    {
                        'student_id': student['student_id'],
                        'name': f"{student['first_name']} {student['last_name']}",
                        'course': student['course']
                    }
                    for student in absent_students
                ],
                'recognition_statistics': {
                    'total_recognitions': len(self.recognition_events),
                    'unique_students_recognized': len(set(event['student_id'] for event in self.recognition_events)),
                    'average_confidence': round(
                        sum(event['confidence'] for event in self.recognition_events) / len(self.recognition_events), 3
                    ) if self.recognition_events else 0,
                    'recognition_distribution': dict(self.recognition_counts)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating attendance summary: {e}")
            return {}
    
    def export_attendance_report(self, export_path: str, exam_date: str = None) -> bool:
        """Export attendance report to file"""
        try:
            exam_date = exam_date or datetime.now().date().isoformat()
            
            # Get attendance data
            attendance_data = self.student_manager.get_attendance_for_date(exam_date)
            summary = self.generate_attendance_summary()
            
            report = {
                'report_generated': datetime.now().isoformat(),
                'exam_date': exam_date,
                'session_id': self.current_session_id,
                'summary': summary,
                'detailed_attendance': attendance_data,
                'recognition_events': self.recognition_events[-100:] if self.recognition_events else [],  # Last 100 events
                'configuration': self.attendance_config
            }
            
            with open(export_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Attendance report exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export attendance report: {e}")
            return False
    
    def draw_attendance_annotations(self, frame, recognized_faces: List[Tuple[str, float, Tuple[int, int, int, int]]]):
        """Draw attendance-specific annotations on frame"""
        try:
            annotated_frame = frame.copy()
            
            for student_id, confidence, bbox in recognized_faces:
                x, y, w, h = bbox
                
                # Get student info
                student = self.student_manager.get_student(student_id)
                student_name = f"{student['first_name']} {student['last_name']}" if student else student_id
                
                # Color based on attendance status
                if student_id in self.attendance_marked:
                    color = (0, 255, 0)  # Green for marked present
                    status = "PRESENT"
                else:
                    color = (0, 255, 255)  # Yellow for recognized but not marked
                    status = "RECOGNIZED"
                
                # Draw bounding box
                cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw labels
                label = f"{student_name} ({confidence:.2f})"
                cv2.putText(annotated_frame, label, (x, y - 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                cv2.putText(annotated_frame, status, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw attendance session info
            if self.attendance_active:
                info_text = f"Attendance: {len(self.attendance_marked)} present | Session: {self.current_session_id}"
                cv2.putText(annotated_frame, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            return annotated_frame
            
        except Exception as e:
            logger.error(f"Error drawing attendance annotations: {e}")
            return frame
    
    def get_attendance_statistics(self) -> Dict[str, Any]:
        """Get attendance tracking statistics"""
        try:
            stats = {
                'session_active': self.attendance_active,
                'current_session_id': self.current_session_id,
                'attendance_mode': self.attendance_mode,
                'configuration': self.attendance_config.copy()
            }
            
            if self.attendance_active:
                with self.attendance_lock:
                    stats.update({
                        'students_marked_present': len(self.attendance_marked),
                        'total_recognition_events': len(self.recognition_events),
                        'total_attendance_events': len(self.attendance_events),
                        'unique_students_recognized': len(self.recognition_counts),
                        'average_recognitions_per_student': round(
                            sum(self.recognition_counts.values()) / len(self.recognition_counts), 1
                        ) if self.recognition_counts else 0
                    })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting attendance statistics: {e}")
            return {}
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update attendance configuration"""
        self.attendance_config.update(new_config)
        logger.info("Attendance configuration updated")
