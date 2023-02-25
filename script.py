import re
import subprocess

class EquipmentInfo():
    def __init__(self):
        self.model_name = ""          # CPU model, string
        self.RAM = -1                 # RAM size (GB), int
        self.screen_size = (-1, -1)   # Screen size (pixels), (int, int)
        self.initialize()

    def initialize(self):
        # CPU model
        output = subprocess.check_output("cat /proc/cpuinfo | grep 'model name'", 
            shell = True,
            text = True)
        r = re.match(r"\s*model name\s*:\s*(.*)", output)
        if r:
            self.model_name = r.group(1)

        # RAM size (GB)
        output = subprocess.check_output("cat /proc/meminfo | numfmt --field 2 --from-unit=Ki --to-unit=Gi | sed 's/ kB/G/g' | grep 'MemTotal'",
            shell = True,
            text = True)
        r = re.match(r"\s*MemTotal\s*:\s*(\d*)G", output)
        if r:
            self.RAM = int(r.group(1))

        # Screen size (pixels)
        output = subprocess.check_output("xdpyinfo | grep 'dimensions'",
            shell = True,
            text = True)
        r = re.match(r"\s*dimensions:\s*(\d*)x(\d*)\s*pixels.*", output)
        if r:
            self.screen_size = (int(r.group(1)), int(r.group(2)))

    def __str__(self):
        return ("model name: %s\nRAM(GB): %s\nscreen size(pixels): %sx%s" % (
                    self.model_name, 
                    self.RAM, 
                    self.screen_size[0],
                    self.screen_size[1]))    

def main():
    info = EquipmentInfo()
    print(info)

if __name__ == "__main__":
    main()