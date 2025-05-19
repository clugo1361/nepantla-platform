from flask import jsonify
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

    if not API_KEY:
        logging.error("API_KEY is not set in environment variables")
        return False

    if not req_key.startswith("Bearer "):
        return False

    token = req_key.split("Bearer ")[1]
    return token == API_KEY

def update_file_record(filename):
    try:
        file_record = CodeFile.query.filter_by(filename=filename).first()
        if file_record:
            file_record.last_modified = datetime.datetime.utcnow()
        else:
            file_record = CodeFile()
            file_record.filename = filename
            file_record.last_modified = datetime.datetime.utcnow()
            file_record.modified_by = "Amaru"
            db.session.add(file_record)
        db.session.commit()
    except Exception as e:
        logging.error(f"Failed to update file record: {e}")
        db.session.rollback()

def get_file_info(full_path, relative_path):
    try:
        stat_info = os.stat(full_path)
        _, ext = os.path.splitext(full_path)
        ext = ext[1:] if ext else ""
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
    if module_type == "google_docs_handler":
        return """import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'nepantla-service-account.json'

class GoogleDocsHandler:
    def __init__(self):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            self.docs_service = build('docs', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.is_connected = True
        except Exception as e:
            print(f"Error initializing Google Docs API: {e}")
            self.is_connected = False

    def create_document(self, title, content=""):
        if not self.is_connected:
            return {"error": "Not connected to Google Docs API"}
        try:
            document = self.docs_service.documents().create(body={"title": title}).execute()
            doc_id = document.get('documentId')
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
        if not self.is_connected:
            return {"error": "Not connected to Google Docs API"}
        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            end_index = document.get('body').get('content')[-1].get('endIndex')
            requests = [{
                'insertText': {
                    'location': {'index': end_index - 1},
                    'text': content
                }}]
            result = self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={'requests': requests}).execute()
            return {"status": "success", "message": f"Content added to document {doc_id}"}
        except Exception as e:
            return {"error": f"Failed to append to document: {str(e)}"}

    def share_document(self, doc_id, email, role='reader'):
        if not self.is_connected:
            return {"error": "Not connected to Google Docs API"}
        try:
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
            return {"status": "success", "message": f"Document shared with {email} as {role}"}
        except Exception as e:
            return {"error": f"Failed to share document: {str(e)}"}

if __name__ == "__main__":
    docs_handler = GoogleDocsHandler()
    new_doc = docs_handler.create_document("Test Document", "This is a test document created by Nepantla AI")
    print(new_doc)
"""
    elif module_type == "journal_tracker":
        return """# Auto-generated journal tracker module.

# Add your code here.
"""
    else:
        return f"# {module_name.replace('_', ' ').title()}\n\n'''\nAuto-generated module for {module_name}\n'''\n\n# Add your code here\n"

def setup_routes(app):
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "message": "Nepantla API is operational",
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
