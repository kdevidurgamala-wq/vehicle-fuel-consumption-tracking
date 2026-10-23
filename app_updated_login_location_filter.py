import json
import os
import re
import secrets
import hashlib
import hmac
import time
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ============================================================
# PAGE SETTINGS
# ============================================================
st.set_page_config(
    page_title="Vehicle Fuel Consumption Tracking System",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# FILES / CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "vehicle_fuel_purchase_dataset_review3(1).csv"
OTP_EXPIRY_SECONDS = 300
MAX_OTP_ATTEMPTS = 5

# Configure these values in .streamlit/secrets.toml.
# Do not put Twilio credentials directly in this source file.
def get_secret(section, key, default=""):
    try:
        return st.secrets[section][key]
    except Exception:
        return os.environ.get(f"{section.upper()}_{key.upper()}", default)


# Passwords are read from the CSV Passward column as requested.

def normalize_mobile(value) -> str:
    """Normalize mobile numbers for dataset matching (last 10 digits)."""
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[-10:] if len(digits) >= 10 else digits




# ============================================================
# SMS OTP (Twilio)
# ============================================================
def send_sms_otp(destination: str, otp: str) -> None:
    account_sid = get_secret("twilio", "account_sid")
    auth_token = get_secret("twilio", "auth_token")
    from_number = get_secret("twilio", "from_number")

    if not all([account_sid, auth_token, from_number]):
        raise RuntimeError(
            "Twilio is not configured. Add account_sid, auth_token, and from_number "
            "to .streamlit/secrets.toml."
        )

    try:
        from twilio.rest import Client
    except ImportError as exc:
        raise RuntimeError("Twilio library is missing. Run: pip install -r requirements.txt") from exc

    client = Client(account_sid, auth_token)
    message = (
        f"Your Vehicle Fuel Tracking System password-reset OTP is {otp}. "
        f"It expires in 5 minutes. Do not share this code."
    )
    client.messages.create(body=message, from_=from_number, to=destination)


def valid_indian_mobile(mobile: str) -> bool:
    digits = re.sub(r"\D", "", mobile)
    return len(digits) == 10 or (len(digits) == 12 and digits.startswith("91"))


def to_e164(mobile: str) -> str:
    digits = re.sub(r"\D", "", mobile)
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    if str(mobile).strip().startswith("+"):
        return "+" + digits
    raise ValueError("Enter a valid mobile number including country code if needed.")


# ============================================================
# CUSTOM STYLE
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(135deg, #eef7ff, #f8f4ff); }
    .main-title {
        text-align: center; font-size: 34px; font-weight: 800;
        color: #173b6c; margin-top: 12px;
    }
    .subtitle {
        text-align: center; color: #5b6472; font-size: 16px;
        margin-bottom: 25px;
    }
    .section-title { color: #173b6c; font-size: 27px; font-weight: 700; }
    .metric-card {
        padding: 19px; border-radius: 16px; color: white; text-align: center;
        box-shadow: 0 5px 15px rgba(0,0,0,0.10); min-height: 105px;
    }
    .metric-card h4 { margin: 0; font-size: 15px; }
    .metric-card h2 { margin: 8px 0 0 0; font-size: 25px; }
    .blue { background: linear-gradient(135deg, #2196f3, #1565c0); }
    .green { background: linear-gradient(135deg, #00b894, #00897b); }
    .orange { background: linear-gradient(135deg, #ff9800, #ef6c00); }
    .purple { background: linear-gradient(135deg, #9c27b0, #6a1b9a); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# LOAD DATASET
# ============================================================
if not CSV_FILE.exists():
    st.error(
        f"Dataset file not found: {CSV_FILE.name}. "
        "Place the CSV file in the same folder as app.py."
    )
    st.stop()

try:
    df = pd.read_csv(CSV_FILE, dtype={"Mobile_Number": str})
except Exception as exc:
    st.error(f"Could not load the CSV dataset: {exc}")
    st.stop()

required_columns = [
    "Mobile_Number", "Fuel_Quantity (L)", "Total_Cost (₹)",
    "Vehicle_Number", "Odometer_Reading (Km)", "Date", "Fuel_Type", "Passward",
]
missing_columns = [column for column in required_columns if column not in df.columns]
if missing_columns:
    st.error("The CSV is missing required columns: " + ", ".join(missing_columns))
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "mobile" not in st.session_state:
    st.session_state.mobile = ""
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"
if "reset_mobile" not in st.session_state:
    st.session_state.reset_mobile = ""
if "otp_hash" not in st.session_state:
    st.session_state.otp_hash = ""
if "otp_expires_at" not in st.session_state:
    st.session_state.otp_expires_at = 0
if "otp_attempts" not in st.session_state:
    st.session_state.otp_attempts = 0
if "otp_verified" not in st.session_state:
    st.session_state.otp_verified = False
if "otp_sent" not in st.session_state:
    st.session_state.otp_sent = False


# ============================================================
# LOGIN / FORGOT PASSWORD
# ============================================================
if not st.session_state.logged_in:
    st.markdown(
        '<div class="main-title">⛽ Vehicle Fuel Consumption Tracking System</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">Securely access your vehicle fuel records</div>',
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([1, 1.25, 1])
    with center:
        if st.session_state.auth_page == "login":
            st.subheader("🔐 Login")
            with st.form("login_form"):
                mobile_input = st.text_input(
                    "Registered Mobile Number",
                    placeholder="Enter registered mobile number",
                    max_chars=16,
                )
                password_input = st.text_input(
                    "4-Digit PIN", type="password", placeholder="Enter your 4-digit PIN", max_chars=4
                )
                login_clicked = st.form_submit_button(
                    "LOGIN", use_container_width=True
                )

            if login_clicked:
                mobile_key = normalize_mobile(mobile_input)
                matching_rows = df[df["Mobile_Number"].astype(str).map(normalize_mobile) == mobile_key]
                if (not matching_rows.empty and password_input.isdigit() and len(password_input) == 4
                        and str(matching_rows.iloc[0]["Passward"]).zfill(4) == password_input):
                    st.session_state.logged_in = True
                    st.session_state.mobile = mobile_key
                    st.session_state.auth_page = "login"
                    st.rerun()
                else:
                    st.error("Invalid mobile number or PIN.")

            if st.button("Forgot Password?", use_container_width=True):
                st.session_state.auth_page = "forgot"
                st.session_state.reset_mobile = ""
                st.session_state.otp_hash = ""
                st.session_state.otp_sent = False
                st.session_state.otp_verified = False
                st.session_state.otp_attempts = 0
                st.rerun()

            st.info("Enter the 4-digit PIN assigned to your registered mobile number. New-user registration is disabled.")

        else:
            st.subheader("🔑 Forgot Password")
            st.write("Enter the mobile number associated with your pre-configured account.")

            with st.form("request_otp_form"):
                reset_mobile_input = st.text_input(
                    "Registered Mobile Number",
                    value=st.session_state.reset_mobile,
                    placeholder="10-digit mobile number",
                    max_chars=16,
                )
                send_otp_clicked = st.form_submit_button(
                    "SEND SMS OTP", use_container_width=True
                )

            if send_otp_clicked:
                mobile_key = normalize_mobile(reset_mobile_input)
                known_mobiles = set(df["Mobile_Number"].astype(str).map(normalize_mobile))
                if not valid_indian_mobile(reset_mobile_input):
                    st.error("Enter a valid 10-digit Indian mobile number.")
                elif mobile_key not in known_mobiles:
                    # Do not reveal whether a number belongs to the dataset.
                    st.error("If this number is registered, an OTP can be sent. Check the number or contact the administrator.")
                else:
                    try:
                        otp = f"{secrets.randbelow(1_000_000):06d}"
                        destination = to_e164(reset_mobile_input)
                        send_sms_otp(destination, otp)
                        st.session_state.reset_mobile = mobile_key
                        st.session_state.otp_hash = hashlib.sha256(otp.encode()).hexdigest()
                        st.session_state.otp_expires_at = time.time() + OTP_EXPIRY_SECONDS
                        st.session_state.otp_attempts = 0
                        st.session_state.otp_verified = False
                        st.session_state.otp_sent = True
                        st.success("OTP sent by SMS. It expires in 5 minutes.")
                    except Exception as exc:
                        st.error(f"Could not send the SMS OTP: {exc}")

            if st.session_state.otp_sent and not st.session_state.otp_verified:
                st.caption("Enter the 6-digit code sent to your registered mobile.")
                with st.form("verify_otp_form"):
                    otp_input = st.text_input("SMS OTP", max_chars=6)
                    verify_clicked = st.form_submit_button(
                        "VERIFY OTP", use_container_width=True
                    )

                if verify_clicked:
                    if time.time() > st.session_state.otp_expires_at:
                        st.session_state.otp_sent = False
                        st.session_state.otp_hash = ""
                        st.error("OTP expired. Please request a new one.")
                    elif st.session_state.otp_attempts >= MAX_OTP_ATTEMPTS:
                        st.session_state.otp_sent = False
                        st.session_state.otp_hash = ""
                        st.error("Too many incorrect attempts. Request a new OTP.")
                    else:
                        st.session_state.otp_attempts += 1
                        entered_hash = hashlib.sha256(otp_input.strip().encode()).hexdigest()
                        if hmac.compare_digest(entered_hash, st.session_state.otp_hash):
                            st.session_state.otp_verified = True
                            st.success("Mobile number verified. Set a new 4-digit PIN below.")
                        else:
                            st.error("Incorrect OTP.")

            if st.session_state.otp_verified:
                with st.form("new_password_form"):
                    new_password = st.text_input(
                        "New 4-Digit PIN", type="password", max_chars=4,
                        help="Enter exactly 4 digits."
                    )
                    confirm_password = st.text_input(
                        "Confirm New 4-Digit PIN", type="password", max_chars=4
                    )
                    reset_clicked = st.form_submit_button(
                        "RESET PIN", use_container_width=True
                    )

                if reset_clicked:
                    if time.time() > st.session_state.otp_expires_at:
                        st.session_state.otp_verified = False
                        st.session_state.otp_sent = False
                        st.error("The OTP session expired. Please request a new OTP.")
                    elif not new_password.isdigit() or len(new_password) != 4:
                        st.error("PIN must contain exactly 4 digits.")
                    elif new_password != confirm_password:
                        st.error("PINs do not match.")
                    else:
                        mobile_key = st.session_state.reset_mobile
                        row_mask = df["Mobile_Number"].astype(str).map(normalize_mobile) == mobile_key
                        if not row_mask.any():
                            st.error("Registered mobile number not found. Contact the administrator.")
                        else:
                            # This selected approach stores the 4-digit PIN in the CSV column.
                            # Update every row for this mobile number so all records stay consistent.
                            df.loc[row_mask, "Passward"] = new_password
                            try:
                                df.drop(columns=[c for c in ["_mobile_key"] if c in df.columns]).to_csv(CSV_FILE, index=False)
                            except OSError as exc:
                                st.error(f"Could not save the new PIN to the dataset: {exc}")
                            else:
                                st.session_state.auth_page = "login"
                                st.session_state.reset_mobile = ""
                                st.session_state.otp_hash = ""
                                st.session_state.otp_sent = False
                                st.session_state.otp_verified = False
                                st.session_state.otp_attempts = 0
                                st.success("PIN reset successfully. Please log in with your new 4-digit PIN.")
                                st.rerun()

            if st.button("← Back to Login", use_container_width=True):
                st.session_state.auth_page = "login"
                st.session_state.reset_mobile = ""
                st.session_state.otp_hash = ""
                st.session_state.otp_sent = False
                st.session_state.otp_verified = False
                st.session_state.otp_attempts = 0
                st.rerun()

    st.stop()


# ============================================================
# AUTHENTICATED USER RECORDS
# ============================================================
mobile = st.session_state.mobile
if "Mobile_Number" not in df.columns:
    st.error("The CSV must contain a Mobile_Number column.")
    st.stop()

df["_mobile_key"] = df["Mobile_Number"].astype(str).map(normalize_mobile)
result = df[df["_mobile_key"] == mobile].drop(columns=["_mobile_key", "Passward"], errors="ignore").copy()

if result.empty:
    st.session_state.logged_in = False
    st.session_state.mobile = ""
    st.error("No fuel records are associated with this account. Contact the administrator.")
    st.stop()

# Numeric conversions keep calculations robust when CSV values contain text.
for column in ["Fuel_Quantity (L)", "Total_Cost (₹)", "Odometer_Reading (Km)", "Mileage (Km/L)", "Fuel_Price (₹/L)"]:
    if column in result.columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")

total_fuel = result["Fuel_Quantity (L)"].fillna(0).sum()
total_expense = result["Total_Cost (₹)"].fillna(0).sum()
total_purchases = len(result)
total_vehicles = result["Vehicle_Number"].nunique()

distance_total = 0.0
for _, vehicle_data in result.groupby("Vehicle_Number"):
    readings = pd.to_numeric(vehicle_data["Odometer_Reading (Km)"], errors="coerce").dropna()
    if len(readings) >= 2:
        distance_total += max(0.0, float(readings.max() - readings.min()))

if "Mileage (Km/L)" in result.columns:
    mileage_data = pd.to_numeric(result["Mileage (Km/L)"], errors="coerce").dropna()
    average_mileage = float(mileage_data.mean()) if not mileage_data.empty else 0.0
else:
    average_mileage = 0.0

# ============================================================
# SIDEBAR / NAVIGATION
# ============================================================
st.sidebar.title("🚗 Vehicle Fuel System")
st.sidebar.success(f"📱 {mobile}")
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "⛽ Fuel History", "📊 Analytics"],
)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.mobile = ""
    st.session_state.auth_page = "login"
    st.rerun()

st.markdown(
    '<div class="main-title">⛽ Vehicle Fuel Consumption Tracking System</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="subtitle">Fuel information for registered mobile number: {mobile}</div>',
    unsafe_allow_html=True,
)

# ============================================================
# DASHBOARD
# ============================================================
if page == "🏠 Dashboard":
    st.markdown('<div class="section-title">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.success(f"Records successfully loaded for {mobile}")

    col1, col2, col3, col4 = st.columns(4)
    cards = [
        (col1, "⛽ Total Fuel", f"{total_fuel:.2f} L", "blue"),
        (col2, "💰 Total Expense", f"₹{total_expense:.2f}", "green"),
        (col3, "🛣️ Distance", f"{distance_total:.2f} Km", "orange"),
        (col4, "📈 Avg Mileage", f"{average_mileage:.2f} Km/L", "purple"),
    ]
    for col, label, value, color in cards:
        with col:
            st.markdown(
                f'<div class="metric-card {color}"><h4>{label}</h4><h2>{value}</h2></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### 📊 Purchase Overview")
    col5, col6 = st.columns(2)
    col5.metric("🧾 Number of Purchases", total_purchases)
    col6.metric("🚗 Number of Vehicles", total_vehicles)

    st.markdown("### 🚘 Vehicle Information")
    vehicle_columns = [c for c in ["Vehicle_Number", "Vehicle_Type"] if c in result.columns]
    if vehicle_columns:
        st.dataframe(result[vehicle_columns].drop_duplicates(), use_container_width=True, hide_index=True)
    else:
        st.info("Vehicle details are not available in the dataset.")

# ============================================================
# FUEL HISTORY
# ============================================================
elif page == "⛽ Fuel History":
    st.markdown('<div class="section-title">⛽ Fuel History</div>', unsafe_allow_html=True)
    st.write("Search your fuel purchases by station location, station name, or other record details.")

    history = result.copy()

    # Dedicated location/station filters. These search only the current user's records.
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        location_search = st.text_input(
            "📍 Search Fuel Station Location",
            placeholder="e.g., Vijayawada, Guntur, Hyderabad",
            key="fuel_location_search",
        ).strip()
    with filter_col2:
        station_search = st.text_input(
            "⛽ Search Fuel Station Name",
            placeholder="e.g., HP Petrol Pump",
            key="fuel_station_search",
        ).strip()

    if location_search and "Fuel_Station_Location" in history.columns:
        history = history[
            history["Fuel_Station_Location"].astype(str).str.contains(
                location_search, case=False, na=False, regex=False
            )
        ]
    if station_search and "Fuel_Station" in history.columns:
        history = history[
            history["Fuel_Station"].astype(str).str.contains(
                station_search, case=False, na=False, regex=False
            )
        ]

    general_search = st.text_input(
        "🔎 Search other record details (optional)",
        placeholder="e.g., Petrol, UPI, vehicle number, date",
        key="fuel_general_search",
    ).strip().lower()
    if general_search:
        history = history[
            history.astype(str).apply(
                lambda row: row.str.lower().str.contains(
                    general_search, na=False, regex=False
                ).any(),
                axis=1,
            )
        ]

    st.success(f"Found {len(history)} matching fuel purchase records")

    preferred_columns = [
        "Date", "Vehicle_Number", "Fuel_Type", "Fuel_Quantity (L)",
        "Fuel_Price (₹/L)", "Total_Cost (₹)", "Odometer_Reading (Km)",
        "Mileage (Km/L)", "Fuel_Station", "Fuel_Station_Location",
        "Payment_Mode", "Vehicle_Type",
    ]
    display_columns = [c for c in preferred_columns if c in history.columns]
    if display_columns:
        if history.empty:
            st.warning("No fuel records match these filters. Try another location or station name.")
        else:
            st.dataframe(history[display_columns], use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Download displayed history as CSV",
                data=history[display_columns].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"fuel_history_{mobile}.csv",
                mime="text/csv",
            )
    else:
        st.warning("No displayable columns were found.")
    st.info(f"Showing {len(history)} of {len(result)} records for your account.")

# ============================================================
# ANALYTICS
# ============================================================
elif page == "📊 Analytics":
    st.markdown('<div class="section-title">📊 Fuel Analytics</div>', unsafe_allow_html=True)
    st.write(f"Analytics for mobile number: **{mobile}**")

    date_data = result.copy()
    date_data["Date"] = pd.to_datetime(date_data["Date"], dayfirst=True, errors="coerce")
    date_data = date_data.dropna(subset=["Date"]).sort_values("Date")

    if "Fuel_Type" in result.columns:
        st.subheader("⛽ Fuel Consumption by Fuel Type")
        fuel = result.groupby("Fuel_Type")["Fuel_Quantity (L)"].sum().sort_values(ascending=False)
        fig1, ax1 = plt.subplots(figsize=(8, 4.5))
        ax1.bar(fuel.index.astype(str), fuel.values)
        ax1.set_title("Fuel Consumption by Fuel Type")
        ax1.set_xlabel("Fuel Type")
        ax1.set_ylabel("Fuel Quantity (L)")
        fig1.tight_layout()
        st.pyplot(fig1)
        plt.close(fig1)

        st.subheader("💰 Fuel Expense by Fuel Type")
        expense = result.groupby("Fuel_Type")["Total_Cost (₹)"].sum().sort_values(ascending=False)
        fig2, ax2 = plt.subplots(figsize=(8, 4.5))
        ax2.bar(expense.index.astype(str), expense.values)
        ax2.set_title("Fuel Expense by Fuel Type")
        ax2.set_xlabel("Fuel Type")
        ax2.set_ylabel("Total Expense (₹)")
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close(fig2)

        st.subheader("🥧 Fuel Type Distribution")
        if fuel.sum() > 0:
            fig4, ax4 = plt.subplots(figsize=(6, 6))
            ax4.pie(fuel.values, labels=fuel.index.astype(str), autopct="%1.1f%%")
            ax4.set_title("Fuel Type Distribution")
            fig4.tight_layout()
            st.pyplot(fig4)
            plt.close(fig4)

    if not date_data.empty:
        st.subheader("📈 Fuel Consumption Trend")
        daily = date_data.groupby("Date", as_index=False)["Fuel_Quantity (L)"].sum()
        fig3, ax3 = plt.subplots(figsize=(10, 4.5))
        ax3.plot(daily["Date"], daily["Fuel_Quantity (L)"], marker="o")
        ax3.set_title("Fuel Consumption Trend")
        ax3.set_xlabel("Date")
        ax3.set_ylabel("Fuel Quantity (L)")
        fig3.autofmt_xdate()
        fig3.tight_layout()
        st.pyplot(fig3)
        plt.close(fig3)

        st.subheader("🗓️ Monthly Fuel Summary")
        monthly = date_data.set_index("Date").resample("MS").agg(
            Fuel_Quantity=("Fuel_Quantity (L)", "sum"),
            Total_Expense=("Total_Cost (₹)", "sum"),
        )
        monthly.index = monthly.index.strftime("%Y-%m")
        st.dataframe(monthly, use_container_width=True)
    else:
        st.info("Valid dates are not available to create time-based analytics.")
