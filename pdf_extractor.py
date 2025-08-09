import fitz  # PyMuPDF
import logging
from typing import Dict, Optional
import os
import tempfile

logger = logging.getLogger(__name__)


class PDFExtractor:
    """PDF text extraction utility using PyMuPDF"""
    
    def __init__(self):
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit
        self.supported_formats = ['.pdf']
    
    def extract_text_from_file(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from PDF file
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            Dict containing extracted text and metadata
        """
        try:
            # Check file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                raise ValueError(f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB")
            
            # Check file extension
            _, ext = os.path.splitext(file_path.lower())
            if ext not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {ext}. Supported: {self.supported_formats}")
            
            # Open PDF and extract text
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = doc.metadata
            page_count = doc.page_count
            
            # Extract text from all pages
            full_text = ""
            pages_text = []
            
            for page_num in range(page_count):
                page = doc[page_num]
                page_text = page.get_text()
                pages_text.append({
                    "page_number": page_num + 1,
                    "text": page_text.strip(),
                    "char_count": len(page_text)
                })
                full_text += page_text + "\n"
            
            # Close document
            doc.close()
            
            # Clean up text
            full_text = self._clean_text(full_text)
            
            if not full_text.strip():
                raise ValueError("No text content found in PDF")
            
            result = {
                "text": full_text,
                "metadata": {
                    "source_type": "pdf",
                    "filename": os.path.basename(file_path),
                    "file_size_bytes": file_size,
                    "page_count": page_count,
                    "char_count": len(full_text),
                    "word_count": len(full_text.split()),
                    "pdf_metadata": {
                        "title": metadata.get("title", ""),
                        "author": metadata.get("author", ""),
                        "subject": metadata.get("subject", ""),
                        "creator": metadata.get("creator", ""),
                        "producer": metadata.get("producer", ""),
                        "creation_date": metadata.get("creationDate", ""),
                        "modification_date": metadata.get("modDate", "")
                    }
                },
                "pages": pages_text
            }
            
            logger.info(f"Successfully extracted text from PDF: {os.path.basename(file_path)}")
            logger.info(f"Pages: {page_count}, Characters: {len(full_text)}, Words: {len(full_text.split())}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            raise
    
    def extract_text_from_bytes(self, pdf_bytes: bytes, filename: str = "document.pdf") -> Dict[str, any]:
        """
        Extract text from PDF bytes
        
        Args:
            pdf_bytes (bytes): PDF file content as bytes
            filename (str): Original filename for metadata
            
        Returns:
            Dict containing extracted text and metadata
        """
        try:
            # Check file size
            file_size = len(pdf_bytes)
            if file_size > self.max_file_size:
                raise ValueError(f"File too large. Maximum size: {self.max_file_size / (1024*1024):.1f}MB")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Extract using file path method
                result = self.extract_text_from_file(temp_file_path)
                
                # Update filename in metadata
                result["metadata"]["filename"] = filename
                result["metadata"]["file_size_bytes"] = file_size
                
                return result
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error extracting text from PDF bytes: {e}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line:  # Skip empty lines
                lines.append(line)
        
        # Join with single newlines
        cleaned_text = '\n'.join(lines)
        
        # Replace multiple spaces with single space
        import re
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        
        return cleaned_text
    
    def validate_pdf_file(self, file_content: bytes) -> bool:
        """
        Validate if file content is a valid PDF
        
        Args:
            file_content (bytes): File content to validate
            
        Returns:
            bool: True if valid PDF, False otherwise
        """
        try:
            # Check PDF magic number
            if not file_content.startswith(b'%PDF-'):
                return False
            
            # Try to open with PyMuPDF
            doc = fitz.open(stream=file_content, filetype="pdf")
            page_count = doc.page_count
            doc.close()
            
            return page_count > 0
            
        except Exception:
            return False
    
    def get_pdf_info(self, file_content: bytes) -> Dict[str, any]:
        """
        Get basic PDF information without full text extraction
        
        Args:
            file_content (bytes): PDF file content
            
        Returns:
            Dict with basic PDF information
        """
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            
            metadata = doc.metadata
            page_count = doc.page_count
            
            # Get first page text preview
            preview_text = ""
            if page_count > 0:
                first_page = doc[0]
                page_text = first_page.get_text()
                preview_text = page_text[:200] + "..." if len(page_text) > 200 else page_text
            
            doc.close()
            
            return {
                "page_count": page_count,
                "file_size": len(file_content),
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "preview": preview_text.strip()
            }
            
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
            return {}