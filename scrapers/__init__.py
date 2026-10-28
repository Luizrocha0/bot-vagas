"""
Módulo de scrapers para o Caçador de Vagas.
Contém a classe base BaseJobScraper e implementações para diferentes fontes:
- LinkedIn
- Gupy
- Programathor
- Indeed
"""

from .base import BaseJobScraper
from .gupy_scraper import GupyScraper
from .programathor_scraper import ProgramathorScraper
from .indeed_scraper import IndeedScraper
from linkedin_scraper import LinkedInScraper

__all__ = [
    "BaseJobScraper",
    "LinkedInScraper",
    "GupyScraper",
    "ProgramathorScraper",
    "IndeedScraper"
]
