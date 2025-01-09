
# 🕵️‍♂️ **SFAC - Subdomain Finder & Accessibility Checker**

  

>  **Version:** 1.7 🚀 | **Created by:** Sneakywarwolf 🐺

  

🎯 **Discover subdomains, check their accessibility, and capture screenshots — all in one script!**

SFAC is your ultimate tool for subdomain enumeration and accessibility checks. Whether you're a cybersecurity enthusiast 🛡️ or just curious about the domains lurking under a main website 🌐, SFAC has got your back!

  

---

  

## 📖 **Features**

  

- 🎯 **Subdomain Enumeration:** Automatically find unique subdomains using Sublist3r.

- ✅ **Accessibility Check:** Test if subdomains are live and accessible.

- 📸 **Screenshot Capture:** Snap screenshots of live domains in headless mode.

- 💾 **CSV Output:** Save results in a neatly organized CSV file.

- 🎨 **Color-Coded CLI Output:** Clear, visually appealing logs to make debugging fun!

  

---

  

## ⚡ **Getting Started**

  

### 🚧 **Prerequisites**

  

1.  **Python 3.6+** 🐍

2.  **Google Chrome** 🌐

3.  **ChromeDriver** (Add it to your system PATH).

  

### 🛠️ **Setup**

  

1. Clone this repository:

```bash
git clone https://github.com/your-username/SFAC.git
cd SFAC
```
2. Install the required Python dependencies:

```bash
pip install -r requirements.txt
```
  

### 🏃‍♂️ **Usage**

---------------

  

### 🎯 **Find Subdomains for a Domain**

  ```bash
python finder_v1.7.py -D example.com`
```
  

### 📂 **Check Subdomains from a File**

  

```bash
`python  finder_v1.7.py  -t  subdomains.txt`
```
  

### 💾 **Save Results to a CSV**

  
  

`python  finder_v1.7.py  -D  example.com  -o  results.csv`

  

### 📸 **Enable Screenshots of Accessible Subdomains**

  

`python  finder_v1.7.py  -D  example.com  -s  snapshots`

  

### 🧵 **Adjust Concurrency for Faster Checks**

  

`python  finder_v1.7.py  -D  example.com  -T  20`

  

*  *  *  *  *

  

🖥️  **Output**

--------------

  

-  **CSV Results:**

Contains subdomain, status code, and accessibility information.

  

-  **Screenshots:**

Saved in the folder of your choice (default: `snapshots/`).

  

-  **Sample Log:**

  

🕒 [16:36:01] Starting Sublist3r...

✅ [16:36:12] Sublist3r found 22 unique subdomains.

❌ [16:36:30] Failed to access subdomain: sub.example.com.

✅ [16:36:45] Screenshot saved: snapshots/example_com.png`

  

* * * * *

  

✨  **Features  at  a  Glance**

--------------------------

-   🔍 **Subdomain Finder**: Quickly discover subdomains for a given domain using Sublist3r.
-   🚦 **Accessibility Checker**: Determine the accessibility of subdomains with detailed status codes.
-   📸 **Screenshot Capture**: Automatically take screenshots of accessible subdomains for better analysis.
-   📁 **CSV Export**: Save all findings into a clean, structured CSV file.
-   ⚡ **Concurrency Support**: Speed up the subdomain accessibility checks with multithreading.
-   🎨 **Color-Coded Output**: Visually distinct messages in the terminal for easy understanding.
-   🛠️ **Customizable Options**: Set domain, input file, output file, snapshot folder, and concurrency via CLI arguments.
-   ❌ **Handles Invalid Subdomains**: Filters and excludes invalid subdomains automatically.
-   🖥️ **Cross-Platform Compatibility**: Works seamlessly on Windows, macOS, and Linux.

  

* * * * *

  

## 🛡️  **Disclaimer**

------------------
 

> This tool is for **educational purposes only**. Please do not use it for unauthorized activities. Always ensure you have the proper permissions before testing any domain.

 
* * * * *

  

💡  **Contributing**

-------------------

  

1.  Fork  the  repository  🍴

2.  Create  a  new  branch:

		git checkout -b feature/awesome-feature`

 
3.  Commit  your  changes:

		git commit -m "Added an awesome feature 🚀"`

  
4.  Push  to  the  branch:

		git push origin feature/awesome-feature`

  
5.  Submit  a  pull  request  🤝

  

* * * * *

  

## 📞  **Contact**

--------------

  

🔗  **GitHub:** [Sneakywarwolf](https://github.com/sneakywarwolf)   [![LinkedIn](https://img.shields.io/badge/-LinkedIn-blue?logo=linkedin)](https://www.linkedin.com/in/sneakywarwolf/)

📧  **Email:**  sneakypentester@gmail.com

* * * * *

## 🚀 **Happy Hacking!** ✨