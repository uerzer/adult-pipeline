"""
Content Brain - AI-powered content generation for adult creator pipeline

Uses FREE LLM APIs with NO signup and NO API keys:
  1. UncloseAI (hermes.ai.unturf.com) - primary
  2. TorGPT (torgpt.space) - fallback
  3. Pollinations.ai text - second fallback

Image generation via Pollinations.ai (free, no key).

Environment Variables:
  None required. Fully autonomous.
"""

import os
import sqlite3
import json
import time
import random
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote

import requests
from PIL import Image
from io import BytesIO


# ─── Free LLM Provider Configs ──────────────────────────────────────

LLM_PROVIDERS = [
    {
        "name": "UncloseAI-Hermes",
        "url": "https://hermes.ai.unturf.com/v1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer choose-any-value"
        },
        "model": "hermes-3",
        "format": "openai"  # OpenAI-compatible
    },
    {
        "name": "UncloseAI-Qwen",
        "url": "https://qwen.ai.unturf.com/v1/chat/completions",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer choose-any-value"
        },
        "model": "qwen-3-coder",
        "format": "openai"
    },
    {
        "name": "TorGPT",
        "url": "https://torgpt.space/api/v1/chat",
        "headers": {
            "Content-Type": "application/json"
        },
        "model": None,  # TorGPT doesn't need model param
        "format": "torgpt"
    },
    {
        "name": "Pollinations-Text",
        "url": "https://text.pollinations.ai/",
        "headers": {
            "Content-Type": "application/json"
        },
        "model": "openai",
        "format": "pollinations"
    }
]


class ContentBrain:
    """
    Uses free, no-auth LLM APIs with automatic fallback chain.
    No API keys, no signup, no environment variables needed.
    """

    def __init__(self):
        """Initialize ContentBrain - no credentials needed."""
        self.providers = LLM_PROVIDERS.copy()
        self._active_provider_idx = 0
        print("[BRAIN] ContentBrain initialized (free LLM APIs, no keys needed)")
        print(f"[BRAIN] Provider chain: {' -> '.join(p['name'] for p in self.providers)}")

    def _call_openai_format(self, provider: dict, prompt: str) -> str:
        """Call an OpenAI-compatible API endpoint."""
        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": "You are a creative content writer for social media marketing. Follow instructions precisely. Return ONLY what is asked, no extra commentary."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,
            "temperature": 0.85
        }
        resp = requests.post(
            provider["url"],
            headers=provider["headers"],
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    def _call_torgpt(self, provider: dict, prompt: str) -> str:
        """Call TorGPT API."""
        payload = {
            "messages": [
                {"role": "system", "content": "You are a creative content writer for social media marketing. Follow instructions precisely. Return ONLY what is asked."},
                {"role": "user", "content": prompt}
            ]
        }
        resp = requests.post(
            provider["url"],
            headers=provider["headers"],
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        # TorGPT returns {"response": "..."} or {"choices": [...]}
        if "response" in data:
            return data["response"].strip()
        elif "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        else:
            return str(data).strip()

    def _call_pollinations(self, provider: dict, prompt: str) -> str:
        """Call Pollinations text API."""
        payload = {
            "messages": [
                {"role": "system", "content": "You are a creative content writer. Follow instructions precisely. Return ONLY what is asked."},
                {"role": "user", "content": prompt}
            ],
            "model": provider["model"],
            "seed": random.randint(1, 999999)
        }
        resp = requests.post(
            provider["url"],
            headers=provider["headers"],
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        # Pollinations may return plain text or JSON
        try:
            data = resp.json()
            if isinstance(data, str):
                return data.strip()
            if "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            return str(data).strip()
        except (json.JSONDecodeError, ValueError):
            return resp.text.strip()

    def _generate(self, prompt: str, max_retries: int = 2) -> str:
        """
        Generate content with automatic provider fallback.
        Tries each provider in chain, falls back on failure.
        """
        errors = []

        for provider in self.providers:
            for attempt in range(max_retries):
                try:
                    fmt = provider["format"]
                    if fmt == "openai":
                        result = self._call_openai_format(provider, prompt)
                    elif fmt == "torgpt":
                        result = self._call_torgpt(provider, prompt)
                    elif fmt == "pollinations":
                        result = self._call_pollinations(provider, prompt)
                    else:
                        raise ValueError(f"Unknown format: {fmt}")

                    if result and len(result) > 5:
                        print(f"[BRAIN] Generated via {provider['name']} ({len(result)} chars)")
                        return result

                except Exception as e:
                    wait = (attempt + 1) * 2
                    errors.append(f"{provider['name']} attempt {attempt+1}: {e}")
                    print(f"[BRAIN] {provider['name']} attempt {attempt+1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(wait)

            print(f"[BRAIN] {provider['name']} exhausted, trying next provider...")

        # All providers failed
        error_log = "\n".join(errors)
        raise RuntimeError(f"[BRAIN] All LLM providers failed:\n{error_log}")

    # ─── Content Generation Methods ──────────────────────────────────

    def generate_reddit_title(self) -> str:
        """Generate a hook-style Reddit post title with curiosity gap. SFW."""
        prompt = """Generate a single Reddit post title for an adult content creator's profile teaser.

Requirements:
- Hook-style with curiosity gap
- SFW (no explicit words)
- Builds intrigue and mystery
- 8-15 words max
- Makes people want to click profile
- Examples: "The story of how I went from shy to this...", "What happens when an introvert discovers confidence", "They said I couldn't pull this off..."

Return ONLY the title, no quotes, no explanation."""

        title = self._generate(prompt)
        # Clean up any stray quotes
        title = title.strip('"\'')
        print(f"[BRAIN] Generated Reddit title: {title}")
        return title

    def generate_reddit_caption(self, title: str) -> str:
        """Generate SFW Reddit caption that builds intrigue."""
        prompt = f"""Generate a Reddit post caption to accompany this title: "{title}"

Requirements:
- 2-4 sentences
- SFW (safe for work, no explicit language)
- Builds curiosity and intrigue
- Personal and authentic tone
- Must end with "link in bio" or similar call to action
- No emojis
- Makes people want to check profile

Return ONLY the caption text."""

        caption = self._generate(prompt)
        print(f"[BRAIN] Generated Reddit caption ({len(caption)} chars)")
        return caption

    def generate_tiktok_hooks(self, count: int = 6) -> List[str]:
        """Generate TikTok carousel text overlay hooks."""
        prompt = f"""Generate {count} short text hooks for a TikTok carousel about an adult content creator's journey/transformation.

Requirements:
- Each hook is 5-10 words max
- SFW appropriate
- Creates curiosity and story progression
- Could work as text overlays on images
- Tells a mini-story across the {count} slides
- Examples: "Before I discovered my confidence...", "They told me I couldn't...", "Then everything changed..."

Return as a numbered list, one hook per line."""

        hooks_text = self._generate(prompt)
        hooks = [line.split('. ', 1)[1].strip() if '. ' in line else line.strip()
                 for line in hooks_text.split('\n') if line.strip()]
        hooks = [h for h in hooks if h and not h.startswith('#')][:count]

        print(f"[BRAIN] Generated {len(hooks)} TikTok hooks")
        return hooks

    def generate_dm_script(self) -> str:
        """Generate a warm, personal DM welcome script for OnlyFans."""
        prompt = """Generate a welcome DM script for a new OnlyFans subscriber.

Requirements:
- Warm and personal tone
- 3-4 sentences
- Thanks them for subscribing
- Makes them feel special
- Asks an open-ended question to start conversation
- Not salesy or spammy
- Natural and authentic

Return ONLY the DM text."""

        dm_script = self._generate(prompt)
        print(f"[BRAIN] Generated DM script ({len(dm_script)} chars)")
        return dm_script

    def generate_content_angles(self, count: int = 10) -> List[str]:
        """Generate different content angles/personas/scenarios for variety."""
        prompt = f"""Generate {count} different content angles/personas/scenarios for an adult content creator to explore.

Requirements:
- Each angle is a unique persona, scenario, or content theme
- Variety across different styles (confident, shy, playful, mysterious, etc.)
- 1-2 sentences describing each angle
- Helps creator avoid repetitive content
- SFW descriptions

Return as a numbered list."""

        angles_text = self._generate(prompt)
        angles = [line.split('. ', 1)[1].strip() if '. ' in line else line.strip()
                  for line in angles_text.split('\n') if line.strip()]
        angles = [a for a in angles if a and not a.startswith('#')][:count]

        print(f"[BRAIN] Generated {len(angles)} content angles")
        return angles


class ImageBrain:
    """
    Uses Pollinations.ai (free, no API key needed) to generate SFW teaser images.
    """

    def __init__(self, output_dir: str = "output/images"):
        """Initialize ImageBrain with output directory."""
        self.output_dir = output_dir
        self.base_url = "https://image.pollinations.ai/prompt"
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"[BRAIN] ImageBrain initialized, output dir: {self.output_dir}")

    def generate_teaser_image(
        self,
        description: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate a SFW teaser image (tasteful, lingerie/swimwear level).
        Returns local file path or None if failed.
        """
        if description is None:
            description = (
                "professional portrait photography, confident woman, "
                "tasteful lingerie, soft studio lighting, elegant pose, "
                "fashion photography style, high quality, artistic"
            )

        safe_prompt = f"{description}, SFW, tasteful, artistic, professional photography"

        try:
            encoded_prompt = quote(safe_prompt)
            url = f"{self.base_url}/{encoded_prompt}"
            if seed is not None:
                url += f"?seed={seed}"

            print(f"[BRAIN] Generating image from Pollinations.ai...")

            response = requests.get(url, timeout=60)
            response.raise_for_status()

            img = Image.open(BytesIO(response.content))

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            seed_str = f"_seed{seed}" if seed else ""
            filename = f"teaser_{timestamp}{seed_str}.png"
            filepath = os.path.join(self.output_dir, filename)

            img.save(filepath, "PNG")
            print(f"[BRAIN] Image saved: {filepath} ({img.size[0]}x{img.size[1]})")
            return filepath

        except Exception as e:
            print(f"[BRAIN] ERROR: Image generation failed: {e}")
            return None

    def generate_batch(
        self,
        count: int,
        base_prompt: Optional[str] = None
    ) -> List[str]:
        """Generate multiple images with different seeds."""
        print(f"[BRAIN] Generating batch of {count} images...")
        images = []

        for i in range(count):
            seed = int(time.time() * 1000) + i
            filepath = self.generate_teaser_image(description=base_prompt, seed=seed)
            if filepath:
                images.append(filepath)
            if i < count - 1:
                time.sleep(2)

        print(f"[BRAIN] Batch complete: {len(images)}/{count} images generated")
        return images


class ContentQueue:
    """SQLite-backed content queue for managing generated content."""

    def __init__(self, db_path: str = "output/queue.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        print(f"[BRAIN] ContentQueue initialized: {db_path}")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                platform TEXT NOT NULL,
                content_text TEXT NOT NULL,
                image_path TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                posted_at TIMESTAMP,
                metadata TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON content_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_platform_status ON content_queue(platform, status)")
        conn.commit()
        conn.close()

    def add_item(self, content_type: str, platform: str, content_text: str,
                 image_path: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        metadata_json = json.dumps(metadata) if metadata else None
        cursor.execute("""
            INSERT INTO content_queue (type, platform, content_text, image_path, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (content_type, platform, content_text, image_path, metadata_json))
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"[BRAIN] Added to queue: {content_type}/{platform} (ID: {item_id})")
        return item_id

    def get_pending(self, platform: Optional[str] = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if platform:
            cursor.execute("""
                SELECT * FROM content_queue WHERE status = 'pending' AND platform = ?
                ORDER BY created_at ASC
            """, (platform,))
        else:
            cursor.execute("SELECT * FROM content_queue WHERE status = 'pending' ORDER BY created_at ASC")
        rows = cursor.fetchall()
        conn.close()
        items = [dict(row) for row in rows]
        print(f"[BRAIN] Retrieved {len(items)} pending items" + (f" for {platform}" if platform else ""))
        return items

    def mark_posted(self, item_id: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE content_queue SET status = 'posted', posted_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()
        print(f"[BRAIN] Marked item {item_id} as posted")

    def mark_failed(self, item_id: int, error: Optional[str] = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM content_queue WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        metadata = json.loads(row[0]) if row and row[0] else {}
        metadata['error'] = error or "Unknown error"
        metadata['failed_at'] = datetime.now().isoformat()
        cursor.execute("UPDATE content_queue SET status = 'failed', metadata = ? WHERE id = ?",
                       (json.dumps(metadata), item_id))
        conn.commit()
        conn.close()
        print(f"[BRAIN] Marked item {item_id} as failed: {error}")

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) as count FROM content_queue GROUP BY status")
        stats = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("SELECT COUNT(*) FROM content_queue")
        stats['total'] = cursor.fetchone()[0]
        conn.close()
        return stats


def main():
    """
    Generate a full day's content batch:
    - 3 Reddit posts (title + caption + image each)
    - 6 TikTok carousel hooks
    - 1 DM script
    """
    print("[BRAIN] ========================================")
    print("[BRAIN] Starting daily content generation batch")
    print("[BRAIN] ========================================\n")

    try:
        content_brain = ContentBrain()
        image_brain = ImageBrain()
        queue = ContentQueue()

        # Reddit posts
        print("\n[BRAIN] --- GENERATING REDDIT POSTS ---")
        for i in range(3):
            print(f"\n[BRAIN] Reddit post {i+1}/3:")
            title = content_brain.generate_reddit_title()
            caption = content_brain.generate_reddit_caption(title)
            image_path = image_brain.generate_teaser_image()

            if image_path:
                queue.add_item(
                    content_type='reddit_post',
                    platform='reddit',
                    content_text=json.dumps({'title': title, 'caption': caption}),
                    image_path=image_path,
                    metadata={'post_number': i+1}
                )
            else:
                print(f"[BRAIN] WARNING: Post {i+1} has no image, adding text-only")
                queue.add_item(
                    content_type='reddit_post',
                    platform='reddit',
                    content_text=json.dumps({'title': title, 'caption': caption}),
                    metadata={'post_number': i+1, 'no_image': True}
                )

            if i < 2:
                time.sleep(3)

        # TikTok hooks
        print("\n[BRAIN] --- GENERATING TIKTOK HOOKS ---")
        hooks = content_brain.generate_tiktok_hooks(count=6)
        queue.add_item(
            content_type='tiktok_carousel',
            platform='tiktok',
            content_text=json.dumps({'hooks': hooks}),
            metadata={'hook_count': len(hooks)}
        )

        # DM script
        print("\n[BRAIN] --- GENERATING DM SCRIPT ---")
        dm_script = content_brain.generate_dm_script()
        queue.add_item(
            content_type='dm_script',
            platform='onlyfans',
            content_text=dm_script,
            metadata={'script_type': 'welcome'}
        )

        # Summary
        print("\n[BRAIN] ========================================")
        print("[BRAIN] BATCH GENERATION COMPLETE")
        print("[BRAIN] ========================================")

        stats = queue.get_stats()
        print(f"\n[BRAIN] Queue Stats:")
        for status, count in stats.items():
            print(f"[BRAIN]   {status}: {count}")

        print("\n[BRAIN] All content saved to queue.db")
        print("[BRAIN] Images saved to output/images/")
        print("[BRAIN] Ready for posting modules to process!")

    except Exception as e:
        print(f"\n[BRAIN] FATAL ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
