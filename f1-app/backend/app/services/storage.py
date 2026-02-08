from google.cloud import storage
import uuid
import os

BUCKET_NAME = "f1-data-library"

from datetime import datetime

def upload_file(file_obj, filename: str, subfolder: str = "misc", use_timestamp: bool = False) -> str:
    """
    Uploads a file-like object to GCS and returns the gs:// URI.
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        
        if use_timestamp:
            # Format: YYYYMMDD_HHMMSS_<filename>
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize filename just in case
            safe_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in (' ', '.', '_')]).strip().replace(' ', '_')
            blob_name = f"uploads/{subfolder}/{timestamp}_{safe_filename}"
        else:
            # Create a unique path to avoid collisions
            unique_id = str(uuid.uuid4())
            blob_name = f"uploads/{subfolder}/{unique_id}/{filename}"
        
        blob = bucket.blob(blob_name)
        # Upload from file object (ensure start of file)
        file_obj.seek(0)
        blob.upload_from_file(file_obj)
        
        return f"gs://{BUCKET_NAME}/{blob_name}"
        
    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        raise

def list_files(subfolder: str = "uploads/dashboard") -> list:
    """
    Lists files in a specific GCS subfolder.
    Returns a list of dicts: {'name': str, 'uri': str, 'created': datetime}
    """
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=subfolder)
        
        files = []
        for blob in blobs:
            if blob.name.endswith("/"): # Skip directories
                continue
                
            files.append({
                "name": os.path.basename(blob.name),
                "full_path": blob.name,
                "uri": f"gs://{BUCKET_NAME}/{blob.name}",
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None
            })
            
        # Sort by creation time desc
        files.sort(key=lambda x: x['created'] or "", reverse=True)
        return files
        
    except Exception as e:
        print(f"Error listing GCS files: {e}")
        return []
