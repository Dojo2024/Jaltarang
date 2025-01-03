import streamlit as st
from naksha import chat_with_agent

st.title("🤖 Naksha AI")
st.markdown("""
Welcome! I can help you understand the data stored in the system.\n
Just ask me anything about any maritime information you need that is stored in the database!
""")


user_input = st.text_input(
    "Your question:",
    placeholder="Ask anything about the stored data...",
    key="user_input"
)


if user_input:
    st.divider()
    
    
    with st.spinner("Processing your question..."):
        
        response = chat_with_agent(user_input)
    
    
    col1, col2 = st.columns([1, 20])
    with col1:
        st.markdown("#### 💡")
    with col2:
        st.markdown("#### Answer")
        st.write(response)
        
    
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 3])