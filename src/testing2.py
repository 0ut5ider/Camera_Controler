import gphoto2 as gp
import sys

print("Searching for cameras...")

context = gp.Context()

try:
    # This returns a list of (name, addr) tuples
    port_info_list = gp.check_result(gp.gp_port_info_list_new())
    gp.check_result(gp.gp_port_info_list_load(port_info_list))

    abilities_list = gp.check_result(gp.gp_abilities_list_new())
    gp.check_result(gp.gp_abilities_list_load(abilities_list, context))

    detected_cameras = gp.check_result(gp.gp_abilities_list_detect(abilities_list, port_info_list, context))

    if not detected_cameras:
        print("No cameras detected.")
        sys.exit(0)

    print(f"Detected {len(detected_cameras)} camera(s):")

    for name, addr in detected_cameras:
        print(f"  Found camera: {name} on port {addr}")

        camera = None
        try:
            # Initialize camera object for the detected camera
            camera = gp.Camera()
            # Set the port for this specific camera using the address (addr)
            idx = port_info_list.lookup_path(addr)
            camera.set_port_info(port_info_list[idx])

            camera.init()

            # Get the configuration tree
            config_root = camera.get_config()

            # Navigate the configuration tree to find 'serialnumber'
            try:
                serial_number_widget = gp.check_result(gp.gp_widget_get_child_by_name(config_root, 'serialnumber'))
                serial_number = gp.check_result(gp.gp_widget_get_value(serial_number_widget))
                print(f"    Serial Number: {serial_number}")
            except gp.GPhoto2Error as e:
                print(f"    Could not retrieve serial number: {e}")
            except AttributeError:
                 print("    Could not find 'serialnumber' config. It might not be available or its name is different for this camera.")


        except gp.GPhoto2Error as e:
            print(f"    GPhoto2 Error connecting to {name}: {e}")
        except Exception as e:
            print(f"    An unexpected error occurred with {name}: {e}")
        finally:
            # Always try to exit the camera cleanly
            if camera:
                try:
                    camera.exit()
                    print(f"    Disconnected from {name}")
                except gp.GPhoto2Error as e:
                     print(f"    Error disconnecting from {name}: {e}")

except gp.GPhoto2Error as ex:
    if ex.code == gp.GP_ERROR_MODEL_NOT_FOUND:
        print("No cameras found.")
    else:
        print(f"Error detecting cameras: {ex}")
except Exception as e:
    print(f"An unexpected error occurred during detection: {e}")

print("\nFinished processing cameras.")
