#!/usr/bin/env python3
"""
Flask API backend for Sports Innovation Lab PowerPoint Generator
Provides REST endpoints for the web frontend
"""

import os
import sys
import json
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import threading
import queue
import uuid
import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot

# Add parent directory to path to import existing modules
sys.path.append(str(Path(__file__).parent.parent))

from utils.team_config_manager import TeamConfigManager
from report_builder.pptx_builder import PowerPointBuilder
from data_processors.snowflake_connector import test_connection

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Job tracking
jobs = {}  # job_id -> job_info
job_queues = {}  # job_id -> queue for progress updates


class JobManager:
    """Manages background PowerPoint generation jobs"""

    @staticmethod
    def create_job(team_key: str, options: dict) -> str:
        """Create a new job and return job ID"""
        job_id = str(uuid.uuid4())

        jobs[job_id] = {
            'id': job_id,
            'team_key': team_key,
            'team_name': None,
            'status': 'pending',
            'progress': 0,
            'message': 'Initializing...',
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'output_file': None,
            'error': None,
            'options': options
        }

        # Create progress queue for this job
        job_queues[job_id] = queue.Queue()

        return job_id

    @staticmethod
    def update_job(job_id: str, **kwargs):
        """Update job information"""
        if job_id in jobs:
            jobs[job_id].update(kwargs)

            # Send update to queue if exists
            if job_id in job_queues:
                try:
                    job_queues[job_id].put_nowait(kwargs)
                except queue.Full:
                    pass


def generate_pptx_worker(job_id: str, team_key: str, options: dict):
    """Worker function to generate PowerPoint in background"""
    try:
        # Get team configuration
        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)

        JobManager.update_job(job_id,
                              team_name=team_config['team_name'],
                              status='running',
                              progress=10,
                              message='Connecting to database...')

        # Test connection
        if not test_connection():
            raise Exception("Failed to connect to Snowflake")

        JobManager.update_job(job_id,
                              progress=20,
                              message='Loading data...')

        # Create builder
        builder = PowerPointBuilder(team_key)

        # Custom progress callback
        original_method = builder.build_presentation

        def build_with_progress(*args, **kwargs):
            # Update progress during build
            JobManager.update_job(job_id,
                                  progress=30,
                                  message='Processing demographics...')

            # You could add more granular progress updates here
            # by modifying the PowerPointBuilder class

            return original_method(*args, **kwargs)

        builder.build_presentation = build_with_progress

        # Build presentation
        JobManager.update_job(job_id,
                              progress=40,
                              message='Generating slides...')

        output_path = builder.build_presentation(
            include_custom_categories=not options.get('skip_custom', False),
            custom_category_count=options.get('custom_count')
        )

        # Complete
        JobManager.update_job(job_id,
                              status='completed',
                              progress=100,
                              message='PowerPoint generated successfully!',
                              completed_at=datetime.now().isoformat(),
                              output_file=str(output_path))

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        logger.error(traceback.format_exc())

        JobManager.update_job(job_id,
                              status='failed',
                              progress=0,
                              message='Generation failed',
                              error=str(e),
                              completed_at=datetime.now().isoformat())


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Get all available teams"""
    try:
        config_manager = TeamConfigManager()
        teams = []

        for team_key in config_manager.list_teams():
            team_config = config_manager.get_team_config(team_key)
            teams.append({
                'key': team_key,
                'name': team_config['team_name'],
                'league': team_config['league'],
                'view_prefix': team_config['view_prefix']
            })

        return jsonify({
            'teams': teams,
            'count': len(teams)
        })

    except Exception as e:
        logger.error(f"Error getting teams: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/leagues', methods=['GET'])
def get_leagues():
    """Get all unique leagues"""
    try:
        config_manager = TeamConfigManager()
        leagues = set()

        for team_key in config_manager.list_teams():
            team_config = config_manager.get_team_config(team_key)
            leagues.add(team_config['league'])

        return jsonify({
            'leagues': sorted(list(leagues))
        })

    except Exception as e:
        logger.error(f"Error getting leagues: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-connection', methods=['GET'])
def test_db_connection():
    """Test Snowflake connection"""
    try:
        connected = test_connection()
        return jsonify({
            'connected': connected,
            'message': 'Connection successful' if connected else 'Connection failed'
        })
    except Exception as e:
        logger.error(f"Connection test error: {str(e)}")
        return jsonify({
            'connected': False,
            'error': str(e)
        }), 500


@app.route('/api/generate', methods=['POST'])
def generate_report():
    """Start PowerPoint generation job"""
    try:
        data = request.json
        team_key = data.get('team_key')

        if not team_key:
            return jsonify({'error': 'team_key is required'}), 400

        # Validate team exists
        config_manager = TeamConfigManager()
        if team_key not in config_manager.list_teams():
            return jsonify({'error': f'Team {team_key} not found'}), 404

        # Create job
        options = {
            'skip_custom': data.get('skip_custom', False),
            'custom_count': data.get('custom_count')
        }

        job_id = JobManager.create_job(team_key, options)

        # Start background worker
        thread = threading.Thread(
            target=generate_pptx_worker,
            args=(job_id, team_key, options),
            daemon=True
        )
        thread.start()

        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'message': 'Generation started'
        })

    except Exception as e:
        logger.error(f"Error starting generation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(jobs[job_id])


@app.route('/api/jobs/<job_id>/progress', methods=['GET'])
def get_job_progress_stream(job_id):
    """Server-sent events stream for job progress"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    def generate():
        # Send initial status
        yield f"data: {json.dumps(jobs[job_id])}\n\n"

        # Wait for updates
        job_queue = job_queues.get(job_id)
        if job_queue:
            while True:
                try:
                    # Wait for update with timeout
                    update = job_queue.get(timeout=30)

                    # Send current job state
                    yield f"data: {json.dumps(jobs[job_id])}\n\n"

                    # Check if job is complete
                    if jobs[job_id]['status'] in ['completed', 'failed']:
                        break

                except queue.Empty:
                    # Send heartbeat
                    yield f"data: {json.dumps({'heartbeat': True})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/jobs/<job_id>/download', methods=['GET'])
def download_report(job_id):
    """Download generated PowerPoint file"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404

    job = jobs[job_id]

    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400

    if not job['output_file'] or not Path(job['output_file']).exists():
        return jsonify({'error': 'Output file not found'}), 404

    return send_file(
        job['output_file'],
        as_attachment=True,
        download_name=Path(job['output_file']).name,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs (recent first)"""
    job_list = sorted(
        jobs.values(),
        key=lambda x: x['created_at'],
        reverse=True
    )

    # Limit to recent jobs
    return jsonify({
        'jobs': job_list[:50],
        'total': len(jobs)
    })


if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5001, debug=True)