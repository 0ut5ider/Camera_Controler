#!/bin/bash

# Record script start time
START_TIME=$(date +%s.%N)
echo "Script started at $START_TIME"

# Get a base timestamp for filenames if needed
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Replace with your actual camera ports and desired filenames
# Use --capture-image-and-download or just --capture-image

# Record camera 1 launch time
CAM1_LAUNCH_TIME=$(date +%s.%N)
echo "Launching camera 1 at $CAM1_LAUNCH_TIME..."
gphoto2 --port "usb:003,057" --capture-image-and-download --filename "cam1-${TIMESTAMP}.%C" &
PID1=$!

# Record camera 2 launch time
CAM2_LAUNCH_TIME=$(date +%s.%N)
echo "Launching camera 2 at $CAM2_LAUNCH_TIME..."
gphoto2 --port "usb:003,056" --capture-image-and-download --filename "cam2-${TIMESTAMP}.%C" &
PID2=$!


echo "Capture commands sent to all cameras."
echo "Waiting for processes to complete..."

# Wait for camera 1 background job to finish
wait $PID1
CAM1_WAIT_FINISH_TIME=$(date +%s.%N)
echo "Camera 1 process (PID $PID1) finished waiting at $CAM1_WAIT_FINISH_TIME"

# Wait for camera 2 background job to finish
wait $PID2
CAM2_WAIT_FINISH_TIME=$(date +%s.%N)
echo "Camera 2 process (PID $PID2) finished waiting at $CAM2_WAIT_FINISH_TIME"

echo "All cameras finished."

# Record script end time
END_TIME=$(date +%s.%N)
echo "Script finished at $END_TIME"

# Calculate and print durations
LAUNCH_DIFF=$(echo "$CAM2_LAUNCH_TIME - $CAM1_LAUNCH_TIME" | bc)
CAM1_PROCESS_DURATION=$(echo "$CAM1_WAIT_FINISH_TIME - $CAM1_LAUNCH_TIME" | bc)
CAM2_PROCESS_DURATION=$(echo "$CAM2_WAIT_FINISH_TIME - $CAM2_LAUNCH_TIME" | bc)
TOTAL_DURATION=$(echo "$END_TIME - $START_TIME" | bc)

echo "--- Timing Results ---"
echo "Time between camera launch commands: ${LAUNCH_DIFF} seconds"
echo "Camera 1 process duration: ${CAM1_PROCESS_DURATION} seconds"
echo "Camera 2 process duration: ${CAM2_PROCESS_DURATION} seconds"
echo "Total script execution time: ${TOTAL_DURATION} seconds"
