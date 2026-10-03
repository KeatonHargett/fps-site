# All-time records audit — program_stats.json

Audit date: 2026-10-02 · Branch: `audit/all-time-records` (from `fix/rank-all-time-wins`, PR #12) · **Report only — no data changed.**
`front_porch_games.json` was not modified (SHA-256 `adbcadc3f6662d790f9251602e1669b5256a0fc1bc80b7bd85e94f53c0410118`).

## 1. Headline

- `program_stats.json` all-time records are **frozen at the end of the 2025 season** (no 2026 games), are **not reproducible** (no generator script in the repo; added as a static file in the initial commit 2026-06-11; best partial match is "CFBD games in seasons where the team is FBS-classified", 30/136 exact), and **undercount 126 of 136 programs by more than 5 wins** against NCAA official totals.
- Michigan is shown with 954 wins; the NCAA official total through 2025 is **1,021** (1,024 with 2026 games). Alabama's 999 is neither its official total (985) nor its on-field total (1,014).
- Causes: missing early seasons (72 programs, primary), FCS/lower-division-era games excluded (46), vacated/forfeited wins counted as wins (5 primary, 50 affected), frozen snapshot drift from current CFBD (8 primary).
- Every other field was spot-checked too (section 6): conference titles, consensus All-Americans, NFL draft picks and bowl counts have real errors; Heisman and claimed national titles are mostly right; Ohio St.'s claimed titles miss 2024; Oklahoma St.'s recognized titles show 0 where the NCAA lists 1945.

## 2. Baselines: how each source treats vacated wins and forfeits

| Source | Vacated wins | NCAA-ordered forfeits | As of |
|---|---|---|---|
| Wikipedia "NCAA Division I FBS football win–loss records" | **Excluded** (official) — lead: "This list takes into account results modified later due to NCAA action, such as vacated victories and forfeits" | **Applied** | Current revision 1376851742 is mixed: 125 rows updated part-way through 2025 (~Sept 17, 2025), 6 through full 2025, Texas has an arithmetic error (+11-2 vs actual 10-3). **Pinned revision 1271870786 (2025-01-26, "End-of-season update") = through 2024 for every row.** |
| NCAA 2026 FBS Records Book (PDF created 2026-09-21), p.110 | **Excluded** — "Some teams have had records adjusted by the NCAA Committee on Infractions" | **Applied** | Through 2025. Top-25 lists only (33 programs). Its 2019–25 decade table (p.111, 130 programs) equals CFBD on-field minus vacated wins exactly for 124/130; the 6 differences are Arizona St. −10, Iowa −4, Kentucky −10, Michigan St. −14, Tennessee −11 (all vacated) and Michigan +1. |
| NCAA Statistics Policies & Guidelines, p.21 (the rule both follow) | Regular-season vacated: "the wins and ties, but not the losses, of the penalized team are dropped"; vacated postseason games drop W and L; opponents unchanged | "the wins of the penalized team must be changed to losses, and the losses of its opponents must be changed to wins." Only COI/IARP/NCAA executive action — conference-imposed forfeits do not change NCAA records | — |

**How our columns are built from that:**

- **Official (NCAA) through 2025** = NCAA Records Book where it lists the program (33); otherwise Wikipedia pinned rev 1271870786 (through 2024) + the program's full 2025 record from CFBD `/records` + NCAA rulings issued after Jan 2025 that the pinned revision cannot contain: **Iowa −4** (2023), **Michigan St. −14** (2022–24, ruling Nov 12, 2025). Validation: this reconstruction equals the Records Book for **29/33** programs; the 4 others are Arizona St. (vacation ruled after Jan 2025 — Book used), Delaware (FCS until 2025 — Book used), Georgia Southern (Book 432 vs 433) and Michigan (Book 1,022 vs 1,021; Michigan's own 2026 guide prints 1,021 and every 2019–25 game is in CFBD — **1,021 used, Book flagged**).
- **On-field through 2025** = official + vacated W/L/T added back + every NCAA-ordered forfeit reversed on both sides (penalized team and each opponent). 45 vacated team-seasons (Wikipedia "List of vacated games in NCAA Division I FBS football", rev 1357084197, plus Michigan St. 2022–24 and Mississippi St. 2018 from the season lists); forfeits: Alabama 1993 (8W+1T), Michigan St. 1994 (5), Mississippi St. 1975–77 (18W+1T), Tulane 1983 (2), UNLV 1983–84 (18); opponents of each forfeit taken from CFBD results — counts reconcile game-for-game with the forfeited totals. Penn St.'s 2012 vacation was restored in 2015 — no adjustment.
- **2026** = CFBD `/records?year=2026` (all games incl. non-FBS opponents) as of 2026-10-02, added to both columns.
- Cross-check against 2026 media guides: **Alabama official 985-345-43 and on-field 1,014-336-44 match exactly**; LSU official 822-444-47 matches (LSU's printed "on-field" 859-444-47 keeps its two 1975–76 forfeit wins — pure on-field is 857-446-47); Texas 971-398-33 matches.


**2026 media guide cross-check (12 programs):**

| Program | Guide prints | Our reconstruction (thru 2025) | Result |
|---|---|---|---|
| [Michigan](https://mgoblue.com/documents/2026/9/18/2026-fbl-media-guide-victors-valiant.pdf) | 1021-362-36 | 1,021-362-36 | match (Records Book 1,022 is the outlier) |
| [Georgia Southern](https://gseagles.com/documents/2026/8/10/FB_1_General_Info_2026.pdf) | 370-187-1 | 432-264-10 | guide prints modern era (1982–) only, 370-187-1; Book 432-264-10 used |
| [Ball St.](https://ballstatesports.com/documents/download/2026/4/18/FootballRecordBook_ADA_Accessible.pdf) | 483-473-32 | 484-475-32 | guide 483-473-32 — differs; Wikipedia row shows an unexplained +1W/−1L correction; needs resolution |
| [Missouri St.](https://missouristatebears.com/documents/2026/8/21/2026_MOST_MEDIAGUIDE_V1.pdf) | 507-542-39 | — | guide contradicts itself (507-542-39 vs 507-551-39); no other baseline — unresolved |
| [Texas](https://texaslonghorns.com/documents/download/2026/9/22/Football_Record_Book_-_2026.pdf) | 971-398-33 | 971-398-33 | match |
| [Delaware](https://bluehens.com/documents/2026/7/28/Delaware_Football_Record_Book.pdf) | 796-491-43 | 746-491-43 | guide prints 796 but its own .600 pct only fits 746 (= Records Book 746-491-43, 1,280 games) — guide typo |
| [Western Kentucky](https://wkusports.com/documents/2026/9/3/WKU_FB_26___Record_Book.pdf) | 630-437-31 | 632-436-30 | guide 630-437-31 vs 632-436-30 — 2W/1L/1T apart; needs resolution |
| [Mississippi St.](https://static.hailstate.com/custompages/pdf/fb/2026/fb_26mg.pdf) | 617-610-40 (official 593-627-40) | 593-627-39 | guide official 593-627-40 vs 593-627-39 (1 tie); guide on-field 617-610-40 vs 618-609-40 |
| [Alabama](https://rolltide.com/documents/2026/8/5/2026_Alabama_Football_Media_Guide.pdf) | 985-345-43 (on-field 1014-336-44) | 985-345-43 | exact match, official and on-field |
| [LSU](http://static.lsusports.net/assets/docs/fb/pdf/26guide.pdf) | 859-444-47 (official 822-444-47) | 822-444-47 | official exact; guide "on-field" keeps 2 forfeit wins |
| [Akron](https://gozips.com/documents/2020/11/3/2020_Akron_FB_Guide_Complete.pdf) (2020 guide, through 2019) | 522-559-36 | 534-608-36 | no 2025/2026 guide published (2020 guide only) |
| [Air Force](https://goairforcefalcons.com/documents/2026/7/9/2026_Air_Force_Football_Media_Guide.pdf) | 436-349-13 | 442-357-13 | guide 436-349-13 omits a 1955 season the same guide lists; Wikipedia/CFBD 442-357-13 — needs resolution |

## 3. Vacated / forfeit-affected programs (official vs on-field, through 2025)

| Team | Official (NCAA) | On-field | Wins removed/changed | Ours (frozen) |
|---|---|---|---|---|
| LSU | 822-444-47 | 857-446-47 | -35 | 830-431-47 |
| Alabama | 985-345-43 | 1,014-336-44 | -29 | 999-319-42 |
| Ole Miss | 698-552-35 | 727-556-35 | -29 | 702-533-34 |
| Mississippi St. | 593-627-39 | 618-609-40 | -25 | 610-597-37 |
| Louisiana Lafayette | 581-591-34 | 603-591-34 | -22 | 288-326-5 |
| Notre Dame | 972-341-42 | 993-342-42 | -21 | 916-327-33 |
| Michigan St. | 725-502-44 | 744-497-44 | -19 | 616-420-30 |
| UNLV | 273-393-4 | 291-375-4 | -18 | 220-339-3 |
| North Carolina | 739-584-54 | 755-584-54 | -16 | 695-556-48 |
| USC | 891-378-54 | 905-379-54 | -14 | 807-337-40 |
| Ohio St. | 990-337-53 | 1,002-337-53 | -12 | 882-270-36 |
| Florida St. | 588-298-17 | 599-299-17 | -11 | 563-277-16 |
| Syracuse | 756-589-49 | 767-589-49 | -11 | 711-539-41 |
| Arizona St. | 647-432-24 | 657-432-24 | -10 | 611-389-18 |
| Arkansas St. | 511-536-37 | 521-536-37 | -10 | 231-285-2 |
| Tennessee | 883-422-53 | 893-422-54 | -10 | 869-404-51 |
| Kentucky | 652-662-44 | 661-663-44 | -9 | 537-593-36 |
| Missouri | 729-598-52 | 738-598-52 | -9 | 681-566-50 |
| FIU | 99-184-0 | 104-184-0 | -5 | 97-181-0 |
| California | 705-582-51 | 709-582-51 | -4 | 608-556-31 |
| Iowa | 706-585-39 | 710-585-39 | -4 | 680-557-34 |
| SMU | 553-567-54 | 557-573-54 | -4 | 554-568-54 |
| Georgia Tech | 772-550-43 | 773-550-43 | -1 | 766-529-40 |
| Tulane | 585-680-38 | 586-679-38 | -1 | 560-659-35 |
| Arkansas | 749-555-40 | 748-556-40 | +1 | 715-532-37 |
| Indiana | 534-715-44 | 533-716-44 | +1 | 509-692-38 |
| Kansas St. | 585-680-42 | 584-681-42 | +1 | 526-634-35 |
| Louisiana Tech | 653-509-37 | 652-510-37 | +1 | 266-259-7 |
| Memphis | 552-544-33 | 551-545-33 | +1 | 376-365-8 |
| Miami (OH) | 740-496-44 | 739-497-44 | +1 | 400-313-15 |
| Nevada | 583-540-33 | 582-541-33 | +1 | 238-226-0 |
| New Mexico St. | 462-688-30 | 461-689-30 | +1 | 343-628-14 |
| Northwestern | 577-716-44 | 576-717-44 | +1 | 544-689-33 |
| Oregon St. | 571-646-50 | 570-647-50 | +1 | 499-607-36 |
| Purdue | 644-618-48 | 643-619-48 | +1 | 604-606-46 |
| Rice | 501-668-32 | 500-669-32 | +1 | 493-667-32 |
| San José St. | 527-554-38 | 526-555-38 | +1 | 374-459-14 |
| South Carolina | 648-624-44 | 647-625-44 | +1 | 614-592-41 |
| Toledo | 596-462-24 | 595-463-24 | +1 | 436-295-8 |
| Vanderbilt | 635-674-50 | 634-675-50 | +1 | 573-651-43 |
| Washington | 790-477-50 | 789-478-50 | +1 | 684-449-32 |
| Wisconsin | 751-533-53 | 750-534-53 | +1 | 721-518-50 |
| Fresno St. | 660-457-27 | 658-459-27 | +2 | 401-284-4 |
| Louisville | 568-504-17 | 566-506-17 | +2 | 403-334-7 |
| North Texas | 560-550-33 | 558-552-33 | +2 | 302-374-11 |
| San Diego St. | 604-460-32 | 602-462-32 | +2 | 372-297-8 |
| Utah St. | 583-582-31 | 581-584-31 | +2 | 548-557-28 |
| Auburn | 809-485-47 | 806-487-48 | +3 | 783-475-43 |
| Southern Miss | 621-477-26 | 618-480-26 | +3 | 388-335-6 |

Programs shifted by 1–3 only (e.g. Auburn, Fresno St., Southern Miss) are opponents of NCAA-ordered forfeits: officially credited a win they lost on the field.

## 4. All 136 programs, sorted by largest discrepancy (wins, through 2025)

"Official" and "on-field" are through 2025 so they compare like with like against our frozen numbers; the last two columns add 2026 games. Likely cause decomposes the gap: games CFBD lacks (split into *missing early seasons* vs *FCS/lower-division era* by CFBD's own classification data), vacated/forfeited wins, and drift between the frozen file and current CFBD data.

| # | Team | Ours W-L-T (pct) | Official thru 2025 (pct) | Diff W | On-field thru 2025 | Diff W | Likely cause | 2026 (CFBD) | Official now | On-field now | Official source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Missouri St. | 101-156-0 | — | — | — | — | other: no baseline (FBS since 2025; Missouri St. media guide prints 507-542-39 and 507-551-39) | 1-3-0 | — | — | none |
| 2 | Delaware | 156-108-0 (0.591) | 746-491-43 (.600) | +590 | 746-491-43 | +590 | FCS/lower-division era games excluded (+536); other: frozen program_stats differs from current CFBD (-54) | 2-2-0 | 748-493-43 | 748-493-43 | ncaa-book (wiki-end2024+cfbd2025 = None) |
| 3 | Western Kentucky | 160-130-0 (0.552) | 632-436-30 (.589) | +472 | 632-436-30 | +472 | FCS/lower-division era games excluded (+462); other: frozen program_stats differs from current CFBD (-10) | 1-4-0 | 633-440-30 | 633-440-30 | wiki-end2024+cfbd2025 |
| 4 | Middle Tennessee | 153-174-0 (0.468) | 613-481-28 (.559) | +460 | 613-481-28 | +460 | FCS/lower-division era games excluded (+453); other: frozen program_stats differs from current CFBD (-7) | 2-2-0 | 615-483-28 | 615-483-28 | wiki-end2024+cfbd2025 |
| 5 | UMass | 129-204-4 (0.389) | 582-661-50 (.469) | +453 | 582-661-50 | +453 | FCS/lower-division era games excluded (+412); other: frozen program_stats differs from current CFBD (-41) | 4-0-0 | 586-661-50 | 586-661-50 | wiki-end2024+cfbd2025 |
| 6 | Jacksonville St. | 182-80-0 (0.695) | 630-432-39 (.590) | +448 | 630-432-39 | +448 | FCS/lower-division era games excluded (+442); other: frozen program_stats differs from current CFBD (-6) | 3-2-0 | 633-434-39 | 633-434-39 | wiki-end2024+cfbd2025 |
| 7 | Texas St. | 111-156-0 (0.416) | 548-511-25 (.517) | +437 | 548-511-25 | +437 | FCS/lower-division era games excluded (+430); other: frozen program_stats differs from current CFBD (-7) | 2-2-0 | 550-513-25 | 550-513-25 | wiki-end2024+cfbd2025 |
| 8 | Appalachian St. | 252-143-5 (0.636) | 674-368-29 (.643) | +422 | 674-368-29 | +422 | FCS/lower-division era games excluded (+415); other: frozen program_stats differs from current CFBD (-7) | 3-1-0 | 677-369-29 | 677-369-29 | ncaa-book |
| 9 | Troy | 171-139-0 (0.552) | 587-445-28 (.567) | +416 | 587-445-28 | +416 | FCS/lower-division era games excluded (+411); other: frozen program_stats differs from current CFBD (-5) | 2-2-0 | 589-447-28 | 589-447-28 | wiki-end2024+cfbd2025 |
| 10 | Sam Houston St. | 168-94-0 (0.641) | 583-501-34 (.537) | +415 | 583-501-34 | +415 | FCS/lower-division era games excluded (+412); other: frozen program_stats differs from current CFBD (-3) | 1-3-0 | 584-504-34 | 584-504-34 | wiki-end2024+cfbd2025 |
| 11 | Connecticut | 131-183-2 (0.418) | 539-617-38 (.467) | +408 | 539-617-38 | +408 | FCS/lower-division era games excluded (+385); other: frozen program_stats differs from current CFBD (-23) | 2-2-0 | 541-619-38 | 541-619-38 | wiki-end2024+cfbd2025 |
| 12 | Louisiana Tech | 266-259-7 (0.507) | 653-509-37 (.560) | +387 | 652-510-37 | +386 | FCS/lower-division era games excluded (+352); other: frozen program_stats differs from current CFBD (-34) | 1-2-0 | 654-511-37 | 653-512-37 | wiki-end2024+cfbd2025 |
| 13 | Akron | 166-292-3 (0.363) | 534-608-36 (.469) | +368 | 534-608-36 | +368 | FCS/lower-division era games excluded (+348); other: frozen program_stats differs from current CFBD (-20) | 1-3-0 | 535-611-36 | 535-611-36 | wiki-end2024+cfbd2025 |
| 14 | Marshall | 276-294-3 (0.484) | 643-581-47 (.524) | +367 | 643-581-47 | +367 | FCS/lower-division era games excluded (+357); other: frozen program_stats differs from current CFBD (-10) | 3-1-0 | 646-582-47 | 646-582-47 | wiki-end2024+cfbd2025 |
| 15 | Central Michigan | 313-269-11 (0.537) | 658-464-36 (.584) | +345 | 658-464-36 | +345 | FCS/lower-division era games excluded (+339); other: frozen program_stats differs from current CFBD (-6) | 2-2-0 | 660-466-36 | 660-466-36 | wiki-end2024+cfbd2025 |
| 16 | Nevada | 238-226-0 (0.513) | 583-540-33 (.519) | +345 | 582-541-33 | +344 | FCS/lower-division era games excluded (+320); other: frozen program_stats differs from current CFBD (-24) | 1-3-0 | 584-543-33 | 583-544-33 | wiki-end2024+cfbd2025 |
| 17 | Miami (OH) | 400-313-15 (0.560) | 740-496-44 (.595) | +340 | 739-497-44 | +339 | missing early seasons (+312); other: frozen program_stats differs from current CFBD (-27) | 2-2-0 | 742-498-44 | 741-499-44 | wiki-end2024+cfbd2025 |
| 18 | Eastern Michigan | 192-381-7 (0.337) | 499-638-47 (.441) | +307 | 499-638-47 | +307 | FCS/lower-division era games excluded (+305) | 2-3-0 | 501-641-47 | 501-641-47 | wiki-end2024+cfbd2025 |
| 19 | Northern Illinois | 324-347-4 (0.483) | 622-541-51 (.533) | +298 | 622-541-51 | +298 | FCS/lower-division era games excluded (+298) | 0-4-0 | 622-545-51 | 622-545-51 | wiki-end2024+cfbd2025 |
| 20 | Louisiana Lafayette | 288-326-5 (0.469) | 581-591-34 (.496) | +293 | 603-591-34 | +315 | FCS/lower-division era games excluded (+312); vacated/forfeited wins (ours counts on-field) (-22); other: frozen program_stats differs from current CFBD (-3) | 3-1-0 | 584-592-34 | 606-592-34 | wiki-end2024+cfbd2025 |
| 21 | Ohio | 333-387-9 (0.463) | 623-591-48 (.513) | +290 | 623-591-48 | +290 | missing early seasons (+275); other: frozen program_stats differs from current CFBD (-15) | 2-2-0 | 625-593-48 | 625-593-48 | wiki-end2024+cfbd2025 |
| 22 | Arkansas St. | 231-285-2 (0.448) | 511-536-37 (.488) | +280 | 521-536-37 | +290 | FCS/lower-division era games excluded (+266); other: frozen program_stats differs from current CFBD (-24); vacated/forfeited wins (ours counts on-field) (-10) | 2-2-0 | 513-538-37 | 523-538-37 | wiki-end2024+cfbd2025 |
| 23 | Hawaii | 325-320-6 (0.504) | 597-503-25 (.542) | +272 | 597-503-25 | +272 | FCS/lower-division era games excluded (+241); other: frozen program_stats differs from current CFBD (-31) | 1-3-0 | 598-506-25 | 598-506-25 | wiki-end2024+cfbd2025 |
| 24 | Georgia Southern | 161-119-0 (0.575) | 432-264-10 (.619) | +271 | 432-264-10 | +271 | FCS/lower-division era games excluded (+271) | 1-3-0 | 433-267-10 | 433-267-10 | ncaa-book (wiki-end2024+cfbd2025 = [433, 264, 10]) |
| 25 | Cincinnati | 409-395-12 (0.509) | 671-620-51 (.519) | +262 | 671-620-51 | +262 | FCS/lower-division era games excluded (+235); other: frozen program_stats differs from current CFBD (-27) | 4-0-0 | 675-620-51 | 675-620-51 | wiki-end2024+cfbd2025 |
| 26 | Buffalo | 163-241-4 (0.404) | 422-568-28 (.428) | +259 | 422-568-28 | +259 | FCS/lower-division era games excluded (+250); other: frozen program_stats differs from current CFBD (-9) | 2-2-0 | 424-570-28 | 424-570-28 | wiki-end2024+cfbd2025 |
| 27 | Fresno St. | 401-284-4 (0.585) | 660-457-27 (.589) | +259 | 658-459-27 | +257 | FCS/lower-division era games excluded (+227); other: frozen program_stats differs from current CFBD (-30) | 3-1-0 | 663-458-27 | 661-460-27 | wiki-end2024+cfbd2025 |
| 28 | North Texas | 302-374-11 (0.448) | 560-550-33 (.504) | +258 | 558-552-33 | +256 | FCS/lower-division era games excluded (+235); other: frozen program_stats differs from current CFBD (-21) | 3-2-0 | 563-552-33 | 561-554-33 | wiki-end2024+cfbd2025 |
| 29 | Western Michigan | 374-339-7 (0.524) | 613-492-24 (.554) | +239 | 613-492-24 | +239 | missing early seasons (+239) | 2-2-0 | 615-494-24 | 615-494-24 | wiki-end2024+cfbd2025 |
| 30 | Southern Miss | 388-335-6 (0.536) | 621-477-26 (.564) | +233 | 618-480-26 | +230 | FCS/lower-division era games excluded (+205); other: frozen program_stats differs from current CFBD (-25) | 1-3-0 | 622-480-26 | 619-483-26 | wiki-end2024+cfbd2025 |
| 31 | San Diego St. | 372-297-8 (0.555) | 604-460-32 (.566) | +232 | 602-462-32 | +230 | FCS/lower-division era games excluded (+214); other: frozen program_stats differs from current CFBD (-16) | 1-3-0 | 605-463-32 | 603-465-32 | wiki-end2024+cfbd2025 |
| 32 | Boise St. | 292-92-0 (0.760) | 511-194-2 (.724) | +219 | 511-194-2 | +219 | FCS/lower-division era games excluded (+201); other: frozen program_stats differs from current CFBD (-18) | 3-1-0 | 514-195-2 | 514-195-2 | ncaa-book |
| 33 | Rutgers | 466-459-12 (0.504) | 683-708-42 (.491) | +217 | 683-708-42 | +217 | missing early seasons (+185); other: frozen program_stats differs from current CFBD (-32) | 1-3-0 | 684-711-42 | 684-711-42 | wiki-end2024+cfbd2025 |
| 34 | Ball St. | 280-304-4 (0.480) | 484-475-32 (.505) | +204 | 484-475-32 | +204 | FCS/lower-division era games excluded (+199); other: frozen program_stats differs from current CFBD (-5) | 1-3-0 | 485-478-32 | 485-478-32 | wiki-end2024+cfbd2025 + correction since Jan 2025 (unverified) |
| 35 | Bowling Green | 383-328-11 (0.538) | 573-440-52 (.562) | +190 | 573-440-52 | +190 | FCS/lower-division era games excluded (+181); other: frozen program_stats differs from current CFBD (-9) | 0-4-0 | 573-444-52 | 573-444-52 | wiki-end2024+cfbd2025 |
| 36 | James Madison | 212-74-0 (0.741) | 390-227-4 (.631) | +178 | 390-227-4 | +178 | FCS/lower-division era games excluded (+173); other: frozen program_stats differs from current CFBD (-5) | 4-0-0 | 394-227-4 | 394-227-4 | ncaa-book |
| 37 | Louisiana Monroe | 157-293-2 (0.350) | 333-480-8 (.410) | +176 | 333-480-8 | +176 | FCS/lower-division era games excluded (+166); other: frozen program_stats differs from current CFBD (-10) | 0-4-0 | 333-484-8 | 333-484-8 | wiki-end2024+cfbd2025 |
| 38 | Memphis | 376-365-8 (0.507) | 552-544-33 (.504) | +176 | 551-545-33 | +175 | FCS/lower-division era games excluded (+172); other: frozen program_stats differs from current CFBD (-3) | 3-1-0 | 555-545-33 | 554-546-33 | wiki-end2024+cfbd2025 |
| 39 | Boston College | 537-439-14 (0.549) | 703-541-37 (.563) | +166 | 703-541-37 | +166 | missing early seasons (+149); other: frozen program_stats differs from current CFBD (-17) | 2-2-0 | 705-543-37 | 705-543-37 | wiki-end2024+cfbd2025 |
| 40 | Louisville | 403-334-7 (0.546) | 568-504-17 (.529) | +165 | 566-506-17 | +163 | missing early seasons (+153); other: frozen program_stats differs from current CFBD (-10) | 2-2-0 | 570-506-17 | 568-508-17 | wiki-end2024+cfbd2025 |
| 41 | Toledo | 436-295-8 (0.595) | 596-462-24 (.562) | +160 | 595-463-24 | +159 | missing early seasons (+156); other: frozen program_stats differs from current CFBD (-3) | 3-1-0 | 599-463-24 | 598-464-24 | wiki-end2024+cfbd2025 |
| 42 | Liberty | 155-103-0 (0.601) | 311-266-4 (.539) | +156 | 311-266-4 | +156 | FCS/lower-division era games excluded (+155) | 3-1-0 | 314-267-4 | 314-267-4 | wiki-end2024+cfbd2025 |
| 43 | Temple | 348-460-26 (0.433) | 502-633-52 (.445) | +154 | 502-633-52 | +154 | FCS/lower-division era games excluded (+147); other: frozen program_stats differs from current CFBD (-7) | 1-3-0 | 503-636-52 | 503-636-52 | wiki-end2024+cfbd2025 |
| 44 | San José St. | 374-459-14 (0.450) | 527-554-38 (.488) | +153 | 526-555-38 | +152 | FCS/lower-division era games excluded (+130); other: frozen program_stats differs from current CFBD (-22) | 2-2-0 | 529-556-38 | 528-557-38 | wiki-end2024+cfbd2025 |
| 45 | Kent St. | 231-476-5 (0.328) | 371-614-28 (.380) | +140 | 371-614-28 | +140 | missing early seasons (+138) | 2-2-0 | 373-616-28 | 373-616-28 | wiki-end2024+cfbd2025 |
| 46 | Tulsa | 518-498-18 (0.510) | 654-551-27 (.542) | +136 | 654-551-27 | +136 | FCS/lower-division era games excluded (+116); other: frozen program_stats differs from current CFBD (-20) | 3-2-0 | 657-553-27 | 657-553-27 | wiki-end2024+cfbd2025 |
| 47 | Arizona | 519-468-23 (0.525) | 646-511-33 (.557) | +127 | 646-511-33 | +127 | missing early seasons (+125) | 3-1-0 | 649-512-33 | 649-512-33 | wiki-end2024+cfbd2025 |
| 48 | New Mexico St. | 343-628-14 (0.355) | 462-688-30 (.404) | +119 | 461-689-30 | +118 | FCS/lower-division era games excluded (+118) | 2-3-0 | 464-691-30 | 463-692-30 | wiki-end2024+cfbd2025 |
| 49 | East Carolina | 361-339-3 (0.516) | 477-463-12 (.507) | +116 | 477-463-12 | +116 | FCS/lower-division era games excluded (+110); other: frozen program_stats differs from current CFBD (-6) | 2-2-0 | 479-465-12 | 479-465-12 | wiki-end2024+cfbd2025 |
| 50 | Kentucky | 537-593-36 (0.476) | 652-662-44 (.496) | +115 | 661-663-44 | +124 | missing early seasons (+112); other: frozen program_stats differs from current CFBD (-12); vacated/forfeited wins (ours counts on-field) (-9) | 3-1-0 | 655-663-44 | 664-664-44 | wiki-end2024+cfbd2025 |
| 51 | Michigan St. | 616-420-30 (0.592) | 725-502-44 (.588) | +109 | 744-497-44 | +128 | missing early seasons (+124); vacated/forfeited wins (ours counts on-field) (-19); other: frozen program_stats differs from current CFBD (-4) | 2-2-0 | 727-504-44 | 746-499-44 | wiki-end2024+cfbd2025 + correction since Jan 2025 (unverified) |
| 52 | Ohio St. | 882-270-36 (0.758) | 990-337-53 (.737) | +108 | 1,002-337-53 | +120 | FCS/lower-division era games excluded (+118); vacated/forfeited wins (ours counts on-field) (-12) | 3-1-0 | 993-338-53 | 1,005-338-53 | ncaa-book |
| 53 | Washington | 684-449-32 (0.601) | 790-477-50 (.619) | +106 | 789-478-50 | +105 | missing early seasons (+103) | 3-1-0 | 793-478-50 | 792-479-50 | ncaa-book |
| 54 | California | 608-556-31 (0.522) | 705-582-51 (.546) | +97 | 709-582-51 | +101 | missing early seasons (+101); vacated/forfeited wins (ours counts on-field) (-4) | 2-2-0 | 707-584-51 | 711-584-51 | wiki-end2024+cfbd2025 |
| 55 | UCF | 207-162-0 (0.561) | 302-249-1 (.548) | +95 | 302-249-1 | +95 | missing early seasons (+90); other: frozen program_stats differs from current CFBD (-5) | 3-1-0 | 305-250-1 | 305-250-1 | wiki-end2024+cfbd2025 |
| 56 | Maryland | 593-550-30 (0.518) | 685-640-43 (.516) | +92 | 685-640-43 | +92 | missing early seasons (+91) | 2-2-0 | 687-642-43 | 687-642-43 | wiki-end2024+cfbd2025 |
| 57 | New Mexico | 425-587-17 (0.421) | 513-651-31 (.442) | +88 | 513-651-31 | +88 | missing early seasons (+83); other: frozen program_stats differs from current CFBD (-5) | 3-1-0 | 516-652-31 | 516-652-31 | wiki-end2024+cfbd2025 |
| 58 | West Virginia | 703-482-41 (0.590) | 791-541-45 (.591) | +88 | 791-541-45 | +88 | FCS/lower-division era games excluded (+86) | 3-1-0 | 794-542-45 | 794-542-45 | ncaa-book |
| 59 | Virginia | 613-619-37 (0.498) | 699-652-48 (.517) | +86 | 699-652-48 | +86 | missing early seasons (+79); other: frozen program_stats differs from current CFBD (-7) | 3-1-0 | 702-653-48 | 702-653-48 | wiki-end2024+cfbd2025 |
| 60 | USC | 807-337-40 (0.699) | 891-378-54 (.694) | +84 | 905-379-54 | +98 | missing early seasons (+90); vacated/forfeited wins (ours counts on-field) (-14); other: frozen program_stats differs from current CFBD (-8) | 4-1-0 | 895-379-54 | 909-380-54 | ncaa-book |
| 61 | Oregon | 653-472-34 (0.578) | 731-514-46 (.584) | +78 | 731-514-46 | +78 | missing early seasons (+78) | 3-1-0 | 734-515-46 | 734-515-46 | wiki-end2024+cfbd2025 |
| 62 | Stanford | 603-496-34 (0.547) | 677-513-49 (.566) | +74 | 677-513-49 | +74 | missing early seasons (+72) | 2-2-0 | 679-515-49 | 679-515-49 | wiki-end2024+cfbd2025 |
| 63 | Washington St. | 514-560-38 (0.479) | 587-597-45 (.496) | +73 | 587-597-45 | +73 | missing early seasons (+71) | 1-3-0 | 588-600-45 | 588-600-45 | wiki-end2024+cfbd2025 |
| 64 | Oregon St. | 499-607-36 (0.453) | 571-646-50 (.470) | +72 | 570-647-50 | +71 | missing early seasons (+71) | 2-2-0 | 573-648-50 | 572-649-50 | wiki-end2024+cfbd2025 |
| 65 | Michigan | 954-336-34 (0.733) | 1,021-362-36 (.732) | +67 | 1,021-362-36 | +67 | other: frozen program_stats differs from current CFBD (-40); missing early seasons (+27) | 3-1-0 | 1,024-363-36 | 1,024-363-36 | Wikipedia end-2024 + CFBD 2025 = 2026 Michigan media guide (Records Book prints 1,022) |
| 66 | UTEP | 349-600-18 (0.370) | 415-653-30 (.392) | +66 | 415-653-30 | +66 | missing early seasons (+62); other: frozen program_stats differs from current CFBD (-4) | 1-3-0 | 416-656-30 | 416-656-30 | wiki-end2024+cfbd2025 |
| 67 | Vanderbilt | 573-651-43 (0.469) | 635-674-50 (.486) | +62 | 634-675-50 | +61 | missing early seasons (+61) | 3-1-0 | 638-675-50 | 637-676-50 | wiki-end2024+cfbd2025 |
| 68 | Kansas St. | 526-634-35 (0.455) | 585-680-42 (.464) | +59 | 584-681-42 | +58 | missing early seasons (+53); other: frozen program_stats differs from current CFBD (-5) | 3-1-0 | 588-681-42 | 587-682-42 | wiki-end2024+cfbd2025 |
| 69 | Kansas | 557-670-54 (0.456) | 615-693-58 (.471) | +58 | 615-693-58 | +58 | missing early seasons (+57) | 1-2-0 | 616-695-58 | 616-695-58 | wiki-end2024+cfbd2025 |
| 70 | Notre Dame | 916-327-33 (0.731) | 972-341-42 (.733) | +56 | 993-342-42 | +77 | missing early seasons (+70); vacated/forfeited wins (ours counts on-field) (-21); other: frozen program_stats differs from current CFBD (-7) | 4-0-0 | 976-341-42 | 997-342-42 | ncaa-book |
| 71 | Colorado | 682-530-35 (0.561) | 735-557-36 (.567) | +53 | 735-557-36 | +53 | missing early seasons (+53) | 2-2-0 | 737-559-36 | 737-559-36 | wiki-end2024+cfbd2025 |
| 72 | Oklahoma | 907-331-47 (0.724) | 960-351-53 (.723) | +53 | 960-351-53 | +53 | missing early seasons (+47); other: frozen program_stats differs from current CFBD (-6) | 2-2-0 | 962-353-53 | 962-353-53 | ncaa-book |
| 73 | UNLV | 220-339-3 (0.394) | 273-393-4 (.410) | +53 | 291-375-4 | +71 | missing early seasons (+68); vacated/forfeited wins (ours counts on-field) (-18); other: frozen program_stats differs from current CFBD (-3) | 2-2-0 | 275-395-4 | 293-377-4 | wiki-end2024+cfbd2025 |
| 74 | Texas | 920-388-32 (0.699) | 971-398-33 (.704) | +51 | 971-398-33 | +51 | missing early seasons (+50) | 4-0-0 | 975-398-33 | 975-398-33 | ncaa-book |
| 75 | Miami | 637-359-12 (0.638) | 686-394-19 (.633) | +49 | 686-394-19 | +49 | FCS/lower-division era games excluded (+48) | 4-0-0 | 690-394-19 | 690-394-19 | ncaa-book |
| 76 | Pittsburgh | 727-519-37 (0.581) | 776-571-42 (.574) | +49 | 776-571-42 | +49 | missing early seasons (+47) | 4-0-0 | 780-571-42 | 780-571-42 | ncaa-book |
| 77 | Missouri | 681-566-50 (0.544) | 729-598-52 (.547) | +48 | 738-598-52 | +57 | missing early seasons (+55); vacated/forfeited wins (ours counts on-field) (-9) | 3-1-0 | 732-599-52 | 741-599-52 | wiki-end2024+cfbd2025 |
| 78 | Navy | 711-579-52 (0.549) | 759-605-57 (.554) | +48 | 759-605-57 | +48 | missing early seasons (+30); other: frozen program_stats differs from current CFBD (-18) | 1-2-0 | 760-607-57 | 760-607-57 | wiki-end2024+cfbd2025 |
| 79 | Minnesota | 704-538-42 (0.565) | 749-553-44 (.573) | +45 | 749-553-44 | +45 | other: frozen program_stats differs from current CFBD (-29); missing early seasons (+16) | 3-1-0 | 752-554-44 | 752-554-44 | ncaa-book |
| 80 | Syracuse | 711-539-41 (0.567) | 756-589-49 (.560) | +45 | 767-589-49 | +56 | missing early seasons (+55); vacated/forfeited wins (ours counts on-field) (-11) | 1-2-0 | 757-591-49 | 768-591-49 | wiki-end2024+cfbd2025 |
| 81 | North Carolina | 695-556-48 (0.553) | 739-584-54 (.556) | +44 | 755-584-54 | +60 | missing early seasons (+60); vacated/forfeited wins (ours counts on-field) (-16) | 2-1-0 | 741-585-54 | 757-585-54 | wiki-end2024+cfbd2025 |
| 82 | Purdue | 604-606-46 (0.499) | 644-618-48 (.510) | +40 | 643-619-48 | +39 | other: frozen program_stats differs from current CFBD (-29); missing early seasons (+10) | 1-3-0 | 645-621-48 | 644-622-48 | wiki-end2024+cfbd2025 |
| 83 | Arizona St. | 611-389-18 (0.609) | 647-432-24 (.597) | +36 | 657-432-24 | +46 | FCS/lower-division era games excluded (+46); vacated/forfeited wins (ours counts on-field) (-10) | 2-1-0 | 649-433-24 | 659-433-24 | ncaa-book (wiki-end2024+cfbd2025 = [657, 432, 24]) |
| 84 | Army | 710-533-48 (0.569) | 746-553-51 (.571) | +36 | 746-553-51 | +36 | other: frozen program_stats differs from current CFBD (-22); missing early seasons (+14) | 2-1-0 | 748-554-51 | 748-554-51 | ncaa-book |
| 85 | Nebraska | 896-411-38 (0.680) | 931-436-40 (.676) | +35 | 931-436-40 | +35 | missing early seasons (+34) | 4-0-0 | 935-436-40 | 935-436-40 | ncaa-book |
| 86 | Utah St. | 548-557-28 (0.496) | 583-582-31 (.500) | +35 | 581-584-31 | +33 | missing early seasons (+30); other: frozen program_stats differs from current CFBD (-3) | 1-3-0 | 584-585-31 | 582-587-31 | wiki-end2024+cfbd2025 |
| 87 | Virginia Tech | 746-504-44 (0.594) | 781-521-46 (.596) | +35 | 781-521-46 | +35 | missing early seasons (+35) | 4-0-0 | 785-521-46 | 785-521-46 | ncaa-book |
| 88 | Arkansas | 715-532-37 (0.571) | 749-555-40 (.572) | +34 | 748-556-40 | +33 | missing early seasons (+32) | 2-2-0 | 751-557-40 | 750-558-40 | ncaa-book |
| 89 | South Carolina | 614-592-41 (0.509) | 648-624-44 (.509) | +34 | 647-625-44 | +33 | missing early seasons (+31) | 2-2-0 | 650-626-44 | 649-627-44 | wiki-end2024+cfbd2025 |
| 90 | Northwestern | 544-689-33 (0.443) | 577-716-44 (.448) | +33 | 576-717-44 | +32 | other: frozen program_stats differs from current CFBD (-24); missing early seasons (+8) | 2-1-0 | 579-717-44 | 578-718-44 | wiki-end2024+cfbd2025 |
| 91 | Oklahoma St. | 608-555-41 (0.522) | 641-592-48 (.519) | +33 | 641-592-48 | +33 | missing early seasons (+31) | 3-1-0 | 644-593-48 | 644-593-48 | wiki-end2024+cfbd2025 |
| 92 | Illinois | 619-618-43 (0.500) | 651-632-50 (.507) | +32 | 651-632-50 | +32 | other: frozen program_stats differs from current CFBD (-22); missing early seasons (+10) | 2-2-0 | 653-634-50 | 653-634-50 | wiki-end2024+cfbd2025 |
| 93 | Penn St. | 918-402-37 (0.690) | 950-418-41 (.689) | +32 | 950-418-41 | +32 | missing early seasons (+20); other: frozen program_stats differs from current CFBD (-12) | 3-1-0 | 953-419-41 | 953-419-41 | ncaa-book |
| 94 | UAB | 147-186-0 (0.441) | 179-204-2 (.468) | +32 | 179-204-2 | +32 | missing early seasons (+31) | 2-2-0 | 181-206-2 | 181-206-2 | wiki-end2024+cfbd2025 |
| 95 | Texas Tech | 586-462-24 (0.558) | 617-488-32 (.557) | +31 | 617-488-32 | +31 | missing early seasons (+28); other: frozen program_stats differs from current CFBD (-3) | 4-0-0 | 621-488-32 | 621-488-32 | wiki-end2024+cfbd2025 |
| 96 | Utah | 704-468-30 (0.598) | 735-491-31 (.597) | +31 | 735-491-31 | +31 | missing early seasons (+29) | 4-0-0 | 739-491-31 | 739-491-31 | wiki-end2024+cfbd2025 |
| 97 | Wisconsin | 721-518-50 (0.579) | 751-533-53 (.582) | +30 | 750-534-53 | +29 | other: frozen program_stats differs from current CFBD (-25); missing early seasons (+4) | 3-1-0 | 754-534-53 | 753-535-53 | ncaa-book |
| 98 | Auburn | 783-475-43 (0.618) | 809-485-47 (.621) | +26 | 806-487-48 | +23 | missing early seasons (+23) | 3-1-0 | 812-486-47 | 809-488-48 | ncaa-book |
| 99 | Georgia | 878-411-50 (0.674) | 904-434-54 (.669) | +26 | 904-434-54 | +26 | missing early seasons (+26) | 4-0-0 | 908-434-54 | 908-434-54 | ncaa-book |
| 100 | Iowa | 680-557-34 (0.548) | 706-585-39 (.545) | +26 | 710-585-39 | +30 | missing early seasons (+29); vacated/forfeited wins (ours counts on-field) (-4) | 4-0-0 | 710-585-39 | 714-585-39 | wiki-end2024+cfbd2025 + correction since Jan 2025 (unverified) |
| 101 | Florida | 745-454-37 (0.618) | 770-458-40 (.623) | +25 | 770-458-40 | +25 | missing early seasons (+24) | 4-0-0 | 774-458-40 | 774-458-40 | ncaa-book |
| 102 | Florida St. | 563-277-16 (0.667) | 588-298-17 (.661) | +25 | 599-299-17 | +36 | missing early seasons (+33); vacated/forfeited wins (ours counts on-field) (-11); other: frozen program_stats differs from current CFBD (-3) | 2-2-0 | 590-300-17 | 601-301-17 | ncaa-book |
| 103 | Indiana | 509-692-38 (0.426) | 534-715-44 (.430) | +25 | 533-716-44 | +24 | missing early seasons (+24) | 4-0-0 | 538-715-44 | 537-716-44 | wiki-end2024+cfbd2025 |
| 104 | Tulane | 560-659-35 (0.461) | 585-680-38 (.464) | +25 | 586-679-38 | +26 | missing early seasons (+26); vacated/forfeited wins (ours counts on-field) (-1) | 2-2-0 | 587-682-38 | 588-681-38 | wiki-end2024+cfbd2025 |
| 105 | Wyoming | 547-602-26 (0.477) | 572-616-28 (.482) | +25 | 572-616-28 | +25 | missing early seasons (+25) | 2-2-0 | 574-618-28 | 574-618-28 | wiki-end2024+cfbd2025 |
| 106 | Iowa St. | 561-674-45 (0.456) | 585-685-46 (.462) | +24 | 585-685-46 | +24 | missing early seasons (+19); other: frozen program_stats differs from current CFBD (-5) | 2-2-0 | 587-687-46 | 587-687-46 | wiki-end2024+cfbd2025 |
| 107 | North Carolina St. | 628-591-46 (0.515) | 652-611-55 (.516) | +24 | 652-611-55 | +24 | missing early seasons (+21); other: frozen program_stats differs from current CFBD (-3) | 2-2-0 | 654-613-55 | 654-613-55 | wiki-end2024+cfbd2025 |
| 108 | South Alabama | 71-102-0 (0.410) | 94-106-0 (.470) | +23 | 94-106-0 | +23 | missing early seasons (+19); other: frozen program_stats differs from current CFBD (-4) | 2-2-0 | 96-108-0 | 96-108-0 | wiki-end2024+cfbd2025 |
| 109 | Texas A&M | 775-498-44 (0.605) | 797-511-48 (.605) | +22 | 797-511-48 | +22 | missing early seasons (+20) | 2-2-0 | 799-513-48 | 799-513-48 | ncaa-book |
| 110 | UCLA | 623-425-31 (0.592) | 645-462-37 (.580) | +22 | 645-462-37 | +22 | missing early seasons (+22) | 4-0-0 | 649-462-37 | 649-462-37 | wiki-end2024+cfbd2025 |
| 111 | Duke | 535-557-28 (0.490) | 556-565-31 (.496) | +21 | 556-565-31 | +21 | missing early seasons (+19) | 4-0-0 | 560-565-31 | 560-565-31 | wiki-end2024+cfbd2025 |
| 112 | TCU | 682-562-50 (0.546) | 703-582-57 (.545) | +21 | 703-582-57 | +21 | missing early seasons (+19) | 2-2-0 | 705-584-57 | 705-584-57 | wiki-end2024+cfbd2025 |
| 113 | Clemson | 795-475-44 (0.622) | 815-482-45 (.624) | +20 | 815-482-45 | +20 | missing early seasons (+20) | 3-1-0 | 818-483-45 | 818-483-45 | ncaa-book |
| 114 | South Florida | 164-151-0 (0.521) | 184-164-0 (.529) | +20 | 184-164-0 | +20 | missing early seasons (+20) | 4-0-0 | 188-164-0 | 188-164-0 | wiki-end2024+cfbd2025 |
| 115 | Mississippi St. | 610-597-37 (0.505) | 593-627-39 (.486) | -17 | 618-609-40 | +8 | vacated/forfeited wins (ours counts on-field) (-25); missing early seasons (+7) | 4-0-0 | 597-627-39 | 622-609-40 | wiki-end2024+cfbd2025 |
| 116 | Alabama | 999-319-42 (0.750) | 985-345-43 (.733) | -14 | 1,014-336-44 | +15 | vacated/forfeited wins (ours counts on-field) (-29); missing early seasons (+15) | 4-0-0 | 989-345-43 | 1,018-336-44 | ncaa-book |
| 117 | Tennessee | 869-404-51 (0.676) | 883-422-53 (.670) | +14 | 893-422-54 | +24 | missing early seasons (+24); vacated/forfeited wins (ours counts on-field) (-10) | 3-1-0 | 886-423-53 | 896-423-54 | ncaa-book |
| 118 | Houston | 474-385-15 (0.551) | 486-405-15 (.545) | +12 | 486-405-15 | +12 | missing early seasons (+11) | 3-1-0 | 489-406-15 | 489-406-15 | wiki-end2024+cfbd2025 |
| 119 | Wake Forest | 495-693-31 (0.419) | 505-697-33 (.422) | +10 | 505-697-33 | +10 | missing early seasons (+10) | 3-1-0 | 508-698-33 | 508-698-33 | wiki-end2024+cfbd2025 |
| 120 | Old Dominion | 98-84-0 (0.538) | 107-89-0 (.546) | +9 | 107-89-0 | +9 | other: frozen program_stats differs from current CFBD (-8) | 1-3-0 | 108-92-0 | 108-92-0 | wiki-end2024+cfbd2025 |
| 121 | Colorado St. | 541-607-31 (0.472) | 549-631-33 (.466) | +8 | 549-631-33 | +8 | missing early seasons (+6) | 2-2-0 | 551-633-33 | 551-633-33 | wiki-end2024+cfbd2025 |
| 122 | LSU | 830-431-47 (0.652) | 822-444-47 (.644) | -8 | 857-446-47 | +27 | vacated/forfeited wins (ours counts on-field) (-35); missing early seasons (+27) | 3-1-0 | 825-445-47 | 860-447-47 | ncaa-book |
| 123 | Rice | 493-667-32 (0.427) | 501-668-32 (.430) | +8 | 500-669-32 | +7 | missing early seasons (+6) | 1-3-0 | 502-671-32 | 501-672-32 | wiki-end2024+cfbd2025 |
| 124 | Baylor | 631-605-41 (0.510) | 638-614-44 (.509) | +7 | 638-614-44 | +7 | missing early seasons (+7) | 3-1-0 | 641-615-44 | 641-615-44 | wiki-end2024+cfbd2025 |
| 125 | Coastal Carolina | 171-100-0 (0.631) | 178-103-0 (.633) | +7 | 178-103-0 | +7 | FCS/lower-division era games excluded (+7) | 1-3-0 | 179-106-0 | 179-106-0 | wiki-end2024+cfbd2025 |
| 126 | Air Force | 436-355-12 (0.550) | 442-357-13 (.552) | +6 | 442-357-13 | +6 | missing early seasons (+6) | 2-1-0 | 444-358-13 | 444-358-13 | wiki-end2024+cfbd2025 |
| 127 | Georgia Tech | 766-529-40 (0.589) | 772-550-43 (.581) | +6 | 773-550-43 | +7 | missing early seasons (+7); vacated/forfeited wins (ours counts on-field) (-1) | 1-3-0 | 773-553-43 | 774-553-43 | ncaa-book |
| 128 | Ole Miss | 702-533-34 (0.567) | 698-552-35 (.557) | -4 | 727-556-35 | +25 | vacated/forfeited wins (ours counts on-field) (-29); missing early seasons (+25) | 3-1-0 | 701-553-35 | 730-557-35 | wiki-end2024+cfbd2025 |
| 129 | Charlotte | 48-101-0 (0.322) | 51-105-0 (.327) | +3 | 51-105-0 | +3 | FCS/lower-division era games excluded (+3) | 0-4-0 | 51-109-0 | 51-109-0 | wiki-end2024+cfbd2025 |
| 130 | FAU | 126-155-0 (0.448) | 129-172-0 (.429) | +3 | 129-172-0 | +3 | missing early seasons (+3) | 3-1-0 | 132-173-0 | 132-173-0 | wiki-end2024+cfbd2025 |
| 131 | FIU | 97-181-0 (0.349) | 99-184-0 (.350) | +2 | 104-184-0 | +7 | FCS/lower-division era games excluded (+7); vacated/forfeited wins (ours counts on-field) (-5) | 2-2-0 | 101-186-0 | 106-186-0 | wiki-end2024+cfbd2025 |
| 132 | SMU | 554-568-54 (0.494) | 553-567-54 (.494) | -1 | 557-573-54 | +3 | vacated/forfeited wins (ours counts on-field) (-4); missing early seasons (+3) | 3-1-0 | 556-568-54 | 560-574-54 | wiki-end2024+cfbd2025 |
| 133 | BYU | 639-447-26 (0.586) | 639-447-26 (.586) | +0 | 639-447-26 | +0 | minor (within ±2) (+0) | 3-0-0 | 642-447-26 | 642-447-26 | wiki-end2024+cfbd2025 |
| 134 | Georgia St. | 65-125-0 (0.342) | 65-126-0 (.340) | +0 | 65-126-0 | +0 | minor (within ±2) (+0) | 3-1-0 | 68-127-0 | 68-127-0 | wiki-end2024+cfbd2025 |
| 135 | Kennesaw St. | 83-44-0 (0.653) | 83-44-0 (.654) | +0 | 83-44-0 | +0 | minor (within ±2) (+0) | 1-3-0 | 84-47-0 | 84-47-0 | wiki-end2024+cfbd2025 |
| 136 | UTSA | 98-87-0 (0.530) | 98-87-0 (.530) | +0 | 98-87-0 | +0 | minor (within ±2) (+0) | 3-1-0 | 101-88-0 | 101-88-0 | wiki-end2024+cfbd2025 |

## 5. Top 25 all-time wins — ours vs source

| Rank | Ours (as shown on /rank today) | Official NCAA (thru 2025 + 2026 CFBD) | On-field (thru 2025 + 2026 CFBD) |
|---|---|---|---|
| 1 | Alabama 999 | Michigan 1,024 | Michigan 1,024 |
| 2 | Michigan 954 | Ohio St. 993 | Alabama 1,018 |
| 3 | Texas 920 | Alabama 989 | Ohio St. 1,005 |
| 4 | Penn St. 918 | Notre Dame 976 | Notre Dame 997 |
| 5 | Notre Dame 916 | Texas 975 | Texas 975 |
| 6 | Oklahoma 907 | Oklahoma 962 | Oklahoma 962 |
| 7 | Nebraska 896 | Penn St. 953 | Penn St. 953 |
| 8 | Ohio St. 882 | Nebraska 935 | Nebraska 935 |
| 9 | Georgia 878 | Georgia 908 | USC 909 |
| 10 | Tennessee 869 | USC 895 | Georgia 908 |
| 11 | LSU 830 | Tennessee 886 | Tennessee 896 |
| 12 | USC 807 | LSU 825 | LSU 860 |
| 13 | Clemson 795 | Clemson 818 | Clemson 818 |
| 14 | Auburn 783 | Auburn 812 | Auburn 809 |
| 15 | Texas A&M 775 | Texas A&M 799 | Texas A&M 799 |
| 16 | Georgia Tech 766 | West Virginia 794 | West Virginia 794 |
| 17 | Virginia Tech 746 | Washington 793 | Washington 792 |
| 18 | Florida 745 | Virginia Tech 785 | Virginia Tech 785 |
| 19 | Pittsburgh 727 | Pittsburgh 780 | Pittsburgh 780 |
| 20 | Wisconsin 721 | Florida 774 | Florida 774 |
| 21 | Arkansas 715 | Georgia Tech 773 | Georgia Tech 774 |
| 22 | Navy 711 | Navy 760 | Syracuse 768 |
| 23 | Syracuse 711 | Syracuse 757 | Navy 760 |
| 24 | Army 710 | Wisconsin 754 | North Carolina 757 |
| 25 | Minnesota 704 | Minnesota 752 | Wisconsin 753 |

Ours lists Arkansas and Army, which are not in the official top 25, and omits West Virginia and Washington. The order is wrong at the top: Alabama shown 1st (officially 3rd), Michigan 2nd (1st), Penn St. 4th (7th), Ohio St. 8th (2nd), USC 12th (10th).

## 6. Every other field in program_stats.json — usage and spot checks

Sample (same 10 for every field): Alabama, Michigan, Ohio St., Notre Dame, USC, Oklahoma St., Pittsburgh, Minnesota, Boise St., Toledo.

| Field | Used by | Source checked (as of) | Matches (of 10) | Verdict |
|---|---|---|---|---|
| `claimedNatChamps` (+`ranks`) | rank, compare, team, conference | Wikipedia "College football national championships in NCAA Division I FBS" → *Claims by school* (rev 1377269636) | **9/10** | **Ohio St. 8 vs 9** — missing the 2024 title. Oklahoma St. = 1 ✔ |
| `recognizedNatChamps` (+`ranks`) | rank, compare, team, conference | Site definition: "recognized by the NCAA or major selectors" → NCAA Records Book major selections (pp.120–125) / Wikipedia *Total selections from major selectors* and *Poll era (AP/Coaches)* tables | **4/10** vs AP/Coaches; **2/10** vs major-selector totals | **Follows no single definition.** Michigan 11 (AP/Coaches 3, major selectors 19), Pittsburgh 9 (2 / 11), USC 11 (7 / 17). **Oklahoma St. shows 0, but the Records Book lists "Oklahoma St.: AFCA — AFCA awarded Oklahoma St. the 1945 AFCA Trophy retroactively in 2016" (p.122) → must be 1** per your rule and the site's own definition |
| `confChamps` (+`ranks`) | rank, compare, team, conference | Wikipedia team infobox `ConfTitles` (sample articles, revs in `wiki_fields.json`) | **4/10** | **Gross errors: Boise St. 0 vs 23, Toledo 0 vs 15, Pittsburgh 21 vs 3** (Big East 2004, 2010; ACC 2021). Smaller: Alabama 33 vs 34, USC 39 vs 37, Minnesota 18 vs 20 (2 pre-Big Ten IAAN titles) |
| `bowlAppearances` (+`ranks`) | rank, compare, team | Wikipedia "List of NCAA Division I FBS football bowl records" (rev 1371724322, through 2025–26 bowls) | **5/10** | Ours higher for Alabama (85 vs 78), Ohio St. (61 vs 60), Notre Dame (46 vs 45), USC (59 vs 57), Toledo (25 vs 23) — likely counts CFP games that are not bowls and/or vacated bowls |
| `bowlRecord` | conference | same | **5/10** | Alabama 49-33-3 vs 46-30-3; Ohio St. 31-30 vs 30-30; Notre Dame 24-22 vs 23-22; USC 37-22 vs 36-21; Toledo 12-13 vs 12-11 |
| `bowlWinPct` (+`ranks`) | none (not read by any page) | derived | — | inherits bowlRecord errors |
| `allAmericans` (+`ranks`) — labelled **"Consensus All-Americans"** | rank, compare, team, conference | NCAA *Football Award Winners* (PDF created 2026-06-16), "Consensus All-Americans by School" pp.19–32 | **0/10** | Counts a different thing: USC 155 vs **86**, Ohio St. 148 vs **99**, Alabama 117 vs **87**, Pittsburgh 81 vs 55, Michigan 107 vs 89, Oklahoma St. 24 vs 21, Boise St. 0 vs 4, Toledo 0 vs 2 (Notre Dame 114 vs 113 closest). The category's #1 (USC) is wrong |
| `heismanWinners` (+`ranks`) | rank, compare, team, conference, rankings | Wikipedia team infoboxes (`Heismans`); field was rebuilt from a verified list in 3bbf60c | **10/10** | OK |
| `nflDraftPicks` (+`ranks`) | rank, compare, team, conference | Wikipedia "List of <school> in the NFL draft" — rows counted two ways, agreeing within 2 (includes 2026 draft) | **0/6 verified** (Ohio St., Notre Dame, USC, Minnesota tables not machine-countable — not verified) | Alabama 386 vs ~435, Michigan 368 vs ~429, Oklahoma St. 218 vs 177 (lead: 176), Pittsburgh 281 vs 304, **Boise St. 0 vs 75, Toledo 0 vs 62** |
| `firstRoundPicks` (+`ranks`) | rank, compare | same | **0/5 verified** | Alabama 71 vs 85 (lead: 86), Michigan 54 vs 57, Oklahoma St. 15 vs 21, Pittsburgh 39 vs 27, Boise St. 0 vs 6 |
| `weeksInPoll` (+`ranks`) | rank, compare, team | NCAA Records Book "Most Weekly Appearances in the AP Poll" (p.143, through 2025); CFBD AP polls recount | **0/5** vs Book (5 sample programs listed); 10/10 vs CFBD recount | CFBD's AP data is missing some weeks: Ohio St. 1,007 vs 1,016, Michigan 935 vs 943, Alabama 903 vs 907, Notre Dame 902 vs 907, USC 822 vs 830. Also frozen — 2026 polls not counted |
| `weeksAtOne` (+`ranks`) | rank, compare | NCAA Records Book "Most Weeks At No. 1 — All-Time" (p.142; excludes preseason) | **7/10** | Alabama 140 vs 141, Ohio St. 117 vs 120, USC 88 vs 91 (lower even though CFBD counts preseason polls → missing weeks) |
| `rankedRecords` (top25/top10/top5) | team (vs-ranked section), compare | No official published source; recomputed from CFBD games + AP polls (1936–2025) | **0/10** reproducible | Ours consistently lower (Alabama top-25 178-149-5 vs recomputed 186-160-6). Method undocumented; treat as unverified |
| `ranks.*` | team rank grid, compare tiles | derived | — | Every rank inherits its field's errors |

**Oklahoma St. national championship count:** `claimedNatChamps` = 1 (correct); `recognizedNatChamps` = **0 (wrong; should be 1)**. Not changed in this pass.


## 7. Where record figures appear on the site (full impact)

| Page | What shows | Field(s) |
|---|---|---|
| `rank.html` | **All-Time Wins** category (rows + values) and **All-Time Record** (win %) category | `record.wins`, `winPct` (ranks are recomputed on the page) |
| `team.html` | Hero all-time record line (W-L-T, win %) — overrides the game-file tally; National rank grid cards "All-Time Wins #N of 136" and "Win % #N" | `record`, `winPct`, `ranks.wins`, `ranks.winPct` |
| `compare.html` | Program Comparison tiles: All-Time Wins (value + rank), Win % (value + rank + W-L-T sub-line) | `record`, `winPct`, `ranks.wins`, `ranks.winPct` |
| `conference.html` | "All-Time Record" and "Win %" columns (sortable) | `record`, `winPct` |
| `rankings.html` (/rankings) | Hard-coded legacy per-category ranks incl. Win% (`cats[0]`) and Wins (`cats[5]`) plus a composite — **not read from program_stats**, will stay inconsistent unless regenerated | embedded `RANKINGS` |
| `rank.html` fallback paths | If `program_stats.json` fails, All-Time Wins falls back to `league.json` / the games file, which tally only head-to-head-dataset games (Alabama 867) — very different numbers | `data/derived/league.*.json` |
| `scripts/parity_check.js` | Holds rank.html All-Time Wins == `record.wins` | `record.wins` |
| `scripts/generate_sitemap.py` | `lastmod` for /rank and /conference | file mtime |

Not affected: index, games, teams, schedules, scoreboard, heisman.

## 8. Proposed fix — `scripts/build_program_records.py` (not implemented)

Replaces the record fields in `program_stats.json` with a reproducible build instead of patching the frozen values.

**Inputs (committed under `data/sources/records/`, each with URL, revision/sha256 and retrieval date):**
1. `wiki_fbs_wl_rev1271870786.json` — raw wikitext + parsed rows of the pinned Wikipedia revision (through 2024). `--verify-source` re-fetches that exact revid via the MediaWiki API (descriptive User-Agent) and fails if the parse differs.
2. `ncaa_records_book_2026.json` — the Book's p.110 all-time rows and p.111 2019–25 table, with PDF URL + sha256 (cross-check only).
3. `cfbd_records_<season>.json` — CFBD `/records` per completed season since the pinned baseline (2025 frozen), plus the current season (2026) refreshed every Tuesday. Key from repo secret; never printed.
4. `record_adjustments.json` — every vacated / forfeit / post-baseline ruling with season, W/L/T, side (penalized or opponent), source URL + revision, and a `decision` note where sources disagree (Michigan 1,021; Georgia Southern; Missouri St. baseline).

**Output (only these keys change; script aborts if any other field differs — same guard as `rebuild_heisman.py`):** `record` (official W-L-T), `winPct` (official, ties = ½), `recordOnField`, `winPctOnField`, `recordAsOf` {`throughSeason`, `throughDate`, `sources`}, `ranks.wins`, `ranks.winPct` (competition ranking over the 136). Proposal: pages show **official** as the primary figure (consistent with the standing rule that official sources outrank CFBD) with on-field as a secondary line where vacated wins exist — your call.

**Tuesday refresh (weekly_refresh.yml):** after `refresh_games.py`: `build_program_records.py` → `build_derived_data.py` → parity → commit → deploy (main only). Each week only the current-season CFBD file changes, so every program's total moves only by games actually played. Each January, after the bowls, a roll-forward freezes the finished season's CFBD file (and may re-pin Wikipedia to a newer end-of-season revision only if it reproduces the build's totals exactly).

**Checks (all fail-loud: no commit, no deploy, red run):**
- Book cross-check: built official totals through 2025 must equal the Records Book rows except the documented exceptions; built 2019–25 on-field minus vacated must equal the Book's decade table.
- Monotonic guard: no total may decrease vs the committed file unless `record_adjustments.json` changed in the same commit; no program may gain more games in a week than CFBD shows it played.
- `parity_check.js` gains a records block: rank.html All-Time Wins and All-Time Record rows, team.html hero/rank cards and compare.html tiles must all read the built values; `node scripts/build_program_records.py --check` (or the Python equivalent) must reproduce the committed file byte-for-byte in CI on every push.
- `front_porch_games.json` checksum unchanged.

**Media guides still to confirm before the build lands:** this audit checked 12 programs' 2026 guides (all source conflicts plus a cross-section). The other 114 programs that differ by >5 wins rest on Wikipedia+CFBD validated by the Records Book; confirming each against its guide can be done as part of building `record_adjustments.json`.
