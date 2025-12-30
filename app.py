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

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
CONFIG = {
    'SECRET_KEY': os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex()),
    'LOG_FORMAT': '%(asctime)s - %(message)s',
    'LOG_DATE_FORMAT': '%d-%b-%y %H:%M:%S'
}

# Setup logging
def setup_logging(config):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers if reloaded
    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        config['LOG_FORMAT'],
        datefmt=config['LOG_DATE_FORMAT']
    ))
    logger.addHandler(console_handler)

    return logger


# Create Flask app
try:
    app = Flask(__name__)
    app.config.update(CONFIG)
    app.logger = setup_logging(app.config)
    app.logger.info("Flask app object created successfully")
except Exception as e:
    import sys
    import traceback
    print(f"[FATAL] Failed to create Flask app: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise

# Log startup configuration
app.logger.info("=" * 60)
app.logger.info("Flask app initializing...")
app.logger.info(f"Project root: {PROJECT_ROOT}")

# Check Supabase configuration
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
app.logger.info(f"SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'}")
if supabase_url:
    app.logger.info(f"SUPABASE_URL value: {supabase_url[:30]}...")
app.logger.info(f"SUPABASE_KEY: {'SET' if supabase_key else 'NOT SET'}")
if supabase_key:
    app.logger.info(f"SUPABASE_KEY starts with: {supabase_key[:20]}...")
app.logger.info(f"SUPABASE_SERVICE_KEY: {'SET' if supabase_service_key else 'NOT SET'}")
app.logger.info(f"DASHSCOPE_API_KEY: {'SET' if os.getenv('DASHSCOPE_API_KEY') else 'NOT SET'}")

# Import services
app.logger.info("Importing GDD service...")
try:
    from backend.gdd_service import (
        upload_and_index_document_bytes,
        list_documents,
        get_document_options,
        query_gdd_documents,
        get_document_sections
    )

    gdd_service_available = True
    app.logger.info("[OK] GDD service imported successfully")
    
    # Check Supabase availability in GDD service
    try:
        from backend.storage.gdd_supabase_storage import USE_SUPABASE
        app.logger.info(f"GDD Supabase storage: {'ENABLED' if USE_SUPABASE else 'DISABLED'}")
    except Exception as e:
        app.logger.warning(f"Could not check GDD Supabase status: {e}")
        
except ImportError as e:
    app.logger.error(f"[ERROR] Could not import GDD service: {e}")
    import traceback
    app.logger.error(f"Import traceback: {traceback.format_exc()}")
    gdd_service_available = False

app.logger.info("Importing Code service...")
try:
    from backend.code_service import (
        query_codebase,
        list_indexed_files
    )
    code_service_available = True
    app.logger.info("[OK] Code service imported successfully")
    
    # Check Supabase availability in Code service
    try:
        from backend.storage.code_supabase_storage import USE_SUPABASE as CODE_USE_SUPABASE
        app.logger.info(f"Code Supabase storage: {'ENABLED' if CODE_USE_SUPABASE else 'DISABLED'}")
    except Exception as e:
        app.logger.warning(f"Could not check Code Supabase status: {e}")
        
except ImportError as e:
    app.logger.error(f"[ERROR] Could not import Code service: {e}")
    import traceback
    app.logger.error(f"Import traceback: {traceback.format_exc()}")
    code_service_available = False

# Log all registered routes on startup
def log_registered_routes():
    """Log registered routes for debugging (safe: no recursion)."""
    try:
        with app.app_context():
            app.logger.info("Registered routes:")
            for rule in app.url_map.iter_rules():
                if rule.rule.startswith('/api') or rule.rule in ['/', '/gdd', '/code', '/health']:
                    methods = [m for m in rule.methods if m not in {'HEAD', 'OPTIONS'}]
                    app.logger.info(f"  {rule.rule} [{', '.join(methods)}]")
    except Exception as e:
        app.logger.warning(f"Could not log routes: {e}")



# Log routes after app is fully configured
try:
    log_registered_routes()
    app.logger.info("=" * 60)
    app.logger.info("App is ready to serve requests")
    app.logger.info("=" * 60)

except ImportError as e:
    app.logger.error(f"[ERROR] Could not import Code service: {e}")
    import traceback
    app.logger.error(f"Import traceback: {traceback.format_exc()}")
    code_service_available = False

app.logger.info("=" * 60)

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
    """Handle document uploads for GDD RAG (diskless: bytes -> Docling -> Supabase)"""
    try:
        if not gdd_service_available:
            return jsonify({'error': 'GDD service not available'}), 500

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided', 'status': 'error'}), 400

        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'No file selected', 'status': 'error'}), 400

        # DISKLESS: read bytes and pass into bytes-based pipeline
        pdf_bytes = file.read()
        result = upload_and_index_document_bytes(pdf_bytes, file.filename)
        return jsonify(result)

    except Exception as e:
        app.logger.error(f"Error in GDD upload: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500



@app.route('/api/gdd/documents', methods=['GET'])
def gdd_documents():
    """List all indexed GDD documents"""
    app.logger.info("=" * 60)
    app.logger.info("GET /api/gdd/documents - Starting request")
    
    try:
        if not gdd_service_available:
            app.logger.warning("GDD service not available")
            return jsonify({'documents': [], 'options': ['All Documents']})
        
        app.logger.info("GDD service is available, calling list_documents()...")
        documents = list_documents()
        app.logger.info(f"list_documents() returned {len(documents)} documents")
        
        if documents:
            app.logger.info(f"Sample document: {documents[0].get('name', 'N/A')}")
        
        app.logger.info("Calling get_document_options()...")
        options = get_document_options()
        app.logger.info(f"get_document_options() returned {len(options)} options")
        
        app.logger.info(f"Returning response with {len(documents)} documents and {len(options)} options")
        app.logger.info("=" * 60)
        return jsonify({
            'documents': documents,
            'options': options
        })
    except Exception as e:
        app.logger.error(f"[ERROR] Error listing GDD documents: {e}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        app.logger.info("=" * 60)
        return jsonify({'documents': [], 'options': ['All Documents'], 'error': str(e)})

@app.route('/api/gdd/sections', methods=['GET'])
def get_gdd_sections():
    """Get all sections/headers for a specific document"""
    app.logger.info("=" * 60)
    app.logger.info("[GDD Sections API] *** ROUTE HIT ***")
    app.logger.info(f"[GDD Sections API] Request URL: {request.url}")
    app.logger.info(f"[GDD Sections API] Request method: {request.method}")
    app.logger.info(f"[GDD Sections API] Request args: {dict(request.args)}")
    app.logger.info(f"[GDD Sections API] doc_id parameter: {request.args.get('doc_id')}")
    app.logger.info("=" * 60)
    
    try:
        if not gdd_service_available:
            app.logger.warning("[GDD Sections API] GDD service not available")
            return jsonify({'sections': [], 'error': 'GDD service not available'})
        
        doc_id = request.args.get('doc_id')
        if not doc_id:
            app.logger.warning("[GDD Sections API] Missing doc_id parameter")
            return jsonify({'sections': [], 'error': 'doc_id parameter required'})
        
        app.logger.info(f"[GDD Sections API] Calling get_document_sections for doc_id: {doc_id}")
        # get_document_sections is already imported at module level
        sections = get_document_sections(doc_id)
        app.logger.info(f"[GDD Sections API] Returning {len(sections)} sections for doc_id: {doc_id}")
        
        result = {
            'sections': sections,
            'doc_id': doc_id
        }
        app.logger.info(f"[GDD Sections API] Response: {len(sections)} sections")
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"[GDD Sections API] Error getting sections for document {request.args.get('doc_id')}: {e}")
        import traceback
        app.logger.error(f"[GDD Sections API] Traceback: {traceback.format_exc()}")
        return jsonify({'sections': [], 'error': str(e)})

@app.route('/api/code/query', methods=['POST'])
def code_query():
    """Handle Code Q&A queries"""
    try:
        if not code_service_available:
            return jsonify({'error': 'Code service not available', 'status': 'error'}), 500
        
        data = request.get_json()
        query = data.get('query', '')
        file_filters = data.get('file_filters', [])
        selected_methods = data.get('selected_methods', [])
        
        app.logger.info(f"[Code Q&A API] Received query: {query[:100]}")
        app.logger.info(f"[Code Q&A API] File filters: {file_filters}")
        app.logger.info(f"[Code Q&A API] Selected methods: {selected_methods}")
        
        result = query_codebase(query, file_filters=file_filters, selected_methods=selected_methods)
        
        app.logger.info(f"[Code Q&A API] Response status: {result.get('status')}")
        app.logger.info(f"[Code Q&A API] Response length: {len(result.get('response', ''))}")
        
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"[Code Q&A API] Error in Code query: {e}")
        import traceback
        app.logger.error(f"[Code Q&A API] Traceback: {traceback.format_exc()}")
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

@app.route('/api/debug/code-supabase', methods=['GET'])
def debug_code_supabase():
    """Debug endpoint to check Code Q&A Supabase connection and data"""
    diagnostics = {
        'code_supabase_available': False,
        'code_files_count': 0,
        'code_chunks_count': 0,
        'sample_files': [],
        'errors': []
    }
    
    try:
        from backend.storage.code_supabase_storage import USE_SUPABASE, list_code_files_supabase
        from backend.storage.supabase_client import get_code_files
        
        diagnostics['code_supabase_available'] = USE_SUPABASE
        
        if USE_SUPABASE:
            try:
                files = get_code_files()
                diagnostics['code_files_count'] = len(files) if files else 0
                diagnostics['sample_files'] = [f.get('file_path', 'unknown') for f in (files[:5] if files else [])]
                
                # Try to get chunk count
                try:
                    from backend.storage.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    result = client.table('code_chunks').select('id', count='exact').limit(1).execute()
                    diagnostics['code_chunks_count'] = result.count if hasattr(result, 'count') else 'unknown'
                except Exception as e:
                    diagnostics['errors'].append(f"Could not count chunks: {e}")
                    
            except Exception as e:
                diagnostics['errors'].append(f"Error fetching code files: {e}")
        else:
            diagnostics['errors'].append("Code Supabase not configured")
            
    except Exception as e:
        diagnostics['errors'].append(f"Diagnostic error: {e}")
        import traceback
        diagnostics['traceback'] = traceback.format_exc()
    
    return jsonify(diagnostics)

@app.route('/api/debug/supabase', methods=['GET'])
def debug_supabase():
    """Diagnostic endpoint to check Supabase connection and configuration"""
    diagnostics = {
        'environment_variables': {},
        'supabase_connection': {},
        'data_access': {},
        'errors': []
    }
    
    try:
        # Check environment variables (masked for security)
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        diagnostics['environment_variables'] = {
            'SUPABASE_URL': supabase_url[:30] + '...' if supabase_url else 'NOT SET',
            'SUPABASE_KEY': supabase_key[:20] + '...' if supabase_key else 'NOT SET',
            'SUPABASE_SERVICE_KEY': 'SET' if supabase_service_key else 'NOT SET',
            'DASHSCOPE_API_KEY': 'SET' if os.getenv('DASHSCOPE_API_KEY') else 'NOT SET'
        }
        
        # Test Supabase connection
        if supabase_url and supabase_key:
            try:
                from backend.storage.supabase_client import get_supabase_client, get_gdd_documents, get_code_files
                
                # Test anon key connection
                client = get_supabase_client(use_service_key=False)
                diagnostics['supabase_connection']['anon_key'] = 'SUCCESS'
                
                # Test data access
                try:
                    gdd_docs = get_gdd_documents()
                    diagnostics['data_access']['gdd_documents'] = {
                        'count': len(gdd_docs),
                        'status': 'SUCCESS' if len(gdd_docs) > 0 else 'EMPTY'
                    }
                    if len(gdd_docs) > 0:
                        diagnostics['data_access']['gdd_sample'] = {
                            'doc_id': gdd_docs[0].get('doc_id'),
                            'name': gdd_docs[0].get('name')
                        }
                except Exception as e:
                    diagnostics['data_access']['gdd_documents'] = {
                        'count': 0,
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    diagnostics['errors'].append(f"GDD documents access error: {e}")
                
                try:
                    code_files_list = get_code_files()
                    diagnostics['data_access']['code_files'] = {
                        'count': len(code_files_list),
                        'status': 'SUCCESS' if len(code_files_list) > 0 else 'EMPTY'
                    }
                except Exception as e:
                    diagnostics['data_access']['code_files'] = {
                        'count': 0,
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    diagnostics['errors'].append(f"Code files access error: {e}")
                
            except Exception as e:
                diagnostics['supabase_connection']['anon_key'] = 'FAILED'
                diagnostics['supabase_connection']['error'] = str(e)
                diagnostics['errors'].append(f"Supabase connection error: {e}")
        else:
            diagnostics['supabase_connection']['status'] = 'MISSING_ENV_VARS'
            diagnostics['errors'].append("SUPABASE_URL or SUPABASE_KEY not set")
        
        # Check if Supabase is being used
        try:
            from backend.storage.gdd_supabase_storage import USE_SUPABASE
            diagnostics['supabase_usage'] = {
                'USE_SUPABASE': USE_SUPABASE,
                'status': 'ENABLED' if USE_SUPABASE else 'DISABLED'
            }
        except Exception as e:
            diagnostics['supabase_usage'] = {
                'status': 'ERROR',
                'error': str(e)
            }
        
    except Exception as e:
        diagnostics['errors'].append(f"Diagnostic error: {e}")
        import traceback
        diagnostics['traceback'] = traceback.format_exc()
    
    return jsonify(diagnostics)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Render"""
    return jsonify({'status': 'ok', 'service': 'unified-rag-app'}), 200

# Add 404 error handler for debugging
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors with detailed logging"""
    app.logger.error("=" * 60)
    app.logger.error(f"[404 ERROR] Request to {request.url} not found")
    app.logger.error(f"[404 ERROR] Path: {request.path}")
    app.logger.error(f"[404 ERROR] Method: {request.method}")
    app.logger.error(f"[404 ERROR] Args: {dict(request.args)}")
    app.logger.error("=" * 60)
    return jsonify({'error': 'Not found', 'path': request.path, 'method': request.method}), 404

# Log all registered routes after all routes are defined
def log_all_routes():
    """Log all registered routes for debugging"""
    try:
        with app.app_context():
            app.logger.info("=" * 60)
            app.logger.info("All registered routes:")
            api_routes = []
            other_routes = []
            for rule in app.url_map.iter_rules():
                methods = [m for m in rule.methods if m not in {'HEAD', 'OPTIONS'}]
                route_info = f"  {rule.rule} [{', '.join(methods)}]"
                if rule.rule.startswith('/api'):
                    api_routes.append(route_info)
                else:
                    other_routes.append(route_info)
            
            for route in sorted(api_routes):
                app.logger.info(route)
            for route in sorted(other_routes):
                app.logger.info(route)
            app.logger.info("=" * 60)
    except Exception as e:
        app.logger.warning(f"Could not log routes: {e}")

# Log routes after all are defined
log_all_routes()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.logger.info(f"Starting Flask development server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

