#!/usr/bin/env python3
"""
Camera Manager for Exam Monitoring System
Handles camera initialization, frame capture, and different camera backends
"""

import cv2
import time
import logging
import threading
from typing import Tuple, Optional, Any

# Camera imports with Pi 5 support
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False

logger = logging.getLogger(__name__)

class CameraManager:
    """Manages camera operations for the exam monitoring system"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.camera_config = config_manager.get_camera_config()
        
        # Camera objects
        self.cap = None
        self.picam2 = None
        self.camera_method = None
        self.is_initialized = False
        
        # Frame management
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.last_frame_time = 0
        
        # Camera state
        self.is_recording = False
        self.frame_count = 0
        
    def initialize_camera(self) -> bool:
        """Initialize camera with specified settings (optimized for Pi 5)"""
        try:
            logger.info("Initializing camera...")
            
            # Try different camera methods in order of preference
            if self._try_picamera2():
                self.camera_method = "picamera2"
                logger.info("✓ Camera initialized using picamera2 (Pi 5 native)")
                self.is_initialized = True
                return True
            
            if self._try_gstreamer():
                self.camera_method = "gstreamer"
                logger.info("✓ Camera initialized using GStreamer pipeline")
                self.is_initialized = True
                return True
            
            if self._try_opencv_methods():
                logger.info(f"✓ Camera initialized using {self.camera_method}")
                self.is_initialized = True
                return True
            
            raise Exception("No working camera method found")
            
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            self._log_troubleshooting_steps()
            return False
    
    def _try_picamera2(self) -> bool:
        """Try to initialize camera using picamera2 (Pi 5 native)"""
        if not PICAMERA2_AVAILABLE:
            return False
        
        try:
            logger.info("Trying picamera2 method (Pi 5 native)...")
            self.picam2 = Picamera2()
            
            # Configure camera with full field of view
            width, height = self.camera_config.get('resolution', [1640, 1232])
            fps = self.camera_config.get('fps', 20)
            sensor_mode = self.camera_config.get('sensor_mode', 'full_fov')
            
            if sensor_mode == 'full_fov':
                # Use full sensor mode for wider field of view
                config = self.picam2.create_video_configuration(
                    main={"size": (width, height), "format": "RGB888"},
                    controls={"FrameRate": fps},
                    sensor={"output_size": (1640, 1232), "bit_depth": 10}
                )
            else:
                # Standard configuration
                config = self.picam2.create_preview_configuration(
                    main={"size": (width, height), "format": "RGB888"}
                )
            
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(2)  # Allow camera to stabilize
            
            # Test capture
            test_frame = self.picam2.capture_array()
            if test_frame is not None and test_frame.shape[0] > 0:
                logger.info(f"picamera2 working! Resolution: {test_frame.shape}")
                return True
            else:
                self._cleanup_picamera2()
                return False
                
        except Exception as e:
            logger.warning(f"picamera2 method failed: {e}")
            self._cleanup_picamera2()
            return False
    
    def _try_gstreamer(self) -> bool:
        """Try to initialize camera using GStreamer pipeline"""
        try:
            logger.info("Trying GStreamer pipeline method...")
            width, height = self.camera_config.get('resolution', [1640, 1232])
            fps = self.camera_config.get('fps', 20)
            
            pipeline = (
                f'libcamerasrc ! '
                f'video/x-raw,width={width},height={height},framerate={fps}/1 ! '
                f'videoconvert ! '
                f'appsink drop=1'
            )
            
            self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            
            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    logger.info(f"GStreamer working! Resolution: {test_frame.shape}")
                    return True
                else:
                    self.cap.release()
                    return False
            else:
                return False
                
        except Exception as e:
            logger.warning(f"GStreamer method failed: {e}")
            return False
    
    def _try_opencv_methods(self) -> bool:
        """Try various OpenCV camera methods"""
        camera_methods = [
            {'method': 'V4L2', 'init': lambda: cv2.VideoCapture(0, cv2.CAP_V4L2)},
            {'method': 'Standard', 'init': lambda: cv2.VideoCapture(0)},
            {'method': 'V4L2 Index 1', 'init': lambda: cv2.VideoCapture(1, cv2.CAP_V4L2)},
        ]
        
        for method_info in camera_methods:
            try:
                method_name = method_info['method']
                logger.info(f"Trying camera method: {method_name}")
                
                self.cap = method_info['init']()
                
                if self.cap.isOpened():
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None:
                        self.camera_method = method_name.lower().replace(' ', '_')
                        
                        # Set camera properties for OpenCV methods
                        self._configure_opencv_camera()
                        
                        logger.info(f"OpenCV method '{method_name}' working!")
                        return True
                    else:
                        self.cap.release()
                        
            except Exception as e:
                logger.warning(f"Camera method '{method_info['method']}' error: {e}")
                continue
        
        return False
    
    def _configure_opencv_camera(self):
        """Configure OpenCV camera properties"""
        if not self.cap:
            return
        
        width, height = self.camera_config.get('resolution', [1640, 1232])
        fps = self.camera_config.get('fps', 20)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency
        
        # Try to set MJPG codec for better performance
        try:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        except:
            pass
    
    def read_frame(self) -> Tuple[bool, Optional[Any]]:
        """Read frame from camera using the appropriate method"""
        if not self.is_initialized:
            return False, None
        
        try:
            if self.camera_method == "picamera2" and self.picam2:
                return self._read_picamera2_frame()
            else:
                return self._read_opencv_frame()
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return False, None
    
    def _read_picamera2_frame(self) -> Tuple[bool, Optional[Any]]:
        """Read frame from picamera2"""
        try:
            frame = self.picam2.capture_array()
            if frame is not None:
                # Convert RGB to BGR for OpenCV
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self._update_frame_stats()
                return True, frame_bgr
            else:
                return False, None
        except Exception as e:
            logger.error(f"picamera2 read error: {e}")
            return False, None
    
    def _read_opencv_frame(self) -> Tuple[bool, Optional[Any]]:
        """Read frame from OpenCV VideoCapture"""
        if self.cap:
            ret, frame = self.cap.read()
            if ret:
                self._update_frame_stats()
            return ret, frame
        return False, None
    
    def _update_frame_stats(self):
        """Update frame statistics"""
        current_time = time.time()
        self.last_frame_time = current_time
        self.frame_count += 1
    
    def get_camera_info(self) -> dict:
        """Get camera information and statistics"""
        info = {
            'method': self.camera_method,
            'initialized': self.is_initialized,
            'frame_count': self.frame_count,
            'last_frame_time': self.last_frame_time,
            'resolution': self.camera_config.get('resolution'),
            'fps': self.camera_config.get('fps'),
            'sensor_mode': self.camera_config.get('sensor_mode')
        }
        
        # Add method-specific info
        if self.camera_method == "picamera2" and self.picam2:
            try:
                # Get picamera2 specific info if available
                info['picamera2_info'] = "Active"
            except:
                pass
        elif self.cap:
            try:
                info['actual_width'] = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                info['actual_height'] = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                info['actual_fps'] = self.cap.get(cv2.CAP_PROP_FPS)
            except:
                pass
        
        return info
    
    def apply_rotation(self, frame, rotation: int):
        """Apply rotation to frame if specified"""
        if rotation == 0:
            return frame
        elif rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            logger.warning(f"Invalid rotation angle: {rotation}")
            return frame
    
    def start_recording(self):
        """Start recording frames (for future video recording feature)"""
        self.is_recording = True
        logger.info("Frame recording started")
    
    def stop_recording(self):
        """Stop recording frames"""
        self.is_recording = False
        logger.info("Frame recording stopped")
    
    def capture_screenshot(self, filename: str) -> bool:
        """Capture a screenshot to file"""
        try:
            ret, frame = self.read_frame()
            if ret and frame is not None:
                cv2.imwrite(filename, frame)
                logger.info(f"Screenshot saved to {filename}")
                return True
            else:
                logger.error("Failed to capture frame for screenshot")
                return False
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return False
    
    def update_config(self, new_config: dict):
        """Update camera configuration"""
        self.camera_config.update(new_config)
        logger.info("Camera configuration updated")
        # Note: Camera restart may be required for some changes
    
    def restart_camera(self) -> bool:
        """Restart camera with current configuration"""
        logger.info("Restarting camera...")
        self.cleanup()
        time.sleep(1)
        return self.initialize_camera()
    
    def _cleanup_picamera2(self):
        """Clean up picamera2 resources"""
        if self.picam2:
            try:
                self.picam2.stop()
            except:
                pass
            self.picam2 = None
    
    def _log_troubleshooting_steps(self):
        """Log troubleshooting steps for camera issues"""
        logger.error("Camera troubleshooting steps:")
        logger.error("1. Check camera connection and enable: sudo raspi-config -> Interface Options -> Camera")
        logger.error("2. Test camera: libcamera-still -o test.jpg")
        logger.error("3. Install Pi 5 support: pip install picamera2")
        logger.error("4. Install GStreamer: sudo apt install gstreamer1.0-libcamera")
        logger.error("5. Reboot and try again")
        logger.error("6. Consider using USB webcam as alternative")
    
    def cleanup(self):
        """Clean up camera resources"""
        logger.info("Cleaning up camera resources...")
        
        self.is_initialized = False
        
        if self.picam2:
            try:
                self.picam2.stop()
                logger.info("picamera2 stopped")
            except:
                pass
            self.picam2 = None
        
        if self.cap:
            try:
                self.cap.release()
                logger.info("OpenCV capture released")
            except:
                pass
            self.cap = None
        
        self.camera_method = None
        logger.info("Camera cleanup completed")
    
    def __enter__(self):
        """Context manager entry"""
        self.initialize_camera()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()