"""
Reddit Posting Module for Adult Creator Traffic Pipeline
Automated SFW teaser posting with account warming and human-like behavior
"""

import praw
import requests
import os
import time
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path

# Requirements: praw, requests, pillow


class RedditPoster:
    """Handles Reddit authentication and posting via PRAW"""
    
    def __init__(self):
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        self.user_agent = f"python:adult-creator-pipeline:v1.0 (by /u/{self.username})"
        
        if not all([self.client_id, self.client_secret, self.username, self.password]):
            print("[REDDIT] ⚠️  Missing credentials! Set these env vars:")
            print("[REDDIT]   REDDIT_CLIENT_ID")
            print("[REDDIT]   REDDIT_CLIENT_SECRET")
            print("[REDDIT]   REDDIT_USERNAME")
            print("[REDDIT]   REDDIT_PASSWORD")
            print("[REDDIT] Get credentials from: https://www.reddit.com/prefs/apps")
            raise ValueError("Missing Reddit credentials")
        
        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            username=self.username,
            password=self.password,
            user_agent=self.user_agent
        )
        
        print(f"[REDDIT] ✓ Authenticated as u/{self.username}")
    
    def get_account_age_days(self) -> int:
        """Get account age in days"""
        created_utc = self.reddit.user.me().created_utc
        age = datetime.now() - datetime.fromtimestamp(created_utc)
        return age.days
    
    def get_karma(self) -> Tuple[int, int]:
        """Get link and comment karma"""
        user = self.reddit.user.me()
        return user.link_karma, user.comment_karma
    
    def get_subreddit_flair(self, subreddit_name: str) -> Optional[List[Dict]]:
        """Get available flairs for a subreddit"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            flairs = list(subreddit.flair.link_templates)
            return flairs
        except Exception as e:
            print(f"[REDDIT] Could not get flairs for r/{subreddit_name}: {e}")
            return None
    
    def post_image(
        self,
        subreddit_name: str,
        title: str,
        image_path: str,
        flair_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Post an image to a subreddit
        Returns: post URL if successful, None if failed
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            print(f"[REDDIT] Posting to r/{subreddit_name}: '{title[:50]}...'")
            
            submission = subreddit.submit_image(
                title=title,
                image_path=image_path,
                flair_id=flair_id
            )
            
            post_url = f"https://reddit.com{submission.permalink}"
            print(f"[REDDIT] ✓ Posted successfully: {post_url}")
            
            return post_url
            
        except Exception as e:
            print(f"[REDDIT] ✗ Failed to post to r/{subreddit_name}: {e}")
            return None
    
    def comment_on_post(self, post_url: str, comment_text: str) -> bool:
        """Comment on a Reddit post"""
        try:
            submission = self.reddit.submission(url=post_url)
            submission.reply(comment_text)
            print(f"[REDDIT] ✓ Commented on post")
            return True
        except Exception as e:
            print(f"[REDDIT] ✗ Failed to comment: {e}")
            return False
    
    def upvote_random_posts(self, subreddit_name: str, count: int = 5):
        """Upvote random posts in a subreddit (for account warming)"""
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = list(subreddit.hot(limit=50))
            random.shuffle(posts)
            
            upvoted = 0
            for post in posts[:count]:
                if not post.stickied:  # Skip pinned posts
                    post.upvote()
                    upvoted += 1
                    time.sleep(random.uniform(2, 5))
            
            print(f"[REDDIT] ✓ Upvoted {upvoted} posts in r/{subreddit_name}")
            
        except Exception as e:
            print(f"[REDDIT] ✗ Failed to upvote in r/{subreddit_name}: {e}")


class SubredditManager:
    """Manages target subreddits with metadata"""
    
    SUBREDDITS = [
        {
            "name": "OnlyFansPromotions",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "OF promotion hub"
        },
        {
            "name": "Feetishh",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 100,
            "description": "Feet content niche"
        },
        {
            "name": "AmateurPhotography",
            "requires_flair": True,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 50,
            "description": "Amateur photo sharing"
        },
        {
            "name": "Amateurs",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "Amateur content"
        },
        {
            "name": "FreePornAccounts",
            "requires_flair": False,
            "link_allowed": True,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "Free account promo"
        },
        {
            "name": "onlyfansgirls101",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "OF girls promo"
        },
        {
            "name": "NSFW411",
            "requires_flair": False,
            "link_allowed": True,
            "image_allowed": False,
            "karma_threshold": 200,
            "description": "NSFW directory"
        },
        {
            "name": "OnlyFans101",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "OF promo main"
        },
        {
            "name": "RealGirls",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 500,
            "description": "High karma real girls"
        },
        {
            "name": "Verification",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "Verification posts"
        },
        {
            "name": "gonewild",
            "requires_flair": True,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 1000,
            "description": "High karma NSFW"
        },
        {
            "name": "petitegonewild",
            "requires_flair": True,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 500,
            "description": "Petite niche"
        },
        {
            "name": "AssAndTittiesOF",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "OF body focus"
        },
        {
            "name": "SluttyConfessions",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": False,
            "karma_threshold": 100,
            "description": "Text confession promo"
        },
        {
            "name": "OFpromo",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "OF promo alt"
        },
        {
            "name": "CurvyWomenOfColor",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 50,
            "description": "Curvy WOC niche"
        },
        {
            "name": "TributeMe",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 200,
            "description": "Tribute requests"
        },
        {
            "name": "ExposedAmateurs",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 0,
            "description": "Amateur exposure"
        },
        {
            "name": "ChubbyGirls",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 50,
            "description": "Body positive niche"
        },
        {
            "name": "Thickness",
            "requires_flair": False,
            "link_allowed": False,
            "image_allowed": True,
            "karma_threshold": 100,
            "description": "Thick body type"
        }
    ]
    
    def get_eligible_subreddits(self, karma: int, account_age_days: int) -> List[Dict]:
        """Get subreddits user is eligible to post in"""
        eligible = []
        
        for sub in self.SUBREDDITS:
            if karma >= sub["karma_threshold"]:
                eligible.append(sub)
        
        return eligible
    
    def get_low_karma_subs(self) -> List[Dict]:
        """Get subreddits with karma threshold <= 100"""
        return [s for s in self.SUBREDDITS if s["karma_threshold"] <= 100]
    
    def get_all_subreddits(self) -> List[Dict]:
        """Get all subreddits"""
        return self.SUBREDDITS


class WarmingSchedule:
    """Manages account warming progression and post timing"""
    
    def __init__(self, db_path: str = "output/reddit_state.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for state tracking"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS account_state (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                account_age_days INTEGER,
                link_karma INTEGER,
                comment_karma INTEGER,
                last_post_date TEXT,
                total_posts INTEGER DEFAULT 0,
                warming_phase TEXT,
                updated_at TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS post_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                subreddit TEXT,
                post_url TEXT,
                posted_at TEXT,
                karma_at_post INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def update_account_state(
        self,
        username: str,
        account_age_days: int,
        link_karma: int,
        comment_karma: int
    ):
        """Update account state in database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        phase = self._determine_phase(account_age_days, link_karma + comment_karma)
        
        c.execute('''
            INSERT OR REPLACE INTO account_state 
            (username, account_age_days, link_karma, comment_karma, warming_phase, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, account_age_days, link_karma, comment_karma, phase, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"[REDDIT] Account state: {account_age_days} days old, {link_karma + comment_karma} karma, Phase: {phase}")
    
    def _determine_phase(self, age_days: int, total_karma: int) -> str:
        """Determine warming phase based on account age and karma"""
        if age_days < 14:
            return "WARMING_WEEK_1_2"
        elif age_days < 28:
            return "WARMING_WEEK_3_4"
        else:
            return "FULL_ROTATION"
    
    def get_warming_phase(self, username: str) -> str:
        """Get current warming phase for user"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT warming_phase FROM account_state WHERE username = ?', (username,))
        row = c.fetchone()
        conn.close()
        
        return row[0] if row else "WARMING_WEEK_1_2"
    
    def can_post_today(self, username: str) -> bool:
        """Check if account can post today based on warming schedule"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT last_post_date FROM account_state WHERE username = ?', (username,))
        row = c.fetchone()
        conn.close()
        
        if not row or not row[0]:
            return True
        
        last_post = datetime.fromisoformat(row[0])
        days_since = (datetime.now() - last_post).days
        
        # Don't post more than once per day
        return days_since >= 1
    
    def record_post(self, username: str, subreddit: str, post_url: str, karma: int):
        """Record a post in history"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO post_history (username, subreddit, post_url, posted_at, karma_at_post)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, subreddit, post_url, datetime.now().isoformat(), karma))
        
        # Update last post date
        c.execute('''
            UPDATE account_state 
            SET last_post_date = ?, total_posts = total_posts + 1
            WHERE username = ?
        ''', (datetime.now().isoformat(), username))
        
        conn.commit()
        conn.close()
    
    def get_optimal_post_time(self) -> datetime:
        """
        Get optimal post time (peak Reddit hours: 9am-12pm or 6pm-10pm EST)
        Returns a datetime with random jitter
        """
        now = datetime.now()
        
        # Choose morning or evening slot randomly
        if random.random() < 0.5:
            # Morning slot: 9am-12pm EST
            hour = random.randint(9, 11)
        else:
            # Evening slot: 6pm-10pm EST
            hour = random.randint(18, 21)
        
        minute = random.randint(0, 59)
        
        # Add jitter: +/- 30 minutes
        jitter_minutes = random.randint(-30, 30)
        
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        target_time += timedelta(minutes=jitter_minutes)
        
        return target_time


class HumanBehavior:
    """Simulates human-like behavior to avoid bot detection"""
    
    @staticmethod
    def random_delay(min_seconds: int = 30, max_seconds: int = 120):
        """Sleep with gaussian distribution (more natural than uniform)"""
        mean = (min_seconds + max_seconds) / 2
        std_dev = (max_seconds - min_seconds) / 6
        
        delay = random.gauss(mean, std_dev)
        delay = max(min_seconds, min(max_seconds, delay))  # Clamp to range
        
        print(f"[REDDIT] Waiting {delay:.1f}s (human timing)...")
        time.sleep(delay)
    
    @staticmethod
    def typing_pause():
        """Simulate reading/thinking time before posting"""
        pause = random.gauss(15, 5)  # ~15 seconds average
        pause = max(5, min(30, pause))
        print(f"[REDDIT] Reading time: {pause:.1f}s...")
        time.sleep(pause)
    
    @staticmethod
    def should_skip_today() -> bool:
        """Randomly skip posting 1 day per week (14% chance)"""
        skip = random.random() < 0.14
        if skip:
            print("[REDDIT] 🎲 Randomly skipping today (human behavior)")
        return skip


class ContentQueue:
    """Interface to content queue from content_brain.py"""
    
    def __init__(self, db_path: str = "output/queue.db"):
        self.db_path = db_path
    
    def get_pending_reddit_content(self) -> List[Dict]:
        """Get pending Reddit posts from queue"""
        if not os.path.exists(self.db_path):
            print(f"[REDDIT] Queue database not found: {self.db_path}")
            return []
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''
                SELECT id, platform, content_type, caption, image_path, created_at
                FROM content_queue
                WHERE platform = 'reddit' AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 5
            ''')
            
            rows = c.fetchall()
            
            content = []
            for row in rows:
                content.append({
                    'id': row[0],
                    'platform': row[1],
                    'content_type': row[2],
                    'caption': row[3],
                    'image_path': row[4],
                    'created_at': row[5]
                })
            
            return content
            
        except sqlite3.OperationalError as e:
            print(f"[REDDIT] Queue database error: {e}")
            return []
        finally:
            conn.close()
    
    def mark_posted(self, content_id: int, post_url: str):
        """Mark content as posted"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            UPDATE content_queue
            SET status = 'posted', posted_at = ?, post_url = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), post_url, content_id))
        
        conn.commit()
        conn.close()
    
    def mark_failed(self, content_id: int, error: str):
        """Mark content as failed"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            UPDATE content_queue
            SET status = 'failed', error = ?
            WHERE id = ?
        ''', (error, content_id))
        
        conn.commit()
        conn.close()


def log_activity(message: str, log_path: str = "output/reddit_log.txt"):
    """Log activity to file"""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(log_entry)


def main():
    """Main orchestration function"""
    print("[REDDIT] ====================================")
    print("[REDDIT] Reddit Posting Module Starting")
    print("[REDDIT] ====================================")
    
    try:
        # Initialize components
        poster = RedditPoster()
        sub_manager = SubredditManager()
        warming = WarmingSchedule()
        behavior = HumanBehavior()
        queue = ContentQueue()
        
        # Get account info
        account_age = poster.get_account_age_days()
        link_karma, comment_karma = poster.get_karma()
        total_karma = link_karma + comment_karma
        
        print(f"[REDDIT] Account: u/{poster.username}")
        print(f"[REDDIT] Age: {account_age} days")
        print(f"[REDDIT] Karma: {total_karma} (link: {link_karma}, comment: {comment_karma})")
        
        # Update account state
        warming.update_account_state(poster.username, account_age, link_karma, comment_karma)
        
        # Check if we should post today
        if not warming.can_post_today(poster.username):
            print("[REDDIT] Already posted today. Skipping.")
            log_activity("Already posted today - skipping")
            return
        
        # Random skip for human behavior
        if behavior.should_skip_today():
            log_activity("Randomly skipped today (human behavior)")
            return
        
        # Get warming phase
        phase = warming.get_warming_phase(poster.username)
        print(f"[REDDIT] Current phase: {phase}")
        
        # Phase-specific behavior
        if phase == "WARMING_WEEK_1_2":
            print("[REDDIT] WARMING PHASE 1-2: Upvoting and commenting only")
            log_activity("Warming phase 1-2: upvoting posts")
            
            # Upvote in a few subreddits
            low_karma_subs = sub_manager.get_low_karma_subs()
            random.shuffle(low_karma_subs)
            
            for sub in low_karma_subs[:3]:
                poster.upvote_random_posts(sub['name'], count=5)
                behavior.random_delay(60, 180)
            
            print("[REDDIT] ✓ Warming activity complete")
            
        elif phase == "WARMING_WEEK_3_4":
            print("[REDDIT] WARMING PHASE 3-4: Posting to 1-2 low-karma subs")
            log_activity("Warming phase 3-4: limited posting")
            
            # Get eligible low-karma subs
            low_karma_subs = sub_manager.get_low_karma_subs()
            eligible = [s for s in low_karma_subs if total_karma >= s['karma_threshold']]
            
            if not eligible:
                print("[REDDIT] No eligible subreddits yet. Need more karma.")
                return
            
            # Get content from queue
            pending_content = queue.get_pending_reddit_content()
            
            if not pending_content:
                print("[REDDIT] No pending content in queue")
                return
            
            content = pending_content[0]  # Take first item
            
            # Post to 1-2 subs
            target_subs = random.sample(eligible, min(2, len(eligible)))
            
            for sub in target_subs:
                behavior.typing_pause()
                
                post_url = poster.post_image(
                    subreddit_name=sub['name'],
                    title=content['caption'],
                    image_path=content['image_path']
                )
                
                if post_url:
                    warming.record_post(poster.username, sub['name'], post_url, total_karma)
                    queue.mark_posted(content['id'], post_url)
                    log_activity(f"Posted to r/{sub['name']}: {post_url}")
                else:
                    queue.mark_failed(content['id'], f"Failed to post to r/{sub['name']}")
                
                behavior.random_delay(120, 300)
        
        else:  # FULL_ROTATION
            print("[REDDIT] FULL ROTATION: Posting to all eligible subs")
            log_activity("Full rotation: unrestricted posting")
            
            # Get all eligible subreddits
            eligible = sub_manager.get_eligible_subreddits(total_karma, account_age)
            
            if not eligible:
                print("[REDDIT] No eligible subreddits. Need more karma.")
                return
            
            print(f"[REDDIT] Eligible subreddits: {len(eligible)}")
            
            # Get content from queue
            pending_content = queue.get_pending_reddit_content()
            
            if not pending_content:
                print("[REDDIT] No pending content in queue")
                return
            
            content = pending_content[0]
            
            # Post to 3-5 subreddits
            target_count = random.randint(3, 5)
            target_subs = random.sample(eligible, min(target_count, len(eligible)))
            
            print(f"[REDDIT] Posting to {len(target_subs)} subreddits today")
            
            for sub in target_subs:
                behavior.typing_pause()
                
                post_url = poster.post_image(
                    subreddit_name=sub['name'],
                    title=content['caption'],
                    image_path=content['image_path']
                )
                
                if post_url:
                    warming.record_post(poster.username, sub['name'], post_url, total_karma)
                    queue.mark_posted(content['id'], post_url)
                    log_activity(f"Posted to r/{sub['name']}: {post_url}")
                else:
                    queue.mark_failed(content['id'], f"Failed to post to r/{sub['name']}")
                
                behavior.random_delay(120, 300)
        
        print("[REDDIT] ====================================")
        print("[REDDIT] Session complete")
        print("[REDDIT] ====================================")
        
    except ValueError as e:
        print(f"[REDDIT] Configuration error: {e}")
        log_activity(f"ERROR: {e}")
    except Exception as e:
        print(f"[REDDIT] Unexpected error: {e}")
        log_activity(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
