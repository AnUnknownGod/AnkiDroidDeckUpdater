# AnkiDroid Deck Updater

A Python program for automatically updating an AnkiDroid deck with new words.

## Description

This script allows you to automatically add new words to your AnkiDroid deck. It reads words from a file and adds them to the specified deck, simplifying the process of updating and maintaining your flashcards.

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/AnUnknownGod/AnkiDroidDeckUpdater
    cd AnkiDroidDeckUpdater
    ```

## Usage

1. Prepare a TXT file with the new words (e.g., `new_words.txt`).
2. Run the script:
    ```bash
    python main.py new_words.txt ankiwords.apkg ' - '
    ```

## Parameters

- `WORDLIST`: Path to the TXT file with new words.
- `APKG_FILE`: Path to the AnkiDroid .apkg file. You can get it from your mobile phone using Export button. 
- `DELIMITER` ( Optional ): A symbol or set of symbols that separates the original word/phrase and the translation
## License

This project is licensed under the MIT License. See the LICENSE file for details.

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
---

I hope this helps! If you need any changes or additions, feel free to let me know. 😊
