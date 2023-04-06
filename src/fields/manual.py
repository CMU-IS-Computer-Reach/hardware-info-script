from fields.field import ManualField
from fields.config import VIDEO_PORT_OPTIONS, FINAL_OS_OPTIONS, ALL_FIELDS_API_NAMES

CRID = ManualField(
    "CRID", 
    "CRID", 
    type="id"
)
def validate_crid(input_s, sf):
    if input_s == "":
        raise Exception("CRID is required")
    else:
        try:
            sf.Equipment__c.get_by_custom_id(ALL_FIELDS_API_NAMES["CRID"], input_s)['Id']
            return input_s
        except:
            raise Exception(f"There is no record with CRID {input_s} in Salesforce, please double check and reenter")
CRID.validate_fn = validate_crid

has_webcam = ManualField(
    "has_webcam", 
    "Has webcam?", 
    type="bool", 
    default_value=False
)
def validate_webcam(input_s):
    if input_s == "y":
        return True
    elif input_s == "n":
        return False
    elif input_s == "":
        return None
    else:
        raise Exception("Please provide a valid option [y/n], or ENTER to skip")
has_webcam.validate_fn = validate_webcam


video_ports = ManualField(
    "video_ports", 
    "Video ports", 
    type="multiselect",
    default_value=[],
    options=VIDEO_PORT_OPTIONS
)
def validate_video_ports(input_s):
    if input_s == "":
        return None
    elif input_s in video_ports.options:
        return input_s
    else:
        raise Exception(f"Please provide a valid option {video_ports.options}")
video_ports.validate_fn = validate_video_ports


num_usb_ports = ManualField(
    "num_usb_ports",
    "# USB ports", 
    type="int"
)
def validate_num_usb(input_s):
    if input_s == "":
        return None
    try:
        num = int(input_s)
        if (num < 0 or num > 99):
            raise ValueError
        return num
    except ValueError:
        raise Exception(f"Please provide a valid integer between 0 and 99")
num_usb_ports.validate_fn = validate_num_usb

    
adapter_watts = ManualField(
    "adapter_watts",
    "Adapter watts",
    type="text"
)


final_os = ManualField(
    "final_os",
    "Final OS",
    type="select",
    options=FINAL_OS_OPTIONS
)
def validate_final_os(input_s):
    if input_s == "":
        return None
    elif input_s in final_os.options:
        return input_s
    else:
        raise Exception(f"Please provide a valid option {final_os.options}")
final_os.validate_fn = validate_final_os

manual_fields = [CRID, has_webcam, video_ports, num_usb_ports, adapter_watts, final_os]