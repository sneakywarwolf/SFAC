import requests
import csv
import sys
from tqdm import tqdm
import subprocess

def run_sublist3r(domain):
    try:
        result = subprocess.run(
            ['python', 'sublist3r.py', '-d', domain, '-o', 'sublist3r_output.txt'],
            capture_output=True,
            text=True,
            cwd='Sublist3r'
        )
        if result.returncode == 0:
            with open('Sublist3r/sublist3r_output.txt', 'r') as file:
                subdomains = [line.strip() for line in file.readlines()]
            return subdomains
        else:
            print(f"Sublist3r error: {result.stderr}")
            return []
    except Exception as e:
        print(f"Error running Sublist3r: {e}")
        return []

def run_subfinder(domain):
    try:
        result = subprocess.run(
            ['subfinder', '-d', domain, '-silent'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            subdomains = result.stdout.splitlines()
            return subdomains
        else:
            print(f"Subfinder error: {result.stderr}")
            return []
    except Exception as e:
        print(f"Error running Subfinder: {e}")
        return []

def enumerate_subdomains(domain):
    print(f"Enumerating subdomains for {domain} using Sublist3r and Subfinder...")
    sublist3r_subdomains = run_sublist3r(domain)
    subfinder_subdomains = run_subfinder(domain)
    combined_subdomains = set(sublist3r_subdomains + subfinder_subdomains)
    return list(combined_subdomains)

def check_subdomains(subdomain_list, output_file):
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
        check_subdomains(subdomains, output_file)

    elif choice == "2":
        subdomain_file = input("Enter the subdomain list file: ").strip()
        output_file = input("Enter the output CSV file name: ").strip()

        try:
            with open(subdomain_file, 'r') as file:
                subdomains = [line.strip() for line in file.readlines()]

            check_subdomains(subdomains, output_file)

        except FileNotFoundError:
            print(f"Error: File {subdomain_file} not found.")
            sys.exit(1)

    else:
        print("Invalid choice. Please run the script again and choose 1 or 2.")
        sys.exit(1)
