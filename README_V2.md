# MaxFlash v2.0 - Crypto Trading System

**Version**: 2.0 (Fixed - No Look-Ahead Bias)
**Date**: 2025-12-17
**Status**: ✅ Production Ready

---

## 🚨 IMPORTANT UPDATE

**Version 2.0 fixes critical look-ahead bias** that made v1.0 produce unrealistic results.

### What Changed:

| Metric | v1.0 (WRONG) | v2.0 (FIXED) |
|--------|--------------|--------------|
| Win Rate | 100% ❌ | 48-52% ✅ |
| Profit Factor | 999 ❌ | 1.3-1.8 ✅ |
| Methodology | Look-ahead bias | Realistic labels |

**If you see 100% win rate, you're using the old broken code!**

---

## ⚡ Quick Start

### 1. Train Model (5 min)

```bash
python scripts/train_lightgbm_fixed.py --quick
```

### 2. Verify with Backtest (10 min)

```bash
python scripts/run_walk_forward_backtest.py --coins 5
```

**Expected**: Win Rate ~50%, Profit Factor ~1.5

### 3. Deploy to Server (10 min)

#### Windows:
```powershell
.\DEPLOY_COMMANDS.ps1
```

#### Linux/Mac:
```bash
bash DEPLOY_COMMANDS.sh
```

**Done!** Dashboard: http://192.168.0.203:8050

---

## 📚 Complete Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get started in 30 minutes
- **[README_FIXES.md](README_FIXES.md)** - What was fixed and why
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment guide
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Step-by-step checklist
- **[CHANGES_SUMMARY.md](CHANGES_SUMMARY.md)** - Detailed changelog

---

## 🎯 Key Features

✅ **No Look-Ahead Bias** - Labels from current indicators only
✅ **Walk-Forward Validation** - Proper train/test methodology
✅ **Realistic Metrics** - 45-55% win rate (achievable)
✅ **Automated Deployment** - One command to production
✅ **Complete Docs** - 5 comprehensive guides

---

**Ready to deploy?** → [QUICK_START.md](QUICK_START.md)

**Want details?** → [README_FIXES.md](README_FIXES.md)

**Deployment help?** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

*MaxFlash v2.0 - Trading with Realistic Expectations* 🚀
