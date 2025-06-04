#!/usr/bin/env python3
"""
Exam Utilities for Exam Monitoring System
Helper functions, email notifications, system monitoring, and other utilities
(Renamed from utils.py to avoid conflict with YOLOv5 utils module)
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import cv2

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Email functionality
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    from email.mime.image import MimeImage
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitors system performance and health"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_check_time = 0
        
    def get_system_stats(self) -> Optional[Dict[str, Any]]:
        """Get Pi 5 system performance statistics"""
        if not PSUTIL_AVAILABLE:
            return None
            
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get Pi temperature
            temperature = self._get_pi_temperature()
            
            # Get network stats
            net_stats = psutil.net_io_counters()
            
            return {
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_used': memory.used // (1024**2),  # MB
                'memory_total': memory.total // (1024**2),  # MB
                'disk_percent': round(disk.percent, 1),
                'disk_used': disk.used // (1024**3),  # GB
                'disk_total': disk.total // (1024**3),  # GB
                'temperature': temperature,
                'uptime': round(time.time() - self.start_time, 1),
                'network_bytes_sent': net_stats.bytes_sent,
                'network_bytes_recv': net_stats.bytes_recv
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return None
    
    def _get_pi_temperature(self) -> float:
        """Get Raspberry Pi temperature"""
        try:
            # Try Pi 5 method first
            temp_result = os.popen("vcgencmd measure_temp").readline()
            if temp_result:
                temperature = float(temp_result.replace("temp=", "").replace("'C\n", ""))
                return round(temperature, 1)
        except:
            pass
        
        try:
            # Try thermal zone method
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_str = f.read().strip()
                temperature = float(temp_str) / 1000.0
                return round(temperature, 1)
        except:
            pass
        
        return 0.0
    
    def check_system_health(self) -> Dict[str, Any]:
        """Check system health and return warnings"""
        stats = self.get_system_stats()
        if not stats:
            return {'status': 'unknown', 'warnings': ['Unable to get system stats']}
        
        warnings = []
        status = 'healthy'
        
        # CPU check
        if stats['cpu_percent'] > 90:
            warnings.append(f"High CPU usage: {stats['cpu_percent']}%")
            status = 'warning'
        
        # Memory check
        if stats['memory_percent'] > 85:
            warnings.append(f"High memory usage: {stats['memory_percent']}%")
            status = 'warning'
        
        # Temperature check
        if stats['temperature'] > 75:
            warnings.append(f"High temperature: {stats['temperature']}°C")
            status = 'critical' if stats['temperature'] > 80 else 'warning'
        
        # Disk check
        if stats['disk_percent'] > 90:
            warnings.append(f"Low disk space: {100 - stats['disk_percent']}% free")
            status = 'warning'
        
        return {
            'status': status,
            'warnings': warnings,
            'stats': stats
        }

class EmailNotifier:
    """Handles email notifications for violations and alerts"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.alerts_config = config_manager.get_alerts_config()
        self.enabled = EMAIL_AVAILABLE and self.alerts_config.get('email_enabled', False)
        
        if not EMAIL_AVAILABLE and self.alerts_config.get('email_enabled', False):
            logger.warning("Email notifications requested but email modules not available")
    
    def send_violation_alert(self, violation_type: str, description: str, 
                           confidence: float, violation_count: int, 
                           screenshot_path: str = None) -> bool:
        """Send email alert for violations"""
        if not self.enabled:
            return False
        
        try:
            subject = f"Exam Violation Detected: {violation_type}"
            
            body = f"""
Violation detected during exam monitoring:

Type: {violation_type}
Description: {description}
Confidence: {confidence:.2f}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total violations in session: {violation_count}

This is an automated alert from the Exam Monitoring System.
Please review the violation and take appropriate action if necessary.
"""
            
            return self._send_email(subject, body, screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to send violation alert: {e}")
            return False
    
    def send_system_alert(self, alert_type: str, message: str, severity: str = 'INFO') -> bool:
        """Send system alert email"""
        if not self.enabled:
            return False
        
        try:
            subject = f"Exam Monitor System Alert: {alert_type}"
            
            body = f"""
System alert from Exam Monitoring System:

Alert Type: {alert_type}
Severity: {severity}
Message: {message}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

System Information:
- Monitoring System: Active
- Alert Generated: Automatically

Please check the system if this is a critical alert.
"""
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send system alert: {e}")
            return False
    
    def send_session_summary(self, session_data: Dict[str, Any]) -> bool:
        """Send session summary email"""
        if not self.enabled:
            return False
        
        try:
            subject = f"Exam Session Summary - {session_data.get('session_id', 'Unknown')}"
            
            violations = session_data.get('violations', [])
            violation_summary = session_data.get('violation_summary', [])
            
            body = f"""
Exam Monitoring Session Summary:

Session ID: {session_data.get('session_id', 'Unknown')}
Start Time: {session_data.get('start_time', 'Unknown')}
End Time: {session_data.get('end_time', 'Unknown')}
Duration: {session_data.get('duration', 'Unknown')}
Total Violations: {len(violations)}

Violation Breakdown:
"""
            
            for summary in violation_summary:
                body += f"- {summary['type']}: {summary['count']} times\n"
            
            if violations:
                body += "\nRecent Violations:\n"
                for violation in violations[:10]:  # Last 10 violations
                    body += f"- {violation['timestamp']}: {violation['violation_type']} - {violation['description']}\n"
            
            body += "\nThis is an automated summary from the Exam Monitoring System."
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send session summary: {e}")
            return False
    
    def _send_email(self, subject: str, body: str, attachment_path: str = None) -> bool:
        """Send email with optional attachment"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.alerts_config['email_from']
            msg['To'] = self.alerts_config['email_to']
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MimeText(body, 'plain'))
            
            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                try:
                    with open(attachment_path, 'rb') as f:
                        img_data = f.read()
                    
                    img = MimeImage(img_data)
                    img.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(attachment_path)}"')
                    msg.attach(img)
                except Exception as e:
                    logger.warning(f"Failed to attach image: {e}")
            
            # Send email
            server = smtplib.SMTP(self.alerts_config['email_smtp'], self.alerts_config['email_port'])
            server.starttls()
            server.login(self.alerts_config['email_from'], self.alerts_config['email_password'])
            
            server.send_message(msg)
            server.quit()
            
            logger.info("Email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def test_email_config(self) -> bool:
        """Test email configuration"""
        return self.send_system_alert("Configuration Test", "This is a test email to verify email configuration.", "INFO")

class ScreenshotManager:
    """Manages screenshot capture and storage"""
    
    def __init__(self, screenshots_dir='screenshots'):
        self.screenshots_dir = screenshots_dir
        os.makedirs(screenshots_dir, exist_ok=True)
    
    def save_violation_screenshot(self, frame, violation_type: str, confidence: float = 0.0) -> str:
        """Save screenshot for a violation"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
            filename = f"violation_{violation_type.replace(' ', '_').lower()}_{timestamp}_{confidence:.2f}.jpg"
            filepath = os.path.join(self.screenshots_dir, filename)
            
            # Save with high quality
            quality = self._get_screenshot_quality()
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return ""
    
    def _get_screenshot_quality(self) -> int:
        """Get screenshot quality from config or default"""
        # This could be made configurable
        return 90
    
    def cleanup_old_screenshots(self, days_to_keep: int = 7) -> int:
        """Clean up old screenshots"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            
            for filename in os.listdir(self.screenshots_dir):
                filepath = os.path.join(self.screenshots_dir, filename)
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old screenshots")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup screenshots: {e}")
            return 0

class AlertManager:
    """Manages different types of alerts and notifications"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.alerts_config = config_manager.get_alerts_config()
        self.monitoring_config = config_manager.get_monitoring_config()
        
        self.last_alert_time = 0
        self.alert_cooldown = self.monitoring_config.get('alert_cooldown', 30)
        
        # Initialize components
        self.email_notifier = EmailNotifier(config_manager)
        self.screenshot_manager = ScreenshotManager()
    
    def trigger_violation_alert(self, violation_type: str, description: str, 
                              confidence: float, frame, violation_count: int):
        """Trigger all configured alerts for a violation"""
        current_time = time.time()
        
        # Check alert cooldown
        if current_time - self.last_alert_time < self.alert_cooldown:
            return
        
        self.last_alert_time = current_time
        
        # Save screenshot
        screenshot_path = self.screenshot_manager.save_violation_screenshot(
            frame, violation_type, confidence
        )
        
        # Sound alert
        if self.alerts_config.get('sound_alerts', True):
            self._play_sound_alert()
        
        # Email alert
        if self.alerts_config.get('email_enabled', False):
            self.email_notifier.send_violation_alert(
                violation_type, description, confidence, violation_count, screenshot_path
            )
        
        logger.warning(f"VIOLATION ALERT: {violation_type} - {description} (Confidence: {confidence:.2f})")
    
    def _play_sound_alert(self):
        """Play sound alert"""
        try:
            # Simple beep (cross-platform)
            if os.name == 'posix':  # Linux/Unix
                os.system('echo -e "\a"')
            elif os.name == 'nt':  # Windows
                import winsound
                winsound.Beep(1000, 500)
        except Exception as e:
            logger.warning(f"Failed to play sound alert: {e}")

class SessionManager:
    """Manages monitoring sessions"""
    
    def __init__(self):
        self.current_session_id = None
        self.session_start_time = None
        
    def start_session(self) -> str:
        """Start a new monitoring session"""
        self.current_session_id = self._generate_session_id()
        self.session_start_time = datetime.now()
        logger.info(f"Started monitoring session: {self.current_session_id}")
        return self.current_session_id
    
    def end_session(self) -> Optional[str]:
        """End current monitoring session"""
        if self.current_session_id:
            session_id = self.current_session_id
            logger.info(f"Ended monitoring session: {session_id}")
            self.current_session_id = None
            self.session_start_time = None
            return session_id
        return None
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get current session information"""
        if not self.current_session_id:
            return None
        
        return {
            'session_id': self.current_session_id,
            'start_time': self.session_start_time.isoformat() if self.session_start_time else None,
            'duration': (datetime.now() - self.session_start_time).total_seconds() if self.session_start_time else 0
        }
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"

def setup_logging(log_level: str = 'INFO') -> None:
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('exam_monitor.log')
        ]
    )

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    info = {
        'platform': os.name,
        'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'Model' in line:
                    info['pi_model'] = line.split(':')[1].strip()
                    break
    except:
        pass
    
    return info

def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def validate_email_config(config: Dict[str, Any]) -> list[str]:
    """Validate email configuration"""
    errors = []
    
    if not EMAIL_AVAILABLE:
        errors.append("Email modules not available")
        return errors
    
    required_fields = ['email_from', 'email_to', 'email_password', 'email_smtp']
    
    for field in required_fields:
        if not config.get(field):
            errors.append(f"Missing required email field: {field}")
    
    # Validate email format (basic)
    email_from = config.get('email_from', '')
    email_to = config.get('email_to', '')
    
    if email_from and '@' not in email_from:
        errors.append("Invalid sender email format")
    
    if email_to and '@' not in email_to:
        errors.append("Invalid recipient email format")
    
    # Validate port
    port = config.get('email_port', 0)
    if not isinstance(port, int) or port < 1 or port > 65535:
        errors.append("Invalid email port")
    
    return errors
