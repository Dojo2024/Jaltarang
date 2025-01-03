import streamlit as st
import pandas as pd
import sqlite3
import logging
from contextlib import contextmanager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect('data_classification.db', check_same_thread=False)
        yield conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


def get_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0] for table in cursor.fetchall()]


def get_table_data(table_name):
    with get_db_connection() as conn:
        try:
            return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        except Exception as e:
            st.error(f"Error reading table {table_name}: {str(e)}")
            return None

st.title("Database Management Interface")


st.sidebar.title("Navigation")
tables = get_tables()
tables.remove("sqlite_sequence")
tables.remove("RAG_data")
selected_table = st.sidebar.selectbox("Select Table", tables)


if 'show_clear_confirm' not in st.session_state:
    st.session_state.show_clear_confirm = False


if selected_table:
    st.subheader(f"Managing {selected_table}")
    
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🗑 Clear Table", type="secondary", key="clear_button"):
            st.session_state.show_clear_confirm = True

    
    if st.session_state.show_clear_confirm:
        st.warning(f"⚠ Are you sure you want to clear all data from {selected_table}? This action cannot be undone!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Clear All", key="confirm_clear"):
                with get_db_connection() as conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM {selected_table}")
                        conn.commit()
                        st.success(f"{selected_table} cleared successfully!")
                        st.session_state.show_clear_confirm = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing table: {str(e)}")
        with col2:
            if st.button("❌ No, Cancel", key="cancel_clear"):
                st.session_state.show_clear_confirm = False
                st.rerun()

    
    data = get_table_data(selected_table)
    
    if data is not None and not data.empty:
        
        search_term = st.text_input("🔍 Search entries:", "", placeholder="Type to search...")
        
        
        if search_term:
            mask = data.astype(str).apply(lambda x: x.str.contains(search_term, case=False)).any(axis=1)
            filtered_data = data[mask]
        else:
            filtered_data = data

        
        st.markdown(f"""
            <div style='padding-bottom: 10px; border-radius: 5px; margin: 10px 0;'>
                📊 Showing <b>{len(filtered_data)}</b> out of <b>{len(data)}</b> entries
            </div>
        """, unsafe_allow_html=True)

        
        view_mode = st.radio("Select View Mode:", 
                            ["Interactive Table", "Detailed View"], 
                            horizontal=True)

        if view_mode == "Interactive Table":
            
            st.dataframe(
                filtered_data,
                use_container_width=True,
                hide_index=True,
            )
            
            
            st.markdown("### Actions")
            col1, col2 = st.columns(2)
            with col1:
                entry_id = st.number_input("Enter Row ID to modify:", 
                                         min_value=1, 
                                         max_value=len(filtered_data))
            with col2:
                action = st.selectbox("Choose Action:", ["Select Action", "Edit", "Delete"])
            
            if action == "Edit":
                row = filtered_data.iloc[entry_id-1] if entry_id <= len(filtered_data) else None
                if row is not None:
                    with st.form(key="edit_form"):
                        st.subheader(f"Edit Entry {entry_id}")
                        new_values = {}
                        for column in row.index:
                            new_values[column] = st.text_input(column, row[column])
                        
                        if st.form_submit_button("💾 Save Changes"):
                            with get_db_connection() as conn:
                                try:
                                    cursor = conn.cursor()
                                    set_clause = ", ".join([f"{col} = ?" for col in new_values.keys()])
                                    query = f"UPDATE {selected_table} SET {set_clause} WHERE rowid = ?"
                                    cursor.execute(query, list(new_values.values()) + [entry_id])
                                    conn.commit()
                                    st.success("✅ Entry updated successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating entry: {str(e)}")
            
            elif action == "Delete":
                st.warning(f"Are you sure you want to delete entry {entry_id}?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, Delete"):
                        with get_db_connection() as conn:
                            try:
                                cursor = conn.cursor()
                                cursor.execute(f"DELETE FROM {selected_table} WHERE rowid = ?", (entry_id,))
                                conn.commit()
                                st.success(f"Entry {entry_id} deleted successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting entry: {str(e)}")
                with col2:
                    if st.button("Cancel"):
                        st.rerun()

        else:  
            for i, (idx, row) in enumerate(filtered_data.iterrows()):
                with st.expander(f"📝 Entry {i+1}", expanded=i==0):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        for column in row.index:
                            st.markdown(f"#### {column}")
                            st.text_area(f"{column}_{i}", row[column], 
                                       height=100 if len(str(row[column])) > 100 else 50, 
                                       disabled=True)
                    
                    with col2:
                        st.markdown("#### Actions")
                        if st.button("✏ Edit", key=f"edit_{i}"):
                            st.session_state[f"editing_{i}"] = True
                            
                        if st.button("🗑 Delete", key=f"delete_{i}"):
                            with get_db_connection() as conn:
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute(f"DELETE FROM {selected_table} WHERE rowid = ?", (idx+1,))
                                    conn.commit()
                                    st.success(f"Entry {i+1} deleted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error deleting entry: {str(e)}")
    else:
        st.info(f"No data available in {selected_table}.")
else:
    st.info("Please select a table from the sidebar to begin.")
