# Deployment Instructions for Streamlit Cloud

## Prerequisites
1. A Streamlit Cloud account (https://streamlit.io/cloud)
2. At least one API key: Anthropic Claude or OpenAI GPT
3. Your code pushed to a GitHub repository

## Setting up API Keys in Streamlit Cloud

### Step 1: Deploy Your App
1. Go to https://streamlit.io/cloud
2. Click "New app"
3. Connect your GitHub repository
4. Select the branch and file: `streamlit_demo_deploy.py`
5. Click "Deploy"

### Step 2: Add Secrets
1. Once deployed, go to your app's settings (⚙️ icon)
2. Navigate to "Secrets" section
3. Add your API keys in this format:

```toml
# Primary AI Service - Anthropic Claude
ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-ACTUAL-KEY-HERE"

# Fallback AI Service - OpenAI GPT  
OPENAI_API_KEY = "sk-YOUR-OPENAI-KEY-HERE"
```

4. Click "Save"
5. Your app will automatically restart with the new secrets

## How the Fallback System Works

The app automatically handles API failures with this priority:
1. **Anthropic Claude** (primary) - Used first if available
2. **OpenAI GPT** (fallback) - Used if Anthropic fails or has insufficient credits
3. **Error handling** - Clear messages if both services fail

### Automatic Fallback Scenarios:
- Anthropic API has insufficient credits → Switches to OpenAI
- Anthropic API is down → Switches to OpenAI
- OpenAI also fails → Shows error message to user

## Local Development

For local testing, create `.streamlit/secrets.toml`:

```bash
mkdir .streamlit
cp secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your actual API keys
```

## Files for Deployment

- `streamlit_demo_deploy.py` - Main application file for Streamlit Cloud
- `streamlit_demo_local.py` - Local version (uses .env file)
- `requirements.txt` - Python dependencies
- `config.py` - Configuration module (handles both secrets and env vars)
- `format_validators.py` - Format validation utilities
- `aws_s3_service.py` - AWS S3 integration (optional)

## API Key Management

### Getting API Keys:
1. **Anthropic Claude**: https://console.anthropic.com/
   - Sign up/Login
   - Go to API Keys section
   - Create new key
   - Add credits/subscription

2. **OpenAI GPT**: https://platform.openai.com/
   - Sign up/Login
   - Go to API Keys section
   - Create new key
   - Add credits to your account

### Best Practices:
- Never commit API keys to GitHub
- Use different keys for development and production
- Monitor usage to avoid unexpected charges
- Set up billing alerts on both platforms

## Troubleshooting

### "Credit balance too low" error:
- Add credits to your Anthropic account
- App will automatically use OpenAI if configured

### Both APIs failing:
- Check if API keys are correctly added in Streamlit secrets
- Verify keys are active and have credits
- Check API service status pages

### App not updating after adding secrets:
- Manually reboot the app from Streamlit Cloud dashboard
- Check logs for any error messages

## Features Available in Both Versions

✅ AI-powered header detection
✅ Automatic format standardization  
✅ Multi-sheet support
✅ Data quality analysis
✅ Smart column naming
✅ Conservative data cleaning
✅ Format validation
✅ User query application

## Support

For issues or questions:
- Check the logs in Streamlit Cloud dashboard
- Ensure API keys are valid and have credits
- Test locally first with `.streamlit/secrets.toml`