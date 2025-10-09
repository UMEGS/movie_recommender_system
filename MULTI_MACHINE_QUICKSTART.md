# 🚀 Multi-Machine Embedding Generation - Quick Start

## TL;DR

Run `generate_embeddings.py` on **multiple machines simultaneously** to speed up embedding generation. The script **already supports this** - just run it on each machine!

## ✅ It Already Works!

The script automatically:
- ✅ Checks database before generating each embedding
- ✅ Skips embeddings that already exist
- ✅ Coordinates through the central database
- ✅ No conflicts between machines

## 🎯 Quick Setup

### On Each Additional Machine:

#### 1. Clone & Install
```bash
git clone <your-repo>
cd movie_recommender_system
pip install -r requirements.txt
```

#### 2. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start and pull model
ollama serve &
ollama pull nomic-embed-text
```

#### 3. Configure Database
Create `.env` file:
```bash
# Replace with your actual database IP
DATABASE_URL=postgresql://postgres:password@192.168.1.100:5432/movie_recommender
```

#### 4. Run!
```bash
python scripts/generate_embeddings.py --workers 10
```

## 📊 Performance

| Machines | Speed | Time (28K movies) |
|----------|-------|-------------------|
| 1 | 2-3 emb/s | ~3-4 hours |
| 2 | 4-6 emb/s | ~1.5-2 hours |
| 3 | 6-9 emb/s | ~1 hour |
| 5 | 10-15 emb/s | ~30-45 min |

## 🎮 Example: 3 Machines

**Machine 1** (Your current machine):
```bash
python scripts/generate_embeddings.py --workers 10
```

**Machine 2** (MacBook):
```bash
# After setup above
python scripts/generate_embeddings.py --workers 8
```

**Machine 3** (Linux):
```bash
# After setup above
python scripts/generate_embeddings.py --workers 10
```

**Result:** 3x faster! ⚡

## 📈 Monitor Combined Progress

On any machine:
```bash
python scripts/monitor_embeddings.py
```

Shows real-time progress:
```
████████████████░░░░░░░░ 65.5% | 18,405/28,099 | 8.5 emb/s | ETA: 18.9m | Elapsed: 30.2m
```

## 🔧 Database Setup (One-Time)

### Allow Remote Connections

On your **PostgreSQL server machine**, edit `/etc/postgresql/*/main/postgresql.conf`:
```conf
listen_addresses = '*'
```

Edit `/etc/postgresql/*/main/pg_hba.conf`:
```conf
# Add this line (adjust IP range for your network)
host    all    all    192.168.1.0/24    md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

Open firewall:
```bash
sudo ufw allow 5432/tcp
```

### Test Connection

From another machine:
```bash
psql -h 192.168.1.100 -U postgres -d movie_recommender
```

## 💡 What You'll See

Each machine shows its own progress:

**Machine 1:**
```
Generating embeddings: 40%|████| 11240/28099 [30:00<45:00, ✓=3500, ⊘=7700, ✗=40]
```

**Machine 2:**
```
Generating embeddings: 40%|████| 11240/28099 [30:00<45:00, ✓=3800, ⊘=7400, ✗=40]
```

**Machine 3:**
```
Generating embeddings: 40%|████| 11240/28099 [30:00<45:00, ✓=4000, ⊘=7200, ✗=40]
```

Notice:
- **Same total progress** (40%) - they're coordinated!
- **Different ✓ counts** - each machine doing different movies
- **High ⊘ counts** - skipping what others already did

## 🚨 Troubleshooting

### Can't Connect to Database

**Check database IP:**
```bash
# On database machine
hostname -I
```

**Test connection:**
```bash
psql -h YOUR_DB_IP -U postgres -d movie_recommender
```

**Check firewall:**
```bash
# On database machine
sudo ufw status
sudo ufw allow 5432/tcp
```

### Ollama Not Working

**Check Ollama:**
```bash
ollama list
curl http://localhost:11434/api/tags
```

**Restart Ollama:**
```bash
pkill ollama
ollama serve &
```

## 📝 Optimal Settings

### MacBook M1/M2
```bash
python scripts/generate_embeddings.py --workers 8 --batch-size 100
```

### MacBook Intel
```bash
python scripts/generate_embeddings.py --workers 5 --batch-size 50
```

### Linux with GPU
```bash
python scripts/generate_embeddings.py --workers 15 --batch-size 200
```

### Linux CPU Only
```bash
python scripts/generate_embeddings.py --workers 8 --batch-size 100
```

## ✅ Checklist

Before running on each machine:

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Ollama installed and running
- [ ] `nomic-embed-text` model pulled
- [ ] `.env` file configured with database URL
- [ ] Can connect to database (`python scripts/test_db_connection.py`)
- [ ] Ollama working (`python scripts/test_ollama_connection.py`)

## 🎯 Ready to Go!

1. **Setup additional machines** (steps above)
2. **Run on all machines:**
   ```bash
   python scripts/generate_embeddings.py --workers 10
   ```
3. **Monitor progress:**
   ```bash
   python scripts/monitor_embeddings.py
   ```

That's it! The machines will automatically coordinate through the database. 🚀

## 📚 Full Documentation

See `docs/MULTI_MACHINE_SETUP.md` for complete details.

## 💬 Tips

- **Start all machines at once** for best work distribution
- **You can stop/start any machine anytime** - progress is saved
- **Add more machines anytime** - even while others are running
- **Different speeds are OK** - faster machines will do more work
- **High skip rate is normal** - means coordination is working!

---

**Current Status:** You have 46,259/70,645 embeddings (65.5%) already done! 🎉

Run on 2-3 more machines to finish the remaining 24,386 embeddings much faster!

