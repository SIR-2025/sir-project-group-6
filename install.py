import os
import subprocess
import sys
import venv
import time
import signal

VENV_DIR = "venv"

GESTURE_API_PATH = os.path.join("oli-4", "config", "run_GestureAPI.py")

def create_venv():
    if not os.path.isdir(VENV_DIR):
        print("Creating virtual environment...")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    else:
        print("Virtual environment already exists.")

def install_requirements():
    print("Installing dependencies...")
    python_executable = (
        os.path.join(VENV_DIR, "Scripts", "python.exe")
        if os.name == "nt"
        else os.path.join(VENV_DIR, "bin", "python")
    )
    subprocess.check_call([python_executable, "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([python_executable, "-m", "pip", "install", "-r", "requirements.txt"])


def run_gesture_api_initialize_model():
    """
    Runs the GestureAPI for a short time so it loads the model.
    Then terminates it.
    """
    print("\nInitializing GestureAPI model (this may take a minute)...")

    python_executable = (
        os.path.join(VENV_DIR, "Scripts", "python.exe")
        if os.name == "nt"
        else os.path.join(VENV_DIR, "bin", "python")
    )

    if not os.path.isfile(GESTURE_API_PATH):
        print(f"[Warning] GestureAPI file not found at: {GESTURE_API_PATH}")
        return

    # Start GestureAPI
    process = subprocess.Popen([python_executable, GESTURE_API_PATH])

    # Give it time to download/init the model
    time.sleep(90)

    print("GestureAPI model should be initialized. Stopping process...")

    # Clean shutdown depending on OS
    try:
        if os.name == "nt":
            subprocess.call(["taskkill", "/F", "/T", "/PID", str(process.pid)])
        else:
            os.kill(process.pid, signal.SIGTERM)
    except Exception as e:
        print(f"Could not terminate GestureAPI cleanly: {e}")

    print("GestureAPI initialization complete.\n")


def main():
    create_venv()
    install_requirements()
    run_gesture_api_initialize_model()

    print("Setup complete! You can now run the system using run_demo.bat.")
    print("To activate the venv manually:")
    if os.name == "nt":
        print("  venv\\Scripts\\activate")
    else:
        print("  source venv/bin/activate")


if __name__ == "__main__":
    main()
