# Robot Invigilator - Autonomous Exam Monitoring System

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi 5](https://img.shields.io/badge/Raspberry%20Pi-5-red.svg)](https://www.raspberrypi.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive AI-powered exam monitoring system with autonomous robot invigilation capabilities, designed for Raspberry Pi 5 with Camera Module 2 and BonicBot S1 integration.

## 🎯 Project Overview

This system combines computer vision, face recognition, and robotics to create an autonomous exam invigilation solution. The robot patrols predefined positions while AI algorithms detect violations and track attendance in real-time.

### 🚀 Key Features

- **🤖 Autonomous Robot Invigilation**: BonicBot S1 patrols exam room automatically
- **👁️ Real-time Violation Detection**: YOLOv5-based detection of suspicious activities
- **👥 Face Recognition & Attendance**: Automated student identification and attendance marking
- **🌐 Web Interface**: Complete remote monitoring and control via browser
- **📊 Analytics Dashboard**: Comprehensive reporting and data visualization
- **📧 Alert System**: Email notifications and real-time alerts
- **🎥 Live Streaming**: Real-time camera feed with AI annotations
- **💾 Data Logging**: SQLite database with violation and attendance records

## 🔧 Hardware Requirements

### Essential Components
- **Raspberry Pi 5** (4GB+ RAM recommended)
- **Camera Module 2** (or compatible Pi camera)
- **BonicBot S1** robot platform
- **MicroSD Card** (32GB+ Class 10)
- **Power Supply** for Pi 5 (27W USB-C)
- **Network Connection** (WiFi or Ethernet)

### Optional Components
- **External Speaker** for audio alerts
- **GPIO Expansion Board** for additional sensors
- **Case/Enclosure** for Pi protection

## 📚 Learning Resources

This project is part of a comprehensive course available on **[Bonic.ai](https://bonic.ai)** - a project-based learning platform. The course includes:

- 📖 **Detailed Documentation**: Step-by-step assembly and coding guides
- 🎥 **Video Tutorials**: Complete walkthrough of system development
- 🛠️ **Component Guides**: Hardware integration and wiring diagrams
- 💡 **Learning Modules**: Computer vision, robotics, and AI concepts
- 🔧 **Troubleshooting**: Common issues and solutions
- 🎓 **Certification**: Project completion certificates

**[Visit Bonic.ai →](https://bonic.ai)** to access the full learning experience.

## ⚡ Quick Start

### 1. Hardware Setup
```bash
# Connect Camera Module 2 to Pi 5 camera port
# Connect BonicBot S1 via USB or GPIO UART
# Ensure all connections are secure
```

### 2. Software Installation
```bash
# Clone the repository
git clone <repository-url>
cd bonicbot-invigilator

# Run the automated installation script
chmod +x install_script.sh
sudo ./install_script.sh

# Reboot system
sudo reboot
```

### 3. Initial Configuration
```bash
# Navigate to project directory
cd exam_monitor

# Test camera functionality
libcamera-still -o test.jpg

# Test robot connection
python test_robot.py

# Configure robot positions via web interface
python exam_monitor.py --web
```

### 4. Start Monitoring
```bash
# Web interface mode (recommended)
./start_monitor_web.sh

# Direct monitoring mode
./start_monitor.sh

# Attendance tracking mode
./start_attendance.sh

# Robot invigilation mode
./start_robot_invigilation.sh
```

## 🖥️ Usage Modes

### 1. Web Interface Mode
Access the complete system via web browser:
```bash
# Start web server
python exam_monitor.py --web --host 0.0.0.0 --port 5000

# Access via browser
http://localhost:5000          # Local access
http://YOUR_PI_IP:5000         # Network access
```

**Web Interface Features:**
- 📹 Live camera feed with AI detection
- 🤖 Robot control and configuration
- 👥 Student registration and management
- 📋 Real-time attendance tracking
- 📊 Analytics and reporting dashboard
- ⚙️ System configuration and settings

### 2. Standalone Monitoring
```bash
# Violation detection mode
python exam_monitor.py

# Attendance tracking mode
python exam_monitor.py --attendance

# Robot invigilation mode
python exam_monitor.py --robot
```

### 3. Robot Control Commands
```bash
# Emergency stop
python -c "from robot_controller import *; robot = RobotInvigilator(None); robot.emergency_stop()"

# Test robot movements
python test_robot.py

# Configure robot positions
# Use web interface at http://YOUR_PI_IP:5000/robot
```

## ⚙️ Configuration

### Main Configuration (`config.json`)
```json
{
    "camera": {
        "resolution": [1640, 1232],
        "fps": 30,
        "sensor_mode": "full_fov"
    },
    "detection": {
        "confidence_threshold": 0.4,
        "face_absence_threshold": 4.0
    },
    "attendance": {
        "recognition_threshold": 0.6,
        "auto_mark_attendance": true
    }
}
```

### Robot Configuration (`robot_config.json`)
```json
{
    "serial_port": "/dev/ttyAMA0",
    "baudrate": 9600,
    "movement_speed": 80,
    "detection_duration": 30,
    "student_positions": [
        {
            "name": "Position 1",
            "forward_time": 2.0,
            "turn_angle": 0
        }
    ]
}
```

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │◄──►│  Flask Server   │◄──►│  Exam Monitor   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   BonicBot S1   │◄──►│ Robot Controller│◄───┤  Detection      │
└─────────────────┘    └─────────────────┘    │   Engine        │
                                               └─────────────────┘
┌─────────────────┐    ┌─────────────────┐              │
│   Camera V2     │◄──►│ Camera Manager  │◄─────────────┘
└─────────────────┘    └─────────────────┘    
                                               
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SQLite DB     │◄──►│ Database Mgr    │◄──►│ Student Manager │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎮 Control Interface

### Desktop Controls (Regular Mode)
- **'q'**: Quit monitoring
- **'a'**: Toggle attendance mode
- **'s'**: Take manual screenshot
- **'r'**: Robot emergency stop

### Web Interface Controls
- **🎯 Live Feed**: Real-time camera with AI annotations
- **🤖 Robot Control**: Start/stop invigilation, configure positions
- **👥 Student Management**: Register students, view attendance
- **📊 Analytics**: View reports, export data
- **⚙️ Settings**: Configure system parameters

## 📁 File Structure

```
robot-invigilator/
├── exam_monitor.py          # Main application
├── robot_controller.py      # Robot control logic
├── student_manager.py       # Student & face recognition
├── attendance_manager.py    # Attendance tracking
├── web_server.py           # Flask web interface
├── camera_manager.py       # Pi 5 camera handling
├── detection_engine.py     # AI detection (YOLOv5)
├── database_manager.py     # SQLite operations
├── config_manager.py       # Configuration handling
├── exam_utils.py          # Utility functions
├── install_script.sh      # Automated installer
├── requirements.txt       # Python dependencies
├── config.json           # Main configuration
├── robot_config.json     # Robot settings
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── robot.html
│   └── ...
└── scripts/              # Utility scripts
    ├── start_monitor.sh
    ├── start_robot.sh
    └── test_robot.py
```

## 🛠️ Installation Details

### System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y build-essential cmake git wget

# Install camera support (Pi 5)
sudo apt install -y python3-picamera2 libcamera-apps
sudo apt install -y gstreamer1.0-libcamera

# Install OpenCV dependencies
sudo apt install -y libopencv-dev python3-opencv
sudo apt install -y libatlas-base-dev libhdf5-dev

# Enable camera and UART
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_serial 2
```

### Python Dependencies
```bash
# Create virtual environment
python3 -m venv exam_monitor_env
source exam_monitor_env/bin/activate

# Install core packages
pip install opencv-python-headless numpy Pillow
pip install torch torchvision ultralytics
pip install flask flask-cors
pip install face_recognition dlib
pip install pyserial bonicbot
pip install picamera2
```

## 🚨 Troubleshooting

### Camera Issues
```bash
# Test camera functionality
libcamera-still -o test.jpg

# Check camera detection
lsusb  # For USB cameras
vcgencmd get_camera  # For Pi cameras

# Install Pi 5 camera support
pip install picamera2
sudo apt install python3-picamera2
```

### Robot Connection Issues
```bash
# Check serial ports
ls /dev/tty*

# Test serial connection
python test_robot.py

# Add user to dialout group
sudo usermod -a -G dialout $USER
# Reboot required after group change
```

### Face Recognition Issues
```bash
# Install dlib dependencies
sudo apt install libdlib-dev

# Alternative dlib installation
pip install dlib --no-cache-dir

# Memory issues - increase swap
sudo dphys-swapfile swapoff
sudo dphys-swapfile swapon
```

### YOLOv5 Issues
```bash
# Clear torch cache
rm -rf ~/.cache/torch

# Install dependencies
pip install seaborn matplotlib scipy PyYAML requests tqdm

# Alternative installation
pip install ultralytics
```

## 📈 Performance Optimization

### Raspberry Pi 5 Optimizations
```bash
# Increase GPU memory split
sudo raspi-config
# Advanced Options → Memory Split → 128

# Enable performance governor
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase swap for face recognition
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Model Optimization
- Use **YOLOv5s** for better performance on Pi 5
- Reduce camera resolution for better FPS
- Enable model caching
- Use confidence thresholds to reduce false positives

## 🔒 Security Considerations

- **Network Security**: Use HTTPS in production
- **Access Control**: Implement authentication for web interface
- **Data Privacy**: Encrypt stored student photos
- **Physical Security**: Secure robot against tampering
- **Regular Updates**: Keep all dependencies updated

## 📊 Data Management

### Database Schema
- **Students**: Registration and face encoding data
- **Attendance**: Check-in/out records with confidence scores
- **Violations**: Detected infractions with timestamps
- **Sessions**: Monitoring session metadata
- **Robot Logs**: Movement and invigilation history

### Data Export
```bash
# Export attendance report
python attendance_report.py

# Export violation data
python view_violations.py

# Backup database
cp exam_violations.db backup_$(date +%Y%m%d).db
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd robot-invigilator

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Code formatting
black *.py
flake8 *.py
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Bonic.ai](https://bonic.ai)** - Project-based learning platform
- **BonicBot Team** - Robot platform and libraries
- **Ultralytics** - YOLOv5 object detection
- **OpenCV Community** - Computer vision libraries
- **Raspberry Pi Foundation** - Single-board computer platform

## 📞 Support

### Get Help
- 📚 **Course Materials**: Access full tutorials on [Bonic.ai](https://bonic.ai)
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💬 **Community Support**: Join the Bonic.ai community forums
- 📧 **Direct Support**: Contact the development team

### Quick Links
- 🌐 **Project Homepage**: [Bonic.ai Course Page](https://bonic.ai)
- 📖 **Documentation**: [GitHub Wiki](wiki-link)
- 🎥 **Video Tutorials**: [Course Videos](course-videos-link)
- 💻 **Code Examples**: [Additional Examples](examples-link)

---

**⭐ Star this repository if you found it helpful!**

**🎓 Enroll in the full course at [Bonic.ai](https://bonic.ai) for comprehensive learning experience.**