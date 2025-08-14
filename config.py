import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""
    
    # Flask settings
    HOST = '0.0.0.0'  # Hardcoded for deployment
    PORT = 8081       # Hardcoded for deployment
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # API settings
    MAX_TEXT_LENGTH = int(os.getenv('MAX_TEXT_LENGTH', 10000))
    DEFAULT_SEARCH_RESULTS = int(os.getenv('DEFAULT_SEARCH_RESULTS', 5))
    MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', 50))
    
    # Cache settings
    CACHE_SIZE = int(os.getenv('CACHE_SIZE', 1000))
    
    # Chroma settings
    CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'documents')
    
    # Gemini settings
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-embedding-001')
    EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', 3072))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        return True