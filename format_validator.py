"""
Universal Format Validator and Highlighter
Validates and highlights cells that don't match universal formats
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class UniversalFormatValidator:
    """Validates data against universal format standards"""
    
    def __init__(self):
        # Define universal format patterns
        self.formats = {
            'date': {
                'pattern': r'^\d{2}/\d{2}/\d{4}$',  # DD/MM/YYYY
                'description': 'DD/MM/YYYY',
                'example': '25/12/2024'
            },
            'pan': {
                'pattern': r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',  # PAN Card
                'description': 'AAAAA9999A',
                'example': 'ABCDE1234F'
            },
            'gst': {
                'pattern': r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9]{1}[Z]{1}[0-9A-Z]{1}$',  # GST Number
                'description': '99AAAAA9999A9Z9',
                'example': '27AABCU9603R1ZP'
            },
            'phone': {
                'pattern': r'^(\+91[-\s]?)?[6-9]\d{9}$',  # Indian Phone
                'description': '+91-9999999999 or 9999999999',
                'example': '+91-9876543210'
            },
            'email': {
                'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'description': 'email@domain.com',
                'example': 'user@example.com'
            },
            'pincode': {
                'pattern': r'^\d{6}$',  # Indian Pincode
                'description': '6 digits',
                'example': '110001'
            },
            'aadhaar': {
                'pattern': r'^\d{4}\s?\d{4}\s?\d{4}$',  # Aadhaar (masked)
                'description': 'XXXX XXXX XXXX',
                'example': '1234 5678 9012'
            },
            'ifsc': {
                'pattern': r'^[A-Z]{4}0[A-Z0-9]{6}$',  # IFSC Code
                'description': 'AAAA0999999',
                'example': 'SBIN0001234'
            },
            'vehicle': {
                'pattern': r'^[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,2}[\s-]?\d{4}$',  # Vehicle Number
                'description': 'AA 99 AA 9999',
                'example': 'DL 01 AB 1234'
            },
            'percentage': {
                'pattern': r'^\d{1,3}(\.\d{1,2})?%?$',  # Percentage
                'description': '0-100 with optional decimal',
                'example': '18.5%'
            },
            'currency_inr': {
                'pattern': r'^₹?\s?\d{1,3}(,\d{3})*(\.\d{2})?$',  # Indian Currency
                'description': '₹ 1,234.56',
                'example': '₹ 12,345.67'
            }
        }
    
    def detect_column_format(self, series: pd.Series, column_name: str) -> str:
        """
        Detect the format type of a column based on its name and content
        """
        col_lower = str(column_name).lower()
        
        # Check column name for hints
        if any(word in col_lower for word in ['date', 'dt', 'day', 'month', 'year']):
            return 'date'
        elif any(word in col_lower for word in ['pan', 'pan_card', 'pancard']):
            return 'pan'
        elif any(word in col_lower for word in ['gst', 'gstin', 'gst_no', 'gst_number']):
            return 'gst'
        elif any(word in col_lower for word in ['phone', 'mobile', 'contact', 'tel']):
            return 'phone'
        elif any(word in col_lower for word in ['email', 'mail', 'e-mail']):
            return 'email'
        elif any(word in col_lower for word in ['pin', 'pincode', 'zip', 'postal']):
            return 'pincode'
        elif any(word in col_lower for word in ['aadhaar', 'aadhar', 'uid']):
            return 'aadhaar'
        elif any(word in col_lower for word in ['ifsc', 'bank_code']):
            return 'ifsc'
        elif any(word in col_lower for word in ['vehicle', 'registration', 'reg_no']):
            return 'vehicle'
        elif any(word in col_lower for word in ['percent', 'percentage', 'rate']):
            return 'percentage'
        elif any(word in col_lower for word in ['amount', 'price', 'cost', 'total', 'sum']):
            return 'currency_inr'
        
        # Try to detect based on content
        sample = series.dropna().head(20).astype(str)
        if len(sample) > 0:
            # Check for date patterns
            if sum(1 for val in sample if re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', val)) > len(sample) * 0.5:
                return 'date'
            # Check for GST pattern
            elif sum(1 for val in sample if re.match(r'^[0-9]{2}[A-Z]{5}', val)) > len(sample) * 0.3:
                return 'gst'
            # Check for PAN pattern
            elif sum(1 for val in sample if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', val)) > len(sample) * 0.3:
                return 'pan'
            # Check for phone pattern
            elif sum(1 for val in sample if re.match(r'^[6-9]\d{9}', val.replace(' ', '').replace('-', ''))) > len(sample) * 0.3:
                return 'phone'
            # Check for email pattern
            elif sum(1 for val in sample if '@' in val and '.' in val) > len(sample) * 0.3:
                return 'email'
        
        return None
    
    def validate_format(self, value: Any, format_type: str) -> bool:
        """
        Validate if a value matches the specified format
        """
        if pd.isna(value) or value == '':
            return True  # Allow empty values
        
        value_str = str(value).strip()
        
        if format_type not in self.formats:
            return True
        
        pattern = self.formats[format_type]['pattern']
        
        # Special handling for dates
        if format_type == 'date':
            # Also check if it's a valid date
            try:
                if re.match(pattern, value_str):
                    day, month, year = value_str.split('/')
                    day, month, year = int(day), int(month), int(year)
                    if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                        return True
            except:
                pass
            return False
        
        return bool(re.match(pattern, value_str))
    
    def standardize_value(self, value: Any, format_type: str) -> str:
        """
        Attempt to standardize a value to match the universal format
        """
        if pd.isna(value) or value == '':
            return value
        
        value_str = str(value).strip()
        
        if format_type == 'date':
            # Try to convert various date formats to DD/MM/YYYY
            # Common patterns: DD-MM-YY, MM/DD/YYYY, YYYY-MM-DD, etc.
            patterns = [
                (r'^(\d{1,2})-(\d{1,2})-(\d{2})$', lambda m: f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/20{m.group(3)}"),
                (r'^(\d{1,2})/(\d{1,2})/(\d{2})$', lambda m: f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/20{m.group(3)}"),
                (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', lambda m: f"{m.group(3).zfill(2)}/{m.group(2).zfill(2)}/{m.group(1)}"),
                (r'^(\d{1,2})-(\d{1,2})-(\d{4})$', lambda m: f"{m.group(1).zfill(2)}/{m.group(2).zfill(2)}/{m.group(3)}"),
            ]
            for pattern, formatter in patterns:
                match = re.match(pattern, value_str)
                if match:
                    return formatter(match)
        
        elif format_type == 'phone':
            # Remove spaces and dashes
            phone = re.sub(r'[\s-]', '', value_str)
            # Add +91 if not present
            if len(phone) == 10 and phone[0] in '6789':
                return f"+91-{phone}"
            elif phone.startswith('91') and len(phone) == 12:
                return f"+91-{phone[2:]}"
            elif phone.startswith('+91'):
                return f"+91-{phone[3:]}"
        
        elif format_type == 'gst':
            # Uppercase GST number
            return value_str.upper()
        
        elif format_type == 'pan':
            # Uppercase PAN
            return value_str.upper()
        
        elif format_type == 'currency_inr':
            # Add ₹ symbol and format with commas
            try:
                # Remove existing currency symbols and commas
                num_str = re.sub(r'[₹$,]', '', value_str).strip()
                num = float(num_str)
                # Format with Indian number system
                return f"₹ {num:,.2f}"
            except:
                pass
        
        elif format_type == 'percentage':
            # Ensure % symbol
            if not value_str.endswith('%'):
                try:
                    num = float(value_str)
                    return f"{num}%"
                except:
                    pass
        
        return value_str
    
    def validate_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, List[Tuple[int, str]]]]:
        """
        Validate entire dataframe and return validation results
        Returns: (df, violations_dict)
        violations_dict: {column_name: [(row_index, invalid_value), ...]}
        """
        violations = {}
        
        for col in df.columns:
            format_type = self.detect_column_format(df[col], col)
            if format_type:
                col_violations = []
                for idx, value in df[col].items():
                    if not self.validate_format(value, format_type):
                        col_violations.append((idx, str(value)))
                
                if col_violations:
                    violations[str(col)] = {
                        'format_type': format_type,
                        'format_description': self.formats[format_type]['description'],
                        'violations': col_violations
                    }
        
        return df, violations
    
    def auto_standardize_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Automatically standardize formats in dataframe
        Returns: (standardized_df, changes_log)
        """
        df_copy = df.copy()
        changes_log = []
        
        for col in df_copy.columns:
            format_type = self.detect_column_format(df_copy[col], col)
            if format_type:
                original_invalid = 0
                standardized = 0
                
                for idx in df_copy.index:
                    value = df_copy.at[idx, col]
                    if not self.validate_format(value, format_type):
                        original_invalid += 1
                        new_value = self.standardize_value(value, format_type)
                        if self.validate_format(new_value, format_type):
                            df_copy.at[idx, col] = new_value
                            standardized += 1
                
                if standardized > 0:
                    changes_log.append(f"Column '{col}': Standardized {standardized}/{original_invalid} values to {self.formats[format_type]['description']} format")
        
        return df_copy, changes_log

def highlight_format_violations(df: pd.DataFrame, violations: Dict[str, Any]) -> pd.DataFrame:
    """
    Create a styled dataframe with red highlighting for format violations
    """
    def style_violations(val, row_idx, col_name):
        """Style function for individual cells"""
        if col_name in violations:
            violation_rows = [v[0] for v in violations[col_name]['violations']]
            if row_idx in violation_rows:
                return 'background-color: #ffcccc; color: #cc0000; font-weight: bold'
        return ''
    
    # Create style dataframe
    styled = df.style
    
    for col in df.columns:
        col_str = str(col)
        if col_str in violations:
            violation_indices = [v[0] for v in violations[col_str]['violations']]
            styled = styled.apply(
                lambda x: [style_violations(val, idx, col_str) for idx, val in enumerate(x)],
                subset=[col]
            )
    
    return styled