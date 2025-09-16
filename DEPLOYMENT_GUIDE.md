# 🚀 Streamlit Cloud Deployment Guide

## Overview
This guide explains how to deploy the Excel Data Cleaner application to Streamlit Cloud.

## Files Structure

### Main Application Files
- **`new_streamlit_app.py`** - Main application file (use this for deployment)
- **`new_streamlit_local.py`** - Local development version (with .env support)

### Configuration Priority
The application checks for API keys in this order:
1. **Streamlit Secrets** (st.secrets) - Used in deployment
2. **Environment Variables** (.env file) - Used in local development

## Deployment Steps

### Step 1: Prepare Your Repository

1. Ensure your GitHub repository contains:
```
Main_path/
├── new_streamlit_app.py         # Main app
├── ai_service.py                # AI service with token tracking
├── config.py                    # Configuration manager
├── cleaning_llm.py              # Cleaning LLM
├── code_generator.py            # Code generator
├── data_quality_scorer.py       # Quality scorer
├── header_detection.py          # Header detector
├── format_validators.py         # Format validators
├── requirements.txt             # Dependencies
└── .streamlit/
    └── secrets.toml.example     # Example secrets file
```

### Step 2: Set Up Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set branch (e.g., `main` or `master`)
6. Set main file path: `Main_path/new_streamlit_app.py`

### Step 3: Configure Secrets

In Streamlit Cloud dashboard:

1. Click on "Settings" → "Secrets"
2. Add your secrets in TOML format:

```toml
# Required - Anthropic Claude API Key
ANTHROPIC_API_KEY = "sk-ant-api03-YOUR_ACTUAL_KEY_HERE"

# Optional - OpenAI Fallback
OPENAI_API_KEY = "sk-YOUR_OPENAI_KEY_HERE"

# Optional - Application Settings
[app]
MAX_FILE_SIZE_MB = "100"
ENABLE_LOGGING = "true"
LOG_LEVEL = "INFO"

# Optional - Feature Flags
[features]
ENABLE_AI_HEADER_DETECTION = "true"
ENABLE_FORMAT_STANDARDIZATION = "true"
ENABLE_MULTI_SHEET_SUPPORT = "true"
```

### Step 4: Deploy

1. Click "Deploy"
2. Wait for the app to build and start
3. Your app will be available at: `https://[your-app-name].streamlit.app`

## Local Development Setup

### Using .env File (Recommended for Local)

1. Create `.env` file in Main_path/:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
OPENAI_API_KEY=sk-YOUR_OPENAI_KEY_HERE  # Optional
```

2. Run locally:
```bash
cd Main_path
streamlit run new_streamlit_local.py
```

### Using Streamlit Secrets (Local Testing)

1. Create `.streamlit/secrets.toml` in Main_path/:
```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit with your actual keys
```

2. Run:
```bash
streamlit run new_streamlit_app.py
```

## Environment Variables vs Streamlit Secrets

### Streamlit Secrets (Deployment)
- Used when `hasattr(st, 'secrets')` is True
- Configured in Streamlit Cloud dashboard
- Secure and encrypted
- Automatically loaded

### Environment Variables (Local)
- Used as fallback when secrets not available
- Configured in `.env` file
- Loaded via `python-dotenv`
- Good for local development

## Token Tracking & Cost Monitoring

The app includes real-time token tracking:

### Features
- **Input Tokens**: Tracked for every API call
- **Output Tokens**: Tracked for responses
- **Cost Calculation**: 
  - Claude: $3/million input, $15/million output
  - OpenAI: ~$30/million input, ~$60/million output

### Display Locations
- Sidebar: Running total
- Processing: Per-operation costs
- Download tab: Final summary

### Reset Option
- Footer includes "Reset Token Counter" button
- Clears session token tracking

## Troubleshooting

### Issue: API Key Not Found
**Solution**: 
- Check Streamlit secrets are properly formatted
- Ensure no extra spaces in keys
- Verify key starts with correct prefix

### Issue: Module Import Errors
**Solution**:
- Check all required files are in repository
- Verify requirements.txt is complete
- Ensure file paths are correct

### Issue: Token Tracking Not Working
**Solution**:
- Verify ai_service.py has token tracking code
- Check session state initialization
- Ensure API responses include usage data

## Security Best Practices

1. **Never commit secrets to Git**
   - Add `.env` to `.gitignore`
   - Don't commit `.streamlit/secrets.toml`

2. **Use environment-specific keys**
   - Different keys for dev/production
   - Monitor usage regularly

3. **Set rate limits**
   - Configure in secrets
   - Monitor API usage

## Requirements File

Ensure `requirements.txt` includes:
```
streamlit
pandas
numpy
anthropic
openai
python-dotenv
openpyxl
```

## Testing Deployment

1. **Upload Test File**: Use a small Excel file first
2. **Check Token Display**: Verify costs show correctly
3. **Test Fallback**: If Claude fails, should switch to OpenAI
4. **Download Results**: Ensure cleaned data downloads

## Monitoring & Logs

- Check Streamlit Cloud logs for errors
- Monitor token usage in sidebar
- Review LLM activity logs
- Track costs per file processed

## Support

For issues:
1. Check Streamlit Cloud logs
2. Verify API keys are valid
3. Test locally first
4. Review this guide

## Cost Optimization

- Process smaller files when possible
- Use quality threshold of 50% (default)
- Limit to 2 iterations (default)
- Reset tokens between sessions if needed