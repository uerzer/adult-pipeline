#!/usr/bin/env python3
"""
Adult Creator Content Pipeline Orchestrator
Master controller that runs the entire content generation and posting pipeline daily.
"""

import sqlite3
import schedule
import time
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json

# Import pipeline modules
try:
    import content_brain
    import tiktok_module
    import reddit_module
except ImportError as e:
    print(f"[ORCH] Warning: Could not import module: {e}")
    print("[ORCH] Some modules may not be available yet")


class StatsTracker:
    """SQLite-backed statistics tracker for pipeline performance"""
    
    def __init__(self, db_path: str = "output/stats.db"):
        self.db_path = db_path
        Path("output").mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Daily pipeline stats
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
        
        # Performance metrics per post
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
        """Log daily pipeline execution stats"""
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
        """Log individual post performance"""
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
        """Get aggregated stats for last 7 days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Daily stats summary
        cursor.execute("""
            SELECT 
                COUNT(*) as days_active,
                SUM(reddit_posts_made) as total_reddit_posts,
                SUM(tiktok_exports) as total_tiktok_exports,
                SUM(content_generated) as total_content_generated,
                SUM(errors) as total_errors,
                AVG(execution_time_seconds) as avg_execution_time
            FROM daily_stats
            WHERE date >= ?
        """, (week_ago,))
        
        daily_summary = cursor.fetchone()
        
        # Performance summary
        cursor.execute("""
            SELECT 
                platform,
                COUNT(*) as post_count,
                SUM(upvotes) as total_upvotes,
                SUM(comments) as total_comments,
                AVG(upvotes) as avg_upvotes
            FROM performance
            WHERE date >= ?
            GROUP BY platform
        """, (week_ago,))
        
        performance_by_platform = cursor.fetchall()
        
        # Top performing angles
        cursor.execute("""
            SELECT 
                content_angle,
                COUNT(*) as uses,
                AVG(upvotes) as avg_upvotes,
                SUM(upvotes) as total_upvotes
            FROM performance
            WHERE date >= ? AND content_angle IS NOT NULL AND content_angle != ''
            GROUP BY content_angle
            ORDER BY avg_upvotes DESC
            LIMIT 5
        """, (week_ago,))
        
        top_angles = cursor.fetchall()
        
        conn.close()
        
        return {
            'period': f'Last 7 days (since {week_ago})',
            'daily_stats': {
                'days_active': daily_summary[0] or 0,
                'total_reddit_posts': daily_summary[1] or 0,
                'total_tiktok_exports': daily_summary[2] or 0,
                'total_content_generated': daily_summary[3] or 0,
                'total_errors': daily_summary[4] or 0,
                'avg_execution_time_seconds': round(daily_summary[5] or 0, 2)
            },
            'performance_by_platform': [
                {
                    'platform': row[0],
                    'post_count': row[1],
                    'total_upvotes': row[2],
                    'total_comments': row[3],
                    'avg_upvotes': round(row[4], 2)
                }
                for row in performance_by_platform
            ],
            'top_angles': [
                {
                    'angle': row[0],
                    'uses': row[1],
                    'avg_upvotes': round(row[2], 2),
                    'total_upvotes': row[3]
                }
                for row in top_angles
            ]
        }


class PerformanceLogger:
    """Tracks Reddit post performance and identifies top-performing content angles"""
    
    def __init__(self, stats_tracker: StatsTracker):
        self.stats_tracker = stats_tracker
        self.best_angles_path = Path("output/best_angles.txt")
    
    def check_reddit_performance(self):
        """Check Reddit post performance from last 24h and log metrics"""
        print("[ORCH] Checking Reddit performance...")
        
        try:
            import praw
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            
            reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                username=os.getenv('REDDIT_USERNAME'),
                password=os.getenv('REDDIT_PASSWORD'),
                user_agent=os.getenv('REDDIT_USER_AGENT', 'AdultCreatorBot/1.0')
            )
            
            user = reddit.redditor(os.getenv('REDDIT_USERNAME'))
            
            # Get submissions from last 24 hours
            now = datetime.now()
            cutoff = now - timedelta(hours=24)
            
            recent_posts = []
            for submission in user.submissions.new(limit=50):
                post_time = datetime.fromtimestamp(submission.created_utc)
                if post_time >= cutoff:
                    post_data = {
                        'post_id': submission.id,
                        'title': submission.title,
                        'angle': self._extract_angle_from_title(submission.title),
                        'upvotes': submission.score,
                        'comments': submission.num_comments,
                        'clicks_estimated': submission.score * 10  # Rough estimate
                    }
                    recent_posts.append(post_data)
                    
                    # Log to database
                    self.stats_tracker.log_performance('reddit', post_data)
            
            print(f"[ORCH] Logged performance for {len(recent_posts)} recent Reddit posts")
            
            # Update best angles file
            if recent_posts:
                self._update_best_angles(recent_posts)
            
        except Exception as e:
            print(f"[ORCH] Error checking Reddit performance: {e}")
            traceback.print_exc()
    
    def _extract_angle_from_title(self, title: str) -> str:
        """Extract content angle/hook from post title"""
        # Simple heuristic: first sentence or first 50 chars
        angle = title.split('.')[0].split('?')[0].strip()
        return angle[:100] if angle else 'Unknown'
    
    def _update_best_angles(self, recent_posts: List[Dict]):
        """Update best_angles.txt with top performing content angles"""
        # Sort by upvotes
        sorted_posts = sorted(recent_posts, key=lambda x: x['upvotes'], reverse=True)
        top_posts = sorted_posts[:5]
        
        with open(self.best_angles_path, 'w') as f:
            f.write(f"# Top Performing Content Angles\n")
            f.write(f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for i, post in enumerate(top_posts, 1):
                f.write(f"{i}. [{post['upvotes']} upvotes] {post['angle']}\n")
            
            f.write(f"\n# Recent Performance Summary\n")
            f.write(f"Total posts analyzed: {len(recent_posts)}\n")
            f.write(f"Average upvotes: {sum(p['upvotes'] for p in recent_posts) / len(recent_posts):.1f}\n")
            f.write(f"Total engagement: {sum(p['upvotes'] + p['comments'] for p in recent_posts)}\n")
        
        print(f"[ORCH] Updated best angles file: {self.best_angles_path}")


class PipelineOrchestrator:
    """Master controller for the entire content pipeline"""
    
    def __init__(self):
        self.stats_tracker = StatsTracker()
        self.performance_logger = PerformanceLogger(self.stats_tracker)
        self.log_path = Path("output/pipeline_log.txt")
        Path("output").mkdir(exist_ok=True)
    
    def _log(self, message: str):
        """Write to both console and log file"""
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
        
        # Step 1: Generate content
        self._log("STEP 1/3: Generating content with content_brain...")
        try:
            result = content_brain.main()
            stats['content_generated'] = result.get('items_generated', 0)
            self._log(f"Content generation complete: {stats['content_generated']} items")
        except Exception as e:
            self._log(f"ERROR in content_brain: {e}")
            traceback.print_exc()
            stats['errors'] += 1
        
        # Step 2: Generate TikTok content
        self._log("STEP 2/3: Generating TikTok carousels...")
        try:
            result = tiktok_module.main()
            stats['tiktok_exports'] = result.get('exports_created', 0)
            self._log(f"TikTok generation complete: {stats['tiktok_exports']} exports")
        except Exception as e:
            self._log(f"ERROR in tiktok_module: {e}")
            traceback.print_exc()
            stats['errors'] += 1
        
        # Step 3: Post to Reddit
        self._log("STEP 3/3: Posting to Reddit...")
        try:
            result = reddit_module.main()
            stats['reddit_posts_made'] = result.get('posts_made', 0)
            self._log(f"Reddit posting complete: {stats['reddit_posts_made']} posts")
        except Exception as e:
            self._log(f"ERROR in reddit_module: {e}")
            traceback.print_exc()
            stats['errors'] += 1
        
        # Calculate execution time
        execution_time = time.time() - start_time
        stats['execution_time_seconds'] = execution_time
        
        # Log final stats
        self._log(f"Pipeline execution complete in {execution_time:.2f}s")
        self._log(f"Summary: {stats['content_generated']} content | {stats['tiktok_exports']} TikTok | {stats['reddit_posts_made']} Reddit | {stats['errors']} errors")
        
        # Save to database
        self.stats_tracker.log_day(stats)
        
        self._log("=" * 60)
    
    def run_performance_check(self):
        """Run performance tracking (every 6 hours)"""
        self._log("Running performance check...")
        self.performance_logger.check_reddit_performance()
    
    def generate_weekly_summary(self):
        """Generate and display weekly summary report"""
        self._log("Generating weekly summary report...")
        
        summary = self.stats_tracker.get_weekly_summary()
        
        report = [
            "\n" + "=" * 60,
            "WEEKLY SUMMARY REPORT",
            f"Period: {summary['period']}",
            "=" * 60,
            "",
            "PIPELINE ACTIVITY:",
            f"  Days active: {summary['daily_stats']['days_active']}",
            f"  Total content generated: {summary['daily_stats']['total_content_generated']}",
            f"  Total TikTok exports: {summary['daily_stats']['total_tiktok_exports']}",
            f"  Total Reddit posts: {summary['daily_stats']['total_reddit_posts']}",
            f"  Total errors: {summary['daily_stats']['total_errors']}",
            f"  Avg execution time: {summary['daily_stats']['avg_execution_time_seconds']}s",
            "",
            "PERFORMANCE BY PLATFORM:",
        ]
        
        for platform in summary['performance_by_platform']:
            report.extend([
                f"  {platform['platform'].upper()}:",
                f"    Posts: {platform['post_count']}",
                f"    Total upvotes: {platform['total_upvotes']}",
                f"    Total comments: {platform['total_comments']}",
                f"    Avg upvotes: {platform['avg_upvotes']}",
            ])
        
        report.extend(["", "TOP PERFORMING CONTENT ANGLES:"])
        for i, angle in enumerate(summary['top_angles'], 1):
            report.append(f"  {i}. {angle['angle']}")
            report.append(f"     Used {angle['uses']}x | Avg {angle['avg_upvotes']} upvotes | Total {angle['total_upvotes']}")
        
        report.append("=" * 60 + "\n")
        
        report_text = "\n".join(report)
        print(report_text)
        
        # Save to file
        report_path = Path("output") / f"weekly_summary_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(report_path, 'w') as f:
            f.write(report_text)
        
        self._log(f"Weekly summary saved to {report_path}")
    
    def get_queue_status(self):
        """Show current queue status from queue.db"""
        queue_db = Path("output/queue.db")
        
        if not queue_db.exists():
            print("[ORCH] No queue database found (queue.db)")
            return
        
        try:
            conn = sqlite3.connect(queue_db)
            cursor = conn.cursor()
            
            # Check if content_queue table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='content_queue'")
            if not cursor.fetchone():
                print("[ORCH] Queue database exists but content_queue table not found")
                conn.close()
                return
            
            # Get queue stats
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
            print(f"[ORCH] Error reading queue status: {e}")


def setup_scheduler(orchestrator: PipelineOrchestrator):
    """Setup scheduled tasks"""
    print("[ORCH] Setting up scheduler...")
    
    # Daily pipeline at 8:00 AM
    schedule.every().day.at("08:00").do(orchestrator.run_daily)
    print("[ORCH]   - Daily pipeline: 8:00 AM")
    
    # Performance check every 6 hours
    schedule.every(6).hours.do(orchestrator.run_performance_check)
    print("[ORCH]   - Performance check: Every 6 hours")
    
    # Weekly summary on Sunday at 9:00 AM
    schedule.every().sunday.at("09:00").do(orchestrator.generate_weekly_summary)
    print("[ORCH]   - Weekly summary: Sundays at 9:00 AM")
    
    print("[ORCH] Scheduler ready. Running loop...")


def main():
    """CLI interface"""
    orchestrator = PipelineOrchestrator()
    
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py [run|schedule|stats|status]")
        print("  run      - Run pipeline once now")
        print("  schedule - Start scheduler loop (runs continuously)")
        print("  stats    - Print weekly summary")
        print("  status   - Show content queue status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "run":
        print("[ORCH] Running pipeline once...")
        orchestrator.run_daily()
    
    elif command == "schedule":
        setup_scheduler(orchestrator)
        
        # Run once immediately on startup
        print("[ORCH] Running initial pipeline execution...")
        orchestrator.run_daily()
        
        # Start scheduler loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    elif command == "stats":
        orchestrator.generate_weekly_summary()
    
    elif command == "status":
        orchestrator.get_queue_status()
    
    else:
        print(f"[ORCH] Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
