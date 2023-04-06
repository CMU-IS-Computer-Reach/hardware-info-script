from fields.manual import manual_fields
from fields.auto import auto_fields
from fields.config import ALL_FIELDS_API_NAMES
import argparse
from simple_salesforce import Salesforce
import os

def authenticate(is_test):
    # Salesforce authentication
    if is_test:
        return Salesforce(
            username = os.getenv("SF_BENCH_USERNAME"), 
            password = os.getenv("SF_BENCH_PASSWORD"), 
            security_token = os.getenv("SF_BENCH_TOKEN"),
            client_id='Hardware Info Script (test)',
            domain='test',
        )
    else:
        return Salesforce(
            username = os.getenv("SF_BENCH_USERNAME"), 
            password = os.getenv("SF_BENCH_PASSWORD"), 
            security_token = os.getenv("SF_BENCH_TOKEN"),
            client_id='Hardware Info Script',
        )

def manual_input(sf, is_test):
    print("\033[104m***Manual Data Entry Section***\033[00m")
    print("\033[93mAfter each prompt, enter value and press ENTER, or directly press ENTER to skip\033[00m")
    cnt = 1
    for field in manual_fields:
        if field.type == "id":
            while True:
                ans = input(f" ({cnt:02d}/{len(manual_fields):02d}) Enter {field.display_string}: ")
                try:
                    field.validate_id(ans, sf)
                    break
                except Exception as e:
                    print(f"\033[91m  {e}\033[00m")
        elif field.type in ["text", "int", "number"]:
            while True:
                ans = input(f" ({cnt:02d}/{len(manual_fields):02d}) Enter {field.display_string}: ")
                try:
                    field.validate(ans)
                    break
                except Exception as e:
                    print(f"\033[91m  {e}\033[00m")
        elif field.type == "bool":
            while True:
                ans = input(f" ({cnt:02d}/{len(manual_fields):02d}) {field.display_string} [y/n]: ")
                try:
                    field.validate(ans)
                    break
                except Exception as e:
                    print(f"\033[91m  {e}\033[00m")
        elif field.type == "select":
            choices = ""
            for idx, option in enumerate(field.options):
                choices += "  [{}] {}\n".format(idx+1, option)
            while True:
                ans = input(f" ({cnt:02d}/{len(manual_fields):02d}) Choose an option for {field.display_string}:\n{choices} *choice: ")
                if ans == "":
                    break
                else:
                    try:
                        ans = int(ans)
                        if ans <= 0 or ans > len(field.options):
                            raise IndexError
                        else:
                            try:
                                field.validate(field.options[ans-1])
                                break
                            except Exception as e:
                                print(f"\033[91m  {e}\033[00m")
                    except (ValueError, IndexError):
                        print("\033[91m  Please enter a valid choice number, or ENTER to skip\033[00m")
        elif field.type == "multiselect":
            print(f" ({cnt:02d}/{len(manual_fields):02d}) Choose available {field.display_string}:")
            for option in field.options:
                while True:
                    ans = input(f"  - {option}? [y/n]:")
                    if ans == "y":
                        field.validate(option)
                        break
                    elif ans == "n" or ans == "":
                        break
                    else:
                        print("\033[91m  Please provide a valid option [y/n], or ENTER to skip\033[00m")
        else:
            raise Exception(f"Unexpected field type {field.type}")
        cnt += 1
    
    print()
    if is_test:
        print("DEBUGGING OUTPUT:")
        for field in manual_fields:
            print(field)
        print()

def auto_collection(sf, is_test):
    print("\033[104m***Auto Data Collection Section***\033[00m")
    for field in auto_fields:
        field.run_and_validate()

    errors = []
    for field in auto_fields:
        if field.error:
            errors.append(f"\033[91m - {field.display_string}: {field.error}\033[00m")
    if errors:
        print("\033[91mBelow error occured when running Linux commands:\033[00m")
        for error in errors:
            print(error)

    if is_test:
        print("DEBUGGING OUTPUT:")
        for field in auto_fields:
            print(field)
        print()

def review_and_upload(sf, is_test):
    print("\033[104m***Data Upload Section***\033[00m")
    print("\033[93m!!!Please carefully review the data to be uploaded first!!!\033[00m")
    print("\033[93m(fields not shown below will be empty in Salesforce)\033[00m")
    for field in manual_fields + auto_fields:
        if field.value != None:
            print(field)
    
    print()
    while True:
        res = input(f"\033[44mUpload to Salesforce? [y/n]: \033[00m").lower()
        if res == "y":
            # convert data to JSON format
            record = dict()
            for field in manual_fields + auto_fields:
                val = field.value
                if field.type == "multiselect": # picklist (multi-select) field in Salesforce has format "selection1;selection;..."
                    val = ";".join(field.value) if field.value else None
                
                if val != None:
                    record[ALL_FIELDS_API_NAMES[field.field_name]] = val

            # upload
            try:
                crid = manual_fields[0].value
                eid = sf.Equipment__c.get_by_custom_id(ALL_FIELDS_API_NAMES["CRID"], crid)['Id']
                sf.Equipment__c.update(eid, record)
                print("\033[92mData uploaded successfully! See below for details:\033[00m")
                print(f" ***CRID: {crid}***")
                print(f" Fields updated:")
                for k, v in record.items():
                    if k != ALL_FIELDS_API_NAMES["CRID"]:
                        print(f"  {k:<25}: {v}")
            except:
                print(f"\033[91mUnexpected error, likely that record with CRID {crid} is recently deleted from Salesforce\033[00m")
                print("\033[90mData not uploaded.\033[00m")
            finally:
                break
        elif res == "n":
            print("\033[90mData not uploaded.\033[00m")
            break
        else:
            print("\033[91m  Please enter a valid option [y/n]\033[00m")

def main():
    # command line arguments
    parser = argparse.ArgumentParser(description = "A script that collects and parses hardware details and upload them to Salesforce.")
    parser.add_argument("-t", "--test", action='store_true', help="test the script on Salesforce Sandbox")
    parser.add_argument("-c", "--cml", action='store_true', help="run the command line version (without GUI)")
    args = parser.parse_args()

    sf = authenticate(args.test)

    manual_input(sf, args.test)
    auto_collection(sf, args.test)
    review_and_upload(sf, args.test)


if __name__ == "__main__":
    main()