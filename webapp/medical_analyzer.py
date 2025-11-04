# ============================================================================
# PART 1: NEW IMPORTS (Add these at the top after existing imports)
# ============================================================================

# PDF Generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from datetime import datetime

# OCR for scanned images
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️  Warning: OCR libraries not installed. Scanned image support disabled.")
    print("   Install with: pip install pytesseract pillow opencv-python")

import json
import re
from typing import TypedDict, Literal, List, Optional
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from PyPDF2 import PdfReader
import pdfplumber
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize LLM
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

# --- State Definition ---
# ============================================================================
# PART 2: UPDATE GraphState (Replace existing GraphState)
# ============================================================================

class GraphState(TypedDict):
    pdf_path: str
    raw_text: str
    patient_info: dict
    document_type: Literal["tabular", "semi-structured", "unstructured", "error"]
    extracted_data: List[dict]
    validated_data: List[dict]
    validation_issues: List[str]
    summarized_report: str
    analyzed_results: List[dict]
    recommendations: str
    trends: List[dict]
    error: str
    is_scanned_image: bool  # NEW
    missing_ranges_explanation: dict  # NEW

# --- Test Name Mapping ---
TEST_NAME_MAPPING = {
    # Glucose variations
    "fasting blood sugar": "glucose",
    "fbs": "glucose",
    "blood glucose": "glucose",
    "fasting glucose": "glucose",
    "blood sugar": "glucose",
    
    # Hemoglobin variations
    "hb": "hemoglobin",
    "hgb": "hemoglobin",
    "haemoglobin": "hemoglobin",
    
    # WBC variations
    "white blood cell count": "wbc",
    "white blood cells": "wbc",
    "leucocytes": "wbc",
    "leukocytes": "wbc",
    
    # RBC variations
    "red blood cell count": "rbc",
    "red blood cells": "rbc",
    "erythrocytes": "rbc",
    
    # Cholesterol variations
    "total cholesterol": "cholesterol",
    "chol": "cholesterol",
    
    # HDL variations
    "hdl cholesterol": "hdl",
    "hdl-c": "hdl",
    "good cholesterol": "hdl",
    
    # LDL variations
    "ldl cholesterol": "ldl",
    "ldl-c": "ldl",
    "bad cholesterol": "ldl",
    
    # TSH variations
    "thyroid stimulating hormone": "tsh",
    "thyrotropin": "tsh",
    
    # HbA1c variations
    "glycated hemoglobin": "hba1c",
    "glycosylated hemoglobin": "hba1c",
    "a1c": "hba1c",
}

# --- Reference Ranges Database ---
REFERENCE_RANGES = {
    # Blood Sugar
    "glucose": {"low": 70, "high": 99, "unit": "mg/dL"},
    "hba1c": {"low": 4.0, "high": 5.6, "unit": "%"},
    
    # Complete Blood Count
    "hemoglobin": {"low": 12.0, "high": 15.5, "unit": "g/dL", "gender_specific": True},
    "hemoglobin_male": {"low": 13.5, "high": 17.5, "unit": "g/dL"},
    "hemoglobin_female": {"low": 12.0, "high": 15.5, "unit": "g/dL"},
    "wbc": {"low": 4.5, "high": 11.0, "unit": "x10³/µL"},
    "rbc": {"low": 4.2, "high": 5.9, "unit": "x10⁶/µL", "gender_specific": True},
    "rbc_male": {"low": 4.5, "high": 5.9, "unit": "x10⁶/µL"},
    "rbc_female": {"low": 4.2, "high": 5.4, "unit": "x10⁶/µL"},
    "platelets": {"low": 150, "high": 450, "unit": "x10³/µL"},
    "hematocrit": {"low": 38.3, "high": 48.6, "unit": "%", "gender_specific": True},
    "hematocrit_male": {"low": 40.7, "high": 50.3, "unit": "%"},
    "hematocrit_female": {"low": 36.1, "high": 44.3, "unit": "%"},
    "mcv": {"low": 80, "high": 100, "unit": "fL"},
    "mch": {"low": 27, "high": 33, "unit": "pg"},
    "mchc": {"low": 32, "high": 36, "unit": "g/dL"},
    
    # Electrolytes
    "sodium": {"low": 136, "high": 145, "unit": "mmol/L"},
    "potassium": {"low": 3.5, "high": 5.1, "unit": "mmol/L"},
    "calcium": {"low": 8.6, "high": 10.2, "unit": "mg/dL"},
    
    # Kidney Function
    "creatinine": {"low": 0.7, "high": 1.3, "unit": "mg/dL", "gender_specific": True},
    "creatinine_male": {"low": 0.7, "high": 1.3, "unit": "mg/dL"},
    "creatinine_female": {"low": 0.6, "high": 1.1, "unit": "mg/dL"},
    "bun": {"low": 7, "high": 20, "unit": "mg/dL"},
    "egfr": {"low": 60, "high": 120, "unit": "mL/min/1.73m²"},
    "uric_acid": {"low": 3.5, "high": 7.2, "unit": "mg/dL"},
    
    # Liver Function
    "ast": {"low": 10, "high": 40, "unit": "U/L"},
    "alt": {"low": 9, "high": 46, "unit": "U/L"},
    "alkaline_phosphatase": {"low": 44, "high": 147, "unit": "U/L"},
    "ggt": {"low": 0, "high": 51, "unit": "U/L"},
    "bilirubin": {"low": 0.2, "high": 1.2, "unit": "mg/dL"},
    "albumin": {"low": 3.5, "high": 5.5, "unit": "g/dL"},
    "total_protein": {"low": 6.0, "high": 8.3, "unit": "g/dL"},
    
    # Lipid Panel
    "cholesterol": {"low": 0, "high": 200, "unit": "mg/dL"},
    "ldl": {"low": 0, "high": 100, "unit": "mg/dL"},
    "hdl": {"low": 40, "high": 60, "unit": "mg/dL", "gender_specific": True},
    "hdl_male": {"low": 40, "high": 60, "unit": "mg/dL"},
    "hdl_female": {"low": 50, "high": 70, "unit": "mg/dL"},
    "triglycerides": {"low": 0, "high": 150, "unit": "mg/dL"},
    "vldl": {"low": 2, "high": 30, "unit": "mg/dL"},
    
    # Thyroid
    "tsh": {"low": 0.4, "high": 4.2, "unit": "mIU/L"},
    "t3": {"low": 80, "high": 200, "unit": "ng/dL"},
    "t4": {"low": 5.0, "high": 12.0, "unit": "µg/dL"},
    "free_t4": {"low": 0.8, "high": 1.8, "unit": "ng/dL"},
    
    # Vitamins & Minerals
    "vitamin_d": {"low": 30, "high": 100, "unit": "ng/mL"},
    "vitamin_b12": {"low": 200, "high": 900, "unit": "pg/mL"},
    "folate": {"low": 2.7, "high": 17.0, "unit": "ng/mL"},
    "iron": {"low": 60, "high": 170, "unit": "μg/dL"},
    
    # Inflammatory Markers
    "crp": {"low": 0, "high": 3.0, "unit": "mg/L"},
    "esr": {"low": 0, "high": 20, "unit": "mm/hr"},
}

# --- Helper Functions ---
def normalize_test_name(test_name: str) -> str:
    """Normalize test name for reference range lookup."""
    if not test_name:
        return ""
    
    normalized = test_name.lower().strip()
    
    # Remove common prefixes/suffixes
    normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.replace(':', '').strip()
    
    # Check mapping
    return TEST_NAME_MAPPING.get(normalized, normalized)

def extract_numeric_value(value_str: str) -> Optional[float]:
    """Extract numeric value from string."""
    if not value_str:
        return None
    
    try:
        # Handle ranges like "70-99" - take the midpoint
        if '-' in str(value_str) and not str(value_str).startswith('-'):
            parts = str(value_str).split('-')
            if len(parts) == 2:
                try:
                    low = float(re.search(r'[\d.]+', parts[0]).group())
                    high = float(re.search(r'[\d.]+', parts[1]).group())
                    return (low + high) / 2
                except:
                    pass
        
        # Extract first number found
        match = re.search(r'[\d.]+', str(value_str))
        if match:
            return float(match.group())
    except (ValueError, AttributeError):
        pass
    
    return None

# --- Node Functions ---
# def parse_pdf_node(state: GraphState) -> GraphState:
#     """Extract raw text from PDF using PyPDF2."""
#     print("\n" + "="*60)
#     print("NODE: PARSING PDF")
#     print("="*60)
    
#     try:
#         reader = PdfReader(state["pdf_path"])
#         raw_text = "\n\n".join([page.extract_text() or "" for page in reader.pages])
        
#         if not raw_text.strip():
#             return {**state, "error": "PDF appears to be empty or unreadable."}
        
#         print(f"✓ Extracted {len(raw_text)} characters from {len(reader.pages)} pages")
#         return {**state, "raw_text": raw_text}
    
#     except Exception as e:
#         print(f"✗ Error parsing PDF: {e}")
#         return {**state, "error": f"Failed to parse PDF: {str(e)}"}

# ============================================================================
# PART 4: UPDATED parse_pdf_node (Replace existing function)
# ============================================================================

def parse_pdf_node(state: GraphState) -> GraphState:
    """Extract raw text from PDF, with OCR support for scanned documents."""
    print("\n" + "="*60)
    print("NODE: PARSING PDF")
    print("="*60)
    
    try:
        # Check if it's a scanned image
        is_scanned, raw_text = check_if_scanned_image(state["pdf_path"])
        
        if is_scanned and raw_text is None:
            return {**state, "error": "Scanned document detected but OCR is not available. Please install: pip install pytesseract pillow pdf2image opencv-python"}
        
        if not raw_text or not raw_text.strip():
            return {**state, "error": "PDF appears to be empty or unreadable."}
        
        print(f"✓ Extracted {len(raw_text)} characters")
        if is_scanned:
            print("✓ Used OCR for scanned document")
        
        return {**state, "raw_text": raw_text, "is_scanned_image": is_scanned}
    
    except Exception as e:
        print(f"✗ Error parsing PDF: {e}")
        return {**state, "error": f"Failed to parse PDF: {str(e)}"}


def extract_patient_info_node(state: GraphState) -> GraphState:
    """Extract patient demographics (age, gender) for context."""
    print("\n" + "="*60)
    print("NODE: EXTRACTING PATIENT INFO")
    print("="*60)
    
    if state.get("error"):
        return state
    
    prompt = f"""
Extract patient information from this medical report. Return ONLY a JSON object.

Text (first 1500 characters):
{state['raw_text'][:1500]}

Extract:
- age: number or null
- gender: "male", "female", or "unknown"

Return ONLY this JSON format:
{{"age": 45, "gender": "male"}}

If information is not found, use null for age and "unknown" for gender.
"""
    
    try:
        response = llm.invoke(prompt)
        json_match = re.search(r'\{.*?\}', response.content, re.DOTALL)
        
        if json_match:
            patient_info = json.loads(json_match.group())
        else:
            patient_info = {"age": None, "gender": "unknown"}
        
        print(f"✓ Patient Info: Age={patient_info.get('age', 'N/A')}, Gender={patient_info.get('gender', 'unknown')}")
        return {**state, "patient_info": patient_info}
    
    except Exception as e:
        print(f"✗ Error extracting patient info: {e}")
        return {**state, "patient_info": {"age": None, "gender": "unknown"}}

def classify_document_node(state: GraphState) -> GraphState:
    """Classify document structure."""
    print("\n" + "="*60)
    print("NODE: CLASSIFYING DOCUMENT STRUCTURE")
    print("="*60)
    
    if state.get("error"):
        return {**state, "document_type": "error"}
    
    prompt = f"""
Classify this medical report's structure as ONE of these types:
- "tabular": Contains clear tables with rows and columns
- "semi-structured": Mix of labels and values (e.g., "Test: Value")
- "unstructured": Narrative text format

Text sample:
{state['raw_text'][:2000]}

Return ONLY one word: tabular, semi-structured, or unstructured
"""
    
    response = llm.invoke(prompt)
    document_type = response.content.strip().lower()
    
    # Normalize response
    if "tabular" in document_type:
        document_type = "tabular"
    elif "semi" in document_type:
        document_type = "semi-structured"
    elif "unstructured" in document_type:
        document_type = "unstructured"
    else:
        document_type = "semi-structured"  # Default
    
    print(f"✓ Document classified as: {document_type}")
    return {**state, "document_type": document_type}

def extract_tabular_data_node(state: GraphState) -> GraphState:
    """Extract tables using pdfplumber."""
    print("\n" + "="*60)
    print("NODE: EXTRACTING TABULAR DATA")
    print("="*60)
    
    try:
        extracted_data = []
        with pdfplumber.open(state["pdf_path"]) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table_num, table in enumerate(tables):
                    if len(table) > 1:
                        df = pd.DataFrame(table[1:], columns=table[0])
                        extracted_data.extend(df.to_dict("records"))
        
        if not extracted_data:
            print("✗ No tables found, falling back to semi-structured extraction")
            return extract_semi_structured_data_node(state)
        
        print(f"✓ Extracted {len(extracted_data)} records from tables")
        return {**state, "extracted_data": extracted_data}
    
    except Exception as e:
        print(f"✗ Error extracting tables: {e}")
        return extract_semi_structured_data_node(state)

def extract_semi_structured_data_node(state: GraphState) -> GraphState:
    """Extract data using LLM."""
    print("\n" + "="*60)
    print("NODE: EXTRACTING SEMI-STRUCTURED DATA")
    print("="*60)
    
    prompt = f"""
Extract ALL test results from this medical report. Be thorough.

Medical Report:
{state['raw_text']}

Return a JSON array of ALL tests found. Each test must have:
- test_name: The name of the test
- test_value: The numeric value or result
- units: The unit of measurement
- reference_range: The normal range if mentioned (optional)

Example format:
[
  {{"test_name": "Glucose", "test_value": "98", "units": "mg/dL", "reference_range": "70-99"}},
  {{"test_name": "Hemoglobin", "test_value": "14.2", "units": "g/dL", "reference_range": "12-15.5"}}
]

Extract EVERY test you can find. Return ONLY the JSON array, no other text.
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Extract JSON array
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        
        if json_match:
            extracted_data = json.loads(json_match.group())
            print(f"✓ Extracted {len(extracted_data)} test results")
            return {**state, "extracted_data": extracted_data}
        else:
            print("✗ No JSON array found in LLM output")
            return {**state, "error": "Failed to extract test results from report"}
    
    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing error: {e}")
        return {**state, "error": f"Failed to parse extracted data: {str(e)}"}
    except Exception as e:
        print(f"✗ Extraction error: {e}")
        return {**state, "error": f"Failed to extract data: {str(e)}"}

def extract_unstructured_data_node(state: GraphState) -> GraphState:
    """Extract data from unstructured text."""
    print("\n" + "="*60)
    print("NODE: EXTRACTING UNSTRUCTURED DATA")
    print("="*60)
    
    return extract_semi_structured_data_node(state)

def validate_extraction_node(state: GraphState) -> GraphState:
    """Validate extracted data quality."""
    print("\n" + "="*60)
    print("NODE: VALIDATING EXTRACTION")
    print("="*60)
    
    if state.get("error"):
        return state
    
    extracted_data = state.get("extracted_data", [])
    
    if not extracted_data:
        return {**state, "error": "No test results extracted from report"}
    
    validated_data = []
    issues = []
    
    for i, result in enumerate(extracted_data):
        test_name = result.get("test_name", "").strip()
        test_value = result.get("test_value", "").strip()
        
        if not test_name:
            issues.append(f"Result {i+1}: Missing test name")
            continue
        
        if not test_value:
            issues.append(f"Result {i+1}: Missing value for '{test_name}'")
            continue
        
        # Normalize the result
        normalized_result = {
            "test_name": test_name,
            "test_value": test_value,
            "units": result.get("units", "").strip(),
            "reference_range": result.get("reference_range", "").strip()
        }
        
        validated_data.append(normalized_result)
    
    if issues:
        print(f"⚠ Validation warnings: {len(issues)}")
        for issue in issues[:5]:
            print(f"  - {issue}")
    
    if not validated_data:
        return {**state, "error": "No valid test results after validation"}
    
    print(f"✓ Validated {len(validated_data)} test results")
    return {**state, "validated_data": validated_data, "validation_issues": issues}

# def analyze_results_node(state: GraphState) -> GraphState:
#     """Compare results with reference ranges."""
#     print("\n" + "="*60)
#     print("NODE: ANALYZING RESULTS")
#     print("="*60)
    
#     if state.get("error"):
#         return state
    
#     patient_gender = state.get("patient_info", {}).get("gender", "unknown")
#     validated_data = state.get("validated_data", [])
#     analyzed_results = []
    
#     for result in validated_data:
#         test_name_raw = result.get("test_name", "")
#         test_name = normalize_test_name(test_name_raw)
#         test_value = result.get("test_value", "")
#         units = result.get("units", "")
        
#         numeric_value = extract_numeric_value(test_value)
        
#         if numeric_value is None:
#             analyzed_results.append({
#                 **result,
#                 "normalized_name": test_name,
#                 "numeric_value": None,
#                 "status": "unknown",
#                 "analysis": "Cannot analyze non-numeric value",
#                 "confidence": "low",
#                 "confidence_notes": ["Non-numeric value"]
#             })
#             continue
        
#         # Get reference range
#         ref_range = None
#         if test_name in REFERENCE_RANGES:
#             ref_range = REFERENCE_RANGES[test_name]
            
#             # Use gender-specific range if available
#             if ref_range.get("gender_specific", False) and patient_gender in ["male", "female"]:
#                 gender_key = f"{test_name}_{patient_gender}"
#                 if gender_key in REFERENCE_RANGES:
#                     ref_range = REFERENCE_RANGES[gender_key]
        
#         # Analyze the value
#         confidence = "high"
#         confidence_notes = []
        
#         if ref_range:
#             low = ref_range["low"]
#             high = ref_range["high"]
#             ref_unit = ref_range.get("unit", "")
            
#             if numeric_value < low:
#                 status = "low"
#                 analysis = f"Below normal range ({low}-{high} {ref_unit})"
#             elif numeric_value > high:
#                 status = "high"
#                 analysis = f"Above normal range ({low}-{high} {ref_unit})"
#             else:
#                 status = "normal"
#                 analysis = f"Within normal range ({low}-{high} {ref_unit})"
            
#             # Check unit consistency
#             if units and units.lower() != ref_unit.lower():
#                 confidence = "medium"
#                 confidence_notes.append(f"Unit mismatch: {units} vs {ref_unit}")
#         else:
#             status = "unknown"
#             analysis = "No reference range available for this test"
#             confidence = "low"
#             confidence_notes.append("No reference range")
        
#         # Check if test name was normalized
#         if test_name != test_name_raw.lower():
#             confidence_notes.append("Test name normalized")
        
#         analyzed_results.append({
#             **result,
#             "normalized_name": test_name,
#             "numeric_value": numeric_value,
#             "status": status,
#             "analysis": analysis,
#             "reference_range": f"{low}-{high} {ref_unit}" if ref_range else "Not available",
#             "confidence": confidence,
#             "confidence_notes": confidence_notes
#         })
    
#     # Print summary
#     normal_count = sum(1 for r in analyzed_results if r["status"] == "normal")
#     abnormal_count = sum(1 for r in analyzed_results if r["status"] in ["high", "low"])
#     unknown_count = sum(1 for r in analyzed_results if r["status"] == "unknown")
    
#     print(f"✓ Analysis complete:")
#     print(f"  - Normal: {normal_count}")
#     print(f"  - Abnormal: {abnormal_count}")
#     print(f"  - Unknown: {unknown_count}")
    
#     return {**state, "analyzed_results": analyzed_results}

# ============================================================================
# PART 5: UPDATED analyze_results_node (Replace existing function)
# ============================================================================

def analyze_results_node(state: GraphState) -> GraphState:
    """Compare results with reference ranges and explain missing ones."""
    print("\n" + "="*60)
    print("NODE: ANALYZING RESULTS")
    print("="*60)
    
    if state.get("error"):
        return state
    
    patient_gender = state.get("patient_info", {}).get("gender", "unknown")
    validated_data = state.get("validated_data", [])
    analyzed_results = []
    missing_ranges_explanation = {}  # NEW: Store explanations
    
    for result in validated_data:
        test_name_raw = result.get("test_name", "")
        test_name = normalize_test_name(test_name_raw)
        test_value = result.get("test_value", "")
        units = result.get("units", "")
        
        numeric_value = extract_numeric_value(test_value)
        
        if numeric_value is None:
            analyzed_results.append({
                **result,
                "normalized_name": test_name,
                "numeric_value": None,
                "status": "unknown",
                "analysis": "Cannot analyze non-numeric value",
                "confidence": "low",
                "confidence_notes": ["Non-numeric value"]
            })
            continue
        
        # Get reference range
        ref_range = None
        if test_name in REFERENCE_RANGES:
            ref_range = REFERENCE_RANGES[test_name]
            
            # Use gender-specific range if available
            if ref_range.get("gender_specific", False) and patient_gender in ["male", "female"]:
                gender_key = f"{test_name}_{patient_gender}"
                if gender_key in REFERENCE_RANGES:
                    ref_range = REFERENCE_RANGES[gender_key]
        
        # Analyze the value
        confidence = "high"
        confidence_notes = []
        
        if ref_range:
            low = ref_range["low"]
            high = ref_range["high"]
            ref_unit = ref_range.get("unit", "")
            
            if numeric_value < low:
                status = "low"
                analysis = f"Below normal range ({low}-{high} {ref_unit})"
            elif numeric_value > high:
                status = "high"
                analysis = f"Above normal range ({low}-{high} {ref_unit})"
            else:
                status = "normal"
                analysis = f"Within normal range ({low}-{high} {ref_unit})"
            
            # Check unit consistency
            if units and units.lower() != ref_unit.lower():
                confidence = "medium"
                confidence_notes.append(f"Unit mismatch: {units} vs {ref_unit}")
        else:
            # NEW: Handle missing reference ranges
            status = "no_reference"
            analysis = "Reference range not available in our database"
            confidence = "low"
            confidence_notes.append("No reference range")
            
            # Get LLM explanation for this test
            print(f"   Getting explanation for: {test_name_raw}")
            explanation = get_missing_test_explanation(test_name_raw, test_value, units)
            missing_ranges_explanation[test_name_raw] = explanation
        
        # Check if test name was normalized
        if test_name != test_name_raw.lower():
            confidence_notes.append("Test name normalized")
        
        analyzed_results.append({
            **result,
            "normalized_name": test_name,
            "numeric_value": numeric_value,
            "status": status,
            "analysis": analysis,
            "reference_range": f"{low}-{high} {ref_unit}" if ref_range else "Not available",
            "confidence": confidence,
            "confidence_notes": confidence_notes
        })
    
    # Print summary
    normal_count = sum(1 for r in analyzed_results if r["status"] == "normal")
    abnormal_count = sum(1 for r in analyzed_results if r["status"] in ["high", "low"])
    unknown_count = sum(1 for r in analyzed_results if r["status"] == "unknown")
    no_ref_count = sum(1 for r in analyzed_results if r["status"] == "no_reference")  # NEW
    
    print(f"✓ Analysis complete:")
    print(f"  - Normal: {normal_count}")
    print(f"  - Abnormal: {abnormal_count}")
    print(f"  - No Reference: {no_ref_count}")  # NEW
    print(f"  - Unknown: {unknown_count}")
    
    return {
        **state, 
        "analyzed_results": analyzed_results,
        "missing_ranges_explanation": missing_ranges_explanation  # NEW
    }

def summarize_report_node(state: GraphState) -> GraphState:
    """Generate patient-friendly summary."""
    print("\n" + "="*60)
    print("NODE: GENERATING SUMMARY")
    print("="*60)
    
    if state.get("error"):
        return state
    
    analyzed = state.get("analyzed_results", [])
    patient_info = state.get("patient_info", {})
    
    normal_count = sum(1 for r in analyzed if r.get("status") == "normal")
    abnormal_count = sum(1 for r in analyzed if r.get("status") in ["high", "low"])
    
    age = patient_info.get("age", "unknown")
    gender = patient_info.get("gender", "unknown")
    
    prompt = f"""
You are a compassionate healthcare assistant explaining lab results to a patient.

Patient Context:
- Age: {age}
- Gender: {gender}
- Total tests: {len(analyzed)}
- Normal results: {normal_count}
- Abnormal results: {abnormal_count}

Test Results:
{json.dumps(analyzed, indent=2)}

Create a clear, empathetic summary that:

1. **Overall Assessment**: Start with a reassuring overview
2. **What Was Tested**: Briefly explain what these tests measure in simple terms
3. **Key Findings**: Highlight important results (especially abnormal ones) without causing alarm
4. **What This Means**: Explain implications in everyday language
5. **Next Steps**: Suggest when to follow up with a doctor

Guidelines:
- Use warm, conversational tone
- Avoid medical jargon (or explain it simply)
- Use analogies when helpful
- Break into clear sections with headers
- Be encouraging but honest
- Keep paragraphs short and readable

Write the summary now:
"""
    
    response = llm.invoke(prompt)
    print("✓ Summary generated")
    return {**state, "summarized_report": response.content}

def generate_recommendations_node(state: GraphState) -> GraphState:
    """Generate lifestyle and follow-up recommendations."""
    print("\n" + "="*60)
    print("NODE: GENERATING RECOMMENDATIONS")
    print("="*60)
    
    if state.get("error"):
        return state
    
    analyzed = state.get("analyzed_results", [])
    abnormal_results = [r for r in analyzed if r.get("status") in ["high", "low"]]
    
    if not abnormal_results:
        recommendations = """
## Recommendations

✅ **Great News!**
All your test results are within normal ranges. Keep up your current healthy habits!

**To Maintain Your Health:**
- Continue a balanced diet with plenty of fruits and vegetables
- Stay physically active (aim for 150 minutes of moderate exercise per week)
- Get adequate sleep (7-9 hours for most adults)
- Stay hydrated
- Manage stress through relaxation techniques
- Schedule regular check-ups with your doctor

**When to Follow Up:**
- Annual physical examination
- As recommended by your healthcare provider
"""
        print("✓ Generated maintenance recommendations")
        return {**state, "recommendations": recommendations}
    
    prompt = f"""
Based on these abnormal test results, provide general lifestyle recommendations and follow-up suggestions.

IMPORTANT: Do NOT provide specific medical advice or diagnoses. Focus on general wellness.

Abnormal Results:
{json.dumps(abnormal_results, indent=2)}

Provide recommendations in these sections:

## Dietary Suggestions
(General nutrition advice based on the findings)

## Lifestyle Changes
(Exercise, sleep, stress management, etc.)

## When to Consult a Doctor
(Urgency level and what to discuss)

## Potential Follow-Up Tests
(Common tests that might be recommended)

Write in clear, supportive language. Use bullet points for readability.
"""
    
    response = llm.invoke(prompt)
    print("✓ Recommendations generated")
    return {**state, "recommendations": response.content}

def handle_error_node(state: GraphState) -> GraphState:
    """Handle errors gracefully."""
    print("\n" + "="*60)
    print("NODE: HANDLING ERROR")
    print("="*60)
    print(f"✗ Error: {state.get('error', 'Unknown error')}")
    return state

# --- Routing ---
def route_document(state: GraphState) -> str:
    """Route based on document type."""
    if state.get("error"):
        return "error"
    
    dt = state.get("document_type", "")
    
    if "tabular" in dt:
        return "extract_tabular"
    elif "semi" in dt:
        return "extract_semi_structured"
    else:
        return "extract_unstructured"

# --- Build Graph ---
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("parse_pdf", parse_pdf_node)
workflow.add_node("extract_patient_info", extract_patient_info_node)
workflow.add_node("classify_document", classify_document_node)
workflow.add_node("extract_tabular", extract_tabular_data_node)
workflow.add_node("extract_semi_structured", extract_semi_structured_data_node)
workflow.add_node("extract_unstructured", extract_unstructured_data_node)
workflow.add_node("validate_extraction", validate_extraction_node)
workflow.add_node("analyze_results", analyze_results_node)
workflow.add_node("summarize_report", summarize_report_node)
workflow.add_node("generate_recommendations", generate_recommendations_node)
workflow.add_node("handle_error", handle_error_node)

# Set entry point
workflow.set_entry_point("parse_pdf")

# Add edges
workflow.add_edge("parse_pdf", "extract_patient_info")
workflow.add_edge("extract_patient_info", "classify_document")

workflow.add_conditional_edges(
    "classify_document",
    route_document,
    {
        "extract_tabular": "extract_tabular",
        "extract_semi_structured": "extract_semi_structured",
        "extract_unstructured": "extract_unstructured",
        "error": "handle_error",
    },
)

# Connect extraction to validation
workflow.add_edge("extract_tabular", "validate_extraction")
workflow.add_edge("extract_semi_structured", "validate_extraction")
workflow.add_edge("extract_unstructured", "validate_extraction")

# Analysis pipeline
workflow.add_edge("validate_extraction", "analyze_results")
workflow.add_edge("analyze_results", "summarize_report")
workflow.add_edge("summarize_report", "generate_recommendations")
workflow.add_edge("generate_recommendations", END)
workflow.add_edge("handle_error", END)

# Compile
app = workflow.compile()

# Q - Now, can we see how the graph looks like ?

# Visualize the graph
from IPython.display import Image,display

# try catch block
try:
    # display method = responsible for displaying the graph w.r.t any image object that we give
    display(Image(app.get_graph().draw_mermaid_png()))
except Exception:
    pass

# --- Output Formatting ---
# def generate_user_friendly_output(final_state: dict) -> dict:
#     """Convert technical output to user-friendly format."""
    
#     if final_state.get("error"):
#         return {
#             "success": False,
#             "message": "We encountered an issue processing your report.",
#             "details": final_state["error"],
#             "suggestion": "Please ensure the PDF is readable and contains medical test results."
#         }
    
#     analyzed = final_state.get("analyzed_results", [])
    
#     return {
#         "success": True,
#         "patient_info": final_state.get("patient_info", {}),
#         "summary": final_state.get("summarized_report", ""),
#         "recommendations": final_state.get("recommendations", ""),
#         "statistics": {
#             "total_tests": len(analyzed),
#             "normal_count": sum(1 for r in analyzed if r.get("status") == "normal"),
#             "abnormal_count": sum(1 for r in analyzed if r.get("status") in ["high", "low"]),
#             "unknown_count": sum(1 for r in analyzed if r.get("status") == "unknown")
#         },
#         "detailed_results": analyzed,
#         "validation_issues": final_state.get("validation_issues", []),
#         "confidence_summary": {
#             "high_confidence": sum(1 for r in analyzed if r.get("confidence") == "high"),
#             "medium_confidence": sum(1 for r in analyzed if r.get("confidence") == "medium"),
#             "low_confidence": sum(1 for r in analyzed if r.get("confidence") == "low")
#         }
#     }

# ============================================================================
# PART 7: UPDATED generate_user_friendly_output (Replace existing function)
# ============================================================================

def generate_user_friendly_output(final_state: dict) -> dict:
    """Convert technical output to user-friendly format."""
    
    if final_state.get("error"):
        return {
            "success": False,
            "message": "We encountered an issue processing your report.",
            "details": final_state["error"],
            "suggestion": "Please ensure the PDF is readable and contains medical test results."
        }
    
    analyzed = final_state.get("analyzed_results", [])
    
    return {
        "success": True,
        "patient_info": final_state.get("patient_info", {}),
        "summary": final_state.get("summarized_report", ""),
        "recommendations": final_state.get("recommendations", ""),
        "statistics": {
            "total_tests": len(analyzed),
            "normal_count": sum(1 for r in analyzed if r.get("status") == "normal"),
            "abnormal_count": sum(1 for r in analyzed if r.get("status") in ["high", "low"]),
            "unknown_count": sum(1 for r in analyzed if r.get("status") == "unknown"),
            "no_reference_count": sum(1 for r in analyzed if r.get("status") == "no_reference"),  # NEW
        },
        "detailed_results": analyzed,
        "validation_issues": final_state.get("validation_issues", []),
        "confidence_summary": {
            "high_confidence": sum(1 for r in analyzed if r.get("confidence") == "high"),
            "medium_confidence": sum(1 for r in analyzed if r.get("confidence") == "medium"),
            "low_confidence": sum(1 for r in analyzed if r.get("confidence") == "low")
        },
        "missing_ranges_explanation": final_state.get("missing_ranges_explanation", {}),  # NEW
        "is_scanned": final_state.get("is_scanned_image", False)  # NEW
    }

def print_results_summary(output: dict):
    """Print a beautiful summary of results."""
    
    print("\n" + "="*80)
    print(" "*25 + "MEDICAL REPORT ANALYSIS")
    print("="*80)
    
    if not output["success"]:
        print("\n❌ ERROR")
        print("-"*80)
        print(f"Message: {output['message']}")
        print(f"Details: {output['details']}")
        print(f"Suggestion: {output['suggestion']}")
        return
    
    # Patient Info
    patient = output.get("patient_info", {})
    print("\n👤 PATIENT INFORMATION")
    print("-"*80)
    print(f"Age: {patient.get('age', 'N/A')}")
    print(f"Gender: {patient.get('gender', 'Unknown').capitalize()}")
    
    # Statistics
    stats = output.get("statistics", {})
    print("\n📊 TEST STATISTICS")
    print("-"*80)
    print(f"Total Tests Analyzed: {stats.get('total_tests', 0)}")
    print(f"✅ Normal Results: {stats.get('normal_count', 0)}")
    print(f"⚠️  Abnormal Results: {stats.get('abnormal_count', 0)}")
    print(f"❓ Unknown/Unanalyzed: {stats.get('unknown_count', 0)}")
    
    # Confidence
    conf = output.get("confidence_summary", {})
    print(f"\nConfidence Levels:")
    print(f"  High: {conf.get('high_confidence', 0)}")
    print(f"  Medium: {conf.get('medium_confidence', 0)}")
    print(f"  Low: {conf.get('low_confidence', 0)}")
    
    # Key Abnormal Results
    abnormal_results = [
        r for r in output.get("detailed_results", [])
        if r.get("status") in ["high", "low"]
    ]
    
    if abnormal_results:
        print("\n⚠️  KEY ABNORMAL RESULTS")
        print("-"*80)
        for result in abnormal_results[:5]:  # Show top 5
            status_icon = "📈" if result.get("status") == "high" else "📉"
            print(f"{status_icon} {result.get('test_name', 'Unknown')}: {result.get('test_value', 'N/A')} {result.get('units', '')}")
            print(f"   Status: {result.get('status', 'unknown').upper()}")
            print(f"   Normal Range: {result.get('reference_range', 'N/A')}")
            print(f"   {result.get('analysis', 'No analysis available')}")
            print()
    
    # Validation Issues
    issues = output.get("validation_issues", [])
    if issues:
        print("\n⚠️  VALIDATION WARNINGS")
        print("-"*80)
        for issue in issues[:3]:
            print(f"  • {issue}")
        if len(issues) > 3:
            print(f"  ... and {len(issues) - 3} more")
    
    print("\n" + "="*80)
    print("Files saved:")
    print("  📄 patient_report.json - Complete analysis")
    print("  📄 analyzed_results.json - Detailed test results")
    print("  📄 patient_summary.txt - Patient-friendly summary")
    print("="*80)

# ============================================================================
# PART 3: NEW HELPER FUNCTIONS (Add after existing helper functions)
# ============================================================================

def preprocess_image_for_ocr(image_path: str) -> str:
    """Preprocess and extract text from scanned image using OCR."""
    if not OCR_AVAILABLE:
        return None
    
    try:
        # Read image
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to preprocess the image
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Noise removal
        gray = cv2.medianBlur(gray, 3)
        
        # Perform OCR
        text = pytesseract.image_to_string(gray, lang='eng')
        
        return text
    except Exception as e:
        print(f"OCR Error: {e}")
        return None

def check_if_scanned_image(pdf_path: str) -> tuple[bool, str]:
    """Check if PDF is a scanned image and extract text accordingly."""
    try:
        # Try normal PDF extraction first
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        # If text is very sparse, it's likely a scanned image
        if len(text.strip()) < 100:
            print("⚠️  Detected scanned document, attempting OCR...")
            
            if not OCR_AVAILABLE:
                return True, None
            
            # Convert PDF pages to images and perform OCR
            import pdf2image
            images = pdf2image.convert_from_path(pdf_path)
            
            ocr_text = ""
            for i, img in enumerate(images):
                print(f"   Processing page {i+1}/{len(images)} with OCR...")
                # Save temporarily
                temp_img = f"temp_page_{i}.png"
                img.save(temp_img)
                
                # Extract text
                page_text = preprocess_image_for_ocr(temp_img)
                if page_text:
                    ocr_text += page_text + "\n\n"
                
                # Cleanup
                os.remove(temp_img)
            
            return True, ocr_text if ocr_text else None
        
        return False, text
    
    except Exception as e:
        print(f"Error checking document type: {e}")
        return False, None

def get_missing_test_explanation(test_name: str, test_value: str, units: str) -> str:
    """Use LLM to explain tests without reference ranges."""
    
    prompt = f"""
You are a medical expert. Explain this lab test in simple terms for a patient.

Test: {test_name}
Value: {test_value} {units}

Provide a brief explanation (2-3 sentences) covering:
1. What this test measures
2. Why it might be ordered
3. General interpretation guidance (without providing specific medical advice)

Keep it simple, reassuring, and mention they should discuss with their doctor.
"""
    
    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"This test measures {test_name}. Please consult your healthcare provider for interpretation of this result."

# ============================================================================
# PART 6: NEW PDF GENERATION FUNCTION
# ============================================================================

def generate_pdf_report(output: dict, filename: str = "medical_report.pdf"):
    """Generate a professional PDF report."""
    
    doc = SimpleDocTemplate(filename, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Add only NEW custom styles (don't redefine existing ones)
    styles.add(ParagraphStyle(name='CustomTitle', 
                             parent=styles['Heading1'],
                             fontSize=24,
                             textColor=colors.HexColor('#2c3e50'),
                             spaceAfter=30,
                             alignment=TA_CENTER))
    
    styles.add(ParagraphStyle(name='SectionHeader',
                             parent=styles['Heading2'],
                             fontSize=14,
                             textColor=colors.HexColor('#34495e'),
                             spaceAfter=12,
                             spaceBefore=12))
    
    styles.add(ParagraphStyle(name='CustomBody',  # Changed from 'BodyText' to 'CustomBody'
                             parent=styles['BodyText'],
                             fontSize=10,
                             alignment=TA_JUSTIFY,
                             spaceAfter=12))
    
    # Title
    elements.append(Paragraph("Medical Report Analysis", styles['CustomTitle']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Date
    date_text = f"Report Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    elements.append(Paragraph(date_text, styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Patient Information
    elements.append(Paragraph("Patient Information", styles['SectionHeader']))
    patient = output.get("patient_info", {})
    patient_data = [
        ["Age:", str(patient.get('age', 'N/A'))],
        ["Gender:", patient.get('gender', 'Unknown').capitalize()],
    ]
    patient_table = Table(patient_data, colWidths=[1.5*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(patient_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Statistics
    elements.append(Paragraph("Test Statistics", styles['SectionHeader']))
    stats = output.get("statistics", {})
    stats_data = [
        ["Total Tests:", str(stats.get('total_tests', 0))],
        ["Normal Results:", str(stats.get('normal_count', 0))],
        ["Abnormal Results:", str(stats.get('abnormal_count', 0))],
        ["Tests Without Reference:", str(stats.get('no_reference_count', 0))],
    ]
    stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Abnormal Results
    abnormal_results = [r for r in output.get("detailed_results", []) 
                       if r.get("status") in ["high", "low"]]
    
    if abnormal_results:
        elements.append(Paragraph("⚠ Key Abnormal Results", styles['SectionHeader']))
        
        for result in abnormal_results:
            test_name = result.get('test_name', 'Unknown')
            value = f"{result.get('test_value', 'N/A')} {result.get('units', '')}"
            status = result.get('status', 'unknown').upper()
            ref_range = result.get('reference_range', 'N/A')
            analysis = result.get('analysis', 'No analysis available')
            
            elements.append(Paragraph(f"<b>{test_name}</b>", styles['CustomBody']))
            elements.append(Paragraph(f"Value: {value} | Status: {status}", styles['Normal']))
            elements.append(Paragraph(f"Normal Range: {ref_range}", styles['Normal']))
            elements.append(Paragraph(f"{analysis}", styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))
    
    # Tests Without Reference Ranges
    no_ref_results = [r for r in output.get("detailed_results", []) 
                     if r.get("status") == "no_reference"]
    
    if no_ref_results:
        elements.append(PageBreak())
        elements.append(Paragraph("Tests Without Standard Reference Ranges", styles['SectionHeader']))
        elements.append(Paragraph(
            "The following tests don't have standard reference ranges in our database. "
            "This doesn't mean they're abnormal - many specialized tests have context-dependent ranges. "
            "Please discuss these results with your healthcare provider.",
            styles['CustomBody']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        explanations = output.get("missing_ranges_explanation", {})
        for result in no_ref_results:
            test_name = result.get('test_name', 'Unknown')
            value = f"{result.get('test_value', 'N/A')} {result.get('units', '')}"
            explanation = explanations.get(test_name, "Please consult your doctor for interpretation.")
            
            elements.append(Paragraph(f"<b>{test_name}</b>: {value}", styles['CustomBody']))
            elements.append(Paragraph(explanation, styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))
    
    # Summary
    elements.append(PageBreak())
    elements.append(Paragraph("Detailed Summary", styles['SectionHeader']))
    summary_text = output.get("summary", "No summary available.")
    
    # Split and clean summary text
    for para in summary_text.split('\n\n'):
        if para.strip():
            # Remove markdown headers and format
            clean_para = para.strip().replace('#', '').replace('**', '')
            if clean_para:
                elements.append(Paragraph(clean_para, styles['CustomBody']))
    
    # Recommendations
    elements.append(PageBreak())
    elements.append(Paragraph("Recommendations", styles['SectionHeader']))
    rec_text = output.get("recommendations", "No recommendations available.")
    
    # Split and clean recommendations
    for para in rec_text.split('\n\n'):
        if para.strip():
            clean_para = para.strip().replace('#', '').replace('**', '')
            if clean_para:
                elements.append(Paragraph(clean_para, styles['CustomBody']))
    
    # Disclaimer
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("DISCLAIMER", styles['SectionHeader']))
    disclaimer = (
        "This analysis is for informational purposes only and does not constitute "
        "medical advice. Always consult with your healthcare provider for proper "
        "interpretation of your medical reports and treatment recommendations."
    )
    elements.append(Paragraph(disclaimer, styles['CustomBody']))
    
    # Build PDF
    try:
        doc.build(elements)
        print(f"✓ PDF report generated: {filename}")
    except Exception as e:
        print(f"⚠️  Warning: PDF generation failed: {e}")
        print("   Text summary is still available in patient_summary.txt")


# # --- Main Execution ---
# if __name__ == "__main__":
#     import sys
    
#     # Get PDF path from command line or use default
#     pdf_path = "sampleReport.pdf"
#     # sys.argv[1] if len(sys.argv) > 1 else
    
#     print("\n" + "="*80)
#     print(" "*20 + "MEDICAL REPORT ANALYZER v2.0")
#     print("="*80)
#     print(f"\nProcessing: {pdf_path}")

#     # debug
#     # print("Current working directory:", os.getcwd())
#     # print("Looking for file at:", os.path.abspath(pdf_path))

    
#     # Check if file exists
#     if not os.path.exists(pdf_path):
#         print(f"\n❌ Error: File '{pdf_path}' not found!")
#         print("Usage: python script.py <path_to_pdf>")
#         sys.exit(1)
    
#     # Run the workflow
#     try:
#         inputs = {"pdf_path": pdf_path}
#         final_state = app.invoke(inputs)
        
#         # Generate user-friendly output
#         output = generate_user_friendly_output(final_state)
        
#         # Save outputs
#         # 1. Complete analysis as JSON
#         with open("patient_report.json", "w", encoding="utf-8") as f:
#             json.dump(output, f, indent=2, ensure_ascii=False)
        
#         # 2. Detailed results
#         if output.get("success"):
#             with open("analyzed_results.json", "w", encoding="utf-8") as f:
#                 json.dump(output["detailed_results"], f, indent=2, ensure_ascii=False)
            
#             # 3. Patient summary
#             with open("patient_summary.txt", "w", encoding="utf-8") as f:
#                 f.write("="*80 + "\n")
#                 f.write(" "*25 + "MEDICAL REPORT SUMMARY\n")
#                 f.write("="*80 + "\n\n")
                
#                 f.write("PATIENT INFORMATION\n")
#                 f.write("-"*80 + "\n")
#                 patient = output.get("patient_info", {})
#                 f.write(f"Age: {patient.get('age', 'N/A')}\n")
#                 f.write(f"Gender: {patient.get('gender', 'Unknown').capitalize()}\n\n")
                
#                 f.write("TEST STATISTICS\n")
#                 f.write("-"*80 + "\n")
#                 stats = output.get("statistics", {})
#                 f.write(f"Total Tests: {stats.get('total_tests', 0)}\n")
#                 f.write(f"Normal Results: {stats.get('normal_count', 0)}\n")
#                 f.write(f"Abnormal Results: {stats.get('abnormal_count', 0)}\n\n")
                
#                 f.write("="*80 + "\n")
#                 f.write("DETAILED SUMMARY\n")
#                 f.write("="*80 + "\n\n")
#                 f.write(output.get("summary", "No summary available."))
                
#                 f.write("\n\n" + "="*80 + "\n")
#                 f.write("RECOMMENDATIONS\n")
#                 f.write("="*80 + "\n\n")
#                 f.write(output.get("recommendations", "No recommendations available."))
                
#                 f.write("\n\n" + "="*80 + "\n")
#                 f.write("DETAILED TEST RESULTS\n")
#                 f.write("="*80 + "\n\n")
                
#                 for i, result in enumerate(output.get("detailed_results", []), 1):
#                     f.write(f"{i}. {result.get('test_name', 'Unknown Test')}\n")
#                     f.write(f"   Value: {result.get('test_value', 'N/A')} {result.get('units', '')}\n")
#                     f.write(f"   Status: {result.get('status', 'unknown').upper()}\n")
#                     f.write(f"   Normal Range: {result.get('reference_range', 'Not available')}\n")
#                     f.write(f"   Analysis: {result.get('analysis', 'No analysis available')}\n")
#                     if result.get("confidence") != "high":
#                         f.write(f"   Confidence: {result.get('confidence', 'unknown')}\n")
#                     f.write("\n")
                
#                 f.write("="*80 + "\n")
#                 f.write("DISCLAIMER\n")
#                 f.write("="*80 + "\n")
#                 f.write("This analysis is for informational purposes only and does not constitute\n")
#                 f.write("medical advice. Always consult with your healthcare provider for proper\n")
#                 f.write("interpretation of your medical reports and treatment recommendations.\n")
        
#         # Print summary to console
#         print_results_summary(output)
        
#         # Exit with appropriate code
#         sys.exit(0 if output["success"] else 1)
    
#     except KeyboardInterrupt:
#         print("\n\n❌ Analysis interrupted by user")
#         sys.exit(1)
    
#     except Exception as e:
#         print(f"\n\n❌ Unexpected error: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)

# ============================================================================
# PART 8: UPDATED MAIN EXECUTION 
# Replace everything from "if __name__ == "__main__":" to the end of your file
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Get PDF path from command line or use default
    pdf_path = "/Users/_biibekk_/Downloads/clicked.pdf"
    # sys.argv[1] if len(sys.argv) > 1 else
    
    print("\n" + "="*80)
    print(" "*20 + "MEDICAL REPORT ANALYZER v3.0")
    print("="*80)
    print(f"\nProcessing: {pdf_path}")
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"\n❌ Error: File '{pdf_path}' not found!")
        print("Usage: python script.py <path_to_pdf>")
        sys.exit(1)
    
    # Run the workflow
    try:
        inputs = {"pdf_path": pdf_path}
        final_state = app.invoke(inputs)
        
        # Generate user-friendly output
        output = generate_user_friendly_output(final_state)
        
        # Save outputs
        # 1. Complete analysis as JSON
        with open("patient_report.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # 2. Detailed results
        if output.get("success"):
            with open("analyzed_results.json", "w", encoding="utf-8") as f:
                json.dump(output["detailed_results"], f, indent=2, ensure_ascii=False)
            
            # 3. Generate PDF Report (NEW)
            generate_pdf_report(output, "medical_report_summary.pdf")
            
            # 4. Keep text summary for backward compatibility
            with open("patient_summary.txt", "w", encoding="utf-8") as f:
                f.write("="*80 + "\n")
                f.write(" "*25 + "MEDICAL REPORT SUMMARY\n")
                f.write("="*80 + "\n\n")
                
                f.write("PATIENT INFORMATION\n")
                f.write("-"*80 + "\n")
                patient = output.get("patient_info", {})
                f.write(f"Age: {patient.get('age', 'N/A')}\n")
                f.write(f"Gender: {patient.get('gender', 'Unknown').capitalize()}\n\n")
                
                f.write("TEST STATISTICS\n")
                f.write("-"*80 + "\n")
                stats = output.get("statistics", {})
                f.write(f"Total Tests: {stats.get('total_tests', 0)}\n")
                f.write(f"Normal Results: {stats.get('normal_count', 0)}\n")
                f.write(f"Abnormal Results: {stats.get('abnormal_count', 0)}\n")
                f.write(f"Tests Without Reference: {stats.get('no_reference_count', 0)}\n\n")
                
                # Add explanations for tests without references
                if output.get("missing_ranges_explanation"):
                    f.write("TESTS WITHOUT STANDARD REFERENCE RANGES\n")
                    f.write("-"*80 + "\n")
                    for test_name, explanation in output["missing_ranges_explanation"].items():
                        f.write(f"\n{test_name}:\n{explanation}\n")
                    f.write("\n")
                
                f.write("="*80 + "\n")
                f.write("DETAILED SUMMARY\n")
                f.write("="*80 + "\n\n")
                f.write(output.get("summary", "No summary available."))
                
                f.write("\n\n" + "="*80 + "\n")
                f.write("RECOMMENDATIONS\n")
                f.write("="*80 + "\n\n")
                f.write(output.get("recommendations", "No recommendations available."))
                
                f.write("\n\n" + "="*80 + "\n")
                f.write("DETAILED TEST RESULTS\n")
                f.write("="*80 + "\n\n")
                
                for i, result in enumerate(output.get("detailed_results", []), 1):
                    f.write(f"{i}. {result.get('test_name', 'Unknown Test')}\n")
                    f.write(f"   Value: {result.get('test_value', 'N/A')} {result.get('units', '')}\n")
                    f.write(f"   Status: {result.get('status', 'unknown').upper()}\n")
                    f.write(f"   Normal Range: {result.get('reference_range', 'Not available')}\n")
                    f.write(f"   Analysis: {result.get('analysis', 'No analysis available')}\n")
                    if result.get("confidence") != "high":
                        f.write(f"   Confidence: {result.get('confidence', 'unknown')}\n")
                    f.write("\n")
                
                f.write("="*80 + "\n")
                f.write("DISCLAIMER\n")
                f.write("="*80 + "\n")
                f.write("This analysis is for informational purposes only and does not constitute\n")
                f.write("medical advice. Always consult with your healthcare provider for proper\n")
                f.write("interpretation of your medical reports and treatment recommendations.\n")
        
        # Print summary to console
        print_results_summary(output)
        
        print("\n" + "="*80)
        print("Files saved:")
        print("  📄 patient_report.json - Complete analysis")
        print("  📄 analyzed_results.json - Detailed test results")
        print("  📄 medical_report_summary.pdf - PDF Report (NEW)")
        print("  📄 patient_summary.txt - Text summary")
        print("="*80)
        
        # Exit with appropriate code
        sys.exit(0 if output["success"] else 1)
    
    except KeyboardInterrupt:
        print("\n\n❌ Analysis interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
