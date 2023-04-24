# Linux Commands Explanations

This document explains all Linux shell commands being used in the script for automatic data collection. For a more detailed walkthrough of other parts of the code, refer to [this video](https://www.youtube.com/watch?v=Rg_dFDKNYLg)

## `data_collection` structure
This function handles all the automatic data collection. It has several sections, each of which aims to get one piece of information we need, as listed in the comment before each section.
Each section has three main steps:
1. **`output = subprocess.check_output(...)`**: send a (or a series of) shell command to the OS, and get the result
    1. The commands being run for these fields are stored in `AUTO_FIELDS_LINUX_COMMANDS`, defined at the start of the file; this is so that they can be examined and edited quickly
    2. What the commands mean in human language will be explained in a later section

2. **`except subprocess.CalledProcessError as e`**: if the OS told us it can't find the information we need, we note it down

3. **`else`**: the OS gives us the information, but in some cases we still need to clean it up a bit:
    1. **`r = re.match(...)`**: we check the result to see if it follows our expected format, by using regex
    2. **`self.xxx = r.group(...)`**: if the result follows the expected format, we extract the exact part we want from it. For example, 123-12-1234 follows the earlier "group of 3, hyphen, group of 2, hyphen, group of 4" pattern, but we are only interested in the last four digits, so we get the third group by doing `self.last4digits = r.group(3)`
    3. **`except Expection as e`**: if we ran into some random errors during data formatting, also note it down

## shell commands meaning

As mentioned earlier, in each section responsible for collecting one type of data, the very first step is to send a series of shell commands to the OS, which is the long string in `subprocess.check_output(...)`. All these commands are stored in `AUTO_FIELDS_LINUX_COMMANDS` for convenience.

### CPU model

1. **`cat /proc/cpuinfo`**: *every* Linux machine stores system information in a folder called `proc`, where there's a file called `cpuinfo` that stores, as the name suggests, CPU information. `cat` is used to display a file, so here we are asking the OS to display all CPU information that is stored in `/proc/cpuinfo`
    - sample output:
```
processor       : 0
vendor_id       : GenuineIntel
cpu family      : 6
model           : 45
model name      : Intel(R) Xeon(R) CPU E5-2660 0 @ 2.20GHz
stepping        : 6
microcode       : 1561
cpu MHz         : 600.000
cache size      : 20480 KB
physical id     : 0
siblings        : 16
core id         : 0
cpu cores       : 8
...
```
2. **`grep 'model name'`**: step 1 gives us a lot of information, but the only thing we need is the CPU model name. `grep` is used to filter the file by the given search string, so here we only keep the line with "model name" in it
    - sample output:
```
model name      : Intel(R) Xeon(R) CPU E5-2660 0 @ 2.20GHz
```
(After getting the above, we use regex in the later steps to extract the actual name from it)

### RAM

1. **`cat /proc/meminfo`**: similar to above, the `proc` folder stores information about a computer's RAM as well, just in a different file `meminfo` (memory information)
    - sample output:
```
MemTotal:        1882064 kB
MemFree:         1376380 kB
MemAvailable:    1535676 kB
Buffers:            2088 kB
Cached:           292324 kB
...
```
2. **`numfmt --field 2 --from-unit=Ki --to-unit=Gi`**: as shown above, the data is displayed in kilobytes, so we use `numfmt` (number formatter) to convert every number from kilobytes to gigabytes, which is the unit used in our database
3. **`sed 's/ kB/G/g'`**: this step is dispensible, as it's simply replacing the string "kB" to "G" to indicate the correct unit after the above conversion
4. **`grep 'MemTotal'`**: the only information we need is the total memory, listed in the line starting with `MemTotal`
5. **`awk '{print $2}'`**: take the second "column" of the line we selected above, which contains the number; columns are just strings as separated by spaces

### Screen size

1. **`xrandr --current`**: `xrandr` displays information about monitors, `--current` means only show the monitors currently being used; since almost all devices we are working with (laptops) only has one connected monitor at the time of audit, we expect this command to get information about exactly one monitor
2. **`grep ' connected'`**: make sure the monitor is listed as "connected" - this is just a redundant safety check though
    - sample output: `eDP-1 connected primary 3424x1926+0+0 (normal left inverted right x axis y axis) 310mm x 174mm`

(Screen size in our database is defined as the physical size of the screen, measured by the length of the diagonal in inches. So from the above, we later use regex to extract the last part, `310mm x 174mm`, and do the calculation from there.)

### Battery health

1. **``upower -i `upower -e | grep 'BAT'` ``**: `upower` displays information about power sources of a computer; ``-i \`upower -e | grep 'BAT'` `` means only shows battery information, since batteries are listed as files with `BAT` in its name in Linux (e.g. `/org/freedesktop/UPower/devices/battery_BAT0`)
    - sample output:
```
Device: /org/freedesktop/UPower/devices/battery_BAT0
  native-path:          BAT0
  battery
    present:             yes
    rechargeable:        yes
    state:               fully-charged
    energy:              954.6 Wh
    energy-empty:        0 Wh
    energy-full:         957 Wh
    energy-full-design:  980 Wh
    energy-rate:         9.2056 W
    capacity:            97.7%
...
```
2. **`grep 'capacity'`**: take the battery capacity, defined and calculated as the ratio between `energy-full` (maximum energy the battery can have now) and `energy-full-design` (max energy the battery is designed to be able to have)
3. **`awk '{print $2}'`**: take the second column, which contains the number
4. **`grep .`**: this step is just for easier error handling when a battery is not found

### Ethernet

1. **`lspci`**: this command displays all the devices connected to PCI buses - which the ethernet controller is (usually) connected to
    - sample output:
```
00:01.1 IDE interface: Intel Corporation 82371AB/EB/MB PIIX4 IDE (rev 01)
00:02.0 VGA compatible controller: VMware SVGA II Adapter
00:03.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet Controller (rev 02)
...
```
2. **`grep 'ethernet' -i`**: the ethernet controller, if exists, is (usually) named "ethernet controller" (see above example), so we look for the word "ethernet" (`-i` means case insentitive) to determine if ethernet exists
3. **`grep .`**: again, this is for easier error handling when the ethernet controller is not found

### WiFi

1. **`lspci`**: same as ethernet, wifi controller is also (usually) connected to PCI buses
2. **`grep 'network|wireless' -i -E`**: what makes this slightly different from above is that wifi controller, if exists, can show up under different names, but they are usually either called "network controller" or contain the word "wireless" in its name, so we look for either of the two keywords (`-E` means searching by a regex pattern)
    - sample output: `0000:0e:00.0 Network controller: Realtek Semiconductor Co., Ltd. RTL8187SE Wireless LAN Controller (rev 22)`
3. **`grep .`**: same as above

### Optical Drive

1. **`dmesg`**: this command is used to examine Linux kernel riong buffer - in other words, it displays information related to device drivers, hardware devices, etc.
2. **`grep 'cdrom|cd-rom|dvd' -i -E`**: optical drive, if exists, usually shows up with one of these keywords (cdrom/dvd) in its name
    - sample output: `[    5.437307] cdrom: Uniform CD-ROM driver Revision: 3.20`
3. **`grep .`**: same as above

### Touchscreen

1. **`xinput`**: this commands show information about input devices, such as keyboard, mouse, touchscreen, touchpad, etc.
    - sample output:
```
⎡ Virtual core pointer                    	id=2	[master pointer  (3)]
⎜   ↳ Virtual core XTEST pointer              	id=4	[slave  pointer  (2)]
⎜   ↳ DELL0ABC:DE F123:4567 Mouse             	id=9	[slave  pointer  (2)]
⎜   ↳ DELL0ABC:DE F123:4567 Touchpad          	id=10	[slave  pointer  (2)]
⎜   ↳ PS/2 Generic Mouse                      	id=16	[slave  pointer  (2)]
```
2. **`grep 'touchscreen' -i`**: same logic as above - we just search for the keyword "touchscreen"
3. **`grep .`**: same as above
