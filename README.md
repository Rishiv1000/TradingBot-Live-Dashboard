# 🚀 Trading Dashboard (Live & Paper)

Professional algorithmic trading dashboard built with **FastAPI** (Backend) and **React** (Frontend). This project is specialized for **Live Trading** and **Real-time Paper Trading**.

## 🌟 Key Features
- **Real-time Monitoring:** Track EMA and Green strategy dataframes live.
- **Process Manager:** Granular control over backend engines (Start/Stop/Kill via PID).
- **Kite Integration:** Daily automated session management with Zerodha.
- **Real Trading Toggle:** Safety-first switch between Paper and Live modes with confirmation alerts.
- **System Terminal:** Live logs for both Backend (FastAPI) and Frontend (Vite).
- **Notifications:** Browser desktop notifications for trade entries and exits.

## 🛠️ Quick Setup

### 1. Environment Variables
Copy the template and fill in your actual Zerodha API credentials:
```bash
cp configuration/.env.example configuration/.env
```
Ensure `REAL_TRADING_ENABLED=False` initially for safety.

### 2. Database
Ensure MySQL is running and your database (`trading_bot_live`) is created. You can use the **Setup DB** button in the dashboard sidebar to initialize tables.

### 3. Run the Dashboard
Simply run the startup script:
```bash
bash run_dashboard.sh
```
- **Backend:** http://127.0.0.1:8000
- **Frontend:** http://127.0.0.1:5173

## 📁 Project Structure
- `emaStrategy/`: EMA crossover logic and engines.
- `greenStrategy/`: Green candle strategy logic.
- `dashboard-ui/`: React frontend source.
- `others/logs/`: Centralized log storage.

---
**⚠️ Disclaimer:** Trading involves risk. Use the "Live Mode" toggle with caution.
