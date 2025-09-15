"""
Format Validators for Indian and International Standard Formats
Detects and validates common standardized formats without removing data
"""

import re
from typing import List, Dict, Tuple, Optional
import pandas as pd

class FormatValidator:
    """Validates standardized formats and flags mismatches"""
    
    # Indian Format Patterns
    PATTERNS = {
        'PAN_CARD': {
            'pattern': r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
            'description': 'Indian PAN Card (ABCDE1234F)',
            'example': 'ABCDE1234F'
        },
        'AADHAAR': {
            'pattern': r'^\d{4}\s?\d{4}\s?\d{4}$',
            'description': 'Indian Aadhaar (12 digits)',
            'example': '1234 5678 9012'
        },
        'GST_NUMBER': {
            'pattern': r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$',
            'description': 'Indian GST Number',
            'example': '29ABCDE1234F1Z5'
        },
        'INDIAN_MOBILE': {
            'pattern': r'^(\+91[\-\s]?)?[6-9]\d{9}$',
            'description': 'Indian Mobile Number',
            'example': '+91-9876543210'
        },
        'PINCODE': {
            'pattern': r'^[1-9][0-9]{5}$',
            'description': 'Indian Pincode (6 digits)',
            'example': '560001'
        },
        'IFSC_CODE': {
            'pattern': r'^[A-Z]{4}0[A-Z0-9]{6}$',
            'description': 'Bank IFSC Code',
            'example': 'SBIN0001234'
        },
        'VEHICLE_NUMBER': {
            'pattern': r'^[A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,2}[\s\-]?\d{1,4}$',
            'description': 'Indian Vehicle Number',
            'example': 'KA 01 AB 1234'
        },
        
        # International Formats
        'EMAIL': {
            'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'description': 'Email Address',
            'example': 'user@example.com'
        },
        'US_SSN': {
            'pattern': r'^\d{3}-?\d{2}-?\d{4}$',
            'description': 'US Social Security Number',
            'example': '123-45-6789'
        },
        'US_PHONE': {
            'pattern': r'^(\+1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}$',
            'description': 'US Phone Number',
            'example': '+1 (555) 123-4567'
        },
        'UK_POSTCODE': {
            'pattern': r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$',
            'description': 'UK Postcode',
            'example': 'SW1A 1AA'
        },
        'PASSPORT': {
            'pattern': r'^[A-Z][0-9]{7}$',
            'description': 'Indian Passport Number',
            'example': 'A1234567'
        },
        'DATE_YYYY_MM_DD': {
            'pattern': r'^\d{4}[-/]\d{2}[-/]\d{2}$',
            'description': 'Date (YYYY-MM-DD)',
            'example': '2024-01-15'
        },
        'DATE_DD_MM_YYYY': {
            'pattern': r'^\d{2}[-/]\d{2}[-/]\d{4}$',
            'description': 'Date (DD-MM-YYYY)',
            'example': '15-01-2024'
        },
        'CREDIT_CARD': {
            'pattern': r'^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$',
            'description': 'Credit Card Number',
            'example': '1234 5678 9012 3456'
        },
        'ISBN': {
            'pattern': r'^(97[89])?\d{9}(\d|X)$',
            'description': 'ISBN Number',
            'example': '9781234567890'
        },
        'IPV4': {
            'pattern': r'^(\d{1,3}\.){3}\d{1,3}$',
            'description': 'IPv4 Address',
            'example': '192.168.1.1'
        },
        'PERCENTAGE': {
            'pattern': r'^\d{1,3}(\.\d{1,2})?%?$',
            'description': 'Percentage Value',
            'example': '85.50%'
        },
        'CURRENCY_INR': {
            'pattern': r'^₹?\s?\d{1,3}(,\d{3})*(\.\d{2})?$',
            'description': 'Indian Rupee Amount',
            'example': '₹ 1,234.56'
        },
        'CURRENCY_USD': {
            'pattern': r'^\$?\s?\d{1,3}(,\d{3})*(\.\d{2})?$',
            'description': 'US Dollar Amount',
            'example': '$1,234.56'
        }
    }
    
    @classmethod
    def detect_format(cls, values: pd.Series) -> Optional[Dict]:
        """
        Detect the format pattern in a series of values
        Returns the detected format and validation results
        """
        if values.empty or values.dropna().empty:
            return None
        
        # Clean and prepare values, keeping track of original indices
        original_values = values.copy()
        clean_values = values.dropna().astype(str).str.strip()
        if clean_values.empty:
            return None
        
        # Sample values for testing (up to 100)
        sample_values = clean_values.head(100)
        
        best_match = None
        best_match_rate = 0
        
        # Test each pattern
        for format_name, format_info in cls.PATTERNS.items():
            pattern = format_info['pattern']
            matches = sample_values.str.match(pattern, case=False)
            match_rate = matches.sum() / len(matches) if len(matches) > 0 else 0
            
            # If more than 60% match, consider it a potential format
            if match_rate > 0.6 and match_rate > best_match_rate:
                best_match = format_name
                best_match_rate = match_rate
        
        if best_match:
            # Validate all values and get exact indices
            pattern = cls.PATTERNS[best_match]['pattern']
            
            # Create a boolean mask for all original values (including NaN)
            all_matches = pd.Series([False] * len(original_values), index=original_values.index)
            
            # Check each non-null value
            for idx, val in clean_values.items():
                import re
                if re.match(pattern, str(val), re.IGNORECASE):
                    all_matches.loc[idx] = True
            
            # Get mismatched indices and values
            mismatched_mask = (~all_matches) & (original_values.notna())
            mismatched_indices = mismatched_mask[mismatched_mask].index.tolist()
            mismatched_values = original_values[mismatched_mask].astype(str).tolist()
            
            return {
                'format_detected': best_match,
                'format_description': cls.PATTERNS[best_match]['description'],
                'format_example': cls.PATTERNS[best_match]['example'],
                'total_values': len(clean_values),
                'matching_values': all_matches.sum(),
                'mismatched_values': len(mismatched_indices),
                'match_percentage': (all_matches.sum() / len(clean_values)) * 100 if len(clean_values) > 0 else 0,
                'mismatched_indices': mismatched_indices,
                'mismatched_samples': mismatched_values[:10]
            }
        
        return None
    
    @classmethod
    def validate_column(cls, series: pd.Series, expected_format: str) -> Dict:
        """
        Validate a column against a specific expected format
        """
        if expected_format not in cls.PATTERNS:
            return {
                'error': f'Unknown format: {expected_format}',
                'valid': False
            }
        
        clean_values = series.dropna().astype(str).str.strip()
        if clean_values.empty:
            return {
                'valid': True,
                'message': 'No values to validate (all null)'
            }
        
        pattern = cls.PATTERNS[expected_format]['pattern']
        matches = clean_values.str.match(pattern, case=False)
        
        return {
            'format': expected_format,
            'format_description': cls.PATTERNS[expected_format]['description'],
            'total_values': len(clean_values),
            'valid_values': matches.sum(),
            'invalid_values': (~matches).sum(),
            'validity_percentage': (matches.sum() / len(matches)) * 100,
            'invalid_indices': clean_values[~matches].index.tolist(),
            'invalid_samples': clean_values[~matches].head(10).tolist(),
            'valid': matches.all()
        }
    
    @classmethod
    def analyze_dataframe(cls, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Analyze all columns in a dataframe for format patterns
        Returns format validation results for each column
        """
        results = {}
        
        for col in df.columns:
            format_result = cls.detect_format(df[col])
            if format_result:
                results[col] = format_result
        
        return results
    
    @classmethod
    def get_format_suggestions(cls, value: str) -> List[str]:
        """
        Suggest corrections for a mismatched value based on detected format
        """
        suggestions = []
        
        # Remove common issues
        cleaned = value.strip().upper()
        
        # Check which formats it's close to
        for format_name, format_info in cls.PATTERNS.items():
            if format_name == 'PAN_CARD':
                # Check if it's close to PAN format
                if len(cleaned) == 10 and cleaned[:5].isalpha() and cleaned[5:9].isdigit():
                    suggestions.append(f"Possible PAN: {cleaned[:5]}{cleaned[5:9]}{cleaned[9]}")
            
            elif format_name == 'AADHAAR':
                # Check if it's close to Aadhaar
                digits_only = re.sub(r'\D', '', value)
                if len(digits_only) == 12:
                    formatted = f"{digits_only[:4]} {digits_only[4:8]} {digits_only[8:]}"
                    suggestions.append(f"Possible Aadhaar: {formatted}")
            
            elif format_name == 'INDIAN_MOBILE':
                digits_only = re.sub(r'\D', '', value)
                if len(digits_only) == 10 and digits_only[0] in '6789':
                    suggestions.append(f"Possible Mobile: +91-{digits_only}")
                elif len(digits_only) == 12 and digits_only[:2] == '91':
                    suggestions.append(f"Possible Mobile: +91-{digits_only[2:]}")
        
        return suggestions


def validate_and_flag_formats(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Validate formats in dataframe and return flagged issues
    Does NOT modify the original data, only flags issues
    """
    validator = FormatValidator()
    format_results = validator.analyze_dataframe(df)
    
    flags = []
    
    for col, result in format_results.items():
        if result['mismatched_values'] > 0:
            flag = {
                'column': col,
                'issue_type': 'FORMAT_MISMATCH',
                'severity': 'HIGH' if result['match_percentage'] < 80 else 'MEDIUM',
                'format_detected': result['format_detected'],
                'format_description': result['format_description'],
                'total_values': result['total_values'],
                'mismatched_count': result['mismatched_values'],
                'match_percentage': round(result['match_percentage'], 2),
                'sample_mismatches': result['mismatched_samples'][:5],
                'recommendation': f"Column '{col}' appears to contain {result['format_description']} "
                                f"but {result['mismatched_values']} values don't match the expected format. "
                                f"Review these values for data entry errors."
            }
            flags.append(flag)
    
    return df, flags