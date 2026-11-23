# GCAM dimension IDs for D6 (WordNet-Affect, Loughran-McDonald)

Status: read on 17 Nov 2026 from the GCAM master codebook,
http://data.gdeltproject.org/documentation/GCAM-MASTER-CODEBOOK.TXT
(tab-separated; header `Variable DictionaryID DimensionID Type LanguageCode DictionaryHumanName DimensionHumanName DictionaryCitation`).
The workspace could not download the file directly. It was read in chunks through a web-fetch tool that summarises
pages, so every ID below is **[UNVERIFIED until gcam_pilot.py regenerates this file from the codebook itself]**.
`gcam_pilot.py` overwrites this file with a table extracted from the downloaded codebook.

In the GKG `GCAM` field, `cX.Y` is the word count for dimension Y of dictionary X; `vX.Y` is the
scored value for dictionaries that have one.

## Loughran and McDonald Financial Sentiment Dictionaries (dictionary 6)

| Variable | Dimension | Status |
|---|---|---|
| c6.1 | Litigious | seen in codebook chunk [UNVERIFIED] |
| c6.2 | ModalStrong | seen [UNVERIFIED] |
| c6.3 | ModalWeak | seen [UNVERIFIED] |
| c6.4 | Negative | seen [UNVERIFIED] |
| c6.5 | Positive | seen [UNVERIFIED] |
| c6.6 | Uncertainty | seen [UNVERIFIED] |

## WordNet Affect

Two dictionaries exist in the codebook:

* **WordNet Affect 1.0 (dictionary 14)**, 11 broad categories: c14.1 Attitude, c14.2 Behaviour, c14.3 Cognitive State,
  c14.4 Edonic Signal, c14.5 Emotion, c14.6 Mood, c14.7 Physical State, c14.8 Emotional Response, c14.9 Sensation,
  c14.10 Emotion-Eliciting Situation, c14.11 Trait. [UNVERIFIED]
* **WordNet Affect 1.1 (dictionary 15)**, 280 fine emotion labels, c15.1 (abashment) to c15.280 (wrath), lower-case names. [UNVERIFIED]

Selected WordNet Affect 1.1 emotions likely to matter for inflation news (IDs as reported by the summariser; verify):

| Variable | Emotion | | Variable | Emotion |
|---|---|---|---|---|
| c15.15 | anger | | c15.148 | hopelessness |
| c15.22 | anxiety | | c15.167 | joy |
| c15.25 | apprehension | | c15.176 | love |
| c15.72 | despair | | c15.187 | misery |
| c15.81 | disgust | | c15.198 | negative-fear |
| c15.86 | distress | | c15.204 | panic |
| c15.122 | frustration | | c15.212 | positive-hope |
| c15.128 | gloom | | c15.227 | sadness |
| c15.137 | happiness | | c15.241 | shame |
| | | | c15.254 | surprise |
| | | | c15.268 | unrest |

Not found as exact labels in dictionary 15: "fear", "hope", "worry", "dread", "alarm", "uneasiness", "ire"
(near matches: negative-fear c15.198, fear-intimidation c15.111, despair-intimidation c15.73).

Which emotions to use is a D12 decision: take them from base paper 1 (Consoli, Tiozzo Pezzoli & Tosetti 2021),
whose appendix lists WordNet-Affect labels by name (e.g. abashment, abhorrence, admiration, wrath) without GCAM codes,
and map the names to IDs with `data/processed/gcam_ids.csv`.

Other dictionaries seen in the codebook, for orientation only: 1 Forest Values, 2 General Inquirer, 3 Lexicoder Sentiment,
4 Lexicoder Topic, 5 LIWC, 9 Roget's 1911, 10 SentiWordNet 3.0, 11 SentiWords, 12 Subjectivity Lexicon,
13 Body Boundary, 16 WordNet Domains 3.2, 17 WordNet 3.1 Lexical Categories, 18 GDELT GKG Themes, 19 ANEW,
20 ML-SENTICON (English), 21 Hedonometer (English), 25 Moral Foundations, 26 VADER.
