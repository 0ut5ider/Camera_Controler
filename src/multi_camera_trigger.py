import gphoto2 as gp
import threading
import time
import os

# --- Configuration ---
# Set to True if you want to download the image immediately after capture.
# For purest trigger simultaneity, keep this False and download later.
DOWNLOAD_AFTER_CAPTURE = True
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
    # Return the lists along with camera_infos
    return camera_infos, port_info_list, abilities_list


def initialize_camera(camera_info, port_info_list, abilities_list, context):
    """Initializes a camera given its info and the detected lists."""
    camera = None
    serial_number = "unknown_serial"
    print(f"Initializing camera: {camera_info['name']} at {camera_info['addr']} (ID: {camera_info['id']})")
    try:
        camera = gp.Camera()
        
        # Set the port for this specific camera using the address (addr)
        # Use the port_info_list passed from list_connected_cameras
        idx = port_info_list.lookup_path(camera_info['addr'])
        camera.set_port_info(port_info_list[idx])

        camera.init()
        
        print(f"Initialized: {camera_info['name']}")

        # Get serial number
        try:
            config_root = camera.get_config()
            serial_number_widget = gp.check_result(gp.gp_widget_get_child_by_name(config_root, 'serialnumber'))
            serial_number = gp.check_result(gp.gp_widget_get_value(serial_number_widget))
            print(f"Extracted Serial Number: {serial_number}")
        except gp.GPhoto2Error as e:
            print(f"Could not get serial number: {e}")
        except AttributeError:
             print("Could not find 'serialnumber' config widget.")

        return camera, serial_number
    except gp.GPhoto2Error as ex:
        print(f"Failed to initialize camera {camera_info['name']}: {ex}")
        # No need to exit here, the camera object is not fully initialized
        return None, None

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
    finally:
        # Always try to exit the camera cleanly after capture attempt
        if camera:
            try:
                camera.exit()
                print(f"{thread_name}: Attempted camera exit after capture.")
            except gp.GPhoto2Error as exit_ex:
                 print(f"{thread_name}: Error during camera exit after capture attempt: {exit_ex}")

def main():
    context = gp.Context()
    
    print("Detecting cameras...")
    camera_infos, port_info_list, abilities_list = list_connected_cameras(context)

    if not camera_infos:
        print("No cameras detected. Exiting.")
        return

#    print(camera_infos)
#    print("  ")

    initialized_cameras_data = []
    for i, cam_info in enumerate(camera_infos):
        # Assign a simple ID for this session (still useful for logging/tracking)
        cam_info['id'] = i + 1 # Use 1-based indexing for user-friendliness
        # Pass the detected lists to initialize_camera
        camera_obj, serial_number = initialize_camera(cam_info, port_info_list, abilities_list, context)
        if camera_obj and serial_number:
            initialized_cameras_data.append({'obj': camera_obj, 'id': cam_info['id'], 'serial': serial_number})

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

    print("Script finished.")

if __name__ == "__main__":
    main()
