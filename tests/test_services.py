import unittest
from pathlib import Path

from marketplace import database, services


class MarketplaceServiceTests(unittest.TestCase):
    def setUp(self):
        database.close_connection()
        db_path = Path(database.__file__).resolve().parent / "marketplace.db"
        if db_path.exists():
            db_path.unlink()
        database.initialize_database()

    def register_homeowner(self, idx: int = 1):
        return services.register_homeowner(
            email=f"homeowner{idx}@example.com",
            password="SecurePass123!",
            profile={"full_name": f"Homeowner {idx}"},
        )["user_id"]

    def register_contractor(self, idx: int = 1):
        return services.register_contractor(
            email=f"contractor{idx}@example.com",
            password="SecurePass123!",
            profile={"business_name": f"Contractor {idx}", "specialties": ["painting"], "service_areas": ["NY"]},
        )["user_id"]

    def create_project(self, homeowner_id: int, idx: int = 1):
        return services.create_project(
            homeowner_id,
            {
                "title": f"Project {idx}",
                "project_type": "Remodel",
                "description": "Kitchen remodel",
                "budget_min": 5000,
                "budget_max": 10000,
                "desired_start_date": "2025-01-01",
                "location": "New York",
                "photos": [],
            },
        )

    def test_basic_homeowner_project_limit(self):
        homeowner_id = self.register_homeowner()
        self.create_project(homeowner_id)
        with self.assertRaises(services.MarketplaceError):
            self.create_project(homeowner_id, idx=2)

    def test_basic_homeowner_quote_limit(self):
        homeowner_id = self.register_homeowner()
        project = self.create_project(homeowner_id)
        for idx in range(1, 4):
            contractor_id = self.register_contractor(idx)
            services.submit_quote(
                contractor_id,
                project_id=project["id"],
                payload={
                    "amount": 7000 + idx,
                    "cost_breakdown": "Labor and materials",
                    "timeline": "4 weeks",
                },
            )
        contractor_id = self.register_contractor(4)
        with self.assertRaises(services.MarketplaceError):
            services.submit_quote(
                contractor_id,
                project_id=project["id"],
                payload={"amount": 7500, "cost_breakdown": "Extra", "timeline": "5 weeks"},
            )

    def test_accepting_quote_generates_invoice(self):
        homeowner_id = self.register_homeowner()
        project = self.create_project(homeowner_id)
        contractor_id = self.register_contractor()
        quote = services.submit_quote(
            contractor_id,
            project_id=project["id"],
            payload={"amount": 8000, "cost_breakdown": "Labor", "timeline": "3 weeks"},
        )
        accepted = services.accept_quote(homeowner_id, quote["id"])
        self.assertEqual("accepted", accepted["status"])
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE quote_id = ?", (quote["id"],))
        invoice = cursor.fetchone()
        self.assertIsNotNone(invoice)
        self.assertAlmostEqual(float(invoice["amount"]), 240.0, places=2)

    def test_dashboard_summary(self):
        homeowner_id = self.register_homeowner()
        project = self.create_project(homeowner_id)
        contractor_id = self.register_contractor()
        services.submit_quote(
            contractor_id,
            project_id=project["id"],
            payload={"amount": 9000, "cost_breakdown": "Full scope", "timeline": "6 weeks"},
        )
        homeowner_summary = services.dashboard_summary(homeowner_id, "homeowner")
        contractor_summary = services.dashboard_summary(contractor_id, "contractor")
        self.assertEqual(homeowner_summary["open_projects"], 1)
        self.assertGreaterEqual(homeowner_summary["quotes_received"], 1)
        self.assertEqual(contractor_summary["submitted_quotes"], 1)


if __name__ == "__main__":
    unittest.main()
