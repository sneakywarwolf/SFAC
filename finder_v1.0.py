import os
import csv
import sys
import requests
from tqdm import tqdm
import subprocess
import dns.resolver

def list_files_in_directory():
    """List all files in the current working directory."""
    print("\nFiles in the current directory:")
    files_in_directory = os.listdir(os.getcwd())
    for file in files_in_directory:
        print(file)

def run_sublist3r(domain):
    """Run Sublist3r to enumerate subdomains."""
    sublist3r_path = os.path.join('Sublist3r', 'sublist3r.py')
    if not os.path.exists(sublist3r_path):
        print("Error: Sublist3r script not found in the Sublist3r folder.")
        return []

    try:
        result = subprocess.run(
            ['python', sublist3r_path, '-d', domain, '-o', 'sublist3r_output.txt'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            with open('sublist3r_output.txt', 'r') as file:
                subdomains = [line.strip() for line in file.readlines()]
            return subdomains
        else:
            print(f"Sublist3r error: {result.stderr}")
            return []
    except Exception as e:
        print(f"Error running Sublist3r: {e}")
        return []

def enumerate_subdomains(domain):
    """Enumerate subdomains using Sublist3r."""
    print(f"Enumerating subdomains for {domain} using Sublist3r...")
    sublist3r_subdomains = run_sublist3r(domain)
    return list(set(sublist3r_subdomains))

def check_subdomains(subdomain_list, output_file):
    """Check the accessibility of subdomains and save the results to a CSV file."""
    results = []

    for subdomain in tqdm(subdomain_list, desc="Checking subdomains", unit="subdomain"):
        try:
            response = requests.get(f"http://{subdomain}", timeout=5)
            status_code = response.status_code
            accessible = "Yes" if status_code == 200 else "No"
        except requests.RequestException:
            status_code = "N/A"
            accessible = "No"

        results.append({"Subdomain": subdomain, "Status Code": status_code, "Accessible": accessible})

    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["Subdomain", "Status Code", "Accessible"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(results)

    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    print("Choose an option:")
    print("1: Enter a domain")
    print("2: Provide a list of subdomains")

    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == "1":
        domain = input("Enter the domain: ").strip()
        output_file = input("Enter the output CSV file name: ").strip()

        subdomains = enumerate_subdomains(domain)
        if subdomains:
            check_subdomains(subdomains, output_file)
        else:
            print("No subdomains found.")

    elif choice == "2":
        list_files_in_directory()
        subdomain_file = input("\nEnter the subdomain list file (choose from the above files): ").strip()
        output_file = input("Enter the output CSV file name: ").strip()

        try:
            with open(subdomain_file, 'r') as file:
                subdomains = [line.strip() for line in file.readlines()]

            if subdomains:
                check_subdomains(subdomains, output_file)
            else:
                print("Subdomain list is empty.")

        except FileNotFoundError:
            print(f"Error: File {subdomain_file} not found.")
            sys.exit(1)

    else:
        print("Invalid choice. Please run the script again and choose 1 or 2.")
        sys.exit(1)
