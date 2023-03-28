import os
import sys
import re
import subprocess
import argparse
from simple_salesforce import Salesforce

description = """
A script that collects and parses hardware details and upload them to Salesforce.

Following fields are asked to be manually input:
- CRID
- Webcam
- Video ports
- # USB ports
- Adapter watts
- Final OS

Following fields are automatically collected:
- CPU model
- RAM
- Storage
- Screen size
- Battery health
- Ethernet
- Wifi
- Optical drive
- Touchscreen
"""

# Salesforce API name for all the fields to be uploaded
ALL_FIELDS_API_NAMES = {
    "CRID":                 "Computer_Reach_ID__c",
    "has_webcam":           "Webcam_present__c",
    "video_ports":          "Video__c",
    "num_usb_ports":        "USB__c",
    "adapter_watts":        "Adapter_Watts__c",
    "final_os":             "Final_Operating_System__c",
    "serial_number":        "Serial_Number__c",
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

# Fields that are asked to be manually input
MANUAL_FIELDS = ["CRID", "has_webcam", "video_ports", "num_usb_ports", "adapter_watts", "final_os"]
# Configurations for some manual fields for convenience
FINAL_OS_OPTIONS = ["20.04_Xubuntu_Linux", "Win 10", "Chrome OS"] # Salesforce API Name of all final OS options
VIDEO_PORT_OPTIONS = ["VGA", "DVI", "HDMI", "Mini-HDMI", "Display Port", "Mini-Display"] # Salesforce API Name of all video ports options

# Fields that will be automatically collected
AUTO_FIELDS = ["serial_number", "model_name", "RAM", "storage", "screen_size", "battery_health", "has_ethernet", "has_wifi", "has_optical_drive", "has_touchscreen"]
# Linux commands used to automatically collect a field
AUTO_FIELDS_LINUX_COMMANDS = {
    "model_name":           ["cat /proc/cpuinfo", "grep 'model name'"],
    "RAM":                  ["cat /proc/meminfo", "numfmt --field 2 --from-unit=Ki --to-unit=Gi", "sed 's/ kB/G/g'", "grep 'MemTotal'", "awk '{print $2}'"],
    "storage":              ["df -x tmpfs --total -BG", "grep 'total'", "awk '{print $2}'"],
    "screen_size":          ["xrandr --current", "grep ' connected'"],
    "battery_health":       ["upower -i `upower -e | grep 'BAT'`", "grep 'capacity'", "awk '{print $2}'", "grep ."],
    "has_ethernet":         ["lspci", "grep 'ethernet' -i"],
    "has_wifi":             ["lspci", "grep 'network|wireless' -i -E"],
    "has_optical_drive":    ["dmesg", "grep 'cdrom|cd-rom|dvd' -i -E"],
    "has_touchscreen":      ["xinput list", "grep 'touchscreen' -i"],
}


class EquipmentInfo():
    def __init__(self):                  # description                     # type
        # manually entered fields
        self.CRID = None                 # CRID                              str
        self.has_webcam = None           # Webcam (exists or not)            bool
        self.video_ports = None          # Video ports                       list(str)
        self.num_usb_ports = None        # Number of USB ports               int
        self.adapter_watts = None        # Adapter Watts                     str
        self.final_os = None             # final OS                          str
        
        # automatically collected fields
        self.serial_number = None        # Serial number                     str
        self.model_name = None           # CPU model                         str
        self.RAM = None                  # RAM size (GB)                     int
        self.storage = None              # Storage size (GB)                 int
        self.screen_size = None          # Screen size (inch)                int
        self.battery_health = None       # Battery health (%)                float
        self.has_ethernet = None         # Ethernet adapter (exists or not)  bool
        self.has_wifi = None             # Wifi card (exists or not)         bool
        self.has_optical_drive = None    # Optical drive (exists or not)     bool
        self.has_touchscreen = None      # Touchscreen (exists or not)       bool

        self._errors = dict()            # field -> errors during parsing    str -> str
        self.eid = None                  # Salesforce id

        # Salesforce authentication
        self.sf = Salesforce(
            username = os.getenv("SF_BENCH_USERNAME"), 
            password = os.getenv("SF_BENCH_PASSWORD"), 
            security_token = os.getenv("SF_BENCH_TOKEN"),
            client_id='Hardware Info Script',
            domain='test', # TODO: testing on Sandbox,
        )

        # command line arguments
        parser = argparse.ArgumentParser(description = description)
        parser.add_argument("-t", "--test", action='store_true', help="test the script on Salesforce Sandbox")
        self._args = parser.parse_args()

        self.data_input()
        self.data_collection()
        self.data_upload()

    def data_input(self):
        print()
        print("\033[104m***Manual Data Entry Section***\033[00m")
        print("\033[93mAfter each prompt, enter value and press ENTER, or directly press ENTER to skip\033[00m")
        cnt = len(VIDEO_PORT_OPTIONS) + 5
        i = 1

        while True:
            cr = input(f" ({i:02d}/{cnt}) [REQUIRED] Enter CRID: ")
            if not cr:
                print("\033[91m  CRID is required\033[00m")
            else:
                try:
                    self.eid = self.sf.Equipment__c.get_by_custom_id(ALL_FIELDS_API_NAMES["CRID"], cr)['Id']
                    self.CRID = cr
                    break
                except:
                    print(f"\033[91m  There is no record with CRID {self.CRID} in Salesforce, please double check and reenter\033[00m")
                    print("\033[93m  (if you are trying to create a new equipment record, please add it from Salesforce UI first)\033[00m")
        i += 1
        
        while True:
            webcam = input(f" ({i:02d}/{cnt}) Webcam presents? [y/n]: ").lower()
            if webcam == "y":
                self.has_webcam = True
                break
            elif webcam == "n":
                self.has_webcam = False
                break
            elif webcam == "":
                break
            else:
                print("\033[91m  Please enter a valid option [y/n], or ENTER to skip\033[00m")
        i += 1

        for port in VIDEO_PORT_OPTIONS:
            while True:
                p = input(f" ({i:02d}/{cnt}) {port} port presents? [y/n]: ").lower()
                if p == "y":
                    if not self.video_ports:
                        self.video_ports = []
                    self.video_ports.append(port)
                    break
                elif p == "n":
                    if not self.video_ports:
                        self.video_ports = []
                    break
                elif p == "":
                    break
                else:
                    print("\033[91m  Please enter a valid option [y/n], or ENTER to skip\033[00m")
            i +=1

        while True:
            usb = input(f" ({i:02d}/{cnt}) Enter # USB ports: ")
            if not usb:
                break
            try:
                self.num_usb_ports = int(usb)
                break
            except ValueError:
                print("\033[91m  Please enter a valid integer, or ENTER to skip\033[00m")
        i += 1

        watts = input(f" ({i:02d}/{cnt}) Enter adpater watts: ")
        if watts:
            self.adapter_watts = watts
        i += 1

        while True:
            choices = ""
            for j, opt in enumerate(FINAL_OS_OPTIONS):
                choices += "  [{}] {}\n".format(j+1, opt)
            os = input(f" ({i:02d}/{cnt}) Choose an option for final OS, or ENTER to skip:\n{choices} *choice: ")
            if not os:
                break
            try:
                if int(os) < 1:
                    raise ValueError
                self.final_os = FINAL_OS_OPTIONS[int(os)-1]
                break
            except:
                print("\033[91m  Please enter a valid integer option, or ENTER to skip\033[00m")
    
        print()

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
        
        # Storage size (GB) 
        # NOTE: -BG means converting size to GB in powers of 1024; change to -H if powers of 1000 is desired instead
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["storage"]),
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self._errors["storage"] = e.output if e.output else "`grep` didn't find match (unexpected output format from `df`)"
        else:
            try:
                r = re.match(r"(\d+)G", output)
                self.storage = int(r.group(1))
            except Exception as e:
                self._errors["storage"] = "regex matching error (unexpected output format from `df`)"

        # Screen size (inch)
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS["screen_size"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self._errors["screen size"] = e.output if e.output else "`grep` didn't find match (`xrandr` cannot find current display device)"
        else:
            try:
                # output = "eDP-1 connected primary 3424x1926+0+0 (normal left inverted right x axis y axis) 310mm x 174mm"
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
                self.battery_health = float(r.group(1))
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
        
    def data_upload(self):
        print("\033[104m***Data Upload Section***\033[00m")
        print("\033[93m!!!Please carefully review the data to be uploaded first!!!\033[00m")
        self._display_info()
        print()
        while True:
            res = input(f"\033[44mUpload to Salesforce? [y/n]: \033[00m").lower()
            if res == "y":
                record = self._convert_to_record()
                try:
                    self.sf.Equipment__c.update(self.eid, record)
                    print("\033[92mData uploaded successfully! See below for details:\033[00m")
                    print(f" ***CRID: {self.CRID}***")
                    print(f" Fields updated:")
                    for k, v in record.items():
                        if k != ALL_FIELDS_API_NAMES["CRID"]:
                            print(f"  {k:<25}: {v}")
                except:
                    print(f"\033[91mUnexpected error, likely that the record with CRID {self.CRID} is recently deleted from Salesforce\033[00m")
                    print("\033[90mData not uploaded.\033[00m")
                finally:
                    break
            elif res == "n":
                print("\033[90mData not uploaded.\033[00m")
                break
            else:
                print("\033[91m  Please enter a valid option [y/n]\033[00m")

    def _display_errors(self):
        if len(self._errors):
            print("\033[91mBelow error occured when running Linux commands:\033[00m")
            for field, err in self._errors.items():
                print(f"\033[91m - {field}: {err}\033[00m")
        else:
            print("\033[92mNo error occured; all commands returned successfully\033[00m")
        print()
        
    def _display_info(self):
        print("\033[92m Below fields are input manually:\033[00m")
        for field in MANUAL_FIELDS:
            var = getattr(self, field)
            if var != None:
                print(f" - {field:<20}: {var}")
            
        print("\033[92m Below fields are successfully collected:\033[00m")
        for field in AUTO_FIELDS:
            var = getattr(self, field)
            if var != None:
                print(f" - {field:<20}: {var}")
        
        print("\033[93m Below fields are not collected and will be empty: (update them in Salesforce manually if necessary)\033[00m")
        for field in ALL_FIELDS_API_NAMES:
            if getattr(self, field) == None:
                print(f" - {field}")

    def _convert_to_record(self):
        record = dict()
        
        for field in ALL_FIELDS_API_NAMES:
            var = getattr(self, field)
            if var != None:
                if field == "video_ports": # this is a picklist (multi-select) field in Salesforce, so data should be in the format of "selection1;selection;..."
                    var = ";".join(var)
                record[ALL_FIELDS_API_NAMES[field]] = var

        return record

def main():
    valid = True
    if not os.getenv("SF_BENCH_USERNAME"):
        print(f"\033[91mPlease make sure environment variable SF_BENCH_USERNAME is set\033[00m")
        valid = False
    if not os.getenv("SF_BENCH_PASSWORD"):
        print(f"\033[91mPlease make sure environment variable SF_BENCH_PASSWORD is set\033[00m")
        valid = False
    if not os.getenv("SF_BENCH_TOKEN"):
        print(f"\033[91mPlease make sure environment variable SF_BENCH_TOKEN is set\033[00m")
        valid = False
    if not valid:
        sys.exit(1)

    info = EquipmentInfo()

if __name__ == "__main__":
    main()
