from flask import Flask, request
from flask_restx import Api, Resource, fields
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
import logging
from typing import List, Dict, Any
import json

from embedding_service import EmbeddingService
from config import Config
from pdf_extractor import PDFExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Configure file upload settings
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Flask-RESTX with Swagger UI
api = Api(
    app,
    version='1.0',
    title='Embedding Service API with PDF Support',
    description='A production-ready Flask API for text embeddings using Google Gemini, Chroma vector database, LRU caching, and PDF document processing.',
    doc='/docs/',
    prefix='/api/v1'
)

# Initialize services
embedding_service = EmbeddingService()
pdf_extractor = PDFExtractor()

# Define API namespaces
ns_health = api.namespace('health', description='Health check operations')
ns_embed = api.namespace('embed', description='Embedding operations')  
ns_docs = api.namespace('documents', description='Document management operations')
ns_search = api.namespace('search', description='Search operations')
ns_collection = api.namespace('collection', description='Collection management')
ns_cache = api.namespace('cache', description='Cache management')

# Define API models for request/response validation
embed_request_model = api.model('EmbedRequest', {
    'text': fields.String(required=True, description='Text to generate embedding for', example='Hello, this is a test message.')
})

embed_response_model = api.model('EmbedResponse', {
    'text': fields.String(description='Input text'),
    'embedding': fields.List(fields.Float, description='Generated embedding vector'),
    'dimension': fields.Integer(description='Embedding dimension')
})

# Text-based document request
add_text_document_model = api.model('AddTextDocument', {
    'text': fields.String(required=True, description='Document text to add', example='The lighthouse keeper watched over ships in the stormy night.'),
    'metadata': fields.Raw(description='Optional metadata dictionary', example={'category': 'story', 'theme': 'lighthouse'})
})

# PDF document response model
pdf_extraction_info_model = api.model('PDFExtractionInfo', {
    'source_type': fields.String(description='Source type'),
    'filename': fields.String(description='Original filename'),
    'file_size_bytes': fields.Integer(description='File size in bytes'),
    'page_count': fields.Integer(description='Number of pages'),
    'char_count': fields.Integer(description='Character count'),
    'word_count': fields.Integer(description='Word count'),
    'pdf_title': fields.String(description='PDF title (optional)'),
    'pdf_author': fields.String(description='PDF author (optional)'),
    'pdf_creator': fields.String(description='PDF creator (optional)'),
    'pdf_producer': fields.String(description='PDF producer (optional)')
})

add_document_response_model = api.model('AddDocumentResponse', {
    'document_id': fields.String(description='Generated document ID'),
    'text': fields.String(description='Extracted/provided text'),
    'metadata': fields.Nested(pdf_extraction_info_model, description='Document metadata'),
    'message': fields.String(description='Success message'),
    'extraction_info': fields.Raw(description='Additional extraction information for PDFs')
})

search_request_model = api.model('SearchRequest', {
    'query': fields.String(required=True, description='Search query text', example='lighthouse and sea stories'),
    'k': fields.Integer(description='Number of results to return', default=5, example=3)
})

search_result_model = api.model('SearchResult', {
    'id': fields.String(description='Document ID'),
    'text': fields.String(description='Document text'),
    'metadata': fields.Raw(description='Document metadata'),
    'distance': fields.Float(description='Vector distance'),
    'similarity_score': fields.Float(description='Similarity score (0-1)')
})

search_response_model = api.model('SearchResponse', {
    'query': fields.String(description='Search query'),
    'results': fields.List(fields.Nested(search_result_model)),
    'count': fields.Integer(description='Number of results returned')
})

health_response_model = api.model('HealthResponse', {
    'status': fields.String(description='Health status'),
    'services': fields.Raw(description='Service status details')
})

collection_info_model = api.model('CollectionInfo', {
    'collection_name': fields.String(description='Collection name'),
    'document_count': fields.Integer(description='Number of documents'),
    'embedding_dimension': fields.Integer(description='Embedding dimension'),
    'model': fields.String(description='Embedding model name')
})

cache_stats_model = api.model('CacheStats', {
    'cache_hits': fields.Integer(description='Number of cache hits'),
    'cache_misses': fields.Integer(description='Number of cache misses'),
    'cache_size': fields.Integer(description='Current cache size'),
    'cache_maxsize': fields.Integer(description='Maximum cache size'),
    'hit_rate': fields.Float(description='Cache hit rate (0-1)')
})

error_model = api.model('Error', {
    'error': fields.String(description='Error message')
})

# File upload parser
file_upload_parser = api.parser()
file_upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='PDF file to upload')
file_upload_parser.add_argument('metadata', location='form', type=str, help='Optional metadata as JSON string')

# Health Check Endpoints
@ns_health.route('/')
class HealthCheck(Resource):
    @ns_health.doc('health_check')
    @ns_health.marshal_with(health_response_model)
    @ns_health.response(200, 'Success', health_response_model)
    @ns_health.response(500, 'Service Unavailable', error_model)
    def get(self):
        """Check service health and connectivity"""
        try:
            test_result = embedding_service.test_connection()
            return {
                "status": "healthy",
                "services": {
                    "gemini_api": test_result.get("gemini", False),
                    "chroma_db": test_result.get("chroma", False)
                }
            }, 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"error": str(e)}, 500

# Embedding Endpoints
@ns_embed.route('/')
class GenerateEmbedding(Resource):
    @ns_embed.doc('generate_embedding')
    @ns_embed.expect(embed_request_model, validate=True)
    @ns_embed.marshal_with(embed_response_model)
    @ns_embed.response(200, 'Success', embed_response_model)
    @ns_embed.response(400, 'Bad Request', error_model)
    @ns_embed.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Generate embedding for given text"""
        try:
            data = request.json
            text = data['text'].strip()
            
            if not text:
                return {"error": "Text cannot be empty"}, 400
            
            embedding = embedding_service.generate_embedding(text)
            
            if embedding is None:
                return {"error": "Failed to generate embedding"}, 500
            
            return {
                "text": text,
                "embedding": embedding.tolist(),
                "dimension": len(embedding)
            }, 200
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return {"error": "Internal server error"}, 500

# Document Management Endpoints
@ns_docs.route('/text')
class AddTextDocument(Resource):
    @ns_docs.doc('add_text_document')
    @ns_docs.expect(add_text_document_model, validate=True)
    @ns_docs.marshal_with(add_document_response_model)
    @ns_docs.response(201, 'Document Added', add_document_response_model)
    @ns_docs.response(400, 'Bad Request', error_model)
    @ns_docs.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Add text document to vector database"""
        try:
            data = request.json
            text = data['text'].strip()
            metadata = data.get('metadata', {})
            
            if not text:
                return {"error": "Text cannot be empty"}, 400
            
            # Add source type to metadata
            metadata['source_type'] = 'text'
            
            doc_id = embedding_service.add_document(text, metadata)
            
            if doc_id is None:
                return {"error": "Failed to add document"}, 500
            
            return {
                "document_id": doc_id,
                "text": text,
                "metadata": metadata,
                "message": "Text document added successfully"
            }, 201
            
        except Exception as e:
            logger.error(f"Error adding text document: {e}")
            return {"error": "Internal server error"}, 500

@ns_docs.route('/pdf')
class AddPDFDocument(Resource):
    @ns_docs.doc('add_pdf_document')
    @ns_docs.expect(file_upload_parser)
    @ns_docs.response(201, 'PDF Document Added Successfully')
    @ns_docs.response(400, 'Bad Request - Invalid file or format', error_model)
    @ns_docs.response(413, 'File too large', error_model)
    @ns_docs.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Upload and add PDF document to vector database"""
        try:
            # Check if file is present
            if 'file' not in request.files:
                return {"error": "No file provided"}, 400
            
            file = request.files['file']
            if file.filename == '':
                return {"error": "No file selected"}, 400
            
            # Get optional metadata
            metadata_str = request.form.get('metadata', '{}')
            try:
                metadata = json.loads(metadata_str) if metadata_str else {}
            except json.JSONDecodeError:
                return {"error": "Invalid metadata JSON format"}, 400
            
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                return {"error": "Only PDF files are supported"}, 400
            
            # Read file content
            file_content = file.read()
            
            # Validate PDF content
            if not pdf_extractor.validate_pdf_file(file_content):
                return {"error": "Invalid PDF file"}, 400
            
            # Extract text from PDF
            try:
                extraction_result = pdf_extractor.extract_text_from_bytes(
                    file_content, 
                    secure_filename(file.filename)
                )
            except ValueError as ve:
                return {"error": str(ve)}, 400
            except Exception as e:
                logger.error(f"PDF extraction error: {e}")
                return {"error": "Failed to extract text from PDF"}, 500
            
            # Flatten PDF metadata for Chroma compatibility
            pdf_metadata = extraction_result['metadata']
            
            # Flatten nested pdf_metadata to top-level keys with prefix
            nested_metadata = pdf_metadata.pop('pdf_metadata', {})
            for key, value in nested_metadata.items():
                # Only include non-empty values and convert to string
                if value:
                    pdf_metadata[f'pdf_{key}'] = str(value)
            
            # Merge with user metadata (user metadata takes precedence)
            pdf_metadata.update(metadata)
            
            # Add document to vector database
            doc_id = embedding_service.add_document(
                extraction_result['text'], 
                pdf_metadata
            )
            
            if doc_id is None:
                return {"error": "Failed to add document to vector database"}, 500
            
            # Prepare response
            response = {
                "document_id": doc_id,
                "text": extraction_result['text'][:500] + "..." if len(extraction_result['text']) > 500 else extraction_result['text'],
                "metadata": pdf_metadata,
                "message": "PDF document processed and added successfully",
                "extraction_info": {
                    "pages_processed": pdf_metadata['page_count'],
                    "total_characters": pdf_metadata['char_count'],
                    "total_words": pdf_metadata['word_count'],
                    "file_size_mb": round(pdf_metadata['file_size_bytes'] / (1024*1024), 2)
                }
            }
            
            logger.info(f"Successfully processed PDF: {pdf_metadata['filename']}")
            return response, 201
            
        except Exception as e:
            logger.error(f"Error processing PDF upload: {e}")
            return {"error": "Internal server error"}, 500

# Keep the original /documents/ endpoint for backward compatibility
@ns_docs.route('/')
class AddDocument(Resource):
    @ns_docs.doc('add_document_legacy', description='Legacy endpoint - use /text or /pdf instead')
    @ns_docs.expect(add_text_document_model, validate=True)
    @ns_docs.marshal_with(add_document_response_model)
    @ns_docs.response(201, 'Document Added', add_document_response_model)
    @ns_docs.response(400, 'Bad Request', error_model)
    @ns_docs.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Add text document to vector database (legacy endpoint)"""
        try:
            data = request.json
            text = data['text'].strip()
            metadata = data.get('metadata', {})
            
            if not text:
                return {"error": "Text cannot be empty"}, 400
            
            metadata['source_type'] = 'text'
            
            doc_id = embedding_service.add_document(text, metadata)
            
            if doc_id is None:
                return {"error": "Failed to add document"}, 500
            
            return {
                "document_id": doc_id,
                "text": text,
                "metadata": metadata,
                "message": "Document added successfully"
            }, 201
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return {"error": "Internal server error"}, 500

# Search Endpoints
@ns_search.route('/')
class SimilaritySearch(Resource):
    @ns_search.doc('similarity_search')
    @ns_search.expect(search_request_model, validate=True)
    @ns_search.marshal_with(search_response_model)
    @ns_search.response(200, 'Success', search_response_model)
    @ns_search.response(400, 'Bad Request', error_model)
    @ns_search.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Perform similarity search in vector database"""
        try:
            data = request.json
            query = data['query'].strip()
            k = data.get('k', 5)
            
            if not query:
                return {"error": "Query cannot be empty"}, 400
            
            if not isinstance(k, int) or k <= 0:
                return {"error": "k must be a positive integer"}, 400
            
            results = embedding_service.search_similar(query, k)
            
            return {
                "query": query,
                "results": results,
                "count": len(results)
            }, 200
            
        except Exception as e:
            logger.error(f"Error in similarity search: {e}")
            return {"error": "Internal server error"}, 500

# Collection Management Endpoints
@ns_collection.route('/info')
class CollectionInfo(Resource):
    @ns_collection.doc('collection_info')
    @ns_collection.marshal_with(collection_info_model)
    @ns_collection.response(200, 'Success', collection_info_model)
    @ns_collection.response(500, 'Internal Server Error', error_model)
    def get(self):
        """Get collection information and statistics"""
        try:
            info = embedding_service.get_collection_info()
            return info, 200
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"error": "Internal server error"}, 500

@ns_collection.route('/reset')
class ResetCollection(Resource):
    @ns_collection.doc('reset_collection')
    @ns_collection.response(200, 'Collection reset successfully')
    @ns_collection.response(500, 'Failed to reset collection', error_model)
    def post(self):
        """Reset the collection (delete all documents)"""
        try:
            success = embedding_service.reset_collection()
            
            if success:
                return {"message": "Collection reset successfully"}, 200
            else:
                return {"error": "Failed to reset collection"}, 500
                
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return {"error": "Internal server error"}, 500

# Cache Management Endpoints
@ns_cache.route('/stats')
class CacheStats(Resource):
    @ns_cache.doc('cache_stats')
    @ns_cache.marshal_with(cache_stats_model)
    @ns_cache.response(200, 'Success', cache_stats_model)
    @ns_cache.response(500, 'Internal Server Error', error_model)
    def get(self):
        """Get cache statistics and performance metrics"""
        try:
            stats = embedding_service.get_cache_stats()
            return stats, 200
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": "Internal server error"}, 500

@ns_cache.route('/clear')
class ClearCache(Resource):
    @ns_cache.doc('clear_cache')
    @ns_cache.response(200, 'Cache cleared successfully')
    @ns_cache.response(500, 'Internal Server Error', error_model)
    def post(self):
        """Clear the embedding cache"""
        try:
            embedding_service.clear_cache()
            return {"message": "Cache cleared successfully"}, 200
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"error": "Internal server error"}, 500

# Error handlers
@api.errorhandler
def default_error_handler(error):
    """Default error handler"""
    return {"error": "Internal server error"}, 500

@app.errorhandler(413)
def file_too_large(error):
    """Handle file too large error"""
    return {"error": "File too large. Maximum size: 50MB"}, 413

if __name__ == '__main__':
    logger.info("Starting Embedding Service API...")
    logger.info("Swagger UI available at: http://127.0.0.1:5000/docs/")
    logger.info("PDF Upload endpoint: POST /api/v1/documents/pdf")
    logger.info("Text Upload endpoint: POST /api/v1/documents/text")
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )