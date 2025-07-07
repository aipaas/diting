"""
Service for importing test cases from external files.
Handles CSV and Excel file processing with validation and error handling.
"""

import pandas as pd
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FileImportService:
    """
    Service for importing test cases from CSV and Excel files.

    Provides functionality to parse, validate, and convert file data
    into LLMCase objects with proper error handling and data cleaning.
    """

    REQUIRED_COLUMNS = ["input", "actual_output"]
    OPTIONAL_COLUMNS = ["expected_output", "context", "retrieval_context", "tags"]

    async def process_dataframe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Process pandas DataFrame and convert to case data.

        Args:
            df: DataFrame containing case data

        Returns:
            List of dictionaries representing test cases

        Raises:
            ValueError: If required columns are missing or data is invalid
        """
        # Clean column names (remove whitespace, lowercase)
        df.columns = df.columns.str.strip().str.lower()  # type: ignore[misc]

        # Validate required columns
        missing_columns = [
            col for col in self.REQUIRED_COLUMNS if col not in df.columns
        ]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

        # Process each row
        cases: list[Dict[str, Any]] = []
        for index, row in df.iterrows():
            try:
                case_data = self._process_row(row, index)  # type: ignore[misc]
                if case_data:  # Skip None results (invalid rows)
                    cases.append(case_data)
            except Exception as e:
                logger.warning(f"Skipping row {index + 1}: {str(e)}")  # type: ignore[misc]
                continue

        if not cases:
            raise ValueError("No valid cases found in the file")

        logger.info(f"Successfully processed {len(cases)} cases from file")
        return cases

    def _process_row(self, row: pd.Series, row_index: int) -> Optional[Dict[str, Any]]:
        """
        Process a single row from the DataFrame.

        Args:
            row: Pandas Series representing a single row
            row_index: Index of the row for error reporting

        Returns:
            Dictionary representing a test case, or None if invalid

        Raises:
            ValueError: If row data is invalid
        """
        # Check required fields
        if pd.isna(row.get("input")) or not str(row.get("input")).strip():  # type: ignore[misc]
            raise ValueError("Input is required and cannot be empty")

        if (
            pd.isna(row.get("actual_output"))  # type: ignore
            or not str(row.get("actual_output")).strip()  # type: ignore
        ):
            raise ValueError("Actual output is required and cannot be empty")

        # Build case data
        case_data = {
            "input": str(row["input"]).strip(),  # type: ignore[misc]
            "actual_output": str(row["actual_output"]).strip(),  # type: ignore[misc]
        }

        # Process optional fields
        expected_output = row.get("expected_output")  # type: ignore[misc]
        if not pd.isna(expected_output) and str(expected_output).strip():  # type: ignore[misc]
            case_data["expected_output"] = str(expected_output).strip()  # type: ignore[misc]

        # Process list fields (context, retrieval_context, tags)
        for list_field in ["context", "retrieval_context", "tags"]:
            field_value = row.get(list_field)  # type: ignore[misc]
            if not pd.isna(field_value) and str(field_value).strip():  # type: ignore[misc]
                # Split by semicolon or comma and clean
                items = [
                    item.strip()
                    for item in str(field_value).split(";")
                    if item.strip()  # type: ignore[misc]
                ]
                if not items:
                    # Try splitting by comma if semicolon didn't work
                    items = [
                        item.strip()
                        for item in str(field_value).split(",")  # type: ignore[misc]
                        if item.strip()
                    ]

                if items:
                    case_data[list_field] = items  # type: ignore[misc]

        return case_data

    def get_sample_template(self) -> Dict[str, List[str]]:
        """
        Get a sample template for CSV/Excel import.

        Returns:
            Dictionary with sample data structure
        """
        return {
            "input": [
                "What is the capital of France?",
                "Explain quantum computing in simple terms",
            ],
            "actual_output": [
                "The capital of France is Paris.",
                "Quantum computing uses quantum bits or qubits...",
            ],
            "expected_output": [
                "Paris is the capital of France.",
                "Quantum computing is a type of computation...",
            ],
            "context": [
                "Geography question",
                "Technology explanation; Physics concept",
            ],
            "retrieval_context": [
                "France is a country in Europe",
                "Quantum mechanics; Computer science",
            ],
            "tags": ["geography; capitals", "technology; physics; explanation"],
        }
