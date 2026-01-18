from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import re

app = Flask(__name__)

# ==============================
# LOAD EXCEL AS DATABASE
# ==============================
EXCEL_FILE = "All Project Salesforce For Visualization.xlsx"
df = pd.read_excel(EXCEL_FILE)

# Normalize text columns
TEXT_COLS = [
    "Name",
    "Bedrooms__c",
    "Project_Status__c",
    "Category__c",
    "City__c",
    "Share_On_Website__c",
    "Ownership__c"
]

for col in TEXT_COLS:
    df[col] = df[col].astype(str).str.lower()

# Clean numeric columns
def clean_number(val):
    try:
        return float(str(val).replace(",", "").strip())
    except:
        return None

df["price"] = df["Project_Base_Price__c"].apply(clean_number)
df["area_min"] = df["Area_Range_Min__c"].apply(clean_number)
df["area_max"] = df["Area_Range_Max__c"].apply(clean_number)
df["total_area"] = df["Total_Project_Area__c"].apply(clean_number)
df["floors"] = df["Total_no_of_Floors_Tower__c"].apply(clean_number)

# ==============================
# FILTER ENGINE
# ==============================
def filter_projects(question):
    q = question.lower()
    data = df.copy()

    if "noida" in q:
        data = data[data["City__c"] == "noida"]
    if "gurgaon" in q:
        data = data[data["City__c"] == "gurgaon"]

    if "ready" in q:
        data = data[data["Project_Status__c"].str.contains("ready", na=False)]
    if "under" in q:
        data = data[data["Project_Status__c"].str.contains("under", na=False)]

    if "residential" in q:
        data = data[data["Category__c"] == "residential"]
    if "commercial" in q:
        data = data[data["Category__c"] == "commercial"]

    bhk_match = re.search(r"(\d)\s*bhk", q)
    if bhk_match:
        bhk = bhk_match.group(1)
        data = data[data["Bedrooms__c"].str.contains(bhk, na=False)]

    if "crore" in q:
        num = re.search(r"(\d+)", q)
        if num:
            max_price = int(num.group(1)) * 10000000
            data = data[data["price"] <= max_price]

    if "sq ft" in q or "sqft" in q:
        num = re.search(r"(\d+)", q)
        if num:
            area = int(num.group(1))
            data = data[
                (data["area_min"] <= area) &
                (data["area_max"] >= area)
            ]

    if "leasehold" in q:
        data = data[data["Ownership__c"] == "leasehold"]
    if "freehold" in q:
        data = data[data["Ownership__c"] == "freehold"]

    if "website" in q:
        data = data[data["Share_On_Website__c"] == "yes"]

    if "floor" in q:
        num = re.search(r"(\d+)", q)
        if num:
            min_floor = int(num.group(1))
            data = data[data["floors"] >= min_floor]

    return data.head(5)

# ==============================
# WHATSAPP BOT
# ==============================
@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming = request.values.get("Body", "").strip()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming.lower() == "hello":
        msg.body(
            "👋 Welcome to MRE Project Bot 🤖\n\n"
            "You can ask:\n"
            "• Noida residential projects\n"
            "• 2 BHK ready projects in Noida\n"
            "• Projects under 1 crore\n"
            "• Commercial projects Gurgaon"
        )
        return str(resp)

    results = filter_projects(incoming)

    if results.empty:
        msg.body("❌ No matching projects found.")
        return str(resp)

    reply = "🏗 Matching Projects:\n\n"
    for _, row in results.iterrows():
        reply += (
            f"🏢 {row['Name'].title()}\n"
            f"📍 {row['City__c'].title()}\n"
            f"🏠 BHK: {row['Bedrooms__c']}\n"
            f"🏗 Status: {row['Project_Status__c'].title()}\n"
            f"🏷 Category: {row['Category__c'].title()}\n"
            f"💰 Price: {row['Project_Base_Price__c']}\n"
            f"📐 Area: {row['Area_Range_Min__c']} - {row['Area_Range_Max__c']} sq ft\n"
            f"🏢 Floors: {row['Total_no_of_Floors_Tower__c']}\n\n"
        )

    msg.body(reply)
    return str(resp)
