# Codebase Documentation: Multi-Camera Trigger Script

## Overview

This Python script (`src/multi_camera_trigger.py`) is designed to control and trigger multiple cameras connected to the system via USB. It utilizes the `gphoto2` library for camera communication and `threading` for concurrent camera operations.

The primary goal of the script is to achieve simultaneous triggering of all detected and initialized cameras. It also provides an option to download the captured images immediately after capture or to leave them on the camera's storage for later retrieval.

## Key Features

- **Camera Detection:** Automatically detects cameras supported by `gphoto2`.
- **Camera Initialization:** Initializes each detected camera for control.
- **Time Synchronization (Optional):** Attempts to set the internal clock of each camera to the current system time. This feature might not be supported by all camera models.
- **Simultaneous Triggering:** Uses Python's `threading` module to send trigger commands to all initialized cameras as concurrently as possible.
- **Image Download (Optional):** Can be configured to download captured images to a specified local directory. If disabled, images remain on the camera's memory card, which can lead to faster trigger responses.
- **Error Handling:** Includes basic error handling for `gphoto2` operations.

## Configuration

The script has a few configuration constants at the top of the file:

- `DOWNLOAD_AFTER_CAPTURE` (boolean):
    - If `True`, the script will attempt to download the image from each camera immediately after it's captured.
    - If `False` (default), images are captured and left on the camera's memory card. This is generally recommended for achieving the best trigger simultaneity.
- `DOWNLOAD_PATH_PREFIX` (string):
    - Specifies the base directory for saving downloaded images. The camera's serial number will be appended to this path to create separate folders for each camera.
    - Example: If set to `"captures"`, images will be saved in folders like `captures/[serial_number]/`, with filenames including a timestamp and the original camera filename.

## Core Functions

### `list_connected_cameras(context)`
- Detects all cameras connected to the system that `gphoto2` can recognize.
- Returns a list of dictionaries, each containing information about a detected camera (name, address, etc.).

### `initialize_camera(camera_info, context)`
- Takes camera information (from `list_connected_cameras`) and a `gphoto2` context.
- Attempts to establish a connection with the camera and initialize it.
- Extracts the camera's serial number from the camera summary.
- Returns a tuple containing a `gphoto2.Camera` object and the extracted serial number if successful, otherwise `None, None`.

### `set_camera_time_to_now(camera, camera_id, context)`
- Attempts to set the specified camera's internal date and time to the current system time.
- This uses the `datetime` widget in the camera's configuration. Not all cameras support this, or the widget name might differ.

### `trigger_and_handle_camera(camera, camera_id, context, timestamp, serial_number)`
- This function is executed in a separate thread for each camera.
- Receives the camera object, a session-specific camera ID, the gphoto2 context, a global timestamp for the capture batch, and the camera's serial number.
- Sends the capture command to the camera.
- If `DOWNLOAD_AFTER_CAPTURE` is `True`, it proceeds to download the captured image to a folder named after the `serial_number` within the `DOWNLOAD_PATH_PREFIX`, using the provided `timestamp` in the filename.

### `main()`
- The main entry point of the script.
- Creates a `gphoto2.Context`.
- Calls `list_connected_cameras` to find cameras.
- Iterates through detected cameras, calls `initialize_camera` for each, and optionally `set_camera_time_to_now`.
- Waits for user input (Enter key) before triggering.
- Creates and starts a new thread for each initialized camera, targeting the `trigger_and_handle_camera` function.
- Waits for all threads to complete.
- Cleans up by exiting and freeing all camera objects.

## Dependencies

- `python-gphoto2`: Python bindings for the `libgphoto2` library.
- `os`: For creating directories if downloading images.
- `time`: For timestamps and performance measurement.
- `threading`: For concurrent camera operations.

## Usage

1. Ensure `libgphoto2` and the `python-gphoto2` wrapper are installed.
2. Connect your cameras via USB.
3. Run the script from the command line: `python src/multi_camera_trigger.py`
4. The script will list detected cameras and attempt to initialize them.
5. If cameras are initialized successfully, press Enter to trigger them.

## Notes

- For the most precise simultaneous triggering, it's recommended to set `DOWNLOAD_AFTER_CAPTURE = False`. Downloading images introduces variable delays for each camera.
- Camera compatibility depends on `libgphoto2` support.
- Ensure cameras are in a mode that allows remote control (e.g., PTP mode).
