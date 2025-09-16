"""
Code Generator LLM Module
Generates and validates Python code for data cleaning operations
"""

import pandas as pd
import numpy as np
import json
import re
from typing import Dict, Any, Optional
from ai_service import make_ai_call, get_ai_service
import logging

logger = logging.getLogger(__name__)

class CodeGeneratorLLM:
    """
    LLM for generating executable Python code for data cleaning
    """
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.max_retries = 3
        
    def generate_code(self, df: pd.DataFrame, task: str, context: Dict[str, Any] = None) -> str:
        """
        Generate Python code for a specific cleaning task
        
        Args:
            df: The dataframe to clean
            task: Description of the cleaning task
            context: Additional context about the data
            
        Returns:
            Executable Python code string
        """
        if not self.ai_service.is_available():
            logger.error("AI service not available")
            return self._get_fallback_code(df, task)
        
        # Prepare the prompt
        prompt = self._create_code_prompt(df, task, context)
        
        try:
            response = make_ai_call(prompt, max_tokens=800)
            if response:
                # Extract code from response
                code = self._extract_code(response)
                # Validate code
                if self._validate_code(code, df):
                    return code
                else:
                    # Try to fix the code
                    return self._fix_code(code, df, task)
            else:
                return self._get_fallback_code(df, task)
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            return self._get_fallback_code(df, task)
    
    def _create_code_prompt(self, df: pd.DataFrame, task: str, context: Dict[str, Any] = None) -> str:
        """Create a detailed prompt for code generation"""
        
        # Convert numpy types to Python native types
        def convert_to_native(obj):
            import numpy as np
            import pandas as pd
            if isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif pd.isna(obj):
                return None
            elif isinstance(obj, dict):
                return {k: convert_to_native(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_native(item) for item in obj]
            else:
                return str(obj)
        
        # Get DataFrame info with proper type conversion
        sample_records = []
        for _, row in df.head(3).iterrows():
            record = {}
            for col in df.columns:
                record[str(col)] = convert_to_native(row[col])
            sample_records.append(record)
        
        null_counts = {}
        for col in df.columns:
            null_counts[str(col)] = int(df[col].isnull().sum())
        
        df_info = {
            'shape': [int(df.shape[0]), int(df.shape[1])],
            'columns': [str(col) for col in df.columns],
            'dtypes': {str(col): str(dtype) for col, dtype in df.dtypes.items()},
            'sample': sample_records,
            'null_counts': null_counts
        }
        
        prompt = f"""You are an expert Python data analyst. Generate clean, efficient pandas code for the following task.

TASK: {task}

DataFrame Information:
- Shape: {df_info['shape']}
- Columns: {df_info['columns']}
- Data Types: {json.dumps(df_info['dtypes'], indent=2, default=str)}
- Null Counts: {json.dumps(df_info['null_counts'], indent=2, default=str)}

Sample Data (first 3 rows):
{json.dumps(df_info['sample'], indent=2, default=str)}

"""
        
        if context:
            # Convert context to ensure it's serializable
            context_safe = {}
            for key, value in context.items():
                if key == 'dtypes' and isinstance(value, dict):
                    context_safe[key] = {str(k): str(v) for k, v in value.items()}
                elif isinstance(value, (list, tuple)):
                    context_safe[key] = [str(item) for item in value]
                else:
                    context_safe[key] = str(value) if value is not None else None
            
            prompt += f"""Additional Context:
{json.dumps(context_safe, indent=2, default=str)}

"""
        
        prompt += """CRITICAL REQUIREMENTS - ZERO TOLERANCE DATA PRESERVATION:
1. The code must work with a DataFrame variable named 'df'
2. The code must return the modified DataFrame as 'df'
3. Use only pandas, numpy, and re libraries (already imported)
4. Handle edge cases and errors gracefully
5. Add data validation where appropriate
6. Preserve data types where possible

🚨 ABSOLUTE PROHIBITION - NEVER USE THESE OPERATIONS:
- df.drop() - NO row/column removal
- df.dropna() - NO missing value removal  
- df.drop_duplicates() - NO duplicate removal
- df[condition] filtering that removes rows
- .iloc[] or .loc[] operations that reduce size
- ANY operation that reduces df.shape

✅ ALLOWED OPERATIONS ONLY:
- Value modifications (df[col] = new_values)
- Type conversions (pd.to_numeric, pd.to_datetime)
- String operations (.strip(), .replace(), etc.)
- Column renaming (df.columns = new_names)
- Data filling (df.fillna())
- Adding calculated columns

Generate ONLY the Python code, no explanations. The code should be complete and executable.

Example format:
```python
# Task: Clean string data (ZERO TOLERANCE: preserves all data)
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
```

Now generate ZERO TOLERANCE code for the given task:"""
        
        return prompt
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from LLM response"""
        # Try to find code blocks
        code_pattern = r'```python\n(.*?)```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # Try to find code without markers
        code_pattern = r'```\n(.*?)```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()
        
        # If no code blocks, assume entire response is code
        # Remove common non-code lines
        lines = response.split('\n')
        code_lines = []
        for line in lines:
            # Skip obvious non-code lines
            if not line.strip():
                continue
            if line.strip().startswith('#'):
                code_lines.append(line)
            elif any(keyword in line for keyword in ['df', 'pd.', 'np.', '=', '(', ')', '[', ']']):
                code_lines.append(line)
        
        return '\n'.join(code_lines)
    
    def _validate_code(self, code: str, df: pd.DataFrame) -> bool:
        """Validate that the code is executable"""
        try:
            # Create a test environment
            test_df = df.copy()
            local_vars = {
                'df': test_df,
                'pd': pd,
                'np': np,
                're': re
            }
            
            # Try to execute the code
            exec(code, {}, local_vars)
            
            # Check if df was modified and is still valid
            result_df = local_vars.get('df')
            if result_df is not None and isinstance(result_df, pd.DataFrame):
                return True
            
            return False
        except Exception as e:
            logger.warning(f"Code validation failed: {str(e)}")
            return False
    
    def _fix_code(self, code: str, df: pd.DataFrame, task: str) -> str:
        """Attempt to fix broken code"""
        # Try common fixes
        fixes = [
            # Add df assignment if missing
            (r'^(?!df\s*=)', 'df = '),
            # Fix column name issues
            (r"df\['([^']+)'\]", lambda m: f"df['{m.group(1)}']" if m.group(1) in df.columns else f"df[df.columns[0]]"),
            # Fix method chaining
            (r'\.(\w+)\(\)\.', r'.\1().'),
        ]
        
        fixed_code = code
        for pattern, replacement in fixes:
            if callable(replacement):
                fixed_code = re.sub(pattern, replacement, fixed_code)
            else:
                fixed_code = re.sub(pattern, replacement, fixed_code)
        
        # Validate the fixed code
        if self._validate_code(fixed_code, df):
            return fixed_code
        
        # If fixes didn't work, generate new code with more specific instructions
        retry_prompt = f"""The following code failed to execute:
```python
{code}
```

Task: {task}

Generate a corrected version that:
1. Uses proper pandas syntax
2. Handles the DataFrame 'df' correctly
3. Returns the modified DataFrame as 'df'
4. Works with these columns: {list(df.columns)[:10]}

Provide ONLY the corrected Python code:"""
        
        try:
            response = make_ai_call(retry_prompt, max_tokens=600)
            if response:
                new_code = self._extract_code(response)
                if self._validate_code(new_code, df):
                    return new_code
        except:
            pass
        
        # If all else fails, return fallback code
        return self._get_fallback_code(df, task)
    
    def _get_fallback_code(self, df: pd.DataFrame, task: str) -> str:
        """Generate ZERO TOLERANCE fallback code - NO DATA REMOVAL ALLOWED"""
        task_lower = task.lower()
        
        # ZERO TOLERANCE: All operations must preserve data
        if 'duplicate' in task_lower:
            # NO duplicate removal - only mark them
            return "# ZERO TOLERANCE: No duplicate removal allowed\n# Duplicates identified but preserved\npass"
        
        elif 'trim' in task_lower or 'whitespace' in task_lower:
            # Safe: Only modifies values, doesn't remove data
            code = """# Trim whitespace from string columns (ZERO TOLERANCE: preserves all data)
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)"""
            return code
        
        elif 'missing' in task_lower or 'null' in task_lower:
            if 'drop' in task_lower:
                # NO dropping allowed
                return "# ZERO TOLERANCE: No data removal allowed\n# Missing values identified but preserved\npass"
            elif 'fill' in task_lower:
                # Safe: Fills missing values without removing data
                return "df = df.fillna('')  # ZERO TOLERANCE: Fill with empty string, no removal"
            else:
                return "# ZERO TOLERANCE: Identify missing values only\nmissing_mask = df.isnull()"
        
        elif 'convert' in task_lower and 'numeric' in task_lower:
            # Safe: Only converts types, doesn't remove data
            code = """# Convert to numeric where possible (ZERO TOLERANCE: preserves all data)
for col in df.select_dtypes(include=['object']).columns:
    try:
        df[col] = pd.to_numeric(df[col], errors='ignore')
    except:
        pass"""
            return code
        
        elif 'date' in task_lower or 'datetime' in task_lower:
            # Safe: Only converts types, doesn't remove data
            code = """# Convert to datetime (ZERO TOLERANCE: preserves all data)
for col in df.select_dtypes(include=['object']).columns:
    try:
        # Try to parse as datetime
        temp = pd.to_datetime(df[col], errors='coerce')
        if temp.notna().sum() > len(df) * 0.5:  # If more than 50% parsed successfully
            df[col] = temp
    except:
        pass"""
            return code
        
        elif 'lowercase' in task_lower or 'uppercase' in task_lower or 'case' in task_lower:
            if 'lower' in task_lower:
                operation = 'lower'
            elif 'upper' in task_lower:
                operation = 'upper'
            else:
                operation = 'title'
            
            code = f"""# Standardize text case
for col in df.select_dtypes(include=['object']).columns:
    df[col] = df[col].apply(lambda x: x.{operation}() if isinstance(x, str) else x)"""
            return code
        
        elif 'column' in task_lower and 'drop' in task_lower:
            # NO column dropping allowed
            return "# ZERO TOLERANCE: No column removal allowed\n# Empty columns identified but preserved\npass"
        
        elif 'rename' in task_lower:
            # Safe: Only renames, doesn't remove data
            return "# Rename columns (ZERO TOLERANCE: preserves all data)\ndf.columns = [str(col).strip().replace(' ', '_').lower() for col in df.columns]"
        
        elif 'outlier' in task_lower:
            # NO outlier removal - only identify
            code = """# ZERO TOLERANCE: Identify outliers but do not remove
numeric_cols = df.select_dtypes(include=[np.number]).columns
for col in numeric_cols:
    try:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        # Outliers identified but preserved (ZERO TOLERANCE)
        pass
    except:
        pass"""
            return code
        
        else:
            # Generic code that doesn't modify the dataframe
            return "# ZERO TOLERANCE: No modifications applied\n# df remains unchanged\npass"