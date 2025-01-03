import streamlit as st
from utils import nav_title

st.set_page_config(
    page_title="Naksha Maritime Surveillance System",
    page_icon="🚢",
    layout="wide",
)

nav_title()

dashboard_page = st.Page("files/1_zonalMap.py", title="Zonal Map", icon="📊", default=True)
message_map_page = st.Page("files/2_surveillanceMap.py", title="Surveillance Map", icon="📨")
upload_page = st.Page("files/3_upload.py", title="Upload Reports", icon="📤")
ai_page = st.Page("files/4_nakshaAI.py", title="Naksha AI", icon="🤖")
db_page = st.Page("files/5_manage.py", title="Database Management", icon="🗄️")

pages = {
    "Dashboard": [dashboard_page, message_map_page],
    "AI Tools": [ai_page],
    "Data Management": [upload_page, db_page],
}

with st.sidebar:
    st.title("About Naksha Maritime Surveillance System")
    st.write(
        """
        Naksha is a Streamlit-based application for maritime surveillance. 
        It provides a set of tools for visualizing and analyzing maritime data.
        """
    )

pg = st.navigation(pages)
pg.run()