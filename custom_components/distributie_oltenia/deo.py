import requests
import re
import json
import logging
from urllib.parse import quote
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

class DEOPortal:
    """Interface for Distributie Oltenia Portal."""

    def __init__(self, email, password, token=None, pod=None):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://portal.distributieoltenia.ro/",
            "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        self.base_url = "https://portal.distributieoltenia.ro"
        self.logged_in = False
        self.token = token
        self.pod = pod

    def login(self):
        """Perform login using Keycloak/Laravel flow."""
        try:
            login_url = f"{self.base_url}/loginuserkeycloak?user_type=end_client"
            _LOGGER.warning(f"DEO: Starting login...")
            r = self.session.get(login_url)
            
            if "keycloak" not in r.url and "auth.distributieoltenia" not in r.url:
                _LOGGER.error(f"DEO: Login redirect failed. URL: {r.url}")
                return False

            soup = BeautifulSoup(r.text, "html.parser")
            login_form = soup.find("form", id="kc-form-login")
            if not login_form:
                _LOGGER.error("DEO: Could not find login form")
                return False

            action_url = login_form.get("action")
            payload = {
                "username": self.email,
                "password": self.password,
                "credentialId": ""
            }

            r = self.session.post(action_url, data=payload, allow_redirects=True)
            
            if "roleForm" in r.text or "user_type" in r.text:
                _LOGGER.warning("DEO: Role selection required, navigating to /client...")
                r = self.session.get(f"{self.base_url}/client", allow_redirects=True)
            
            is_authenticated = any(m in r.text.lower() for m in ["checklogout", "deconectare", "utilizator:", "istoric"]) or "dashboard" in r.url.lower()

            if is_authenticated:
                self.logged_in = True
                _LOGGER.warning("DEO: Login successful!")
                return True
            
            _LOGGER.error(f"DEO: Login failed at {r.url}")
            return False

        except Exception as e:
            _LOGGER.exception(f"DEO: Login exception: {e}")
            return False

    def get_token(self):
        """Discover POD token. Real tokens are >50 chars."""
        MIN_TOKEN_LENGTH = 50
        
        pages = [
            f"{self.base_url}/pages/consumption-location/end_client",
        ]
        
        all_tokens_found = []

        for page in pages:
            _LOGGER.warning(f"DEO: Checking page: {page}")
            try:
                r = self.session.get(page)
                _LOGGER.warning(f"DEO: Landed on: {r.url[:80]} (status {r.status_code})")
                
                # Log page size and snippet for debugging
                _LOGGER.warning(f"DEO: Page size: {len(r.text)} chars")
                
                # Search ENTIRE HTML for token= pattern (not just <a> tags)
                all_token_matches = re.findall(r'token=([^&\s"\'<>]{10,})', r.text)
                _LOGGER.warning(f"DEO: Found {len(all_token_matches)} token patterns in HTML")
                
                for token in all_token_matches:
                    all_tokens_found.append((len(token), token[:30]))
                    if len(token) >= MIN_TOKEN_LENGTH:
                        _LOGGER.warning(f"DEO: Found VALID token (len={len(token)})")
                        return token
                
                # If no tokens found, log a snippet of the page to see what's there
                if not all_token_matches:
                    # Look for common patterns
                    if "pod" in r.text.lower() or "POD" in r.text:
                        _LOGGER.warning("DEO: Page contains 'POD' references")
                    if "istoric" in r.text.lower():
                        _LOGGER.warning("DEO: Page contains 'istoric' references")
                    # Log a snippet
                    snippet = r.text[0:500].replace('\n', ' ')
                    _LOGGER.warning(f"DEO: HTML start: {snippet}")
                    
            except Exception as e:
                _LOGGER.error(f"DEO: Failed to get {page}: {e}")
                continue
        
        if all_tokens_found:
            _LOGGER.error(f"DEO: Tokens found but too short: {all_tokens_found}")
        else:
            _LOGGER.error("DEO: No tokens found!")
        
        return None

    def get_consumption_data(self):
        """Fetch data with session priming."""
        if not self.logged_in and not self.login():
            _LOGGER.error("DEO: Login failed, cannot fetch data")
            return None

        try:
            # Use configured token if available (preferred - stable)
            token = None
            if self.token and len(self.token.strip()) > 50:
                token = self.token.strip()
                _LOGGER.warning(f"DEO: Using configured token (len={len(token)})")
            else:
                # Try to discover token
                _LOGGER.warning("DEO: No valid config token, attempting discovery...")
                token = self.get_token()
            
            if not token:
                _LOGGER.error("DEO: No token available! Please provide the long token in config.")
                return None
            
            token_preview = token[:30] if len(token) > 30 else token
            _LOGGER.warning(f"DEO: Using token: {token_preview}...")
            
            if self.pod:
                prime_url = f"{self.base_url}/pages/informatiiContract?pod={self.pod}"
                _LOGGER.warning(f"DEO: Priming session with POD page...")
                self.session.get(prime_url)

            encoded_token = quote(token, safe='')
            
            pages_to_try = [
                f"{self.base_url}/pages/istoricIndecsi?token={encoded_token}",
            ]
            
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": f"{self.base_url}/pages/dashboard"
            }
            
            r = None
            for page_url in pages_to_try:
                _LOGGER.warning(f"DEO: Fetching history page...")
                try:
                    r = self.session.get(page_url, headers=headers)
                    _LOGGER.warning(f"DEO: Got status: {r.status_code}")
                    if r.status_code == 200:
                        break
                    _LOGGER.error(f"DEO: Page returned {r.status_code}")
                except Exception as req_err:
                    _LOGGER.error(f"DEO: Request failed: {req_err}")
            
            if not r or r.status_code != 200:
                _LOGGER.error(f"DEO: History page failed")
                return None

            data_match = re.search(r'(?:let|var)\s+data\s*=\s*(\[.*?\]);', r.text, re.DOTALL)
            if not data_match:
                _LOGGER.error("DEO: No 'data' variable found in page")
                _LOGGER.warning(f"DEO: Page preview: {r.text[:300]}")
                return None
            
            try:
                return json.loads(data_match.group(1))
            except json.JSONDecodeError:
                return json.loads(data_match.group(1).replace('\\/', '/'))

        except Exception as e:
            _LOGGER.exception(f"DEO: Data fetch error: {e}")
            return None
