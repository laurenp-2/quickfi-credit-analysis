"""
QuickFi Credit Agent — Streamlit UI 
Run:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="QuickFi Credit Agent",
    page_icon="🏦",
    layout="wide",
)

st.title("QuickFi Credit Agent")
st.caption("AI-powered credit validation and risk analysis for commercial equipment finance")

mode = st.sidebar.radio(
    "Select Mode",
    ["Validation", "Credit Summary"],
    help="Validation: compare application data against credit records.\n"
         "Credit Summary: analyze financial documents and generate a risk report.",
)

# Validation Mode 
if mode == "Validation":
    st.header("Credit Application Validation")
    st.markdown(
        "Upload the credit application spreadsheet and one or more credit record PDFs. "
        "The agent will compare key fields and flag discrepancies."
    )

    col1, col2 = st.columns(2)
    with col1:
        app_file = st.file_uploader(
            "Credit Application (Excel or CSV)",
            type=["xlsx", "xls", "csv"],
            help="The 'Input Data' spreadsheet",
        )
    with col2:
        credit_files = st.file_uploader(
            "Credit Record PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            help="One PDF per credit record pulled for this applicant",
        )

    if st.button("Run Validation", type="primary", disabled=not (app_file and credit_files)):
        st.info("Validation pipeline coming in Week 4.")

# Credit Summary Mode 
else:
    st.header("Credit Summary Generator")
    st.markdown(
        "Upload a zip file containing the borrower's financial documents "
        "(P&L, balance sheet, bank statements, tax returns, etc.)."
    )

    fin_zip = st.file_uploader(
        "Financial Documents (.zip)",
        type=["zip"],
        help="Zip archive containing PDFs or images of financial documents",
    )

    if fin_zip:
        st.success(f"Uploaded: {fin_zip.name} ({fin_zip.size / 1024:.1f} KB)")

    if st.button("Generate Credit Summary", type="primary", disabled=not fin_zip):
        st.info("Credit summary pipeline coming in Week 4.")
