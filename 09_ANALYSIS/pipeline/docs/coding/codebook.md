# Audit codebook (D15, D25)

Used by the human coder and, verbatim, by both LLM coders (`scripts/audit/llm_code.py`
sends this file as the system prompt). FREEZE this file before the first LLM call and before human coding
starts; `llm_code.py` records its SHA-256 in every output row. Any later edit means re-coding.

All examples below are **HYPOTHETICAL**. They were written for this codebook. They are not
real articles, not drawn from GDELT, and must not be treated as data.

## Unit and general rules

- Unit: one article (the text file for one `audit_id`). Code what the article itself says.
  Do not use outside knowledge of what really happened to prices.
- Code the article's own framing, not whether the framing is correct.
- Headline plus first half of the article carry most weight. A passing mention in one
  sentence of a long article about something else is NOT enough for relevance = Y.
- If the text is unreadable, empty, paywalled or not an article, do not code it as N.
  Leave the code fields empty and put `UNREADABLE` in `notes` (see human instructions).
- Leave `direction`, `cause_primary`, `cause_secondary` empty when relevance = N.

## Variable 1: relevance (Y / N)

Question: is the article about inflation or the cost of living in India?

Code **Y** if the main subject, or a major named subtopic, is any of:
- general price level or inflation in India (CPI, WPI, "inflation", "mehngai"/"mahagai");
- prices of everyday household goods or services in India going up or down (food, vegetables,
  cooking gas, petrol/diesel at the pump, rent, school fees, transport fares, medicines);
- household cost-of-living burden, or policy aimed at prices (RBI inflation target, price
  controls, GST rate changes justified by prices, subsidies to hold prices).

Code **N** if:
- inflation or prices abroad only, with no stated link to India (that is N, not "international cause");
- company results, stock or commodity market moves with no household-price angle;
- price of an asset only (gold, shares, crypto, real-estate investment returns) with no cost-of-living angle;
- the word "price" appears only in a different sense (price of a ticket for a match, bounty);
- sports, entertainment, crime, politics with no price content.

Edge cases:
1. India-linked world news ("global oil rises; Indian fuel prices may follow"): Y if the India
   consequence is explicit and substantive; N if India is only a one-line aside.
2. State-only story (vegetable prices in one city): Y. It is still India.
3. Wage or GDP stories: N unless inflation or prices are a stated major theme.
4. Opinion pieces and explainers on inflation: Y.
5. Market round-ups that mention "inflation data due" in a list: N.
6. A forecast or a policy meeting (RBI MPC) where inflation is the stated reason for the decision: Y.

Worked examples (HYPOTHETICAL):
- H-R1. "Tomato prices double in a week as rains hit supply, households cut back" -> Y.
- H-R2. "Sensex ends flat ahead of earnings; investors await CPI print" (market wrap, CPI one clause) -> N.
- H-R3. "US consumer prices rise 3.4% as Fed signals caution" (no India link anywhere) -> N.

## Variable 2: direction (rising / falling / stable / mixed / none)

Only if relevance = Y. Direction of prices or inflation **as described by the article** for India.

- `rising`: prices or inflation are going up, or accelerating, or described as high and worsening.
- `falling`: prices or inflation are going down, easing, cooling, or disinflation is reported.
- `stable`: described as steady, unchanged, anchored, within target without a trend.
- `mixed`: the article reports both clear rises and clear falls (for example food up, fuel down) with
  no overall winner, or a headline-rate fall alongside a rise in a main component.
- `none`: relevant (about inflation/cost of living) but no direction is stated (a pure explainer, a
  definition, a policy-design story).

Decision rules:
1. "Inflation eases to 4.9% from 5.1%" is `falling`, even though prices are still rising in level
   terms. We code the movement of the inflation rate. "Prices rise at a slower pace" -> `falling`.
2. If an article gives an overall direction and also a minor opposite item, use the overall direction.
3. If the article is mostly about the burden of high prices without movement words, use `rising` only
   if it says prices have gone up or are hurting more; otherwise `none`.
4. Use the dominant India-wide statement when national and local directions differ; if neither dominates, `mixed`.

Worked examples (HYPOTHETICAL):
- H-D1. "Retail inflation climbs to a five-month high of 6.2%" -> rising.
- H-D2. "Onion prices fall sharply after fresh arrivals; vegetables still dear" with onions the main topic -> falling.
- H-D3. "Food inflation up, but fuel prices cut by the government; overall CPI reading flat" -> mixed.

## Variable 3: cause (primary, optional secondary)

Only if relevance = Y. What does the article itself offer as the reason for the price movement or
the burden? Choose ONE primary and, if a second distinct cause is clearly given, ONE secondary.
Leave the secondary empty if none is clear. If no cause is stated, primary = `other_none`.

Fixed list (use these exact codes in the sheet):

| code | meaning | typical cues |
|---|---|---|
| `domestic_food_supply` | domestic food supply, crop, monsoon, weather, hoarding, mandi arrivals, storage | monsoon, crop damage, poor harvest, supply glut, hoarding, pulses, vegetables |
| `fuel_energy_domestic` | domestic fuel and energy pricing or supply, NOT involving a tax or duty: pump-price revisions by oil marketing companies, LPG cylinder price revisions, power tariffs, fuel shortages | oil marketing companies raise petrol price, electricity tariff, LPG shortage |
| `global_oil_commodities` | global crude oil, edible oil, metals, fertiliser or other international commodity prices | Brent, crude, global edible oil prices, import costs of commodities |
| `exchange_rate` | rupee depreciation or appreciation | weak rupee, imports costlier because of rupee |
| `monetary_policy` | RBI/domestic monetary policy: repo rate, liquidity, interest rates | repo rate cut or hike, loose liquidity |
| `fiscal_tax_administered` | ANY tax or duty (GST, excise, VAT, import duty, cess), subsidies, MSP, administered or regulated prices, government spending | GST rate, excise duty cut on petrol, import duty on edible oil, MSP raise, subsidy cut |
| `wages_demand` | wages, incomes, consumer demand, demand-pull | strong demand, wage growth, festive demand |
| `corporate_pricing` | firms raising prices, margins, pass-through, cartels | companies hike prices, FMCG pass-through, input cost pass-through by a named firm |
| `international_inflation_abroad` | inflation, supply chain or policy abroad transmitted to India, wars or global shocks not tied to one commodity above | global inflation, war disruption, shipping disruption, foreign central bank tightening |
| `other_none` | another cause, or no cause stated | |

Decision rules:
1. Code what the article blames, using its own words. Prefer the most specific code: a rupee fall
   that raises import costs is `exchange_rate`; crude prices -> `global_oil_commodities`.
   Precedence rules for overlaps (apply in this order):
   a. Any tax or duty is `fiscal_tax_administered`, including excise or VAT on petrol/diesel and import
      duty on edible oil. A pump-price change explained by a tax change is therefore fiscal.
   b. MSP and other administered prices are `fiscal_tax_administered`, even in a food story.
   c. A pump-price or LPG revision by oil companies WITHOUT a tax: `global_oil_commodities` if the article
      gives crude/global prices as the reason, otherwise `fuel_energy_domestic`.
   d. Hoarding or stockpiling by traders is `domestic_food_supply`, unless the article names a firm or a
      cartel/collusion, then `corporate_pricing`.
   e. A global commodity price (palm oil, wheat, fertiliser) is `global_oil_commodities` even when the
      article also mentions the rupee; the rupee goes in the secondary slot.
2. Primary = the cause given first and most weight. Tie -> the one in the headline.
3. A foreign central bank (Fed, ECB) is `international_inflation_abroad` unless the article
   explicitly runs it through the rupee, in which case primary = `exchange_rate`.
4. Do not infer a cause the article does not state. Descriptive "prices rose" with no why -> `other_none`.
5. Primary and secondary must differ. Secondary is optional and is never used to derive the binary below.
6. The government blaming "global factors" counts only if the article reports it as the stated cause; if
   it is reported as a disputed claim, code the cause the article itself leans to, else `other_none` and tick `uncertain`.

### Derived binary: international_imported (do not enter in the sheet)

Computed by script from `cause_primary` (D25 fix, mapping fixed at Gate 2):
`international_imported = 1` if cause_primary is in {`global_oil_commodities`, `exchange_rate`,
`international_inflation_abroad`}; `= 0` for every other primary code including `other_none`;
missing if relevance = N or cause_primary is empty. Secondary causes never enter this binary.

Worked examples (HYPOTHETICAL):
- H-C1. "Monsoon failure pushes pulses prices up; traders accused of hoarding" -> primary `domestic_food_supply`,
  secondary empty (hoarding is part of the supply story). international_imported = 0.
- H-C2. "Cooking oil costlier as global palm oil prices jump and rupee slips" -> primary `global_oil_commodities`,
  secondary `exchange_rate`. international_imported = 1.
- H-C3. "GST on packaged foods raises household bills; opposition protests" -> primary `fiscal_tax_administered`,
  secondary empty. international_imported = 0.
- H-C4. "Inflation hurts middle-class budgets" (no reasons given) -> `other_none`. international_imported = 0.

## Variable 4: uncertain (0 / 1)

Set 1 if you are unsure of ANY of relevance, direction or cause after one careful reading: ambiguous
text, truncated text, mixed languages, conflicting cues. You must still enter your best code.
Leave 0 otherwise. Do not use `uncertain` for unreadable texts (use `UNREADABLE` in notes).

Worked examples (HYPOTHETICAL):
- H-U1. Text cuts off after the headline and one sentence about "rising prices" -> relevance Y, direction rising, cause `other_none`, uncertain = 1.
- H-U2. Clear article on petrol price hike due to global crude -> uncertain = 0.

## Variable 5: notes (free text)

Optional. One short line on anything odd. Keep out of notes any guess about what a GDELT flag or an LLM
would say (coders never see those).

## Allowed values (machine-checked)

- relevance: `Y`, `N`
- direction: `rising`, `falling`, `stable`, `mixed`, `none` (empty when relevance = N)
- cause_primary / cause_secondary: `domestic_food_supply`, `fuel_energy_domestic`, `global_oil_commodities`,
  `exchange_rate`, `monetary_policy`, `fiscal_tax_administered`, `wages_demand`, `corporate_pricing`,
  `international_inflation_abroad`, `other_none` (secondary may also be empty; both empty when relevance = N)
- uncertain: `0`, `1`

Anything else is treated as missing by the metrics script. It is never repaired or guessed.
