from src.fields.config import ALL_FIELDS_API_NAMES, AUTO_FIELDS_LINUX_COMMANDS
import subprocess

class Field:
    def __init__(self, 
                 field_name, 
                 display_string, 
                 default_value = None):
        if field_name not in ALL_FIELDS_API_NAMES:
            raise Exception("To add a new field, please add its API name to config file first.")
        self.field_name = field_name
        self.display_string = display_string
        self.API_name = ALL_FIELDS_API_NAMES[field_name]
        self.value = default_value
    
    def __repr__(self):
        return f" - {self.display_string:<20}: {self.value}"

VALID_MANUAL_TYPES = ["id", "text", "int", "number", "bool", "select", "multiselect"]

class ManualField(Field):
    def __init__(self, 
                 field_name, 
                 display_string, 
                 type, # id/text/int/number/bool/select/multiselect
                 default_value = None,
                 options = []):
        if type not in VALID_MANUAL_TYPES:
            raise Exception(f"Invalid manual field type, must be one of {VALID_MANUAL_TYPES}")
        super().__init__(field_name, display_string, default_value)
        self.type = type
        self.validate_fn = lambda x: x if x != "" else None
        self.options = options

    def validate(self, input_str):
        val = self.validate_fn(input_str)
        if val != None:
            if self.type == "multiselect":
                self.value.append(val)
            else:
                self.value = val

    def validate_id(self, input_str, sf):
        self.value = self.validate_fn(input_str, sf)


class AutoField(Field):
    def __init__(self, 
                 field_name, 
                 display_string, 
                 type, # text/int/number/bool/select/multiselect
                 default_value = None,
                 options = []):
        super().__init__(field_name, display_string, default_value)
        self.type = type
        self.error = None
        self.validate_fn = lambda x: x if x != "" else None # either return the value to be stored, or return None, or raise exception
        self.options = options

    def run_and_validate(self):
        try:
            output = subprocess.check_output((" | ").join(AUTO_FIELDS_LINUX_COMMANDS[self.field_name]), 
                shell = True,
                text = True,
                stderr = subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.error = e.output if e.output else "`grep` didn't find match (unexpected file or output format from linux commands)"
        else:
            try:
                val = self.validate_fn(output)
                if val != None:
                    self.value = val
            except Exception as e:
                self.error = "regex matching error (unexpected output format from linux commands)"
    
