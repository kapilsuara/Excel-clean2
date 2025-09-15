"""
Data Quality Scorer for Excel Data Cleaner
Implements GIGO (Garbage In, Garbage Out) detection
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, List

logger = logging.getLogger(__name__)

class DataQualityScorer:
    """Calculate data quality score based on multiple factors"""
    
    def __init__(self):
        self.garbage_threshold = 30  # Below this score = garbage data
        self.weights = {
            'missing_values': 0.25,
            'duplicate_rows': 0.15,
            'inconsistent_types': 0.20,
            'empty_columns': 0.15,
            'data_patterns': 0.15,
            'header_quality': 0.10
        }
    
    def calculate_score(self, df: pd.DataFrame, header_detected: bool = False) -> Tuple[int, Dict, str]:
        """
        Calculate overall data quality score
        
        Returns:
            Tuple of (score, details, recommendation)
        """
        scores = {}
        
        # 1. Missing Values Score (0-100)
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        missing_ratio = missing_cells / total_cells if total_cells > 0 else 0
        scores['missing_values'] = max(0, 100 - (missing_ratio * 200))  # 50% missing = 0 score
        
        # 2. Duplicate Rows Score (0-100)
        duplicate_rows = df.duplicated().sum()
        duplicate_ratio = duplicate_rows / len(df) if len(df) > 0 else 0
        scores['duplicate_rows'] = max(0, 100 - (duplicate_ratio * 150))  # 66% duplicates = 0 score
        
        # 3. Inconsistent Data Types Score (0-100)
        inconsistent_cols = 0
        for col in df.columns:
            if df[col].dtype == 'object':
                # Check if column has mixed types
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    # Try to detect mixed types
                    has_numbers = any(self._is_number(x) for x in non_null.head(20))
                    has_text = any(not self._is_number(x) for x in non_null.head(20))
                    if has_numbers and has_text:
                        inconsistent_cols += 1
        
        inconsistent_ratio = inconsistent_cols / len(df.columns) if len(df.columns) > 0 else 0
        scores['inconsistent_types'] = max(0, 100 - (inconsistent_ratio * 100))
        
        # 4. Empty Columns Score (0-100)
        empty_cols = df.isnull().all().sum()
        empty_ratio = empty_cols / len(df.columns) if len(df.columns) > 0 else 0
        scores['empty_columns'] = max(0, 100 - (empty_ratio * 100))
        
        # 5. Data Patterns Score (0-100)
        pattern_score = 100
        
        # Check for single value columns (no variation)
        single_value_cols = 0
        for col in df.columns:
            if df[col].nunique() == 1:
                single_value_cols += 1
        
        # Check for columns that are mostly nulls
        mostly_null_cols = 0
        for col in df.columns:
            if df[col].isnull().sum() > len(df) * 0.9:
                mostly_null_cols += 1
        
        # Check if data has reasonable shape
        if len(df) < 2 or len(df.columns) < 2:
            pattern_score -= 30
        
        if single_value_cols > len(df.columns) * 0.3:
            pattern_score -= 20
        
        if mostly_null_cols > len(df.columns) * 0.5:
            pattern_score -= 30
        
        scores['data_patterns'] = max(0, pattern_score)
        
        # 6. Header Quality Score (0-100)
        header_score = 100
        if not header_detected:
            header_score -= 20
        
        # Check for generic column names
        generic_names = sum(1 for col in df.columns if 
                          'Unnamed' in str(col) or 
                          'Column_' in str(col) or
                          pd.isna(col) or
                          str(col).strip() == '')
        
        if generic_names > len(df.columns) * 0.5:
            header_score -= 40
        elif generic_names > len(df.columns) * 0.2:
            header_score -= 20
        
        scores['header_quality'] = max(0, header_score)
        
        # Calculate weighted average
        total_score = sum(scores[key] * self.weights[key] for key in scores)
        total_score = int(total_score)
        
        # Generate recommendation
        if total_score < self.garbage_threshold:
            recommendation = "GARBAGE DATA DETECTED! This data requires significant manual cleanup or restructuring before it can be processed. Consider using AI chat assistance or manual data preparation."
            quality_level = "GARBAGE"
        elif total_score < 50:
            recommendation = "Poor data quality. Multiple issues detected that need attention before processing."
            quality_level = "POOR"
        elif total_score < 70:
            recommendation = "Fair data quality. Some issues present but data can be processed with caution."
            quality_level = "FAIR"
        elif total_score < 85:
            recommendation = "Good data quality. Minor issues that can be addressed during cleaning."
            quality_level = "GOOD"
        else:
            recommendation = "Excellent data quality. Data is well-structured and ready for processing."
            quality_level = "EXCELLENT"
        
        # Create detailed report
        details = {
            'scores': scores,
            'total_score': total_score,
            'quality_level': quality_level,
            'issues': self._identify_issues(scores),
            'stats': {
                'missing_cells': f"{missing_cells}/{total_cells} ({missing_ratio*100:.1f}%)",
                'duplicate_rows': f"{duplicate_rows}/{len(df)} ({duplicate_ratio*100:.1f}%)",
                'empty_columns': f"{empty_cols}/{len(df.columns)}",
                'inconsistent_columns': f"{inconsistent_cols}/{len(df.columns)}",
                'generic_column_names': f"{generic_names}/{len(df.columns)}"
            }
        }
        
        return total_score, details, recommendation
    
    def _is_number(self, value) -> bool:
        """Check if a value is numeric"""
        try:
            float(str(value).replace(',', '').replace('$', '').replace('€', '').replace('£', ''))
            return True
        except:
            return False
    
    def _identify_issues(self, scores: Dict) -> List[str]:
        """Identify specific issues based on scores"""
        issues = []
        
        if scores['missing_values'] < 50:
            issues.append("High percentage of missing values")
        
        if scores['duplicate_rows'] < 70:
            issues.append("Significant duplicate rows detected")
        
        if scores['inconsistent_types'] < 70:
            issues.append("Mixed data types in columns")
        
        if scores['empty_columns'] < 80:
            issues.append("Empty or mostly empty columns")
        
        if scores['data_patterns'] < 60:
            issues.append("Poor data structure or patterns")
        
        if scores['header_quality'] < 70:
            issues.append("Missing or poor quality headers")
        
        return issues
    
    def generate_cleanup_suggestions(self, details: Dict) -> List[str]:
        """Generate specific cleanup suggestions based on issues"""
        suggestions = []
        scores = details['scores']
        
        if scores['missing_values'] < 50:
            suggestions.append("Fill or remove rows with excessive missing values")
        
        if scores['duplicate_rows'] < 70:
            suggestions.append("Remove duplicate rows to improve data quality")
        
        if scores['inconsistent_types'] < 70:
            suggestions.append("Standardize data types in mixed-type columns")
        
        if scores['empty_columns'] < 80:
            suggestions.append("Remove completely empty columns")
        
        if scores['header_quality'] < 70:
            suggestions.append("Add proper column headers or detect header row")
        
        if details['total_score'] < self.garbage_threshold:
            suggestions.insert(0, "⚠️ CRITICAL: Consider restructuring the data completely or using manual cleanup tools")
        
        return suggestions

def assess_data_quality(df: pd.DataFrame, header_detected: bool = False) -> Tuple[int, Dict, str, List[str]]:
    """
    Main function to assess data quality
    
    Returns:
        Tuple of (score, details, recommendation, suggestions)
    """
    scorer = DataQualityScorer()
    score, details, recommendation = scorer.calculate_score(df, header_detected)
    suggestions = scorer.generate_cleanup_suggestions(details)
    
    return score, details, recommendation, suggestions