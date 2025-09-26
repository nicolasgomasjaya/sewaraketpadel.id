import streamlit as st
from datetime import datetime, timedelta
from utils import initiate_worksheet, read_worksheet, write_worksheet
from utils import load_racket_df, load_booking_df


st.title("Time Slot")

# setting up dataframes
with st.spinner("Fetching data..."):
    if "racket_df" in st.session_state:
        racket_df = st.session_state["racket_df"]
    else:
        racket_df = load_racket_df()

    if "booking_df" in st.session_state:
        booking_df = st.session_state["booking_df"]
    else:
        booking_df = load_booking_df()


# filter dropdown
col1, col2 = st.columns([1, 1])
with col1:
    selected_date = st.date_input("📅 Select a date", datetime.today())
with col2:
    racket_type = st.selectbox("🏓 Select a racket", racket_df["type"].tolist())
check_btn = st.button("🔍 Check Time Slot")


if check_btn:
    # filter booking_df for that racket & date
    racket_id = racket_df.loc[racket_df["type"] == racket_type, "id"].values[0]
    day_start = datetime.combine(selected_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    racket_bookings = booking_df[
        (booking_df["racket_id"] == racket_id) &
        (booking_df["start_datetime"] < day_end) &
        (booking_df["end_datetime"] > day_start)
    ]

    # build hourly slots
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for i in range(24):
        slot_start = day_start + timedelta(hours=i)
        slot_end = slot_start + timedelta(hours=1)

        overlapping = racket_bookings[
            (racket_bookings["start_datetime"] < slot_end) &
            (racket_bookings["end_datetime"] > slot_start)
        ]

        target_col = cols[i // 8]  # 0–7 → col1, 8–15 → col2, 16–23 → col3
        with target_col:
            if overlapping.empty:
                st.success(f"{i:02d}:00 - {i+1:02d}:00")
            else:
                st.error(f"{i:02d}:00 - {i+1:02d}:00")

