import requests
from src.utils import logger

class GitHubClient:
    def __init__(self, repo, token=None, timeout=5000):
        self.repo = repo
        self.token = token
        self.timeout = timeout / 1000.0  # Convert to seconds

    def get_latest_release(self):
        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            tag_name = data.get("tag_name")
            name = data.get("name")
            html_url = data.get("html_url")
            
            # Remove 'v' prefix if present for cleaner version string
            version = tag_name
            if version and version.startswith('v'):
                version = version[1:]
            
            # Fallback to name if tag_name is missing
            if not version and name:
                version = name
            
            return {
                "version": version,
                "tag_name": tag_name,
                "release_url": html_url,
                "published_at": data.get("published_at")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching latest release from GitHub: {e}")
            return None
