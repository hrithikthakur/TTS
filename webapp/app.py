import os
import time
import secrets
import hashlib
from flask import Flask, render_template, request, jsonify, send_from_directory, current_app, abort, redirect
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from utils import process_ebook
import uuid
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_USER', 'noreply@audiobookcreator.com')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'epub', 'pdf', 'txt'}
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.config['DOWNLOAD_LINK_EXPIRY'] = 7 * 24 * 60 * 60  # 7 days in seconds

# Do NOT set SERVER_NAME here - it causes issues with the development server

mail = Mail(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# In-memory token storage for downloads
# In production, you'd use a database instead
download_tokens = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_download_token(filename, email):
    """Generate a secure download token that expires after the configured time"""
    # Create a unique token
    token = secrets.token_urlsafe(32)
    expiry = int(time.time()) + app.config['DOWNLOAD_LINK_EXPIRY']
    
    # Store token info
    download_tokens[token] = {
        'filename': filename,
        'email': email,
        'expiry': expiry
    }
    
    return token

def process_file_async(filepath, email, original_filename):
    # Create an application context for the thread
    with app.app_context():
        try:
            # Process the ebook
            output_path = process_ebook(filepath)
            
            # Get just the filename
            output_filename = os.path.basename(output_path)
            
            # Generate secure download token
            token = generate_download_token(output_filename, email)
            
            # Create secure download link
            base_url = os.getenv('BASE_URL', 'http://localhost:5000')
            download_url = f"{base_url}/secure-download/{token}"
            
            # Send email with the result
            msg = Message('Your Audiobook is Ready!',
                        sender=app.config['MAIL_DEFAULT_SENDER'],
                        recipients=[email])
            msg.body = f"""
            Your audiobook has been generated successfully!
            
            Original file: {original_filename}
            
            You can download your audiobook here:
            {download_url}
            
            This link will expire in 7 days.
            
            Thank you for using our service!
            """
            mail.send(msg)
            
        except Exception as e:
            print(f"Error processing file: {e}")
            # Send error email
            try:
                msg = Message('Error Processing Your Audiobook',
                            sender=app.config['MAIL_DEFAULT_SENDER'],
                            recipients=[email])
                msg.body = f"""
                We encountered an error while processing your ebook file.
                
                Error details: {str(e)}
                
                Please try again or contact support if the issue persists.
                """
                mail.send(msg)
            except Exception as email_error:
                print(f"Failed to send error email: {email_error}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    email = request.form.get('email')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    if file and allowed_file(file.filename):
        # Generate a unique filename
        original_filename = file.filename
        filename = secure_filename(f"{uuid.uuid4()}_{original_filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Start processing in background
        thread = threading.Thread(target=process_file_async, args=(filepath, email, original_filename))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'Your file is being processed. You will receive an email when your audiobook is ready!'
        })
    
    return jsonify({'error': 'File type not allowed. Please upload EPUB, PDF, or TXT files.'}), 400

@app.route('/secure-download/<token>')
def secure_download(token):
    # Check if token exists and is valid
    if token not in download_tokens:
        return render_template('download_error.html', error='Invalid or expired download link'), 404
    
    # Get token data
    token_data = download_tokens[token]
    
    # Check if token has expired
    if int(time.time()) > token_data['expiry']:
        # Remove expired token
        del download_tokens[token]
        return render_template('download_error.html', error='Download link has expired'), 410
    
    # Get filename from token
    filename = token_data['filename']
    
    # Serve the file
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.route('/download/<filename>')
def download_file(filename):
    # This is the old direct download method - we keep it for backward compatibility
    # but in production, you might want to disable this and only use secure downloads
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large (max 16MB)'}), 413

# Cleanup expired tokens regularly
def cleanup_expired_tokens():
    now = int(time.time())
    expired = [token for token, data in download_tokens.items() if data['expiry'] < now]
    for token in expired:
        del download_tokens[token]

if __name__ == '__main__':
    app.run(debug=True) 