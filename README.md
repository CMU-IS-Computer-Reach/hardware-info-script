# hardware-info-script
A script to get hardware info and upload to Salesforce. Only Linux is supported currently.

## usage
1. Make sure Python3 is installed: `python3 --version`
2. Make sure `tkinter` (for GUI) is installed: `python3 -m tkinter`
    1. If not, install with `sudo apt-get install python3-tk`
3. Make sure the dependencies is installed (**this only needs to be run once**): `pip install -r requirements.txt`
4. Make sure the following **environment variables** are set/up-to-date (add `export NAME=VALUE` to your `~/.bashrc` file, and then run `source .bashrc`, and then restart terminal):
    1. `SF_BENCH_USERNAME`: Salesforce username of the account used for auditing devices
    2. `SF_BENCH_PASSWORD`: password
    3. `SF_BENCH_TOKEN`: security token ([how to find it](https://help.salesforce.com/s/articleView?id=sf.user_security_token.htm&type=5))
5. Run `python3 <path to script.py>`
    1. You will be asked to enter the **CRID** of the device you are auditing; this CRID must already exist in Salesforce (if not, create a record for it via Salesforce UI first)
    2. You will then be prompted to manually input some fields (see next section)
    3. The script then automatically collects some other fields (see next section)
        - Any errors that occured will be displayed
        - If you are just using the script, you can ignore the errors, but keep in mind that those fields will be empty in Salesforce
        - If you are the maintainer of the script, run the Linux command for fields that failed and examine the output to determine if it needs to be fixed
    4. The script then displays all fields it will upload and asks if you'd like to upload the data to Salesforce
        - **REVIEW IT BEFORE PROCEEDING**

## fields collected

### fields asked to be manually input
- CRID
- Webcam
- Video ports
- \# USB ports
- Adapter watts
- Final OS

### fields automatically collected
See `ALL_FIELDS_API_NAMES` for the Linux commands run for each field
- CPU model
- RAM
- Storage
- Screen size
- Battery health
- Ethernet
- Wifi
- Optical drive
- Touchscreen

## how to add new fields

### to add a new field to be manually input
1. Add an entry `{name of the field: corresponding Salesforce API name}` in `ALL_FIELDS_API_NAMES`
2. Add the name of the field to `MANUAL_FIELDS`
3. Add a new class variable `self.<name of the field>` to the `EquipmentInfo` class
4. In the `data_input()` function, follow the format of an existing section to add the code for manually input
    - Make sure there is **appropriate error checking and type conversion**
5. If the field value requires special conversion before uploading to Salesforce, add the code in the `_convert_to_record()` function
    - For example, an existing field that needs conversion is `video_ports`, because it's a picklist field in Salesforce so the data needs to be formatted in a special way


### to add a new field to be automatically collected
1. Add an entry `{name of the field: corresponding Salesforce API name}` in `ALL_FIELDS_API_NAMES`
2. Add the name of the field to `AUTO_FIELDS`
3. Add the Linux commands to be run to collect this field in `AUTO_FIELDS_LINUX_COMMANDS`
4. Add a new class variable `self.<name of the field>` to the `EquipmentInfo` class
5. In the `data_collection()` function, follow the format of an existing section to add the code for parsing the value
    - Run the Linux command, then use RegEx to parse the output if necessary
    - Make sure there is **appropriate error checking and type conversion**, and store meaningful error message into `self._errors`
6. Similar to above, if the field value requires special conversion, add the code in the `_convert_to_record()` function
