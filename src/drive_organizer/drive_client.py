from typing import Optional
from googleapiclient.discovery import Resource

MIME_TYPE_FOLDER = 'application/vnd.google-apps.folder'
MIME_TYPE_DOCUMENT = 'application/vnd.google-apps.document'
MIME_TYPE_SPREADSHEET = 'application/vnd.google-apps.spreadsheet'
MIME_TYPE_PRESENTATION = 'application/vnd.google-apps.presentation'

# extract text snippet from file content
def get_file_content_snippet(service: Resource, file: dict, max_chars: int = 500) -> Optional[str]:
    file_id = file.get('id')
    mime_type = file.get('mimeType', '')
    file_name = file.get('name', 'Unknown')
    
    try:
        # google Docs, Sheets, Slides can be exported as plain text
        if mime_type == MIME_TYPE_DOCUMENT:
            # export Google Doc as plain text
            content = service.files().export(
                fileId=file_id,
                mimeType='text/plain'
            ).execute()
            
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            return content[:max_chars] if content else None
            
        elif mime_type == MIME_TYPE_SPREADSHEET:
            # export Google Sheet as CSV (1st sheet only)
            content = service.files().export(
                fileId=file_id,
                mimeType='text/csv'
            ).execute()
            
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            return content[:max_chars] if content else None
            
        elif mime_type == MIME_TYPE_PRESENTATION:
            # export Google Slides as plain text
            content = service.files().export(
                fileId=file_id,
                mimeType='text/plain'
            ).execute()
            
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            return content[:max_chars] if content else None
        
        return None
        
    except Exception as e:
        return None

# generic function to list files with pagination support
def list_files(service: Resource, page_size: int = 100, query: Optional[str] = None):
    all_files = []
    page_token = None
    # specify the fields we want to retrieve
    fields = "nextPageToken, files(id, name, mimeType, parents, createdTime, modifiedTime)"
    print("Fetching files from Google Drive...")

    while True:
        #build API request
        request_params = {
            'pageSize': page_size,
            'fields': fields,
            'pageToken': page_token
        }

        if query:
            request_params['q'] = query
        
        # execute the request
        results = service.files().list(**request_params).execute()
        files = results.get('files', [])
        all_files.extend(files)
        # check if there are more pages
        page_token = results.get('nextPageToken')

        if not page_token:
            break

        print(f"  Fetched {len(all_files)} files so far...")

    print(f"Total files fetched: {len(all_files)}")
    return all_files

# get all folders in user's drive
def get_folders(service: Resource):
    print("Fetching existing folders...")
    # filter to only get folders
    query = f"mimeType = '{MIME_TYPE_FOLDER}' and trashed = false"
    folders = list_files(service, query=query)
    return folders

# get files in root drive
def get_loose_files(service: Resource):
    print("Finding loose (unorganized) files...")
    query = (
        "'root' in parents and "
        f"mimeType != '{MIME_TYPE_FOLDER}' and "
        "trashed = false"
    )
    loose_files = list_files(service, query=query)
    return loose_files

# get only top level folders (those in root)
def get_root_folders(service: Resource):
    print("Fetching top-level fodlers...")
    query = (
        f"mimeType = '{MIME_TYPE_FOLDER}' and "
        "'root' in parents and "
        "trashed = false"
    )
    root_folders = list_files(service, query=query)
    return root_folders

# debugging: print summary of files
def print_file_summary(files: list[dict], title: str = "Files"):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

    if not files:
        print(" (none)")
        return 
    
    # group files by type
    type_counts = {}
    for f in files:
        mime = f.get('mimeType', 'unknown')
        if 'folder' in mime:
            simple_type = 'Folder'
        elif 'document' in mime:
            simple_type = 'Google Doc'
        elif 'spreadsheet' in mime:
            simple_type = 'Google Sheet'
        elif 'presentation' in mime:
            simple_type = 'Google Slides'
        elif 'pdf' in mime:
            simple_type = 'PDF'
        elif 'image' in mime:
            simple_type = 'Image'
        else:
            simple_type = mime.split('/')[-1][:20]
        
        type_counts[simple_type] = type_counts.get(simple_type, 0) + 1

    print(f"\n  Total: {len(files)} items\n")
    print("  By type:")
    for file_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {file_type}: {count}")
    
    # show first 10 files as sample
    print(f"\n  First {min(10, len(files))} items:")
    for f in files[:10]:
        name = f.get('name', 'Untitled')
        # truncate long names
        if len(name) > 45:
            name = name[:42] + '...'
        print(f"    • {name}")
    
    if len(files) > 10:
        print(f"    ... and {len(files) - 10} more")
    
    print()



if __name__ == "__main__":
    # import our auth module
    from auth import get_drive_service
    
    print("=" * 60)
    print(" Google Drive Explorer")
    print("=" * 60 + "\n")
    
    # authenticate
    service = get_drive_service()
    
    # get and display root folders
    folders = get_root_folders(service)
    print_file_summary(folders, "Your Top-Level Folders")
    
    # get and display loose files
    loose = get_loose_files(service)
    print_file_summary(loose, "Loose Files (need organizing)")
    
    # summary
    print("=" * 60)
    print(" Summary")
    print("=" * 60)
    print(f"\n  You have {len(folders)} top-level folders")
    print(f"  You have {len(loose)} loose files that could be organized\n")
    
    if loose:
        print("  These loose files are what we'll help you organize!")
    else:
        print("  Your Drive is already well organized! 🎉")
