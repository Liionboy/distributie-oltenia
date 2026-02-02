import requests
import re
import json
import logging
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

class DEOPortal:
    """Interface for Distributie Oltenia Portal."""

    def __init__(self, email, password, token=None):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://portal.distributieoltenia.ro/"
        })
        self.base_url = "https://portal.distributieoltenia.ro"
        self.logged_in = False
        self.token = token  # Allow passing a known token

    def login(self):
        """Perform login using Keycloak/Laravel flow."""
        try:
            # 1. Get initial login page to get Keycloak redirect URL
            login_url = f"{self.base_url}/loginuserkeycloak?user_type=end_client"
            _LOGGER.debug(f"Visiting login entry point: {login_url}")
            r = self.session.get(login_url)
            
            if "keycloak" not in r.url and "auth.distributieoltenia" not in r.url:
                _LOGGER.error(f"Initial login didn't redirect to Keycloak. Current URL: {r.url}")
                return False

            # 2. Extract Keycloak login form action and fields
            soup = BeautifulSoup(r.text, "html.parser")
            login_form = soup.find("form", id="kc-form-login")
            if not login_form:
                _LOGGER.error("Could not find Keycloak login form")
                return False

            action_url = login_form.get("action")
            
            payload = {
                "username": self.email,
                "password": self.password,
                "credentialId": ""
            }

            # 3. Post login to Keycloak
            r = self.session.post(action_url, data=payload, allow_redirects=True)
            
            # 4. Check if we are back at the portal and authenticated
            is_authenticated = (
                "checklogout" in r.text.lower() or 
                "deconectare" in r.text.lower() or
                "utilizator:" in r.text.lower() or
                "dashboard" in r.url.lower() or
                "istoric" in r.text.lower()
            )

            if is_authenticated:
                self.logged_in = True
                _LOGGER.debug("Login successful")
                return True
            
            _LOGGER.error(f"Login failed. Final URL: {r.url}")
            return False

        except Exception as e:
            _LOGGER.exception(f"Exception during login: {e}")
            return False

    def get_token(self):
        """Attempt to discover the POD token."""
        # Check commonly used page for redirection or content
        pages_to_check = [
            f"{self.base_url}/", 
            f"{self.base_url}/pages/dashboard",
            f"{self.base_url}/pages/consumul-meu"
        ]

        token = None
        for page in pages_to_check:
            r = self.session.get(page)
            
            # Check URL for token
            match = re.search(r'token=([^"\'\s&>]+)', r.url)
            if match:
                token = match.group(1)
                _LOGGER.debug(f"Found token in URL of {page}")
                return token
                
            # Check content for token links
            match = re.search(r'token=([^"\'\s&>]+)', r.text)
            if match:
                token = match.group(1)
                _LOGGER.debug(f"Found token in content of {page}")
                return token
        
        return None

    def get_consumption_data(self):
        """Fetch consumption data from the portal."""
        if not self.logged_in:
            if not self.login():
                return None

        try:
            # Use configured token if available, otherwise try to find it
            token = self.token
            if not token:
                token = self.get_token()
            
            if not token:
                _LOGGER.error("Could not find token and none provided in config.")
                return None
            
            history_url = f"{self.base_url}/pages/istoricIndecsi?token={token}"
            _LOGGER.debug(f"Fetching history from: {history_url}")

            r = self.session.get(history_url)
            
            # Extract 'data' variable
            data_match = re.search(r'(?:let|var)\s+data\s*=\s*(\[.*?\]);', r.text, re.DOTALL)
            if not data_match:
                _LOGGER.error("Could not find consumption data in page source")
                return None
            
            raw_data = data_match.group(1)
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                _LOGGER.warning("JSON decode failed, attempting cleanup")
                data = json.loads(raw_data.replace('\\/', '/'))
                
            return data

        except Exception as e:
            _LOGGER.exception(f"Exception fetching consumption data: {e}")
            return None
