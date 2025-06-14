import re
import shutil
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

class FileProcessor:
    def __init__(self, base_output_dir="audiobooks"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
    
    def create_output_directory(self, book_name, force_create=False):
        """Create a directory for the book output."""
        # Clean the book name to make it filesystem-safe
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', book_name)
        output_dir = self.base_output_dir / safe_name
        
        # Check if directory exists
        if output_dir.exists() and not force_create:
            return output_dir, safe_name, True  # Return True to indicate directory exists
        else:
            if output_dir.exists():
                # Remove existing directory and its contents
                shutil.rmtree(output_dir)
            output_dir.mkdir(exist_ok=True)
            # Create images subdirectory
            images_dir = output_dir / "images"
            images_dir.mkdir(exist_ok=True)
            return output_dir, safe_name, False  # Return False to indicate new directory
    
    def extract_text_from_epub(self, epub_path):
        """Extract text from EPUB file preserving document order and paragraph structure."""
        try:
            book = epub.read_epub(epub_path)
            
            # Build a map from spine IDs to items for quick lookup
            id_map = {item.get_id(): item for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}
            
            paragraphs = []
            # Process items in spine order to maintain reading sequence
            for spine_id, _ in book.spine:
                item = id_map.get(spine_id)
                if not item:
                    continue
                    
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                
                # Process elements in document order, preserving the sequence of headings and paragraphs
                for elem in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                    # Get text while preserving paragraph structure
                    text = elem.get_text(separator=' ', strip=True)
                    if text:
                        # Add extra newline for headings to ensure they start new paragraphs
                        if elem.name.startswith('h'):
                            paragraphs.append('\n' + text + '\n')
                        else:
                            paragraphs.append(text)
            
            # Join paragraphs with double newlines to create clear paragraph breaks
            text = '\n\n'.join(paragraphs)
            
            # Clean up any excessive whitespace within paragraphs
            text = re.sub(r'[ \t]+', ' ', text)  # Normalize spaces within lines
            text = re.sub(r'\n{3,}', '\n\n', text)  # Remove excessive paragraph breaks
            text = text.strip()
            
            return text
            
        except Exception as e:
            print(f"Error extracting text from EPUB: {str(e)}")
            return ""
    
    def extract_images_from_epub(self, epub_path, output_dir):
        """Extract images from EPUB file and save them to the output directory."""
        book = epub.read_epub(epub_path)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                # Get the filename from the path and clean it
                filename = Path(item.get_name()).name
                # Create a safe filename by removing any problematic characters
                safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                image_path = images_dir / safe_filename
                try:
                    with open(image_path, 'wb') as f:
                        f.write(item.get_content())
                except Exception as e:
                    print(f"Warning: Could not save image {filename}: {str(e)}")
    
    def get_existing_audio_files(self, output_dir):
        """Get list of existing audio files in the output directory."""
        if not output_dir or not output_dir.exists():
            return []
        # Get all wav files and sort them by section number
        audio_files = []
        for file in output_dir.glob("section_*.wav"):
            try:
                section_num = int(file.stem.split('_')[1])
                audio_files.append((section_num, str(file)))
            except (ValueError, IndexError):
                continue
        # Sort by section number and return just the file paths
        return [file for _, file in sorted(audio_files)]
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file preserving document structure."""
        try:
            reader = PdfReader(pdf_path)
            text = []
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
            
            # Join all pages with double newlines to create clear page breaks
            full_text = '\n\n'.join(text)
            
            # Clean up any excessive whitespace
            full_text = re.sub(r'[ \t]+', ' ', full_text)  # Normalize spaces within lines
            full_text = re.sub(r'\n{3,}', '\n\n', full_text)  # Remove excessive paragraph breaks
            full_text = full_text.strip()
            
            return full_text
            
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def read_text_file(self, file_path):
        """Read content from a text file."""
        file_path = Path(file_path)
        
        # Handle different file types
        if file_path.suffix.lower() == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_path.suffix.lower() == '.epub':
            return self.extract_text_from_epub(file_path)
        else:
            # Default to reading as text file
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read() 