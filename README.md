# hardware-info-script
A script to get hardware info and upload to Salesforce. Only Linux is supported currently.

The script has two versions:
1. command line: runs in Linux terminal without GUI, fully developed
2. GUI: spins up a GUI; currently only a proof-of-concept - missing some important functionalities

## Usage
(You can also refer to this video for a walkthrough.)
1. Make sure Python3 is installed: `python3 --version`
    1. If not, install with `sudo apt install python3.8`
2. If you want to run the GUI version, make sure `tkinter` is installed: `python3 -m tkinter`
    1. If not, install with `sudo apt-get install python3-tk`
3. Make sure the dependencies is installed (**this only needs to be run once**): `pip install -r requirements.txt`
4. Make sure the following **environment variables** are set/up-to-date (add `export NAME=VALUE` to your `~/.bashrc` file, and then run `source ~/.bashrc`, and then restart terminal):
    1. `SF_BENCH_USERNAME`: Salesforce username of the account used for auditing devices
    2. `SF_BENCH_PASSWORD`: password
    3. `SF_BENCH_TOKEN`: security token ([how to find it](https://help.salesforce.com/s/articleView?id=sf.user_security_token.htm&type=5))
5. To run the command line version: `python3 <path to script.py> -c`
    1. You will be asked to enter the **CRID** of the device you are auditing; this CRID must already exist in Salesforce (if not, create a record for it via Salesforce UI first)
    2. You will then be prompted to manually input some fields (see next section)
    3. The script then automatically collects some other fields (see next section)
        - Any errors that occured will be displayed
        - If you are just using the script, you can ignore the errors, but keep in mind that those fields will be empty in Salesforce
        - If you are the maintainer of the script, run the Linux command for fields that failed and examine the output to determine if it needs to be fixed
    4. The script then displays all fields and allows you to select any field you want to modify
    5. Once done with modification, you can choose whether or not to upload the data to Salesforce
        - **REVIEW IT BEFORE PROCEEDING**

## Fields Collected

### fields asked to be manually input
- CRID
- Webcam
- Video ports
- \# USB ports
- Adapter watts
- Final OS
- Storage

### fields automatically collected
See `ALL_FIELDS_API_NAMES` for the Linux commands run for each field
- CPU model
- RAM
- Screen size
- Battery health
- Ethernet
- Wifi
- Optical drive
- Touchscreen

## Maintenance 

`script.py` is comprehensively documentated with instructions on how to maintain and/or extend the script to include new fields or modify existing ones. However, it is highly suggested that you refer to this video for a detailed walkthrough of the code.
