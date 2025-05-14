"""
Web Tools Module
-------------
This module provides web-related tools for the agent.
"""

import os
import re
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from utils.logger import get_logger


class WebTools:
    """Provides web-related tools for the agent."""
    
    def __init__(self):
        """Initialize the web tools."""
        self.logger = get_logger(__name__)
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get an aiohttp session.
        
        Returns:
            An aiohttp.ClientSession instance
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})
        return self.session
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Search the web using a search engine API.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            A dictionary with search results
        """
        # Check if we have an API key for SerpAPI
        serp_api_key = os.getenv("SERPAPI_API_KEY")
        
        if not serp_api_key:
            self.logger.warning("No SERPAPI_API_KEY found. Using a simplified search.")
            return await self._simple_search(query, num_results)
        
        try:
            # Use SerpAPI
            session = await self._get_session()
            
            params = {
                "api_key": serp_api_key,
                "q": query,
                "num": num_results,
                "engine": "google"
            }
            
            async with session.get("https://serpapi.com/search", params=params) as response:
                if response.status != 200:
                    self.logger.error(f"SerpAPI error: {response.status}")
                    return await self._simple_search(query, num_results)
                
                data = await response.json()
                
                # Extract organic results
                results = []
                for result in data.get("organic_results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "link": result.get("link", ""),
                        "snippet": result.get("snippet", "")
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": results
                }
        
        except Exception as e:
            self.logger.error(f"Error during search: {str(e)}")
            return await self._simple_search(query, num_results)
    
    async def _simple_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Simple search implementation without using an API.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            A dictionary with search results
        """
        try:
            session = await self._get_session()
            
            # Use a public search engine that doesn't block bots
            search_url = f"https://html.duckduckgo.com/html/?q={query}"
            
            async with session.get(search_url) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"Search failed with status {response.status}"
                    }
                
                html = await response.text()
                
                # Parse the results
                soup = BeautifulSoup(html, "html.parser")
                result_elements = soup.select(".result")
                
                results = []
                for i, result in enumerate(result_elements):
                    if i >= num_results:
                        break
                    
                    title_elem = result.select_one(".result__title")
                    link_elem = result.select_one(".result__url")
                    snippet_elem = result.select_one(".result__snippet")
                    
                    title = title_elem.text.strip() if title_elem else ""
                    link = link_elem.text.strip() if link_elem else ""
                    snippet = snippet_elem.text.strip() if snippet_elem else ""
                    
                    # Try to find the actual href
                    a_tag = title_elem.find("a") if title_elem else None
                    if a_tag and a_tag.has_attr("href"):
                        href = a_tag["href"]
                        if href.startswith("/"):
                            link = f"https://duckduckgo.com{href}"
                        else:
                            link = href
                    
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "results": results
                }
        
        except Exception as e:
            self.logger.error(f"Error during simple search: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def browse(self, url: str) -> Dict[str, Any]:
        """
        Browse a web page and extract its content.
        
        Args:
            url: The URL to browse
            
        Returns:
            A dictionary with the page content
        """
        try:
            session = await self._get_session()
            
            # Set a timeout for the request
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"Failed to load page: {response.status}"
                    }
                
                content_type = response.headers.get("Content-Type", "")
                
                # Handle non-HTML content
                if "text/html" not in content_type:
                    return {
                        "success": True,
                        "url": url,
                        "content_type": content_type,
                        "is_html": False,
                        "text": f"[Non-HTML content: {content_type}]",
                        "title": url
                    }
                
                html = await response.text()
                
                # Parse the HTML
                soup = BeautifulSoup(html, "html.parser")
                
                # Extract the title
                title = soup.title.text.strip() if soup.title else url
                
                # Extract readable content
                article_text = self._extract_article_text(soup)
                
                return {
                    "success": True,
                    "url": url,
                    "content_type": content_type,
                    "is_html": True,
                    "text": article_text,
                    "title": title,
                    "links": self._extract_links(soup, url)
                }
        
        except Exception as e:
            self.logger.error(f"Error browsing {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_article_text(self, soup: BeautifulSoup) -> str:
        """
        Extract the main article text from a web page.
        
        Args:
            soup: The BeautifulSoup object
            
        Returns:
            The extracted text
        """
        # Try to identify main content
        main_content = None
        
        # Common content identifiers
        content_ids = ["content", "main", "article", "post", "entry", "blog"]
        
        # Try to find main content by ID
        for content_id in content_ids:
            main_content = soup.find(id=re.compile(content_id, re.I))
            if main_content:
                break
        
        # Try to find main content by class
        if not main_content:
            for content_id in content_ids:
                main_content = soup.find(class_=re.compile(content_id, re.I))
                if main_content:
                    break
        
        # Try to find main content by tag
        if not main_content:
            main_content = soup.find("article")
        
        # If still no main content, use the body
        if not main_content:
            main_content = soup.body
        
        # If still nothing, just use the whole soup
        if not main_content:
            main_content = soup
        
        # Remove script, style, and iframe tags
        for tag in main_content.find_all(["script", "style", "iframe"]):
            tag.decompose()
        
        # Get the text
        text = ""
        for paragraph in main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
            text += paragraph.text.strip() + "\n\n"
        
        # If we didn't find any paragraphs, just get all the text
        if not text:
            text = main_content.get_text(separator="\n", strip=True)
        
        return text
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """
        Extract links from a web page.
        
        Args:
            soup: The BeautifulSoup object
            base_url: The base URL
            
        Returns:
            A list of links
        """
        links = []
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.text.strip()
            
            # Skip empty or javascript links
            if not href or href.startswith("javascript:"):
                continue
            
            # Make relative URLs absolute
            if href.startswith("/"):
                parsed_url = urlparse(base_url)
                href = f"{parsed_url.scheme}://{parsed_url.netloc}{href}"
            elif not href.startswith("http"):
                # Handle relative paths without leading slash
                if not base_url.endswith("/"):
                    base_url += "/"
                href = f"{base_url}{href}"
            
            links.append({
                "url": href,
                "text": text
            })
        
        return links
    
    async def download(self, url: str, path: str) -> Dict[str, Any]:
        """
        Download a file from the web.
        
        Args:
            url: The URL to download
            path: The path to save the file
            
        Returns:
            A dictionary with the result
        """
        file_path = Path(path)
        
        try:
            session = await self._get_session()
            
            # Set a timeout for the request
            timeout = aiohttp.ClientTimeout(total=60)
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download the file
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"Failed to download file: {response.status}"
                    }
                
                # Get content type
                content_type = response.headers.get("Content-Type", "")
                
                # Save the file
                with open(file_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                
                return {
                    "success": True,
                    "url": url,
                    "path": str(file_path),
                    "content_type": content_type,
                    "size": file_path.stat().st_size
                }
        
        except Exception as e:
            self.logger.error(f"Error downloading {url}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()


def get_web_tools() -> Dict[str, Any]:
    """
    Get the web tools.
    
    Returns:
        A dictionary of web tool functions
    """
    tools = WebTools()
    
    return {
        "search": tools.search,
        "browse": tools.browse,
        "download": tools.download
    }