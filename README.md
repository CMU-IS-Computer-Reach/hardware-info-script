# hardware-info-script
A script to get hardware info and upload to Salesforce. Only Linux is supported currently.

# What it does
Following fields are collected:
1) CPU model name
2) RAM size (in GB, power of 1024)
3) Storage size (in GB, power of 1024)
4) Battery capacity (%%)
5) All types of available video ports
6) Ethernet adapter existence (Y/N)
7) WiFi card existence (Y/N)
8) Final OS (default to 20.04 Xubuntu Linux)
- TODO: others to be added
It then prints out all the fields as well as any errors occured when parsing a field.

# How to run it
- Make sure Python3 is installed: `python3 --version`
- Run `python3 <path to script.py>`


