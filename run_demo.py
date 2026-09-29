#!/usr/bin/env python
"""
MPLAD-AI Demo Runner

This script runs the complete prototype:
1. Starts the FastAPI backend (in background)
2. Starts the Streamlit dashboard (foreground)

Usage:
    python run_demo.py [--api-only | --dashboard-only]
"""
import subprocess
import sys
import time
import os
import signal
from pathlib import Path


def find_free_port(start=8000):
    """Find a free port starting from start."""
    import socket
    port = start
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            port += 1


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="MPLAD-AI Demo Runner")
    parser.add_argument("--api-only", action="store_true", help="Run only API")
    parser.add_argument("--dashboard-only", action="store_true", help="Run only dashboard")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🛡️  MPLAD-AI - Risk Monitoring System")
    print("=" * 60)
    print()
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    if args.api_only:
        # Run API only
        print("Starting FastAPI backend...")
        cmd = [sys.executable, "-m", "uvicorn", 
               "mplads.backend.main:app", 
               "--host", "0.0.0.0", 
               "--port", str(args.port)]
        print(f"Command: {' '.join(cmd)}")
        print()
        print(f"API will be available at: http://localhost:{args.port}")
        print(f"Docs at: http://localhost:{args.port}/docs")
        print()
        
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\nShutting down...")
    
    elif args.dashboard_only:
        # Run dashboard only
        print("Starting Streamlit dashboard...")
        cmd = [sys.executable, "-m", "streamlit", "run", "mplads/dashboard/app.py"]
        print(f"Command: {' '.join(cmd)}")
        print()
        print("Dashboard will open in your browser.")
        print()
        
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\nShutting down...")
    
    else:
        # Run both
        print("Starting FastAPI backend on port", args.port, "...")
        
        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", 
             "mplads.backend.main:app", 
             "--host", "0.0.0.0", 
             "--port", str(args.port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Wait for API to start
        print("Waiting for API to start...")
        time.sleep(3)
        
        # Check if API started successfully
        if api_process.poll() is not None:
            print("❌ API failed to start!")
            stdout, _ = api_process.communicate()
            print(stdout)
            sys.exit(1)
        
        print("✅ API is running!")
        print()
        print("-" * 60)
        print()
        print("Starting Streamlit dashboard...")
        print()
        print("The dashboard will open in your browser at:")
        print("  http://localhost:8501")
        print()
        print("Press Ctrl+C to stop both services.")
        print("-" * 60)
        print()
        
        # Run dashboard
        dashboard_process = subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "mplads/dashboard/app.py"]
        )
        
        try:
            # Wait for dashboard or keyboard interrupt
            dashboard_process.wait()
        except KeyboardInterrupt:
            print("\nStopping services...")
        finally:
            # Clean up
            api_process.terminate()
            dashboard_process.terminate()
            api_process.wait()
            dashboard_process.wait()
            print("✅ All services stopped.")


if __name__ == "__main__":
    main()