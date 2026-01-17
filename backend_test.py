#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime

class AutomotivePartsAPITester:
    def __init__(self, base_url="https://guidebook-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.supplier_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", expected_status=None, actual_status=None):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            if expected_status and actual_status:
                print(f"   Expected status: {expected_status}, Got: {actual_status}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "expected_status": expected_status,
            "actual_status": actual_status
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        if files:
            # Remove Content-Type for file uploads
            headers.pop('Content-Type', None)

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=data, headers=headers, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json() if response.content else {}
                    self.log_test(name, True)
                    return True, response_data
                except:
                    self.log_test(name, True)
                    return True, {}
            else:
                try:
                    error_data = response.json() if response.content else {}
                    self.log_test(name, False, error_data.get('detail', 'Unknown error'), expected_status, response.status_code)
                except:
                    self.log_test(name, False, f"HTTP {response.status_code}", expected_status, response.status_code)
                return False, {}

        except requests.exceptions.RequestException as e:
            self.log_test(name, False, f"Request failed: {str(e)}")
            return False, {}

    def test_seed_data(self):
        """Test seed data creation"""
        print("\n🌱 Testing seed data creation...")
        return self.run_test(
            "Seed Data Creation",
            "POST",
            "seed-data",
            200
        )

    def test_admin_login(self):
        """Test admin login"""
        print("\n🔐 Testing admin login...")
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@rvparts.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            print(f"   Admin token obtained: {self.admin_token[:20]}...")
            return True
        return False

    def test_supplier_login(self):
        """Test supplier login"""
        print("\n🔐 Testing supplier login...")
        success, response = self.run_test(
            "Supplier Login",
            "POST",
            "auth/login",
            200,
            data={"email": "supplier1@metalworks.com", "password": "supplier123"}
        )
        if success and 'access_token' in response:
            self.supplier_token = response['access_token']
            print(f"   Supplier token obtained: {self.supplier_token[:20]}...")
            return True
        return False

    def test_auth_me_admin(self):
        """Test /auth/me endpoint for admin"""
        print("\n👤 Testing admin profile...")
        return self.run_test(
            "Admin Profile (/auth/me)",
            "GET",
            "auth/me",
            200,
            token=self.admin_token
        )

    def test_auth_me_supplier(self):
        """Test /auth/me endpoint for supplier"""
        print("\n👤 Testing supplier profile...")
        return self.run_test(
            "Supplier Profile (/auth/me)",
            "GET",
            "auth/me",
            200,
            token=self.supplier_token
        )

    def test_parts_stats_admin(self):
        """Test parts stats for admin"""
        print("\n📊 Testing parts stats (admin)...")
        return self.run_test(
            "Parts Stats (Admin)",
            "GET",
            "parts/stats",
            200,
            token=self.admin_token
        )

    def test_parts_stats_supplier(self):
        """Test parts stats for supplier"""
        print("\n📊 Testing parts stats (supplier)...")
        return self.run_test(
            "Parts Stats (Supplier)",
            "GET",
            "parts/stats",
            200,
            token=self.supplier_token
        )

    def test_parts_list_admin(self):
        """Test parts list for admin"""
        print("\n📦 Testing parts list (admin)...")
        return self.run_test(
            "Parts List (Admin)",
            "GET",
            "parts",
            200,
            token=self.admin_token
        )

    def test_parts_list_supplier(self):
        """Test parts list for supplier"""
        print("\n📦 Testing parts list (supplier)...")
        return self.run_test(
            "Parts List (Supplier)",
            "GET",
            "parts",
            200,
            token=self.supplier_token
        )

    def test_suppliers_list_admin(self):
        """Test suppliers list (admin only)"""
        print("\n👥 Testing suppliers list (admin)...")
        return self.run_test(
            "Suppliers List (Admin)",
            "GET",
            "suppliers",
            200,
            token=self.admin_token
        )

    def test_suppliers_list_supplier_forbidden(self):
        """Test suppliers list should be forbidden for supplier"""
        print("\n🚫 Testing suppliers list forbidden (supplier)...")
        return self.run_test(
            "Suppliers List Forbidden (Supplier)",
            "GET",
            "suppliers",
            403,
            token=self.supplier_token
        )

    def test_audit_logs_admin(self):
        """Test audit logs (admin only)"""
        print("\n📋 Testing audit logs (admin)...")
        return self.run_test(
            "Audit Logs (Admin)",
            "GET",
            "audit-logs",
            200,
            token=self.admin_token
        )

    def test_audit_logs_supplier_forbidden(self):
        """Test audit logs should be forbidden for supplier"""
        print("\n🚫 Testing audit logs forbidden (supplier)...")
        return self.run_test(
            "Audit Logs Forbidden (Supplier)",
            "GET",
            "audit-logs",
            403,
            token=self.supplier_token
        )

    def test_create_part_supplier(self):
        """Test creating a part as supplier"""
        print("\n➕ Testing part creation (supplier)...")
        test_part = {
            "sku": f"TEST-PART-{datetime.now().strftime('%H%M%S')}",
            "name": "Test Part for API Testing",
            "description": "Created during API testing",
            "country_of_origin": "USA",
            "total_weight_kg": 10.5,
            "total_value_usd": 250.00
        }
        success, response = self.run_test(
            "Create Part (Supplier)",
            "POST",
            "parts",
            200,
            data=test_part,
            token=self.supplier_token
        )
        if success and 'id' in response:
            self.test_part_id = response['id']
            print(f"   Created part ID: {self.test_part_id}")
            return True, response
        return False, {}

    def test_add_child_part(self):
        """Test adding a child part"""
        if not hasattr(self, 'test_part_id'):
            print("   Skipping - no test part created")
            return False, {}
        
        print("\n➕ Testing child part creation...")
        child_part = {
            "identifier": f"CHILD-{datetime.now().strftime('%H%M%S')}",
            "name": "Test Child Component",
            "description": "Test child component",
            "country_of_origin": "USA",
            "weight_kg": 2.5,
            "value_usd": 50.00,
            "aluminum_content_percent": 15,
            "steel_content_percent": 80,
            "has_russian_content": False,
            "manufacturing_method": "CNC Machined"
        }
        return self.run_test(
            "Add Child Part",
            "POST",
            f"parts/{self.test_part_id}/children",
            200,
            data=child_part,
            token=self.supplier_token
        )

    def test_search_parts(self):
        """Test parts search"""
        print("\n🔍 Testing parts search...")
        return self.run_test(
            "Search Parts",
            "GET",
            "search?q=TEST",
            200,
            token=self.supplier_token
        )

    def test_export_template(self):
        """Test export template download"""
        print("\n📥 Testing export template...")
        return self.run_test(
            "Export Template",
            "GET",
            "export/template",
            200,
            token=self.supplier_token
        )

    def test_invalid_login(self):
        """Test invalid login credentials"""
        print("\n🚫 Testing invalid login...")
        return self.run_test(
            "Invalid Login",
            "POST",
            "auth/login",
            401,
            data={"email": "invalid@test.com", "password": "wrongpassword"}
        )

    def test_unauthorized_access(self):
        """Test unauthorized access"""
        print("\n🚫 Testing unauthorized access...")
        return self.run_test(
            "Unauthorized Access",
            "GET",
            "parts",
            401
        )

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting Automotive Parts Portal API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)

        # Test seed data first
        self.test_seed_data()

        # Test authentication
        admin_login_success = self.test_admin_login()
        supplier_login_success = self.test_supplier_login()

        if not admin_login_success or not supplier_login_success:
            print("\n❌ Login tests failed - stopping further tests")
            return False

        # Test profile endpoints
        self.test_auth_me_admin()
        self.test_auth_me_supplier()

        # Test core endpoints
        self.test_parts_stats_admin()
        self.test_parts_stats_supplier()
        self.test_parts_list_admin()
        self.test_parts_list_supplier()

        # Test admin-only endpoints
        self.test_suppliers_list_admin()
        self.test_suppliers_list_supplier_forbidden()
        self.test_audit_logs_admin()
        self.test_audit_logs_supplier_forbidden()

        # Test CRUD operations
        self.test_create_part_supplier()
        self.test_add_child_part()
        self.test_search_parts()

        # Test export functionality
        self.test_export_template()

        # Test security
        self.test_invalid_login()
        self.test_unauthorized_access()

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = AutomotivePartsAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": tester.tests_run,
        "passed_tests": tester.tests_passed,
        "success_rate": (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0,
        "test_details": tester.test_results
    }
    
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())