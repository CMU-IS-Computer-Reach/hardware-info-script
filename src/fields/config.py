# Salesforce API name for all the fields to be uploaded
ALL_FIELDS_API_NAMES = {
    "CRID":                 "Computer_Reach_ID__c",
    "has_webcam":           "Webcam_present__c",
    "video_ports":          "Video__c",
    "num_usb_ports":        "USB__c",
    "adapter_watts":        "Adapter_Watts__c",
    "final_os":             "Final_Operating_System__c",
    "model_name":           "Processor_Speed__c",
    "RAM":                  "RAM_Total_MB__c", # TODO: the API name says MB but the field name says GB
    "storage":              "Hard_Drive_GB__c",
    "screen_size":          "Screen_Size__c",
    "battery_health":       "Battery_Health__c",
    "has_ethernet":         "Ethernet_present__c",
    "has_wifi":             "WiFi_present__c",
    "has_optical_drive":    "Optical_Drive_present__c",
    "has_touchscreen":      "TouchScreen_Works__c",
}

# Fields that are asked to be manually input
MANUAL_FIELDS = ["CRID", "has_webcam", "video_ports", "num_usb_ports", "adapter_watts", "final_os"]
# Configurations for some manual fields for convenience
FINAL_OS_OPTIONS = ["20.04_Xubuntu_Linux"] # Salesforce API Name of all final OS options
VIDEO_PORT_OPTIONS = ["VGA", "DVI", "HDMI", "Mini-HDMI", "Display Port", "Mini-Display"] # Salesforce API Name of all video ports options

# Fields that will be automatically collected
AUTO_FIELDS = ["model_name", "RAM", "storage", "screen_size", "battery_health", "has_ethernet", "has_wifi", "has_optical_drive", "has_touchscreen"]
# Linux commands used to automatically collect a field
AUTO_FIELDS_LINUX_COMMANDS = {
    "model_name":           ["cat /proc/cpuinfo", "grep 'model name'"],
    "RAM":                  ["cat /proc/meminfo", "numfmt --field 2 --from-unit=Ki --to-unit=Gi", "sed 's/ kB/G/g'", "grep 'MemTotal'", "awk '{print $2}'"],
    "storage":              ["lsblk -I 8 -d -n --output SIZE"],
    "screen_size":          ["xrandr --current", "grep ' connected'"],
    "battery_health":       ["upower -i `upower -e | grep 'BAT'`", "grep 'capacity'", "awk '{print $2}'", "grep ."],
    "has_ethernet":         ["lspci", "grep 'ethernet' -i"],
    "has_wifi":             ["lspci", "grep 'network|wireless' -i -E"],
    "has_optical_drive":    ["dmesg", "grep 'cdrom|cd-rom|dvd' -i -E"],
    "has_touchscreen":      ["xinput list", "grep 'touchscreen' -i"],
}