from src.fields.field import AutoField
from src.fields.config import VIDEO_PORT_OPTIONS, FINAL_OS_OPTIONS, ALL_FIELDS_API_NAMES
import re

model_name = AutoField(
    "model_name",
    "CPU model name",
    type="text"
)
def validate_model(input_s):
    r = re.match(r"\s*model name\s*:\s*(.*)", input_s)
    return r.group(1)
model_name.validate_fn = validate_model


ram = AutoField(
    "RAM",
    "RAM (GB)",
    type="int"
)
def validate_ram(input_s):
    r = re.match(r"(\d+)G", input_s)
    return int(r.group(1))
ram.validate_fn = validate_ram


screen_size = AutoField(
    "screen_size",
    "Screen size (inch)",
    type="number"
)
def validate_screen_size(input_s):
    r = re.match(r".*\s+(\d+)mm\s+x\s+(\d+)mm", input_s)
    w = int(r.group(1))
    h = int(r.group(2))
    diagonal = (w * w + h * h) ** 0.5
    return round(diagonal / 25.4)
screen_size.validate_fn = validate_screen_size


battery_health = AutoField(
    "battery_health",
    "Battery health",
    type="text"
)
def validate_battery(input_s):
    r = re.match(r"([\d\.]*)%", input_s)
    return str(round(float(r.group(1)), 2)) + "%"
battery_health.validate_fn = validate_battery


ethernet = AutoField(
    "has_ethernet",
    "Has ethernet?",
    type="bool",
    default_value=False
)
ethernet.validate_fn = lambda x: True


wifi = AutoField(
    "has_wifi",
    "Has WiFi?",
    type="bool",
    default_value=False
)
wifi.validate_fn = lambda x: True


optical_drive = AutoField(
    "has_optical_drive",
    "Has optical drive?",
    type="bool",
    default_value=False
)
optical_drive.validate_fn = lambda x: True


has_touchscreen = AutoField(
    "has_touchscreen",
    "Has touchscreen?",
    type="bool",
    default_value=False
)
has_touchscreen.validate_fn = lambda x: True


auto_fields = [model_name, ram, screen_size, battery_health, ethernet, wifi, optical_drive, has_touchscreen]