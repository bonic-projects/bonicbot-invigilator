#!/usr/bin/env python3
"""
Configuration Manager for Exam Monitoring System
Handles loading, saving, and validating configuration settings
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration settings for the exam monitoring system"""
    
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = {}
        self.default_config = self._get_default_config()
        self.load_config()
    
    def _get_default_config(self):
        """Get default configuration settings"""
        return {
            "camera": {
                "resolution": [1640, 1232],
                "fps": 20,
                "rotation": 0,
                "sensor_mode": "full_fov"
            },
            "detection": {
                "confidence_threshold": 0.4,
                "nms_threshold": 0.3,
                "max_faces": 1,
                "face_absence_threshold": 4.0,
                "head_turn_threshold": 25
            },
            "alerts": {
                "email_enabled": False,
                "email_smtp": "smtp.gmail.com",
                "email_port": 587,
                "email_from": "",
                "email_password": "",
                "email_to": "",
                "sound_alerts": True
            },
            "model": {
                "yolo_model": "yolov5m",
                "device": "cpu"
            },
            "web_server": {
                "host": "0.0.0.0",
                "port": 5000,
                "debug": False
            },
            "monitoring": {
                "alert_cooldown": 30,
                "screenshot_quality": 90,
                "log_level": "INFO"
            }
        }
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self.config = self._merge_configs(self.default_config, loaded_config)
                    logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.warning(f"Config file {self.config_file} not found. Using default configuration.")
                self.config = self.default_config.copy()
                self.save_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = self.default_config.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get(self, section, key=None, default=None):
        """Get configuration value"""
        try:
            if key is None:
                return self.config.get(section, default)
            else:
                return self.config.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def set(self, section, key, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
    
    def update_section(self, section, updates):
        """Update entire configuration section"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section].update(updates)
    
    def validate_config(self):
        """Validate configuration settings"""
        errors = []
        
        # Validate camera settings
        camera = self.config.get('camera', {})
        resolution = camera.get('resolution', [])
        if not isinstance(resolution, list) or len(resolution) != 2:
            errors.append("Camera resolution must be [width, height]")
        
        fps = camera.get('fps', 0)
        if not isinstance(fps, int) or fps <= 0 or fps > 60:
            errors.append("Camera FPS must be between 1 and 60")
        
        # Validate detection settings
        detection = self.config.get('detection', {})
        confidence = detection.get('confidence_threshold', 0)
        if not 0 <= confidence <= 1:
            errors.append("Confidence threshold must be between 0 and 1")
        
        # Validate web server settings
        web = self.config.get('web_server', {})
        port = web.get('port', 0)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("Web server port must be between 1 and 65535")
        
        # Validate email settings if enabled
        alerts = self.config.get('alerts', {})
        if alerts.get('email_enabled', False):
            required_email_fields = ['email_from', 'email_to', 'email_password']
            for field in required_email_fields:
                if not alerts.get(field):
                    errors.append(f"Email {field} is required when email alerts are enabled")
        
        return errors
    
    def _merge_configs(self, default, loaded):
        """Recursively merge loaded config with default config"""
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_camera_config(self):
        """Get camera-specific configuration"""
        return self.config.get('camera', {})
    
    def get_detection_config(self):
        """Get detection-specific configuration"""
        return self.config.get('detection', {})
    
    def get_alerts_config(self):
        """Get alerts-specific configuration"""
        return self.config.get('alerts', {})
    
    def get_model_config(self):
        """Get model-specific configuration"""
        return self.config.get('model', {})
    
    def get_web_config(self):
        """Get web server configuration"""
        return self.config.get('web_server', {})
    
    def get_monitoring_config(self):
        """Get monitoring-specific configuration"""
        return self.config.get('monitoring', {})
    
    def export_config(self, export_path):
        """Export configuration to a different file"""
        try:
            with open(export_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.info(f"Configuration exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False
    
    def import_config(self, import_path):
        """Import configuration from a file"""
        try:
            with open(import_path, 'r') as f:
                imported_config = json.load(f)
            
            # Validate imported config
            temp_config = self.config
            self.config = self._merge_configs(self.default_config, imported_config)
            errors = self.validate_config()
            
            if errors:
                self.config = temp_config  # Restore previous config
                logger.error(f"Invalid configuration in {import_path}: {errors}")
                return False
            
            self.save_config()
            logger.info(f"Configuration imported from {import_path}")
            return True
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset configuration to default values"""
        self.config = self.default_config.copy()
        self.save_config()
        logger.info("Configuration reset to defaults")
    
    def __getitem__(self, key):
        """Allow dictionary-style access"""
        return self.config[key]
    
    def __setitem__(self, key, value):
        """Allow dictionary-style assignment"""
        self.config[key] = value
    
    def __contains__(self, key):
        """Allow 'in' operator"""
        return key in self.config