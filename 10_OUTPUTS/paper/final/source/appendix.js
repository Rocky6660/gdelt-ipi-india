const rounds = `2016-03|2016-03-01|Month rule|—|Yes
2016-06|2016-06-01|Month rule|—|Yes
2016-09|2016-09-01|Month rule|—|Yes
2016-11|2016-11-01|Month rule|—|Yes
2016-12|2016-12-01|Month rule|—|Yes
2017-03|2017-03-01|Month rule|—|Yes
2017-05|2017-05-01|Month rule|—|Yes
2017-06|2017-06-01|Month rule|—|Yes
2017-09|2017-09-01|Month rule|—|Yes
2017-11|2017-11-01|Month rule|—|Yes
2017-12|2017-12-01|Month rule|—|Yes
2018-03|2018-03-01|Month rule|—|Yes
2018-05|2018-05-01|Month rule|—|Yes
2018-06|2018-06-01|Month rule|—|Yes
2018-09|2018-09-01|Month rule|—|Yes
2018-11|2018-11-01|Month rule|—|Yes
2018-12|2018-12-01|Month rule|—|Yes
2019-03|2019-03-01|Month rule|—|Yes
2019-05|2019-05-01|Month rule|—|Yes
2019-07|2019-07-01|Month rule|—|Yes
2019-09|2019-09-01|Month rule|—|Yes
2019-11|2019-11-01|Month rule|—|Yes
2020-01|2020-01-01|Month rule|—|Yes
2020-03|2020-02-27|Exact|—|Yes
2020-05|2020-05-05|Exact|Telephone|Yes
2020-07|2020-07-01|Month rule|—|Yes
2020-09|2020-09-01|Month rule|—|Yes
2020-11|2020-11-01|Month rule|—|Yes
2021-01|2021-01-02|Exact|Telephone|Yes
2021-03|2021-02-27|Exact|—|Yes
2021-05|2021-04-29|Exact|Telephone|Yes
2021-07|2021-06-28|Exact|Telephone|Yes
2021-09|2021-08-29|Exact|Telephone|Yes
2021-11|2021-10-25|Exact|Telephone|Yes
2022-01|2022-01-02|Exact|—|Yes
2022-03|2022-03-02|Exact|—|Yes
2022-05|2022-05-02|Exact|—|Yes
2022-07|2022-07-07|Exact|—|Yes
2022-09|2022-09-01|Exact|—|Yes
2022-11|2022-11-02|Exact|—|Yes
2023-01|2023-01-02|Exact|—|Yes
2023-03|2023-03-02|Exact|—|Yes
2023-05|2023-05-02|Exact|—|Yes
2023-07|2023-07-01|Exact|—|Yes
2023-09|2023-09-02|Exact|—|Yes
2023-11|2023-11-02|Exact|—|Yes
2024-01|2024-01-02|Exact|—|Yes
2024-03|2024-03-02|Exact|—|Yes
2024-05|2024-05-02|Exact|—|Yes
2024-07|2024-07-02|Exact|—|Yes
2024-09|2024-09-01|Exact|—|Yes
2024-11|2024-11-02|Exact|—|Yes
2025-01|2025-01-02|Exact|—|Yes
2025-03|2025-03-01|Exact|—|Yes
2025-05|2025-05-02|Exact|—|Yes
2025-07|2025-07-01|Exact|—|No (GDELT outage)
2025-09|2025-08-28|Exact|—|Yes
2025-11|2025-11-01|Exact|—|Yes
2026-01|2026-01-02|Exact|—|Yes
2026-03|2026-02-25|Exact|—|Yes
2026-05|2026-05-02|Exact|—|Yes
2026-07|2026-07-11|Exact|—|Yes
2026-09|2026-09-10|Exact|—|Yes`.split("\n").map(r=>r.split("|"));

const e3 = [["CPI surprise","0.054","0.060","0.123","0.094","0.012","0.091","0.058","0.091","0.140","0.102"],["Brent (1%)","0.016","0.011","0.020","0.011","0.020","0.013","0.013","0.008","0.009","0.006"]];

module.exports = [
["h1","Appendix A"],
["h2","A.1 Theme Codes by Definition"],
["table","Table A1. GDELT theme codes by definition",["Definition","Codes"],[["Baseline","ECON_INFLATION"],["World Bank","WB_442_INFLATION"],["Strict","ECON_INFLATION and WB_442_INFLATION"],["Price family","ECON_INFLATION; WB_442_INFLATION; ECON_COST_OF_LIVING; ECON_PRICECONTROL; WB_2107_PRICE_CONTROLS; ECON_PRICEGOUGE; ECON_PRICEMANIPULATION; FUELPRICES; ECON_OILPRICE; ECON_GASOLINEPRICE; ECON_DIESELPRICE; ECON_ELECTRICALPRICE; ECON_NATGASPRICE; ECON_TRANSPORT_COST; WB_1623_PRICE_SUBSIDIES"]],"All definitions were fixed in the analysis plan before the audit. Theme families used in the extensions (international framing, item attention) are defined in the replication repository."],
["h1","Appendix B"],
["h2","B.1 Core Outlets"],
["p","The panel contains 714 Indian domains. The 104 core outlets present in at least 80% of the survey windows are listed below by language."],
["table","Table B1. Core outlets by language",["Language","Outlets"],[
["English (50)","aninews.in, auto.economictimes.indiatimes.com, bangaloremirror.indiatimes.com, bollywoodhungama.com, business-standard.com, businessinsider.in, businesstoday.in, businessworld.in, calcuttanews.net, campaignindia.in, chennaionline.com, deccanchronicle.com, deccanherald.com, desimartini.com, digit.in, dnaindia.com, downtoearth.org.in, economictimes.indiatimes.com, energy.economictimes.indiatimes.com, epw.in, femina.in, food.ndtv.com, freepressjournal.in, ibtimes.co.in, indiaeducationdiary.in, indiatimes.com, jagranjosh.com, livemint.com, moneycontrol.com, moneylife.in, navhindtimes.in, ndtv.com, printweek.in, prokerala.com, realty.economictimes.indiatimes.com, retail.economictimes.indiatimes.com, scroll.in, siasat.com, skymetweather.com, telecom.economictimes.indiatimes.com, thecitizen.in, thehindu.com, thehindubusinessline.com, theindianawaaz.com, themobileindian.com, timesofindia.indiatimes.com, tribuneindia.com, twocircles.net, vogue.in, zeenews.india.com"],
["Hindi (23)","aajsamaaj.com, agrasamachar.com, amarujala.com, bhaskar.com, bollywoodtadka.in, dainiktribuneonline.com, forwardpress.in, haribhoomi.com, haryana.punjabkesari.in, hindi.moneycontrol.com, hindi.webdunia.com, jagran.com, khabarfast.com, livehindustan.com, loktej.com, navbharattimes.indiatimes.com, nayaindia.com, newstracklive.com, patrika.com, prabhatkhabar.com, punjabkesari.in, samacharjagat.com, samaylive.com"],
["Tamil (9)","cinema.dinamalar.com, cinema.vikatan.com, dailythanthi.com, dinamalar.com, dinamani.com, maalaimalar.com, temple.dinamalar.com, thinaboomi.com, vikatan.com"],
["Malayalam (6)","evartha.in, janayugomonline.com, mathrubhumi.com, puzha.com, sirajlive.com, thejasnews.com"],
["Telugu (4)","eenadu.net, janamsakshi.org, prabhanews.com, sakshi.com"],
["Kannada (3)","kannadaprabha.com, prajavani.net, sanjevani.com"],
["Marathi (3)","divyamarathi.bhaskar.com, lokmat.com, prahaar.in"],
["Punjabi (3)","jagbani.punjabkesari.in, punjabitribuneonline.com, quamiekta.com"],
["Gujarati (2)","divyabhaskar.co.in, nobat.com"],
["Bengali (1)","anandabazar.com"]],""],
["h1","Appendix C"],
["h2","C.1 Survey Rounds"],
["table","Table C1. Survey rounds: fieldwork start, dating rule, mode and window validity",["Round","Fieldwork start","Date rule","Mode","Valid window"],rounds,"\"Month rule\": fieldwork start set to the first day of the survey month because exact dates are not published. Mode is shown where the survey documents identify a telephone round; \"—\" means not stated."],
["h1","Appendix D"],
["h2","D.1 Retrieval by Stratum and Period"],
["table","Table D1. Retrieval by stratum and period",["Stratum","Period","Sampled","Retrieved","Rate"],[
["English, economic, untagged","2019 onwards","143","132","0.92"],["English, economic, untagged","2015–18","157","134","0.85"],
["English, tagged","2019 onwards","177","165","0.93"],["English, tagged","2015–18","123","91","0.74"],
["Hindi/Marathi, economic, untagged","2019 onwards","54","51","0.94"],["Hindi/Marathi, economic, untagged","2015–18","46","39","0.85"],
["Hindi/Marathi, tagged","2019 onwards","68","65","0.96"],["Hindi/Marathi, tagged","2015–18","32","26","0.81"],
["Non-economic, other","2019 onwards","41","39","0.95"],["Non-economic, other","2015–18","59","48","0.81"],
["Non-economic, price word in address","2019 onwards","80","76","0.95"],["Non-economic, price word in address","2015–18","70","66","0.94"],
["Other Indian languages, economic, untagged","2019 onwards","62","59","0.95"],["Other Indian languages, economic, untagged","2015–18","38","31","0.82"],
["Other Indian languages, tagged","2019 onwards","66","65","0.99"],["Other Indian languages, tagged","2015–18","34","26","0.76"]],""],
["h2","D.2 Weights and Estimation"],
["p","Design weights are post-stratified within stratum-by-period cells (2015–18 and 2019 onwards) to each cell's full sampled weight over the coded articles. Unretrieved or uncoded articles are not imputed; they re-weight the remaining articles in their cell, which assumes that retrieval is unrelated to relevance within a cell. Precision and recall are ratios of weighted totals, and confidence intervals come from 1,000 bootstrap draws resampling within cells. Recall in the gating frame excludes the unscreened non-economic stratum, which is used only for the bound reported in Section 4.1.3."],
["h2","D.3 Codebook Summary"],
["p","Relevance is coded Yes if the article substantially discusses price levels, inflation or the cost of living affecting consumers in India; passing mentions, asset prices, single-product launch prices, and foreign inflation without an Indian angle are coded No. Direction is coded as rising, falling, mixed or none. Cause is coded in nine categories plus other or none, for a primary and a secondary cause. An uncertainty flag is set when the coder was unsure. The codebook text was fixed, and its hash recorded, before coding began."],
["h1","Appendix E"],
["h2","E.1 Construction Variants"],
["table","Table E1. Construction variants in the primary specification (one-year median, h = 0)",["Construction","N","Coefficient","95% CI","p"],[
["Word share","56","0.261","(−0.014, 0.537)","0.066"],["Pooled ratio","56","0.333","(0.113, 0.554)","0.020"],["Share among economic articles","56","0.328","(0.027, 0.628)","0.029"],["Wire-copy filter","56","0.325","(0.009, 0.641)","0.037"],["Strict definition","56","0.324","(0.015, 0.633)","0.034"],["Price family","56","0.251","(0.068, 0.434)","0.058"],["World Bank theme","56","0.324","(0.015, 0.633)","0.044"],["2018 core including additional vernacular outlets","47","0.282","(−0.015, 0.579)","0.072"]],"Variants of the baseline index unless stated. EWC fixed-b intervals; wild-bootstrap p-values."],
["h2","E.2 State Dependence"],
["table","Table E2. State dependence, including leave-one-episode-out (price family)",["Specification","N","Coefficient","95% CI","p"],[
["Index × High","56","0.179","(0.057, 0.301)","0.016"],["Index × (CPI − 4)","56","0.121","(0.025, 0.216)","0.062"],["Index × High, excluding 2020–21","46","0.038","(−0.256, 0.332)","0.776"],
["Leave out high-inflation episode 1","55","0.184","(0.068, 0.299)","—"],["Leave out high-inflation episode 2","55","0.180","(0.060, 0.299)","—"],["Leave out high-inflation episode 3","52","0.274","(−0.246, 0.793)","—"],["Leave out high-inflation episode 4","55","0.157","(−0.011, 0.325)","—"],["Leave out high-inflation episode 5","51","0.211","(−0.063, 0.484)","—"],["Leave out high-inflation episode 6","55","0.180","(0.059, 0.300)","—"],["Leave out high-inflation episode 7","55","0.182","(0.058, 0.307)","—"]],"\"High\" indicates lagged CPI inflation above 6%. Bootstrap p-values were not computed for the leave-one-out rows (\"—\")."],
["h2","E.3 Monthly Responses of Attention to Price Shocks"],
["table","Table E3. Monthly local projections of the standardised index on price shocks (price family)",["Months after shock","CPI surprise (1 pp)","s.e.","Brent (1%)","s.e."],[
["0","0.054","0.060","0.016","0.011"],["1","0.123","0.094","0.020","0.011"],["2","0.012","0.091","0.020","0.013"],["3","0.058","0.091","0.013","0.008"],["4","0.140","0.102","0.009","0.006"],["5","0.074","0.163","0.006","0.006"],["6","0.055","0.174","0.011","0.007"],["7","−0.041","0.136","0.009","0.004"],["8","0.015","0.141","0.010","0.004"],["9","−0.002","0.131","0.013","0.004"],["10","0.111","0.108","−0.001","0.006"],["11","0.032","0.144","−0.008","0.008"],["12","−0.040","0.215","−0.001","0.007"]],"Responses in standard deviations of the monthly index per one-point CPI surprise (relative to a recursive autoregressive forecast) or per one per cent change in Brent; EWC standard errors. N = 103–106 for CPI surprises and 114–127 for Brent."],
["h2","E.4 Outlet Composition"],
["table","Table E4. Core outlets contributing to each valid window, by year",["Year","Windows","Min","Median","Max"],[["2016","5","92","99","101"],["2017","6","97","98","101"],["2018","6","97","98","100"],["2019","5","101","103","103"],["2020","6","99","100","101"],["2021","6","91","96","103"],["2022","6","91","92","93"],["2023","6","86","102.5","103"],["2024","6","96","97.5","101"],["2025","5","91","94","95"],["2026","5","84","88","92"],["All","62","84","97.5","103"]],"An outlet contributes to a window if it published at least 10 distinct articles on valid days in that window."],
["h1","Appendix F"],
["h2","F.1 Extension Regressions"],
["table","Table F1. Extension regressions (descriptive)",["Definition","Regression","N","Coefficient","95% CI","p"],[
["Baseline, 2018 core","English index alone (one-year median)","56","0.259","(0.015, 0.503)","0.043"],["Baseline, 2018 core","Indian-language index alone (one-year median)","56","0.264","(0.027, 0.501)","0.036"],["Baseline, 2018 core","Indian-language index with English control","56","0.206","(−0.048, 0.460)","0.090"],
["Baseline, 2018 core","English index alone (current perception)","56","0.157","(0.012, 0.303)","0.108"],["Baseline, 2018 core","Indian-language index alone (current perception)","56","0.131","(−0.041, 0.302)","0.133"],["Baseline, 2018 core","Indian-language with English control (current perception)","56","0.083","(−0.086, 0.252)","0.306"],
["Price family","International share alongside index","56","−0.053","(−0.285, 0.179)","0.670"],["Price family","Index with international-share control","56","0.262","(0.080, 0.443)","0.033"],["Price family","Excess attention during disinflation","56","0.291","(−0.027, 0.610)","0.185"],["Price family","Index with excess-attention control","56","0.154","(0.040, 0.268)","0.056"],
["Baseline","International share alongside index","56","0.002","(−0.208, 0.211)","0.989"],["Baseline","Index with international-share control","56","0.328","(0.014, 0.642)","0.044"],["Baseline","Excess attention during disinflation","56","0.258","(−0.162, 0.678)","0.247"],["Baseline","Index with excess-attention control","56","0.213","(−0.129, 0.556)","0.117"]],"Reported for completeness; the international-framing regressions are not interpreted because the audit agreement condition was not met. The English and Indian-language series use the baseline tag and the 2018 core (99 outlets)."],
["h2","F.2 Salience-Weighted Inflation"],
["table","Table F2. Salience-weighted inflation: horse race with published CPI (outcome: change in current perceived inflation, median; search-implied version)",["Regression","N","Coefficient","95% CI","p"],[
["Salience-weighted median, horse race","54","−0.006","(−0.019, 0.007)","0.429"],["Published CPI, horse race","54","0.102","(−0.075, 0.279)","0.267"],["Absolute salience-weighted measure, horse race","54","−0.002","(−0.008, 0.005)","0.573"],["Salience-weighted median alone","54","−0.008","(−0.014, −0.003)","0.040"]],"The salience-weighted median and published CPI inflation correlate at −0.12 (N = 55). Trends-based measures rest on one pull."],
["h2","F.3 Lead–Lag Correlations"],
["table","Table F3. Correlation of Indian-language and English monthly attention at leads and lags",["Lag (months)","Correlation","N","Lag (months)","Correlation","N"],[
["−6","0.632","99","1","0.752","104"],["−5","0.677","100","2","0.716","103"],["−4","0.700","101","3","0.671","102"],["−3","0.739","102","4","0.633","101"],["−2","0.780","103","5","0.578","100"],["−1","0.797","104","6","0.499","99"],["0","0.905","105","",""," "]],"A positive lag means the Indian-language series moves later. N is 105 rather than 129 because the language series use the 2018 core and start in January 2018; N falls by one per month of lead or lag."],
["h2","F.4 Attention Peaks under the Baseline Tag"],
["table","Table F4. Peaks in monthly attention (baseline tag)",["Peak","Peak (%)","Prior 12-month level (%)","Months of rise","Half-life (months)"],[["Jun 2022","3.12","0.98","4","9"],["Mar 2025","1.64","1.31","5","2"],["Apr 2026","2.76","1.06","3","—"]],"Computed on the 3-month centred moving average of the monthly baseline series. The half-life for April 2026 is right-censored: the series had not fallen back to the half-way level by the end of the sample (\"—\")."],
];
