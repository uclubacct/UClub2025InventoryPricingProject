








import pandas as pd
import json
import numpy as np
import openpyxl as pyxl
from master import source as source
import re



def check_unit_type(unit_type):
  # unit_type is a string denoting
  if isinstance(unit_type, str):
    unit_type = unit_type.strip()
    if unit_type in ["cs", "CS", "case"]:
      unit_type = "CASE"
    elif unit_type in ["lb", "lbs", "LBS"]:
      unit_type = "LB"
    elif unit_type in ["ea", "each","Each"]:
      unit_type = "EACH"
    elif unit_type in ["half"]:
      unit_type = "HALF"

  return unit_type










def main(ROOT):

  schemas_folder = ROOT / "master" / "schemas"

  with open(schemas_folder / "sections_order_info.json") as file:
    all_sections_info = json.load(file)
  with open(schemas_folder / "vcode_locs.json") as file:
    vcode_list = json.load(file)
  with open(schemas_folder / "misc_item_locs.json") as file:
    misc_list = json.load(file)

  # load master csv
  master_list = pd.read_csv(ROOT / "deliverables" / "master_pricing.csv")
  deliverable_path = ROOT / "deliverables" / "printable_inventory_sheet.xlsx"


  deliverable = []

  all_sections_info

  for key in all_sections_info:
    section = all_sections_info[key]
    deliverable.append({
      "VENDOR/BRAND": key, 
      "ITEM_DESC": key,
      "UNIT": "",
      "PACK": "",
      "PER_PACK": "",
      "PRICE": "",
      "QUANTITY": ""
    })

    for item_info in section:
      master_key, misc_key = item_info
      # analyze vcode
      vendor_brand, vcode = master_key.split(",", maxsplit=1)
      vendor_brand = vendor_brand.strip()
      vcode = vcode.strip()

      vendor = vendor_brand
      # get vendor instead of vendor/brand from key
      if len(vendor_brand.split('/')) > 1:
        vendor, _brand = vendor_brand.split('/')

      valid_master_key = (vendor == "SYSCO" and vcode != "NAN")

      # sanitize vcode
      vcode = vcode.split(".")[0]
      vcode = re.sub(r'\D', '', vcode)
      while len(vcode) < 7:
        # add leading zeros until such is not the case
        vcode = "".join(["0", vcode])

      # try to convert to int
      try:
        vcode = int(vcode)
      except Exception as e:
        # couldn't sanitize, forcing NAN
        vcode = "NAN"
        print(f"couldn't turn vcode {vcode} into an int: {e}")

      
      

      # check to see if master key already exists in master
      if valid_master_key and vcode in master_list["VENDOR_CODE"].values:
        # get item information from master inventory list
        info = master_list[master_list['VENDOR_CODE'].values == int(vcode)]
        info["UNIT"].values[0] = check_unit_type(info["UNIT"].values[0])
        # there are some items in master_list without information
        # if this is the case for this item, instead
        # get and use info from vcode_locs to the best of our ability
        deliverable.append({
          "VENDOR/BRAND": "".join(
            [str(info["VENDOR"].values[0]), 
            "/", 
            str(info["BRAND"].values[0])]),
          "VENDOR_CODE": vcode, 
          "ITEM_DESC": info["ITEM_DESC"].values[0], 
          "UNIT": info["UNIT"].values[0],
          "PACK": info["PACK"].values[0], 
          "PER_PACK": info["PER_PACK"].values[0], 
          "PRICE": info["PRICE"].values[0], 
          "QUANTITY": ""
        })

      elif valid_master_key and master_key in vcode_list:
        # use item info from vcode_locs.json
        info = vcode_list[master_key]
        info["UNIT"][0] = check_unit_type(info["UNIT"][0])
        
        deliverable.append({
          "VENDOR/BRAND": vendor,
          "VENDOR_CODE": vcode,
          "ITEM_DESC": info["ITEM_DESC"][0], 
          "UNIT": info["UNIT"][0],
          "PACK": "", 
          "PER_PACK": "", 
          "PRICE": info["PRICES"][0],
          "QUANTITY": ""
        })
          
        # error, valid key but no information found with key
      elif valid_master_key:
        deliverable.append({
          "VENDOR/BRAND": vendor,
          "VENDOR_CODE": "",
          "ITEM_DESC": f"ITEM INFORMATION NOT FOUND {vcode}", 
          "UNIT": "",
          "PACK": "", 
          "PER_PACK": "", 
          "PRICE": "",
          "QUANTITY": ""
        })



      # master key not valid, using misc_key now
      else:
        # use the item information in misc_item_locs.json
        vendor, item_desc = misc_key.split(",", maxsplit = 1)
        item_desc = item_desc.strip()
        if vendor in ["NAN", "?"]:
          vendor = ""
        
        if misc_key in misc_list:
          
          info = misc_list[misc_key]
          info["UNIT"][0] = check_unit_type(info["UNIT"][0])

          deliverable.append({
            "VENDOR/BRAND": vendor,
            "VENDOR_CODE": "",
            "ITEM_DESC": item_desc, 
            "UNIT": info["UNIT"][0],
            "PACK": "", 
            "PER_PACK": "", 
            "PRICE": info["PRICES"][0] ,
            "QUANTITY": ""
          })

        else:
          deliverable.append({
            "VENDOR/BRAND": vendor,
            "VENDOR_CODE": "",
            "ITEM_DESC": item_desc, 
            "UNIT": "",
            "PACK": "", 
            "PER_PACK": "", 
            "PRICE": "",
            "QUANTITY": ""
          })
          






  ###########################################
  # Creating and Formatting the Excel Sheet #
  ###########################################

  deliverable = pd.DataFrame(
    deliverable, 
    columns = [
      "VENDOR/BRAND", "VENDOR_CODE", "ITEM_DESC", "UNIT", 
      "PACK", "PER_PACK", "PRICE", "QUANTITY"]
  )
  # adding these columns
  deliverable["EST_PRICE"] = 0
  deliverable["TOTAL_EST_VALUE"] = np.nan

  deliverable.to_excel(deliverable_path)

  # read in the file and do the excel formatting
  printed = pyxl.load_workbook(deliverable_path)
  ws = printed.active

  
  
  # ## ADD ROW STATING: "For month ending in MONTH/YEAR"
  # ws.insert_rows(2)
  # ws.merge_cells("B2:J2")
  # ws["B2"].value = "For Month Ending _____ / ____"

  # ws["B2"].alignment = pyxl.styles.Alignment(
  #   horizontal = "center", vertical = "center"
  # )
  # ws["B2"].font = pyxl.styles.Font(bold = True)


  ## ADDING 10 BLANK ROWS AT BOTTOM OF SECTIONS
  n_blanks = 10

  total_rows = []
  for i, row in enumerate(ws.iter_rows(min_row = 2), start = 2):
    for cell in row:
      if "TOTAL:" in str(cell.value):
        total_rows.append(i)
        break

  for i in reversed(total_rows):
    ws.insert_rows(i, amount = n_blanks)


  ## CREATING ESTIMATED PRICE COLUMN AS PRODUCT OF QUANTITY AND PRICE
  header_row = 1
  headers = {cell.value: idx + 1 for idx, cell in enumerate(ws[header_row])}

  price_col = pyxl.utils.get_column_letter(headers["PRICE"])
  qty_col = pyxl.utils.get_column_letter(headers["QUANTITY"])
  est_col = pyxl.utils.get_column_letter(headers["EST_PRICE"])

  for row in range(header_row + 1, ws.max_row + 1):
    ws[f"{est_col}{row}"] = f"={price_col}{row}*{qty_col}{row}"


  ## TEXT WRAPPING FOR VENDOR/BRAND AND ITEM_DESC
  wrap_alignment = pyxl.styles.Alignment(wrap_text = True, vertical = "center")

  for col in ws.iter_cols():
    for cell in col:
      cell.alignment = wrap_alignment

  for cell in ws[1]:
    cell.alignment = wrap_alignment


  ## CENTER ALIGNMENT FOR VENDOR_CODE, UNIT, PACK, PER_PACK
  center_alignment = pyxl.styles.Alignment(
    horizontal = "center", vertical = "center")
  for col_name in ["VENDOR_CODE", "UNIT","PACK","PER_PACK"]:
    col_letter = pyxl.utils.get_column_letter(headers[col_name])
    for cell in ws[col_letter]:
      cell.alignment = center_alignment


  ## FREEZE TOP ROW AND PRINT HEADER ROW ON EACH PAGE
  ws.freeze_panes = "A2"
  ws.print_title_rows = "1:1"


  ## BOLD & ENLARGE FONT & HIGHLIGHT & MERGE SECTION HEADERS

  section_fill = pyxl.styles.PatternFill(
    start_color = "CCE5FF", end_color = "CCE5FF", fill_type = "solid"
  )
  section_font = pyxl.styles.Font(bold = True, size = 24)
  vender_col = headers['VENDOR/BRAND']

  for i, row in enumerate(ws.iter_rows(min_row = 2, max_col = ws.max_column), start = 2):
    cell = ws.cell(row = i, column = vender_col)
    if cell.value in all_sections_info.keys():
      # merge all 8 rows
      ws.merge_cells(f"B{i}:J{i}") 

      # format first leftmost visible cell in merged range
      merged_cell = ws.cell(row = i, column = 2)
      merged_cell.font = section_font
      merged_cell.fill = section_fill
      merged_cell.alignment = pyxl.styles.Alignment(
        horizontal = "center", vertical = "center"
      )



  ## HIGHLIGHT ROWS CONTAINING TOTAL:
  ## MERGE ROWS CONTAINING TOTAL:
  ## ADD NEW COLUMN TOTAL EST VALUE WITH SECTION SUMS
  total_fill = pyxl.styles.PatternFill(
    start_color = "FFFACD", end_color = "FFFACD", fill_type="solid"
  )
  last_total_row = 2

  for i, row in enumerate(ws.iter_rows(min_row = 2), start = 2):
    total_text = None
    for cell in row:
      if "TOTAL:" in str(cell.value):
        total_text = str(cell.value)
        break
    if total_text:
      # merging columns B - I for this row
      ws.merge_cells(f"B{i}:J{i}") 

      top_left = ws[f"B{i}"]
      top_left.value = total_text

      # determine the excel range for EST_PRICE (column I = 9)
      start_row = last_total_row + 1
      end_row = i - 1
      if end_row >= start_row:
        formula = f"=SUM(J{start_row}:J{end_row})"
      else:
        formula = "=0"

      total_cell = ws[f"K{i}"]
      total_cell.value = formula
      total_cell.number_format = pyxl.styles.numbers.FORMAT_CURRENCY_USD_SIMPLE



      # highlight & format the total row
      for cell in row:
        cell.fill = total_fill
        cell.font = pyxl.styles.Font(bold = True)
        cell.alignment = pyxl.styles.Alignment(
          horizontal = "center", vertical = "center")

      last_total_row = i


  ## ADD BORDER AROUND EACH ITEM
  thin_border = pyxl.styles.Border(
    left = pyxl.styles.Side(style = 'thin', color = '000000'),
    right = pyxl.styles.Side(style = 'thin', color = '000000'),
    top = pyxl.styles.Side(style = 'thin', color = '000000'),
    bottom = pyxl.styles.Side(style = 'thin', color = '000000')
  )

  for row in ws.iter_rows(
    min_row = 1, max_row = ws.max_row,
    min_col = 1, max_col = ws.max_column):
    for cell in row:
      cell.border = thin_border



  ## FORMATTING PRICE, EST_PRICE, TOTAL EST VALUE AS ACCOUNTING COLS
  for col in [headers["PRICE"], headers["EST_PRICE"]]:
    col_letter = pyxl.utils.get_column_letter(col)
    for cell in ws[col_letter]:
      cell.number_format = pyxl.styles.numbers.FORMAT_CURRENCY_USD_SIMPLE

  ## FORMATTING QUANTITY TO BE NUMERIC COLUMN
  col_letter = pyxl.utils.get_column_letter(headers["QUANTITY"])
  for cell in ws[col_letter]:
    cell.number_format = pyxl.styles.numbers.FORMAT_NUMBER

  ## FORMATTING VENDOR_CODE TO BE TEXT TO PRESERVE LEADING ZEROS
  # forwent this, because I haven't yet built in a functionality that corrects
  # any mistakes in vendor codes like leading zeros for those that need to be 
  # a specific length, like Sysco: 7 and Stan Setas: 4

  ## ADDING TOTAL OF TOTAL_EST_VALUE FOR TOTAL VALUE ACROSS INVENTORY
  last_row = ws.max_row
  
  ws["K2"].value = f"=SUM(K3:K{last_row})"
  ws["K2"].number_format = pyxl.styles.numbers.FORMAT_CURRENCY_USD_SIMPLE
  ws["K2"].font = pyxl.styles.Font(bold = True)




  ## ADJUST COLUMN WIDTHS AND HEADER ROW HEIGHT
  ws.column_dimensions["A"].width = 8
  ws.column_dimensions["B"].width = 20
  ws.column_dimensions["C"].width = 15
  ws.column_dimensions["D"].width = 40
  ws.column_dimensions["K"].width = 15
  for col in range(5, 11):
    col_letter = pyxl.utils.get_column_letter(col)
    ws.column_dimensions[col_letter].width = 10

  ws.row_dimensions[1].height = 35
  
  try:
    printed.save(deliverable_path)
    print(f"File saved successfully in {deliverable_path}")
  except Exception as e:
    print(f"An unexpected error occurred while saving the file: {e}")

  source.write_log(ROOT, "Ran 'deliverable_creation.py' successfully.")

  return


if __name__ == "__main__":
  try:
    from pathlib import Path
    ROOT = Path(__file__).resolve().parent.parent
    main(ROOT)
  except Exception as e:
    print(e)
    source.write_log(ROOT, 
      f"Tried to run 'deliverable_creation.py' and failed. Error: {e}")
