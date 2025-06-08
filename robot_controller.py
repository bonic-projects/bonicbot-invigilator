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
from invigilation_sequence import RunSequence 

# Import BonicBot library (assuming it's installed)
try:
    from bonicbot import create_serial_controller, BonicBotController
    BONICBOT_AVAILABLE = True
except ImportError:
    BONICBOT_AVAILABLE = False
    print("Warning: BonicBot library not available. Robot functionality disabled.")

logger = logging.getLogger(__name__)

class RobotInvigilator:
    """Main robot invigilator controller"""
    
    def __init__(self, exam_monitor_system):
        self.exam_monitor = exam_monitor_system
        self.robot_controller = None
        self.is_connected = False
        self.is_invigilating = False
        self.current_position = 0
        self.invigilation_thread = None
        self.stop_event = threading.Event()
        
        # Statistics
        self.start_time = None
        
    def connect_robot(self) -> Tuple[bool, str]:
        """Connect to the robot"""
        if not BONICBOT_AVAILABLE:
            return False, "BonicBot library not available"
        
        try:
            serial_port = "/dev/ttyAMA0"
            baudrate = 9600
            
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
    
    def delay(self, seconds: float):
        elapsed = 0
        check_interval = 0.1
        while elapsed < seconds:
            if self.stop_event.is_set():
                self.robot_controller.stop()
                return False
            time.sleep(check_interval)
            elapsed += check_interval
        return True

    def _invigilation_sequence(self):
        """Execute the main invigilation sequence"""
        try:
            RunSequence(self.robot_controller, self.delay)  # Call the external invigilation sequence
            self._log_event("Invigilation sequence started")
            
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
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'bonicbot_available': BONICBOT_AVAILABLE,
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
