"""
S3 Storage Provider
---------------
Provides integration with Amazon S3 or compatible storage for storing and retrieving data.
"""

import os
import logging
import asyncio
import json
import pickle
import boto3
import aioboto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, BinaryIO, Tuple

from ..base import StorageProvider

# Setup logger
logger = logging.getLogger(__name__)


class S3StorageProvider(StorageProvider):
    """Amazon S3 or compatible storage provider."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for required configuration
        aws_access_key = self.config.get('aws_access_key') or os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret_key = self.config.get('aws_secret_key') or os.getenv('AWS_SECRET_ACCESS_KEY')
        bucket_name = self.config.get('bucket_name') or os.getenv('S3_BUCKET_NAME')
        
        if not bucket_name:
            raise ValueError("S3 bucket name is required. Set 'bucket_name' in config or S3_BUCKET_NAME environment variable.")
        
        # Set default values
        self.config.setdefault('aws_access_key', aws_access_key)
        self.config.setdefault('aws_secret_key', aws_secret_key)
        self.config.setdefault('bucket_name', bucket_name)
        self.config.setdefault('region_name', self.config.get('region_name') or os.getenv('AWS_REGION', 'us-east-1'))
        
        # Set default prefix (folder)
        self.config.setdefault('prefix', self.config.get('prefix') or os.getenv('S3_PREFIX', ''))
        
        # S3-compatible endpoint (for MinIO, etc.)
        endpoint_url = self.config.get('endpoint_url') or os.getenv('S3_ENDPOINT_URL')
        if endpoint_url:
            self.config['endpoint_url'] = endpoint_url
        
        # Additional options
        self.config.setdefault('content_type_detection', True)
        self.config.setdefault('create_bucket', self.config.get('create_bucket') or os.getenv('S3_CREATE_BUCKET', 'false').lower() == 'true')
    
    def initialize(self) -> None:
        """Initialize the S3 storage provider."""
        try:
            # Session will be created when needed
            self.session = None
            self.resource = None
            
            # Check if bucket exists and possibly create it
            if self.config['create_bucket']:
                self._sync_ensure_bucket_exists()
            
            logger.info(f"Initialized S3 storage provider for bucket {self.config['bucket_name']}")
        except Exception as e:
            logger.error(f"Error initializing S3 storage provider: {str(e)}")
            raise
    
    def _sync_ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create it if necessary (synchronous)."""
        s3_config = {
            'region_name': self.config['region_name']
        }
        
        if 'endpoint_url' in self.config:
            s3_config['endpoint_url'] = self.config['endpoint_url']
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=self.config['aws_access_key'],
            aws_secret_access_key=self.config['aws_secret_key'],
            **s3_config
        )
        
        try:
            s3_client.head_bucket(Bucket=self.config['bucket_name'])
            logger.info(f"S3 bucket {self.config['bucket_name']} exists")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.config['region_name'] == 'us-east-1':
                        # Special case for us-east-1
                        s3_client.create_bucket(Bucket=self.config['bucket_name'])
                    else:
                        # Other regions need LocationConstraint
                        s3_client.create_bucket(
                            Bucket=self.config['bucket_name'],
                            CreateBucketConfiguration={
                                'LocationConstraint': self.config['region_name']
                            }
                        )
                    logger.info(f"Created S3 bucket {self.config['bucket_name']}")
                except ClientError as create_error:
                    logger.error(f"Error creating S3 bucket: {str(create_error)}")
                    raise
            else:
                # Other error
                logger.error(f"Error checking S3 bucket: {str(e)}")
                raise
    
    async def _get_session(self):
        """Get or create an aioboto3 session."""
        if self.session is None:
            s3_config = {
                'region_name': self.config['region_name']
            }
            
            if 'endpoint_url' in self.config:
                s3_config['endpoint_url'] = self.config['endpoint_url']
            
            self.session = aioboto3.Session(
                aws_access_key_id=self.config['aws_access_key'],
                aws_secret_access_key=self.config['aws_secret_key']
            )
        
        return self.session
    
    def _get_full_key(self, key: str) -> str:
        """
        Get the full S3 key including the prefix.
        
        Args:
            key: Storage key
            
        Returns:
            Full S3 key
        """
        prefix = self.config['prefix']
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        
        # Ensure the key doesn't start with /
        if key.startswith('/'):
            key = key[1:]
        
        return f"{prefix}{key}"
    
    def _parse_content_type(self, key: str) -> str:
        """
        Parse content type based on file extension.
        
        Args:
            key: Storage key
            
        Returns:
            Content type
        """
        if not self.config['content_type_detection']:
            return 'application/octet-stream'
        
        _, ext = os.path.splitext(key)
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
        
        return content_type_map.get(ext, 'application/octet-stream')
    
    async def store(self, key: str, data: Any) -> Dict[str, Any]:
        """
        Store data in S3.
        
        Args:
            key: Storage key
            data: Data to store
            
        Returns:
            Storage status
        """
        try:
            session = await self._get_session()
            s3_key = self._get_full_key(key)
            
            # Extra args for S3 upload
            extra_args = {}
            
            # Determine the data type and format
            if isinstance(data, str):
                # Store as text
                body = data.encode('utf-8')
                extra_args['ContentType'] = 'text/plain; charset=utf-8'
                data_type = 'text'
            
            elif isinstance(data, bytes):
                # Store as binary
                body = data
                extra_args['ContentType'] = self._parse_content_type(key)
                data_type = 'binary'
            
            elif isinstance(data, (dict, list)) or hasattr(data, '__dict__'):
                # Store as JSON
                try:
                    if hasattr(data, '__dict__'):
                        json_data = json.dumps(data.__dict__)
                    else:
                        json_data = json.dumps(data)
                    
                    body = json_data.encode('utf-8')
                    extra_args['ContentType'] = 'application/json; charset=utf-8'
                    data_type = 'json'
                except (TypeError, OverflowError):
                    # If JSON serialization fails, fallback to pickle
                    body = pickle.dumps(data)
                    extra_args['ContentType'] = 'application/python-pickle'
                    data_type = 'pickle'
            
            else:
                # Store as pickle
                body = pickle.dumps(data)
                extra_args['ContentType'] = 'application/python-pickle'
                data_type = 'pickle'
            
            # Set metadata
            extra_args['Metadata'] = {
                'data_type': data_type,
                'timestamp': datetime.now().isoformat()
            }
            
            s3_config = {}
            if 'endpoint_url' in self.config:
                s3_config['endpoint_url'] = self.config['endpoint_url']
            
            async with session.client('s3', region_name=self.config['region_name'], **s3_config) as s3:
                await s3.put_object(
                    Bucket=self.config['bucket_name'],
                    Key=s3_key,
                    Body=body,
                    **extra_args
                )
            
            return {
                'success': True,
                'key': key,
                's3_key': s3_key,
                'bucket': self.config['bucket_name'],
                'size': len(body),
                'data_type': data_type,
                'content_type': extra_args['ContentType'],
                'timestamp': extra_args['Metadata']['timestamp']
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
        Retrieve data from S3.
        
        Args:
            key: Storage key
            
        Returns:
            Retrieved data
        
        Raises:
            FileNotFoundError: If the key does not exist
        """
        try:
            session = await self._get_session()
            s3_key = self._get_full_key(key)
            
            s3_config = {}
            if 'endpoint_url' in self.config:
                s3_config['endpoint_url'] = self.config['endpoint_url']
            
            async with session.client('s3', region_name=self.config['region_name'], **s3_config) as s3:
                try:
                    response = await s3.get_object(
                        Bucket=self.config['bucket_name'],
                        Key=s3_key
                    )
                except ClientError as e:
                    if e.response['Error']['Code'] in ['NoSuchKey', 'NotFound', '404']:
                        raise FileNotFoundError(f"Key not found: {key}")
                    raise
                
                # Get metadata
                metadata = response.get('Metadata', {})
                content_type = response.get('ContentType', '')
                
                # Read the data
                body = await response['Body'].read()
                
                # Determine how to interpret the data
                data_type = metadata.get('data_type')
                
                if data_type == 'text' or (not data_type and 'text/' in content_type):
                    # Text data
                    return body.decode('utf-8')
                
                elif data_type == 'json' or (not data_type and 'application/json' in content_type):
                    # JSON data
                    try:
                        return json.loads(body.decode('utf-8'))
                    except json.JSONDecodeError:
                        # Not valid JSON, return as text
                        return body.decode('utf-8')
                
                elif data_type == 'pickle' or (not data_type and 'application/python-pickle' in content_type):
                    # Pickle data
                    return pickle.loads(body)
                
                else:
                    # Binary data or unknown type
                    # Try to decode as text
                    try:
                        text = body.decode('utf-8')
                        
                        # Try to parse as JSON
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            # Not valid JSON, return as text
                            return text
                    
                    except UnicodeDecodeError:
                        # Not a text file, try to unpickle
                        try:
                            return pickle.loads(body)
                        except:
                            # Not a pickle, return as binary
                            return body
        
        except FileNotFoundError:
            logger.error(f"Key not found: {key}")
            raise
        
        except Exception as e:
            logger.error(f"Error retrieving data for key '{key}': {str(e)}")
            raise
    
    async def delete(self, key: str) -> Dict[str, Any]:
        """
        Delete data from S3.
        
        Args:
            key: Storage key
            
        Returns:
            Deletion status
        """
        try:
            session = await self._get_session()
            s3_key = self._get_full_key(key)
            
            # Get metadata before deletion
            try:
                metadata = await self.get_metadata(key)
            except:
                metadata = {}
            
            s3_config = {}
            if 'endpoint_url' in self.config:
                s3_config['endpoint_url'] = self.config['endpoint_url']
            
            async with session.client('s3', region_name=self.config['region_name'], **s3_config) as s3:
                try:
                    await s3.delete_object(
                        Bucket=self.config['bucket_name'],
                        Key=s3_key
                    )
                except ClientError as e:
                    if e.response['Error']['Code'] in ['NoSuchKey', 'NotFound', '404']:
                        return {
                            'success': False,
                            'key': key,
                            'error': f"Key not found: {key}"
                        }
                    raise
            
            return {
                'success': True,
                'key': key,
                's3_key': s3_key,
                'bucket': self.config['bucket_name'],
                'size': metadata.get('size'),
                'timestamp': metadata.get('last_modified')
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
            session = await self._get_session()
            
            # Combine the base prefix with the filter prefix
            if prefix:
                if prefix.startswith('/'):
                    prefix = prefix[1:]
                s3_prefix = self._get_full_key(prefix)
            else:
                s3_prefix = self.config['prefix']
            
            s3_config = {}
            if 'endpoint_url' in self.config:
                s3_config['endpoint_url'] = self.config['endpoint_url']
            
            async with session.client('s3', region_name=self.config['region_name'], **s3_config) as s3:
                paginator = s3.get_paginator('list_objects_v2')
                
                list_params = {
                    'Bucket': self.config['bucket_name']
                }
                
                if s3_prefix:
                    list_params['Prefix'] = s3_prefix
                
                keys = []
                
                async for page in paginator.paginate(**list_params):
                    if 'Contents' not in page:
                        continue
                    
                    for obj in page['Contents']:
                        key = obj['Key']
                        
                        # Remove the base prefix to get the relative key
                        base_prefix = self.config['prefix']
                        if base_prefix and key.startswith(base_prefix):
                            if base_prefix.endswith('/'):
                                key = key[len(base_prefix):]
                            else:
                                key = key[len(base_prefix) + 1:]
                        
                        # Skip empty keys (directories)
                        if key:
                            keys.append(key)
            
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
            session = await self._get_session()
            s3_key = self._get_full_key(key)
            
            s3_config = {}
            if 'endpoint_url' in self.config:
                s3_config['endpoint_url'] = self.config['endpoint_url']
            
            async with session.client('s3', region_name=self.config['region_name'], **s3_config) as s3:
                try:
                    response = await s3.head_object(
                        Bucket=self.config['bucket_name'],
                        Key=s3_key
                    )
                except ClientError as e:
                    if e.response['Error']['Code'] in ['NoSuchKey', 'NotFound', '404']:
                        raise FileNotFoundError(f"Key not found: {key}")
                    raise
                
                return {
                    'success': True,
                    'key': key,
                    's3_key': s3_key,
                    'bucket': self.config['bucket_name'],
                    'size': response['ContentLength'],
                    'last_modified': response['LastModified'].isoformat(),
                    'etag': response['ETag'].strip('"'),
                    'content_type': response.get('ContentType', 'application/octet-stream'),
                    'metadata': response.get('Metadata', {})
                }
        
        except FileNotFoundError:
            logger.error(f"Key not found: {key}")
            raise
        
        except Exception as e:
            logger.error(f"Error getting metadata for key '{key}': {str(e)}")
            raise
    
    async def generate_presigned_url(self, key: str, expires_in: int = 3600, operation: str = 'get') -> Dict[str, Any]:
        """
        Generate a presigned URL for the object.
        
        Args:
            key: Storage key
            expires_in: URL expiration time in seconds
            operation: S3 operation ('get' or 'put')
            
        Returns:
            Dictionary with presigned URL information
        """
        try:
            session = await self._get_session()
            s3_key = self._get_full_key(key)
            
            s3_config = {}
            if 'endpoint_url' in self.config:
                s3_config['endpoint_url'] = self.config['endpoint_url']
            
            async with session.client('s3', region_name=self.config['region_name'], **s3_config) as s3:
                client_method = 'get_object' if operation.lower() == 'get' else 'put_object'
                
                url = await s3.generate_presigned_url(
                    ClientMethod=client_method,
                    Params={
                        'Bucket': self.config['bucket_name'],
                        'Key': s3_key
                    },
                    ExpiresIn=expires_in
                )
                
                return {
                    'success': True,
                    'key': key,
                    's3_key': s3_key,
                    'bucket': self.config['bucket_name'],
                    'url': url,
                    'expires_in': expires_in,
                    'operation': operation
                }
        
        except Exception as e:
            logger.error(f"Error generating presigned URL for key '{key}': {str(e)}")
            
            return {
                'success': False,
                'key': key,
                'error': str(e)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the S3 storage integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if S3 is accessible
            loop = asyncio.get_event_loop()
            
            async def check() -> Tuple[bool, Optional[str]]:
                try:
                    session = await self._get_session()
                    
                    s3_config = {}
                    if 'endpoint_url' in self.config:
                        s3_config['endpoint_url'] = self.config['endpoint_url']
                    
                    async with session.client('s3', region_name=self.config['region_name'], **s3_config) as s3:
                        # Try to check if the bucket exists
                        try:
                            await s3.head_bucket(Bucket=self.config['bucket_name'])
                            return True, None
                        except ClientError as e:
                            if e.response['Error']['Code'] == '404':
                                return False, f"Bucket {self.config['bucket_name']} does not exist"
                            elif e.response['Error']['Code'] == '403':
                                return False, f"Access denied to bucket {self.config['bucket_name']}"
                            else:
                                return False, str(e)
                
                except Exception as e:
                    return False, str(e)
            
            is_healthy, error_message = loop.run_until_complete(check())
            
            if is_healthy:
                return {
                    "status": "healthy",
                    "provider": "s3",
                    "bucket": self.config['bucket_name'],
                    "region": self.config['region_name'],
                    "endpoint": self.config.get('endpoint_url', 'AWS')
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "s3",
                    "bucket": self.config['bucket_name'],
                    "region": self.config['region_name'],
                    "endpoint": self.config.get('endpoint_url', 'AWS'),
                    "error": error_message
                }
        
        except Exception as e:
            logger.error(f"S3 health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "s3",
                "bucket": self.config['bucket_name'],
                "error": str(e)
            }