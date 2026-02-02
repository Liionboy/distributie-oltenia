import requests
import re
import json
import logging
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

class DEOPortal:
    """Interface for Distributie Oltenia Portal."""

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://portal.distributieoltenia.ro/"
        })
        self.base_url = "https://portal.distributieoltenia.ro"
        self.logged_in = False

    def login(self):
        """Perform login using Keycloak/Laravel flow."""
        try:
            # 1. Get initial login page to get Keycloak redirect URL
            # The /login route seems to fail with 500, but /loginuserkeycloak redirects to auth
            # We add user_type=end_client to avoid the role selection page
            login_url = f"{self.base_url}/loginuserkeycloak?user_type=end_client"
            _LOGGER.debug(f"Visiting login entry point: {login_url}")
            r = self.session.get(login_url)
            
            _LOGGER.debug(f"Redirected to: {r.url}")
            if "keycloak" not in r.url and "auth.distributieoltenia" not in r.url:
                _LOGGER.error(f"Initial login didn't redirect to Keycloak. Current URL: {r.url}")
                with open("login_dump.html", "w", encoding="utf-8") as f:
                    f.write(r.text)
                print("DEBUG: Dumped login page to login_dump.html")
                return False

            # 2. Extract Keycloak login form action and fields
            soup = BeautifulSoup(r.text, "html.parser")
            login_form = soup.find("form", id="kc-form-login")
            if not login_form:
                _LOGGER.error("Could not find Keycloak login form")
                return False

            action_url = login_form.get("action")
            _LOGGER.debug(f"Keycloak form action: {action_url}")
            
            payload = {
                "username": self.email,
                "password": self.password,
                "credentialId": ""
            }

            # 3. Post login to Keycloak
            _LOGGER.debug(f"Posting to Keycloak action: {action_url}")
            r = self.session.post(action_url, data=payload, allow_redirects=True)
            
            # 4. Check if we are back at the portal and authenticated
            # We look for common markers of being logged in
            is_authenticated = (
                "checklogout" in r.text.lower() or 
                "deconectare" in r.text.lower() or
                "utilizator:" in r.text.lower() or
                "dashboard" in r.url.lower() or
                "istoric" in r.text.lower()
            )

            if is_authenticated:
                self.logged_in = True
                _LOGGER.info("Login successful")
                return True
            
            _LOGGER.error(f"Login failed. Final URL: {r.url}")
            # Log a bit of the response for debugging
            _LOGGER.debug(f"Response preview: {r.text[:2000]}")
            return False

        except Exception as e:
            _LOGGER.exception(f"Exception during login: {e}")
            return False

    def get_consumption_data(self):
        """Fetch consumption data from the portal."""
        if not self.logged_in:
            if not self.login():
                return None

        try:
            # 1. First we need to get the POD token
            # We revisit the home page which should redirect us to the correct context (e.g. end_client list with a temp token)
            pages_to_check = [
                f"{self.base_url}/", 
                # Other pages might be useful if strictly on dashboard
                f"{self.base_url}/pages/dashboard"
            ]

            token = None
            for page in pages_to_check:
                _LOGGER.debug(f"Checking page for token: {page}")
                r = self.session.get(page)
                
                # Update current page URL after redirects
                print(f"DEBUG: Landed on URL: {r.url}")
                
                # Check if the token is in the URL (e.g. redirected to ...?token=XYZ)
                url_token_match = re.search(r'token=([^"\'\s&>]+)', r.url)
                if url_token_match:
                    possible_token = url_token_match.group(1)
                    # If this is the "partner" token (short), it might not be the POD token
                    # But if it's the only one we have, we might log it.
                    _LOGGER.debug(f"Found token in URL of {page}: {possible_token}")
                    
                # Parse links on the page
                soup = BeautifulSoup(r.text, "html.parser")
                links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
                _LOGGER.debug(f"Found {len(links)} links on page {page}.")
                
                # Log links for debugging
                for l in links:
                    if "token=" in l or "istoric" in l or "dashboard" in l:
                         _LOGGER.debug(f"  Interesting link: {l}")

                # Search for the "Select" or "Vezi detalii" link for a POD
                # Usually sends to /pages/dashboard?token=... or istoricIndecsi?token=...
                # We look for a link containing 'token=' and maybe 'dashboard' or just a long token
                
                # Regex for a link with a token
                link_token_match = re.search(r'(?:dashboard|istoricIndecsi|consumul-meu).*?token=([^"\'\s&>]+)', r.text)
                if link_token_match:
                    token = link_token_match.group(1)
                    _LOGGER.debug(f"Found POD token in link on {page}: {token[:20]}...")
                    break
                
                # Fallback: look for "Selectati" link robustly
                if not token:
                    # Specific POD provided by user or found in previous logs
                    target_pod = "59401020000424868771667067"
                    
                    # Dump page for debugging
                    with open("page_dump.html", "w", encoding="utf-8") as f:
                        f.write(r.text)

                    # Try to find the POD in the text and get the link nearby
                    if target_pod in r.text:
                         print(f"DEBUG: Found target POD {target_pod} in page.")
                         # Use regex to find the link that follows the POD or is in the same row
                         # Look for token=... after the POD
                         pod_token_match = re.search(target_pod + r'.*?token=([^"\'\s&>]+)', r.text, re.DOTALL)
                         if pod_token_match:
                             token = pod_token_match.group(1)
                             print(f"DEBUG: Extracted token via POD match: {token}")
                             _LOGGER.debug(f"Found POD token via POD match: {token[:20]}...")
                             break
                    
                    # Search for any link containing "Selecta" to handle diacritics/whitespace
                    select_link = soup.find("a", string=lambda t: t and "Selecta" in t)
                    if not select_link:
                         select_link = soup.find("a", href=re.compile(r"token="))
                    
                    if select_link and select_link.get("href"):
                         href = select_link.get("href")
                         print(f"DEBUG: Found likely Selectati link: {href}")
                         link_token_match = re.search(r'token=([^"\'\s&>]+)', href)
                         if link_token_match:
                            token = link_token_match.group(1)
                            print(f"DEBUG: Extracted token: {token}")
                            _LOGGER.debug(f"Found POD token in 'Selectati' link: {token[:20]}...")
                            break
                    else:
                        print("DEBUG: No 'Selectati' link found.")
                        # Print all links to debug
                        for a in soup.find_all("a", href=True):
                            print(f"DEBUG: Link: {a.text.strip()} -> {a['href']}")

            if not token:
                _LOGGER.error("Could not find POD token on any of the checked pages")
                
                # Check directly on dashboard or consumul-meu - sometimes we are already redirected?
                fallback_pages = [
                    f"{self.base_url}/pages/consumul-meu",
                    f"{self.base_url}/pages/dashboard"
                ]
                for fb in fallback_pages:
                    _LOGGER.debug(f"Fallback check: {fb}")
                    r = self.session.get(fb)
                    # Look for token in URL or content
                    match = re.search(r'token=([^"\'\s&>]+)', r.url)
                    if match:
                        token = match.group(1)
                        _LOGGER.debug(f"Found token on fallback page {fb}: {token}")
                        break
                    match = re.search(r'token=([^"\'\s&>]+)', r.text)
                    if match:
                        token = match.group(1)
                        _LOGGER.debug(f"Found token in content of fallback page {fb}: {token}")
                        break

            if not token:
                _LOGGER.warning("Token extraction failed. Using hardcoded token provided by user for testing.")
                token = "eyJfX21ldGFkYXRhIjp7ImlkIjoiaHR0cDovL3NhcGd3cDAwOjgwMDAvc2FwL29wdS9vZGF0YS9zYXAvWkRDUF9TUlYvQlBfUFJFTUlTRVNTZXQoJzU5NDAxMDIwMDAwNDI0ODY4NzcxNjY3MDY3JykiLCJ1cmkiOiJodHRwOi8vc2FwZ3dwMDA6ODAwMC9zYXAvb3B1L29kYXRhL3NhcC9aRENQX1NSVi9CUF9QUkVNSVNFU1NldCgnNTk0MDEwMjAwMDA0MjQ4Njg3NzE2NjcwNjcnKSIsInR5cGUiOiJaRENQX1NSVi5CUF9QUkVNSVNFUyJ9LCJOQU1FX0ZJUlNUIjoiQURSSUFOIE5JQ09MQUUiLCJOQU1FX0xBU1QiOiJCUklTQ0EiLCJOQU1FX09SRyI6IiIsIlBPRF9MT05HIjoiNTk0MDEwMjAwMDA0MjQ4Njg3NzE2NjcwNjciLCJJRE5VTSI6IjE4OTAyMTkwMzAwNDkiLCJQUkVNSVNFIjoiNTE4NDY5MTUiLCJQQVJUTkVSIjoiOTE5NDQyMDIiLCJTTVRQX0FERFIiOiJhZHJpYW4uYnJpc2NhQGdtYWlsLmNvbSIsIlRFTF9OVU1CRVIiOiIwNzQ1OTg1Mzk1IiwiQUREUl9OVU0iOiIyMTVCIiwiQUREUl9TVFJFRVQiOiJJWlZPUlVMVUkiLCJBRERSX0ZMT09SIjoiIiwiQUREUl9DSVRZMiI6IiIsIkFERFJfQlVJTERJTkciOiIiLCJBRERSX1NQUEwxIjoiIiwiQUREUl9ST09NTlVNQkVSIjoiIiwiZGV0YWlsX3VybCI6Imh0dHA6Ly9wb3J0YWwuZGlzdHJpYnV0aWVvbHRlbmlhLnJvL3BhZ2VzL2luZm9ybWF0aWlDb250cmFjdD9wb2Q9NTk0MDEwMjAwMDA0MjQ4Njg3NzE2NjcwNjcifQ=="
            
            if not token:
                # Log a bit of the home page to see what's actually there
                r = self.session.get(f"{self.base_url}/")
                _LOGGER.debug(f"Home page preview: {r.text[:2000]}")
                return None
            
            history_url = f"{self.base_url}/pages/istoricIndecsi?token={token}"
            _LOGGER.debug(f"Fetching history from: {history_url}")

            # 2. Go to history page
            r = self.session.get(history_url)
            
            # 3. Extract the 'data' variable from the script
            # Looking for: let data = [...]; or var data = [...];
            data_match = re.search(r'(?:let|var)\s+data\s*=\s*(\[.*?\]);', r.text, re.DOTALL)
            if not data_match:
                _LOGGER.error("Could not find consumption data in page source")
                print(f"DEBUG: Could not find 'var data' in history page. Size: {len(r.text)}")
                with open("history_dump.html", "w", encoding="utf-8") as f:
                    f.write(r.text)
                print("DEBUG: Dumped history page to history_dump.html")
                return None
            
            raw_data = data_match.group(1)
            # SAP JSON sometimes has escaping or dates in /Date(123)/ format
            # We might need to pre-process it if json.loads fails
            try:
                data = json.loads(raw_data)
                print("DEBUG: Successfully parsed JSON data!")
            except json.JSONDecodeError:
                # Try simple cleanup for JS format
                _LOGGER.warning("JSON decode failed, attempting cleanup")
                # Remove common JS-isms (though let's hope it's clean JSON)
                data = json.loads(raw_data.replace('\\/', '/'))
                
            return data

        except Exception as e:
            _LOGGER.exception(f"Exception fetching consumption data: {e}")
            return None

if __name__ == "__main__":
    # Test script - enter credentials to test manually
    import os
    logging.basicConfig(level=logging.DEBUG)
    # email = input("Email: ")
    # password = input("Password: ")
    email = "adrian.brisca@gmail.com"
    password = "Putrigai12@"
    
    portal = DEOPortal(email, password)
    if portal.login():
        data = portal.get_consumption_data()
        if data:
            print(json.dumps(data, indent=2))
        else:
            print("Failed to fetch data")
    else:
        print("Login failed")
