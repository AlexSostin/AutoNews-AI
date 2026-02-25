# How to Get Pexels API Key (Free)

## Step 1: Register on Pexels

1. Go to https://www.pexels.com/api/
2. Click **"Get Started"** button
3. Fill in registration form:
   - **Name**: Your name
   - **Email**: Your email
   - **Project Description**: "Automotive news website - AutoNews AI"
   - **Website** (optional): Your website URL

## Step 2: Get API Key

1. After registration, you'll be redirected to your dashboard
2. Your **API Key** will be displayed immediately
3. Copy the API key (looks like: `abcd1234efgh5678ijkl9012mnop3456`)

## Step 3: Add to .env File

1. Open `/backend/.env` file
2. Add this line:
   ```bash
   PEXELS_API_KEY=your_api_key_here
   ```
3. Replace `your_api_key_here` with your actual API key
4. Save the file

## Step 4: Restart Backend

```bash
cd /home/kille_wsl/Projects/FreshMotors_GoogleAntigravity/AutoNews-AI
docker-compose restart backend
```

## Step 5: Test Connection

```bash
docker exec autonews_backend python -c "
from ai_engine.modules.pexels_client import test_pexels_connection
test_pexels_connection()
"
```

You should see:
```
🔍 Testing Pexels API connection...
✅ Pexels API working!
📸 Found image: https://images.pexels.com/photos/...
```

## Step 6: Test with RSS Scan

```bash
# Dry run to see what images would be found
docker exec autonews_backend python manage.py scan_rss_feeds --feed-id 2 --dry-run
```

---

## API Limits (Free Forever)

- ✅ **200 requests/hour**
- ✅ **20,000 requests/month**
- ✅ **No credit card required**
- ✅ **No expiration**

## Troubleshooting

### "Pexels API key not configured"
- Make sure you added `PEXELS_API_KEY` to `.env`
- Restart backend container

### "Pexels API test failed"
- Check your API key is correct
- Make sure you have internet connection
- Check Pexels API status: https://www.pexels.com/api/

### "Rate limit exceeded"
- Wait 1 hour for limit to reset
- System will automatically fallback to no image

---

## What Happens Now?

When you scan RSS feeds:
1. ✅ System extracts images from RSS feed (if available)
2. ✅ If no images found → **Pexels searches automatically**
3. ✅ Smart keywords extracted from title + brand
4. ✅ Best matching image downloaded
5. ✅ Image added to pending article

**Example:**
- RSS article: "Ford F-150 Lightning Electric Truck Review"
- No images in RSS feed
- Pexels search: "Ford F-150 Lightning car"
- Result: High-quality Ford F-150 image automatically added! 🎉
