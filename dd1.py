import os
import pytesseract
import pandas as pd
import PyPDF2
from pdf2image import convert_from_path
import re
import json
import fitz  # PyMuPDF
import sys  # Required for command-line arguments

# Ensure Tesseract is set correctly
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Get the PDF file path from command-line arguments
if len(sys.argv) < 2:
    print(json.dumps({"error": "No PDF file provided"}))
    exit()

pdf_path = sys.argv[1]

# Open the PDF file with PyMuPDF
pdf_document = fitz.open(pdf_path)
images = convert_from_path(pdf_path, poppler_path=r"C:\Users\mahi\OneDrive\Desktop\bank statement analysis\Release-23.11.0-0\poppler-23.11.0\Library\bin")

# Initialize dictionaries to store data
sections_data = {
    "Account Summary": [],
    "Deposits": [],
    "Other Credits": [],
    "Other Debits": [],
    "Daily Balances": []
}

current_section = None


for page_number, image in enumerate(images, start=1):
    image = image.convert("L")
    image = image.point(lambda x: 0 if x < 150 else 255, '1')

    ocr_result = pytesseract.image_to_string(image, config="--psm 6")
    lines = ocr_result.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if "Account Summary" in line:
            current_section = "Account Summary"
            continue
        elif "Deposits" in line:
            current_section = "Deposits"
            continue
        elif "Other Credits" in line:
            current_section = "Other Credits"
            continue
        elif "Other Debits" in line:
            current_section = "Other Debits"
            continue
        elif "Daily Balances" in line:
            current_section = "Daily Balances"
            continue

        if current_section in ["Deposits", "Other Credits", "Other Debits"]:
            match = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$([\d,\.]+)$", line)
            if match:
                date, description, amount = match.groups()
                sections_data[current_section].append([date, description, f"${float(amount.replace(',', '')):,.2f}"])
            else:
                if len(sections_data[current_section]) > 0:
                    sections_data[current_section][-1][1] += f" {line}"

        elif current_section == "Account Summary":
            match = re.match(r"^(.+?)\s+\$([\d,\.]+)$", line)
            if match:
                description, amount = match.groups()
                date_match = re.search(r"\d{2}/\d{2}/\d{4}", description)
                date = date_match.group() if date_match else None
                description = description.replace(date, "").strip() if date else description
                sections_data[current_section].append([date, description, f"${float(amount.replace(',', '')):,.2f}"])

        elif current_section == "Daily Balances":
            match = re.findall(r"(\d{2}/\d{2}/\d{4})\s+\$([\d,\.]+)", line)
            if match:
                for date, amount in match:
                    sections_data[current_section].append([date, f"${float(amount.replace(',', '')):,.2f}"])

# Convert data into DataFrames
account_summary_df = pd.DataFrame(sections_data["Account Summary"], columns=["Date", "Description", "Amount"])
deposits_df = pd.DataFrame(sections_data["Deposits"], columns=["Date", "Description", "Amount"])
other_credits_df = pd.DataFrame(sections_data["Other Credits"], columns=["Date", "Description", "Amount"])
other_debits_df = pd.DataFrame(sections_data["Other Debits"], columns=["Date", "Description", "Amount"])
daily_balances_df = pd.DataFrame(sections_data["Daily Balances"], columns=["Date", "Amount"])

# Merge transactions
other_credits_df['Type'] = 'Credit'
other_debits_df['Type'] = 'Debit'
merged_other_transactions_df = pd.concat([other_credits_df, other_debits_df])
merged_other_transactions_df['Date'] = pd.to_datetime(merged_other_transactions_df['Date']).dt.strftime('%Y-%m-%d')
merged_other_transactions_df = merged_other_transactions_df.sort_values(by=['Date']).reset_index(drop=True)
# Calculate Total Credit and Debit in Merged Transactions
total_credit = merged_other_transactions_df[merged_other_transactions_df['Type'] == 'Credit']['Amount'].apply(lambda x: float(str(x).replace('$', '').replace(',', ''))).sum()
total_debit = merged_other_transactions_df[merged_other_transactions_df['Type'] == 'Debit']['Amount'].apply(lambda x: float(str(x).replace('$', '').replace(',', ''))).sum()

# Convert dataframes to JSON
output_data = {
    "Account Summary": account_summary_df.to_dict(orient="records"),
    "Deposits": deposits_df.to_dict(orient="records"),
    "Other Credits": other_credits_df.to_dict(orient="records"),
    "Other Debits": other_debits_df.to_dict(orient="records"),
    "Daily Balances": daily_balances_df.to_dict(orient="records"),
    "Merged Transactions": merged_other_transactions_df.to_dict(orient="records"),
    "Total Credit": f"${total_credit:,.2f}",   # Add formatted total credit
    "Total Debit": f"${total_debit:,.2f}"      # Add formatted total debit
}

print(json.dumps(output_data, default=str))

