import re

sara_identity_keywords = {
    "religion": [
        "islam", "muslim", "muslimah", "kristen", "katolik",
        "hindu", "buddha", "budha", "konghucu", "yahudi",
        "ateis", "atheis", "syiah", "sunni", "wahabi",
        "nasrani", "pendeta", "ustad", "ustadz", "ulama",
        "gereja", "masjid", "vihara", "pura"
    ],

    "ethnic_racial": [
        "jawa", "sunda", "batak", "minang", "padang",
        "madura", "bugis", "dayak", "papua", "ambon",
        "tionghoa", "cina", "chindo", "arab", "melayu",
        "bali", "banjar", "aceh", "aseng", "asing"
    ],

    "intergroup": [
        "kadrun", "cebong", "kampret", "buzzer",
        "komunis", "pki", "liberal", "radikal",
        "antek asing", "antek aseng", "pengkhianat bangsa",
        "pribumi", "pendatang", "minoritas", "mayoritas"
    ]
}

sara_attack_keywords = {
    "religious_attack": [
        "kafir", "sesat", "murtad", "penista agama",
        "agama palsu", "ajaran sesat", "masuk neraka",
        "teroris", "ekstremis", "fanatik",
        "anti islam", "anti kristen", "anti agama"
    ],

    "ethnic_racial_attack": [
        "antek cina", "cina komunis", "pribumi tolol",
        "pendatang kurang ajar", "ras rendah",
        "kulit hitam", "kulit gelap", "monyet",
        "bau", "jorok", "kampungan"
    ],

    "exclusion_threat": [
        "usir", "diusir", "pergi dari indonesia",
        "balik ke negara asal", "balik ke daerah asal",
        "jangan tinggal di sini", "tidak pantas hidup di sini",
        "boikot", "bubarkan", "hapuskan", "musnahkan"
    ],

    "general_degrading": [
        "bodoh", "goblok", "tolol", "bego", "dungu",
        "jelek", "hina", "rendahan", "sampah",
        "najis", "jijik", "kotor", "bau",
        "tidak berguna", "beban", "memalukan",
        "hama", "sdm rendah"
    ]
}

normalization_map = {
    "4": "a",
    "@": "a",
    "1": "i",
    "!": "i",
    "0": "o",
    "3": "e",
    "$": "s",
    "5": "s"
}

def normalize_text(text):
    text = text.lower()
    for key, value in normalization_map.items():
        text = text.replace(key, value)
    
    # Remove repeated characters
    text = re.sub(r'(.)\1+', r'\1', text)
    
    # Strip punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    return text

def flatten_keyword_dict(keyword_dict):
    result = []
    for category, words in keyword_dict.items():
        for word in words:
            result.append((word, category))
    return result

def find_keyword_matches(text, keyword_dict):
    matches = []
    flat_keywords = flatten_keyword_dict(keyword_dict)

    for keyword, category in flat_keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, text):
            matches.append({
                "keyword": keyword,
                "category": category
            })
    return matches

def term_positions(words, term):
    term_words = term.split()
    positions = []
    for i in range(len(words) - len(term_words) + 1):
        if words[i:i + len(term_words)] == term_words:
            positions.append(i)
    return positions

def has_near_match(text, identity_matches, attack_matches, max_distance=6):
    words = text.split()
    for identity in identity_matches:
        identity_positions = term_positions(words, identity["keyword"])
        for attack in attack_matches:
            attack_positions = term_positions(words, attack["keyword"])
            for i_pos in identity_positions:
                for a_pos in attack_positions:
                    if abs(i_pos - a_pos) <= max_distance:
                        return True
    return False

def classify_sara_cyberbullying(text):
    if not text:
        return 0
        
    normalized_text = normalize_text(text)
    
    identity_matches = find_keyword_matches(normalized_text, sara_identity_keywords)
    attack_matches = find_keyword_matches(normalized_text, sara_attack_keywords)
    
    if identity_matches and attack_matches:
        if has_near_match(normalized_text, identity_matches, attack_matches, max_distance=6):
            return 1
            
    return 0

def classify_tweet(text):
    return classify_sara_cyberbullying(text)

if __name__ == "__main__":
    test_cases = [
        "dasar cina komunis lu",
        "orang tionghoa sedang makan",
        "islam itu agama damai",
        "dasar islam sesat",
        "jawa bau kampungan"
    ]
    for t in test_cases:
        print(f"'{t}' -> {classify_tweet(t)}")
