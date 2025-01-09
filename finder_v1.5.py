import os  # Provides functions to interact with the operating system
import csv  # Handles reading and writing CSV files
import sys  # Access system-specific parameters and functions
import requests  # Simplifies making HTTP requests
from tqdm import tqdm  # Displays progress bars for loops
import subprocess  # Runs subprocesses and interacts with system commands
import time  # Provides time-related functions
from concurrent.futures import ThreadPoolExecutor  # Manages multithreading
import re  # Adds regular expressions for pattern matching and validation
import argparse
from colorama import Fore, Style

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
                                                                    v1.5 created by Sneakywarwolf
"""
print(Fore.MAGENTA + ascii_art + Style.RESET_ALL)

def validate_output_path(output_file):
    """Ensure the directory for the output file exists."""
    output_dir = os.path.dirname(output_file) or os.getcwd()
    if not os.path.exists(output_dir):
        raise FileNotFoundError(f"Output directory does not exist: {output_dir}")

def print_status(message, color=Fore.WHITE):
    """Print a status message with a timestamp and color."""
    print(f"{color}[{time.strftime('%H:%M:%S')}] {message}{Style.RESET_ALL}")

def run_sublist3r(domain):
    """Run Sublist3r to enumerate subdomains with a dynamic progress bar."""
    sublist3r_path = os.path.join('Sublist3r', 'sublist3r.py')
    if not os.path.exists(sublist3r_path):
        print_status("Error: Sublist3r script not found in the Sublist3r folder.", color=Fore.RED)
        return []

    try:
        print_status("Starting Sublist3r...", color=Fore.CYAN)
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
            print_status(f"Sublist3r error: {process.stderr.read().strip()}", color=Fore.RED)
            return []

        print_status(f"Sublist3r found {len(subdomains)} unique subdomains.", color=Fore.GREEN)
        return list(subdomains)
    except Exception as e:
        print_status(f"Error running Sublist3r: {e}", color=Fore.RED)
        return []

def is_valid_subdomain(subdomain):
    """Validate subdomain using a regular expression."""
    subdomain_regex = r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]+)+$'
    return re.match(subdomain_regex, subdomain) is not None

def check_subdomain(subdomain):
    """Check the accessibility of a single subdomain."""
    if not is_valid_subdomain(subdomain):
        return {"Subdomain": subdomain, "Status Code": "Invalid", "Accessible": "No"}

    try:
        response = requests.get(f"http://{subdomain}", timeout=5)
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

    print_status(f"Filtered results saved to {output_file}", color=Fore.GREEN)

def check_subdomains_concurrently(subdomain_list, output_file):
    """Check subdomains concurrently and save results to a CSV file."""
    print_status(f"Checking accessibility of {len(subdomain_list)} subdomains...", color=Fore.CYAN)
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(tqdm(executor.map(check_subdomain, subdomain_list), total=len(subdomain_list), desc="Checking subdomains"))

    write_filtered_to_csv(results, output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Subdomain enumeration and accessibility checker.")
    parser.add_argument("-D", "--domain", help="Domain to enumerate subdomains for (e.g., example.com).")
    parser.add_argument("-t", "--textfile", help="Path to a file containing subdomains, one per line.")
    parser.add_argument("-o", "--output", help="Name of the output CSV file (default: autogenerated).", default=f"output_{int(time.time())}.csv")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose mode for detailed logging.")

    args = parser.parse_args()

    try:
        validate_output_path(args.output)
    except FileNotFoundError as e:
        print_status(str(e), color=Fore.RED)
        sys.exit(1)

    if args.domain:
        output_file = args.output
        if not output_file.endswith(".csv"):
            output_file += ".csv"

        subdomains = run_sublist3r(args.domain)
        if subdomains:
            check_subdomains_concurrently(subdomains, output_file)
        else:
            print_status("No subdomains found.", color=Fore.YELLOW)

    elif args.textfile:
        if os.path.exists(args.textfile):
            with open(args.textfile, 'r') as file:
                subdomains = [line.strip() for line in file.readlines()]
            if subdomains:
                check_subdomains_concurrently(subdomains, args.output)
            else:
                print_status("Subdomain list is empty.", color=Fore.YELLOW)
        else:
            print_status(f"Error: File {args.textfile} not found.", color=Fore.RED)
    else:
        parser.print_help()
        sys.exit(1)
