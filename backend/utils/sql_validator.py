"""SQL validation and safety checks."""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class SQLValidator:
    """Validates SQL queries for safety."""
    
    def __init__(self):
        """Initialize SQL validator."""
        self.dangerous_keywords = [
            "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE",
            "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE"
        ]
    
    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """Validate SQL syntax and structure.
        
        Args:
            sql: SQL query string
            
        Returns:
            Validation result with valid flag and errors
        """
        errors = []
        
        # Basic syntax check
        if not sql or not sql.strip():
            return {
                "valid": False,
                "errors": ["Empty SQL query"]
            }
        
        sql_upper = sql.upper().strip()
        
        # Check for dangerous operations
        for keyword in self.dangerous_keywords:
            if re.search(rf'\b{keyword}\b', sql_upper):
                errors.append(f"Dangerous keyword detected: {keyword}")
        
        # Basic structure validation
        if not sql_upper.startswith("SELECT"):
            errors.append("Only SELECT queries are allowed")
        
        # Check for SQL injection patterns
        injection_patterns = [
            r"';.*--",
            r"';.*/\*",
            r"UNION.*SELECT",
            r"OR.*1.*=.*1",
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                errors.append(f"Potential SQL injection detected: {pattern}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "execution_plan": self._generate_execution_plan(sql) if len(errors) == 0 else {}
        }
    
    def check_allowlist(self, sql: str, allowlist: Dict[str, List[str]]) -> Dict[str, Any]:
        """Check if SQL only uses allowlisted tables and columns.
        
        Args:
            sql: SQL query
            allowlist: Dictionary mapping table names to allowed columns
            
        Returns:
            Allowlist check result
        """
        errors = []
        
        # Extract table names
        table_pattern = r'FROM\s+(\w+)'
        tables = re.findall(table_pattern, sql.upper())
        
        # Extract column names (simplified)
        column_pattern = r'SELECT\s+(.*?)\s+FROM'
        column_match = re.search(column_pattern, sql.upper())
        
        # Check tables
        for table in tables:
            if table not in allowlist:
                errors.append(f"Table '{table}' is not in allowlist")
        
        # Check columns (if allowlist specifies columns)
        if column_match:
            columns_str = column_match.group(1)
            if columns_str != "*":
                # Parse columns (simplified)
                columns = [col.strip() for col in columns_str.split(",")]
                for table in tables:
                    if table in allowlist:
                        allowed_cols = allowlist[table]
                        for col in columns:
                            if "." in col:
                                col = col.split(".")[-1]
                            if col not in allowed_cols and "*" not in allowed_cols:
                                errors.append(f"Column '{col}' is not allowed for table '{table}'")
        
        return {
            "allowed": len(errors) == 0,
            "errors": errors
        }
    
    def is_read_only(self, sql: str) -> bool:
        """Check if SQL is read-only.
        
        Args:
            sql: SQL query
            
        Returns:
            True if read-only
        """
        sql_upper = sql.upper().strip()
        
        # Check for write operations
        write_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"]
        
        for keyword in write_keywords:
            if re.search(rf'\b{keyword}\b', sql_upper):
                return False
        
        # Must start with SELECT
        return sql_upper.startswith("SELECT")
    
    def estimate_cost(self, sql: str) -> Dict[str, Any]:
        """Estimate query cost.
        
        Args:
            sql: SQL query
            
        Returns:
            Cost estimate
        """
        # Simple heuristics
        complexity = 1.0
        
        # Count joins
        join_count = len(re.findall(r'\bJOIN\b', sql.upper()))
        complexity += join_count * 0.5
        
        # Count subqueries
        subquery_count = sql.upper().count("SELECT") - 1
        complexity += subquery_count * 0.3
        
        # Estimate row limit (if specified)
        limit_match = re.search(r'LIMIT\s+(\d+)', sql.upper())
        row_limit = int(limit_match.group(1)) if limit_match else 1000
        
        return {
            "complexity": complexity,
            "estimated_rows": min(row_limit, 10000),  # Cap at 10k
            "cost_score": complexity * (row_limit / 1000)
        }
    
    def _generate_execution_plan(self, sql: str) -> Dict[str, Any]:
        """Generate execution plan (simplified).
        
        Args:
            sql: SQL query
            
        Returns:
            Execution plan
        """
        return {
            "tables": re.findall(r'FROM\s+(\w+)', sql.upper()),
            "joins": len(re.findall(r'\bJOIN\b', sql.upper())),
            "filters": len(re.findall(r'\bWHERE\b', sql.upper())),
            "order_by": "ORDER BY" in sql.upper(),
            "limit": bool(re.search(r'LIMIT\s+(\d+)', sql.upper()))
        }
