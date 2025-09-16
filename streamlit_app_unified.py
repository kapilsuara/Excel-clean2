#!/usr/bin/env python3
"""
Unified Excel Data Cleaner with AI Chatbot Integration
Features:
- Multi-stage LLM cleaning pipeline
- AI Chatbot for Excel queries and transformations
- Comprehensive metadata generation
- Code generation with retry logic
- Data quality scoring
- Automatic re-cleaning if quality is low
- Real-time token tracking and cost calculation
- Natural language Excel operations

Configuration:
- For deployment: Uses Streamlit secrets (st.secrets)
- For local dev: Falls back to .env file
- API keys priority: Streamlit secrets > Environment variables
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import re
import time
import traceback
import logging
from datetime import datetime
from pathlib import Path
import tempfile
from typing import Dict, List, Any, Tuple, Optional
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import custom modules
from ai_service import make_ai_call, get_ai_service
from config import get_anthropic_api_key
from header_detection import AIHeaderDetector

# Import data quality scorer with fallback
try:
    from data_quality_scorer import calculate_quality_score, get_quality_report
except ImportError as e:
    print(f"Warning: Could not import from data_quality_scorer: {e}")
    # Fallback implementation
    def calculate_quality_score(df):
        missing_pct = (df.isnull().sum().sum() / df.size) * 100 if df.size > 0 else 0
        score = max(0, 100 - missing_pct)
        return score
    
    def get_quality_report(df):
        score = calculate_quality_score(df)
        return {
            'score': score,
            'quality_level': 'HIGH' if score > 70 else 'MEDIUM' if score > 40 else 'LOW',
            'issues': [],
            'suggestions': [],
            'stats': {},
            'recommendation': f"Quality score: {score}%",
            'detailed_scores': {}
        }

# Import validators with fallback
try:
    from format_validators import UniversalFormatValidator, highlight_format_violations
except ImportError:
    print("Warning: Format validators not available")
    class UniversalFormatValidator:
        def validate_dataframe(self, df):
            return pd.DataFrame(), {}
    def highlight_format_violations(df, violations):
        return df

# Import LLM modules with fallback
try:
    from cleaning_llm import CleaningLLM
except ImportError:
    print("Warning: CleaningLLM not available")
    class CleaningLLM:
        def analyze_and_suggest(self, df, metadata):
            return []

try:
    from code_generator_llm import CodeGeneratorLLM
except ImportError:
    print("Warning: CodeGeneratorLLM not available")
    class CodeGeneratorLLM:
        def generate_code(self, df, task, context=None):
            return "# Code generation not available"

# Set page config
st.set_page_config(
    page_title="Excel Data Cleaner with AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 1.5rem 0 1rem;
        border-bottom: 2px solid #667eea;
        padding-bottom: 0.5rem;
    }
    .quality-score {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .quality-high {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .quality-medium {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    .quality-low {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        color: white;
    }
    .metadata-box {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: black;
    }
    .user-message {
        background-color: #f0f8ff;
        text-align: left;
        color: black;
    }
    .bot-message {
        background-color: #f5f5f5;
        text-align: left;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'uploaded_files_dict' not in st.session_state:
        st.session_state.uploaded_files_dict = {}
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = None
    if 'selected_sheet' not in st.session_state:
        st.session_state.selected_sheet = None
    if 'available_sheets' not in st.session_state:
        st.session_state.available_sheets = []
    if 'uploaded_file_content' not in st.session_state:
        st.session_state.uploaded_file_content = None
    if 'current_df' not in st.session_state:
        st.session_state.current_df = None
    if 'original_df' not in st.session_state:
        st.session_state.original_df = None
    if 'metadata' not in st.session_state:
        st.session_state.metadata = None
    if 'cleaning_suggestions' not in st.session_state:
        st.session_state.cleaning_suggestions = []
    if 'quality_score' not in st.session_state:
        st.session_state.quality_score = 0
    if 'quality_report' not in st.session_state:
        st.session_state.quality_report = {}
    if 'cleaning_iteration' not in st.session_state:
        st.session_state.cleaning_iteration = 0
    if 'cleaning_history' not in st.session_state:
        st.session_state.cleaning_history = []
    if 'llm_logs' not in st.session_state:
        st.session_state.llm_logs = []
    if 'ai_header_suggestions' not in st.session_state:
        st.session_state.ai_header_suggestions = {"has_suggestions": False, "suggested_headers": [], "confidence": 0, "reasoning": ""}
    if 'token_usage' not in st.session_state:
        st.session_state.token_usage = {'input_tokens': 0, 'output_tokens': 0, 'total_cost': 0.0}
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'chat_mode' not in st.session_state:
        st.session_state.chat_mode = False

init_session_state()

def process_chat_query(query: str, df: pd.DataFrame = None) -> Tuple[str, pd.DataFrame]:
    """
    Process natural language queries about Excel data
    Returns response text and optionally modified dataframe
    """
    ai_service = get_ai_service()
    
    # Track tokens before
    tokens_before = ai_service.get_token_usage()
    
    # Prepare context
    context = ""
    if df is not None:
        context = f"""
        Current Excel Data Context:
        - Shape: {df.shape[0]} rows, {df.shape[1]} columns
        - Columns: {', '.join(df.columns.tolist()[:10])}{'...' if len(df.columns) > 10 else ''}
        - Data types: {df.dtypes.value_counts().to_dict()}
        - Missing values: {df.isnull().sum().sum()}
        - First 3 rows sample: {df.head(3).to_string()}
        """
    
    # Create prompt for Excel operations
    system_prompt = """You are an AI assistant specialized in Excel data operations.
    When users ask about data operations, provide very brief, simple confirmations only.
    Do NOT provide explanations, technical details, or descriptions of what will happen.
    Just acknowledge the request briefly and provide executable Python code.
    Keep responses to 1-2 sentences maximum.
    
    For queries that modify data, generate executable Python code using pandas.
    Always return the modified dataframe as 'df'.
    """
    
    prompt = f"""
    User Query: {query}
    
    {context}
    
    Please help with this Excel data query. If this requires modifying the data, 
    provide Python code that can be executed to perform the operation.
    Format code blocks with ```python and ```.
    """
    
    response = make_ai_call(prompt, max_tokens=1500, system_prompt=system_prompt)
    
    # Track tokens after
    tokens_after = ai_service.get_token_usage()
    tokens_used = tokens_after['total_tokens'] - tokens_before['total_tokens']
    cost_incurred = tokens_after['total_cost'] - tokens_before['total_cost']
    
    # Update session state
    st.session_state.token_usage = {
        'input_tokens': tokens_after['input_tokens'],
        'output_tokens': tokens_after['output_tokens'],
        'total_cost': tokens_after['total_cost']
    }
    
    # Log activity
    log_llm_activity(f"Chat query processed (Tokens: {tokens_used:,}, Cost: ${cost_incurred:.4f})", "ChatBot", True)
    
    # Try to extract and execute code if present
    modified_df = df
    if response and df is not None:
        code_blocks = re.findall(r'```python\n(.*?)\n```', response, re.DOTALL)
        if code_blocks:
            for code in code_blocks:
                try:
                    # Create safe execution environment
                    exec_globals = {'df': df.copy(), 'pd': pd, 'np': np, 're': re}
                    exec(code, exec_globals)
                    if 'df' in exec_globals:
                        modified_df = exec_globals['df']
                        st.success("✅ Operation executed successfully!")
                except Exception as e:
                    st.error(f"Failed to execute operation: {str(e)}")
            
            # Remove code blocks and technical explanations from response to keep it clean
            response = re.sub(r'```python\n.*?\n```', '', response, flags=re.DOTALL)
            # Remove common technical explanation patterns
            response = re.sub(r'This will.*?(?=\.|$)', '', response, flags=re.DOTALL)
            response = re.sub(r'Here\'s.*?(?=\.|$)', '', response, flags=re.DOTALL)
            response = re.sub(r'The dataframe.*?(?=\.|$)', '', response, flags=re.DOTALL)
            response = response.strip()
            
            # If response is mostly empty after cleaning, provide simple confirmation
            if not response or len(response.strip()) < 10:
                response = "Done! Operation completed successfully."
    
    return response, modified_df

def detect_and_process_headers(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], Dict[str, Any]]:
    """
    AI-enhanced processing: Check existing headers, remove empty rows/columns, validate with AI
    """
    changes = []
    ai_suggestions = {"has_suggestions": False, "suggested_headers": [], "confidence": 0, "reasoning": ""}
    
    try:
        header_detector = AIHeaderDetector()
        header_row_index, processed_df, detection_log, ai_suggestions = header_detector.detect_header_row(df)
        changes.extend(detection_log)
        return processed_df, changes, ai_suggestions
    except Exception as e:
        changes.append(f"⚠️ Processing failed: {str(e)[:100]}")
        changes.append("Using original data as-is")
        return df, changes, ai_suggestions

def generate_metadata(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate comprehensive metadata for the dataframe"""
    metadata = {
        'shape': df.shape,
        'columns': list(df.columns),
        'dtypes': df.dtypes.to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'memory_usage': df.memory_usage(deep=True).sum() / 1024**2,  # MB
        'duplicate_rows': df.duplicated().sum(),
        'quality_indicators': {
            'potentially_datetime': [],
            'potentially_numeric_text': [],
            'high_missing_columns': []
        }
    }
    
    # Identify potential datetime columns
    for col in df.select_dtypes(include=['object']).columns:
        sample = df[col].dropna().head(20)
        if len(sample) > 0:
            try:
                pd.to_datetime(sample, errors='raise')
                metadata['quality_indicators']['potentially_datetime'].append(col)
            except:
                pass
    
    # Identify numeric text columns
    for col in df.select_dtypes(include=['object']).columns:
        if col not in metadata['quality_indicators']['potentially_datetime']:
            sample = df[col].dropna().head(20)
            if len(sample) > 0:
                try:
                    pd.to_numeric(sample, errors='raise')
                    metadata['quality_indicators']['potentially_numeric_text'].append(col)
                except:
                    pass
    
    # Identify columns with high missing values
    missing_threshold = 0.5
    for col in df.columns:
        if df[col].isnull().sum() / len(df) > missing_threshold:
            metadata['quality_indicators']['high_missing_columns'].append(col)
    
    return metadata

def display_metadata(metadata: Dict[str, Any]):
    """Display metadata in a formatted way"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📊 Dataset Overview")
        st.write(f"**Shape:** {metadata['shape'][0]} rows × {metadata['shape'][1]} columns")
        st.write(f"**Memory:** {metadata['memory_usage']:.2f} MB")
        st.write(f"**Duplicates:** {metadata['duplicate_rows']} rows")
    
    with col2:
        st.markdown("### ⚠️ Quality Indicators")
        indicators = metadata['quality_indicators']
        if indicators['potentially_datetime']:
            st.write(f"**Date columns:** {len(indicators['potentially_datetime'])}")
        if indicators['potentially_numeric_text']:
            st.write(f"**Numeric text:** {len(indicators['potentially_numeric_text'])}")
        if indicators['high_missing_columns']:
            st.write(f"**High missing:** {len(indicators['high_missing_columns'])}")
    
    with col3:
        st.markdown("### 🔍 Data Types")
        dtype_counts = pd.Series([str(dt) for dt in metadata['dtypes'].values()]).value_counts()
        for dtype, count in dtype_counts.items():
            st.write(f"**{dtype}:** {count} columns")

def display_quality_score(score: int, report: Dict[str, Any]):
    """Display quality score with visual styling"""
    if score >= 70:
        quality_class = "quality-high"
        emoji = "🟢"
    elif score >= 40:
        quality_class = "quality-medium"
        emoji = "🟡"
    else:
        quality_class = "quality-low"
        emoji = "🔴"
    
    st.markdown(f"""
    <div class="{quality_class} quality-score">
        {emoji} Data Quality Score: {score}%
    </div>
    """, unsafe_allow_html=True)
    
    if report.get('issues'):
        st.warning("**Issues Found:**")
        for issue in report['issues']:
            st.write(f"• {issue}")
    
    if report.get('suggestions'):
        st.info("**Suggestions:**")
        for suggestion in report['suggestions']:
            st.write(f"• {suggestion}")

def log_llm_activity(activity: str, llm_name: str, success: bool = True):
    """Log LLM activity for transparency with token tracking"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status = "✅" if success else "❌"
    
    # Get token usage from AI service
    ai_service = get_ai_service()
    token_stats = ai_service.get_token_usage()
    
    # Update session state token usage
    st.session_state.token_usage = {
        'input_tokens': token_stats['input_tokens'],
        'output_tokens': token_stats['output_tokens'],
        'total_cost': token_stats['total_cost']
    }
    
    log_entry = f"[{timestamp}] {status} **{llm_name}**: {activity}"
    st.session_state.llm_logs.append(log_entry)

def run_cleaning_pipeline(df: pd.DataFrame, metadata: Dict[str, Any], 
                         max_iterations: int = 2, quality_threshold: int = 50) -> pd.DataFrame:
    """
    Run the multi-LLM cleaning pipeline
    """
    df_cleaned = df.copy()
    iteration = 0
    
    with st.spinner("🤖 Running Multi-LLM Cleaning Pipeline..."):
        while iteration < max_iterations:
            iteration += 1
            st.session_state.cleaning_iteration = iteration
            
            progress_text = f"Iteration {iteration}/{max_iterations}"
            progress_bar = st.progress(iteration / max_iterations, text=progress_text)
            
            st.write(f"### 🔄 Cleaning Iteration {iteration}")
            
            # LLM1: Cleaning Analysis
            st.write("**Step 1: AI Cleaning Analysis**")
            cleaning_llm = CleaningLLM()
            
            # Track tokens before call
            ai_service = get_ai_service()
            tokens_before = ai_service.get_token_usage()
            
            suggestions = cleaning_llm.analyze_and_suggest(df_cleaned, metadata)
            
            # Track tokens after call
            tokens_after = ai_service.get_token_usage()
            tokens_used = tokens_after['total_tokens'] - tokens_before['total_tokens']
            cost_incurred = tokens_after['total_cost'] - tokens_before['total_cost']
            
            log_llm_activity(f"Analyzed data and generated {len(suggestions)} suggestions (Tokens: {tokens_used:,}, Cost: ${cost_incurred:.4f})", "LLM1-CleaningAnalyzer", True)
            
            if not suggestions:
                st.info("No cleaning suggestions generated. Data appears clean.")
                break
            
            st.session_state.cleaning_suggestions = suggestions
            
            # Display suggestions
            with st.expander(f"📋 View {len(suggestions)} Cleaning Suggestions"):
                for idx, suggestion in enumerate(suggestions, 1):
                    st.write(f"**{idx}. {suggestion.get('category', 'general').title()}**")
                    st.write(f"   - {suggestion.get('description', 'No description')}")
                    st.write(f"   - Priority: {suggestion.get('priority', 'medium')}")
            
            # LLM2/3: Code Generation
            st.write("**Step 2: Code Generation & Execution**")
            code_generator = CodeGeneratorLLM()
            
            applied_changes = []
            for suggestion in suggestions[:5]:  # Limit to top 5
                if suggestion.get('requires_code', False):
                    task = suggestion.get('action', suggestion.get('description', ''))
                    
                    # Generate code with retries
                    code = None
                    for retry in range(3):
                        try:
                            tokens_before = ai_service.get_token_usage()
                            
                            code = code_generator.generate_code(df_cleaned, task, context=suggestion)
                            
                            tokens_after = ai_service.get_token_usage()
                            tokens_used = tokens_after['total_tokens'] - tokens_before['total_tokens']
                            cost_incurred = tokens_after['total_cost'] - tokens_before['total_cost']
                            
                            if code and code != "# Code generation not available":
                                log_llm_activity(f"Generated code for: {task[:50]}... (Tokens: {tokens_used:,}, Cost: ${cost_incurred:.4f})", f"LLM2-Attempt{retry+1}", True)
                                break
                        except Exception as e:
                            log_llm_activity(f"Code generation failed: {str(e)[:50]}", f"LLM2-Attempt{retry+1}", False)
                    
                    # Execute code
                    if code and code != "# Code generation not available":
                        try:
                            exec_globals = {'df': df_cleaned.copy(), 'pd': pd, 'np': np, 're': re}
                            exec(code, exec_globals)
                            df_cleaned = exec_globals.get('df', df_cleaned)
                            applied_changes.append(task)
                            log_llm_activity(f"Executed: {task[:50]}...", "CodeExecutor", True)
                        except Exception as e:
                            st.warning(f"Failed to execute: {task[:50]}... Error: {str(e)[:100]}")
                            log_llm_activity(f"Execution failed: {str(e)[:50]}", "CodeExecutor", False)
            
            st.success(f"Applied {len(applied_changes)} cleaning operations")
            
            # LLM4: Quality Assessment
            st.write("**Step 3: Quality Assessment**")
            
            tokens_before = ai_service.get_token_usage()
            
            quality_report = get_quality_report(df_cleaned)
            quality_score = quality_report['score']
            st.session_state.quality_score = quality_score
            st.session_state.quality_report = quality_report
            
            tokens_after = ai_service.get_token_usage()
            tokens_used = tokens_after['total_tokens'] - tokens_before['total_tokens']
            cost_incurred = tokens_after['total_cost'] - tokens_before['total_cost']
            
            log_llm_activity(f"Quality score: {quality_score}% (Tokens: {tokens_used:,}, Cost: ${cost_incurred:.4f})", "LLM4-QualityScorer", True)
            
            display_quality_score(quality_score, quality_report)
            
            if quality_score >= quality_threshold:
                st.success(f"✅ Quality threshold ({quality_threshold}%) met! Cleaning complete.")
                break
            else:
                if iteration < max_iterations:
                    st.warning(f"Quality score {quality_score}% below threshold {quality_threshold}%. Running another iteration...")
                else:
                    st.warning(f"⚠️ Maximum iterations reached. Final quality: {quality_score}%")
            
            metadata = generate_metadata(df_cleaned)
            
            st.session_state.cleaning_history.append({
                'iteration': iteration,
                'quality_score': quality_score,
                'changes_applied': len(applied_changes),
                'shape': df_cleaned.shape
            })
    
    return df_cleaned

# Main App
st.markdown('<h1 class="main-header">🤖 Excel Data Cleaner with AI Assistant</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Check API key status (silently)
    api_key = get_anthropic_api_key()
    
    if not api_key:
        st.error("❌ API Key not found")
        st.info("""
        **For deployment:**
        Add ANTHROPIC_API_KEY to Streamlit secrets
        
        **For local development:**
        Add ANTHROPIC_API_KEY to .env file
        """)
    
    # Only show token usage and logs when AI chat is not active
    if not st.session_state.chat_mode:
        # Display token usage and cost
        if st.session_state.token_usage['total_cost'] > 0:
            st.markdown("### 💰 Token Usage & Cost")
            st.write(f"""
            **Input Tokens:** {st.session_state.token_usage['input_tokens']:,}
            **Output Tokens:** {st.session_state.token_usage['output_tokens']:,}
            **Total Cost:** ${st.session_state.token_usage['total_cost']:.4f}
            """)
            st.caption("""
            Claude Pricing:
            - Input: $3/million tokens
            - Output: $15/million tokens
            """)
        
        # Display cleaning history
        if st.session_state.cleaning_history:
            st.markdown("### 📊 Cleaning History")
            for entry in st.session_state.cleaning_history:
                st.write(f"**Iteration {entry['iteration']}**")
                st.write(f"• Quality: {entry['quality_score']}%")
                st.write(f"• Changes: {entry['changes_applied']}")
                st.write(f"• Shape: {entry['shape']}")
        
        # LLM Activity Log
        if st.session_state.llm_logs:
            st.markdown("### 🤖 LLM Activity Log")
            with st.expander("View Activity"):
                for log in reversed(st.session_state.llm_logs[-10:]):
                    st.markdown(log)
    
    # Chat mode toggle
    st.markdown("### 💬 AI Assistant")
    chat_enabled = st.checkbox("Enable AI Chat Assistant", value=st.session_state.chat_mode)
    st.session_state.chat_mode = chat_enabled

# Main content area with tabs
tabs = st.tabs(["📤 Upload & Process", "🧹 Clean", "💬 AI Chat", "📊 Results", "⬇️ Download"])

with tabs[0]:
    st.markdown("<div class='section-header'>Step 1: Upload and Process Excel File</div>", unsafe_allow_html=True)
    
    # File upload for multiple files
    uploaded_files = st.file_uploader(
        "Choose Excel files",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        help="Upload one or more Excel files. Each file can have multiple sheets."
    )
    
    if uploaded_files:
        # Store uploaded files in session state
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in st.session_state.uploaded_files_dict:
                try:
                    excel_file = pd.ExcelFile(uploaded_file)
                    sheet_names = excel_file.sheet_names
                    
                    st.session_state.uploaded_files_dict[uploaded_file.name] = {
                        'file': uploaded_file,
                        'sheets': sheet_names,
                        'content': uploaded_file.getvalue()
                    }
                    st.success(f"✅ Loaded {uploaded_file.name} with {len(sheet_names)} sheet(s)")
                except Exception as e:
                    st.error(f"Error loading {uploaded_file.name}: {str(e)}")
    
    # File and Sheet Selection UI
    if st.session_state.uploaded_files_dict:
        st.markdown("### 📁 Select File and Sheet")
        
        col1, col2 = st.columns(2)
        
        with col1:
            file_names = list(st.session_state.uploaded_files_dict.keys())
            selected_filename = st.selectbox(
                "Select a file to process:",
                file_names,
                key="file_selector"
            )
            
            if selected_filename:
                st.session_state.selected_file = selected_filename
                file_info = st.session_state.uploaded_files_dict[selected_filename]
                st.session_state.available_sheets = file_info['sheets']
        
        with col2:
            if st.session_state.available_sheets:
                selected_sheet = st.selectbox(
                    "Select a sheet:",
                    st.session_state.available_sheets,
                    key="sheet_selector"
                )
                st.session_state.selected_sheet = selected_sheet
        
        # Load button
        if st.session_state.selected_file and st.session_state.selected_sheet:
            if st.button("🚀 Load and Process Selected Sheet", type="primary"):
                try:
                    with st.spinner("Loading data..."):
                        file_info = st.session_state.uploaded_files_dict[st.session_state.selected_file]
                        file_content = BytesIO(file_info['content'])
                        
                        df = pd.read_excel(file_content, sheet_name=st.session_state.selected_sheet, header=None)
                        st.session_state.original_df = df.copy()
                        
                        # Initial quality assessment
                        with st.spinner("🔍 Assessing initial data quality..."):
                            try:
                                initial_quality_score = calculate_quality_score(df)
                                initial_quality_report = get_quality_report(df)
                                
                                st.markdown("### 📊 Initial Data Quality Assessment")
                                col1, col2 = st.columns([1, 2])
                                
                                with col1:
                                    if initial_quality_score >= 70:
                                        st.success(f"**Quality Score:** {initial_quality_score}%")
                                    elif initial_quality_score >= 40:
                                        st.warning(f"**Quality Score:** {initial_quality_score}%")
                                    else:
                                        st.error(f"**Quality Score:** {initial_quality_score}%")
                                
                                with col2:
                                    if 'detailed_scores' in initial_quality_report:
                                        scores = initial_quality_report['detailed_scores']
                                        for metric, score in scores.items():
                                            st.progress(score/100, text=f"{metric.replace('_', ' ').title()}: {score:.1f}%")
                                
                                st.session_state.initial_quality_score = initial_quality_score
                                st.session_state.initial_quality_report = initial_quality_report
                                
                            except Exception as e:
                                st.error(f"❌ Initial quality assessment failed: {str(e)}")
                                st.session_state.initial_quality_score = 0
                    
                    # AI-enhanced processing
                    ai_service = get_ai_service()
                    tokens_before = ai_service.get_token_usage()
                    
                    df_processed, processing_changes, ai_suggestions = detect_and_process_headers(df)
                    
                    tokens_after = ai_service.get_token_usage()
                    tokens_used = tokens_after['total_tokens'] - tokens_before['total_tokens']
                    cost_incurred = tokens_after['total_cost'] - tokens_before['total_cost']
                    
                    changes = processing_changes
                    st.session_state.current_df = df_processed
                    st.session_state.ai_header_suggestions = ai_suggestions
                    
                    st.success(f"✅ Sheet loaded successfully: {selected_sheet} from {selected_filename}")
                    
                    # Display basic info
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("File", selected_filename[:20] + "..." if len(selected_filename) > 20 else selected_filename)
                    with col2:
                        st.metric("Sheet", selected_sheet)
                    with col3:
                        st.metric("Original", f"{df.shape[0]}×{df.shape[1]}")
                    with col4:
                        st.metric("Cleaned", f"{df_processed.shape[0]}×{df_processed.shape[1]}")
                    
                    if changes:
                        st.write("**Basic Cleaning Applied:**")
                        for change in changes:
                            st.write(f"• {change}")
                    
                    # Show AI header suggestions if available
                    if ai_suggestions.get("has_suggestions", False):
                        st.subheader("🤖 AI Header Suggestions")
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.info(f"**AI Assessment:** {ai_suggestions.get('reasoning', 'No reasoning provided')}")
                            st.write(f"**Confidence:** {ai_suggestions.get('confidence', 0)}%")
                            
                            if ai_suggestions.get('improvements'):
                                st.write("**Suggested Improvements:**")
                                for improvement in ai_suggestions['improvements']:
                                    st.write(f"• {improvement}")
                        
                        with col2:
                            if st.button("🔄 Apply AI Suggestions", key="apply_ai_headers"):
                                try:
                                    from header_detection import AIHeaderDetector
                                    detector = AIHeaderDetector()
                                    df_with_new_headers = detector.apply_suggested_headers(
                                        df_processed, 
                                        ai_suggestions['suggested_headers']
                                    )
                                    st.session_state.current_df = df_with_new_headers
                                    st.success("✅ Applied AI-suggested headers!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to apply headers: {str(e)}")
                    
                    # Show preview
                    st.subheader("Data Preview (After Basic Cleaning)")
                    st.dataframe(df_processed.head(20), use_container_width=True, hide_index=True)
                    
                    # Generate and display metadata
                    with st.spinner("Generating metadata..."):
                        metadata = generate_metadata(df_processed)
                        st.session_state.metadata = metadata
                    
                    display_metadata(metadata)
                    
                    st.success("✅ Ready for advanced cleaning! Go to the Clean tab.")
                    
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")

with tabs[1]:
    st.markdown("<div class='section-header'>Step 2: Advanced Cleaning Pipeline</div>", unsafe_allow_html=True)
    
    if st.session_state.current_df is None:
        st.warning("⚠️ Please upload and load a file first")
    else:
        if st.session_state.selected_file:
            if st.session_state.selected_sheet:
                st.info(f"📄 **Currently cleaning:** {st.session_state.selected_file} → Sheet: {st.session_state.selected_sheet}")
            else:
                st.info(f"📄 **Currently cleaning:** {st.session_state.selected_file}")
        
        if st.session_state.quality_score > 0:
            display_quality_score(st.session_state.quality_score, st.session_state.quality_report)
        
        auto_clean = True
        max_iterations = 2
        quality_threshold = 50
        
        st.info(f"**Settings:** Max iterations: {max_iterations}, Quality threshold: {quality_threshold}%")
        
        if st.button("🚀 Run Multi-LLM Cleaning Pipeline", type="primary"):
            df_cleaned = run_cleaning_pipeline(
                st.session_state.current_df,
                st.session_state.metadata,
                max_iterations=max_iterations,
                quality_threshold=quality_threshold
            )
            
            st.session_state.current_df = df_cleaned
            st.session_state.metadata = generate_metadata(df_cleaned)
            
            st.markdown("### 📊 Before/After Comparison")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Before Cleaning**")
                st.write(f"Shape: {st.session_state.original_df.shape}")
                st.write(f"Quality: {st.session_state.initial_quality_score}%")
                
            with col2:
                st.markdown("**After Cleaning**")
                st.write(f"Shape: {df_cleaned.shape}")
                st.write(f"Quality: {st.session_state.quality_score}%")

with tabs[2]:
    st.markdown("<div class='section-header'>💬 AI Chat Assistant</div>", unsafe_allow_html=True)
    
    if not st.session_state.chat_mode:
        st.info("💡 Enable the AI Chat Assistant in the sidebar to interact with your Excel data using natural language!")
    else:
        if st.session_state.current_df is None:
            st.warning("⚠️ Please upload and load an Excel file first to use the chat assistant.")
        else:
            st.write("### 🤖 Ask me anything about your Excel data!")
            st.caption("Examples: 'Remove all empty rows', 'Convert text dates to datetime', 'Show me columns with missing values'")
            
            # Chat input
            user_query = st.text_input("Your question or command:", key="chat_input", placeholder="Type your Excel query here...")
            
            col1, col2 = st.columns([1, 5])
            with col1:
                send_button = st.button("📤 Send", type="primary")
            with col2:
                clear_chat = st.button("🗑️ Clear Chat")
            
            if clear_chat:
                st.session_state.chat_history = []
                st.rerun()
            
            if send_button and user_query:
                # Add user message to history
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                
                # Process query
                with st.spinner("🤔 Thinking..."):
                    response, modified_df = process_chat_query(user_query, st.session_state.current_df)
                
                # Add bot response to history
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                
                # Update dataframe if modified
                if modified_df is not None and not modified_df.equals(st.session_state.current_df):
                    st.session_state.current_df = modified_df
                    st.session_state.metadata = generate_metadata(modified_df)
                    st.success("✅ Data has been modified based on your request!")
            
            # Display chat history
            if st.session_state.chat_history:
                st.markdown("### 💬 Conversation History")
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.markdown(f"""
                        <div class="chat-message user-message">
                            <strong>You:</strong> {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="chat-message bot-message">
                            <strong>AI Assistant:</strong><br>
                            {message["content"]}
                        </div>
                        """, unsafe_allow_html=True)
            
            # Show current data preview
            if st.session_state.current_df is not None:
                st.markdown("### 📊 Current Data Preview")
                st.dataframe(st.session_state.current_df.head(20), use_container_width=True, hide_index=True)
                
                # Quick stats
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rows", st.session_state.current_df.shape[0])
                with col2:
                    st.metric("Columns", st.session_state.current_df.shape[1])
                with col3:
                    missing_pct = (st.session_state.current_df.isnull().sum().sum() / st.session_state.current_df.size * 100)
                    st.metric("Missing %", f"{missing_pct:.1f}%")

with tabs[3]:
    st.markdown("<div class='section-header'>Step 3: Review Results</div>", unsafe_allow_html=True)
    
    if st.session_state.current_df is not None:
        st.success(f"✅ Data cleaned successfully!")
        
        if st.session_state.quality_score > 0:
            display_quality_score(st.session_state.quality_score, st.session_state.quality_report)
        
        st.subheader("Cleaned Data Preview")
        st.dataframe(st.session_state.current_df.head(50), use_container_width=True, hide_index=True)
        
        if st.session_state.metadata:
            st.subheader("Dataset Metadata")
            display_metadata(st.session_state.metadata)
        
        if st.session_state.cleaning_suggestions:
            st.subheader("Cleaning Operations Applied")
            for idx, suggestion in enumerate(st.session_state.cleaning_suggestions[:10], 1):
                st.write(f"**{idx}. {suggestion.get('category', 'general').title()}**")
                st.write(f"   - {suggestion.get('description', '')}")
    else:
        st.info("No cleaned data available yet. Please run the cleaning pipeline.")

with tabs[4]:
    st.markdown("<div class='section-header'>Step 4: Download Cleaned Data</div>", unsafe_allow_html=True)
    
    if st.session_state.current_df is not None:
        st.success("🎉 **Processing Complete!**")
        
        st.write("### 💾 Download Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Excel download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.current_df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download as Excel",
                data=output.getvalue(),
                file_name=f"cleaned_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            # CSV download
            csv = st.session_state.current_df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"cleaned_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        # Show summary statistics
        st.subheader("📊 Summary Statistics")
        st.write(st.session_state.current_df.describe())
    else:
        st.info("No data available for download. Please process a file first.")

# Footer
st.markdown("---")
st.markdown("🤖 Excel Data Cleaner with AI Assistant")