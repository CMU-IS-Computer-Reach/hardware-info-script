import re
import subprocess

class EquipmentInfo():
    def __init__(self):               # description                     # type
        self.model_name = ""          # CPU model                         string
        self.RAM = -1                 # RAM size (GB)                     int
        self.screen_size = (-1, -1)   # Screen size (pixels)              (int, int)
        self.errors = dict()          # field -> errors during parsing    str -> str
        self.initialize()

    def initialize(self):
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
            output = subprocess.check_output("cat /proc/meminfo | numfmt --field 2 --from-unit=Ki --to-unit=Gi | sed 's/ kB/G/g' | grep 'MemTotal'",
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.errors["RAM"] = e.output if e.output else "`grep` didn't find match"
        else:
            try:
                r = re.match(r"\s*MemTotal\s*:\s*(\d*)G", output)
                self.RAM = int(r.group(1))
            except Exception as e:
                self.errors["RAM"] = str(e)

        # Screen size (pixels)
        try:
            output = subprocess.check_output("xdpyinfo | grep 'dimensions'",
                shell = True,
                text = True)
        except subprocess.CalledProcessError as e:
            self.errors["screen size"] = e.output
        else:
            try:
                r = re.match(r"\s*dimensions:\s*(\d*)x(\d*)\s*pixels.*", output)
                self.screen_size = (int(r.group(1)), int(r.group(2)))
            except Exception as e:
                self.errors["screen size"] = str(e)

    def print_errors(self):
        if len(self.errors):
            print("****PARSING ERRORS****")
        for field, err in self.errors.items():
            print(f"-{field}: {err}")

    def __str__(self):
        return ("model name: %s\nRAM(GB): %s\nscreen size(pixels): %sx%s" % (
                    self.model_name, 
                    self.RAM, 
                    self.screen_size[0],
                    self.screen_size[1]))    

def main():
    info = EquipmentInfo()
    print(info)
    info.print_errors()

if __name__ == "__main__":
    main()