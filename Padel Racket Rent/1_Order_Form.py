import streamlit as st
from utils import parse_order_form, validate_order_form
from utils import initiate_worksheet, read_worksheet, write_worksheet
from utils import load_racket_df, load_booking_df


st.title("Order Form")

order_form_template = """📝 Form Order

Nama:
No WA:
Jenis raket:

Drop off
📍 Venue:
📅 Tanggal:
⏰ Jam:

Pick up
📍 Venue:
📅 Tanggal:
⏰ Jam:

PIC Nama"""

with st.spinner("Fetching data..."):
    if "racket_df" in st.session_state:
        racket_df = st.session_state["racket_df"]
    else:
        racket_df = load_racket_df()

with st.expander("Order form template"):
    st.code(order_form_template, language="python")

with st.expander("Racket list"):
    racket_types = racket_df['type'].dropna().unique().tolist()
    racket_types = [r.lower().strip() for r in racket_types]
    st.dataframe(racket_df)

with st.expander("Check availability", expanded=True):
    with st.form("order_form_box"):
        order_form_text = st.text_area("Paste the order form here", placeholder=order_form_template, height=300)
        submitted = st.form_submit_button("Check availability")
        
        if submitted:
            order_form_df = parse_order_form(order_form_text)
            racket_type = order_form_df.at[0, "racket_type"].strip().lower()
            is_valid, msg = validate_order_form(order_form_df)
            if not is_valid:
                st.error(f"Error: {msg}")
                st.dataframe(order_form_df.drop(columns=["id", "created_at"]))
            elif racket_type not in racket_types:
                st.error(f"Error: Racket type '{order_form_df.at[0, 'racket_type']}' is not in the racket list.")
                st.dataframe(order_form_df.drop(columns=["id", "created_at"]))
            else:
                st.success("Order form is valid!")
                st.session_state["order_form_df"] = order_form_df
                order_worksheet = initiate_worksheet(worksheet_name='order')
                write_worksheet(order_worksheet, order_form_df, is_overwrite=False)
                st.switch_page("pages/2_Booking.py")





