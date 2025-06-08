#!/usr/bin/env python3
"""
Simple Invigilation Sequence for Robot Invigilator
A basic movement pattern that students can easily modify
"""

import time
import logging
from bonicbot import create_serial_controller

logger = logging.getLogger(__name__)


def move_to_next_student(robot_controller, delay_func):
    """
    Move to the next student position and perform a head scan.
    
    Args:
        robot_controller: BonicBot controller instance
        delay_func: Function to handle delays with stop checking
    """
    logger.info("Moving to next student position")
    
    # Move forward for 3 seconds
    robot_controller.move_forward(speed=30)
    if not delay_func(10.0):
        return False
    
    # Stop movement
    robot_controller.stop()
    if not delay_func(3.0):
        return False
    
    # Perform head scan
    robot_controller.control_head(pan_angle=90, pan_speed=800)
    if not delay_func(8.0):
        return False
    
    
    robot_controller.control_head(pan_angle=-90, pan_speed=800)
    if not delay_func(10.0):
        return False
    
    robot_controller.control_head(pan_angle=0, pan_speed=800)
    if not delay_func(2.0):
        return False
    
    return True
    

def RunSequence(robot_controller, delay_func):
    """
    Simple invigilation sequence for the robot invigilator
    Students can modify this function to create their own patrol patterns
    
    Args:
        robot_controller: BonicBot controller instance
        delay_func: Function to handle delays with stop checking
    """
    
    logger.info("Starting simple robot invigilation sequence")
    
    try:
        # Initialize robot position
        robot_controller.stop()
        delay_func(3.0)
        
        # Reset head to center position
        robot_controller.control_head(pan_angle=0, tilt_angle=0, pan_speed=800)
        delay_func(3.0)
        
        # Main invigilation loop
        sequence_count = 0
        
        while True:
            sequence_count += 1
            logger.info(f"Starting patrol sequence #{sequence_count}")
            # === STUDENTS CAN MODIFY THE MOVEMENTS BELOW ===
            
            #first row
            move_to_next_student(robot_controller, delay_func)
            
            #second row
            move_to_next_student(robot_controller, delay_func)
            
            robot_controller.move_forward(speed=30)
            if not delay_func(10.0):
                break
            
            robot_controller.turn_left(speed=30)                       # Turn left
            if not delay_func(3.5):
                break
            
            #second row
            move_to_next_student(robot_controller, delay_func)
            
            #first row
            move_to_next_student(robot_controller, delay_func)
            
            
            robot_controller.move_forward(speed=30)
            if not delay_func(10.0):
                break
            
            robot_controller.turn_right(speed=30)                       # Turn right
            if not delay_func(3.5):
                break
            
            robot_controller.stop()  # Stop moving
            if not delay_func(4):
                break
            
            # === END OF STUDENT MODIFIABLE SECTION ===
            
            # Pause between patrol cycles
            logger.info("Patrol cycle completed, pausing...")
            if not delay_func(5.0):
                break
        
        logger.info("Invigilation sequence completed or stopped")
        
    except Exception as e:
        logger.error(f"Error in invigilation sequence: {e}")
        robot_controller.stop()
    finally:
        # Ensure robot is stopped and head is centered
        robot_controller.stop()
        robot_controller.control_head(pan_angle=0, tilt_angle=0)

# Students: Modify the movements in the RunSequence function above!
# 
# Ideas for modifications:
# 1. Change the head angles (try -90 to 90 for pan, -38 to 45 for tilt)
# 2. Adjust movement speeds (40-60 for base movement, 100-500 for head)
# 3. Change timing by modifying delay_func() values
# 4. Add backward movement: robot_controller.move_backward(speed=40)
# 5. Try different turn directions: turn_right() instead of turn_left()
# 6. Add more head movements with different angles
# 7. Create a square or triangle movement pattern
# 8. Add arm movements using control_left_hand() or control_right_hand()
#
# Remember: Always use delay_func() instead of time.sleep() for proper stopping!

def delay(seconds):
    time.sleep(seconds)
    return True

def main():
    serial_port = "/dev/ttyAMA0"
    baudrate = 9600
    robot_controller = create_serial_controller(serial_port, baudrate)
    RunSequence(robot_controller, delay)
    robot_controller.close()

if __name__ == '__main__':
    main()
