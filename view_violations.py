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
