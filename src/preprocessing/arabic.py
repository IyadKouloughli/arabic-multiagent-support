# -*- coding: utf-8 -*-
"""Arabic text preprocessing module.
Removes diacritics (tashkeel) and tatweel (kashida) while preserving original letter forms.
"""
import re

# Harakat / Diacritics: fathatan, dammatan, kasratan, fatha, damma, kasra, shadda, sukun, dagger alif, etc.
DIACRITICS_REGEX = re.compile(r"[\u064B-\u0652\u0670\u0653-\u065F]")
TATWEEL_REGEX = re.compile(r"\u0640")
MULTI_SPACE_REGEX = re.compile(r"[^\S\r\n]+")


def preprocess_arabic(text: str) -> str:
    """Preprocess Arabic text by removing diacritics and tatweel while keeping original letter forms.
    
    Examples:
        - "مَرْحَبــــاً" -> "مرحبا"
        - "أَهْلاً بِكُمْ فِي متجرِنا" -> "أهلا بكم في متجرنا"
        - Letters 'أ', 'إ', 'آ', 'ة', 'ي', 'ى' keep their exact original forms.
    """
    if not text:
        return ""
    
    # 1. Remove tatweel (kashida)
    text = TATWEEL_REGEX.sub("", text)
    
    # 2. Remove all diacritics / tashkeel
    text = DIACRITICS_REGEX.sub("", text)
    
    # 3. Normalize multiple horizontal spaces
    text = MULTI_SPACE_REGEX.sub(" ", text)
    
    return text.strip()
