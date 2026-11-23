# Instructions for the human coder

You will read about 150 news articles and record three judgements per article. This sheet
is the check on the automated index, so your honest first-read judgement is what matters.

## Time budget

- About 150 articles, about 4.5 hours in total, over two sessions on two days.
- Roughly 1.5 to 2 minutes per English article and 2 to 2.5 minutes per Hindi article.
  About 40 of the 150 are Hindi.
- Suggested split: session 1 about 75 articles (about 2.25 h), session 2 about 75 (about 2.25 h).
  Take a 5-minute break about every 45 minutes. Code in the order given in the sheet.
- Do not spend more than 4 minutes on any article. If unsure, give your best code and set `uncertain` to 1.

## The blind rule (important)

You must NOT look at any LLM codes or GDELT flags before or while coding. That includes the
key file (`audit_key_*.csv`), the LLM output files, the gate reports and the sampling script
outputs. Do not open them until all 150 are coded and the sheet is saved and handed over.
Do not try to guess the stratum, and do not search the web for the article. Work only from the
sheet and the text file in the `text_file` column. If you accidentally see any of this, write
`SAW_BLIND_INFO` in `notes` for the affected rows and tell the project lead.

## What you need

- `coding_sheet.csv` (open in a spreadsheet; keep it as CSV).
- The folder of text files named in the `text_file` column.
- `codebook.md`. Read it fully once before starting (about 20 minutes, not counted above).

## How to use the sheet

One row per article. Do not change `audit_id`, `language`, `url`, `retrieval_mode`, `text_file`.
Fill, in this order:

1. `relevance`: `Y` or `N`. Is the article about inflation or the cost of living in India?
2. `direction`: only if Y: `rising`, `falling`, `stable`, `mixed`, `none`.
3. `cause_primary`: only if Y: one code from the codebook list.
4. `cause_secondary`: optional, different from the primary; otherwise leave empty.
5. `uncertain`: `1` if you doubt any of the three above, else `0`.
6. `notes`: optional, short.
7. `coder`: your initials. `coded_at`: date and time (any clear format, e.g. 2026-11-20 14:35).

If relevance = N, leave direction and both cause columns empty. Use the exact lowercase codes
from the codebook. Save often and keep a backup copy at the end of each session.

## Unreadable, paywalled or irrelevant texts

- Empty, garbled, only a cookie notice or a login/paywall page, a video page, a list of links, or an
  error page: leave relevance and all other code columns EMPTY and write `UNREADABLE` in `notes`.
  Do not code these N. Do not go to the live site to look for the article.
- Partly readable (headline and a few lines): code it, set `uncertain` = 1, write `PARTIAL` in notes.
- Clearly not about inflation or prices (sport, crime, politics): relevance = N. Spend under 30 seconds.
- Text is from the Wayback Machine, or is approximate text rebuilt from stitched n-gram fragments (the
  first line says so): code it as normal, note `APPROX` if the text is scrambled or incomplete.
- Duplicate or near-duplicate articles: code each row separately.

## Hindi (and other non-English) articles

- Read the Hindi text directly. Do not machine-translate it unless you truly cannot follow a passage;
  if you do translate a passage, note `USED_TRANSLATION`.
- Same codebook, same codes (the codes are in English). Common cues: महंगाई (inflation), दाम/कीमत/भाव (price),
  सब्जी/दाल/तेल (vegetables/pulses/oil), पेट्रोल-डीज़ल, रसोई गैस, जीएसटी, रेपो रेट, डॉलर/रुपया.
- A Hindi article on prices abroad only is still N. Local crop or mandi price stories are Y.
- Your sheet contains English and Hindi articles only. Marathi, Bengali and other languages are coded by the LLM
  coders alone (checked LLM against LLM) unless the project lead confirms you read them. If a row in another
  language still appears, code it only if you read it fluently, else mark it UNREADABLE and tell the project lead.

## What not to do

- Do not decide by the URL words alone; read the text.
- Do not use outside knowledge of actual prices that month.
- Do not discuss the codes with anyone who has seen the LLM codes or flags until coding is finished.

## When you finish

Save the sheet, keep the filename, and send it back. Only then may you be shown the key and LLM codes.
