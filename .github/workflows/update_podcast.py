import os
import re
import html
import feedparser
from pathlib import Path

RSS_URL = os.environ["RSS_URL"]
INDEX_FILE = Path("index.html")


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", "", value)
    return " ".join(value.split())


def get_episode_number(title):
    match = re.search(r"Επ\.\s*(\d+)", title, re.IGNORECASE)
    return int(match.group(1)) if match else None


def get_year(title):
    match = re.search(r"\((\d{4})\)", title)
    return match.group(1) if match else ""


def get_duration(entry):
    seconds = entry.get("itunes_duration", "")

    if not seconds:
        return ""

    if isinstance(seconds, int):
        minutes = seconds // 60
        return f"{minutes}m"

    if ":" in str(seconds):
        parts = str(seconds).split(":")
        if len(parts) == 2:
            return f"{parts[0]}m"
        if len(parts) == 3:
            return f"{int(parts[0]) * 60 + int(parts[1])}m"

    return str(seconds)


feed = feedparser.parse(RSS_URL)

if not feed.entries:
    raise RuntimeError("Δεν βρέθηκαν επεισόδια στο RSS.")

entries = []

for entry in feed.entries:
    title = clean_text(entry.get("title", ""))
    number = get_episode_number(title)

    if number is not None:
        entries.append((number, entry))

if not entries:
    raise RuntimeError("Δεν βρέθηκαν επεισόδια με αριθμό.")

entries.sort(key=lambda x: x[0], reverse=True)

number, episode = entries[0]
title = clean_text(episode.get("title", ""))

image = ""

if episode.get("image"):
    image = episode.image.get("href", "")

if not image and feed.feed.get("image"):
    image = feed.feed.image.get("href", "")

if not image:
    image = "thehowlingthreelogo-mark.png"

spotify_link = episode.get("link", "")
duration = get_duration(episode)
year = get_year(title)

description = clean_text(
    episode.get("summary", "")
    or episode.get("description", "")
)

# Για το Επ. 107 χρησιμοποιούμε τα γνωστά στοιχεία.
if number == 107:
    director = "John Waters"
    country = "ΗΠΑ"
    genre = "Μαύρη κωμωδία"
    collection = "Σινεμά"
else:
    # Για μελλοντικά επεισόδια παίρνουμε στοιχεία από την περιγραφή
    # όταν υπάρχουν.
    director = "—"
    country = "—"
    genre = "—"
    collection = "—"

    patterns = {
        "director": r"Σκηνοθεσία\s*[:\-]\s*([^\n|]+)",
        "country": r"Χώρα\s*[:\-]\s*([^\n|]+)",
        "genre": r"Είδος\s*[:\-]\s*([^\n|]+)",
        "collection": r"Συλλογή\s*[:\-]\s*([^\n|]+)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if key == "director":
                director = value
            elif key == "country":
                country = value
            elif key == "genre":
                genre = value
            elif key == "collection":
                collection = value

record = f'''
        <article class="record reveal" data-collection="{collection.lower()}" data-latest="true">
          <div class="record-media">
            <div class="record-frame"><img loading="lazy" src="{image}" alt="{title}" /></div>
            <span class="record-id">THT—{number}</span>
          </div>
          <div class="record-body">
            <h3 class="episode-title">{title}</h3>
            <dl class="record-fields">
              <div><dt>Σκηνοθεσία</dt><dd>{director}</dd></div>
              <div><dt>Χώρα</dt><dd>{country}</dd></div>
              <div><dt>Είδος</dt><dd>{genre}</dd></div>
              <div><dt>Συλλογή</dt><dd>{collection}</dd></div>
              <div><dt>Διάρκεια</dt><dd>{duration}</dd></div>
            </dl>
            <a class="episode-link" href="{spotify_link}" target="_blank" rel="noopener noreferrer">
              Ακούστε στο Spotify
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/></svg>
            </a>
          </div>
        </article>
'''

content = INDEX_FILE.read_text(encoding="utf-8")

# Αν το επεισόδιο υπάρχει ήδη, δεν κάνουμε τίποτα.
if f"THT—{number}" in content:
    print(f"Επ. {number} υπάρχει ήδη.")
    raise SystemExit(0)

# Το νέο επεισόδιο μπαίνει ακριβώς πριν από το πρώτο υπάρχον record.
marker = '        <article class="record reveal"'

position = content.find(marker)

if position == -1:
    raise RuntimeError("Δεν βρέθηκε η λίστα επεισοδίων στο index.html.")

content = content[:position] + record + "\n" + content[position:]

# Το νέο επεισόδιο είναι το μοναδικό latest.
content = re.sub(
    r'\sdata-latest="true"',
    "",
    content
)

# Ξαναβάζουμε latest στο νέο επεισόδιο.
new_marker = f'<article class="record reveal" data-collection="{collection.lower()}" data-latest="true"'
content = content.replace(
    f'<article class="record reveal" data-collection="{collection.lower()}">',
    new_marker,
    1
)

INDEX_FILE.write_text(content, encoding="utf-8")

print(f"Προστέθηκε το Επ. {number}: {title}")
