#!/usr/bin/env python3
"""
Script to update all AI calls in streamlit_demo_local.py to use the unified AI service
"""

import re

# Read the file
with open('streamlit_demo_local.py', 'r') as f:
    content = f.read()

# Replace imports
content = content.replace(
    "from config import get_anthropic_api_key, get_app_settings, get_feature_flags, validate_config",
    "from ai_service import make_ai_call, get_ai_service"
)

# Remove the validate_config block
content = re.sub(
    r'# Validate configuration.*?st\.stop\(\)',
    '''# Check if AI service is available
ai_service = get_ai_service()
if not ai_service.is_available() and 'initialized' not in st.session_state:
    st.error("Configuration Error")
    st.error("• No AI service configured")
    st.info("Please add ANTHROPIC_API_KEY or OPENAI_API_KEY to .streamlit/secrets.toml or .env file")
    st.stop()''',
    content,
    flags=re.DOTALL
)

# Remove get_anthropic_client function
content = re.sub(
    r'# Get Anthropic client.*?return anthropic\.Anthropic\(api_key=api_key\)',
    '# AI service is now handled by ai_service module',
    content,
    flags=re.DOTALL
)

# Replace all client = get_anthropic_client() checks
content = re.sub(
    r'client = get_anthropic_client\(\)\s+if not client:',
    'if not get_ai_service().is_available():',
    content
)

# Replace all response = client.messages.create patterns
# Pattern 1: With system prompt
content = re.sub(
    r'response = client\.messages\.create\(\s*model="[^"]+",\s*max_tokens=(\d+),\s*system=([^,]+),\s*messages=\[.*?\]\s*\)',
    r'response_text = make_ai_call(prompt, max_tokens=\1, system_prompt=\2)',
    content,
    flags=re.DOTALL
)

# Pattern 2: Without system prompt
content = re.sub(
    r'response = client\.messages\.create\(\s*model="[^"]+",\s*max_tokens=(\d+),\s*messages=\[\{"role": "user", "content": prompt\}\]\s*\)',
    r'response_text = make_ai_call(prompt, max_tokens=\1)',
    content
)

# Replace response.content[0].text.strip() patterns
content = re.sub(
    r'response\.content\[0\]\.text\.strip\(\)',
    'response_text',
    content
)

# Add error handling after make_ai_call
content = re.sub(
    r'response_text = make_ai_call\(prompt, max_tokens=(\d+)\)\n',
    r'''response_text = make_ai_call(prompt, max_tokens=\1)
        if not response_text:
            logger.error("AI call failed")
            return None
''',
    content
)

# Update the sidebar status check
content = re.sub(
    r'ai_available = get_anthropic_client\(\) is not None\s+if ai_available:\s+st\.success.*?\s+else:\s+st\.warning.*?',
    '''ai_status = get_ai_service().get_status()
        st.info(ai_status)''',
    content,
    flags=re.DOTALL
)

# Write the updated content
with open('streamlit_demo_local.py', 'w') as f:
    f.write(content)

print("Updated streamlit_demo_local.py with unified AI service")