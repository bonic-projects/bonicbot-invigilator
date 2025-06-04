#!/usr/bin/env python3
"""
Detection Engine for Exam Monitoring System
Handles YOLOv5 object detection, face detection, and violation analysis
Enhanced with attendance support through face recognition
"""

import cv2
import torch
import numpy as np
import logging
from typing import List, Tuple, Dict, Any
import time

logger = logging.getLogger(__name__)

class DetectionEngine:
    """Handles AI detection, violation analysis, and attendance recognition"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.detection_config = config_manager.get_detection_config()
        self.model_config = config_manager.get_model_config()
        
        # Models
        self.yolo_model = None
        self.face_cascade = None
        self.device = None
        
        # Detection parameters
        self.suspicious_objects = ['cell phone', 'book', 'laptop', 'tablet', 'mouse', 'keyboard']
        self.coco_classes = self._load_coco_classes()
        
        # State tracking
        self.person_tracker = {}
        self.last_face_time = time.time()
        
        # Performance metrics
        self.detection_times = []
        self.frame_count = 0
        
        # Attendance integration
        self.attendance_manager = None
        self.attendance_mode = False
    
    def set_attendance_manager(self, attendance_manager):
        """Set the attendance manager for face recognition integration"""
        self.attendance_manager = attendance_manager
        logger.info("Attendance manager integrated with detection engine")
    
    def set_attendance_mode(self, enabled: bool):
        """Enable or disable attendance mode"""
        self.attendance_mode = enabled
        logger.info(f"Attendance mode {'enabled' if enabled else 'disabled'}")
    
    def initialize_models(self) -> bool:
        """Initialize detection models"""
        try:
            logger.info("Initializing detection models...")
            
            if not self._load_yolo_model():
                return False
            
            if not self._load_face_cascade():
                return False
            
            logger.info("Detection models initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize detection models: {e}")
            return False
    
    def _load_yolo_model(self) -> bool:
        """Load YOLOv5 model with error handling"""
        try:
            logger.info("Loading YOLOv5 model...")
            
            model_name = self.model_config.get('yolo_model', 'yolov5s')
            device_name = self.model_config.get('device', 'cpu')
            
            # Load YOLOv5 model
            self.yolo_model = torch.hub.load('ultralytics/yolov5', 
                                           model_name, 
                                           pretrained=True, 
                                           trust_repo=True)
            
            # Configure model
            self.yolo_model.conf = self.detection_config.get('confidence_threshold', 0.4)
            self.yolo_model.iou = self.detection_config.get('nms_threshold', 0.3)
            
            # Set device
            self.device = torch.device(device_name)
            self.yolo_model.to(self.device)
            
            logger.info(f"YOLOv5 model '{model_name}' loaded successfully on {device_name}")
            return True
            
        except ImportError as e:
            if 'seaborn' in str(e):
                logger.error("Missing seaborn dependency. Run: pip install seaborn matplotlib scipy PyYAML requests tqdm")
            else:
                logger.error(f"Import error loading YOLOv5: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to load YOLOv5 model: {e}")
            self._try_clear_cache_and_reload()
            return False
    
    def _try_clear_cache_and_reload(self):
        """Try to clear cache and reload model"""
        try:
            import shutil
            import os
            
            cache_dir = os.path.expanduser("~/.cache/torch/hub")
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                logger.info("Cleared torch cache, retrying...")
                
                model_name = self.model_config.get('yolo_model', 'yolov5s')
                self.yolo_model = torch.hub.load('ultralytics/yolov5', 
                                               model_name, 
                                               pretrained=True,
                                               trust_repo=True)
                logger.info("YOLOv5 model loaded successfully after cache clear")
                return True
        except Exception as retry_error:
            logger.error(f"Failed to load model after cache clear: {retry_error}")
            return False
    
    def _load_face_cascade(self) -> bool:
        """Load OpenCV face cascade classifier"""
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            if self.face_cascade.empty():
                logger.error("Failed to load face cascade classifier")
                return False
            
            logger.info("Face cascade classifier loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading face cascade: {e}")
            return False
    
    def _load_coco_classes(self) -> List[str]:
        """Load COCO class names"""
        return [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
            'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
            'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
    
    def detect_faces(self, frame) -> List[Tuple[int, int, int, int]]:
        """Detect faces in the frame"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            return faces
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            return []
    
    def detect_objects(self, frame):
        """Detect objects using YOLOv5"""
        try:
            start_time = time.time()
            
            # Run inference
            results = self.yolo_model(frame)
            
            # Parse results
            detections = results.pandas().xyxy[0]
            
            # Record detection time
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            if len(self.detection_times) > 100:  # Keep last 100 times
                self.detection_times.pop(0)
            
            return detections
            
        except Exception as e:
            logger.error(f"Error in object detection: {e}")
            return None
    
    def analyze_head_pose(self, face_roi) -> bool:
        """Basic head pose analysis to detect looking away"""
        try:
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            # Detect eyes using Haar cascades
            eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
            eyes = eye_cascade.detectMultiScale(gray)
            
            # If less than 2 eyes detected, person might be looking away
            return len(eyes) < 2
            
        except Exception as e:
            logger.error(f"Error in head pose analysis: {e}")
            return False
    
    def process_frame(self, frame) -> Tuple[List[Tuple[str, str, float]], List, Any, List]:
        """Process a single frame for violations and attendance"""
        violations = []
        faces = []
        detections = None
        attendance_updates = []
        
        try:
            self.frame_count += 1
            
            # Handle attendance processing if enabled
            if self.attendance_mode and self.attendance_manager:
                attendance_updates = self.attendance_manager.process_frame_for_attendance(frame)
            
            # Detect faces (for both violation detection and attendance)
            faces = self.detect_faces(frame)
            
            # Check for multiple faces or no faces (violation detection)
            max_faces = self.detection_config.get('max_faces', 1)
            
            if len(faces) > max_faces:
                violations.append((
                    "Multiple Persons", 
                    f"Detected {len(faces)} persons in frame", 
                    0.9
                ))
            elif len(faces) == 0:
                # Check if face has been absent for too long
                current_time = time.time()
                face_absence_threshold = self.detection_config.get('face_absence_threshold', 4.0)
                
                if current_time - self.last_face_time > face_absence_threshold:
                    violations.append((
                        "No Person Detected", 
                        "Examinee not visible in frame", 
                        0.8
                    ))
            else:
                self.last_face_time = time.time()
            
            # Analyze head pose for single face (violation detection)
            if len(faces) == 1:
                x, y, w, h = faces[0]
                face_roi = frame[y:y+h, x:x+w]
                
                if self.analyze_head_pose(face_roi):
                    violations.append((
                        "Looking Away", 
                        "Examinee appears to be looking away", 
                        0.7
                    ))
            
            # Detect suspicious objects
            detections = self.detect_objects(frame)
            
            if detections is not None and len(detections) > 0:
                for _, detection in detections.iterrows():
                    class_name = detection['name']
                    confidence = detection['confidence']
                    
                    if class_name in self.suspicious_objects:
                        violations.append((
                            "Suspicious Object", 
                            f"Detected {class_name}", 
                            confidence
                        ))
                    
                    # Multiple persons check via YOLO
                    if class_name == 'person' and confidence > 0.5:
                        person_count = len(detections[detections['name'] == 'person'])
                        if person_count > max_faces:
                            violations.append((
                                "Multiple Persons", 
                                f"YOLO detected {person_count} persons", 
                                confidence
                            ))
            
            return violations, faces, detections, attendance_updates
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return violations, faces, detections, attendance_updates
    
    def draw_annotations(self, frame, faces, detections, violations, attendance_updates=None) -> np.ndarray:
        """Draw bounding boxes and annotations on frame"""
        try:
            annotated_frame = frame.copy()
            
            # If in attendance mode, use attendance-specific annotations
            if self.attendance_mode and self.attendance_manager:
                # Get recognized faces for attendance display
                recognized_faces = []
                if hasattr(self.attendance_manager.student_manager, 'recognize_faces_in_frame'):
                    recognized_faces = self.attendance_manager.student_manager.recognize_faces_in_frame(frame)
                
                # Draw attendance annotations
                annotated_frame = self.attendance_manager.draw_attendance_annotations(annotated_frame, recognized_faces)
                
                # Add attendance updates to display
                if attendance_updates:
                    for i, update in enumerate(attendance_updates[-3:]):  # Show last 3 updates
                        student_id = update.get('student_id', '')
                        action = update.get('action', '')
                        cv2.putText(annotated_frame, f"✓ {student_id} - {action}", 
                                   (10, 100 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                # Regular monitoring annotations
                # Draw face rectangles
                for (x, y, w, h) in faces:
                    cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(annotated_frame, 'Face', (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                # Draw object detections
                if detections is not None and len(detections) > 0:
                    for _, detection in detections.iterrows():
                        x1, y1, x2, y2 = int(detection['xmin']), int(detection['ymin']), \
                                         int(detection['xmax']), int(detection['ymax'])
                        class_name = detection['name']
                        confidence = detection['confidence']
                        
                        # Color based on object type
                        color = (0, 0, 255) if class_name in self.suspicious_objects else (255, 0, 0)
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                        
                        label = f"{class_name}: {confidence:.2f}"
                        cv2.putText(annotated_frame, label, (x1, y1-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Draw violation alerts (always show these)
            if violations:
                cv2.putText(annotated_frame, f"VIOLATIONS: {len(violations)}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                for i, (v_type, desc, conf) in enumerate(violations[:3]):  # Show max 3 violations
                    cv2.putText(annotated_frame, f"{v_type}", (10, 60 + i*25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)
            
            # Add mode indicator
            mode_text = "ATTENDANCE MODE" if self.attendance_mode else "MONITORING MODE"
            mode_color = (255, 255, 0) if self.attendance_mode else (255, 255, 255)
            cv2.putText(annotated_frame, mode_text, (annotated_frame.shape[1] - 250, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
            
            return annotated_frame
            
        except Exception as e:
            logger.error(f"Error drawing annotations: {e}")
            return frame
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection performance statistics"""
        stats = {
            'frame_count': self.frame_count,
            'model_name': self.model_config.get('yolo_model', 'unknown'),
            'device': str(self.device) if self.device else 'unknown',
            'suspicious_objects': self.suspicious_objects,
            'detection_config': self.detection_config.copy(),
            'attendance_mode': self.attendance_mode
        }
        
        if self.detection_times:
            stats['avg_detection_time'] = sum(self.detection_times) / len(self.detection_times)
            stats['max_detection_time'] = max(self.detection_times)
            stats['min_detection_time'] = min(self.detection_times)
            stats['fps_estimate'] = 1.0 / stats['avg_detection_time'] if stats['avg_detection_time'] > 0 else 0
        
        # Add attendance statistics if available
        if self.attendance_manager:
            stats['attendance_stats'] = self.attendance_manager.get_attendance_statistics()
        
        return stats
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update detection configuration"""
        self.detection_config.update(new_config)
        
        # Update model parameters if they changed
        if self.yolo_model:
            self.yolo_model.conf = self.detection_config.get('confidence_threshold', 0.4)
            self.yolo_model.iou = self.detection_config.get('nms_threshold', 0.3)
        
        logger.info("Detection configuration updated")
    
    def add_suspicious_object(self, object_name: str):
        """Add a new suspicious object to detect"""
        if object_name not in self.suspicious_objects:
            self.suspicious_objects.append(object_name)
            logger.info(f"Added suspicious object: {object_name}")
    
    def remove_suspicious_object(self, object_name: str):
        """Remove a suspicious object from detection"""
        if object_name in self.suspicious_objects:
            self.suspicious_objects.remove(object_name)
            logger.info(f"Removed suspicious object: {object_name}")
    
    def reset_stats(self):
        """Reset detection statistics"""
        self.detection_times.clear()
        self.frame_count = 0
        self.person_tracker.clear()
        logger.info("Detection statistics reset")
    
    def cleanup(self):
        """Clean up detection resources"""
        logger.info("Cleaning up detection resources...")
        
        if self.yolo_model:
            del self.yolo_model
            self.yolo_model = None
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.face_cascade = None
        self.device = None
        self.attendance_manager = None
        
        logger.info("Detection cleanup completed")
