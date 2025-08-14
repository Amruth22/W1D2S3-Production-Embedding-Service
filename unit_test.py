import unittest
import requests
import json
import time
import os
import tempfile
import io
from typing import Dict, Any
import numpy as np

# Fix for SQLite3 compatibility with ChromaDB
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

# Import existing modules for testing
from embedding_service import EmbeddingService
from pdf_extractor import PDFExtractor
from config import Config

class TestEmbeddingService(unittest.TestCase):
    """Comprehensive unit tests for the embedding service"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://127.0.0.1:8081/api/v1"
        cls.embedding_service = EmbeddingService()
        cls.pdf_extractor = PDFExtractor()
        cls.sample_text = "The lighthouse keeper watched over ships in the stormy night."
        cls.sample_query = "lighthouse and sea stories"
        
        # Wait for API to be ready
        print("\n🔧 Setting up test environment...")
        cls._wait_for_api()
    
    @classmethod
    def _wait_for_api(cls, timeout=30):
        """Wait for API server to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{cls.base_url}/health/", timeout=2)
                if response.status_code == 200:
                    print("✅ API server is ready")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        raise RuntimeError("API server not available. Please start: python app.py")
    
    def test_01_api_key_validation(self):
        """Test Case 1: Validate API keys and connections"""
        print("\n🔑 Testing API Key Validation...")
        
        # Test Gemini API key configuration
        self.assertIsNotNone(os.getenv('GEMINI_API_KEY'), "GEMINI_API_KEY not configured")
        
        # Test service connection through health endpoint
        response = requests.get(f"{self.base_url}/health/")
        self.assertEqual(response.status_code, 200)
        
        health_data = response.json()
        self.assertEqual(health_data['status'], 'healthy')
        self.assertTrue(health_data['services']['gemini_api'], "Gemini API connection failed")
        self.assertTrue(health_data['services']['chroma_db'], "Chroma DB connection failed")
        
        # Test direct service connection
        test_result = self.embedding_service.test_connection()
        self.assertTrue(test_result.get('gemini', False), "Direct Gemini connection failed")
        self.assertTrue(test_result.get('chroma', False), "Direct Chroma connection failed")
        
        print("✅ API key validation passed")
    
    def test_02_gemini_embedding_response(self):
        """Test Case 2: Validate Gemini embedding response"""
        print("\n🧠 Testing Gemini Embedding Response...")
        
        # Test embedding generation via API
        embed_data = {"text": self.sample_text}
        response = requests.post(f"{self.base_url}/embed/", json=embed_data)
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        
        # Validate response structure
        self.assertIn('text', result)
        self.assertIn('embedding', result)
        self.assertIn('dimension', result)
        
        # Validate embedding properties
        embedding = result['embedding']
        self.assertIsInstance(embedding, list, "Embedding should be a list")
        self.assertGreater(len(embedding), 0, "Embedding should not be empty")
        self.assertEqual(len(embedding), result['dimension'], "Dimension mismatch")
        
        # Check if all values are floats
        for value in embedding[:5]:  # Check first 5 values
            self.assertIsInstance(value, (int, float), "Embedding values should be numeric")
        
        # Test direct service method
        direct_embedding = self.embedding_service.generate_embedding(self.sample_text)
        self.assertIsNotNone(direct_embedding, "Direct embedding generation failed")
        self.assertIsInstance(direct_embedding, np.ndarray, "Direct embedding should be numpy array")
        
        print(f"✅ Gemini embedding response validated (dimension: {result['dimension']})")
    
    def test_03_chroma_setup_validation(self):
        """Test Case 3: Validate Chroma setup and configuration"""
        print("\n🗄️ Testing Chroma Setup Validation...")
        
        # Test collection info via API
        response = requests.get(f"{self.base_url}/collection/info")
        self.assertEqual(response.status_code, 200)
        
        collection_info = response.json()
        self.assertIn('collection_name', collection_info)
        self.assertIn('document_count', collection_info)
        self.assertIn('embedding_dimension', collection_info)
        self.assertIn('model', collection_info)
        
        # Validate collection configuration
        self.assertEqual(collection_info['model'], 'gemini-embedding-001')
        self.assertGreaterEqual(collection_info['document_count'], 0)
        
        # Test direct service collection access
        info = self.embedding_service.get_collection_info()
        self.assertIsInstance(info, dict, "Collection info should be a dictionary")
        self.assertIn('collection_name', info)
        
        print(f"✅ Chroma setup validated (collection: {collection_info['collection_name']})")
    
    def test_04_document_ingestion_text(self):
        """Test Case 4a: Test text document ingestion"""
        print("\n📝 Testing Text Document Ingestion...")
        
        # Test text document upload
        text_data = {
            "text": self.sample_text,
            "metadata": {
                "category": "test_story",
                "source": "unit_test",
                "test_type": "text_ingestion"
            }
        }
        
        response = requests.post(f"{self.base_url}/documents/text", json=text_data)
        self.assertEqual(response.status_code, 201)
        
        result = response.json()
        self.assertIn('document_id', result)
        self.assertIn('message', result)
        self.assertEqual(result['text'], self.sample_text)
        self.assertEqual(result['metadata']['source_type'], 'text')
        
        # Store document ID for later tests
        self.text_doc_id = result['document_id']
        
        print(f"✅ Text document ingested successfully (ID: {self.text_doc_id})")
    
    def test_04_document_ingestion_pdf(self):
        """Test Case 4b: Test PDF document ingestion"""
        print("\n📄 Testing PDF Document Ingestion...")
        
        # Create a simple test PDF content
        pdf_content = self._create_test_pdf_content()
        
        # Test PDF upload
        files = {'file': ('test_document.pdf', io.BytesIO(pdf_content), 'application/pdf')}
        data = {'metadata': json.dumps({"category": "test_pdf", "source": "unit_test"})}
        
        response = requests.post(f"{self.base_url}/documents/pdf", files=files, data=data)
        self.assertEqual(response.status_code, 201)
        
        result = response.json()
        self.assertIn('document_id', result)
        self.assertIn('message', result)
        self.assertIn('extraction_info', result)
        
        # Validate extraction info
        extraction_info = result['extraction_info']
        self.assertIn('pages_processed', extraction_info)
        self.assertIn('total_characters', extraction_info)
        self.assertIn('total_words', extraction_info)
        
        # Store document ID for later tests
        self.pdf_doc_id = result['document_id']
        
        print(f"✅ PDF document ingested successfully (ID: {self.pdf_doc_id})")
    
    def test_05_search_retrieval(self):
        """Test Case 5: Test search retrieval functionality"""
        print("\n🔍 Testing Search Retrieval...")
        
        # Test similarity search
        search_data = {
            "query": self.sample_query,
            "k": 3
        }
        
        response = requests.post(f"{self.base_url}/search/", json=search_data)
        self.assertEqual(response.status_code, 200)
        
        search_result = response.json()
        self.assertIn('query', search_result)
        self.assertIn('results', search_result)
        self.assertIn('count', search_result)
        
        # Validate search results structure
        if search_result['count'] > 0:
            result = search_result['results'][0]
            self.assertIn('id', result)
            self.assertIn('text', result)
            self.assertIn('metadata', result)
            self.assertIn('distance', result)
            self.assertIn('similarity_score', result)
            
            # Validate similarity score range (0-1)
            self.assertGreaterEqual(result['similarity_score'], 0)
            self.assertLessEqual(result['similarity_score'], 1)
        
        # Test direct service search
        direct_results = self.embedding_service.search_similar(self.sample_query, 2)
        self.assertIsInstance(direct_results, list, "Direct search should return a list")
        
        print(f"✅ Search retrieval validated (found {search_result['count']} results)")
    
    def test_06_chroma_index_storage(self):
        """Test Case 6: Test Chroma index storage and persistence"""
        print("\n💾 Testing Chroma Index Storage...")
        
        # Get collection info to check document count
        response = requests.get(f"{self.base_url}/collection/info")
        self.assertEqual(response.status_code, 200)
        
        collection_info = response.json()
        initial_count = collection_info['document_count']
        
        # Add a test document
        test_text = "This is a test document for index storage validation."
        text_data = {
            "text": test_text,
            "metadata": {"test_type": "index_storage", "timestamp": str(time.time())}
        }
        
        response = requests.post(f"{self.base_url}/documents/text", json=text_data)
        self.assertEqual(response.status_code, 201)
        
        # Check if document count increased
        response = requests.get(f"{self.base_url}/collection/info")
        updated_info = response.json()
        self.assertEqual(updated_info['document_count'], initial_count + 1)
        
        # Test that document can be found via search
        search_data = {"query": "test document index storage", "k": 1}
        response = requests.post(f"{self.base_url}/search/", json=search_data)
        search_result = response.json()
        
        # Should find at least one result
        self.assertGreater(search_result['count'], 0)
        
        print(f"✅ Chroma index storage validated (documents: {updated_info['document_count']})")
    
    def test_07_cache_functionality(self):
        """Test Case 7: Test cache functionality"""
        print("\n⚡ Testing Cache Functionality...")
        
        # Get initial cache stats
        response = requests.get(f"{self.base_url}/cache/stats")
        self.assertEqual(response.status_code, 200)
        
        initial_stats = response.json()
        self.assertIn('cache_hits', initial_stats)
        self.assertIn('cache_misses', initial_stats)
        self.assertIn('cache_size', initial_stats)
        self.assertIn('hit_rate', initial_stats)
        
        initial_hits = initial_stats['cache_hits']
        initial_misses = initial_stats['cache_misses']
        
        # Generate embedding for same text multiple times to test cache
        test_text = "Cache test text for embedding"
        embed_data = {"text": test_text}
        
        # First request (should be cache miss)
        response1 = requests.post(f"{self.base_url}/embed/", json=embed_data)
        self.assertEqual(response1.status_code, 200)
        
        # Second request (should be cache hit)
        response2 = requests.post(f"{self.base_url}/embed/", json=embed_data)
        self.assertEqual(response2.status_code, 200)
        
        # Check that both responses are identical
        result1 = response1.json()
        result2 = response2.json()
        self.assertEqual(result1['embedding'], result2['embedding'])
        
        # Get updated cache stats
        response = requests.get(f"{self.base_url}/cache/stats")
        updated_stats = response.json()
        
        # Cache hits should have increased
        self.assertGreaterEqual(updated_stats['cache_hits'], initial_hits)
        
        # Test cache clearing
        response = requests.post(f"{self.base_url}/cache/clear")
        self.assertEqual(response.status_code, 200)
        
        # Check cache stats after clearing
        response = requests.get(f"{self.base_url}/cache/stats")
        cleared_stats = response.json()
        
        print(f"✅ Cache functionality validated (hits: {updated_stats['cache_hits']}, misses: {updated_stats['cache_misses']})")
    
    def _create_test_pdf_content(self) -> bytes:
        """Create simple PDF content for testing"""
        # This creates a minimal PDF structure for testing
        # In a real scenario, you might want to use a library like reportlab
        pdf_header = b'%PDF-1.4\n'
        pdf_content = pdf_header + b'''1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 4 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj

4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

5 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test PDF Content) Tj
ET
endstream
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000103 00000 n 
0000000229 00000 n 
0000000299 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
397
%%EOF'''
        return pdf_content

def run_tests():
    """Run all tests with detailed output"""
    print("="*70)
    print("🧪 EMBEDDING SERVICE COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEmbeddingService)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=None,
        descriptions=True,
        failfast=False
    )
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {len(result.failures) + len(result.errors)} TEST(S) FAILED")
    
    print("="*70)
    return result.wasSuccessful()

if __name__ == '__main__':
    print("🚀 Starting Embedding Service Test Suite")
    print("📋 Make sure the API server is running: python app.py")
    print("🔧 Ensure your .env file has GEMINI_API_KEY configured")
    print()
    
    try:
        success = run_tests()
        exit_code = 0 if success else 1
        exit(exit_code)
    except Exception as e:
        print(f"❌ Test suite failed to run: {e}")
        exit(1)