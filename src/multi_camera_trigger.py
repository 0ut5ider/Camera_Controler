import gphoto2 as gp
import threading
import time
import os

# --- Configuration ---
# Set to True if you want to download the image immediately after capture.
# For purest trigger simultaneity, keep this False and download later.
DOWNLOAD_AFTER_CAPTURE = False
DOWNLOAD_PATH_PREFIX = "captures/cam" # Files will be saved like: captures/cam1_timestamp_IMG_1234.JPG
# ---------------------

def list_connected_cameras(context):
    """Detects and returns basic info for connected cameras."""
    camera_infos = []
    try:
        # gp.check_result can raise GPhoto2Error if something goes wrong
        port_info_list = gp.check_result(gp.gp_port_info_list_new())
        gp.check_result(gp.gp_port_info_list_load(port_info_list))
        
        abilities_list = gp.check_result(gp.gp_abilities_list_new())
        gp.check_result(gp.gp_abilities_list_load(abilities_list, context))
        
        detected_cameras = gp.check_result(gp.gp_abilities_list_detect(abilities_list, port_info_list, context))
        
        for i, (name, addr) in enumerate(detected_cameras):
            camera_infos.append({'id': i, 'name': name, 'addr': addr, 'port_info_list': port_info_list, 'abilities_list': abilities_list})
        
        # Free the lists if they are not used outside this scope by camera objects directly
        # Note: Camera objects will take ownership of port_info and abilities_list items
        # if we pass their items directly. Here we are passing the whole list for lookup.
        # If not using later, they should be freed. However, often easier to let camera object manage.
    except gp.GPhoto2Error as ex:
        if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
            print("No cameras found.")
        else:
            print(f"Error detecting cameras: {ex}")
    return camera_infos


def initialize_camera(camera_info, context):
    """Initializes a camera given its info."""
    camera = gp.check_result(gp.gp_camera_new())
    
    # Set abilities
    abilities = gp.check_result(gp.gp_abilities_list_get_abilities(camera_info['abilities_list'], camera_info['id']))
    gp.check_result(gp.gp_camera_set_abilities(camera, abilities))

    # Set port
    port_info = gp.check_result(gp.gp_port_info_list_get_info(camera_info['port_info_list'], gp.check_result(gp.gp_port_info_list_lookup_path(camera_info['port_info_list'],camera_info['addr']))))
    gp.check_result(gp.gp_camera_set_port_info(camera, port_info))
    
    print(f"Initializing camera: {camera_info['name']} at {camera_info['addr']} (ID: {camera_info['id']})")
    try:
        gp.check_result(gp.gp_camera_init(camera, context))
        summary_text = gp.check_result(gp.gp_camera_get_summary(camera, context)).text
        print(f"Initialized: {summary_text.strip()}")

        # Attempt to extract serial number from summary
        serial_number = "unknown_serial"
        for line in summary_text.splitlines():
            if "Serial Number:" in line:
                serial_number = line.split("Serial Number:")[1].strip()
                break
        print(f"Extracted Serial Number: {serial_number}")

        return camera, serial_number
    except gp.GPhoto2Error as ex:
        print(f"Failed to initialize camera {camera_info['name']}: {ex}")
        gp.check_result(gp.gp_camera_exit(camera, context)) # Attempt to exit even on init fail
        gp.check_result(gp.gp_camera_free(camera)) # Free the camera object
        return None, None

def set_camera_time_to_now(camera, camera_id, context):
    """Sets the camera's datetime to the current system time."""
    try:
        config = gp.check_result(gp.gp_camera_get_config(camera, context))
        dt_widget = gp.check_result(gp.gp_widget_get_child_by_name(config, 'datetime'))
        # Set to current system time (UTC epoch seconds)
        now_epoch = int(time.time())
        gp.check_result(gp.gp_widget_set_value(dt_widget, now_epoch))
        gp.check_result(gp.gp_camera_set_config(camera, config, context))
        print(f"Cam {camera_id}: Time set to {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_epoch))}")
    except gp.GPhoto2Error as ex:
        # Not all cameras support this, or widget name might differ
        if ex.code == gp.GP_ERROR_NOT_SUPPORTED or "Could not find widget" in str(ex):
            print(f"Cam {camera_id}: Setting time not supported or 'datetime' widget not found.")
        else:
            print(f"Cam {camera_id}: Error setting time: {ex}")


def trigger_and_handle_camera(camera, camera_id, context, timestamp, serial_number):
    """Triggers the camera and optionally downloads the image."""
    thread_name = threading.current_thread().name
    print(f"{thread_name}: Triggering Cam {camera_id} (Serial: {serial_number})...")
    try:
        # Capture image (leaves on camera card - fastest for triggering)
        # camera.capture returns a CameraFilePath object (folder, name)
        file_path = gp.check_result(gp.gp_camera_capture(camera, gp.GP_CAPTURE_IMAGE, context))
        capture_time = time.perf_counter()
        print(f"{thread_name}: Cam {camera_id} captured: {file_path.folder}/{file_path.name} at {capture_time:.4f}")

        if DOWNLOAD_AFTER_CAPTURE:
            # Use serial number for the target folder
            target_folder = f"captures/{serial_number}"
            os.makedirs(target_folder, exist_ok=True)
            target_filename = f"{target_folder}/{timestamp}_{file_path.name}"
            
            print(f"{thread_name}: Cam {camera_id} downloading {file_path.folder}/{file_path.name} to {target_filename}")
            camera_file = gp.check_result(gp.gp_camera_file_get(
                camera, file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL, context))
            gp.check_result(gp.gp_file_save(camera_file, target_filename))
            download_time = time.perf_counter()
            print(f"{thread_name}: Cam {camera_id} downloaded in {download_time - capture_time:.2f}s")

    except gp.GPhoto2Error as ex:
        print(f"{thread_name}: Cam {camera_id} - ERROR: {ex}")
    except Exception as e:
        print(f"{thread_name}: Cam {camera_id} - UNEXPECTED ERROR: {e}")

def main():
    context = gp.Context()
    
    print("Detecting cameras...")
    camera_infos = list_connected_cameras(context)

    if not camera_infos:
        print("No cameras detected. Exiting.")
        return

    initialized_cameras_data = []
    for i, cam_info in enumerate(camera_infos):
        # Assign a simple ID for this session (still useful for logging/tracking)
        cam_info['id'] = i + 1 # Use 1-based indexing for user-friendliness
        camera_obj, serial_number = initialize_camera(cam_info, context)
        if camera_obj and serial_number:
            initialized_cameras_data.append({'obj': camera_obj, 'id': cam_info['id'], 'serial': serial_number})
            # Optionally synchronize time
            set_camera_time_to_now(camera_obj, cam_info['id'], context)


    if not initialized_cameras_data:
        print("No cameras were successfully initialized. Exiting.")
        return

    print(f"\n--- Will attempt to trigger {len(initialized_cameras_data)} camera(s) ---")
    input("Press Enter to trigger all cameras...")

    threads = []
    global_timestamp = time.strftime("%Y%m%d-%H%M%S")

    trigger_start_time = time.perf_counter()
    for cam_data in initialized_cameras_data:
        thread = threading.Thread(
            target=trigger_and_handle_camera,
            args=(cam_data['obj'], cam_data['id'], context, global_timestamp, cam_data['serial']),
            name=f"Thread-Cam{cam_data['id']}"
        )
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
    
    trigger_end_time = time.perf_counter()
    print(f"\nAll camera trigger threads completed in {trigger_end_time - trigger_start_time:.4f} seconds.")

    # Cleanup
    print("\nExiting cameras...")
    for cam_data in initialized_cameras_data:
        try:
            gp.check_result(gp.gp_camera_exit(cam_data['obj'], context))
            gp.check_result(gp.gp_camera_free(cam_data['obj'])) # Free the camera object
            print(f"Exited and freed Cam {cam_data['id']}")
        except gp.GPhoto2Error as ex:
            print(f"Error exiting Cam {cam_data['id']}: {ex}")
        except Exception as e:
             print(f"Unexpected error exiting Cam {cam_data['id']}: {e}")


    print("Script finished.")

if __name__ == "__main__":
    main()
