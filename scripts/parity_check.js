#!/usr/bin/env node
/*
 * Front Porch Sports - parity check for data/derived/ (run after build_derived_data.py).
 *
 * Proves the derived files give every page exactly what front_porch_games.json gave it.
 * No dependencies; loads the real js/matchup-filter.js and js/derived-data.js in a VM.
 *
 *   1. Records   every team file decodes (FPSData.decodeTeam) to the same 16 fields as the
 *                original rows, in the same order, with the same location / coaches / venue
 *                the old loaders produced from game_sites.json, coaches_data.json and
 *                game_venues.json (via FPSMatchupFilter.annotate*).
 *   2. Pairs     200+ team pairs (named rivalries, NDSU, Sacramento St., never-met pairs and a
 *                seeded random sample): meetings, W/L/T, series leader, current streak, largest
 *                margins, longest streaks, H2H chart data, Record (Winning %) chart data and
 *                all-time game counts, computed with compare.html's own functions on the old
 *                data and on the merged two-team derived data.
 *   3. Filters   for each pair, every year-range x location x coach x last-N combination run
 *                through FPSMatchupFilter.filterGames on both: same games, same missing counts.
 *   4. Pages     rank.html / team.html / compare.html league ranks and fallbacks, teams.html
 *                team list, index.html hero counts + Blue Bloods cards, games.html END default.
 *
 * Exit 1 on any mismatch (the weekly workflow then stops before commit / deploy).
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');
const readJSON = f => JSON.parse(read(f));
const DERIVED = 'data/derived/';

let checks = 0;
const mismatches = [];
function eq(label, a, b) {
  checks++;
  const sa = JSON.stringify(a), sb = JSON.stringify(b);
  if (sa !== sb) {
    mismatches.push(label);
    if (mismatches.length <= 25) console.log(`MISMATCH ${label}\n   old: ${sa.slice(0, 300)}\n   new: ${sb.slice(0, 300)}`);
  }
}

// ---- load the browser modules -----------------------------------------------------------
function loadModules() {
  const ctx = { window: {}, console, fetch: () => Promise.reject(new Error('no fetch in parity check')) };
  ctx.window.window = ctx.window;
  vm.createContext(ctx);
  vm.runInContext(read('js/matchup-filter.js'), ctx);
  vm.runInContext(read('js/derived-data.js').replace(/\(typeof window !== 'undefined' \? window : this\)\s*;\s*$/, '(window);'), ctx);
  return { MF: ctx.window.FPSMatchupFilter, FD: ctx.window.FPSData };
}

// ---- compare.html functions, verbatim ----------------------------------------------------
function longestStreak(games, team) {
  const sorted = [...games].sort((a,b)=>a.game_date.localeCompare(b.game_date));
  let best = 0, cur = 0, bestStart = null, bestEnd = null, curStart = null;
  for (const g of sorted) {
    if (g.winner === team) {
      if (cur === 0) curStart = g.season;
      cur++;
      if (cur > best) { best = cur; bestStart = curStart; bestEnd = g.season; }
    } else { cur = 0; }
  }
  return { length: best, start: bestStart, end: bestEnd };
}
function largestMargin(games, team) {
  let best = { margin: 0, season: null, score: '' };
  for (const g of games) {
    if (g.winner !== team) continue;
    const m = Math.abs(g.margin);
    if (m > best.margin) {
      const wScore = Math.max(g.team_a_score, g.team_b_score);
      const lScore = Math.min(g.team_a_score, g.team_b_score);
      best = { margin: m, season: g.season, score: `${wScore}-${lScore}` };
    }
  }
  return best;
}
function currentH2HStreak(games) {
  const all = games.slice().sort((a, b) => b.game_date.localeCompare(a.game_date));
  if (all.length === 0) return null;
  if (all[0].is_tie) return { count: 0, team: null, startYear: all[0].season, endYear: all[0].season, tied: true };
  const streakTeam = all[0].winner;
  let count = 0, startYear = null, endYear = null;
  for (const g of all) {
    if (g.winner === streakTeam) { count++; if (endYear === null) endYear = g.season; startYear = g.season; }
    else break;
  }
  return { count, team: streakTeam, startYear, endYear, tied: false };
}
// compare.html's pair / team indexes (buildGameIndexes)
function indexes(GAMES) {
  const pairKey = (a, b) => (a < b ? a + '\u0000' + b : b + '\u0000' + a);
  const PAIR = new Map(), TEAM = new Map();
  for (const g of GAMES) {
    const k = pairKey(g.team_a, g.team_b);
    let arr = PAIR.get(k); if (!arr) PAIR.set(k, arr = []); arr.push(g);
    let ta = TEAM.get(g.team_a); if (!ta) TEAM.set(g.team_a, ta = []); ta.push(g);
    if (g.team_b !== g.team_a) { let tb = TEAM.get(g.team_b); if (!tb) TEAM.set(g.team_b, tb = []); tb.push(g); }
  }
  return { pair: (a, b) => PAIR.get(pairKey(a, b)) || [], team: t => TEAM.get(t) || [] };
}
function seasonWinPct(teamGamesArr, team) {
  const bySeason = {};
  teamGamesArr.forEach(g => {
    const s = g.season;
    const r = bySeason[s] = bySeason[s] || {w:0,l:0,t:0};
    if (g.is_tie) r.t++; else if (g.winner === team) r.w++; else r.l++;
  });
  return bySeason;
}
function winPctChart(idx, t1, t2, startYear, endYear) {
  const s1 = seasonWinPct(idx.team(t1), t1), s2 = seasonWinPct(idx.team(t2), t2);
  const allSeasons = [...new Set([...Object.keys(s1), ...Object.keys(s2)].map(Number))]
    .filter(y => y >= startYear && y <= endYear).sort((a,b)=>a-b);
  const recordOf = (bySeason, yr) => { const r = bySeason[yr]; if (!r) return null; const tot = r.w+r.l+r.t;
    return { pct: tot ? (r.w + r.t*0.5)/tot : null, rec: `${r.w}-${r.l}${r.t?'-'+r.t:''}` }; };
  return { labels: allSeasons,
    d1: allSeasons.map(y => { const x = recordOf(s1,y); return x?x.pct:null; }),
    d2: allSeasons.map(y => { const x = recordOf(s2,y); return x?x.pct:null; }),
    rec1: allSeasons.map(y => { const x = recordOf(s1,y); return x?x.rec:''; }),
    rec2: allSeasons.map(y => { const x = recordOf(s2,y); return x?x.rec:''; }) };
}
function totalGamesAllTime(GAMES, team) {
  const c = {};
  for (const g of GAMES) { c[g.team_a] = (c[g.team_a] || 0) + 1; c[g.team_b] = (c[g.team_b] || 0) + 1; }
  return c[team] || 0;
}
function headerMetrics(games, t1, t2) {
  const t1Wins = games.filter(g => g.winner===t1).length, t2Wins = games.filter(g => g.winner===t2).length;
  const ties = games.filter(g => g.is_tie).length, total = games.length;
  const leader = t1Wins>t2Wins ? t1 : t2Wins>t1Wins ? t2 : null;
  const recordStr = leader ? `${leader} leads ${Math.max(t1Wins,t2Wins)}-${Math.min(t1Wins,t2Wins)}${ties?'-'+ties:''}`
                           : `Series tied ${t1Wins}-${t2Wins}${ties?'-'+ties:''}`;
  const sorted = [...games].sort((a,b)=>a.game_date.localeCompare(b.game_date));
  return { total, t1Wins, t2Wins, ties, recordStr, streak: currentH2HStreak(games),
    m1: largestMargin(games, t1), m2: largestMargin(games, t2), s1: longestStreak(games, t1), s2: longestStreak(games, t2),
    h2hLabels: sorted.map(g => g.season),
    h2hData: sorted.map(g => g.is_tie ? 0 : (g.winner === t1 ? Math.abs(g.margin) : -Math.abs(g.margin))),
    ids: games.map(g => g.game_id) };
}
// League-wide loops (compare.html buildWinsRank/buildWinPctRank, team.html same,
// rank.html liveWins/liveWinPct), verbatim, over a games array...
function winsRankFromGames(GAMES) {
  const counts = {};
  GAMES.forEach(g => { if (g.is_tie) return; counts[g.winner] = (counts[g.winner] || 0) + 1; });
  return rankWins(counts);
}
function recsFromGames(GAMES) {
  const recs = {};
  GAMES.forEach(g => {
    [g.team_a, g.team_b].forEach(t => { if (!recs[t]) recs[t] = { w: 0, l: 0, t: 0 }; });
    if (g.is_tie) { recs[g.team_a].t++; recs[g.team_b].t++; }
    else if (g.winner === g.team_a) { recs[g.team_a].w++; recs[g.team_b].l++; }
    else if (g.winner === g.team_b) { recs[g.team_b].w++; recs[g.team_a].l++; }
  });
  return recs;
}
// ...and the same reductions from league.json (what the pages now do).
function winsFromLeague(L) { const counts = {}; L.wins.forEach(([t, w]) => { counts[t] = w; }); return counts; }
function recsFromLeague(L) { const recs = {}; L.records.forEach(([t, w, l, ti]) => { recs[t] = { w, l, t: ti }; }); return recs; }
function rankWins(counts) {
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const rank = {}; sorted.forEach(([team, w], i) => { rank[team] = { value: w, rank: i + 1 }; });
  return { rank, total: sorted.length, order: sorted.map(x => x[0]) };
}
function rankPct(recs) {
  const q = Object.entries(recs).map(([team, r]) => ({ team, g: r.w + r.l + r.t, pct: (r.w + 0.5 * r.t) / Math.max(1, r.w + r.l + r.t) }))
    .filter(x => x.g >= 50).sort((a, b) => b.pct - a.pct);
  const rank = {}; q.forEach((x, i) => { rank[x.team] = { value: x.pct, rank: i + 1 }; });
  return { rank, total: q.length, order: q.map(x => x.team) };
}
function liveWinPct(recs) {   // rank.html
  const out = {};
  Object.entries(recs).forEach(([team, r]) => { const tot = r.w + r.l + r.t; if (tot >= 50) out[team] = { pct: (r.w + 0.5 * r.t) / tot, games: tot, w: r.w, l: r.l, t: r.t }; });
  return out;
}

// ---- rank.html's own category code, lifted from the page source ------------------------------
// Pulls `const NAME = {...};` / `function NAME(...) {...}` out of rank.html by brace matching
// (string-aware), so this runs exactly what the page runs - not a copy that could drift.
function liftDecl(src, head) {
  const start = src.indexOf(head);
  if (start < 0) throw new Error('rank.html: cannot find ' + head);
  let i = src.indexOf('{', start), depth = 0, quote = null;
  for (; i < src.length; i++) {
    const c = src[i];
    if (quote) { if (c === '\\') { i++; continue; } if (c === quote) quote = null; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) break;
  }
  let end = i + 1;
  if (src[end] === ';') end++;
  return src.slice(start, end);
}
function checkRankCategories(OLD, league) {
  const src = read('rank.html');
  const code = [
    liftDecl(src, 'const TEAM_STATS = {'), liftDecl(src, 'const CATEGORIES = {'), liftDecl(src, 'const PS_KEY_MAP = {'),
    'let _winsCache = null;', liftDecl(src, 'function liveWins()'),
    'let _winPctCache = null;', liftDecl(src, 'function liveWinPct()'),
    liftDecl(src, 'function buildRows()'),
    // one-line array literal (liftDecl matches braces only)
    src.slice(src.indexOf('const HIDDEN_CATEGORIES = ['), src.indexOf('\n', src.indexOf('const HIDDEN_CATEGORIES = ['))),
    'this.__run = (slug, ps, lg, games, fbs, b) => { currentCatSlug = slug; PROGRAM_STATS = ps; LEAGUE = lg; GAMES = games; TEAMS_LIVE = fbs;' +
    ' basis = b || "official"; _winsCache = null; _winPctCache = null; return buildRows(); };' +
    ' this.__cats = Object.keys(CATEGORIES); this.__hidden = HIDDEN_CATEGORIES.slice();' +
    ' this.__basisCats = Object.keys(CATEGORIES).filter(k => CATEGORIES[k].basis);',
  ].join('\n');
  const ctx = { currentCatSlug: null, PROGRAM_STATS: null, LEAGUE: null, GAMES: [], TEAMS_LIVE: [], basis: 'official' };
  vm.createContext(ctx);
  vm.runInContext('var currentCatSlug, PROGRAM_STATS, LEAGUE, GAMES, TEAMS_LIVE, basis;\n' + code, ctx);
  const ps = readJSON('program_stats.json');
  const fbs = (readJSON('fbs_teams.json').teams || []).map(t => t.name);
  let rows = 0;
  // 7 visible categories; the 5 unverified ones stay hidden until rebuilt from sources.
  const HIDDEN = ['conference-championships', 'bowl-games', 'all-americans', 'nfl-draft-picks', 'first-round-nfl-draft-picks'];
  eq('rank.html visible categories', ['all-time-record', 'claimed-national-championships', 'recognized-national-championships',
    'all-time-wins', 'heisman-winners', 'weeks-in-poll', 'weeks-at-ap-number-one'], ctx.__cats);
  eq('rank.html hidden categories (not in navigation)', HIDDEN, ctx.__hidden.filter(s => !ctx.__cats.includes(s)));
  eq('rank.html official/on-field toggle categories', ['all-time-record', 'all-time-wins'], ctx.__basisCats);
  for (const slug of ctx.__cats) {
    // three data paths: program_stats (normal), league.json fallback, full-games fallback
    const run = (label, args) => {
      try { return ctx.__run(slug, ...args); }
      catch (e) { eq(`rank.html ${slug} (${label}) runs without throwing`, 'ok', String(e && e.message || e)); return null; }
    };
    const main = run('program_stats', [ps, league, [], fbs]);
    const onField = ctx.__basisCats.includes(slug) ? run('program_stats on field', [ps, league, [], fbs, 'onfield']) : main;
    const viaLeague = run('league.json fallback', [null, league, [], fbs]);
    const viaGames = run('full-games fallback', [null, null, OLD, fbs]);
    if (!main || !onField || !viaLeague || !viaGames) continue;
    const plain = r => r.map(x => [x.team, x.value, x.rank]);
    for (const [label, rs] of [['official', main], ['on field', onField]]) {
      checks++;
      if (!rs.length) { mismatches.push(`rank.html ${slug} ${label}: no rows`); console.log(`MISMATCH rank.html ${slug} ${label}: no rows`); }
      eq(`rank.html ${slug} (${label}): values numeric, no _meta row, ranks consistent`,
        true, rs.every((x, i) => typeof x.value === 'number' && isFinite(x.value) && x.team !== '_meta' &&
          (i === 0 ? x.rank === 1 : (x.value === rs[i - 1].value ? x.rank === rs[i - 1].rank : x.rank === i + 1))));
    }
    eq(`rank.html ${slug}: league.json fallback == full-games fallback`, plain(viaGames), plain(viaLeague));
    rows += main.length + viaLeague.length + viaGames.length + (onField === main ? 0 : onField.length);
  }
  // The two record categories must show exactly what the records build wrote.
  const fbsSet = new Set(fbs);
  const teamsPS = Object.entries(ps).filter(([t, v]) => t !== '_meta' && v && v.record && fbsSet.has(t));
  const byValue = (get) => teamsPS.map(([t, v]) => [t, get(v)]).sort((a, b) => b[1] - a[1]);
  const rowsOf = (slug, b) => ctx.__run(slug, ps, league, [], fbs, b).map(x => [x.team, x.value]);
  eq('rank.html all-time-wins (official) == program_stats record.wins', byValue(v => v.record.wins), rowsOf('all-time-wins'));
  eq('rank.html all-time-wins (on field) == program_stats recordOnField.wins', byValue(v => v.recordOnField.wins), rowsOf('all-time-wins', 'onfield'));
  eq('rank.html all-time-record (official) == program_stats winPct', byValue(v => v.winPct), rowsOf('all-time-record'));
  eq('rank.html all-time-record (on field) == program_stats winPctOnField', byValue(v => v.winPctOnField), rowsOf('all-time-record', 'onfield'));
  return { cats: ctx.__cats.length, rows };
}

// Record fields written by scripts/build_program_records.py: internally consistent, and the
// ranks team.html / compare.html print are the competition ranks of the official values.
function checkProgramRecords() {
  const ps = readJSON('program_stats.json');
  const teams = Object.keys(ps).filter(k => k !== '_meta');
  // same exact half-up rounding as build_program_records.py: floor((2N + D) / 2D)
  const pct = r => {
    const g = r.wins + r.losses + r.ties; if (!g) return 0;
    const num = (2 * r.wins + r.ties) * 10000, den = 2 * g;
    return Math.floor((2 * num + den) / (2 * den)) / 1e4;
  };
  const comp = vals => { const s = [...vals].sort((a, b) => b - a); return v => s.indexOf(v) + 1; };
  const rankWins = comp(teams.map(t => ps[t].record.wins)), rankPct = comp(teams.map(t => ps[t].winPct));
  let n = 0;
  for (const t of teams) {
    const p = ps[t];
    eq(`${t}: record fields present`, true, !!(p.record && p.recordOnField && p.recordAsOf && p.winPct != null && p.winPctOnField != null));
    if (!(p.record && p.recordOnField)) continue;
    eq(`${t}: winPct == official W-L-T`, pct(p.record), p.winPct);
    eq(`${t}: winPctOnField == on-field W-L-T`, pct(p.recordOnField), p.winPctOnField);
    eq(`${t}: ranks.wins == competition rank of record.wins`, rankWins(p.record.wins), p.ranks.wins);
    eq(`${t}: ranks.winPct == competition rank of winPct`, rankPct(p.winPct), p.ranks.winPct);
    const a = p.recordAdjust || {};
    eq(`${t}: on-field minus official wins == vacated + forfeited - awarded (footnote counts)`,
      p.recordOnField.wins - p.record.wins, (a.vacated | 0) + (a.forfeited | 0) - (a.awarded | 0));
    n++;
  }
  eq('Oklahoma St. claimed national titles', 1, ps['Oklahoma St.'].claimedNatChamps);
  eq('Oklahoma St. recognized national titles (1945 AFCA)', 1, ps['Oklahoma St.'].recognizedNatChamps);
  eq('Ohio St. claimed national titles (adds 2024)', 9, ps['Ohio St.'].claimedNatChamps);
  return n;
}

// ---- seeded random ------------------------------------------------------------------------
function rng(seed) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }

function main() {
  const t0 = Date.now();
  const { MF, FD } = loadModules();
  const OLD = readJSON('front_porch_games.json');
  const manifest = readJSON(DERIVED + 'manifest.json');
  const names = manifest.names;

  // Old path: the same annotations the live pages applied from the side files.
  MF.annotateSites(OLD, readJSON('game_sites.json'));
  const coachesDoc = readJSON('coaches_data.json');
  MF.annotateCoaches(OLD, coachesDoc);
  const venueOf = MF.venueLookup(readJSON('game_venues.json'));
  const oldCoach = (g, which) => { const ix = which === 'a' ? g._ca : g._cb; return ix == null ? null : coachesDoc.coaches[ix]; };

  // Manifest-level facts. A stale build (front_porch_games.json changed, derived files not
  // rebuilt) fails right here.
  const srcSha = require('crypto').createHash('sha256').update(fs.readFileSync(path.join(ROOT, 'front_porch_games.json'))).digest('hex');
  eq('manifest.sourceSha256 matches front_porch_games.json (derived files are current)', srcSha, manifest.sourceSha256);
  const oldNames = [...new Set(OLD.flatMap(g => [g.team_a, g.team_b]))];
  eq('manifest.names (set + first-appearance order)', oldNames, names);
  eq('manifest.gameCount', OLD.length, manifest.gameCount);
  let maxSeason = 0; for (const g of OLD) if ((g.season|0) > maxSeason) maxSeason = g.season|0;
  eq('manifest.maxSeason', maxSeason, manifest.maxSeason);

  // ---- 1. records -------------------------------------------------------------------------
  const decoded = {};           // team -> decoded rows
  const newCoach = (g, which) => { const ix = which === 'a' ? g._ca : g._cb; return ix == null ? null : FD.coachNames[ix]; };
  const oldByTeam = {};
  OLD.forEach((g, gi) => {
    (oldByTeam[g.team_a] = oldByTeam[g.team_a] || []).push(gi);
    if (g.team_b !== g.team_a) (oldByTeam[g.team_b] = oldByTeam[g.team_b] || []).push(gi);
  });
  let recordChecks = 0;
  for (const team of names) {
    const file = manifest.teams[manifest.slugs[names.indexOf(team)]];
    const doc = readJSON(DERIVED + file);
    eq(`team file ${file} belongs to ${team}`, team, doc.team);
    const rows = FD.decodeTeam(doc, names);
    decoded[team] = rows;
    eq(`${team}: row positions`, oldByTeam[team], rows.map(g => g._gi));
    rows.forEach(g => {
      const o = OLD[g._gi];
      const plain = x => ({ game_id: x.game_id, season: x.season, game_date: x.game_date, date_estimated: x.date_estimated, era: x.era,
        postseason: x.postseason, team_a: x.team_a, team_b: x.team_b, team_a_score: x.team_a_score, team_b_score: x.team_b_score,
        winner: x.winner, is_tie: x.is_tie, margin: x.margin, total_points: x.total_points, city: x.city, state: x.state });
      checks++; recordChecks++;
      const so = JSON.stringify(plain(o)) + '|' + o._site + '|' + oldCoach(o, 'a') + '|' + oldCoach(o, 'b') + '|' + (venueOf(o) || null);
      const sn = JSON.stringify(plain(g)) + '|' + g._site + '|' + newCoach(g, 'a') + '|' + newCoach(g, 'b') + '|' + (g._venue || null);
      if (so !== sn) { mismatches.push(`${team} row ${g._gi}`); if (mismatches.length <= 25) console.log(`MISMATCH ${team} row ${g._gi}\n   old: ${so}\n   new: ${sn}`); }
      // key order too (pages never depend on it, but the records should be indistinguishable)
      eq(`${team} row ${g._gi} key order`, Object.keys(o).filter(k => !k.startsWith('_')), Object.keys(g).filter(k => !k.startsWith('_')));
    });
  }

  // ---- 2 + 3. pairs and filters --------------------------------------------------------------
  const oldIdx = indexes(OLD);
  const has = t => names.includes(t);
  const named = [['Alabama','Auburn'], ['Oklahoma St.','Oklahoma'], ['Michigan','Ohio St.'], ['Texas','Oklahoma'], ['Army','Navy'],
    ['North Dakota St.','South Dakota St.'], ['North Dakota St.','Montana'], ['Sacramento St.','UC Davis'], ['Sacramento St.','Montana'],
    ['North Dakota St.','Sacramento St.'], ['Notre Dame','USC'], ['Nebraska','Oklahoma'], ['Miami','Miami'], ['Hawaii','Buffalo']];
  const pairs = named.filter(([a, b]) => has(a) && has(b));
  const rand = rng(20261002);
  const seen = new Set(pairs.map(p => p.join('|')));
  // pairs that met (sampled from real games) ...
  while (pairs.length < 190) {
    const g = OLD[Math.floor(rand() * OLD.length)];
    const k = [g.team_a, g.team_b].join('|');
    if (g.team_a !== g.team_b && !seen.has(k)) { seen.add(k); pairs.push([g.team_a, g.team_b]); }
  }
  // ... and pairs that never met
  let neverMet = 0;
  while (neverMet < 25) {
    const a = names[Math.floor(rand() * names.length)], b = names[Math.floor(rand() * names.length)];
    const k = [a, b].join('|');
    if (a !== b && !seen.has(k) && oldIdx.pair(a, b).length === 0) { seen.add(k); pairs.push([a, b]); neverMet++; }
  }

  let filterChecks = 0;
  for (const [t1, t2] of pairs) {
    // compare.html now holds just these two teams' files, merged in original order.
    const byGi = new Map();
    for (const t of [t1, t2]) for (const g of decoded[t] || []) if (!byGi.has(g._gi)) byGi.set(g._gi, g);
    const NEW = [...byGi.keys()].sort((x, y) => x - y).map(k => byGi.get(k));
    const newIdx = indexes(NEW);
    const op = oldIdx.pair(t1, t2), np = newIdx.pair(t1, t2);
    const label = `${t1} vs ${t2}`;
    eq(`${label}: header metrics`, headerMetrics(op, t1, t2), headerMetrics(np, t1, t2));
    eq(`${label}: Record chart`, winPctChart(oldIdx, t1, t2, 1887, maxSeason), winPctChart(newIdx, t1, t2, 1887, maxSeason));
    eq(`${label}: Record chart 2000-`, winPctChart(oldIdx, t1, t2, 2000, maxSeason), winPctChart(newIdx, t1, t2, 2000, maxSeason));
    eq(`${label}: all-time games`, [totalGamesAllTime(OLD, t1), totalGamesAllTime(OLD, t2)], [totalGamesAllTime(NEW, t1), totalGamesAllTime(NEW, t2)]);
    eq(`${label}: coach options`, [MF.coachOptions(op.map(g => g), t1).length, 0], [MF.coachOptions(np, t1).length, 0]);
    // Filters: every range x location x coach x last-N combination.
    const opts1 = MF.coachOptions(np, t1).slice(0, 2).map(o => o.value), opts2 = MF.coachOptions(np, t2).slice(0, 2).map(o => o.value);
    const ranges = [[null, null], [2000, maxSeason], [1950, 1980], [1887, 1920]];
    for (const [s, e] of ranges) for (const site of MF.SITES) for (const c1 of ['all', ...opts1]) for (const c2 of ['all', ...opts2]) for (const lastN of [null, 5]) {
      const f = { team1: t1, team2: t2, startYear: s, endYear: e, site, coach1: c1, coach2: c2, lastN };
      // old games carry indices into coaches_data.json's list, new ones into the registry;
      // compare by name through each side's own lookup.
      MF.setCoachNames(coachesDoc.coaches); const ro = MF.filterGames(op, f);
      MF.setCoachNames(FD.coachNames);      const rn = MF.filterGames(np, f);
      filterChecks++;
      eq(`${label}: filter ${JSON.stringify(f)}`, [ro.games.map(g => g.game_id), ro.missingSite, ro.missingCoach, headerMetrics(ro.games, t1, t2).recordStr],
                                               [rn.games.map(g => g.game_id), rn.missingSite, rn.missingCoach, headerMetrics(rn.games, t1, t2).recordStr]);
    }
    MF.setCoachNames(FD.coachNames);
    eq(`${label}: coach dropdowns`, (() => { MF.setCoachNames(coachesDoc.coaches); const x = [MF.coachOptions(op, t1), MF.coachOptions(op, t2)]; return x; })(),
                                    (() => { MF.setCoachNames(FD.coachNames); return [MF.coachOptions(np, t1), MF.coachOptions(np, t2)]; })());
    eq(`${label}: hasNeutral`, MF.hasNeutral(op), MF.hasNeutral(np));
  }

  // ---- 4. aggregate pages ---------------------------------------------------------------------
  const league = readJSON(DERIVED + manifest.league);
  const home = readJSON(DERIVED + manifest.home);
  const winsOld = rankWins((() => { const c = {}; OLD.forEach(g => { if (g.is_tie) return; c[g.winner] = (c[g.winner] || 0) + 1; }); return c; })());
  eq('league wins rank (compare/team buildWinsRank, rank liveWins)', winsOld, rankWins(winsFromLeague(league)));
  eq('league wins key order', Object.keys(winsRankFromGames(OLD).rank), Object.keys(rankWins(winsFromLeague(league)).rank));
  eq('league win% rank (compare/team buildWinPctRank)', rankPct(recsFromGames(OLD)), rankPct(recsFromLeague(league)));
  eq('rank.html liveWinPct', liveWinPct(recsFromGames(OLD)), liveWinPct(recsFromLeague(league)));
  eq('rank.html liveWins counts', Object.entries((() => { const c = {}; OLD.forEach(g => { if (!g.is_tie) c[g.winner] = (c[g.winner] || 0) + 1; }); return c; })()),
                                  Object.entries(winsFromLeague(league)));
  eq('teams.html team list', [...new Set(OLD.flatMap(g => [g.team_a, g.team_b]))].sort(), [...names].sort());
  eq('index.html hero', [OLD.length, maxSeason], [home.gameCount, home.maxSeason]);
  const idxSrc = read('index.html');
  const bbMatch = idxSrc.match(/const BLUE_BLOODS = (\[\[.*?\]\]);/);
  const BB = bbMatch ? JSON.parse(bbMatch[1].replace(/'/g, '"')) : null;
  eq('index.html BLUE_BLOODS matches build_derived_data.py', BB, home.blueBloods.map(x => [x[0], x[1]]));
  (BB || []).forEach(([a, b], i) => {
    const rg = OLD.filter(g => (g.team_a===a&&g.team_b===b)||(g.team_a===b&&g.team_b===a));
    eq(`index Blue Bloods ${a} vs ${b}`, [a, b, rg.filter(g=>g.winner===a).length, rg.filter(g=>g.winner===b).length, rg.filter(g=>g.is_tie).length], home.blueBloods[i]);
  });
  // team.html: per-team page values come from the team file alone.
  for (const team of names) {
    const o = OLD.filter(g => g.team_a === team || g.team_b === team), n = decoded[team];
    eq(`team.html ${team}`, o.map(g => g.game_id), n.map(g => g.game_id));
  }

  // ---- 5. rank.html: every category, through the page's own code ----------------------
  const rankRows = checkRankCategories(OLD, league);
  const recTeams = checkProgramRecords();

  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`rank.html: ${rankRows.cats} visible categories x 3 data paths (+ on-field basis), ${rankRows.rows.toLocaleString()} rows checked`);
  console.log(`program_stats.json records: ${recTeams} programs consistent (official + on field, win %, ranks)`);
  console.log(`\nparity: ${checks.toLocaleString()} checks (${recordChecks.toLocaleString()} records, ${pairs.length} pairs incl. ${neverMet} never-met, ` +
              `${filterChecks.toLocaleString()} filter combinations), ${mismatches.length} mismatches, ${secs}s`);
  if (mismatches.length) { console.log('PARITY FAILED'); process.exit(1); }
  console.log('PARITY OK');
}

main();
