"""
MEDICAL REPORT ANALYZER
"""

import json
import re
import os
import sys
from typing import TypedDict, Literal, List, Optional
from datetime import datetime

# Import reference data
from reference_data import REFERENCE_RANGES, TEST_NAME_MAPPING, get_reference_range

# LangChain & LLM
from langchain_groq import ChatGroq
from openai import OpenAI
from langgraph.graph import StateGraph, END

# PDF Processing
from PyPDF2 import PdfReader
import pdfplumber
import pandas as pd

# OCR
try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR libraries not available")

# PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# Environment setup
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("GROQ_API_KEY not found. Create .env file with: GROQ_API_KEY=your_key")
    sys.exit(1)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

# llm = OpenAI(
#     model="gpt-5.1",
#     api_key=os.getenv("OPENAI_API_KEY"),
#     temperature=0
# )

print("LLM initialized!")

# ============================================================================
# LEARNED RANGES MANAGEMENT
# ============================================================================

LEARNED_RANGES_FILE = "learned_reference_ranges.json"

def load_learned_ranges():
    """Load previously learned reference ranges."""
    if os.path.exists(LEARNED_RANGES_FILE):
        try:
            with open(LEARNED_RANGES_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_learned_range(test_name: str, low: float, high: float, unit: str, 
                       source: str = "extracted"):
    """Save a newly learned reference range."""
    learned = load_learned_ranges()
    
    learned[test_name] = {
        "low": low,
        "high": high,
        "unit": unit,
        "source": source,
        "learned_date": datetime.now().isoformat(),
        "confidence": "medium"
    }
    
    with open(LEARNED_RANGES_FILE, 'w') as f:
        json.dump(learned, f, indent=2)
    
    print(f"✓ Learned new reference range: {test_name} = {low}-{high} {unit}")

# ============================================================================
# STATE DEFINITION
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
    error: str
    is_scanned_image: bool
    missing_ranges_explanation: dict
    extraction_confidence: float
    document_category: str

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_test_name(test_name: str) -> str:
    """Normalize test names using mapping."""
    if not test_name:
        return ""
    
    normalized = test_name.lower().strip()
    normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.replace(':', '').strip()
    
    return TEST_NAME_MAPPING.get(normalized, normalized)

def extract_numeric_value(value_str: str) -> Optional[float]:
    """Extract numeric value from string."""
    if not value_str:
        return None
    
    try:
        cleaned = str(value_str).replace(',', '').strip()
        
        if '-' in cleaned and not cleaned.startswith('-'):
            parts = cleaned.split('-')
            if len(parts) == 2:
                try:
                    low = float(re.search(r'[\d.]+', parts[0]).group())
                    high = float(re.search(r'[\d.]+', parts[1]).group())
                    return (low + high) / 2
                except:
                    pass
        
        match = re.search(r'(\d+\.?\d*)', cleaned)
        if match:
            return float(match.group(1))
            
    except (ValueError, AttributeError):
        pass
    
    return None

def is_valid_medical_entry(test_name: str, value: str, category: str) -> bool:
    """Validate if entry is a real medical test/measurement."""
    if not test_name or not value:
        return False
    
    false_positives = [
        'page', 'date', 'time', 'patient', 'doctor', 'hospital',
        'phone', 'address', 'name', 'age', 'gender', 'report',
        'signature', 'stamp', 'normal', 'abnormal', 'within limits',
        'unremarkable', 'finding', 'impression', 'conclusion'
    ]
    
    test_lower = test_name.lower()
    value_lower = str(value).lower()
    
    if any(fp in test_lower for fp in false_positives):
        return False
    
    if any(fp in value_lower for fp in ['normal', 'abnormal', 'within limits']):
        return False
    
    if not re.search(r'\d', str(value)):
        return False
    
    if len(test_name) < 2 or len(test_name) > 100:
        return False
    
    return True

def detect_document_category(text: str) -> str:
    """Detect document type: lab, imaging, or mixed."""
    text_lower = text.lower()
    
    imaging_keywords = [
        'ultrasound', 'usg', 'sonography', 'scan', 'size', 'measurement',
        'cm', 'mm', 'liver', 'kidney', 'spleen', 'prostate'
    ]
    
    lab_keywords = [
        'laboratory', 'lab', 'blood test', 'cbc', 'glucose', 
        'creatinine', 'hemoglobin', 'wbc', 'rbc'
    ]
    
    imaging_count = sum(1 for kw in imaging_keywords if kw in text_lower)
    lab_count = sum(1 for kw in lab_keywords if kw in text_lower)
    
    if imaging_count > lab_count and imaging_count >= 2:
        return "imaging"
    elif lab_count > imaging_count and lab_count >= 2:
        return "lab"
    return "mixed"

def extract_imaging_measurements(text: str) -> List[dict]:
    """Extract imaging measurements using regex patterns."""
    patterns = [
        (r'(liver|kidney|spleen|prostate|gallbladder|pancreas|aorta)\s*(?:size|length|measurement|volume|weight)?\s*[:\-]?\s*([\d.]+)\s*(cm|mm|ml|grams?)', 'organ'),
        (r'(right\s+kidney|left\s+kidney|rt\s+kidney|lt\s+kidney)\s*[:\-]?\s*([\d.]+)\s*(cm|mm)', 'kidney'),
        (r'(calculus|stone|calculi|concretion|echogenic\s+foci)\s*(?:size|at)?\s*[:\-]?\s*([\d.]+)\s*(mm|cm)', 'stone'),
        (r'(?:prostate|gland)\s*(?:size|volume|weight)?\s*[:\-]?\s*([\d.]+)\s*(ml|grams?|cc)', 'prostate'),
    ]
    
    results = []
    seen = set()
    
    for pattern, mtype in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                if mtype == 'organ':
                    test_name = match.group(1).title() + " Size"
                    value = match.group(2)
                    unit = match.group(3)
                elif mtype == 'kidney':
                    test_name = match.group(1).title() + " Size"
                    value = match.group(2)
                    unit = match.group(3)
                elif mtype == 'stone':
                    test_name = match.group(1).title() + " Size"
                    value = match.group(2)
                    unit = match.group(3)
                elif mtype == 'prostate':
                    test_name = "Prostate Size"
                    value = match.group(1)
                    unit = match.group(2)
                
                test_name = str(test_name)
                value = str(value)
                unit = str(unit)
                
                key = f"{test_name}_{value}_{unit}"
                if key not in seen:
                    seen.add(key)
                    results.append({
                        "test_name": test_name,
                        "test_value": value,
                        "units": unit,
                        "reference_range": "",
                        "extraction_method": "regex"
                    })
            except Exception as e:
                print(f"  Regex extraction error for match: {e}")
                continue
    
    return results

def check_if_scanned_image(pdf_path: str) -> tuple[bool, str]:
    """Check if PDF is scanned and use OCR if needed."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        if len(text.strip()) < 100:
            print("⚠️  Scanned document detected, using OCR...")
            
            if not OCR_AVAILABLE:
                return True, None
            
            try:
                import pdf2image
                images = pdf2image.convert_from_path(pdf_path)
                
                ocr_text = ""
                for i, img in enumerate(images):
                    print(f"   Processing page {i+1}/{len(images)}...")
                    temp_img = f"temp_page_{i}.png"
                    img.save(temp_img)
                    
                    cv_img = cv2.imread(temp_img)
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                    
                    page_text = pytesseract.image_to_string(gray, lang='eng')
                    if page_text:
                        ocr_text += page_text + "\n\n"
                    
                    if os.path.exists(temp_img):
                        os.remove(temp_img)
                
                return True, ocr_text if ocr_text else None
            except Exception as e:
                print(f"OCR failed: {e}")
                return True, None
        
        return False, text
    except Exception as e:
        print(f"Error: {e}")
        return False, None

# ============================================================================
# ENHANCED REFERENCE EXTRACTION
# ============================================================================

def extract_reference_from_report(test_name: str, raw_text: str, llm) -> dict:
    """Try to extract reference range from the report itself."""
    prompt = f"""
Look at this medical report and find if there's a reference range mentioned for "{test_name}".

Report excerpt:
{raw_text[:3000]}

Search for patterns like:
- "Normal range: X-Y"
- "Reference: X-Y"
- "(X-Y)" next to the test
- "Normal: X-Y"

Return JSON:
{{
  "found": true/false,
  "low": <number or null>,
  "high": <number or null>,
  "unit": "<unit or null>",
  "confidence": "high"/"medium"/"low"
}}

If you cannot find a reference range for this specific test, return found: false.
Return ONLY valid JSON.
"""
    
    try:
        response = llm.invoke(prompt)
        json_match = re.search(r'\{.*?\}', response.content, re.DOTALL)
        
        if json_match:
            result = json.loads(json_match.group())
            if result.get("found") and result.get("low") is not None and result.get("high") is not None:
                return result
    except Exception as e:
        print(f"  Error extracting reference from report: {e}")
    
    return {"found": False}

def get_comprehensive_explanation(test_name: str, value: str, units: str, 
                                 category: str, llm) -> dict:
    """Generate comprehensive explanation for tests without standard references."""
    prompt = f"""
You are a medical expert. Provide comprehensive information about this test result.

Test: {test_name}
Value: {value} {units}
Report Type: {category}

Provide detailed response:

1. **What This Measures**: Brief explanation (2-3 sentences)
2. **Typical Range**: Based on medical knowledge, what's a typical/normal range? Be specific with numbers if possible.
3. **Your Result**: Interpretation of the value {value} {units}
4. **Clinical Significance**: What does this value potentially indicate?
5. **When to Be Concerned**: What values would be concerning?
6. **Recommendation**: Should patient discuss with doctor?

Format as JSON:
{{
  "description": "What this measures",
  "estimated_range": "Typical range with units (e.g., '20-30 ml')",
  "interpretation": "Interpretation of this specific value",
  "clinical_significance": "What this means clinically",
  "concern_level": "low/medium/high",
  "doctor_consultation": "yes/no and brief reason",
  "additional_context": "Any other relevant information"
}}

Be specific, helpful, and medically accurate. Return ONLY valid JSON.
"""
    
    try:
        response = llm.invoke(prompt)
        json_match = re.search(r'\{.*?\}', response.content, re.DOTALL)
        
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"  Error generating explanation: {e}")
    
    return {
        "description": f"This measures {test_name}",
        "estimated_range": "Please consult your doctor for typical ranges",
        "interpretation": f"Your value is {value} {units}",
        "clinical_significance": "Clinical interpretation needed",
        "concern_level": "medium",
        "doctor_consultation": "yes - for proper interpretation",
        "additional_context": "Discuss with your healthcare provider"
    }

def get_reference_with_learning(test_name: str, gender: str, raw_text: str, llm) -> tuple:
    """
    Enhanced reference lookup with 4-level fallback:
    1. Standard database
    2. Learned ranges
    3. Extract from report
    4. AI explanation
    """
    # Level 1: Standard database
    ref_range = get_reference_range(test_name, gender)
    if ref_range:
        return ref_range, "standard", None
    
    # Level 2: Learned ranges
    learned = load_learned_ranges()
    test_name_normalized = test_name.lower().strip()
    
    if test_name_normalized in learned:
        learned_range = learned[test_name_normalized]
        return {
            "low": learned_range["low"],
            "high": learned_range["high"],
            "unit": learned_range["unit"]
        }, "learned", None
    
    # Level 3: Extract from report
    print(f"  Attempting to extract reference for: {test_name}")
    extracted = extract_reference_from_report(test_name, raw_text, llm)
    if extracted.get("found"):
        save_learned_range(
            test_name_normalized,
            extracted["low"],
            extracted["high"],
            extracted["unit"],
            source="extracted_from_report"
        )
        
        return {
            "low": extracted["low"],
            "high": extracted["high"],
            "unit": extracted["unit"]
        }, "extracted", None
    
    # Level 4: No reference found
    return None, "no_reference", None

# ============================================================================
# EXTRACTION WITH VALIDATION
# ============================================================================

def extract_with_llm(raw_text: str, llm, category: str) -> List[dict]:
    """Extract using LLM with context awareness."""
    
    category_instructions = {
        "imaging": "Extract anatomical measurements with units (cm, mm, ml, grams). Include organ sizes and any calculi/stones found.",
        "lab": "Extract laboratory test results with numeric values and units.",
        "mixed": "Extract both laboratory values and imaging measurements."
    }
    
    instruction = category_instructions.get(category, "Extract medical test results.")
    
    prompt = f"""
You are a medical report parser. Extract ALL actual test results and measurements from this report.

DOCUMENT TYPE: {category.upper()} REPORT
{instruction}

RULES:
1. Extract ONLY tests/measurements EXPLICITLY mentioned
2. DO NOT extract demographics (name, age, gender, address)
3. DO NOT extract metadata (date, page numbers, report IDs)
4. Each entry MUST have a numeric value
5. Include the unit of measurement
6. For imaging: include organ names with "Size", "Length", or "Volume"
7. For stones/calculi: include the size with "Calculus Size" or "Stone Size"

Report Text:
{raw_text[:8000]}

Return JSON array:
[
  {{
    "test_name": "Exact name from report",
    "test_value": "Numeric value",
    "units": "Unit (cm, mm, ml, mg/dL, etc.)",
    "reference_range": "If provided"
  }}
]

Return ONLY the JSON array.
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        json_match = re.search(r'\[.*?\]', content, re.DOTALL)
        if not json_match:
            return []
        
        extracted = json.loads(json_match.group())
        
        validated = []
        for item in extracted:
            test_name = str(item.get("test_name", "")).strip()
            test_value = str(item.get("test_value", "")).strip()
            units = str(item.get("units", "")).strip()
            
            if is_valid_medical_entry(test_name, test_value, category):
                validated.append({
                    "test_name": test_name,
                    "test_value": test_value,
                    "units": units,
                    "reference_range": str(item.get("reference_range", "")).strip(),
                    "extraction_method": "llm"
                })
        
        return validated
        
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return []

# ============================================================================
# GRAPH NODES
# ============================================================================

def parse_pdf_node(state: GraphState) -> GraphState:
    """Parse PDF with OCR support."""
    print("\n" + "="*60)
    print("NODE: PARSING PDF")
    print("="*60)
    
    try:
        is_scanned, raw_text = check_if_scanned_image(state["pdf_path"])
        
        if not raw_text or not raw_text.strip():
            return {**state, "error": "PDF empty or unreadable"}
        
        print(f"✓ Extracted {len(raw_text)} characters")
        if is_scanned:
            print("✓ Used OCR")
        
        category = detect_document_category(raw_text)
        print(f"✓ Category: {category}")
        
        return {
            **state, 
            "raw_text": raw_text,
            "is_scanned_image": is_scanned,
            "document_category": category
        }
    
    except Exception as e:
        return {**state, "error": str(e)}

def extract_patient_info_node(state: GraphState) -> GraphState:
    """Extract patient info."""
    print("\n" + "="*60)
    print("NODE: EXTRACTING PATIENT INFO")
    print("="*60)
    
    if state.get("error"):
        return state
    
    prompt = f"""
Extract patient information from this report.

Text:
{state['raw_text'][:1500]}

Return JSON with these fields:
{{
  "name": "Patient full name or 'Unknown' if not found",
  "age": <number or null>,
  "gender": "male"/"female"/"unknown"
}}

IMPORTANT:
- Extract the patient's name if clearly mentioned (e.g., "Patient Name:", "Name:", in header)
- Do NOT extract doctor names, hospital names, or report IDs
- If multiple names appear, choose the one labeled as "Patient"
- Return "Unknown" for name if not clearly identifiable

Return ONLY valid JSON.
"""
    
    try:
        response = llm.invoke(prompt)
        json_match = re.search(r'\{.*?\}', response.content, re.DOTALL)
        
        if json_match:
            patient_info = json.loads(json_match.group())
            # Ensure all fields exist
            if "name" not in patient_info:
                patient_info["name"] = "Unknown"
            if "age" not in patient_info:
                patient_info["age"] = None
            if "gender" not in patient_info:
                patient_info["gender"] = "unknown"
        else:
            patient_info = {"name": "Unknown", "age": None, "gender": "unknown"}
        
        print(f"✓ Patient: Patient: Name={patient_info.get('name', 'Unknown')}, Age={patient_info.get('age', 'N/A')}, Gender={patient_info.get('gender', 'unknown')}")
        return {**state, "patient_info": patient_info}
    
    except:
        return {**state, "patient_info": {"name": "Unknown", "age": None, "gender": "unknown"}}

def classify_document_node(state: GraphState) -> GraphState:
    """Classify document structure."""
    print("\n" + "="*60)
    print("NODE: CLASSIFYING DOCUMENT")
    print("="*60)
    
    if state.get("error"):
        return {**state, "document_type": "error"}
    
    doc_type = "semi-structured"
    
    print(f"✓ Classified as: {doc_type}")
    return {**state, "document_type": doc_type}

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
    """Extract with multiple methods."""
    print("\n" + "="*60)
    print("NODE: EXTRACTING DATA")
    print("="*60)
    
    category = state.get("document_category", "mixed")
    raw_text = state["raw_text"]

    # DEBUG: Print first 500 chars of raw text
    # print("\n=== DEBUG: Raw Text Sample ===")
    # print(raw_text[:500])
    # print("=" * 60)
    
    # llm_results = extract_with_llm(raw_text, llm, category)
    
    # DEBUG: Print LLM results
    # print(f"\n=== DEBUG: LLM Extracted {len(llm_results)} items ===")
    # if llm_results:
    #     print(json.dumps(llm_results[:3], indent=2))
    
    # regex_results = []
    # if category in ["imaging", "mixed"]:
    #     regex_results = extract_imaging_measurements(raw_text)
    
    # DEBUG: Print regex results
    # print(f"\n=== DEBUG: Regex Extracted {len(regex_results)} items ===")
    # if regex_results:
    #     print(json.dumps(regex_results[:3], indent=2))
    
    llm_results = extract_with_llm(raw_text, llm, category)
    
    regex_results = []
    if category in ["imaging", "mixed"]:
        regex_results = extract_imaging_measurements(raw_text)
    
    all_results = llm_results + regex_results
    
    unique_results = []
    seen = set()
    for item in all_results:
        key = f"{item.get('test_name','')}_{item.get('test_value','')}"
        if key not in seen:
            seen.add(key)
            unique_results.append(item)
    
    if not unique_results:
        return {**state, "error": "No tests extracted"}
    
    print(f"✓ Extracted {len(unique_results)} entries")
    print(f"   - LLM: {len(llm_results)}, Regex: {len(regex_results)}")
    
    return {
        **state,
        "extracted_data": unique_results,
        "extraction_confidence": min(1.0, len(unique_results) / 30)
    }

def extract_unstructured_data_node(state: GraphState) -> GraphState:
    """Extract data from unstructured text."""
    print("\n" + "="*60)
    print("NODE: EXTRACTING UNSTRUCTURED DATA")
    print("="*60)
    
    return extract_semi_structured_data_node(state)


def validate_extraction_node(state: GraphState) -> GraphState:
    """Validate extracted data."""
    print("\n" + "="*60)
    print("NODE: VALIDATING")
    print("="*60)
    
    if state.get("error"):
        return state
    
    extracted = state.get("extracted_data", [])
    category = state.get("document_category", "mixed")
    
    if not extracted:
        print("⚠️  No data to validate")
        return {**state, "error": "No tests extracted"}
    
    validated = []
    issues = []
    
    for i, result in enumerate(extracted):
        try:
            test_name = str(result.get("test_name", "")).strip()
            test_value = str(result.get("test_value", "")).strip()
            units = str(result.get("units", "")).strip()
            
            if not test_name or not test_value:
                issues.append(f"Entry {i+1}: Missing name or value")
                continue
            
            if not is_valid_medical_entry(test_name, test_value, category):
                issues.append(f"Entry {i+1}: Invalid - {test_name}")
                continue
            
            validated.append({
                "test_name": test_name,
                "test_value": test_value,
                "units": units,
                "reference_range": str(result.get("reference_range", "")).strip(),
                "extraction_method": result.get("extraction_method", "unknown")
            })
        except Exception as e:
            print(f"  Validation error for entry {i+1}: {e}")
            issues.append(f"Entry {i+1}: Validation error - {e}")
            continue
    
    if issues:
        print(f"⚠️  {len(issues)} issues")
        for issue in issues[:3]:
            print(f"    {issue}")
    
    if not validated:
        print("❌ No valid entries after validation")
        return {**state, "error": "No valid tests after validation"}
    
    print(f"✓ Validated {len(validated)} entries")
    return {**state, "validated_data": validated, "validation_issues": issues}

def analyze_results_node(state: GraphState) -> GraphState:
    """Enhanced analysis with intelligent reference handling."""
    print("\n" + "="*60)
    print("NODE: ANALYZING (ENHANCED)")
    print("="*60)
    
    if state.get("error"):
        return state
    
    patient_gender = state.get("patient_info", {}).get("gender", "unknown")
    validated = state.get("validated_data", [])
    raw_text = state.get("raw_text", "")
    category = state.get("document_category", "mixed")
    
    analyzed = []
    missing_explanations = {}
    
    stats = {
        "standard_db": 0,
        "learned": 0,
        "extracted": 0,
        "ai_explained": 0
    }
    
    for result in validated:
        test_name_raw = result.get("test_name", "")
        test_value = result.get("test_value", "")
        units = result.get("units", "")
        
        test_name = normalize_test_name(test_name_raw)
        numeric_value = extract_numeric_value(test_value)
        
        if numeric_value is None:
            analyzed.append({
                **result,
                "normalized_name": test_name,
                "numeric_value": None,
                "status": "unknown",
                "analysis": "Non-numeric value",
                "confidence": "low"
            })
            continue
        
        # Enhanced reference lookup
        ref_range, source, _ = get_reference_with_learning(
            test_name, patient_gender, raw_text, llm
        )
        
        if ref_range:
            low = ref_range["low"]
            high = ref_range["high"]
            ref_unit = ref_range.get("unit", units)
            
            if numeric_value < low:
                status = "low"
                analysis = f"Below normal range ({low}-{high} {ref_unit})"
            elif numeric_value > high:
                status = "high"
                analysis = f"Above normal range ({low}-{high} {ref_unit})"
            else:
                status = "normal"
                analysis = f"Within normal range ({low}-{high} {ref_unit})"
            
            confidence = "high" if source == "standard" else "medium"
            
            if source == "extracted":
                analysis += " (range extracted from report)"
                stats["extracted"] += 1
            elif source == "learned":
                analysis += " (using previously learned range)"
                stats["learned"] += 1
            else:
                stats["standard_db"] += 1
        
        else:
            # No reference - use AI explanation
            status = "no_reference"
            
            print(f"  Generating AI explanation for: {test_name_raw}")
            comprehensive = get_comprehensive_explanation(
                test_name_raw, test_value, units, category, llm
            )
            
            analysis = f"{comprehensive['interpretation']}"
            if comprehensive.get('estimated_range') and comprehensive['estimated_range'] != "varies by individual":
                analysis += f". Typical range: {comprehensive['estimated_range']}"
            
            confidence = "medium"
            missing_explanations[test_name_raw] = comprehensive
            stats["ai_explained"] += 1
        
        analyzed.append({
            **result,
            "normalized_name": test_name,
            "numeric_value": numeric_value,
            "status": status,
            "analysis": analysis,
            "reference_range": f"{low}-{high} {ref_unit}" if ref_range else "See detailed explanation below",
            "confidence": confidence,
            "reference_source": source if ref_range else "ai_generated"
        })
    
    # Statistics
    normal = sum(1 for r in analyzed if r["status"] == "normal")
    abnormal = sum(1 for r in analyzed if r["status"] in ["high", "low"])
    no_ref = sum(1 for r in analyzed if r["status"] == "no_reference")
    
    print(f"✓ Analysis complete:")
    print(f"   Normal: {normal}, Abnormal: {abnormal}, No Ref: {no_ref}")
    print(f"   Reference sources:")
    print(f"   - Standard DB: {stats['standard_db']}")
    print(f"   - Learned: {stats['learned']}")
    print(f"   - Extracted: {stats['extracted']}")
    print(f"   - AI Explained: {stats['ai_explained']}")
    
    return {
        **state,
        "analyzed_results": analyzed,
        "missing_ranges_explanation": missing_explanations
    }

def summarize_report_node(state: GraphState) -> GraphState:
    """Generate comprehensive summary."""
    print("\n" + "="*60)
    print("NODE: SUMMARIZING")
    print("="*60)
    
    if state.get("error"):
        return state
    
    analyzed = state.get("analyzed_results", [])
    patient = state.get("patient_info", {})
    category = state.get("document_category", "mixed")
    missing_explanations = state.get("missing_ranges_explanation", {})
    
    normal_count = sum(1 for r in analyzed if r.get("status") == "normal")
    abnormal_count = sum(1 for r in analyzed if r.get("status") in ["high", "low"])
    no_ref_count = sum(1 for r in analyzed if r.get("status") == "no_reference")
    
    high_results = [r for r in analyzed if r.get("status") == "high"]
    low_results = [r for r in analyzed if r.get("status") == "low"]
    no_ref_results = [r for r in analyzed if r.get("status") == "no_reference"]
    
    has_stones = any("calculus" in r.get("test_name", "").lower() or 
                     "stone" in r.get("test_name", "").lower() 
                     for r in analyzed)
    
    # Prepare detailed info for tests without references
    no_ref_details = ""
    if no_ref_results and missing_explanations:
        no_ref_details = "\n\nTESTS REQUIRING DETAILED EXPLANATION:\n"
        for result in no_ref_results:
            test_name = result.get("test_name", "")
            if test_name in missing_explanations:
                explanation = missing_explanations[test_name]
                no_ref_details += f"\n- {test_name}: {result.get('test_value')} {result.get('units')}\n"
                no_ref_details += f"  Description: {explanation.get('description', '')}\n"
                no_ref_details += f"  Typical Range: {explanation.get('estimated_range', '')}\n"
                no_ref_details += f"  Interpretation: {explanation.get('interpretation', '')}\n"
    
    prompt = f"""
Create a clear, empathetic, comprehensive summary of this {category} report for the patient.

**Patient Information:**
- Name: {patient.get('name', 'Unknown')}
- Age: {patient.get('age', 'N/A')}
- Gender: {patient.get('gender', 'unknown')}
Total findings: {len(analyzed)}
Normal: {normal_count}
High: {len(high_results)}
Low: {len(low_results)}
Requiring explanation: {no_ref_count}

All Results:
{json.dumps(analyzed, indent=2)}
{no_ref_details}

Write a comprehensive, empathetic summary with these sections:

## Overall Assessment
(Start with reassuring tone, mention what was evaluated)

## What Was Measured
(Brief explanation of what these tests/measurements mean)

## Key Findings

### Tests Within Normal Range
(List all normal results briefly - be reassuring)

### Results Requiring Attention
(For HIGH/LOW results, explain each one clearly)

### Special Measurements
(For tests without standard ranges, use the detailed explanations provided above. 
Present the information in a clear, non-alarming way. Include the typical ranges and 
interpretations that were provided.)

**IMPORTANT GUIDELINES**: 
- For NORMAL results: Clearly state "This is within the healthy range"
- For HIGH results: Explain what this might indicate
- For LOW results: Explain what this might indicate
- For tests without standard ranges: Use the detailed explanations provided, be thorough but reassuring
- For stones/calculi: Explain size significance (stones <5mm often pass naturally)
- Never say "no reference range available" - instead use the provided explanations
- Be specific with numbers and ranges

## What This Means for You
(Practical implications in everyday language)

## Next Steps
(What the patient should do - doctor consultation timing, etc.)

Guidelines:
- Use warm, conversational, supportive tone
- Avoid medical jargon or explain it simply
- Use analogies when helpful
- Be honest but reassuring
- Short paragraphs for easy reading
- For tests without standard ranges, present information confidently using the AI explanations

Write the summary now:
"""
    
    try:
        response = llm.invoke(prompt)
        print("✓ Comprehensive summary generated")
        return {**state, "summarized_report": response.content}
    except Exception as e:
        print(f"Error generating summary: {e}")
        fallback = f"""
## Overall Assessment
We've analyzed your {category} report with {len(analyzed)} findings.

## Results Summary
- Normal findings: {normal_count}
- Findings needing attention: {abnormal_count}
- Specialized measurements: {no_ref_count}

## What To Do Next
Please schedule an appointment with your healthcare provider to discuss these results in detail.
"""
        return {**state, "summarized_report": fallback}

def generate_recommendations_node(state: GraphState) -> GraphState:
    """Generate context-aware recommendations."""
    print("\n" + "="*60)
    print("NODE: RECOMMENDATIONS")
    print("="*60)
    
    if state.get("error"):
        return state
    
    analyzed = state.get("analyzed_results", [])
    abnormal = [r for r in analyzed if r.get("status") in ["high", "low"]]
    category = state.get("document_category", "mixed")
    patient = state.get("patient_info", {})
    
    has_kidney_stones = any("calculus" in r.get("test_name", "").lower() or 
                           "stone" in r.get("test_name", "").lower() or
                           "echogenic" in r.get("test_name", "").lower()
                           for r in analyzed)
    
    large_stones = [r for r in analyzed 
                    if ("calculus" in r.get("test_name", "").lower() or 
                        "stone" in r.get("test_name", "").lower()) 
                    and r.get("numeric_value", 0) > 5]
    
    if not abnormal and not has_kidney_stones:
        recommendations = """
## Recommendations

✅ **Excellent News!**
All your measurements are within normal healthy ranges.

### Maintain Your Health:
- **Hydration**: Drink 8-10 glasses of water daily
- **Balanced Diet**: Include plenty of fruits and vegetables
- **Regular Exercise**: Aim for 150 minutes per week of moderate activity
- **Adequate Sleep**: Get 7-9 hours of quality sleep
- **Stress Management**: Practice relaxation techniques
- **Regular Check-ups**: Schedule annual health screenings

### Follow-Up:
- Annual physical examination
- Continue monitoring as recommended by your healthcare provider
"""
        return {**state, "recommendations": recommendations}
    
    if has_kidney_stones:
        prompt = f"""
Based on this imaging report showing kidney stones/calculi, provide specific lifestyle recommendations.

**Patient Information:**
- Name: {patient.get('name', 'Unknown')}
- Age: {patient.get('age', 'unknown')}
- Gender: {patient.get('gender', 'unknown')}Findings:
{json.dumps([r for r in analyzed if 'calculus' in r.get('test_name', '').lower() or 'stone' in r.get('test_name', '').lower()], indent=2)}

Provide practical recommendations in these sections:

## Dietary Recommendations
(Specific foods to eat/avoid for kidney stone prevention)

## Hydration Guidelines
(Detailed fluid intake recommendations)

## Lifestyle Modifications
(Exercise, habits that help prevent stones)

## Medical Follow-Up
(When to see a doctor, urgency level based on stone size)

## Warning Signs
(Symptoms that require immediate medical attention)

Be specific, practical, and reassuring. Use bullet points.
Keep language simple and actionable.
"""
    else:
        prompt = f"""
Based on these {category} findings, provide general wellness recommendations.

**Patient Information:**
- Name: {patient.get('name', 'Unknown')}
- Age: {patient.get('age', 'unknown')}
- Gender: {patient.get('gender', 'unknown')}Abnormal Results:
{json.dumps(abnormal, indent=2)}

Provide recommendations in sections:

## General Health Guidance
(Overall lifestyle recommendations)

## Dietary Suggestions
(If applicable to the findings)

## When to Consult a Doctor
(Urgency and what to discuss)

## Monitoring
(What to watch for)

Be supportive, specific, and practical.
Use bullet points for readability.
"""
    
    try:
        response = llm.invoke(prompt)
        print("✓ Context-aware recommendations generated")
        return {**state, "recommendations": response.content}
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        fallback = """
## Recommendations

### General Health Guidance:
- Maintain a balanced, nutritious diet
- Stay well-hydrated (8-10 glasses of water daily)
- Exercise regularly (150 minutes per week)
- Get adequate sleep (7-9 hours nightly)
- Manage stress through relaxation techniques
- Avoid smoking and limit alcohol

### Follow-Up:
- Schedule an appointment with your healthcare provider to discuss these results
- Bring this report to your appointment
- Ask your doctor about any concerns or questions you have

### When to Seek Immediate Care:
- Severe pain
- Persistent symptoms
- Fever or infection signs
- Any symptoms that concern you
"""
        return {**state, "recommendations": fallback}

def handle_error_node(state: GraphState) -> GraphState:
    """Handle errors."""
    print("\n" + "="*60)
    print("ERROR HANDLER")
    print("="*60)
    print(f"Error: {state.get('error', 'Unknown')}")
    return state

# ============================================================================
# BUILD GRAPH
# ============================================================================

def route_document(state: GraphState) -> str:
    if state.get("error"):
        return "error"
    return "extract_semi_structured"

workflow = StateGraph(GraphState)

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

workflow.add_edge("validate_extraction", "analyze_results")
workflow.add_edge("analyze_results", "summarize_report")
workflow.add_edge("summarize_report", "generate_recommendations")
workflow.add_edge("generate_recommendations", END)
workflow.add_edge("handle_error", END)

app = workflow.compile()
print("Workflow compiled!")

# ============================================================================
# PDF GENERATION
# ============================================================================

def generate_pdf_report(output: dict, filename: str = "medical_report.pdf"):
    """Generate PDF report with enhanced handling of missing references."""
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    elements = []
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(name='CustomTitle', parent=styles['Heading1'],
                             fontSize=24, textColor=colors.HexColor('#2c3e50'),
                             spaceAfter=30, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='SectionHeader', parent=styles['Heading2'],
                             fontSize=14, textColor=colors.HexColor('#34495e'),
                             spaceAfter=12, spaceBefore=12))
    styles.add(ParagraphStyle(name='CustomBody', parent=styles['BodyText'],
                             fontSize=10, alignment=TA_JUSTIFY, spaceAfter=12))
    
    elements.append(Paragraph("Medical Report Analysis", styles['CustomTitle']))
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # Patient Info
    # Patient Info
    elements.append(Paragraph("Patient Information", styles['SectionHeader']))
    patient = output.get("patient_info", {})
    patient_data = [
        ["Name:", patient.get('name', 'Unknown')],
        ["Age:", str(patient.get('age', 'N/A'))],
        ["Gender:", patient.get('gender', 'Unknown').capitalize()],
    ]
    patient_table = Table(patient_data, colWidths=[1.5*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
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
        ["Total:", str(stats.get('total_tests', 0))],
        ["Normal:", str(stats.get('normal_count', 0))],
        ["Abnormal:", str(stats.get('abnormal_count', 0))],
        ["Requiring Explanation:", str(stats.get('no_reference_count', 0))],
    ]
    stats_table = Table(stats_data, colWidths=[2*inch, 1.5*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Abnormal Results
    abnormal = [r for r in output.get("detailed_results", []) if r.get("status") in ["high", "low"]]
    
    if abnormal:
        elements.append(Paragraph("⚠️ Key Abnormal Results", styles['SectionHeader']))
        for result in abnormal:
            test_name = result.get('test_name', 'Unknown')
            value = f"{result.get('test_value', 'N/A')} {result.get('units', '')}"
            status = result.get('status', 'unknown').upper()
            ref_range = result.get('reference_range', 'N/A')
            analysis = result.get('analysis', 'No analysis')
            
            elements.append(Paragraph(f"<b>{test_name}</b>", styles['CustomBody']))
            elements.append(Paragraph(f"Value: {value} | Status: {status}", styles['Normal']))
            elements.append(Paragraph(f"Normal Range: {ref_range}", styles['Normal']))
            elements.append(Paragraph(analysis, styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))
    
    # Tests requiring detailed explanation
    no_ref = [r for r in output.get("detailed_results", []) if r.get("status") == "no_reference"]
    
    if no_ref:
        elements.append(PageBreak())
        elements.append(Paragraph("Specialized Measurements - Detailed Explanation", styles['SectionHeader']))
        elements.append(Paragraph(
            "These measurements have been analyzed using advanced medical knowledge. "
            "The interpretations below are based on current medical understanding.",
            styles['CustomBody']
        ))
        elements.append(Spacer(1, 0.2*inch))
        
        explanations = output.get("missing_ranges_explanation", {})
        for result in no_ref:
            test_name = result.get('test_name', 'Unknown')
            value = f"{result.get('test_value', 'N/A')} {result.get('units', '')}"
            explanation = explanations.get(test_name, {})
            
            elements.append(Paragraph(f"<b>{test_name}</b>: {value}", styles['CustomBody']))
            
            if explanation:
                elements.append(Paragraph(f"<b>What This Measures:</b> {explanation.get('description', '')}", styles['Normal']))
                elements.append(Paragraph(f"<b>Typical Range:</b> {explanation.get('estimated_range', '')}", styles['Normal']))
                elements.append(Paragraph(f"<b>Your Result:</b> {explanation.get('interpretation', '')}", styles['Normal']))
                elements.append(Paragraph(f"<b>Clinical Significance:</b> {explanation.get('clinical_significance', '')}", styles['Normal']))
                
                if explanation.get('concern_level') == 'high':
                    elements.append(Paragraph(f"<b>⚠️ Recommendation:</b> {explanation.get('doctor_consultation', '')}", styles['Normal']))
                else:
                    elements.append(Paragraph(f"<b>Recommendation:</b> {explanation.get('doctor_consultation', '')}", styles['Normal']))
            
            elements.append(Spacer(1, 0.15*inch))
    
    # Summary
    elements.append(PageBreak())
    elements.append(Paragraph("Detailed Summary", styles['SectionHeader']))
    summary = output.get("summary", "No summary available.")
    
    for para in summary.split('\n\n'):
        if para.strip():
            clean = para.strip().replace('#', '').replace('**', '')
            if clean:
                elements.append(Paragraph(clean, styles['CustomBody']))
    
    # Recommendations
    elements.append(PageBreak())
    elements.append(Paragraph("Recommendations", styles['SectionHeader']))
    recs = output.get("recommendations", "No recommendations.")
    
    for para in recs.split('\n\n'):
        if para.strip():
            clean = para.strip().replace('#', '').replace('**', '')
            if clean:
                elements.append(Paragraph(clean, styles['CustomBody']))
    
    # Disclaimer
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("DISCLAIMER", styles['SectionHeader']))
    disclaimer = (
        "This analysis is for informational purposes only and does not constitute "
        "medical advice. Always consult your healthcare provider for proper "
        "interpretation and treatment recommendations. AI-generated explanations "
        "are based on general medical knowledge and should be verified by a qualified healthcare professional."
    )
    elements.append(Paragraph(disclaimer, styles['CustomBody']))
    
    try:
        doc.build(elements)
        print(f"✓ PDF report generated: {filename}")
    except Exception as e:
        print(f"⚠️  PDF generation failed: {e}")

# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def generate_user_friendly_output(final_state: dict) -> dict:
    """Convert to user-friendly format."""
    
    if final_state.get("error"):
        return {
            "success": False,
            "message": "Issue processing your report.",
            "details": final_state["error"],
            "suggestion": "Ensure PDF is readable and contains medical results."
        }
    
    analyzed = final_state.get("analyzed_results", [])
    
    return {
        "success": True,
        "patient_info": final_state.get("patient_info", {}),
        "summary": final_state.get("summarized_report", ""),
        "recommendations": final_state.get("recommendations", ""),
        "raw_extracted_tests": {
            r["normalized_name"]: r["numeric_value"]
            for r in analyzed if r.get("numeric_value") is not None
        },
        "statistics": {
            "total_tests": len(analyzed),
            "normal_count": sum(1 for r in analyzed if r.get("status") == "normal"),
            "abnormal_count": sum(1 for r in analyzed if r.get("status") in ["high", "low"]),
            "unknown_count": sum(1 for r in analyzed if r.get("status") == "unknown"),
            "no_reference_count": sum(1 for r in analyzed if r.get("status") == "no_reference"),
        },
        "detailed_results": analyzed,
        "validation_issues": final_state.get("validation_issues", []),
        "confidence_summary": {
            "high_confidence": sum(1 for r in analyzed if r.get("confidence") == "high"),
            "medium_confidence": sum(1 for r in analyzed if r.get("confidence") == "medium"),
            "low_confidence": sum(1 for r in analyzed if r.get("confidence") == "low")
        },
        "missing_ranges_explanation": final_state.get("missing_ranges_explanation", {}),
        "is_scanned": final_state.get("is_scanned_image", False),
        "extraction_confidence": final_state.get("extraction_confidence", 0.0),
        "document_category": final_state.get("document_category", "unknown")
    }

def print_results_summary(output: dict):
    """Print beautiful summary."""
    
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
    
    # Patient
    patient = output.get("patient_info", {})
    print("\n👤 PATIENT INFORMATION")
    print("-"*80)
    print(f"Name: {patient.get('name', 'Unknown')}")
    print(f"Age: {patient.get('age', 'N/A')}")
    print(f"Gender: {patient.get('gender', 'Unknown').capitalize()}")
    print(f"Document Type: {output.get('document_category', 'Unknown').title()}")
    
    # Stats
    stats = output.get("statistics", {})
    print("\n📊 TEST STATISTICS")
    print("-"*80)
    print(f"Total Tests: {stats.get('total_tests', 0)}")
    print(f"✅ Normal: {stats.get('normal_count', 0)}")
    print(f"⚠️  Abnormal: {stats.get('abnormal_count', 0)}")
    print(f"ℹ️  Requiring Explanation: {stats.get('no_reference_count', 0)}")
    print(f"❓ Unknown: {stats.get('unknown_count', 0)}")
    
    # Confidence
    conf = output.get("confidence_summary", {})
    print(f"\nExtraction Confidence: {output.get('extraction_confidence', 0):.1%}")
    print(f"High: {conf.get('high_confidence', 0)} | "
          f"Medium: {conf.get('medium_confidence', 0)} | "
          f"Low: {conf.get('low_confidence', 0)}")
    
    # Reference sources
    results = output.get("detailed_results", [])
    std_db = sum(1 for r in results if r.get("reference_source") == "standard")
    learned = sum(1 for r in results if r.get("reference_source") == "learned")
    extracted = sum(1 for r in results if r.get("reference_source") == "extracted")
    ai_gen = sum(1 for r in results if r.get("reference_source") == "ai_generated")
    
    print(f"\nReference Sources:")
    print(f"📚 Standard Database: {std_db}")
    if learned > 0:
        print(f"🧠 Learned Ranges: {learned}")
    if extracted > 0:
        print(f"📄 Extracted from Report: {extracted}")
    if ai_gen > 0:
        print(f"🤖 AI Explained: {ai_gen}")
    
    # Key abnormals
    abnormal = [r for r in results if r.get("status") in ["high", "low"]]
    
    if abnormal:
        print("\n⚠️  KEY ABNORMAL RESULTS")
        print("-"*80)
        for result in abnormal[:5]:
            icon = "📈" if result.get("status") == "high" else "📉"
            print(f"{icon} {result.get('test_name', 'Unknown')}: "
                  f"{result.get('test_value', 'N/A')} {result.get('units', '')}")
            print(f"   Status: {result.get('status', 'unknown').upper()}")
            print(f"   Normal: {result.get('reference_range', 'N/A')}")
            print(f"   {result.get('analysis', 'No analysis')}")
            print()
    
    # Tests with AI explanations
    no_ref = [r for r in results if r.get("status") == "no_reference"]
    if no_ref:
        print("\nℹ️  SPECIALIZED MEASUREMENTS (AI EXPLAINED)")
        print("-"*80)
        for result in no_ref:
            print(f"🔬 {result.get('test_name', 'Unknown')}: "
                  f"{result.get('test_value', 'N/A')} {result.get('units', '')}")
            print(f"   {result.get('analysis', 'See detailed explanation in report')}")
            print()
    
    # All extracted tests
    print("\n📋 ALL EXTRACTED TESTS")
    print("-"*80)
    for i, result in enumerate(results, 1):
        source_icon = {
            "standard": "📚",
            "learned": "🧠", 
            "extracted": "📄",
            "ai_generated": "🤖"
        }.get(result.get("reference_source"), "❓")
        
        print(f"{i}. {result.get('test_name', 'Unknown')}: "
              f"{result.get('test_value', 'N/A')} {result.get('units', '')} "
              f"[{result.get('status', 'unknown').upper()}] {source_icon}")
    
    print("\n" + "="*80)
    print("✅ Analysis complete!")
    print("="*80)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def analyze_medical_report(pdf_path: str):
    """Main function to analyze a medical report."""
    
    print("\n" + "="*80)
    print(" "*20 + "MEDICAL REPORT ANALYZER v5.0")
    print(" "*22 + "Enhanced Edition with AI Fallback")
    print("="*80)
    print(f"\n📄 Processing: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"\n❌ Error: File not found!")
        return None
    
    try:
        # Run workflow
        inputs = {"pdf_path": pdf_path}
        final_state = app.invoke(inputs)
        
        # Generate output
        output = generate_user_friendly_output(final_state)
        
        # output directoy
        output_dir = os.path.dirname(os.path.abspath(__file__))

        # saveing outputs
        # 1. Complete analysis as JSON
        with open(os.path.join(output_dir, "patient_report.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # 2. Detailed results
        if output.get("success"):
            with open(os.path.join(output_dir, "analyzed_results.json"), "w", encoding="utf-8") as f:
                json.dump(output["detailed_results"], f, indent=2, ensure_ascii=False)
            
            # Generate PDF
            generate_pdf_report(output, os.path.join(output_dir, "medical_report_summary.pdf"))
            
            # 4. Keep text summary for backward compatibility
            with open(os.path.join(output_dir, "patient_summary.txt"), "w", encoding="utf-8") as f:
                f.write("="*80 + "\n")
                f.write(" "*25 + "MEDICAL REPORT SUMMARY\n")
                f.write("="*80 + "\n\n")
                
                f.write("PATIENT INFORMATION\n")
                f.write("-"*80 + "\n")
                patient = output.get("patient_info", {})
                f.write(f"Name: {patient.get('name', 'Unknown')}\n")
                f.write(f"Age: {patient.get('age', 'N/A')}\n")
                f.write(f"Gender: {patient.get('gender', 'Unknown').capitalize()}\n")
                f.write(f"Document Type: {output.get('document_category', 'Unknown').title()}\n\n")
                
                f.write("TEST STATISTICS\n")
                f.write("-"*80 + "\n")
                stats = output.get("statistics", {})
                f.write(f"Total Tests: {stats.get('total_tests', 0)}\n")
                f.write(f"Normal Results: {stats.get('normal_count', 0)}\n")
                f.write(f"Abnormal Results: {stats.get('abnormal_count', 0)}\n")
                f.write(f"Specialized Measurements: {stats.get('no_reference_count', 0)}\n\n")
                
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
                
                explanations = output.get("missing_ranges_explanation", {})
                
                for i, result in enumerate(output.get("detailed_results", []), 1):
                    f.write(f"{i}. {result.get('test_name', 'Unknown')}\n")
                    f.write(f"   Value: {result.get('test_value', 'N/A')} {result.get('units', '')}\n")
                    f.write(f"   Status: {result.get('status', 'unknown').upper()}\n")
                    f.write(f"   Normal Range: {result.get('reference_range', 'N/A')}\n")
                    f.write(f"   Analysis: {result.get('analysis', 'No analysis')}\n")
                    
                    # Add detailed explanation if available
                    test_name = result.get('test_name', '')
                    if test_name in explanations:
                        exp = explanations[test_name]
                        f.write(f"\n   DETAILED EXPLANATION:\n")
                        f.write(f"   - What it measures: {exp.get('description', '')}\n")
                        f.write(f"   - Typical range: {exp.get('estimated_range', '')}\n")
                        f.write(f"   - Clinical significance: {exp.get('clinical_significance', '')}\n")
                        f.write(f"   - Recommendation: {exp.get('doctor_consultation', '')}\n")
                    
                    if result.get("confidence") != "high":
                        f.write(f"   Confidence: {result.get('confidence', 'unknown')}\n")
                    
                    source = result.get("reference_source", "unknown")
                    if source == "learned":
                        f.write(f"   Source: Previously learned range\n")
                    elif source == "extracted":
                        f.write(f"   Source: Extracted from this report\n")
                    elif source == "ai_generated":
                        f.write(f"   Source: AI-generated explanation\n")
                    
                    f.write("\n")
                
                f.write("="*80 + "\n")
                f.write("DISCLAIMER\n")
                f.write("="*80 + "\n")
                f.write("This analysis is for informational purposes only and does not constitute\n")
                f.write("medical advice. Always consult with your healthcare provider for proper\n")
                f.write("interpretation of your medical reports and treatment recommendations.\n")
                f.write("AI-generated explanations are based on general medical knowledge and should\n")
                f.write("be verified by a qualified healthcare professional.\n")
        
        # Print summary
        print_results_summary(output)
        
        print("\n" + "="*80)
        print("FILES SAVED:")
        print("  📄 patient_report.json - Complete analysis")
        print("  📄 analyzed_results.json - Detailed test results")
        print("  📄 medical_report_summary.pdf - PDF Report")
        print("  📄 patient_summary.txt - Text summary")
        if os.path.exists(LEARNED_RANGES_FILE):
            learned = load_learned_ranges()
            if learned:
                print(f"  🧠 {LEARNED_RANGES_FILE} - {len(learned)} learned ranges")
        print("="*80)
        
        return output

    except KeyboardInterrupt:
        print("\n\n❌ Analysis interrupted by user")
        return None
    
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Get PDF path
    # if len(sys.argv) > 1:
    #     pdf_path = sys.argv[1]
    # else:
    #     pdf_path = input("Enter path to medical report PDF: ").strip().strip('"')
    
    # if not pdf_path:
    pdf_path = "/Users/_biibekk_/Desktop/Minor Project/reports/Report_Oliver_Rose.pdf"
    
    result = analyze_medical_report(pdf_path)
    
    if result and result.get("success"):
        print(f"\nAnalysis completed successfully!")
        print(f"\nKey Stats:")
        stats = result.get("statistics", {})
        print(f"  - Total Tests: {stats.get('total_tests', 0)}")
        print(f"  - Normal: {stats.get('normal_count', 0)}")
        print(f"  - Abnormal: {stats.get('abnormal_count', 0)}")
        print(f"  - Specialized Measurements: {stats.get('no_reference_count', 0)}")
        
        # Show learned ranges summary
        if os.path.exists(LEARNED_RANGES_FILE):
            learned = load_learned_ranges()
            if learned:
                print(f"\n🧠 System has learned {len(learned)} new reference ranges")
                print(f"   These will be used automatically for future reports!")
    else:
        print(f"\nAnalysis failed.")
        if result:
            print(f"Error: {result.get('details', 'Unknown error')}")

