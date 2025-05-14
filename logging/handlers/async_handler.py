"""
Asynchronous Logging Handlers
-------------------------
This module provides asynchronous logging handlers for better performance
when logging large amounts of data or to slow destinations.
"""

import os
import logging
import logging.handlers
import queue
import threading
import time
from typing import Any, Optional, Dict, List


class AsyncHandler(logging.Handler):
    """
    A base handler that processes log records asynchronously.
    Subclasses must implement the _emit method.
    """
    
    def __init__(self, capacity=10000):
        """
        Initialize the async handler.
        
        Args:
            capacity: Maximum number of log records to buffer before dropping
        """
        super().__init__()
        
        # Create queue and worker thread
        self.queue = queue.Queue(capacity)
        self.thread = None
        self.running = False
        
        # Stats
        self.processed_records = 0
        self.dropped_records = 0
        self.errors = 0
        self.last_flush_time = time.time()
        
        # Start the worker thread
        self._start_worker()
    
    def _start_worker(self):
        """Start the worker thread to process log records."""
        if self.thread is None or not self.thread.is_alive():
            self.running = True
            self.thread = threading.Thread(
                target=self._worker_thread,
                name=f"AsyncHandler-{id(self)}",
                daemon=True
            )
            self.thread.start()
    
    def _worker_thread(self):
        """Worker thread that processes log records from the queue."""
        while self.running:
            try:
                # Get record from queue with timeout to check running flag periodically
                try:
                    record = self.queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                # Process the record
                try:
                    self._emit(record)
                    self.processed_records += 1
                except Exception as e:
                    self.handleError(record)
                    self.errors += 1
                finally:
                    self.queue.task_done()
                
                # Flush periodically
                if time.time() - self.last_flush_time > 5:  # Flush every 5 seconds
                    try:
                        self.flush()
                    except:
                        pass
                    self.last_flush_time = time.time()
            
            except Exception:
                # Log exceptions in the worker thread
                self.handleError(None)
    
    def emit(self, record):
        """
        Add the record to the queue for processing.
        
        Args:
            record: Log record to emit
        """
        try:
            if self.running and not self.queue.full():
                self.queue.put_nowait(record)
            else:
                self.dropped_records += 1
        except Exception:
            self.handleError(record)
    
    def _emit(self, record):
        """
        Process a log record (must be implemented by subclasses).
        
        Args:
            record: Log record to process
        """
        raise NotImplementedError("Subclasses must implement _emit")
    
    def flush(self):
        """Flush any buffered log records."""
        # Subclasses may implement this
        pass
    
    def close(self):
        """Close the handler and wait for processing to complete."""
        if not self.running:
            return
        
        # Signal the thread to stop
        self.running = False
        
        # Wait for all records to be processed
        if self.thread is not None and self.thread.is_alive():
            # Add a sentinel to the queue to ensure the thread wakes up
            try:
                self.queue.put_nowait(None)
            except queue.Full:
                pass
            
            # Give the thread a chance to exit
            self.thread.join(timeout=5.0)
            
            # If the thread is still alive, we can't do much about it
            # since it's a daemon thread, it will be terminated on program exit
        
        # Close the underlying handler
        super().close()
    
    def get_stats(self):
        """
        Get statistics about the handler.
        
        Returns:
            Dictionary with handler statistics
        """
        return {
            'processed_records': self.processed_records,
            'dropped_records': self.dropped_records,
            'errors': self.errors,
            'queue_size': self.queue.qsize(),
            'queue_capacity': self.queue.maxsize,
        }


class AsyncFileHandler(AsyncHandler):
    """
    An asynchronous file handler that writes log records to a file.
    """
    
    def __init__(self, filename, mode='a', encoding='utf-8', capacity=10000):
        """
        Initialize the async file handler.
        
        Args:
            filename: Path to the log file
            mode: File mode ('a' for append, 'w' for write)
            encoding: File encoding
            capacity: Maximum number of log records to buffer before dropping
        """
        super().__init__(capacity=capacity)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        self.filename = filename
        self.mode = mode
        self.encoding = encoding
        self.stream = None
        
        # Open the file
        self._open()
    
    def _open(self):
        """Open the log file."""
        self.stream = open(self.filename, self.mode, encoding=self.encoding)
    
    def _emit(self, record):
        """
        Write the log record to the file.
        
        Args:
            record: Log record to write
        """
        if record is None:
            return
        
        # Check if the file is still open
        if self.stream is None or self.stream.closed:
            self._open()
        
        # Format the record
        msg = self.format(record)
        
        # Write to the file
        self.stream.write(msg + '\n')
        self.stream.flush()
    
    def flush(self):
        """Flush the file stream."""
        if self.stream is not None and not self.stream.closed:
            self.stream.flush()
    
    def close(self):
        """Close the handler and the file stream."""
        # Close the async handler first to stop processing records
        super().close()
        
        # Close the file stream
        if self.stream is not None and not self.stream.closed:
            self.stream.flush()
            self.stream.close()
            self.stream = None