#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=redefined-outer-name
import app as orchestrator_app
from app import app as flask_app
import pytest


@pytest.fixture
def app():
    # Clear global state before each test
    with orchestrator_app.lock:
        orchestrator_app.jobs.clear()
        orchestrator_app.results.clear()
        orchestrator_app.job_queue.clear()
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def test_create_job(client):
    """Test creating a new job."""
    response = client.post("/api/jobs", json={"image_name": "test_image:latest"})
    assert response.status_code == 201
    data = response.get_json()
    assert "job_id" in data


def test_create_job_missing_image(client):
    """Test creating a job with missing image_name."""
    response = client.post("/api/jobs", json={})
    assert response.status_code == 400


def test_get_next_job(client):
    """Test getting the next job from the queue."""
    # Add a job first
    client.post("/api/jobs", json={"image_name": "test_image:next"})

    response = client.get("/api/jobs/next")
    assert response.status_code == 200
    data = response.get_json()
    assert data["job"]["image_name"] == "test_image:next"
    assert data["job"]["status"] == "running"

    # Check if queue is empty now
    response = client.get("/api/jobs/next")
    assert response.status_code == 200
    data = response.get_json()
    assert data["job"] is None


def test_get_job_status(client):
    """Test getting job status."""
    post_response = client.post("/api/jobs", json={"image_name": "test_image:status"})
    job_id = post_response.get_json()["job_id"]

    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["job_id"] == job_id
    assert data["status"] == "pending"


def test_submit_and_get_results(client):
    """Test submitting and retrieving results."""
    post_response = client.post("/api/jobs", json={"image_name": "test_image:results"})
    job_id = post_response.get_json()["job_id"]

    # Consume the job so its status becomes running
    client.get("/api/jobs/next")

    # Submit results
    results_data = {"log": "Test log", "exit_code": 0, "test_outputs": {"cmd": "OK"}}
    response = client.post(f"/api/results/{job_id}", json=results_data)
    assert response.status_code == 200

    # Check job status changed to completed
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    assert response.get_json()["status"] == "completed"

    # Get results
    response = client.get(f"/api/results/{job_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["log"] == "Test log"
    assert data["exit_code"] == 0
    assert data["test_outputs"] == {"cmd": "OK"}


def test_get_results_not_found(client):
    """Test getting results for a non-existent job."""
    response = client.get("/api/results/non-existent-id")
    assert response.status_code == 404
