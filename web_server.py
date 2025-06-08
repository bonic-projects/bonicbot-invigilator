#!/usr/bin/env python3
"""
Web Server for Exam Monitoring System
Flask-based web interface for remote monitoring, control, and attendance management
Enhanced with Robot Invigilator control
"""

import cv2
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import json
import base64

# Flask imports
try:
    from flask import Flask, render_template, Response, jsonify, request, send_from_directory, redirect, url_for, flash
    from werkzeug.utils import secure_filename
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

logger = logging.getLogger(__name__)

class WebServer:
    """Flask web server for remote monitoring, attendance management, and robot control"""
    
    def __init__(self, monitoring_system, config_manager):
        self.monitoring_system = monitoring_system
        self.config_manager = config_manager
        self.web_config = config_manager.get_web_config()
        
        # Flask app
        self.app = None
        self.server_thread = None
        self.is_running = False
        
        # Frame streaming
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # File upload configuration
        self.upload_folder = 'uploads'
        Path(self.upload_folder).mkdir(exist_ok=True)
        
        if FLASK_AVAILABLE:
            self.setup_flask_app()
        else:
            logger.error("Flask not available - web server disabled")
    
    def setup_flask_app(self):
        """Setup Flask web application"""
        self.app = Flask(__name__)
        self.app.secret_key = 'exam_monitor_secret_key_change_in_production'
        
        # Configure Flask
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
        self.app.config['UPLOAD_FOLDER'] = self.upload_folder
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/attendance')
        def attendance():
            return render_template('attendance.html')
        
        @self.app.route('/students')
        def students():
            return render_template('students.html')
        
        @self.app.route('/reports')
        def reports():
            return render_template('reports.html')
        
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self._generate_frames(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @self.app.route('/api/status')
        def api_status():
            """Get system status"""
            try:
                system_stats = self.monitoring_system.get_system_stats()
                camera_info = self.monitoring_system.get_camera_info()
                detection_stats = self.monitoring_system.get_detection_stats()
                attendance_status = self.monitoring_system.get_attendance_status()
                robot_status = self.monitoring_system.get_robot_status()  # NEW
                
                return jsonify({
                    'monitoring_active': self.monitoring_system.is_monitoring_active(),
                    'attendance_active': self.monitoring_system.is_attendance_active(),
                    'violation_count': self.monitoring_system.get_violation_count(),
                    'current_violations': len(self.monitoring_system.get_current_violations()),
                    'recent_violations': self.monitoring_system.get_recent_violations(5),
                    'current_attendance_updates': self.monitoring_system.get_current_attendance_updates(),
                    'system_stats': system_stats,
                    'camera_info': camera_info,
                    'detection_stats': detection_stats,
                    'attendance_status': attendance_status,
                    'robot_status': robot_status,  # NEW
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/violations')
        def api_violations():
            """Get violations data"""
            try:
                limit = request.args.get('limit', 50, type=int)
                offset = request.args.get('offset', 0, type=int)
                session_id = request.args.get('session_id')
                violation_type = request.args.get('type')
                realtime = request.args.get('realtime', 'false').lower() == 'true'
                
                if realtime:
                    violations = self.monitoring_system.get_recent_violations(limit)
                else:
                    violations = self.monitoring_system.get_violations(
                        limit=limit, offset=offset, session_id=session_id, 
                        violation_type=violation_type
                    )
                
                return jsonify({
                    'violations': violations,
                    'total_count': len(violations)
                })
            except Exception as e:
                logger.error(f"Error getting violations: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/monitoring', methods=['POST'])
        def api_monitoring():
            """Control monitoring"""
            try:
                data = request.get_json()
                action = data.get('action')
                attendance_mode = data.get('attendance_mode', False)
                
                if action == 'start':
                    if not self.monitoring_system.is_monitoring_active():
                        success = self.monitoring_system.start_monitoring(attendance_mode=attendance_mode)
                        if success:
                            mode_text = "with attendance tracking" if attendance_mode else "for violation detection"
                            return jsonify({'success': True, 'message': f'Monitoring started {mode_text}'})
                        else:
                            return jsonify({'success': False, 'message': 'Failed to start monitoring'})
                    else:
                        return jsonify({'success': False, 'message': 'Monitoring already active'})
                
                elif action == 'stop':
                    self.monitoring_system.stop_monitoring()
                    return jsonify({'success': True, 'message': 'Monitoring stopped'})
                
                elif action == 'toggle_attendance':
                    success = self.monitoring_system.toggle_attendance_mode()
                    if success:
                        is_attendance = self.monitoring_system.is_attendance_active()
                        mode = "attendance" if is_attendance else "monitoring"
                        return jsonify({'success': True, 'message': f'Switched to {mode} mode'})
                    else:
                        return jsonify({'success': False, 'message': 'Failed to toggle attendance mode'})
                
                elif action == 'restart':
                    self.monitoring_system.stop_monitoring()
                    time.sleep(1)
                    success = self.monitoring_system.start_monitoring(attendance_mode=attendance_mode)
                    if success:
                        return jsonify({'success': True, 'message': 'Monitoring restarted'})
                    else:
                        return jsonify({'success': False, 'message': 'Failed to restart monitoring'})
                
                else:
                    return jsonify({'error': 'Invalid action'}), 400
                    
            except Exception as e:
                logger.error(f"Error controlling monitoring: {e}")
                return jsonify({'error': str(e)}), 500
        
        # NEW: Robot Control APIs
        @self.app.route('/api/robot', methods=['GET', 'POST'])
        def api_robot():
            """Control robot"""
            if request.method == 'GET':
                # Get robot status
                try:
                    robot_status = self.monitoring_system.get_robot_status()
                    return jsonify(robot_status)
                except Exception as e:
                    logger.error(f"Error getting robot status: {e}")
                    return jsonify({'error': str(e)}), 500
            
            elif request.method == 'POST':
                # Control robot
                try:
                    data = request.get_json()
                    action = data.get('action')
                    
                    if action == 'connect':
                        success, message = self.monitoring_system.connect_robot()
                        return jsonify({'success': success, 'message': message})
                    
                    elif action == 'disconnect':
                        self.monitoring_system.disconnect_robot()
                        return jsonify({'success': True, 'message': 'Robot disconnected'})
                    
                    elif action == 'start_invigilation':
                        success, message = self.monitoring_system.start_invigilation_sequence()
                        return jsonify({'success': success, 'message': message})
                    
                    elif action == 'stop_invigilation':
                        self.monitoring_system.stop_invigilation_sequence()
                        return jsonify({'success': True, 'message': 'Invigilation sequence stopped'})
                    
                    elif action == 'test_connection':
                        success, message = self.monitoring_system.test_robot_connection()
                        return jsonify({'success': success, 'message': message})
                    
                    elif action == 'emergency_stop':
                        self.monitoring_system.emergency_stop_robot()
                        return jsonify({'success': True, 'message': 'Emergency stop activated'})
                    
                    else:
                        return jsonify({'error': 'Invalid robot action'}), 400
                        
                except Exception as e:
                    logger.error(f"Error controlling robot: {e}")
                    return jsonify({'error': str(e)}), 500
        
        # Student Management APIs (keeping existing code)
        @self.app.route('/api/students', methods=['GET', 'POST'])
        def api_students():
            """Get or register students"""
            if request.method == 'GET':
                try:
                    active_only = request.args.get('active_only', 'true').lower() == 'true'
                    students = self.monitoring_system.get_all_students(active_only=active_only)
                    return jsonify({'students': students})
                except Exception as e:
                    logger.error(f"Error getting students: {e}")
                    return jsonify({'error': str(e)}), 500
            
            elif request.method == 'POST':
                try:
                    if 'photo' not in request.files:
                        return jsonify({'error': 'No photo file provided'}), 400
                    
                    photo_file = request.files['photo']
                    if photo_file.filename == '':
                        return jsonify({'error': 'No photo file selected'}), 400
                    
                    student_data = {
                        'student_id': request.form.get('student_id'),
                        'first_name': request.form.get('first_name'),
                        'last_name': request.form.get('last_name'),
                        'email': request.form.get('email', ''),
                        'phone': request.form.get('phone', ''),
                        'course': request.form.get('course', ''),
                        'semester': request.form.get('semester', '')
                    }
                    
                    required_fields = ['student_id', 'first_name', 'last_name']
                    for field in required_fields:
                        if not student_data.get(field):
                            return jsonify({'error': f'Missing required field: {field}'}), 400
                    
                    success, message = self.monitoring_system.register_student(student_data, photo_file)
                    
                    if success:
                        return jsonify({'success': True, 'message': message})
                    else:
                        return jsonify({'success': False, 'message': message}), 400
                        
                except Exception as e:
                    logger.error(f"Error registering student: {e}")
                    return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/students/<student_id>', methods=['GET', 'PUT', 'DELETE'])
        def api_student_detail(student_id):
            """Get, update, or delete specific student"""
            if request.method == 'GET':
                try:
                    student = self.monitoring_system.get_student(student_id)
                    if student:
                        return jsonify({'student': student})
                    else:
                        return jsonify({'error': 'Student not found'}), 404
                except Exception as e:
                    logger.error(f"Error getting student {student_id}: {e}")
                    return jsonify({'error': str(e)}), 500
            
            elif request.method == 'PUT':
                try:
                    updates = request.get_json()
                    success = self.monitoring_system.update_student(student_id, updates)
                    
                    if success:
                        return jsonify({'success': True, 'message': 'Student updated successfully'})
                    else:
                        return jsonify({'success': False, 'message': 'Failed to update student'}), 400
                        
                except Exception as e:
                    logger.error(f"Error updating student {student_id}: {e}")
                    return jsonify({'error': str(e)}), 500
            
            elif request.method == 'DELETE':
                try:
                    success = self.monitoring_system.delete_student(student_id)
                    
                    if success:
                        return jsonify({'success': True, 'message': 'Student deleted successfully'})
                    else:
                        return jsonify({'success': False, 'message': 'Failed to delete student'}), 400
                        
                except Exception as e:
                    logger.error(f"Error deleting student {student_id}: {e}")
                    return jsonify({'error': str(e)}), 500
        
        # Attendance Management APIs (keeping existing code)
        @self.app.route('/api/attendance', methods=['GET', 'POST'])
        def api_attendance():
            """Get attendance or mark attendance"""
            if request.method == 'GET':
                try:
                    exam_date = request.args.get('exam_date')
                    attendance_data = self.monitoring_system.get_attendance_for_date(exam_date)
                    return jsonify({'attendance': attendance_data})
                except Exception as e:
                    logger.error(f"Error getting attendance: {e}")
                    return jsonify({'error': str(e)}), 500
            
            elif request.method == 'POST':
                try:
                    data = request.get_json()
                    action = data.get('action')
                    student_id = data.get('student_id')
                    
                    if action == 'mark':
                        notes = data.get('notes', '')
                        success, message = self.monitoring_system.manual_mark_attendance(student_id, notes)
                        return jsonify({'success': success, 'message': message})
                    
                    elif action == 'unmark':
                        success, message = self.monitoring_system.unmark_attendance(student_id)
                        return jsonify({'success': success, 'message': message})
                    
                    else:
                        return jsonify({'error': 'Invalid action'}), 400
                        
                except Exception as e:
                    logger.error(f"Error with attendance action: {e}")
                    return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/attendance/summary')
        def api_attendance_summary():
            """Get attendance summary"""
            try:
                start_date = request.args.get('start_date')
                end_date = request.args.get('end_date')
                
                summary = self.monitoring_system.get_attendance_summary(start_date, end_date)
                return jsonify({'summary': summary})
            except Exception as e:
                logger.error(f"Error getting attendance summary: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/attendance/session', methods=['POST'])
        def api_attendance_session():
            """Control attendance session"""
            try:
                data = request.get_json()
                action = data.get('action')
                
                if action == 'start':
                    mode = data.get('mode', 'auto')
                    success = self.monitoring_system.start_attendance_session(mode)
                    if success:
                        return jsonify({'success': True, 'message': f'Attendance session started in {mode} mode'})
                    else:
                        return jsonify({'success': False, 'message': 'Failed to start attendance session'})
                
                elif action == 'stop':
                    summary = self.monitoring_system.stop_attendance_session()
                    return jsonify({'success': True, 'message': 'Attendance session stopped', 'summary': summary})
                
                else:
                    return jsonify({'error': 'Invalid action'}), 400
                    
            except Exception as e:
                logger.error(f"Error controlling attendance session: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/camera', methods=['POST'])
        def api_camera():
            """Control camera"""
            try:
                data = request.get_json()
                action = data.get('action')
                
                if action == 'restart':
                    success = self.monitoring_system.restart_camera()
                    if success:
                        return jsonify({'success': True, 'message': 'Camera restarted'})
                    else:
                        return jsonify({'success': False, 'message': 'Failed to restart camera'})
                
                elif action == 'screenshot':
                    filename = f"manual_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    success = self.monitoring_system.capture_screenshot(filename)
                    if success:
                        return jsonify({'success': True, 'message': f'Screenshot saved: {filename}'})
                    else:
                        return jsonify({'success': False, 'message': 'Failed to take screenshot'})
                
                else:
                    return jsonify({'error': 'Invalid camera action'}), 400
                    
            except Exception as e:
                logger.error(f"Error controlling camera: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/export')
        def api_export():
            """Export data"""
            try:
                export_type = request.args.get('type', 'violations')
                export_format = request.args.get('format', 'json')
                exam_date = request.args.get('exam_date')
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                if export_type == 'attendance':
                    filename = f"attendance_report_{timestamp}.json"
                    success = self.monitoring_system.export_attendance_report(filename, exam_date)
                else:
                    session_id = request.args.get('session_id')
                    filename = f"exam_monitor_export_{timestamp}.json"
                    success = self.monitoring_system.export_data(filename, session_id=session_id)
                
                if success:
                    return jsonify({'success': True, 'filename': filename})
                else:
                    return jsonify({'success': False, 'message': 'Export failed'})
                    
            except Exception as e:
                logger.error(f"Error exporting data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/violations/summary')
        def api_violations_summary():
            """Get violations summary"""
            try:
                session_id = request.args.get('session_id')
                days = request.args.get('days', type=int)
                
                summary = self.monitoring_system.get_violations_summary(
                    session_id=session_id, days=days
                )
                
                return jsonify({'summary': summary})
            except Exception as e:
                logger.error(f"Error getting violations summary: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/sessions')
        def api_sessions():
            """Get monitoring sessions"""
            try:
                limit = request.args.get('limit', 20, type=int)
                sessions = self.monitoring_system.get_sessions(limit=limit)
                
                return jsonify({'sessions': sessions})
            except Exception as e:
                logger.error(f"Error getting sessions: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def api_config():
            """Get or update configuration"""
            if request.method == 'GET':
                try:
                    return jsonify(self.config_manager.config)
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            elif request.method == 'POST':
                try:
                    new_config = request.get_json()
                    
                    for section, values in new_config.items():
                        if isinstance(values, dict):
                            self.config_manager.update_section(section, values)
                        else:
                            self.config_manager.config[section] = values
                    
                    self.config_manager.save_config()
                    
                    return jsonify({'success': True, 'message': 'Configuration updated'})
                except Exception as e:
                    logger.error(f"Error updating config: {e}")
                    return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/system')
        def api_system():
            """Get system information"""
            try:
                from exam_utils import get_system_info
                system_info = get_system_info()
                
                return jsonify({
                    'system_info': system_info,
                    'database_stats': self.monitoring_system.get_database_stats(),
                    'uptime': time.time() - self.monitoring_system.start_time if hasattr(self.monitoring_system, 'start_time') else 0
                })
            except Exception as e:
                logger.error(f"Error getting system info: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/screenshots/<filename>')
        def screenshots(filename):
            """Serve screenshot files"""
            try:
                return send_from_directory('screenshots', filename)
            except Exception as e:
                logger.error(f"Error serving screenshot: {e}")
                return jsonify({'error': 'File not found'}), 404
        
        # Error handlers
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Not found'}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500
    
    def _generate_frames(self):
        """Generate frames for video streaming"""
        while True:
            try:
                if self.current_frame is not None:
                    with self.frame_lock:
                        frame = self.current_frame.copy()
                    
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                logger.error(f"Error generating frame: {e}")
                time.sleep(1)
    
    def update_frame(self, frame):
        """Update current frame for streaming"""
        try:
            with self.frame_lock:
                self.current_frame = frame
        except Exception as e:
            logger.error(f"Error updating frame: {e}")
            
    def start_server(self, host: str = None, port: int = None, debug: bool = False):
        """Start the Flask web server"""
        if not FLASK_AVAILABLE:
            logger.error("Flask not available - cannot start web server")
            return False
        
        if not self.app:
            logger.error("Flask app not initialized")
            return False
        
        host = host or self.web_config.get('host', '0.0.0.0')
        port = port or self.web_config.get('port', 5000)
        debug = debug or self.web_config.get('debug', False)
        
        try:
            logger.info(f"Starting web server with robot control on http://{host}:{port}")
            
            if host == '0.0.0.0':
                logger.info(f"Web interface accessible at:")
                logger.info(f"  - Local: http://localhost:{port}")
                logger.info(f"  - Network: http://YOUR_PI_IP:{port}")
                logger.info(f"  - Robot Control: Available via web dashboard")
            
            self.is_running = True
            self.app.run(host=host, port=port, debug=debug, threaded=True)
            
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            self.is_running = False
            return False
    
    def stop_server(self):
        """Stop the web server"""
        self.is_running = False
        logger.info("Web server stopped")
    
    def is_server_running(self) -> bool:
        """Check if server is running"""
        return self.is_running