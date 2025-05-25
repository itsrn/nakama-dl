import feedparser
import requests
from bs4 import BeautifulSoup
import os
import rarfile
from PIL import Image
import yaml
import time
from datetime import datetime, timedelta
import logging
from mega import Mega

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration Loading ---


def load_config(config_path='config.yml'):
    """Loads configuration from a YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logging.info("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logging.error(
            f"Config file '{config_path}' not found. Please create it.")
        exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing config file: {e}")
        exit(1)


config = load_config()

RSS_FEED_URL = config.get('rss_feed_url')
OUTPUT_PDF_DIR = config.get('output_pdf_directory')
CHAPTER_KEYWORD = config.get('chapter_keyword', 'צ\'אפטר')
CHECK_INTERVAL_MINUTES = config.get('check_interval_minutes', 60)
MAX_AGE_HOURS = config.get('max_age_hours', 24)

TEMP_DIR = os.path.join(os.getcwd(), 'temp_downloads')
os.makedirs(TEMP_DIR, exist_ok=True)  # Ensure temp directory exists

PROCESSED_CHAPTERS_FILE = os.path.join(os.getcwd(), 'processed_chapters.txt')

def load_processed_chapters():
    """Loads the list of already processed chapter URLs from file."""
    if not os.path.exists(PROCESSED_CHAPTERS_FILE):
        return set()
    
    try:
        with open(PROCESSED_CHAPTERS_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        logging.error(f"Error loading processed chapters file: {e}")
        return set()

def save_processed_chapter(post_url):
    """Saves a successfully processed chapter URL to file."""
    try:
        with open(PROCESSED_CHAPTERS_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{post_url}\n")
        logging.info(f"Saved URL to processed chapters file: {post_url}")
    except Exception as e:
        logging.error(f"Error saving to processed chapters file: {e}")

# --- Helper Functions ---


def download_file(url, destination_path):
    """Downloads a file from a given URL to a destination path."""
    logging.info(f"Attempting to download from: {url}")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an exception for HTTP errors
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0

        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded_size += len(chunk)
                # You can add a progress bar here if needed
        logging.info(f"Downloaded: {destination_path}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading {url}: {e}")
        return False


def extract_rar(rar_path, extract_to_path):
    """Extracts a RAR archive."""
    logging.info(f"Extracting RAR: {rar_path} to {extract_to_path}")
    try:
        with rarfile.RarFile(rar_path, 'r') as rf:
            rf.extractall(path=extract_to_path)
        logging.info(f"Successfully extracted to: {extract_to_path}")
        return True
    except rarfile.RarCannotExec as e:
        logging.error(
            f"UnRar executable not found or not in PATH. Please install 'unrar': {e}")
        return False
    except rarfile.BadRarFile as e:
        logging.error(f"Bad RAR file: {rar_path} - {e}")
        return False
    except Exception as e:
        logging.error(f"Error extracting RAR {rar_path}: {e}")
        return False


def images_to_pdf(image_folder, output_pdf_path, chapter_number):
    """Converts a folder of images to a single PDF, maintaining order."""
    logging.info(
        f"Converting images in {image_folder} to PDF: {output_pdf_path}")
    image_files = [f for f in os.listdir(
        image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    # Sort files naturally based on chapter number and page number
    # Assumes filenames like cXXXX_pYY.jpg
    def sort_key(filename):
        parts = os.path.splitext(filename)[0].split('_p')
        if len(parts) == 2:
            try:
                return (int(parts[0].replace('c', '')), int(parts[1]))
            except ValueError:
                pass  # Fallback to default sort if parsing fails
        return filename

    image_paths = sorted([os.path.join(image_folder, f)
                         for f in image_files], key=sort_key)

    if not image_paths:
        logging.warning(
            f"No valid images found in {image_folder} to create PDF.")
        return False

    images = []
    for path in image_paths:
        try:
            img = Image.open(path).convert('RGB')
            images.append(img)
        except Exception as e:
            logging.error(f"Could not open image {path}: {e}")

    if images:
        try:
            images[0].save(output_pdf_path, save_all=True,
                           append_images=images[1:])
            logging.info(f"PDF created successfully at: {output_pdf_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving PDF {output_pdf_path}: {e}")
            return False
    else:
        logging.warning("No valid images to create PDF.")
        return False


def get_mega_file_url(post_url):
    """Fetches the Mega.nz link from the chapter post."""
    logging.info(f"Fetching Mega.nz link from: {post_url}")
    try:
        response = requests.get(post_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all <a> tags that contain "mega.nz" in their href inside the chapter post
        mega_links = [a['href'] for a in soup.find_all(
            'a', href=True) if 'mega.nz' in a['href']]

        if mega_links:
            logging.info(f"Found Mega.nz link: {mega_links[0]}")
            return mega_links[0]
        else:
            logging.warning(f"No Mega.nz link found on post: {post_url}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching post {post_url}: {e}")
        return None


def download_from_mega(mega_url, destination_folder):
    """Downloads a file from Mega.nz using mega.py."""
    logging.info(f"Attempting to download from Mega: {mega_url}")
    try:
        m = Mega().login()  # Anonymous login for public links
        filename = m.download_url(mega_url, dest_path=destination_folder)

        destination_path = os.path.join(
            destination_folder, filename) if filename else None

        # Give some time for file handles to be released
        time.sleep(5)

        if destination_path and os.path.exists(destination_path):
            logging.info(
                f"Successfully downloaded '{filename}' from Mega to '{destination_folder}'.")
            return destination_path, filename
        else:
            logging.error(f"Download failed for Mega URL: {mega_url}")
            return None, None

    except Exception as e:
        if 'WinError 32' in str(e):
            # If we get access error, wait and check if file exists
            time.sleep(5)
            # Look for .rar files in destination folder
            rar_files = [f for f in os.listdir(
                destination_folder) if f.endswith('.rar')]
            if rar_files:
                # Take the most recently modified file
                latest_rar = max(rar_files, key=lambda x: os.path.getmtime(
                    os.path.join(destination_folder, x)))
                destination_path = os.path.join(destination_folder, latest_rar)
                logging.info(
                    f"Found downloaded RAR despite access error: {latest_rar}")
                return destination_path, latest_rar

        logging.error(f"Error downloading from Mega {mega_url}: {e}")
        return None, None


def get_chapter_number_from_filename(filename):
    """Extracts chapter number from filename like 'cXXXX.rar'."""
    try:
        name_parts = os.path.splitext(filename)[0]  # cXXXX
        if name_parts.startswith('c') and name_parts[1:].isdigit():
            return int(name_parts[1:])
        return None
    except Exception as e:
        logging.error(f"Could not extract chapter number from {filename}: {e}")
        return None


def get_chapter_number_from_title(title):
    """Extracts chapter number from the RSS entry title."""
    try:
        # Looking for patterns like "צ'אפטר 1234" or similar
        import re
        match = re.search(r'\d+', title)
        if match:
            return int(match.group())
        return None
    except Exception as e:
        logging.error(
            f"Error extracting chapter number from title '{title}': {e}")
        return None


def process_new_chapter(post_link):
    """Main logic to process a new chapter."""
    logging.info(f"Processing new chapter from post: {post_link}")

    # 1. Get Mega.nz link
    mega_link = get_mega_file_url(post_link)
    if not mega_link:
        return False

    # 2. Download RAR from Mega
    temp_rar_path, rar_filename = download_from_mega(mega_link, TEMP_DIR)
    if not temp_rar_path:
        return False

    chapter_number = get_chapter_number_from_filename(rar_filename)
    if chapter_number is None:
        logging.error(
            f"Could not determine chapter number from RAR filename: {rar_filename}. Skipping.")
        os.remove(temp_rar_path)  # Clean up
        return False

    chapter_temp_extract_dir = os.path.join(
        TEMP_DIR, f'chapter_{chapter_number}')
    os.makedirs(chapter_temp_extract_dir, exist_ok=True)

    # 3. Extract RAR
    if not extract_rar(temp_rar_path, chapter_temp_extract_dir):
        os.remove(temp_rar_path)  # Clean up failed download
        return False

    # 4. Remove downloaded RAR file
    try:
        os.remove(temp_rar_path)
        logging.info(f"Removed temporary RAR file: {temp_rar_path}")
    except OSError as e:
        logging.error(f"Error removing RAR file {temp_rar_path}: {e}")

    # 5. Create PDF
    # Format as One Piece - 0XXX.pdf
    pdf_filename = f"One Piece - {chapter_number:04d}.pdf"
    final_pdf_path = os.path.join(OUTPUT_PDF_DIR, pdf_filename)

    if not images_to_pdf(chapter_temp_extract_dir, final_pdf_path, chapter_number):
        return False

    # 6. Clean up temporary extracted chapter folder
    try:
        import shutil
        shutil.rmtree(chapter_temp_extract_dir)
        logging.info(
            f"Removed temporary extraction directory: {chapter_temp_extract_dir}")
    except OSError as e:
        logging.error(
            f"Error removing temporary directory {chapter_temp_extract_dir}: {e}")

    # 7. Save to processed chapters
    save_processed_chapter(post_link)

    logging.info(
        f"Successfully processed chapter {chapter_number}. PDF saved to {final_pdf_path}")
    return True

# --- Main Watchdog Loop ---


def watch_rss_feed():
    """Continuously watches the RSS feed for new chapters."""
    logging.info(
        f"Starting RSS feed watcher. Checking every {CHECK_INTERVAL_MINUTES} minutes...")
    processed_urls = load_processed_chapters()  # Load previously processed URLs

    while True:
        try:
            feed = feedparser.parse(RSS_FEED_URL)
            if not feed.entries:
                logging.warning("No entries found in RSS feed.")

            for entry in feed.entries:
                # Check if entry is within MAX_AGE_HOURS
                published_time = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed))
                if datetime.now() - published_time > timedelta(hours=MAX_AGE_HOURS):
                    continue

                # Check for chapter keyword and if already processed
                if CHAPTER_KEYWORD.lower() in entry.title.lower():
                    if entry.link not in processed_urls:
                        logging.info(f"New chapter post detected: '{entry.title}'")
                        if process_new_chapter(entry.link):
                            processed_urls.add(entry.link)
                        else:
                            logging.error(f"Failed to process chapter from '{entry.link}'. Will retry on next loop.")
                    else:
                        logging.debug(f"Chapter already processed: '{entry.title}'")

        except Exception as e:
            logging.error(f"An error occurred during RSS feed check: {e}")

        logging.info(f"Sleeping for {CHECK_INTERVAL_MINUTES} minutes...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    watch_rss_feed()
