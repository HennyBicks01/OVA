import PyInstaller.__main__
import os
import json
import sys
from multiprocessing import cpu_count

def create_default_config():
    return {
        'voice_type': 'Azure Voice',
        'voice_name': 'en-US-AnaNeural', 
        'sleep_timer': 30,
        'personality_preset': 'ova',
        'display_mode': 'bubble',
        'enable_random_actions': True,
        'min_action_interval': 5,
        'max_action_interval': 10,
        'enabled_actions': {
            'take_flight': True,
            'look_around': True,
            'dance': True,
            'screech': True
        }
    }

def create_spec_content(script_path, current_dir, datas, icon_path, console=False):
    exe_name = 'OVA-debug' if console else 'OVA'
    return f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

assets_dir = os.path.join(r'{current_dir}', 'assets')
presets_dir = os.path.join(r'{current_dir}', 'scripts', 'presets')

# Collect all asset files
asset_datas = []
for root, dirs, files in os.walk(assets_dir):
    for file in files:
        src = os.path.join(root, file)
        dst = os.path.relpath(root, r'{current_dir}')
        asset_datas.append((src, dst))

# Collect all preset files
preset_datas = []
for root, dirs, files in os.walk(presets_dir):
    for file in files:
        src = os.path.join(root, file)
        dst = 'presets'  # All presets go in the presets directory
        preset_datas.append((src, dst))

a = Analysis(
    [r'{script_path}'],
    pathex=[r'{current_dir}'],
    binaries=[],
    datas=[*asset_datas, *preset_datas, (r'{current_dir}/config.json', '.')],
    hiddenimports=[
        'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui',
        'edge_tts', 'speech_recognition', 'ollama', 'PyQt5.sip'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['matplotlib', 'notebook', 'PIL', 'tk', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False
)

# Remove unnecessary files
a.binaries = [x for x in a.binaries if not x[0].startswith('msvcp')]
a.binaries = [x for x in a.binaries if not x[0].startswith('opengl')]
a.binaries = [x for x in a.binaries if not x[0].startswith('qt5web')]

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{icon_path}'
)
'''

def verify_required_files():
    """Verify all required asset directories and files exist"""
    current_dir = os.path.abspath(os.path.dirname(__file__))
    required_dirs = ['assets/idle', 'assets/sounds', 'scripts']
    
    for dir_path in required_dirs:
        full_path = os.path.join(current_dir, dir_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Missing required directory: {dir_path}")

def collect_all_files(directory):
    """Recursively collect all files in directory with proper PyInstaller paths"""
    files = []
    base_dir = os.path.dirname(__file__)
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if not any(filename.endswith(ext) for ext in ['.pyc', '.pyo', '.pyd']):
                source = os.path.join(root, filename)
                # Calculate destination path relative to the base directory
                dest = os.path.relpath(root, base_dir)
                # Create tuple in PyInstaller format
                files.append((source, dest))
    return files

def build_exe():
    # Verify required files
    verify_required_files()
    
    # Setup paths
    current_dir = os.path.abspath(os.path.dirname(__file__))
    script_path = os.path.join(current_dir, "scripts", "desktop_pet.py")
    icon_path = os.path.join(current_dir, "assets", "idle", "1.png")
    
    # Create config
    config_path = os.path.join(current_dir, "config.json")
    with open(config_path, 'w') as f:
        json.dump(create_default_config(), f, indent=4)

    # Build only debug version during development, both for production
    versions = [True] if '--debug-only' in sys.argv else [False, True]
    
    for console in versions:
        spec_content = create_spec_content(script_path, current_dir, [], icon_path, console)
        spec_name = 'OVA-debug.spec' if console else 'OVA.spec'
        spec_path = os.path.join(current_dir, spec_name)
        
        with open(spec_path, 'w') as f:
            f.write(spec_content)

        PyInstaller.__main__.run([
            spec_path,
            '--clean',
            '--log-level=DEBUG'
        ])

        os.remove(spec_path)

    # Setup dist directory
    dist_dir = os.path.join(current_dir, 'dist')
    history_dir = os.path.join(dist_dir, 'history')
    os.makedirs(history_dir, exist_ok=True)
    
    os.remove(config_path)
    
    print("\nBuild complete!")
    if '--debug-only' in sys.argv:
        print("Debug version created in dist folder: OVA-debug.exe")
    else:
        print("Two versions have been created in the dist folder:")
        print("1. OVA.exe - Regular version without console")
        print("2. OVA-debug.exe - Debug version with console window")

if __name__ == '__main__':
    build_exe()