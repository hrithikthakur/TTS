# Ebook to Audiobook Web Converter

A web application that converts ebooks to audiobooks using text-to-speech technology.

## Setup

1. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the requirements:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the webapp directory with the following content:
```
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password
```

Note: For Gmail, you'll need to use an App Password. You can generate one in your Google Account settings under Security > 2-Step Verification > App passwords.

## Running the Application

1. Make sure you're in the webapp directory
2. Run the Flask application:
```bash
python app.py
```
3. Open your browser and navigate to `http://localhost:5000`

## Features

- Upload EPUB, PDF, or TXT files
- Automatic conversion to audiobook
- Email notification when processing is complete
- Modern, responsive UI
- Drag and drop file upload
- Progress indication

## File Size Limits

- Maximum file size: 16MB
- Supported formats: EPUB, PDF, TXT 