import gphoto2 as gp
import time
import os

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
        # gp.check_result(gp.gp_camera_free(camera)) # Free the camera object - Removed due to AttributeError
        return None, None

def main():
    context = gp.Context()

    print("Detecting cameras...")
    camera_infos = list_connected_cameras(context)

    if not camera_infos:
        print("No cameras detected. Exiting.")
        return

    print(camera_infos)
    print("  ")

    

    initialized_cameras_data = []
    for i, cam_info in enumerate(camera_infos):
        # Assign a simple ID for this session (still useful for logging/tracking)
        cam_info['id'] = i + 1 # Use 1-based indexing for user-friendliness
        camera_obj, serial_number = initialize_camera(cam_info, context)
        if camera_obj and serial_number:
            initialized_cameras_data.append({'obj': camera_obj, 'id': cam_info['id'], 'serial': serial_number})
            # In this test script, we don't need to set time or trigger, just initialize and exit
            try:
                gp.check_result(gp.gp_camera_exit(camera_obj, context))
                print(f"Exited Cam {cam_info['id']}")
            except gp.GPhoto2Error as ex:
                print(f"Error exiting Cam {cam_info['id']}: {ex}")
            except Exception as e:
                 print(f"Unexpected error exiting Cam {cam_info['id']}: {e}")


    if not initialized_cameras_data:
        print("No cameras were successfully initialized. Exiting.")
        return

    print("\nInitialization test finished.")


if __name__ == "__main__":
    main()
