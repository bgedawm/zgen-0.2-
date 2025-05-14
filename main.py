#!/usr/bin/env python3
"""
Local Scout AI Agent - Main Entry Point
---------------------------------------
This is the main entry point for the Local Scout AI Agent.
It initializes all components and starts the web server.
"""

import os
import sys
import logging
import argparse
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Initialize logging
from utils.logger import setup_logging

# Load environment variables
load_dotenv()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Local Scout AI Agent")
    parser.add_argument(
        "--web-only", 
        action="store_true", 
        help="Start only the web interface"
    )
    parser.add_argument(
        "--scheduler-only", 
        action="store_true", 
        help="Start only the task scheduler"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=int(os.getenv("WEB_PORT", 8001)),
        help="Port for the web interface"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default=os.getenv("WEB_HOST", "0.0.0.0"),
        help="Host for the web interface"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Run in debug mode"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_args()
    
    # Setup logging first
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_logging(log_level.upper())
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Local Scout AI Agent...")
    
    # Import necessary components
    from core.agent import ScoutAgent
    from scheduler.scheduler import TaskScheduler
    from api.app import create_app
    
    # Initialize the agent
    logger.info("Initializing AI agent...")
    agent = ScoutAgent()
    
    # Initialize the scheduler
    logger.info("Initializing task scheduler...")
    scheduler = TaskScheduler(agent)
    
    # Initialize monitoring system
    logger.info("Initializing monitoring system...")
    try:
        # Import and initialize monitoring components
        from monitoring.system_monitor import start_monitoring
        from monitoring.alerting import start_alerting, create_standard_rules
        
        # Start monitoring and alerting system
        start_monitoring()
        start_alerting()
        
        # Create standard alert rules
        create_standard_rules()
        
        logger.info("Monitoring system initialized successfully")
    except ImportError as e:
        logger.warning(f"Could not initialize monitoring system: {e}")
    except Exception as e:
        logger.error(f"Error initializing monitoring system: {e}")
    
    # Start scheduler if not web-only mode
    if not args.web_only:
        logger.info("Starting scheduler...")
        scheduler.start()
    
    # Start web server if not scheduler-only mode
    if not args.scheduler_only:
        logger.info(f"Starting web server on {args.host}:{args.port}...")
        app = create_app(agent, scheduler)
        
        import uvicorn
        uvicorn.run(
            app, 
            host=args.host, 
            port=args.port, 
            log_level="debug" if args.debug else "info"
        )
    else:
        # If only running the scheduler, keep the main thread alive
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()