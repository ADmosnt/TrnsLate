# TrnsLate

A transparent overlay window for PC that captures, detects, and translates text in real-time — inspired by Android's Google Lens overlay.

## How it works

1. A transparent, resizable window sits on top of all other windows
2. It continuously captures the screen region beneath it
3. OCR detects any text in that region
4. Detected English text is translated to your target language
5. Translated text is rendered on top of the original

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

### Controls

- **Drag** the overlay window to move it over the text you want to translate
- **Resize** from edges/corners
- **Right-click** for options menu (change languages, toggle auto-translate)
- **Ctrl+Q** to quit
- **Ctrl+T** to toggle translation on/off
- **Ctrl+R** to force refresh/re-scan

### Command-line options

```bash
python main.py --source en --target es    # English to Spanish
python main.py --opacity 0.3              # Set overlay opacity (0.0-1.0)
python main.py --width 600 --height 400   # Set initial window size
```

## Supported Languages

Source and target languages depend on EasyOCR and deep-translator support.
Common codes: `en`, `es`, `fr`, `de`, `pt`, `it`, `ja`, `ko`, `zh-cn`, `ru`
