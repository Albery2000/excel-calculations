import streamlit as st
import subprocess
import sys

# Debug: Check if plotly is installed and list all packages
try:
    import plotly
    import plotly.express as px
    st.success("Plotly and Plotly Express are installed!")
except ModuleNotFoundError as e:
    st.error(f"Failed to import package: {e}")
    st.write(f"Python version: {sys.version}")
    # Run pip list and capture output
    try:
        pip_list_output = subprocess.check_output([sys.executable, "-m", "pip", "list"], text=True)
        st.write("Installed packages:")
        st.code(pip_list_output)
        # Check specifically for plotly
        if "plotly" not in pip_list_output:
            st.error("Plotly is not installed in the environment.")
        else:
            st.write("Plotly is listed as installed, but import failed. Possible version mismatch or corrupted install.")
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to run pip list: {e}")
    # Do not stop the app here to allow further debugging
    st.write("Proceeding with the app despite the error (charts may not work).")

import pandas as pd
import io

# Rest of your code...
# ----------------- Page Config -----------------
st.set_page_config(page_title="📊 Transaction Analyzer", layout="wide")

st.title("📊 Transaction Analyzer")
st.markdown("Analyze transaction amounts by **Account Code**, with filters, pivot tables, charts, and Excel export.")

# ----------------- Download requirements.txt -----------------
st.markdown("### 📋 Download Dependencies")
requirements_content = """streamlit==1.36.0
pandas==2.2.2
openpyxl==3.1.5
plotly==5.22.0
plotly-express==0.5.0"""
st.download_button(
    label="📥 Download requirements.txt",
    data=requirements_content,
    file_name="requirements.txt",
    mime="text/plain"
)
st.divider()

# ----------------- File Upload -----------------
uploaded_file = st.file_uploader("📁 Upload Excel File", type=["xlsx"])

if uploaded_file:
    # Load and clean
    df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    df = df.dropna(subset=['Transaction Date', 'Account Code', 'Base Amount'])

    # Date processing
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'])
    df['Year'] = df['Transaction Date'].dt.year
    df['Month'] = df['Transaction Date'].dt.strftime('%b')
    df['Month_Num'] = df['Transaction Date'].dt.month

    # ----------------- Sidebar Filters -----------------
    with st.sidebar:
        st.header("🔍 Filters")

        selected_year = st.selectbox("Select Year", sorted(df['Year'].unique(), reverse=True))
        df_year = df[df['Year'] == selected_year]

        account_codes = sorted(df_year['Account Code'].unique())
        selected_codes = st.multiselect("Select Account Codes", account_codes, default=account_codes)

        month_options = df_year['Month'].unique()
        month_map = dict(zip(df_year['Month'], df_year['Month_Num']))
        sorted_months = sorted(month_options, key=lambda m: month_map[m])
        selected_months = st.multiselect("Select Months", sorted_months, default=sorted_months)

    # ----------------- Filtered Data -----------------
    filtered_df = df_year[
        (df_year['Account Code'].isin(selected_codes)) &
        (df_year['Month'].isin(selected_months))
    ]

    # ----------------- KPIs -----------------
    st.markdown("### 📌 Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("🔢 Total Transactions", f"{len(filtered_df):,}")
    col2.metric("💰 Total Amount", f"${filtered_df['Base Amount'].sum():,.2f}")
    col3.metric("📈 Avg per Transaction", f"${filtered_df['Base Amount'].mean():,.2f}")

    st.divider()

    # ----------------- Pivot Table -----------------
    st.subheader(f"📆 Pivot Table for {selected_year}")
    
    # Create pivot table based on filtered data (selected months and account codes)
    pivot = pd.pivot_table(
        filtered_df,
        index='Account Code',
        columns='Month',
        values='Base Amount',
        aggfunc='sum',
        fill_value=0
    )
    
    # Sort columns by month order and reindex to include only selected months
    pivot = pivot.reindex(columns=selected_months, fill_value=0)
    
    # Calculate total for all months in the selected year (ignoring month filter)
    total_pivot = pd.pivot_table(
        df_year[df_year['Account Code'].isin(selected_codes)],
        index='Account Code',
        values='Base Amount',
        aggfunc='sum',
        fill_value=0
    )
    pivot['Total'] = total_pivot
    
    # Format the pivot table
    st.dataframe(pivot.style.format("{:,.2f}"), use_container_width=True)

    # ----------------- Bar Chart -----------------
    st.subheader("📊 Monthly Total Amount")
    monthly_totals = filtered_df.groupby('Month').agg({'Base Amount': 'sum'}).reset_index()
    monthly_totals['Month_Num'] = monthly_totals['Month'].map(month_map)
    monthly_totals = monthly_totals.sort_values(by='Month_Num')

    try:
        bar_fig = px.bar(
            monthly_totals,
            x='Month',
            y='Base Amount',
            text_auto='.2s',
            color='Month',
            title="Monthly Transaction Amounts",
            labels={'Base Amount': 'Amount'},
        )
        st.plotly_chart(bar_fig, use_container_width=True)
    except NameError:
        st.warning("Bar chart cannot be displayed because Plotly is not available.")

    # ----------------- Pie Chart -----------------
    st.subheader("📎 Amount Distribution by Account Code")
    code_totals = filtered_df.groupby('Account Code').agg({'Base Amount': 'sum'}).reset_index()
    
    try:
        pie_fig = px.pie(
            code_totals,
            names='Account Code',
            values='Base Amount',
            title="Contribution by Account Code",
            hole=0.4
        )
        st.plotly_chart(pie_fig, use_container_width=True)
    except NameError:
        st.warning("Pie chart cannot be displayed because Plotly is not available.")

    # ----------------- Excel
