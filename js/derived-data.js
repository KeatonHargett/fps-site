/*!
 * js/derived-data.js - Front Porch Sports loader for data/derived/.
 *
 * scripts/build_derived_data.py turns front_porch_games.json into small content-hashed
 * files (one per team, plus league-wide aggregates). This loader fetches only what a page
 * needs and rebuilds game records IDENTICAL to the originals - same 16 fields, same
 * values, same relative order (rows are merged by their global row index "gi") - so every
 * page computes exactly what it computed from the full file.
 *
 * Each decoded record also carries the location / head-coach / venue fields the filters
 * read (g._site, g._ca, g._cb, g._venue), so the location and coach filters are ready the
 * moment the teams are; js/matchup-filter.js runs unchanged on top of them.
 *
 * If anything derived fails to load, callers fall back to front_porch_games.json via
 * FPSData.loadFull() (console.warn, never an error), so a page never breaks.
 *
 * Plain <script>, no build step, defines window.FPSData.
 */
(function (global) {
  'use strict';

  var BASE = 'data/derived/';
  var FIELDS_ERA_POST = [false, true, null];

  var manifestPromise = null;
  var fileCache = {};          // path -> Promise<json>
  var rowsByGi = new Map();    // gi -> decoded record (all loaded teams)
  var loaded = new Set();      // team names whose file is in rowsByGi
  var coachNames = [];         // page-wide coach registry (g._ca / g._cb index into it)
  var coachIx = new Map();

  function getJSON(path) {
    if (!fileCache[path]) {
      fileCache[path] = fetch(path).then(function (r) {
        if (!r.ok) throw new Error(path + ' HTTP ' + r.status);
        return r.json();
      });
      // A failed fetch may be retried later rather than poisoning the cache.
      fileCache[path].catch(function () { delete fileCache[path]; });
    }
    return fileCache[path];
  }

  /* manifest.json: names, slugs, current hashed file names, gameCount, maxSeason. */
  function manifest() {
    if (!manifestPromise) {
      manifestPromise = getJSON(BASE + 'manifest.json').then(function (m) {
        if (!m || m.v !== 1 || !m.names || !m.teams) throw new Error('unexpected manifest');
        m.slugOf = {};
        m.names.forEach(function (n, i) { m.slugOf[n] = m.slugs[i]; });
        return m;
      });
      manifestPromise.catch(function () { manifestPromise = null; });
    }
    return manifestPromise;
  }

  function regCoach(name) {
    var i = coachIx.get(name);
    if (i === undefined) { i = coachNames.length; coachNames.push(name); coachIx.set(name, i); }
    return i;
  }

  function pad2(n) { return n < 10 ? '0' + n : '' + n; }
  function dateStr(d) {
    if (!d) return '';
    var y = Math.floor(d / 10000), m = Math.floor(d / 100) % 100, day = d % 100;
    return y + '-' + pad2(m) + '-' + pad2(day);
  }

  /* One team file -> original game records (+ _site/_ca/_cb/_venue). */
  function decodeTeam(doc, names) {
    var out = new Array(doc.n);
    var est = {};
    (doc.est || []).forEach(function (p) { est[p] = true; });
    var gid = doc.gid || {};
    var localCoach = (doc.coaches || []).map(regCoach);
    for (var i = 0; i < doc.n; i++) {
      var ta = names[doc.a[i]], tb = names[doc.b[i]];
      var as = doc.as[i], bs = doc.bs[i], w = doc.w[i];
      var gd = dateStr(doc.d[i]);
      var g = {
        game_id: gid[i] !== undefined ? gid[i] : (gd ? gd.replace(/-/g, '') : '00000000') + '_' + ta + '_vs_' + tb,
        season: doc.s[i],
        game_date: gd,
        date_estimated: !!est[i],
        era: doc.eras[doc.e[i]],
        postseason: FIELDS_ERA_POST[doc.p[i]],
        team_a: ta,
        team_b: tb,
        team_a_score: as,
        team_b_score: bs,
        winner: w === 0 ? '' : (w === 1 ? ta : tb),
        is_tie: w === 0,
        margin: Math.abs(as - bs),
        total_points: as + bs,
        city: doc.cities[doc.c[i]],
        state: doc.states[doc.st[i]]
      };
      var sc = doc.site.charAt(i);
      // Non-enumerable so a record still deep-equals the original 16-field object.
      Object.defineProperty(g, '_gi', { value: doc.gi[i], enumerable: false, writable: true });
      g._site = sc === '-' ? null : sc;
      g._ca = doc.ca[i] < 0 ? null : localCoach[doc.ca[i]];
      g._cb = doc.cb[i] < 0 ? null : localCoach[doc.cb[i]];
      g._venue = doc.vn[i] < 0 ? null : doc.venues[doc.vn[i]];
      out[i] = g;
    }
    return out;
  }

  /* Every loaded game, in front_porch_games.json order. */
  function allLoaded() {
    return Array.from(rowsByGi.keys()).sort(function (x, y) { return x - y; })
      .map(function (k) { return rowsByGi.get(k); });
  }

  /* Load the files for these teams (skipping ones already loaded) and return every loaded
     game in original order. Unknown names (not in the dataset) simply contribute no
     games - exactly what filtering the full file for them would give. Rejects if a file
     fails, so the caller can fall back. */
  function loadTeams(teamNames) {
    return manifest().then(function (m) {
      var want = (teamNames || []).filter(function (t) { return t && !loaded.has(t) && m.slugOf[t]; });
      return Promise.all(want.map(function (t) {
        return getJSON(BASE + m.teams[m.slugOf[t]]).then(function (doc) {
          if (doc.team !== t) throw new Error('team file mismatch for ' + t);
          if (loaded.has(t)) return;
          decodeTeam(doc, m.names).forEach(function (g) {
            if (!rowsByGi.has(g._gi)) rowsByGi.set(g._gi, g);
          });
          loaded.add(t);
        });
      })).then(function () { return allLoaded(); });
    });
  }

  function loadNamed(key) {
    return manifest().then(function (m) { return getJSON(BASE + m[key]); });
  }

  /* The fallback: the full dataset, as every page loaded it before. */
  function loadFull() {
    return getJSON('front_porch_games.json');
  }

  function warnFallback(page, err) {
    console.warn('[FPSData] ' + page + ': derived data unavailable (' + (err && err.message || err) +
      ') - falling back to front_porch_games.json');
  }

  global.FPSData = {
    manifest: manifest,
    loadTeams: loadTeams,
    loadLeague: function () { return loadNamed('league'); },
    loadHome: function () { return loadNamed('home'); },
    loadIndex: function () { return loadNamed('index'); },
    loadFull: loadFull,
    warnFallback: warnFallback,
    isLoaded: function (t) { return loaded.has(t); },
    coachNames: coachNames,
    decodeTeam: decodeTeam,     // exposed for scripts/parity_check.js
    BASE: BASE
  };
})(typeof window !== 'undefined' ? window : this);
