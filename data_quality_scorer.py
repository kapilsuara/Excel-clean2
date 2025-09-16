"""
Realistic Data Quality Scorer for Excel Data Cleaner
Implements balanced quality assessment that's more forgiving for normal Excel files
"""

import pandas as pd
import numpy as np
import logging
import re
from typing import Dict, Tuple, List

logger = logging.getLogger(__name__)

class RealisticDataQualityScorer:
    """Realistic data quality scorer that's more forgiving for normal Excel files"""
    
    def __init__(self):
        self.garbage_threshold = 25  # Below this score = garbage data (lowered from 30)
        # Adjusted weights to be more balanced and forgiving
        self.weights = {
            'structural_integrity': 0.25,  # Increased importance for basic structure
            'data_completeness': 0.30,     # Most important - data should exist
            'data_consistency': 0.15,      # Reduced - mixed types are common in Excel
            'data_uniqueness': 0.10,       # Reduced - duplicates might be intentional
            'format_compliance': 0.05,     # Much reduced - format violations are common
            'business_logic': 0.05,        # Reduced - hard to assess without context
            'header_quality': 0.10         # Reasonable importance for headers
        }
    
    def calculate_score(self, df: pd.DataFrame, header_detected: bool = False, original_df: pd.DataFrame = None) -> Tuple[int, Dict, str]:
        """
        Realistic data quality calculation that's more forgiving for normal Excel files
        
        Returns:
            Tuple of (score, details, recommendation)
        """
        scores = {}
        
        # 1. Structural Integrity (0-100) - More forgiving
        scores['structural_integrity'] = self._analyze_structural_integrity_realistic(df, original_df)
        
        # 2. Data Completeness (0-100) - Most important metric
        scores['data_completeness'] = self._analyze_data_completeness_realistic(df)
        
        # 3. Data Consistency (0-100) - More forgiving for Excel files
        scores['data_consistency'] = self._analyze_data_consistency_realistic(df)
        
        # 4. Data Uniqueness (0-100) - More forgiving
        scores['data_uniqueness'] = self._analyze_data_uniqueness_realistic(df)
        
        # 5. Format Compliance (0-100) - Much more forgiving
        scores['format_compliance'] = self._analyze_format_compliance_realistic(df)
        
        # 6. Business Logic (0-100) - More forgiving
        scores['business_logic'] = self._analyze_business_logic_realistic(df)
        
        # 7. Header Quality (0-100) - Reasonable assessment
        scores['header_quality'] = self._analyze_header_quality_realistic(df, header_detected)
        
        # Calculate weighted average
        total_score = sum(scores[key] * self.weights[key] for key in scores)
        total_score = int(total_score)
        
        # Generate recommendation with more realistic thresholds
        if total_score < self.garbage_threshold:
            recommendation = "Very poor data quality. Significant issues detected that require attention."
            quality_level = "POOR"
        elif total_score < 45:
            recommendation = "Below average data quality. Some issues present but data can be processed."
            quality_level = "FAIR"
        elif total_score < 65:
            recommendation = "Good data quality. Minor issues that can be easily addressed."
            quality_level = "GOOD"
        elif total_score < 80:
            recommendation = "Very good data quality. Well-structured data ready for processing."
            quality_level = "VERY_GOOD"
        else:
            recommendation = "Excellent data quality. Premium quality data structure."
            quality_level = "EXCELLENT"
        
        # Create detailed report
        details = {
            'scores': scores,
            'total_score': total_score,
            'quality_level': quality_level,
            'issues': self._identify_realistic_issues(scores),
            'stats': self._generate_realistic_stats(df)
        }
        
        return total_score, details, recommendation
    
    def _analyze_structural_integrity_realistic(self, df: pd.DataFrame, original_df: pd.DataFrame = None) -> float:
        """More forgiving structural analysis"""
        score = 100.0
        
        # Less harsh penalties for shape
        if len(df) < 1:
            score -= 50  # Only penalize if no data at all
        elif len(df) < 3:
            score -= 15  # Reduced penalty for small datasets
        
        if len(df.columns) < 1:
            score -= 50  # Only penalize if no columns at all
        elif len(df.columns) > 100:  # Increased threshold
            score -= 10  # Reduced penalty
        
        # More forgiving empty row/column assessment
        empty_rows = df.isnull().all(axis=1).sum()
        empty_cols = df.isnull().all(axis=0).sum()
        
        # Only penalize if more than 50% empty (was 30%)
        if empty_rows > len(df) * 0.5:
            score -= 20  # Reduced penalty
        elif empty_rows > len(df) * 0.3:
            score -= 5   # Minimal penalty
            
        if empty_cols > len(df.columns) * 0.5:
            score -= 20  # Reduced penalty
        elif empty_cols > len(df.columns) * 0.3:
            score -= 5   # Minimal penalty
        
        return max(0, score)
    
    def _analyze_data_completeness_realistic(self, df: pd.DataFrame) -> float:
        """Realistic data completeness analysis"""
        if df.empty:
            return 0
            
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        missing_ratio = missing_cells / total_cells
        
        # More forgiving missing value assessment
        # 50% missing = 50 score (was 0), 25% missing = 75 score
        base_score = max(0, 100 - (missing_ratio * 100))
        
        # Bonus for having any data at all
        if missing_ratio < 0.9:  # Less than 90% missing
            base_score = max(base_score, 40)  # Minimum 40 points for having some data
        
        return base_score
    
    def _analyze_data_consistency_realistic(self, df: pd.DataFrame) -> float:
        """More forgiving data consistency analysis - mixed types are normal in Excel"""
        if df.empty:
            return 50  # Neutral score
            
        score = 85.0  # Start higher - mixed types are normal in Excel
        
        # Only penalize severely mixed columns
        severely_mixed_cols = 0
        for col in df.columns:
            if df[col].dtype == 'object' and not df[col].isnull().all():
                non_null = df[col].dropna().astype(str)
                if len(non_null) > 1:
                    # Check for severely mixed types (more than 3 types)
                    numeric_count = sum(1 for x in non_null.head(20) if self._is_number(x))
                    date_count = sum(1 for x in non_null.head(20) if self._is_date(x))
                    text_count = len(non_null.head(20)) - numeric_count - date_count
                    
                    # Count non-zero types
                    type_counts = [c for c in [numeric_count, date_count, text_count] if c > 0]
                    if len(type_counts) > 2 and all(c > len(non_null) * 0.2 for c in type_counts):
                        severely_mixed_cols += 1
        
        if severely_mixed_cols > 0:
            penalty = (severely_mixed_cols / len(df.columns)) * 20  # Reduced penalty
            score -= penalty
        
        return max(50, score)  # Minimum 50 for realistic assessment
    
    def _analyze_data_uniqueness_realistic(self, df: pd.DataFrame) -> float:
        """More forgiving uniqueness analysis - duplicates might be intentional"""
        if df.empty:
            return 50
            
        score = 90.0  # Start high - duplicates might be normal
        
        # Only penalize excessive duplicates
        if len(df) > 1:
            duplicate_rows = df.duplicated().sum()
            duplicate_ratio = duplicate_rows / len(df)
            # Only penalize if more than 70% duplicates (was any duplicates)
            if duplicate_ratio > 0.7:
                score -= duplicate_ratio * 30
            elif duplicate_ratio > 0.5:
                score -= duplicate_ratio * 15
        
        # Only penalize if more than 50% of columns are single-value
        single_value_cols = sum(1 for col in df.columns 
                               if df[col].nunique() <= 1 and not df[col].isnull().all())
        if single_value_cols > len(df.columns) * 0.5:
            score -= 20
        
        return max(50, score)
    
    def _analyze_format_compliance_realistic(self, df: pd.DataFrame) -> float:
        """Much more forgiving format compliance - Excel files often have mixed formats"""
        try:
            from format_validator import UniversalFormatValidator
            
            if df.empty:
                return 70  # Higher neutral score
            
            validator = UniversalFormatValidator()
            _, violations = validator.validate_dataframe(df)
            
            if not violations:
                return 100
            
            # Much more forgiving scoring for format violations
            total_format_violations = 0
            total_format_cells = 0
            
            for col, info in violations.items():
                violation_count = len(info['violations'])
                total_format_violations += violation_count
                total_format_cells += df[col].notna().sum()
            
            if total_format_cells == 0:
                return 70
            
            violation_ratio = total_format_violations / total_format_cells
            # Much more forgiving: even 50% violations = 60 score
            score = max(40, 100 - (violation_ratio * 60))
            return score
        except:
            return 80  # Higher default score
    
    def _analyze_business_logic_realistic(self, df: pd.DataFrame) -> float:
        """More forgiving business logic analysis"""
        if df.empty or len(df) < 2:
            return 75  # Higher neutral score
            
        score = 90.0  # Start high - business logic is hard to assess
        
        # Only penalize extreme outliers
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            values = df[col].dropna()
            if len(values) > 1:
                try:
                    q1, q3 = values.quantile([0.25, 0.75])
                    iqr = q3 - q1
                    if iqr > 0:
                        # More lenient outlier detection (5 IQRs instead of 3)
                        outliers = ((values < (q1 - 5 * iqr)) | (values > (q3 + 5 * iqr))).sum()
                        outlier_ratio = outliers / len(values)
                        if outlier_ratio > 0.2:  # Only penalize if more than 20% outliers
                            score -= min(outlier_ratio * 20, 10)
                except:
                    pass
        
        return max(60, score)
    
    def _analyze_header_quality_realistic(self, df: pd.DataFrame, header_detected: bool) -> float:
        """Realistic header quality analysis"""
        score = 85.0  # Start reasonably high
        
        if not header_detected:
            score -= 15  # Reduced penalty
        
        # More forgiving generic column names assessment
        generic_names = sum(1 for col in df.columns if 
                          'Unnamed' in str(col) or 
                          'Column_' in str(col) or
                          pd.isna(col) or
                          str(col).strip() == '')
        
        if len(df.columns) > 0:
            generic_ratio = generic_names / len(df.columns)
            # Only penalize if more than 50% generic names
            if generic_ratio > 0.5:
                score -= generic_ratio * 30
            elif generic_ratio > 0.3:
                score -= generic_ratio * 15
        
        return max(50, score)
    
    def _is_number(self, value) -> bool:
        """Check if a value is numeric"""
        try:
            float(str(value).replace(',', '').replace('$', '').replace('€', '').replace('£', ''))
            return True
        except:
            return False
    
    def _is_date(self, value) -> bool:
        """Check if a value looks like a date"""
        try:
            date_patterns = [
                r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
                r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
                r'\w+ \d{1,2}, \d{4}'
            ]
            val_str = str(value)
            return any(re.search(pattern, val_str) for pattern in date_patterns)
        except:
            return False
    
    def _identify_realistic_issues(self, scores: Dict) -> List[str]:
        """Identify issues with more realistic thresholds"""
        issues = []
        
        if scores['structural_integrity'] < 50:
            issues.append("Poor data structure - consider reviewing the data layout")
        
        if scores['data_completeness'] < 40:
            issues.append("Significant missing data - may need data collection improvements")
        
        if scores['data_consistency'] < 60:
            issues.append("Some data type inconsistencies - can be addressed during cleaning")
        
        if scores['data_uniqueness'] < 50:
            issues.append("High level of duplicate data - review if duplicates are intentional")
        
        if scores['format_compliance'] < 30:
            issues.append("Some format standardization opportunities available")
        
        if scores['business_logic'] < 60:
            issues.append("Minor data validation points to consider")
        
        if scores['header_quality'] < 50:
            issues.append("Header quality could be improved")
        
        return issues
    
    def _generate_realistic_stats(self, df: pd.DataFrame) -> Dict[str, str]:
        """Generate realistic statistics"""
        if df.empty:
            return {"status": "Empty dataset"}
        
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        duplicate_rows = df.duplicated().sum()
        empty_cols = df.isnull().all().sum()
        
        # Count different data types
        numeric_cols = len(df.select_dtypes(include=[np.number]).columns)
        text_cols = len(df.select_dtypes(include=['object']).columns)
        datetime_cols = len(df.select_dtypes(include=['datetime']).columns)
        
        return {
            'shape': f"{df.shape[0]} rows × {df.shape[1]} columns",
            'missing_data': f"{missing_cells:,}/{total_cells:,} cells ({missing_cells/total_cells*100:.1f}%)",
            'duplicate_rows': f"{duplicate_rows:,}/{len(df):,} rows ({duplicate_rows/len(df)*100:.1f}%)",
            'empty_columns': f"{empty_cols}/{len(df.columns)} columns",
            'data_types': f"Numeric: {numeric_cols}, Text: {text_cols}, DateTime: {datetime_cols}",
            'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024**2:.1f} MB"
        }
    
    def generate_cleanup_suggestions(self, details: Dict) -> List[str]:
        """Generate realistic cleanup suggestions"""
        suggestions = []
        scores = details['scores']
        
        if scores['structural_integrity'] < 60:
            suggestions.append("Consider reviewing data structure and removing any unnecessary empty sections")
        
        if scores['data_completeness'] < 50:
            suggestions.append("Address missing values where appropriate - consider data collection or imputation")
        
        if scores['data_consistency'] < 70:
            suggestions.append("Some data type standardization could improve consistency")
        
        if scores['data_uniqueness'] < 60:
            suggestions.append("Review duplicate records to determine if they should be removed or are intentional")
        
        if scores['format_compliance'] < 50:
            suggestions.append("Consider standardizing date and numeric formats for better consistency")
        
        if scores['business_logic'] < 70:
            suggestions.append("Review data for any obvious outliers or inconsistencies")
        
        if scores['header_quality'] < 60:
            suggestions.append("Consider improving column headers for better clarity")
        
        return suggestions

# Compatibility functions for existing code using the realistic scorer
def calculate_quality_score(df: pd.DataFrame) -> float:
    """Wrapper function for backward compatibility using realistic scoring"""
    scorer = RealisticDataQualityScorer()
    score, _, _ = scorer.calculate_score(df)
    return float(score)

def get_quality_report(df: pd.DataFrame) -> Dict:
    """Generate quality report with realistic scoring"""
    scorer = RealisticDataQualityScorer()
    score, details, recommendation = scorer.calculate_score(df)
    
    return {
        'score': score,
        'quality_level': details['quality_level'],
        'issues': details['issues'],
        'suggestions': scorer.generate_cleanup_suggestions(details),
        'stats': details['stats'],
        'recommendation': recommendation,
        'detailed_scores': details['scores']
    }

# Keep the old class for backward compatibility but use realistic scorer
AdvancedDataQualityScorer = RealisticDataQualityScorer