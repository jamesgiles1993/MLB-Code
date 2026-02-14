# %%
from U01Imports import *

# %%
def download_steamer():
# Download Steamer Projections
    ### Login
    # Set up the Chrome driver
    driver = webdriver.Chrome()
    
    # Open the login page
    driver.get('http://www.steamerprojections.com/index.php/login')

    time.sleep(3)
    
    # Extract username and password
    # Note: Set these in cmd prompt using setx STEAMER_USERNAME "{USERNAME}" and setx STEAMER_PASSWORD "{PASSWORD}"
    steamer_username = os.getenv("STEAMER_USERNAME")
    steamer_password = os.getenv("STEAMER_PASSWORD")
    
    # Find the username and password fields and fill them in
    username_field = driver.find_element(By.NAME, 'username')
    password_field = driver.find_element(By.NAME, 'password')

    username_field.send_keys(steamer_username)
    password_field.send_keys(steamer_password)

    time.sleep(1)
    
    # Submit the form
    password_field.send_keys(Keys.RETURN)
    
    
    
    ### Current-Year Projections
    # Step 1: Navigate to the page with the links
    driver.get('http://www.steamerprojections.com/index.php/projections/2025-projections')
    
    # Step 2: Find all the links on the page
    links = driver.find_elements(By.TAG_NAME, 'a')

    time.sleep(5)
    # Step 3: Filter links that contain "1168" in their href attribute (Pitchers)
    download_links = [link.get_attribute('href') for link in links if 'item_id=1168' in link.get_attribute('href')]
    
    # Step 4: Open each link to download the file
    time.sleep(5)
    driver.get(download_links[0])
    
    # Step 5: Filter links that contain "1167" in their href attribute (Hitters)
    download_links = [link.get_attribute('href') for link in links if 'item_id=1167' in link.get_attribute('href')]
    
    # Step 5: Open each link to download the file
    time.sleep(5)
    driver.get(download_links[0])
    
    
    
    ### Historical Projections
    # Step 1: Navigate to the page with the links
    driver.get('http://www.steamerprojections.com/index.php/projections/historical-weekly-logs')
    
    # Step 2: Find all the links on the page
    links = driver.find_elements(By.TAG_NAME, 'a')
    
    # Step 3: Filter links that contain "1138" in their href attribute (Pitchers)
    download_links = [link.get_attribute('href') for link in links if 'item_id=1138' in link.get_attribute('href')]
    
    # Step 4: Open each link to download the file
    time.sleep(5)
    driver.get(download_links[0])
    
    # Step 5: Filter links that contain "1137" in their href attribute (Hitters)
    download_links = [link.get_attribute('href') for link in links if 'item_id=1137' in link.get_attribute('href')]
    
    # Step 6: Open each link to download the file
    time.sleep(5)
    driver.get(download_links[0])
    
    
    ### Quit When Downloads are Finished
    # Wait for downloads to complete
    def downloads_done(download_dir):
        # Check for any files in the download directory with ".crdownload" extension (common for incomplete downloads)
        return not any([filename.endswith('.crdownload') for filename in os.listdir(download_dir)])
    
    # Poll the download directory until downloads are complete
    while not downloads_done(download_path):
        time.sleep(1)
    
    # Clean up
    driver.quit()


# %%
# Move Steamer Projections
def move_steamer():
    # Steamer Folder - will move files from downloads folder to here
    destination_folder = os.path.join(baseball_path, "A03. Steamer")
    
    # Find latest pitcher log download
    matching_files = glob.glob(os.path.join(download_path, "steamer_pitchers_weekly*"))
    
    # Move to destination folder
    if matching_files:
        most_recent_file = max(matching_files, key=os.path.getmtime)
        shutil.move(most_recent_file, os.path.join(destination_folder, os.path.basename(most_recent_file)))
        print(f"Moved '{most_recent_file}' to '{destination_folder}'.")
    else:
        print(f"No matching files found in '{download_path}'.")
    
    
    # Find latest hitter log download
    matching_files = glob.glob(os.path.join(download_path, "steamer_hitters_weekly*"))
    
    # Move to destination folder
    if matching_files:
        most_recent_file = max(matching_files, key=os.path.getmtime)
        shutil.move(most_recent_file, os.path.join(destination_folder, os.path.basename(most_recent_file)))
        print(f"Moved '{most_recent_file}' to '{destination_folder}'.")
    else:
        print(f"No matching files found in '{download_path}'.")
    
    # Find latest pitcher current download
    matching_files = glob.glob(os.path.join(download_path, "steamer_pitchers.csv"))
    
    # Move to destination folder
    if matching_files:
        most_recent_file = max(matching_files, key=os.path.getmtime)
        shutil.move(most_recent_file, os.path.join(destination_folder, os.path.basename(most_recent_file)))
        print(f"Moved '{most_recent_file}' to '{destination_folder}'.")
    else:
        print(f"No matching files found in '{download_path}'.")
    
    # Find latest hitter current download
    matching_files = glob.glob(os.path.join(download_path, "steamer_hitters.csv"))
    
    # Move to destination folder
    if matching_files:
        most_recent_file = max(matching_files, key=os.path.getmtime)
        shutil.move(most_recent_file, os.path.join(destination_folder, os.path.basename(most_recent_file)))
        print(f"Moved '{most_recent_file}' to '{destination_folder}'.")
    else:
        print(f"No matching files found in '{download_path}'.")


# %%
__all__ = [name for name in globals() if not name.startswith("_")]