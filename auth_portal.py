from playwright.sync_api import sync_playwright
from requests.adapters import HTTPAdapter, Retry
import requests
from config.app_config import Config


def get_authenticated_session():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(Config.PORTAL_URL)

        page.fill("input[name='username']", Config.USERNAME)
        page.fill("input[name='password']", Config.PASSWORD)
        page.click("button[type='submit']")

        page.wait_for_url(f"{Config.PORTAL_URL}/{Config.LANDING}")

        cookies = context.cookies()
        browser.close()

    cookie_dict = {c["name"]: c["value"] for c in cookies}

    session = requests.Session()
    session.cookies.update(cookie_dict)

    retries = Retry(
        total=5,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("https://", adapter)

    return session