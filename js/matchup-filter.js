/*!
 * js/matchup-filter.js - Front Porch Sports shared matchup filters.
 *
 * Sibling of js/range-filter.js. range-filter owns the year slider + Time Period
 * dropdown; this module owns everything else that narrows a head-to-head series:
 *   - game location (All / Team 1 home / Team 2 home / Neutral), from game_sites.json
 *   - each team's head coach, from coaches_data.json
 *   - the one filter pipeline every page applies, so compare.html's numbers and
 *     games.html's list can never disagree
 *   - the URL contract both pages read and write
 *   - team-name aliases (?team1=Oklahoma State / osu / Oklahoma St. -> "Oklahoma St.")
 *   - the location segmented control
 *
 * game_sites.json is keyed by game_id; each value is "<site><source>[venue]" where
 * site is a (team_a home) / b (team_b home) / n (neutral). coaches_data.json holds
 * each school's coach(es) per season. annotateSites() / annotateCoaches() fold both
 * into precomputed fields on every game record (g._site, g._ca, g._cb), once, on
 * load, so toggling a filter never re-reads either file.
 *
 * Location values are always from Team 1's point of view, which is what the URL
 * stores (?site=team1home|team2home|neutral), so a shared link reopens the same view.
 * Coaches are stored by name (?c1=Nick Saban&c2=Gus Malzahn); c1 is Team 1's coach.
 *
 * Games with no site or no coach data are never guessed: they count under "All"
 * and drop out of any view that filters on what they are missing, and the count
 * that dropped is returned so the page can say so.
 *
 * Plain <script>, no build step, defines window.FPSMatchupFilter.
 */
(function (global) {
  'use strict';

  var SITES = ['all', 'team1home', 'team2home', 'neutral'];

  /* ---- location data ------------------------------------------------------ */

  function loadSites(url) {
    return fetch(url || 'game_sites.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  /* Precompute each game's site once: g._site = 'a' | 'b' | 'n' | null. */
  function annotateSites(games, doc) {
    var map = (doc && doc.games) || {};
    for (var i = 0; i < games.length; i++) {
      var v = map[games[i].game_id];
      games[i]._site = v ? v.charAt(0) : null;
    }
    return !!(doc && doc.games);
  }

  /* 'team1home' | 'team2home' | 'neutral' | null, from team1's point of view. */
  function siteOf(g, team1) {
    var s = g._site;
    if (!s) return null;
    if (s === 'n') return 'neutral';
    var home = s === 'a' ? g.team_a : g.team_b;
    return home === team1 ? 'team1home' : 'team2home';
  }

  function hasNeutral(games) {
    for (var i = 0; i < games.length; i++) if (games[i]._site === 'n') return true;
    return false;
  }

  /* ---- coach data ---------------------------------------------------------- */

  var COACH_NAMES = [];
  var NO_COACH = 'No coach';

  function loadCoaches(url) {
    return fetch(url || 'coaches_data.json')
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }

  /* Precompute both coaches once per game: g._ca / g._cb = coach index or null.
     Split seasons carry the last game date of every coach but the last; a few
     games are pinned individually (doc.games). */
  function annotateCoaches(games, doc) {
    if (!doc || !doc.teams) return false;
    COACH_NAMES = doc.coaches || [];
    var teams = doc.teams, pinned = doc.games || {};
    function pick(team, g) {
      var pin = pinned[g.game_id];
      if (pin && pin[team] != null) return pin[team];
      var spans = teams[team] && teams[team][g.season];
      if (!spans || !spans.length) return null;
      if (spans.length === 1) return spans[0][0];
      if (!g.game_date) return null;
      for (var i = 0; i < spans.length; i++) {
        var s = spans[i];
        if (s.length < 3 || !s[2] || g.game_date <= s[2]) return s[0];
      }
      return spans[spans.length - 1][0];
    }
    for (var i = 0; i < games.length; i++) {
      games[i]._ca = pick(games[i].team_a, games[i]);
      games[i]._cb = pick(games[i].team_b, games[i]);
    }
    return true;
  }

  /* Coach name for `team` in game g, or null when unknown. */
  function coachOf(g, team) {
    var ix = team === g.team_a ? g._ca : team === g.team_b ? g._cb : null;
    return ix == null ? null : COACH_NAMES[ix];
  }

  function coachLabel(name) {
    return name === NO_COACH ? 'No head coach' : name;
  }

  /* Dropdown options for one side of a series: every coach `team` had in at least
     one meeting, most recent tenure first, with that coach's series record. */
  function coachOptions(pairGames, team) {
    var by = {};
    for (var i = 0; i < pairGames.length; i++) {
      var g = pairGames[i], c = coachOf(g, team);
      if (c == null) continue;
      var r = by[c] || (by[c] = { name: c, w: 0, l: 0, t: 0, last: '' });
      if (g.is_tie) r.t++; else if (g.winner === team) r.w++; else r.l++;
      var d = g.game_date || String(g.season);
      if (d > r.last) r.last = d;
    }
    return Object.keys(by).map(function (k) { return by[k]; })
      .sort(function (a, b) { return b.last.localeCompare(a.last); })
      .map(function (r) {
        var rec = r.w + '-' + r.l + (r.t ? '-' + r.t : '');
        return { value: r.name, record: rec, label: coachLabel(r.name) + ' (' + rec + ')' };
      });
  }

  /* Short form for the summary line ("Saban vs Malzahn"); co-coach labels already are. */
  function coachShort(name) {
    if (name === NO_COACH) return 'No head coach';
    if (name.indexOf(' / ') >= 0) return name;
    var parts = name.replace(/\s+(Jr\.?|Sr\.?|II|III|IV)$/, '').split(' ');
    return parts[parts.length - 1];
  }

  /* ---- team-name aliases --------------------------------------------------- */

  function fold(s) {
    return String(s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '')
      .toLowerCase().replace(/\s+/g, ' ').trim();
  }

  /* Build a resolver from the dataset's team names. extra = { alias: datasetName }
     for abbreviations and display names the page knows about (first alias wins, so
     pass the site's own abbreviations - OSU, OHST - before generic ones). Matching
     is case and accent insensitive; "X State" and "X St" both reach a dataset
     "X St.". Returns the dataset name, or null when nothing matches. */
  function teamResolver(names, extra) {
    var map = {};
    function add(alias, name) { var k = fold(alias); if (k && !(k in map)) map[k] = name; }
    names.forEach(function (n) { add(n, n); });
    names.forEach(function (n) {
      if (/ St\.$/.test(n)) {
        add(n.replace(/ St\.$/, ' State'), n);
        add(n.replace(/ St\.$/, ' St'), n);
      }
    });
    Object.keys(extra || {}).forEach(function (a) {
      if (names.indexOf(extra[a]) >= 0) add(a, extra[a]);
    });
    return function (input) {
      if (input == null) return null;
      var k = fold(input);
      if (k in map) return map[k];
      var k2 = k.replace(/^the /, '').replace(/ university$/, '');
      return map[k2] || null;
    };
  }

  /* ---- the filter pipeline ------------------------------------------------- */

  /* f: { team1, team2, startYear, endYear, site, coach1, coach2, lastN }
     AND logic, same order everywhere: year range, location, coaches, then "last N"
     by COUNT (most recent first). */
  function filterGames(pairGames, f) {
    var site = f.site || 'all';
    var c1 = f.coach1 && f.coach1 !== 'all' ? f.coach1 : null;
    var c2 = f.coach2 && f.coach2 !== 'all' ? f.coach2 : null;
    var out = [];
    var missingSite = 0, missingCoach = 0;
    for (var i = 0; i < pairGames.length; i++) {
      var g = pairGames[i];
      if (f.startYear != null && g.season < f.startYear) continue;
      if (f.endYear != null && g.season > f.endYear) continue;
      if (site !== 'all') {
        var s = siteOf(g, f.team1);
        if (s === null) { missingSite++; continue; }
        if (s !== site) continue;
      }
      if (c1 || c2) {
        var a = c1 ? coachOf(g, f.team1) : '', b = c2 ? coachOf(g, f.team2) : '';
        if (a === null || b === null) { missingCoach++; continue; }
        if ((c1 && a !== c1) || (c2 && b !== c2)) continue;
      }
      out.push(g);
    }
    if (f.lastN) {
      out.sort(function (x, y) { return y.game_date.localeCompare(x.game_date); });
      out = out.slice(0, f.lastN);
    }
    return { games: out, missingSite: missingSite, missingCoach: missingCoach };
  }

  /* Every filter except the year range, for "Last N Matchups", whose slider span
     must come from the N most recent games in the current view. */
  function filterLocationOnly(pairGames, f) {
    return filterGames(pairGames, {
      team1: f.team1, team2: f.team2, site: f.site, coach1: f.coach1, coach2: f.coach2
    }).games;
  }

  /* ---- URL contract -------------------------------------------------------- */

  function readParams(params) {
    var site = params.get('site');
    return {
      site: SITES.indexOf(site) > 0 ? site : 'all',
      coach1: params.get('c1') || 'all',
      coach2: params.get('c2') || 'all',
      start: parseInt(params.get('start'), 10) || null,
      end: parseInt(params.get('end'), 10) || null,
      preset: params.get('preset') || null,
      lastN: parseInt(params.get('last'), 10) || null
    };
  }

  /* Write the filter state onto a URLSearchParams. Defaults are omitted so an
     unfiltered view keeps a clean URL. */
  function writeParams(params, f) {
    ['start', 'end', 'preset', 'last', 'site', 'c1', 'c2'].forEach(function (k) { params.delete(k); });
    if (f.preset && f.preset !== 'all') {
      params.set('preset', f.preset);
    } else if (!f.preset && (f.startYear !== f.minYear || f.endYear !== f.maxYear)) {
      params.set('start', f.startYear);
      params.set('end', f.endYear);
    }
    if (f.site && f.site !== 'all') params.set('site', f.site);
    if (f.coach1 && f.coach1 !== 'all') params.set('c1', f.coach1);
    if (f.coach2 && f.coach2 !== 'all') params.set('c2', f.coach2);
    return params;
  }

  /* The games.html link: always carries the exact range plus every other filter. */
  function gamesListQuery(f) {
    var p = new URLSearchParams();
    p.set('team1', f.team1);
    p.set('team2', f.team2);
    p.set('start', f.startYear);
    p.set('end', f.endYear);
    if (f.lastN) p.set('last', f.lastN);
    if (f.site && f.site !== 'all') p.set('site', f.site);
    if (f.coach1 && f.coach1 !== 'all') p.set('c1', f.coach1);
    if (f.coach2 && f.coach2 !== 'all') p.set('c2', f.coach2);
    return p.toString();
  }

  /* How many of the location + coach filters are on (the "More filters (n)" badge). */
  function hiddenActiveCount(f) {
    return (f.site && f.site !== 'all' ? 1 : 0) +
      (f.coach1 && f.coach1 !== 'all' ? 1 : 0) +
      (f.coach2 && f.coach2 !== 'all' ? 1 : 0);
  }

  function isActive(f) {
    return !!(hiddenActiveCount(f) || f.lastN ||
      f.startYear !== f.minYear || f.endYear !== f.maxYear);
  }

  /* "2000-2026 · At Auburn · Saban vs Malzahn" - the one-line, screenshot-ready
     summary. names: { team1, team2, abbr1, abbr2 }. */
  function summary(f, names) {
    var parts = [];
    parts.push(f.lastN ? 'Last ' + f.lastN + ' Matchups' : f.startYear + '–' + f.endYear);
    if (f.site === 'team1home') parts.push('At ' + names.team1);
    else if (f.site === 'team2home') parts.push('At ' + names.team2);
    else if (f.site === 'neutral') parts.push('Neutral Site');
    var c1 = f.coach1 && f.coach1 !== 'all', c2 = f.coach2 && f.coach2 !== 'all';
    if (c1 && c2) parts.push(coachShort(f.coach1) + ' vs ' + coachShort(f.coach2));
    else if (c1) parts.push(coachShort(f.coach1) + ' (' + (names.abbr1 || names.team1) + ')');
    else if (c2) parts.push(coachShort(f.coach2) + ' (' + (names.abbr2 || names.team2) + ')');
    return parts.join(' · ');
  }

  /* "6 early games missing coach data". what = 'site' | 'coach'. */
  function missingNote(n, what) {
    if (!n) return '';
    return n + ' early game' + (n === 1 ? '' : 's') + ' missing ' + (what || 'site') + ' data';
  }

  /* ---- location segmented control ------------------------------------------ */

  /* opts: { container, onChange(value) }. Arrow keys move between options (and
     select, like a radio group); aria-pressed marks the active one; only the active
     button is in the tab order. */
  function createSiteControl(opts) {
    var container = typeof opts.container === 'string'
      ? document.querySelector(opts.container) : opts.container;
    var value = 'all';
    var labels = { all: 'All', team1home: 'Home', team2home: 'Home', neutral: 'Neutral' };
    var showNeutral = true;

    container.innerHTML =
      '<div class="site-filter" role="group" aria-label="Game location">' +
        SITES.map(function (s) {
          return '<button type="button" class="site-btn" data-site="' + s + '"></button>';
        }).join('') +
      '</div>';
    var buttons = Array.prototype.slice.call(container.querySelectorAll('.site-btn'));

    function visible() {
      return buttons.filter(function (b) { return !b.hidden; });
    }

    function paint() {
      buttons.forEach(function (b) {
        var s = b.getAttribute('data-site');
        b.textContent = labels[s];
        b.hidden = s === 'neutral' && !showNeutral;
        var on = s === value;
        b.setAttribute('aria-pressed', on ? 'true' : 'false');
        b.tabIndex = on ? 0 : -1;
      });
    }

    function select(v, focus) {
      if (SITES.indexOf(v) < 0) v = 'all';
      var changed = v !== value;
      value = v;
      paint();
      if (focus) {
        var b = buttons.filter(function (x) { return x.getAttribute('data-site') === v; })[0];
        if (b) b.focus();
      }
      if (changed && opts.onChange) opts.onChange(value);
    }

    container.addEventListener('click', function (e) {
      var b = e.target.closest('.site-btn');
      if (b) select(b.getAttribute('data-site'), false);
    });
    container.addEventListener('keydown', function (e) {
      var keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
      var vis = visible();
      var i = vis.indexOf(document.activeElement);
      if (i < 0) return;
      var next = null;
      if (keys[e.key]) next = vis[(i + keys[e.key] + vis.length) % vis.length];
      else if (e.key === 'Home') next = vis[0];
      else if (e.key === 'End') next = vis[vis.length - 1];
      if (!next) return;
      e.preventDefault();
      select(next.getAttribute('data-site'), true);
    });

    paint();
    return {
      get value() { return value; },
      /* Silent set (no onChange) - for restoring state from the URL. */
      setValue: function (v) { value = SITES.indexOf(v) >= 0 ? v : 'all'; paint(); },
      setTeams: function (abbr1, abbr2, neutralPlayed) {
        labels.team1home = abbr1 + ' Home';
        labels.team2home = abbr2 + ' Home';
        showNeutral = !!neutralPlayed;
        if (!showNeutral && value === 'neutral') value = 'all';
        paint();
      },
      element: container
    };
  }

  global.FPSMatchupFilter = {
    SITES: SITES,
    NO_COACH: NO_COACH,
    loadSites: loadSites,
    annotateSites: annotateSites,
    siteOf: siteOf,
    hasNeutral: hasNeutral,
    loadCoaches: loadCoaches,
    annotateCoaches: annotateCoaches,
    coachOf: coachOf,
    coachOptions: coachOptions,
    coachLabel: coachLabel,
    teamResolver: teamResolver,
    filterGames: filterGames,
    filterLocationOnly: filterLocationOnly,
    readParams: readParams,
    writeParams: writeParams,
    gamesListQuery: gamesListQuery,
    hiddenActiveCount: hiddenActiveCount,
    isActive: isActive,
    summary: summary,
    missingNote: missingNote,
    createSiteControl: createSiteControl
  };
})(window);
