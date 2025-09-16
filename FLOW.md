# Excel Data Cleaner - Complete Application Flow Documentation

## 🎯 Overview
`new_streamlit_local.py` is the main entry point for the Excel Data Cleaner application. It orchestrates a multi-stage LLM pipeline for cleaning Excel data using AI.

## 📁 File Dependencies & Architecture

```
new_streamlit_local.py (Main Application)
│
├── Configuration & Setup
│   ├── config.py                 # API key management
│   └── .env                      # Environment variables (local)
│
├── Core AI Service Layer
│   └── ai_service.py             # Unified AI service with token tracking
│       ├── AIService class       # Manages Anthropic/OpenAI calls
│       ├── Token tracking        # Monitors usage & costs
│       └── Automatic fallback    # Switches between providers
│
├── Data Processing Modules
│   ├── header_detection.py       # AI-powered header detection
│   │   └── AIHeaderDetector      # Identifies & fixes headers
│   │
│   ├── cleaning_llm.py          # Cleaning analysis & suggestions
│   │   └── CleaningLLM          # Generates cleaning recommendations
│   │
│   ├── code_generator.py        # Code generation for cleaning
│   │   └── CodeGeneratorLLM     # Creates executable Python code
│   │
│   └── data_quality_scorer.py   # Quality assessment
│       ├── calculate_quality_score()
│       └── get_quality_report()
│
└── Validation & Formatting
    └── format_validators.py      # Format validation
        └── UniversalFormatValidator
```

## 🔄 Complete Application Flow

### Phase 1: Initialization & Setup

```mermaid
Start
  │
  ├─> Load environment variables (.env)
  ├─> Initialize logging
  ├─> Import all modules with fallbacks
  ├─> Set Streamlit page config
  ├─> Apply custom CSS
  └─> Initialize session state variables
```

**Session State Variables:**
- `uploaded_files_dict` - Stores multiple Excel files
- `selected_file` - Currently selected file
- `selected_sheet` - Currently selected sheet
- `current_df` - Current working dataframe
- `original_df` - Original uploaded dataframe
- `metadata` - Dataset metadata
- `cleaning_suggestions` - LLM-generated suggestions
- `quality_score` - Current quality score
- `quality_report` - Detailed quality report
- `cleaning_history` - History of cleaning operations
- `llm_logs` - LLM activity logs
- `token_usage` - Token tracking (input, output, cost)

### Phase 2: File Upload & Processing (Tab 1)

```
User uploads Excel file(s)
  │
  ├─> Store files in session_state.uploaded_files_dict
  ├─> Extract sheet names using pd.ExcelFile()
  └─> Display file/sheet selector UI
      │
      └─> User selects file & sheet
          │
          ├─> Load selected sheet (pd.read_excel)
          ├─> Store original_df
          │
          ├─> AI-Enhanced Header Processing
          │   ├─> header_detection.AIHeaderDetector()
          │   ├─> Makes AI call via ai_service.make_ai_call()
          │   ├─> Detects header row
          │   ├─> Removes empty rows/columns
          │   ├─> Suggests better headers
          │   └─> Returns: processed_df, changes, ai_suggestions
          │
          ├─> Initial Quality Assessment
          │   ├─> data_quality_scorer.calculate_quality_score()
          │   ├─> data_quality_scorer.get_quality_report()
          │   └─> Display initial quality metrics
          │
          ├─> Format Validation
          │   ├─> format_validators.UniversalFormatValidator()
          │   ├─> Validates data formats
          │   └─> Highlights violations
          │
          └─> Generate Metadata
              ├─> generate_metadata()
              ├─> Identifies data types
              ├─> Finds missing values
              └─> Detects quality indicators
```

### Phase 3: Multi-LLM Cleaning Pipeline (Tab 2)

```
User clicks "Run Multi-LLM Cleaning Pipeline"
  │
  └─> run_cleaning_pipeline() [Max 2 iterations, Quality threshold: 50%]
      │
      ├─> ITERATION LOOP (max 2 times)
      │   │
      │   ├─> Step 1: AI Cleaning Analysis (LLM1)
      │   │   ├─> cleaning_llm.CleaningLLM()
      │   │   ├─> analyze_and_suggest(df, metadata)
      │   │   ├─> Makes AI call for analysis
      │   │   ├─> Generates cleaning suggestions
      │   │   ├─> Tracks tokens & cost
      │   │   └─> Returns: suggestions list
      │   │
      │   ├─> Step 2: Code Generation & Execution (LLM2/3)
      │   │   ├─> code_generator.CodeGeneratorLLM()
      │   │   ├─> For each suggestion (max 5):
      │   │   │   ├─> generate_code(df, task, context)
      │   │   │   ├─> Makes AI call for code generation
      │   │   │   ├─> Retry logic (3 attempts)
      │   │   │   ├─> Tracks tokens & cost
      │   │   │   └─> Returns: Python code string
      │   │   │
      │   │   └─> Execute generated code
      │   │       ├─> Create safe exec environment
      │   │       ├─> Run code with exec()
      │   │       └─> Update dataframe
      │   │
      │   ├─> Step 3: Quality Assessment (LLM4)
      │   │   ├─> data_quality_scorer.get_quality_report()
      │   │   ├─> Calculate new quality score
      │   │   ├─> Tracks tokens & cost
      │   │   └─> Display quality metrics
      │   │
      │   └─> Check Quality Threshold
      │       ├─> If score >= 50%: Complete
      │       └─> If score < 50% & iterations < 2: Continue loop
      │
      └─> Update session state with final results
```

### Phase 4: Results Review (Tab 3)

```
Display Results
  │
  ├─> Show final quality score
  ├─> Display cleaned data preview
  ├─> Show metadata
  └─> List applied cleaning operations
```

### Phase 5: Download (Tab 4)

```
Download Options
  │
  ├─> Display total token usage & cost
  │   ├─> Total input tokens
  │   ├─> Total output tokens
  │   └─> Total cost in USD
  │
  ├─> Excel download (.xlsx)
  └─> CSV download (.csv)
```

## 🔌 AI Service Integration Flow

```
Any LLM Module makes a call
  │
  └─> ai_service.make_ai_call(prompt, max_tokens, system_prompt)
      │
      └─> AIService.call()
          │
          ├─> Try Anthropic (Claude)
          │   ├─> _call_anthropic()
          │   ├─> Track input/output tokens
          │   ├─> Calculate cost ($3/$15 per million)
          │   └─> Return response + token counts
          │
          ├─> If fails: Try OpenAI (GPT-4)
          │   ├─> _call_openai()
          │   ├─> Track input/output tokens
          │   ├─> Calculate cost ($30/$60 per million)
          │   └─> Return response + token counts
          │
          └─> Update total token usage & cost
```

## 📊 Token Tracking Flow

```
Every AI Call
  │
  ├─> Before: Get current token usage
  ├─> Make API call
  ├─> After: Get new token usage
  ├─> Calculate difference
  ├─> Update session state
  └─> Display in UI
      ├─> Sidebar (running total)
      ├─> Activity logs (per operation)
      └─> Final summary (download tab)
```

## 🎨 UI Components & Display Flow

### Sidebar
- Configuration status
- API key validation
- Token usage & cost (live)
- Cleaning history
- LLM activity logs

### Main Area (4 Tabs)
1. **Upload & Process** - File selection, initial processing
2. **Clean** - Run cleaning pipeline
3. **Results** - Review cleaned data
4. **Download** - Export & cost summary

### Footer
- App info
- Reset token counter button

## 📝 Key Functions & Their Roles

### Core Functions in new_streamlit_local.py

1. **init_session_state()**
   - Initializes all session variables
   - Maintains state across reruns

2. **detect_and_process_headers(df)**
   - Calls: `header_detection.AIHeaderDetector()`
   - Returns: processed_df, changes, ai_suggestions

3. **generate_metadata(df)**
   - Analyzes dataframe structure
   - Identifies quality indicators

4. **run_cleaning_pipeline(df, metadata)**
   - Orchestrates multi-LLM cleaning
   - Manages iteration loop
   - Tracks quality improvements

5. **log_llm_activity(activity, llm_name)**
   - Records LLM operations
   - Updates token tracking

6. **display_quality_score(score, report)**
   - Shows quality metrics
   - Displays token usage

## 🔧 Configuration Files

### .env (Local Configuration)
```
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # Optional fallback
```

### requirements.txt
- streamlit
- pandas
- numpy
- anthropic
- openai
- python-dotenv
- openpyxl

## 🚀 Execution Flow Summary

1. **Start**: User runs `streamlit run new_streamlit_local.py`
2. **Initialize**: Load configs, setup UI
3. **Upload**: User uploads Excel file(s)
4. **Select**: Choose file and sheet
5. **Process**: AI header detection, initial cleaning
6. **Clean**: Run multi-LLM pipeline (2 iterations max)
7. **Review**: Check results and quality
8. **Download**: Export cleaned data
9. **Monitor**: Track tokens & cost throughout

## 💡 Key Features

- **Multi-file support**: Handle multiple Excel files
- **Multi-sheet support**: Process individual sheets
- **AI-powered cleaning**: 4 different LLMs working together
- **Automatic retries**: Code generation with 3 attempts
- **Quality-driven**: Iterates until quality threshold met
- **Cost tracking**: Real-time token usage & pricing
- **Fallback support**: Automatic switch from Claude to GPT-4
- **Safe execution**: Sandboxed code execution environment

## 🔍 Error Handling

- Module import fallbacks
- API failure handling
- Code execution safety
- Token tracking resilience
- Session state persistence

## 📈 Performance Considerations

- Max 2 cleaning iterations (hardcoded)
- Quality threshold: 50% (hardcoded)
- Top 5 suggestions per iteration
- 3 retry attempts for code generation
- Token usage reset option

This flow ensures efficient, tracked, and cost-effective Excel data cleaning using multiple AI models working in concert.