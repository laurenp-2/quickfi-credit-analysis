"""
QuickFi Credit Agent — Streamlit UI
Run:  streamlit run app.py
"""

import tempfile
from pathlib import Path

import streamlit as st

from agents.validation_agent import ValidationAgent

from agents import generate_credit_summary, generate_credit_summary_raw
from extractors.financial_doc_extractor import FinancialDocExtractor
from utils.ingest import ingest_documents

st.set_page_config(
    page_title="QuickFi Credit Agent",
    page_icon="🏦",
    layout="wide",
)

st.title("QuickFi Credit Agent")
st.caption(
    "AI-powered credit validation and risk analysis for commercial equipment finance"
)

mode = st.sidebar.radio(
    "Select Mode",
    ["Validation", "Credit Summary"],
    help=(
        "Validation: compare application data against credit records.\n"
        "Credit Summary: analyze financial documents and generate a risk report."
    ),
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
            help="The Input Data spreadsheet",
        )

    with col2:
        credit_files = st.file_uploader(
            "Credit Record PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            help="One PDF per credit record pulled for this applicant",
        )

    if st.button(
        "Run Validation",
        type="primary",
        disabled=not (app_file and credit_files),
    ):

        with st.spinner("Running validation..."):

            # Save application file temporarily
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=Path(app_file.name).suffix,
            ) as tmp_app:
                tmp_app.write(app_file.getbuffer())
                application_path = tmp_app.name

            # Save credit record files temporarily
            credit_paths = []

            for uploaded_file in credit_files:
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=Path(uploaded_file.name).suffix,
                ) as tmp_credit:
                    tmp_credit.write(uploaded_file.getbuffer())
                    credit_paths.append(tmp_credit.name)

            # Run validation agent
            agent = ValidationAgent()

            result = agent.run(
                application_file=application_path,
                credit_record_files=credit_paths,
            )

        st.success("Validation complete")

        st.subheader("Validation Summary")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Match Score", result["match_score"])

        with c2:
            st.metric("Confidence", result["match_confidence"].title())

        with c3:
            st.metric("Result", result["overall_result"])

        st.write("Matched Credit Record:", result["matched_credit_record"])

        st.subheader("Identity Match Summary")
        st.json(result["identity_match_summary"])

        st.subheader("Field Comparisons")
        st.dataframe(
            result["field_comparisons"],
            use_container_width=True,
        )

# -------------------------------------------------------------------
# Credit Summary Mode
# -------------------------------------------------------------------
else:
    st.header("Credit Summary Generator")

    st.markdown(
        "Upload a zip file containing the borrower's financial documents "
        "(P&L, balance sheet, bank statements, tax returns, etc.)."
    )

    pure_ai = st.toggle(
        "Pure AI Mode",
        help="Skip all parsing and ratio calculations — let the AI analyze the raw documents directly.",
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
        help="Optional — used to calculate the loan-to-revenue ratio (standard mode) or assess loan sizing (Pure AI mode)",
    )

    if fin_zip:
        st.success(
            f"Uploaded: {fin_zip.name} ({fin_zip.size / 1024:.1f} KB)"
        )

    if st.button("Generate Credit Summary", type="primary", disabled=not fin_zip):

        if pure_ai:
            with st.spinner("Extracting documents…"):
                try:
                    docs = FinancialDocExtractor(fin_zip.getvalue()).extract()
                except Exception as e:
                    st.error(f"Document extraction failed: {e}")
                    st.stop()

            with st.spinner("Analyzing with AI…"):
                try:
                    summary = generate_credit_summary_raw(docs, loan_amount=loan_amount_input or None)
                except Exception as e:
                    st.error(f"Credit summary generation failed: {e}")
                    st.stop()

            ingest_result = None

        else:
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

            
            st.subheader("Recommended Loan Amount")
            recommended_loan_amount = summary.get("Recommended Loan Amount", "Cannot determine")
            if recommended_loan_amount: 
                st.markdown(f"{recommended_loan_amount}")


        st.divider()

        
        if ingest_result:
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

        with st.expander("Raw JSON Response", expanded=False):
            st.json(summary)
