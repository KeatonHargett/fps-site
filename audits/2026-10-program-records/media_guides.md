# Media-guide confirmation — all-time records through 2025

Every program the audit found >5 wins off was checked against its official school media guide / record book (2026 edition = through 2025 where published; 2025 editions compared through 2024). Sources: the schools' own PDFs only (no Sports Reference, no stats.ncaa.org, no third-party sites). The build's figures come from `scripts/build_program_records.py`; the NCAA Records Book (p.110) additionally confirms 33 programs exactly (Michigan excepted, documented).

**127 guide checks:** 50 match the official NCAA figure exactly, 2 match the on-field figure exactly, 32 are within 3 games, 28 differ by more than 3 games, 15 print no all-time total / no guide found.

## Resolved by documented decision (in `record_adjustments.json`)

| Program | Decision |
|---|---|
| Michigan | official 1,021-362-36 through 2025 (Records Book prints 1,022) |
| Delaware | Records Book 746-491-43 (guide internally inconsistent) |
| Georgia Southern | Records Book 432-264-10 (guide prints modern era only) |
| Ball St. | media guide 483-473-32 (internally consistent) |
| Western Kentucky | media guide 630-437-31 (internally consistent) |
| Missouri St. | 507-551-39 from the guide's year-by-year totals (Quick Facts 507-542-39 is a typo; no Records Book row) - documented exception |
| Air Force | keep the reconstruction 442-357-13 through 2025 (pinned Wikipedia + CFBD 2025) |
| Mississippi St. | keep the reconstruction: official 593-627-39, on field 618-609-40 through 2025 |

## Differ by more than 3 games (not changed - NCAA official figure kept)

Most are counting-convention differences the guides themselves describe (club / rugby / junior-college / non-collegiate games, on-field vs official, stale tables). Each needs a source-by-source review before any override.

| Program | Guide prints (alt) | Thru | Records Book p.110 | Official (built) | On field (built) | Guide notes | Source |
|---|---|---|---|---|---|---|---|
| Appalachian St. | 673-370-28 | 2025 | confirms built: 674-368-29 | 674-368-29 | 674-368-29 | Prints 'All-Time Record ....673-370-28 (96 seasons completed)', First Year 1928. No year-by-year total row found in the text. No vacated/forfeit footnote. 96 seasons since 1928 nec | [guide](https://appstatesports.com/documents/2026/7/17/FB_2026_MediaGuide.pdf) |
| Baylor | 643-614-44 | 2025 | not listed | 638-614-44 | 638-614-44 | Quick Facts 'All-Time Football Record: 643-614-44 (.511)'; decade table '125-YEAR TOTALS 1,301 643 614 44 .511' (2010-2019 decade printed 83-47-0). No vacated/forfeit footnote on t | [guide](https://baylorbears.com/documents/2026/8/19/BU_FB_2026_Media_Almanac_081926_web_version.pdf) |
| California | 707-578-51 (793-606-62) | 2025 | not listed | 705-582-51 | 709-582-51 | OVERALL RECORDS table: 'NCAA Recognized 707 578 51 .548'; 'Rugby 86 22 11'; 'All-Time 793 606 62 .564' (the All-Time line adds the 1906-14 rugby seasons). Footnote under the year-b | [guide](https://calbears.com/documents/download/2026/8/7/2026_Cal_Football_Info_Guide.pdf) |
| Connecticut | 536-608-38 | 2025 | not listed | 539-617-38 | 539-617-38 | Only total printed is the unlabeled bottom row of the All-Time Coaching Records table: '1182 536 608 38 .453' (games, W, L, T, pct), covering 1896-2025 incl. Gordon Sammis (interim | [guide](https://uconnhuskies.com/documents/2026/9/5/2026_UConn_Football_History___Record_Book.pdf) |
| East Carolina | 481-463-11 | 2025 | not listed | 477-463-12 | 477-463-12 | Footnote: "1986 Temple game and 1989 Louisiana Tech game were forfeited to ECU due to use of an ineligible player. The school and coaching records reflect this change." Totals cove | [guide](https://ecupirates.com/documents/download/2026/8/14/2026_ECU_Football_Record_Book.pdf) |
| Indiana | 536-716-45 | 2025 | not listed | 534-715-44 | 533-716-44 | 'OVERALL RECORD 536-716-45 - 139 Years (1885-)' printed after the 2025 (16-0) season. Results pages mark games 'Game later forfeited to IU' (PDF pp.5, 18) and '# - later forfeited  | [guide](https://static.iuhoosiers.com/custompages/PDF/FB/2026/26-FB-Record_Book.pdf) |
| Jacksonville St. | 632-407-40 (631-408-40) | 2025 | not listed | 630-432-39 | 630-432-39 | Quick Facts: 'All-Time Record: 632-407-40', 'Modern Era (Since 1947): 526-296-17'. Coaching records: 'OVERALL 631 408 40 .607'. These disagree with each other, and both differ a lo | [guide](https://jaxstatesports.com/documents/2026/8/24/2026FootballMediaGuide.pdf) |
| James Madison | 390-231-4 | 2025 | confirms built: 390-227-4 | 390-227-4 | 390-227-4 | Both totals agree. Covers all seasons since 1972, including D-III, D-II, I-AA and FCS years. Losses differ from the batch-list NCAA figure (227). | [guide](https://jmusports.com/documents/2026/7/8/2026_Football_Media_Guide.pdf) |
| Marshall | 620-556-35 (620-566-35) | 2025 | not listed | 643-581-47 | 643-581-47 | Book states: 'The records listed herein are only from games against college competition.' The year-by-year table (PDF p.2, 1895-2025, includes I-AA/Southern Conference years) has n | [guide](https://herdzone.com/documents/download/2026/7/31/2026_Marshall_Football_Record_Book.pdf) |
| Missouri | 722-596-52 | 2025 | not listed | 729-598-52 | 738-598-52 | Footnote p.93: '&Wins vacated by NCAA; on field record in 2015 and 2016 was 5-7 and 4-8, respectively' (the ledger lists 2015 as 0-7-0 and 2016 as 0-8-0). p.94: 'MU vacated five wi | [guide](https://mutigers.com/documents/c5eb61c5-88b5-4fd8-89e0-fbbb14e2d4fd.pdf) |
| North Carolina St. | 656-614-55 | 2025 | not listed | 652-611-55 | 652-611-55 | The two printed figures agree. No vacated or forfeit footnote attached to the total. | [guide](https://gopack.com/documents/2026/7/14/2026NCStateFootball.pdf) |
| Oklahoma St. | 643-595-48 | 2025 | not listed | 641-592-48 | 641-592-48 | All printed totals agree. No quick-facts all-time line found. Forfeits counted as OSU wins: 1922 Tulsa '(win by forfeit) W 1-0'; 1972 at Oklahoma '^ Oklahoma later forfeited, handi | [guide](https://okstate.com/documents/2026/7/6/2026_Oklahoma_State_Football_Media_Guide.pdf) |
| Oregon St. | 576-646-50 (574-636-50) | 2025 | not listed | 571-646-50 | 570-647-50 | Quick facts and the coaching-records total agree (576-646-50). The year-by-year table total in the same Section 7 PDF prints 574-636-50, a gap of 2 W and 10 L. Section 7 URL: https | [guide](https://osubeavers.com/documents/2026/8/23/Section_1_-_Rosters.pdf) |
| Rice | 490-635-32 | 2025 | not listed | 501-668-32 | 500-669-32 | The only all-time total printed is in the series-records table: 'College Opponents 482-628-31 / Other Opponents 8-7-1 / All Opponents 490-635-32'. The year-by-year All-Time Record  | [guide](https://riceowls.com/documents/download/2026/8/22/2026_Factbook_work_copy.pdf) |
| Sam Houston St. | 576-500-36 | 2025 | not listed | 583-501-34 | 583-501-34 | The file path is dated 2022, but the cover reads 'UPDATED JANUARY 2026' and the book includes Phil Longo 2025 (2-10). Covers all 110 seasons, including NAIA, D-II, I-AA and FCS yea | [guide](https://gobearkats.com/documents/2022/11/21/records_football.pdf) |
| San José St. | 523-547-38 | 2025 | not listed | 527-554-38 | 526-555-38 | Series 'Totals 1893 2025 ... 523-547-38+' with footnotes '* - record later changed by action of the conference. Only on-the-field results are counted.' and '+ - includes on-the-fie | [guide](https://storage.googleapis.com/san-jose-state-prod/2026/06/03/fqCR7BEO62BBaTnXaRSJBXZehhE8QNKaixN6l7ju.pdf) |
| Southern Miss | 625-479-27 | 2025 | not listed | 621-477-26 | 618-480-26 | All three totals agree; covers 109 seasons back to 1912. Series footnote: '*Includes one forfeit / **Includes two forfeits'. Series pages note '# Mississippi State forfeited the ga | [guide](https://southernmiss.com/documents/2026/7/15/2026_Southern_Miss_Football_Record_Book.pdf) |
| Stanford | 771-533-52 (767-525-52) | 2025 | not listed | 677-513-49 | 677-513-49 | CONFLICT INSIDE GUIDE. The year-by-year table runs through 2025 (Frank Reich 4-8) and totals 771-533-52 over 131 seasons. The coaching-records table ends with 'Troy Taylor 2023-24' | [guide](https://gostanford.com/documents/0d8ced6e-145f-4cd0-84af-1ef0c7902e4b.pdf) |
| Temple | 495-639-52 | 2025 | not listed | 502-633-52 | 502-633-52 | Printed total is well below the batch list (502-633-52). No vacated/forfeit footnote found. | [guide](https://owlsports.com/documents/download/2026/7/16/2026_R_F_Book.pdf) |
| Texas St. | 579-534-33 | 2025 | not listed | 548-511-25 | 548-511-25 | Totals begin with 1904 (5-1, including games vs. high schools and academies) and 1908-21 independent seasons. Section headers note 'NAIA (1932-1957); NCAA COLLEGE DIVISION (1958-72 | [guide](https://txst.com/documents/2026/2/1/2026_Record_Book.pdf) |
| Tulane | 583-684-38 | 2025 | not listed | 585-680-38 | 586-679-38 | '132 Years, 42 Coaches Overall Record: 583-684-38 ... *includes one or more NCAA-mandated forfeits'. The series page carries the same footnote, and the coaching page says '*include | [guide](https://tulanegreenwave.com/documents/2026/8/26/Complete.pdf) |
| Tulsa | 666-560-32 | 2025 | not listed | 654-551-27 | 654-551-27 | Totals agree. The results pages count forfeits as wins ('Claremore High (forfeit) W 1-0'; '†Kansas later forfeited game to Tulsa') and include games against non-collegiate opponent | [guide](https://tulsahurricane.com/documents/2026/8/28/2026_Football_MG.pdf) |
| UTEP | 419-655-28 | 2025 | not listed | 415-653-30 | 415-653-30 | Year-by-year totals from 1914. No quick-facts all-time line was found (team information gives only the 2025 record). No vacated or forfeit footnote. | [guide](https://utepminers.com/documents/2026/8/4/2026_UTEP_FB_Media_Guide.pdf) |
| Utah St. | 592-585-31 | 2025 | not listed | 583-582-31 | 581-584-31 | Both totals agree; no quick-facts all-time line found. Counts the 1972 Oklahoma game as a 2-0 win: '*Game forfeited by Oklahoma (L 0-49)'. No vacated footnote. | [guide](https://utahstateaggies.com/documents/2026/8/25/2026_USU_FB_Media_Guide.pdf) |
| Washington St. | 591-593-45 | 2025 | not listed | 587-597-45 | 587-597-45 | One total printed. Year-by-year results note Pac-10-ordered forfeits counted as WSU wins: '* = Game later forfeited to WSU by order of Pacific-10 Conference' (late 1970s). No vacat | [guide](https://wsucougars.com/documents/b976304f-b243-40e2-b8b7-56baae1fcaa4.pdf) |

## Within 3 games

| Program | Guide prints (alt) | Thru | Records Book p.110 | Official (built) | On field (built) | Source |
|---|---|---|---|---|---|---|
| Arizona St. | 636-427-24 | 2024 | confirms built: 647-432-24 | 639-427-24 | 649-427-24 | [guide](https://thesundevils.com/documents/a9c21c74-aed0-4b03-a61f-829b03c288e3.pdf) |
| Arkansas St. | 511-537-37 (519-535-37) | 2025 | not listed | 511-536-37 | 521-536-37 | [guide](https://astateredwolves.com/documents/2026/8/10/2026_Arkansas_State_Football_Media_Guide_Reduced_Size.pdf) |
| Boise St. | 713-255-12 (512-193-2) | 2025 | confirms built: 511-194-2 | 511-194-2 | 511-194-2 | [guide](https://broncosports.com/documents/2026/7/22/2026_Boise_State_Football_Record_Book.pdf) |
| Boston College | 703-540-37 | 2025 | not listed | 703-541-37 | 703-541-37 | [guide](https://bceagles.com/documents/download/2026/8/14/2026_BCFB_MEDIA_GUIDE.pdf) |
| Cincinnati | 674-620-51 (674-621-50) | 2025 | not listed | 671-620-51 | 671-620-51 | [guide](https://gobearcats.com/documents/1f5f8e61-50ca-4a12-8fb5-efb36af00905.pdf) |
| Colorado St. | 548-621-33 | 2024 | not listed | 547-621-33 | 547-621-33 | [guide](https://csurams.com/documents/2025/8/25/2025_Media_Guide.pdf) |
| Florida St. | 600-298-17 | 2025 | confirms built: 588-298-17 | 588-298-17 | 599-299-17 | [guide](https://seminoles.com/documents/2026/7/13/8_-_Records.pdf) |
| Fresno St. | 660-460-27 (661-460-27) | 2025 | not listed | 660-457-27 | 658-459-27 | [guide](https://gobulldogs.com/documents/2026/8/17/1._2026_Intro.pdf) |
| Hawaii | 598-503-25 (434-446-9) | 2025 | not listed | 597-503-25 | 597-503-25 | [guide](https://hawaiiathletics.com/documents/2026/8/24/2026_FB_Media_Guide_Web.pdf) |
| Illinois | 651-632-51 | 2025 | not listed | 651-632-50 | 651-632-50 | [guide](https://fightingillini.com/documents/2026/8/28/4-Record_Book-2026.pdf) |
| Iowa | 707-584-39 | 2025 | not listed | 706-585-39 | 710-585-39 | [guide](https://storage.googleapis.com/hawkeyesports-prod/2026/08/17/mY7U4aafGvGu5XNBhXGcYoKBH4pSLg0EkwJW4nkj.pdf) |
| Kansas | 616-693-58 | 2025 | not listed | 615-693-58 | 615-693-58 | [guide](https://kuathletics.com/documents/2026/7/31/07312026_Kansas_Football_Media_Guide.pdf) |
| Kansas St. | 585-681-41 | 2025 | not listed | 585-680-42 | 584-681-42 | [guide](https://www.kstatesports.com/documents/2026/7/7/2026_K-State_Football_Media_Guide.pdf) |
| Louisiana Monroe | 335-480-8 | 2025 | not listed | 333-480-8 | 333-480-8 | [guide](https://ulmwarhawks.com/documents/2026/9/5/2026_ULM_Football_Media_Guide.pdf) |
| Louisville | 568-505-17 | 2025 | not listed | 568-504-17 | 566-506-17 | [guide](https://files.provationsgroupcdn.com/publications/Louisville-Football-Guide-2026/docs/Louisville-Football-Guide-2026.pdf) |
| Memphis | 543-541-33 (501-521-33) | 2024 | not listed | 544-539-33 | 543-540-33 | [guide](https://gotigersgo.com/documents/2025/9/6/25_Football_Record_Book.pdf) |
| Middle Tennessee | 611-472-28 | 2024 | not listed | 610-472-28 | 610-472-28 | [guide](https://goblueraiders.com/documents/download/2025/7/18/2025_Record_Book.pdf) |
| New Mexico | 513-650-31 | 2025 | not listed | 513-651-31 | 513-651-31 | [guide](https://storage.googleapis.com/golobos-prod/2026/09/02/s7lwwTTGa3LwemXXxQOxiCwr83MuBRrTrDcv4RRa.pdf) |
| New Mexico St. | 463-687-30 (459-679-30) | 2025 | not listed | 462-688-30 | 461-689-30 | [guide](https://nmstatesports.com/documents/2026/8/14/2026_Football_Media_Guide.pdf) |
| North Texas | 561-550-34 | 2025 | not listed | 560-550-33 | 558-552-33 | [guide](https://meangreensports.com/documents/2026/8/26/UNT_FB_2026_Media_Almanac.pdf) |
| Northwestern | 579-717-44 | 2025 | not listed | 577-716-44 | 576-717-44 | [guide](https://storage.googleapis.com/nusports-com-prod/2026/08/24/wQKYqLO9F7myWi7owtyqW1GXeTnSwW9aTSyM6XND.pdf) |
| Penn St. | 950-418-42 | 2025 | confirms built: 950-418-41 | 950-418-41 | 950-418-41 | [guide](https://gopsusports.com/documents/4d144510-9ba5-4b25-bed1-35711e8d460e.pdf) |
| TCU | 705-582-56 | 2025 | not listed | 703-582-57 | 703-582-57 | [guide](https://gofrogs.com/documents/2026/7/31/2026_TCU_Football_Media_Guide.pdf) |
| Tennessee | 883-423-54 (894-423-54) | 2025 | confirms built: 883-422-53 | 883-422-53 | 893-422-54 | [guide](https://utsports.com/documents/2026/7/24/Volmanac_Section__Web_.pdf) |
| Toledo | 597-461-24 | 2025 | not listed | 596-462-24 | 595-463-24 | [guide](https://utrockets.com/documents/2026/8/20/2026_Toledo_football_media_guide.pdf) |
| Troy | 588-444-28 | 2025 | not listed | 587-445-28 | 587-445-28 | [guide](https://troytrojans.com/documents/download/2026/7/14/2026_Troy_Football_Record_Book_R.pdf) |
| UAB | 180-204-2 | 2025 | not listed | 179-204-2 | 179-204-2 | [guide](https://uabsports.com/documents/2026/7/16/2026_UAB_Football_Media_Guide.pdf) |
| UCF | 304-248-1 | 2025 | not listed | 302-249-1 | 302-249-1 | [guide](https://storage.googleapis.com/ucfknights-com-prod/2026/09/10/p5MTXAzi7KjOpmNotvRy3Yib0KERZ9TbJdNa9eYN.pdf) |
| UMass | 582-661-51 (584-672-51) | 2025 | not listed | 582-661-50 | 582-661-50 | [guide](https://umassathletics.com/documents/download/2026/6/18/2026_Football_RecordBook.pdf) |
| UNLV | 291-376-4 | 2025 | not listed | 273-393-4 | 291-375-4 | [guide](https://s3.us-east-2.amazonaws.com/sidearm.nextgen.sites/unlvrebels.com/documents/2026/7/14/2026_UNLV_Football_Record_Book__ONLINE_.pdf) |
| Wyoming | 574-615-28 | 2025 | not listed | 572-616-28 | 572-616-28 | [guide](https://gowyo.com/documents/2026/7/9/2026_Wyoming_Football_Media_Guide.pdf) |

## Exact matches

Alabama, Arizona, Arkansas, Army, Auburn, Ball St., Bowling Green, Central Michigan, Clemson, Coastal Carolina, Colorado, Duke, Eastern Michigan, Florida, Georgia, Houston, Iowa St., Kent St., Kentucky, LSU, Maryland, Miami (OH), Michigan, Michigan St., Minnesota, Missouri St., Nebraska, Nevada, North Carolina, Northern Illinois, Notre Dame (on field), Ohio St., Oklahoma, Oregon, Pittsburgh, Purdue, San Diego St., South Carolina (on field), South Florida, Syracuse, Texas, Texas A&M, Texas Tech, UCLA, USC, Utah, Vanderbilt, Virginia, Wake Forest, West Virginia, Western Kentucky, Wisconsin

## No all-time total printed / no guide found

| Program | Records Book p.110 | Note |
|---|---|---|
| Akron | not listed | Tried: WebSearch x3 (2026 media guide gozips; gozips.com-restricted record book/media guide 2025/2026; '2025/2026 Media Guide' Akron), the gozips.com/sports/foo |
| Buffalo | not listed | NOT FOUND: the 2026 Info Guide prints year-by-year records through 2025, coaches ranked by wins and all-time series records, but no all-time W-L-T total anywher |
| Georgia Tech | confirms 772-550-43 | Not found. The '2026 GT Football Info Guide' link on ramblinwreck.com game previews returns HTTP 404, and guessed storage URLs failed. Checked the 2025 GT FB In |
| Liberty | not listed | NOT FOUND. Tried: (1) the football media-guides page, which lists guides only through 2021 and says full guides were discontinued; (2) the 'History and Records' |
| Louisiana Lafayette | not listed | NOT FOUND: the ragincajuns.com football schedule and football pages link no media guide or record book. Searches (4) returned only weekly game notes and old gui |
| Louisiana Tech | not listed | NOT FOUND. Tried: latechsports.com football page and Media Center; the 'Football Record Book' page (latechsports.com/sports/2018/7/20/_m_footbl_media_guides_htm |
| Miami | confirms 686-394-19 | NOT FOUND. No 2026 media guide is linked on miamihurricanes.com/sports/football; only the 2025 guide is, at https://storage.googleapis.com/hurricanesports-com/2 |
| Navy | not listed | NOT FOUND in the extractable text. Searched All-Time Coaching Records (printed p.160, no total row), All-Time Scores (pp.170-179, season lines only) and the sch |
| Ohio | not listed | NOT FOUND in a guide: the record book runs through 2025 ('2025 (9-4 ...)', Hauser 1-0 in the bowl) but prints no all-time W-L-T total. No 2026 media guide is po |
| Old Dominion | not listed | Not found. The 2026 ODU media guide (linked as 'Media Guide' from odusports.com/sports/football) prints season-by-season results 2009-2025 (PDF pp.131-133) and  |
| Rutgers | not listed | NOT FOUND. The 2026 guide (121 PDF spreads) prints 'First Year of Football 1869', the 'All-Time Bowl Record 7-6', season-by-season All-Time Results (printed pp. |
| South Alabama | not listed | NOT FOUND as a printed total. The 2026 guide prints season records 2009-2025 and each coach's W-L (Jones 52-50, Wommack 22-16, Applewhite 11-14, Campbell 9-26)  |
| Virginia Tech | confirms 781-521-46 | NOT FOUND: the hokiesports.com 'Media Guides' page (football-media-guides-in-pdf-format) only goes up to the 2022 guide. The 'Record Book' link points to the st |
| Washington | confirms 790-477-50 | NOT FOUND IN DOCUMENT: the 180-page 2026 guide prints no all-time W-L-T total (Quick Facts gives only 2025 record and coach records; year-by-year pages give per |
| Western Michigan | not listed | NOT FOUND. Tried: (1) the wmubroncos.com football page, whose only football PDFs are 2026 game notes, programs and stats; (2) the athletic media-relations page  |
