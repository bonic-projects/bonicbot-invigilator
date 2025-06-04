#!/usr/bin/env python3
"""
Robot Controller for Invigilator Bot
Handles robot movement sequences and integration with exam monitoring
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json

# Import BonicBot library (assuming it's installed)
try:
    from bonicbot import create_serial_controller, BonicBotController
    BONICBOT_AVAILABLE = True
except ImportError:
    BONICBOT_AVAILABLE = False
    print("Warning: BonicBot library not available. Robot functionality disabled.")

logger = logging.getLogger(__name__)

class RobotInvigilatorConfig:
    """Configuration for robot movement and invigilation sequence"""
    
    def __init__(self, config_file='robot_config.json'):
        self.config_file = config_file
        self.default_config = {
            "serial_port": "/dev/ttyAMA0",  # Adjust based on your system
            "baudrate": 115200,
            "movement_speed": 80,  # Base movement speed (0-255)
            "turn_speed": 60,      # Turning speed
            "detection_duration": 30,  # Detection time per student (seconds)
            "student_positions": [
                {
                    "name": "Student 1",
                    "forward_time": 2.0,    # Time to move forward (seconds)
                    "turn_angle": 0,        # 0=no turn, 1=left, 2=right
                    "turn_time": 0.0        # Time to turn (seconds)
                },
                {
                    "name": "Student 2", 
                    "forward_time": 1.5,
                    "turn_angle": 1,        # Turn left
                    "turn_time": 1.0
                },
                {
                    "name": "Student 3",
                    "forward_time": 1.5,
                    "turn_angle": 2,        # Turn right  
                    "turn_time": 1.2
                }
            ],
            "return_to_start": True,  # Whether to return to starting position
            "pause_between_moves": 1.0,  # Pause between movements (seconds)
            "head_scan_enabled": True,   # Enable head scanning during detection
            "head_scan_angles": [-45, 0, 45],  # Head pan angles for scanning
            "head_scan_interval": 5.0    # Time between head movements
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load robot configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                # Merge with defaults
                config = self.default_config.copy()
                config.update(loaded_config)
                return config
        except FileNotFoundError:
            logger.info(f"Config file {self.config_file} not found, creating with defaults")
            self.save_config(self.default_config)
            return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error loading robot config: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any] = None):
        """Save configuration to file"""
        try:
            config_to_save = config or self.config
            with open(self.config_file, 'w') as f:
                json.dump(config_to_save, f, indent=4)
            logger.info(f"Robot configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving robot config: {e}")
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values"""
        self.config.update(updates)
        self.save_config()

class RobotInvigilator:
    """Main robot invigilator controller"""
    
    def __init__(self, exam_monitor_system, config_file='robot_config.json'):
        self.exam_monitor = exam_monitor_system
        self.config = RobotInvigilatorConfig(config_file)
        self.robot_controller = None
        self.is_connected = False
        self.is_invigilating = False
        self.current_position = 0
        self.invigilation_thread = None
        self.stop_event = threading.Event()
        
        # Statistics
        self.start_time = None
        self.positions_visited = 0
        self.total_detections = 0
        self.invigilation_log = []
        
    def connect_robot(self) -> Tuple[bool, str]:
        """Connect to the robot"""
        if not BONICBOT_AVAILABLE:
            return False, "BonicBot library not available"
        
        try:
            serial_port = self.config.config['serial_port']
            baudrate = self.config.config['baudrate']
            
            logger.info(f"Connecting to robot on {serial_port} at {baudrate} baud")
            
            self.robot_controller = create_serial_controller(serial_port, baudrate)
            
            # Test connection by sending a simple command
            self.robot_controller.stop()  # Send stop command to test
            time.sleep(0.5)
            
            self.is_connected = True
            logger.info("Robot connected successfully")
            return True, "Robot connected successfully"
            
        except Exception as e:
            error_msg = f"Failed to connect to robot: {str(e)}"
            logger.error(error_msg)
            self.is_connected = False
            return False, error_msg
    
    def disconnect_robot(self):
        """Disconnect from the robot"""
        try:
            if self.robot_controller:
                self.robot_controller.stop()  # Stop any movement
                self.robot_controller.close()  # Close connection
                self.robot_controller = None
            
            self.is_connected = False
            logger.info("Robot disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting robot: {e}")
    
    def start_invigilation_sequence(self) -> Tuple[bool, str]:
        """Start the automated invigilation sequence"""
        if self.is_invigilating:
            return False, "Invigilation already in progress"
        
        if not self.is_connected:
            return False, "Robot not connected"
        
        try:
            self.is_invigilating = True
            self.stop_event.clear()
            self.start_time = datetime.now()
            self.positions_visited = 0
            self.total_detections = 0
            self.invigilation_log = []
            
            # Start invigilation in background thread
            self.invigilation_thread = threading.Thread(
                target=self._invigilation_sequence, 
                daemon=True
            )
            self.invigilation_thread.start()
            
            logger.info("Invigilation sequence started")
            return True, "Invigilation sequence started successfully"
            
        except Exception as e:
            self.is_invigilating = False
            error_msg = f"Failed to start invigilation: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def stop_invigilation_sequence(self):
        """Stop the invigilation sequence"""
        if not self.is_invigilating:
            return
        
        logger.info("Stopping invigilation sequence...")
        self.stop_event.set()
        self.is_invigilating = False
        
        # Stop robot movement
        if self.robot_controller:
            try:
                self.robot_controller.stop()
            except Exception as e:
                logger.error(f"Error stopping robot: {e}")
        
        # Stop exam monitoring if active
        if self.exam_monitor.is_monitoring_active():
            self.exam_monitor.stop_monitoring()
        
        # Wait for thread to finish
        if self.invigilation_thread and self.invigilation_thread.is_alive():
            self.invigilation_thread.join(timeout=5)
        
        logger.info("Invigilation sequence stopped")
    
    def _invigilation_sequence(self):
        """Execute the main invigilation sequence"""
        try:
            positions = self.config.config['student_positions']
            detection_duration = self.config.config['detection_duration']
            pause_between_moves = self.config.config['pause_between_moves']
            
            logger.info(f"Starting invigilation sequence for {len(positions)} positions")
            
            for i, position in enumerate(positions):
                if self.stop_event.is_set():
                    break
                
                self.current_position = i + 1
                position_name = position.get('name', f'Position {i+1}')
                
                logger.info(f"Moving to {position_name}")
                self._log_event(f"Moving to {position_name}")
                
                # Move to position
                success = self._move_to_position(position)
                if not success or self.stop_event.is_set():
                    break
                
                self.positions_visited += 1
                
                # Pause before starting detection
                time.sleep(pause_between_moves)
                
                if self.stop_event.is_set():
                    break
                
                # Start monitoring/detection
                logger.info(f"Starting detection at {position_name} for {detection_duration} seconds")
                self._log_event(f"Started detection at {position_name}")
                
                # Start exam monitoring in attendance mode for better student tracking
                monitoring_started = self.exam_monitor.start_monitoring(attendance_mode=True)
                
                if monitoring_started:
                    # Optional: Start head scanning for better coverage
                    if self.config.config.get('head_scan_enabled', False):
                        self._start_head_scanning()
                    
                    # Monitor for specified duration
                    detection_start = time.time()
                    while (time.time() - detection_start) < detection_duration:
                        if self.stop_event.is_set():
                            break
                        time.sleep(0.5)  # Check stop condition frequently
                    
                    # Stop monitoring
                    self.exam_monitor.stop_monitoring()
                    self.total_detections += 1
                    
                    logger.info(f"Detection completed at {position_name}")
                    self._log_event(f"Detection completed at {position_name}")
                else:
                    logger.warning(f"Failed to start monitoring at {position_name}")
                    self._log_event(f"Failed to start monitoring at {position_name}")
                
                # Pause before moving to next position
                if i < len(positions) - 1:  # Not the last position
                    time.sleep(pause_between_moves)
            
            # Return to start position if configured
            if self.config.config.get('return_to_start', False) and not self.stop_event.is_set():
                logger.info("Returning to starting position")
                self._log_event("Returning to starting position")
                self._return_to_start()
            
            # Generate summary
            self._generate_invigilation_summary()
            
        except Exception as e:
            logger.error(f"Error in invigilation sequence: {e}")
            self._log_event(f"Error in sequence: {str(e)}")
        finally:
            self.is_invigilating = False
            if self.robot_controller:
                try:
                    self.robot_controller.stop()
                except:
                    pass
    
    def _move_to_position(self, position: Dict[str, Any]) -> bool:
        """Move robot to specified position"""
        try:
            if not self.robot_controller:
                return False
            
            forward_time = position.get('forward_time', 2.0)
            turn_angle = position.get('turn_angle', 0)  # 0=none, 1=left, 2=right
            turn_time = position.get('turn_time', 0.0)
            movement_speed = self.config.config['movement_speed']
            turn_speed = self.config.config['turn_speed']
            
            # Move forward
            if forward_time > 0:
                logger.debug(f"Moving forward for {forward_time} seconds at speed {movement_speed}")
                self.robot_controller.move_forward(movement_speed)
                
                # Check for stop condition during movement
                elapsed = 0
                check_interval = 0.1
                while elapsed < forward_time:
                    if self.stop_event.is_set():
                        self.robot_controller.stop()
                        return False
                    time.sleep(check_interval)
                    elapsed += check_interval
                
                self.robot_controller.stop()
                time.sleep(0.2)  # Brief pause
            
            # Turn if specified
            if turn_angle > 0 and turn_time > 0:
                if turn_angle == 1:  # Turn left
                    logger.debug(f"Turning left for {turn_time} seconds at speed {turn_speed}")
                    self.robot_controller.turn_left(turn_speed)
                elif turn_angle == 2:  # Turn right
                    logger.debug(f"Turning right for {turn_time} seconds at speed {turn_speed}")
                    self.robot_controller.turn_right(turn_speed)
                
                # Check for stop condition during turn
                elapsed = 0
                check_interval = 0.1
                while elapsed < turn_time:
                    if self.stop_event.is_set():
                        self.robot_controller.stop()
                        return False
                    time.sleep(check_interval)
                    elapsed += check_interval
                
                self.robot_controller.stop()
                time.sleep(0.2)  # Brief pause after turn
            
            return True
            
        except Exception as e:
            logger.error(f"Error moving to position: {e}")
            if self.robot_controller:
                try:
                    self.robot_controller.stop()
                except:
                    pass
            return False
    
    def _start_head_scanning(self):
        """Start head scanning during detection"""
        try:
            if not self.robot_controller:
                return
            
            scan_angles = self.config.config.get('head_scan_angles', [-45, 0, 45])
            scan_interval = self.config.config.get('head_scan_interval', 5.0)
            
            # Start with center position
            self.robot_controller.control_head(pan_angle=0, tilt_angle=0)
            
            # Note: In a full implementation, you might want to run this in a separate thread
            # For simplicity, we'll just set initial position here
            
        except Exception as e:
            logger.error(f"Error in head scanning: {e}")
    
    def _return_to_start(self):
        """Return robot to starting position (simple reverse movements)"""
        try:
            # This is a simplified return - in practice, you might want to 
            # reverse the exact movements or use positioning systems
            
            movement_speed = self.config.config['movement_speed']
            
            # Turn around (180 degrees)
            self.robot_controller.turn_left(self.config.config['turn_speed'])
            time.sleep(2.0)  # Approximate 180 degree turn
            self.robot_controller.stop()
            
            # Move forward to approximate starting position
            self.robot_controller.move_forward(movement_speed)
            time.sleep(3.0)  # Adjust based on total forward movement
            self.robot_controller.stop()
            
            # Turn to face forward
            self.robot_controller.turn_left(self.config.config['turn_speed'])
            time.sleep(2.0)  # Another 180 degree turn
            self.robot_controller.stop()
            
        except Exception as e:
            logger.error(f"Error returning to start: {e}")
    
    def _log_event(self, event: str):
        """Log invigilation events"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'event': event,
            'position': self.current_position
        }
        self.invigilation_log.append(log_entry)
        logger.info(f"Invigilation Event: {event}")
    
    def _generate_invigilation_summary(self):
        """Generate and log invigilation summary"""
        try:
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds() if self.start_time else 0
            
            summary = {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'positions_visited': self.positions_visited,
                'total_detections': self.total_detections,
                'events_log': self.invigilation_log,
                'robot_config': self.config.config
            }
            
            # Save summary to file
            summary_filename = f"invigilation_summary_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
            try:
                with open(summary_filename, 'w') as f:
                    json.dump(summary, f, indent=2)
                logger.info(f"Invigilation summary saved to {summary_filename}")
            except Exception as e:
                logger.error(f"Failed to save summary: {e}")
            
            logger.info(f"Invigilation Summary: Visited {self.positions_visited} positions in {duration:.1f}s")
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current robot and invigilation status"""
        return {
            'robot_connected': self.is_connected,
            'is_invigilating': self.is_invigilating,
            'current_position': self.current_position,
            'positions_visited': self.positions_visited,
            'total_detections': self.total_detections,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'bonicbot_available': BONICBOT_AVAILABLE,
            'config': self.config.config
        }
    
    def test_robot_connection(self) -> Tuple[bool, str]:
        """Test robot connection and basic movements"""
        if not self.is_connected:
            return False, "Robot not connected"
        
        try:
            logger.info("Testing robot movements...")
            
            # Test basic movements
            self.robot_controller.move_forward(50)
            time.sleep(0.5)
            self.robot_controller.stop()
            
            time.sleep(0.2)
            
            self.robot_controller.turn_left(50)
            time.sleep(0.5)
            self.robot_controller.stop()
            
            time.sleep(0.2)
            
            self.robot_controller.turn_right(50)
            time.sleep(0.5)
            self.robot_controller.stop()
            
            # Test head movement
            self.robot_controller.control_head(pan_angle=30, tilt_angle=0)
            time.sleep(0.5)
            self.robot_controller.control_head(pan_angle=0, tilt_angle=0)
            
            logger.info("Robot test completed successfully")
            return True, "Robot test completed successfully"
            
        except Exception as e:
            error_msg = f"Robot test failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def emergency_stop(self):
        """Emergency stop - immediately stop all robot movement"""
        logger.warning("Emergency stop activated!")
        
        try:
            if self.robot_controller:
                self.robot_controller.stop()
            
            self.stop_invigilation_sequence()
            
        except Exception as e:
            logger.error(f"Error during emergency stop: {e}")
    
    def cleanup(self):
        """Clean up robot resources"""
        logger.info("Cleaning up robot controller...")
        
        self.stop_invigilation_sequence()
        self.disconnect_robot()
        
        logger.info("Robot controller cleanup completed")
