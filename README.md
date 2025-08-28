# Embedding Service API

A production-ready Flask API for text embeddings using Google Gemini, Chroma vector database, and LRU caching.

## Features

- **Flask REST API** with comprehensive endpoints
- **Google Gemini Embeddings** for high-quality text embeddings
- **Chroma Vector Database** for scalable vector storage and retrieval
- **LRU Cache** for embedding optimization and performance
- **Error Handling & Logging** for production reliability
- **Health Checks** and monitoring endpoints

## Quick Start

### 1. Install Dependencies
```bash
cd embedding_service
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### 3. Run the Service
```bash
python app.py
```

The API will be available at `http://0.0.0.0:8081`

## API Endpoints

### Health Check
```bash
GET /health
```

### Generate Embedding
```bash
POST /embed
Content-Type: application/json

{
  "text": "Your text here"
}
```

### Add Document
```bash
POST /add
Content-Type: application/json

{
  "text": "Document content",
  "metadata": {"title": "Optional metadata"}
}
```

### Search Similar Documents
```bash
POST /search
Content-Type: application/json

{
  "query": "Search query",
  "k": 5
}
```

### Collection Management
```bash
GET /collection/info     # Get collection stats
POST /collection/reset   # Reset collection
```

### Cache Management
```bash
GET /cache/stats         # Get cache statistics
POST /cache/clear        # Clear cache
```

## Example Usage

```bash
# Add documents
curl -X POST http://0.0.0.0:8081/add \
  -H "Content-Type: application/json" \
  -d '{"text": "The quick brown fox jumps over the lazy dog"}'

# Search similar
curl -X POST http://0.0.0.0:8081/search \

## Testing

### Async Test Suite

The project includes a comprehensive async test suite using pytest and httpx:

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests with pytest (recommended)
pytest tests.py -v

# Or use the test runner script
python run_tests.py

# Run tests directly with asyncio
python run_tests.py --direct

# Run specific test
pytest tests.py::test_generate_embedding -v
```

### Test Coverage

The test suite includes 16 comprehensive test cases:

- **Health Check** - API connectivity and service status
- **Embedding Generation** - Core embedding functionality and validation
- **Document Management** - Text and PDF document ingestion
- **Search Operations** - Similarity search and validation
- **Collection Management** - Collection info, stats, and reset
- **Cache Management** - Cache statistics and functionality
- **Error Handling** - Input validation and error responses
- **Concurrent Operations** - Multi-request performance testing

### Test Requirements

- API server must be running at `http://localhost:8081`
- Valid `GEMINI_API_KEY` configured in `.env`
- All dependencies installed from `requirements.txt`

  -H "Content-Type: application/json" \
  -d '{"query": "fast animal jumping", "k": 3}'
```

## Configuration

Environment variables in `.env`:

- `GEMINI_API_KEY` - Your Google Gemini API key (required)
- `HOST` - API host (hardcoded: 0.0.0.0)
- `PORT` - API port (hardcoded: 8081)
- `DEBUG` - Debug mode (default: false)
- `CACHE_SIZE` - LRU cache size (default: 1000)

## Troubleshooting

### SQLite3 Compatibility Issue

If you encounter the error:
```
RuntimeError: Your system has an unsupported version of sqlite3. Chroma requires sqlite3 >= 3.35.0.
```

**Quick Fix:**
```bash
# Run the setup script
chmod +x setup.sh
./setup.sh
```

**Manual Fix:**
```bash
# Install pysqlite3-binary
pip install pysqlite3-binary

# Reinstall requirements
pip install -r requirements.txt
```

The code already includes compatibility fixes that automatically use `pysqlite3-binary` when available.

### Other Common Issues

- **Missing API Key**: Ensure `GEMINI_API_KEY` is set in your `.env` file
- **Port Already in Use**: Change the `PORT` in `.env` or kill the process using the port
- **Permission Issues**: Ensure write permissions for `chroma_db` and `uploads` directories

## Architecture

```
Client → Flask API → LRU Cache → Gemini API → Chroma DB → Response
```

## Performance Features

- **LRU Caching**: Avoids redundant embedding generation
- **Persistent Storage**: Chroma DB maintains data between restarts
- **Efficient Search**: Vector similarity search with configurable results
- **Error Recovery**: Comprehensive error handling and logging