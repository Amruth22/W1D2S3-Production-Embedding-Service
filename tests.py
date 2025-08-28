import pytest
import asyncio
import httpx
import json
import io
from typing import Dict, Any

BASE_URL = "http://localhost:8081/api/v1"

@pytest.mark.asyncio
async def test_health_check():
    """Test that the Embedding Service API is running and accessible"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "gemini_api" in data["services"]
        assert "chroma_db" in data["services"]
        print("PASS: Health check passed")

@pytest.mark.asyncio
async def test_generate_embedding():
    """Test embedding generation functionality"""
    async with httpx.AsyncClient() as client:
        embed_data = {
            "text": "The lighthouse keeper watched over ships in the stormy night."
        }
        
        response = await client.post(f"{BASE_URL}/embed/", json=embed_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "text" in data
        assert "embedding" in data
        assert "dimension" in data
        assert data["text"] == embed_data["text"]
        assert isinstance(data["embedding"], list)
        assert len(data["embedding"]) == data["dimension"]
        assert data["dimension"] > 0
        
        # Check if embedding values are numeric
        for value in data["embedding"][:5]:
            assert isinstance(value, (int, float))
        
        print("PASS: Generate embedding test passed")

@pytest.mark.asyncio
async def test_embedding_validation():
    """Test embedding request validation"""
    async with httpx.AsyncClient() as client:
        # Test empty text
        invalid_data = {"text": ""}
        response = await client.post(f"{BASE_URL}/embed/", json=invalid_data)
        assert response.status_code == 400
        
        # Test missing text field
        response = await client.post(f"{BASE_URL}/embed/", json={})
        assert response.status_code == 400
        
        # Test whitespace only text
        whitespace_data = {"text": "   "}
        response = await client.post(f"{BASE_URL}/embed/", json=whitespace_data)
        assert response.status_code == 400
        
        print("PASS: Embedding validation test passed")

@pytest.mark.asyncio
async def test_add_text_document():
    """Test adding text documents to the vector database"""
    async with httpx.AsyncClient() as client:
        doc_data = {
            "text": "The ancient lighthouse stood tall against the crashing waves, guiding ships safely to shore.",
            "metadata": {
                "category": "maritime",
                "theme": "lighthouse",
                "test_type": "async_text_ingestion"
            }
        }
        
        response = await client.post(f"{BASE_URL}/documents/text", json=doc_data)
        assert response.status_code == 201
        data = response.json()
        
        assert "document_id" in data
        assert "message" in data
        assert data["text"] == doc_data["text"]
        assert data["metadata"]["source_type"] == "text"
        assert data["metadata"]["category"] == "maritime"
        
        print(f"PASS: Add text document test passed (ID: {data['document_id']})")

@pytest.mark.asyncio
async def test_add_text_document_validation():
    """Test text document validation"""
    async with httpx.AsyncClient() as client:
        # Test empty text
        invalid_doc = {"text": "", "metadata": {}}
        response = await client.post(f"{BASE_URL}/documents/text", json=invalid_doc)
        assert response.status_code == 400
        
        # Test missing text field
        response = await client.post(f"{BASE_URL}/documents/text", json={"metadata": {}})
        assert response.status_code == 400
        
        print("PASS: Text document validation test passed")

@pytest.mark.asyncio
async def test_add_pdf_document():
    """Test adding PDF documents via file upload"""
    async with httpx.AsyncClient() as client:
        # Create a simple test PDF content
        pdf_content = _create_test_pdf_content()
        
        files = {
            'file': ('test_document.pdf', io.BytesIO(pdf_content), 'application/pdf')
        }
        data = {
            'metadata': json.dumps({
                "category": "test_pdf",
                "source": "async_unit_test",
                "test_type": "pdf_ingestion"
            })
        }
        
        response = await client.post(f"{BASE_URL}/documents/pdf", files=files, data=data)
        assert response.status_code == 201
        result = response.json()
        
        assert "document_id" in result
        assert "message" in result
        assert "extraction_info" in result
        assert result["metadata"]["source_type"] == "pdf"
        assert result["metadata"]["filename"] == "test_document.pdf"
        
        extraction_info = result["extraction_info"]
        assert "pages_processed" in extraction_info
        assert "total_characters" in extraction_info
        assert "total_words" in extraction_info
        
        print(f"PASS: Add PDF document test passed (ID: {result['document_id']})")

@pytest.mark.asyncio
async def test_pdf_upload_validation():
    """Test PDF upload validation"""
    async with httpx.AsyncClient() as client:
        # Test non-PDF file
        files = {
            'file': ('test.txt', io.BytesIO(b'This is not a PDF'), 'text/plain')
        }
        
        response = await client.post(f"{BASE_URL}/documents/pdf", files=files)
        assert response.status_code == 400
        
        # Test no file provided
        response = await client.post(f"{BASE_URL}/documents/pdf", files={})
        assert response.status_code == 400
        
        print("PASS: PDF upload validation test passed")

@pytest.mark.asyncio
async def test_similarity_search():
    """Test similarity search functionality"""
    async with httpx.AsyncClient() as client:
        # First, add a document to search against
        doc_data = {
            "text": "The old lighthouse keeper maintained the beacon that guided sailors through dangerous waters.",
            "metadata": {"category": "maritime", "test_type": "search_test"}
        }
        
        await client.post(f"{BASE_URL}/documents/text", json=doc_data)
        
        # Now perform similarity search
        search_data = {
            "query": "lighthouse beacon sailors navigation",
            "k": 3
        }
        
        response = await client.post(f"{BASE_URL}/search/", json=search_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "query" in data
        assert "results" in data
        assert "count" in data
        assert data["query"] == search_data["query"]
        assert isinstance(data["results"], list)
        assert data["count"] >= 0
        
        # If results exist, validate structure
        if data["count"] > 0:
            result = data["results"][0]
            assert "id" in result
            assert "text" in result
            assert "metadata" in result
            assert "distance" in result
            assert "similarity_score" in result
            
            # Validate similarity score range
            assert 0 <= result["similarity_score"] <= 1
        
        print(f"PASS: Similarity search test passed (found {data['count']} results)")

@pytest.mark.asyncio
async def test_search_validation():
    """Test search request validation"""
    async with httpx.AsyncClient() as client:
        # Test empty query
        invalid_search = {"query": "", "k": 5}
        response = await client.post(f"{BASE_URL}/search/", json=invalid_search)
        assert response.status_code == 400
        
        # Test invalid k value
        invalid_k = {"query": "test query", "k": -1}
        response = await client.post(f"{BASE_URL}/search/", json=invalid_k)
        assert response.status_code == 400
        
        # Test non-integer k
        invalid_k2 = {"query": "test query", "k": "invalid"}
        response = await client.post(f"{BASE_URL}/search/", json=invalid_k2)
        assert response.status_code == 400
        
        print("PASS: Search validation test passed")

@pytest.mark.asyncio
async def test_collection_management():
    """Test collection information and management"""
    async with httpx.AsyncClient() as client:
        # Get collection info
        response = await client.get(f"{BASE_URL}/collection/info")
        assert response.status_code == 200
        data = response.json()
        
        assert "collection_name" in data
        assert "document_count" in data
        assert "embedding_dimension" in data
        assert "model" in data
        assert data["model"] == "gemini-embedding-001"
        assert isinstance(data["document_count"], int)
        assert data["document_count"] >= 0
        
        print(f"PASS: Collection info test passed (documents: {data['document_count']})")

@pytest.mark.asyncio
async def test_cache_management():
    """Test cache statistics and management"""
    async with httpx.AsyncClient() as client:
        # Get cache stats
        response = await client.get(f"{BASE_URL}/cache/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "cache_hits" in data
        assert "cache_misses" in data
        assert "cache_size" in data
        assert "cache_maxsize" in data
        assert "hit_rate" in data
        
        assert isinstance(data["cache_hits"], int)
        assert isinstance(data["cache_misses"], int)
        assert isinstance(data["cache_size"], int)
        assert isinstance(data["hit_rate"], (int, float))
        assert 0 <= data["hit_rate"] <= 1
        
        # Test cache clearing
        clear_response = await client.post(f"{BASE_URL}/cache/clear")
        assert clear_response.status_code == 200
        clear_data = clear_response.json()
        assert "message" in clear_data
        
        print("PASS: Cache management test passed")

@pytest.mark.asyncio
async def test_cache_functionality():
    """Test cache hit/miss functionality"""
    async with httpx.AsyncClient() as client:
        # Get initial cache stats
        initial_response = await client.get(f"{BASE_URL}/cache/stats")
        initial_stats = initial_response.json()
        initial_hits = initial_stats["cache_hits"]
        
        # Generate embedding for same text multiple times
        test_text = {"text": "Cache test text for embedding validation"}
        
        # First request (likely cache miss)
        response1 = await client.post(f"{BASE_URL}/embed/", json=test_text)
        assert response1.status_code == 200
        
        # Second request (should be cache hit)
        response2 = await client.post(f"{BASE_URL}/embed/", json=test_text)
        assert response2.status_code == 200
        
        # Verify responses are identical
        result1 = response1.json()
        result2 = response2.json()
        assert result1["embedding"] == result2["embedding"]
        
        # Check cache stats improved
        final_response = await client.get(f"{BASE_URL}/cache/stats")
        final_stats = final_response.json()
        
        # Cache hits should have increased
        assert final_stats["cache_hits"] >= initial_hits
        
        print("PASS: Cache functionality test passed")

@pytest.mark.asyncio
async def test_legacy_document_endpoint():
    """Test legacy document endpoint for backward compatibility"""
    async with httpx.AsyncClient() as client:
        doc_data = {
            "text": "Legacy endpoint test document for backward compatibility.",
            "metadata": {"test_type": "legacy_endpoint"}
        }
        
        response = await client.post(f"{BASE_URL}/documents/", json=doc_data)
        assert response.status_code == 201
        data = response.json()
        
        assert "document_id" in data
        assert "message" in data
        assert data["metadata"]["source_type"] == "text"
        
        print("PASS: Legacy document endpoint test passed")

@pytest.mark.asyncio
async def test_collection_reset():
    """Test collection reset functionality"""
    async with httpx.AsyncClient() as client:
        # Add a test document first
        doc_data = {
            "text": "Document to be deleted during reset test.",
            "metadata": {"test_type": "reset_test"}
        }
        
        await client.post(f"{BASE_URL}/documents/text", json=doc_data)
        
        # Get initial count
        info_response = await client.get(f"{BASE_URL}/collection/info")
        initial_info = info_response.json()
        initial_count = initial_info["document_count"]
        
        # Reset collection
        reset_response = await client.post(f"{BASE_URL}/collection/reset")
        assert reset_response.status_code == 200
        reset_data = reset_response.json()
        assert "message" in reset_data
        
        # Verify collection is empty
        final_info_response = await client.get(f"{BASE_URL}/collection/info")
        final_info = final_info_response.json()
        assert final_info["document_count"] == 0
        
        print(f"PASS: Collection reset test passed (cleared {initial_count} documents)")

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent API operations"""
    async with httpx.AsyncClient() as client:
        # Create multiple concurrent embedding requests
        texts = [
            {"text": f"Concurrent test text number {i} for performance testing."}
            for i in range(5)
        ]
        
        # Execute concurrent requests
        tasks = [
            client.post(f"{BASE_URL}/embed/", json=text_data)
            for text_data in texts
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for i, response in enumerate(responses):
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == texts[i]["text"]
            assert "embedding" in data
        
        print("PASS: Concurrent operations test passed")

@pytest.mark.asyncio
async def test_error_handling():
    """Test API error handling"""
    async with httpx.AsyncClient() as client:
        # Test invalid JSON
        response = await client.post(
            f"{BASE_URL}/embed/",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        
        # Test unsupported content type
        response = await client.post(
            f"{BASE_URL}/embed/",
            content="text data",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code in [400, 415]  # Bad Request or Unsupported Media Type
        
        print("PASS: Error handling test passed")

def _create_test_pdf_content() -> bytes:
    """Create simple PDF content for testing"""
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
/Length 55
>>
stream
BT
/F1 12 Tf
72 720 Td
(Async Test PDF Content) Tj
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
408
%%EOF'''
    return pdf_content

async def run_all_tests():
    """Run all async tests concurrently for faster execution"""
    print("Running async API tests for Production Embedding Service...")
    print("Server should be running at: http://localhost:8081")
    print("=" * 70)
    
    # List of all test functions
    test_functions = [
        test_health_check(),
        test_generate_embedding(),
        test_embedding_validation(),
        test_add_text_document(),
        test_add_text_document_validation(),
        test_add_pdf_document(),
        test_pdf_upload_validation(),
        test_similarity_search(),
        test_search_validation(),
        test_collection_management(),
        test_cache_management(),
        test_cache_functionality(),
        test_legacy_document_endpoint(),
        test_concurrent_operations(),
        test_error_handling(),
        # Note: collection_reset test is run separately to avoid interfering with other tests
    ]
    
    try:
        # Run most tests concurrently
        await asyncio.gather(*test_functions)
        
        # Run collection reset test separately
        await test_collection_reset()
        
        print("=" * 70)
        print("🎉 All async API tests passed!")
        print("✅ Embedding Service is working correctly")
        return True
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Production Embedding Service Async Tests")
    print("📋 Make sure the API server is running: python app.py")
    print("🔧 Ensure your .env file has GEMINI_API_KEY configured")
    print()
    
    # Run the async tests
    result = asyncio.run(run_all_tests())
    exit(0 if result else 1)