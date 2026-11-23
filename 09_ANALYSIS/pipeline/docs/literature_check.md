# D32 literature check (web, 17 Nov 2026)

Rule: only what was confirmed from the source page or PDF in this session is recorded. Content descriptions come
from reading the paper or its official abstract page through a web-fetch tool that summarises, so short quotes
are exact but descriptions are paraphrase. Nothing here was taken from memory.

## 1. MPRA 118951 (Kishor & Pratap): resolved

- **Confirmed:** N. Kundan Kishor (Univ. of Wisconsin-Milwaukee) and Bhanu Pratap (RBI), *"The Role of Inflation
  Targeting in Anchoring Long-Run Inflation Expectations: Evidence from India"*, MPRA Paper No. 118951,
  dated 23 Oct 2023 (posted 27 Oct 2023). https://mpra.ub.uni-muenchen.de/118951/1/MPRA_paper_118951.pdf
- **What it does:** builds a daily inflation-sentiment series from five English business dailies (Hindu
  BusinessLine, Economic Times, Financial Express, Mint, Business Standard), Jan 2010 to Dec 2021, using the
  Loughran-McDonald lexicon with valence-shifting bigrams at sentence level. It splits Consensus Economics
  forecasters' one-year-ahead CPI forecasts into trend and cycle with an unobserved-components model, then runs
  state-dependent local projections split at Oct 2016 (first MPC). Before 2016, long-run expectations respond to
  inflation sentiment (peak about 16-18 months); after 2016 they do not, which the authors read as anchoring.
  Robustness: 10-year G-sec yields and RBI's SPF. **No household survey.**
- **D32 dispute settled:** both labels are right. The paper is by Kishor & Pratap and is about inflation targeting
  and anchoring; the news-sentiment index is an input, not the paper's main object. D33 should cite it as
  "news sentiment from five English business dailies, dictionary method, professional forecasters' expectations".

## 2. "Forecasting Food Inflation using News-based Sentiment Indicators": confirmed, but NOT an RBI Bulletin article

- **Confirmed:** Bhanu Pratap, Abhishek Ranjan, Vimal Kishore, Binod B. Bhoi (DEPR, RBI). Published in **RBI
  Occasional Papers, Vol. 42, No. 2** (listed under the 2021 volume; received 1 Jun 2022, accepted 13 Jul 2022).
  https://rbi.org.in/Scripts/bs_viewcontent.aspx?Id=4198 ;
  PDF: https://website.rbi.org.in/documents/87730/30842423/OP42181020223b0bfc4e175d4bd6a8769ec7fee40979.pdf
- **What it does:** articles on tomatoes, onions and potatoes from nine English national dailies (Jan 2011 to Aug
  2021), Loughran-McDonald lexicon at sentence level; DoCA daily prices (167 centres); vegetable and food CPI.
  Sentiment Granger-causes TOP prices; adding it improves vegetable (m/m) forecasts; mixed for food and beverages.
- **Fix for D32:** cite as RBI Occasional Papers 42(2), not "RBI Bulletin (2022)". Outcome is CPI, not households.

## 3. IIM Calcutta WPS 830: confirmed; it DOES compare with the IESH

- **Confirmed:** Ashok Banerjee, Ayush Kanodia, Partha Ray, *"Deciphering Indian Inflationary Expectations through
  Text Mining: An Exploratory Approach"*, IIM Calcutta Working Paper No. 830, July 2019.
  https://studentlive.iimcal.ac.in/sites/all/files/pdfs/wps_830.pdf . The IIMC repository lists a version in
  *Indian Economic Review* vol. 56, pp. 49-66 (2021): https://ir.iimcal.ac.in:8443/jspui/handle/123456789/4918
- **What it does:** Economic Times and Business Line articles from Factiva (about 3,000 a month); Naive Bayes
  classification into CPI baskets (food, fuel, clothing, housing, etc.), rule-based price/production sentiment with
  negation handling; monthly basket sentiment predicts next-month CPI inflation (y/y). Reports a correlation of
  0.70 between predicted and actual inflation, against 0.50 for the IESH.
- **Consequence for D33:** the claim "no household survey" must be softened for this paper: it uses the IESH as a
  benchmark forecaster of CPI (not as the outcome to explain). Our distinct element is the IESH as the outcome
  (perception/expectation responses to news), not the mere presence of the IESH.

## 4. Ruhi, Sharma & Sankaran, RBI Bulletin July 2025: confirmed, quote verified

- **Confirmed:** Ankit Ruhi, Kanupriya Sharma, Subhadhra Sankaran, *"Household Inflation Expectations in India:
  Emerging Trends, Determinants and Impact of Monetary Policy"*, RBI Bulletin, 23 Jul 2025.
  https://rbi.org.in/scripts/BS_ViewBulletin.aspx?Id=23518
- **The D32 claim is supported.** Footnote 26: "The IESH does not capture information on households' awareness
  about the Reserve Bank, its monetary policy functioning or exposure to media and social interactions related to
  policy or inflation dynamics." (read as two fragments by the fetch tool; check the punctuation in the PDF before quoting.)
- **Useful facts for D7 (same article):** about 6,000 households in 19 cities; bi-monthly since 2016 (quarterly
  before); respondents choose from "0-1 per cent" to "15-16 per cent" in increments of 100 basis points, "greater
  than (or equal to) 16 per cent", or "No Idea"; two-stage random sampling since 2018; the paper uses unit-level
  IESH data. So the **bin step for the median is 1 percentage point**.

## 5. ECB 2025, attention to inflation: confirmed

- Ilias Aarab, Marta Bańbura, Elena Bobeica, Emma Leguay, *"Monitoring attention to inflation in the news"*, ECB
  Economic Bulletin, Issue 6/2025 (box).
  https://www.ecb.europa.eu/press/economic-bulletin/focus/2025/html/ecb.ebbox202506_05~b5c5ed8127.da.html
- Daily index = share of articles with inflation keywords (adapted from Baker et al. 2016) in general-interest
  newspapers of France, Germany, Italy, Spain (Factiva, >3 million articles); finds attention tracks consumers'
  perceived past inflation and short-term expectations, and stayed elevated after inflation fell; food attention
  still high in 2025.

## 6. Arndt 2024 / 2026: confirmed (2024 WP; 2026 = seminar version; 2025 dissertation)

- Sarah Arndt, *"Different Newspapers – Different Inflation Perceptions"*, Heidelberg University Dept. of
  Economics Working Paper No. 748, 25 Jun 2024. https://econpapers.repec.org/RePEc:awi:wpaper:0748 .
  German newspapers, GPT-3.5 sentiment; tabloid indicator predicts perceived inflation of lower-income /
  lower-education households, reputable papers predict higher-income / more-educated households; monetary policy
  shocks move tabloid sentiment at once, reputable papers later and less.
- 2026 version: *"Different Newspapers – Different Expectations"*, seminar slides/paper dated 22 Jan 2026
  (Bild, FAZ, SZ; ~45,000 articles, Jan 2014 to Aug 2023; EC consumer survey; readers matched by education).
  https://www.wiwi.uni-wuerzburg.de/fileadmin/12010109/2026/Different_Newspapers_Different_Expectations_Arndt.pdf
- Related: Arndt's Heidelberg dissertation (2025), *"Essays on Inflation and Inflation Expectations: The Role of
  Media and Regime-Dependence"* https://archiv.ub.uni-heidelberg.de/volltextserver/37464 ; and Arndt & Tohme,
  *"Fiscal Narratives and Inflation"* (draft 25 Nov 2025, ECB conference Mar 2026)
  https://www.ecb.europa.eu/press/conferences/shared/pdf/20260323_forecasting/Arndt_poster_paper.pdf
- Not confirmed: any journal publication of the newspaper paper. "Arndt 2026" in D32 should cite the Jan 2026 version as a working paper.

## 7. Heddaya et al. 2025: two papers; the relevant one confirmed

- Mourad Heddaya, Chenhao Tan, Rob Voigt, Qingcheng Zeng, Alexander Zentefis, *"A Century of Inflation
  Narratives"*, Northwestern IPR Working Paper WP-25-23 (2025); also SSRN 5259107.
  https://www.ipr.northwestern.edu/our-work/working-papers/2025/wp-25-23.html
  US newspapers since 1923, 4.2 million sentences; narrative prevalence shifts by era and region; narrative framing
  predicts differences in short- and long-term expectations across income and education groups; lower-income
  households more sensitive to cost-of-living narratives.
- Companion method paper: Heddaya, Zeng, Tan, Voigt, Zentefis, *"Causal Micro-Narratives"*, arXiv 2410.05252
  (venue not confirmed). https://arxiv.org/abs/2410.05252 . Ontology of 8 causes and 11 effects of inflation;
  fine-tuned Llama 3.1 8B beats GPT-4o few-shot.

## Implications for D33 wording (for the proposer; not decided here)

1. Closest Indian precedents (Kishor & Pratap 2023; Pratap et al. OP 42(2); Banerjee-Kanodia-Ray WPS 830) all use
   2-9 **English** business/national dailies and dictionary or rule-based sentiment, with CPI or professional
   forecasters as outcome. None uses vernacular press, GDELT, or the IESH as the **dependent variable**.
2. WPS 830 benchmarks against the IESH, so "no household survey" is inaccurate for it; use "household survey not
   used as the outcome".
3. The RBI's own July 2025 article states the IESH has no media-exposure information (footnote 26): that is the gap
   the index fills, quotable after checking the PDF punctuation.
