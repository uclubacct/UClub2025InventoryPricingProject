"""
Developed by Colin W Fairbourn 2025 October 1

Automated Sysco Invoice Data Extraction and Sanitization Pipeline.

This program processes a multi-page PDF document containing scanned Sysco invoices. 
It uses image processing (OpenCV), visual hashing, and Optical Character Recognition 
(Tesseract) to isolate key data points (Item Codes, Unit Prices, Invoice Date, Account). 
The extracted data is then sanitized for consistency and stored in structured CSV files.

The pipeline ensures data quality through multiple checks:
1. Invoice Page Verification: Uses perceptual hashing to identify actual invoice sheets.
2. Temporal Validation: Sanitizes dates, ensuring chronological order and consistency.
3. Pricing Reconciliation: Cross-validates prices extracted from two separate columns 
   to correct OCR errors, using positional and substring matching.

Outputs include a final inventory DataFrame (`inv_info.csv`) and a separate log of 
any processing errors encountered (`error_info.csv`).

Dependencies:
  - fitz (PyMuPDF)
  - PIL (Pillow)
  - pytesseract
  - pandas
  - imagehash
  - numpy
  - opencv-python (cv2)
  - source (Local utility module)

Execution:
  - Requires Tesseract OCR to be installed and the path to the executable set correctly.
  - Requires predefined template images for visual hashing and boundary constants 
    in 'source.py'.
"""


## SETUP
import imagehash
import fitz
from PIL import Image
import pytesseract as tess
import pandas as pd
import shutil
from datetime import datetime
import io
import os
from master import source
import time
import warnings



warnings.filterwarnings(
  "ignore", 
  category=FutureWarning, 
  module="pandas"
) 







def main(ROOT):


  # Try to find tesseract in PATH
  tess_path = shutil.which("tesseract")

  # Fallback to default Windows install location
  if tess_path is None:
    default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_path):
      tess_path = default_path

  if tess_path:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = tess_path
  else:
    raise FileNotFoundError("Tesseract executable not found. Please add it to PATH or install it.")


  # Confirm Tesseract is working
  try: 
      tess.get_tesseract_version()
  except Exception as tesseract_error:
      print(f"Tesseract Error: {tesseract_error}")
  
  # sysco reference sheet
  ref_hash = imagehash.average_hash(Image.open(
    ROOT / "master" / "references" / "sysco_invoice_reference_1.png"))
  
  ## FILE OPENING
  input_folder = ROOT / "inputs" / "invoices"
  processed_path = input_folder / "processed_invoices"
  info_directory = ROOT / "master" / "inputs"
  error_directory = ROOT / "master" / "errors"
  input_files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]
  
  if len(input_files) < 1:
    print(f"No '.pdf' documents found in {input_folder}.")
    source.write_log(ROOT, "Ran 'reading_sysco_invoice.py' successfully.")
    return 0

  n_docs = len(input_files)
  start_time = time.time()
  error_info = []

  for doc_num, file in enumerate(input_files):
    # opening desired scanned file
    file_path = os.path.join(input_folder, file)    
    doc = fitz.open(
      file_path
    )

    ## INITIALIZATION OF VARIABLES
    date_list = []
    pricing_data = []

    n_pages = len(doc)

    # start timer
    print(f"Analyzing {n_pages} pages in doc {doc_num + 1}/{n_docs}, {file}")
    
    ## MAIN PROCESSING LOOP
    for page_num in range(n_pages):
      
      ## EXTRACTING INDIVIDUAL SHEET FROM PDF FORMAT
      img = doc[page_num].get_images(full = True)[0]
      image_bytes = doc.extract_image(img[0])["image"]
      img_pil = Image.open(io.BytesIO(image_bytes))


      ## ADD ETL AND PROGRESS DISPLAY HERE
      source.display_time(doc_num, page_num, start_time, n_pages, n_docs)
      

      ## ANALYZE INDIVIDUAL SHEET
      if source.is_invoice(img_pil, ref_hash):

        ## POLISHING UP IMAGE  
        invoice = source.polish_image(img_pil)
        height, width = invoice.shape

        # calculating general boundaries for cropping
        icup_area = [source.table_bounds * height, source.icup_bounds * width]
        up_area = [source.table_bounds * height, source.up_bounds * width]
        date_area = [source.d_height * height, source.d_width * width]
        ac_area = [source.ac_height * height, source.ac_width * width]

        
        ## Both ItemCodes and UnitPrices (icup) 
        icup_img = source.crop_image(invoice, icup_area, "icup")
        icup_pairs = source.extract_text(icup_img, source.icup_config, source.icup_regex)
        ## Unit Prices
        up_img = source.crop_image(invoice, up_area, "up")
        up_list = source.extract_text(up_img, source.up_config, source.up_regex)
        # sanitizing pricing
        pricing_error, new_pricing = source.sanitize_pricing(icup_pairs, up_list)

        ## Invoice Date
        date_img = source.crop_image(invoice, date_area, "LAST_UPDATE")
        date_text = source.extract_text(date_img, source.date_config, source.date_regex)
        # sanitizing and updating date_list
        date_error, date_page, date_list = source.sanitize_date(date_text, date_list)
        
        ## Invoice Account
        account_img = source.crop_image(invoice, ac_area, "account")
        account_text = source.extract_text(account_img, source.account_config, source.account_regex)
        # sanitizing account
        account_error, account_invoice = source.sanitize_account(account_text)
      

        # checking for errors on this page
        if any([pricing_error, date_error, account_error]):
          error_print = [
            f"--- ERROR in Document: {file} ---\n", 
            f"Data mismatch on page {int(page_num + 1)}:\n",
            f"\t- Pairs Detected: {len(icup_pairs)}\n",
            f"\t- Prices Detected: {len(up_list)}\n",
            f"\t- Invoice Date: {date_page}\n",
            f"\t- Account: {account_invoice}\n"
            ]
          error_out = {
            "DOC": file,
            "PAGE": int(page_num + 1),
            "PAIRS": len(icup_pairs),
            "PRICES": len(up_list),
            "DATE": date_page,
            "ACCOUNT": account_invoice
          }
          error_info.append(error_out)
          print("".join(error_print))
          print("")

        # add new_pricing to total 
        for row in new_pricing:
          pricing_data.append({
            "VENDOR_CODE": row["VENDOR_CODE"], 
            "UNIT_PRICE": row["UNIT_PRICE"], 
            "LAST_UPDATE": date_page, 
            "ACCOUNT": account_invoice,
            "PAGE": int(page_num + 1)
          })


    ## if we have finished analyzing a document, move that document from 
    # vendors/sysco/inputs into inputs\\processed
    doc.close()
    source.move_analyzed_document(file, input_folder, processed_path)

  
  if len(input_files) > 0:


    if not os.path.exists(info_directory):
      os.makedirs(info_directory)
    

    info_path = os.path.join(info_directory, "sysco_info.csv")
    
    # save inventory info
    inv_info = pd.DataFrame(
      pricing_data,
      columns = ["VENDOR_CODE", "PRICE", "LAST_UPDATE", "ACCOUNT","PAGE"])

    # --- 4. Group, Sort, and Select the Newest Row per Group (The Python Equivalent) ---

    # The most efficient and idiomatic way in pandas to get the newest row
    # for each group is to sort and then use drop_duplicates.

    newest_prices = inv_info \
      .sort_values(by='LAST_UPDATE', ascending=False) \
      .drop_duplicates(subset=['VENDOR_CODE'], keep='first')

    newest_prices.to_csv(info_path)


    if len(error_info) > 0:  
      if not os.path.exists(error_directory):
        os.makedirs(error_directory)
      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
      error_path = os.path.join(error_directory, "".join(["sysco_error", timestamp ,".csv"]))
      # save error info
      error_df = pd.DataFrame(
        error_info, columns = ["DOC", "PAGE", "PAIRS", "PRICES", "DATE", "ACCOUNT"])
      error_df.to_csv(error_path)

    # final cleanup message
    print("\nAnalysis complete. Results saved to CSV files.")

  source.write_log(ROOT, "Ran 'reading_sysco_invoice.py' successfully.")

  return 0



## EXECUTION BLOCK
if __name__ == "__main__":
  try:
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    main(ROOT)
  except Exception as e:
    print(e)
    source.write_log(ROOT, 
      f"Tried to run 'reading_sysco_invoice.py' and failed. Error: {e}")