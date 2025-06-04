#!/bin/bash
# Enhanced install.sh - Installation script for Exam Monitoring System with Robot Invigilator Support

echo "=== Exam Monitoring System with Robot Invigilator Setup ==="
echo "This script will install all required dependencies including robot control capabilities"

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies for face recognition
echo "Installing system dependencies for face recognition..."
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y libopencv-dev python3-opencv
sudo apt install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev
sudo apt install -y libqtgui4 libqt4-test
sudo apt install -y git wget cmake

# Install face recognition dependencies
echo "Installing face recognition system dependencies..."
sudo apt install -y build-essential cmake
sudo apt install -y libopenblas-dev liblapack-dev 
sudo apt install -y libx11-dev libgtk-3-dev
sudo apt install -y libboost-python-dev
sudo apt install -y libdlib-dev
sudo apt install -y python3-numpy python3-scipy

# Install robot-specific system dependencies
echo "Installing robot control system dependencies..."
sudo apt install -y python3-serial  # PySerial for robot communication
sudo apt install -y python3-smbus   # I2C communication (optional)
sudo apt install -y python3-rpi.gpio  # GPIO control (if using GPIO)

# Try to install dlib dependencies
echo "Installing dlib dependencies..."
sudo apt install -y libdlib19 libdlib-dev || echo "dlib packages not available, will compile from source"

# Install camera support (updated for Pi 5)
echo "Installing camera support..."
sudo apt install -y python3-picamera2  # NEW - for Pi 5
sudo apt install -y libcamera-apps libcamera-dev
sudo apt install -y v4l-utils  # V4L2 camera utilities
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good
sudo apt install -y gstreamer1.0-libcamera  # GStreamer camera support for Pi 5
sudo raspi-config nonint do_camera 0  # Enable camera

# Enable UART for robot communication (Pi 5 specific)
echo "Configuring UART for robot communication..."
sudo raspi-config nonint do_serial 2  # Enable UART, disable console
echo "enable_uart=1" | sudo tee -a /boot/firmware/config.txt
echo "dtoverlay=uart0" | sudo tee -a /boot/firmware/config.txt

# Add user to dialout group for serial port access
sudo usermod -a -G dialout $USER
sudo usermod -a -G video $USER

# Create virtual environment (in current directory)
echo "Creating Python virtual environment..."
python3 -m venv exam_monitor_env --system-site-packages
source exam_monitor_env/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install basic Python dependencies first
echo "Installing basic Python packages..."
pip install numpy
pip install Pillow
pip install opencv-python-headless

# Install robot communication libraries
echo "Installing robot communication libraries..."
pip install pyserial>=3.5  # Serial communication for robot
pip install RPi.GPIO || echo "RPi.GPIO not available (not on Raspberry Pi)"

# Install BonicBot library (if available)
echo "Installing BonicBot library..."
pip install bonicbot || {
    echo "BonicBot library not available via pip"
    echo "Please install manually or contact robot manufacturer for library"
    # Create a placeholder module for development
    mkdir -p temp_bonicbot
    cat > temp_bonicbot/bonicbot.py << 'EOF'
"""
Placeholder BonicBot module for development
Replace with actual BonicBot library when available
"""

class BonicBotController:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.connected = False
    
    def connect(self):
        print(f"[PLACEHOLDER] Connecting to robot on {self.port}")
        self.connected = True
        return True
    
    def disconnect(self):
        print("[PLACEHOLDER] Disconnecting from robot")
        self.connected = False
    
    def move_forward(self, speed):
        print(f"[PLACEHOLDER] Moving forward at speed {speed}")
    
    def move_backward(self, speed):
        print(f"[PLACEHOLDER] Moving backward at speed {speed}")
    
    def turn_left(self, speed):
        print(f"[PLACEHOLDER] Turning left at speed {speed}")
    
    def turn_right(self, speed):
        print(f"[PLACEHOLDER] Turning right at speed {speed}")
    
    def stop(self):
        print("[PLACEHOLDER] Stopping robot")
    
    def control_head(self, pan_angle=0, tilt_angle=0):
        print(f"[PLACEHOLDER] Moving head to pan:{pan_angle}, tilt:{tilt_angle}")
    
    def close(self):
        self.disconnect()

def create_serial_controller(port, baudrate):
    """Create a serial controller for the robot"""
    return BonicBotController(port, baudrate)
EOF
    pip install ./temp_bonicbot
    rm -rf temp_bonicbot
    echo "Installed placeholder BonicBot module for development"
}

# Install dlib (required for face_recognition)
echo "Installing dlib (this may take a while on Raspberry Pi)..."
pip install dlib || {
    echo "Failed to install dlib via pip, trying alternative method..."
    # Alternative: compile dlib from source with optimizations for Pi
    wget http://dlib.net/files/dlib-19.24.tar.bz2
    tar -xf dlib-19.24.tar.bz2
    cd dlib-19.24
    python3 setup.py install --compiler-flags "-O3"
    cd ..
    rm -rf dlib-19.24*
}

# Install face_recognition
echo "Installing face_recognition library..."
pip install face_recognition || {
    echo "Failed to install face_recognition, trying with no dependencies..."
    pip install --no-deps face_recognition
    pip install Click>=6.0
    pip install dlib>=19.7
    pip install numpy
    pip install Pillow
}

# Install PyTorch (optimized for Pi)
echo "Installing PyTorch..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other ML dependencies
echo "Installing machine learning packages..."
pip install pandas scipy scikit-learn
pip install ultralytics

# Install YOLOv5 dependencies
echo "Installing YOLOv5 dependencies..."
pip install seaborn matplotlib
pip install PyYAML requests tqdm
pip install thop  # For model analysis

# Install Pi 5 camera support (optional, for advanced camera features)
echo "Installing Pi 5 camera libraries..."
pip install picamera2 || echo "picamera2 install failed - will try fallback methods"

# Install Flask for web server
echo "Installing Flask for web interface..."
pip install flask flask-cors
pip install Werkzeug

# Install additional packages for attendance and robot system
echo "Installing additional packages for enhanced system..."
pip install psutil  # System monitoring
pip install python-dateutil  # Date handling
pip install python-magic  # File type detection

# Install email packages with error handling
echo "Installing email packages..."
pip install --upgrade setuptools
pip install --upgrade email-validator || echo "Warning: email-validator install failed"

# Create enhanced project directory structure
echo "Creating enhanced project structure with robot support..."
mkdir -p exam_monitor
mkdir -p exam_monitor/screenshots
mkdir -p exam_monitor/logs
mkdir -p exam_monitor/templates
mkdir -p exam_monitor/students
mkdir -p exam_monitor/students/photos
mkdir -p exam_monitor/students/encodings
mkdir -p exam_monitor/attendance_photos
mkdir -p exam_monitor/uploads
mkdir -p exam_monitor/exports
mkdir -p exam_monitor/robot_logs

# Set proper permissions for directories
chmod 755 exam_monitor/students
chmod 755 exam_monitor/students/photos
chmod 755 exam_monitor/students/encodings
chmod 755 exam_monitor/attendance_photos
chmod 755 exam_monitor/uploads
chmod 755 exam_monitor/robot_logs

# Debug: Show current directory and files
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Define list of required Python module files (enhanced with robot support)
MODULE_FILES=(
    "exam_monitor.py"
    "config_manager.py"
    "camera_manager.py"
    "detection_engine.py"
    "database_manager.py"
    "exam_utils.py"
    "web_server.py"
    "student_manager.py"
    "attendance_manager.py"
    "robot_controller.py"
)

# Define list of template files
TEMPLATE_FILES=(
    "base.html"
    "index.html"
    "attendance.html"
    "students.html"
    "reports.html"
    "robot.html"
)

# Define list of configuration files
CONFIG_FILES=(
    "config.json"
    "robot_config.json"
)

# Copy Python module files
echo "Copying enhanced application modules with robot support..."
MISSING_FILES=()

for file in "${MODULE_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" exam_monitor/
        echo "✓ Copied $file"
    else
        echo "✗ ERROR: $file not found in current directory!"
        MISSING_FILES+=("$file")
    fi
done

# Copy template files to templates directory
echo "Copying HTML template files..."
for file in "${TEMPLATE_FILES[@]}"; do
    # Check if templates are in a templates/ subdirectory first
    if [ -f "templates/$file" ]; then
        cp "templates/$file" "exam_monitor/templates/$file"
        echo "✓ Copied templates/$file to templates/$file"
    # Fallback: check for _template suffix in root directory
    elif [ -f "${file/.html/_template.html}" ]; then
        cp "${file/.html/_template.html}" "exam_monitor/templates/$file"
        echo "✓ Copied ${file/.html/_template.html} to templates/$file"
    else
        echo "✗ ERROR: Template file $file not found!"
        echo "   Looked for: templates/$file OR ${file/.html/_template.html}"
        MISSING_FILES+=("$file")
    fi
done

# Copy configuration files
echo "Copying configuration files..."
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        cp "$file" exam_monitor/
        echo "✓ Copied $file"
    else
        echo "✗ ERROR: $file not found in current directory!"
        MISSING_FILES+=("$file")
    fi
done

# Create default robot configuration if not present
if [ ! -f "exam_monitor/robot_config.json" ]; then
    echo "Creating default robot configuration..."
    cat > exam_monitor/robot_config.json << 'EOF'
{
    "serial_port": "/dev/ttyAMA0",
    "baudrate": 9600,
    "movement_speed": 80,
    "turn_speed": 60,
    "detection_duration": 30,
    "student_positions": [
        {
            "name": "Student Position 1 - Front Row Left",
            "description": "First student desk in front row, left side",
            "forward_time": 2.0,
            "turn_angle": 0,
            "turn_time": 0.0,
            "notes": "Straight movement to first position"
        },
        {
            "name": "Student Position 2 - Front Row Center", 
            "description": "Second student desk in front row, center",
            "forward_time": 1.5,
            "turn_angle": 1,
            "turn_time": 1.0,
            "notes": "Move forward then turn left to face center desk"
        },
        {
            "name": "Student Position 3 - Front Row Right",
            "description": "Third student desk in front row, right side", 
            "forward_time": 1.5,
            "turn_angle": 2,
            "turn_time": 1.2,
            "notes": "Move forward then turn right to face right desk"
        }
    ],
    "return_to_start": true,
    "pause_between_moves": 2.0,
    "head_scan_enabled": true,
    "head_scan_angles": [-45, -20, 0, 20, 45],
    "head_scan_interval": 8.0,
    "head_tilt_angle": -10,
    "safety_settings": {
        "max_movement_time": 10.0,
        "movement_timeout": 15.0,
        "emergency_stop_on_high_violations": true,
        "max_violations_before_stop": 10,
        "require_confirmation_for_movement": false
    },
    "detection_settings": {
        "enable_monitoring_during_movement": false,
        "enable_attendance_tracking": true,
        "save_violation_screenshots": true,
        "alert_on_violations": true,
        "violation_confidence_threshold": 0.7
    },
    "advanced_movement": {
        "use_acceleration_control": true,
        "smooth_turns": true,
        "position_verification": false,
        "return_path_optimization": true
    },
    "logging": {
        "log_all_movements": true,
        "log_detection_events": true,
        "save_movement_summary": true,
        "detailed_timing_logs": false
    },
    "customization": {
        "classroom_layout": "3x3_grid",
        "desk_spacing_meters": 1.5,
        "robot_height_adjustment": 0,
        "camera_field_of_view": 60
    }
}
EOF
    echo "✓ Created default robot_config.json"
fi

# Check if any files are missing
if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo ""
    echo "❌ INSTALLATION FAILED - Missing required files:"
    for file in "${MISSING_FILES[@]}"; do
        echo "   - $file"
    done
    echo ""
    echo "Please ensure all required files are in the current directory:"
    echo "$(pwd)"
    echo ""
    echo "Required files for enhanced system with robot support:"
    echo "Python Modules:"
    for file in "${MODULE_FILES[@]}"; do
        echo "   - $file"
    done
    echo "Template Files (in templates/ folder):"
    for file in "${TEMPLATE_FILES[@]}"; do
        echo "   - templates/$file"
    done
    echo "Configuration Files:"
    for file in "${CONFIG_FILES[@]}"; do
        echo "   - $file"
    done
    exit 1
fi

# Set permissions
chmod +x exam_monitor/exam_monitor.py

# Verify files were copied
echo "Verifying enhanced installation with robot support..."
VERIFICATION_FAILED=false

# Check Python modules
for file in "${MODULE_FILES[@]}"; do
    if [ -f "exam_monitor/$file" ]; then
        echo "✓ Verified: $file"
    else
        echo "✗ Missing: $file"
        VERIFICATION_FAILED=true
    fi
done

# Check configuration files
for file in "${CONFIG_FILES[@]}"; do
    if [ -f "exam_monitor/$file" ]; then
        echo "✓ Verified: $file"
    else
        echo "✗ Missing: $file"
        VERIFICATION_FAILED=true
    fi
done

# Check template files
for file in "${TEMPLATE_FILES[@]}"; do
    if [ -f "exam_monitor/templates/${file}" ]; then
        echo "✓ Verified template: ${file}"
    else
        echo "✗ Missing template: ${file}"
        VERIFICATION_FAILED=true
    fi
done

if [ "$VERIFICATION_FAILED" = true ]; then
    echo "✗ Error: Files not copied properly"
    exit 1
fi

echo "✓ All enhanced files and templates copied and verified successfully"

# Create enhanced service file for auto-start
echo "Creating enhanced systemd service with robot support..."
CURRENT_DIR=$(pwd)
sudo tee /etc/systemd/system/exam-monitor.service > /dev/null <<EOF
[Unit]
Description=Enhanced Exam Monitoring System with Robot Invigilation Support
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=${CURRENT_DIR}/exam_monitor
Environment=PATH=${CURRENT_DIR}/exam_monitor_env/bin
ExecStart=${CURRENT_DIR}/exam_monitor_env/bin/python exam_monitor.py --web
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Enable the service (but don't start it yet)
sudo systemctl daemon-reload
sudo systemctl enable exam-monitor.service

# Create enhanced start/stop scripts with robot support
echo "Creating enhanced control scripts with robot support..."
CURRENT_DIR=$(pwd)

# Regular monitoring script
cat > exam_monitor/start_monitor.sh << EOF
#!/bin/bash
cd ${CURRENT_DIR}/exam_monitor
source ${CURRENT_DIR}/exam_monitor_env/bin/activate
echo "Starting Enhanced Exam Monitor with Robot Support (Regular Mode)..."
echo "Press 'q' in the camera window to quit"
echo "Press 'a' to toggle attendance mode"
echo "Press 's' to take screenshot"
echo "Press 'r' to emergency stop robot"
echo "Press Ctrl+C in terminal to force quit"
python exam_monitor.py
EOF

# Attendance mode script
cat > exam_monitor/start_attendance.sh << EOF
#!/bin/bash
cd ${CURRENT_DIR}/exam_monitor
source ${CURRENT_DIR}/exam_monitor_env/bin/activate
echo "Starting Attendance Tracking Mode with Robot Support..."
echo "Press 'q' in the camera window to quit"
echo "Press 'a' to toggle to monitoring mode"
echo "Press 's' to take screenshot"
echo "Press 'r' to emergency stop robot"
echo "Press Ctrl+C in terminal to force quit"
python exam_monitor.py --attendance
EOF

# Robot invigilation script
cat > exam_monitor/start_robot_invigilation.sh << EOF
#!/bin/bash
cd ${CURRENT_DIR}/exam_monitor
source ${CURRENT_DIR}/exam_monitor_env/bin/activate
echo "Starting Robot Invigilator Mode..."
echo "🤖 Robot will autonomously patrol and monitor exam"
echo "🎓 Combined with AI detection and attendance tracking"
echo "Press 'q' in the camera window to quit"
echo "Press 'r' to emergency stop robot"
echo "Press Ctrl+C in terminal to force quit"
python exam_monitor.py --robot
EOF

# Web monitoring script with robot support
cat > exam_monitor/start_monitor_web.sh << EOF
#!/bin/bash
cd ${CURRENT_DIR}/exam_monitor
source ${CURRENT_DIR}/exam_monitor_env/bin/activate
echo "Starting Enhanced Exam Monitor Web Server with Robot Control..."
echo ""
echo "🌐 Access the web interface at:"
echo "   📱 Local access: http://localhost:5000"
echo "   🌍 Network access: http://\$(hostname -I | awk '{print \$1}'):5000"
echo ""
echo "Enhanced features available in web interface:"
echo "   📹 Live camera feed with real-time detection"
echo "   👥 Student registration and management"
echo "   📋 Attendance tracking and reporting"
echo "   🤖 Robot invigilation control and monitoring"
echo "   📍 Movement sequence configuration"
echo "   📊 System performance monitoring"
echo "   🚨 Violation alerts and history"
echo "   ⚙️ Remote control (start/stop monitoring)"
echo "   🛑 Emergency stop functionality"
echo "   📱 Mobile-friendly responsive design"
echo "   📈 Analytics and reporting dashboard"
echo ""
echo "🤖 Robot Control Features:"
echo "   🔌 Connect/disconnect robot remotely"
echo "   🚀 Start/stop autonomous invigilation sequences"
echo "   📍 Configure student position waypoints"
echo "   🎮 Manual robot control for testing"
echo "   📊 Real-time invigilation progress monitoring"
echo "   📝 Movement logs and invigilation history"
echo "   ⚙️ Robot configuration management"
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"
python exam_monitor.py --web --host 0.0.0.0 --port 5000
EOF

# Stop monitoring script
cat > exam_monitor/stop_monitor.sh << 'EOF'
#!/bin/bash
echo "Stopping Enhanced Exam Monitor with Robot Support..."
sudo systemctl stop exam-monitor.service
pkill -f exam_monitor.py
echo "Enhanced Exam Monitor stopped"
EOF

# Robot test script
cat > exam_monitor/test_robot.py << 'EOF'
#!/usr/bin/env python3
"""
Robot Test Script
Test robot connection and basic movements
"""
import sys
from pathlib import Path

# Add current directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from robot_controller import RobotInvigilator
    from config_manager import ConfigManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def main():
    try:
        print("=== Robot Connection Test ===\n")
        
        # Initialize robot controller
        print("Initializing robot controller...")
        config_manager = ConfigManager()
        robot = RobotInvigilator(None, 'robot_config.json')  # No exam monitor for test
        
        # Test connection
        print("Testing robot connection...")
        success, message = robot.connect_robot()
        
        if success:
            print(f"✅ {message}")
            
            # Test basic movements
            print("\nTesting basic movements...")
            test_success, test_message = robot.test_robot_connection()
            
            if test_success:
                print(f"✅ {test_message}")
            else:
                print(f"❌ {test_message}")
            
            # Disconnect
            robot.disconnect_robot()
            print("✅ Robot disconnected")
            
        else:
            print(f"❌ {message}")
            print("\nTroubleshooting tips:")
            print("1. Check robot is powered on")
            print("2. Verify USB/serial cable connection")
            print("3. Check robot_config.json serial port setting")
            print("4. Ensure user is in dialout group: sudo usermod -a -G dialout $USER")
            print("5. Reboot after adding user to group")
        
        # Show robot status
        status = robot.get_status()
        print(f"\nRobot Status:")
        print(f"  Connected: {status['robot_connected']}")
        print(f"  BonicBot Available: {status['bonicbot_available']}")
        print(f"  Config: {status['config']['serial_port']} @ {status['config']['baudrate']} baud")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
EOF

# Set permissions for all scripts
chmod +x exam_monitor/start_monitor.sh
chmod +x exam_monitor/start_attendance.sh
chmod +x exam_monitor/start_robot_invigilation.sh
chmod +x exam_monitor/start_monitor_web.sh
chmod +x exam_monitor/stop_monitor.sh
chmod +x exam_monitor/test_robot.py

# Create enhanced desktop shortcuts
CURRENT_DIR=$(pwd)

# Regular monitoring shortcut
cat > ~/Desktop/ExamMonitor.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Exam Monitor
Comment=Start Exam Monitoring System
Exec=${CURRENT_DIR}/exam_monitor/start_monitor.sh
Icon=camera
Terminal=true
Categories=Education;
EOF

# Attendance mode shortcut
cat > ~/Desktop/ExamAttendance.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Exam Attendance
Comment=Start Attendance Tracking System
Exec=${CURRENT_DIR}/exam_monitor/start_attendance.sh
Icon=user-check
Terminal=true
Categories=Education;
EOF

# Robot invigilation shortcut
cat > ~/Desktop/RobotInvigilator.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Robot Invigilator
Comment=Start Autonomous Robot Exam Monitoring
Exec=${CURRENT_DIR}/exam_monitor/start_robot_invigilation.sh
Icon=robot
Terminal=true
Categories=Education;
EOF

# Web interface shortcut
cat > ~/Desktop/ExamMonitorWeb.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Exam Monitor (Web + Robot)
Comment=Start Exam Monitor Web Server with Robot Control
Exec=${CURRENT_DIR}/exam_monitor/start_monitor_web.sh
Icon=applications-internet
Terminal=true
Categories=Education;Network;
EOF

# Robot test shortcut
cat > ~/Desktop/TestRobot.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Test Robot
Comment=Test Robot Connection and Movement
Exec=${CURRENT_DIR}/exam_monitor/test_robot.py
Icon=cog
Terminal=true
Categories=Education;Development;
EOF

chmod +x ~/Desktop/ExamMonitor.desktop
chmod +x ~/Desktop/ExamAttendance.desktop
chmod +x ~/Desktop/RobotInvigilator.desktop
chmod +x ~/Desktop/ExamMonitorWeb.desktop
chmod +x ~/Desktop/TestRobot.desktop

# Test enhanced Python imports including robot modules
echo "Testing enhanced Python module imports with robot support..."
cd exam_monitor
source ../exam_monitor_env/bin/activate

python3 << 'EOF'
try:
    print("Testing core modules...")
    from config_manager import ConfigManager
    print("✓ config_manager")
    from camera_manager import CameraManager
    print("✓ camera_manager")
    from detection_engine import DetectionEngine
    print("✓ detection_engine")
    from database_manager import DatabaseManager
    print("✓ database_manager")
    from exam_utils import SystemMonitor
    print("✓ exam_utils")
    from web_server import WebServer
    print("✓ web_server")
    
    print("Testing attendance modules...")
    from student_manager import StudentManager
    print("✓ student_manager")
    from attendance_manager import AttendanceManager
    print("✓ attendance_manager")
    
    print("Testing robot modules...")
    from robot_controller import RobotInvigilator
    print("✓ robot_controller")
    
    print("Testing face recognition...")
    import face_recognition
    print("✓ face_recognition library")
    
    print("Testing robot communication...")
    import serial
    print("✓ pyserial library")
    
    try:
        import bonicbot
        print("✓ bonicbot library (or placeholder)")
    except ImportError:
        print("⚠ bonicbot library not available (using placeholder)")
    
    print("✅ All enhanced module imports successful!")
except Exception as e:
    print(f"❌ Import error: {e}")
    exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "❌ Enhanced module import test failed!"
    exit 1
fi

cd ..

echo ""
echo "🎉 === Enhanced Installation with Robot Support Complete! ==="
echo ""
echo "📁 Enhanced Setup Summary:"
echo "   • System installed in: ${CURRENT_DIR}/exam_monitor/"
echo "   • Python environment: ${CURRENT_DIR}/exam_monitor_env/"
echo "   • Configuration file: ${CURRENT_DIR}/exam_monitor/config.json"
echo "   • Robot configuration: ${CURRENT_DIR}/exam_monitor/robot_config.json"
echo "   • HTML templates: ${CURRENT_DIR}/exam_monitor/templates/"
echo "   • Student data: ${CURRENT_DIR}/exam_monitor/students/"
echo "   • Attendance photos: ${CURRENT_DIR}/exam_monitor/attendance_photos/"
echo "   • Robot logs: ${CURRENT_DIR}/exam_monitor/robot_logs/"
echo "   • Screenshots: ${CURRENT_DIR}/exam_monitor/screenshots/"
echo "   • Database: ${CURRENT_DIR}/exam_monitor/exam_violations.db"
echo "   • System logs: ${CURRENT_DIR}/exam_monitor/exam_monitor.log"
echo ""
echo "🤖 Robot Hardware Setup:"
echo "   • Connect robot to Raspberry Pi via USB or GPIO UART"
echo "   • Default serial port: /dev/ttyAMA0 (configurable)"
echo "   • Ensure robot is powered and responsive"
echo "   • Test connection: ${CURRENT_DIR}/exam_monitor/test_robot.py"
echo ""
echo "🌐 Web Interface Templates:"
echo "   • Base template: templates/base.html"
echo "   • Main monitoring: templates/index.html"
echo "   • Attendance management: templates/attendance.html"
echo "   • Student management: templates/students.html"
echo "   • Robot control: templates/robot.html"
echo "   • Reports & analytics: templates/reports.html"
echo ""
echo "🚀 Enhanced Usage Options:"
echo "   1. 🖥️  Regular monitoring: ${CURRENT_DIR}/exam_monitor/start_monitor.sh"
echo "   2. 📋 Attendance tracking: ${CURRENT_DIR}/exam_monitor/start_attendance.sh"
echo "   3. 🤖 Robot invigilation: ${CURRENT_DIR}/exam_monitor/start_robot_invigilation.sh"
echo "   4. 🌐 Web interface: ${CURRENT_DIR}/exam_monitor/start_monitor_web.sh"
echo "   5. 🔧 Test robot: ${CURRENT_DIR}/exam_monitor/test_robot.py"
echo "   6. 📊 View violations: ${CURRENT_DIR}/exam_monitor/view_violations.py"
echo "   7. 📈 Attendance report: ${CURRENT_DIR}/exam_monitor/attendance_report.py"
echo "   8. 🔧 Auto-start service: sudo systemctl start exam-monitor.service"
echo "   9. 🖱️  Desktop shortcuts available on desktop"
echo ""
echo "🌐 Enhanced Web Interface Access:"
echo "   • Local access: http://localhost:5000"
echo "   • Network access: http://\$(hostname -I | awk '{print \$1}'):5000"
echo "   • Robot control page: http://YOUR_PI_IP:5000/robot"
echo "   • 📱 Mobile-friendly responsive design"
echo "   • 👥 Student registration and management"
echo "   • 📋 Real-time attendance tracking"
echo "   • 🤖 Complete robot invigilation control"
echo "   • 📊 Analytics and reporting dashboard"
echo ""
echo "🤖 Robot Invigilation Features:"
echo "   • Autonomous movement to predefined student positions"
echo "   • Configurable detection duration per position"
echo "   • Real-time violation detection during patrol"
echo "   • Automatic attendance tracking integration"
echo "   • Emergency stop functionality (web and hardware)"
echo "   • Movement sequence configuration via web interface"
echo "   • Manual robot control for testing and positioning"
echo "   • Comprehensive logging of all robot activities"
echo ""
echo "👥 Student Management Features:"
echo "   • Face recognition-based attendance"
echo "   • Student registration with photo upload"
echo "   • Automatic attendance marking during robot patrol"
echo "   • Manual attendance override"
echo "   • Attendance reports and analytics"
echo "   • Export functionality for reports"
echo ""
echo "⚙️ Configuration:"
echo "   • Edit: ${CURRENT_DIR}/exam_monitor/config.json"
echo "   • Robot settings: ${CURRENT_DIR}/exam_monitor/robot_config.json"
echo "   • Enhanced settings for attendance, face recognition, robot control"
echo "   • Customize thresholds, alerts, and behavior"
echo "   • Email notifications for attendance summaries"
echo "   • Robot movement sequences and timing"
echo ""
echo "🎮 Enhanced Controls:"
echo "   • Regular mode: Press 'q' to quit, 'a' to toggle attendance mode, 's' for screenshot, 'r' for robot emergency stop"
echo "   • Robot mode: Autonomous patrol with AI detection and attendance tracking"
echo "   • Web mode: Full remote control via web interface including robot management"
echo "   • Emergency stop: ${CURRENT_DIR}/exam_monitor/stop_monitor.sh"
echo ""
echo "📋 Enhanced Architecture:"
echo "   • ✅ Modular design with attendance and robot support"
echo "   • ✅ Face recognition integration"
echo "   • ✅ Student database management"
echo "   • ✅ Real-time attendance tracking"
echo "   • ✅ Autonomous robot invigilation"
echo "   • ✅ Robot movement sequence configuration"
echo "   • ✅ Enhanced web interface with robot control"
echo "   • ✅ Professional-grade reporting system"
echo "   • ✅ Complete HTML template system"
echo "   • ✅ Serial communication for robot control"
echo "   • ✅ Emergency stop and safety systems"
echo "   • ✅ Real-time robot status monitoring"
echo ""
echo "🔧 Robot Setup & Testing:"
echo "   1. 🔌 Connect robot to Raspberry Pi (USB or UART)"
echo "   2. ⚡ Ensure robot is powered on"
echo "   3. 🧪 Test connection: python test_robot.py"
echo "   4. ⚙️ Configure positions via web interface"
echo "   5. 🚀 Start autonomous invigilation"
echo ""
echo "🔄 Next Steps:"
echo "   1. 🔄 Reboot recommended: sudo reboot"
echo "   2. 📸 Test camera: libcamera-still -o test.jpg"
echo "   3. 🤖 Test robot: cd exam_monitor && python test_robot.py"
echo "   4. 👥 Register students via web interface"
echo "   5. 📍 Configure robot movement positions"
echo "   6. 📋 Start attendance tracking session"
echo "   7. 🤖 Test robot invigilation sequence"
echo "   8. 🌐 Access web interface from any device on network"
echo ""
echo "🛡️ Safety Reminders:"
echo "   • Always test robot movements manually before autonomous operation"
echo "   • Keep emergency stop accessible during robot operation"
echo "   • Ensure clear paths for robot movement"
echo "   • Monitor robot operation remotely via web interface"
echo "   • Robot will stop automatically if violations exceed threshold"
echo ""
echo "📚 For help and documentation, check the README.md file"
echo "🎓 Enjoy your enhanced exam monitoring system with autonomous robot invigilation!"