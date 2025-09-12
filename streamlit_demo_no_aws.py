import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import tempfile
import shutil
from pathlib import Path
import openpyxl
from openpyxl.utils import range_boundaries
import re
import logging
from datetime import datetime
import anthropic
from dotenv import load_dotenv
import time
import traceback
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Excel Data Cleaner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1.5rem;
        color: #2c3e50;
        text-shadow: 1px 1px #ecf0f1;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #27ae60;
        margin: 1.5rem 0 1rem;
        border-bottom: 2px solid #27ae60;
        padding-bottom: 0.5rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #ecf0f1;
        border: none;
        padding: 10px 20px;
        margin: 0 5px;
        border-radius: 5px;
        font-weight: 500;
    }
    .stTabs [data-baseweb="tab-list"] button:hover {
        background-color: #3498db;
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] button[data-selected="true"] {
        background-color: #3498db;
        color: white;
    }
    .sidebar .stButton>button {
        width: 100%;
        margin: 5px 0;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .expander {
        background-color: #f9f9f9;
        border-radius: 5px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if 'uploaded_file_content' not in st.session_state:
    st.session_state.uploaded_file_content = None
if 'current_excel_name' not in st.session_state:
    st.session_state.current_excel_name = None
if 'current_sheet_name' not in st.session_state:
    st.session_state.current_sheet_name = None
if 'available_sheets' not in st.session_state:
    st.session_state.available_sheets = []
if 'cleaned_data' not in st.session_state:
    st.session_state.cleaned_data = None
if 'cleaned_file_content' not in st.session_state:
    st.session_state.cleaned_file_content = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'agent_decision' not in st.session_state:
    st.session_state.agent_decision = None

# Get Anthropic client
@st.cache_resource
def get_anthropic_client():
    """Get Anthropic client with settings"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)

def llm_detect_header_row(df, max_rows_to_analyze=15):
    """
    Use LLM to intelligently detect header row with fallback to rule-based detection.
    """
    # Check if DataFrame is empty
    if df.empty or len(df.columns) == 0:
        logger.warning("DataFrame is empty, cannot detect header")
        return -1
    
    try:
        client = get_anthropic_client()
        if not client:
            logger.info("LLM not available, falling back to rule-based header detection")
            return detect_header_row_smart(df)
        
        # Limit analysis to prevent overwhelming LLM
        sample_df = df.head(max_rows_to_analyze)
        
        # Convert to a format suitable for LLM analysis with better data representation
        sample_data = []
        for i in range(len(sample_df)):
            row_data = []
            for j in range(len(sample_df.columns)):
                val = sample_df.iloc[i, j]
                # Better value representation
                if pd.isna(val):
                    row_data.append("EMPTY")
                elif isinstance(val, (int, float)):
                    row_data.append(f"NUM:{val}")
                elif isinstance(val, str):
                    row_data.append(f"TEXT:{val[:50]}")  # Limit string length
                else:
                    row_data.append(f"OTHER:{str(val)[:30]}")
            sample_data.append({"row": i, "values": row_data})
        
        # Also collect column statistics for better analysis
        col_stats = []
        for j in range(min(len(df.columns), 20)):  # Analyze first 20 columns
            col = df.iloc[:, j].dropna()
            if len(col) > 0:
                text_count = sum(1 for v in col if isinstance(v, str) and not str(v).replace('.','').replace('-','').isdigit())
                num_count = sum(1 for v in col if isinstance(v, (int, float)) or (isinstance(v, str) and str(v).replace('.','').replace('-','').isdigit()))
                col_stats.append({
                    "col_index": j,
                    "text_ratio": text_count / len(col),
                    "num_ratio": num_count / len(col),
                    "unique_count": col.nunique()
                })
        
        prompt = f"""Analyze this Excel data and identify the header row.

DATA SAMPLE (first {len(sample_data)} rows):
{json.dumps(sample_data, indent=2, default=str)}

COLUMN STATISTICS:
{json.dumps(col_stats[:10], indent=2, default=str)}

HEADER DETECTION RULES:
1. Headers contain descriptive labels (TEXT values), not data
2. Common header keywords: name, id, date, amount, total, price, quantity, code, number, description, status, type, category, address, phone, email, customer, product, order
3. Headers usually appear before actual data rows
4. If first row has mostly TEXT values and subsequent rows have mixed/numeric data, first row is likely header
5. Empty rows before header are common (header may not be at row 0)
6. Headers should span most columns (not just a few cells)
7. If no clear headers exist, return -1

IMPORTANT: Look for the row that transitions from labels/headers to actual data values.

Return ONLY this JSON:
{{
    "header_row_index": <number or -1>,
    "confidence": <0.0 to 1.0>,
    "reasoning": "<brief explanation>"
}}"""

        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0.2,  # Lower temperature for more consistent results
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        # Extract JSON even if wrapped in text
        import re
        json_match = re.search(r'\{[^}]*"header_row_index"[^}]*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        # Parse JSON response
        try:
            result = json.loads(response_text)
            header_idx = result.get('header_row_index', -1)
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', 'No reasoning provided')
            
            logger.info(f"LLM header detection: row {header_idx}, confidence {confidence}")
            logger.info(f"LLM reasoning: {reasoning}")
            
            # Validate the result more thoroughly
            if isinstance(header_idx, int) and header_idx >= -1 and header_idx < len(df):
                if header_idx == -1 or confidence > 0.4:  # Lower threshold for acceptance
                    return header_idx
            
            logger.info("LLM result invalid or low confidence, falling back to rule-based detection")
            return detect_header_row_smart(df)
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}, falling back to rule-based detection")
            return detect_header_row_smart(df)
            
    except Exception as e:
        logger.warning(f"LLM header detection error: {str(e)}, falling back to rule-based detection")
        return detect_header_row_smart(df)

def detect_header_row_smart(df):
    """
    Enhanced smart header detection with better pattern recognition
    Returns the index of the header row, or -1 if no clear header
    """
    if df.empty or len(df.columns) == 0:
        return -1
    
    # Check first 15 rows for potential headers
    max_check = min(15, len(df))
    header_scores = []
    
    for row_idx in range(max_check):
        try:
            row_data = df.iloc[row_idx]
            non_null = row_data.dropna()
            
            if len(non_null) == 0:
                header_scores.append(0)
                continue
            
            # Calculate header likelihood score
            score = 0
            string_count = 0
            numeric_count = 0
            header_like_count = 0
            
            for val in non_null:
                val_str = str(val).strip().lower()
                
                # Check if value is string-like
                is_string_like = isinstance(val, str) or (
                    not pd.isna(val) and 
                    not (isinstance(val, (int, float)) and str(val).replace('.','').replace('-','').isdigit())
                )
                
                if is_string_like:
                    # Check for header-like characteristics
                    header_indicators = [
                        len(val_str) > 2,  # Not too short
                        any(c.isalpha() for c in val_str),  # Contains letters
                        val_str not in ['nan', 'null', 'none', '', '0', '1', 'true', 'false'],  # Not common data values
                        not val_str.replace('.','').replace('-','').replace(' ','').isdigit(),  # Not purely numeric
                        any(keyword in val_str for keyword in [
                            'name', 'id', 'date', 'amount', 'total', 'price', 'cost',
                            'code', 'number', 'address', 'phone', 'email', 'status', 
                            'type', 'description', 'category', 'customer', 'product',
                            'quantity', 'order', 'invoice', 'payment', 'reference'
                        ])  # Common header keywords
                    ]
                    
                    if sum(header_indicators) >= 3:
                        header_like_count += 1
                        score += 3
                    elif sum(header_indicators) >= 2:
                        score += 2
                    
                    string_count += 1
                else:
                    numeric_count += 1
                    # Penalize if it looks like data
                    if isinstance(val, (int, float)) and val > 100:
                        score -= 1
        
            # Boost score based on string ratio
            if len(non_null) > 0:
                string_ratio = string_count / len(non_null)
                if string_ratio >= 0.8:
                    score += 5
                elif string_ratio >= 0.6:
                    score += 3
                elif string_ratio >= 0.4:
                    score += 1
            
            # Boost score if most values look like headers
            if len(non_null) > 0 and header_like_count / len(non_null) >= 0.6:
                score += 4
            
            # Check if next rows look more like data
            data_like_next = 0
            for next_idx in range(row_idx + 1, min(row_idx + 4, len(df))):
                if next_idx < len(df):
                    try:
                        next_row = df.iloc[next_idx].dropna()
                        if len(next_row) > 0:
                            numeric_in_next = sum(1 for v in next_row if isinstance(v, (int, float)) or 
                                                (isinstance(v, str) and str(v).replace('.','').replace('-','').isdigit()))
                            if numeric_in_next / len(next_row) > 0.4:
                                data_like_next += 1
                    except:
                        pass
            
            if data_like_next >= 2:
                score += 3
            elif data_like_next >= 1:
                score += 1
            
            # Penalize if row is too early and sparse
            if row_idx > 0 and len(non_null) < len(df.columns) * 0.3:
                score -= 2
            
            header_scores.append(score)
        except Exception as e:
            logger.warning(f"Error processing row {row_idx} for header detection: {e}")
            header_scores.append(0)
    
    # Find the row with highest score above threshold
    if header_scores:
        max_score = max(header_scores)
        if max_score >= 5:  # Minimum confidence threshold
            best_idx = header_scores.index(max_score)
            
            # Additional validation: ensure it's not too late in the data
            if best_idx < min(8, len(df) // 3):
                return best_idx
    
    # Fallback: check if first few rows look like headers
    for row_idx in range(min(3, len(df))):
        row_data = df.iloc[row_idx].dropna()
        if len(row_data) > 0:
            string_ratio = sum(1 for v in row_data if isinstance(v, str) and 
                             not str(v).replace('.','').replace('-','').isdigit()) / len(row_data)
            if string_ratio >= 0.7:
                return row_idx
    
    return -1  # No header found

def clean_excel_basic(input_path, output_path, sheet_name=None):
    """Ultra-conservative Excel cleaning - preserves ALL data, no additions or deletions"""
    start_time = time.time()
    changes_log = []
    
    try:
        logger.info(f"Starting ultra-conservative clean_excel_basic: {input_path}")
        
        # Read the Excel file exactly as is - no headers assumed
        try:
            df = pd.read_excel(input_path, sheet_name=sheet_name, header=None, engine='openpyxl')
            
            # Handle case where pandas returns a dict for multiple sheets
            if isinstance(df, dict):
                if sheet_name and sheet_name in df:
                    df = df[sheet_name]
                else:
                    # Get the first sheet
                    df = list(df.values())[0] if df else pd.DataFrame()
            
            original_shape = df.shape
            changes_log.append(f"✓ Loaded Excel file with shape: {original_shape}")
        except Exception as e:
            logger.error(f"Error reading Excel file: {e}")
            changes_log.append(f"❌ Error reading Excel file: {str(e)}")
            processing_time = time.time() - start_time
            return pd.DataFrame(), changes_log, processing_time
        
        # Check if the DataFrame is completely empty
        if df.empty or (df.shape[0] == 0 or df.shape[1] == 0):
            changes_log.append("❌ Error: The Excel file appears to be completely empty")
            processing_time = time.time() - start_time
            return pd.DataFrame(), changes_log, processing_time
        
        # Step 1: Remove ONLY completely empty rows (all values are NaN)
        initial_rows = len(df)
        df = df.dropna(how='all')
        rows_removed = initial_rows - len(df)
        if rows_removed > 0:
            changes_log.append(f"✓ Removed {rows_removed} completely empty rows")
        
        # Check if DataFrame is empty after removing empty rows
        if df.empty or len(df) == 0:
            changes_log.append("❌ Error: All rows in the Excel file are empty")
            processing_time = time.time() - start_time
            return pd.DataFrame(), changes_log, processing_time
        
        # Step 2: Remove ONLY completely empty columns (all values are NaN)
        initial_cols = len(df.columns)
        df = df.dropna(axis=1, how='all')
        cols_removed = initial_cols - len(df.columns)
        if cols_removed > 0:
            changes_log.append(f"✓ Removed {cols_removed} completely empty columns")
        
        # Check if DataFrame has no columns after removing empty columns
        if df.empty or len(df.columns) == 0:
            changes_log.append("❌ Error: All columns in the Excel file are empty")
            processing_time = time.time() - start_time
            return pd.DataFrame(), changes_log, processing_time
        
        # Step 3: LLM-powered smart header detection with fallback
        header_row_idx = llm_detect_header_row(df)
        
        if header_row_idx > 0:
            # There are values above the header - preserve them in column names
            changes_log.append(f"✓ Detected header at row {header_row_idx + 1}")
            
            # Get the actual header row
            header_values = df.iloc[header_row_idx].fillna('').astype(str)
            
            # Generate proper column names
            new_columns = []
            for i, col in enumerate(header_values):
                if col == '' or col == 'nan' or str(col).strip() == '':
                    new_columns.append(f"Column_{i+1}")
                else:
                    new_columns.append(str(col).strip())
            
            df.columns = new_columns
            
            # Remove header row
            df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
            changes_log.append(f"✓ Removed header row, preserved info in column names")
            
        elif header_row_idx == 0:
            # First row is the header
            header_values = df.iloc[0].fillna('').astype(str)
            
            # Generate proper column names
            new_columns = []
            for i, col in enumerate(header_values):
                if col == '' or col == 'nan' or str(col).strip() == '':
                    new_columns.append(f"Column_{i+1}")
                else:
                    new_columns.append(str(col).strip())
            
            df.columns = new_columns
            
            # Remove the header row since it's now used as column names
            df = df.iloc[1:].reset_index(drop=True)
            changes_log.append("✓ Used first row as column names and removed header row")
        else:
            # No header detected - generate column names
            df.columns = [f"Column_{i+1}" for i in range(len(df.columns))]
            changes_log.append("✓ Generated column names (no header row detected)")
        
        # Step 4: Clean column names
        cleaned_columns = []
        seen_names = {}
        for col in df.columns:
            # Clean the column name
            col_str = str(col).strip()
            if col_str == '' or col_str == 'nan':
                col_str = f"Unnamed_{len(cleaned_columns)+1}"
            else:
                # Replace problematic characters
                col_str = col_str.replace('\n', '_').replace('\r', '_').replace('\t', '_')
                col_str = col_str.replace('/', '_').replace('\\', '_')
                # Remove multiple underscores
                col_str = '_'.join(filter(None, col_str.split('_')))
            
            # Handle duplicates
            if col_str in seen_names:
                seen_names[col_str] += 1
                col_str = f"{col_str}_{seen_names[col_str]}"
            else:
                seen_names[col_str] = 0
            
            cleaned_columns.append(col_str)
        
        df.columns = cleaned_columns
        changes_log.append(f"✓ Cleaned {len(df.columns)} column names")
        
        # Step 5: Minimal data cleaning (no data loss)
        for col in df.columns:
            if df[col].dtype == 'object':
                # Only trim whitespace, don't change values
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
        
        changes_log.append("✓ Trimmed whitespace from text values")
        
        # Step 6: Standardize only obvious missing value representations
        df = df.replace(['NULL', 'null', '#N/A'], np.nan)
        changes_log.append("✓ Standardized NULL representations to NaN")
        
        # Save the cleaned data
        df.to_excel(output_path, index=False, engine='openpyxl')
        changes_log.append(f"✅ Saved cleaned data to {output_path}")
        
        processing_time = time.time() - start_time
        changes_log.append(f"📊 Final dataset: {df.shape[0]} rows × {df.shape[1]} columns")
        changes_log.append(f"⏱️ Processing completed in {processing_time:.2f} seconds")
        return df, changes_log, processing_time
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"❌ Error processing file: {str(e)}"
        changes_log.append(error_msg)
        logger.error(f"Clean error: {str(e)} - {traceback.format_exc()}")
        return pd.DataFrame(), changes_log, processing_time

def ai_analyze_df(df):
    """Enhanced AI analysis with comprehensive metadata"""
    try:
        client = get_anthropic_client()
        if not client:
            return None, ["AI service not available - check API key"]
        
        # Limit DataFrame size to prevent overwhelming the AI
        MAX_COLS = 50
        if len(df.columns) > MAX_COLS:
            df_sample = df.iloc[:, :MAX_COLS]
            logger.info(f"DataFrame has {len(df.columns)} columns, analyzing first {MAX_COLS}")
        else:
            df_sample = df
        
        # Prepare comprehensive metadata for each column
        metadata = {}
        for col in df_sample.columns:
            try:
                col_data = df_sample[col]
                non_null_data = col_data.dropna()
                
                # Get up to 10 sample values
                sample_values = []
                if len(non_null_data) > 0:
                    unique_vals = non_null_data.unique()
                    # Take up to 10 unique values, convert to string safely
                    sample_values = []
                    for val in unique_vals[:10]:
                        try:
                            sample_values.append(str(val))
                        except:
                            sample_values.append("(complex value)")
                
                # Analyze data patterns
                col_metadata = {
                    "dtype": str(col_data.dtype),
                    "total_count": int(len(col_data)),
                    "non_null_count": int(len(non_null_data)),
                    "null_count": int(col_data.isnull().sum()),
                    "null_percentage": round(float((col_data.isnull().sum() / len(col_data)) * 100), 2) if len(col_data) > 0 else 0,
                    "unique_count": int(col_data.nunique()),
                    "sample_values": sample_values[:5],  # Limit to 5 samples to reduce size
                    "has_whitespace_issues": False,
                    "has_mixed_types": False
                }
                
                # Check for whitespace issues in string columns
                if col_data.dtype == 'object' and len(non_null_data) > 0:
                    try:
                        str_values = non_null_data[non_null_data.apply(lambda x: isinstance(x, str))]
                        if len(str_values) > 0:
                            sample_str = str_values.iloc[:min(100, len(str_values))]
                            col_metadata["has_whitespace_issues"] = any(
                                sample_str.apply(lambda x: x != x.strip() if isinstance(x, str) else False)
                            )
                    except:
                        pass
                
                # For numeric columns, add statistics
                if col_data.dtype in ['int64', 'float64', 'Int64', 'Float64']:
                    if len(non_null_data) > 0:
                        try:
                            col_metadata["min"] = round(float(non_null_data.min()), 2)
                            col_metadata["max"] = round(float(non_null_data.max()), 2)
                            col_metadata["mean"] = round(float(non_null_data.mean()), 2)
                        except:
                            pass
                
                metadata[str(col)[:50]] = col_metadata  # Limit column name length
            except Exception as e:
                logger.warning(f"Error processing column {col}: {e}")
                metadata[str(col)[:50]] = {"error": "Could not process column"}
        
        # Prepare a simplified summary for AI
        df_summary = {
            "total_rows": int(df.shape[0]),
            "total_columns": int(df.shape[1]),
            "columns_analyzed": len(metadata),
            "duplicate_rows": int(df.duplicated().sum()),
            "column_samples": {}
        }
        
        # Add simplified column info
        for col_name, col_meta in list(metadata.items())[:20]:  # Limit to 20 columns for the prompt
            df_summary["column_samples"][col_name] = {
                "dtype": col_meta.get("dtype", "unknown"),
                "null_pct": col_meta.get("null_percentage", 0),
                "unique": col_meta.get("unique_count", 0),
                "samples": col_meta.get("sample_values", [])[:3]  # Only 3 samples
            }
        
        prompt = f"""Analyze this DataFrame summary and provide data quality assessment.

DataFrame Overview:
- Shape: {df_summary['total_rows']} rows × {df_summary['total_columns']} columns
- Duplicate rows: {df_summary['duplicate_rows']}
- Columns analyzed: {df_summary['columns_analyzed']}

Column Samples (first 20):
{json.dumps(df_summary['column_samples'], indent=2, default=str)}

Provide a brief analysis focusing on:
1. Data quality issues (formatting, types, consistency)
2. Cleaning suggestions (no data removal)

Return ONLY valid JSON with this exact structure:
{{
    "analysis": ["issue 1", "issue 2", "issue 3"],
    "suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"],
    "data_quality_score": 75
}}

Keep responses concise. Maximum 3-5 items per list."""
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        # Try to extract JSON from the response
        try:
            # First try direct parsing
            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    analysis = json.loads(json_match.group())
                except:
                    # Return a default structure
                    analysis = {
                        "analysis": ["Unable to parse AI response - data analyzed successfully"],
                        "suggestions": ["Please review the metadata below for details"],
                        "data_quality_score": 70
                    }
            else:
                analysis = {
                    "analysis": ["Data analysis completed"],
                    "suggestions": ["Review metadata for detailed information"],
                    "data_quality_score": 70
                }
        
        # Add the metadata to the analysis
        analysis["metadata"] = metadata
        
        # Ensure all required fields exist
        if "analysis" not in analysis:
            analysis["analysis"] = ["Data analyzed successfully"]
        if "suggestions" not in analysis:
            analysis["suggestions"] = ["No specific suggestions"]
        if "data_quality_score" not in analysis:
            analysis["data_quality_score"] = 70
            
        return analysis, []
        
    except Exception as e:
        logger.error(f"Error in ai_analyze_df: {str(e)}")
        # Return a basic analysis with the metadata we collected
        try:
            return {
                "metadata": metadata if 'metadata' in locals() else {},
                "analysis": ["Error during AI analysis, showing basic metadata"],
                "suggestions": ["Review the metadata below for column information"],
                "data_quality_score": 50
            }, []
        except:
            return None, [f"AI Error: {str(e)}"]

def apply_ai_suggestions(df, selected_suggestions):
    """Apply AI suggestions with data preservation"""
    try:
        client = get_anthropic_client()
        if not client:
            return df, "AI service not available"
        
        # Get current shape for validation
        original_shape = df.shape
        
        df_info = f"Columns: {list(df.columns)}\nShape: {df.shape}\nDtypes: {df.dtypes.to_dict()}\nSample data:\n{df.head(5).to_string()}"
        
        prompt = f"""Given this DataFrame:
{df_info}

Implement these cleaning suggestions:
{json.dumps(selected_suggestions)}

CRITICAL RULES:
1. NEVER remove any rows or columns
2. NEVER drop or delete data
3. Only clean and standardize existing data
4. Preserve all original data values (just clean formatting)
5. Fix data types without losing information
6. Standardize formats and units
7. Clean whitespace and encoding issues
8. The output DataFrame must have the same number of rows and columns as input

Generate Python pandas code to modify 'df' following these rules. Only return executable code, no explanations.
Example transformations:
- df['col'] = df['col'].str.strip()  # Clean whitespace
- df['col'] = pd.to_numeric(df['col'], errors='ignore')  # Convert types safely
- df.columns = df.columns.str.replace(' ', '_')  # Clean column names"""
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        
        code = response.content[0].text.strip()
        
        # Remove any code blocks markers if present
        if '```python' in code:
            code = code.replace('```python', '').replace('```', '').strip()
        
        local_vars = {'df': df.copy(), 'pd': pd, 'np': np, 're': re}
        exec(code, {}, local_vars)
        
        result_df = local_vars['df']
        
        # Validate that no data was removed
        if result_df.shape[0] < original_shape[0]:
            return df, f"❌ Error: Suggestions would remove rows. Original: {original_shape[0]} rows, Result: {result_df.shape[0]} rows. Keeping original data."
        if result_df.shape[1] < original_shape[1]:
            return df, f"❌ Error: Suggestions would remove columns. Original: {original_shape[1]} cols, Result: {result_df.shape[1]} cols. Keeping original data."
        
        return result_df, f"✅ Applied suggestions successfully. Shape preserved: {original_shape}"
        
    except Exception as e:
        return df, f"❌ Error applying suggestions: {str(e)}"

def apply_user_query_to_df(df, query):
    """Apply user query"""
    try:
        client = get_anthropic_client()
        if not client:
            return df, "AI service not available"
        
        df_info = f"Columns: {list(df.columns)}\nSample data:\n{df.head(3).to_string()}"
        
        prompt = f"""Given this DataFrame:
{df_info}

User query: {query}

Generate Python pandas code to modify 'df'. Do not fill missing values. Do not remove columns unless completely empty with no name. Only return executable code.
Example: df = df.rename(columns={{'Col1': 'Name'}})"""
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        code = response.content[0].text.strip()
        
        local_vars = {'df': df.copy(), 'pd': pd, 'np': np}
        exec(code, {}, local_vars)
        
        return local_vars['df'], f"✅ Applied: {code}"
        
    except Exception as e:
        return df, f"❌ Error: {str(e)}"

# Main app
def main():
    st.markdown("<div class='main-header'>📊 Excel Data Cleaner (No Cloud)</div>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🔧 Navigation")
        st.markdown("### 📊 Status")
        ai_available = get_anthropic_client() is not None
        if ai_available:
            st.success("✅ AI Service Available")
        else:
            st.warning("⚠️ AI Service Unavailable - Add ANTHROPIC_API_KEY to .env")
        
        if st.session_state.current_excel_name:
            st.markdown("### 📂 Current File")
            st.info(f"Name: {st.session_state.current_excel_name}")
            if st.session_state.current_sheet_name:
                st.info(f"Sheet: {st.session_state.current_sheet_name}")
            if st.button("🗑️ Clear Session"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 Upload", "🧹 Clean", "🔍 Analyze", "💡 Apply Suggestions", "📥 Download"])
    
    with tab1:
        st.markdown("### Upload Excel File")
        uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx', 'xls'])
        
        if uploaded_file:
            st.info(f"**File:** {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            if st.button("📤 Load File", type="primary"):
                try:
                    # Store file content
                    st.session_state.uploaded_file_content = uploaded_file.read()
                    st.session_state.current_excel_name = uploaded_file.name
                    
                    # Get sheet names
                    temp_file = Path(tempfile.mktemp(suffix=".xlsx"))
                    with open(temp_file, 'wb') as f:
                        f.write(st.session_state.uploaded_file_content)
                    
                    with pd.ExcelFile(temp_file, engine='openpyxl') as xl_file:
                        st.session_state.available_sheets = xl_file.sheet_names
                    
                    if temp_file.exists():
                        temp_file.unlink()
                    
                    st.success("✅ File loaded successfully!")
                    st.write("**Available sheets:**", ", ".join(st.session_state.available_sheets))
                    
                    # Display preview
                    if st.session_state.available_sheets:
                        selected_sheet = st.selectbox("Select sheet to preview:", st.session_state.available_sheets)
                        df_preview = pd.read_excel(
                            BytesIO(st.session_state.uploaded_file_content), 
                            sheet_name=selected_sheet,
                            nrows=10
                        )
                        st.write("**Preview (first 10 rows):**")
                        st.dataframe(df_preview)
                        
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")
    
    with tab2:
        st.markdown("### Clean Data")
        
        if not st.session_state.uploaded_file_content:
            st.warning("⚠️ Please upload a file first!")
        else:
            st.info(f"**File:** {st.session_state.current_excel_name}")
            
            if st.session_state.available_sheets:
                selected_sheet = st.selectbox(
                    "Select sheet to clean:", 
                    st.session_state.available_sheets,
                    key="clean_sheet"
                )
                
                if st.button("🧹 Clean Data", type="primary"):
                    with st.spinner("Cleaning data..."):
                        try:
                            # Save to temp file
                            temp_input = Path(tempfile.mktemp(suffix=".xlsx"))
                            temp_output = Path(tempfile.mktemp(suffix="_cleaned.xlsx"))
                            
                            with open(temp_input, 'wb') as f:
                                f.write(st.session_state.uploaded_file_content)
                            
                            # Clean the data
                            df, changes_log, processing_time = clean_excel_basic(
                                str(temp_input), 
                                str(temp_output), 
                                selected_sheet
                            )
                            
                            if not df.empty:
                                # Store cleaned data
                                st.session_state.cleaned_data = df
                                st.session_state.current_sheet_name = selected_sheet
                                
                                # Read cleaned file content
                                with open(temp_output, 'rb') as f:
                                    st.session_state.cleaned_file_content = f.read()
                                
                                st.success(f"✅ Data cleaned successfully in {processing_time:.2f} seconds!")
                                
                                # Display metrics
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Rows", df.shape[0])
                                with col2:
                                    st.metric("Columns", df.shape[1])
                                with col3:
                                    st.metric("Total Cells", df.shape[0] * df.shape[1])
                                
                                # Show changes log
                                with st.expander("📋 Cleaning Report", expanded=True):
                                    for change in changes_log:
                                        if "✅" in change or "✓" in change:
                                            st.success(change)
                                        elif "⚠️" in change:
                                            st.warning(change)
                                        elif "❌" in change:
                                            st.error(change)
                                        else:
                                            st.info(change)
                                
                                # Show cleaned data
                                st.write("**Cleaned Data:**")
                                st.dataframe(df)
                            else:
                                st.error("❌ Cleaning failed - check the error messages above")
                                for change in changes_log:
                                    if "❌" in change:
                                        st.error(change)
                            
                            # Clean up temp files
                            if temp_input.exists():
                                temp_input.unlink()
                            if temp_output.exists():
                                temp_output.unlink()
                                
                        except Exception as e:
                            st.error(f"Error cleaning data: {str(e)}")
    
    with tab3:
        st.markdown("### Analyze Data")
        
        if not st.session_state.cleaned_data is None:
            if st.button("🔍 Analyze with AI", type="primary"):
                with st.spinner("Analyzing data..."):
                    analysis, errors = ai_analyze_df(st.session_state.cleaned_data)
                    
                    if analysis:
                        st.session_state.analysis_results = analysis
                        st.success("✅ Analysis complete!")
                        
                        # Display quality score
                        if 'data_quality_score' in analysis:
                            score = analysis['data_quality_score']
                            color = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                            st.markdown(f"### {color} Data Quality Score: {score}/100")
                            st.progress(score / 100)
                        
                        # Display analysis
                        if 'analysis' in analysis:
                            st.markdown("**🔍 Data Quality Issues:**")
                            for item in analysis['analysis']:
                                st.write(f"• {item}")
                        
                        # Display suggestions
                        if 'suggestions' in analysis:
                            st.markdown("**💡 Cleaning Suggestions:**")
                            for suggestion in analysis['suggestions']:
                                st.write(f"• {suggestion}")
                        
                        # Display metadata
                        if 'metadata' in analysis:
                            with st.expander("📊 Detailed Column Metadata"):
                                for col_name, col_meta in analysis['metadata'].items():
                                    st.markdown(f"**Column: `{col_name}`**")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.write(f"Type: {col_meta.get('dtype', 'unknown')}")
                                        st.write(f"Non-null: {col_meta.get('non_null_count', 0)}")
                                    with col2:
                                        st.write(f"Unique: {col_meta.get('unique_count', 0)}")
                                        st.write(f"Missing: {col_meta.get('null_percentage', 0)}%")
                                    with col3:
                                        if col_meta.get('sample_values'):
                                            st.write(f"Samples: {', '.join(str(v) for v in col_meta['sample_values'][:3])}")
                                    st.markdown("---")
                    else:
                        st.error(f"❌ Analysis failed: {', '.join(errors)}")
        else:
            st.warning("⚠️ Please clean the data first!")
    
    with tab4:
        st.markdown("### Apply Suggestions")
        
        if st.session_state.analysis_results and 'suggestions' in st.session_state.analysis_results:
            st.markdown("**Select suggestions to apply:**")
            
            selected_suggestions = []
            for i, suggestion in enumerate(st.session_state.analysis_results['suggestions']):
                if st.checkbox(suggestion, key=f"sug_{i}"):
                    selected_suggestions.append(suggestion)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if selected_suggestions and st.button("💡 Apply Selected Suggestions", type="primary"):
                    with st.spinner("Applying suggestions..."):
                        modified_df, result = apply_ai_suggestions(
                            st.session_state.cleaned_data, 
                            selected_suggestions
                        )
                        
                        if "✅" in result:
                            st.session_state.cleaned_data = modified_df
                            
                            # Update cleaned file
                            temp_file = Path(tempfile.mktemp(suffix=".xlsx"))
                            modified_df.to_excel(temp_file, index=False, engine='openpyxl')
                            with open(temp_file, 'rb') as f:
                                st.session_state.cleaned_file_content = f.read()
                            if temp_file.exists():
                                temp_file.unlink()
                            
                            st.success(result)
                            st.write("**Updated Data:**")
                            st.dataframe(modified_df)
                        else:
                            st.error(result)
            
            with col2:
                st.markdown("**Or apply custom query:**")
                user_query = st.text_area("Enter your modification query:", 
                                         placeholder="e.g., 'Rename column Col1 to CustomerName'")
                
                if user_query and st.button("❓ Apply Query", type="secondary"):
                    with st.spinner("Applying query..."):
                        modified_df, result = apply_user_query_to_df(
                            st.session_state.cleaned_data, 
                            user_query
                        )
                        
                        if "✅" in result:
                            st.session_state.cleaned_data = modified_df
                            
                            # Update cleaned file
                            temp_file = Path(tempfile.mktemp(suffix=".xlsx"))
                            modified_df.to_excel(temp_file, index=False, engine='openpyxl')
                            with open(temp_file, 'rb') as f:
                                st.session_state.cleaned_file_content = f.read()
                            if temp_file.exists():
                                temp_file.unlink()
                            
                            st.success(result)
                            st.write("**Updated Data:**")
                            st.dataframe(modified_df)
                        else:
                            st.error(result)
        else:
            st.warning("⚠️ Please analyze the data first to get suggestions!")
    
    with tab5:
        st.markdown("### Download Cleaned Data")
        
        if st.session_state.cleaned_file_content:
            col1, col2 = st.columns(2)
            
            with col1:
                st.download_button(
                    label="📥 Download Cleaned Excel",
                    data=st.session_state.cleaned_file_content,
                    file_name=f"cleaned_{st.session_state.current_excel_name}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col2:
                if st.session_state.cleaned_data is not None:
                    csv = st.session_state.cleaned_data.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"cleaned_{st.session_state.current_excel_name.replace('.xlsx', '.csv')}",
                        mime="text/csv"
                    )
        else:
            st.warning("⚠️ No cleaned data available. Please clean the data first!")
    
    # Footer
    st.markdown("---")
    st.markdown("<div style='text-align: center; color: #7f8c8d; font-size: 0.9rem;'>Excel Data Cleaner v2.0 (Local Version - No Cloud Storage)</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()