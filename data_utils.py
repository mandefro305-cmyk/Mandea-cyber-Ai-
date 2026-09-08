import io
import pandas as pd
import streamlit as st

def parse_csv_file(file_bytes: bytes, filename: str) -> dict:
    """
    Parses CSV/Excel file into pandas DataFrame and extracted text summary.
    """
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        summary = f"Dataset: {filename}\nRows: {df.shape[0]}, Columns: {df.shape[1]}\n"
        summary += f"Columns: {', '.join(df.columns)}\n\n"
        summary += f"First 5 Rows:\n{df.head().to_string()}\n"
        return {
            "success": True,
            "filename": filename,
            "df": df,
            "summary_text": summary
        }
    except Exception as e:
        return {
            "success": False,
            "filename": filename,
            "error": str(e)
        }

def render_data_analysis_ui(df: pd.DataFrame, filename: str):
    """
    Renders interactive dataset preview and chart generation in Streamlit.
    """
    st.subheader(f"📊 Dataset Analysis: {filename}")
    st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")

    col1, col2 = st.tabs(["📋 Data Preview & Stats", "📈 Quick Chart Visualizer"])

    with col1:
        st.dataframe(df.head(50), use_container_width=True)
        st.markdown("**Summary Statistics:**")
        st.dataframe(df.describe(include="all").transpose(), use_container_width=True)

    with col2:
        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
        all_cols = df.columns.tolist()

        if len(num_cols) < 1:
            st.warning("No numeric columns found in dataset for charting.")
        else:
            chart_type = st.selectbox("Chart Type", ["Bar Chart", "Line Chart", "Scatter Plot"], key=f"chart_type_{filename}")
            x_col = st.selectbox("X Axis Column", options=all_cols, index=0, key=f"x_col_{filename}")
            y_col = st.selectbox("Y Axis Column", options=num_cols, index=0, key=f"y_col_{filename}")

            if chart_type == "Bar Chart":
                st.bar_chart(df.set_index(x_col)[y_col])
            elif chart_type == "Line Chart":
                st.line_chart(df.set_index(x_col)[y_col])
            elif chart_type == "Scatter Plot":
                st.scatter_chart(df, x=x_col, y=y_col)
