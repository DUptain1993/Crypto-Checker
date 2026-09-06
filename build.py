#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Application Builder — Builds the complete application package
"""
import os
import sys
import subprocess
import shutil
import base64
from pathlib import Path

HOME = os.path.expanduser("~")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "dist")

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("="*60)
print("Application Builder v3.1")
print("="*60)


def build_application():
    """Build the complete application."""
    print("Building application...")
    
    main_py = os.path.join(BASE_DIR, "main.py")
    if not os.path.exists(main_py):
        print("main.py not found!")
        return False
    
    # Check if we're on Linux with Wine
    if sys.platform.startswith("linux"):
        try:
            result = subprocess.run(['which', 'wine'], capture_output=True, text=True)
            has_wine = result.returncode == 0
        except:
            has_wine = False
        
        if has_wine:
            # Find Wine Python
            wine_prefix = os.path.expanduser("~/.wine/drive_c")
            wine_python = None
            for path in [
                os.path.join(wine_prefix, "Program Files", "Python311", "python.exe"),
                os.path.join(wine_prefix, "Program Files", "Python310", "python.exe"),
                os.path.join(wine_prefix, "Python311", "python.exe"),
            ]:
                if os.path.exists(path):
                    wine_python = path
                    break
            
            if wine_python:
                print(f"Using Wine Python: {wine_python}")
                cmd = [
                    'wine', wine_python, '-m', 'PyInstaller',
                    '--onefile',
                    '--windowed',
                    '--noconsole',
                    '--name', 'crypto_checker',
                    '--distpath', OUTPUT_DIR,
                    '--workpath', os.path.join(BASE_DIR, 'build'),
                    '--specpath', os.path.join(BASE_DIR, 'spec'),
                    '--add-data', f"actions;actions",
                    '--add-data', f"scanner;scanner",
                    '--add-data', f"config.json;.",
                    '--hidden-import', 'cryptography',
                    '--hidden-import', 'psutil',
                    '--hidden-import', 'ctypes',
                    '--hidden-import', 'win32api',
                    '--hidden-import', 'win32con',
                    '--hidden-import', 'win32process',
                    '--exclude-module', 'tkinter',
                    '--exclude-module', 'test',
                    '--strip',
                    main_py
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    exe_path = os.path.join(OUTPUT_DIR, "crypto_checker.exe")
                    if os.path.exists(exe_path):
                        size = os.path.getsize(exe_path) / (1024 * 1024)
                        print(f"✅ Built: {exe_path} ({size:.2f} MB)")
                        return True
                    return False
    
    # Native build
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',
        '--windowed',
        '--noconsole',
        '--name', 'crypto_checker',
        '--distpath', OUTPUT_DIR,
        '--workpath', os.path.join(BASE_DIR, 'build'),
        '--specpath', os.path.join(BASE_DIR, 'spec'),
        '--add-data', f"actions{os.pathsep}actions",
        '--add-data', f"scanner{os.pathsep}scanner",
        '--add-data', f"config.json{os.pathsep}.",
        '--hidden-import', 'cryptography',
        '--hidden-import', 'psutil',
        '--hidden-import', 'ctypes',
        '--exclude-module', 'tkinter',
        '--exclude-module', 'test',
        '--strip',
        main_py
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode == 0:
        exe_path = os.path.join(OUTPUT_DIR, "crypto_checker.exe")
        if os.path.exists(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"✅ Built: {exe_path} ({size:.2f} MB)")
            return True
    
    print("❌ Build failed")
    return False


def main():
    print("Application Builder")
    print("="*60)
    
    # Ensure directories exist
    os.makedirs(os.path.join(BASE_DIR, "actions"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "scanner"), exist_ok=True)
    
    success = build_application()
    
    if success:
        print("\n" + "="*60)
        print("Build complete!")
        print(f"Output: {OUTPUT_DIR}/crypto_checker.exe")
        print("="*60)
    else:
        print("\nBuild failed.")


if __name__ == "__main__":
    main()
