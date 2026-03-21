import aiohttp
import asyncio
import re
import json
import logging
from urllib.parse import quote
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://portal.distributieoltenia.ro/",
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
}

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


def parse_european_number(val):
    """Parse European number format: 1.218,001 -> 1218.001"""
    if not val:
        return None
    try:
        return float(str(val).replace('.', '').replace(',', '.'))
    except (ValueError, TypeError):
        return val


class DEOPortal:
    """Interface for Distributie Oltenia Portal (async)."""

    def __init__(self, email, password, token=None, pod=None):
        self.email = email
        self.password = password
        self.base_url = "https://portal.distributieoltenia.ro"
        self.logged_in = False
        self.token = token
        self.pod = pod
        self._cookies = None

    async def _get_session(self):
        """Create an aiohttp session with stored cookies."""
        jar = aiohttp.CookieJar()
        if self._cookies:
            jar.update_cookies(self._cookies)
        return aiohttp.ClientSession(
            headers=DEFAULT_HEADERS,
            cookie_jar=jar,
            timeout=REQUEST_TIMEOUT,
        )

    async def login(self):
        """Perform login using Keycloak/Laravel flow."""
        try:
            async with aiohttp.ClientSession(
                headers=DEFAULT_HEADERS,
                timeout=REQUEST_TIMEOUT,
            ) as session:
                login_url = f"{self.base_url}/loginuserkeycloak?user_type=end_client"
                _LOGGER.debug("DEO: Starting login...")

                async with session.get(login_url, allow_redirects=True) as r:
                    final_url = str(r.url)
                    if "keycloak" not in final_url and "auth.distributieoltenia" not in final_url:
                        _LOGGER.error("DEO: Login redirect failed. URL: %s", final_url)
                        return False

                    text = await r.text()

                soup = BeautifulSoup(text, "html.parser")
                login_form = soup.find("form", id="kc-form-login")
                if not login_form:
                    _LOGGER.error("DEO: Could not find login form")
                    return False

                action_url = login_form.get("action")
                payload = {
                    "username": self.email,
                    "password": self.password,
                    "credentialId": "",
                }

                async with session.post(action_url, data=payload, allow_redirects=True) as r:
                    text = await r.text()

                if "roleForm" in text or "user_type" in text:
                    _LOGGER.debug("DEO: Role selection required, navigating to /client...")
                    async with session.get(f"{self.base_url}/client", allow_redirects=True) as r:
                        text = await r.text()

                is_authenticated = (
                    any(m in text.lower() for m in ["checklogout", "deconectare", "utilizator:", "istoric"])
                    or "dashboard" in str(r.url).lower()
                )

                if is_authenticated:
                    self.logged_in = True
                    # Store cookies for future requests
                    self._cookies = {}
                    for cookie in session.cookie_jar:
                        self._cookies[cookie.key] = cookie.value
                    _LOGGER.info("DEO: Login successful")
                    return True

                _LOGGER.error("DEO: Login failed at %s", r.url)
                return False

        except aiohttp.ClientError as e:
            _LOGGER.error("DEO: Login network error: %s", e)
            return False
        except asyncio.TimeoutError:
            _LOGGER.error("DEO: Login timed out")
            return False
        except Exception as e:
            _LOGGER.exception("DEO: Login exception: %s", e)
            return False

    async def get_token(self):
        """Discover POD token. Real tokens are >50 chars."""
        MIN_TOKEN_LENGTH = 50
        pages = [f"{self.base_url}/pages/consumption-location/end_client"]
        all_tokens_found = []

        session = await self._get_session()
        try:
            for page in pages:
                _LOGGER.debug("DEO: Checking page: %s", page)
                try:
                    async with session.get(page) as r:
                        _LOGGER.debug("DEO: Landed on: %s (status %s)", str(r.url)[:80], r.status)
                        text = await r.text()
                        _LOGGER.debug("DEO: Page size: %d chars", len(text))

                        all_token_matches = re.findall(r'token=([^&\s"\'<>]{10,})', text)
                        _LOGGER.debug("DEO: Found %d token patterns in HTML", len(all_token_matches))

                        for token in all_token_matches:
                            all_tokens_found.append((len(token), token[:30]))
                            if len(token) >= MIN_TOKEN_LENGTH:
                                _LOGGER.info("DEO: Found valid token (len=%d)", len(token))
                                return token

                        if not all_token_matches:
                            _LOGGER.debug("DEO: No token patterns found on page")

                except aiohttp.ClientError as e:
                    _LOGGER.error("DEO: Failed to get %s: %s", page, e)
                    continue

        finally:
            await session.close()

        if all_tokens_found:
            _LOGGER.error("DEO: Tokens found but too short: %s", all_tokens_found)
        else:
            _LOGGER.error("DEO: No tokens found")

        return None

    async def get_consumption_data(self):
        """Fetch data with session priming."""
        if not self.logged_in and not await self.login():
            _LOGGER.error("DEO: Login failed, cannot fetch data")
            return None

        try:
            token = None
            if self.token and len(self.token.strip()) > 50:
                token = self.token.strip()
                _LOGGER.debug("DEO: Using configured token (len=%d)", len(token))
            else:
                _LOGGER.debug("DEO: No valid config token, attempting discovery...")
                token = await self.get_token()

            if not token:
                _LOGGER.error("DEO: No token available! Please provide the long token in config.")
                return None

            _LOGGER.debug("DEO: Using token: %s...", token[:30])

            session = await self._get_session()
            try:
                if self.pod:
                    prime_url = f"{self.base_url}/pages/informatiiContract?pod={self.pod}"
                    _LOGGER.debug("DEO: Priming session with POD page...")
                    await session.get(prime_url)

                encoded_token = quote(token, safe="")
                history_url = f"{self.base_url}/pages/istoricIndecsi?token={encoded_token}"

                headers = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Referer": f"{self.base_url}/pages/dashboard",
                }

                _LOGGER.debug("DEO: Fetching history page...")
                async with session.get(history_url, headers=headers) as r:
                    _LOGGER.debug("DEO: Got status: %s", r.status)
                    if r.status != 200:
                        _LOGGER.error("DEO: History page returned %s", r.status)
                        return None
                    text = await r.text()

                data_match = re.search(r'(?:let|var)\s+data\s*=\s*(\[.*?\]);', text, re.DOTALL)
                if not data_match:
                    _LOGGER.error("DEO: No 'data' variable found in page")
                    return None

                try:
                    return json.loads(data_match.group(1))
                except json.JSONDecodeError:
                    return json.loads(data_match.group(1).replace("\\/", "/"))

            finally:
                await session.close()

        except aiohttp.ClientError as e:
            _LOGGER.error("DEO: Data fetch network error: %s", e)
            return None
        except asyncio.TimeoutError:
            _LOGGER.error("DEO: Data fetch timed out")
            return None
        except Exception as e:
            _LOGGER.exception("DEO: Data fetch error: %s", e)
            return None
