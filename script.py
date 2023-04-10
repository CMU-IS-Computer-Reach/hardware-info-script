import os
import sys
import re
import subprocess
import argparse
from simple_salesforce import Salesforce
import PySimpleGUI as sg

description = """
A script that collects and parses hardware details and upload them to Salesforce.

Following fields are asked to be manually input:
- CRID
- Webcam
- Video ports
- # USB ports
- Adapter watts
- Final OS
- Storage

Following fields are automatically collected:
- CPU model
- RAM
- Screen size
- Battery health
- Ethernet
- Wifi
- Optical drive
- Touchscreen
"""

# Salesforce API name for all the fields to be uploaded
# NOTE: If adding a new field, must include its API name here (as shown in Salesforce object schema)
ALL_FIELDS_API_NAMES = {
    "CRID":                 "Computer_Reach_ID__c",
    "has_webcam":           "Webcam_present__c",
    "video_ports":          "Video__c",
    "num_usb_ports":        "USB__c",
    "adapter_watts":        "Adapter_Watts__c",
    "final_os":             "Final_Operating_System__c",
    "model_name":           "Processor_Speed__c",
    "RAM":                  "RAM_Total_MB__c", # TODO: the API name says MB but the field name says GB
    "storage":              "Hard_Drive_GB__c",
    "screen_size":          "Screen_Size__c",
    "battery_health":       "Battery_Health__c",
    "has_ethernet":         "Ethernet_present__c",
    "has_wifi":             "WiFi_present__c",
    "has_optical_drive":    "Optical_Drive_present__c",
    "has_touchscreen":      "TouchScreen_Works__c",
}

# Configurations for some manual fields for convenience
FINAL_OS_OPTIONS = ["20.04_Xubuntu_Linux"] # Salesforce API Name of all final OS options
VIDEO_PORT_OPTIONS = ["VGA", "DVI", "HDMI", "Mini-HDMI", "Display Port", "Mini-Display"] # Salesforce API Name of all video ports options

# Linux commands used to automatically collect a field
AUTO_FIELDS_LINUX_COMMANDS = {
    "model_name":           ["cat /proc/cpuinfo", "grep 'model name'"],
    "RAM":                  ["cat /proc/meminfo", "numfmt --field 2 --from-unit=Ki --to-unit=Gi", "sed 's/ kB/G/g'", "grep 'MemTotal'", "awk '{print $2}'"],
    "storage":              ["lsblk -I 8 -d -n --output SIZE"],
    "screen_size":          ["xrandr --current", "grep ' connected'"],
    "battery_health":       ["upower -i `upower -e | grep 'BAT'`", "grep 'capacity'", "awk '{print $2}'", "grep ."],
    "has_ethernet":         ["lspci", "grep 'ethernet' -i", "grep ."],
    "has_wifi":             ["lspci", "grep 'network|wireless' -i -E", "grep ."],
    "has_optical_drive":    ["dmesg", "grep 'cdrom|cd-rom|dvd' -i -E", "grep ."],
    "has_touchscreen":      ["xinput list", "grep 'touchscreen' -i", "grep ."],
}


class EquipmentInfo():
    def __init__(self):                  # description                     # type
        # manually input fields
        # NOTE: If adding a new manual field, MUST add a new class variable (as shown below) AND add the new variable name as is in self.manual_fields
        #       Also needs to update ALL_FIELDS_API_NAMES above correspondingly
        self.CRID = None                 # CRID                              str
        self.has_webcam = False          # Webcam (exists or not)            bool
        self.video_ports = []            # Video ports                       list(str)
        self.num_usb_ports = None        # Number of USB ports               int
        self.adapter_watts = None        # Adapter Watts                     str
        self.final_os = None             # final OS                          str
        self.storage = None              # Storage size (GB)                 number
        
        self.manual_fields = [
            "CRID", 
            "has_webcam", 
            "video_ports", 
            "num_usb_ports", 
            "adapter_watts", 
            "final_os", 
            "storage"
        ]
        
        # automatically collected fields
        # NOTE: If adding a new auto field, MUST add a new class variable (as shown below) AND add the new variable name as is in self.auto_fields
        #       Furthermore, add the corresponding Linux commands to be run in AUTO_FIELDS_LINUX_COMMANDS above
        self.model_name = None           # CPU model                         str
        self.RAM = None                  # RAM size (GB)                     int
        self.screen_size = None          # Screen size (inch)                int
        self.battery_health = None       # Battery health (%)                number
        self.has_ethernet = False        # Ethernet adapter (exists or not)  bool
        self.has_wifi = False            # Wifi card (exists or not)         bool
        self.has_optical_drive = False   # Optical drive (exists or not)     bool
        self.has_touchscreen = False     # Touchscreen (exists or not)       bool
        self.auto_fields = [
            "model_name",
            "RAM",
            "screen_size",
            "battery_health",
            "has_ethernet",
            "has_wifi",
            "has_optical_drive",
            "has_touchscreen"
        ]

        self._errors = dict()            # Stores all the errors that occur when running Linux commands for the automatically collected fields
                                         # Data type: a dictionary mapping from field name (str) to error message (str)

        # Salesforce internal id
        self.eid = None                  

        # command line arguments
        parser = argparse.ArgumentParser(description = description)
        parser.add_argument("-t", "--test", action='store_true', help="test the script on Salesforce Sandbox")
        parser.add_argument("-c", "--cml", action='store_true', help="run the command line version (without GUI)")
        self._args = parser.parse_args()

        # Salesforce authentication
        self.sf = None
        if self.authenticate():
            # run the command line version
            if self._args.cml:
                self.data_input()
                self.data_collection()
                self.data_review()
                self.data_upload()
            else: # run the GUI version
                self.start_GUI()
        else:
            sys.exit(1)

    ########
    # This function checks if Salesforce credentials are stored in the environment, and attempts to connect to Salesforce if so
    ########
    def authenticate(self):
        # check that username, password, and security tokens all exist as environment variables 
        missing = []
        if not os.getenv("SF_BENCH_USERNAME"):
            missing.append("SF_BENCH_USERNAME")
        if not os.getenv("SF_BENCH_PASSWORD"):
            missing.append("SF_BENCH_PASSWORD")
        if not os.getenv("SF_BENCH_TOKEN"):
            missing.append("SF_BENCH_TOKEN")
        if missing:
            print(f"\033[91mMissing the following environment variables for Salesforce credentials: {missing}\033[00m")
            print("Please see instructions in https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/main/README.md")
            return False

        try:
            if self._args.test: # use Sandbox connection for test
                self.sf = Salesforce(
                    username = os.getenv("SF_BENCH_USERNAME"), 
                    password = os.getenv("SF_BENCH_PASSWORD"), 
                    security_token = os.getenv("SF_BENCH_TOKEN"),
                    client_id='Hardware Info Script (test)',
                    domain='test',
                )
            else: # production environment
                self.sf = Salesforce(
                    username = os.getenv("SF_BENCH_USERNAME"), 
                    password = os.getenv("SF_BENCH_PASSWORD"), 
                    security_token = os.getenv("SF_BENCH_TOKEN"),
                    client_id='Hardware Info Script',
                )
            return True
        except Exception as e:
            print(f"\033[91mError occured when trying to connect to Salesforce: {e.message}\033[00m")
            print("Please double check your environment variables SF_BENCH_USERNAME, SF_BENCH_PASSWORD, SF_BENCH_TOKEN, to make sure the correct Salesforce credential is stored; note that security token is automatically updated every time password is changed.")
            return False

    ########
    # This function handles the section where users are asked to manually input data for all fields listed in self.manual_fields
    #
    # NOTE: If a new field is to be added, MUST add code to handle data input and validation for that field as a new class function
    #       Further more, if the new field is called xxx, the corresponding handling function MUST be named _xxx_fn
    #       Scroll down for functions under the comment "data input handling functions for manual fields" as a reference
    ########
    def data_input(self):
        print()
        print("\033[104m***Manual Data Entry Section***\033[00m")
        print("\033[93mAfter each prompt, enter value and press ENTER, or directly press ENTER to skip\033[00m")
        cnt = len(self.manual_fields)
        i = 1

        # input CRID (required)
        while True:
            cr = input(f" ({i:02d}/{cnt:02d}) [REQUIRED] Enter CRID: ")
            if not cr:
                print("\033[91m  CRID is required\033[00m")
            else:
                try:
                    self.eid = self.sf.Equipment__c.get_by_custom_id(ALL_FIELDS_API_NAMES["CRID"], cr)['Id']
                    self.CRID = cr
                    break
                except:
                    print(f"\033[91m  There is no record with CRID {cr} in Salesforce, please double check and reenter\033[00m")
                    print("\033[93m  (if you are trying to create a new equipment record, please add it from Salesforce UI first)\033[00m")
        i += 1

        # input the remaining manual fields
        # functions handling taking input and validating it for each field are further below
        for field in self.manual_fields[1:]:
            try:
                getattr(self, f"_{field}_fn")(i)
            except:
                print(f"\033[91m  Unspecified new field {field}; please contact administrator to update the script\033[00m")
            i += 1

        print()

    ########
    # This function handles the section where all fields listed in self.auto_fields are collected automatically by running Linux commands
    #
    # NOTE: If a new field is to be added, MUST add the corresponding Linux command to AUTO_FIELDS_LINUX_COMMANDS
    #       Each section in this function handles a single field; refer to their structure if you are adding a new field
    ########
    def data_collection(self):
        print("\033[104m***Auto Data Collection Section***\033[00m")

        # CPU model
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["model_name"]), 
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self._errors["model name"] = e.output if e.output else "`grep` didn't find match (unexpected /proc/cpuinfo file format)"
        else:
            try:
                r = re.match(r"\s*model name\s*:\s*(.*)", output)
                self.model_name = r.group(1)
            except Exception as e:
                self._errors["model name"] = "regex matching error (unexpected /proc/cpuinfo file format)"

        # RAM size (GB)
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["RAM"]),
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self._errors["RAM"] = e.output if e.output else "`grep` didn't find match (unexpected /proc/meminfo file format)"
        else:
            try:
                r = re.match(r"(\d+)G", output)
                self.RAM = int(r.group(1))
            except Exception as e:
                self._errors["RAM"] = "regex matching error (unexpected /proc/meminfo file format)"
        
        # Screen size (inch)
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["screen_size"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self._errors["screen size"] = e.output if e.output else "`grep` didn't find match (`xrandr` cannot find current display device)"
        else:
            try:
                r = re.match(r".*\s+(\d+)mm\s+x\s+(\d+)mm", output)
                w = int(r.group(1))
                h = int(r.group(2))
                diagonal = (w * w + h * h) ** 0.5
                self.screen_size = round(diagonal / 25.4)
            except Exception as e:
                self._errors["screen size"] = "regex matching error (unexpected output format from `xrandr`)"
                
        # Battery health (%)
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["battery_health"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self._errors["battery health"] = e.output if e.output else "`grep` didn't find match (battery information not found by `upower`)"
        else:
            try:
                r = re.match(r"([\d\.]*)%", output)
                self.battery_health = round(float(r.group(1)), 2)
            except Exception as e:
                self._errors["battery health"] = "regex matching error (unexpected output format from `upower`)"
        
        # Ethernet
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["has_ethernet"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_ethernet = False
        else:
            self.has_ethernet = True

        # WiFi
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["has_wifi"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_wifi = False
        else:
            self.has_wifi = True

        # Optical drive
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["has_optical_drive"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_optical_drive = False
        else:
            self.has_optical_drive = True

        # Touchscreen
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["has_touchscreen"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_touchscreen = False
        else:
            self.has_touchscreen = True

        self._display_errors()

    ########
    # This function handles the section where users can review the current data and modify any fields if necessary
    #
    # NOTE: If a new field is to be added, there are several cases:
    #       - (a) If it's a manual field, you should have already implemented the corresponding input handling function, as directed in the comments for data_input() above
    #             then section (a) below already handles input, and no additional code needs to be added
    #       - (b) If it's an auto field that takes on a boolean value, you MUST name it has_xxx, 
    #             then section (b) below already handles input, and no additional code needs to be added
    #       - (c) If it's an auto field that takes on other types of value, you MUST implement the code for taking input and validating it in this function
    #             see section (c) below as a reference
    #       - (d) If it's an auto field that you do not want to be ever manually modified, add it to section (d) below, which currenly handles model_name and RAM
    ########
    def data_review(self):
        print("\033[104m***Data Review Section***\033[00m")
        all_fields = self.manual_fields + self.auto_fields

        updated = True
        while True:
            # re-display the current data if any modifications has been made
            if updated:
                print("\nData:")
                for idx, field in enumerate(all_fields):
                    if idx == 0:
                        continue
                    val = getattr(self, field)
                    if val != None:
                        print(f" [{idx:>2}] {field:<20}: {val}")
                    else:
                        print(f" [{idx:>2}] {field:<20}: (empty)")

            # allow user to choose a field they want to modify
            choice = input(f" *Enter integet option if you want to modify any field, or Y to proceed to data upload:").lower()
            if not choice:
                print("\033[91m  Please enter a valid integer option, or Y to proceed\033[00m")
                updated = False
            elif choice == "y":
                print()
                break
            else:
                try:
                    choice = int(choice)
                    if choice < 1:
                        raise ValueError
                    field = all_fields[choice]
                except:
                    print("\033[91m  Please enter a valid integer option, or ENTER to skip\033[00m")
                    updated = False
                else:
                    # (a) manual fields: call the corresponding input handling function, the same as the one used in data input section
                    if field in self.manual_fields:
                        print()
                        getattr(self, f"_{field}_fn")()
                        updated = True
                    # (b) automatic fields that're called "has_xxx": input has to be [y/n], mapped to True of False
                    elif field.startswith("has"):
                        print()
                        while True:
                            ans = input(f" - Enter new value for {field} [y/n]: ").lower()
                            if ans == "y":
                                setattr(self, field, True)
                                break
                            elif ans == "n" or ans == "":
                                setattr(self, field, False)
                                break
                            else:
                                print("\033[91m  Please enter a valid option [y/n], or ENTER to skip\033[00m")
                        updated = True
                    # (c) automatic fields that are floats
                    elif field == "screen_size" or field == "battery_health":
                        print()
                        while True:
                            ans = input(f" - Enter new value for {field} (a number): ").lower()
                            try:
                                ans = float(ans)
                                if ans > 100:
                                    raise ValueError
                                setattr(self, field, ans)
                                break
                            except:
                                print("\033[91m  Please enter a valid number within 100, or ENTER to skip\033[00m")
                        updated = True
                    # (d) automatic fields that have no good reason to be modified
                    elif field == "model_name" or field == "RAM":
                        print(f"\033[91m  ***{field} should almost never be manually altered; if must, modify it in Salesforce directly\033[00m")
                        updated = False
                    # other unspecified new field
                    else:
                        print(f"\033[91m  Unhandled new field {field}; please modify it in Salesforce directly and contact administrator to update the script\033[00m")
                        updated = False

    ########
    # This function handles the section where users can choose whether or not they want to upload the data to Salesforce
    #
    # NOTE: If a new field is to be added, there are no changes to be done here, 
    #       BUT you may need to modify _convert_to_record() for some types of fields - scroll to that function for more information
    ########
    def data_upload(self):
        print("\033[104m***Data Upload Section***\033[00m")
        print("\033[93m Below fields will be uploaded to Saleforce, any fields not shown will be empty:\033[00m")
        for field in self.manual_fields + self.auto_fields:
            val = getattr(self, field)
            if val != None:
                print(f"  {field:<20}: {val}")
        print()

        while True:
            res = input(f"\033[44mUpload to Salesforce? [y/n]: \033[00m").lower()
            if res == "y":
                record = self._convert_to_record()
                try:
                    self.sf.Equipment__c.update(self.eid, record)
                    print(f"\033[92mData uploaded successfully! CRID: {self.CRID}\033[00m")
                except:
                    print(f"\033[91mUnexpected error, likely that record with CRID {self.CRID} is recently deleted from Salesforce\033[00m")
                    print("\033[90mData not uploaded.\033[00m")
                finally:
                    break
            elif res == "n":
                print("\033[90mData not uploaded.\033[00m")
                break
            else:
                print("\033[91m  Please enter a valid option [y/n]\033[00m")

    ########
    # This section contains all the functions that handles data input and validation for manual fields
    # NOTE: If a field is named xxx, the corresponding function MUST be named _xxx_fn
    # NOTE: Each function also takes in an optional integer i - this is purely for display purpose!!!
    #       (data_input() calls these functions with an integer i, so as to show how many questions there are left to be answer,
    #        but data_review() calls these functions without the integer, since there's no question number to display)
    ########

    def _has_webcam_fn(self, i=None):
        while True:
            if i:
                webcam = input(f" ({i:02d}/{len(self.manual_fields):02d}) Webcam presents? [y/n]: ").lower()
            else:
                webcam = input(f" - Enter new value for has_webcam [y/n]: ").lower()

            if webcam == "y":
                self.has_webcam = True
                break
            elif webcam == "n" or webcam == "":
                self.has_webcam = False
                break
            else:
                print("\033[91m  Please enter a valid option [y/n], or ENTER to skip\033[00m")

    def _video_ports_fn(self, i=None):
        if i:
            print(f" ({i:02d}/{len(self.manual_fields):02d}) Choose available video ports:")
        else:
            print(f" - Choose available video ports:")

        for port in VIDEO_PORT_OPTIONS:
            while True:
                p = input(f"  - {port} port presents? [y/n]: ").lower()
                if p == "y":
                    self.video_ports.append(port)
                    break
                elif p == "n" or p == "":
                    break
                else:
                    print("\033[91m  Please enter a valid option [y/n], or ENTER to skip\033[00m")

    def _num_usb_ports_fn(self, i=None):
        while True:
            if i:
                usb = input(f" ({i:02d}/{len(self.manual_fields):02d}) Enter # USB ports: ")
            else:
                usb = input(f" - Enter new value for # USB ports: ")

            if not usb:
                break
            try:
                usb = int(usb)
                if (usb < 0 or usb > 99):
                    raise ValueError
                self.num_usb_ports = usb
                break
            except ValueError:
                print("\033[91m  Please enter a valid integer, or ENTER to skip\033[00m")

    def _adapter_watts_fn(self, i=None):
        if i:
            watts = input(f" ({i:02d}/{len(self.manual_fields):02d}) Enter adpater watts: ")
        else:
            watts = input(f" Enter new value for adpater watts: ")

        if watts:
            self.adapter_watts = watts
        i += 1

    def _final_os_fn(self, i=None):
        while True:
            choices = ""
            for j, opt in enumerate(FINAL_OS_OPTIONS):
                choices += "  [{}] {}\n".format(j+1, opt)
            if i:
                os = input(f" ({i:02d}/{len(self.manual_fields):02d}) Choose an option for final OS, or ENTER to skip:\n{choices} *choice: ")
            else:
                os = input(f" - Choose an option for final OS, or ENTER to skip:\n{choices} *choice: ")

            if not os:
                break
            try:
                if int(os) < 1:
                    raise ValueError
                self.final_os = FINAL_OS_OPTIONS[int(os)-1]
                break
            except:
                print("\033[91m  Please enter a valid integer option, or ENTER to skip\033[00m")

    def _storage_fn(self, i=None):
        if i:
            print(f" ({i:02d}/{len(self.manual_fields):02d}) Enter storage size (GB):")
        else:
            print(f" - Enter new value for storage size (GB):")

        print("  Below are a list of all mounted file systems and their size:")
        try:
            output = subprocess.check_output("lsblk -d -o NAME,SIZE,TYPE,MOUNTPOINT | grep 'name|sda|sdb|nvme' -i -E",
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"\033[91m  (Unexpected error when running Linux command, no available information can be provided at this time)\033[00m")
        else:
            for line in output.split("\n"):
                if not line:
                    continue
                else:
                    print(f"  {line}")
            while True:
                storage = input(f" *total storage size (GB): ")
                if not storage:
                    break
                try:
                    storage = float(storage)
                    self.storage = storage
                    break
                except ValueError:
                    print("\033[91m  Please enter a valid number, or ENTER to skip\033[00m")

    ########
    # other helper functions
    ########

    ########
    # This functions converts data into the correct JSON format accepted by the database schema in Salesforce
    # NOTE: Most fields, such as those of boolean or number types, don't require extra convertion, because their values can be uploaded as is into Salesforce
    #       However, some fields, such as multi-select, require the data to be a special format, hence MUST be converted in this function
    #       For some other fields, we may also want to convert the data due to some requirements,
    #         e.g. in this function we change battery health from just a number, to a number followed by a % sign, so that it's more readable in Salesforce
    ########
    def _convert_to_record(self):
        record = dict()
        
        for field in ALL_FIELDS_API_NAMES:
            var = getattr(self, field)
            if var != None:
                if field == "video_ports": # this is a picklist (multi-select) field in Salesforce, so data should be in the format of "selection1;selection;..."
                    var = ";".join(var)
                elif field == "battery_health": # add a % sign after the number for readability
                    var = str(var) + "%"
                record[ALL_FIELDS_API_NAMES[field]] = var

        return record
    
    ########
    # This functions is for displaying errors that happen when running Linux commands for the automatically collected fields
    # NOTE: If a new auto field is to be added, there are no changes to be done here
    #       However, you should make sure that any new errors that may occur for the new auto field is saved to self._errors, which is a dictionary mapping field name to the error
    ########
    def _display_errors(self):
        if len(self._errors):
            print("\033[91mBelow error occured when running Linux commands:\033[00m")
            for field, err in self._errors.items():
                print(f"\033[91m - {field}: {err}\033[00m")
        else:
            print("\033[92mNo error occured; all commands returned successfully\033[00m")
        print()

    ########
    # This function runs a simple GUI, implemented with PySimpleGUI, that is (mostly) doing the same thing as the script above
    #
    # NOTE: The GUI is mostly hardcoded and not easily extendable at the moment. It is more of a proof of concept as opposed to a fully developed GUI,
    #       since there is NO validation of user inputs, nor can users modify fields like they could in the command line version
    #       To add a new field, you should manually add the new boxes into the layout, and manually turn their display on and off at the correct step
    ########
    def start_GUI(self):
        step = 0

        # color theme of the GUI
        sg.theme('LightGrey1')
        font_small = ("Arial", 12)
        font = ("Arial", 14)
        font_bold = ("Arial Bold", 14)

        # make the checkboxes for all video ports
        video_ports = [sg.pin(sg.Checkbox(port, key=port, font=font_small, size=(15,1), visible=False)) for port in VIDEO_PORT_OPTIONS]
        video_ports_boxes = []
        for i in range(0, len(VIDEO_PORT_OPTIONS), 3):
            video_ports_boxes.append([video_ports[i], video_ports[i+1], video_ports[i+2]])

        # make the select box for final OS
        final_os_boxes = [
            sg.pin(sg.Text("Final OS:", key="final_os_text", size=(15,1), font=font_bold, visible=False)),
            sg.Combo(["(leave as empty)"] + FINAL_OS_OPTIONS, default_value="(leave as empty)", key="final_os", font=font, visible=False)
        ]

        # make the texts for storage size display
        storage_boxes = [
            [sg.pin(sg.Text("Storage (GB):", key="storage_text", size=(15,1), font=font_bold, visible=False)), sg.Input(key="storage", size=(8,1), font=font, visible=False)],
            [sg.pin(sg.Text("(Below are a list of all mounted file systems and their size:)", key="storage_prompt", font=font_small, visible=False))]
        ]
        try:
            output = subprocess.check_output("lsblk -d -o NAME,SIZE,TYPE,MOUNTPOINT | grep 'name|sda|sdb|nvme' -i -E",
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            pass
        else:
            rows = []
            heading = []
            for i, line in enumerate(output.split("\n")):
                if not line:
                    continue
                elif i == 0:
                    heading = line.split()
                else:
                    line = line.split()
                    rows.append(line)
        finally:
            storage_boxes.append([sg.pin(sg.Table(
                values=rows, 
                headings=heading,
                key="storage_table",
                visible=False,
            ))])

        auto_fields_boxes = [[
            sg.pin(sg.Text(f"{field}:", key=field+"_text", size=(15,1), font=font_bold, visible=False)),
            sg.pin(sg.Text("", key=field, size=(45,1), font=font_small, visible=False))
        ] for field in self.auto_fields]
        
        window = sg.Window(title="Hardware Info Script", margins=(20, 20), layout=[
            # status bar
            [sg.StatusBar("(Error messages will be displayed in this bar)", key="status", size=(30,1), font=font_small, text_color="Yellow", background_color="grey")],
            [sg.Text("")],

            # CRID display
            [sg.pin(sg.Text("CRID: ", key="CRID_text", size=(5,1), font=font_bold)), sg.Input(key="CRID", size=(15,1), font=font)],
            [sg.pin(sg.Text("", key="CRID_display", size=(20,1), font=font_bold, visible=False))],

            # section prompt
            [sg.Text("", key="prompt_space")],
            [sg.pin(sg.Text("", key="prompt", size=(60,1), text_color="Blue", font=font))],
            
            # manual data entry
            [sg.pin(sg.Text("Webcam exists?:", key="has_webcam_text", size=(15,1), font=font_bold, visible=False)), sg.Checkbox("", key="has_webcam", visible=False)],
            [sg.pin(sg.Text("# USB ports:", key="num_usb_ports_text", size=(15,1), font=font_bold, visible=False)), sg.Input(key="num_usb_ports", size=(8,1), font=font, visible=False)],
            [sg.pin(sg.Text("Adapter watts:", key="adapter_watts_text", size=(15,1), font=font_bold, visible=False)), sg.Input(key="adapter_watts", size=(8,1), font=font, visible=False)],
            [sg.pin(sg.Text("Video ports:", key="video_ports_text", size=(15,1), font=font_bold, visible=False))],
            video_ports_boxes,
            final_os_boxes,
            storage_boxes,
            
            # automatic data collection
            [sg.pin(sg.Text("Below shows values of all automatically collected fields:", key="prompt_auto_data", size=(60,1), font=font, visible=False))],
            auto_fields_boxes,

            # prompts for data upload
            [sg.pin(sg.Text("", key="prompt_space_2", size=(20,1), visible=False))],
            [sg.pin(sg.Text("Click NEXT to upload data to Salesforce (may take a few seconds to load!)", key="prompt_upload", size=(60,1), font=font, visible=False))],
            [sg.pin(sg.Text("Data uploaded successfully!", key="prompt_upload_success", size=(60,1), font=font, visible=False))],
            [sg.pin(sg.Text("Data upload FAILED.", key="prompt_upload_failure", size=(60,1), font=font, visible=False))],
            
            # NEXT and EXIT buttons
            [sg.Button("NEXT", font=font_small, size=(6,1)), sg.Button("EXIT", font=font_small, size=(6,1))],
        ], size=(700, 700))

        while True:
            event, values = window.read()
            if event in (None, 'EXIT'):
                break
            # page 2: manual data entry
            if event == "NEXT" and step == 0:
                window['status'].update("")
                cr = values['CRID']
                try:
                    self.eid = self.sf.Equipment__c.get_by_custom_id(ALL_FIELDS_API_NAMES["CRID"], cr)['Id']
                    self.CRID = cr
                    # display CRID
                    window['CRID_text'].update(visible = False)
                    window['CRID'].update(visible = False)
                    window['CRID_display'].update(f"CRID: {self.CRID}")
                    window['CRID_display'].update(visible = True)

                    # display section prompt
                    window['prompt_space'].update(visible = True)
                    window['prompt'].update("====STEP 1: MANUAL DATA ENTRY====")

                    # display manual input fields
                    # has webcam
                    window['has_webcam_text'].update(visible = True)
                    window['has_webcam'].update(visible = True)
                    
                    # number of usb ports
                    window['num_usb_ports_text'].update(visible = True)
                    window['num_usb_ports'].update(visible = True)

                    # adapter watts
                    window['adapter_watts_text'].update(visible = True)
                    window['adapter_watts'].update(visible = True)
                    
                    # video ports
                    window['video_ports_text'].update(visible = True)
                    for port in VIDEO_PORT_OPTIONS:
                        window[port].update(visible = True)

                    # final OS
                    window['final_os_text'].update(visible = True)
                    window['final_os'].update(visible = True)

                    # storage
                    window['storage_text'].update(visible = True)
                    window['storage'].update(visible = True)
                    window['storage_prompt'].update(visible = True)
                    window['storage_table'].update(visible = True)

                    step += 1
                except:
                    window['status'].update(f"No record with CRID {cr} in Salesforce, please double check and reenter")
            # page 3: auto data collection
            elif event == "NEXT" and step == 1:
                # save user inputs
                for field in self.manual_fields:
                    if field == "CRID":
                        pass
                    elif field == "video_ports":
                        self.video_ports = []
                        for port in VIDEO_PORT_OPTIONS:
                            if values[port]:
                                self.video_ports.append(port)
                    elif field == "final_os":
                        if values[field] != "(leave as empty)":
                            setattr(self, field, values[field])
                    else:
                        if values[field] != "":
                            setattr(self, field, values[field])
                step += 1

                # turn off display for previous input fields first
                window['has_webcam_text'].update(visible = False)
                window['has_webcam'].update(visible = False)
                window['num_usb_ports_text'].update(visible = False)
                window['num_usb_ports'].update(visible = False)
                window['adapter_watts_text'].update(visible = False)
                window['adapter_watts'].update(visible = False)
                window['video_ports_text'].update(visible = False)
                for port in VIDEO_PORT_OPTIONS:
                    window[port].update(visible = False)
                window['final_os_text'].update(visible = False)
                window['final_os'].update(visible = False)
                window['storage_text'].update(visible = False)
                window['storage'].update(visible = False)
                window['storage_prompt'].update(visible = False)
                window['storage_table'].update(visible = False)

                # then turn on display for auto collected data
                window['prompt'].update("====STEP 2: AUTO DATA COLLECTION====")

                # run data collection and report errors (if any)
                self.data_collection()
                if len(self._errors):
                    window['status'].update(f"Error has occured on {len(self._errors)} field(s), please report terminal output to manager")
                
                window["prompt_auto_data"].update(visible = True)
                window["prompt_space_2"].update(visible = True)
                window["prompt_upload"].update(visible = True)
                for field in self.auto_fields:
                    window[field+'_text'].update(visible = True)
                    window[field].update(visible = True)
                    if getattr(self, field) != None:
                        window[field].update(getattr(self, field))
                    else:
                        window[field].update("(empty)")
            # page 4: display if data upload is successful
            elif event == "NEXT" and step == 2:
                window['status'].update("")

                # turn off display for the previous page first
                window["prompt_auto_data"].update(visible = False)
                window["prompt_space_2"].update(visible = False)
                window["prompt_upload"].update(visible = False)
                for field in self.auto_fields:
                    window[field+'_text'].update(visible = False)
                    window[field].update(visible = False)

                # then turn on display for the data upload section
                window['prompt'].update("====STEP 3: DATA UPLOAD====")

                # attempt to upload data and display the result
                record = self._convert_to_record()
                try:
                    self.sf.Equipment__c.update(self.eid, record)
                    window["prompt_upload_success"].update(visible = True)
                except:
                    window['status'].update(f"Unexpected error, likely that record with CRID {self.CRID} is recently deleted from Salesforce")
                    window["prompt_upload_failure"].update(visible = True)

                # already on the last page, no more NEXT button
                window["NEXT"].update(visible = False)

def main():
    info = EquipmentInfo()

if __name__ == "__main__":
    main()
