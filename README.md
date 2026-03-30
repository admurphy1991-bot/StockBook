# Sansom Stock Book

AI-powered voice stock entry app for construction sites.

## How It Works

1. Worker taps the mic and says e.g. *"Sika Boom, job 2847, 3 cans, taken by Dave"*
2. Claude AI matches the product, extracts job/qty/name
3. If ambiguous (e.g. "Sikadur UA" could be 4L or 8L) the worker taps the right one
4. Worker reviews and confirms — entry saves to PostgreSQL
5. Admin exports to CSV in the stock book import format

## Output Format

`Item Code | Date | Job | Supplier | Description | Cost Quantity | Unit | Comments`

---

## Deploy to Railway

### Step 1 — Create a GitHub repo and push this code

```bash
cd stockbook
git init
git add .
git commit -m "Initial commit"
# Create a new repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/sansom-stockbook.git
git push -u origin main
```

### Step 2 — Create Railway project

1. Go to [railway.app](https://railway.app) and click **New Project**
2. Select **Deploy from GitHub repo** → choose your new repo
3. Railway will detect the Dockerfile and start building

### Step 3 — Add PostgreSQL

1. In your Railway project, click **+ New** → **Database** → **PostgreSQL**
2. Railway will auto-inject the `DATABASE_URL` environment variable

### Step 4 — Add environment variables

In Railway → your web service → **Variables**, add:

| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (from console.anthropic.com) |
| `DATABASE_URL` | Auto-injected by Railway PostgreSQL plugin |

### Step 5 — Deploy

Railway auto-deploys on every push to `main`. Your app will be live at the Railway-provided URL (e.g. `sansom-stockbook.up.railway.app`).

---

## Local Development

### Backend
```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL="postgresql://user:pass@localhost/stockbook"
export ANTHROPIC_API_KEY="sk-ant-..."
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173 with API proxy to :8000
```

---

## Updating the Product List

The product catalogue is embedded in `backend/main.py` in the `PRODUCTS` list.
To add or update products, edit that list and redeploy (just push to GitHub).

---

## Notes

- Voice uses the browser's built-in Web Speech API — works best in **Chrome** on Android or desktop
- Safari on iOS has limited support; recommend Chrome
- The `en-NZ` locale is set for New Zealand English recognition
