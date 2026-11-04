import json
import re
import sys
from pathlib import Path
from typing import Dict, List

# Standard German pronouns in our app's order
PRONOUNS = ["ich", "du", "er/sie/es", "wir", "ihr", "sie/Sie"]

def _generate_compound_tenses(participle: str, aux: str) -> dict:
    """Uses the auxiliary (haben/sein) and participle to generate compound tenses."""
    if aux == "sein":
        aux_praesens = ["bin", "bist", "ist", "sind", "seid", "sind"]
        aux_praet = ["war", "warst", "war", "waren", "wart", "waren"]
        aux_inf = "sein"
    else:
        aux_praesens = ["habe", "hast", "hat", "haben", "habt", "haben"]
        aux_praet = ["hatte", "hattest", "hatte", "hatten", "hattet", "hatten"]
        aux_inf = "haben"

    werden_praesens = ["werde", "wirst", "wird", "werden", "werdet", "werden"]
    
    return {
        "perfekt": [f"{a} {participle}" for a in aux_praesens],
        "plusquamperfekt": [f"{a} {participle}" for a in aux_praet],
        "futur2": [f"{w} {participle} {aux_inf}" for w in werden_praesens]
    }

def load_tatoeba(filepath: str) -> List[dict]:
    """Loads a TSV of German-English sentences from ManyThings."""
    sentences = []
    try:
        with open(filepath, encoding="utf-8") as f:
            for i, line in enumerate(f):
                parts = line.strip().split("\t")
                # Format: English \t German \t Attribution
                if len(parts) >= 2:
                    # We use the line number as a fallback ID
                    source = parts[2] if len(parts) > 2 else f"tatoeba-line-{i}"
                    sentences.append({"id": str(i), "en": parts[0], "de": parts[1], "source": source})
    except FileNotFoundError:
        print(f"Warning: Tatoeba file {filepath} not found. Sentences will be empty.")
    return sentences

def extract_verb_forms(kaikki_entry: dict) -> dict:
    forms = kaikki_entry.get("forms", [])
    verb_data = {
        "auxiliary": "haben", # Default, flagged for review if uncertain
        "separable": False,
        "reflexive": "sich" in kaikki_entry.get("word", ""),
        "participle": "",
        "pronouns": PRONOUNS,
        "tenses": {
            "praesens": [""] * 6,
            "praeteritum": [""] * 6,
            "konjunktiv1": [""] * 6,
            "konjunktiv2": [""] * 6,
        },
        "imperative": {"du": "", "ihr": "", "Sie": ""}
    }

    # Map Kaikki tags to our pronoun indices
    person_map = {"first-person": 0, "second-person": 1, "third-person": 2}
    
    for f in forms:
        tags = f.get("tags", [])
        form_text = f.get("form", "")
        
        if "participle" in tags and "past" in tags:
            verb_data["participle"] = form_text
        
        if "imperative" in tags:
            if "singular" in tags and "second-person" in tags:
                verb_data["imperative"]["du"] = form_text
            elif "plural" in tags and "second-person" in tags:
                verb_data["imperative"]["ihr"] = form_text

        # Tense routing
        tense_key = None
        if "present" in tags and "indicative" in tags: tense_key = "praesens"
        elif "past" in tags and "indicative" in tags: tense_key = "praeteritum"
        elif "present" in tags and "subjunctive-i" in tags: tense_key = "konjunktiv1"
        elif "past" in tags and "subjunctive-ii" in tags: tense_key = "konjunktiv2"

        if tense_key:
            person = next((person_map[t] for t in tags if t in person_map), None)
            number = 0 if "singular" in tags else 3 if "plural" in tags else None
            if person is not None and number is not None:
                verb_data["tenses"][tense_key][person + number] = form_text
                # sie/Sie share the 3rd person plural
                if person + number == 5:
                    verb_data["imperative"]["Sie"] = f"{form_text} Sie"
    
    # Check for auxiliary in glosses or tags
    glosses = str(kaikki_entry.get("senses", [])).lower()
    if "auxiliary sein" in glosses:
        verb_data["auxiliary"] = "sein"
        
    # Generate compound tenses
    if verb_data["participle"]:
        compounds = _generate_compound_tenses(verb_data["participle"], verb_data["auxiliary"])
        verb_data["tenses"].update(compounds)
        
        # Futur 1: werden + infinitive
        inf = kaikki_entry.get("word", "")
        werden = ["werde", "wirst", "wird", "werden", "werdet", "werden"]
        verb_data["tenses"]["futur1"] = [f"{w} {inf}" for w in werden]

    return verb_data

def build_deck(a1_lemmas: List[str], kaikki_path: str, tatoeba_path: str, out_path: str):
    print("Loading Tatoeba sentences...")
    sentences = load_tatoeba(tatoeba_path)
    
    targets = {w.lower(): w for w in a1_lemmas}
    deck = {"schema": 2, "words": []}
    
    print(f"Scanning Kaikki JSONL for {len(targets)} words...")
    
    with open(kaikki_path, encoding="utf-8") as f:
        for line in f:
            if not targets:
                break
                
            entry = json.loads(line)
            word = entry.get("word", "")
            if word.lower() not in targets:
                continue
                
            pos = entry.get("pos", "")
            senses = entry.get("senses", [])
            if not senses: continue
            
            english_gloss = senses[0].get("glosses", [""])[0]
            
            word_obj = {
                "id": f"{word.lower()}-{pos}",
                "lemma": word,
                "pos": pos,
                "level": "A1",
                "english": english_gloss,
                "explanation": english_gloss,
                "examples": []
            }
            
            # Find an example sentence
            for s in sentences:
                if re.search(r'\b' + re.escape(word) + r'\b', s["de"], re.IGNORECASE):
                    if len(s["de"].split()) <= 10:  # Keep it short
                        word_obj["examples"].append({
                            "de": s["de"], 
                            "en": s["en"], 
                            "source": f"tatoeba:{s['id']}"
                        })
                        break
            
            if pos == "verb":
                word_obj["verb"] = extract_verb_forms(entry)
            elif pos == "noun":
                tags = entry.get("tags", [])
                forms = entry.get("forms", [])
                
                article = "der" if "masculine" in tags else "die" if "feminine" in tags else "das" if "neuter" in tags else ""
                plural = next((f.get("form") for f in forms if "plural" in f.get("tags", [])), "-")
                genitive = next((f.get("form") for f in forms if "genitive" in f.get("tags", []) and "singular" in f.get("tags", [])), "-")
                
                word_obj["noun"] = {"article": article, "plural": plural, "genitive": genitive}
            
            deck["words"].append(word_obj)
            del targets[word.lower()]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(deck, f, indent=2, ensure_ascii=False)
        
    print(f"\nBuilt {len(deck['words'])} words. Saved to {out_path}")
    if targets:
        print(f"Missing from Kaikki: {list(targets.keys())}")

if __name__ == "__main__":
    import os
    if not os.path.exists("kaikki.jsonl"):
        print("Missing 'kaikki.jsonl'. Download German JSONL from Kaikki.org")
        sys.exit(1)
        
    lemmas = ["lernen", "sein", "Apfel", "Wasser", "schnell"] # Expand this list
    if os.path.exists("a1_lemmas.txt"):
        with open("a1_lemmas.txt", encoding="utf-8") as f:
            lemmas = [line.strip() for line in f if line.strip()]
            
    build_deck(lemmas, "kaikki.jsonl", "tatoeba.tsv", "../data/vocab.json")
