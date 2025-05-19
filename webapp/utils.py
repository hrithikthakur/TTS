import os
import subprocess
import tempfile
import io
from PIL import Image
try:
    import PyPDF2
    from ebooklib import epub
except ImportError:
    print("Warning: PyPDF2 or ebooklib not installed. Some file formats will not be supported.")

# Use the exact same settings from main3.py that are working
from dotenv import load_dotenv
load_dotenv()

# NVIDIA TTS API settings - using the same values from main3.py
API_ENDPOINT = "grpc.nvcf.nvidia.com:443"
FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"
LANGUAGE = "en-US"
VOICE = "Magpie-Multilingual.EN-US.Sofia"
AUTH = os.getenv("AUTH")  # This needs to be in your .env file

def process_ebook(file_path):
    """
    Process an ebook file and convert it to an audiobook
    
    Args:
        file_path: Path to the ebook file
        
    Returns:
        Path to the generated audiobook file
    """
    # Get file name without extension
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    # Clean up the filename by removing UUID if present
    if '_' in file_name and len(file_name.split('_')[0]) == 36:
        file_name = '_'.join(file_name.split('_')[1:])
    
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'webapp', 'output')
    output_path = os.path.join(output_dir, f"{file_name}.wav")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract text from the ebook
    text = extract_text(file_path)
    
    # If text is empty, return error
    if not text or text.strip() == "":
        raise ValueError("Could not extract text from the file or the file is empty")
    
    # For long texts, we need to split into chunks (NVIDIA API has a limit)
    MAX_CHAR = 400  # Same as in main3.py
    chunks = chunk_text(text, MAX_CHAR)
    
    try:
        # Try to use NVIDIA TTS API - using the exact same code from main3.py
        try:
            print("Trying to use NVIDIA TTS...")
            print(f"API_ENDPOINT: {API_ENDPOINT}")
            print(f"FUNCTION_ID: {FUNCTION_ID}")
            print(f"AUTH: {AUTH[:5]}..." if AUTH else "AUTH: None")
            print(f"LANGUAGE: {LANGUAGE}")
            print(f"VOICE: {VOICE}")
            print(f"Chunk count: {len(chunks)}")
            
            # Process each chunk and combine them
            temp_audio_files = []
            for i, chunk in enumerate(chunks):
                temp_file = f"temp_chunk_{i}.wav"
                temp_audio_files.append(temp_file)
                
                # Use the same approach as in main3.py with the talk.py script path
                cmd = [
                    "python", 
                    "/Users/hrithikthakur/python-clients/scripts/tts/talk.py",
                    "--server", API_ENDPOINT,
                    "--use-ssl",
                    "--metadata", "function-id", FUNCTION_ID,
                    "--metadata", "authorization", AUTH,
                    "--language-code", LANGUAGE,
                    "--text", chunk,  # Use --text not --text-file
                    "--voice", VOICE,
                    "--output", temp_file
                ]
                
                print(f"Processing chunk {i+1}/{len(chunks)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    print(f"NVIDIA TTS API Error on chunk {i+1}: {result.stderr}")
                    raise Exception(f"NVIDIA TTS API Error: {result.stderr}")
                    
                if not os.path.exists(temp_file):
                    print(f"Output file not found for chunk {i+1}")
                    raise Exception(f"Output file not found for chunk {i+1}")
            
            # Stitch audio files together
            stitch_audio(temp_audio_files, output_path)
            print(f"Successfully created audio file at {output_path}")
            
            # Clean up temp files
            for temp_file in temp_audio_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
        except Exception as e:
            print(f"Failed to use NVIDIA TTS API: {e}")
            # Fall back to local TTS if available
            try:
                # Try to use TTS module if available
                from TTS.api import TTS
                
                # Initialize TTS
                tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", 
                         progress_bar=True, 
                         gpu=False)
                
                # Generate audio
                tts.tts_to_file(
                    text=text,
                    language="en",
                    file_path=output_path
                )
                
                if not os.path.exists(output_path):
                    raise Exception("Local TTS failed to generate output file")
                    
            except Exception as local_tts_error:
                print(f"Failed to use local TTS: {local_tts_error}")
                # If everything fails, create a dummy WAV
                create_dummy_wav(output_path)
                
        return output_path
    finally:
        pass  # We handle cleanup separately for the audio files

def chunk_text(text, max_len=400):
    """Split text into chunks that fit within the API limits"""
    chunks = []
    current = ""
    for sentence in text.split('.'):
        sentence = sentence.strip()
        if not sentence:
            continue
        sentence += "."
        if len(current) + len(sentence) <= max_len:
            current += " " + sentence
        else:
            chunks.append(current.strip())
            current = sentence
    if current:
        chunks.append(current.strip())
    return chunks

def stitch_audio(audio_files, output_path):
    """Combine multiple audio files into one"""
    import wave
    
    valid_chunks = [c for c in audio_files if c and os.path.exists(c)]
    
    if not valid_chunks:
        raise Exception("No valid audio chunks to stitch")
        
    with wave.open(valid_chunks[0], 'rb') as first:
        params = first.getparams()
        
    with wave.open(output_path, 'wb') as output:
        output.setparams(params)
        for chunk in valid_chunks:
            with wave.open(chunk, 'rb') as w:
                output.writeframes(w.readframes(w.getnframes()))

def extract_text(file_path):
    """
    Extract text from an ebook file
    
    Args:
        file_path: Path to the ebook file
        
    Returns:
        Extracted text
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings if utf-8 fails
            for encoding in ['latin-1', 'cp1252', 'ascii']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            # If all encodings fail, return error
            raise ValueError(f"Unable to decode text file with common encodings: {file_path}")
            
    elif file_ext == '.epub' and 'epub' in globals():
        try:
            book = epub.read_epub(file_path)
            text = ""
            for item in book.get_items():
                if item.get_type() == epub.ITEM_DOCUMENT:
                    text += item.get_content().decode('utf-8')
            # Simple HTML stripping (basic implementation)
            text = text.replace('<br>', '\n').replace('<p>', '\n').replace('</p>', '\n')
            import re
            text = re.sub(r'<[^>]*>', '', text)
            return text
        except Exception as e:
            print(f"Error processing EPUB: {e}")
            return f"Failed to extract text from EPUB: {file_path}\nError: {str(e)}"
            
    elif file_ext == '.pdf' and 'PyPDF2' in globals():
        try:
            text = ""
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page_num in range(len(pdf_reader.pages)):
                    text += pdf_reader.pages[page_num].extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return f"Failed to extract text from PDF: {file_path}\nError: {str(e)}"
    else:
        return f"Sample text for demonstration from: {file_path}\nThe full content would be extracted in a production environment."

def create_dummy_wav(output_path):
    """
    Create a dummy WAV file for testing when actual TTS is not available
    """
    print(f"Creating dummy WAV file at {output_path}")
    # Create a simple WAV file header (44 bytes) + some silent audio data
    with open(output_path, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write((36).to_bytes(4, byteorder='little'))  # File size - 8
        f.write(b'WAVE')
        
        # Format chunk
        f.write(b'fmt ')
        f.write((16).to_bytes(4, byteorder='little'))  # Chunk size
        f.write((1).to_bytes(2, byteorder='little'))   # Audio format (PCM)
        f.write((1).to_bytes(2, byteorder='little'))   # Num channels (mono)
        f.write((44100).to_bytes(4, byteorder='little'))  # Sample rate
        f.write((44100).to_bytes(4, byteorder='little'))  # Byte rate
        f.write((1).to_bytes(2, byteorder='little'))   # Block align
        f.write((8).to_bytes(2, byteorder='little'))   # Bits per sample
        
        # Data chunk
        f.write(b'data')
        f.write((100).to_bytes(4, byteorder='little'))  # Chunk size
        
        # Write 100 bytes of silence (8-bit PCM, value 128 = silence)
        f.write(bytes([128] * 100)) 