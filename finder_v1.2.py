import os
import csv
import sys
import requests
from tqdm import tqdm
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

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
        total_subdomains = None

        # Use a progress bar
        with tqdm(desc="Finding subdomains", unit="subdomain") as pbar:
            for line in process.stdout:
                # Process output dynamically
                line = line.strip()
                if line.startswith("[+] Total Unique Subdomains Found:"):
                    total_subdomains = int(line.split(":")[-1].strip())
                    pbar.total = total_subdomains
                elif line.startswith("[+]"):
                    # Extract subdomain and add it to the list
                    subdomain = line.split()[-1]
                    if subdomain not in subdomains:
                        subdomains.add(subdomain)
                        pbar.update(1)

        process.wait()
        if process.returncode != 0:
            print(f"Sublist3r error: {process.stderr.read()}")
            return []

        print_status(f"Sublist3r found {len(subdomains)} unique subdomains.")
        return list(subdomains)
    except Exception as e:
        print(f"Error running Sublist3r: {e}")
        return []

def check_subdomain(subdomain):
    """Check the accessibility of a single subdomain."""
    try:
        response = requests.get(f"http://{subdomain}", timeout=10)
        return {
            "Subdomain": subdomain,
            "Status Code": response.status_code,
            "Accessible": "Yes" if response.status_code == 200 else "No"
        }
    except requests.RequestException:
        return {"Subdomain": subdomain, "Status Code": "N/A", "Accessible": "No"}

def check_subdomains_concurrently(subdomain_list, output_file):
    """Check subdomains concurrently and save results to a CSV file."""
    print_status(f"Checking accessibility of {len(subdomain_list)} subdomains...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ["Subdomain", "Status Code", "Accessible"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for result in tqdm(executor.map(check_subdomain, subdomain_list), total=len(subdomain_list), desc="Checking subdomains"):
                writer.writerow(result)
    print_status(f"Results saved to {output_file}")

if __name__ == "__main__":
    print("Choose an option:")
    print("1: Enter a domain")
    print("2: Provide a list of subdomains")

    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == "1":
        domain = input("Enter the domain: ").strip()
        output_file = input("Enter the output CSV file name (or press Enter for default): ").strip()
        if not output_file:
            output_file = f"output_{int(time.time())}.csv"
        if not output_file.endswith(".csv"):
            output_file += ".csv"

        subdomains = run_sublist3r(domain)
        if subdomains:
            check_subdomains_concurrently(subdomains, output_file)
        else:
            print_status("No subdomains found.")

    elif choice == "2":
        list_files_in_directory()
        subdomain_file = input("\nEnter the subdomain list file: ").strip()
        output_file = input("Enter the output CSV file name (or press Enter for default): ").strip()
        if not output_file:
            output_file = f"output_{int(time.time())}.csv"
        if not output_file.endswith(".csv"):
            output_file += ".csv"

        if os.path.exists(subdomain_file):
            with open(subdomain_file, 'r') as file:
                subdomains = [line.strip() for line in file.readlines()]
            if subdomains:
                check_subdomains_concurrently(subdomains, output_file)
            else:
                print_status("Subdomain list is empty.")
        else:
            print(f"Error: File {subdomain_file} not found.")
    else:
        print("Invalid choice. Please run the script again.")
        sys.exit(1)
