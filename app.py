"""
Unified RAG Web Application
Combines GDD RAG and Code Q&A into a single Flask app
"""

from flask import Flask, render_template, request, session, jsonify
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
PARENT_ROOT = PROJECT_ROOT.parent
if str(PARENT_ROOT) not in sys.path:
    sys.path.insert(0, str(PARENT_ROOT))

# Configuration
CONFIG = {
    'SECRET_KEY': os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex()),
    'LOG_FILE': 'app.log',
    'LOG_FORMAT': '%(asctime)s - %(message)s',
    'LOG_DATE_FORMAT': '%d-%b-%y %H:%M:%S'
}

# Setup logging
def setup_logging(config):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(config['LOG_FILE'])
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(config['LOG_FORMAT'], datefmt=config['LOG_DATE_FORMAT']))
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(config['LOG_FORMAT'], datefmt=config['LOG_DATE_FORMAT']))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Create Flask app
app = Flask(__name__)
app.config.update(CONFIG)
app.logger = setup_logging(app.config)

# Import services
try:
    from backend.gdd_service import (
        upload_and_index_document,
        list_documents,
        get_document_options,
        query_gdd_documents
    )
    gdd_service_available = True
except ImportError as e:
    app.logger.warning(f"Could not import GDD service: {e}")
    gdd_service_available = False

try:
    from backend.code_service import (
        query_codebase,
        list_indexed_files
    )
    code_service_available = True
except ImportError as e:
    app.logger.warning(f"Could not import Code service: {e}")
    code_service_available = False

@app.route('/')
def index():
    """Main page with tabs for GDD RAG and Code Q&A"""
    return render_template('index.html')

@app.route('/gdd')
def gdd_tab():
    """GDD RAG tab"""
    return render_template('gdd_tab.html')

@app.route('/code')
def code_tab():
    """Code Q&A tab"""
    return render_template('code_tab.html')

@app.route('/api/gdd/query', methods=['POST'])
def gdd_query():
    """Handle GDD RAG queries"""
    try:
        if not gdd_service_available:
            return jsonify({'error': 'GDD service not available'}), 500
        
        data = request.get_json()
        query = data.get('query', '')
        selected_doc = data.get('selected_doc', None)
        
        result = query_gdd_documents(query, selected_doc)
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in GDD query: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/gdd/upload', methods=['POST'])
def gdd_upload():
    """Handle document uploads for GDD RAG"""
    try:
        if not gdd_service_available:
            return jsonify({'error': 'GDD service not available'}), 500
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided', 'status': 'error'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected', 'status': 'error'}), 400
        
        # Save uploaded file temporarily
        from werkzeug.utils import secure_filename
        import tempfile
        
        filename = secure_filename(file.filename)
        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / filename
        file.save(str(temp_file))
        
        # Process the file
        result = upload_and_index_document(temp_file)
        
        # Clean up temp file
        try:
            temp_file.unlink()
        except:
            pass
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in GDD upload: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/gdd/documents', methods=['GET'])
def gdd_documents():
    """List all indexed GDD documents"""
    try:
        if not gdd_service_available:
            return jsonify({'documents': [], 'options': ['All Documents']})
        
        documents = list_documents()
        options = get_document_options()
        
        return jsonify({
            'documents': documents,
            'options': options
        })
    except Exception as e:
        app.logger.error(f"Error listing GDD documents: {e}")
        return jsonify({'documents': [], 'options': ['All Documents'], 'error': str(e)})

@app.route('/api/code/query', methods=['POST'])
def code_query():
    """Handle Code Q&A queries"""
    try:
        if not code_service_available:
            return jsonify({'error': 'Code service not available', 'status': 'error'}), 500
        
        data = request.get_json()
        query = data.get('query', '')
        file_filters = data.get('file_filters', [])
        rerank = data.get('rerank', False)
        
        result = query_codebase(query, file_filters=file_filters, rerank=rerank)
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error in Code query: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/code/files', methods=['GET'])
def code_files():
    """List all indexed code files"""
    try:
        if not code_service_available:
            return jsonify({'files': []})
        
        files = list_indexed_files()
        app.logger.info(f"Returning {len(files)} code files")
        return jsonify({'files': files})
    except Exception as e:
        app.logger.error(f"Error listing code files: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'files': []}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

