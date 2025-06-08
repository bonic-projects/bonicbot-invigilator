#!/usr/bin/env python3
"""
Simple Invigilation Sequence for Robot Invigilator
A basic movement pattern that students can easily modify
"""

import time
import logging

logger = logging.getLogger(__name__)

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
        delay_func(1.0)
        
        # Reset head to center position
        robot_controller.control_head(pan_angle=0, tilt_angle=0)
        delay_func(2.0)
        
        # Main invigilation loop
        sequence_count = 0
        
        while True:
            sequence_count += 1
            logger.info(f"Starting patrol sequence #{sequence_count}")
            
            # === STUDENTS CAN MODIFY THE MOVEMENTS BELOW ===
            
            # Step 1: Look left and right from starting position
            logger.info("Step 1: Initial scanning")
            robot_controller.control_head(pan_angle=-45, tilt_angle=0)  # Look left
            if not delay_func(2.0):
                break
            
            robot_controller.control_head(pan_angle=45, tilt_angle=0)   # Look right  
            if not delay_func(2.0):
                break
                
            robot_controller.control_head(pan_angle=0, tilt_angle=0)    # Look center
            if not delay_func(1.0):
                break
            
            # Step 2: Move forward while looking around
            logger.info("Step 2: Forward patrol")
            robot_controller.move_forward(speed=40)                     # Move slowly forward
            if not delay_func(3.0):
                break
            
            robot_controller.stop()                                     # Stop moving
            if not delay_func(1.0):
                break
            
            # Look around while stopped
            robot_controller.control_head(pan_angle=-60, tilt_angle=0)  # Look far left
            if not delay_func(2.0):
                break
                
            robot_controller.control_head(pan_angle=60, tilt_angle=0)   # Look far right
            if not delay_func(2.0):
                break
                
            robot_controller.control_head(pan_angle=0, tilt_angle=0)    # Return to center
            if not delay_func(1.0):
                break
            
            # Step 3: Turn to scan different area
            logger.info("Step 3: Turn and scan")
            robot_controller.turn_left(speed=50)                        # Turn left
            if not delay_func(1.5):
                break
            
            robot_controller.stop()                                     # Stop turning
            if not delay_func(0.5):
                break
            
            # Scan the new area
            robot_controller.control_head(pan_angle=-30, tilt_angle=0)
            if not delay_func(1.5):
                break
                
            robot_controller.control_head(pan_angle=30, tilt_angle=0)
            if not delay_func(1.5):
                break
                
            robot_controller.control_head(pan_angle=0, tilt_angle=0)
            if not delay_func(1.0):
                break
            
            # Step 4: Move to new position
            logger.info("Step 4: Move to new position")
            robot_controller.move_forward(speed=45)                     # Move forward again
            if not delay_func(2.5):
                break
            
            robot_controller.stop()                                     # Stop
            if not delay_func(1.0):
                break
            
            # Step 5: Final comprehensive scan
            logger.info("Step 5: 360-degree scan")
            robot_controller.turn_right(speed=50)                       # Slow 360-degree turn
            if not delay_func(3.0):
                break
            
            robot_controller.stop()                                     # Stop turning
            if not delay_func(1.0):
                break
            
            # Return head to center
            robot_controller.control_head(pan_angle=0, tilt_angle=0)
            if not delay_func(1.0):
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
