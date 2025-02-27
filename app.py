from flask import Flask, render_template, jsonify, request, send_from_directory
from summarizer_methods import get_summary, get_answers
import os
from werkzeug.utils import secure_filename
import PyPDF2
import traceback

# Change static folder to 'static' instead of '.'
app = Flask(__name__, static_folder='static')

# Configuration
UPLOAD_FOLDER = 'uploaded_pdfs'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Dictionary to store extracted text from PDFs
pdf_texts = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    """Extract text content from a PDF file"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page_text = pdf_reader.pages[page_num].extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        print(traceback.format_exc())
        return None
    return text if text.strip() else "No extractable text found in the PDF."

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Update static file serving - you'll need to move these to a static folder eventually
@app.route('/stylesheet.css')
def stylesheet():
    return send_from_directory('.', 'stylesheet.css')

@app.route('/script.js')
def script():
    return send_from_directory('.', 'script.js')

# Added test route to verify POST functionality
@app.route('/test_post', methods=['GET', 'POST'])
def test_post():
    if request.method == 'POST':
        return jsonify({'message': 'POST received successfully'})
    return jsonify({'message': 'GET received successfully'})

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    """Handle PDF upload, extract text and store it"""
    try:
        print("Upload request received")
        if 'pdf_file' not in request.files:
            print("No file part in request")
            return jsonify({'error': 'No file part'}), 400
            
        file = request.files['pdf_file']
        print(f"File received: {file.filename}")
            
        if file.filename == '':
            print("Empty filename")
            return jsonify({'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            print(f"Secured filename: {filename}")
            
            # Check upload directory
            upload_dir = app.config['UPLOAD_FOLDER']
            print(f"Upload directory: {os.path.abspath(upload_dir)}")
            print(f"Directory exists: {os.path.exists(upload_dir)}")
            print(f"Directory is writable: {os.access(upload_dir, os.W_OK)}")
            
            # Ensure directory exists
            if not os.path.exists(upload_dir):
                print(f"Creating upload directory: {upload_dir}")
                os.makedirs(upload_dir, exist_ok=True)
                
            file_path = os.path.join(upload_dir, filename)
            print(f"Target file path: {file_path}")
            
            # Save the file
            try:
                file.save(file_path)
                print(f"File saved successfully to {file_path}")
                
                # Check if file exists after saving
                if os.path.exists(file_path):
                    print(f"Verified file exists at: {file_path}")
                    print(f"File size: {os.path.getsize(file_path)} bytes")
                else:
                    print(f"WARNING: File not found after save: {file_path}")
                    
            except Exception as e:
                print(f"Error saving file: {e}")
                print(traceback.format_exc())
                return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
            
             # Extract text from PDF
            print(f"Attempting to extract text from: {file_path}")
            text = extract_text_from_pdf(file_path)
            if text:
                print(f"Text extracted successfully: {len(text)} characters")
                # Store the text with the filename as key
                pdf_texts[filename] = text
                return jsonify({'success': True, 'filename': filename, "message": "File successfully uploaded"}), 200
            else:
                print("Text extraction failed or returned empty text")
                return jsonify({'error': 'Failed to extract text from PDF or PDF has no extractable text'}), 500

            
            
           
        return jsonify({'error': 'Invalid file type'}), 400
        
    except Exception as e:
        print(f"Unexpected error in upload_pdf: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500
    
@app.route('/test_json', methods=['GET'])
def test_json():
    return jsonify({'test': 'success'}), 200

@app.route('/generate', methods=['POST'])
def generate_summary():
    """Generate a summary for a specific PDF"""
    try:
        data = request.json
        pdf_name = data.get('pdf_name')
        
        if not pdf_name or pdf_name not in pdf_texts:
            return jsonify({'error': 'PDF not found or not processed'}), 404
            
        
        try:
            # Call the get_summary function from summarizer_methods.py
            summary = get_summary(pdf_name)
            return jsonify({'summary': summary}), 200
        except Exception as e:
            print(f"Error generating summary: {e}")
            print(traceback.format_exc())
            return jsonify({'error': f'Failed to generate summary: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Unexpected error in generate_summary: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    """Answer a question about a specific PDF"""
    try:
        data = request.json
        question = data.get('question')
        pdf_name = data.get('pdf_name')
            
        if not pdf_name or pdf_name not in pdf_texts:
            return jsonify({'error': 'PDF not found or not processed'}), 404
            
        if not question:
            return jsonify({'error': 'No question provided'}), 400
            
        
        try:
            # Call the get_answers function from summarizer_methods.py with the correct parameters
            answer = get_answers(question,pdf_name)
            return jsonify({'response': answer}), 200
        except Exception as e:
            print(f"Error generating answer: {e}")
            print(traceback.format_exc())
            return jsonify({'error': f'Failed to generate answer: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Unexpected error in ask_question: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    print("Starting Flask app...")
    print(f"Routes defined: {[f'{rule}, {rule.methods}' for rule in app.url_map.iter_rules()]}")
    app.run(debug=True)