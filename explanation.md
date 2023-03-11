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
The [script](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/main/script.py) has one main class, `EquipmentInfo`, with three main functions:
1. **[`__init__`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L5)**: housekeeping work, also describes what information we are trying to collect and their data types
2. **[`initialize`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L14)**: the data collection part, where the script talks to the OS to get and parse hardware information
3. **`upload`**: the data upload part, where the script uploads the collected information into the database in Salesforce

### `initialize`
This function handles data collection. It has several sections, each of which aims to get one piece of information we need, as listed in the comment before each section.
Each section does three main steps:
1. **[`output = subprocess.check_output(...)`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L16-L20)**: send a (or a series of) shell command to the OS, and get the result
    1. What the commands mean in human language will be explained in a later section

2. **[`except subprocess.CalledProcessError as e`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L21-L22)**: if the OS told us it can't find the information we need, we note it down

3. **[`else`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L23-L24)**: the OS gives us the information, but we still need to clean it up a bit:
    1. **[`r = re.match(...)`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L25)**: we check the result to see if it follows our expected format, by using regex
    2. **[`self.xxx = r.group(...)`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L26)**: if the result follows the expected format, we extract the exact part we want from it. For example, 123-12-1234 follows the earlier "group of 3, hyphen, group of 2, hyphen, group of 4" pattern, but we are only interested in the last four digits, so we get the third group by doing `self.last4digits = r.group(3)`
    3. **[`except Expection as e`](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L27-L28)**: if we ran into some random errors during data formatting, also note it down

### `upload`
TODO: this function hasn't been implemented yet

## Shell Commands Meaning

As mentioned earlier, in each section responsible for collecting one type of data, the very first step is to send a series of shell commands to the OS, which is the long string in `subprocess.check_output(...)`

In the shell command string, `|` means multiple steps, so `subprocess.check_output("step a | step b | step c")` means do step a, then step b based on step a's result, then step c based on step b's result

### [CPU model](https://github.com/CMU-IS-Computer-Reach/hardware-info-script/blob/4c29fd71c42c632ef6aff0ac6c5c7701bf59b7cf/script.py#L15-L17)

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
