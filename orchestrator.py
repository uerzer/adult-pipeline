#!/usr/bin/env python3
"""
Adult Creator Content Pipeline Orchestrator
Master controller — generates content, posts to Reddit via nodriver, exports TikTok assets.

No API keys required. Uses free LLM endpoints + undetected Chrome.

Environment Variables (in .env):
  REDDIT_USERNAME  - Reddit login
  REDDIT_PASSWORD  - Reddit login
  CREATOR_HANDLE   - Your social handle (optional, for content gen)
  CREATOR_OF_URL   - Your monetization link (optional)
"""

import sqlite3
import schedule
import time
import sys
import os
import asyncio
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

from dotenv import load_dotenv
load_dotenv()

# Import pipeline modules
try:
    from content_brain import ContentBrain, ImageBrain, ContentQueue
except ImportError as e:
    print(f"[ORCH] Warning: Could not import content_brain: {e}")
    ContentBrain = ImageBrain = ContentQueue = None

try:
    from reddit_module import RedditAutomator
except ImportError as e:
    print(f"[ORCH] Warning: Could not import reddit_module: {e}")
    RedditAutomator = None

try:
    import tiktok_module
except ImportError as e:
    print(f"[ORCH] Warning: Could not import tiktok_module: {e}")
    tiktok_module = None


class StatsTracker:
    """SQLite-backed statistics tracker for pipeline performance"""

    def __init__(self, db_path: str = "output/stats.db"):
        self.db_path = db_path
        Path("output").mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                reddit_posts_made INTEGER DEFAULT 0,
                tiktok_exports INTEGER DEFAULT 0,
                content_generated INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                execution_time_seconds REAL DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                platform TEXT NOT NULL,
                post_id TEXT,
                post_title TEXT,
                content_angle TEXT,
                upvotes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                clicks_estimated INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        print(f"[ORCH] Stats database initialized: {self.db_path}")

    def log_day(self, stats_dict: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        date = stats_dict.get('date', datetime.now().strftime('%Y-%m-%d'))
        cursor.execute("""
            INSERT OR REPLACE INTO daily_stats
            (date, reddit_posts_made, tiktok_exports, content_generated, errors, execution_time_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            date,
            stats_dict.get('reddit_posts_made', 0),
            stats_dict.get('tiktok_exports', 0),
            stats_dict.get('content_generated', 0),
            stats_dict.get('errors', 0),
            stats_dict.get('execution_time_seconds', 0)
        ))
        conn.commit()
        conn.close()
        print(f"[ORCH] Logged daily stats for {date}")

    def log_performance(self, platform: str, post_data: Dict):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO performance
            (date, platform, post_id, post_title, content_angle, upvotes, comments, clicks_estimated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime('%Y-%m-%d'),
            platform,
            post_data.get('post_id', ''),
            post_data.get('title', ''),
            post_data.get('angle', ''),
            post_data.get('upvotes', 0),
            post_data.get('comments', 0),
            post_data.get('clicks_estimated', 0)
        ))
        conn.commit()
        conn.close()

    def get_weekly_summary(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT
                COUNT(*) as days_active,
                COALESCE(SUM(reddit_posts_made), 0),
                COALESCE(SUM(tiktok_exports), 0),
                COALESCE(SUM(content_generated), 0),
                COALESCE(SUM(errors), 0),
                COALESCE(AVG(execution_time_seconds), 0)
            FROM daily_stats WHERE date >= ?
        """, (week_ago,))
        ds = cursor.fetchone()

        cursor.execute("""
            SELECT platform, COUNT(*), COALESCE(SUM(upvotes),0),
                   COALESCE(SUM(comments),0), COALESCE(AVG(upvotes),0)
            FROM performance WHERE date >= ? GROUP BY platform
        """, (week_ago,))
        perf = cursor.fetchall()

        cursor.execute("""
            SELECT content_angle, COUNT(*), COALESCE(AVG(upvotes),0), COALESCE(SUM(upvotes),0)
            FROM performance
            WHERE date >= ? AND content_angle IS NOT NULL AND content_angle != ''
            GROUP BY content_angle ORDER BY AVG(upvotes) DESC LIMIT 5
        """, (week_ago,))
        top = cursor.fetchall()
        conn.close()

        return {
            'period': f'Last 7 days (since {week_ago})',
            'daily_stats': {
                'days_active': ds[0], 'total_reddit_posts': ds[1],
                'total_tiktok_exports': ds[2], 'total_content_generated': ds[3],
                'total_errors': ds[4], 'avg_execution_time_seconds': round(ds[5], 2)
            },
            'performance_by_platform': [
                {'platform': r[0], 'post_count': r[1], 'total_upvotes': r[2],
                 'total_comments': r[3], 'avg_upvotes': round(r[4], 2)} for r in perf
            ],
            'top_angles': [
                {'angle': r[0], 'uses': r[1], 'avg_upvotes': round(r[2], 2),
                 'total_upvotes': r[3]} for r in top
            ]
        }


class PipelineOrchestrator:
    """Master controller for the entire content pipeline"""

    def __init__(self):
        self.stats_tracker = StatsTracker()
        self.log_path = Path("output/pipeline_log.txt")
        Path("output").mkdir(exist_ok=True)

    def _log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(f"[ORCH] {message}")
        with open(self.log_path, 'a') as f:
            f.write(log_line + "\n")

    def run_daily(self):
        """Execute the full daily pipeline"""
        start_time = time.time()
        self._log("=" * 60)
        self._log("Starting daily pipeline execution")

        stats = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'reddit_posts_made': 0,
            'tiktok_exports': 0,
            'content_generated': 0,
            'errors': 0
        }

        # ── Step 1: Generate content (text + images) ──
        self._log("STEP 1/3: Generating content...")
        try:
            if ContentBrain is None:
                raise ImportError("content_brain module not available")

            brain = ContentBrain()
            img_brain = ImageBrain()
            queue = ContentQueue()

            generated = 0

            # 3 Reddit posts
            for i in range(3):
                self._log(f"  Generating Reddit post {i+1}/3...")
                title = brain.generate_reddit_title()
                caption = brain.generate_reddit_caption(title)
                image_path = img_brain.generate_teaser_image()

                queue.add_item(
                    content_type='reddit_post',
                    platform='reddit',
                    content_text=json.dumps({'title': title, 'caption': caption}),
                    image_path=image_path,
                    metadata={'post_number': i + 1}
                )
                generated += 1
                time.sleep(2)

            # TikTok hooks
            self._log("  Generating TikTok hooks...")
            hooks = brain.generate_tiktok_hooks(count=6)
            queue.add_item(
                content_type='tiktok_carousel',
                platform='tiktok',
                content_text=json.dumps({'hooks': hooks}),
                metadata={'hook_count': len(hooks)}
            )
            generated += 1

            # DM script
            self._log("  Generating DM script...")
            dm = brain.generate_dm_script()
            queue.add_item(
                content_type='dm_script',
                platform='onlyfans',
                content_text=dm,
                metadata={'script_type': 'welcome'}
            )
            generated += 1

            stats['content_generated'] = generated
            self._log(f"Content generation complete: {generated} items queued")

        except Exception as e:
            self._log(f"ERROR in content generation: {e}")
            traceback.print_exc()
            stats['errors'] += 1

        # ── Step 2: Export TikTok carousels ──
        self._log("STEP 2/3: Exporting TikTok carousels...")
        try:
            if tiktok_module is not None:
                result = tiktok_module.main()
                stats['tiktok_exports'] = result.get('exports_created', 0) if isinstance(result, dict) else 0
                self._log(f"TikTok export complete: {stats['tiktok_exports']} exports")
            else:
                self._log("TikTok module not available, skipping")
        except Exception as e:
            self._log(f"ERROR in tiktok_module: {e}")
            traceback.print_exc()
            stats['errors'] += 1

        # ── Step 3: Post to Reddit via nodriver ──
        self._log("STEP 3/3: Posting to Reddit (browser automation)...")
        try:
            if RedditAutomator is None:
                raise ImportError("reddit_module not available")

            username = os.getenv('REDDIT_USERNAME')
            password = os.getenv('REDDIT_PASSWORD')

            if not username or not password:
                self._log("WARNING: REDDIT_USERNAME/PASSWORD not set, skipping Reddit")
            else:
                automator = RedditAutomator()

                # Check account phase
                phase = automator.get_account_phase(username)
                self._log(f"Reddit account phase: {phase}")

                if phase == "lurk":
                    self._log("Account in lurk phase — running warming session only")
                    asyncio.run(automator.warm_account(username, password))
                elif phase == "comment":
                    self._log("Account in comment phase — warming + commenting")
                    asyncio.run(automator.warm_account(username, password))
                else:
                    # Full posting mode
                    self._log("Account ready for posting — executing post queue")
                    queue = ContentQueue()
                    pending = queue.get_pending(platform='reddit')

                    posts_made = 0
                    for item in pending[:3]:  # Max 3 posts per run
                        try:
                            content = json.loads(item['content_text'])
                            title = content.get('title', '')
                            caption = content.get('caption', '')

                            # Pick a subreddit from config
                            subreddits = automator.config.get('target_subreddits', ['selfie'])
                            import random
                            subreddit = random.choice(subreddits)

                            success = asyncio.run(automator.post_to_subreddit(
                                username=username,
                                password=password,
                                subreddit=subreddit,
                                title=title,
                                body=caption,
                                image_path=item.get('image_path')
                            ))

                            if success:
                                queue.mark_posted(item['id'])
                                posts_made += 1
                                self._log(f"  Posted to r/{subreddit}: {title[:50]}...")
                            else:
                                queue.mark_failed(item['id'], "Post failed")

                        except Exception as e:
                            self._log(f"  Error posting item {item['id']}: {e}")
                            queue.mark_failed(item['id'], str(e))

                        # Human-like delay between posts
                        time.sleep(random.uniform(120, 300))

                    stats['reddit_posts_made'] = posts_made
                    self._log(f"Reddit posting complete: {posts_made} posts made")

        except Exception as e:
            self._log(f"ERROR in reddit posting: {e}")
            traceback.print_exc()
            stats['errors'] += 1

        # ── Wrap up ──
        execution_time = time.time() - start_time
        stats['execution_time_seconds'] = execution_time

        self._log(f"Pipeline complete in {execution_time:.1f}s")
        self._log(f"Summary: {stats['content_generated']} content | "
                  f"{stats['tiktok_exports']} TikTok | "
                  f"{stats['reddit_posts_made']} Reddit | "
                  f"{stats['errors']} errors")

        self.stats_tracker.log_day(stats)
        self._log("=" * 60)
        return stats

    def run_warming_only(self):
        """Run a Reddit warming session without posting"""
        self._log("Running Reddit warming session...")

        if RedditAutomator is None:
            self._log("ERROR: reddit_module not available")
            return

        username = os.getenv('REDDIT_USERNAME')
        password = os.getenv('REDDIT_PASSWORD')

        if not username or not password:
            self._log("ERROR: REDDIT_USERNAME/PASSWORD not set in .env")
            return

        automator = RedditAutomator()
        phase = automator.get_account_phase(username)
        self._log(f"Account phase: {phase}")

        asyncio.run(automator.warm_account(username, password))
        self._log("Warming session complete")

    def generate_weekly_summary(self):
        """Generate and display weekly summary report"""
        self._log("Generating weekly summary report...")
        summary = self.stats_tracker.get_weekly_summary()

        report = [
            "\n" + "=" * 60,
            "WEEKLY SUMMARY REPORT",
            f"Period: {summary['period']}",
            "=" * 60, "",
            "PIPELINE ACTIVITY:",
            f"  Days active: {summary['daily_stats']['days_active']}",
            f"  Content generated: {summary['daily_stats']['total_content_generated']}",
            f"  TikTok exports: {summary['daily_stats']['total_tiktok_exports']}",
            f"  Reddit posts: {summary['daily_stats']['total_reddit_posts']}",
            f"  Errors: {summary['daily_stats']['total_errors']}",
            f"  Avg execution time: {summary['daily_stats']['avg_execution_time_seconds']}s",
            "", "PERFORMANCE BY PLATFORM:",
        ]

        for p in summary['performance_by_platform']:
            report.extend([
                f"  {p['platform'].upper()}:",
                f"    Posts: {p['post_count']}",
                f"    Total upvotes: {p['total_upvotes']}",
                f"    Avg upvotes: {p['avg_upvotes']}",
            ])

        report.extend(["", "TOP CONTENT ANGLES:"])
        for i, a in enumerate(summary['top_angles'], 1):
            report.append(f"  {i}. {a['angle']}")
            report.append(f"     {a['uses']}x used | Avg {a['avg_upvotes']} upvotes")

        report.append("=" * 60 + "\n")
        report_text = "\n".join(report)
        print(report_text)

        report_path = Path("output") / f"weekly_summary_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(report_path, 'w') as f:
            f.write(report_text)
        self._log(f"Weekly summary saved to {report_path}")

    def get_queue_status(self):
        """Show current queue status"""
        queue_db = Path("output/queue.db")
        if not queue_db.exists():
            print("[ORCH] No queue database found")
            return

        try:
            conn = sqlite3.connect(queue_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='content_queue'")
            if not cursor.fetchone():
                print("[ORCH] Queue table not found")
                conn.close()
                return

            cursor.execute("SELECT status, COUNT(*) FROM content_queue GROUP BY status")
            status_counts = dict(cursor.fetchall())
            cursor.execute("SELECT COUNT(*) FROM content_queue")
            total = cursor.fetchone()[0]

            print("\n" + "=" * 40)
            print("CONTENT QUEUE STATUS")
            print("=" * 40)
            print(f"Total items: {total}")
            for status, count in status_counts.items():
                print(f"  {status}: {count}")
            print("=" * 40 + "\n")
            conn.close()

        except Exception as e:
            print(f"[ORCH] Error reading queue: {e}")


def setup_scheduler(orchestrator: PipelineOrchestrator):
    """Setup scheduled tasks"""
    print("[ORCH] Setting up scheduler...")

    # Daily pipeline at 8:00 AM
    schedule.every().day.at("08:00").do(orchestrator.run_daily)
    print("[ORCH]   - Daily pipeline: 8:00 AM")

    # Reddit warming every 4 hours (keeps account active)
    schedule.every(4).hours.do(orchestrator.run_warming_only)
    print("[ORCH]   - Reddit warming: Every 4 hours")

    # Weekly summary on Sunday at 9:00 AM
    schedule.every().sunday.at("09:00").do(orchestrator.generate_weekly_summary)
    print("[ORCH]   - Weekly summary: Sundays at 9:00 AM")

    print("[ORCH] Scheduler ready.")


def main():
    """CLI interface"""
    orchestrator = PipelineOrchestrator()

    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py [run|warm|schedule|stats|status]")
        print("  run      - Run full pipeline once (generate + post)")
        print("  warm     - Run Reddit warming session only")
        print("  schedule - Start scheduler loop (runs continuously)")
        print("  stats    - Print weekly summary")
        print("  status   - Show content queue status")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "run":
        print("[ORCH] Running full pipeline...")
        orchestrator.run_daily()

    elif command == "warm":
        orchestrator.run_warming_only()

    elif command == "schedule":
        setup_scheduler(orchestrator)
        print("[ORCH] Running initial pipeline execution...")
        orchestrator.run_daily()
        while True:
            schedule.run_pending()
            time.sleep(60)

    elif command == "stats":
        orchestrator.generate_weekly_summary()

    elif command == "status":
        orchestrator.get_queue_status()

    else:
        print(f"[ORCH] Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
