from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class DashboardStatsTests(TestCase):
    def test_authenticated_dashboard_returns_metrics(self):
        user = get_user_model().objects.create_user(
            username="dashboard-user",
            password="test-password",
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/dashboard/stats/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("invoice_counts", response.data)
        self.assertIn("payment_summary", response.data)
        self.assertIn("vendor_analytics", response.data)
