import re
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from dataclasses import dataclass, field


@dataclass
class SocialPost:
    id: str
    text: str
    normalized_text: str
    platform: str
    author: Optional[str]
    timestamp: str
    metadata: dict = field(default_factory=dict)


SLANG_MAP = {
    r'\bu\b': 'you',
    r'\bur\b': 'your',
    r'\br\b': 'are',
    r'\bw/\b': 'with',
    r'\bidk\b': 'I do not know',
    r'\bimo\b': 'in my opinion',
    r'\btbh\b': 'to be honest',
    r'\bomg\b': 'oh my god',
    r'\blmao\b': 'laughing',
    r'\bsmh\b': 'shaking my head',
    r'\bngl\b': 'not going to lie',
    r'\bfr\b': 'for real',
}


def normalize_text(text: str) -> str:
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#(\w+)', r'\1', text)

    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F9FF"
        u"\U00002702-\U000027B0"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub(' ', text)

    for pattern, replacement in SLANG_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    words = text.split()
    normalized_words = []
    for word in words:
        if len(word) > 4 and word.isupper():
            word = word.capitalize()
        normalized_words.append(word)
    text = ' '.join(normalized_words)

    text = re.sub(r'[!?]{2,}', '!', text)
    text = re.sub(r'\.{2,}', '...', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


class PostCache:
    def __init__(self, cache_file: str = "logs/post_cache.json", ttl_hours: int = 24):
        self.cache_file = cache_file
        self.ttl_seconds = ttl_hours * 3600  # Extended TTL for aggressive caching (saves ~15s per hit)
        self._memory: dict = {}
        self._load()

    def _load(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file) as f:
                try:
                    self._memory = json.load(f)
                    self._cleanup_expired()
                except json.JSONDecodeError:
                    self._memory = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self._memory, f, indent=2)

    def _cleanup_expired(self):
        """Remove entries older than TTL to keep cache fresh."""
        now = datetime.now(timezone.utc)
        expired_keys = []
        for key, entry in self._memory.items():
            if "cached_at" in entry:
                try:
                    cached_time = datetime.fromisoformat(entry["cached_at"])
                    if (now - cached_time).total_seconds() > self.ttl_seconds:
                        expired_keys.append(key)
                except ValueError:
                    expired_keys.append(key)
        for key in expired_keys:
            del self._memory[key]
        if expired_keys:
            self._save()

    def _key(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def is_cached(self, normalized_text: str) -> bool:
        key = self._key(normalized_text)
        if key not in self._memory:
            return False
        entry = self._memory[key]
        if "cached_at" in entry:
            try:
                cached_time = datetime.fromisoformat(entry["cached_at"])
                age = (datetime.now(timezone.utc) - cached_time).total_seconds()
                return age <= self.ttl_seconds
            except ValueError:
                return False
        return True

    def get(self, normalized_text: str) -> Optional[dict]:
        key = self._key(normalized_text)
        entry = self._memory.get(key)
        if entry and "cached_at" in entry:
            try:
                cached_time = datetime.fromisoformat(entry["cached_at"])
                age = (datetime.now(timezone.utc) - cached_time).total_seconds()
                if age <= self.ttl_seconds:
                    return entry
            except ValueError:
                return entry
        return entry if entry and "cached_at" not in entry else None

    def set(self, normalized_text: str, result: dict):
        self._memory[self._key(normalized_text)] = {
            **result,
            "cached_at": datetime.now(timezone.utc).isoformat()
        }
        self._save()


SIMULATED_FEED = [
    "COVID vaccines contain microchips that track your location",
    "The Great Wall of China is the only man-made structure visible from space",
    "Elon Musk bought Twitter for $44 billion in 2022",
    "can't believe how good this pizza is omg",
    "The Amazon River is the largest river in the world by discharge volume",
    "drinking bleach cures COVID its been proven",
    "water boils at 100 degrees at sea level mind blown",
    "5G towers are causing cancer in people who live nearby",
    "what time does the library close on sundays",
    "napoleon was actually really short like 5ft2",
]


def get_simulated_feed(limit: int = 10) -> List[SocialPost]:
    posts = []
    for i, text in enumerate(SIMULATED_FEED[:limit]):
        normalized = normalize_text(text)
        posts.append(SocialPost(
            id=f"sim_{i:04d}",
            text=text,
            normalized_text=normalized,
            platform="simulated",
            author=f"user_{i}",
            timestamp=datetime.now(timezone.utc).isoformat()
        ))
    return posts


def ingest_single_post(raw_text: str, platform: str = "api") -> SocialPost:
    normalized = normalize_text(raw_text)
    post_id = hashlib.sha256(raw_text.encode()).hexdigest()[:12]

    return SocialPost(
        id=post_id,
        text=raw_text,
        normalized_text=normalized,
        platform=platform,
        author=None,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


_spacy_model = None

def _get_spacy_model():
    """
    Singleton spaCy model loader.
    Loads once on first call, reuses on all subsequent calls.
    Prevents 500ms reload penalty on every request.
    """
    global _spacy_model
    if _spacy_model is None:
        import spacy
        _spacy_model = spacy.load("en_core_web_sm")
    return _spacy_model


def extract_entities(text: str) -> Dict:
    """
    Runs spaCy NER and dependency parsing on normalized text.
    Extracts named entities and subject-verb-object relationships.
    Used to build precise search queries for the retriever.
    
    Returns dict with:
    - entities: list of {text, label} dicts
    - entity_string: space-joined entity texts for search
    - subject: main subject of the claim
    - verb: main action/verb
    - key_terms: top nouns and proper nouns
    """
    try:
        nlp = _get_spacy_model()
        doc = nlp(text)

        # Named Entity Recognition
        entities = []
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "GPE", "LOC", "MONEY", 
                               "DATE", "PERCENT", "PRODUCT", "EVENT"]:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_
                })

        # Dependency Parsing — extract subject and main verb
        subject = None
        verb = None
        for token in doc:
            if token.dep_ in ["nsubj", "nsubjpass"] and subject is None:
                subject = token.text
            if token.pos_ == "VERB" and token.dep_ in ["ROOT"] and verb is None:
                verb = token.lemma_

        # Key terms — proper nouns and nouns
        key_terms = list(set([
            token.text for token in doc
            if token.pos_ in ["PROPN", "NOUN"]
            and not token.is_stop
            and len(token.text) > 2
        ]))[:5]

        # Build entity string for search query enhancement
        entity_string = " ".join([e["text"] for e in entities])

        return {
            "entities": entities,
            "entity_string": entity_string,
            "subject": subject,
            "verb": verb,
            "key_terms": key_terms
        }

    except Exception as e:
        return {
            "entities": [],
            "entity_string": "",
            "subject": None,
            "verb": None,
            "key_terms": []
        }
