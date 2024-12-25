# Owl Virtual Assistant (OVA)

A desktop virtual assistant in the form of an adorable owl that sits on your desktop, responds to voice commands, and provides helpful interactions using AI.

## Features

- 🦉 Cute owl desktop companion with fluid animations
- 🎤 Voice-activated interactions (wake word: "Hey Ova")
- 💬 Natural language conversations powered by Ollama
- 🗣️ Text-to-speech responses using Edge TTS
- 💭 Multiple personality presets
- 🎵 Sound effects and ambient responses
- 🖱️ Interactive animations (drag & drop, flying, dancing)
- 💤 Idle animations and sleep mode
- ⚙️ Customizable settings

## Requirements

- Windows OS
- Python 3.12+
- [Ollama](https://ollama.ai/) running locally
- Internet connection for Edge TTS

## Quick Start

1. Install dependencies:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the application:
```bash
python scripts/desktop_pet.py
```

3. Build executable:
```bash
python build.py
```

## Usage

- Say "Hey Ova" to activate voice recognition
- Click and drag to move Ova around your desktop
- Right-click for settings and options
- Ova will perform random actions when idle
- After a period of inactivity, Ova will go to sleep

## Configuration

- Edit `config.json` to customize:
  - Voice type and name
  - Sleep timer duration
  - Personality preset
  - Display mode
  - Random action settings

## Project Structure

```
owl/
├── assets/           # Animation frames and sound effects
├── scripts/         
│   ├── display/     # Display management
│   ├── presets/     # Personality presets
│   └── *.py        # Core Python modules
├── build.py         # PyInstaller build script
├── config.json      # Configuration file
└── requirements.txt # Python dependencies
```

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

[MIT License](LICENSE)
