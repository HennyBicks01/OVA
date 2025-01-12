import PyInstaller.__main__
import os
import json
import sys
import shutil
from multiprocessing import cpu_count

def create_default_config():
    """Create default configuration"""
    return {
        'personality_preset': 'ova',
        'voice_type': 'Azure Voice',
        'voice_name': 'en-US-AriaNeural',
        'sleep_timer': 60,
        'display_mode': 'bubble',
        'save_conversation_history': True,
        'max_conversation_pairs': 5,
        'enable_random_actions': True,
        'min_action_interval': 5,
        'max_action_interval': 10,
        'enabled_actions': {
            'take_flight': False,
            'look_around': True,
            'dance': True,
            'screech': True
        },
        'ai_provider': 'google',
        'ai_settings': {
            'google_api_key': 'YOUR_API_KEY',
            'google_model': 'gemini-1.5-flash-8b',
            'ollama_model': 'llama3.2:1b'
        }
    }

def create_spec_content(script_path, current_dir, icon_path, console=False):
    """Create PyInstaller spec file content"""
    exe_name = 'OVA-debug' if console else 'OVA'
    
    # Define default config outside of f-string to avoid formatting issues
    default_config = {
        'voice_type': 'Azure Voice',
        'voice_name': 'en-US-AnaNeural',
        'sleep_timer': 30,
        'personality_preset': 'ova',
        'display_mode': 'bubble'
    }
    
    return f'''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

assets_dir = os.path.join(r'{current_dir}', 'assets')
presets_dir = os.path.join(r'{current_dir}', 'assets', 'presets')
history_dir = os.path.join(r'{current_dir}', 'history')
config_file = os.path.join(r'{current_dir}', 'config.json')

# Collect all asset files
asset_datas = []
for root, dirs, files in os.walk(assets_dir):
    for file in files:
        src = os.path.join(root, file)
        dst = os.path.relpath(root, r'{current_dir}')
        asset_datas.append((src, dst))

# Create empty history directory if it doesn't exist
if not os.path.exists(history_dir):
    os.makedirs(history_dir)

# Create default config if it doesn't exist
if not os.path.exists(config_file):
    with open(config_file, 'w') as f:
        json.dump({default_config}, f, indent=4)

a = Analysis(
    [r'{script_path}'],
    pathex=[r'{current_dir}'],
    binaries=[],
    datas=asset_datas,
    hiddenimports=[
        'PyQt5.QtWidgets', 'PyQt5.QtCore', 'PyQt5.QtGui',
        'edge_tts', 'speech_recognition', 'ollama', 'PyQt5.sip',
        'pygame'
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
    required_dirs = ['assets/idle', 'assets/sounds', 'scripts', 'assets/presets']
    
    for dir_path in required_dirs:
        full_path = os.path.join(current_dir, dir_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Missing required directory: {dir_path}")

def setup_config():
    """Set up configuration file"""
    current_dir = os.path.abspath(os.path.dirname(__file__))
    config_path = os.path.join(current_dir, 'config.json')
    
    # Create default config
    config = create_default_config()
    
    # Save config file
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"Created default config at {config_path}")

def build():
    """Build the executable"""
    try:
        # Get current directory
        current_dir = os.path.abspath(os.path.dirname(__file__))
        
        # Verify required files
        verify_required_files()
        
        # Set up paths
        script_path = os.path.join(current_dir, 'scripts', 'desktop_pet.py')
        icon_path = os.path.join(current_dir, 'assets', 'tray_icon.ico')
        
        # Set up config
        setup_config()
        
        # Determine if building debug version only
        debug_only = '--debug-only' in sys.argv
        versions = [True] if debug_only else [False, True]
        
        for console in versions:
            # Create spec file
            spec_name = 'OVA-debug.spec' if console else 'OVA.spec'
            spec_path = os.path.join(current_dir, spec_name)
            
            spec_content = create_spec_content(script_path, current_dir, icon_path, console)
            with open(spec_path, 'w') as f:
                f.write(spec_content)
            
            # Build with PyInstaller
            PyInstaller.__main__.run([
                spec_path,
                '--clean',
                '--noconfirm',
            ])
            
            # Clean up spec file
            os.remove(spec_path)
        
        # Create history directory in dist
        history_dir = os.path.join(current_dir, 'dist', 'history')
        os.makedirs(history_dir, exist_ok=True)
        
        if debug_only:
            print("\nBuild complete! Debug version created in dist folder: OVA-debug.exe")
        else:
            print("\nBuild complete! Two versions have been created in the dist folder:")
            print("1. OVA.exe - Regular version without console")
            print("2. OVA-debug.exe - Debug version with console window")
        
    except Exception as e:
        print(f"Build failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build()