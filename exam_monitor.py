#!/usr/bin/env python3
"""
Exam Monitoring System - Main Application
Orchestrates all modules for comprehensive exam proctoring and attendance tracking
Enhanced with Robot Invigilator functionality
"""

import sys
import time
import argparse
import logging
import threading
from datetime import datetime
from pathlib import Path

# Import our modules
try:
    from config_manager import ConfigManager
    from camera_manager import CameraManager
    from detection_engine import DetectionEngine
    from database_manager import DatabaseManager
    from exam_utils import SystemMonitor, AlertManager, SessionManager, setup_logging
    from web_server import WebServer
    from student_manager import StudentManager
    from attendance_manager import AttendanceManager
    from robot_controller import RobotInvigilator  # NEW: Robot integration
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all module files are in the same directory as exam_monitor.py")
    sys.exit(1)

# Setup logging
logger = logging.getLogger(__name__)

class ExamMonitoringSystem:
    """Main exam monitoring system that orchestrates all modules including robot invigilator"""
    
    def __init__(self, config_file='config.json', web_mode=False):
        self.web_mode = web_mode
        self.monitoring_active = False
        self.attendance_active = False
        self.start_time = time.time()
        
        # Initialize all managers
        self.config_manager = ConfigManager(config_file)
        self.system_monitor = SystemMonitor()
        self.session_manager = SessionManager()
        self.alert_manager = AlertManager(self.config_manager)
        
        # Initialize core components
        self.camera_manager = None
        self.detection_engine = None
        self.database_manager = None
        self.web_server = None
        
        # Initialize attendance components
        self.student_manager = None
        self.attendance_manager = None
        
        # Initialize robot components (NEW)
        self.robot_invigilator = None
        self.robot_enabled = False
        
        # Threading
        self.monitoring_thread = None
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.violation_count = 0
        self.current_violations = []
        self.current_session_id = None
        self.current_attendance_updates = []
        self.recent_violations = []  # Store recent violations for web display
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            logger.info("Initializing Enhanced Exam Monitoring System with Robot Support...")
            
            # Initialize database
            self.database_manager = DatabaseManager()
            
            # Initialize student management
            self.student_manager = StudentManager(self.database_manager)
            
            # Initialize attendance management
            self.attendance_manager = AttendanceManager(
                self.student_manager, 
                self.database_manager, 
                self.config_manager
            )
            
            # Initialize camera
            self.camera_manager = CameraManager(self.config_manager)
            if not self.camera_manager.initialize_camera():
                raise Exception("Failed to initialize camera")
            
            # Initialize detection engine
            self.detection_engine = DetectionEngine(self.config_manager)
            if not self.detection_engine.initialize_models():
                raise Exception("Failed to initialize detection models")
            
            # Connect attendance manager to detection engine
            self.detection_engine.set_attendance_manager(self.attendance_manager)
            
            # Initialize robot invigilator (NEW)
            try:
                self.robot_invigilator = RobotInvigilator(self)
                self.robot_enabled = True
                logger.info("Robot invigilator initialized successfully")
            except Exception as e:
                logger.warning(f"Robot invigilator initialization failed: {e}")
                self.robot_enabled = False
                self.robot_invigilator = None
            
            # Initialize web server if in web mode
            if self.web_mode:
                self.web_server = WebServer(self, self.config_manager)
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    def start_monitoring(self, attendance_mode: bool = False) -> bool:
        """Start the monitoring process"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return False
        
        try:
            # Start new session
            self.current_session_id = self.session_manager.start_session()
            self.database_manager.create_session(
                self.current_session_id,
                camera_method=self.camera_manager.camera_method,
                config_snapshot=self.config_manager.config
            )
            
            # Reset statistics
            self.violation_count = 0
            self.current_violations = []
            self.current_attendance_updates = []
            self.recent_violations = []  # Clear recent violations for new session
            
            # Set attendance mode
            self.attendance_active = attendance_mode
            self.detection_engine.set_attendance_mode(attendance_mode)
            
            # Start attendance session if in attendance mode
            if attendance_mode:
                self.attendance_manager.start_attendance_session(
                    session_id=self.current_session_id,
                    mode='auto'
                )
            
            # Start monitoring
            self.monitoring_active = True
            
            if self.web_mode:
                # Start monitoring in background thread for web mode
                self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
                self.monitoring_thread.start()
            else:
                # Start monitoring in main thread for regular mode
                self._monitoring_loop()
            
            mode_text = "with attendance tracking" if attendance_mode else "for violation detection"
            logger.info(f"Monitoring started {mode_text} - Session: {self.current_session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self.monitoring_active = False
            return False
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        if not self.monitoring_active:
            return
        
        logger.info("Stopping monitoring...")
        self.monitoring_active = False
        self.shutdown_event.set()
        
        # Stop attendance session if active
        if self.attendance_active:
            attendance_summary = self.attendance_manager.stop_attendance_session()
            self.attendance_active = False
            logger.info(f"Attendance session summary: {attendance_summary.get('total_present', 0)} students present")
        
        # End session
        if self.current_session_id:
            self.database_manager.end_session(self.current_session_id)
            self.session_manager.end_session()
        
        # Wait for monitoring thread to finish
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        logger.info("Monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting monitoring loop...")
        
        try:
            while self.monitoring_active and not self.shutdown_event.is_set():
                # Read frame from camera
                ret, frame = self.camera_manager.read_frame()
                if not ret or frame is None:
                    logger.error("Failed to read frame from camera")
                    break
                
                # Apply rotation if configured
                rotation = self.config_manager.get('camera', 'rotation', 0)
                if rotation != 0:
                    frame = self.camera_manager.apply_rotation(frame, rotation)
                
                # Process frame for violations and attendance
                violations, faces, detections, attendance_updates = self.detection_engine.process_frame(frame)
                
                # Update current state
                self.current_violations = violations
                self.current_attendance_updates = attendance_updates
                
                # Handle violations (only if not in pure attendance mode)
                if not self.attendance_active or len(violations) > 0:
                    for violation_type, description, confidence in violations:
                        self._handle_violation(violation_type, description, confidence, frame)
                
                # Draw annotations for display
                annotated_frame = self.detection_engine.draw_annotations(
                    frame, faces, detections, violations, attendance_updates
                )
                
                # Add system stats overlay
                annotated_frame = self._add_system_overlay(annotated_frame)
                
                if self.web_mode:
                    # Update frame for web streaming
                    if self.web_server:
                        self.web_server.update_frame(annotated_frame)
                else:
                    # Display frame in OpenCV window
                    import cv2
                    cv2.imshow('Exam Monitoring System', annotated_frame)
                    
                    # Check for quit key
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('a'):  # Toggle attendance mode
                        self.toggle_attendance_mode()
                    elif key == ord('s'):  # Take screenshot
                        self.capture_screenshot(f"manual_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.033)  # ~30 FPS
                
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        finally:
            if not self.web_mode:
                import cv2
                cv2.destroyAllWindows()
            
            self.monitoring_active = False
    
    def toggle_attendance_mode(self):
        """Toggle between attendance and monitoring modes"""
        try:
            if self.attendance_active:
                # Stop attendance mode
                self.attendance_manager.stop_attendance_session()
                self.attendance_active = False
                self.detection_engine.set_attendance_mode(False)
                logger.info("Switched to monitoring mode")
            else:
                # Start attendance mode
                self.attendance_manager.start_attendance_session(
                    session_id=self.current_session_id,
                    mode='auto'
                )
                self.attendance_active = True
                self.detection_engine.set_attendance_mode(True)
                logger.info("Switched to attendance mode")
            
            return True
        except Exception as e:
            logger.error(f"Failed to toggle attendance mode: {e}")
            return False
    
    def _handle_violation(self, violation_type: str, description: str, confidence: float, frame):
        """Handle a detected violation"""
        # Increment violation count
        self.violation_count += 1
        
        # Log to database
        violation_id = self.database_manager.log_violation(
            violation_type=violation_type,
            description=description,
            confidence=confidence,
            session_id=self.current_session_id,
            metadata={'frame_number': self.detection_engine.frame_count}
        )
        
        # Add to recent violations for web display
        violation_data = {
            'id': violation_id,
            'timestamp': datetime.now().isoformat(),
            'violation_type': violation_type,
            'description': description,
            'confidence': confidence,
            'session_id': self.current_session_id
        }
        
        self.recent_violations.append(violation_data)
        
        # Keep only last 20 violations for web display
        if len(self.recent_violations) > 20:
            self.recent_violations = self.recent_violations[-20:]
        
        # Trigger alerts
        self.alert_manager.trigger_violation_alert(
            violation_type, description, confidence, frame, self.violation_count
        )
        
        logger.warning(f"VIOLATION #{self.violation_count}: {violation_type} - {description} (ID: {violation_id})")
    
    def _add_system_overlay(self, frame):
        """Add system information overlay to frame"""
        try:
            import cv2
            
            # Get system stats
            stats = self.system_monitor.get_system_stats()
            if stats:
                overlay_text = f"CPU: {stats['cpu_percent']}% | RAM: {stats['memory_percent']}% | Temp: {stats['temperature']}°C"
                cv2.putText(frame, overlay_text, (10, frame.shape[0]-80), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # Add session info
            if self.attendance_active:
                attendance_status = self.attendance_manager.get_current_attendance_status()
                present_count = attendance_status.get('students_marked_present', 0)
                cv2.putText(frame, f"Students Present: {present_count}", 
                           (10, frame.shape[0]-60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            else:
                cv2.putText(frame, f"Total Violations: {self.violation_count}", 
                           (10, frame.shape[0]-60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Add robot status (NEW)
            if self.robot_enabled and self.robot_invigilator:
                robot_status = "Robot: " + ("Active" if self.robot_invigilator.is_invigilating else "Ready")
                color = (0, 255, 0) if self.robot_invigilator.is_connected else (0, 0, 255)
                cv2.putText(frame, robot_status, (10, frame.shape[0]-100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Add timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cv2.putText(frame, timestamp, (10, frame.shape[0]-40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Add session ID
            cv2.putText(frame, f"Session: {self.current_session_id}", 
                       (10, frame.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            return frame
            
        except Exception as e:
            logger.error(f"Error adding system overlay: {e}")
            return frame
    
    # Robot API methods (NEW)
    def connect_robot(self):
        """Connect to the robot"""
        if not self.robot_enabled or not self.robot_invigilator:
            return False, "Robot not available"
        return self.robot_invigilator.connect_robot()
    
    def disconnect_robot(self):
        """Disconnect from the robot"""
        if self.robot_invigilator:
            self.robot_invigilator.disconnect_robot()
    
    def start_invigilation_sequence(self):
        """Start robot invigilation sequence"""
        if not self.robot_enabled or not self.robot_invigilator:
            return False, "Robot not available"
        return self.robot_invigilator.start_invigilation_sequence()
    
    def stop_invigilation_sequence(self):
        """Stop robot invigilation sequence"""
        if self.robot_invigilator:
            self.robot_invigilator.stop_invigilation_sequence()
    
    def test_robot_connection(self):
        """Test robot connection"""
        if not self.robot_enabled or not self.robot_invigilator:
            return False, "Robot not available"
        return self.robot_invigilator.test_robot_connection()
    
    def emergency_stop_robot(self):
        """Emergency stop robot"""
        if self.robot_invigilator:
            self.robot_invigilator.emergency_stop()
    
    def get_robot_status(self):
        """Get robot status"""
        if not self.robot_enabled or not self.robot_invigilator:
            return {
                'robot_enabled': False,
                'robot_available': False,
                'error': 'Robot not available'
            }
        
        status = self.robot_invigilator.get_status()
        status['robot_enabled'] = self.robot_enabled
        status['robot_available'] = True
        return status
    
    # Existing API methods (keeping all original methods)
    def is_monitoring_active(self) -> bool:
        """Check if monitoring is active"""
        return self.monitoring_active
    
    def is_attendance_active(self) -> bool:
        """Check if attendance tracking is active"""
        return self.attendance_active
    
    def get_violation_count(self) -> int:
        """Get total violation count"""
        return self.violation_count
    
    def get_current_violations(self) -> list:
        """Get current frame violations"""
        return self.current_violations
    
    def get_current_attendance_updates(self) -> list:
        """Get current attendance updates"""
        return self.current_attendance_updates
    
    def get_system_stats(self):
        """Get system performance statistics"""
        return self.system_monitor.get_system_stats()
    
    def get_camera_info(self):
        """Get camera information"""
        return self.camera_manager.get_camera_info() if self.camera_manager else {}
    
    def get_detection_stats(self):
        """Get detection performance statistics"""
        return self.detection_engine.get_detection_stats() if self.detection_engine else {}
    
    def get_violations(self, limit=50, offset=0, session_id=None, violation_type=None):
        """Get violations from database"""
        return self.database_manager.get_violations(limit, offset, session_id, violation_type)
    
    def get_recent_violations(self, limit=10):
        """Get recent violations for real-time display"""
        return self.recent_violations[-limit:] if self.recent_violations else []
    
    def get_violations_summary(self, session_id=None, days=None):
        """Get violations summary"""
        return self.database_manager.get_violations_summary(session_id, days)
    
    def get_sessions(self, limit=20):
        """Get monitoring sessions"""
        return self.database_manager.get_sessions(limit)
    
    def get_database_stats(self):
        """Get database statistics"""
        stats = self.database_manager.get_statistics()
        if self.student_manager:
            stats.update(self.student_manager.get_statistics())
        return stats
    
    def restart_camera(self) -> bool:
        """Restart camera"""
        if self.camera_manager:
            return self.camera_manager.restart_camera()
        return False
    
    def capture_screenshot(self, filename: str) -> bool:
        """Capture manual screenshot"""
        if self.camera_manager:
            return self.camera_manager.capture_screenshot(filename)
        return False
    
    def export_data(self, export_path: str, session_id: str = None) -> bool:
        """Export monitoring data"""
        if self.database_manager:
            return self.database_manager.export_data(export_path, session_id=session_id)
        return False
    
    # Attendance-specific API methods (keeping all original methods)
    def register_student(self, student_data, photo_file):
        """Register a new student"""
        if self.student_manager:
            return self.student_manager.register_student(student_data, photo_file)
        return False, "Student manager not available"
    
    def get_student(self, student_id):
        """Get student information"""
        if self.student_manager:
            return self.student_manager.get_student(student_id)
        return None
    
    def get_all_students(self, active_only=True):
        """Get all registered students"""
        if self.student_manager:
            return self.student_manager.get_all_students(active_only)
        return []
    
    def get_attendance_for_date(self, exam_date=None):
        """Get attendance for a specific date"""
        if self.student_manager:
            return self.student_manager.get_attendance_for_date(exam_date)
        return []
    
    def get_attendance_summary(self, start_date=None, end_date=None):
        """Get attendance summary"""
        if self.student_manager:
            return self.student_manager.get_attendance_summary(start_date, end_date)
        return {}
    
    def manual_mark_attendance(self, student_id, notes=""):
        """Manually mark attendance for a student"""
        if self.attendance_manager:
            return self.attendance_manager.manual_mark_attendance(student_id, notes)
        return False, "Attendance manager not available"
    
    def unmark_attendance(self, student_id):
        """Unmark attendance for a student"""
        if self.attendance_manager:
            return self.attendance_manager.unmark_attendance(student_id)
        return False, "Attendance manager not available"
    
    def get_attendance_status(self):
        """Get current attendance session status"""
        if self.attendance_manager:
            return self.attendance_manager.get_current_attendance_status()
        return {}
    
    def start_attendance_session(self, mode='auto'):
        """Start attendance tracking session"""
        if self.attendance_manager:
            return self.attendance_manager.start_attendance_session(
                session_id=self.current_session_id,
                mode=mode
            )
        return False
    
    def stop_attendance_session(self):
        """Stop attendance tracking session"""
        if self.attendance_manager:
            return self.attendance_manager.stop_attendance_session()
        return {}
    
    def export_attendance_report(self, export_path, exam_date=None):
        """Export attendance report"""
        if self.attendance_manager:
            return self.attendance_manager.export_attendance_report(export_path, exam_date)
        return False
    
    def update_student(self, student_id, updates):
        """Update student information"""
        if self.student_manager:
            return self.student_manager.update_student(student_id, updates)
        return False
    
    def delete_student(self, student_id):
        """Delete (deactivate) a student"""
        if self.student_manager:
            return self.student_manager.delete_student(student_id)
        return False
    
    def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up system resources...")
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Stop robot if active (NEW)
        if self.robot_invigilator:
            self.robot_invigilator.cleanup()
        
        # Cleanup components
        if self.camera_manager:
            self.camera_manager.cleanup()
        
        if self.detection_engine:
            self.detection_engine.cleanup()
        
        if self.database_manager:
            self.database_manager.close()
        
        logger.info("System cleanup completed")
    
    def run_web_mode(self, host='0.0.0.0', port=5000):
        """Run in web mode"""
        if not self.web_server:
            logger.error("Web server not initialized")
            return
        
        logger.info("Starting web server with robot invigilator support...")
        self.web_server.start_server(host, port)
    
    def run_regular_mode(self, attendance_mode=False):
        """Run in regular monitoring mode"""
        mode_text = "attendance tracking" if attendance_mode else "violation monitoring"
        logger.info(f"Starting regular mode for {mode_text}...")
        
        if not self.web_mode:
            print("\n" + "="*60)
            print("EXAM MONITORING SYSTEM - CONTROLS")
            print("="*60)
            print("• Press 'q' to quit")
            print("• Press 'a' to toggle attendance mode")
            print("• Press 's' to take screenshot")
            print("="*60)
            if attendance_mode:
                print("🎓 ATTENDANCE MODE: Tracking student presence")
            else:
                print("👁️  MONITORING MODE: Detecting violations")
            if self.robot_enabled:
                print("🤖 ROBOT: Available for invigilation")
            print("="*60 + "\n")
        
        self.start_monitoring(attendance_mode=attendance_mode)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Exam Monitoring System with Robot Invigilator')
    parser.add_argument('--web', action='store_true', help='Run in web mode with Flask server')
    parser.add_argument('--attendance', action='store_true', help='Start in attendance mode')
    parser.add_argument('--host', default='0.0.0.0', help='Web server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Web server port (default: 5000)')
    parser.add_argument('--config', default='config.json', help='Configuration file path')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Create monitoring system
    system = None
    
    try:
        if args.web:
            logger.info("Starting Exam Monitoring System with Robot Invigilator in Web Mode")
            system = ExamMonitoringSystem(config_file=args.config, web_mode=True)
            system.run_web_mode(host=args.host, port=args.port)
        else:
            logger.info("Starting Exam Monitoring System with Robot Invigilator in Regular Mode")
            system = ExamMonitoringSystem(config_file=args.config, web_mode=False)
            system.run_regular_mode(attendance_mode=args.attendance)
        
    except KeyboardInterrupt:
        logger.info("System interrupted by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        return 1
    finally:
        if system:
            system.cleanup()
    
    return 0

if __name__ == "__main__":
    exit(main())