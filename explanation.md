# Non-Technical Explanation

This is a non-technical explanation document of the script. It doesn't aim to be 100% technically accurate but to provide the minimal amount of information one needs to understand what this script does and how.

## Background Knowledge
- **operating system (OS)**: if a computer is a store and you are the customer then the OS is the manager of the store 
  - **Linux**: a free OS
  - **shell commands**: The language in which you talk to your OS. If you speak it correctly you can ask your OS to do and display magic things to you.
- **regular expression (regex)**: A way to describe or specify patterns of texts. For example, an SSN number often has this pattern: a group of 3 digits, followed by a hyphen, then a group of 2 digits, followed by another hyphen, and then a group of 4 digits.
  - **match**: When we say to "match a text against a regex (pattern)", we mean to check if the text follows a certain pattern. For example, 123-12-123 doesn't follow the above pattern.

## Goal of the Script
**What the script is trying to accomplish**: In our store-manager-customer analogy, currently we go to the store and look for everything we want ourselves. But it would have been easier and faster to just ask the manager to help us. In the actual context, we want to replace the manual work of checking hardware details of a computer, e.g. CPU model, how much storage it has, etc.

**How it does it**: Since the OS is the manager of a computer, it knows everything about it. So if we ask the OS correct questions, we can get the information we want. But we are also lazy, so we have this script to 1) do the talking for us, and 2) also upload the info to Salesforce.

## Code Structure
The [script](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/main/script.py) has one main class, `EquipmentInfo`, with four main functions:
1. **`__init__`**: housekeeping work such as connecting to Salesforce, also describes what information we are trying to collect and their data types
2. **`data_input`**: manual data input part, where user is asked to type in some information the script doesn't have access to
3. **`data_collection`**: automatic data collection part, where the script talks to the OS to get and parse hardware information
4. **`data_upload`**: data upload part, where the script uploads the collected information into the database in Salesforce

### `data_collection`
This function handles data collection. It has several sections, each of which aims to get one piece of information we need, as listed in the comment before each section.
Each section has three main steps:
1. **`output = subprocess.check_output(...)`**: send a (or a series of) shell command to the OS, and get the result
    1. The commands being run for these fields are stored in `AUTO_FIELDS_LINUX_COMMANDS`, defined at the start of the file; this is so that they can be examined and edited quickly
    2. What the commands mean in human language will be explained in a later section

2. **`except subprocess.CalledProcessError as e`**: if the OS told us it can't find the information we need, we note it down

3. **`else`**: the OS gives us the information, but in some cases we still need to clean it up a bit:
    1. **`r = re.match(...)`**: we check the result to see if it follows our expected format, by using regex
    2. **`self.xxx = r.group(...)`**: if the result follows the expected format, we extract the exact part we want from it. For example, 123-12-1234 follows the earlier "group of 3, hyphen, group of 2, hyphen, group of 4" pattern, but we are only interested in the last four digits, so we get the third group by doing `self.last4digits = r.group(3)`
    3. **`except Expection as e`**: if we ran into some random errors during data formatting, also note it down

### `data_upload`
This function handles data upload, with the following steps:
1. `self._display_info()`: displays all the information ready to be uploaded
2. `Upload to Salesforce? [y/n]:` asks the user to review and confirm if they want to proceed with the upload
3. `self._convert_to_record()`: if user chooses to proceed, converts the data into the desired JSON format
    1. This step exists because some fields in Salesforce of special types take in data of a special format. For example, a picklist/multi-select field, such as "what video ports are available on this laptop", on the Salesforce UI will just look like a bunch of pickboxes, but when uploading via a script we have to pass the data in a way that Salesforce can understand.
4. `self.sf.Equipment__c.update(...)`: updates the record in Salesforce with the corresponding CRID; this is done via a third-party library [SimpleSalesforce](https://simple-salesforce.readthedocs.io/en/latest/user_guide/record_management.html)

## Shell Commands Meaning

As mentioned earlier, in each section responsible for collecting one type of data, the very first step is to send a series of shell commands to the OS, which is the long string in `subprocess.check_output(...)`. All these commands are stored in `AUTO_FIELDS_LINUX_COMMANDS` for convenience.

### CPU model

1. **`cat /proc/cpuinfo`**: *every* Linux machine stores system information in a folder called `proc`, where there's a file called `cpuinfo` that stores, as the name suggests, CPU information. `cat` is used to display a file, so here we are asking the OS to display all CPU information that is stored in `/proc/cpuinfo`
    - example output:
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
    - example output:
```
model name      : Intel(R) Xeon(R) CPU E5-2660 0 @ 2.20GHz
```
(After getting the above, we use regex in the later steps to extract the actual name from it)

### RAM

1. **`cat /proc/meminfo`**: similar to above, the `proc` folder stores information about a computer's RAM as well, just in a different file `meminfo` (memory information)
    - example output:
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

### Storage

1. **`df -x tmpfs --total -BG`**: `df` shows free disc space of all the file systems on a device; `-x tmpfs` is used to exclude (`-x`) temporary file systems (`tmpfs`), which are part of virtual memory, not physical disk space; `--total` is displaying the sum of everything left; `-BG` means showing the numbers in gigabytes, converted in powers of 1024
    - example output:
```
Filesystem      Size     Used   Available   Use%   Mounted on
/dev/sda10      7.8G       1G        6.8G    13%   /home
/dev/sda1        30G       0G         30G     0%   /boot/efi
total          37.8G       1G       36.8G     3%   -
```
2. **`grep 'total'`**: take the last line showing the total space
3. **`awk '{print $2}'`**: take the second column which contains the total storage (used + free)

### Screen size

1. **`xrandr --current`**: `xrandr` displays information about monitors, `--current` means only show the monitors currently being used; since almost all devices we are working with (laptops) only has one connected monitor at the time of audit, we expect this command to get information about exactly one monitor
2. **`grep ' connected'`**: make sure the monitor is listed as "connected" - this is just a redundant safety check though
    - example output: `eDP-1 connected primary 3424x1926+0+0 (normal left inverted right x axis y axis) 310mm x 174mm`

(Screen size in our database is defined as the physical size of the screen, measured by the length of the diagonal in inches. So from the above, we later use regex to extract the last part, `310mm x 174mm`, and do the calculation from there.)

### Battery health

1. **``upower -i `upower -e | grep 'BAT'` ``**: `upower` displays information about power sources of a computer; ``-i \`upower -e | grep 'BAT'` `` means only shows battery information, since batteries are listed as files with `BAT` in its name in Linux (e.g. `/org/freedesktop/UPower/devices/battery_BAT0`)
    - example output:
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
