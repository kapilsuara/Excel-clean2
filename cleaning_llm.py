"""
Cleaning LLM Module
Handles comprehensive data cleaning suggestions using AI
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Any, Optional
from ai_service import make_ai_call, get_ai_service
import logging

logger = logging.getLogger(__name__)

class CleaningLLM:
    """
    LLM for analyzing data and suggesting cleaning operations
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.cleaning_categories = {
            "structural": [
                "Remove empty rows and columns",
                "Handle merged cells",
                "Fix multi-row headers",
                "Standardize column names",
                "Remove duplicate sheets",
                "Split combined cells",
                "Normalize column order",
                "Detect hidden rows/columns"
            ],
            "text": [
                "Trim whitespace",
                "Remove special characters",
                "Fix encoding issues",
                "Standardize text case",
                "Normalize naming conventions",
                "Remove non-printable characters",
                "Split concatenated text",
                "Handle mixed languages"
            ],
            "numerical": [
                "Convert text to numbers",
                "Fix negative number formats",
                "Standardize number separators",
                "Round decimals consistently",
                "Normalize currency formats",
                "Handle outliers",
                "Fix calculation errors",
                "Normalize units"
            ],
            "datetime": [
                "Convert text to datetime",
                "Standardize date formats",
                "Remove invalid dates",
                "Fill missing dates",
                "Extract date components",
                "Handle timezones",
                "Split datetime columns",
                "Fix date ranges"
            ],
            "duplicates": [
                "Remove exact duplicates",
                "Handle partial duplicates",
                "Deduplicate with rules",
                "Identify near-duplicates",
                "Merge duplicate records",
                "Flag suspicious duplicates"
            ],
            "missing": [
                "Identify missing patterns",
                "Fill with statistics",
                "Forward/backward fill",
                "Drop excessive missing",
                "Impute with ML",
                "Add missing flags"
            ],
            "consistency": [
                "Standardize units",
                "Normalize categories",
                "Fix phone formats",
                "Validate emails",
                "Normalize booleans",
                "Ensure data types",
                "Harmonize IDs",
                "Fix inconsistent spelling"
            ],
            "validation": [
                "Validate totals",
                "Check relationships",
                "Verify calculations",
                "Detect anomalies",
                "Validate patterns",
                "Check business rules",
                "Cross-reference data",
                "Verify hierarchies"
            ]
        }
    
    def analyze_and_suggest(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze dataframe and suggest cleaning operations
        
        Args:
            df: The dataframe to analyze
            metadata: Metadata about the dataframe
            
        Returns:
            List of cleaning suggestions with details
        """
        if not self.ai_service.is_available():
            logger.error("AI service not available")
            return self._get_rule_based_suggestions(df, metadata)
        
        suggestions = []
        
        # Prepare comprehensive context for LLM
        context = self._prepare_context(df, metadata)
        
        # Convert numpy types to Python types for JSON serialization
        def convert_to_serializable(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.Series):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        # Convert context to serializable format
        overview_serializable = convert_to_serializable(context['overview'])
        columns_serializable = convert_to_serializable(context['columns'][:10])
        issues_serializable = convert_to_serializable(context['quality_issues'])
        
        # Generate cleaning suggestions using LLM
        prompt = f"""You are an expert data cleaning specialist. Analyze this Excel data and provide comprehensive cleaning suggestions.

Dataset Overview:
{json.dumps(overview_serializable, indent=2)}

Column Details:
{json.dumps(columns_serializable, indent=2)}  # First 10 columns

Data Quality Issues:
{json.dumps(issues_serializable, indent=2)}

Sample Data (first 5 rows):
{context['sample_data']}

TASK: Provide a comprehensive list of cleaning operations needed for this dataset.

Consider ALL aspects:
1. Structural Cleaning (empty rows/cols, merged cells, headers)
2. Text Cleaning (whitespace, encoding, case, special chars)
3. Numerical Cleaning (formats, units, outliers, calculations)
4. Date/Time Cleaning (formats, invalid dates, timezones)
5. Duplicates & Missing Values
6. Consistency & Standardization
7. Validation & Business Rules
8. Advanced Pattern Detection

For each suggestion, provide:
- Category (structural/text/numerical/datetime/duplicates/missing/consistency/validation)
- Description of the issue
- Specific action to take
- Priority (high/medium/low)
- Whether it requires code generation (true/false)

Return ONLY a JSON array of suggestions:
[
    {{
        "category": "structural",
        "description": "Remove 5 completely empty columns",
        "action": "Drop columns with all null values",
        "priority": "high",
        "requires_code": true,
        "affected_columns": ["col1", "col2"],
        "impact": "Reduces dataset size by 20%"
    }},
    ...
]

Provide at least 10-15 specific, actionable suggestions based on the actual data issues found."""

        try:
            response = make_ai_call(prompt, max_tokens=2000)
            if response:
                suggestions = json.loads(response)
                # Add metadata context to each suggestion (ensure serializable)
                for suggestion in suggestions:
                    suggestion['context'] = {
                        'df_shape': [int(df.shape[0]), int(df.shape[1])],
                        'columns': [str(col) for col in df.columns],
                        'dtypes': {str(col): str(dtype) for col, dtype in df.dtypes.items()}
                    }
            else:
                suggestions = self._get_rule_based_suggestions(df, metadata)
        except Exception as e:
            logger.error(f"Error in LLM analysis: {str(e)}")
            suggestions = self._get_rule_based_suggestions(df, metadata)
        
        return suggestions
    
    def _prepare_context(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comprehensive context for LLM analysis with null-safe metadata handling"""
        # Ensure metadata is not None
        if metadata is None:
            metadata = {'quality_indicators': {}}
        
        # Convert data types dictionary to serializable format
        dtypes_dict = {}
        for dtype, count in df.dtypes.value_counts().items():
            dtypes_dict[str(dtype)] = int(count)
        
        context = {
            'overview': {
                'shape': [int(df.shape[0]), int(df.shape[1])],
                'memory_usage_mb': float(df.memory_usage(deep=True).sum() / 1024**2),
                'missing_percentage': float((df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100) if df.size > 0 else 0,
                'duplicate_rows': int(df.duplicated().sum()),
                'data_types': dtypes_dict
            },
            'columns': [],
            'quality_issues': [],
            'sample_data': df.head(5).to_string()
        }
        
        # Analyze each column
        for col in df.columns:
            # Convert sample values to Python types
            sample_vals = []
            for val in df[col].dropna().head(5):
                if pd.isna(val):
                    sample_vals.append(None)
                elif isinstance(val, (np.integer, np.int64)):
                    sample_vals.append(int(val))
                elif isinstance(val, (np.floating, np.float64)):
                    sample_vals.append(float(val))
                else:
                    sample_vals.append(str(val))
            
            col_info = {
                'name': str(col),
                'dtype': str(df[col].dtype),
                'missing_count': int(df[col].isnull().sum()),
                'missing_percent': float((df[col].isnull().sum() / len(df)) * 100),
                'unique_count': int(df[col].nunique()),
                'sample_values': sample_vals
            }
            
            # Detect issues
            if col_info['missing_percent'] > 50:
                context['quality_issues'].append(f"Column '{col}' has {col_info['missing_percent']:.1f}% missing values")
            
            if col_info['unique_count'] == 1:
                context['quality_issues'].append(f"Column '{col}' has only one unique value")
            
            if df[col].dtype == 'object':
                # Check for leading/trailing spaces
                sample = df[col].dropna().head(10)
                if any(str(val) != str(val).strip() for val in sample):
                    context['quality_issues'].append(f"Column '{col}' has leading/trailing whitespace")
            
            context['columns'].append(col_info)
        
        # Detect structural issues
        if df.duplicated().any():
            context['quality_issues'].append(f"Found {df.duplicated().sum()} duplicate rows")
        
        # Check for potential date columns stored as text (with null-safe access)
        quality_indicators = metadata.get('quality_indicators', {}) if metadata else {}
        potentially_datetime = quality_indicators.get('potentially_datetime', [])
        for col in potentially_datetime:
            context['quality_issues'].append(f"Column '{col}' appears to contain dates stored as text")
        
        # Check for numeric columns stored as text (with null-safe access)
        potentially_numeric_text = quality_indicators.get('potentially_numeric_text', [])
        for col in potentially_numeric_text:
            context['quality_issues'].append(f"Column '{col}' appears to contain numbers stored as text")
        
        return context
    
    def _get_rule_based_suggestions(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback rule-based suggestion generation"""
        suggestions = []
        
        # Check for duplicate rows
        if df.duplicated().any():
            suggestions.append({
                "category": "duplicates",
                "description": f"Remove {df.duplicated().sum()} duplicate rows",
                "action": "Drop duplicate rows keeping first occurrence",
                "priority": "high",
                "requires_code": True,
                "affected_columns": "all",
                "impact": f"Removes {df.duplicated().sum()} rows"
            })
        
        # Check for columns with high missing values
        for col in df.columns:
            missing_pct = (df[col].isnull().sum() / len(df)) * 100
            if missing_pct > 70:
                suggestions.append({
                    "category": "missing",
                    "description": f"Column '{col}' has {missing_pct:.1f}% missing values",
                    "action": f"Consider dropping column '{col}' or imputing values",
                    "priority": "medium",
                    "requires_code": True,
                    "affected_columns": [col],
                    "impact": f"Affects {missing_pct:.1f}% of rows"
                })
        
        # Check for text columns that need cleaning
        for col in df.select_dtypes(include=['object']).columns:
            sample = df[col].dropna().head(20)
            
            # Check for whitespace issues
            if any(str(val) != str(val).strip() for val in sample):
                suggestions.append({
                    "category": "text",
                    "description": f"Column '{col}' contains leading/trailing whitespace",
                    "action": "Trim whitespace from all values",
                    "priority": "high",
                    "requires_code": True,
                    "affected_columns": [col],
                    "impact": "Improves data consistency"
                })
            
            # Check for inconsistent case
            unique_lower = sample.str.lower().nunique()
            unique_original = sample.nunique()
            if unique_lower < unique_original:
                suggestions.append({
                    "category": "text",
                    "description": f"Column '{col}' has inconsistent text case",
                    "action": "Standardize text case",
                    "priority": "medium",
                    "requires_code": True,
                    "affected_columns": [col],
                    "impact": f"Reduces unique values from {unique_original} to {unique_lower}"
                })
        
        # Check for potential datetime columns
        for col in metadata.get('quality_indicators', {}).get('potentially_datetime', []):
            suggestions.append({
                "category": "datetime",
                "description": f"Column '{col}' appears to contain dates as text",
                "action": "Convert to datetime format",
                "priority": "high",
                "requires_code": True,
                "affected_columns": [col],
                "impact": "Enables date operations and sorting"
            })
        
        # Check for numeric text columns
        for col in metadata.get('quality_indicators', {}).get('potentially_numeric_text', []):
            suggestions.append({
                "category": "numerical",
                "description": f"Column '{col}' contains numbers stored as text",
                "action": "Convert to numeric type",
                "priority": "high",
                "requires_code": True,
                "affected_columns": [col],
                "impact": "Enables numeric operations"
            })
        
        # Check for single-value columns
        for col in df.columns:
            if df[col].nunique() == 1:
                suggestions.append({
                    "category": "structural",
                    "description": f"Column '{col}' contains only one unique value",
                    "action": "Consider dropping this column",
                    "priority": "low",
                    "requires_code": True,
                    "affected_columns": [col],
                    "impact": "Reduces redundant data"
                })
        
        return suggestions