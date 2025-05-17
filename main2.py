# import os

# def split_text_into_chunks(text, chunk_size=250):
#     words = text.split()
#     return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# def save_chunks_to_files(chunks, output_dir="chunks", prefix="chunk"):
#     os.makedirs(output_dir, exist_ok=True)
#     for i, chunk in enumerate(chunks):
#         with open(os.path.join(output_dir, f"{prefix}_{i+1:03d}.txt"), 'w') as f:
#             f.write(chunk)

# def chunk_text_file(input_path, chunk_size=250):
#     with open(input_path, 'r') as f:
#         full_text = f.read()
#     chunks = split_text_into_chunks(full_text, chunk_size)
#     save_chunks_to_files(chunks)
#     print(f"✅ Split into {len(chunks)} chunks of ~{chunk_size} words each.")

# # Example usage:
# chunk_text_file("understand.txt")

import os
from TTS.api import TTS

# Initialize the model (load once)
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True, gpu=False)

# Directory containing text chunks
chunk_dir = "chunks"
output_dir = "audio"
os.makedirs(output_dir, exist_ok=True)

# Reference audio for cloning (optional - if using voice cloning)
# Set to None if not cloning
reference_audio_path = "reference.wav"
language = "en"

# Process each chunk file
for fname in sorted(os.listdir(chunk_dir)):
    if not fname.endswith(".txt"):
        continue

    with open(os.path.join(chunk_dir, fname), 'r') as f:
        text = f.read()

    output_wav_path = os.path.join(output_dir, fname.replace(".txt", ".wav"))
    print(f"🗣️ Generating audio for {fname}...")

    # If reference voice is used
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_audio_path,
        language=language,
        file_path=output_wav_path
    )

print("✅ Done. All chunks processed into audio.")