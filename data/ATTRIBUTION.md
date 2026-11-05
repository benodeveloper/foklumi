# Data attribution

Foklumi's bundled vocabulary combines hand-written learner content with open
dictionary and example-sentence data.

## Curated content

`data/curated_words.json` contains translations, explanations, and example
sentences written for Foklumi. They are not copied from the sources below
unless noted.

## Kaikki / Wiktionary

Noun and verb grammar (articles, plurals, genitives, conjugations, participles,
auxiliaries, and imperatives) is derived from Kaikki.org's German dictionary
extract, which is generated from Wiktionary.

- Source: <https://kaikki.org/dictionary/German/>
- Wiktionary: <https://en.wiktionary.org/>
- License: Creative Commons Attribution-ShareAlike 3.0 Unported
  (CC BY-SA 3.0)
- License text: <https://creativecommons.org/licenses/by-sa/3.0/>

## Tatoeba

Tatoeba is used only as a fallback source of German example sentences and
English translations for words that do not yet have a curated example.
Generated entries keep the original Tatoeba attribution in the example's
`source` field.

- Source: <https://tatoeba.org/>
- Export used: <https://www.manythings.org/anki/>
- License: Creative Commons Attribution 2.0 France (CC BY 2.0 FR)
- License text: <https://creativecommons.org/licenses/by/2.0/fr/>

## Generated file

`data/vocab.json` is generated from the sources above by
`tools/build_pipeline.py`. Do not edit it by hand; edit
`data/curated_words.json` and rebuild.
