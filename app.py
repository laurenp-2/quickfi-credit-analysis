"""
QuickFi Credit Agent — Streamlit UI
Run:  streamlit run app.py
"""
import streamlit as st

from agents import generate_credit_summary
from utils.ingest import ingest_documents

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

# validation mode
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

# credit summary mode
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

    loan_amount_input = st.number_input(
        "Requested Loan Amount ($)",
        min_value=0.0,
        value=0.0,
        step=1000.0,
        help="Optional — used to calculate the loan-to-revenue ratio",
    )

    if fin_zip:
        st.success(f"Uploaded: {fin_zip.name} ({fin_zip.size / 1024:.1f} KB)")

    if st.button("Generate Credit Summary", type="primary", disabled=not fin_zip):
        loan_amount = loan_amount_input if loan_amount_input > 0 else None

        with st.spinner("Extracting and classifying documents…"):
            try:
                ingest_result = ingest_documents(
                    financial_zip=fin_zip,
                    loan_amount=loan_amount,
                )
            except Exception as e:
                st.error(f"Document ingestion failed: {e}")
                st.stop()

        with st.spinner("Analyzing with AI…"):
            try:
                summary = generate_credit_summary(ingest_result)
            except Exception as e:
                st.error(f"Credit summary generation failed: {e}")
                st.stop()

        # results display

        risk = summary.get("Risk Analysis", "Unknown")
        risk_color = {"Low Risk": "green", "Medium Risk": "orange", "High Risk": "red"}.get(risk, "gray")
        st.markdown(f"### Risk Analysis: :{risk_color}[{risk}]")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Credit Profile")
            for point in summary.get("Credit Profile", []):
                st.markdown(f"- {point}")

            st.subheader("Fraud Detection")
            st.markdown(summary.get("Fraud Detection", "No issues identified."))

        with col_right:
            suggestions = summary.get("Suggestions", {})

            st.subheader("Additional Documentation Needed")
            for item in suggestions.get("Additional Documentation", []):
                st.markdown(f"- {item}")

            st.subheader("Improvement Suggestions")
            for item in suggestions.get("Improvement Suggestions", []):
                st.markdown(f"- {item}")

        st.divider()

        
        ratios = ingest_result.get("ratios", {})
        if ratios:
            with st.expander("Calculated Ratios", expanded=False):
                _skip = {"flags", "data_gaps", "overall_tier"}
                for name, result in ratios.items():
                    if name in _skip or not isinstance(result, dict):
                        continue
                    val  = result.get("value")
                    tier = result.get("tier", "unknown")
                    tier_color = {"low": "green", "medium": "orange", "high": "red"}.get(tier, "gray")
                    st.markdown(f"**{name}**: {val} — :{tier_color}[{tier} risk]")
                if ratios.get("data_gaps"):
                    st.warning("Data gaps: " + ", ".join(ratios["data_gaps"]))
                if ratios.get("flags"):
                    st.error("Flags: " + ", ".join(ratios["flags"]))

        # 
        with st.expander("Raw JSON Response", expanded=False):
            st.json(summary)
