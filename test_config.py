import streamlit as st
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

st.title("Configuration Test")

# Check for API keys
anthropic_key = None
openai_key = None

# Try Streamlit secrets first
try:
    if 'ANTHROPIC_API_KEY' in st.secrets:
        anthropic_key = st.secrets['ANTHROPIC_API_KEY']
        st.success("✅ Found Anthropic key in Streamlit secrets")
    if 'OPENAI_API_KEY' in st.secrets:
        openai_key = st.secrets['OPENAI_API_KEY']
        st.success("✅ Found OpenAI key in Streamlit secrets")
except:
    st.info("Streamlit secrets not configured")

# Try environment variables
if not anthropic_key:
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if anthropic_key:
        st.success("✅ Found Anthropic key in environment variables")
        st.write(f"Key starts with: {anthropic_key[:15]}...")
        
if not openai_key:
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        st.success("✅ Found OpenAI key in environment variables")
        st.write(f"Key starts with: {openai_key[:15]}...")

# Summary
st.markdown("---")
st.markdown("### Summary")
if anthropic_key:
    st.success("✅ Anthropic API key is available")
else:
    st.error("❌ Anthropic API key not found")
    
if openai_key:
    st.success("✅ OpenAI API key is available")
else:
    st.error("❌ OpenAI API key not found")

if anthropic_key or openai_key:
    st.success("✅ At least one AI service is configured!")
else:
    st.error("❌ No AI services configured")
    st.info("Add keys to .streamlit/secrets.toml or .env file")