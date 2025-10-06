"""
Test script for Universal PDF Generator

This script tests the universal report generation system.
"""

import sys
import os

# Add the backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), 'rise_app_backend')
sys.path.insert(0, backend_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rise_app_backend.settings')

import django
django.setup()

from utils.universal_pdf_generator import UniversalPDFGenerator
from oil_extraction.models import Machine

def test_machine_pdf():
    """Test generating PDF for oil extraction machines."""
    print("\n=== Testing Machine PDF Generation ===")

    machines = Machine.objects.all()
    print(f"Found {machines.count()} machines")

    generator = UniversalPDFGenerator(
        title="Oil Extraction Machines Report",
        data=list(machines),
        description="List of all oil extraction machines",
        metadata={"Total Machines": machines.count()}
    )

    pdf_bytes = generator.generate()

    # Save to file
    output_file = "test_machines_report.pdf"
    with open(output_file, 'wb') as f:
        f.write(pdf_bytes)

    print(f"[OK] PDF generated successfully: {output_file}")
    print(f"  File size: {len(pdf_bytes)} bytes")
    return True

def test_dict_data():
    """Test generating PDF from dictionary data."""
    print("\n=== Testing Dictionary Data PDF Generation ===")

    sample_data = [
        {"name": "Item A", "quantity": 100, "price": 50.00},
        {"name": "Item B", "quantity": 200, "price": 75.50},
        {"name": "Item C", "quantity": 150, "price": 120.00},
    ]

    generator = UniversalPDFGenerator(
        title="Sample Inventory Report",
        data=sample_data,
        metadata={"Total Items": len(sample_data)}
    )

    pdf_bytes = generator.generate()

    # Save to file
    output_file = "test_dict_report.pdf"
    with open(output_file, 'wb') as f:
        f.write(pdf_bytes)

    print(f"[OK] PDF generated successfully: {output_file}")
    print(f"  File size: {len(pdf_bytes)} bytes")
    return True

def test_endpoint():
    """Test the Django endpoint."""
    print("\n=== Testing Universal Report Endpoint ===")

    from django.test import RequestFactory
    from universal_reports.views import UniversalReportBase64View

    factory = RequestFactory()
    view = UniversalReportBase64View.as_view()

    # Test with Machine model
    request = factory.get('/api/universal-report-base64/', {
        'app': 'oil_extraction',
        'model': 'Machine'
    })

    response = view(request)

    if response.status_code == 200:
        print(f"[OK] Endpoint test passed")
        print(f"  Status: {response.status_code}")
        if hasattr(response, 'data'):
            data = response.data
            if data.get('success'):
                print(f"  Filename: {data.get('filename')}")
                print(f"  File size: {data.get('file_size')} bytes")
            else:
                print(f"  Error: {data.get('error')}")
        return True
    else:
        print(f"[FAIL] Endpoint test failed: Status {response.status_code}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Universal PDF Generator Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    try:
        results.append(("Machine PDF", test_machine_pdf()))
    except Exception as e:
        print(f"[FAIL] Machine PDF test error: {e}")
        results.append(("Machine PDF", False))

    try:
        results.append(("Dictionary Data PDF", test_dict_data()))
    except Exception as e:
        print(f"[FAIL] Dictionary test error: {e}")
        results.append(("Dictionary Data PDF", False))

    try:
        results.append(("Endpoint", test_endpoint()))
    except Exception as e:
        print(f"[FAIL] Endpoint test error: {e}")
        results.append(("Endpoint", False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed!")
    else:
        print(f"{total - passed} test(s) failed")
