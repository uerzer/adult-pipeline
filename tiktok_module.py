"""
TikTok Carousel Generator for Adult Creator Traffic Pipeline

Generates TikTok carousel slide images (1080x1920) with text overlays,
assembles them into MP4 videos, and exports for Postiz or manual upload.

Requirements: pillow, opencv-python, moviepy, requests
"""

import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
import requests
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import cv2
    import numpy as np
    from moviepy.editor import ImageSequenceClip, AudioFileClip
except ImportError as e:
    print(f"[TIKTOK] Missing dependency: {e}")
    print("[TIKTOK] Install with: pip install pillow opencv-python moviepy requests")
    raise


class TextOverlay:
    """Handles text overlay operations on images."""
    
    def __init__(self, font_path: Optional[str] = None):
        """Initialize with custom font or download Roboto-Bold if needed."""
        self.font_path = font_path or self._ensure_font()
        
    def _ensure_font(self) -> str:
        """Download Roboto-Bold.ttf from Google Fonts if not present."""
        font_dir = Path("fonts")
        font_dir.mkdir(exist_ok=True)
        font_path = font_dir / "Roboto-Bold.ttf"
        
        if not font_path.exists():
            print("[TIKTOK] Downloading Roboto-Bold font...")
            url = "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf"
            response = requests.get(url)
            if response.status_code == 200:
                font_path.write_bytes(response.content)
                print("[TIKTOK] Font downloaded successfully")
            else:
                print("[TIKTOK] Font download failed, using default font")
                return None
        
        return str(font_path)
    
    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get font at specified size."""
        try:
            if self.font_path:
                return ImageFont.truetype(self.font_path, size)
        except Exception as e:
            print(f"[TIKTOK] Font loading failed: {e}, using default")
        
        # Fallback to default font
        return ImageFont.load_default()
    
    def add_hook_text(self, image: Image.Image, text: str) -> Image.Image:
        """Add large centered bold text with semi-transparent dark background bar."""
        img = image.copy()
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Calculate text size
        font = self._get_font(80)
        
        # Word wrap for long text
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > 900:  # Max width
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate total text height
        line_height = 100
        total_height = len(lines) * line_height
        
        # Draw semi-transparent background bar
        y_start = (1920 - total_height) // 2 - 40
        y_end = y_start + total_height + 80
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([(0, y_start), (1080, y_end)], fill=(0, 0, 0, 180))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        
        # Draw text with shadow
        draw = ImageDraw.Draw(img)
        y_offset = y_start + 40
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (1080 - text_width) // 2
            
            # Shadow
            draw.text((x + 3, y_offset + 3), line, font=font, fill=(0, 0, 0, 255))
            # Main text
            draw.text((x, y_offset), line, font=font, fill=(255, 255, 255, 255))
            
            y_offset += line_height
        
        return img
    
    def add_subtle_text(self, image: Image.Image, text: str) -> Image.Image:
        """Add smaller bottom text with white shadow."""
        img = image.copy()
        draw = ImageDraw.Draw(img)
        
        font = self._get_font(50)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        x = (1080 - text_width) // 2
        y = 1750  # Near bottom
        
        # Shadow
        draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 255))
        # Main text
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
        
        return img
    
    def add_cta_slide(self, username: str, of_link_text: str = "Link in bio") -> Image.Image:
        """Generate final black CTA slide with white text."""
        img = Image.new('RGB', (1080, 1920), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Main CTA text
        font_large = self._get_font(90)
        cta_text = "Follow for more"
        bbox = draw.textbbox((0, 0), cta_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        x = (1080 - text_width) // 2
        y = 700
        
        draw.text((x, y), cta_text, font=font_large, fill=(255, 255, 255, 255))
        
        # Arrow emoji (unicode)
        arrow_font = self._get_font(120)
        arrow = "↑"
        bbox = draw.textbbox((0, 0), arrow, font=arrow_font)
        arrow_width = bbox[2] - bbox[0]
        x_arrow = (1080 - arrow_width) // 2
        draw.text((x_arrow, y + 150), arrow, font=arrow_font, fill=(255, 255, 255, 255))
        
        # Link text
        font_medium = self._get_font(60)
        bbox = draw.textbbox((0, 0), of_link_text, font=font_medium)
        link_width = bbox[2] - bbox[0]
        x_link = (1080 - link_width) // 2
        draw.text((x_link, y + 350), of_link_text, font=font_medium, fill=(255, 255, 255, 255))
        
        # Username at bottom
        font_small = self._get_font(45)
        username_text = f"@{username}"
        bbox = draw.textbbox((0, 0), username_text, font=font_small)
        user_width = bbox[2] - bbox[0]
        x_user = (1080 - user_width) // 2
        draw.text((x_user, 1800), username_text, font=font_small, fill=(200, 200, 200, 255))
        
        return img
    
    def add_watermark(self, image: Image.Image, handle: str) -> Image.Image:
        """Add small handle text in top-right corner."""
        img = image.copy()
        draw = ImageDraw.Draw(img)
        
        font = self._get_font(35)
        watermark_text = f"@{handle}"
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        
        x = 1080 - text_width - 30
        y = 30
        
        # Shadow for readability
        draw.text((x + 1, y + 1), watermark_text, font=font, fill=(0, 0, 0, 200))
        # Main text
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 220))
        
        return img


class CarouselGenerator:
    """Generates TikTok carousel slide images."""
    
    def __init__(self, username: str):
        """Initialize carousel generator."""
        self.username = username
        self.text_overlay = TextOverlay()
        self.slide_size = (1080, 1920)  # TikTok portrait format
    
    def _download_image(self, prompt: str) -> Image.Image:
        """Download SFW teaser image from Pollinations.ai."""
        # Pollinations.ai free API
        safe_prompt = prompt.replace(" ", "%20")
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1080&height=1920&nologo=true"
        
        print(f"[TIKTOK] Downloading image for: {prompt[:50]}...")
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                # Ensure correct size
                if img.size != self.slide_size:
                    img = img.resize(self.slide_size, Image.Resampling.LANCZOS)
                return img.convert('RGB')
            else:
                print(f"[TIKTOK] Image download failed: {response.status_code}")
                return self._create_placeholder()
        except Exception as e:
            print(f"[TIKTOK] Image download error: {e}")
            return self._create_placeholder()
    
    def _create_placeholder(self) -> Image.Image:
        """Create a placeholder gradient image."""
        img = Image.new('RGB', self.slide_size, color=(50, 50, 80))
        draw = ImageDraw.Draw(img)
        
        # Simple gradient effect
        for y in range(1920):
            color_val = int(50 + (y / 1920) * 100)
            draw.line([(0, y), (1080, y)], fill=(color_val, color_val // 2, color_val + 50))
        
        return img
    
    def generate_slides(self, hook: str, teaser_prompts: List[str], cta_link_text: str = "Link in bio") -> List[Image.Image]:
        """
        Generate 6 carousel slides.
        
        Args:
            hook: Hook text for slide 1
            teaser_prompts: List of 4 prompts for Pollinations.ai teaser images
            cta_link_text: Text for CTA slide
        
        Returns:
            List of 6 PIL Images
        """
        slides = []
        
        # Slide 1: Hook with bold text
        print("[TIKTOK] Generating slide 1: Hook")
        hook_bg = self._download_image("aesthetic minimal gradient background pink purple")
        hook_slide = self.text_overlay.add_hook_text(hook_bg, hook)
        hook_slide = self.text_overlay.add_watermark(hook_slide, self.username)
        slides.append(hook_slide)
        
        # Slides 2-5: SFW teaser images with subtle text
        teaser_texts = [
            "Swipe for more...",
            "You won't believe this",
            "Almost there...",
            "Last one..."
        ]
        
        for i, (prompt, text) in enumerate(zip(teaser_prompts, teaser_texts), 2):
            print(f"[TIKTOK] Generating slide {i}: Teaser")
            teaser_img = self._download_image(prompt)
            teaser_slide = self.text_overlay.add_subtle_text(teaser_img, text)
            teaser_slide = self.text_overlay.add_watermark(teaser_slide, self.username)
            slides.append(teaser_slide)
        
        # Slide 6: CTA
        print("[TIKTOK] Generating slide 6: CTA")
        cta_slide = self.text_overlay.add_cta_slide(self.username, cta_link_text)
        slides.append(cta_slide)
        
        return slides


class VideoAssembler:
    """Assembles slides into MP4 video for TikTok."""
    
    def __init__(self, output_dir: str = "output/tiktok"):
        """Initialize video assembler."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.slides_dir = self.output_dir / "slides"
        self.slides_dir.mkdir(exist_ok=True)
    
    def save_slides(self, slides: List[Image.Image], prefix: str = "") -> List[str]:
        """Save individual slides as JPEGs."""
        slide_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, slide in enumerate(slides, 1):
            filename = f"{prefix}slide_{i}_{timestamp}.jpg"
            filepath = self.slides_dir / filename
            slide.save(filepath, quality=95)
            slide_paths.append(str(filepath))
            print(f"[TIKTOK] Saved slide {i}: {filepath}")
        
        return slide_paths
    
    def create_video(self, slides: List[Image.Image], duration_per_slide: float = 3.0, output_name: Optional[str] = None) -> str:
        """
        Create MP4 video from slides.
        
        Args:
            slides: List of PIL Images
            duration_per_slide: Seconds per slide (default 3)
            output_name: Custom output filename (optional)
        
        Returns:
            Path to output video file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_name:
            video_path = self.output_dir / f"{output_name}.mp4"
        else:
            video_path = self.output_dir / f"tiktok_carousel_{timestamp}.mp4"
        
        print(f"[TIKTOK] Creating video: {video_path}")
        
        # Convert PIL images to numpy arrays for moviepy
        frames = []
        for slide in slides:
            frame = np.array(slide)
            frames.append(frame)
        
        # Create video clip
        fps = 30
        frame_count = int(duration_per_slide * fps)
        
        # Duplicate each frame to achieve desired duration
        video_frames = []
        for frame in frames:
            for _ in range(frame_count):
                video_frames.append(frame)
        
        # Create clip
        clip = ImageSequenceClip(video_frames, fps=fps)
        
        # Write video file (TikTok requires audio, but we'll add silent track)
        clip.write_videofile(
            str(video_path),
            codec='libx264',
            audio=False,  # No audio, user will add music in TikTok app
            preset='medium',
            fps=fps,
            logger=None  # Suppress moviepy verbose output
        )
        
        print(f"[TIKTOK] Video created: {video_path} ({len(slides)} slides, {len(slides) * duration_per_slide}s)")
        
        return str(video_path)


class PostizExporter:
    """Exports content to Postiz (free tier social scheduler) or saves locally."""
    
    def __init__(self):
        """Initialize with Postiz API key from env."""
        self.api_key = os.getenv('POSTIZ_API_KEY')
        self.base_url = "https://api.postiz.com/v1"
    
    def export(self, video_path: str, caption: str, schedule_time: Optional[str] = None) -> bool:
        """
        Export to Postiz if API key present, otherwise print manual upload message.
        
        Args:
            video_path: Path to video file
            caption: Post caption
            schedule_time: ISO format timestamp (optional)
        
        Returns:
            True if exported/saved successfully
        """
        if not self.api_key:
            print("[TIKTOK] No POSTIZ_API_KEY found in environment")
            print(f"[TIKTOK] MANUAL UPLOAD NEEDED: {video_path}")
            print(f"[TIKTOK] Caption: {caption}")
            return True
        
        print("[TIKTOK] Attempting Postiz export...")
        
        try:
            # Postiz API upload endpoint (example - adjust based on actual API)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "platform": "tiktok",
                "media": video_path,
                "caption": caption,
                "schedule_time": schedule_time
            }
            
            # Note: This is a placeholder - actual Postiz API may differ
            # User should verify API documentation
            response = requests.post(
                f"{self.base_url}/posts",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                print("[TIKTOK] Successfully exported to Postiz")
                return True
            else:
                print(f"[TIKTOK] Postiz export failed: {response.status_code}")
                print(f"[TIKTOK] MANUAL UPLOAD NEEDED: {video_path}")
                return False
        
        except Exception as e:
            print(f"[TIKTOK] Postiz export error: {e}")
            print(f"[TIKTOK] MANUAL UPLOAD NEEDED: {video_path}")
            return False


def main():
    """
    Main function: read pending TikTok content from queue.db,
    generate carousels, export or save for manual upload.
    """
    print("[TIKTOK] Starting TikTok carousel generator...")
    
    # Database path
    db_path = Path("output/queue.db")
    
    if not db_path.exists():
        print(f"[TIKTOK] Database not found: {db_path}")
        print("[TIKTOK] Creating sample database...")
        
        # Create sample database schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tiktok_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                hook TEXT NOT NULL,
                teaser_prompt_1 TEXT,
                teaser_prompt_2 TEXT,
                teaser_prompt_3 TEXT,
                teaser_prompt_4 TEXT,
                cta_link_text TEXT DEFAULT 'Link in bio',
                caption TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        """)
        
        # Insert sample data
        cursor.execute("""
            INSERT INTO tiktok_queue (username, hook, teaser_prompt_1, teaser_prompt_2, teaser_prompt_3, teaser_prompt_4, caption)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "yourhandle",
            "POV: you found my secret page...",
            "aesthetic woman in cozy bedroom lighting, soft focus, SFW portrait",
            "artistic boudoir photography, elegant pose, professional lighting, SFW",
            "fashion model portrait, studio lighting, glamorous, SFW",
            "artistic photography, mysterious mood, dramatic shadows, SFW",
            "You won't believe what's in my bio 👀 #fyp #linkinbio"
        ))
        
        conn.commit()
        conn.close()
        
        print("[TIKTOK] Sample database created with 1 pending item")
    
    # Process queue
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, hook, teaser_prompt_1, teaser_prompt_2, 
               teaser_prompt_3, teaser_prompt_4, cta_link_text, caption
        FROM tiktok_queue
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT 10
    """)
    
    rows = cursor.fetchall()
    
    if not rows:
        print("[TIKTOK] No pending items in queue")
        conn.close()
        return
    
    print(f"[TIKTOK] Found {len(rows)} pending items")
    
    # Initialize components
    exporter = PostizExporter()
    
    for row in rows:
        item_id, username, hook, tp1, tp2, tp3, tp4, cta_text, caption = row
        
        print(f"\n[TIKTOK] Processing item {item_id}: @{username}")
        
        teaser_prompts = [tp1, tp2, tp3, tp4]
        
        try:
            # Generate carousel
            generator = CarouselGenerator(username)
            slides = generator.generate_slides(hook, teaser_prompts, cta_text)
            
            # Assemble video
            assembler = VideoAssembler()
            slide_paths = assembler.save_slides(slides, prefix=f"{username}_")
            video_path = assembler.create_video(slides, output_name=f"{username}_{item_id}")
            
            # Export
            success = exporter.export(video_path, caption or "")
            
            # Update database
            if success:
                cursor.execute("""
                    UPDATE tiktok_queue
                    SET status = 'completed', processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item_id,))
                print(f"[TIKTOK] Item {item_id} completed successfully")
            else:
                cursor.execute("""
                    UPDATE tiktok_queue
                    SET status = 'failed', processed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item_id,))
                print(f"[TIKTOK] Item {item_id} marked as failed")
            
            conn.commit()
            
            # Rate limiting (avoid hammering Pollinations API)
            time.sleep(2)
        
        except Exception as e:
            print(f"[TIKTOK] Error processing item {item_id}: {e}")
            cursor.execute("""
                UPDATE tiktok_queue
                SET status = 'error', processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (item_id,))
            conn.commit()
    
    conn.close()
    print("\n[TIKTOK] Processing complete!")


if __name__ == "__main__":
    main()
