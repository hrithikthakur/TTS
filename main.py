from PyPDF2 import PdfReader
from TTS.api import TTS
# reader = PdfReader("Understand.pdf")


# # Extract text from all pages
# all_text = ""
# for page in reader.pages:
#     text = page.extract_text()
#     if text:
#         all_text += text + "\n"

# # Save to a text file
# with open("output.txt", "w", encoding="utf-8") as f:
#     f.write(all_text)

#     from TTS.api import TTS

# Load text from file

# Load XTTS model
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
tts.to("cpu")  # ← explicitly set device

with open("understand2.txt", "r") as f:
    text = f.read()

# Generate speech
tts.tts_to_file(
    text=text,
    speaker_wav="bill.wav",
    language="en",
    file_path="output4.wav"
)