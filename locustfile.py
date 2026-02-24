"""
Basic Locust load test for VMS (Volunteer Management System).

Usage:
  With UI (open http://localhost:8089):
    locust -f locustfile.py --host=http://127.0.0.1:5050

  Headless (no browser):
    locust -f locustfile.py --host=http://127.0.0.1:5050 --headless -u 10 -r 2 -t 1m

  Against staging:
    locust -f locustfile.py --host=https://romulus-jlane.pythonanywhere.com

Note: Many routes require login; this test hits GET endpoints and will get 200 or 302.
That is still valid for measuring server load and response times.
"""

from locust import HttpUser, task, between


class VMSUser(HttpUser):
    """Simulates a user browsing VMS pages."""

    wait_time = between(1, 3)

    @task(5)
    def home(self):
        self.client.get("/")

    @task(3)
    def volunteers_list(self):
        self.client.get("/volunteers")

    @task(3)
    def events_list(self):
        self.client.get("/events")

    @task(2)
    def teachers_list(self):
        self.client.get("/teachers")

    @task(2)
    def students_list(self):
        self.client.get("/students")

    @task(2)
    def organizations_list(self):
        self.client.get("/organizations")
