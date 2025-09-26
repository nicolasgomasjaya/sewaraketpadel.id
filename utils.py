import re
import pandas as pd
from datetime import datetime
import random
import string
import json
from google.oauth2 import service_account
import pygsheets
import streamlit as st


### UTILITIES ###

def parse_order_form(raw_text: str) -> pd.DataFrame:
    def generate_id():
        safe_digits = "23456789"
        digits = "".join(random.choice(safe_digits) for _ in range(3))

        safe_letters = "".join([c for c in string.ascii_uppercase if c not in ["O", "I"]])
        letters = ''.join(random.choices(safe_letters, k=3))
        
        combined = list(digits + letters)
        random.shuffle(combined)
        return ''.join(combined)
    
    def extract(pattern, n=0, text=raw_text):
        matches = re.findall(pattern, text, re.IGNORECASE)
        if len(matches) > n:
            return matches[n].strip()
        return ""

    data = {
        "id": generate_id(),
        "created_at": datetime.now(),
        "created_by": extract(r"pic[ \t]+([^\r\n]+)"),
        "name": extract(r"nama[ \t]*:[ \t]*([^\r\n]+)"),
        "phone_number": extract(r"no wa[ \t]*:[ \t]*([^\r\n]+)"),
        "racket_type": extract(r"jenis raket[ \t]*:[ \t]*([^\r\n]+)"),
        "dropoff_venue": extract(r"venue[ \t]*:[ \t]*([^\r\n]+)"),
        "dropoff_date": extract(r"tanggal[ \t]*:[ \t]*([^\r\n]+)"),
        "dropoff_time": extract(r"jam[ \t]*:[ \t]*([^\r\n]+)"),
        "pickup_venue": extract(r"venue[ \t]*:[ \t]*([^\r\n]+)", 1), # second occurrence
        "pickup_date": extract(r"tanggal[ \t]*:[ \t]*([^\r\n]+)", 1), # second occurrence
        "pickup_time": extract(r"jam[ \t]*:[ \t]*([^\r\n]+)", 1), # second occurrence
    }

    return pd.DataFrame([data])

def validate_order_form(df: pd.DataFrame) -> bool:
    # check if any column is null or empty
    for col in df.columns:
        if df[col].isnull().any() or (df[col].astype(str).str.strip() == "").any():
            return False, "Incomplete data"
    
    # check if phone number is valid (should start with + followed by digits)
    phone = str(df.at[0, "phone_number"]).strip()
    if not re.match(r"^\+?\d+$", phone):
        return False, "Invalid phone number"

    # check if dropoff_date and pickup_date are in yyyy-mm-dd format
    for col in ["dropoff_date", "pickup_date"]:
        val = str(df.at[0, col]).strip()
        try: datetime.strptime(val, "%Y-%m-%d")
        except: return False, "Invalid date format"

    # check if dropoff_time and pickup_time are in HH:MM format
    for col in ["dropoff_time", "pickup_time"]:
        val = str(df.at[0, col]).strip()
        if not re.match(r"^(?:[01]\d|2[0-3]):[0-5]\d$", val):
            return False, "Invalid time format"
        
    # check if dropoff_datetime is before pickup_datetime
    dropoff_datetime_str = f"{df.at[0, 'dropoff_date']} {df.at[0, 'dropoff_time']}"
    pickup_datetime_str = f"{df.at[0, 'pickup_date']} {df.at[0, 'pickup_time']}"
    dropoff_datetime = datetime.strptime(dropoff_datetime_str, "%Y-%m-%d %H:%M")
    pickup_datetime = datetime.strptime(pickup_datetime_str, "%Y-%m-%d %H:%M")
    if dropoff_datetime >= pickup_datetime:
        return False, "Drop-off datetime must be before pick-up datetime"
    
    # check if dropoff_time and pickup_time not in the past
    if dropoff_datetime < datetime.now() or pickup_datetime < datetime.now():
        return False, "Drop-off and pick-up datetime must be in the future"
        
    return True, "Valid"

def check_racket_availability(order_form_df, racket_df, booking_df):
    # get racket_id based on racket_type
    racket_type = order_form_df.at[0, "racket_type"].strip()
    racket_row = racket_df[racket_df["type"].str.lower().str.strip() == racket_type.lower()]
    if racket_row.empty:
        return False, None
    racket_id = racket_row.iloc[0]["id"]

    # build start and end datetime for new booking
    start_datetime_str = f"{order_form_df.at[0, 'dropoff_date']} {order_form_df.at[0, 'dropoff_time']}"
    end_datetime_str   = f"{order_form_df.at[0, 'pickup_date']} {order_form_df.at[0, 'pickup_time']}"
    start_datetime = pd.to_datetime(start_datetime_str, format="%Y-%m-%d %H:%M")
    end_datetime   = pd.to_datetime(end_datetime_str, format="%Y-%m-%d %H:%M")

    # filter bookings for this racket_id
    racket_booking_df = booking_df[booking_df["racket_id"] == racket_id]

    # check overlap: (new_start < existing_end) and (new_end > existing_start)
    for _, row in racket_booking_df.iterrows():
        if start_datetime < row["end_datetime"] and end_datetime > row["start_datetime"]:
            return False, racket_id

    return True, racket_id


### GOOGLE SHEET ###

def initiate_worksheet(gsheet_id='14Z3IUqsG2WjCf9XE3TcijwNEoEdPPOnjxLXBJsUJtvg', worksheet_name=None):
    """
    Initiate GSheet client.
    """
    with open("creds/service_account.json", "r") as f:
        service_account_info = json.load(f)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
    )
    client = pygsheets.authorize(credentials=credentials)
    worksheet = client.open_by_key(gsheet_id).worksheet_by_title(worksheet_name)
    return worksheet

def read_worksheet(worksheet, start_cell='A1', convert_to_datetime=True):
    """
    Read GSheet and return data as dataframe.
    """
    df = worksheet.get_as_df(start=start_cell)
    if convert_to_datetime:
        for col in df.columns:
            try:
                if df[col].dtype == 'object':
                    df[col] = pd.to_datetime(df[col], errors='ignore')
            except:
                pass
    return df

def write_worksheet(worksheet, df, start_cell='A1', is_overwrite=True):
    """
    Write dataframe to GSheet.
    """
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            df[col] = df[col].astype(str)
            
    if is_overwrite:
        worksheet.clear()
        worksheet.rows = df.shape[0] + 2
        worksheet.columns = df.shape[1] + 2
        if not df.empty:
            worksheet.set_dataframe(df, start_cell)
        else:
            worksheet.update_row(1, df.columns.tolist()) # write column name
    else:
        if not df.empty:
            if worksheet.rows > 1:
                worksheet.append_table(values=df.values.tolist())
            else:
                worksheet.set_dataframe(df, start_cell)
        else:
            if worksheet.rows <= 1:
                worksheet.update_row(1, df.columns.tolist()) # write column name


### STREAMLIT ###

@st.cache_data(ttl=60, show_spinner=False)
def load_racket_df():
    racket_worksheet = initiate_worksheet(worksheet_name='racket')
    return read_worksheet(racket_worksheet)

@st.cache_data(ttl=60, show_spinner=False)
def load_booking_df():
    booking_worksheet = initiate_worksheet(worksheet_name='booking')
    return read_worksheet(booking_worksheet)
