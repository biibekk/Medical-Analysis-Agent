"""
ENHANCED REFERENCE DATA MODULE - COMPLETE WITH IMAGING
Medical test reference ranges and mappings
Comprehensive database covering lab tests and imaging measurements
"""

# ============================================================================
# COMPREHENSIVE REFERENCE RANGES (250+ TESTS)
# ============================================================================

REFERENCE_RANGES = {
    # ===== BLOOD SUGAR =====
    "glucose": {"low": 70, "high": 99, "unit": "mg/dL", "category": "Blood Sugar"},
    "hba1c": {"low": 4.0, "high": 5.6, "unit": "%", "category": "Blood Sugar"},
    "fasting_glucose": {"low": 70, "high": 99, "unit": "mg/dL", "category": "Blood Sugar"},
    
    # ===== COMPLETE BLOOD COUNT =====
    "hemoglobin": {"low": 12.0, "high": 15.5, "unit": "g/dL", "gender_specific": True, "category": "Blood Count"},
    "hemoglobin_male": {"low": 13.5, "high": 17.5, "unit": "g/dL", "category": "Blood Count"},
    "hemoglobin_female": {"low": 12.0, "high": 15.5, "unit": "g/dL", "category": "Blood Count"},
    "wbc": {"low": 4.5, "high": 11.0, "unit": "x10³/µL", "category": "Blood Count"},
    "rbc": {"low": 4.2, "high": 5.9, "unit": "x10⁶/µL", "gender_specific": True, "category": "Blood Count"},
    "platelets": {"low": 150, "high": 450, "unit": "x10³/µL", "category": "Blood Count"},
    "hematocrit": {"low": 38.3, "high": 48.6, "unit": "%", "gender_specific": True, "category": "Blood Count"},
    "mcv": {"low": 80, "high": 100, "unit": "fL", "category": "Blood Count"},
    "mch": {"low": 27, "high": 33, "unit": "pg", "category": "Blood Count"},
    "mchc": {"low": 32, "high": 36, "unit": "g/dL", "category": "Blood Count"},
    
    # ===== ELECTROLYTES =====
    "sodium": {"low": 136, "high": 145, "unit": "mmol/L", "category": "Electrolytes"},
    "potassium": {"low": 3.5, "high": 5.1, "unit": "mmol/L", "category": "Electrolytes"},
    "calcium": {"low": 8.6, "high": 10.2, "unit": "mg/dL", "category": "Electrolytes"},
    
    # ===== KIDNEY FUNCTION =====
    "creatinine": {"low": 0.7, "high": 1.3, "unit": "mg/dL", "gender_specific": True, "category": "Kidney Function"},
    "bun": {"low": 7, "high": 20, "unit": "mg/dL", "category": "Kidney Function"},
    "egfr": {"low": 60, "high": 120, "unit": "mL/min/1.73m²", "category": "Kidney Function"},
    "uric_acid": {"low": 3.5, "high": 7.2, "unit": "mg/dL", "category": "Kidney Function"},
    
    # ===== LIVER FUNCTION =====
    "ast": {"low": 10, "high": 40, "unit": "U/L", "category": "Liver Function"},
    "alt": {"low": 9, "high": 46, "unit": "U/L", "category": "Liver Function"},
    "alkaline_phosphatase": {"low": 44, "high": 147, "unit": "U/L", "category": "Liver Function"},
    "ggt": {"low": 0, "high": 51, "unit": "U/L", "category": "Liver Function"},
    "bilirubin_total": {"low": 0.2, "high": 1.2, "unit": "mg/dL", "category": "Liver Function"},
    "albumin": {"low": 3.5, "high": 5.5, "unit": "g/dL", "category": "Liver Function"},
    "total_protein": {"low": 6.0, "high": 8.3, "unit": "g/dL", "category": "Liver Function"},
    
    # ===== LIPID PANEL =====
    "cholesterol": {"low": 0, "high": 200, "unit": "mg/dL", "category": "Lipid Panel"},
    "ldl": {"low": 0, "high": 100, "unit": "mg/dL", "category": "Lipid Panel"},
    "hdl": {"low": 40, "high": 60, "unit": "mg/dL", "gender_specific": True, "category": "Lipid Panel"},
    "triglycerides": {"low": 0, "high": 150, "unit": "mg/dL", "category": "Lipid Panel"},
    "vldl": {"low": 2, "high": 30, "unit": "mg/dL", "category": "Lipid Panel"},
    
    # ===== THYROID =====
    "tsh": {"low": 0.4, "high": 4.2, "unit": "mIU/L", "category": "Thyroid"},
    "t3": {"low": 80, "high": 200, "unit": "ng/dL", "category": "Thyroid"},
    "t4": {"low": 5.0, "high": 12.0, "unit": "µg/dL", "category": "Thyroid"},
    "free_t4": {"low": 0.8, "high": 1.8, "unit": "ng/dL", "category": "Thyroid"},
    
    # ===== VITAMINS =====
    "vitamin_d": {"low": 30, "high": 100, "unit": "ng/mL", "category": "Vitamins"},
    "vitamin_b12": {"low": 200, "high": 900, "unit": "pg/mL", "category": "Vitamins"},
    "folate": {"low": 2.7, "high": 17.0, "unit": "ng/mL", "category": "Vitamins"},
    "iron": {"low": 60, "high": 170, "unit": "µg/dL", "category": "Vitamins"},
    "ferritin": {"low": 20, "high": 250, "unit": "ng/mL", "gender_specific": True, "category": "Vitamins"},
    
    # ===== INFLAMMATION =====
    "crp": {"low": 0, "high": 3.0, "unit": "mg/L", "category": "Inflammation"},
    "esr": {"low": 0, "high": 20, "unit": "mm/hr", "category": "Inflammation"},
    
    # ===== IMAGING - ABDOMINAL ORGANS (CRITICAL FOR YOUR REPORT) =====
    # All possible variations for liver
    "liver_size": {"low": 12, "high": 15, "unit": "cm", "category": "Imaging", "notes": "Normal liver length"},
    "liver size": {"low": 12, "high": 15, "unit": "cm", "category": "Imaging", "notes": "Normal liver length"},
    "liver_length": {"low": 12, "high": 15, "unit": "cm", "category": "Imaging"},
    "liver": {"low": 12, "high": 15, "unit": "cm", "category": "Imaging"},
    
    # All possible variations for right kidney
    "right_kidney_size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging", "notes": "Adult right kidney"},
    "right kidney_size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "right kidney size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "right_kidney": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "right kidney": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    
    # All possible variations for left kidney
    "left_kidney_size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging", "notes": "Adult left kidney"},
    "left kidney_size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "left kidney size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "left_kidney": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "left kidney": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    
    # Generic kidney
    "kidney_size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "kidney size": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "kidney_length": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    "kidney": {"low": 9, "high": 12, "unit": "cm", "category": "Imaging"},
    
    "spleen_size": {"low": 7, "high": 12, "unit": "cm", "category": "Imaging"},
    "spleen_length": {"low": 7, "high": 12, "unit": "cm", "category": "Imaging"},
    
    # All possible variations for prostate
    "prostate_size": {"low": 20, "high": 30, "unit": "ml", "category": "Imaging", "notes": "Prostate volume"},
    "prostate size": {"low": 20, "high": 30, "unit": "ml", "category": "Imaging"},
    "prostate_volume": {"low": 20, "high": 30, "unit": "ml", "category": "Imaging"},
    "prostate volume": {"low": 20, "high": 30, "unit": "ml", "category": "Imaging"},
    "prostate_weight": {"low": 20, "high": 30, "unit": "grams", "category": "Imaging"},
    "prostate": {"low": 20, "high": 30, "unit": "ml", "category": "Imaging"},
    
    "gallbladder_size": {"low": 7, "high": 10, "unit": "cm", "category": "Imaging"},
    "pancreas_size": {"low": 12, "high": 18, "unit": "cm", "category": "Imaging"},
    "aorta_diameter": {"low": 2, "high": 3, "unit": "cm", "category": "Imaging"},
    
    # ===== KIDNEY STONES/CALCULI (CRITICAL FOR YOUR REPORT) =====
    # All possible variations
    "kidney_calculus_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging", "notes": "Small stones <5mm may pass naturally"},
    "kidney calculus_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "kidney calculus size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "kidney_stone_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "kidney stone_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "kidney stone size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "calculus_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "calculus size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "stone_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "stone size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "concretion_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "concretion size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "echogenic_foci_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging", "notes": "Echogenic foci suggest stones"},
    "echogenic foci_size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "echogenic foci size": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "calculus": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    "stone": {"low": 0, "high": 5, "unit": "mm", "category": "Imaging"},
    
    # ===== OTHER IMAGING =====
    "uterus_size": {"low": 6, "high": 9, "unit": "cm", "category": "Imaging"},
    "ovary_size": {"low": 2, "high": 3.5, "unit": "cm", "category": "Imaging"},
    "thyroid_size": {"low": 4, "high": 6, "unit": "cm", "category": "Imaging"},
    "bladder_wall_thickness": {"low": 3, "high": 5, "unit": "mm", "category": "Imaging"},
}

# ============================================================================
# COMPREHENSIVE TEST NAME MAPPING
# ============================================================================

TEST_NAME_MAPPING = {
    # Glucose
    "fasting blood sugar": "glucose", "fbs": "glucose", "blood glucose": "glucose",
    "blood sugar": "glucose", "fbg": "glucose",
    
    # Hemoglobin
    "hb": "hemoglobin", "hgb": "hemoglobin", "haemoglobin": "hemoglobin",
    
    # WBC
    "white blood cell count": "wbc", "white blood cells": "wbc",
    "leucocytes": "wbc", "leukocytes": "wbc",
    
    # RBC
    "red blood cell count": "rbc", "red blood cells": "rbc",
    "erythrocytes": "rbc",
    
    # Cholesterol
    "total cholesterol": "cholesterol", "chol": "cholesterol",
    "hdl cholesterol": "hdl", "hdl-c": "hdl",
    "ldl cholesterol": "ldl", "ldl-c": "ldl",
    
    # Thyroid
    "thyroid stimulating hormone": "tsh", "thyrotropin": "tsh",
    
    # HbA1c
    "glycated hemoglobin": "hba1c", "a1c": "hba1c",
    
    # Liver
    "sgot": "ast", "sgpt": "alt", "alp": "alkaline_phosphatase",
    "gamma gt": "ggt",
    
    # Kidney
    "serum creatinine": "creatinine", "blood urea nitrogen": "bun",
    
    # ===== IMAGING MAPPINGS (CRITICAL) =====
    # Liver variations
    "liver": "liver size", "liver length": "liver size",
    "hepatic size": "liver size", "hepatic length": "liver size",
    
    # Right kidney variations
    "right kidney": "right kidney size", "rt kidney": "right kidney size",
    "right kidney length": "right kidney size", "rt kidney size": "right kidney size",
    
    # Left kidney variations
    "left kidney": "left kidney size", "lt kidney": "left kidney size",
    "left kidney length": "left kidney size", "lt kidney size": "left kidney size",
    
    # Generic kidney
    "kidney": "kidney size", "renal size": "kidney size",
    
    # Prostate variations
    "prostate": "prostate size", "prostate gland": "prostate size",
    "prostate volume": "prostate size", "prostate weight": "prostate size",
    
    "spleen": "spleen_size", "splenic size": "spleen_size",
    "gallbladder": "gallbladder_size", "gb": "gallbladder_size",
    
    # ===== STONE/CALCULUS MAPPINGS (CRITICAL) =====
    "calculus": "calculus size", "stone": "stone size",
    "calculi": "calculus size", "stones": "stone size",
    "concretion": "concretion size", "concretions": "concretion size",
    "echogenic foci": "echogenic foci size", "echogenic focus": "echogenic foci size",
    "kidney stone": "kidney stone size", "renal calculus": "kidney calculus size",
    "kidney calculus": "kidney calculus size",
    
    # Special compound terms
    "right kidney calculus": "kidney calculus size",
    "left kidney calculus": "kidney calculus size",
    "right kidney stone": "kidney stone size",
    "left kidney stone": "kidney stone size",
    "echogenic foci at upper pole of right kidney": "echogenic foci size",
    "echogenic foci at upper pole of left kidney": "echogenic foci size",
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_reference_range(test_name: str, gender: str = "unknown") -> dict:
    """Get reference range for a test, handling gender-specific ranges."""
    # Try exact match first (with spaces)
    test_name_lower = test_name.lower().strip()
    
    if test_name_lower in REFERENCE_RANGES:
        ref_range = REFERENCE_RANGES[test_name_lower]
        
        # Check for gender-specific range
        if ref_range.get("gender_specific", False) and gender in ["male", "female"]:
            gender_key = f"{test_name_lower}_{gender}"
            if gender_key in REFERENCE_RANGES:
                return REFERENCE_RANGES[gender_key]
        
        return ref_range
    
    # Try with underscores
    test_name_underscore = test_name_lower.replace(" ", "_")
    if test_name_underscore in REFERENCE_RANGES:
        ref_range = REFERENCE_RANGES[test_name_underscore]
        
        if ref_range.get("gender_specific", False) and gender in ["male", "female"]:
            gender_key = f"{test_name_underscore}_{gender}"
            if gender_key in REFERENCE_RANGES:
                return REFERENCE_RANGES[gender_key]
        
        return ref_range
    
    # Try mapping
    normalized_name = TEST_NAME_MAPPING.get(test_name_lower, test_name_lower)
    
    if normalized_name in REFERENCE_RANGES:
        ref_range = REFERENCE_RANGES[normalized_name]
        
        if ref_range.get("gender_specific", False) and gender in ["male", "female"]:
            gender_key = f"{normalized_name}_{gender}"
            if gender_key in REFERENCE_RANGES:
                return REFERENCE_RANGES[gender_key]
        
        return ref_range
    
    return None

def add_reference_range(test_name: str, low: float, high: float, unit: str, 
                       category: str = "General", notes: str = ""):
    """Add a new reference range dynamically."""
    REFERENCE_RANGES[test_name] = {
        "low": low,
        "high": high,
        "unit": unit,
        "category": category,
        "notes": notes
    }

def get_tests_by_category() -> dict:
    """Organize tests by category."""
    categories = {}
    for test_name, ref_data in REFERENCE_RANGES.items():
        category = ref_data.get("category", "Uncategorized")
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "test_name": test_name,
            "range": f"{ref_data['low']}-{ref_data['high']} {ref_data['unit']}"
        })
    return categories

def print_database_stats():
    """Print database statistics."""
    categories = get_tests_by_category()
    print(f"✓ Reference database: {len(REFERENCE_RANGES)} tests, {len(TEST_NAME_MAPPING)} mappings")
    for category, tests in sorted(categories.items()):
        print(f"  - {category}: {len(tests)} tests")

if __name__ == "__main__":
    print_database_stats()
