




import imagehash
import matplotlib.pyplot as plt
import pytesseract as tess
import numpy as np
import pandas as pd
import cv2
import re
import time
import os
import shutil
from datetime import datetime
from pathlib import Path



def write_log(ROOT, message, log_dir="logs", log_file="project.log"):
    """
    Appends a timestamped message to logs/project.log.
    Automatically creates the logs/ folder if missing.
    """

    ROOT = Path(ROOT)
    # Build full log directory path inside ROOT
    log_path = ROOT / log_dir
    log_path.mkdir(parents=True, exist_ok=True)

    # Build full path to the log file
    log_file_path = log_path / log_file

    # Format timestamp and message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}\n"

    # Append to log file
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(entry)





# these are the locations of the borders by proportion of page size
icup_bounds = np.array([14.9, 18.6]) / 27.94
up_bounds = np.array([16.8, 18.6]) / 27.94
table_bounds = np.array([4.1, 17.9]) / 21.59

d_width = np.array([15.8, 17.8]) / 27.94
d_height = np.array([0.9, 1.6]) / 21.59

ac_width = np.array([1, 6]) / 27.94
ac_height = np.array([1.1, 2.1]) / 21.59


# config for tesseract, detection of numbers from page into string format
icup_config = r'--oem 3 --psm 4 -c tessedit_char_whitelist=0123456789.' 
ic_config = r'--oem 3 --psm 4 -c tessedit_char_whitelist=0123456789'
up_config = r'--oem 3 --psm 4 -c tessedit_char_whitelist=0123456789.' 
date_config = r'--oem 3 --psm 4 -c tessedit_char_whitelist=0123456789/'
account_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist= ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# config for regex, decoding stringed numbers into lists of valid numbers
icup_regex = r'(\d{7})\s*(\d{,3}+\.\d{2,})'
ic_regex = r'\d{7}'
up_regex = r'\d+\.\d{2,}'
date_regex = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2}\b'
account_regex = r'(BAKERY|SNACK BAR|MSU)'




def polish_image(img_pil):
  """
  Applies a series of image processing steps (rotation, grayscale conversion, 
  and binary thresholding) to prepare a PIL Image object for text extraction 
  via Tesseract/OCR.

  The steps transform the image from a color Pillow object into a high-contrast, 
  monochrome OpenCV format that is oriented correctly for analysis.

  :param img_pil: The input image as a PIL Image object (expected to be an invoice page).
  :return: The processed image as a NumPy array (OpenCV format), 
            which is rotated, grayscaled, and binarized.
  """
  # convert to cv image
  img_cv = cv2.cvtColor((np.array(img_pil)), cv2.COLOR_RGB2BGR)
  # rotate to correct orientation so that cropping is less confusing
  img_rotated = cv2.rotate(img_cv, cv2.ROTATE_90_COUNTERCLOCKWISE)
  # grayscale
  img_gray = cv2.cvtColor(img_rotated, cv2.COLOR_RGB2GRAY)
  # contrast threshold
  _, polished = cv2.threshold(img_gray, 150, 255, cv2.THRESH_BINARY)

  return polished



def is_invoice(img, ref_hash, threshold = 21):
  """
  Determines if an image contains an actual invoice with desired information 
  by comparing its perceptual hash to a reference hash.

  This function calculates the average hash of the input image and checks 
  if the absolute difference between the two hashes is below a specified 
  threshold, indicating perceptual similarity.

  :param img: The PIL Image object of the current page to be checked.
  :param ref_hash: The pre-calculated average hash (imagehash.ImageHash) 
                    of a known reference invoice template.
  :param threshold: The maximum allowed difference between the two hashes 
                    for the image to be considered a match (default is 21).
  :return: True if the image is perceptually similar to the reference invoice 
            (i.e., hash difference is less than the threshold), False otherwise.
  """
  h = imagehash.average_hash(img)
  return abs(h - ref_hash)  < threshold



def crop_image(invoice, bounds, crop_type, debug=False):
  """
  Crops an invoice image based on predefined proportional boundaries and then 
  refines the crop using OpenCV contour detection and filtering.

  The function uses type-specific heuristics (TUNING) to identify and isolate 
  relevant text blocks for OCR. The refinement either aggregates all valid 
  contours ('aggregate') or targets the largest one ('single').

  :param invoice: The polished (rotated, grayscaled, binarized) OpenCV image 
                  (NumPy array) of the invoice page.
  :param bounds: A list or tuple containing two NumPy arrays: 
                  [height_bounds_in_pixels, width_bounds_in_pixels].
  :param crop_type: A string identifying the type of data being cropped 
                    (e.g., "icup", "up", "date", "account").
  :param debug: Boolean flag. If True, various debugging windows are displayed 
                to visualize contour detection and filtering.
  :return: The final, tightly cropped image as a NumPy array (OpenCV format).
  """

  # 1. Define Heuristics based on Type and Behavior
  TUNING = {
    "icup": {
      "min_w": 100, "max_w": 250, "min_h": 750,
      "max_h": 1250, "action": "aggregate"},
    "ic": {
      "min_w": 100, "max_w": 250, "min_h": 750,
      "max_h": 1250, "action": "single"},
    "up": {
      "min_w": 75, "max_w": 250, "min_h": 750, 
      "max_h": 1250, "action": "single"},
    "date": {
      "min_w": 100, "max_w": 200, "min_h": 20, 
      "max_h": 30, "action": "single"}, 
    "account": {
      "min_w": 0, "max_w": 0, "min_h": 0, 
      "max_h": 0, "action": "bypass"}, 
    "default": {
      "min_w": 10, "max_w": 200, "min_h": 10, 
      "max_h": 50, "action": "single"},
  }
  
  params = TUNING.get(crop_type, TUNING["default"])
  min_width = params["min_w"]
  max_width = params["max_w"]
  min_height = params["min_h"]
  max_height = params["max_h"] 
  action = params["action"]

  heights, widths = bounds

  # 2. Initial Crop
  initial = invoice[
    int(heights[0]):int(heights[1]),
    int(widths[0]):int(widths[1])]

  h_initial, w_initial = initial.shape[:2]
  if h_initial == 0 or w_initial == 0:
    return initial

  if action == "bypass":
    return initial
  
  # -----------------------------------
  # DEBUG SETUP BLOCK
  # -----------------------------------
  if debug:
    window_name = f"Per-Contour Debug: {crop_type.upper()}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    MIN_DISPLAY_WIDTH = 300
    target_width = max(w_initial, MIN_DISPLAY_WIDTH)
    aspect_ratio = h_initial / w_initial if w_initial > 0 else 1
    target_height = int(target_width * aspect_ratio)

    cv2.resizeWindow(window_name, target_width, target_height)
  # -----------------------------------
  
  # 3. Find Contours
  contour_input = initial
  contours, _ = cv2.findContours(
    contour_input, 
    cv2.RETR_EXTERNAL, 
    cv2.CHAIN_APPROX_SIMPLE)
  
  valid_contours_bounds = [] 
  
  # 4. Filter Contours (THE NITTY-GRITTY)
  for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    
    # Filtering check
    passed_filter = all([
      w >= min_width,
      w <= max_width,
      h >= min_height,
      h <= max_height])
    
    # -----------------------------------
    # PER-CONTOUR VISUALIZATION BLOCK
    # -----------------------------------
    if debug:
      # 1. Recreate the base image for clean drawing on this step
      base_draw_image = cv2.cvtColor(initial, cv2.COLOR_GRAY2BGR)
      
      # 2. Draw all previously ACCEPTED contours (Green)
      for _, px, py, pw, ph in valid_contours_bounds:
        # Green in BGR is (0, 255, 0)
        cv2.rectangle(base_draw_image, (px, py), (px + pw, py + ph), (0, 255, 0), 4)

      # 3. Draw the CURRENT contour being evaluated
      if passed_filter:
        # Accepted: Draw in Blue
        color = (255, 0, 0) 
        cv2.rectangle(base_draw_image, (x, y), (x + w, y + h), color, 4)
        valid_contours_bounds.append((cv2.contourArea(contour), x, y, w, h)) 
      else:
        # Rejected: Draw in Red
        color = (0, 0, 255) 
        cv2.rectangle(base_draw_image, (x, y), (x + w, y + h), color, 4)
          
      cv2.imshow(window_name, base_draw_image)
      
      key = cv2.waitKey(10) # Wait 10ms
      if key == ord('q'):
        break

    else:
      # Execute filtering logic without drawing if debug is False
      if passed_filter:
        valid_contours_bounds.append((cv2.contourArea(contour), x, y, w, h)) 
    # -----------------------------------
  
  # -----------------------------------
  # DEBUG CLEANUP
  # -----------------------------------
  if debug:
    cv2.destroyWindow(window_name)
  # -----------------------------------

  pad = 1

  # 5. Determine Final Crop Coordinates (Calculation remains the same)
  if not valid_contours_bounds:
    return initial

  # 6. Final Crop Bounding Box Calculation
  if action == "aggregate":
    all_x, all_y, all_w, all_h = zip(*[(c[1], c[2], c[3], c[4]) for c in valid_contours_bounds])
    
    x_min_agg = min(all_x)
    y_min_agg = min(all_y)
    x_max_agg = max(np.array(all_x) + np.array(all_w))
    y_max_agg = max(np.array(all_y) + np.array(all_h))

    x_min, y_min = x_min_agg, y_min_agg
    x_max, y_max = x_max_agg, y_max_agg
  else:
    valid_contours_bounds.sort(key=lambda item: item[0], reverse=True)
    _, x, y, w, h = valid_contours_bounds[0]
    
    x_min, y_min = x, y
    x_max, y_max = x + w, y + h

  # 7. Apply Padding and Final Crop
  final_x_min = max(0, x_min - pad)
  final_y_min = max(0, y_min - pad)
  final_x_max = min(w_initial, x_max + pad)
  final_y_max = min(h_initial, y_max + pad)

  final_cropped = initial[final_y_min:final_y_max, final_x_min:final_x_max]
  
  return final_cropped



def extract_text(img, tess_config, regex):
  """
  Performs Optical Character Recognition (OCR) on a processed image segment 
  using Tesseract and then filters the raw output using a regular expression.

  This function converts image data into raw text and then extracts only the 
  data that matches the defined pattern (e.g., item codes, prices, dates).

  :param img: The processed image segment (NumPy array) containing the target text.
  :param tess_config: The Tesseract configuration string, typically defining 
                      the OCR engine, page segmentation mode, and character whitelist.
  :param regex: The regular expression string used to find and extract the 
                final desired text pattern(s) from the raw Tesseract output.
  :return: A list of strings, or tuples of strings, containing all matches 
           found by the regular expression.
  """
  # text analysis
  text = tess.image_to_string(img, config = tess_config)
  formatted = re.findall(regex, text)

  return formatted



def sanitize_pricing(icup_pairs, up_list):
  """
  Reconciles item code and unit price pairs by correcting potentially truncated or 
  misread prices from a combined extraction (ItemCode + UnitPrice) using the more 
  accurate prices obtained from a single-column UnitPrice extraction.

  The reconciliation is only performed if a missing price from the 'up_list' 
  is a substring of a price in 'icup_pairs' AND their indices (row positions) align,
  ensuring they belong to the same invoice line item.

  :param icup_pairs: List of tuples (str ItemCode, str UnitPrice) extracted from 
                      the combined column, preserving row order.
  :param up_list: List of str UnitPrice extracted from the single price column, 
                  preserving row order.
  :return: A tuple containing:
            - error (bool): if any price failed final float conversion.
            - new_rows (list): A list of dictionaries ready to be converted into 
                              DataFrame rows, with reconciled 'ItemCode' and 'UnitPrice' 
                              (as floats).
  """
  error = False
  # Convert unit prices in up_list to floats for consistent comparison
  up_list_floats = [float(up) for up in up_list]

  # The unit prices already found through the icup extraction
  prices_from_icup = set(float(up) for _, up in icup_pairs)

  # Dictionary to store a potential index match: {index_in_up_list: index_in_icup_pairs}
  index_matches = {}

  # 1. Find the index where the up_list price is missing in the icup_pairs prices
  for i, miss_price in enumerate(up_list_floats):
    
    # Check if this price from the 'up' column is missing from the 'icup' pairs
    if miss_price not in prices_from_icup:
      
      # 2. Search through icup_pairs for a substring match at the SAME INDEX
      for j, (ic, up) in enumerate(icup_pairs):
        match_price = float(up)
        
        str_miss = str(miss_price)
        str_match = str(match_price)
        
        # Check for substring relationship
        if str_miss in str_match or str_match in str_miss:
          
          # 3. CRITICAL CHECK: Does the index align?
          if i == j:
            
            # We found a match that aligns by both price (substring) and position (index)
            # We only store the *first* aligned match; this logic assumes the missing 
            # price is the correction for the icup price at the same index.
            
            # Store the index in icup_pairs (j) and the corrected price (miss_price)
            index_matches[j] = miss_price
            break # Move to the next missing price in up_list

  # 4. Update the original icup_pairs with the corrected prices
  updated_icup_pairs = list(icup_pairs) # Create a mutable copy

  for idx, corrected_price in index_matches.items():
    
    # Update the UnitPrice at the matching index
    item_code, _ = updated_icup_pairs[idx]
    updated_icup_pairs[idx] = (item_code, corrected_price)


  # 5. Finalize data and append to DataFrame
  # This replaces the entire previous 'best_matches' dictionary creation and usage.
  new_rows = []
  for item_code, unit_price in updated_icup_pairs:
    
    # Ensure the price is a float before appending
    try:
      final_price = float(unit_price)
    except ValueError:
      # Handle cases where even the reconciled price might not be a valid number
      error = True
      continue # Skip this row

    new_rows.append({
        "VENDOR_CODE": item_code, 
        "UNIT_PRICE": final_price
    })
  

  return error, new_rows



def sanitize_date(date_text, date_list):
  """
  Validates and standardizes the extracted invoice date, ensuring temporal 
  consistency across multiple pages of an invoice document.

  If a date is found, it's checked against the last known date. If the new 
  date is more than two weeks after the last known date, the last known date 
  is used to prevent large chronological jumps due to extraction errors. If no 
  date is found and it's the first page, a fallback date is used, setting an 
  error flag.

  :param date_text: The raw date string extracted from the current page.
  :param date_list: A list containing all previously confirmed and sanitized 
                    datetime objects from prior pages.
  :return: A tuple containing:
            - error (bool): True if a fallback date (last week's date) was used, 
                            False otherwise.
            - date_invoice (pandas.Timestamp): The final, sanitized date for the 
                                              current page.
            - date_list (list): The updated list of sanitized dates, including 
                                the date from the current page.
  """
  error = False
  # first date discovered
  if date_text and not date_list:
    # hope beyond hope that we identified the date correctly
    date_invoice = pd.to_datetime(date_text[0])

  # new date, check to see if it's within reason of the last date found
  elif date_text:
    try:
      # it's possible that the date read is an invalid date, at which point
      # it should not pass this next line 
      date_invoice = pd.to_datetime(date_text[0])
      last_date = pd.to_datetime(date_list[-1])
      more_1_month = (last_date + pd.DateOffset(weeks = 2) < date_invoice)
      date_invoice = last_date if more_1_month else date_invoice

    except ValueError:
      # if we found an invalid date, just use the last date found
      date_invoice = date_list[-1]
  
  # no date was found, use last date found if possible
  elif not date_text and date_list:
    date_invoice = date_list[-1]

  # no date has been found up to this point
  else:
    # use last week's date as a relatively close guess
    error = True
    date_invoice = pd.to_datetime('today') - pd.DateOffset(weeks = 1)

  date_list.append(date_invoice)

  return error, date_invoice, date_list



def sanitize_account(account_text):
  """
  Cleans and standardizes the extracted account text into a final, usable 
  account identifier.

  Specifically, it maps the extracted text "MSU" to "KITCHEN" and sets an 
  error flag if no account text is found. It assumes the account is the 
  first element of the input list.

  :param account_text: A list of strings, where the first element is expected 
                        to be the raw account identifier extracted from the 
                        invoice page.
  :return: A tuple containing:
            - error (bool): True if no account text was found, False otherwise.
            - account_invoice (str or None): The standardized account name 
                                            ("KITCHEN", other found name, or None).
  """
  
  error = False
  account_invoice = None

  if account_text:
    account_invoice = "KITCHEN" if account_text[0] == "MSU" else account_text[0]
  else:
    error = True
  return error, account_invoice



def display_time(doc_num, page_num, start_time, n_pages, n_docs):
  """
  Calculates and displays the current processing progress, including 
  percentage, elapsed time, and estimated time left (ETL), across multiple documents.

  The output is printed to the console and is updated on the same line 
  using the carriage return (\r) character.

  :param doc_num: The zero-based index of the current document being processed.
  :param page_num: The zero-based index of the current page within the document.
  :param start_time: The time (in sec since the epoch) when the processing loop started.
  :param n_pages_per_doc: The number of pages in EACH document (since they are assumed equal).
  :param n_docs: The total number of documents to be processed.
  :return: None. The function prints the progress directly to the console.
  """

  # helper function for converting time into a human-readable format
  def format_time(seconds):
    """
    Converts a duration in seconds into a human-readable string format.
    """

    # Format the time (e.g., 00:00:15 for 15 seconds)
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    
    # Only display hours if they are greater than zero
    if hours > 0:
      return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"
  
  # --- UPDATED LOGIC FOR MULTI-DOCUMENT TRACKING ---
    
  # Calculate the total number of pages across ALL documents
  total_pages = n_docs * n_pages
  
  # Calculate the total number of pages processed so far:
  # Pages from completed documents + pages from the current document
  completed_pages = doc_num * n_pages
  curr_page_total = completed_pages + (page_num + 1) # page_num is 0-based

  # calculate elapsed time and pages per second
  elapsed_time = time.time() - start_time
  # avoid division by zero
  pages_per_sec = curr_page_total / elapsed_time if elapsed_time > 0 else 0
  
  # estimate time left (ETL)
  remaining_pages = total_pages - curr_page_total
  est_secs_left = remaining_pages / pages_per_sec if pages_per_sec > 0 else 0
  
  elapsed_formatted = format_time(elapsed_time)
  etl_formatted = format_time(est_secs_left)
  
  # Overall progress percentage
  progress_percent = (curr_page_total / total_pages) * 100

  # --- DISPLAY UPDATE ---
  
  # Display the progress, including document and page context
  print(
      f"Processing Document {doc_num + 1}/{n_docs} | Page {page_num + 1}/{n_pages} | "
      f" - Total Pages: {curr_page_total}/{total_pages} | "
      f" - {progress_percent:.1f}% | "
      f" - ETL: {etl_formatted} | "
      f" - Elapsed: {elapsed_formatted}",
      end='\r'
  )



def move_analyzed_document(filename, origin_dir, destination_dir):
  """
  Moves a specified file from the origin directory to the destination directory.

  This function is generalized to handle any file movement by taking 
  the full source and destination directories as arguments.

  Args:
      filename (str): The name of the file to move (e.g., 'invoice_1234.pdf').
      origin_dir (str): The full path to the directory where the file currently resides.
                        Example: 'vendors/sysco/inputs'
      destination_dir (str): The full path to the directory where the file should be moved.
                              Example: 'inputs/processed'
  """
  
  # Construct the full source path: origin_dir/filename
  source_path = os.path.join(origin_dir, filename)

  # Construct the full destination path: destination_dir/filename
  destination_path = os.path.join(destination_dir, filename)

  # Ensure the destination directory exists
  if not os.path.exists(destination_dir):
    # Use exist_ok=True to prevent an error if the directory already exists 
    # (though the check above handles that), and parents=True to create 
    # any necessary parent directories.
    os.makedirs(destination_dir, exist_ok=True)
    print(f"Created destination directory: {destination_dir}")

  try:
    # Move the file using shutil.move()
    shutil.move(source_path, destination_path)
    print(f"Successfully moved: {filename}")
    print(f"From: {source_path}")
    print(f"To: {destination_path}")

  except FileNotFoundError:
    print(f"Error: Source file not found at {source_path}")
  except Exception as e:
    print(f"An unexpected error occurred while moving the file: {e}")

  print("")

  
def move_and_archive_document(filename, origin_dir, destination_dir, remove = False):
  """
  Copies a specified file from the origin directory to the destination directory,
  appending a datetime stamp to the copied file's name. The original file
  remains in the origin directory.

  Args:
      filename (str): The name of the file to move (e.g., 'invoice_1234.pdf').
      origin_dir (str): The full path to the directory where the file currently resides.
                        Example: 'vendors/sysco/inputs'
      destination_dir (str): The full path to the directory where the file should be moved.
                              Example: 'inputs/processed'
  """
  
  # --- 1. PREPARE PATHS AND TIMESTAMP ---

  # Get the current datetime in a safe format (e.g., YYYYMMDD_HHMMSS)
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

  # Separate the filename into name and extension
  name, ext = os.path.splitext(filename)
  
  # Create the new filename: name_timestamp.ext
  new_filename = f"{name}_{timestamp}{ext}"

  # Construct the full source path (the original file)
  source_path = os.path.join(origin_dir, filename)

  # Construct the full destination path with the new filename
  destination_path = os.path.join(destination_dir, new_filename)


  # --- 2. ENSURE DESTINATION DIRECTORY EXISTS ---
  if not os.path.exists(destination_dir):
      # Create destination and any necessary parent directories
      os.makedirs(destination_dir, exist_ok=True)
      print(f"Created destination directory: {destination_dir}")

    # --- 3. COPY THE FILE ---
  try:
      shutil.copy2(source_path, destination_path)
      print(f"Archived: {filename} → {destination_path}")

      # --- 4. OPTIONALLY REMOVE ORIGINAL ---
      if remove:
          os.remove(source_path)
          print(f"Removed original file from: {origin_dir}")
      else:
          print(f"Original file retained in: {origin_dir}")

  except FileNotFoundError:
      print(f"Error: Source file not found at {source_path}")
  except Exception as e:
      print(f"Unexpected error while archiving {filename}: {e}")

  print("")
  return



def compile_images(images):
  """
  Compiles a list of processed image segments (e.g., cropped sections 
  for codes, prices, dates) into a single horizontal figure for visual 
  inspection or debugging.

  Each image is displayed in grayscale with its axes turned off.

  :param images: A list of NumPy arrays (OpenCV/Matplotlib images) 
                 representing the different cropped sections.
  :return: A Matplotlib Figure object containing all images in a single subplot row.
  """

  n = len(images)
  fig, axs = plt.subplots(1, n, figsize = (5*n, 5))

  for i, img in enumerate(images): 
    axs[i].imshow(img, cmap = "gray")

  for ax in axs:
    ax.axis("off")

  plt.tight_layout()
  
  return fig

