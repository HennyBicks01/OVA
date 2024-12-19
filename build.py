import PyInstaller.__main__
import os

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    'scripts/desktop_pet.py',
    '--onefile',
    '--windowed',
    '--name=OwlPet',
    f'--add-data={os.path.join(current_dir, "assets")};assets',
    '--icon=' + os.path.join(current_dir, 'assets', 'idle', '1.png'),
])
