import os
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
import urllib
import pandas as pd

all_data = []
last_index = 1

def download_images(image_url, filename, image_dir):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    cookies = {
        "_99-acs-token" : os.getenv('99_access_token'),
    }
    
    # Parsed the url
    parsed_url = urllib.parse.urlparse(image_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)

    # Ensure the 'url' parameter exists in query
    if 'url' in query_params:
        image_url = "https://www.99.co" + query_params['url'][0]  # Construct correct URL
    else:
        print(f"Skipping image {filename} - Invalid URL format: {image_url}")
        return
    
    # Make directory
    os.makedirs(image_dir, exist_ok=True)
    file_path = os.path.join(image_dir, filename)

    response = requests.get(query_params['url'][0], 
                            headers=headers, 
                            cookies=cookies, 
                            stream=True
                            )
    
    if response.status_code == 200:
         print(f'Success download images {filename}')
         with open(file_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
    else:
        print(f"Failed to download image. Status Code: {response.status_code}")


def scrapper(url, output_folder):
    global last_index

    # ChromeDriver path & options
    chrome_driver_path = "../chromedriver/chromedriver-linux64/chromedriver"
    chrome_service = Service(chrome_driver_path)
    chrome_options = Options()

    # Initialize
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(url)
    time.sleep(1)

    card_elements = driver.find_elements(By.CLASS_NAME, "cardSecondary")
    for index in range(len(card_elements)):
        try:
            # debug
            print(f'processing house : {last_index}')
            # Re fetch
            card_elements = driver.find_elements(By.CLASS_NAME, "cardSecondary")
            
            # Scroll
            driver.execute_script("arguments[0].scrollIntoView(true);", card_elements[index])
            time.sleep(1)

            # Download images
            image_element = card_elements[index].find_element(By.CSS_SELECTOR, ".cardSecondary__media img")
            image_url = image_element.get_attribute("src")

            # Create image directory
            image_dir = os.path.join(output_folder, f"images/image-rumah-{last_index}")
            os.makedirs(image_dir, exist_ok=True)

            image_name = f"image-{last_index}.jpg"

            download_images(image_url, image_name, image_dir)
            time.sleep(2)

            last_index += 1
            
            # Click
            card_elements[index].click()
            time.sleep(3)

            # Check if "Page Not Found" appears
            if driver.find_elements(By.CLASS_NAME, "ui-page-not-found__content"):
                print(f"Skipping card at index {index} - Page Not Found")
                driver.back()
                time.sleep(2)
                continue  # Skip further processing for this card

            # Extract Primary Data
            price = driver.find_element(By.CLASS_NAME, "listingPrice__tag").text
            title = driver.find_element(By.TAG_NAME, "h1").text
            address = driver.find_element(By.CLASS_NAME, "wrapper-address").text

            data = {
                "Price": price,
                "Title": title,
                "Address": address
            }

            # Extract overview attributes
            atributes = driver.find_element(By.CLASS_NAME, "listingOverview").find_elements(By.XPATH, "./div")
            for attribute in atributes:
                    count_div = attribute.find_element(By.XPATH, "./div").text
                    label_span = attribute.find_element(By.XPATH, "./span").text
                    data[label_span] = count_div

            # Attempt to click "Lihat Selengkapnya" and load additional table rows
            more_buttons = driver.find_elements(By.XPATH, "//button[span[text()='Lihat Selengkapnya']]")
            if more_buttons:
                try:
                    driver.execute_script("arguments[0].click();", more_buttons[0])
                    time.sleep(2)
                except Exception as e:
                    print("Error clicking 'Lihat Selengkapnya':", e)
            else:
                print("'Lihat Selengkapnya' button not found, skipping...")

            
            # Extract detailed table data
            table_rows = driver.find_elements(By.CSS_SELECTOR, ".wrapper-detail table tbody tr")
            for row in table_rows:
                headers = row.find_elements(By.CLASS_NAME, "attribute-table-header")
                descriptions = row.find_elements(By.CLASS_NAME, "attribute-table-description")
                if len(headers) == 2 and len(descriptions) == 2:
                    data[headers[0].text] = descriptions[0].text
                    data[headers[1].text] = descriptions[1].text


            # add image path
            data['image_path'] = image_dir

            # Add all data
            all_data.append(data)

            # Back
            driver.back()
            time.sleep(1)
        
        except Exception as e:
            print(f"Error processing card at index {index}: {e}")

    driver.quit()


def main():

    for i in range(1, 10, 1):
        print(f"halaman : {i}")
        url = f"https://www.99.co/id/jual/rumah/area-malang/merjosari?hlmn={i}&listingView=list"
        output_folder = "./dataset13"

        scrapper(url, output_folder)

        df = pd.DataFrame(all_data)
        output_file = os.path.join(output_folder, "scraped_data.csv")
        os.makedirs(output_folder, exist_ok=True)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')


if __name__ == "__main__":
    main()
