# Scrap grammar lessons from kwiziq and convert them into ankii flashcards

import json

import bs4
import genanki
import requests

BASE_URL = "https://french.kwiziq.com"
GRAMMAR_URL = "/revision/grammar"


def get_links():
    res = requests.get(BASE_URL + GRAMMAR_URL)
    res.raise_for_status()
    frenchSoup = bs4.BeautifulSoup(res.text, "html.parser")
    return [
        f"{BASE_URL}{a['href']}"
        for li in frenchSoup.find_all("li")
        for a in li.find_all("a", href=True)
        if a["href"].startswith("/revision/grammar/")
    ]


def download_audio(audio_url, data_sound):
    # Use the 'requests' library to download the audio file
    response = requests.get(audio_url)
    response.raise_for_status()

    # Save the file locally (you can modify the file name here)
    audio_filename = f"{data_sound}.mp3"
    with open(audio_filename, "wb") as f:
        f.write(response.content)

    return audio_filename


def get_sound_dict(frenchSoup):
    sound_dict = {}
    scripts = frenchSoup.find_all("script")
    for script in scripts:
        if script.string and "soundManager.createSound" in script.string:
            start_index = script.string.find("soundManager.createSound(") + len(
                "soundManager.createSound("
            )
            end_index = script.string.find(");", start_index)
            json_string = (
                script.string[start_index:end_index]
                .strip()
                .replace("\n", "")
                .replace("\t", "")
                .replace("'", '"')
                .replace("{id:", '{"id":')
                .replace("type:", '"type":')
                .replace("url:", '"url":')
                .replace('"},  ],}', '"}]}')
            )
            dict = json.loads(json_string)
            sound_dict[dict["id"]] = dict["url"][0]["url"]
    return sound_dict


def get_cards(link):
    res = requests.get(link)
    res.raise_for_status()

    frenchSoup = bs4.BeautifulSoup(res.text, "html.parser")

    title = frenchSoup.select("h1")[0].getText()

    sound_dict = get_sound_dict(frenchSoup)

    articles = frenchSoup.find_all(
        "article", class_="text-example text-example--border-bottom"
    )
    filtered_articles = [
        article for article in articles if not article.find(class_="video-wrapper")
    ]
    cards = []
    for article in filtered_articles:
        lang_french = (
            article.find("span", class_="txt--lang-native")
            .get_text()
            .replace("\xa0", " ")
        )
        lang_english = (
            article.find("span", class_="txt--lang-foreign")
            .get_text()
            .replace("\xa0", " ")
        )
        sound_element = article.find("a", class_="btn-audio--play")
        data_sound = sound_element["data-sound"] if sound_element else None
        sound_url = f"{BASE_URL}{sound_dict[data_sound]}"
        audio_file = download_audio(sound_url, data_sound)
        cards.append(
            {
                "title": title,
                "link": link,
                "french": lang_french,
                "english": lang_english,
                "audio_file": audio_file,
            }
        )
    return cards


def create_anki_deck(cards):
    # Model for the flashcards
    my_model = genanki.Model(
        1,
        "French Grammar Model",
        fields=[
            {"name": "English"},
            {"name": "French"},
            {"name": "Details"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": '<div style="text-align: center; font-weight: bold;">{{English}}</div>',
                "afmt": """
                    <div style="text-align: center;">
                        {{FrontSide}}
                        <hr id="answer">
                        <div>{{French}}</div>
                        <br>
                        <div>{{Details}}</div>
                        <br>
                    </div>
                """,
            },
        ],
    )

    # Create a deck
    my_deck = genanki.Deck(
        1,
        "French Grammar Lessons",
    )

    # Add cards to the deck
    for card in cards:
        note = genanki.Note(
            model=my_model,
            fields=[
                card["english"],
                f"{card['french']} [sound:{card['audio_file'].replace('/', ':')}]",
                f"<b></b><br><a href='{card['link']}'>{card['title']}</a>",
            ],
        )
        my_deck.add_note(note)

    # Save the deck to a file
    package = genanki.Package(my_deck)
    package.media_files = [card["audio_file"] for card in cards]
    package.write_to_file("kwiziq_flashcards.apkg")


if __name__ == "__main__":
    links = get_links()
    count = len(links)
    all_cards = []
    counter = 1
    for link in links:
        all_cards += get_cards(link)
        print(f"{counter}/{count} done.")
        counter += 1
    create_anki_deck(all_cards)
