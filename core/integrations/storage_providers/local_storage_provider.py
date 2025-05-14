"""
Local Storage Provider
------------------
Provides integration with local filesystem for storing and retrieving data.
"""

import os
import logging
import asyncio
import json
import pickle
import base64
import aiofiles
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, BinaryIO

from ..base import StorageProvider

# Setup logger
logger = logging.getLogger(__name__)


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Set default storage path
        base_path = self.config.get('base_path') or os.getenv('LOCAL_STORAGE_PATH', './data/storage')
        self.config.setdefault('base_path', base_path)
        
        # Create directory if it doesn't exist
        os.makedirs(self.config['base_path'], exist_ok=True)
    
    def initialize(self) -> None:
        """Initialize the local storage provider."""
        try:
            # Ensure the base directory exists
            Path(self.config['base_path']).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Initialized local storage provider at {self.config['base_path']}")
        except Exception as e:
            logger.error(f"Error initializing local storage provider: {str(e)}")
            raise
    
    def _get_full_path(self, key: str) -> str:
        """
        Get the full path for a key.
        
        Args:
            key: Storage key
            
        Returns:
            Full file path
        """
        # Normalize the key (replace slashes with os-specific separator)
        norm_key = os.path.normpath(key)
        
        # Join with base path
        return os.path.join(self.config['base_path'], norm_key)
    
    def _ensure_directory_exists(self, path: str) -> None:
        """
        Ensure that the directory for a file exists.
        
        Args:
            path: File path
        """
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
    
    async def store(self, key: str, data: Any) -> Dict[str, Any]:
        """
        Store data in the local filesystem.
        
        Args:
            key: Storage key
            data: Data to store
            
        Returns:
            Storage status
        """
        try:
            full_path = self._get_full_path(key)
            self._ensure_directory_exists(full_path)
            
            # Determine the data type and format
            if isinstance(data, str):
                # Store as text
                async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                    await f.write(data)
                data_type = 'text'
            
            elif isinstance(data, bytes):
                # Store as binary
                async with aiofiles.open(full_path, 'wb') as f:
                    await f.write(data)
                data_type = 'binary'
            
            elif isinstance(data, (dict, list)) or hasattr(data, '__dict__'):
                # Store as JSON
                try:
                    async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                        if hasattr(data, '__dict__'):
                            await f.write(json.dumps(data.__dict__))
                        else:
                            await f.write(json.dumps(data))
                    data_type = 'json'
                except (TypeError, OverflowError):
                    # If JSON serialization fails, fallback to pickle
                    async with aiofiles.open(full_path, 'wb') as f:
                        await f.write(pickle.dumps(data))
                    data_type = 'pickle'
            
            else:
                # Store as pickle
                async with aiofiles.open(full_path, 'wb') as f:
                    await f.write(pickle.dumps(data))
                data_type = 'pickle'
            
            # Get file metadata
            stat = os.stat(full_path)
            
            return {
                'success': True,
                'key': key,
                'path': full_path,
                'size': stat.st_size,
                'timestamp': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'data_type': data_type
            }
        
        except Exception as e:
            logger.error(f"Error storing data for key '{key}': {str(e)}")
            
            return {
                'success': False,
                'key': key,
                'error': str(e)
            }
    
    async def retrieve(self, key: str) -> Any:
        """
        Retrieve data from the local filesystem.
        
        Args:
            key: Storage key
            
        Returns:
            Retrieved data
        
        Raises:
            FileNotFoundError: If the key does not exist
        """
        try:
            full_path = self._get_full_path(key)
            
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Key not found: {key}")
            
            # Try to determine file type by extension
            _, ext = os.path.splitext(full_path)
            ext = ext.lower()
            
            if ext in ['.txt', '.md', '.csv', '.html', '.xml', '.js', '.css', '.py', '.json']:
                # Text file
                async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                    data = await f.read()
                
                # Try to parse JSON if it's a .json file
                if ext == '.json':
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        # Not valid JSON, return as text
                        pass
                
                return data
            
            elif ext in ['.pkl', '.pickle']:
                # Pickle file
                async with aiofiles.open(full_path, 'rb') as f:
                    data = await f.read()
                return pickle.loads(data)
            
            else:
                # Try to read as text first
                try:
                    async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                        data = await f.read()
                    
                    # Try to parse as JSON
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError:
                        # Not valid JSON, return as text
                        return data
                        
                except UnicodeDecodeError:
                    # Not a text file, read as binary
                    async with aiofiles.open(full_path, 'rb') as f:
                        data = await f.read()
                    
                    # Try to unpickle
                    try:
                        return pickle.loads(data)
                    except:
                        # Not a pickle, return as binary
                        return data
        
        except FileNotFoundError:
            logger.error(f"Key not found: {key}")
            raise
        
        except Exception as e:
            logger.error(f"Error retrieving data for key '{key}': {str(e)}")
            raise
    
    async def delete(self, key: str) -> Dict[str, Any]:
        """
        Delete data from the local filesystem.
        
        Args:
            key: Storage key
            
        Returns:
            Deletion status
        """
        try:
            full_path = self._get_full_path(key)
            
            if not os.path.exists(full_path):
                return {
                    'success': False,
                    'key': key,
                    'error': f"Key not found: {key}"
                }
            
            # Get file metadata before deletion
            stat = os.stat(full_path)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # Delete the file
            os.remove(full_path)
            
            # Try to remove empty parent directories
            try:
                directory = os.path.dirname(full_path)
                while directory and directory != self.config['base_path']:
                    if not os.listdir(directory):
                        os.rmdir(directory)
                        directory = os.path.dirname(directory)
                    else:
                        break
            except:
                # Ignore errors when cleaning up directories
                pass
            
            return {
                'success': True,
                'key': key,
                'size': size,
                'timestamp': mtime
            }
        
        except Exception as e:
            logger.error(f"Error deleting key '{key}': {str(e)}")
            
            return {
                'success': False,
                'key': key,
                'error': str(e)
            }
    
    async def list(self, prefix: Optional[str] = None) -> List[str]:
        """
        List storage keys.
        
        Args:
            prefix: Optional key prefix filter
            
        Returns:
            List of keys
        """
        try:
            base_path = Path(self.config['base_path'])
            prefix_path = base_path
            
            # Apply prefix if specified
            if prefix:
                prefix_path = base_path / os.path.normpath(prefix)
            
            # Check if the prefix path exists
            if not prefix_path.exists():
                return []
            
            # Get all files recursively
            keys = []
            
            if prefix_path.is_file():
                # Handle the case where prefix directly points to a file
                rel_path = prefix_path.relative_to(base_path)
                keys.append(str(rel_path).replace('\\', '/'))
            else:
                # Get all files recursively
                for path in prefix_path.glob('**/*'):
                    if path.is_file():
                        rel_path = path.relative_to(base_path)
                        keys.append(str(rel_path).replace('\\', '/'))
            
            return sorted(keys)
        
        except Exception as e:
            logger.error(f"Error listing keys with prefix '{prefix}': {str(e)}")
            return []
    
    async def get_metadata(self, key: str) -> Dict[str, Any]:
        """
        Get metadata for a storage key.
        
        Args:
            key: Storage key
            
        Returns:
            Metadata dictionary
        
        Raises:
            FileNotFoundError: If the key does not exist
        """
        try:
            full_path = self._get_full_path(key)
            
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Key not found: {key}")
            
            # Get file metadata
            stat = os.stat(full_path)
            
            # Try to determine file type by extension
            _, ext = os.path.splitext(full_path)
            ext = ext.lower()
            
            # Map extensions to content types
            content_type_map = {
                '.txt': 'text/plain',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.css': 'text/css',
                '.js': 'application/javascript',
                '.json': 'application/json',
                '.xml': 'application/xml',
                '.csv': 'text/csv',
                '.md': 'text/markdown',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.pdf': 'application/pdf',
                '.zip': 'application/zip',
                '.pkl': 'application/pickle',
                '.pickle': 'application/pickle'
            }
            
            content_type = content_type_map.get(ext, 'application/octet-stream')
            
            return {
                'success': True,
                'key': key,
                'path': full_path,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'extension': ext,
                'content_type': content_type
            }
        
        except FileNotFoundError:
            logger.error(f"Key not found: {key}")
            raise
        
        except Exception as e:
            logger.error(f"Error getting metadata for key '{key}': {str(e)}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the local storage integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            base_path = self.config['base_path']
            
            # Check if the base path exists and is writable
            if not os.path.exists(base_path):
                try:
                    os.makedirs(base_path, exist_ok=True)
                except:
                    return {
                        "status": "unhealthy",
                        "provider": "local_storage",
                        "error": f"Base path '{base_path}' does not exist and could not be created"
                    }
            
            # Check if we can write to the directory
            test_file = os.path.join(base_path, '.health_check')
            try:
                with open(test_file, 'w') as f:
                    f.write('health check')
                os.remove(test_file)
            except:
                return {
                    "status": "unhealthy",
                    "provider": "local_storage",
                    "error": f"Base path '{base_path}' is not writable"
                }
            
            # Get disk usage
            try:
                total, used, free = os.statvfs(base_path)[0:3]
                total_space = total * used
                free_space = free * total
                usage_percent = (total_space - free_space) / total_space * 100
            except:
                # Fallback for Windows
                total_space = free_space = usage_percent = None
            
            return {
                "status": "healthy",
                "provider": "local_storage",
                "path": base_path,
                "details": {
                    "total_space": total_space,
                    "free_space": free_space,
                    "usage_percent": usage_percent
                } if total_space is not None else {}
            }
            
        except Exception as e:
            logger.error(f"Local storage health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "local_storage",
                "error": str(e)
            }