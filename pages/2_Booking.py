import streamlit as st
from datetime import datetime
import pandas as pd
from utils import check_racket_availability
from utils import initiate_worksheet, read_worksheet, write_worksheet


st.title("Booking")

# setting up dataframes
if "order_form_df" in st.session_state:
    order_form_df = st.session_state["order_form_df"]
else:
    st.switch_page("1_Order_Form.py")

if "racket_df" in st.session_state:
    racket_df = st.session_state["racket_df"]
else:
    racket_worksheet = initiate_worksheet(worksheet_name='racket')
    racket_df = read_worksheet(racket_worksheet)

if "booking_df" in st.session_state:
    booking_df = st.session_state["booking_df"]
else:
    booking_worksheet = initiate_worksheet(worksheet_name='booking')
    booking_df = read_worksheet(booking_worksheet)


# setting up display
order_id = order_form_df.at[0, "id"]
racket_type = order_form_df.at[0, "racket_type"]
start_datetime = order_form_df.at[0, "start_datetime"]
end_datetime = order_form_df.at[0, "end_datetime"]
start_time = order_form_df.at[0, "dropoff_time"]
end_time = order_form_df.at[0, "pickup_time"]
venue = order_form_df.at[0, "dropoff_venue"]


# check availability
is_racket_available, racket_id = check_racket_availability(order_form_df, racket_df, booking_df)


# get previous and next booking
booking_df["start_datetime"] = pd.to_datetime(booking_df["start_datetime"], errors="coerce")
booking_df["end_datetime"] = pd.to_datetime(booking_df["end_datetime"], errors="coerce")
racket_booking_df = booking_df[booking_df["racket_id"] == racket_id]
previous_booking = racket_booking_df[
    (racket_booking_df["end_datetime"] <= start_datetime) | # normal previous
    (racket_booking_df["start_datetime"] <= start_datetime) # overlap
].sort_values("end_datetime").tail(1)
next_booking = racket_booking_df[
    (racket_booking_df["start_datetime"] >= end_datetime) | # normal next
    (racket_booking_df["end_datetime"] >= end_datetime) # overlap
].sort_values("start_datetime").head(1)

# display racket info
st.subheader(f"Racket Type: {racket_type}")

# display booking info
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    with st.expander("**Previous Booking**", expanded=True):
        if not previous_booking.empty:
            st.write(f"📍 Pickup {previous_booking.iloc[0]['pickup_venue']}")
            st.write(
                f"🕒 {previous_booking.iloc[0]['start_datetime'].strftime('%-d %b %H:%M')} - "
                f"{previous_booking.iloc[0]['end_datetime'].strftime('%H:%M')}"
            )
        else:
            st.write("No booking")

with col2:
    with st.expander("**Your Slot**", expanded=True):
        st.write(f"📍 Dropoff {venue}")
        st.write(
            f"🕒 {start_datetime.strftime('%-d %b %H:%M')} - "
            f"{end_datetime.strftime('%H:%M')}"
        )

with col3:
    with st.expander("**Next Booking**", expanded=True):
        if not next_booking.empty:
            st.write(f"📍 Dropoff {next_booking.iloc[0]['dropoff_venue']}")
            st.write(
                f"🕒 {next_booking.iloc[0]['start_datetime'].strftime('%-d %b %H:%M')} - "
                f"{next_booking.iloc[0]['end_datetime'].strftime('%H:%M')}"
            )
        else:
            st.write("No booking")

# display availability
if is_racket_available: st.success("Your slot is available ✅")
else: st.error("Your slot is not available ❌")

# track booked order ids
if "booked_order_ids" not in st.session_state:
    st.session_state["booked_order_ids"] = set()

# setting up buttons
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("📖 Book Now", use_container_width=True, disabled=not is_racket_available):
        if order_id in st.session_state["booked_order_ids"]:
            st.warning("⚠️ Already booked this order.")
        else:
            new_booking_df = pd.DataFrame([{
                "id": order_form_df.at[0, "id"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "order_id": order_form_df.at[0, "id"],
                "racket_id": racket_id,
                "start_datetime": start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "end_datetime": end_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "dropoff_venue": order_form_df.at[0, "dropoff_venue"],
                "pickup_venue": order_form_df.at[0, "pickup_venue"],
            }])
            write_worksheet(booking_worksheet, new_booking_df, is_overwrite=False)
            st.session_state["booked_order_ids"].add(order_id)
            st.success("✅ Your slot has been booked!")
with col2:
    if st.button("⬅️ Back", use_container_width=True):
        st.switch_page("1_Order_Form.py")


