"""
algorithm

read in new items information
read in master list

loop through each file found in new_inputs
  loop through each item seen in an invoice
    if item in master list
      if item date is newer than master list update date
        update item price and update date
      else 
        ignore it
    else 
      add it to the list, fill in as much information, flag for manual review
"""








import pandas as pd
import os
from master import source








def main(ROOT):

  ## ESTABLISH FILE NAMES
  master_file = ROOT / "deliverables" / "master_pricing.csv"
  input_folder = ROOT / "master" / "inputs"
  output_folder = input_folder / "processed_inputs"
  archive_folder = ROOT / "master" / "archive"


  # Read in master list from deliverables
  master = pd.read_csv(master_file, dtype={'VENDOR_CODE': int})
  # make sure LAST_UPDATE is datetime
  master["LAST_UPDATE"] = pd.to_datetime(master["LAST_UPDATE"])  

  # --- Read in all new input files ---
  input_files = [f for f in os.listdir(input_folder) if f.endswith(".csv")]

  for file in input_files:
    new_pricing = pd.read_csv(input_folder / file, dtype={'VENDOR_CODE': int})
    new_pricing["LAST_UPDATE"] = pd.to_datetime(new_pricing["LAST_UPDATE"], errors="coerce")
    new_pricing = new_pricing.drop(["Unnamed: 0","PAGE"], axis = 1)

    # Loop through each row (new item)
    for _, item in new_pricing.iterrows():
      vendor_code = item["VENDOR_CODE"]

      if vendor_code in master["VENDOR_CODE"].values:
        # Get index of master row
        idx = master.index[master["VENDOR_CODE"] == vendor_code][0]
        new_date = item["LAST_UPDATE"]
        old_date = master.loc[idx, "LAST_UPDATE"]

        # Compare dates
        if new_date > old_date:
          # update
          master.loc[idx, "PRICE"] = item["PRICE"]
          master.loc[idx, "LAST_UPDATE"] = new_date
        
        master.loc[idx, "ACCOUNT"] = item["ACCOUNT"]

      else:
        # New item → add to master + flag
        item_dict = item.to_dict()
        item_dict["FLAG"] = "Needs Review"
        master = pd.concat([master, pd.DataFrame([item_dict])], 
                            ignore_index=True)

    # move invoice
    source.move_and_archive_document(file, input_folder, output_folder, remove = True)

  
    # --- 2. ENSURE DESTINATION DIRECTORY EXISTS ---
  if not os.path.exists(archive_folder):
    # Create destination and any necessary parent directories
    os.makedirs(archive_folder, exist_ok=True)
    print(f"Created destination directory: {"master\\archive\\"}")

  # move master list from master file to the archive
  source.move_and_archive_document(
    "master_pricing.csv",
    ROOT / "deliverables",
    archive_folder)

  # Save updated master list 
  master.to_csv(master_file, index=False)
  
  source.write_log(ROOT, "Ran 'update_pricing.py' successfully.")

  return 0





if __name__ == "__main__":
  try:
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    main(ROOT)
  except Exception as e:
    print(e)
    source.write_log(ROOT, 
      f"Tried to run 'update_pricing.py' and failed. Error: {e}")







