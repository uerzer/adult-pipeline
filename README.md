# Adult Creator Traffic Pipeline

Fully automated pipeline for adult content creators to drive traffic from Reddit and TikTok to OnlyFans.

## Architecture

```
orchestrator.py          # Master controller - runs everything daily
├── content_brain.py     # Gemini AI content generation + Pollinations image gen
├── reddit_module.py     # Reddit account warming + SFW teaser posting
├── tiktok_module.py     # Carousel slide generator + video assembler
└── link_hub/            # Static landing page (deployed to GitHub Pages)
    └── index.html
```

## Quick Start

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Set up credentials
cp .env.example .env
# Edit .env with your keys

# 3. Run once
python orchestrator.py run

# 4. Start daily scheduler
python orchestrator.py schedule
```

## Free APIs Used

| Tool | Cost | Purpose |
|------|------|----------|
| Gemini 1.5 Flash | Free tier | Caption/hook/DM generation |
| Pollinations.ai | Completely free | SFW teaser image generation |
| PRAW (Reddit) | Free | Reddit posting via official API |
| GitHub Pages | Free | Link hub hosting (live) |

## Modules

- **content_brain.py** - Generates Reddit titles, captions, TikTok hooks, DM scripts using Gemini. Queues everything in SQLite.
- **reddit_module.py** - Progressive account warming (week 1-2: lurk, week 3-4: soft post, week 5+: full rotation). Human behavior simulation.
- **tiktok_module.py** - Creates 6-slide 1080x1920 carousels with hook text, teaser images, CTA slide. Exports as MP4 or individual JPEGs.
- **link_hub/** - High-converting dark-theme landing page. Deployed to GitHub Pages.
- **orchestrator.py** - Ties everything together. Runs at 8am daily, performance checks every 6h, weekly reports Sunday.

## Credentials Needed

- `GEMINI_API_KEY` - free at aistudio.google.com
- Reddit app credentials - free at reddit.com/prefs/apps
- `POSTIZ_API_KEY` - optional, for scheduled TikTok drafts

## Notes

- A `.gitignore` is included -- never commit your `.env` file.
- GitHub Pages is live for the `link_hub/` landing page.
