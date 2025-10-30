"""
This is a program that will read in our current excel document that we're 
  using for inventory purposes, and to analyze it for each specific item, 
  note duplicate items, note vendor codes, and note which sections of our 
  inventory these items are stored in

"""



import pandas as pd
import json
from master import source
import os




# initializing dictionaries
master_dict = {}
misc_dict = {}


def update_master(master_key, row, curr_section, order):
  # have we seen this item code before?
  if master_key not in master_dict:
    # if not, add this as a new item to master_dict
    master_dict[master_key] = {
      "ITEM_DESC": [str(row["ITEM_DESC"]).upper()],
      "SECTIONS": [[curr_section, order]],
      "PRICES": [row["PRICE"]],
      "UNIT": [row["UNIT"]],
      "QUANTITY": [row["QUANTITY"]],
    }

  else: 
    # we have seen this item code before, append it's information
    vcode_info = master_dict[master_key]
    vcode_info['ITEM_DESC'].append(str(row["ITEM_DESC"]).upper())
    vcode_info['SECTIONS'].append([curr_section, order])
    vcode_info['PRICES'].append(row["PRICE"])
    vcode_info['UNIT'].append(row["UNIT"])
    vcode_info['QUANTITY'].append(row["QUANTITY"])
  
  return

def update_misc(misc_key, row, curr_section, order):
  # check to see if this item description is in misc_dict
  if misc_key not in misc_dict:
    # add new item description to dict
    misc_dict[misc_key] = {
      "SECTIONS": [[curr_section, order]],
      "PRICES": [row["PRICE"]],
      "UNIT": [row["UNIT"]],
      "QUANTITY": [row["QUANTITY"]],
    }

  else:
    # we've seen this item desc before, append info
    item_info = misc_dict[misc_key]
    item_info['SECTIONS'].append([curr_section, order])
    item_info['PRICES'].append(row["PRICE"])
    item_info['UNIT'].append(row["UNIT"])
    item_info['QUANTITY'].append(row["QUANTITY"])

  return



def main(ROOT):


  input_folder = ROOT / "inputs" / "inventories"
  processed_folder = input_folder / "processed_inventories"
  schemas_folder = ROOT / "master" / "schemas"
  archive_folder = schemas_folder / "archive"

  # look for files in inputs/inventories
  input_files = [f for f in os.listdir(input_folder) if f.endswith(".xlsx")]
  # if xlsx file is found in inventories, open that filename and run
  if len(input_files) < 1:
    source.write_log(ROOT, "Ran 'reading_inventory.py' successfully.")
    return 0

  ## FILE OPENING
  df = pd.read_excel(input_folder / input_files[0])

  # only grab the first 11 columns because that's what we can handle
  df = df.iloc[:, :11]

  df.columns = [
    "INDEX", "VENDOR/BRAND", "VENDOR_CODE", "ITEM_DESC", "UNIT", "PACK", 
    "PER_PACK", "PRICE", "QUANTITY", "EST_PRICE", "TOTAL_EST_VALUE"
    ]

  section_areas = [
    "MK WALK IN", "MK BLUE RACK", "MK 4 DOOR FREEZER", "MK HOT LINE", 
    "MK HOT LINE FREEZER", "MK BACK SHELF", "UPSTAIRS ICE CREAM FREEZER", 
    "GARDE MANGER COOLER", "GARDE MANGER STATION", "BASEMENT FREEZER", 
    "BASEMENT WALK IN", "BASEMENT ICE CREAM FREEZER", "BASEMENT PROTEIN FREEZER",
    "STOREROOM", "HENRY CENTER FREEZER - SPEED RACK", "HENRY CENTER FREEZER"
  ]

  curr_section = "MK WALK IN" # first section read with excel sheet

  all_sections_info = {section: [] for section in section_areas}

  order = 0

  for i in range(df.shape[0]):

    row = df.iloc[i, :]
    # creation of keys for dictionaries
    master_key = "".join([
      str(row["VENDOR/BRAND"]), ", ", str(row["VENDOR_CODE"])]).upper()
    misc_key = "".join([
      str(row["VENDOR/BRAND"]), ", ", str(row["ITEM_DESC"])]).upper()
    
    # is this item in fact a section name?
    if row["VENDOR/BRAND"] in section_areas:
      curr_section = row["VENDOR/BRAND"]
      curr_section = curr_section.strip()
      order = 0

      continue

    

    # is this is an empty row
    elif pd.isna(row["VENDOR/BRAND"]) and pd.isna(row["ITEM_DESC"]):
      # ignore this non-item row
      continue


    # if the row made it past this point, it is an item
    # regardless if the item code is valid or not, add the keys of the item to the 
    all_sections_info[curr_section].append([master_key, misc_key])
    order += 1
    
    # is the item code valid?
    if pd.isna(row["VENDOR_CODE"]):
      # valid item, invalid item code, add to misc_dict
      update_misc(misc_key, row, curr_section, order)
        
    else:
      update_master(master_key, row, curr_section, order)



  for filename in [
    "sections_order_info.json",
    "misc_item_locs.json",
    "vcode_locs.json"]:
    folder_name = filename.split(".")[0]
    
    source.move_and_archive_document(
      filename,
      schemas_folder,
      archive_folder / folder_name)

  # save JSON schemas
  with open(schemas_folder / "sections_order_info.json", "w", encoding="utf-8") as file:
      json.dump(all_sections_info, file, indent=2, ensure_ascii=False)

  with open(schemas_folder / "vcode_locs.json", "w", encoding="utf-8") as file:
      json.dump(master_dict, file, indent=2, ensure_ascii=False)

  with open(schemas_folder / "misc_item_locs.json", "w", encoding="utf-8") as file:
      json.dump(misc_dict, file, indent=2, ensure_ascii=False)


  # move and archive the read inventory into processed_inventories
  source.move_and_archive_document(
    input_files[0],
    input_folder,
    processed_folder,
    remove=True
)

  source.write_log(ROOT, "Ran 'reading_inventory.py' successfully.")

  return 0




if __name__ == "__main__":
  try:
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    main(ROOT)
  except Exception as e:
    print(e)
    source.write_log(ROOT, 
      f"Tried to run 'reading_inventory.py' and failed. Error: {e}")
