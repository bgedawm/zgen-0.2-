"""
Colored Log Formatter
-----------------
This module provides a formatter that adds ANSI color codes to log messages
for better readability in terminal environments.
"""

import logging
import sys
import datetime
import re
from typing import Dict, Any, Optional


class ColoredFormatter(logging.Formatter):
    """
    A formatter that adds ANSI color codes to log messages for better
    readability in terminal environments.
    """
    
    # ANSI color codes
    COLORS = {
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'DIM': '\033[2m',
        'UNDERLINE': '\033[4m',
        'BLINK': '\033[5m',
        'REVERSE': '\033[7m',
        'HIDDEN': '\033[8m',
        
        # Foreground colors
        'FG_BLACK': '\033[30m',
        'FG_RED': '\033[31m',
        'FG_GREEN': '\033[32m',
        'FG_YELLOW': '\033[33m',
        'FG_BLUE': '\033[34m',
        'FG_MAGENTA': '\033[35m',
        'FG_CYAN': '\033[36m',
        'FG_WHITE': '\033[37m',
        'FG_DEFAULT': '\033[39m',
        
        # Background colors
        'BG_BLACK': '\033[40m',
        'BG_RED': '\033[41m',
        'BG_GREEN': '\033[42m',
        'BG_YELLOW': '\033[43m',
        'BG_BLUE': '\033[44m',
        'BG_MAGENTA': '\033[45m',
        'BG_CYAN': '\033[46m',
        'BG_WHITE': '\033[47m',
        'BG_DEFAULT': '\033[49m',
        
        # Bright foreground colors
        'FG_BRIGHT_BLACK': '\033[90m',
        'FG_BRIGHT_RED': '\033[91m',
        'FG_BRIGHT_GREEN': '\033[92m',
        'FG_BRIGHT_YELLOW': '\033[93m',
        'FG_BRIGHT_BLUE': '\033[94m',
        'FG_BRIGHT_MAGENTA': '\033[95m',
        'FG_BRIGHT_CYAN': '\033[96m',
        'FG_BRIGHT_WHITE': '\033[97m',
    }
    
    # Define color schemes for different log levels
    LEVEL_COLORS = {
        'DEBUG': COLORS['FG_CYAN'],
        'INFO': COLORS['FG_GREEN'],
        'WARNING': COLORS['FG_YELLOW'] + COLORS['BOLD'],
        'ERROR': COLORS['FG_RED'] + COLORS['BOLD'],
        'CRITICAL': COLORS['BG_RED'] + COLORS['FG_WHITE'] + COLORS['BOLD'],
    }
    
    # Define color for different parts of the log message
    PART_COLORS = {
        'timestamp': COLORS['FG_BRIGHT_BLACK'],
        'logger': COLORS['FG_BLUE'],
        'thread': COLORS['FG_MAGENTA'],
        'message': COLORS['RESET'],
        'exception': COLORS['FG_RED'],
    }
    
    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=True):
        """
        Initialize the colored formatter.
        
        Args:
            fmt: Format string
            datefmt: Date format string
            style: Format style (%, {, or $)
            use_colors: Whether to use ANSI colors
        """
        if fmt is None:
            fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        super().__init__(fmt, datefmt, style)
        
        self.use_colors = use_colors and self._supports_color(sys.stdout)
        
        # Detect if we're in a Jupyter notebook
        self.in_jupyter = self._in_jupyter()
    
    def format(self, record):
        """
        Format the log record with colors.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log message with colors
        """
        # Get the regular formatted message first
        formatted = super().format(record)
        
        if not self.use_colors:
            return formatted
        
        # Get the color for this log level
        level_color = self.LEVEL_COLORS.get(record.levelname, self.COLORS['RESET'])
        
        # Split the message into parts (timestamp, logger, level, message)
        parts = formatted.split(' - ', 3)
        
        if len(parts) >= 4:
            timestamp, logger_name, level, message = parts
            
            # Apply colors to each part
            colored_parts = [
                f"{self.PART_COLORS['timestamp']}{timestamp}{self.COLORS['RESET']}",
                f"{self.PART_COLORS['logger']}{logger_name}{self.COLORS['RESET']}",
                f"{level_color}{level}{self.COLORS['RESET']}",
                f"{self.PART_COLORS['message']}{message}{self.COLORS['RESET']}"
            ]
            
            formatted = " - ".join(colored_parts)
            
        else:
            # If we couldn't split the message, just color the whole thing based on level
            formatted = f"{level_color}{formatted}{self.COLORS['RESET']}"
        
        # Add colors to exceptions if present
        if record.exc_info:
            formatted = self._colorize_exception(formatted)
        
        return formatted
    
    def _colorize_exception(self, message):
        """
        Add colors to exception traceback in the message.
        
        Args:
            message: Message with exception
            
        Returns:
            Message with colorized exception
        """
        # Find the traceback part, usually starts with "Traceback (most recent call last):"
        match = re.search(r'(Traceback \(most recent call last\):.*)', message, re.DOTALL)
        
        if match:
            traceback_text = match.group(1)
            colorized_traceback = f"{self.PART_COLORS['exception']}{traceback_text}{self.COLORS['RESET']}"
            message = message.replace(traceback_text, colorized_traceback)
        
        return message
    
    def formatTime(self, record, datefmt=None):
        """
        Format the time from the record.
        
        Args:
            record: Log record
            datefmt: Date format
            
        Returns:
            Formatted time string
        """
        ct = datetime.datetime.fromtimestamp(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return s
    
    def _supports_color(self, stream):
        """
        Check if the stream supports color output.
        
        Args:
            stream: Stream to check
            
        Returns:
            True if color is supported, False otherwise
        """
        # Check if forced disable
        if hasattr(stream, "isatty") and not stream.isatty():
            return False
        
        # Check if NO_COLOR env var is set (see https://no-color.org/)
        if 'NO_COLOR' in os.environ:
            return False
        
        # Check for Windows
        if sys.platform == 'win32':
            # Windows 10 version 1607 and later support ANSI colors
            # but we need to check for this or use colorama
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                
                # Check if ANSI color are supported
                return kernel32.GetConsoleMode(kernel32.GetStdHandle(-11)) & 0x0004
            except:
                # If we can't check, we'll assume no color support
                return False
        
        # Check if running in a known terminal type
        plat = sys.platform
        supported_platform = plat != 'Pocket PC' and (plat != 'win32' or 'ANSICON' in os.environ)
        
        # Check if terminal type is set
        return supported_platform and os.environ.get('TERM') not in ('dumb', 'emacs')
    
    def _in_jupyter(self):
        """
        Check if code is running inside a Jupyter notebook.
        
        Returns:
            True if in Jupyter, False otherwise
        """
        try:
            from IPython import get_ipython
            if get_ipython() is not None:
                return True
            return False
        except:
            return False