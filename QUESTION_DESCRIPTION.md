# Production Embedding Service - Advanced Coding Challenge

## 🎯 Problem Statement

Build a **Production-Ready REST API Service** for text embeddings and document management using Google Gemini AI, ChromaDB vector database, and advanced caching mechanisms. Your task is to create a scalable, enterprise-grade service that can handle text documents, PDF files, and perform efficient similarity searches with comprehensive monitoring and error handling.

## 📋 Requirements Overview

### Core System Components
You need to implement a complete microservice architecture with:

1. **Flask REST API** with comprehensive endpoints and Swagger documentation
2. **Embedding Service** with Google Gemini AI integration and LRU caching
3. **PDF Processing** with text extraction and metadata handling
4. **Vector Database** using ChromaDB for persistent storage
5. **Configuration Management** with environment-based settings
6. **Comprehensive Testing** with unit tests and API validation

## 🏗️ Architecture Requirements

### System Architecture
```
Client → Flask API → LRU Cache → Gemini API → ChromaDB → Response
                  ↓
              PDF Extractor → Text Processing
```

### Required Files Structure
```
├── app.py                 # Main Flask application with REST API
├── embedding_service.py   # Core embedding service with caching
├── pdf_extractor.py      # PDF text extraction utility
├── config.py             # Configuration management
├── unit_test.py          # Comprehensive test suite
├── requirements.txt      # Dependencies
└── .env                  # Environment configuration
```

## 📚 Detailed Implementation Requirements

### 1. Flask REST API (`app.py`)

**Required Endpoints:**

#### Health & Monitoring
- `GET /api/v1/health/` - Health check with service status
- `GET /api/v1/cache/stats` - Cache performance metrics
- `POST /api/v1/cache/clear` - Clear embedding cache
- `GET /api/v1/collection/info` - Collection statistics
- `POST /api/v1/collection/reset` - Reset vector database

#### Embedding Operations
- `POST /api/v1/embed/` - Generate embedding for text
- `POST /api/v1/documents/text` - Add text document
- `POST /api/v1/documents/pdf` - Upload and process PDF
- `POST /api/v1/search/` - Similarity search

**API Features:**
- Flask-RESTX with Swagger UI documentation
- Request/response validation with marshmallow models
- File upload handling (50MB limit)
- Comprehensive error handling and logging
- CORS support and security headers

### 2. Embedding Service (`embedding_service.py`)

**Class: `EmbeddingService`**

**Required Methods:**
```python
def __init__(self, collection_name: str = "documents", cache_size: int = 1000)
    # Initialize with ChromaDB and LRU cache

@lru_cache(maxsize=1000)
def _generate_embedding_cached(self, text_hash: str, text: str) -> Optional[np.ndarray]
    # Cached embedding generation

def generate_embedding(self, text: str) -> Optional[np.ndarray]
    # Generate embedding with cache management

def add_document(self, text: str, metadata: Optional[Dict] = None) -> Optional[str]
    # Add document to ChromaDB collection

def search_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]
    # Perform similarity search

def get_collection_info(self) -> Dict[str, Any]
    # Get collection statistics

def reset_collection(self) -> bool
    # Reset collection data

def get_cache_stats(self) -> Dict[str, Any]
    # Get cache performance metrics

def clear_cache(self)
    # Clear LRU cache

def test_connection(self) -> Dict[str, bool]
    # Test external service connections
```

**Technical Specifications:**
- **Model**: `gemini-embedding-001`
- **Dimensions**: 3072
- **Cache**: LRU cache with configurable size
- **Database**: ChromaDB with persistent storage
- **Error Handling**: Comprehensive exception management

### 3. PDF Extractor (`pdf_extractor.py`)

**Class: `PDFExtractor`**

**Required Methods:**
```python
def extract_text_from_file(self, file_path: str) -> Dict[str, any]
    # Extract text from PDF file

def extract_text_from_bytes(self, pdf_bytes: bytes, filename: str) -> Dict[str, any]
    # Extract text from PDF bytes

def validate_pdf_file(self, file_content: bytes) -> bool
    # Validate PDF file format

def get_pdf_info(self, file_content: bytes) -> Dict[str, any]
    # Get PDF metadata without full extraction

def _clean_text(self, text: str) -> str
    # Clean and normalize extracted text
```

**Features:**
- PyMuPDF integration for text extraction
- Metadata extraction (title, author, page count, etc.)
- File size validation (50MB limit)
- Text cleaning and normalization
- Error handling for corrupted PDFs

### 4. Configuration Management (`config.py`)

**Class: `Config`**

**Required Configuration:**
```python
# Flask settings
HOST, PORT, DEBUG

# API settings  
MAX_TEXT_LENGTH, DEFAULT_SEARCH_RESULTS, MAX_SEARCH_RESULTS

# Cache settings
CACHE_SIZE

# ChromaDB settings
CHROMA_DB_PATH, COLLECTION_NAME

# Gemini settings
GEMINI_API_KEY, GEMINI_MODEL, EMBEDDING_DIMENSION

# Logging
LOG_LEVEL
```

## 🧪 Test Cases & Validation

Your implementation will be tested against these comprehensive scenarios:

### Test Case 1: API Key & Service Validation
```python
# Health check endpoint
response = requests.get("/api/v1/health/")
assert response.status_code == 200
assert response.json()['status'] == 'healthy'
assert response.json()['services']['gemini_api'] == True
assert response.json()['services']['chroma_db'] == True
```

### Test Case 2: Embedding Generation & Caching
```python
# Generate embedding
embed_data = {"text": "Test embedding text"}
response = requests.post("/api/v1/embed/", json=embed_data)
assert response.status_code == 200
result = response.json()
assert len(result['embedding']) == 3072
assert result['dimension'] == 3072

# Test caching (second request should be faster)
response2 = requests.post("/api/v1/embed/", json=embed_data)
assert response.json()['embedding'] == response2.json()['embedding']
```

### Test Case 3: Text Document Management
```python
# Add text document
doc_data = {
    "text": "Sample document content",
    "metadata": {"category": "test", "source": "unit_test"}
}
response = requests.post("/api/v1/documents/text", json=doc_data)
assert response.status_code == 201
assert 'document_id' in response.json()
```

### Test Case 4: PDF Processing
```python
# Upload PDF file
files = {'file': ('test.pdf', pdf_content, 'application/pdf')}
data = {'metadata': '{"category": "test_pdf"}'}
response = requests.post("/api/v1/documents/pdf", files=files, data=data)
assert response.status_code == 201
result = response.json()
assert 'extraction_info' in result
assert result['extraction_info']['pages_processed'] > 0
```

### Test Case 5: Similarity Search
```python
# Perform similarity search
search_data = {"query": "test document content", "k": 3}
response = requests.post("/api/v1/search/", json=search_data)
assert response.status_code == 200
result = response.json()
assert 'results' in result
assert len(result['results']) <= 3
for item in result['results']:
    assert 'similarity_score' in item
    assert 0 <= item['similarity_score'] <= 1
```

### Test Case 6: Collection Management
```python
# Get collection info
response = requests.get("/api/v1/collection/info")
assert response.status_code == 200
info = response.json()
assert 'document_count' in info
assert 'embedding_dimension' in info

# Reset collection
response = requests.post("/api/v1/collection/reset")
assert response.status_code == 200
```

### Test Case 7: Cache Performance
```python
# Get cache stats
response = requests.get("/api/v1/cache/stats")
assert response.status_code == 200
stats = response.json()
assert 'cache_hits' in stats
assert 'cache_misses' in stats
assert 'hit_rate' in stats

# Clear cache
response = requests.post("/api/v1/cache/clear")
assert response.status_code == 200
```

## 📊 Evaluation Criteria

Your solution will be evaluated on:

1. **API Functionality** (30%): All endpoints work correctly with proper HTTP status codes
2. **Data Processing** (25%): Text and PDF processing with metadata extraction
3. **Performance** (20%): Caching implementation and response times
4. **Error Handling** (15%): Robust exception management and logging
5. **Code Quality** (10%): Clean architecture, documentation, and best practices

## 🔧 Technical Requirements

### Dependencies
```txt
flask>=2.3.0
flask-restx>=1.1.0
python-dotenv>=1.0.0
google-genai>=0.3.0
numpy>=1.24.0
chromadb>=0.4.0
requests>=2.31.0
PyMuPDF>=1.23.0
```

### Environment Configuration
```env
GEMINI_API_KEY=your_api_key_here
HOST=127.0.0.1
PORT=5000
DEBUG=false
CACHE_SIZE=1000
CHROMA_DB_PATH=./chroma_db
COLLECTION_NAME=documents
MAX_TEXT_LENGTH=10000
```

### Performance Requirements
- **Response Time**: < 2 seconds for embedding generation
- **Cache Hit Rate**: > 70% for repeated requests
- **File Processing**: Support up to 50MB PDF files
- **Concurrent Users**: Handle 10+ simultaneous requests
- **Memory Usage**: Efficient memory management for large documents

## 📝 Submission Requirements

### Required Files
1. **`app.py`**: Complete Flask application with all endpoints
2. **`embedding_service.py`**: Core service with caching and ChromaDB integration
3. **`pdf_extractor.py`**: PDF processing utility with PyMuPDF
4. **`config.py`**: Configuration management class
5. **`unit_test.py`**: Comprehensive test suite with 7+ test cases
6. **`requirements.txt`**: All required dependencies
7. **`.env`**: Environment configuration template

### Documentation Requirements
- **API Documentation**: Swagger UI accessible at `/docs/`
- **Code Comments**: Clear docstrings and inline comments
- **README**: Setup instructions and API usage examples
- **Error Handling**: Comprehensive logging and error responses

## 🎯 Success Criteria

Your implementation is successful when:

- ✅ All 7 test cases pass with 100% success rate
- ✅ API serves 100+ requests without memory leaks
- ✅ PDF processing handles various document formats
- ✅ Cache achieves >70% hit rate on repeated requests
- ✅ Similarity search returns relevant results with proper ranking
- ✅ Service recovers gracefully from API failures
- ✅ Swagger documentation is complete and functional
- ✅ Code follows Python best practices and PEP 8

## 🔍 Sample Usage

```python
# Start the service
python app.py

# Add text document
curl -X POST http://127.0.0.1:5000/api/v1/documents/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Machine learning is transforming industries", "metadata": {"category": "tech"}}'

# Upload PDF
curl -X POST http://127.0.0.1:5000/api/v1/documents/pdf \
  -F "file=@document.pdf" \
  -F 'metadata={"source": "research_paper"}'

# Search similar documents
curl -X POST http://127.0.0.1:5000/api/v1/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence applications", "k": 5}'

# Check service health
curl http://127.0.0.1:5000/api/v1/health/
```

## ⚠️ Important Notes

- **API Key Security**: Never commit API keys to version control
- **File Handling**: Implement proper file validation and cleanup
- **Memory Management**: Handle large files efficiently
- **Error Logging**: Log all errors with appropriate detail levels
- **Testing**: Ensure all tests can run independently
- **Documentation**: Keep Swagger documentation up to date

Build a production-ready embedding service that demonstrates enterprise-level software engineering skills! 🚀
