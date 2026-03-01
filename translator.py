"""Translation module using deep-translator."""

from deep_translator import GoogleTranslator


class TextTranslator:
    """Translates text between languages using Google Translate (free)."""

    def __init__(self, source="en", target="es"):
        """Initialize the translator.

        Args:
            source: Source language code (e.g., 'en', 'auto')
            target: Target language code (e.g., 'es', 'fr')
        """
        self._source = source
        self._target = target
        self._translator = GoogleTranslator(source=source, target=target)
        self._cache = {}

    def translate(self, text):
        """Translate a single text string.

        Returns the translated text, or the original if translation fails.
        """
        if not text or not text.strip():
            return text

        text = text.strip()

        if text in self._cache:
            return self._cache[text]

        try:
            result = self._translator.translate(text)
            if result:
                self._cache[text] = result
                return result
        except Exception:
            pass

        return text

    def translate_blocks(self, blocks):
        """Translate a list of OCR text blocks.

        Args:
            blocks: List of dicts with 'bbox', 'text', 'confidence' keys

        Returns:
            List of (x, y, w, h, translated_text) tuples
        """
        translated = []

        # Batch translate: collect all texts
        texts = [b["text"] for b in blocks if b["text"].strip()]
        if not texts:
            return translated

        # Translate all at once if possible, fall back to individual
        try:
            combined = "\n||\n".join(texts)
            result = self.translate(combined)
            parts = result.split("\n||\n") if result else []

            if len(parts) == len(texts):
                idx = 0
                for block in blocks:
                    if block["text"].strip():
                        x, y, w, h = block["bbox"]
                        translated.append((x, y, w, h, parts[idx].strip()))
                        idx += 1
                return translated
        except Exception:
            pass

        # Fallback: translate one by one
        for block in blocks:
            if block["text"].strip():
                x, y, w, h = block["bbox"]
                tr = self.translate(block["text"])
                translated.append((x, y, w, h, tr))

        return translated

    def set_languages(self, source, target):
        """Change source and target languages."""
        self._source = source
        self._target = target
        self._translator = GoogleTranslator(source=source, target=target)
        self._cache.clear()
