import os
import subprocess
import wave
from dotenv import load_dotenv

load_dotenv()
# === CONFIGURATION ===
API_ENDPOINT = "grpc.nvcf.nvidia.com:443"
VOICE = "Magpie-Multilingual.EN-US.Sofia"
FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"
LANGUAGE = "en-US"
MAX_CHAR = 400  # API text limit
AUTH = os.getenv("AUTH")  # Get AUTH from environment variables

# === HELPERS ===

def chunk_text(text, max_len=MAX_CHAR):
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

def synthesize(text_chunk, index):
    output_file = f"chunk_{index}.wav"
    cmd = [
        "python", "/Users/hrithikthakur/python-clients/scripts/tts/talk.py",
        "--server", API_ENDPOINT,
        "--use-ssl",
        "--metadata", "function-id", FUNCTION_ID,
        "--metadata", "authorization", AUTH,
        "--language-code", LANGUAGE,
        "--text", text_chunk,
        "--voice", VOICE,
        "--output", output_file
    ]

    print(f"[⏳] Synthesizing chunk {index+1}...")
    result = subprocess.run(cmd, capture_output=True)
    
    if result.returncode != 0:
        print(f"❌ Failed: Chunk {index+1}\n{result.stderr.decode()}")
        return None
    
    if not os.path.exists(output_file):
        print(f"❌ Output file not found: {output_file}")
        return None

    print(f"[✅] Created {output_file}")
    return output_file

def stitch_audio(chunks, output_name="audiobook.wav"):
    valid_chunks = [c for c in chunks if c and os.path.exists(c)]

    if not valid_chunks:
        print("❌ No valid audio chunks to stitch.")
        return

    with wave.open(valid_chunks[0], 'rb') as first:
        params = first.getparams()

    with wave.open(output_name, 'wb') as output:
        output.setparams(params)
        for chunk in valid_chunks:
            with wave.open(chunk, 'rb') as w:
                output.writeframes(w.readframes(w.getnframes()))

    print(f"[📘] Final audiobook saved as: {output_name}")

# === MAIN ===

def main():
    input_file = "understand.txt"  # Replace with your text file

    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    with open(input_file, "r") as f:
        text = f.read()

    chunks = chunk_text(text)
    print(f"[📖] Total text chunks: {len(chunks)}")

    audio_files = []
    for i, chunk in enumerate(chunks):
        audio_file = synthesize(chunk, i)
        if audio_file:
            audio_files.append(audio_file)

    if not audio_files:
        print("❌ No audio was generated.")
        return

    stitch_audio(audio_files)

if __name__ == "__main__":
    main()