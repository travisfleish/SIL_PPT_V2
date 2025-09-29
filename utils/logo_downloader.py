# utils/logo_downloader.py
"""
Logo downloader utility - Enhanced with automated scraping
Integrates with the new LogoScraper for automated logo acquisition
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class LogoDownloader:
    """Enhanced logo downloader with automated scraping capabilities"""

    def __init__(self, cache_dir: Optional[Path] = None, brandfetch_api_key: Optional[str] = None):
        """
        Initialize logo downloader
        
        Args:
            cache_dir: Directory to cache logos
            brandfetch_api_key: Optional BrandFetch API key for better results
        """
        self.cache_dir = cache_dir or Path('logos')
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize the scraper
        try:
            from utils.logo_scraper import LogoScraper
            self.scraper = LogoScraper(
                output_dir=self.cache_dir,
                brandfetch_api_key=brandfetch_api_key,
                cache_enabled=True
            )
            logger.info("LogoDownloader initialized with automated scraping")
        except ImportError:
            logger.warning("LogoScraper not available - using basic functionality only")
            self.scraper = None

    async def download_logo(self, company_name: str, force_refresh: bool = False) -> Optional[Path]:
        """
        Download company logo using automated scraping
        
        Args:
            company_name: Name of the company
            force_refresh: Force refresh even if cached
            
        Returns:
            Path to logo file or None if not found
        """
        if not self.scraper:
            logger.warning("Automated scraping not available")
            return None
        
        logger.info(f"Downloading logo for: {company_name}")
        
        try:
            # Check if logo already exists locally
            if not force_refresh:
                existing_logo = self._find_existing_logo(company_name)
                if existing_logo:
                    logger.info(f"Using existing logo: {existing_logo}")
                    return existing_logo
            
            # Scrape for logo
            result = await self.scraper.scrape_logo(company_name)
            
            if result:
                # Download the logo
                downloaded_path = await self.scraper.download_logo(result)
                
                if downloaded_path:
                    logger.info(f"Logo downloaded successfully: {downloaded_path}")
                    return downloaded_path
                else:
                    logger.warning(f"Failed to download logo for {company_name}")
            else:
                logger.warning(f"No logo found for {company_name}")
                
        except Exception as e:
            logger.error(f"Error downloading logo for {company_name}: {e}")
        
        return None

    def _find_existing_logo(self, company_name: str) -> Optional[Path]:
        """Find existing logo file for company"""
        # Generate possible filename variations (similar to LogoManager)
        search_names = self._generate_search_names(company_name)
        supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
        
        for search_name in search_names:
            for ext in supported_formats:
                logo_path = self.cache_dir / f"{search_name}{ext}"
                if logo_path.exists():
                    return logo_path
        
        return None

    def _generate_search_names(self, company_name: str) -> List[str]:
        """Generate possible filename variations for company"""
        import re
        import unicodedata
        
        variations = []
        
        # Original name
        variations.append(company_name)
        
        # Lowercase
        variations.append(company_name.lower())
        
        # Replace spaces with underscores and hyphens
        variations.append(company_name.lower().replace(' ', '_'))
        variations.append(company_name.lower().replace(' ', '-'))
        
        # Remove special characters
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
        variations.append(clean_name)
        
        # Unicode normalization
        normalized = unicodedata.normalize('NFD', company_name)
        ascii_only = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
        if ascii_only != company_name:
            variations.append(ascii_only.lower())
            variations.append(ascii_only.lower().replace(' ', '_'))
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(variations))

    async def download_multiple_logos(self, company_names: List[str], 
                                    force_refresh: bool = False) -> Dict[str, Optional[Path]]:
        """
        Download logos for multiple companies
        
        Args:
            company_names: List of company names
            force_refresh: Force refresh even if cached
            
        Returns:
            Dict mapping company names to downloaded file paths
        """
        if not self.scraper:
            logger.warning("Automated scraping not available")
            return {name: None for name in company_names}
        
        logger.info(f"Downloading logos for {len(company_names)} companies")
        
        results = {}
        
        for company in company_names:
            try:
                path = await self.download_logo(company, force_refresh)
                results[company] = path
                
                if path:
                    logger.info(f"✅ {company}: {path}")
                else:
                    logger.warning(f"❌ {company}: No logo found")
                    
            except Exception as e:
                logger.error(f"Error processing {company}: {e}")
                results[company] = None
        
        return results

    def get_cached_logo(self, company_name: str) -> Optional[Path]:
        """Check if logo exists in cache"""
        return self._find_existing_logo(company_name)

    def list_cached_logos(self) -> List[str]:
        """List all cached logo files"""
        logos = []
        supported_formats = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}
        
        for ext in supported_formats:
            for logo_file in self.cache_dir.glob(f"*{ext}"):
                logos.append(logo_file.stem)
        
        return sorted(set(logos))

    def get_stats(self) -> Dict[str, Any]:
        """Get downloader statistics"""
        stats = {
            'cache_directory': str(self.cache_dir),
            'cached_logos': len(self.list_cached_logos()),
            'scraper_available': self.scraper is not None
        }
        
        if self.scraper:
            scraper_stats = self.scraper.get_stats()
            stats.update({
                'scraper_cache_enabled': scraper_stats['cache_enabled'],
                'scraper_cached_results': scraper_stats['total_cached_results'],
                'scraper_sources': scraper_stats['sources']
            })
        
        return stats

    def clear_cache(self):
        """Clear all cached logos"""
        try:
            for logo_file in self.cache_dir.glob("*"):
                if logo_file.is_file():
                    logo_file.unlink()
            logger.info(f"Cleared logo cache in {self.cache_dir}")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_missing_logos_report(self, company_names: List[str]) -> Dict[str, bool]:
        """
        Generate report of which companies have/don't have logos
        
        Args:
            company_names: List of company names to check
            
        Returns:
            Dict mapping company name to whether logo exists
        """
        report = {}
        for company in company_names:
            logo_path = self._find_existing_logo(company)
            report[company] = logo_path is not None
        
        return report