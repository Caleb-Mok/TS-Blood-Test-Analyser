# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import copy_metadata, collect_all
import os
import importlib.util

block_cipher = None

# --- HELPER: Find package path manually if needed ---
def get_rapidocr_datas():
    """Explicitly find the rapidocr folder to ensure yaml files are copied."""
    datas = []
    try:
        # Try to find where 'rapidocr' is installed
        spec = importlib.util.find_spec('rapidocr')
        if spec and spec.origin:
            pkg_path = os.path.dirname(spec.origin)
            # Force copy the entire folder to 'rapidocr/' in the exe
            datas.append((pkg_path, 'rapidocr'))
            print(f"Spec File: Found rapidocr at {pkg_path}")
    except Exception as e:
        print(f"Spec File: Could not resolve rapidocr manually: {e}")
    return datas

# --- 1. COLLECT EVERYTHING ---
tmp_ret = []

# Core Docling & PDF Libraries
tmp_ret.append(collect_all('docling'))
tmp_ret.append(collect_all('docling_parse'))
tmp_ret.append(collect_all('pypdfium2')) 
tmp_ret.append(collect_all('filetype'))

# OCR Libraries (The Fix)
# We collect BOTH variations to be safe
tmp_ret.append(collect_all('rapidocr_onnxruntime'))
tmp_ret.append(collect_all('rapidocr')) 
tmp_ret.append(collect_all('onnxruntime'))

# Initialize our lists
my_datas = [
    ('data', 'data'),
    ('.env', '.') 
]
my_binaries = []
my_hiddenimports = []

# Merge results from collect_all
for datas, binaries, hiddenimports in tmp_ret:
    my_datas += datas
    my_binaries += binaries
    my_hiddenimports += hiddenimports

# Add the manual fallback for rapidocr datas
my_datas += get_rapidocr_datas()

# --- 2. ADD METADATA ---
metadata_packages = [
    'transformers',
    'tokenizers',
    'huggingface-hub',
    'safetensors',
    'docling-core',
    'docling-ibm-models',
    'rapidocr_onnxruntime',
    'rapidocr' 
]

for pkg in metadata_packages:
    try:
        my_datas += copy_metadata(pkg)
    except Exception:
        pass

# --- 3. ANALYSIS ---
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=my_binaries,
    datas=my_datas,
    hiddenimports=my_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude unnecessary stuff
    excludes=['tkinter', 'notebook', 'ipython', 'jupyter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BloodTestAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon = "blooddrop.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)