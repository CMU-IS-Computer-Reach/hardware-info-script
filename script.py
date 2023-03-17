import re
import subprocess
import argparse

# configurations
FINAL_OS_OPTIONS = ["20.04_Xubuntu_Linux", "Win 10", "Chrome OS"] # Salesforce API Name of all final OS options
VIDEO_PORT_OPTIONS = ["VGA", "DVI", "HDMI", "Mini-HDMI", "Display Port", "Mini-Display"] # Salesforce API Name of all video ports options

description = """
A script that collects and parses hardware details and upload them to Salesforce.

Following fields are collected:
TODO!!!
"""

# Linux commands ran for each field
LINUX_COMMANDS = {
    "model_name":       ["cat /proc/cpuinfo", "grep 'model name'"],
    "RAM":              ["cat /proc/meminfo", "numfmt --field 2 --from-unit=Ki --to-unit=Gi", "sed 's/ kB/G/g'", "grep 'MemTotal'", "awk '{print $2}'"],
    "storage":          ["df -x tmpfs --total -BG", "grep 'total'", "awk '{print $2}'"],
    "screen_size":      ["xrandr --current", "grep ' connected'"],
    "battery_health":   ["upower -i `upower -e | grep 'BAT'`", "grep 'capacity'", "awk '{print $2}'", "grep ."],
    "has_ethernet":     ["lspci", "grep 'ethernet' -i"],
    "has_wifi":         ["lspci", "grep 'network|wireless' -i -E"],
    "has_optical_drive":["dmesg", "grep 'cdrom|cd-rom|dvd' -i -E"],
    "has_touchscreen":  ["xinput list", "grep 'touchscreen' -i"],
}



class EquipmentInfo():
    def __init__(self):                  # description                     # type
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

        self.CRID = None                 # CRID                              str
        self.has_webcam = None           # Webcam (exists or not)            bool
        self.video_ports = None          # Video ports                       set(str)
        self.num_usb_ports = None        # Number of USB ports               int
        self.adapter_watts = None        # Adapter Watts                     str
        self.final_os = None             # final OS                          str

        self._errors = dict()             # field -> errors during parsing    str -> str

        # command line arguments
        # parser = argparse.ArgumentParser(description = description)
        # parser.add_argument("-os", "--final-os", help = f"Specify final OS (default to {DEFAULT_FINAL_OS})", default = DEFAULT_FINAL_OS)
        # self._args = parser.parse_args()

        self.data_input()
        self.data_collection()
        self.data_upload()

    def data_input(self):
        print()
        print("\033[104m***Manual Data Entry Section***\033[00m")
        print("\033[93mAfter each prompt, enter value and press ENTER, or directly press ENTER to skip\033[00m")
        cnt = len(VIDEO_PORT_OPTIONS) + 5
        i = 1
        
        self.CRID = input(f" ({i:02d}/{cnt}) Enter CRID: ")
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
                    self.video_ports.add(port)
                    break
                elif p == "n":
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

        self.adapter_watts = input(f" ({i:02d}/{cnt}) Enter adpater watts:")
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
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["model_name"]), 
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self._errors["model name"] = e.output if e.output else "`grep` didn't find match (unexpected /proc/cpuinfo file format)"
        else:
            try:
                r = re.match(r"\s*model name\s*:\s*(.*)", output)
                self.model_name = r.group(1)
            except Expection as e:
                self._errors["model name"] = "regex matching error (unexpected /proc/cpuinfo file format)"

        # RAM size (GB)
        try:
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["RAM"]),
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
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["storage"]),
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
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["screen_size"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self._errors["screen size"] = e.output if e.output else "`grep` didn't find match (`xrandr` cannot find current display device)"
        else:
            try:
                output = "eDP-1 connected primary 3424x1926+0+0 (normal left inverted right x axis y axis) 310mm x 174mm"
                r = re.match(r".*\s+(\d+)mm\s+x\s+(\d+)mm", output)
                w = int(r.group(1))
                h = int(r.group(2))
                diagonal = (w * w + h * h) ** 0.5
                self.screen_size = round(diagonal / 25.4)
            except Exception as e:
                self._errors["screen size"] = "regex matching error (unexpected output format from `xrandr`)"
                
        # Battery health (%)
        try:
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["battery_health"]),
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
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["has_ethernet"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_ethernet = False
        else:
            self.has_ethernet = True

        # WiFi
        try:
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["has_wifi"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_wifi = False
        else:
            self.has_wifi = True

        # Optical drive
        try:
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["has_optical_drive"]),
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_optical_drive = False
        else:
            self.has_optical_drive = True

        # Touchscreen
        try:
            output = subprocess.check_output((" | ").join(LINUX_COMMANDS["has_touchscreen"]),
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
        print("\033[93mAny fields not shown above will be empty; update them in Salesforce manually if necessary.\033[00m")
        while True:
            print()
            res = input(f"\033[43mUpload to Salesforce? [y/n]: \033[00m").lower()
            if res == "y":
                # TODO
                print("\033[92mData uploaded successfully!\033[00m")
                break
            elif res == "n":
                print("\033[90mData not uploaded.\033[00m")
                break
            elif res == "":
                print("\033[90mData not uploaded.\033[00m")
                break
            else:
                print("\033[91m  Please enter a valid option [y/n], or ENTER to skip\033[00m")

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
        if self.CRID:
            print(f" - CRID:               {self.CRID}")
        if self.has_webcam != None:
            print(f" - has webcam?:        {self.has_webcam}")
        if self.video_ports:
            print(f" - video ports:        {self.video_ports}")
        if self.num_usb_ports != None:
            print(f" - # USB ports:        {self.num_usb_ports}")
        if self.adapter_watts:
            print(f" - adapater watts:     {self.adapter_watts}")
        if self.final_os:
            print(f" - final OS:           {self.final_os}")

        print("\033[92m Below fields are successfully collected:\033[00m")
        if self.serial_number:
            print(f" - serial number:      {self.serial_number}")
        if self.model_name:
            print(f" - model name:         {self.model_name}")
        if self.RAM:
            print(f" - RAM (GB):           {self.RAM}")
        if self.storage:
            print(f" - storage (GB):       {self.storage}")
        if self.screen_size:
            print(f" - screen size (inch): {self.screen_size}")
        if self.battery_health:
            print(f" - battery health (%): {self.battery_health}")
        if self.has_ethernet != None:
            print(f" - has ethernet?:      {self.has_ethernet}")
        if self.has_wifi != None:
            print(f" - has wifi?:          {self.has_wifi}")
        if self.has_optical_drive != None:
            print(f" - has optical drive?: {self.has_optical_drive}")
        if self.has_touchscreen != None:
            print(f" - has touchscreen?:   {self.has_touchscreen}")

        print("\033[92m Below fields are not collected and will be empty:\033[00m")
        if self.CRID == None:
            print(f" - CRID")
        if self.has_webcam == None:
            print(f" - has webcam?")
        if self.video_ports == None:
            print(f" - video ports")
        if self.num_usb_ports == None:
            print(f" - # USB ports")
        if self.adapter_watts == None:
            print(f" - adapater watts")
        if self.final_os == None:
            print(f" - final OS")
        if self.serial_number == None:
            print(f" - serial number")
        if self.model_name == None:
            print(f" - model name")
        if self.RAM == None:
            print(f" - RAM (GB)")
        if self.storage == None:
            print(f" - storage (GB)")
        if self.screen_size == None:
            print(f" - screen size (inch)")
        if self.battery_health == None:
            print(f" - battery health (%)")
        if self.has_ethernet == None:
            print(f" - has ethernet?")
        if self.has_wifi == None:
            print(f" - has wifi?")
        if self.has_optical_drive == None:
            print(f" - has optical drive?")
        if self.has_touchscreen == None:
            print(f" - has touchscreen?")

def main():
    info = EquipmentInfo()

if __name__ == "__main__":
    main()
