import os
import logging
from flask import request, jsonify
from models import CodeFile, ApiLog, db
import datetime
import traceback

# Get API key from environment variable
API_KEY = os.getenv("REPLIT_SECRET_KEY")

def log_api_request(endpoint, method, status_code, ip_address=None, user_agent=None):
    """Log API requests to the database for monitoring and auditing."""
    try:
        log_entry = ApiLog()
        log_entry.endpoint = endpoint
        log_entry.method = method
        log_entry.status_code = status_code
        log_entry.ip_address = ip_address
        log_entry.user_agent = user_agent
        log_entry.timestamp = datetime.datetime.utcnow()
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        logging.error(f"Failed to log API request: {e}")
        db.session.rollback()

def verify_api_key():
    """Verify if the provided API key is valid."""
    req_key = request.headers.get("Authorization", "")
    
    # Check if key exists and has the correct format
    if not API_KEY:
        logging.error("API_KEY is not set in environment variables")
        return False
        
    # Proper authorization header format is "Bearer <token>"
    if not req_key.startswith("Bearer "):
        return False
        
    # Extract the token part
    token = req_key.split("Bearer ")[1]
    
    # Verify token
    return token == API_KEY

def update_file_record(filename):
    """Update or create a record of file modification."""
    try:
        file_record = CodeFile.query.filter_by(filename=filename).first()
        if file_record:
            file_record.last_modified = datetime.datetime.utcnow()
        else:
            file_record = CodeFile()
            file_record.filename = filename
            file_record.last_modified = datetime.datetime.utcnow()
            file_record.modified_by = "Amaru"  # Assuming the AI agent is named Amaru
            db.session.add(file_record)
        db.session.commit()
    except Exception as e:
        logging.error(f"Failed to update file record: {e}")
        db.session.rollback()

def get_file_info(full_path, relative_path):
    """Get information about a file for the API list endpoint."""
    try:
        stat_info = os.stat(full_path)
        
        # Get file extension
        _, ext = os.path.splitext(full_path)
        ext = ext[1:] if ext else ""  # Remove leading dot
        
        # Get file info from database if available
        db_info = CodeFile.query.filter_by(filename=relative_path).first()
        
        return {
            "name": os.path.basename(full_path),
            "path": relative_path,
            "size": stat_info.st_size,
            "modified": datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            "type": ext,
            "last_modified_by": db_info.modified_by if db_info else None,
            "tracked_in_db": db_info is not None
        }
    except Exception as e:
        logging.error(f"Error getting file info for {full_path}: {e}")
        return {
            "name": os.path.basename(full_path),
            "path": relative_path,
            "error": str(e)
        }

def get_template_for_module(module_type, module_name):
    """Generate template code based on module type and name."""
    
    if module_type == "google_docs_handler":
        return """import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Configuration
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'nepantla-service-account.json'

class GoogleDocsHandler:
    def __init__(self):
        \"\"\"Initialize Google Docs API connection.\"\"\"
        try:
            # Load credentials from service account file
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            
            # Build the Google Docs API client
            self.docs_service = build('docs', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.is_connected = True
            
        except Exception as e:
            print(f"Error initializing Google Docs API: {e}")
            self.is_connected = False
    
    def create_document(self, title, content=""):
        \"\"\"Create a new Google Doc with optional initial content.\"\"\"
        if not self.is_connected:
            return {"error": "Not connected to Google Docs API"}
        
        try:
            # Create a new document
            document = self.docs_service.documents().create(
                body={"title": title}
            ).execute()
            
            doc_id = document.get('documentId')
            
            # If content is provided, add it to the document
            if content:
                self.append_to_document(doc_id, content)
            
            return {
                "document_id": doc_id,
                "title": title,
                "url": f"https://docs.google.com/document/d/{doc_id}/edit"
            }
            
        except Exception as e:
            return {"error": f"Failed to create document: {str(e)}"}
    
    def append_to_document(self, doc_id, content):
        \"\"\"Append content to an existing Google Doc.\"\"\"
        if not self.is_connected:
            return {"error": "Not connected to Google Docs API"}
        
        try:
            # Get the current end index
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            end_index = document.get('body').get('content')[-1].get('endIndex')
            
            # Create the request to insert text
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': end_index - 1
                        },
                        'text': content
                    }
                }
            ]
            
            # Execute the request
            result = self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={'requests': requests}).execute()
            
            return {
                "status": "success",
                "message": f"Content added to document {doc_id}"
            }
            
        except Exception as e:
            return {"error": f"Failed to append to document: {str(e)}"}
    
    def share_document(self, doc_id, email, role='reader'):
        \"\"\"Share a document with a user.\"\"\"
        if not self.is_connected:
            return {"error": "Not connected to Google Docs API"}
        
        try:
            # Create permission
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            result = self.drive_service.permissions().create(
                fileId=doc_id,
                body=user_permission,
                fields='id',
                sendNotificationEmail=True
            ).execute()
            
            return {
                "status": "success",
                "message": f"Document shared with {email} as {role}"
            }
            
        except Exception as e:
            return {"error": f"Failed to share document: {str(e)}"}

# Usage example
if __name__ == "__main__":
    docs_handler = GoogleDocsHandler()
    new_doc = docs_handler.create_document("Test Document", "This is a test document created by Nepantla AI")
    print(new_doc)
"""
    elif module_type == "journal_tracker":
        return """import datetime
import json
import os
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app import db

class JournalEntry(db.Model):
    \"\"\"Model for user journal entries.\"\"\"
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood_score = db.Column(db.Integer, nullable=True)  # Scale of 1-10
    tags = db.Column(db.String(255), nullable=True)  # Comma-separated tags
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationship to User model
    user = relationship("User", back_populates="journal_entries")
    
    def __repr__(self):
        return f"<JournalEntry {self.title}>"
    
    @property
    def tags_list(self):
        \"\"\"Convert tags string to list.\"\"\"
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',')]
    
    @property
    def age_in_days(self):
        \"\"\"Get age of entry in days.\"\"\"
        delta = datetime.datetime.utcnow() - self.created_at
        return delta.days
    
    def to_dict(self):
        \"\"\"Convert entry to dictionary for API responses.\"\"\"
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'mood_score': self.mood_score,
            'tags': self.tags_list,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class JournalTracker:
    \"\"\"Helper class for tracking and analyzing journal entries.\"\"\"
    
    def __init__(self, user_id):
        self.user_id = user_id
    
    def add_entry(self, title, content, mood_score=None, tags=None):
        \"\"\"Add a new journal entry.\"\"\"
        try:
            tags_str = ','.join(tags) if tags else None
            
            entry = JournalEntry(
                user_id=self.user_id,
                title=title,
                content=content,
                mood_score=mood_score,
                tags=tags_str
            )
            
            db.session.add(entry)
            db.session.commit()
            
            return {"status": "success", "entry_id": entry.id}
        
        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}
    
    def get_entries(self, limit=10, offset=0, tags=None):
        \"\"\"Get journal entries, optionally filtered by tags.\"\"\"
        query = JournalEntry.query.filter_by(user_id=self.user_id)
        
        if tags:
            # Filter by tags (basic implementation - could be improved with a tags table)
            tag_filters = []
            for tag in tags:
                tag_filters.append(JournalEntry.tags.like(f"%{tag}%"))
            
            from sqlalchemy import or_
            query = query.filter(or_(*tag_filters))
        
        entries = query.order_by(JournalEntry.created_at.desc()).offset(offset).limit(limit).all()
        
        return [entry.to_dict() for entry in entries]
    
    def get_mood_trends(self, days=30):
        \"\"\"Analyze mood trends over time.\"\"\"
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        
        entries = JournalEntry.query.filter(
            JournalEntry.user_id == self.user_id,
            JournalEntry.created_at >= cutoff_date,
            JournalEntry.mood_score.isnot(None)
        ).order_by(JournalEntry.created_at).all()
        
        mood_data = [
            {
                'date': entry.created_at.strftime('%Y-%m-%d'),
                'mood': entry.mood_score
            }
            for entry in entries
        ]
        
        return {
            'data_points': len(mood_data),
            'mood_data': mood_data,
            'average_mood': sum(item['mood'] for item in mood_data) / len(mood_data) if mood_data else None
        }
    
    def get_common_themes(self, limit=5):
        \"\"\"Identify common themes from journal entries.\"\"\"
        entries = JournalEntry.query.filter_by(user_id=self.user_id).all()
        
        # Extract all tags
        all_tags = []
        for entry in entries:
            all_tags.extend(entry.tags_list)
        
        # Count tag occurrences
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # Sort by count and return top tags
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'tag': tag, 'count': count}
            for tag, count in sorted_tags[:limit]
        ]

# Add relationship to User model
from models import User
User.journal_entries = relationship("JournalEntry", back_populates="user")
"""
    else:
        # Return a simple placeholder for unknown module types
        return f"# {module_name.replace('_', ' ').title()}\n\n'''\nAuto-generated module for {module_name}\n'''\n\n# Add your code here\n"

def setup_routes(app):
    """Set up API routes for the application."""
    
    @app.route("/api/write", methods=["POST"])
    def write_to_file():
        """API endpoint to write content to a file."""
        # Get client information for logging
        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")
        
        # Verify API key
        if not verify_api_key():
            log_api_request("/api/write", "POST", 403, ip_address, user_agent)
            return jsonify({"error": "unauthorized", "message": "Invalid or missing API key"}), 403

        # Get request data
        try:
            data = request.get_json()
            if not data:
                log_api_request("/api/write", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400
                
            filename = data.get("filename")
            content = data.get("content")
            
            # Validate required fields
            if not filename:
                log_api_request("/api/write", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Filename is required"}), 400
                
            if content is None:  # Allow empty content for file clearing
                log_api_request("/api/write", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Content field is required"}), 400
            
            # Security check to prevent path traversal attacks
            normalized_path = os.path.normpath(filename)
            if normalized_path.startswith("..") or normalized_path.startswith("/"):
                log_api_request("/api/write", "POST", 403, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Invalid filename path"}), 403
            
            # Write content to file
            try:
                # Ensure directory exists
                directory = os.path.dirname(filename)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    
                with open(filename, "w") as f:
                    f.write(content)
                
                # Update file record in database
                update_file_record(filename)
                
                log_api_request("/api/write", "POST", 200, ip_address, user_agent)
                return jsonify({
                    "status": "success", 
                    "message": f"{filename} updated",
                    "timestamp": datetime.datetime.utcnow().isoformat()
                })
            except PermissionError:
                log_api_request("/api/write", "POST", 403, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Permission denied to write file"}), 403
            except Exception as e:
                log_api_request("/api/write", "POST", 500, ip_address, user_agent)
                logging.error(f"Error writing file: {str(e)}\n{traceback.format_exc()}")
                return jsonify({"status": "error", "message": str(e)}), 500
                
        except Exception as e:
            log_api_request("/api/write", "POST", 400, ip_address, user_agent)
            logging.error(f"Error processing request: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"status": "error", "message": "Invalid request format"}), 400
    
    @app.route("/api/append", methods=["POST"])
    def append_to_file():
        """API endpoint to append content to a file."""
        # Get client information for logging
        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")
        
        # Verify API key
        if not verify_api_key():
            log_api_request("/api/append", "POST", 403, ip_address, user_agent)
            return jsonify({"error": "unauthorized", "message": "Invalid or missing API key"}), 403

        # Get request data
        try:
            data = request.get_json()
            if not data:
                log_api_request("/api/append", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400
                
            filename = data.get("filename")
            content = data.get("content")
            
            # Validate required fields
            if not filename:
                log_api_request("/api/append", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Filename is required"}), 400
                
            if content is None:  # Allow empty content (though not very useful for append)
                log_api_request("/api/append", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Content field is required"}), 400
            
            # Security check to prevent path traversal attacks
            normalized_path = os.path.normpath(filename)
            if normalized_path.startswith("..") or normalized_path.startswith("/"):
                log_api_request("/api/append", "POST", 403, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Invalid filename path"}), 403
            
            # Append content to file
            try:
                # Ensure directory exists
                directory = os.path.dirname(filename)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                
                # Check if file exists - if not, create it
                file_exists = os.path.exists(filename)
                
                # Append mode will create the file if it doesn't exist
                with open(filename, "a") as f:
                    # If the file already exists and has content, add a line break before appending
                    if file_exists and os.path.getsize(filename) > 0:
                        f.write("\n")
                    f.write(content)
                
                # Update file record in database
                update_file_record(filename)
                
                status_message = f"{filename} {'appended' if file_exists else 'created and content added'}"
                
                log_api_request("/api/append", "POST", 200, ip_address, user_agent)
                return jsonify({
                    "status": "success", 
                    "message": status_message,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "file_existed": file_exists
                })
            except PermissionError:
                log_api_request("/api/append", "POST", 403, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Permission denied to append to file"}), 403
            except Exception as e:
                log_api_request("/api/append", "POST", 500, ip_address, user_agent)
                logging.error(f"Error appending to file: {str(e)}\n{traceback.format_exc()}")
                return jsonify({"status": "error", "message": str(e)}), 500
                
        except Exception as e:
            log_api_request("/api/append", "POST", 400, ip_address, user_agent)
            logging.error(f"Error processing append request: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"status": "error", "message": "Invalid request format"}), 400
    
    @app.route("/api/health", methods=["GET"])
    def health_check():
        """API endpoint to check system health."""
        return jsonify({
            "status": "healthy",
            "message": "Nepantla API is operational",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        
    @app.route("/api/generate", methods=["POST"])
    def generate_module():
        """API endpoint to generate scaffolding for a new module file."""
        # Get client information for logging
        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")
        
        # Verify API key
        if not verify_api_key():
            log_api_request("/api/generate", "POST", 403, ip_address, user_agent)
            return jsonify({"error": "unauthorized", "message": "Invalid or missing API key"}), 403

        # Get request data
        try:
            data = request.get_json()
            if not data:
                log_api_request("/api/generate", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400
                
            module = data.get("module")
            module_type = data.get("type", "backend")  # Default to backend
            filename = data.get("filename")
            
            # Validate required fields
            if not module:
                log_api_request("/api/generate", "POST", 400, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Module name is required"}), 400
                
            if not filename:
                # Generate a default filename based on module name
                filename = f"{module}.py"
            
            # Security check to prevent path traversal attacks
            normalized_path = os.path.normpath(filename)
            if normalized_path.startswith("..") or normalized_path.startswith("/"):
                log_api_request("/api/generate", "POST", 403, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Invalid filename path"}), 403
            
            # Generate template content based on module type
            template_content = get_template_for_module(module, module)
            
            # Write content to file
            try:
                # Ensure directory exists
                directory = os.path.dirname(filename)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    
                file_exists = os.path.exists(filename)
                
                # Only write if file doesn't exist or we're explicitly allowed to overwrite
                if not file_exists or data.get("overwrite", False):
                    with open(filename, "w") as f:
                        f.write(template_content)
                    
                    # Update file record in database
                    update_file_record(filename)
                    
                    status_message = f"{'Created' if not file_exists else 'Overwritten'} module {module} in {filename}"
                    
                    log_api_request("/api/generate", "POST", 200, ip_address, user_agent)
                    return jsonify({
                        "status": "success", 
                        "message": status_message,
                        "filename": filename,
                        "content_preview": template_content[:100] + "..." if len(template_content) > 100 else template_content,
                        "timestamp": datetime.datetime.utcnow().isoformat()
                    })
                else:
                    log_api_request("/api/generate", "POST", 409, ip_address, user_agent)
                    return jsonify({
                        "status": "error", 
                        "message": f"File {filename} already exists. Set 'overwrite': true to replace it."
                    }), 409
                    
            except PermissionError:
                log_api_request("/api/generate", "POST", 403, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Permission denied to write file"}), 403
            except Exception as e:
                log_api_request("/api/generate", "POST", 500, ip_address, user_agent)
                logging.error(f"Error writing module file: {str(e)}\n{traceback.format_exc()}")
                return jsonify({"status": "error", "message": str(e)}), 500
                
        except Exception as e:
            log_api_request("/api/generate", "POST", 400, ip_address, user_agent)
            logging.error(f"Error processing generate request: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"status": "error", "message": "Invalid request format"}), 400
            
    @app.route("/api/list", methods=["GET", "POST"])
    def list_files():
        """API endpoint to list files in the specified directory."""
        # Get client information for logging
        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent", "")
        
        # Verify API key
        if not verify_api_key():
            log_api_request("/api/list", request.method, 403, ip_address, user_agent)
            return jsonify({"error": "unauthorized", "message": "Invalid or missing API key"}), 403

        try:
            # Handle both GET and POST requests
            if request.method == "POST":
                data = request.get_json()
                if not data:
                    log_api_request("/api/list", "POST", 400, ip_address, user_agent)
                    return jsonify({"status": "error", "message": "No JSON data provided"}), 400
                    
                directory = data.get("directory", ".")
                pattern = data.get("pattern")  # Optional file pattern to filter by
                recursive = data.get("recursive", False)  # Whether to search recursively
            else:  # GET request
                directory = request.args.get("directory", ".")
                pattern = request.args.get("pattern")
                recursive_param = request.args.get("recursive", "false").lower()
                recursive = recursive_param in ["true", "1", "yes"]
            
            # Validate and normalize directory path
            normalized_path = os.path.normpath(directory)
            if normalized_path.startswith("..") or normalized_path.startswith("/"):
                log_api_request("/api/list", request.method, 403, ip_address, user_agent)
                return jsonify({"status": "error", "message": "Invalid directory path"}), 403
            
            # Ensure the directory exists
            if not os.path.exists(normalized_path):
                log_api_request("/api/list", request.method, 404, ip_address, user_agent)
                return jsonify({
                    "status": "error", 
                    "message": f"Directory '{normalized_path}' not found"
                }), 404
                
            if not os.path.isdir(normalized_path):
                log_api_request("/api/list", request.method, 400, ip_address, user_agent)
                return jsonify({
                    "status": "error", 
                    "message": f"Path '{normalized_path}' is not a directory"
                }), 400
            
            # List files
            file_list = []
            
            import fnmatch
            
            def should_include(filename):
                """Check if a file matches the pattern filter."""
                if not pattern:
                    return True
                return fnmatch.fnmatch(filename, pattern)
            
            if recursive:
                # Walk directory recursively
                for root, dirs, files in os.walk(normalized_path):
                    # Calculate relative path to the starting directory
                    rel_path = os.path.relpath(root, normalized_path)
                    rel_path = "" if rel_path == "." else rel_path
                    
                    for file in files:
                        if should_include(file):
                            file_path = os.path.join(rel_path, file) if rel_path else file
                            file_info = get_file_info(os.path.join(root, file), file_path)
                            file_list.append(file_info)
            else:
                # List only files in the specified directory
                for item in os.listdir(normalized_path):
                    full_path = os.path.join(normalized_path, item)
                    if os.path.isfile(full_path) and should_include(item):
                        file_info = get_file_info(full_path, item)
                        file_list.append(file_info)
            
            # Log successful request
            log_api_request("/api/list", request.method, 200, ip_address, user_agent)
            
            # Return the list of files
            return jsonify({
                "status": "success",
                "directory": normalized_path,
                "file_count": len(file_list),
                "files": file_list,
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            log_api_request("/api/list", request.method, 500, ip_address, user_agent)
            logging.error(f"Error listing files: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/docs", methods=["GET"])
    def api_docs():
        """API documentation endpoint."""
        # This could be expanded with full OpenAPI/Swagger docs in the future
        api_routes = {
            "/api/write": {
                "methods": ["POST"],
                "description": "Write content to a file",
                "authentication": "Bearer token required",
                "params": {
                    "filename": "Path to the file to write",
                    "content": "Content to write to the file"
                },
                "responses": {
                    "200": "Success - File updated",
                    "400": "Bad request - Missing or invalid parameters",
                    "403": "Unauthorized - Invalid API key or permission denied",
                    "500": "Server error - Failed to write file"
                }
            },
            "/api/append": {
                "methods": ["POST"],
                "description": "Append content to a file",
                "authentication": "Bearer token required",
                "params": {
                    "filename": "Path to the file to append to",
                    "content": "Content to append to the file"
                },
                "responses": {
                    "200": "Success - Content appended to file",
                    "400": "Bad request - Missing or invalid parameters",
                    "403": "Unauthorized - Invalid API key or permission denied",
                    "500": "Server error - Failed to append to file"
                }
            },
            "/api/generate": {
                "methods": ["POST"],
                "description": "Generate a new module file with scaffolding",
                "authentication": "Bearer token required",
                "params": {
                    "module": "Name of the module to generate (e.g., 'google_docs_handler', 'journal_tracker')",
                    "type": "Type of module (default: 'backend')",
                    "filename": "Path to save the file (default: <module_name>.py)",
                    "overwrite": "Boolean to allow overwriting existing files (default: false)"
                },
                "responses": {
                    "200": "Success - Module file created",
                    "400": "Bad request - Missing or invalid parameters",
                    "403": "Unauthorized - Invalid API key or permission denied",
                    "409": "Conflict - File already exists",
                    "500": "Server error - Failed to generate module"
                }
            },
            "/api/list": {
                "methods": ["GET", "POST"],
                "description": "List files in a directory with optional filtering",
                "authentication": "Bearer token required",
                "params": {
                    "directory": "Directory path to list files from (default: current directory)",
                    "pattern": "Optional file pattern to filter by (e.g., '*.py')",
                    "recursive": "Boolean to search directories recursively (default: false)"
                },
                "responses": {
                    "200": "Success - File list returned",
                    "400": "Bad request - Invalid parameters",
                    "403": "Unauthorized - Invalid API key or permission denied",
                    "404": "Not found - Directory does not exist",
                    "500": "Server error - Failed to list files"
                }
            },
            "/api/health": {
                "methods": ["GET"],
                "description": "Check API health status",
                "authentication": "None",
                "responses": {
                    "200": "Success - API is operational"
                }
            },
            "/api/docs": {
                "methods": ["GET"],
                "description": "This documentation endpoint",
                "authentication": "None",
                "responses": {
                    "200": "Success - Documentation returned"
                }
            }
        }
        
        return jsonify({
            "name": "Nepantla Mental Health System API",
            "version": "1.0.0",
            "description": "API for the Nepantla mental health system, enabling AI agent Amaru to interact with the codebase",
            "endpoints": api_routes
        })
