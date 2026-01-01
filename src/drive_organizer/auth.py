import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service(credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
    creds = None
    # convert to path obj for easier handling
    credentials_file = Path(credentials_path)
    token_file = Path(token_path)

    # check if we have saved token
    if token_file.exists():
        print("Found existing token, loading...")
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # it token exists but expired then refresh it
    # if no token or refresh fails, then start fresh OAuth flow
    if not creds or not creds.valid:
        # if we have expired credentials, try to refresh them
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                creds = None

        if not creds:
            if not credentials_file.exists():
                raise FileNotFoundError(f"Credentials file '{credentials_path}' not found." "Download it from Google Cloud Console → APIs & Services → Credentials")
            
            print("\nStarting OAuth flow...")
            print("A browser window will open. Please log in and grant access.\n")

            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            creds = flow.run_local_server(port=0)
            # save the credentials for next time
            print("Saving new token...")
            with open(token_file, 'w') as token:
                token.write(creds.to_json())

    # build and return API service
    print("Building Google Drive service...")
    service = build('drive', 'v3', credentials=creds)
    print("Successfully authenticated with Google Drive!\n")
    return service


if __name__ == "__main__":
    # quick test of the authentication
    print("=" * 50)
    print("Google Drive Authentication Test")
    print("=" * 50 + "\n")
    
    try:
        service = get_drive_service()
        
        # simple API call to verify - get info about the user's Drive
        about = service.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress', 'Unknown')
        
        print(f"Authenticated as: {user_email}")
        print("\n✓ Authentication successful!")
        
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise