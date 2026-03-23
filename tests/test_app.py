"""
Comprehensive tests for the Mergington High School Activities API
"""

import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """
    Fixture to backup and restore the global activities state between tests.
    This ensures test isolation by preventing state pollution.
    """
    # Backup the original state
    original_activities = copy.deepcopy(activities)
    
    yield  # Run the test
    
    # Restore the original state
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for GET /"""
    
    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static HTML"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify it's a dictionary with expected activities
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        assert len(data) == 9  # Should have 9 activities
    
    def test_activity_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        
        # Verify required fields
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        
        # Verify data types
        assert isinstance(chess_club["description"], str)
        assert isinstance(chess_club["schedule"], str)
        assert isinstance(chess_club["max_participants"], int)
        assert isinstance(chess_club["participants"], list)
    
    def test_participants_contain_emails(self, client):
        """Test that participants list contains email addresses"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        participants = chess_club["participants"]
        
        assert len(participants) > 0
        assert all("@" in email for email in participants)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup"""
    
    def test_signup_success(self, client):
        """Test successful signup"""
        email = "newstudent@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert email in response.json()["message"]
    
    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant to the list"""
        email = "newstudent@mergington.edu"
        activity_name = "Chess Club"
        
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()[activity_name]["participants"])
        
        # Sign up
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Verify participant was added
        response = client.get("/activities")
        updated_count = len(response.json()[activity_name]["participants"])
        assert updated_count == initial_count + 1
        assert email in response.json()[activity_name]["participants"]
    
    def test_signup_duplicate_prevention(self, client):
        """Test that duplicate signups are prevented"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity_name = "Chess Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        email = "student@mergington.edu"
        activity_name = "Fictional Club"
        
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_case_sensitive_activity_name(self, client):
        """Test that activity names are case-sensitive"""
        email = "student@mergington.edu"
        
        response = client.post(
            "/activities/chess club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_multiple_students_same_activity(self, client):
        """Test multiple students can sign up for the same activity"""
        activity_name = "Programming Class"
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        
        # Sign up first student
        response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email1}
        )
        assert response1.status_code == 200
        
        # Sign up second student
        response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email2}
        )
        assert response2.status_code == 200
        
        # Verify both are in the list
        response = client.get("/activities")
        participants = response.json()[activity_name]["participants"]
        assert email1 in participants
        assert email2 in participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity_name = "Chess Club"
        
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
        assert email in response.json()["message"]
    
    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        email = "michael@mergington.edu"
        activity_name = "Chess Club"
        
        # Sign up first (to have a known participant)
        # Using a different email to ensure it's added
        signup_email = "temp@mergington.edu"
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": signup_email}
        )
        
        # Verify participant was added
        response = client.get("/activities")
        assert signup_email in response.json()[activity_name]["participants"]
        
        # Unregister
        client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": signup_email}
        )
        
        # Verify participant was removed
        response = client.get("/activities")
        assert signup_email not in response.json()[activity_name]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        email = "student@mergington.edu"
        activity_name = "Fictional Club"
        
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_signed_up(self, client):
        """Test unregister when student is not enrolled"""
        email = "notstudent@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_case_sensitive_activity_name(self, client):
        """Test that activity names are case-sensitive in unregister"""
        email = "student@mergington.edu"
        
        response = client.delete(
            "/activities/chess club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 404


class TestStateManagement:
    """Tests for proper state handling across multiple operations"""
    
    def test_signup_then_unregister(self, client):
        """Test signup followed by unregister"""
        email = "testuser@mergington.edu"
        activity_name = "Tennis Team"
        
        # Sign up
        client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Verify signed up
        response = client.get("/activities")
        assert email in response.json()[activity_name]["participants"]
        
        # Unregister
        client.delete(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        
        # Verify unregistered
        response = client.get("/activities")
        assert email not in response.json()[activity_name]["participants"]
    
    def test_signup_in_multiple_activities(self, client):
        """Test that same student can sign up for multiple activities"""
        email = "versatile@mergington.edu"
        activities_to_join = ["Chess Club", "Basketball Club", "Music Band"]
        
        # Sign up for multiple activities
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify in all activities
        response = client.get("/activities")
        data = response.json()
        for activity in activities_to_join:
            assert email in data[activity]["participants"]
