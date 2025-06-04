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
