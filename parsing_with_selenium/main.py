from selenium import webdriver
from bs4 import BeautifulSoup
import json
import time
import base64
import os
from typing import List, Dict

def extract_encoded_ips_from_page(url: str) -> List[str]:
    """
    Extracts Base64 encoded IP addresses from the specified URL.

    Args:
        url (str): The URL of the page to scrape.

    Returns:
        List[str]: A list of unique Base64 encoded IP addresses found on the page.
    """
    # Start the browser
    driver = webdriver.Chrome()  # Use the appropriate driver
    driver.get(url)

    # Wait for the page to load
    driver.implicitly_wait(4)

    # Get the HTML code of the page
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    encoded_ips = set()  # Use a set for unique values

    # Find all script tags and extract encoded IPs
    for script_tag in soup.find_all('script'):
        if script_tag.string:
            start = script_tag.string.find('Base64.decode("')
            if start != -1:
                start += len('Base64.decode("')
                end = script_tag.string.find('"', start)
                if end != -1:
                    encoded_data = script_tag.string[start:end]
                    encoded_ips.add(encoded_data)  # Add to the set

    driver.quit()  # Close the browser
    return list(encoded_ips)

def decode_ips(encoded_ips: List[str]) -> List[str]:
    """
    Decodes a list of Base64 encoded IP addresses.

    Args:
        encoded_ips (List[str]): A list of Base64 encoded IP addresses.

    Returns:
        List[str]: A list of decoded IP addresses.
    """
    return [base64.b64decode(ip).decode('utf-8') for ip in encoded_ips]

def main() -> None:
    """
    Main function to scrape and decode IP addresses from multiple pages.
    Saves the results in JSON format and execution time in a text file.
    """
    # Define the URLs to scrape
    urls = [f'http://free-proxy.cz/en/proxylist/main/{i}' for i in range(1, 6)]

    all_decoded_ips: Dict[str, List[str]] = {}
    start_time = time.time()  # Start the timer

    for index, url in enumerate(urls):
        # Extract and decode IPs from each URL
        encoded_ips = extract_encoded_ips_from_page(url)
        decoded_ips = decode_ips(encoded_ips)
        
        # Format the current time and create a save ID
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(start_time))
        save_id = f"save_id_{formatted_time}_{index + 1}"
        
        # Store the decoded IPs in the dictionary
        all_decoded_ips[save_id] = decoded_ips

    # Save the results to a JSON file in the current directory
    output_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(output_dir, 'encoded_ips.json'), 'w') as json_file:
        json.dump(all_decoded_ips, json_file, indent=4)

    # Calculate total execution time
    execution_time = time.time() - start_time
    formatted_execution_time = time.strftime("%H:%M:%S", time.gmtime(execution_time))

    # Save the execution time to a text file
    with open(os.path.join(output_dir, 'time.txt'), 'w') as time_file:
        time_file.write(formatted_execution_time)

if __name__ == "__main__":
    main()
