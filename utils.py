import streamlit as st

def nav_title():
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"]::before {
                content: "Welcome to Naksha!";
                margin-left: 20px;
                margin-top: 20px;
                font-size: 30px;
                position: relative;
                top: 0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )