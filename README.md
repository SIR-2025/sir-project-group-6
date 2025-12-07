
# SIR-project Group-6: Oli-4

This project runs a **NAO robot demo** with:

* **Gemini LLM** – for conversational responses
* **Gesture classification** – using a lightweight zero-shot model
* **Speech output** – via NAO’s TTS system

The system consists of three main components:

1. **Redis** – message broker
2. **GestureAPI** – gesture classification
3. **main.py** – NAO interaction script

---

## 1. Quick Start (Recommended)

We provide a **batch file** to automatically start everything in the correct order using a local Python venv.

### Step 1: Install dependencies and create venv

After cloning the repository, run:

```bash
python install.py
```

**What this does:**

* Creates a local `venv/` in the project root
* Installs all required Python packages
* Downloads or initializes the gesture model for `GestureAPI`

> After this step, the environment is ready to run.

---

### Step 2: Start everything

From the project root (`sir-project-group-6/`), run:

```bat
start_all.bat
```

**This will:**

1. Start Redis (`redis-server.exe redis.conf`) in a new terminal
2. Start `GestureAPI` from the project root (venv activated automatically)
3. Wait ~25s for services to initialize
4. Start `main.py` (NAO demo) in the venv

---

## 2. Manual Setup (Alternative)

If you want to set up the environment manually instead of using `install.py`:

### 2.1. Create a Python venv

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2.2. Initialize GestureAPI model

From the project root:

```bash
python run_GestureAPI.py
```

> This will download or load the gesture model in `local_model/`.

### 2.3. Start Redis

From `conf/redis`:

```bash
redis-server.exe redis.conf
```

### 2.4. Start main.py

From the project root:

```bash
python main.py
```

> Ensure Redis and GestureAPI are running first.

---

## 3. Notes

* **Ports:** GestureAPI default: `8001`, Redis default: `6379`
* The **batch file** ensures correct environment activation and execution order
* Your NAO robot must be **network-accessible** from your PC
* Ensure the PC and NAO are on the **same network** (VPNs may block connections)
* Firewalls can sometimes interfere with NAO communication

---