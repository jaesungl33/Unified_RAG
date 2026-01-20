"""
Translation and Synonym service for keyword finder.
Uses Google Translate (free) and WordNet for automatic translation and synonym generation.
Language detection powered by fast-langdetect (80x faster fastText).
Based on test_google_translate.py and test_synonym_english.py
"""
import logging
import re
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

_VIETNAMESE_CHARS_PATTERN = re.compile(
    r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ]',
    re.IGNORECASE
)


def detect_language_local(text: str) -> str:
    """
    Fast language detection using fast-langdetect (fastText-based).
    Returns ISO 639-1 language code (e.g., 'en', 'vi', 'zh', 'ja')
    Falls back to regex-based detection if fast-langdetect is not available.
    """
    try:
        from fast_langdetect import detect
        
        # Detect language using fast-langdetect (lite model by default)
        result = detect(text, model='lite', k=1)
        
        if result and len(result) > 0:
            # Extract language code (e.g., 'en', 'vi', 'zh-cn')
            lang_code = result[0]['lang']
            
            # Handle language codes with subtags (e.g., 'zh-cn' -> 'zh', 'pt-br' -> 'pt')
            base_lang = lang_code.split('-')[0].lower()
            return base_lang
        
        # Fallback to English if detection fails
        return 'en'
        
    except ImportError:
        # Fallback to regex-based detection if fast-langdetect not installed
        return 'vi' if _VIETNAMESE_CHARS_PATTERN.search(text) else 'en'
    except Exception as e:
        # Fallback on any error
        logger.warning(f"Language detection error: {e}, using fallback")
        return 'vi' if _VIETNAMESE_CHARS_PATTERN.search(text) else 'en'


def translate_with_google(text: str, target_language: Optional[str] = None) -> Dict[str, Any]:
    """
    Translate text using free Google Translate API (no API key needed).
    Uses deep-translator library.
    
    Args:
        text: Text to translate
        target_language: Target language code ('en' or 'vi')
                        If None, auto-detects and translates to opposite
    
    Returns:
        dict with translation results
    """
    try:
        from deep_translator import GoogleTranslator
        
        # Detect source language locally first
        detected_lang = detect_language_local(text)
        
        # Determine target language if not specified
        if target_language is None:
            if detected_lang == 'vi':
                target_language = 'en'
            else:
                target_language = 'vi'
        
        translator = GoogleTranslator(source='auto', target=target_language)
        translated_text = translator.translate(text)
        
        # Try to get detected language from translator (optional enhancement)
        try:
            detected = translator.detect(text)
            if isinstance(detected, dict):
                detected_lang = detected.get('lang', detected_lang)
        except Exception:
            # Detection failure is non-critical, use local detection
            pass
        
        return {
            'original_text': text,
            'translated_text': translated_text,
            'detected_language': detected_lang,
            'target_language': target_language,
            'success': True
        }
        
    except ImportError:
        return {
            'original_text': text,
            'translated_text': None,
            'error': 'deep-translator not installed. Run: pip install deep-translator',
            'success': False
        }
    except Exception as e:
        return {
            'original_text': text,
            'translated_text': None,
            'error': str(e),
            'success': False
        }


def setup_nltk():
    """Setup NLTK and download WordNet data if needed."""
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        
        try:
            wn.synsets('test')
        except LookupError:
            logger.info("📥 Downloading NLTK WordNet data (first time only)...")
            nltk.download('wordnet', quiet=True)
            nltk.download('omw-1.4', quiet=True)
            logger.info("✅ WordNet data downloaded!")
        
        return wn
        
    except ImportError:
        logger.error("❌ nltk library not installed. Install with: pip install nltk")
        return None
    except Exception as e:
        logger.error(f"❌ Error setting up NLTK: {e}")
        return None


def get_english_synonyms_wordnet(word: str, wordnet, max_synonyms: int = 3) -> List[str]:
    """
    Get synonyms using WordNet (Artha-inspired approach).
    Filters by part-of-speech, uses most common synset, removes antonyms.
    
    Args:
        word: Word to get synonyms for
        wordnet: WordNet instance (from setup_nltk())
        max_synonyms: Maximum number of synonyms to return
    
    Returns:
        List of synonyms
    """
    if not wordnet:
        return []
    
    word_lower = word.lower().strip()
    synsets = wordnet.synsets(word_lower)
    
    if not synsets:
        return []
    
    # Group synsets by part-of-speech (prioritize: noun > verb > adjective > adverb)
    pos_priority = {'n': 1, 'v': 2, 'a': 3, 's': 3, 'r': 4}
    
    pos_synsets = {}
    for synset in synsets:
        pos = synset.pos()
        if pos not in pos_synsets:
            pos_synsets[pos] = []
        pos_synsets[pos].append(synset)
    
    synonyms = []
    seen = set()
    
    for pos in sorted(pos_synsets.keys(), key=lambda p: pos_priority.get(p, 99)):
        if not pos_synsets[pos]:
            continue
        
        synset = pos_synsets[pos][0]  # Most common synset (WordNet returns in frequency order)
        
        for lemma in synset.lemmas():
            if len(synonyms) >= max_synonyms:
                break
            
            synonym = lemma.name().replace('_', ' ')
            synonym_lower = synonym.lower()
            
            if synonym_lower == word_lower or lemma.antonyms():
                continue
            
            if synonym_lower not in seen:
                synonyms.append(synonym)
                seen.add(synonym_lower)
        
        if len(synonyms) >= max_synonyms:
            break
    
    return synonyms[:max_synonyms]


def get_synonyms_for_word(word: str, max_synonyms: int = 3) -> List[str]:
    """
    Get synonyms for a word using WordNet.
    This is a convenience wrapper that handles WordNet setup.
    
    Args:
        word: Word to get synonyms for
        max_synonyms: Maximum number of synonyms to return
    
    Returns:
        List of synonyms
    """
    wordnet = setup_nltk()
    if not wordnet:
        return []
    
    return get_english_synonyms_wordnet(word, wordnet, max_synonyms)


def auto_translate_and_find_synonyms(keyword: str) -> Dict[str, Any]:
    """
    Automatically translate keyword and find synonyms.
    Main function for automatic translation + synonym finding.
    
    Args:
        keyword: The keyword to process
    
    Returns:
        Dict with 'original', 'detected_language', 'translation', 'synonyms_original',
        'synonyms_translated', 'all_search_terms', 'success', and optionally 'error'
    """
    keyword_stripped = keyword.strip() if keyword else ""
    
    if not keyword_stripped:
        return {
            'original': keyword or '',
            'detected_language': 'en',
            'translation': '',
            'synonyms_original': [],
            'synonyms_translated': [],
            'all_search_terms': [],
            'success': False
        }
    
    detected_lang = detect_language_local(keyword_stripped)
    translation_result = translate_with_google(keyword_stripped)
    
    if not translation_result.get('success'):
        return {
            'original': keyword_stripped,
            'detected_language': detected_lang,
            'translation': '',
            'synonyms_original': [],
            'synonyms_translated': [],
            'all_search_terms': [keyword_stripped],
            'success': False,
            'error': translation_result.get('error', 'Translation failed')
        }
    
    translated_text = translation_result.get('translated_text', '')
    synonyms_original = get_synonyms_for_word(keyword_stripped, max_synonyms=3)
    synonyms_translated = get_synonyms_for_word(translated_text, max_synonyms=3) if translated_text else []
    
    all_search_terms = [keyword_stripped]
    if translated_text:
        all_search_terms.append(translated_text)
    all_search_terms.extend(synonyms_original)
    all_search_terms.extend(synonyms_translated)
    
    # Remove duplicates and empty strings, preserve order
    all_search_terms = [t.strip() for t in all_search_terms if t and t.strip()]
    all_search_terms = list(dict.fromkeys(all_search_terms))
    
    return {
        'original': keyword_stripped,
        'detected_language': detected_lang,
        'translation': translated_text,
        'synonyms_original': synonyms_original,
        'synonyms_translated': synonyms_translated,
        'all_search_terms': all_search_terms,
        'success': True
    }
