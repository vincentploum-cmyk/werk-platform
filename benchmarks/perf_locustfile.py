from locust import HttpUser, task, between
import uuid

class WerkUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # Login to get token
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            print(f"Login successful for user {self}")
        else:
            self.token = None
            self.headers = {}
            print(f"Login failed for user {self}: {response.status_code} {response.text}")

        # Create a test project to use in tasks
        project_name = f"Perf Project {uuid.uuid4().hex[:8]}"
        response = self.client.post("/api/v1/projects/", json={
            "name": project_name,
            "description": "Performance testing project"
        }, headers=self.headers)
        if response.status_code == 201:
            self.project_id = response.json()["id"]
        else:
            self.project_id = None

    @task(3)
    def list_projects(self):
        self.client.get("/api/v1/projects/", headers=self.headers)

    @task(2)
    def get_project(self):
        if self.project_id:
            self.client.get(f"/api/v1/projects/{self.project_id}", headers=self.headers)

    @task(1)
    def create_task(self):
        if self.project_id:
            self.client.post("/api/v1/tasks/", json={
                "project_id": self.project_id,
                "title": "Perf Task",
                "description": "Task created during performance test",
                "priority": 1
            }, headers=self.headers)

    @task(2)
    def list_tasks(self):
        if self.project_id:
            self.client.get(f"/api/v1/tasks/?project_id={self.project_id}", headers=self.headers)
