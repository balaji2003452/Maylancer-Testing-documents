import time
import json
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, urljoin

# ==================== CONFIG ====================
BASE_URL = "https://thecoimbatorian.com/"
visited_pages = set()
pages_to_visit = [BASE_URL]

all_urls = set()
broken_links = []
unauthorized_links = []
server_errors = []

# ---------------- Chrome Options ----------------
options = Options()
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
options.add_argument("--headless=new")       # Headless mode for speed
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--log-level=3")        # Reduce console noise

driver = webdriver.Chrome(options=options)
driver.set_page_load_timeout(60)             # Timeout for slow pages
driver.execute_cdp_cmd("Network.enable", {}) # Enable network tracking

# ==================== FUNCTIONS ====================

def get_internal_links_from_page():
    """
    Use Selenium to find all <a> elements on the current page and return
    absolute internal links only.
    """
    links = set()
    elements = driver.find_elements("tag name", "a")
    for el in elements:
        href = el.get_attribute("href")
        if href:
            href = urljoin(driver.current_url, href)
            parsed_href = urlparse(href)
            if parsed_href.netloc == urlparse(BASE_URL).netloc:
                links.add(href.split("#")[0])  # Remove anchor
    return links

def check_network_logs():
    """
    Check Chrome performance logs for 404, 401, and 5xx errors.
    """
    logs = driver.get_log("performance")
    for log in logs:
        try:
            log_json = json.loads(log["message"])["message"]
            if log_json.get("method") == "Network.responseReceived":
                response = log_json["params"]["response"]
                url = response["url"]
                status = response["status"]

                if url in all_urls:
                    continue
                all_urls.add(url)

                if status == 401:
                    unauthorized_links.append((url, status))
                elif status == 404:
                    broken_links.append((url, status))
                elif status >= 500:
                    server_errors.append((url, status))
        except Exception:
            continue

def save_report_to_csv():
    """
    Save broken links, 401 unauthorized, and 5xx server errors to CSV.
    """
    with open("QA_BrokenLinks_Report.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Category", "URL", "Status"])

        for url, status in broken_links:
            writer.writerow(["404 Broken Link", url, status])
        for url, status in unauthorized_links:
            writer.writerow(["401 Unauthorized", url, status])
        for url, status in server_errors:
            writer.writerow(["5xx Server Error", url, status])

# ==================== CRAWLING LOOP ====================

while pages_to_visit:
    current_page = pages_to_visit.pop(0)
    if current_page in visited_pages:
        continue
    print(f"Visiting: {current_page}")
    visited_pages.add(current_page)
    
    try:
        driver.get(current_page)
    except Exception as e:
        print(f"Error loading {current_page}: {e}")
        continue

    # Scroll to trigger lazy-loading content
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
    except:
        pass

    # Check network responses for errors
    check_network_logs()

    # Extract internal links and queue them
    try:
        links = get_internal_links_from_page()
        for link in links:
            if link not in visited_pages and link not in pages_to_visit:
                pages_to_visit.append(link)
    except Exception:
        continue

driver.quit()

# ==================== FINAL REPORT ====================

print("\n========== FULL SITE QA REPORT ==========")
print("Total Pages Visited           :", len(visited_pages))
print("Total Network Requests Captured:", len(all_urls))
print("Total 404 Broken Links        :", len(broken_links))
print("Total 401 Unauthorized        :", len(unauthorized_links))
print("Total 5xx Server Errors       :", len(server_errors))

# Save to CSV
save_report_to_csv()
print("\nBroken links report saved to QA_BrokenLinks_Report.csv")

# Optional: Print summary in console
print("\n------ 404 Broken Links ------")
for url, status in broken_links:
    print(f"{url} | Status: {status}")

print("\n------ 401 Unauthorized ------")
for url, status in unauthorized_links:
    print(f"{url} | Status: {status}")

print("\n------ 5xx Server Errors ------")
for url, status in server_errors:
    print(f"{url} | Status: {status}")