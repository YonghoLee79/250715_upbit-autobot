import subprocess
import sys
import os

def run_main():
    subprocess.Popen([sys.executable, "main.py"])

def run_streamlit():
    subprocess.call(["streamlit", "run", "dashboard_streamlit.py"])

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    run_main()
    run_streamlit()