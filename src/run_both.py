import subprocess
import sys
import os


import threading

def run_main():
    subprocess.call([sys.executable, "main.py"])

def run_streamlit():
    subprocess.call(["streamlit", "run", "dashboard_streamlit.py"])

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    t1 = threading.Thread(target=run_main)
    t2 = threading.Thread(target=run_streamlit)
    t1.start()
    t2.start()
    t1.join()
    t2.join()