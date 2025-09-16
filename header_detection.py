"""
AI-Enhanced Header Detection Module
Logic:
1. Check if headers are already present (good column names)
2. If not, remove empty rows/columns and use first row as header
3. Use LLM to validate header quality and suggest improvements
4. User can choose to accept LLM suggestions or keep current headers
"""

import pandas as pd
import numpy as np
import logging
import json
import re
from typing import Tuple, List, Dict, Any, Optional
from ai_service import make_ai_call, get_ai_service

logger = logging.getLogger(__name__)

class AIHeaderDetector:
    """
    AI-enhanced header detection with validation and suggestions
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
        
    def detect_header_row(self, df: pd.DataFrame) -> Tuple[int, pd.DataFrame, List[str], Dict[str, Any]]:
        """
        Enhanced logic: Check existing headers, process if needed, then validate with AI
        
        Returns:
            Tuple of (header_row_index, processed_df, detection_log, ai_suggestions)
        """
        detection_log = []
        original_shape = df.shape
        ai_suggestions = {"has_suggestions": False, "suggested_headers": [], "confidence": 0, "reasoning": ""}
        
        # Step 1: Check if headers are already good
        has_good_headers = self._check_existing_headers(df)
        
        if has_good_headers:
            detection_log.append("✅ Good headers already detected, keeping original structure")
            # Still validate with AI even if headers look good
            ai_suggestions = self._get_ai_header_validation(df, df.columns.tolist())
            return -1, df, detection_log, ai_suggestions
        
        # Step 2: Remove completely empty rows and columns
        df_clean = self._remove_empty_rows_and_columns(df)
        
        if df_clean.shape != original_shape:
            removed_rows = original_shape[0] - df_clean.shape[0]
            removed_cols = original_shape[1] - df_clean.shape[1]
            detection_log.append(f"🧹 Removed {removed_rows} empty rows and {removed_cols} empty columns")
        
        # Step 3: Use first row as header (if data exists)
        if len(df_clean) > 0:
            processed_df = self._process_with_first_row_header(df_clean)
            detection_log.append(f"📋 Using first row as headers, {len(processed_df)} data rows remaining")
            
            # Step 4: Get AI validation and suggestions
            current_headers = processed_df.columns.tolist()
            ai_suggestions = self._get_ai_header_validation(processed_df, current_headers)
            
            if ai_suggestions["has_suggestions"]:
                detection_log.append(f"🤖 AI suggests header improvements (confidence: {ai_suggestions['confidence']}%)")
            else:
                detection_log.append("🤖 AI confirms headers look good")
            
            return 0, processed_df, detection_log, ai_suggestions
        else:
            detection_log.append("⚠️ No data rows available after removing empty rows")
            return -1, df_clean, detection_log, ai_suggestions
    
    def _check_existing_headers(self, df: pd.DataFrame) -> bool:
        """
        Check if the dataframe already has good column headers
        """
        if df.empty:
            return False
            
        columns = df.columns.tolist()
        
        # Check for generic/bad column names
        generic_patterns = [
            r'^Unnamed:',           # Unnamed: 0, Unnamed: 1, etc.
            r'^Column_\d+$',        # Column_1, Column_2, etc.
            r'^\d+$',               # Just numbers: 0, 1, 2, etc.
            r'^$',                  # Empty strings
        ]
        
        generic_count = 0
        for col in columns:
            col_str = str(col).strip()
            if not col_str or pd.isna(col):
                generic_count += 1
                continue
                
            for pattern in generic_patterns:
                if re.match(pattern, col_str):
                    generic_count += 1
                    break
        
        # If more than 50% of columns are generic, consider headers as bad
        generic_ratio = generic_count / len(columns) if len(columns) > 0 else 1
        
        # Also check if headers look like data (all numeric, dates, etc.)
        data_like_headers = 0
        for col in columns:
            col_str = str(col).strip()
            # Check if header looks like data
            if self._looks_like_data_value(col_str):
                data_like_headers += 1
        
        data_like_ratio = data_like_headers / len(columns) if len(columns) > 0 else 0
        
        # Good headers if: < 50% generic AND < 30% data-like
        has_good_headers = generic_ratio < 0.5 and data_like_ratio < 0.3
        
        logger.info(f"Header quality check: {generic_count}/{len(columns)} generic, {data_like_headers}/{len(columns)} data-like, good_headers={has_good_headers}")
        
        return has_good_headers
    
    def _looks_like_data_value(self, value: str) -> bool:
        """Check if a value looks like data rather than a header"""
        if not value or len(value.strip()) == 0:
            return False
            
        value = value.strip()
        
        # Check if it's purely numeric
        try:
            float(value.replace(',', '').replace('$', '').replace('€', '').replace('£', ''))
            return True
        except:
            pass
        
        # Check if it looks like a date
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\w+ \d{1,2}, \d{4}'
        ]
        
        for pattern in date_patterns:
            if re.search(pattern, value):
                return True
        
        # Check if it's a very long string (likely data)
        if len(value) > 50:
            return True
            
        # Check if it contains only special characters or numbers
        if re.match(r'^[0-9\s\-\+\(\)\.\,\$\€\£\%]+$', value):
            return True
            
        return False
    
    def _remove_empty_rows_and_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove ONLY completely empty rows and columns (100% null/empty)"""
        df_result = df.copy()
        
        # Remove completely empty rows
        rows_to_remove = []
        for idx in df_result.index:
            row = df_result.loc[idx]
            # Check if all values are NaN, None, empty string, or just whitespace
            is_empty = True
            for val in row:
                if pd.notna(val) and str(val).strip() != '':
                    is_empty = False
                    break
            
            if is_empty:
                rows_to_remove.append(idx)
        
        if rows_to_remove:
            df_result = df_result.drop(index=rows_to_remove)
            logger.info(f"Removed {len(rows_to_remove)} completely empty rows")
        
        # Remove completely empty columns  
        cols_to_remove = []
        for col in df_result.columns:
            col_data = df_result[col]
            # Check if all values are NaN, None, empty string, or just whitespace
            is_empty = True
            for val in col_data:
                if pd.notna(val) and str(val).strip() != '':
                    is_empty = False
                    break
            
            if is_empty:
                cols_to_remove.append(col)
        
        if cols_to_remove:
            df_result = df_result.drop(columns=cols_to_remove)
            logger.info(f"Removed {len(cols_to_remove)} completely empty columns")
        
        return df_result
    
    def _process_with_first_row_header(self, df: pd.DataFrame) -> pd.DataFrame:
        """Use first row as header and remove it from data"""
        if len(df) == 0:
            return df
        
        # Get first row values for column names
        header_values = df.iloc[0].fillna('').astype(str)
        new_columns = []
        seen = {}
        
        for i, col_val in enumerate(header_values):
            # Create column name from header value
            if col_val.strip() == '' or pd.isna(col_val):
                col_name = f"Column_{i+1}"
            else:
                col_name = str(col_val).strip()
            
            # Handle duplicates
            if col_name in seen:
                seen[col_name] += 1
                col_name = f"{col_name}_{seen[col_name]}"
            else:
                seen[col_name] = 0
            
            new_columns.append(col_name)
        
        # Create new dataframe with first row as headers and remaining rows as data
        if len(df) > 1:
            df_processed = df.iloc[1:].copy()  # Remove first row (now used as headers)
            df_processed.columns = new_columns
            df_processed = df_processed.reset_index(drop=True)
        else:
            # Only one row (header row), create empty dataframe with proper columns
            df_processed = pd.DataFrame(columns=new_columns)
        
        return df_processed
    
    def _get_ai_header_validation(self, df: pd.DataFrame, current_headers: List[str]) -> Dict[str, Any]:
        """
        Use AI to validate current headers and suggest improvements
        """
        if not self.ai_service.is_available() or df.empty:
            return {"has_suggestions": False, "suggested_headers": [], "confidence": 0, "reasoning": "AI service not available"}
        
        try:
            # Prepare data for AI analysis (first 10 rows max)
            sample_df = df.head(10)
            
            # Convert to serializable format
            sample_data = []
            for _, row in sample_df.iterrows():
                row_data = {}
                for col in current_headers:
                    val = row.get(col, '')
                    if pd.isna(val):
                        row_data[col] = ''
                    elif isinstance(val, (np.integer, np.int64)):
                        row_data[col] = int(val)
                    elif isinstance(val, (np.floating, np.float64)):
                        row_data[col] = float(val)
                    else:
                        row_data[col] = str(val)
                sample_data.append(row_data)
            
            prompt = f"""You are an expert data analyst. Analyze these column headers and sample data to determine if the headers are appropriate and suggest improvements if needed.

Current Headers: {current_headers}

Sample Data (first 10 rows):
{json.dumps(sample_data, indent=2)}

Dataset Info:
- Total columns: {len(current_headers)}
- Total rows: {len(df)}
- Data types: {dict(df.dtypes.astype(str))}

TASK: Evaluate the header quality and provide suggestions.

Consider:
1. Are headers descriptive and meaningful?
2. Do headers match the data content?
3. Are there any generic names like "Column_1", "Unnamed", etc.?
4. Do headers follow good naming conventions?
5. Are there any duplicates or confusing names?

Provide response in this JSON format:
{{
    "headers_are_good": true/false,
    "confidence": 85,
    "reasoning": "Brief explanation of your assessment",
    "suggested_headers": ["new_header_1", "new_header_2", ...],
    "improvements": ["Specific improvement 1", "Specific improvement 2", ...]
}}

If headers are already good (confidence > 80%), set "headers_are_good": true and empty "suggested_headers".
If headers need improvement, provide better alternatives in "suggested_headers" (same length as current headers).
"""

            response = make_ai_call(prompt, max_tokens=1500)
            
            if response:
                try:
                    ai_result = json.loads(response)
                    
                    # Validate response structure
                    if not isinstance(ai_result, dict):
                        raise ValueError("Invalid response format")
                    
                    headers_are_good = ai_result.get("headers_are_good", True)
                    confidence = min(100, max(0, ai_result.get("confidence", 70)))
                    reasoning = ai_result.get("reasoning", "AI analysis completed")
                    suggested_headers = ai_result.get("suggested_headers", [])
                    improvements = ai_result.get("improvements", [])
                    
                    # Ensure suggested headers match the number of current headers
                    if suggested_headers and len(suggested_headers) != len(current_headers):
                        logger.warning(f"AI suggested {len(suggested_headers)} headers but need {len(current_headers)}")
                        suggested_headers = []
                        headers_are_good = True
                    
                    return {
                        "has_suggestions": not headers_are_good and len(suggested_headers) > 0,
                        "suggested_headers": suggested_headers,
                        "confidence": confidence,
                        "reasoning": reasoning,
                        "improvements": improvements,
                        "headers_are_good": headers_are_good
                    }
                    
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    logger.error(f"Error parsing AI response: {e}")
                    return {"has_suggestions": False, "suggested_headers": [], "confidence": 0, "reasoning": "Error parsing AI response"}
            
        except Exception as e:
            logger.error(f"Error in AI header validation: {e}")
        
        return {"has_suggestions": False, "suggested_headers": [], "confidence": 0, "reasoning": "AI validation failed"}
    
    def apply_suggested_headers(self, df: pd.DataFrame, suggested_headers: List[str]) -> pd.DataFrame:
        """
        Apply AI-suggested headers to the dataframe
        """
        if len(suggested_headers) != len(df.columns):
            logger.error(f"Cannot apply {len(suggested_headers)} suggested headers to {len(df.columns)} columns")
            return df
        
        df_result = df.copy()
        df_result.columns = suggested_headers
        return df_result

# Backward compatibility
SimpleHeaderDetector = AIHeaderDetector