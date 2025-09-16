# Token Tracking & Cost Calculation Guide

## Overview
The Excel Data Cleaner now includes comprehensive token tracking and cost calculation for all LLM API calls. This helps you monitor usage and costs in real-time.

## Pricing Information

### Claude (Anthropic) Pricing
- **Input tokens:** $3 per million tokens
- **Output tokens:** $15 per million tokens

### OpenAI GPT-4 Pricing (approximate)
- **Input tokens:** $30 per million tokens  
- **Output tokens:** $60 per million tokens

## Token Tracking Features

### 1. Real-Time Token Display
Token usage is displayed in multiple locations:

#### Sidebar
- Shows cumulative token counts
- Displays total cost for the session
- Updates after each LLM call

#### Quality Score Display
- Shows tokens used per operation
- Displays cost per cleaning iteration

#### Download Tab
- Shows final token usage summary
- Displays total cost for processing the entire Excel file

### 2. Token Tracking in LLM Logs
Each LLM activity log entry now includes:
- Number of tokens used
- Cost incurred for that specific call
- Example: `"Analyzed data (Tokens: 1,234, Cost: $0.0185)"`

### 3. Cost Breakdown Per Operation

The app tracks tokens for each major operation:

1. **Header Detection** (`header_detection.py`)
   - AI-powered header analysis
   - Tracks tokens for header suggestions

2. **Cleaning Analysis** (`cleaning_llm.py`)
   - Data quality assessment
   - Cleaning suggestions generation
   - Tracks tokens for each analysis

3. **Code Generation** (`code_generator.py`)
   - Generates Python code for cleaning operations
   - Tracks tokens for code generation and retries

4. **Quality Scoring** (`data_quality_scorer.py`)
   - Evaluates data quality
   - Tracks tokens for quality assessment

## Implementation Details

### AIService Class Updates
The `ai_service.py` module now includes:

```python
class AIService:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.anthropic_input_cost = 3.0  # $3/million
        self.anthropic_output_cost = 15.0  # $15/million
    
    def get_token_usage(self):
        """Returns current token usage and cost"""
        return {
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'total_cost': self.total_cost
        }
    
    def reset_token_usage(self):
        """Resets token counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
```

### Session State Tracking
The Streamlit app maintains token usage in session state:
```python
st.session_state.token_usage = {
    'input_tokens': 0,
    'output_tokens': 0,
    'total_cost': 0.0
}
```

## Usage Examples

### Example 1: Processing a Small Excel File
- **Input tokens:** ~5,000
- **Output tokens:** ~2,000
- **Estimated cost:** $0.045

### Example 2: Processing a Large Excel File with 2 Iterations
- **Input tokens:** ~20,000
- **Output tokens:** ~8,000
- **Estimated cost:** $0.18

### Example 3: Complex Data with Multiple Retries
- **Input tokens:** ~50,000
- **Output tokens:** ~20,000
- **Estimated cost:** $0.45

## Cost Optimization Tips

1. **Use Quality Threshold Wisely**
   - Higher threshold = more iterations = higher cost
   - Default is set to 50% for balance

2. **Limit Max Iterations**
   - Currently hardcoded to 2 iterations
   - Prevents runaway costs

3. **Monitor Token Usage**
   - Check sidebar for running total
   - Reset counter between files if needed

4. **Batch Processing**
   - Process multiple sheets together
   - Reduces overhead of repeated analysis

## Testing Token Tracking

Run the test script to verify token tracking:
```bash
python test_token_tracking.py
```

This will:
1. Make a test API call
2. Display tokens used
3. Calculate and show cost
4. Demonstrate reset functionality

## Troubleshooting

### Tokens Not Showing
- Ensure API key is configured
- Check that AI service is initialized
- Verify make_ai_call() is being used

### Incorrect Cost Calculation
- Check pricing constants in ai_service.py
- Verify token counts from API response
- Ensure proper provider detection

### Reset Not Working
- Use the "Reset Token Counter" button in footer
- Manually call `service.reset_token_usage()`
- Clear session state if needed

## Files Modified for Token Tracking

1. **ai_service.py** - Core token tracking implementation
2. **new_streamlit_local.py** - UI display and session management
3. All LLM modules automatically tracked through `make_ai_call()`

## Future Enhancements

Potential improvements:
- Token usage history graph
- Cost per sheet breakdown
- Token usage export to CSV
- Budget alerts and limits
- Provider-specific cost comparison