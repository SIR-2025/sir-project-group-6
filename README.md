
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

> After this step, follow the instructions in step 2.3 for placing your dialogflow and API keys in the right location. Also edit the values labeled with TODO in oli-4/main.py to the values from your dialogflow setup.

> Now the environment is ready to run.

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

> Ensure Redis and GestureAPI are running first.

## 2.3. API Credentials Setup (Required)

After installing the virtual environment and initializing the GestureAPI model,
you must provide credentials for **Google Dialogflow** and **Gemini LLM**.

These credentials are **not included** in the repository.

### 2.3.1. Google Dialogflow Credentials (Speech-to-Text)

1. Obtain a **Google Cloud service account JSON key** with access to Dialogflow.
2. Rename the file to:

```

google-key.json

```

3. Place the file in the following directory:

```

oli-4/config/google-key.json

```

> This file is used by `main.py` to authenticate with Google Dialogflow for
> streaming speech-to-text.

### 2.3.2. Gemini API Key (Language Model)

1. Create a **Gemini API key** via Google AI Studio.
2. Create a text file named:

```

api_key.txt

```

3. Paste **only the API key** into the file (no quotes, no extra spaces).
4. Place the file in the following directory:

```

oli-4/config/api_key.txt

```

> This key is used by `main.py` to access the Gemini large language model.

### 2.4. Start main.py

From the project root:

```bash
python main.py
```

---

## 3. Notes

* **Ports:** GestureAPI default: `8001`, Redis default: `6379`
* The **batch file** ensures correct environment activation and execution order
* Your NAO robot must be **network-accessible** from your PC
* Ensure the PC and NAO are on the **same network** (VPNs may block connections)
* Firewalls can sometimes interfere with NAO communication

---

## 4. NAO Interaction Script (`main.py`) – Functionality Overview

The `main.py` script is the core controller of the Oli-4 demo.
It coordinates **speech input, language generation, gesture selection, and physical robot behavior** to create a live improvisational interaction with the NAO robot.

### 4.1. Scene-Based Interaction Structure

The demo is organized into **multiple scenes**, each defining a different interaction mode:

* **Conversational scenes**

  * The NAO listens to the user
  * Generates a response using the Gemini LLM
  * Classifies the response into a gesture category
  * Executes speech and gestures concurrently
* **Break scenes**

  * No language generation
  * NAO performs face tracking and movement (walking behavior)
  * System waits for a spoken stop-word to continue

Scene prompts, stop-words, and behavior are defined in external configuration files.

### 4.2. Speech Input and Output

**Speech-to-Text (STT)**

* User speech is captured via a local microphone
* Google Dialogflow streaming STT is used for real-time transcription
* Interim and final recognition results are handled
* Keyboard input is used as a fallback if speech recognition fails

**Text-to-Speech (TTS)**

* Generated responses are spoken using NAO’s built-in TTS system
* If TTS fails, the text is printed to the console for debugging

### 4.3. Language Generation (Gemini LLM)

* The script maintains a **conversation history** per scene
* A **scene-specific system prompt** defines the role and behavior of the NAO
* User input is appended to the history and sent to Gemini
* The model response is:

  * Spoken by the robot
  * Used as input for gesture classification
  * Logged for later analysis

### 4.4. Gesture Classification and Execution

* LLM responses are sent to the **GestureAPI**
* A zero-shot classifier assigns the response to a gesture category
* A concrete NAO animation is selected randomly within that category
* Speech and gesture execution run **in parallel** using threading
* Different gesture sets are used depending on whether the robot is:

  * Standing
  * Sitting

### 4.5. LED-Based System State Feedback

The NAO’s LEDs are used to visualize internal system states in real time:

| LED Color | Meaning                        |
| --------- | ------------------------------ |
| Blue      | Listening for user input       |
| Red       | Generating LLM response        |
| Yellow    | Classifying gesture            |
| Green     | Speaking and executing gesture |

This provides immediate feedback during live demos and debugging.

### 4.6. Face Tracking and Movement

* During conversational scenes, the NAO tracks the user’s face using head movement
* During break scenes, tracking switches to a **movement mode**, allowing the robot to walk and follow the user
* Tracking is safely stopped and reset between scenes and on shutdown

### 4.7. Data Logging

Each interaction turn is logged to a JSONL file, including:

* Timestamp
* Scene identifier
* User utterance
* LLM response
* LLM response time
* Gesture classification time
* Selected gesture category and animation

This enables **offline analysis of system performance and interaction quality**.

### 4.8. Robustness and Safety Features

* Graceful handling of:

  * Speech recognition failures
  * TTS failures
  * Keyboard interrupts
* Automatic cleanup on shutdown:

  * Stops face tracking
  * Resets posture
  * Restores autonomous mode
  * Turns LEDs back to a neutral state
