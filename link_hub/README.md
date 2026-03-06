# Link Hub - Adult Creator Landing Page

A high-converting, mobile-optimized link-in-bio page for adult content creators. Dark theme with hot pink accents, optimized for fast load times and conversion.

## 🎨 Features

- **Mobile-first design** - Looks perfect on phones (where 90% of traffic comes from)
- **Fast loading** - Single HTML file, no external dependencies
- **High contrast** - Black background with hot pink CTAs for maximum attention
- **Social proof** - Subscriber count badge to build trust
- **Clear hierarchy** - Primary CTA stands out, secondary links below

## 📝 What to Edit

Open `index.html` and look for comments marked `EDIT THIS`:

### 1. Profile Photo (Line ~108)
```html
<img src="assets/photo.jpg" alt="Profile Photo" class="profile-photo">
```
- Replace `assets/photo.jpg` with your photo URL or path
- Option 1: Upload photo to `assets/photo.jpg` in same directory
- Option 2: Use full URL like `https://i.imgur.com/yourphoto.jpg`

### 2. Creator Name (Line ~111)
```html
<h1 class="creator-name">Your Name</h1>
```
- Replace "Your Name" with your stage name

### 3. Bio Tagline (Line ~114)
```html
<p class="bio">Your exclusive content, daily updates 🔥</p>
```
- Short, enticing description (keep under 60 characters)

### 4. Social Proof Number (Line ~117)
```html
<div class="social-proof">Join 2,400+ subscribers</div>
```
- Update the subscriber count (be honest, or use "Join VIP Club" if starting out)

### 5. Primary CTA Link (Line ~121)
```html
<a href="#your-of-link" class="primary-cta" onclick="trackClick('primary-cta')">
```
- Replace `#your-of-link` with your OnlyFans URL (or Fansly, etc.)
- Example: `https://onlyfans.com/yourprofile`

### 6. Feature Bullets (Lines ~127-131)
```html
<div class="feature-item">Daily exclusive content</div>
<div class="feature-item">Direct DMs answered</div>
<div class="feature-item">Custom requests welcome</div>
```
- Customize to your unique selling points

### 7. Secondary Social Links (Lines ~136-148)
Replace the `#reddit-link`, `#tiktok-link`, `#instagram-link` placeholders:
```html
<a href="https://reddit.com/u/yourprofile" class="secondary-link">
<a href="https://tiktok.com/@yourprofile" class="secondary-link">
<a href="https://instagram.com/yourprofile" class="secondary-link">
```

---

## 🚀 Deployment Options

### Option 1: GitHub Pages (Free, Custom Domain Supported)

**Time: ~5 minutes**

1. **Create a new GitHub repository**
   - Go to github.com and create new repo named `link-hub` (or any name)
   - Make it **public** (required for free GitHub Pages)

2. **Upload your file**
   - Upload `index.html` to the root of the repo
   - If using local photo, create `assets` folder and upload `photo.jpg`

3. **Enable GitHub Pages**
   - Go to repo Settings → Pages
   - Source: Deploy from `main` branch, `/` (root) folder
   - Click Save

4. **Get your URL**
   - URL will be: `https://yourusername.github.io/link-hub/`
   - Takes 1-2 minutes to go live

5. **Test it**
   - Visit the URL on your phone to check mobile experience
   - Click all links to verify they work

**Custom Domain:**
- In GitHub Pages settings, add your custom domain (e.g., `yourname.com`)
- Add DNS records at your domain provider (GitHub shows instructions)
- SSL certificate automatically provided by GitHub

---

### Option 2: Cloudflare Pages (Free, Fastest Option)

**Time: ~3 minutes**

1. **Create Cloudflare account** (free)
   - Go to pages.cloudflare.com
   - Sign up with email

2. **Create new project**
   - Click "Create a project"
   - Choose "Direct Upload"
   - Drag and drop your `index.html` (and `assets` folder if used)

3. **Deploy**
   - Cloudflare generates URL: `https://your-project.pages.dev`
   - Live in ~30 seconds

**Custom Domain:**
- In project settings → Custom domains
- Add your domain (free SSL included)
- Update DNS automatically if domain is on Cloudflare

---

### Option 3: Netlify (Free Alternative)

1. **Create Netlify account** at netlify.com
2. **Drag and drop** your files to deploy
3. **URL**: `https://your-site-name.netlify.app`
4. **Custom domain**: Add in site settings

---

### Option 4: Traditional Web Hosting

If you already have cPanel or FTP hosting:
1. Upload `index.html` to public_html or www folder
2. Rename to `index.html` (most servers use this as default)
3. Upload `assets` folder if using local photo
4. Access via your domain

---

## 🔗 Custom Domain Setup

### Using a Custom Domain (e.g., yourname.com)

**If you own a domain:**
1. Go to your domain registrar (Namecheap, GoDaddy, etc.)
2. Add DNS records (exact records depend on host):

**For GitHub Pages:**
```
Type: CNAME
Name: www
Value: yourusername.github.io
```

**For Cloudflare Pages:**
```
Cloudflare automatically configures DNS if domain is on Cloudflare
```

3. In your hosting platform (GitHub/Cloudflare), add custom domain in settings
4. Wait 5-60 minutes for DNS propagation

**Free Domain Options:**
- `.me` domains often have $0.99 first-year promos
- Freenom offers free `.tk`, `.ml`, `.ga` domains (but often flagged as spam)

---

## 📊 Expected Performance Benchmarks

### Conversion Rates (Industry Averages)

- **Visitor → Link Click**: 15-30% (decent page)
- **Visitor → OF Click**: 5-15% (good page with trust signals)
- **OF Click → Subscriber**: 2-8% (depends on your OF page quality)
- **Overall Visitor → Subscriber**: 0.1-1.2%

**Example with 1,000 visitors:**
- ~100-150 click primary CTA
- ~20-120 click through to OF
- ~2-10 convert to subscribers

### What Affects Conversion:

✅ **Increases conversion:**
- Professional, attractive profile photo
- Real subscriber count (social proof)
- Clear, enticing bio
- Mobile-optimized (this template is)
- Fast load time (this template is)
- Limited-time offers ("Limited Spots")
- Testimonials or preview content

❌ **Decreases conversion:**
- Generic photo or no photo
- Fake/inflated numbers (users can tell)
- Too many links (choice paralysis)
- Slow loading
- Desktop-only design
- No clear value proposition

### Traffic Sources Performance:

| Source | CTR to Page | Page Conversion | Quality |
|--------|-------------|-----------------|---------|
| Reddit (profile bio) | 2-8% | 8-15% | High intent |
| TikTok (bio link) | 1-4% | 5-12% | Medium intent |
| Instagram (bio link) | 3-10% | 6-14% | Medium-high |
| Twitter (pinned) | 1-3% | 4-10% | Medium |
| Direct traffic | N/A | 12-20% | Highest (fans) |

---

## 🎯 Optimization Tips

### A/B Test These Elements:

1. **CTA Button Text:**
   - Current: "FREE TRIAL — Limited Spots"
   - Test: "See Exclusive Content"
   - Test: "Join VIP Access"
   - Test: "Unlock Premium Content"

2. **Social Proof:**
   - Current: "Join 2,400+ subscribers"
   - Test: "Join 2,400+ VIP members"
   - Test: "Trusted by 2,400+ fans"

3. **Feature Bullets:**
   - Focus on unique benefits
   - Use numbers ("100+ photos", "Reply in 24h")
   - Emphasize exclusivity

### Advanced Tracking:

Replace the simple console.log tracking with real analytics:

**Google Analytics (free):**
```html
<!-- Add before </head> -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

**Plausible (privacy-friendly, paid):**
```html
<script defer data-domain="yourdomain.com" src="https://plausible.io/js/script.js"></script>
```

---

## 🔒 Legal & Safety

- **18+ Notice**: Footer includes age restriction notice
- **Content Disclaimer**: States all content is of adults
- **Terms of Service**: Consider adding link to OF terms
- **Privacy**: This page doesn't collect data (unless you add analytics)

---

## 🆘 Troubleshooting

**Photo not showing:**
- Check file path is correct
- Try full URL instead of relative path
- Make sure photo file is uploaded to same directory

**Links not working:**
- Remove `#` placeholder from href
- Use full URLs: `https://onlyfans.com/profile`
- Test each link after editing

**Page looks broken on mobile:**
- This shouldn't happen (mobile-first design)
- Clear browser cache and reload
- Check if you accidentally deleted CSS code

**Page not deploying:**
- Verify file is named `index.html` (lowercase)
- Check repository/project is public
- Wait 2-5 minutes for deployment to complete

---

## 📈 Next Steps

1. **Deploy the page** using one of the methods above
2. **Add URL to all social bios** (Reddit, TikTok, Instagram, Twitter)
3. **Track performance** for 7 days
4. **Test variations** of CTA text and features
5. **Update social proof number** as you grow

---

## 💡 Pro Tips

- **Update subscriber count weekly** - keeps social proof fresh
- **Match link color scheme** to your brand/content style
- **Short URL** - Use bit.ly or your domain to make shareable
- **Screenshot your page** - Use as thumbnail in TikTok/Insta stories
- **Mobile-first mindset** - Test every change on phone before publishing

---

**Questions or need help?** This is a self-contained static page - edit the HTML directly, no coding skills needed beyond copy/paste your links.
