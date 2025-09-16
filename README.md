# Excel Data Cleaner - Local Development Version

This folder contains the local development version of the Excel Data Cleaner with Multi-LLM Pipeline.

## 📁 Files Structure

```
Main_path/
├── new_streamlit_local.py    # Main Streamlit application (local version with dotenv)
├── cleaning_llm.py           # LLM for cleaning analysis and suggestions
├── code_generator.py         # LLM for code generation with retry logic
├── data_quality_scorer.py    # Realistic data quality scoring system
├── header_detection.py       # AI-enhanced header detection
├── ai_service.py            # AI service abstraction (Claude/OpenAI)
├── config.py                # Configuration management
├── format_validators.py     # Universal format validation
├── .env                     # Environment variables (add your API keys here)
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
cd Main_path
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit the `.env` file and add your actual API keys:

```env
ANTHROPIC_API_KEY=your_actual_anthropic_key_here
OPENAI_API_KEY=your_actual_openai_key_here  # Optional
```

### 3. Run the Application

```bash
streamlit run new_streamlit_local.py
```

The application will open in your browser at `http://localhost:8501`

## 🎯 Features

### Multi-LLM Pipeline
1. **LLM1 - Cleaning Analyzer**: Analyzes data and suggests cleaning operations across 8 categories
2. **LLM2/3 - Code Generator**: Generates Python code with 3 retry attempts
3. **LLM4 - Quality Scorer**: Evaluates data quality with realistic scoring (0-100%)

### AI Header Detection
- Checks if existing headers are good
- Removes empty rows/columns
- Uses AI to validate headers against data
- Provides suggestions for better headers

### Hardcoded Values
- **Max Iterations**: 2 (re-cleans automatically if quality < 50%)
- **Quality Threshold**: 50%

### Universal Format Validation
- Indian date format (DD/MM/YYYY)
- PAN cards, GST numbers
- Phone numbers, emails
- Red cell highlighting for violations

### Multi-File & Multi-Sheet Support
- Upload multiple Excel files
- Select specific sheets from each file
- Process one sheet at a time

## 📊 Data Processing Flow

1. **Upload**: Select Excel file and sheet
2. **Header Detection**: AI validates and suggests headers
3. **Basic Cleaning**: Remove empty rows/columns
4. **Advanced Cleaning**: Multi-LLM pipeline with auto re-cleaning
5. **Quality Check**: Score must reach 50% or 2 iterations max
6. **Download**: Export cleaned data as Excel or CSV

## 🔒 Zero Tolerance Data Preservation

The system follows strict rules:
- **NEVER** removes data rows (except 100% empty)
- **NEVER** removes columns (except 100% empty)
- **NEVER** drops duplicates without permission
- Only modifies values, formats, and headers

## 🛠️ Troubleshooting

### API Key Issues
- Ensure `.env` file is in the Main_path directory
- Check that API keys are valid and have sufficient credits
- The app will fall back to OpenAI if Claude fails

### Memory Issues
- For large files (>100MB), consider processing in chunks
- Close other applications to free memory

### Quality Score Too Low
- The realistic scorer is more forgiving than the original
- Scores above 25% indicate usable data
- Even "poor" quality data can be processed

## 📝 Notes

- This is the LOCAL version using `.env` file for configuration
- For deployment, use the main `new_streamlit_demo.py` with Streamlit secrets
- All LLM operations are logged in the sidebar for transparency