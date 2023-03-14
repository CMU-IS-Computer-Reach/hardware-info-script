import re
import subprocess
import argparse

# configurations
DEFAULT_FINAL_OS = "20.04_Xubuntu_Linux" # Salesforce API Name of the default final OS choice

description = """
A script that collects and parses hardware details and upload them to Salesforce.

Following fields are collected:
1) CPU model name
2) RAM size (in GB, power of 1024)
3) Storage size (in GB, power of 1024)
4) Battery capacity (%%)
5) All types of available video ports
6) Ethernet adapter existence (Y/N)
7) WiFi card existence (Y/N)
8) Final OS (default to {final_os})
""".format(final_os = DEFAULT_FINAL_OS)


class EquipmentInfo():
    def __init__(self):                  # description                     # type
        self.model_name = ""             # CPU model                         string
        self.RAM = -1                    # RAM size (GB)                     int
        self.storage = -1                # Storage size (GB)                 int
        self.screen_size = (-1, -1)      # Screen size (pixels)              (int, int)
        self.battery_health = -1         # Battery health (%)                float
        self.video_ports = set()         # Video ports                       set[str]
        self.has_ethernet = None         # Ethernet adapter (exists or not)  bool
        self.has_wifi = None             # Wifi card (exists or not)         bool
        self.final_os = None             # final OS                          str

        self.errors = dict()             # field -> errors during parsing    str -> str

        # command line arguments
        parser = argparse.ArgumentParser(description = description)
        parser.add_argument("-os", "--final-os", help = f"Specify final OS (default to {DEFAULT_FINAL_OS})", default = DEFAULT_FINAL_OS)
        self.args = parser.parse_args()

        self.data_collection()

    def data_collection(self):
        # TODO: run sudo apt install hardinfo and hwinfo maybe?

        # CPU model
        try:
            output = subprocess.check_output("cat /proc/cpuinfo | grep 'model name'", 
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.errors["model name"] = e.output if e.output else "`grep` didn't find match"
        else:
            try:
                r = re.match(r"\s*model name\s*:\s*(.*)", output)
                self.model_name = r.group(1)
            except Expection as e:
                self.errors["model name"] = str(e)

        # RAM size (GB)
        try:
            output = subprocess.check_output("cat /proc/meminfo | numfmt --field 2 --from-unit=Ki --to-unit=Gi | sed 's/ kB/G/g' | grep 'MemTotal' | awk '{print $2}'",
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.errors["RAM"] = e.output if e.output else "`grep` didn't find match"
        else:
            try:
                r = re.match(r"(\d*)G", output)
                self.RAM = int(r.group(1))
            except Exception as e:
                self.errors["RAM"] = str(e)
        
        # Storage size (GB) # TODO: -H (1000 based) or -BG (1024 based)? system monitor is 1000 based
        try:
            output = subprocess.check_output("df -x tmpfs --total -BG | grep 'total' | awk '{print $2}'",
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.errors["storage"] = e.output if e.output else "`grep` didn't find match"
        else:
            try:
                r = re.match(r"(\d*)G", output)
                self.storage = int(r.group(1))
            except Exception as e:
                self.errors["storage"] = str(e)

        # Screen size (pixels)
        try:
            output = subprocess.check_output("xrandr --current | grep '*' | awk '{print $1}'",
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.errors["screen size"] = e.output if e.output else "`grep` didn't find match"
        else:
            try:
                r = re.match(r"(\d*)x(\d*)", output)
                self.screen_size = (int(r.group(1)), int(r.group(2)))
            except Exception as e:
                self.errors["screen size"] = str(e)
                
        # Battery health (%)
        try:
            output = subprocess.check_output("upower -i `upower -e | grep 'BAT'` | grep 'capacity' | awk '{print $2}' | grep .",
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.errors["battery health"] = e.output if e.output else "`grep` didn't find match"
        else:
            try:
                r = re.match(r"([\d\.]*)%", output)
                self.battery_health = float(r.group(1))
            except Exception as e:
                self.errors["battery health"] = str(e)
        
        # Video ports # TODO: lspci or this? see https://unix.stackexchange.com/a/489712, also need to further convert output
        try:
            output = subprocess.check_output("find /sys/devices -name 'edid' | grep .",
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.errors["video ports"] = e.output if e.output else "`find` didn't find match"
        else:
            for line in output.strip().split("\n"):
                try:
                    r = re.match(r".*/drm/card\d+/card\d+-([^-]*).*/edid", line)
                    self.video_ports.add(r.group(1))
                except Exception as e:
                    self.errors["video ports"] = str(e)

        # Ethernet
        try:
            output = subprocess.check_output("lspci | grep 'ethernet' -i",
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_ethernet = False
        else:
            self.has_ethernet = True

        # WiFi (https://help.ubuntu.com/stable/ubuntu-help/net-wireless-troubleshooting-hardware-check.html.en)
        try:
            output = subprocess.check_output("lspci | grep 'network|wireless' -i",
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.has_wifi = False
        else:
            self.has_wifi = True

        # Final OS
        self.final_os = self.args.final_os
                

    def print_errors(self):
        if len(self.errors):
            print("****PARSING ERRORS****")
        for field, err in self.errors.items():
            print(f"-{field}: {err}")

    def __str__(self):
        return "model name: {}\nRAM(GB): {}\nstorage(GB): {}\nscreen size(pixels): {}x{}\nbattery health: {}%\nvideo ports: {}\nhas ethernet?: {}\nhas wifi?: {}\nfinal OS: {}\n".format(
            self.model_name, 
            self.RAM, 
            self.storage,
            self.screen_size[0],
            self.screen_size[1],
            self.battery_health,
            self.video_ports,
            self.has_ethernet,
            self.has_wifi,
            self.final_os
        )

def main():
    info = EquipmentInfo()
    print(info)
    info.print_errors()

if __name__ == "__main__":
    main()
