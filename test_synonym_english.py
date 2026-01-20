"""
English Synonym Generator using WordNet (Artha-inspired)
Uses NLTK WordNet for synonym generation
Inspired by Artha - An open cross-platform thesaurus based on WordNet
Based on: https://github.com/sria91/artha
"""
import re
import os
from pathlib import Path
from itertools import product


def setup_nltk():
    """Setup NLTK and download WordNet data"""
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        
        # Download WordNet data if not already downloaded
        try:
            wn.synsets('test')
        except LookupError:
            print("📥 Downloading NLTK WordNet data (first time only)...")
            nltk.download('wordnet', quiet=True)
            nltk.download('omw-1.4', quiet=True)  # Open Multilingual Wordnet
            print("✅ WordNet data downloaded!")
        
        return wn
        
    except ImportError:
        print("❌ nltk library not installed")
        print("   Install with: pip install nltk")
        return None
    except Exception as e:
        print(f"❌ Error setting up NLTK: {e}")
        return None


def get_english_synonyms_wordnet(word: str, wordnet, max_synonyms: int = 3) -> list:
    """
    Get synonyms using WordNet (Artha-inspired approach)
    Filters by part-of-speech, uses most common synset, removes antonyms
    """
    if not wordnet:
        return []
    
    word_lower = word.lower().strip()
    
    # Get all synsets for the word
    synsets = wordnet.synsets(word_lower)
    
    if not synsets:
        return []
    
    # Group synsets by part-of-speech (prioritize: noun > verb > adjective > adverb)
    pos_priority = {'n': 1, 'v': 2, 'a': 3, 's': 3, 'r': 4}  # 's' is satellite adjective
    
    pos_synsets = {}
    for synset in synsets:
        pos = synset.pos()
        if pos not in pos_synsets:
            pos_synsets[pos] = []
        pos_synsets[pos].append(synset)
    
    # Get synonyms from the most common synset for each POS (prioritized)
    synonyms = []
    seen = set()
    
    # Process in priority order
    for pos in sorted(pos_synsets.keys(), key=lambda p: pos_priority.get(p, 99)):
        pos_synsets_list = pos_synsets[pos]
        # WordNet returns synsets in frequency order (most common first)
        if pos_synsets_list:
            # Use the first (most common) synset
            synset = pos_synsets_list[0]
            
            # Get all lemma names (synonyms) from this synset
            for lemma in synset.lemmas():
                synonym = lemma.name().replace('_', ' ')
                
                # Skip the original word
                if synonym.lower() == word_lower:
                    continue
                
                # Skip antonyms
                if lemma.antonyms():
                    continue
                
                # Add if not already seen
                if synonym.lower() not in seen:
                    synonyms.append(synonym)
                    seen.add(synonym.lower())
                    
                    if len(synonyms) >= max_synonyms:
                        break
        
        if len(synonyms) >= max_synonyms:
            break
    
    return synonyms[:max_synonyms]


def parse_phrase(phrase: str) -> list:
    """Parse phrase into individual words"""
    words = re.findall(r'\b[a-zA-Z]+\b', phrase.lower())
    words = [w for w in words if len(w) >= 3]
    return words


def generate_combinations(word_synonyms_dict: dict) -> list:
    """Generate ALL combinations of synonyms from multiple words"""
    if len(word_synonyms_dict) < 2:
        return []
    
    words = list(word_synonyms_dict.keys())
    synonym_lists = []
    
    for word in words:
        synonyms = word_synonyms_dict[word]
        if not synonyms:
            synonyms = [word]
        synonym_lists.append(synonyms)
    
    combinations = []
    for combo in product(*synonym_lists):
        combined = ' '.join(combo)
        combinations.append(combined)
    
    return combinations


def process_input(input_text: str, wordnet):
    """Process single word or phrase"""
    words = parse_phrase(input_text)
    
    if not words:
        return None
    
    word_synonyms = {}
    
    for word in words:
        synonyms = get_english_synonyms_wordnet(word, wordnet, max_synonyms=3)
        word_synonyms[word] = synonyms
    
    combinations = []
    if len(words) > 1:
        combinations = generate_combinations(word_synonyms)
    
    if len(words) == 1:
        total_outputs = len(word_synonyms[words[0]])
    else:
        total_outputs = len(combinations)
    
    return {
        'original': input_text,
        'parsed_words': words,
        'word_synonyms': word_synonyms,
        'combinations': combinations,
        'total_outputs': total_outputs
    }


def display_results(result: dict):
    """Display results in a nice format"""
    if not result:
        print("❌ No valid words found in input\n")
        return
    
    print("\n" + "=" * 70)
    print(f"📝 Original Input: {result['original']}")
    print(f"🔍 Parsed Words: {', '.join(result['parsed_words'])}")
    print("=" * 70)
    
    word_synonyms = result['word_synonyms']
    combinations = result['combinations']
    
    if len(result['parsed_words']) == 1:
        word = result['parsed_words'][0]
        synonyms = word_synonyms[word]
        
        print(f"\n📚 Synonyms for '{word}' (WordNet - Artha-inspired):")
        if synonyms:
            for i, syn in enumerate(synonyms, 1):
                print(f"   {i}. {syn}")
        else:
            print("   (none found - word might be too rare)")
    else:
        for word, synonyms in word_synonyms.items():
            print(f"\n📚 Synonyms for '{word}':")
            if synonyms:
                for i, syn in enumerate(synonyms, 1):
                    print(f"   {i}. {syn}")
            else:
                print("   (using original word)")
        
        if combinations:
            print(f"\n🔄 All Combinations (Cartesian Product):")
            for i, combo in enumerate(combinations, 1):
                print(f"   {i}. {combo}")
    
    print("\n" + "=" * 70)
    print(f"📊 Total Outputs: {result['total_outputs']}")
    
    if len(result['parsed_words']) == 1:
        word = result['parsed_words'][0]
        print(f"   Single word: {len(word_synonyms[word])} synonyms")
    else:
        synonym_counts = [len(syns) if syns else 1 for syns in word_synonyms.values()]
        breakdown = ' × '.join(str(c) for c in synonym_counts)
        print(f"   Cartesian product: {breakdown} = {result['total_outputs']} combinations")
    
    print("=" * 70 + "\n")


def main():
    """Main CLI loop"""
    print("\n" + "=" * 70)
    print("📖 English Synonym Generator (WordNet - Artha-inspired)")
    print("=" * 70)
    print("Features:")
    print("  • Uses NLTK WordNet (same database as Artha)")
    print("  • Inspired by Artha - Open cross-platform thesaurus")
    print("  • Filters by part-of-speech (noun > verb > adjective)")
    print("  • Uses most common synset (frequency-based)")
    print("  • Removes antonyms automatically")
    print("  • Single word: returns 3 synonyms")
    print("  • Two words: returns 3×3 = 9 combinations")
    print("  • Three words: returns 3×3×3 = 27 combinations")
    print("\nNote: First run downloads WordNet data (~10MB, one-time)")
    print("      Installation: pip install nltk")
    print("\nCommands:")
    print("  • 'quit' or 'exit' - Exit")
    print("=" * 70 + "\n")
    
    # Setup WordNet
    wordnet = setup_nltk()
    
    if not wordnet:
        print("\n❌ Cannot proceed without WordNet")
        return
    
    print()
    
    while True:
        try:
            user_input = input("Enter word or phrase: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not user_input:
                continue
            
            result = process_input(user_input, wordnet)
            display_results(result)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()


