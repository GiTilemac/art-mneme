"""End-to-end test: a real browser against the docker-compose.yaml stack.

Run with `make e2e` from the repository root. It starts the stack with empty volumes,
sets E2E_URL, and removes everything afterwards.
"""

import os
import uuid
from pathlib import Path

from playwright.sync_api import Browser, Page, expect

BASE_URL = os.environ.get("E2E_URL", "http://localhost:8093")
PHOTO = Path(__file__).parent / "artwork.jpg"
PASSWORD = "a long enough password"


def pick(page: Page, text: str, create: bool, picked: int) -> None:
    """Fill the first empty picker, then create `text` or choose the existing one, and wait until it is set."""
    page.get_by_placeholder("Search or create").first.fill(text)
    if create:
        page.get_by_role("button", name=f"Create “{text}”").click()
    else:
        page.get_by_role("button", name=text, exact=True).click()
    expect(page.get_by_role("button", name="Clear")).to_have_count(picked)


def add_collection_artwork(page: Page, title: str, artist: str, subject: str, first_for_user: bool) -> None:
    page.goto(f"{BASE_URL}/artworks/new")
    page.locator("input[type=file]").set_input_files(PHOTO)
    expect(page.get_by_role("button", name="Change photo")).to_be_visible()
    page.get_by_placeholder("The Night Watch").fill(title)
    pick(page, artist, create=first_for_user, picked=1)
    page.get_by_placeholder("From").fill("1889")
    pick(page, subject, create=first_for_user, picked=2)
    pick(page, "Post-Impressionism", create=False, picked=3)
    page.get_by_placeholder("Louvre").fill("MoMA")

    page.get_by_placeholder("Add a tag").fill("swirls")
    page.get_by_role("button", name="Add", exact=True).click()
    expect(page.get_by_role("button", name="Remove swirls")).to_be_visible()

    page.get_by_role("button", name="Add to collection").click()
    expect(page.get_by_role("heading", name=title)).to_be_visible()


def test_collection_and_same_artist_exploration_survive_reload_and_a_new_session(page: Page, browser: Browser):
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    first, second = "The Starry Night", "Wheatfield with Crows"
    artist, subject = "Vincent van Gogh", "Night sky"

    page.goto(f"{BASE_URL}/auth?mode=signup")
    page.get_by_label("Email").fill(email)
    page.get_by_label("Password").fill(PASSWORD)
    page.get_by_role("button", name="Create account").click()
    expect(page).to_have_url(f"{BASE_URL}/collection")

    add_collection_artwork(page, first, artist, subject, first_for_user=True)
    expect(page.get_by_text("MoMA")).to_be_visible()
    expect(page.get_by_text("Night sky")).to_be_visible()
    expect(page.get_by_text("Post-Impressionism")).to_be_visible()
    expect(page.get_by_text("swirls")).to_be_visible()
    page.get_by_role("link", name="Collection", exact=True).click()
    expect(page.get_by_role("link", name=first)).to_be_visible()

    add_collection_artwork(page, second, artist, subject, first_for_user=False)

    page.get_by_role("link", name="Collection", exact=True).click()
    page.get_by_role("link", name=first).click()
    page.get_by_role("link", name="Explore relationships").click()
    page.get_by_role("button", name="Same artist").click()
    expect(page.get_by_role("link", name=second)).to_be_visible()
    explore_url = page.url

    def check(p: Page) -> None:
        p.goto(f"{BASE_URL}/collection")
        expect(p.get_by_role("link", name=first)).to_be_visible()
        expect(p.get_by_role("link", name=second)).to_be_visible()
        p.goto(explore_url)
        p.get_by_role("button", name="Same artist").click()
        expect(p.get_by_role("link", name=second)).to_be_visible()

    page.reload()
    check(page)

    other = browser.new_context()
    other_page = other.new_page()
    other_page.goto(f"{BASE_URL}/auth")
    other_page.get_by_label("Email").fill(email)
    other_page.get_by_label("Password").fill(PASSWORD)
    other_page.get_by_role("button", name="Sign in").click()
    expect(other_page).to_have_url(f"{BASE_URL}/collection")
    check(other_page)
    other.close()
