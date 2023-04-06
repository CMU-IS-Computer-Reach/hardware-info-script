import src.cml
import src.gui
import os, sys, argparse

def main():
    valid = True
    if not os.getenv("SF_BENCH_USERNAME"):
        print(f"\033[91mPlease make sure environment variable SF_BENCH_USERNAME is set\033[00m")
        valid = False
    if not os.getenv("SF_BENCH_PASSWORD"):
        print(f"\033[91mPlease make sure environment variable SF_BENCH_PASSWORD is set\033[00m")
        valid = False
    if not os.getenv("SF_BENCH_TOKEN"):
        print(f"\033[91mPlease make sure environment variable SF_BENCH_TOKEN is set\033[00m")
        valid = False
    if not valid:
        sys.exit(1)

    # command line arguments
    parser = argparse.ArgumentParser(description = "A script that collects and parses hardware details and upload them to Salesforce.")
    parser.add_argument("-t", "--test", action='store_true', help="test the script on Salesforce Sandbox")
    parser.add_argument("-c", "--cml", action='store_true', help="run the command line version (without GUI)")
    args = parser.parse_args()

    if args.cml:
        src.cml.run(args.test)
    else:
        src.gui.run(args.test)


if __name__ == "__main__":
    main()
