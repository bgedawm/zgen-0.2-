"""
Database Provider
-------------
Provides integration with databases for querying and storing data.
"""

import os
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Union

import aiosqlite
import aiomysql
import asyncpg
import motor.motor_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from ..base import DataProvider

# Setup logger
logger = logging.getLogger(__name__)


class DatabaseProvider(DataProvider):
    """Database provider for querying and storing data in various databases."""
    
    def _validate_config(self) -> None:
        """
        Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Check for required configuration
        db_type = self.config.get('type') or os.getenv('DATABASE_TYPE', 'sqlite')
        self.config.setdefault('type', db_type.lower())
        
        # Connection settings based on DB type
        if self.config['type'] == 'sqlite':
            db_path = self.config.get('path') or os.getenv('DATABASE_PATH', './data/database.sqlite')
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
        """Initialize the database connection."""
        try:
            # Connection will be created when needed
            self.connection = None
            self.engine = None
            
            logger.info(f"Initialized database provider for {self.config['type']}")
        except Exception as e:
            logger.error(f"Error initializing database provider: {str(e)}")
            raise
    
    async def _get_connection(self):
        """Get or create a database connection."""
        if self.connection is None or (hasattr(self.connection, 'closed') and self.connection.closed):
            db_type = self.config['type']
            
            if db_type == 'sqlite':
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
    
    async def _get_sqlalchemy_engine(self):
        """Get or create a SQLAlchemy engine."""
        if self.engine is None:
            db_type = self.config['type']
            
            if db_type == 'sqlite':
                conn_str = f"sqlite+aiosqlite:///{self.config['path']}"
                self.engine = create_async_engine(conn_str)
                
            elif db_type == 'mysql':
                conn_str = f"mysql+aiomysql://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
                self.engine = create_async_engine(conn_str)
                
            elif db_type == 'postgresql':
                conn_str = f"postgresql+asyncpg://{self.config['user']}:{self.config['password']}@{self.config['host']}:{self.config['port']}/{self.config['database']}"
                self.engine = create_async_engine(conn_str)
                
            else:
                raise ValueError(f"SQLAlchemy not supported for {db_type}")
            
            self.async_session = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
        
        return self.engine
    
    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a database query.
        
        Args:
            query: SQL query or MongoDB query definition
            **kwargs: Additional query parameters
            
        Returns:
            Query results
        """
        try:
            db_type = self.config['type']
            
            if db_type in ['sqlite', 'mysql', 'postgresql']:
                return await self._sql_query(query, **kwargs)
            elif db_type == 'mongodb':
                return await self._mongodb_query(query, **kwargs)
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
        
        except Exception as e:
            logger.error(f"Error executing database query: {str(e)}")
            
            return {
                'success': False,
                'query': query,
                'error': str(e)
            }
    
    async def _sql_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute an SQL query."""
        connection = await self._get_connection()
        db_type = self.config['type']
        
        # Extract parameters
        params = kwargs.get('params', {})
        
        # Execute the query
        if db_type == 'sqlite':
            # For SQLite
            try:
                cursor = await connection.execute(query, params)
                
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    # For SELECT queries, return results
                    rows = await cursor.fetchall()
                    columns = [col[0] for col in cursor.description]
                    
                    # Convert rows to dictionaries
                    results = []
                    for row in rows:
                        result = {}
                        for i, column in enumerate(columns):
                            result[column] = row[i]
                        results.append(result)
                    
                    return {
                        'success': True,
                        'results': results,
                        'count': len(results),
                        'columns': columns
                    }
                else:
                    # For non-SELECT queries, return affected rows
                    await connection.commit()
                    return {
                        'success': True,
                        'affected_rows': cursor.rowcount,
                        'lastrowid': cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
                    }
            finally:
                if cursor:
                    await cursor.close()
        
        elif db_type == 'mysql':
            # For MySQL
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                
                if query.strip().upper().startswith(('SELECT', 'WITH')):
                    # For SELECT queries, return results
                    rows = await cursor.fetchall()
                    return {
                        'success': True,
                        'results': rows,
                        'count': len(rows),
                        'columns': [col[0] for col in cursor.description]
                    }
                else:
                    # For non-SELECT queries, return affected rows
                    return {
                        'success': True,
                        'affected_rows': cursor.rowcount,
                        'lastrowid': cursor.lastrowid
                    }
        
        elif db_type == 'postgresql':
            # For PostgreSQL
            if query.strip().upper().startswith(('SELECT', 'WITH')):
                # For SELECT queries, return results
                rows = await connection.fetch(query, *params.values() if isinstance(params, dict) else params)
                
                # Convert rows to dictionaries
                results = [dict(row) for row in rows]
                
                return {
                    'success': True,
                    'results': results,
                    'count': len(results),
                    'columns': results[0].keys() if results else []
                }
            else:
                # For non-SELECT queries, return affected rows
                result = await connection.execute(query, *params.values() if isinstance(params, dict) else params)
                return {
                    'success': True,
                    'result': result
                }
    
    async def _mongodb_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute a MongoDB query."""
        connection = await self._get_connection()
        
        # Parse the query
        try:
            if isinstance(query, str):
                # Try to parse as JSON
                query_obj = json.loads(query)
            else:
                query_obj = query
        except json.JSONDecodeError:
            raise ValueError("MongoDB query must be a valid JSON string or object")
        
        # Extract collection name
        collection_name = kwargs.get('collection')
        if not collection_name:
            raise ValueError("Collection name must be provided for MongoDB queries")
        
        collection = connection[collection_name]
        
        # Determine operation type
        operation = kwargs.get('operation', 'find').lower()
        
        if operation == 'find':
            # For find queries
            limit = kwargs.get('limit', 0)
            skip = kwargs.get('skip', 0)
            sort = kwargs.get('sort')
            projection = kwargs.get('projection')
            
            cursor = collection.find(query_obj, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            
            if skip:
                cursor = cursor.skip(skip)
            
            if limit:
                cursor = cursor.limit(limit)
            
            # Get results
            results = await cursor.to_list(length=limit if limit else None)
            
            # Convert ObjectId to string for JSON serialization
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return {
                'success': True,
                'results': results,
                'count': len(results),
                'collection': collection_name
            }
            
        elif operation == 'insert_one':
            result = await collection.insert_one(query_obj)
            return {
                'success': True,
                'operation': 'insert_one',
                'inserted_id': str(result.inserted_id),
                'collection': collection_name
            }
            
        elif operation == 'insert_many':
            documents = kwargs.get('documents', [])
            if not documents:
                raise ValueError("Documents must be provided for insert_many operation")
            
            result = await collection.insert_many(documents)
            return {
                'success': True,
                'operation': 'insert_many',
                'inserted_ids': [str(id) for id in result.inserted_ids],
                'count': len(result.inserted_ids),
                'collection': collection_name
            }
            
        elif operation == 'update_one':
            update = kwargs.get('update')
            if not update:
                raise ValueError("Update document must be provided for update_one operation")
            
            result = await collection.update_one(query_obj, update)
            return {
                'success': True,
                'operation': 'update_one',
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'upserted_id': str(result.upserted_id) if result.upserted_id else None,
                'collection': collection_name
            }
            
        elif operation == 'update_many':
            update = kwargs.get('update')
            if not update:
                raise ValueError("Update document must be provided for update_many operation")
            
            result = await collection.update_many(query_obj, update)
            return {
                'success': True,
                'operation': 'update_many',
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'upserted_id': str(result.upserted_id) if result.upserted_id else None,
                'collection': collection_name
            }
            
        elif operation == 'delete_one':
            result = await collection.delete_one(query_obj)
            return {
                'success': True,
                'operation': 'delete_one',
                'deleted_count': result.deleted_count,
                'collection': collection_name
            }
            
        elif operation == 'delete_many':
            result = await collection.delete_many(query_obj)
            return {
                'success': True,
                'operation': 'delete_many',
                'deleted_count': result.deleted_count,
                'collection': collection_name
            }
            
        elif operation == 'count':
            count = await collection.count_documents(query_obj)
            return {
                'success': True,
                'operation': 'count',
                'count': count,
                'collection': collection_name
            }
            
        elif operation == 'aggregate':
            pipeline = kwargs.get('pipeline')
            if not pipeline:
                raise ValueError("Aggregation pipeline must be provided for aggregate operation")
            
            results = await collection.aggregate(pipeline).to_list(length=None)
            
            # Convert ObjectId to string for JSON serialization
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return {
                'success': True,
                'operation': 'aggregate',
                'results': results,
                'count': len(results),
                'collection': collection_name
            }
            
        else:
            raise ValueError(f"Unsupported MongoDB operation: {operation}")
    
    async def fetch(self, resource: str, **kwargs) -> Dict[str, Any]:
        """
        Fetch a specific database resource.
        
        Args:
            resource: Resource identifier (table, collection, schema, etc.)
            **kwargs: Additional fetch parameters
            
        Returns:
            Resource data
        """
        try:
            db_type = self.config['type']
            
            if db_type in ['sqlite', 'mysql', 'postgresql']:
                return await self._fetch_sql_resource(resource, **kwargs)
            elif db_type == 'mongodb':
                return await self._fetch_mongodb_resource(resource, **kwargs)
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
        
        except Exception as e:
            logger.error(f"Error fetching database resource: {str(e)}")
            
            return {
                'success': False,
                'resource': resource,
                'error': str(e)
            }
    
    async def _fetch_sql_resource(self, resource: str, **kwargs) -> Dict[str, Any]:
        """Fetch an SQL database resource."""
        connection = await self._get_connection()
        db_type = self.config['type']
        
        resource_type = kwargs.get('type', 'table').lower()
        
        if resource_type == 'table':
            # Get table info
            if db_type == 'sqlite':
                # Get table schema
                cursor = await connection.execute(f"PRAGMA table_info({resource})")
                columns = await cursor.fetchall()
                
                # Get table data if requested
                data = []
                if kwargs.get('include_data', False):
                    limit = kwargs.get('limit', 10)
                    offset = kwargs.get('offset', 0)
                    order_by = kwargs.get('order_by')
                    
                    query = f"SELECT * FROM {resource}"
                    if order_by:
                        query += f" ORDER BY {order_by}"
                    query += f" LIMIT {limit} OFFSET {offset}"
                    
                    cursor = await connection.execute(query)
                    rows = await cursor.fetchall()
                    
                    # Convert rows to dictionaries
                    column_names = [col[1] for col in columns]
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            row_dict[column_names[i]] = value
                        data.append(row_dict)
                
                return {
                    'success': True,
                    'resource': resource,
                    'type': 'table',
                    'columns': [{'name': col[1], 'type': col[2], 'notnull': col[3], 'pk': col[5]} for col in columns],
                    'data': data
                }
                
            elif db_type == 'mysql':
                async with connection.cursor() as cursor:
                    await cursor.execute(f"DESCRIBE {resource}")
                    columns = await cursor.fetchall()
                    
                    # Get table data if requested
                    data = []
                    if kwargs.get('include_data', False):
                        limit = kwargs.get('limit', 10)
                        offset = kwargs.get('offset', 0)
                        order_by = kwargs.get('order_by')
                        
                        query = f"SELECT * FROM {resource}"
                        if order_by:
                            query += f" ORDER BY {order_by}"
                        query += f" LIMIT {limit} OFFSET {offset}"
                        
                        await cursor.execute(query)
                        rows = await cursor.fetchall()
                        
                        # Convert rows to dictionaries
                        for row in rows:
                            data.append(dict(zip([col[0] for col in columns], row)))
                    
                    return {
                        'success': True,
                        'resource': resource,
                        'type': 'table',
                        'columns': columns,
                        'data': data
                    }
                    
            elif db_type == 'postgresql':
                # Get table schema
                columns = await connection.fetch(
                    """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = $1
                    ORDER BY ordinal_position
                    """,
                    resource
                )
                
                # Get table data if requested
                data = []
                if kwargs.get('include_data', False):
                    limit = kwargs.get('limit', 10)
                    offset = kwargs.get('offset', 0)
                    order_by = kwargs.get('order_by')
                    
                    query = f"SELECT * FROM {resource}"
                    if order_by:
                        query += f" ORDER BY {order_by}"
                    query += f" LIMIT {limit} OFFSET {offset}"
                    
                    rows = await connection.fetch(query)
                    data = [dict(row) for row in rows]
                
                return {
                    'success': True,
                    'resource': resource,
                    'type': 'table',
                    'columns': [dict(col) for col in columns],
                    'data': data
                }
        
        elif resource_type == 'schema':
            # Get database schema
            if db_type == 'sqlite':
                # Get list of tables
                cursor = await connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = await cursor.fetchall()
                
                schema_info = []
                for table in tables:
                    table_name = table[0]
                    cursor = await connection.execute(f"PRAGMA table_info({table_name})")
                    columns = await cursor.fetchall()
                    
                    schema_info.append({
                        'table': table_name,
                        'columns': [{'name': col[1], 'type': col[2], 'notnull': col[3], 'pk': col[5]} for col in columns]
                    })
                
                return {
                    'success': True,
                    'resource': 'schema',
                    'type': 'schema',
                    'tables': schema_info
                }
                
            elif db_type == 'mysql':
                async with connection.cursor() as cursor:
                    await cursor.execute("SHOW TABLES")
                    tables = await cursor.fetchall()
                    
                    schema_info = []
                    for table in tables:
                        table_name = table[0]
                        await cursor.execute(f"DESCRIBE {table_name}")
                        columns = await cursor.fetchall()
                        
                        schema_info.append({
                            'table': table_name,
                            'columns': columns
                        })
                    
                    return {
                        'success': True,
                        'resource': 'schema',
                        'type': 'schema',
                        'tables': schema_info
                    }
                    
            elif db_type == 'postgresql':
                # Get list of tables
                tables = await connection.fetch(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                    """
                )
                
                schema_info = []
                for table in tables:
                    table_name = table['table_name']
                    columns = await connection.fetch(
                        """
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_name = $1
                        ORDER BY ordinal_position
                        """,
                        table_name
                    )
                    
                    schema_info.append({
                        'table': table_name,
                        'columns': [dict(col) for col in columns]
                    })
                
                return {
                    'success': True,
                    'resource': 'schema',
                    'type': 'schema',
                    'tables': schema_info
                }
        
        elif resource_type == 'query':
            # Execute a predefined query
            # This allows fetching complex predefined queries by name
            predefined_queries = kwargs.get('queries', {})
            if resource not in predefined_queries:
                raise ValueError(f"Predefined query '{resource}' not found")
            
            query = predefined_queries[resource]
            params = kwargs.get('params', {})
            
            return await self._sql_query(query, params=params)
        
        else:
            raise ValueError(f"Unsupported SQL resource type: {resource_type}")
    
    async def _fetch_mongodb_resource(self, resource: str, **kwargs) -> Dict[str, Any]:
        """Fetch a MongoDB resource."""
        connection = await self._get_connection()
        
        resource_type = kwargs.get('type', 'collection').lower()
        
        if resource_type == 'collection':
            # Get collection info
            if resource == 'list':
                # List all collections
                collections = await connection.list_collection_names()
                return {
                    'success': True,
                    'resource': 'collections',
                    'type': 'list',
                    'collections': collections
                }
            else:
                # Get collection info
                collection = connection[resource]
                
                # Get collection data if requested
                data = []
                if kwargs.get('include_data', False):
                    limit = kwargs.get('limit', 10)
                    skip = kwargs.get('skip', 0)
                    sort = kwargs.get('sort')
                    query = kwargs.get('query', {})
                    
                    cursor = collection.find(query)
                    
                    if sort:
                        cursor = cursor.sort(sort)
                    
                    cursor = cursor.skip(skip).limit(limit)
                    
                    data = await cursor.to_list(length=limit)
                    
                    # Convert ObjectId to string for JSON serialization
                    for doc in data:
                        if '_id' in doc:
                            doc['_id'] = str(doc['_id'])
                
                # Get count of documents
                count = await collection.count_documents({})
                
                return {
                    'success': True,
                    'resource': resource,
                    'type': 'collection',
                    'count': count,
                    'data': data
                }
        
        elif resource_type == 'database':
            # Get database info
            if resource == 'stats':
                # Get database stats
                stats = await connection.command('dbStats')
                return {
                    'success': True,
                    'resource': 'database',
                    'type': 'stats',
                    'stats': stats
                }
            elif resource == 'info':
                # Get database info
                collections = await connection.list_collection_names()
                
                collections_info = []
                for collection_name in collections:
                    collection = connection[collection_name]
                    count = await collection.count_documents({})
                    collections_info.append({
                        'name': collection_name,
                        'count': count
                    })
                
                return {
                    'success': True,
                    'resource': 'database',
                    'type': 'info',
                    'database': self.config['database'],
                    'collections': collections_info
                }
        
        else:
            raise ValueError(f"Unsupported MongoDB resource type: {resource_type}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the database integration.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Create a simple request to check if the database is accessible
            loop = asyncio.get_event_loop()
            
            async def check():
                try:
                    db_type = self.config['type']
                    connection = await self._get_connection()
                    
                    if db_type == 'sqlite':
                        cursor = await connection.execute("SELECT 1")
                        result = await cursor.fetchone()
                        return result[0] == 1, None
                    
                    elif db_type == 'mysql':
                        async with connection.cursor() as cursor:
                            await cursor.execute("SELECT 1")
                            result = await cursor.fetchone()
                            return result[0] == 1, None
                    
                    elif db_type == 'postgresql':
                        result = await connection.fetchval("SELECT 1")
                        return result == 1, None
                    
                    elif db_type == 'mongodb':
                        result = await connection.command('ping')
                        return result.get('ok') == 1, None
                    
                except Exception as e:
                    return False, str(e)
            
            is_healthy, error_message = loop.run_until_complete(check())
            
            if is_healthy:
                return {
                    "status": "healthy",
                    "provider": "database",
                    "type": self.config['type'],
                    "database": self.config.get('database', self.config.get('path')),
                    "message": "Database is accessible"
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "database",
                    "type": self.config['type'],
                    "error": error_message
                }
        
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            
            return {
                "status": "unhealthy",
                "provider": "database",
                "type": self.config['type'],
                "error": str(e)
            }