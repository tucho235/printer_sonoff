# printer_utils.py
import os
import time
import json
import subprocess
import requests
from datetime import datetime
from typing import Tuple, Optional

SONOFF_URL = "http://{ip_sonoff}:8081/zeroconf"
LOCK_FILE = "/tmp/printer_sonoff.lock"

def get_current_timestamp() -> int:
    """Get current Unix timestamp."""
    return int(time.time())

def get_formatted_datetime() -> str:
    """Get current datetime in formatted string."""
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def make_printer_request(endpoint: str, data: dict) -> Tuple[dict, int]:
    """Make HTTP request to sonoff API."""
    try:
        response = requests.post(
            f"{SONOFF_URL}/{endpoint}",
            json={"data": data},
            headers={"Content-Type": "application/json"}
        )
        return response.json(), response.status_code
    except requests.RequestException as e:
        print(f"Error making request: {e}")
        return {}, 500

def get_pending_print_jobs() -> str:
    """Get pending print jobs using lpstat command."""
    try:
        result = subprocess.run(['lpstat', '-o'], capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.SubprocessError as e:
        print(f"Error checking print jobs: {e}")
        return ""


# check_print.py
def check_and_turn_off() -> None:
    """Check printer status and turn it off if conditions are met."""
    current_time = get_current_timestamp()
    should_turn_off = True
    print(f"{get_formatted_datetime()} ###########################################")

    # Check if init print file exists and is recent
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                value = f.read().strip()
                if value and value.isdigit():
                    last_print_time = int(value)
                    if last_print_time > (current_time - 60):  # 60 seconds = 1 minute
                        should_turn_off = False
    except IOError as e:
        print(f"Error reading init print file: {e}")
        should_turn_off = False

    # Check for pending print jobs
    if should_turn_off:
        pending_jobs = get_pending_print_jobs()
        if pending_jobs:
            print(pending_jobs)
            should_turn_off = False

    # Turn off printer if conditions are met
    if should_turn_off:
        print("Turning off printer...")
        response, status_code = make_printer_request("switch", {"switch": "off"})
        
        if status_code == 200 and response.get('error') == 0:
            try:
                os.remove(LOCK_FILE)
                print("Printer turned off successfully")
            except OSError as e:
                print(f"Error removing init print file: {e}")
        else:
            print(f"Failed to turn off printer. Status: {status_code}, Error: {response.get('error')}")

def write_timestamp_file(filename: str) -> None:
    """Write current timestamp to file."""
    try:
        with open(filename, 'w') as f:
            f.write(str(get_current_timestamp()))
    except IOError as e:
        print(f"Error writing to file: {e}")

# print.py
def turn_on_printer() -> bool:
    """
    Check printer status and turn it on if needed.
    Returns True if printer is on or successfully turned on.
    """
    # Check printer status
    response, status_code = make_printer_request("info", {})
    
    if status_code != 200:
        print("Failed to query printer status")
        return False
        
    try:
        if response.get('data', {}).get('switch') == "off":
            # Turn on printer
            response, status_code = make_printer_request("switch", {"switch": "on"})
            
            if status_code == 200 and response.get('error') == 0:
                write_timestamp_file(LOCK_FILE)
                print("Printer turned on successfully")
                return True
            else:
                print("Failed to turn on printer")
                return False
        else:
            write_timestamp_file(LOCK_FILE)
            print("Printer was already on")
            return True
    except Exception as e:
        print(f"Error processing printer response: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python printer.py <on|off>")
        sys.exit(1)

    metodo = sys.argv[1]

    if metodo == "on":
        turn_on_printer()
    elif metodo == "off":
        check_and_turn_off()
    else:
        print("Método no reconocido. Usa 'on' u 'off'.")
        sys.exit(1)
