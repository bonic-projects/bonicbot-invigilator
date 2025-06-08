#!/bin/bash
# Enhanced install.sh - Installation script for Exam Monitoring System with Attendance Support and Robot Invigilator

echo "=== Exam Monitoring System Setup (Enhanced with Robot Invigilator) ==="
echo "This script will install all required dependencies including face recognition and robot control"

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

# NEW: Install robot control dependencies
echo "Installing robot control dependencies..."
sudo apt install -y python3-serial  # For serial communication with robot
sudo apt install -y minicom screen  # For debugging serial connections
sudo raspi-config nonint do_serial 0  # Enable serial/UART

# Add user to video and dialout groups for camera and serial access
sudo usermod -a -G video $USER
sudo usermod -a -G dialout $USER  # NEW: For serial port access

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

# Install additional packages for attendance system
echo "Installing additional packages for attendance system..."
pip install psutil  # System monitoring
pip install python-dateutil  # Date handling
pip install python-magic  # File type detection

# NEW: Install robot control library
echo "Installing robot control library..."
pip install pyserial  # Core serial communication

# Install BonicBot library (if available)
echo "Installing BonicBot library..."
pip install bonicbot || {
    echo "BonicBot library not available via pip. Attempting to install from source..."
    
    # Check if bonicbot source is available locally
    if [ -d "bonicbot" ]; then
        echo "Found local BonicBot directory, installing..."
        cd bonicbot
        pip install .
        cd ..
        echo "BonicBot installed from local source"
    else
        echo "Warning: BonicBot library not found. Robot functionality will be limited."
        echo "To enable full robot functionality:"
        echo "1. Obtain the BonicBot library"
        echo "2. Place it in the bonicbot/ directory"
        echo "3. Run: pip install ./bonicbot/"
        echo ""
        echo "The system will still work without robot functionality."
    fi
}

# Install email packages with error handling
echo "Installing email packages..."
pip install --upgrade setuptools
pip install --upgrade email-validator || echo "Warning: email-validator install failed"

# Create project directory structure
echo "Creating enhanced project structure..."
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

# Set proper permissions for directories
chmod 755 exam_monitor/students
chmod 755 exam_monitor/students/photos
chmod 755 exam_monitor/students/encodings
chmod 755 exam_monitor/attendance_photos
chmod 755 exam_monitor/uploads

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
    "invigilation_sequence.py"
)

# Define list of template files (without _template suffix)
TEMPLATE_FILES=(
    "base.html"
    "index.html"
    "attendance.html"
    "students.html"
    "reports.html"
)

# Copy Python module files (check current directory first)
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

# Copy enhanced configuration file
if [ -f "config.json" ]; then
    cp config.json exam_monitor/
    echo "✓ Copied enhanced config.json"
else
    echo "✗ ERROR: config.json not found in current directory!"
    MISSING_FILES+=("config.json")
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
    echo "Configuration:"
    echo "   - config.json"
    exit 1
fi

# Set permissions
chmod +x exam_monitor/exam_monitor.py

# Verify files were copied
echo "Verifying enhanced installation with robot support..."
VERIFICATION_FAILED=false

# Check Python modules
for file in "${MODULE_FILES[@]}" "config.json"; do
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
Description=Enhanced Exam Monitoring System with Robot Invigilator Support
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=${CURRENT_DIR}/exam_monitor
Environment=PATH=${CURRENT_DIR}/exam_monitor_env/bin
ExecStart=${CURRENT_DIR}/exam_monitor_env/bin/python exam_monitor.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Enable the service (but don't start it yet)
sudo systemctl daemon-reload
sudo systemctl enable exam-monitor.service

# Create enhanced start/stop scripts
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
echo "Press Ctrl+C in terminal to force quit"
python exam_monitor.py --attendance
EOF

# Web monitoring script with robot support
cat > exam_monitor/start_monitor_web.sh << EOF
#!/bin/bash
cd ${CURRENT_DIR}/exam_monitor
source ${CURRENT_DIR}/exam_monitor_env/bin/activate
echo "Starting Enhanced Exam Monitor Web Server with Robot Invigilator..."
echo ""
echo "🌐 Access the web interface at:"
echo "   📱 Local access: http://localhost:5000"
echo "   🌍 Network access: http://\$(hostname -I | awk '{print \$1}'):5000"
echo ""
echo "Enhanced features available in web interface:"
echo "   📹 Live camera feed with real-time detection"
echo "   👥 Student registration and management"
echo "   📋 Attendance tracking and reporting"
echo "   🤖 Robot invigilator control and monitoring"
echo "   📊 System performance monitoring"
echo "   🚨 Violation alerts and history"
echo "   ⚙️ Remote control (start/stop monitoring)"
echo "   📱 Mobile-friendly responsive design"
echo "   📈 Analytics and reporting dashboard"
echo ""
echo "🤖 Robot Control Features:"
echo "   🔌 Connect/disconnect robot"
echo "   🎮 Start/stop invigilation sequences"
echo "   🧪 Test robot functionality"
echo "   🚨 Emergency stop capability"
echo "   📊 Real-time robot status monitoring"
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

# Enhanced violation viewer script
cat > exam_monitor/view_violations.py << 'EOF'
#!/usr/bin/env python3
"""
Enhanced Violation Viewer for Exam Monitoring System
"""
import sys
from pathlib import Path

# Add current directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from database_manager import DatabaseManager
    from config_manager import ConfigManager
    from student_manager import StudentManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all module files are in the same directory")
    sys.exit(1)

def main():
    try:
        print("=== Enhanced Exam Monitor Data Viewer ===\n")
        
        # Initialize managers
        db_manager = DatabaseManager()
        config_manager = ConfigManager()
        student_manager = StudentManager(db_manager)
        
        # Get recent violations
        print("📋 Recent Violations (Last 20):")
        violations = db_manager.get_violations(limit=20)
        
        if not violations:
            print("✅ No violations recorded.\n")
        else:
            for v in violations:
                print(f"🚨 {v['timestamp']}: {v['violation_type']}")
                print(f"   Description: {v['description']}")
                print(f"   Confidence: {v['confidence']:.2f}")
                if v['session_id']:
                    print(f"   Session: {v['session_id']}")
                print()
        
        # Get violation summary
        print("📊 Violation Summary:")
        summary = db_manager.get_violations_summary()
        
        if not summary:
            print("No violation data available.\n")
        else:
            for s in summary:
                print(f"   • {s['violation_type']}: {s['count']} times (avg confidence: {s['avg_confidence']:.2f})")
        
        # Get attendance summary
        print("\n👥 Student Summary:")
        students = student_manager.get_all_students()
        attendance_summary = student_manager.get_attendance_summary()
        
        print(f"   • Total Registered Students: {len(students)}")
        print(f"   • Unique Attendees: {attendance_summary.get('unique_attendees', 0)}")
        print(f"   • Total Attendance Records: {attendance_summary.get('total_attendance_records', 0)}")
        
        if attendance_summary.get('daily_summary'):
            print("\n📅 Recent Attendance:")
            for day in attendance_summary['daily_summary'][:5]:  # Last 5 days
                print(f"   • {day['exam_date']}: {day['present_students']} students ({day['attendance_percentage']}%)")
        
        # Get recent sessions
        print("\n📅 Recent Sessions:")
        sessions = db_manager.get_sessions(limit=5)
        
        if not sessions:
            print("No sessions recorded.\n")
        else:
            for s in sessions:
                print(f"   Session: {s['session_id']}")
                print(f"   Started: {s['start_time']}")
                if s['end_time']:
                    print(f"   Ended: {s['end_time']}")
                print(f"   Violations: {s['total_violations']}")
                print()
        
        # Get database statistics
        print("📈 Database Statistics:")
        stats = db_manager.get_statistics()
        student_stats = student_manager.get_statistics()
        
        all_stats = {**stats, **student_stats}
        
        for key, value in all_stats.items():
            print(f"   • {key.replace('_', ' ').title()}: {value}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
EOF

# Attendance report script
cat > exam_monitor/attendance_report.py << 'EOF'
#!/usr/bin/env python3
"""
Attendance Report Generator
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add current directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from database_manager import DatabaseManager
    from student_manager import StudentManager
    from attendance_manager import AttendanceManager
    from config_manager import ConfigManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def main():
    try:
        print("=== Attendance Report Generator ===\n")
        
        # Initialize managers
        db_manager = DatabaseManager()
        config_manager = ConfigManager()
        student_manager = StudentManager(db_manager)
        attendance_manager = AttendanceManager(student_manager, db_manager, config_manager)
        
        # Get today's attendance
        today = datetime.now().date().isoformat()
        attendance_data = student_manager.get_attendance_for_date(today)
        
        print(f"📋 Attendance Report for {today}")
        print("=" * 50)
        
        if not attendance_data:
            print("No attendance records for today.")
            return
        
        present_students = [att for att in attendance_data if att['status'] == 'present']
        
        print(f"Total Present: {len(present_students)}")
        print(f"Total Records: {len(attendance_data)}")
        print()
        
        print("Present Students:")
        print("-" * 40)
        for student in present_students:
            check_in = datetime.fromisoformat(student['check_in_time']).strftime('%H:%M:%S')
            confidence = f"({student['confidence']*100:.1f}%)" if student['confidence'] else "(Manual)"
            print(f"{student['student_id']}: {student['first_name']} {student['last_name']} - {check_in} {confidence}")
        
        # Export report
        export_path = f"attendance_report_{today}.json"
        success = attendance_manager.export_attendance_report(export_path, today)
        
        if success:
            print(f"\n📊 Detailed report exported to: {export_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
EOF

# NEW: Robot test script
cat > exam_monitor/test_robot.py << 'EOF'
#!/usr/bin/env python3
"""
Robot Test Script for BonicBot Integration
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
        print("=== Robot Test Script ===\n")
        
        # Create a mock exam monitor system for testing
        class MockExamMonitor:
            def __init__(self):
                pass
        
        mock_system = MockExamMonitor()
        robot = RobotInvigilator(mock_system)
        
        print("1. Testing robot connection...")
        success, message = robot.connect_robot()
        print(f"   Result: {'✅' if success else '❌'} {message}")
        
        if success:
            print("\n2. Testing robot movements...")
            success, message = robot.test_robot_connection()
            print(f"   Result: {'✅' if success else '❌'} {message}")
            
            print("\n3. Robot status:")
            status = robot.get_status()
            for key, value in status.items():
                print(f"   {key}: {value}")
            
            print("\n4. Disconnecting robot...")
            robot.disconnect_robot()
            print("   Result: ✅ Robot disconnected")
        
        print("\nRobot test completed.")
        
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
chmod +x exam_monitor/start_monitor_web.sh
chmod +x exam_monitor/stop_monitor.sh
chmod +x exam_monitor/view_violations.py
chmod +x exam_monitor/attendance_report.py
chmod +x exam_monitor/test_robot.py

# Create enhanced desktop shortcuts
CURRENT_DIR=$(pwd)

# Regular monitoring shortcut
cat > ~/Desktop/ExamMonitor.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Exam Monitor
Comment=Start Exam Monitoring System with Robot Support
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
Comment=Start Attendance Tracking System with Robot Support
Exec=${CURRENT_DIR}/exam_monitor/start_attendance.sh
Icon=user-check
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

# NEW: Robot test shortcut
cat > ~/Desktop/TestRobot.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Test Robot
Comment=Test Robot Connection and Functionality
Exec=${CURRENT_DIR}/exam_monitor/test_robot.py
Icon=system-run
Terminal=true
Categories=Education;
EOF

chmod +x ~/Desktop/ExamMonitor.desktop
chmod +x ~/Desktop/ExamAttendance.desktop
chmod +x ~/Desktop/ExamMonitorWeb.desktop
chmod +x ~/Desktop/TestRobot.desktop

# Test enhanced Python imports including robot support
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
    
    try:
        from invigilation_sequence import RunSequence
        print("✓ invigilation_sequence")
    except ImportError:
        print("⚠ invigilation_sequence not found (optional)")
    
    print("Testing face recognition...")
    import face_recognition
    print("✓ face_recognition library")
    
    print("Testing robot dependencies...")
    import serial
    print("✓ pyserial")
    
    try:
        from bonicbot import create_serial_controller
        print("✓ bonicbot library")
    except ImportError:
        print("⚠ bonicbot library not available (robot functionality limited)")
    
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
echo "🎉 === Enhanced Installation Complete with Robot Support! ==="
echo ""
echo "📁 Enhanced Setup Summary:"
echo "   • System installed in: ${CURRENT_DIR}/exam_monitor/"
echo "   • Python environment: ${CURRENT_DIR}/exam_monitor_env/"
echo "   • Configuration file: ${CURRENT_DIR}/exam_monitor/config.json"
echo "   • HTML templates: ${CURRENT_DIR}/exam_monitor/templates/"
echo "   • Student data: ${CURRENT_DIR}/exam_monitor/students/"
echo "   • Attendance photos: ${CURRENT_DIR}/exam_monitor/attendance_photos/"
echo "   • Screenshots: ${CURRENT_DIR}/exam_monitor/screenshots/"
echo "   • Database: ${CURRENT_DIR}/exam_monitor/exam_violations.db"
echo "   • Logs: ${CURRENT_DIR}/exam_monitor/exam_monitor.log"
echo ""
echo "🤖 Robot Integration:"
echo "   • Robot controller: robot_controller.py"
echo "   • Invigilation sequence: invigilation_sequence.py"
echo "   • Serial port: /dev/ttyAMA0 (enabled)"
echo "   • User added to dialout group for serial access"
echo "   • Robot test script: ${CURRENT_DIR}/exam_monitor/test_robot.py"
echo ""
echo "📂 Source Organization Tip:"
echo "   For better organization, keep template files in a templates/ folder:"
echo "   templates/base.html, templates/index.html, etc."
echo "   The install script supports both organized and flat structures."
echo ""
echo "🌐 Web Interface Templates with Robot Control:"
echo "   • Base template: templates/base.html"
echo "   • Main monitoring: templates/index.html (with robot panel)"
echo "   • Attendance management: templates/attendance.html"
echo "   • Student management: templates/students.html"
echo "   • Reports & analytics: templates/reports.html"
echo ""
echo "🚀 Enhanced Usage Options:"
echo "   1. 🖥️  Regular monitoring: ${CURRENT_DIR}/exam_monitor/start_monitor.sh"
echo "   2. 📋 Attendance tracking: ${CURRENT_DIR}/exam_monitor/start_attendance.sh"
echo "   3. 🌐 Web interface + Robot: ${CURRENT_DIR}/exam_monitor/start_monitor_web.sh"
echo "   4. 📊 View violations: ${CURRENT_DIR}/exam_monitor/view_violations.py"
echo "   5. 📈 Attendance report: ${CURRENT_DIR}/exam_monitor/attendance_report.py"
echo "   6. 🤖 Test robot: ${CURRENT_DIR}/exam_monitor/test_robot.py"
echo "   7. 🔧 Auto-start service: sudo systemctl start exam-monitor.service"
echo "   8. 🖱️  Desktop shortcuts available on desktop"
echo ""
echo "🌐 Enhanced Web Interface Access with Robot Control:"
echo "   • Local access: http://localhost:5000"
echo "   • Network access: http://\$(hostname -I | awk '{print \$1}'):5000"
echo "   • 📱 Mobile-friendly responsive design"
echo "   • 👥 Student registration and management"
echo "   • 📋 Real-time attendance tracking"
echo "   • 🤖 Robot invigilator control panel"
echo "   • 📊 System performance monitoring"
echo "   • 🚨 Violation alerts and history"
echo "   • ⚙️ Remote control (start/stop monitoring)"
echo "   • 📈 Analytics and reporting dashboard"
echo ""
echo "🤖 Robot Invigilator Features:"
echo "   • 🔌 Connect/disconnect robot via web interface"
echo "   • 🎮 Start/stop automated invigilation sequences"
echo "   • 🧪 Test robot movements and functionality"
echo "   • 🚨 Emergency stop capability"
echo "   • 📊 Real-time robot status monitoring"
echo "   • 📝 Robot activity logging"
echo "   • 🎯 Integration with violation detection system"
echo ""
echo "👥 Student Management Features:"
echo "   • Face recognition-based attendance"
echo "   • Student registration with photo upload"
echo "   • Automatic attendance marking"
echo "   • Manual attendance override"
echo "   • Attendance reports and analytics"
echo "   • Export functionality for reports"
echo ""
echo "⚙️ Configuration:"
echo "   • Edit: ${CURRENT_DIR}/exam_monitor/config.json"
echo "   • Enhanced settings for attendance, face recognition, and robot control"
echo "   • Customize thresholds, alerts, and behavior"
echo "   • Email notifications for attendance summaries"
echo "   • Robot communication settings"
echo ""
echo "🎮 Enhanced Controls:"
echo "   • Regular mode: Press 'q' to quit, 'a' to toggle attendance mode, 's' for screenshot"
echo "   • Attendance mode: Automatic face recognition and attendance marking"
echo "   • Web mode: Full remote control via web interface + robot control"
echo "   • Robot mode: Automated invigilation sequences"
echo "   • Emergency stop: ${CURRENT_DIR}/exam_monitor/stop_monitor.sh"
echo ""
echo "📋 Enhanced Architecture with Robot Support:"
echo "   • ✅ Modular design with attendance and robot support"
echo "   • ✅ Face recognition integration"
echo "   • ✅ Student database management"
echo "   • ✅ Real-time attendance tracking"
echo "   • ✅ Robot invigilator integration"
echo "   • ✅ Serial communication with BonicBot"
echo "   • ✅ Enhanced web interface with robot control"
echo "   • ✅ Professional-grade reporting system"
echo "   • ✅ Complete HTML template system"
echo "   • ✅ Organized project structure (templates/ folder)"
echo "   • ✅ Flexible installation (supports multiple file layouts)"
echo ""
echo "🔄 Next Steps:"
echo "   1. 🔄 Reboot recommended: sudo reboot"
echo "   2. 📸 Test camera: libcamera-still -o test.jpg"
echo "   3. 🤖 Test robot: ${CURRENT_DIR}/exam_monitor/test_robot.py"
echo "   4. 👥 Register students via web interface"
echo "   5. 📋 Start attendance tracking session"
echo "   6. 🤖 Configure robot invigilation sequence"
echo "   7. 🌐 Access web interface from any device on network"
echo ""
echo "🔧 Robot Setup Notes:"
echo "   • Connect robot to GPIO serial pins (TX/RX)"
echo "   • Ensure robot is powered and responsive"
echo "   • Test robot connection before starting invigilation"
echo "   • Configure invigilation_sequence.py for your specific robot behavior"
echo ""
echo "📚 For help and documentation, check the README.md file"
echo "🎓 Enjoy your enhanced exam monitoring system with robot invigilator support!"