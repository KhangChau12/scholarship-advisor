"""
Web Search Tool using SerpAPI for scholarship information
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from loguru import logger
import time

from ..config.settings import settings

class WebSearchTool:
    """Web search tool for finding scholarship information"""
    
    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.base_url = "https://serpapi.com/search"
        self.timeout = settings.SEARCH_TIMEOUT
        self.cache = {}
        self.cache_ttl = 1800  # 30 minutes for search results
        
    def _get_cache_key(self, query: str, **kwargs) -> str:
        """Generate cache key for search query"""
        import hashlib
        cache_content = f"{query}_{kwargs}"
        return hashlib.md5(cache_content.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - timestamp < self.cache_ttl
    
    async def search_scholarships(
        self,
        query: str,
        country: Optional[str] = None,
        field: Optional[str] = None,
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for scholarship information
        
        Args:
            query: Search query
            country: Target country for studies  
            field: Field of study
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        # Build enhanced query
        enhanced_query = f"{query} scholarship"
        
        if country:
            enhanced_query += f" {country}"
        if field:
            enhanced_query += f" {field}"
        
        enhanced_query += " 2024 2025 requirements application"
        
        # Check cache
        cache_key = self._get_cache_key(enhanced_query, num=num_results)
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if self._is_cache_valid(timestamp):
                logger.info(f"Using cached search results for: {query}")
                return result
        
        try:
            params = {
                "q": enhanced_query,
                "api_key": self.api_key,
                "engine": "google",
                "num": num_results,
                "hl": "vi",  # Vietnamese interface
                "gl": "vn",  # Vietnam location
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = self._parse_search_results(data)
                        
                        # Cache results
                        self.cache[cache_key] = (results, time.time())
                        
                        logger.info(f"Found {len(results)} scholarship search results")
                        return results
                    else:
                        logger.error(f"Search API error: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error searching scholarships: {str(e)}")
            return []
    
    def _parse_search_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse SerpAPI response into structured results"""
        results = []
        
        # Parse organic results
        organic_results = data.get("organic_results", [])
        
        for result in organic_results:
            parsed_result = {
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "source": self._extract_domain(result.get("link", "")),
                "relevance_score": self._calculate_relevance(result),
                "type": "scholarship_info"
            }
            results.append(parsed_result)
        
        # Parse knowledge panel if available
        knowledge_graph = data.get("knowledge_graph", {})
        if knowledge_graph:
            results.append({
                "title": knowledge_graph.get("title", ""),
                "description": knowledge_graph.get("description", ""),
                "type": "knowledge_panel",
                "relevance_score": 0.9
            })
        
        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return results[:settings.MAX_SEARCH_RESULTS]
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return "unknown"
    
    def _calculate_relevance(self, result: Dict[str, Any]) -> float:
        """Calculate relevance score for search result"""
        score = 0.5  # Base score
        
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        link = result.get("link", "").lower()
        
        # Boost for scholarship-related keywords
        scholarship_keywords = [
            "scholarship", "học bổng", "grant", "fellowship", 
            "funding", "financial aid", "tuition", "study abroad"
        ]
        
        for keyword in scholarship_keywords:
            if keyword in title:
                score += 0.3
            if keyword in snippet:
                score += 0.2
        
        # Boost for educational domains
        edu_domains = [".edu", ".ac.", "university", "college", "gov"]
        for domain in edu_domains:
            if domain in link:
                score += 0.2
                break
        
        # Boost for recent content
        current_year = "2024"
        next_year = "2025"
        if current_year in snippet or next_year in snippet:
            score += 0.1
        
        return min(score, 1.0)
    
    async def search_tuition_fees(
        self,
        university: str,
        country: str,
        program: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for tuition fee information"""
        
        query = f"{university} {country} tuition fees cost"
        if program:
            query += f" {program}"
        
        query += " 2024 2025 international students"
        
        return await self.search_scholarships(
            query=query,
            country=country,
            field=program,
            num_results=5
        )
    
    async def search_visa_requirements(
        self,
        country: str,
        nationality: str = "Vietnam"
    ) -> List[Dict[str, Any]]:
        """Search for visa requirements"""
        
        query = f"{country} student visa requirements {nationality} 2024"
        
        return await self.search_scholarships(
            query=query,
            country=country,
            num_results=5
        )

# Global search tool instance
web_search_tool = WebSearchTool()