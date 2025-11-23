# SIR-project Group-6: Oli-4

This project runs a NAO robot demo with **Gemini LLM**, **gesture classification**, and **speech output**. The system has three main components:

1. **Redis** – message broker
2. **GestureAPI** – Gesture classification using a lightweight version of Bert
3. **main.py** – NAO interaction script

---

## 1. Conda Setup

This setup uses **`env_sic`** and the provided batch file.

1. Open terminal at the project root (`sir-project-group-6/`)
2. Run:

```bat
start_all.bat
```

**What it does:**

* Starts Redis (`redis-server.exe redis.conf`) in a new terminal
* Starts GestureAPI in `oli-4/config` (conda env activated)
* Waits ~25s to ensure services are up
* Starts `main.py` in `oli-4` (conda env activated)

---

## 2. Manual Environment Setup (alternative)

If you prefer not to use the batch file or want to use a different type of env:

### 2.1. Create environment

**Conda:**

```bash
conda create -n env_sic python=3.10
conda activate env_sic
pip install -r requirements.txt
```

**Or venv:**

```bash
python -m venv env_sic
env_sic\Scripts\activate
pip install -r requirements.txt
```

---

### 2.2. Start Redis

From `conf/redis`:

```bash
redis-server.exe redis.conf
```

---

### 2.3. Start GestureAPI

```bash
cd oli-4\config
python run_GestureAPI.py
```

---

### 2.4. Start main.py

```bash
cd ..
python main.py
```

> Ensure Redis and GestureAPI are running first.

---

## Notes

* **Ports:** GestureAPI default: `8001`, Redis default: `6379`
* **Batch file** simplifies the process and ensures the correct environment is activated
* Make sure your NAO robot is network-accessible for `main.py`
* Make sure you are connected to the same network as the Nao and not using a VPN
* Sometimes firewall can interfere with the connection with the Nao.

---
