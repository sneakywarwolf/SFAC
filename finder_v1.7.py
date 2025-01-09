import os  # Provides functions to interact with the operating system
import csv  # Handles reading and writing CSV files
import sys  # Access system-specific parameters and functions
import requests  # Simplifies making HTTP requests
from tqdm import tqdm  # Displays progress bars for loops
import subprocess  # Runs subprocesses and interacts with system commands
import time  # Provides time-related functions
from concurrent.futures import ThreadPoolExecutor  # Manages multithreading
import re  # Adds regular expressions for pattern matching and validation
import argparse  # Parses command-line arguments
from selenium import webdriver  # Selenium WebDriver for browser automation
from selenium.webdriver.chrome.service import Service  # Manages ChromeDriver service for Selenium
from selenium.webdriver.common.by import By  # Defines various methods to locate elements
from selenium.webdriver.chrome.options import Options  # Configures Chrome options for Selenium
from colorama import Fore, Style  # Adds color formatting for terminal output
import platform  # To identify the operating system
import shutil  # For file operations
import urllib.request  # For downloading files
import zipfile  # For extracting ChromeDriver
import subprocess  # To install dependencies using system commands

ascii_art = """
                                                                                  
   SSSSSSSSSSSSSSS FFFFFFFFFFFFFFFFFFFFFF      AAA                  CCCCCCCCCCCCC
 SS:::::::::::::::SF::::::::::::::::::::F     A:::A              CCC::::::::::::C
S:::::SSSSSS::::::SF::::::::::::::::::::F    A:::::A           CC:::::::::::::::C
S:::::S     SSSSSSSFF::::::FFFFFFFFF::::F   A:::::::A         C:::::CCCCCCCC::::C
S:::::S              F:::::F       FFFFFF  A:::::::::A       C:::::C       CCCCCC
S:::::S              F:::::F              A:::::A:::::A     C:::::C              
 S::::SSSS           F::::::FFFFFFFFFF   A:::::A A:::::A    C:::::C              
  SS::::::SSSSS      F:::::::::::::::F  A:::::A   A:::::A   C:::::C              
    SSS::::::::SS    F:::::::::::::::F A:::::A     A:::::A  C:::::C              
       SSSSSS::::S   F::::::FFFFFFFFFFA:::::AAAAAAAAA:::::A C:::::C              
            S:::::S  F:::::F         A:::::::::::::::::::::AC:::::C              
            S:::::S  F:::::F        A:::::AAAAAAAAAAAAA:::::AC:::::C       CCCCCC
SSSSSSS     S:::::SFF:::::::FF     A:::::A             A:::::AC:::::CCCCCCCC::::C
S::::::SSSSSS:::::SF::::::::FF    A:::::A               A:::::ACC:::::::::::::::C
S:::::::::::::::SS F::::::::FF   A:::::A                 A:::::A CCC::::::::::::C
 SSSSSSSSSSSSSSS   FFFFFFFFFFF  AAAAAAA                   AAAAAAA   CCCCCCCCCCCCC
     
                                    Subdomain Finder and Accessibility Checker  
                                                                    v1.6 created by Sneakywarwolf
"""
print(Fore.MAGENTA + ascii_art + Style.RESET_ALL)

def validate_selenium_dependencies():
    """Validate if ChromeDriver and Google Chrome are installed, and install if not found."""
    try:
        # Check for ChromeDriver and Google Chrome
        chromedriver_installed = shutil.which("chromedriver") is not None
        chrome_installed = shutil.which("google-chrome") is not None or shutil.which("chrome") is not None

        if not (chromedriver_installed and chrome_installed):
            print_status("Missing Selenium dependencies. Installing...")
            install_selenium_dependencies()
        else:
            print_status("Selenium dependencies validated successfully.")
    except Exception as e:
        print_status(f"Error validating or installing Selenium dependencies: {e}")
        sys.exit(1)

def list_files_in_directory():
    """List files in the current working directory."""
    print("\nFiles in the current directory:")
    for file in os.listdir(os.getcwd()):
        print(file)

def print_status(message):
    """Print a status message with a timestamp."""
    print(f"[{time.strftime('%H:%M:%S')}] {message}")

def run_sublist3r(domain):
    """Run Sublist3r to enumerate subdomains with a dynamic progress bar."""
    sublist3r_path = os.path.join('Sublist3r', 'sublist3r.py')
    if not os.path.exists(sublist3r_path):
        print("Error: Sublist3r script not found in the Sublist3r folder.")
        return []

    try:
        print_status("Starting Sublist3r...")
        process = subprocess.Popen(
            ['python', sublist3r_path, '-d', domain],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        subdomains = set()

        with tqdm(desc="Finding subdomains", unit="subdomain", leave=True) as pbar:
            for line in process.stdout:
                line = line.strip()
                if line and "://" not in line:  # Ignore noise
                    subdomain = line.split()[-1] if line.startswith("[+]") else line
                    if subdomain and subdomain not in subdomains:
                        subdomains.add(subdomain)
                        pbar.update(1)

        process.wait()

        if process.returncode != 0:
            print(f"Sublist3r error: {process.stderr.read().strip()}")
            return []

        print_status(f"Sublist3r found {len(subdomains)} unique subdomains.")
        return list(subdomains)
    except Exception as e:
        print(f"Error running Sublist3r: {e}")
        return []

def is_valid_subdomain(subdomain):
    """Validate subdomain using a regular expression."""
    subdomain_regex = r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.(?!-)[A-Za-z0-9.-]{1,255}$'
    return re.match(subdomain_regex, subdomain) is not None

def check_subdomain(subdomain):
    """Check the accessibility of a single subdomain."""
    if not is_valid_subdomain(subdomain):
        return {"Subdomain": subdomain, "Status Code": "Invalid", "Accessible": "No"}

    try:
        response = requests.get(f"http://{subdomain}", timeout=10)
        status_code = response.status_code
        accessible = "Yes" if status_code == 200 else "No"
    except requests.RequestException:
        status_code = "N/A"
        accessible = "No"

    return {"Subdomain": subdomain, "Status Code": status_code, "Accessible": accessible}

def write_filtered_to_csv(results, output_file):
    """Write only valid subdomains to a CSV file."""
    valid_results = [result for result in results if is_valid_subdomain(result["Subdomain"])]
    
    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["Subdomain", "Status Code", "Accessible"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_results)
    
    print_status(f"Filtered results saved to {output_file}")

def print_status(message, message_type="info"):
    """Print a status message with a timestamp and color coding based on message type."""
    # Default to informational messages (blue)
    color = Fore.BLUE

    if message_type == "success":
        color = Fore.GREEN
    elif message_type == "error":
        color = Fore.RED
    elif message_type == "warning":
        color = Fore.YELLOW
    elif message_type == "info":
        color = Fore.CYAN  # or blue depending on preference

    print(f"{color}[{time.strftime('%H:%M:%S')}] {message}{Style.RESET_ALL}")

def take_screenshot(subdomain, folder):
    """Take a screenshot of a subdomain and save it in the specified folder."""
    try:
        validate_selenium_dependencies()  # Validate and install dependencies before proceeding

        # Ensure the folder exists
        os.makedirs(folder, exist_ok=True)

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)

        url = f"http://{subdomain}"
        driver.set_page_load_timeout(10)
        driver.get(url)

        screenshot_path = os.path.join(folder, f"{subdomain.replace('.', '_')}.png")
        driver.save_screenshot(screenshot_path)

        print_status(f"Screenshot saved: {screenshot_path}", message_type="success")

        driver.quit()

    except Exception as e:
        print_status(f"Failed to take screenshot of {subdomain}: {e}", message_type="error")

# Example of logging DevTools messages in yellow
def log_devtools_message(message):
    """Log DevTools related messages in yellow."""
    print_status(message, message_type="warning")

def check_subdomains_concurrently(subdomain_list, output_file, snapshot_folder=None, concurrency=10):
    """Check subdomains concurrently, save results to a CSV file, and optionally take screenshots."""
    if concurrency <= 0:
        print_status("Invalid concurrency value. Falling back to default: 10.")
        concurrency = 10

    print_status(f"Checking accessibility of {len(subdomain_list)} subdomains with concurrency: {concurrency}...")
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(tqdm(executor.map(check_subdomain, subdomain_list), total=len(subdomain_list), desc="Checking subdomains"))

    write_filtered_to_csv(results, output_file)

    # Default folder for snapshots
    if snapshot_folder is None:
        snapshot_folder = "snapshots"

    # Take screenshots of accessible subdomains
    os.makedirs(snapshot_folder, exist_ok=True)
    print_status("Taking screenshots of accessible subdomains...")
    for result in results:
        if result["Accessible"] == "Yes":
            take_screenshot(result["Subdomain"], snapshot_folder)

def install_selenium_dependencies():
    """Ensure ChromeDriver and Google Chrome are installed and configured."""
    # Determine the operating system
    os_type = platform.system().lower()
    is_windows = os_type == "windows"
    is_linux = os_type == "linux"
    is_mac = os_type == "darwin"

    # Check if Google Chrome is installed
    chrome_installed = shutil.which("google-chrome") or shutil.which("chrome")
    if not chrome_installed:
        print_status("Google Chrome not found. Installing it...")

        if is_linux:
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "google-chrome-stable"], check=True)
        elif is_windows:
            chrome_url = "https://dl.google.com/chrome/install/latest/chrome_installer.exe"
            installer_path = "chrome_installer.exe"
            urllib.request.urlretrieve(chrome_url, installer_path)
            subprocess.run([installer_path], check=True)
            os.remove(installer_path)
        elif is_mac:
            subprocess.run(["brew", "install", "--cask", "google-chrome"], check=True)
        else:
            print_status("Unsupported OS for automatic Chrome installation.")
            sys.exit(1)

    # Check if ChromeDriver is installed
    chromedriver_path = shutil.which("chromedriver")
    if not chromedriver_path:
        print_status("ChromeDriver not found. Installing it...")

        # Determine ChromeDriver URL
        chrome_version_output = subprocess.check_output(["google-chrome", "--version"]).decode("utf-8").strip()
        chrome_version = re.search(r"\d+", chrome_version_output).group()
        driver_url = f"https://chromedriver.storage.googleapis.com/{chrome_version}/chromedriver_{'win32' if is_windows else 'linux64' if is_linux else 'mac64'}.zip"

        # Download and extract ChromeDriver
        driver_zip = "chromedriver.zip"
        urllib.request.urlretrieve(driver_url, driver_zip)
        with zipfile.ZipFile(driver_zip, "r") as zip_ref:
            zip_ref.extractall(".")
        os.remove(driver_zip)

        # Ensure ChromeDriver is accessible
        chromedriver_path = "./chromedriver"
        if is_linux or is_mac:
            subprocess.run(["chmod", "+x", chromedriver_path], check=True)
        shutil.move(chromedriver_path, "/usr/local/bin/" if not is_windows else os.getcwd())

    print_status("Selenium dependencies installed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subdomain enumeration and accessibility checker.")
    parser.add_argument("-D", "--domain", help="Domain to enumerate subdomains for.")
    parser.add_argument("-t", "--textfile", help="Path to the text file containing subdomains.")
    parser.add_argument("-o", "--output", help="Output CSV file to save results.", default=f"output_{int(time.time())}.csv")
    parser.add_argument("-s", "--snapshots", help="Enable saving screenshots of accessible subdomains. Optionally specify a folder name.", nargs='?', const="snapshots")
    parser.add_argument("-T", "--concurrency", type=int, help="Number of threads for concurrent checks (default: 10).", default=10)

    args = parser.parse_args()

    if args.domain:
        output_file = args.output
        if not output_file.endswith(".csv"):
            output_file += ".csv"

        subdomains = run_sublist3r(args.domain)
        if subdomains:
            check_subdomains_concurrently(subdomains, output_file, args.snapshots, args.concurrency)
        else:
            print_status("No subdomains found.")

    elif args.textfile:
        if os.path.exists(args.textfile):
            with open(args.textfile, 'r') as file:
                subdomains = [line.strip() for line in file.readlines()]
            if subdomains:
                check_subdomains_concurrently(subdomains, args.output, args.snapshots, args.concurrency)
            else:
                print_status("Subdomain list is empty.")
        else:
            print(f"Error: File {args.textfile} not found.")
    else:
        parser.print_help()
        sys.exit(1)

