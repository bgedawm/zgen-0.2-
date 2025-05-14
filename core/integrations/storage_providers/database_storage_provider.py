"""
Database Storage Provider
--------------------
Provides integration with database systems for storing and retrieving data.
"""

import os
import logging
import json
import pickle
import base64
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

import aiosqlite
import aiomysql
import asyncpg
import motor.motor_asyncio

from ..base import StorageProvider

# Setup logger
logger = logging.getLogger(__name__)


class DatabaseStorageProvider(StorageProvider):
    """Database storage provider for various database systems."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for required configuration
        db_type = self.config.get('type') or os.getenv('STORAGE_DB_TYPE', 'sqlite')
        self.config.setdefault('type', db_type.lower())
        
        # Table/collection name
        table_name = self.config.get('table_name') or os.getenv('STORAGE_TABLE_NAME', 'agent_storage')
        self.config.setdefault('table_name', table_name)
        
        # Auto-create table if not exists
        auto_create = self.config.get('auto_create') or os.getenv('STORAGE_AUTO_CREATE', 'true').lower() == 'true'
        self.config.setdefault('auto_create', auto_create)
        
        # Connection settings based on DB type
        if self.config['type'] == 'sqlite':
            db_path = self.config.get('path') or os.getenv('STORAGE_DB_PATH', './data/storage.sqlite')
            self.config.setdefault('path', db_path)
            
        elif self.config['type'] in ['mysql', 'postgresql']:
            host = self.config.get('host') or os.getenv(f"{self.config['type'].upper()}_HOST", 'localhost')
            port = self.config.get('port') or int(os.getenv(f"{self.config['type'].upper()}_PORT", '3306' if self.config['type'] == 'mysql' else '5432'))
            user = self.config.get('user') or os.getenv(f"{self.config['type'].upper()}_USER")
            password = self.config.get('password') or os.getenv(f"{self.config['type'].upper()}_PASSWORD")
            database = self.config.get('database') or os.getenv(f"{self.config['type'].upper()}_DATABASE")
            
            if not user or not database:
                raise ValueError(f"{self.config['type'].capitalize()} database requires user and database name.")
            
            self.config.setdefault('host', host)
            self.config.setdefault('port', port)
            self.config.setdefault('user', user)
            self.config.setdefault('password', password)
            self.config.setdefault('database', database)
            
        elif self.config['type'] == 'mongodb':
            uri = self.config.get('uri') or os.getenv('MONGODB_URI')
            if not uri:
                host = self.config.get('host') or os.getenv('MONGODB_HOST', 'localhost')
                port = self.config.get('port') or int(os.getenv('MONGODB_PORT', '27017'))
                user = self.config.get('user') or os.getenv('MONGODB_USER')
                password = self.config.get('password') or os.getenv('MONGODB_PASSWORD')
                database = self.config.get('database') or os.getenv('MONGODB_DATABASE', 'scout')
                
                # Build URI if not provided
                if user and password:
                    uri = f"mongodb://{user}:{password}@{host}:{port}/{database}"
                else:
                    uri = f"mongodb://{host}:{port}/{database}"
                
                self.config.setdefault('uri', uri)
                self.config.setdefault('database', database)
            else:
                # Parse database name from URI if not specified
                if 'database' not in self.config:
                    # Extract database name from URI
                    parts = uri.split('/')
                    if len(parts) > 3:
                        database = parts[3].split('?')[0]
                        self.config.setdefault('database', database)
                    else:
                        self.config.setdefault('database', 'scout')
        else:
            raise ValueError(f"Unsupported database type: {self.config['type']}. Supported types: sqlite, mysql, postgresql, mongodb")
        
        # Optional timeout
        self.config.setdefault('timeout', int(os.getenv('DATABASE_TIMEOUT', '30')))
    
    def initialize(self) -> None:
        """Initialize the database storage provider."""
        try:
            # Connection will be created when needed
            self.connection = None
            
            # Create table/collection if auto_create is enabled
            if self.config['auto_create']:
                asyncio.create_task(self._ensure_storage_exists())
            
            logger.info(f"Initialized database storage provider for {self.config['type']}")
        except Exception as e:
            logger.error(f"Error initializing database storage provider: {str(e)}")
            raise
    
    async def _get_connection(self):
        """Get or create a database connection."""
        if self.connection is None or (hasattr(self.connection, 'closed') and self.connection.closed):
            db_type = self.config['type']
            
            if db_type == 'sqlite':
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.config['path']), exist_ok=True)
                
                self.connection = await aiosqlite.connect(
                    self.config['path'],
                    timeout=self.config['timeout']
                )
                # Enable foreign keys
                await self.connection.execute("PRAGMA foreign_keys = ON")
                # Get results as dictionaries
                self.connection.row_factory = aiosqlite.Row
                
            elif db_type == 'mysql':
                self.connection = await aiomysql.connect(
                    host=self.config['host'],
                    port=self.config['port'],
                    user=self.config['user'],
                    password=self.config['password'],
                    db=self.config['database'],
                    connect_timeout=self.config['timeout'],
                    autocommit=True
                )
                
            elif db_type == 'postgresql':
                self.connection = await asyncpg.connect(
                    host=self.config['host'],
                    port=self.config['port'],
                    user=self.config['user'],
                    password=self.config['password'],
                    database=self.config['database'],
                    timeout=self.config['timeout']
                )
                
            elif db_type == 'mongodb':
                if not self.connection:
                    client = motor.motor_asyncio.AsyncIOMotorClient(
                        self.config['uri'],
                        serverSelectionTimeoutMS=self.config['timeout'] * 1000
                    )
                    self.connection = client[self.config['database']]
        
        return self.connection
    
    async def _ensure_storage_exists(self) -> None:
        """Ensure that the storage table or collection exists."""
        connection = await self._get_connection()
        db_type = self.config['type']
        table_name = self.config['table_name']
        
        try:
            if db_type == 'sqlite':
                # Create table for SQLite
                await connection.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    data_type TEXT NOT NULL,
                    content_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
                """)
                await connection.commit()
                
            elif db_type == 'mysql':
                # Create table for MySQL
                async with connection.cursor() as cursor:
                    await cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        `key` VARCHAR(255) PRIMARY KEY,
                        `value` LONGBLOB NOT NULL,
                        `data_type` VARCHAR(50) NOT NULL,
                        `content_type` VARCHAR(100),
                        `created_at` DATETIME NOT NULL,
                        `updated_at` DATETIME NOT NULL,
                        `metadata` JSON
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """)
                
            elif db_type == 'postgresql':
                # Create table for PostgreSQL
                await connection.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    key TEXT PRIMARY KEY,
                    value BYTEA NOT NULL,
                    data_type TEXT NOT NULL,
                    content_type TEXT,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    metadata JSONB
                )
                """)
                
            elif db_type == 'mongodb':
                # For MongoDB, collections are created automatically when used
                # But we can create indexes
                collection = connection[table_name]
                await collection.create_index('key', unique=True)
                
            logger.info(f"Ensured {db_type} storage exists: {table_name}")
        
        except Exception as e:
            logger.error(f"Error ensuring storage exists: {str(e)}")
            raise
    
    async def store(self, key: str, data: Any) -> Dict[str, Any]:
        """
        Store data in the database.
        
        Args:
            key: Storage key
            data: Data to store
            
        Returns:
            Storage status
        """
        try:
            connection = await self._get_connection()
            db_type = self.config['type']
            table_name = self.config['table_name']
            
            # Get current timestamp
            timestamp = datetime.now().isoformat()
            
            # Determine the data type and format
            content_type = None
            metadata = {}
            
            if isinstance(data, str):
                # Store as text
                value = data.encode('utf-8')
                data_type = 'text'
                content_type = 'text/plain; charset=utf-8'
                
            elif isinstance(data, bytes):
                # Store as binary
                value = data
                data_type = 'binary'
                
                # Get extension if key has one
                if '.' in key:
                    ext = key.split('.')[-1].lower()
                    if ext in ['png', 'jpg', 'jpeg', 'gif']:
                        content_type = f'image/{ext}'
                    elif ext in ['pdf']:
                        content_type = 'application/pdf'
                    elif ext in ['html', 'htm']:
                        content_type = 'text/html'
                    # Add more as needed
                
            elif isinstance(data, (dict, list)) or hasattr(data, '__dict__'):
                # Store as JSON
                try:
                    if hasattr(data, '__dict__'):
                        json_data = json.dumps(data.__dict__)
                    else:
                        json_data = json.dumps(data)
                    
                    value = json_data.encode('utf-8')
                    data_type = 'json'
                    content_type = 'application/json; charset=utf-8'
                except (TypeError, OverflowError):
                    # If JSON serialization fails, fallback to pickle
                    value = pickle.dumps(data)
                    data_type = 'pickle'
                    content_type = 'application/python-pickle'
            
            else:
                # Store as pickle
                value = pickle.dumps(data)
                data_type = 'pickle'
                content_type = 'application/python-pickle'
            
            # Store or update the data
            if db_type == 'sqlite':
                # Check if key exists
                cursor = await connection.execute(f"SELECT key FROM {table_name} WHERE key = ?", (key,))
                existing = await cursor.fetchone()
                
                if existing:
                    # Update
                    await connection.execute(
                        f"UPDATE {table_name} SET value = ?, data_type = ?, content_type = ?, updated_at = ?, metadata = ? WHERE key = ?",
                        (value, data_type, content_type, timestamp, json.dumps(metadata), key)
                    )
                else:
                    # Insert
                    await connection.execute(
                        f"INSERT INTO {table_name} (key, value, data_type, content_type, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (key, value, data_type, content_type, timestamp, timestamp, json.dumps(metadata))
                    )
                
                await connection.commit()
                
            elif db_type == 'mysql':
                async with connection.cursor() as cursor:
                    # Check if key exists
                    await cursor.execute(f"SELECT `key` FROM {table_name} WHERE `key` = %s", (key,))
                    existing = await cursor.fetchone()
                    
                    if existing:
                        # Update
                        await cursor.execute(
                            f"UPDATE {table_name} SET `value` = %s, `data_type` = %s, `content_type` = %s, `updated_at` = %s, `metadata` = %s WHERE `key` = %s",
                            (value, data_type, content_type, timestamp, json.dumps(metadata), key)
                        )
                    else:
                        # Insert
                        await cursor.execute(
                            f"INSERT INTO {table_name} (`key`, `value`, `data_type`, `content_type`, `created_at`, `updated_at`, `metadata`) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                            (key, value, data_type, content_type, timestamp, timestamp, json.dumps(metadata))
                        )
                
            elif db_type == 'postgresql':
                # Check if key exists
                existing = await connection.fetchrow(f"SELECT key FROM {table_name} WHERE key = $1", key)
                
                if existing:
                    # Update
                    await connection.execute(
                        f"UPDATE {table_name} SET value = $1, data_type = $2, content_type = $3, updated_at = $4, metadata = $5 WHERE key = $6",
                        value, data_type, content_type, timestamp, json.dumps(metadata), key
                    )
                else:
                    # Insert
                    await connection.execute(
                        f"INSERT INTO {table_name} (key, value, data_type, content_type, created_at, updated_at, metadata) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                        key, value, data_type, content_type, timestamp, timestamp, json.dumps(metadata)
                    )
                
            elif db_type == 'mongodb':
                collection = connection[table_name]
                
                # For MongoDB, store binary data as base64 string to avoid BSON size limitations
                if isinstance(value, bytes):
                    value_to_store = base64.b64encode(value).decode('utf-8')
                    is_base64 = True
                else:
                    value_to_store = value.decode('utf-8') if isinstance(value, bytes) else value
                    is_base64 = False
                
                # Create document
                document = {
                    'key': key,
                    'value': value_to_store,
                    'is_base64': is_base64,
                    'data_type': data_type,
                    'content_type': content_type,
                    'updated_at': datetime.now(),
                    'metadata': metadata
                }
                
                # Update or insert
                await collection.update_one(
                    {'key': key},
                    {'$set': document, '$setOnInsert': {'created_at': datetime.now()}},
                    upsert=True
                )
            
            return {
                'success': True,
                'key': key,
                'size': len(value),
                'data_type': data_type,
                'content_type': content_type,
                'timestamp': timestamp
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
        Retrieve data from the database.
        
        Args:
            key: Storage key
            
        Returns:
            Retrieved data
        
        Raises:
            FileNotFoundError: If the key does not exist
        """
        try:
            connection = await self._get_connection()
            db_type = self.config['type']
            table_name = self.config['table_name']
            
            if db_type == 'sqlite':
                # Retrieve data
                cursor = await connection.execute(
                    f"SELECT value, data_type, content_type FROM {table_name} WHERE key = ?",
                    (key,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    raise FileNotFoundError(f"Key not found: {key}")
                
                value = row[0]
                data_type = row[1]
                content_type = row[2]
                
            elif db_type == 'mysql':
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        f"SELECT `value`, `data_type`, `content_type` FROM {table_name} WHERE `key` = %s",
                        (key,)
                    )
                    row = await cursor.fetchone()
                    
                    if not row:
                        raise FileNotFoundError(f"Key not found: {key}")
                    
                    value = row[0]
                    data_type = row[1]
                    content_type = row[2]
                
            elif db_type == 'postgresql':
                # Retrieve data
                row = await connection.fetchrow(
                    f"SELECT value, data_type, content_type FROM {table_name} WHERE key = $1",
                    key
                )
                
                if not row:
                    raise FileNotFoundError(f"Key not found: {key}")
                
                value = row['value']
                data_type = row['data_type']
                content_type = row['content_type']
                
            elif db_type == 'mongodb':
                collection = connection[table_name]
                document = await collection.find_one({'key': key})
                
                if not document:
                    raise FileNotFoundError(f"Key not found: {key}")
                
                value = document['value']
                data_type = document['data_type']
                content_type = document['content_type']
                is_base64 = document.get('is_base64', False)
                
                # Handle base64-encoded data
                if is_base64:
                    value = base64.b64decode(value)
                else:
                    # Convert string to bytes if needed
                    if isinstance(value, str) and data_type not in ['text', 'json']:
                        value = value.encode('utf-8')
            
            # Convert the data based on its type
            if data_type == 'text':
                if isinstance(value, bytes):
                    return value.decode('utf-8')
                return value
                
            elif data_type == 'binary':
                return value
                
            elif data_type == 'json':
                if isinstance(value, bytes):
                    json_str = value.decode('utf-8')
                else:
                    json_str = value
                return json.loads(json_str)
                
            elif data_type == 'pickle':
                return pickle.loads(value)
                
            else:
                # Unknown type, return as is
                return value
        
        except FileNotFoundError:
            logger.error(f"Key not found: {key}")
            raise
        
        except Exception as e:
            logger.error(f"Error retrieving data for key '{key}': {str(e)}")
            raise
    
    async def delete(self, key: str) -> Dict[str, Any]:
        """
        Delete data from the database.
        
        Args:
            key: Storage key
            
        Returns:
            Deletion status
        """
        try:
            connection = await self._get_connection()
            db_type = self.config['type']
            table_name = self.config['table_name']
            
            # Get metadata before deletion
            try:
                metadata = await self.get_metadata(key)
            except:
                metadata = {}
            
            if db_type == 'sqlite':
                # Delete data
                cursor = await connection.execute(f"DELETE FROM {table_name} WHERE key = ?", (key,))
                await connection.commit()
                
                if cursor.rowcount == 0:
                    return {
                        'success': False,
                        'key': key,
                        'error': f"Key not found: {key}"
                    }
                
            elif db_type == 'mysql':
                async with connection.cursor() as cursor:
                    await cursor.execute(f"DELETE FROM {table_name} WHERE `key` = %s", (key,))
                    
                    if cursor.rowcount == 0:
                        return {
                            'success': False,
                            'key': key,
                            'error': f"Key not found: {key}"
                        }
                
            elif db_type == 'postgresql':
                # Delete data
                result = await connection.execute(f"DELETE FROM {table_name} WHERE key = $1", key)
                
                if result == "DELETE 0":
                    return {
                        'success': False,
                        'key': key,
                        'error': f"Key not found: {key}"
                    }
                
            elif db_type == 'mongodb':
                collection = connection[table_name]
                result = await collection.delete_one({'key': key})
                
                if result.deleted_count == 0:
                    return {
                        'success': False,
                        'key': key,
                        'error': f"Key not found: {key}"
                    }
            
            return {
                'success': True,
                'key': key,
                'size': metadata.get('size'),
                'timestamp': metadata.get('updated_at')
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
            connection = await self._get_connection()
            db_type = self.config['type']
            table_name = self.config['table_name']
            
            if db_type == 'sqlite':
                # Build query
                query = f"SELECT key FROM {table_name}"
                params = []
                
                if prefix:
                    query += " WHERE key LIKE ?"
                    params.append(f"{prefix}%")
                
                query += " ORDER BY key"
                
                # Execute query
                cursor = await connection.execute(query, params)
                rows = await cursor.fetchall()
                
                return [row[0] for row in rows]
                
            elif db_type == 'mysql':
                async with connection.cursor() as cursor:
                    # Build query
                    query = f"SELECT `key` FROM {table_name}"
                    params = []
                    
                    if prefix:
                        query += " WHERE `key` LIKE %s"
                        params.append(f"{prefix}%")
                    
                    query += " ORDER BY `key`"
                    
                    # Execute query
                    await cursor.execute(query, params)
                    rows = await cursor.fetchall()
                    
                    return [row[0] for row in rows]
                
            elif db_type == 'postgresql':
                # Build query
                query = f"SELECT key FROM {table_name}"
                params = []
                
                if prefix:
                    query += " WHERE key LIKE $1"
                    params.append(f"{prefix}%")
                
                query += " ORDER BY key"
                
                # Execute query
                rows = await connection.fetch(query, *params)
                
                return [row['key'] for row in rows]
                
            elif db_type == 'mongodb':
                collection = connection[table_name]
                
                # Build query
                query = {}
                if prefix:
                    query['key'] = {'$regex': f'^{prefix}'}
                
                # Execute query
                cursor = collection.find(query, {'key': 1, '_id': 0}).sort('key', 1)
                documents = await cursor.to_list(length=None)
                
                return [doc['key'] for doc in documents]
            
            return []
        
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
            connection = await self._get_connection()
            db_type = self.config['type']
            table_name = self.config['table_name']
            
            if db_type == 'sqlite':
                # Retrieve metadata
                cursor = await connection.execute(
                    f"SELECT key, data_type, content_type, length(value) as size, created_at, updated_at, metadata FROM {table_name} WHERE key = ?",
                    (key,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    raise FileNotFoundError(f"Key not found: {key}")
                
                metadata = json.loads(row[6]) if row[6] else {}
                
                return {
                    'success': True,
                    'key': row[0],
                    'data_type': row[1],
                    'content_type': row[2],
                    'size': row[3],
                    'created_at': row[4],
                    'updated_at': row[5],
                    'metadata': metadata
                }
                
            elif db_type == 'mysql':
                async with connection.cursor() as cursor:
                    await cursor.execute(
                        f"SELECT `key`, `data_type`, `content_type`, length(`value`) as size, `created_at`, `updated_at`, `metadata` FROM {table_name} WHERE `key` = %s",
                        (key,)
                    )
                    row = await cursor.fetchone()
                    
                    if not row:
                        raise FileNotFoundError(f"Key not found: {key}")
                    
                    metadata = json.loads(row[6]) if row[6] else {}
                    
                    return {
                        'success': True,
                        'key': row[0],
                        'data_type': row[1],
                        'content_type': row[2],
                        'size': row[3],
                        'created_at': row[4].isoformat() if hasattr(row[4], 'isoformat') else row[4],
                        'updated_at': row[5].isoformat() if hasattr(row[5], 'isoformat') else row[5],
                        'metadata': metadata
                    }
                
            elif db_type == 'postgresql':
                # Retrieve metadata
                row = await connection.fetchrow(
                    f"SELECT key, data_type, content_type, octet_length(value) as size, created_at, updated_at, metadata FROM {table_name} WHERE key = $1",
                    key
                )
                
                if not row:
                    raise FileNotFoundError(f"Key not found: {key}")
                
                metadata = row['metadata'] or {}
                
                return {
                    'success': True,
                    'key': row['key'],
                    'data_type': row['data_type'],
                    'content_type': row['content_type'],
                    'size': row['size'],
                    'created_at': row['created_at'].isoformat() if hasattr(row['created_at'], 'isoformat') else row['created_at'],
                    'updated_at': row['updated_at'].isoformat() if hasattr(row['updated_at'], 'isoformat') else row['updated_at'],
                    'metadata': metadata
                }
                
            elif db_type == 'mongodb':
                collection = connection[table_name]
                document = await collection.find_one({'key': key})
                
                if not document:
                    raise FileNotFoundError(f"Key not found: {key}")
                
                # Calculate size based on value
                value = document['value']
                is_base64 = document.get('is_base64', False)
                
                if is_base64:
                    # For base64-encoded data, the original size is approximately 3/4 of the encoded length
                    size = len(value) * 3 // 4
                else:
                    size = len(value)
                
                return {
                    'success': True,
                    'key': document['key'],
                    'data_type': document['data_type'],
                    'content_type': document.get('content_type'),
                    'size': size,
                    'created_at': document.get('created_at', document.get('updated_at')).isoformat() if hasattr(document.get('created_at'), 'isoformat') else document.get('created_at'),
                    'updated_at': document['updated_at'].isoformat() if hasattr(document['updated_at'], 'isoformat') else document['updated_at'],
                    'metadata': document.get('metadata', {})
                }
        
        except FileNotFoundError:
            logger.error(f"Key not found: {key}")
            raise
        
        except Exception as e:
            logger.error(f"Error getting metadata for key '{key}': {str(e)}")
            raise
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the database storage integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the database is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                try:
                    connection = await self._get_connection()
                    db_type = self.config['type']
                    table_name = self.config['table_name']
                    
                    # Check if the table exists
                    if db_type == 'sqlite':
                        cursor = await connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                            (table_name,)
                        )
                        row = await cursor.fetchone()
                        table_exists = row is not None
                        
                    elif db_type == 'mysql':
                        async with connection.cursor() as cursor:
                            await cursor.execute(
                                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                                (self.config['database'], table_name)
                            )
                            row = await cursor.fetchone()
                            table_exists = row is not None
                        
                    elif db_type == 'postgresql':
                        row = await connection.fetchrow(
                            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' AND tablename = $1",
                            table_name
                        )
                        table_exists = row is not None
                        
                    elif db_type == 'mongodb':
                        collection_names = await connection.list_collection_names()
                        table_exists = table_name in collection_names
                    
                    if not table_exists:
                        # Try to create the table/collection
                        if self.config['auto_create']:
                            await self._ensure_storage_exists()
                            table_exists = True
                        else:
                            return False, f"Storage table/collection '{table_name}' does not exist"
                    
                    # Get item count
                    count = 0
                    if db_type == 'sqlite':
                        cursor = await connection.execute(f"SELECT COUNT(*) FROM {table_name}")
                        row = await cursor.fetchone()
                        count = row[0]
                        
                    elif db_type == 'mysql':
                        async with connection.cursor() as cursor:
                            await cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                            row = await cursor.fetchone()
                            count = row[0]
                        
                    elif db_type == 'postgresql':
                        row = await connection.fetchrow(f"SELECT COUNT(*) FROM {table_name}")
                        count = row[0]
                        
                    elif db_type == 'mongodb':
                        collection = connection[table_name]
                        count = await collection.count_documents({})
                    
                    return True, {"table_exists": table_exists, "item_count": count}
                
                except Exception as e:
                    return False, str(e)
            
            is_healthy, details = loop.run_until_complete(check())
            
            if is_healthy:
                if isinstance(details, dict):
                    return {
                        "status": "healthy",
                        "provider": "database_storage",
                        "type": self.config['type'],
                        "table": self.config['table_name'],
                        "details": details
                    }
                else:
                    return {
                        "status": "healthy",
                        "provider": "database_storage",
                        "type": self.config['type'],
                        "table": self.config['table_name']
                    }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "database_storage",
                    "type": self.config['type'],
                    "table": self.config['table_name'],
                    "error": details
                }
        
        except Exception as e:
            logger.error(f"Database storage health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "database_storage",
                "type": self.config['type'],
                "error": str(e)
            }