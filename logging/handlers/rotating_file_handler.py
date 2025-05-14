"""
Enhanced Rotating File Handler
-------------------------
This module provides an enhanced rotating file handler with additional features
like compression, retention policies, and file naming patterns.
"""

import os
import re
import time
import gzip
import shutil
import logging
import logging.handlers
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any


class EnhancedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    An enhanced rotating file handler that supports compression,
    retention policies, and custom file naming patterns.
    """
    
    def __init__(
        self,
        filename,
        mode='a',
        maxBytes=0,
        backupCount=0,
        encoding=None,
        delay=False,
        errors=None,
        compress=False,
        compress_method='gzip',
        retention_days=None,
        date_pattern='%Y-%m-%d',
        log_pattern=None
    ):
        """
        Initialize the enhanced rotating file handler.
        
        Args:
            filename: Base log filename
            mode: File open mode
            maxBytes: Maximum file size in bytes before rotation
            backupCount: Maximum number of backup files to keep
            encoding: File encoding
            delay: Whether to delay opening the file until first log
            errors: Error handling mode for file errors
            compress: Whether to compress rotated files
            compress_method: Compression method ('gzip', 'bzip2', 'zip')
            retention_days: Number of days to keep log files
            date_pattern: Date pattern for file naming
            log_pattern: Custom pattern for log file naming
        """
        super().__init__(
            filename, mode, maxBytes, backupCount,
            encoding, delay, errors
        )
        
        self.compress = compress
        self.compress_method = compress_method
        self.retention_days = retention_days
        self.date_pattern = date_pattern
        self.log_pattern = log_pattern or f'%s.{date_pattern}.%d'
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        # Initialize compression
        if compress and compress_method not in ('gzip', 'bzip2', 'zip'):
            raise ValueError(f"Unsupported compression method: {compress_method}")
        
        # Check for existing compressed logs
        self._find_existing_logs()
    
    def _find_existing_logs(self):
        """Find existing log files and update counts accordingly."""
        if self.backupCount <= 0:
            return
        
        # Get the directory and base filename
        dirname, basename = os.path.split(self.baseFilename)
        
        # Match the log files using the pattern
        if '%s' in self.log_pattern and '%d' in self.log_pattern:
            # Pattern with both date and counter
            prefix, suffix = self.log_pattern.split('%s')
            prefix = prefix.replace('%', '%%')
            suffix = suffix.replace('%', '%%')
            pattern = f"{prefix}{re.escape(basename)}{suffix}"
            pattern = pattern.replace('%%d', r'(\d+)')  # Replace %d with group
            pattern = pattern.replace(f'%%{self.date_pattern}', r'([^.]+)')  # Replace date with group
        else:
            # Standard pattern with just counter
            pattern = f"{re.escape(basename)}\\.\\d+"
        
        files = []
        for fn in os.listdir(dirname):
            match = re.match(pattern, fn)
            if match:
                files.append(os.path.join(dirname, fn))
        
        if self.retention_days:
            self._apply_retention_policy(files)
        
        # Update the count based on existing files
        self.backupCount = max(self.backupCount, len(files))
    
    def _apply_retention_policy(self, files):
        """
        Apply retention policy to log files.
        
        Args:
            files: List of log files to check
        """
        if not self.retention_days or self.retention_days <= 0:
            return
        
        now = time.time()
        max_age = self.retention_days * 24 * 60 * 60  # days to seconds
        
        for filepath in files:
            if os.path.exists(filepath):
                mtime = os.path.getmtime(filepath)
                age = now - mtime
                
                if age > max_age:
                    try:
                        os.unlink(filepath)
                    except (IOError, OSError):
                        # Error removing file, just continue
                        pass
    
    def _get_next_name(self, index):
        """
        Get the next log filename based on the pattern.
        
        Args:
            index: Index of the backup file
            
        Returns:
            Next log filename
        """
        if '%s' in self.log_pattern and '%d' in self.log_pattern:
            # Pattern with both date and counter
            date_str = datetime.now().strftime(self.date_pattern)
            filename = self.log_pattern % (self.baseFilename, date_str, index)
        else:
            # Standard pattern with just counter
            filename = f"{self.baseFilename}.{index}"
        
        return filename
    
    def doRollover(self):
        """Perform log rotation with compression if enabled."""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        if self.backupCount > 0:
            # Shift all existing logs
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self._get_next_name(i)
                dfn = self._get_next_name(i + 1)
                
                # Check compressed versions too
                if self.compress:
                    if not os.path.exists(sfn):
                        sfn = f"{sfn}.gz" if self.compress_method == 'gzip' else f"{sfn}.{self.compress_method}"
                    if os.path.exists(dfn):
                        os.unlink(dfn)
                
                if os.path.exists(sfn):
                    try:
                        os.rename(sfn, dfn)
                    except OSError:
                        # Can't rename, try to copy and delete
                        try:
                            shutil.copy2(sfn, dfn)
                            os.unlink(sfn)
                        except OSError:
                            # Just continue on error
                            pass
            
            # Create the new backup from the current log file
            dfn = self._get_next_name(1)
            
            try:
                if self.compress:
                    # Compress the file
                    self._compress_file(self.baseFilename, dfn)
                else:
                    # Just rename the file
                    os.rename(self.baseFilename, dfn)
            except OSError:
                # Can't rename, try to copy and delete
                try:
                    shutil.copy2(self.baseFilename, dfn)
                    os.unlink(self.baseFilename)
                except OSError:
                    # Just continue on error
                    pass
        
        # Open new log file
        if not self.delay:
            self.stream = self._open()
        
        # Apply retention policy
        if self.retention_days:
            dirname = os.path.dirname(self.baseFilename)
            self._apply_retention_policy([os.path.join(dirname, f) for f in os.listdir(dirname)])
    
    def _compress_file(self, source, dest):
        """
        Compress a log file.
        
        Args:
            source: Source file to compress
            dest: Destination file
        """
        if self.compress_method == 'gzip':
            dest = f"{dest}.gz"
            with open(source, 'rb') as f_in:
                with gzip.open(dest, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        elif self.compress_method == 'bzip2':
            try:
                import bz2
                dest = f"{dest}.bz2"
                with open(source, 'rb') as f_in:
                    with bz2.open(dest, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            except ImportError:
                # Fall back to gzip if bz2 not available
                self._compress_file_gzip(source, dest)
        
        elif self.compress_method == 'zip':
            try:
                import zipfile
                dest = f"{dest}.zip"
                with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as f_zip:
                    f_zip.write(source, os.path.basename(source))
            except ImportError:
                # Fall back to gzip if zipfile not available
                self._compress_file_gzip(source, dest)
        
        # Remove the original file
        os.unlink(source)