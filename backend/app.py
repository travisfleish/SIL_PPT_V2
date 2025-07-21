#!/usr/bin/env python3
"""
Flask API backend for Sports Innovation Lab PowerPoint Generator
Provides REST endpoints for the web frontend
"""

import os
import sys
from pathlib import Path

# CRITICAL: Set working directory and load environment FIRST
backend_dir = Path(__file__).parent
project_dir = backend_dir.parent

# Change to backend directory
os.chdir(backend_dir)

# Add parent directory to path BEFORE any project imports
sys.path.insert(0, str(project_dir))

# Load environment variables BEFORE any imports that might use them
from dotenv import load_dotenv

env_path = project_dir / '.env'
if not env_path.exists():
    # Fallback to current directory
    env_path = Path('.env')

load_dotenv(env_path, override=True)

# Verify environment loaded
print(f"Starting Flask app...")
print(f"Working directory: {os.getcwd()}")
print(f"Env file: {env_path} (exists: {env_path.exists()})")
print(f"SNOWFLAKE_ACCOUNT: {os.getenv('SNOWFLAKE_ACCOUNT', 'NOT SET')}")

# NOW continue with other imports
import json
import logging
import traceback
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from flask_cors import CORS
import threading
import queue
import uuid
import matplotlib

# Configure matplotlib BEFORE importing pyplot
matplotlib.use('Agg')  # Must be before importing pyplot

# Set matplotlib cache directory to a writable location
os.environ['MPLCONFIGDIR'] = os.path.join(tempfile.gettempdir(), 'matplotlib')

import base64
import subprocess
import io
from PIL import Image

# Add parent directory to path to import existing modules
sys.path.append(str(Path(__file__).parent.parent))

# Import font manager BEFORE other visualization imports
from utils.font_manager import font_manager
from utils.cache_manager import CacheManager  # Add CacheManager import

from utils.team_config_manager import TeamConfigManager
from report_builder.pptx_builder import PowerPointBuilder
from data_processors.snowflake_connector import test_connection
from data_processors.merchant_ranker import MerchantRanker
from postgresql_job_store import PostgreSQLJobStore

import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GLOBAL PROGRESS TRACKING
# This allows PowerPointBuilder to update progress without circular imports
_active_jobs = {}


def register_active_job(job_id: str, job_manager):
    """Register a job for progress tracking"""
    _active_jobs[job_id] = job_manager


def unregister_active_job(job_id: str):
    """Unregister a job when complete"""
    _active_jobs.pop(job_id, None)

#
# def update_job_progress(job_id: str, progress: int, message: str):
#     """Update progress for an active job"""
#     if job_id in _active_jobs:
#         _active_jobs[job_id].update_job(job_id, progress=progress, message=message)


def initialize_app():
    """Initialize application components including fonts"""
    try:
        # Initialize custom fonts
        logger.info("Initializing custom fonts...")

        # Configure matplotlib with custom fonts
        font_manager.configure_matplotlib()

        # Log font status for debugging
        font_family = font_manager.get_font_family('Red Hat Display')
        logger.info(f"Font system initialized. Using font family: {font_family}")

        # Optional: Create a test plot to ensure matplotlib is configured
        try:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(1, 1))
            ax.text(0.5, 0.5, 'Font Test', ha='center', va='center')
            plt.close(fig)
            logger.info("Matplotlib font test successful")
        except Exception as e:
            logger.warning(f"Matplotlib font test warning: {e}")

    except Exception as e:
        logger.error(f"Error initializing fonts: {e}")
        logger.error(traceback.format_exc())
        # Continue running even if fonts fail to load


# Initialize fonts at module level (when app starts)
initialize_app()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize PostgreSQL job storage and CacheManager
cache_manager = None  # Initialize as None, will be set if PostgreSQL succeeds

try:
    job_store = PostgreSQLJobStore(os.environ.get('DATABASE_URL'))
    logger.info("Successfully connected to PostgreSQL job store")

    # Initialize CacheManager using the same connection pool
    cache_manager = CacheManager(job_store.pool)
    logger.info("Successfully initialized CacheManager with PostgreSQL backend")

except Exception as e:
    logger.error(f"Failed to initialize PostgreSQL job store: {e}")
    cache_manager = None  # Set to None for fallback


    # Fallback to in-memory storage
    class InMemoryJobStore:
        def __init__(self):
            self.jobs = {}

        def create_job(self, team_key, options):
            job_id = str(uuid.uuid4())
            self.jobs[job_id] = {
                'job_id': job_id,
                'team_key': team_key,
                'status': 'pending',
                'progress': 0,
                'options': options,
                'created_at': datetime.now().isoformat()
            }
            return job_id

        def get_job(self, job_id):
            return self.jobs.get(job_id)

        def update_job(self, job_id, **kwargs):
            if job_id in self.jobs:
                self.jobs[job_id].update(kwargs)
                return True
            return False

        def list_recent_jobs(self, limit=100):
            return list(self.jobs.values())[:limit]


    job_store = InMemoryJobStore()
    logger.warning("Using in-memory job store as fallback")

# Keep job_queues for SSE
job_queues = {}  # job_id -> queue for progress updates


class JobManager:
    """Manages background PowerPoint generation jobs"""

    @staticmethod
    def create_job(team_key: str, options: dict) -> str:
        """Create a new job and return job ID"""
        # Create job in PostgreSQL
        job_id = job_store.create_job(team_key, {
            'team_key': team_key,
            'team_name': None,
            'status': 'pending',
            'progress': 0,
            'message': 'Initializing...',
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'output_file': None,
            'output_dir': None,
            'error': None,
            **options  # Include all options
        })

        # Create progress queue for this job (keep in memory for SSE)
        job_queues[job_id] = queue.Queue()

        return job_id

    @staticmethod
    def update_job(job_id: str, **kwargs):
        """Update job information"""
        # Update in PostgreSQL
        success = job_store.update_job(job_id, **kwargs)

        if success:
            # Send update to queue if exists (for SSE)
            if job_id in job_queues:
                try:
                    job_queues[job_id].put_nowait(kwargs)
                except queue.Full:
                    pass


def generate_pptx_worker(job_id: str, team_key: str, options: dict):
    """Worker function to generate PowerPoint in background with real progress tracking"""
    try:
        # Register this job for progress tracking
        register_active_job(job_id, JobManager)

        # Step 1: Load team configuration (5%)
        JobManager.update_job(job_id,
                              status='running',
                              progress=5,
                              message='Loading team configuration...')

        config_manager = TeamConfigManager()
        team_config = config_manager.get_team_config(team_key)

        JobManager.update_job(job_id,
                              team_name=team_config['team_name'],
                              progress=8,
                              message=f'Loaded configuration for {team_config["team_name"]}')

        # Step 2: Test database connection (10%)
        JobManager.update_job(job_id,
                              progress=10,
                              message='Connecting to Snowflake database...')

        if not test_connection():
            raise Exception("Failed to connect to Snowflake")

        JobManager.update_job(job_id,
                              progress=15,
                              message='Database connection established successfully')

        # Step 3: Initialize PowerPoint builder (20%)
        JobManager.update_job(job_id,
                              progress=20,
                              message='Initializing PowerPoint builder...')

        def progress_callback(progress: int, message: str):
            """Callback to update job progress from PowerPointBuilder"""
            JobManager.update_job(job_id, progress=progress, message=message)
            logger.debug(f"Progress callback: {progress}% - {message}")

        # Pass job_id, cache_manager, AND progress_callback to PowerPointBuilder
        builder = PowerPointBuilder(
            team_key,
            job_id=job_id,
            cache_manager=cache_manager,
            progress_callback=progress_callback
        )

        # Step 4: Build presentation
        # The builder will now update progress from 25% to 90%
        output_path = builder.build_presentation(
            include_custom_categories=not options.get('skip_custom', False),
            custom_category_count=options.get('custom_count')
        )

        # Step 5: Finalize (90-100%)
        JobManager.update_job(job_id,
                              progress=90,
                              message='Finalizing presentation...')

        # Ensure output_path is a Path object
        output_path = Path(output_path)

        JobManager.update_job(job_id,
                              progress=95,
                              message='Saving presentation metadata...')

        # Store both the file path and directory for better tracking
        JobManager.update_job(job_id,
                              status='completed',
                              progress=100,
                              message='PowerPoint generated successfully!',
                              completed_at=datetime.now().isoformat(),
                              output_file=str(output_path),
                              output_dir=str(output_path.parent))

        logger.info(f"Job {job_id} completed. Output file: {output_path}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        logger.error(traceback.format_exc())

        JobManager.update_job(job_id,
                              status='failed',
                              progress=0,
                              message='Generation failed',
                              error=str(e),
                              completed_at=datetime.now().isoformat())

    finally:
        # Always unregister the job when done
        unregister_active_job(job_id)


# ===== FRONTEND SERVING ROUTES =====
# These routes must come before the API routes

@app.route('/')
def serve_frontend():
    """Serve the main frontend HTML file"""
    static_path = Path(__file__).parent / 'static' / 'index.html'
    if static_path.exists():
        return send_file(str(static_path))
    else:
        logger.error(f"Frontend file not found at: {static_path}")
        return jsonify({'error': 'Frontend not found. Please ensure index.html is in backend/static/'}), 404


@app.route('/assets/<path:path>')
def serve_assets(path):
    """Serve asset files (images, etc.)"""
    assets_dir = Path(__file__).parent / 'assets'
    if not assets_dir.exists():
        logger.error(f"Assets directory not found at: {assets_dir}")
        return jsonify({'error': 'Assets directory not found'}), 404

    try:
        return send_from_directory(str(assets_dir), path)
    except FileNotFoundError:
        logger.error(f"Asset not found: {path}")
        return jsonify({'error': f'Asset not found: {path}'}), 404


# Optional: Serve any other static files if needed
@app.route('/static/<path:path>')
def serve_static(path):
    """Serve other static files if needed"""
    static_dir = Path(__file__).parent / 'static'
    try:
        return send_from_directory(str(static_dir), path)
    except FileNotFoundError:
        return jsonify({'error': f'Static file not found: {path}'}), 404


# ===== API ROUTES =====

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with database connectivity check"""
    try:
        # Check database connection
        stats = job_store.get_job_stats() if hasattr(job_store, 'get_job_stats') else {
            'total': len(job_store.jobs) if hasattr(job_store, 'jobs') else 0}

        # Check cache status if available
        cache_status = 'not configured'
        if cache_manager:
            try:
                cache_stats = cache_manager.get_cache_stats()
                cache_status = 'connected'
            except:
                cache_status = 'error'

        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'cache': cache_status,
            'jobs': stats,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'cache': 'not configured',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503


@app.route('/api/debug/fonts', methods=['GET'])
def debug_fonts():
    """Debug endpoint to check available fonts"""
    try:
        from matplotlib import font_manager as fm

        available_fonts = sorted([f.name for f in fm.fontManager.ttflist])
        red_hat_fonts = [f for f in available_fonts if 'Red Hat' in f.lower()]

        # Get current matplotlib settings
        import matplotlib.pyplot as plt
        current_font = plt.rcParams['font.family']

        return jsonify({
            'status': 'success',
            'total_fonts': len(available_fonts),
            'red_hat_fonts': red_hat_fonts,
            'current_matplotlib_font': current_font,
            'matplotlib_cache': os.environ.get('MPLCONFIGDIR', 'default'),
            'font_sample': available_fonts[:20],
            'fonts_loaded': font_manager.fonts_loaded
        })
    except Exception as e:
        logger.error(f"Font debug error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/debug/cache', methods=['GET'])
def debug_cache():
    """Debug endpoint to check cache status"""
    try:
        if not cache_manager:
            return jsonify({
                'status': 'not configured',
                'message': 'CacheManager not initialized (PostgreSQL fallback mode)'
            })

        stats = cache_manager.get_cache_stats()

        return jsonify({
            'status': 'connected',
            'stats': stats,
            'message': 'Cache is operational'
        })
    except Exception as e:
        logger.error(f"Cache debug error: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


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


@app.route('/api/download-behaviors-slide/<team_key>', methods=['GET'])
def download_behaviors_slide(team_key):
    """Generate and download just the behaviors slide as PowerPoint"""
    try:
        # Validate team
        config_manager = TeamConfigManager()
        if team_key not in config_manager.list_teams():
            return jsonify({'error': f'Team {team_key} not found'}), 404

        team_config = config_manager.get_team_config(team_key)

        # Generate behaviors slide PowerPoint
        pptx_path = generate_behaviors_slide_pptx(team_key, team_config)

        # Create filename
        team_name = team_config['team_name'].replace(' ', '_')
        filename = f"{team_name}_Behaviors_Slide.pptx"

        # Send file for download
        return send_file(
            pptx_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )

    except Exception as e:
        logger.error(f"Error generating behaviors slide: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


def generate_behaviors_slide_pptx(team_key: str, team_config: dict) -> Path:
    """Generate just the behaviors slide as a PowerPoint file - exactly like in full report"""
    from slide_generators.behaviors_slide import BehaviorsSlide
    from pptx import Presentation

    try:
        # Load the template EXACTLY like PowerPointBuilder does
        TEMPLATE_PATH = Path(__file__).parent.parent / 'templates' / 'sil_combined_template.pptx'

        if TEMPLATE_PATH.exists():
            presentation = Presentation(str(TEMPLATE_PATH))
            logger.info(f"Loaded SIL combined template from: {TEMPLATE_PATH}")
        else:
            raise FileNotFoundError(f"Template not found at {TEMPLATE_PATH}")

        # Create merchant ranker EXACTLY like PowerPointBuilder does
        view_prefix = team_config.get('view_prefix')
        comparison_pop = team_config.get('comparison_population')

        merchant_ranker = MerchantRanker(
            team_view_prefix=view_prefix,
            comparison_population=comparison_pop,
            cache_manager=cache_manager  # Pass cache_manager
        )

        # Generate slide EXACTLY like PowerPointBuilder does
        behaviors_generator = BehaviorsSlide(presentation)
        presentation = behaviors_generator.generate(
            merchant_ranker,
            team_config
        )

        # Save to temp file
        output_path = Path(tempfile.mktemp(suffix='.pptx'))
        presentation.save(str(output_path))

        return output_path

    except Exception as e:
        logger.error(f"Error generating behaviors slide: {str(e)}")
        raise


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    job = job_store.get_job(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify(job)


@app.route('/api/jobs/<job_id>/status', methods=['GET'])
def get_job_status_simple(job_id):
    """Simple status endpoint for polling fallback"""
    job = job_store.get_job(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    return jsonify({
        'status': job.get('status'),
        'progress': job.get('progress'),
        'message': job.get('message', ''),
        'error': job.get('error')
    })


@app.route('/api/jobs/<job_id>/progress', methods=['GET'])
def get_job_progress_stream(job_id):
    """Server-sent events stream for job progress"""
    job = job_store.get_job(job_id)

    if not job:
        return jsonify({'error': 'Job not found'}), 404

    def generate():
        # Send initial status immediately
        initial_job = job_store.get_job(job_id)
        if initial_job:
            yield f"data: {json.dumps(initial_job)}\n\n".encode('utf-8')

        # Get the queue for this job
        job_queue = job_queues.get(job_id)

        # Keep track of last sent data to avoid duplicates
        last_status = None
        retry_count = 0
        max_retries = 120  # 2 minutes max

        while retry_count < max_retries:
            try:
                current_job = job_store.get_job(job_id)
                if not current_job:
                    yield f"data: {json.dumps({'error': 'Job not found'})}\n\n".encode('utf-8')
                    break

                # Send update if status changed
                current_status = current_job.get('status')
                if current_status != last_status:
                    yield f"data: {json.dumps(current_job)}\n\n".encode('utf-8')
                    last_status = current_status

                # Check if job is complete
                if current_status in ['completed', 'failed']:
                    # Send final update
                    yield f"data: {json.dumps(current_job)}\n\n".encode('utf-8')
                    break

                # Try to get updates from queue
                if job_queue:
                    try:
                        # Non-blocking get
                        update = job_queue.get_nowait()
                        # Get latest job state from PostgreSQL
                        latest_job = job_store.get_job(job_id)
                        if latest_job:
                            yield f"data: {json.dumps(latest_job)}\n\n".encode('utf-8')
                    except queue.Empty:
                        pass

                # Send heartbeat to keep connection alive
                yield f": heartbeat\n\n".encode('utf-8')  # SSE comment to keep alive

                # Sleep briefly
                import time
                time.sleep(1)
                retry_count += 1

            except Exception as e:
                logger.error(f"SSE error for job {job_id}: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n".encode('utf-8')
                break

    # Create response with proper headers
    response = Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',  # Disable Nginx buffering
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream',
            'Access-Control-Allow-Origin': '*',
            'Transfer-Encoding': 'chunked'
        }
    )

    # Ensure response is not buffered
    response.direct_passthrough = True

    return response


@app.route('/api/jobs/<job_id>/download', methods=['GET'])
def download_report(job_id):
    """Download generated PowerPoint file"""
    try:
        # Check if job exists
        job = job_store.get_job(job_id)

        if not job:
            logger.error(f"Download attempted for non-existent job: {job_id}")
            return jsonify({'error': 'Job not found'}), 404

        logger.info(f"Download requested for job {job_id}: status={job['status']}, file={job.get('output_file')}")

        # Check if job is completed
        if job['status'] != 'completed':
            return jsonify({'error': 'Job not completed', 'status': job['status']}), 400

        # Check if output file exists
        output_file = job.get('output_file')
        if not output_file:
            logger.error(f"Job {job_id} has no output_file set")
            return jsonify({'error': 'No output file found for this job'}), 404

        output_path = Path(output_file)
        if not output_path.exists():
            logger.error(f"Output file does not exist: {output_path}")

            # Try to find the file in the output directory
            output_dir = job.get('output_dir')
            if output_dir:
                output_dir_path = Path(output_dir)
                if output_dir_path.exists():
                    # Look for any .pptx file in the directory
                    pptx_files = list(output_dir_path.glob('*.pptx'))
                    if pptx_files:
                        output_path = pptx_files[0]
                        logger.info(f"Found PowerPoint file in output directory: {output_path}")
                    else:
                        logger.error(f"No .pptx files found in output directory: {output_dir}")
                        return jsonify({'error': 'Output file not found'}), 404
                else:
                    logger.error(f"Output directory does not exist: {output_dir}")
                    return jsonify({'error': 'Output directory not found'}), 404
            else:
                return jsonify({'error': 'Output file not found and no output directory specified'}), 404

        # Send the file
        logger.info(f"Sending file: {output_path}")
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=output_path.name,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )

    except Exception as e:
        logger.error(f"Error downloading file for job {job_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs (recent first)"""
    jobs = job_store.list_recent_jobs(limit=50)

    return jsonify({
        'jobs': jobs,
        'total': len(jobs)
    })


@app.route('/api/admin/jobs/cleanup', methods=['POST'])
def admin_cleanup_jobs():
    """Manually trigger cleanup of expired jobs"""
    try:
        deleted_count = job_store.cleanup_expired_jobs() if hasattr(job_store, 'cleanup_expired_jobs') else 0
        return jsonify({
            'success': True,
            'deleted': deleted_count,
            'message': f'Cleaned up {deleted_count} expired jobs'
        })
    except Exception as e:
        logger.error(f"Error cleaning up jobs: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/cache/stats', methods=['GET'])
def admin_cache_stats():
    """Get cache statistics for admin monitoring"""
    try:
        if not cache_manager:
            return jsonify({
                'status': 'not configured',
                'message': 'Cache not available in fallback mode'
            })

        stats = cache_manager.get_cache_stats()

        # Calculate totals
        total_hits = sum(s.get('hits', 0) for s in stats.values())
        total_misses = sum(s.get('misses', 0) for s in stats.values())
        total_entries = sum(s.get('entries', 0) for s in stats.values())
        total_space_mb = sum(s.get('space_mb', 0) for s in stats.values())

        overall_hit_rate = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0

        return jsonify({
            'status': 'success',
            'overall': {
                'hit_rate': overall_hit_rate,
                'total_hits': total_hits,
                'total_misses': total_misses,
                'total_entries': total_entries,
                'total_space_mb': total_space_mb
            },
            'by_type': stats
        })
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/cache/cleanup', methods=['POST'])
def admin_cache_cleanup():
    """Clean up expired cache entries"""
    try:
        if not cache_manager:
            return jsonify({
                'status': 'not configured',
                'message': 'Cache not available in fallback mode'
            })

        cleaned = cache_manager.clean_expired_entries()

        return jsonify({
            'status': 'success',
            'cleaned': cleaned,
            'message': f'Cleaned up expired entries from cache'
        })
    except Exception as e:
        logger.error(f"Error cleaning cache: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/cleanup-old-files', methods=['POST'])
def cleanup_old_files():
    """Clean up old preview and job files"""
    try:
        import time
        current_time = time.time()
        files_deleted = 0

        # Clean up old temporary PowerPoint files
        temp_dir = Path(tempfile.gettempdir())
        for file_path in temp_dir.glob("tmp*.pptx"):
            if current_time - file_path.stat().st_mtime > 3600:  # 1 hour
                file_path.unlink(missing_ok=True)
                files_deleted += 1

        # Clean up expired jobs in PostgreSQL
        jobs_deleted = job_store.cleanup_expired_jobs() if hasattr(job_store, 'cleanup_expired_jobs') else 0

        # Clean up orphaned queues
        job_ids_in_db = {job['job_id'] for job in job_store.list_recent_jobs(limit=1000)}
        queues_to_delete = [job_id for job_id in job_queues if job_id not in job_ids_in_db]

        for job_id in queues_to_delete:
            job_queues.pop(job_id, None)

        # Clean up cache if available
        cache_cleaned = {}
        if cache_manager:
            try:
                cache_cleaned = cache_manager.clean_expired_entries()
            except:
                pass

        return jsonify({
            'status': 'success',
            'files_deleted': files_deleted,
            'jobs_cleaned': jobs_deleted,
            'queues_cleaned': len(queues_to_delete),
            'cache_cleaned': cache_cleaned
        })

    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/preview/hot-brands/<team_key>', methods=['GET'])
def preview_hot_brands(team_key):
    """Get top sponsorship recommendations for preview - with logo support and subcategory filtering"""
    try:
        # Validate team
        config_manager = TeamConfigManager()
        if team_key not in config_manager.list_teams():
            return jsonify({'error': f'Team {team_key} not found'}), 404

        team_config = config_manager.get_team_config(team_key)
        logger.info(f"Processing hot brands for {team_config['team_name']}")

        # Initialize cache manager (optional but recommended)
        cache_manager = None
        try:
            from utils.cache_manager import CacheManager
            from postgresql_job_store import PostgreSQLJobStore

            job_store = PostgreSQLJobStore(os.environ.get('DATABASE_URL'))
            cache_manager = CacheManager(job_store.pool)
            logger.info("Cache manager initialized")
        except Exception as e:
            logger.warning(f"Cache manager not available: {e}")

        # Initialize LogoManager
        from utils.logo_manager import LogoManager
        logo_manager = LogoManager()
        logger.info("LogoManager initialized")

        # Initialize CategoryAnalyzer with cache manager
        from data_processors.category_analyzer import CategoryAnalyzer

        analyzer = CategoryAnalyzer(
            team_name=team_config['team_name'],
            team_short=team_config.get('team_short', team_config['team_name'].split()[-1]),
            league=team_config['league'],
            comparison_population=team_config.get('comparison_population'),
            cache_manager=cache_manager
        )

        recommendations = []
        merchants_to_standardize = []

        # Load data from Snowflake
        from data_processors.snowflake_connector import query_to_dataframe

        view_prefix = team_config['view_prefix']

        # Load all required dataframes
        category_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_CATEGORY_INDEXING_ALL_TIME")
        subcategory_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_SUBCATEGORY_INDEXING_ALL_TIME")
        merchant_df = query_to_dataframe(f"SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME")

        # CRITICAL: Strip whitespace from all string columns
        logger.info("Cleaning data (removing trailing whitespace)...")
        for df in [category_df, subcategory_df, merchant_df]:
            string_cols = df.select_dtypes(include=['object']).columns
            for col in string_cols:
                df[col] = df[col].str.strip()

        if merchant_df.empty:
            logger.error("No merchant data found")
            return jsonify({
                'team_name': team_config['team_name'],
                'recommendations': [],
                'generated_at': datetime.now().isoformat(),
                'error': 'No merchant data found'
            })

        logger.info(f"Loaded {len(merchant_df)} merchant records")

        # Process fixed categories with subcategory filtering
        fixed_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']

        for category_key in fixed_categories:
            try:
                if category_key not in analyzer.categories:
                    continue

                category_config = analyzer.categories[category_key]
                category_names = category_config.get('category_names_in_data', [])

                # Strip whitespace from expected category names
                category_names = [name.strip() for name in category_names]

                # Get merchants for this category
                category_merchant_df = merchant_df[
                    merchant_df['CATEGORY'].isin(category_names)
                ].copy()

                if category_merchant_df.empty:
                    logger.debug(f"No merchants found for category {category_key}")
                    continue

                # CRITICAL: Apply subcategory filtering
                filtered_category_merchant_df = analyzer._filter_merchants_by_subcategory(
                    category_merchant_df,
                    subcategory_df,
                    category_config
                )

                logger.info(f"Category {category_key}: {len(category_merchant_df)} → "
                           f"{len(filtered_category_merchant_df)} merchants after filtering")

                if filtered_category_merchant_df.empty:
                    logger.warning(f"All merchants filtered out for category {category_key}")
                    continue

                # Find top merchant by composite index from FILTERED data
                team_merchants = filtered_category_merchant_df[
                    (filtered_category_merchant_df['AUDIENCE'] == analyzer.audience_name) &
                    (filtered_category_merchant_df['COMPARISON_POPULATION'] == analyzer.comparison_pop) &
                    (filtered_category_merchant_df['COMPOSITE_INDEX'] > 0) &
                    (filtered_category_merchant_df['PERC_AUDIENCE'] >= 0.01)
                ]

                if team_merchants.empty:
                    logger.debug(f"No qualifying merchants for {category_key} after filters")
                    continue

                # Get top merchant
                top_merchant_row = team_merchants.nlargest(1, 'COMPOSITE_INDEX').iloc[0]

                merchants_to_standardize.append({
                    'original_name': top_merchant_row['MERCHANT'],
                    'category': category_config['display_name'],
                    'composite_index': int(top_merchant_row['COMPOSITE_INDEX']),
                    'audience_pct': float(top_merchant_row['PERC_AUDIENCE']) * 100,
                    'perc_index': int(top_merchant_row.get('PERC_INDEX', 0)),
                    'spc_index': int(top_merchant_row.get('SPC_INDEX', 0))
                })

                logger.info(
                    f"Fixed category {category_config['display_name']}: {top_merchant_row['MERCHANT']} "
                    f"(index: {top_merchant_row['COMPOSITE_INDEX']:.0f})")

            except Exception as e:
                logger.warning(f"Could not analyze category {category_key}: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                continue

        # Get custom categories
        try:
            custom_categories = analyzer.get_custom_categories(
                category_df=category_df,
                merchant_df=merchant_df,
                is_womens_team=team_config.get('is_womens_team', False),
                existing_categories=fixed_categories
            )

            logger.info(f"Found {len(custom_categories)} custom categories")

            # Process top 4 custom categories
            for custom_cat in custom_categories[:4]:
                try:
                    # Strip whitespace from category names
                    category_names_clean = [name.strip() for name in custom_cat['category_names_in_data']]

                    # Get merchants for this custom category
                    custom_merchant_df = merchant_df[
                        merchant_df['CATEGORY'].isin(category_names_clean)
                    ].copy()

                    if custom_merchant_df.empty:
                        continue

                    # Create a minimal category config for custom categories
                    custom_cat_config = {
                        'display_name': custom_cat['display_name'],
                        'category_names_in_data': custom_cat['category_names_in_data'],
                        'subcategories': custom_cat.get('subcategories', {'include': [], 'exclude': []}),
                        'is_custom': True
                    }

                    # Apply subcategory filtering to custom categories too
                    filtered_custom_merchant_df = analyzer._filter_merchants_by_subcategory(
                        custom_merchant_df,
                        subcategory_df,
                        custom_cat_config
                    )

                    if filtered_custom_merchant_df.empty:
                        logger.warning(f"All merchants filtered out for custom category {custom_cat['display_name']}")
                        continue

                    # Find top merchant from FILTERED data
                    team_merchants = filtered_custom_merchant_df[
                        (filtered_custom_merchant_df['AUDIENCE'] == analyzer.audience_name) &
                        (filtered_custom_merchant_df['COMPARISON_POPULATION'] == analyzer.comparison_pop) &
                        (filtered_custom_merchant_df['COMPOSITE_INDEX'] > 0) &
                        (filtered_custom_merchant_df['PERC_AUDIENCE'] >= 0.01)
                    ]

                    if team_merchants.empty:
                        continue

                    # Get top merchant
                    top_merchant_row = team_merchants.nlargest(1, 'COMPOSITE_INDEX').iloc[0]

                    merchants_to_standardize.append({
                        'original_name': top_merchant_row['MERCHANT'],
                        'category': custom_cat['display_name'],
                        'composite_index': int(top_merchant_row['COMPOSITE_INDEX']),
                        'audience_pct': float(top_merchant_row['PERC_AUDIENCE']) * 100,
                        'perc_index': int(top_merchant_row.get('PERC_INDEX', 0)),
                        'spc_index': int(top_merchant_row.get('SPC_INDEX', 0)),
                        'is_emerging': custom_cat.get('is_emerging', False)
                    })

                    logger.info(
                        f"Custom category {custom_cat['display_name']}: {top_merchant_row['MERCHANT']} "
                        f"(index: {top_merchant_row['COMPOSITE_INDEX']:.0f})")

                except Exception as e:
                    logger.warning(f"Could not analyze custom category {custom_cat['display_name']}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue

        except Exception as e:
            logger.warning(f"Could not get custom categories: {e}")

        # Import URL encoding for safe logo URLs
        from urllib.parse import quote

        # Standardize merchant names and add logo URLs
        logger.info(f"Standardizing {len(merchants_to_standardize)} merchant names and checking logos...")

        if analyzer.standardizer and merchants_to_standardize:
            names_to_standardize = [m['original_name'] for m in merchants_to_standardize]

            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                standardized_mapping = loop.run_until_complete(
                    analyzer.standardizer.standardize_merchants(names_to_standardize)
                )

                for merchant_info in merchants_to_standardize:
                    original = merchant_info['original_name']
                    standardized = standardized_mapping.get(original, original)

                    if standardized != original:
                        logger.debug(f"Standardized: {original} → {standardized}")

                    # Check if logo exists locally
                    has_logo = logo_manager.get_logo(standardized) is not None

                    # Generate logo URL if logo exists
                    logo_url = ''
                    if has_logo:
                        encoded_name = quote(standardized)
                        logo_url = f"/api/logos/{encoded_name}"
                        logger.debug(f"Logo found for {standardized}: {logo_url}")
                    else:
                        logger.debug(f"No logo found for {standardized}")

                    recommendations.append({
                        'merchant': standardized,
                        'category': merchant_info['category'],
                        'subcategory': '',
                        'composite_index': merchant_info['composite_index'],
                        'affinity_index': merchant_info['perc_index'],
                        'spend_index': merchant_info['spc_index'],
                        'audience_percentage': merchant_info['audience_pct'],
                        'is_emerging': merchant_info.get('is_emerging', False),
                        'logo_url': logo_url,
                        'has_local_logo': has_logo
                    })

            finally:
                loop.close()
        else:
            # No standardization available
            for merchant_info in merchants_to_standardize:
                merchant_name = merchant_info['original_name']

                # Check for logo
                has_logo = logo_manager.get_logo(merchant_name) is not None
                logo_url = ''
                if has_logo:
                    encoded_name = quote(merchant_name)
                    logo_url = f"/api/logos/{encoded_name}"
                    logger.debug(f"Logo found for {merchant_name}: {logo_url}")
                else:
                    logger.debug(f"No logo found for {merchant_name}")

                recommendations.append({
                    'merchant': merchant_name,
                    'category': merchant_info['category'],
                    'subcategory': '',
                    'composite_index': merchant_info['composite_index'],
                    'affinity_index': merchant_info['perc_index'],
                    'spend_index': merchant_info['spc_index'],
                    'audience_percentage': merchant_info['audience_pct'],
                    'is_emerging': merchant_info.get('is_emerging', False),
                    'logo_url': logo_url,
                    'has_local_logo': has_logo
                })

        # Sort by composite index descending
        recommendations.sort(key=lambda x: x['composite_index'], reverse=True)

        # Log summary with logo status
        logger.info(f"Found {len(recommendations)} recommendations for {team_config['team_name']}")
        logos_found = sum(1 for rec in recommendations if rec.get('has_local_logo'))
        logger.info(f"Logos found: {logos_found}/{len(recommendations)}")

        for i, rec in enumerate(recommendations[:10], 1):
            emerging = " ⭐" if rec.get('is_emerging') else ""
            logo_status = " 🖼️" if rec.get('has_local_logo') else " ❌"
            logger.info(
                f"  {i}. {rec['category']}: {rec['merchant']} (index: {rec['composite_index']}){emerging}{logo_status}")

        return jsonify({
            'team_name': team_config['team_name'],
            'team_key': team_key,
            'recommendations': recommendations[:10],  # Return top 10
            'generated_at': datetime.now().isoformat(),
            'total_found': len(recommendations),
            'logos_found': logos_found
        })

    except Exception as e:
        logger.error(f"Error getting hot brands preview: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'error': str(e),
            'team_name': team_config.get('team_name', team_key) if 'team_config' in locals() else team_key,
            'recommendations': [],
            'generated_at': datetime.now().isoformat()
        }), 500

@app.route('/api/logos/<merchant_name>', methods=['GET'])
def serve_logo(merchant_name):
    """Serve logo file for a merchant"""
    try:
        from urllib.parse import unquote
        from flask import send_file
        import io

        # Decode the merchant name
        merchant_name = unquote(merchant_name)

        # Initialize LogoManager
        from utils.logo_manager import LogoManager
        logo_manager = LogoManager()

        # Get the logo
        logo_image = logo_manager.get_logo(merchant_name, size=(200, 200))

        if logo_image:
            # Convert PIL Image to bytes
            img_buffer = io.BytesIO()
            logo_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            return send_file(
                img_buffer,
                mimetype='image/png',
                as_attachment=False,
                download_name=f"{merchant_name}.png"
            )
        else:
            # Return 404 if logo not found
            return jsonify({'error': f'Logo not found for {merchant_name}'}), 404

    except Exception as e:
        logger.error(f"Error serving logo for {merchant_name}: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5001, debug=True)