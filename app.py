import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

# --------------------------------------------------
# PAGE SETTINGS
# --------------------------------------------------

st.set_page_config(
    page_title="Vehicle Fuel Consumption Tracking System",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #eef7ff, #f8f4ff);
}

.main-title {
    text-align: center;
    font-size: 38px;
    font-weight: 800;
    color: #173b6c;
    margin-top: 20px;
}

.subtitle {
    text-align: center;
    color: #5b6472;
    font-size: 17px;
    margin-bottom: 30px;
}

.login-box {
    background: white;
    padding: 35px;
    border-radius: 20px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.10);
    max-width: 650px;
    margin: auto;
}

.card {
    padding: 20px;
    border-radius: 18px;
    color: white;
    text-align: center;
    box-shadow: 0 5px 15px rgba(0,0,0,0.12);
}

.card h4 {
    margin: 0;
    font-size: 16px;
}

.card h2 {
    margin: 8px 0 0 0;
    font-size: 27px;
}

.blue {
    background: linear-gradient(135deg, #2196f3, #1565c0);
}

.green {
    background: linear-gradient(135deg, #00b894, #00897b);
}

.orange {
    background: linear-gradient(135deg, #ff9800, #ef6c00);
}

.purple {
    background: linear-gradient(135deg, #9c27b0, #6a1b9a);
}

.section-title {
    color: #173b6c;
    font-size: 28px;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# LOAD DATASET FROM GITHUB
# --------------------------------------------------

CSV_FILE = "vehicle_fuel_purchase_dataset_with_mileage.csv"

if not os.path.exists(CSV_FILE):
    st.error("Dataset file not found.")
    st.stop()

df = pd.read_csv(CSV_FILE)


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "mobile" not in st.session_state:
    st.session_state.mobile = ""


# --------------------------------------------------
# LOGIN / MOBILE NUMBER PAGE
# --------------------------------------------------

if not st.session_state.logged_in:

    st.markdown(
        '<div class="main-title">⛽ Vehicle Fuel Consumption Tracking System</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Track your vehicle fuel consumption, expenses and mileage</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    st.markdown("### 📱 Enter Your Mobile Number")

    mobile_input = st.text_input(
        "Mobile Number",
        placeholder="Enter registered mobile number",
        max_chars=15
    )

    if st.button("🔍 CHECK MY RECORDS", use_container_width=True):

        mobile_input = mobile_input.strip()

        result = df[
            df["Mobile_Number"].astype(str).str.strip() == mobile_input
        ]

        if result.empty:

            st.error(
                "❌ No vehicle fuel records found for this mobile number."
            )

        else:

            st.session_state.mobile = mobile_input
            st.session_state.logged_in = True

            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    st.info(
        "🔐 Enter the mobile number registered with the vehicle fuel records."
    )

    st.stop()


# --------------------------------------------------
# USER DATA
# --------------------------------------------------

mobile = st.session_state.mobile

result = df[
    df["Mobile_Number"].astype(str).str.strip() == mobile
].copy()

if result.empty:

    st.session_state.logged_in = False
    st.error("No records found.")
    st.stop()


# --------------------------------------------------
# CALCULATIONS
# --------------------------------------------------

total_fuel = result["Fuel_Quantity (L)"].sum()

total_expense = result["Total_Cost (₹)"].sum()

total_purchases = len(result)

total_vehicles = result["Vehicle_Number"].nunique()


# Total distance travelled
distance_total = 0

for vehicle, vehicle_data in result.groupby("Vehicle_Number"):

    vehicle_data = vehicle_data.copy()

    vehicle_data["Odometer_Reading (Km)"] = pd.to_numeric(
        vehicle_data["Odometer_Reading (Km)"],
        errors="coerce"
    )

    if vehicle_data["Odometer_Reading (Km)"].notna().any():

        distance_total += (
            vehicle_data["Odometer_Reading (Km)"].max()
            - vehicle_data["Odometer_Reading (Km)"].min()
        )


# Average mileage
if "Mileage (Km/L)" in result.columns:

    mileage_data = pd.to_numeric(
        result["Mileage (Km/L)"],
        errors="coerce"
    ).dropna()

    if len(mileage_data) > 0:
        average_mileage = mileage_data.mean()
    else:
        average_mileage = 0

else:

    average_mileage = 0


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("🚗 Vehicle Fuel System")

st.sidebar.success(
    f"📱 {mobile}"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Dashboard",
        "⛽ Fuel History",
        "📊 Analytics"
    ]
)

st.sidebar.markdown("---")

if st.sidebar.button("🚪 Logout", use_container_width=True):

    st.session_state.logged_in = False
    st.session_state.mobile = ""

    st.rerun()


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    '<div class="main-title">⛽ Vehicle Fuel Consumption Tracking System</div>',
    unsafe_allow_html=True
)

st.markdown(
    f'<div class="subtitle">Fuel information for mobile number: {mobile}</div>',
    unsafe_allow_html=True
)


# ==================================================
# DASHBOARD
# ==================================================

if page == "🏠 Dashboard":

    st.markdown(
        '<div class="section-title">🏠 Dashboard</div>',
        unsafe_allow_html=True
    )

    st.success(
        f"✅ Records successfully loaded for {mobile}"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.markdown(
            f"""
            <div class="card blue">
                <h4>⛽ Total Fuel</h4>
                <h2>{total_fuel:.2f} L</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="card green">
                <h4>💰 Total Expense</h4>
                <h2>₹{total_expense:.2f}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="card orange">
                <h4>🛣️ Distance</h4>
                <h2>{distance_total:.2f} Km</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:

        st.markdown(
            f"""
            <div class="card purple">
                <h4>📈 Avg Mileage</h4>
                <h2>{average_mileage:.2f} Km/L</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("### 📊 Purchase Overview")

    col5, col6 = st.columns(2)

    with col5:

        st.metric(
            "🧾 Number of Purchases",
            total_purchases
        )

    with col6:

        st.metric(
            "🚗 Number of Vehicles",
            total_vehicles
        )

    st.markdown("### 🚘 Vehicle Information")

    vehicle_info = result[
        [
            "Vehicle_Number",
            "Vehicle_Type"
        ]
    ].drop_duplicates()

    st.dataframe(
        vehicle_info,
        use_container_width=True,
        hide_index=True
    )


# ==================================================
# FUEL HISTORY
# ==================================================

elif page == "⛽ Fuel History":

    st.markdown(
        '<div class="section-title">⛽ Fuel History</div>',
        unsafe_allow_html=True
    )

    st.success(
        f"Showing {len(result)} fuel purchase records"
    )

    search = st.text_input(
        "🔍 Search records"
    ).strip().lower()

    history = result.copy()

    if search:

        history = history[
            history.astype(str)
            .apply(
                lambda row:
                row.str.lower().str.contains(
                    search,
                    na=False
                ).any(),
                axis=1
            )
        ]

    display_columns = [
        "Date",
        "Vehicle_Number",
        "Fuel_Type",
        "Fuel_Quantity (L)",
        "Fuel_Price (₹/L)",
        "Total_Cost (₹)",
        "Odometer_Reading (Km)",
        "Fuel_Station",
        "Fuel_Station_Location",
        "Payment_Mode",
        "Vehicle_Type"
    ]

    st.dataframe(
        history[display_columns],
        use_container_width=True,
        hide_index=True
    )

    st.info(
        f"Showing {len(history)} records"
    )


# ==================================================
# ANALYTICS
# ==================================================

elif page == "📊 Analytics":

    st.markdown(
        '<div class="section-title">📊 Fuel Analytics</div>',
        unsafe_allow_html=True
    )

    st.write(
        f"Analytics for Mobile Number: **{mobile}**"
    )

    # ----------------------------------------------
    # Fuel Consumption
    # ----------------------------------------------

    st.subheader("⛽ Fuel Consumption by Fuel Type")

    fuel = result.groupby(
        "Fuel_Type"
    )["Fuel_Quantity (L)"].sum()

    fig1, ax1 = plt.subplots(figsize=(8, 5))

    ax1.bar(
        fuel.index,
        fuel.values
    )

    ax1.set_title("Fuel Consumption by Fuel Type")
    ax1.set_xlabel("Fuel Type")
    ax1.set_ylabel("Fuel Quantity (L)")

    st.pyplot(fig1)

    # ----------------------------------------------
    # Fuel Expense
    # ----------------------------------------------

    st.subheader("💰 Fuel Expense by Fuel Type")

    expense = result.groupby(
        "Fuel_Type"
    )["Total_Cost (₹)"].sum()

    fig2, ax2 = plt.subplots(figsize=(8, 5))

    ax2.bar(
        expense.index,
        expense.values
    )

    ax2.set_title("Fuel Expense by Fuel Type")
    ax2.set_xlabel("Fuel Type")
    ax2.set_ylabel("Total Expense (₹)")

    st.pyplot(fig2)

    # ----------------------------------------------
    # Fuel Trend
    # ----------------------------------------------

    st.subheader("📈 Fuel Consumption Trend")

    date_data = result.copy()

    date_data["Date"] = pd.to_datetime(
        date_data["Date"],
        dayfirst=True,
        errors="coerce"
    )

    date_data = date_data.sort_values("Date")

    fig3, ax3 = plt.subplots(figsize=(10, 5))

    ax3.plot(
        date_data["Date"],
        date_data["Fuel_Quantity (L)"],
        marker="o"
    )

    ax3.set_title("Fuel Consumption Trend")
    ax3.set_xlabel("Date")
    ax3.set_ylabel("Fuel Quantity (L)")

    plt.xticks(rotation=45)

    st.pyplot(fig3)

    # ----------------------------------------------
    # Fuel Distribution
    # ----------------------------------------------

    st.subheader("🥧 Fuel Type Distribution")

    fig4, ax4 = plt.subplots(figsize=(7, 7))

    ax4.pie(
        fuel.values,
        labels=fuel.index,
        autopct="%1.1f%%"
    )

    ax4.set_title("Fuel Type Distribution")

    st.pyplot(fig4)
