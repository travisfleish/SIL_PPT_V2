# utils/logo_scraper.py
"""
Automated Logo Scraper for Company Logos
Multi-pronged approach using APIs, social media, and web scraping
"""

import asyncio
import aiohttp
import logging
import json
import re
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from urllib.parse import urljoin, urlparse, quote
from PIL import Image
import io
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import base64

logger = logging.getLogger(__name__)


@dataclass
class LogoResult:
    """Result from logo search"""
    url: str
    source: str  # 'brandfetch', 'google', 'instagram', 'linkedin', etc.
    quality_score: float  # 0-1, higher is better
    size: Tuple[int, int]
    format: str
    company_name: str
    search_query: str
    metadata: Dict[str, Any] = None


class LogoScraper:
    """
    Multi-pronged logo scraper using various sources
    """
    
    def __init__(self, 
                 output_dir: Optional[Path] = None,
                 brandfetch_api_key: Optional[str] = None,
                 cache_enabled: bool = True,
                 max_concurrent: int = 5):
        """
        Initialize logo scraper
        
        Args:
            output_dir: Directory to save logos (defaults to assets/logos/merchants)
            brandfetch_api_key: API key for BrandFetch service
            cache_enabled: Whether to use caching
            max_concurrent: Maximum concurrent requests
        """
        self.output_dir = output_dir or Path(__file__).parent.parent / 'assets' / 'logos' / 'merchants'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.brandfetch_api_key = brandfetch_api_key
        self.cache_enabled = cache_enabled
        self.max_concurrent = max_concurrent
        
        # Cache for results
        self.cache_file = self.output_dir.parent / 'logo_scraper_cache.json'
        self.cache = self._load_cache() if cache_enabled else {}
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # seconds between requests per source
        
        # User agents for web scraping
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        
        logger.info(f"LogoScraper initialized with output directory: {self.output_dir}")
    
    def _load_cache(self) -> Dict:
        """Load cache from file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save cache to file"""
        if self.cache_enabled:
            try:
                with open(self.cache_file, 'w') as f:
                    json.dump(self.cache, f, indent=2)
            except Exception as e:
                logger.warning(f"Failed to save cache: {e}")
    
    def _rate_limit(self, source: str):
        """Implement rate limiting"""
        now = time.time()
        if source in self.last_request_time:
            elapsed = now - self.last_request_time[source]
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        self.last_request_time[source] = time.time()
    
    def _generate_cache_key(self, company_name: str, source: str) -> str:
        """Generate cache key for company/source combination"""
        return f"{company_name.lower()}_{source}"
    
    def _is_logo_good_quality(self, image: Image.Image, min_size: int = 64) -> Tuple[bool, float]:
        """
        Evaluate logo quality
        
        Args:
            image: PIL Image object
            min_size: Minimum width/height in pixels
            
        Returns:
            Tuple of (is_good, quality_score)
        """
        width, height = image.size
        
        # Size check
        if width < min_size or height < min_size:
            return False, 0.0
        
        # Aspect ratio check (logos should be roughly square or rectangular)
        aspect_ratio = max(width, height) / min(width, height)
        if aspect_ratio > 4:  # Too elongated
            return False, 0.0
        
        # Color diversity check (logos should have some color variation)
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Get color histogram
            colors = image.getcolors(maxcolors=256*256*256)
            if colors and len(colors) > 1:
                # Calculate color diversity score
                total_pixels = sum(count for count, _ in colors)
                color_diversity = len(colors) / min(total_pixels, 1000)  # Normalize
                
                # Size score (prefer larger images)
                size_score = min(width * height / (200 * 200), 1.0)
                
                # Aspect ratio score
                aspect_score = 1.0 - min(aspect_ratio - 1, 3) / 3
                
                quality_score = (color_diversity * 0.4 + size_score * 0.4 + aspect_score * 0.2)
                
                return quality_score > 0.3, quality_score
            else:
                return False, 0.0
                
        except Exception as e:
            logger.debug(f"Quality check failed: {e}")
            return False, 0.0
    
    async def _fetch_brandfetch_logo(self, company_name: str) -> Optional[LogoResult]:
        """
        Fetch logo from BrandFetch API
        
        Args:
            company_name: Company name to search for
            
        Returns:
            LogoResult or None
        """
        if not self.brandfetch_api_key:
            logger.debug("BrandFetch API key not provided")
            return None
        
        cache_key = self._generate_cache_key(company_name, 'brandfetch')
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if datetime.fromisoformat(cached_result['cached_at']) > datetime.now() - timedelta(days=7):
                logger.debug(f"Using cached BrandFetch result for {company_name}")
                return LogoResult(**cached_result['data'])
        
        self._rate_limit('brandfetch')
        
        try:
            # BrandFetch API uses search endpoint with Client ID parameter
            base_url = "https://api.brandfetch.io/v2/search"
            
            # Try different search variations
            search_queries = [
                company_name,
                company_name.replace(' ', ''),
                company_name.replace(' ', '_'),
                company_name.replace(' ', '-')
            ]
            
            async with aiohttp.ClientSession() as session:
                for query in search_queries:
                    # Build URL with Client ID parameter
                    url = f"{base_url}/{query}"
                    params = {'c': self.brandfetch_api_key}
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # BrandFetch search API returns different structure
                            # Look for logos in the response
                            logos = []
                            
                            # Handle different possible response structures
                            if isinstance(data, dict):
                                if 'logos' in data:
                                    logos = data['logos']
                                elif 'brand' in data and 'logos' in data['brand']:
                                    logos = data['brand']['logos']
                                elif 'results' in data:
                                    # Multiple results, take the first one
                                    for result in data['results']:
                                        if 'logos' in result:
                                            logos = result['logos']
                                            break
                            elif isinstance(data, list) and data:
                                # Response is a list, check first item
                                if 'logos' in data[0]:
                                    logos = data[0]['logos']
                            
                            if logos:
                                # Find the best logo (prefer PNG, then JPG)
                                best_logo = None
                                for logo in logos:
                                    if isinstance(logo, dict):
                                        logo_type = logo.get('type', '').lower()
                                        if logo_type in ['png', 'jpg', 'jpeg']:
                                            best_logo = logo
                                            break
                                
                                if not best_logo and logos:
                                    best_logo = logos[0]
                                
                                if best_logo and isinstance(best_logo, dict):
                                    logo_url = best_logo.get('image') or best_logo.get('url')
                                    if logo_url:
                                        # Download and validate the logo
                                        logo_result = await self._download_and_validate_logo(
                                            logo_url, 'brandfetch', company_name, query
                                        )
                                        
                                        if logo_result:
                                            # Cache the result
                                            self.cache[cache_key] = {
                                                'data': logo_result.__dict__,
                                                'cached_at': datetime.now().isoformat()
                                            }
                                            self._save_cache()
                                            return logo_result
                        
                        await asyncio.sleep(0.5)  # Small delay between requests
                        
        except Exception as e:
            logger.warning(f"BrandFetch API error for {company_name}: {e}")
        
        return None
    
    async def _fetch_google_images_logo(self, company_name: str) -> Optional[LogoResult]:
        """
        Fetch logo from Google Images search
        
        Args:
            company_name: Company name to search for
            
        Returns:
            LogoResult or None
        """
        cache_key = self._generate_cache_key(company_name, 'google')
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if datetime.fromisoformat(cached_result['cached_at']) > datetime.now() - timedelta(days=3):
                logger.debug(f"Using cached Google Images result for {company_name}")
                return LogoResult(**cached_result['data'])
        
        self._rate_limit('google')
        
        try:
            # Create search queries
            search_queries = [
                f"{company_name} logo",
                f"{company_name} brand logo",
                f"{company_name} company logo",
                f'"{company_name}" logo transparent'
            ]
            
            async with aiohttp.ClientSession() as session:
                for query in search_queries:
                    # Use Google Custom Search API or web scraping
                    # For now, we'll use a simple approach with DuckDuckGo images
                    search_url = f"https://duckduckgo.com/?q={quote(query)}&t=h_&iax=images&ia=images"
                    
                    headers = {
                        'User-Agent': self.user_agents[0],
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                    }
                    
                    async with session.get(search_url, headers=headers) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Extract image URLs from the HTML
                            # This is a simplified approach - in production you'd want more robust parsing
                            img_pattern = r'https://[^"]*\.(?:png|jpg|jpeg|gif|webp)'
                            img_urls = re.findall(img_pattern, html, re.IGNORECASE)
                            
                            # Try to download and validate images
                            for img_url in img_urls[:5]:  # Limit to first 5 results
                                try:
                                    logo_result = await self._download_and_validate_logo(
                                        img_url, 'google', company_name, query
                                    )
                                    
                                    if logo_result and logo_result.quality_score > 0.5:
                                        # Cache the result
                                        self.cache[cache_key] = {
                                            'data': logo_result.__dict__,
                                            'cached_at': datetime.now().isoformat()
                                        }
                                        self._save_cache()
                                        return logo_result
                                        
                                except Exception as e:
                                    logger.debug(f"Failed to process image {img_url}: {e}")
                                    continue
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
        except Exception as e:
            logger.warning(f"Google Images search error for {company_name}: {e}")
        
        return None
    
    async def _fetch_social_media_logo(self, company_name: str) -> Optional[LogoResult]:
        """
        Fetch logo from social media profiles (Instagram/LinkedIn)
        
        Args:
            company_name: Company name to search for
            
        Returns:
            LogoResult or None
        """
        cache_key = self._generate_cache_key(company_name, 'social')
        if cache_key in self.cache:
            cached_result = self.cache[cache_key]
            if datetime.fromisoformat(cached_result['cached_at']) > datetime.now() - timedelta(days=5):
                logger.debug(f"Using cached social media result for {company_name}")
                return LogoResult(**cached_result['data'])
        
        self._rate_limit('social')
        
        try:
            # Clean company name for social media search
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
            
            headers = {
                'User-Agent': self.user_agents[0],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            # Try Instagram
            instagram_url = f"https://www.instagram.com/{clean_name}/"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(instagram_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Look for profile picture in meta tags
                            profile_img_pattern = r'<meta property="og:image" content="([^"]*)"'
                            match = re.search(profile_img_pattern, html)
                            
                            if match:
                                img_url = match.group(1)
                                logo_result = await self._download_and_validate_logo(
                                    img_url, 'instagram', company_name, clean_name
                                )
                                
                                if logo_result:
                                    # Cache the result
                                    self.cache[cache_key] = {
                                        'data': logo_result.__dict__,
                                        'cached_at': datetime.now().isoformat()
                                    }
                                    self._save_cache()
                                    return logo_result
                except Exception as e:
                    logger.debug(f"Instagram search failed for {company_name}: {e}")
            
            await asyncio.sleep(1)
            
            # Try LinkedIn
            linkedin_url = f"https://www.linkedin.com/company/{clean_name}/"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(linkedin_url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Look for company logo in meta tags
                            logo_pattern = r'<meta property="og:image" content="([^"]*)"'
                            match = re.search(logo_pattern, html)
                            
                            if match:
                                img_url = match.group(1)
                                logo_result = await self._download_and_validate_logo(
                                    img_url, 'linkedin', company_name, clean_name
                                )
                                
                                if logo_result:
                                    # Cache the result
                                    self.cache[cache_key] = {
                                        'data': logo_result.__dict__,
                                        'cached_at': datetime.now().isoformat()
                                    }
                                    self._save_cache()
                                    return logo_result
                except Exception as e:
                    logger.debug(f"LinkedIn search failed for {company_name}: {e}")
            
        except Exception as e:
            logger.warning(f"Social media search error for {company_name}: {e}")
        
        return None
    
    async def _download_and_validate_logo(self, url: str, source: str, 
                                        company_name: str, search_query: str) -> Optional[LogoResult]:
        """
        Download and validate a logo from URL
        
        Args:
            url: Image URL
            source: Source name (brandfetch, google, etc.)
            company_name: Company name
            search_query: Search query used
            
        Returns:
            LogoResult or None
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': self.user_agents[0],
                    'Accept': 'image/*,*/*;q=0.8',
                }
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        # Read image data
                        image_data = await response.read()
                        
                        # Validate it's actually an image
                        try:
                            image = Image.open(io.BytesIO(image_data))
                            
                            # Check quality
                            is_good, quality_score = self._is_logo_good_quality(image)
                            
                            if is_good:
                                # Determine format
                                format_name = image.format or 'unknown'
                                
                                return LogoResult(
                                    url=url,
                                    source=source,
                                    quality_score=quality_score,
                                    size=image.size,
                                    format=format_name,
                                    company_name=company_name,
                                    search_query=search_query,
                                    metadata={
                                        'content_length': len(image_data),
                                        'content_type': response.headers.get('content-type', 'unknown')
                                    }
                                )
                            else:
                                logger.debug(f"Logo quality too low for {company_name}: {quality_score}")
                                
                        except Exception as e:
                            logger.debug(f"Invalid image data from {url}: {e}")
                            
        except Exception as e:
            logger.debug(f"Failed to download logo from {url}: {e}")
        
        return None
    
    async def scrape_logo(self, company_name: str) -> Optional[LogoResult]:
        """
        Scrape logo for a company using all available methods
        
        Args:
            company_name: Company name to search for
            
        Returns:
            Best LogoResult found or None
        """
        logger.info(f"Scraping logo for: {company_name}")
        
        # Try all methods concurrently
        tasks = []
        
        if self.brandfetch_api_key:
            tasks.append(self._fetch_brandfetch_logo(company_name))
        
        tasks.append(self._fetch_google_images_logo(company_name))
        tasks.append(self._fetch_social_media_logo(company_name))
        
        # Run tasks with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[run_with_semaphore(task) for task in tasks], return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_results = [r for r in results if isinstance(r, LogoResult)]
        
        if not valid_results:
            logger.warning(f"No logos found for {company_name}")
            return None
        
        # Sort by quality score and return the best one
        best_result = max(valid_results, key=lambda x: x.quality_score)
        logger.info(f"Best logo found for {company_name}: {best_result.source} (score: {best_result.quality_score:.2f})")
        
        return best_result
    
    async def download_logo(self, logo_result: LogoResult) -> Optional[Path]:
        """
        Download and save logo to local file
        
        Args:
            logo_result: LogoResult to download
            
        Returns:
            Path to saved file or None
        """
        try:
            # Generate filename
            clean_name = re.sub(r'[^a-zA-Z0-9]', '_', logo_result.company_name.lower())
            filename = f"{clean_name}.{logo_result.format.lower()}"
            filepath = self.output_dir / filename
            
            # Download image
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': self.user_agents[0],
                    'Accept': 'image/*,*/*;q=0.8',
                }
                
                async with session.get(logo_result.url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # Save to file
                        with open(filepath, 'wb') as f:
                            f.write(image_data)
                        
                        logger.info(f"Logo saved: {filepath}")
                        return filepath
                        
        except Exception as e:
            logger.error(f"Failed to download logo for {logo_result.company_name}: {e}")
        
        return None
    
    async def scrape_multiple_logos(self, company_names: List[str]) -> Dict[str, Optional[LogoResult]]:
        """
        Scrape logos for multiple companies
        
        Args:
            company_names: List of company names
            
        Returns:
            Dict mapping company names to LogoResults
        """
        logger.info(f"Scraping logos for {len(company_names)} companies")
        
        # Process companies in batches to avoid overwhelming servers
        batch_size = 10
        results = {}
        
        for i in range(0, len(company_names), batch_size):
            batch = company_names[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(company_names) + batch_size - 1)//batch_size}")
            
            # Process batch concurrently
            batch_tasks = [self.scrape_logo(name) for name in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Store results
            for name, result in zip(batch, batch_results):
                if isinstance(result, LogoResult):
                    results[name] = result
                else:
                    results[name] = None
                    logger.warning(f"Failed to scrape logo for {name}: {result}")
            
            # Small delay between batches
            if i + batch_size < len(company_names):
                await asyncio.sleep(2)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        total_cached = len(self.cache)
        sources = {}
        
        for cached_item in self.cache.values():
            source = cached_item['data']['source']
            sources[source] = sources.get(source, 0) + 1
        
        return {
            'total_cached_results': total_cached,
            'sources': sources,
            'cache_enabled': self.cache_enabled,
            'output_directory': str(self.output_dir)
        }


# CLI interface
async def main():
    """Command line interface for logo scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Logo Scraper')
    parser.add_argument('companies', nargs='+', help='Company names to scrape logos for')
    parser.add_argument('--brandfetch-key', help='BrandFetch API key')
    parser.add_argument('--output-dir', help='Output directory for logos')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    parser.add_argument('--download', action='store_true', help='Download found logos')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = LogoScraper(
        output_dir=Path(args.output_dir) if args.output_dir else None,
        brandfetch_api_key=args.brandfetch_key,
        cache_enabled=not args.no_cache
    )
    
    if args.stats:
        stats = scraper.get_stats()
        print(f"Logo Scraper Statistics:")
        print(f"  Total cached results: {stats['total_cached_results']}")
        print(f"  Sources: {stats['sources']}")
        print(f"  Cache enabled: {stats['cache_enabled']}")
        print(f"  Output directory: {stats['output_directory']}")
        return
    
    # Scrape logos
    results = await scraper.scrape_multiple_logos(args.companies)
    
    # Print results
    print(f"\nLogo Scraping Results:")
    print(f"{'='*60}")
    
    for company, result in results.items():
        if result:
            print(f"✅ {company}")
            print(f"   Source: {result.source}")
            print(f"   Quality: {result.quality_score:.2f}")
            print(f"   Size: {result.size[0]}x{result.size[1]}")
            print(f"   Format: {result.format}")
            print(f"   URL: {result.url}")
            
            if args.download:
                downloaded_path = await scraper.download_logo(result)
                if downloaded_path:
                    print(f"   Downloaded: {downloaded_path}")
            
            print()
        else:
            print(f"❌ {company} - No logo found")
    
    # Save cache
    scraper._save_cache()


if __name__ == '__main__':
    asyncio.run(main())
