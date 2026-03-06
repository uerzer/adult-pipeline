"""
Reddit Module - Browser Automation via nodriver (undetected Chrome)
Posts SFW teasers to niche subreddits with human-like warming behavior.
No API credentials needed — just a Reddit account (username + password).
"""

import asyncio
import nodriver as uc
import os
import time
import random
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict


# ─── Config ────────────────────────────────────────────────────────────────────

REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
PROXY_URL       = os.getenv("PROXY_URL", "")          # optional: socks5://host:port
OUTPUT_DIR      = Path("output")
DB_PATH         = OUTPUT_DIR / "reddit.db"

# Target subreddits with metadata
SUBREDDITS: List[Dict] = [
    {"name": "OnlyFansPromotions",  "karma_min": 0,   "image": True,  "nsfw": False},
    {"name": "Feetishh",            "karma_min": 100,  "image": True,  "nsfw": False},
    {"name": "GoneWildPlus",        "karma_min": 50,   "image": True,  "nsfw": True},
    {"name": "RealGirls",           "karma_min": 200,  "image": True,  "nsfw": True},
    {"name": "NSFWposts",           "karma_min": 0,    "image": True,  "nsfw": True},
    {"name": "amihot",              "karma_min": 0,    "image": True,  "nsfw": False},
    {"name": "PetiteGoneWild",      "karma_min": 50,   "image": True,  "nsfw": True},
    {"name": "AmateurPhotography",  "karma_min": 0,    "image": True,  "nsfw": False},
    {"name": "SFWNextDoor",         "karma_min": 0,    "image": True,  "nsfw": False},
    {"name": "onlyfansadvice",      "karma_min": 0,    "image": False, "nsfw": False},
]

# Human-like timing ranges (seconds)
DELAYS = {
    "between_actions":  (2.5, 6.0),
    "between_posts":    (180, 600),     # 3-10 min between posts
    "scroll_pause":     (0.8, 2.5),
    "typing_char":      (0.05, 0.18),
    "post_read":        (8, 30),
    "session_start":    (5, 15),
}

# Warming schedule — days since account creation
WARMING_PHASES = {
    "lurk":    (0, 7),     # days 0-7: only browse, upvote
    "comment": (7, 14),    # days 7-14: browse + comment on others
    "post":    (14, 9999), # day 14+: full posting
}


# ─── Database ──────────────────────────────────────────────────────────────────

def init_db():
    OUTPUT_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subreddit   TEXT,
            title       TEXT,
            image_path  TEXT,
            post_url    TEXT,
            upvotes     INTEGER DEFAULT 0,
            posted_at   TEXT,
            status      TEXT DEFAULT 'pending'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS account_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            action     TEXT,
            target     TEXT,
            timestamp  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def log_action(action: str, target: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO account_log (action, target) VALUES (?, ?)", (action, target))
    conn.commit()
    conn.close()


def log_post(subreddit: str, title: str, image_path: str, post_url: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO posts (subreddit, title, image_path, post_url, posted_at, status) VALUES (?, ?, ?, ?, ?, ?)",
        (subreddit, title, image_path, post_url, datetime.now().isoformat(), "posted")
    )
    conn.commit()
    conn.close()


def already_posted_today(subreddit: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute(
        "SELECT COUNT(*) FROM posts WHERE subreddit=? AND posted_at LIKE ? AND status='posted'",
        (subreddit, f"{today}%")
    )
    count = c.fetchone()[0]
    conn.close()
    return count > 0


# ─── Browser helpers ──────────────────────────────────────────────────────────

async def human_delay(category: str = "between_actions"):
    lo, hi = DELAYS.get(category, (2, 5))
    await asyncio.sleep(random.uniform(lo, hi))


async def human_scroll(page, iterations: int = None):
    """Scroll the page naturally with random pauses."""
    iters = iterations or random.randint(3, 8)
    for _ in range(iters):
        distance = random.randint(200, 700)
        direction = "+" if random.random() > 0.15 else "-"
        await page.evaluate(f"window.scrollBy(0, {direction}{distance})")
        await human_delay("scroll_pause")


async def human_type(element, text: str):
    """Type text character by character with human-like timing."""
    for char in text:
        await element.send_keys(char)
        if char == " " and random.random() < 0.3:
            await asyncio.sleep(random.uniform(0.3, 0.9))
        else:
            await asyncio.sleep(random.uniform(*DELAYS["typing_char"]))


async def wait_for_selector(page, selector: str, timeout: int = 15) -> Optional[object]:
    """Wait for an element to appear, return it or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            el = await page.find(selector, timeout=2)
            if el:
                return el
        except Exception:
            pass
        await asyncio.sleep(0.5)
    return None


# ─── Browser factory ──────────────────────────────────────────────────────────

async def launch_browser() -> uc.Browser:
    """Launch nodriver browser with anti-detection settings."""
    args = [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--lang=en-US,en;q=0.9",
        f"--window-size={random.randint(1200,1440)},{random.randint(800,900)}",
    ]

    if PROXY_URL:
        args.append(f"--proxy-server={PROXY_URL}")

    browser = await uc.start(
        browser_args=args,
        headless=False,   # set True on VPS with Xvfb
        lang="en-US",
    )
    return browser


# ─── Reddit actions ───────────────────────────────────────────────────────────

async def login(browser: uc.Browser) -> uc.Tab:
    """Log into Reddit. Returns the active tab."""
    print("[REDDIT] Logging in...")
    tab = await browser.get("https://www.reddit.com/login")
    await human_delay("session_start")

    user_field = await wait_for_selector(tab, "input#loginUsername")
    if not user_field:
        raise RuntimeError("Could not find username field on login page")
    await human_type(user_field, REDDIT_USERNAME)
    await human_delay()

    pass_field = await wait_for_selector(tab, "input#loginPassword")
    await human_type(pass_field, REDDIT_PASSWORD)
    await human_delay()

    submit_btn = await wait_for_selector(tab, "button[type='submit']")
    await submit_btn.click()
    await asyncio.sleep(4)

    if "login" in tab.url:
        raise RuntimeError("[REDDIT] Login failed — check credentials")

    print(f"[REDDIT] Logged in as u/{REDDIT_USERNAME}")
    log_action("login", REDDIT_USERNAME)
    return tab


async def browse_subreddit(tab: uc.Tab, subreddit: str, read_posts: int = None):
    """Browse a subreddit naturally — scroll, read posts, maybe upvote."""
    n = read_posts or random.randint(3, 8)
    print(f"[REDDIT] Browsing r/{subreddit} ({n} posts)...")

    await tab.get(f"https://www.reddit.com/r/{subreddit}/")
    await human_delay("session_start")
    await human_scroll(tab, random.randint(2, 5))

    for _ in range(n):
        try:
            posts = await tab.find_all("a[data-click-id='body']")
            if not posts:
                break
            post = random.choice(posts[:15])
            await post.click()
            await human_delay("post_read")
            await human_scroll(tab, random.randint(2, 6))

            # Randomly upvote (30% chance)
            if random.random() < 0.3:
                upvote_btn = await tab.find("button[aria-label='upvote']")
                if upvote_btn:
                    await upvote_btn.click()
                    log_action("upvote", subreddit)
                    await human_delay()

            await tab.back()
            await human_delay()
        except Exception as e:
            print(f"[REDDIT] Browse error (non-fatal): {e}")
            break

    print(f"[REDDIT] Done browsing r/{subreddit}")


async def leave_comment(tab: uc.Tab, subreddit: str, comment_text: str):
    """Find a post and leave a comment — used during warming phase."""
    print(f"[REDDIT] Commenting in r/{subreddit}...")
    await tab.get(f"https://www.reddit.com/r/{subreddit}/new/")
    await human_delay()
    await human_scroll(tab, 2)

    try:
        posts = await tab.find_all("a[data-click-id='body']")
        if not posts:
            return
        post = random.choice(posts[:10])
        await post.click()
        await human_delay("post_read")

        comment_box = await wait_for_selector(tab, "div[data-testid='comment-submission-form-richtext']")
        if comment_box:
            await comment_box.click()
            await human_type(comment_box, comment_text)
            await human_delay()

            submit = await wait_for_selector(tab, "button[type='submit']")
            if submit:
                await submit.click()
                await asyncio.sleep(3)
                log_action("comment", subreddit)
                print(f"[REDDIT] Commented in r/{subreddit}")
    except Exception as e:
        print(f"[REDDIT] Comment error: {e}")


async def post_image_to_subreddit(
    tab: uc.Tab,
    subreddit: str,
    title: str,
    image_path: str,
) -> Optional[str]:
    """
    Post an image to a subreddit using the browser.
    Returns post URL or None on failure.
    """
    if already_posted_today(subreddit):
        print(f"[REDDIT] Already posted to r/{subreddit} today, skipping")
        return None

    print(f"[REDDIT] Posting to r/{subreddit}...")
    await tab.get(f"https://www.reddit.com/r/{subreddit}/submit?type=image")
    await human_delay("session_start")

    try:
        title_field = await wait_for_selector(tab, "textarea[name='title'], input[name='title']")
        if not title_field:
            print(f"[REDDIT] Could not find title field in r/{subreddit}")
            return None
        await title_field.click()
        await human_type(title_field, title)
        await human_delay()

        file_input = await wait_for_selector(tab, "input[type='file']")
        if not file_input:
            print(f"[REDDIT] Could not find file upload in r/{subreddit}")
            return None
        await file_input.send_file(str(Path(image_path).resolve()))
        await asyncio.sleep(4)

        await human_delay()

        submit_btn = await wait_for_selector(tab, "button[type='submit']:not([disabled])")
        if not submit_btn:
            print(f"[REDDIT] Submit button not found or disabled in r/{subreddit}")
            return None

        await submit_btn.click()
        await asyncio.sleep(5)

        post_url = tab.url
        if "/comments/" in post_url:
            print(f"[REDDIT] Posted: {post_url}")
            log_post(subreddit, title, image_path, post_url)
            log_action("post", subreddit)
            return post_url
        else:
            print(f"[REDDIT] Post may have failed — landed at: {post_url}")
            return None

    except Exception as e:
        print(f"[REDDIT] Post error in r/{subreddit}: {e}")
        return None


# ─── Warming phase logic ──────────────────────────────────────────────────────

def get_account_phase() -> str:
    """Determine current warming phase based on account creation record."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT MIN(timestamp) FROM account_log")
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        log_action("account_created", REDDIT_USERNAME)
        return "lurk"

    created = datetime.fromisoformat(row[0])
    days_old = (datetime.now() - created).days

    for phase, (start, end) in WARMING_PHASES.items():
        if start <= days_old < end:
            return phase

    return "post"


# ─── Main pipeline entry points ───────────────────────────────────────────────

async def run_warming_session():
    """
    Run a warming session — browse subreddits, upvote, maybe comment.
    Call this daily even before the account is ready to post.
    """
    init_db()
    phase = get_account_phase()
    print(f"[REDDIT] Account phase: {phase}")

    browser = await launch_browser()
    try:
        tab = await login(browser)
        await human_delay()

        subs_to_browse = random.sample(SUBREDDITS, min(4, len(SUBREDDITS)))
        for sub in subs_to_browse:
            await browse_subreddit(tab, sub["name"], random.randint(3, 7))
            await human_delay("between_posts")

        if phase == "comment":
            warming_comments = [
                "Love this community",
                "This made my day honestly",
                "Incredible, keep it up!",
                "Amazing content as always",
                "You're too good at this lol",
            ]
            comment_sub = random.choice(SUBREDDITS)
            await leave_comment(tab, comment_sub["name"], random.choice(warming_comments))

        print(f"[REDDIT] Warming session complete (phase: {phase})")

    finally:
        browser.stop()


async def run_post_session(posts: List[Dict]) -> List[str]:
    """
    Post a batch of SFW teasers to subreddits.
    posts = [{"subreddit": "...", "title": "...", "image_path": "..."}, ...]
    Returns list of successful post URLs.
    """
    init_db()
    phase = get_account_phase()

    if phase != "post":
        print(f"[REDDIT] Account in '{phase}' phase — not posting yet. Running warming instead.")
        await run_warming_session()
        return []

    browser = await launch_browser()
    successful_urls = []

    try:
        tab = await login(browser)

        # Warm up before posting — browse for a few minutes
        print("[REDDIT] Warming up before posting...")
        warmup_subs = random.sample(SUBREDDITS, min(2, len(SUBREDDITS)))
        for sub in warmup_subs:
            await browse_subreddit(tab, sub["name"], random.randint(2, 4))
            await human_delay("between_posts")

        for post in posts:
            url = await post_image_to_subreddit(
                tab,
                subreddit=post["subreddit"],
                title=post["title"],
                image_path=post["image_path"],
            )
            if url:
                successful_urls.append(url)

            await human_delay("between_posts")

            # Browse between posts (looks natural)
            browse_sub = random.choice(SUBREDDITS)
            await browse_subreddit(tab, browse_sub["name"], random.randint(2, 4))
            await human_delay("between_posts")

        print(f"[REDDIT] Session complete: {len(successful_urls)}/{len(posts)} posts successful")

    finally:
        browser.stop()

    return successful_urls


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python reddit_module.py warm                          # Run warming session")
        print("  python reddit_module.py phase                         # Show current account phase")
        print("  python reddit_module.py post <sub> <title> <img>     # Post single image")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "warm":
        asyncio.run(run_warming_session())

    elif cmd == "phase":
        init_db()
        print(f"Account phase: {get_account_phase()}")

    elif cmd == "post":
        if len(sys.argv) < 5:
            print("Usage: python reddit_module.py post <subreddit> <title> <image_path>")
            sys.exit(1)
        sub, title, img = sys.argv[2], sys.argv[3], sys.argv[4]
        results = asyncio.run(run_post_session([
            {"subreddit": sub, "title": title, "image_path": img}
        ]))
        print(f"Posted: {results}")
