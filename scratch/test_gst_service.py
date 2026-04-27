import sys
import os

# Add the project root and apps directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps')))

from taxation.services.gst_service import calculate_gst

def test_gst_calculations():
    print("Running GST Calculation Tests...\n")
    
    # 1. Test Intra-state (Same State Code)
    print("Test 1: Intra-state (Maharashtra to Maharashtra)")
    res1 = calculate_gst(1000, "27", "27", 18)
    print(res1)
    assert res1['cgst_amount'] == 90.0
    assert res1['sgst_amount'] == 90.0
    assert res1['igst_amount'] == 0.0
    assert res1['total_amount'] == 1180.0
    print("PASSED\n")

    # 2. Test Inter-state (Different State Codes)
    print("Test 2: Inter-state (Maharashtra to Gujarat)")
    res2 = calculate_gst(1000, "27", "24", 18)
    print(res2)
    assert res2['cgst_amount'] == 0.0
    assert res2['sgst_amount'] == 0.0
    assert res2['igst_amount'] == 180.0
    assert res2['total_amount'] == 1180.0
    print("PASSED\n")

    # 3. Test Edge Case: 5% tax rate with rounding
    print("Test 3: Rounding (5% tax on 333.33)")
    res3 = calculate_gst(333.33, "27", "27", 5)
    print(res3)
    # 333.33 * 0.025 = 8.33325 -> 8.33
    assert res3['cgst_amount'] == 8.33
    print("PASSED\n")

    # 4. Test Validations
    print("Test 4: Negative amount validation")
    try:
        calculate_gst(-100, "27", "27", 18)
    except ValueError as e:
        print(f"Caught expected error: {e}")
        print("PASSED\n")

    print("All tests completed successfully!")

if __name__ == "__main__":
    test_gst_calculations()
