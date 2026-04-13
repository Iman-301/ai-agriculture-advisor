"""Test TTS (Text-to-Speech) with any Amharic text input.

Usage:
    python test_tts.py                          # Interactive mode
    python test_tts.py "ጤፍ ለምን ያህል ዩሪያ ልጠቀም"   # Direct text
    python test_tts.py --file input.txt         # From file
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.services.tts_service import GTTSService


def main():
    """Test TTS with Amharic text."""
    tts = GTTSService(lang="am")
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file":
            # Read from file
            if len(sys.argv) < 3:
                print("Usage: python test_tts.py --file <filename>")
                return
            
            file_path = sys.argv[2]
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                print(f"Reading from file: {file_path}")
                print(f"Text: {text}")
            except FileNotFoundError:
                print(f"Error: File '{file_path}' not found")
                return
        else:
            # Direct text from command line
            text = " ".join(sys.argv[1:])
    else:
        # Interactive mode
        print("=== Amharic Text-to-Speech Test ===")
        print("Enter Amharic text to speak (or 'quit' to exit):")
        print()
        
        while True:
            text = input("Text: ").strip()
            
            if text.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            
            if not text:
                print("Please enter some text.")
                continue
            
            print(f"\nSpeaking: {text}")
            try:
                tts.synthesize_and_play(text)
                print("✓ Done!\n")
            except Exception as e:
                print(f"Error: {e}\n")
        
        return
    
    # Speak the text
    if text:
        print(f"\nSpeaking: {text}")
        try:
            tts.synthesize_and_play(text)
            print("✓ Done!")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("No text provided.")


if __name__ == "__main__":
    main()
