#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import logging
import threading
import time
import uuid

from flask import Flask
from flask import jsonify
from flask import request


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)


@app.before_request
def log_request_info():
    app.logger.info("Headers: %s", request.headers)
    # app.logger.info('Body: %s', request.get_data())


# Simple in-memory storage for jobs and results
jobs = {}
results = {}
job_queue = []
lock = threading.RLock()

DEFAULT_PORT = 5000


# --- Helper Functions ---
def get_job(job_id):
    with lock:
        return jobs.get(job_id)


def update_job_status(job_id, status):
    with lock:
        if job_id in jobs:
            jobs[job_id]["status"] = status
            jobs[job_id]["last_updated"] = time.time()
            return True
    return False


# --- API Endpoints ---
@app.route("/api/jobs", methods=["POST"])
def create_job():
    data = request.get_json()
    if not data or "image_name" not in data:
        return jsonify({"error": "Missing image_name"}), 400

    job_id = str(uuid.uuid4())
    with lock:
        jobs[job_id] = {
            "job_id": job_id,
            "image_name": data["image_name"],
            "test_commands": data.get("test_commands", ["servo_fw_version"]),
            "start_servod_args": data.get("start_servod_args", ["-c", "local"]),
            "servod_args": data.get("servod_args", []),
            "status": "pending",
            "created_at": time.time(),
            "last_updated": time.time(),
        }
        job_queue.append(job_id)

    return jsonify({"job_id": job_id}), 201


@app.route("/api/jobs/next", methods=["GET"])
def get_next_job():
    with lock:
        if not job_queue:
            return jsonify({"job": None}), 200

        job_id = job_queue.pop(0)
        job = jobs.get(job_id)
        if job:
            job["status"] = "running"
            job["last_updated"] = time.time()
            return jsonify({"job": job})
    # Should not happen if queue and jobs are in sync
    return jsonify({"error": "Job ID from queue not found"}), 500


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200


@app.route("/api/results/<job_id>", methods=["POST"])
def submit_results(job_id):
    app.logger.info("--- Submit Results for Job: %s ---", job_id)
    if not get_job(job_id):
        app.logger.warning("Job %s not found", job_id)
        return jsonify({"error": "Job not found"}), 404

    app.logger.info("Getting JSON data...")
    data = request.get_json()
    if not data:
        app.logger.warning("Missing result data")
        return jsonify({"error": "Missing result data"}), 400
    # app.logger.info(f"Received data: {data}") # Can be very large with logs

    app.logger.info("Acquiring lock...")
    with lock:
        app.logger.info("Lock acquired")
        results[job_id] = {
            "job_id": job_id,
            "submitted_at": time.time(),
            "exit_code": data.get("exit_code", None),
            "log": data.get("log", ""),
            "error": data.get("error", ""),
            "executed_start_cmd": data.get("executed_start_cmd", ""),
            "test_outputs": data.get("test_outputs", {}),
        }
        app.logger.info("Updating job status for %s", job_id)
        update_job_status(
            job_id, "completed" if data.get("exit_code") == 0 else "failed"
        )
        app.logger.info("Lock released")

    app.logger.info("--- Results for %s submitted ---", job_id)
    return jsonify({"message": "Results received"}), 200


@app.route("/api/results/<job_id>", methods=["GET"])
def get_results(job_id):
    if not get_job(job_id):
        return jsonify({"error": "Job not found"}), 404

    with lock:
        result = results.get(job_id)

    if not result:
        return jsonify({"error": "Results not yet available"}), 404

    return jsonify(result), 200


# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Orchestrator Service")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Port to listen on"
    )
    args = parser.parse_args()
    # Adjust DEFAULT_PORT for Flask debug server if run directly
    if parser.get_default("port") == DEFAULT_PORT and DEFAULT_PORT == 5000:
        print(f"Starting Test Orchestrator Service on port {args.port}...")
        app.run(host="0.0.0.0", port=args.port, debug=False)
    else:
        print(f"Running with non-default port or not in main: {args.port}")
        app.run(host="0.0.0.0", port=args.port, debug=False)
