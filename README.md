


This project was created by Colin W Fairbourn (he/him) during the Fall of 2025. Purpose is to assist the admin at the University Club of MSU in maintaining accurate and up to date information on their inventory by analyzing invoices given to us by Sysco, gathering the information on any and all items purchased and their price, so that when inventory is counted, they have accurate and recent prices on any items that are in inventory.


___

# The Process 
There are four things to manage here: the 3 inputs to the program, those being new invoices, old inventory sheets, and the master pricing list; and the program 'master_program.py' itself.
- Inputs: 
  - Invoices: 
    - When a new invoice needs to be analyzed for new pricing information, then the invoice as a '.pdf' file must be placed into 'inputs\\invoices\\' and it must stay there when running the program. After the program runs successfully, the prices will be saved to the master pricing list, and the invoice will then be placed into 'inputs\\invoices\\processed_invoices\\' so that the program doesn't unnecessarily read and analyze that same file for the same information again. 
    - Note: The program does not require there to be a new invoice to analyze in order to run, it just won't run that section of the program if there isn't a new invoice.
  - Inventories:
    - When a change to the inventory sheet is made and you wish to apply that change across all future inventory sheets, [see How to Change the Inventory Sheet Without Breaking Anything, Hopefully], then that inventory sheet must be placed within 'inputs\\inventories\\' when running the program.
    - Note: Like invoices, the program does not require there to be an old inventory sheet, as the program stores the information from within the 'master\\schemas' directory from the last time it read an inventory sheet. 
  - Master Pricing: 
    - Within 'deliverables\\' is the file 'master_pricing.csv' that acts as both input and output. When running the program, this file is opened both to read and write to, but a copy is saved within 'master\\archive\\'. Whenever a new item and price is found that is not already in the master list, it will be added, but no further information will be gathered by the program besides the vendor code and the price, and so any further information like Item Description, Unit Type, Pack Size, etc. need to be manually entered into the csv. This information was found by logging into Sysco's ordering website using the login from Chef or the Director of Operations' (at the time of writing this, Chef Eric Manning and/or Director Meg Moody's login information were used), inserting the vendor codes manually, and copying relevant information.
    - Note: Unlike other inputs, this file is mandatory to have and the program will not function without it being present. If it is missing, a reference sheet exists within the 'references\\' folder to act as a copy.
- 'master_program.py'
  - Running this program will generate an updated inventory sheet in 'deliverables\\printable_inventory_sheet.xlsx'. To do so, it does not require any new invoices or new inventory sheets, as much of the information from the last time it ran is saved. 
  - The steps (assuming that all of the steps in the install.md installation instructions have been followed)
    1. Open an Anaconda Prompt.
    2. Run each of the following commands individually: 
    
```bash
venv\Scripts\activate
python UClub2025InventoryPricingProject/master_program.py
```

## Example Step by Step:
  1. Place a newly scanned Sysco invoice into 'inputs\\invoices\\' following a format exactly like 'references\\Sanitized_Redacted_Invoice_Reference.pdf' 
  2. Place last month's inventory sheet with its edits and changes into 'inputs\\inventories\\' following a format exactly like 'references\\input-inventory_reference_sheet_2025-Oct-27.xlsx'
  3. Run the program 'master_pricing.py'.
     -  ```bash
        venv\Scripts\activate
        python UClub2025InventoryPricingProject/master_program.py
        ```
  5. Open 'deliverables\\printable_inventory_sheet.xlsx' or a copy of it and hide any columns that might be deemed unnecessary for the inventory counter. Recommended columns include 'VENDOR_CODE', 'EST_PRICE', 'TOTAL_EST_PRICE', and then print the sheet.

## Optional Continuation:
  - It is possible new items were purchased that did not already exist in the file 'master_pricing.csv', and so those items do not have important information. Log into 'https://shop.sysco.com/auth/login', copy the vendor code into the search bar, and copy relevant information.
  - Run the program again to produce a new printable inventory sheet that includes the new information that was found and entered into 'master_pricing.csv' during the previous step. This is necessary if you want the inventory sheet to include the new information for a new item.



___

# Breakdown of Directories:
- deliverables\\:
  - This directory exists to store the deliverables of this project, 'master_pricing.csv' is stored within this file, and acts as an input, while 'printable_inventory_sheet.xlsx' is the most deliverable part of this project.
- inputs\\:
  - This directory exists as a location for new inputs to be placed, as well as an organization structure that moves older used and processed files into their respective processed folder within that specific input type directory. 
  - inventories\\:
    - Whenever an old inventory needs to be used as a structure template for the new inventory to be created, the old inventory must be placed in this directory, with the name of it being unimportant, so long as it is a '.xlsx' file type. It is recommended that the old excel sheet being used for inventory is a copy of the original inventory. 
    - Ignored in Git
  - invoices\\:
    - Whenever a new sysco invoice is scanned, it should go into this folder. The name of it is unimportant, so long as it is a '.pdf' file type.
    - Ignored in Git
- master\\:
  - archive\\:
    - This directory exists to contain any and all old iterations of the 'master_pricing_list.csv'
    - Ignored in Git
  - errors\\:
    - If any errors are found in the process of analyzing the invoice, they will be recorded here, though very few errors have ever been found.
  - inputs\\:
    - This directory exists as the destination for where info collected from scanned pdf files will be found. It also contains within it the directory for all old input files.
    - Ignored in Git
  - references\\:
    - This directory exists to contain images of example Sysco Invoice sheets, the purpose of which is to help 'reading_sysco_invoice.py' identify which images in the '.pdf' file are pages with information worth extracting.
  - schemas\\:
    - This directory exists as a location for stored information about inventory's structure that is necessary beyond the master_pricing.csv, including:
      - misc_item_locs.json
        - .json file containing information about items that we don't have as specific vendor codes and vendor information for
      - section_order_info.json
        - .json file containing information about what sections contain which items as well as recording and preserving their order
      - vcode_locs.json
        - .json file containing information about items that we specifically have vendor code and vendor information for
    - archive\\:
      - This directory has 3 subdirectories, all of which exist as the respective archived files of old structures
      - Ignored in Git
  - source\\:
    - This is a directory containing only the source file for this project containing a lot of functions and variables that are used in various programs.
  - master_pricing.csv
    - This file is an editable file that is a list containing every item we've ever purchased from Sysco as well as it's details such as vendor information and pricing. 
  - deliverable_creation.py
    - This is a program, step 4 and final step in the process. This program reads in the structure '.json' files, then creates and formats the excel spreadsheet that would be printed and used for counting inventory at end of month.
  - reading_inventory.py
    - This is a program, step 3 in the overall process, that reads in the previous inventory excel spreadsheet, gathers the information about what sections have what items, what sections are specific items in, and what sections are specific vendor codes in, as well as the order that all of this shows up in.
  - reading_sysco_invoice.py:
    - This is a program, step 1 in the overall process, that intakes a '.pdf' file inside the directory 'inputs\\invoices', assuming it's a sysco invoice, analyzes each page for it's textual information, and builds a '.csv' file with all of the items present on that invoice. 
  - update_pricing.py
    - This is a program, step 2 in the overall process, that contains information gathered from 'reading_sysco_invoice.py', in the '.csv' file that is placed in 'master\\inputs' and updates the already existing 'master_pricing_list.csv' as well as archiving the old file.
- references\\:
  - This contains reference and example files for Inventories, a single scanned Sysco Invoice, as well as a copy of a master pricing list

___


### How to Change the Inventory Sheet Without Breaking Anything, Hopefully
The program is dependent on the columns of the inventory being in the precise order that they are currently in. Any changes to the order of the columns is likely to break something or cause unpredictable and unexpected behavior. An inclusion of any other columns, like notes for example, should go after the first 11 columns (Up to the Kth column). Note: any new column past column 11 will not be analyzed nor taken into account in the program creating the new inventory sheet, and so will be lost in the new sheet.

* Inserting additional rows to allow for more items to be recorded in the desired area / section. Removing rows as well, meaning that we might not carry that item anymore, or that that item isn't stored in this location anymore. **Note: It is VITAL that the entire row is removed**, not just the first few columns that have information on them.
* You can fill out additional information for items on Inventory sheet within those first 11 columns, even items we don't have prices for yet. These items, if supplied with a vendor code that matches one in the master pricing list will be automatically included in the items that get updated when the price is updated.
* Do **NOT** change any of the section names, like MK WALK IN, or STOREROOM or HENRY CENTER FREEZER - SPEED RACK


___

The information required to log in to this github account for uclubacct is inside the 'AP Related Log in Info.xlsx' file.
