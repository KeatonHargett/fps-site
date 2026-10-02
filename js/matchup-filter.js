/*!
 * js/matchup-filter.js - Front Porch Sports shared matchup filters.
 *
 * Sibling of js/range-filter.js. range-filter owns the year slider + Time Period
 * dropdown; this module owns everything else that narrows a head-to-head series:
 *   - game location (All / Team 1 home / Team 2 home / Neutral), from game_sites.json
 *   - the one filter pipeline every page applies, so compare.html's numbers and
 *     games.html's list can never disagree
 *   - the URL contract both pages read and write
 *   - the location segmented control
 *
 * game_sites.json is keyed by game_id; each value is "<site><source>[venue]" where
 * site is a (team_a home) / b (team_b home) / n (neutral). annotateSites() turns
 * that into one precomputed `_site` field per game record, once, on load, so
 * toggling a filter never re-reads the file.
 *
 * Location values are always from Team 1's point of view, which is what the URL
 * stores (?site=team1home|team2home|neutral), so a shared link reopens the same view.
 *
 * Plain <script>, no build step, defines window.FPSMatchupFilter.
 */
(function (global) {
  'use strict';

  var SITES = ['all', 'team1home', 'team2home', 'neutral'];

  /* ---- data ------------------------------------------------------------ */

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

  /* ---- the filter pipeline ---------------------------------------------- */

  /* f: { team1, startYear, endYear, site, lastN }
     Order matters and is the same everywhere: year range, then location, then
     "last N" by COUNT (most recent first). Games with no site data stay in under
     'all' and drop out of every location view; that drop is reported, not hidden. */
  function filterGames(pairGames, f) {
    var site = f.site || 'all';
    var out = [];
    var missingSite = 0;
    for (var i = 0; i < pairGames.length; i++) {
      var g = pairGames[i];
      if (f.startYear != null && g.season < f.startYear) continue;
      if (f.endYear != null && g.season > f.endYear) continue;
      if (site !== 'all') {
        var s = siteOf(g, f.team1);
        if (s === null) { missingSite++; continue; }
        if (s !== site) continue;
      }
      out.push(g);
    }
    if (f.lastN) {
      out.sort(function (a, b) { return b.game_date.localeCompare(a.game_date); });
      out = out.slice(0, f.lastN);
    }
    return { games: out, missingSite: missingSite };
  }

  /* Location-only cut (no year range), for "Last N Matchups", whose slider span
     must come from the N most recent games in the current location view. */
  function filterLocationOnly(pairGames, f) {
    return filterGames(pairGames, { team1: f.team1, site: f.site }).games;
  }

  /* ---- URL contract ------------------------------------------------------ */

  function readParams(params) {
    var site = params.get('site');
    return {
      site: SITES.indexOf(site) > 0 ? site : 'all',
      start: parseInt(params.get('start'), 10) || null,
      end: parseInt(params.get('end'), 10) || null,
      preset: params.get('preset') || null,
      lastN: parseInt(params.get('last'), 10) || null
    };
  }

  /* Write the filter state onto a URLSearchParams. Defaults are omitted so an
     unfiltered view keeps a clean URL. */
  function writeParams(params, f) {
    ['start', 'end', 'preset', 'last', 'site'].forEach(function (k) { params.delete(k); });
    if (f.preset && f.preset !== 'all') {
      params.set('preset', f.preset);
    } else if (!f.preset && (f.startYear !== f.minYear || f.endYear !== f.maxYear)) {
      params.set('start', f.startYear);
      params.set('end', f.endYear);
    }
    if (f.site && f.site !== 'all') params.set('site', f.site);
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
    return p.toString();
  }

  function isActive(f) {
    return !!((f.site && f.site !== 'all') || f.lastN ||
      f.startYear !== f.minYear || f.endYear !== f.maxYear);
  }

  /* "2000-2026 · At Auburn" - the one-line, screenshot-ready summary. */
  function summary(f, names) {
    var parts = [];
    parts.push(f.lastN ? 'Last ' + f.lastN + ' Matchups' : f.startYear + '–' + f.endYear);
    if (f.site === 'team1home') parts.push('At ' + names.team1);
    else if (f.site === 'team2home') parts.push('At ' + names.team2);
    else if (f.site === 'neutral') parts.push('Neutral Site');
    return parts.join(' · ');
  }

  function missingNote(n) {
    if (!n) return '';
    return n + ' early game' + (n === 1 ? '' : 's') + ' missing site data';
  }

  /* ---- location segmented control ---------------------------------------- */

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
    loadSites: loadSites,
    annotateSites: annotateSites,
    siteOf: siteOf,
    hasNeutral: hasNeutral,
    filterGames: filterGames,
    filterLocationOnly: filterLocationOnly,
    readParams: readParams,
    writeParams: writeParams,
    gamesListQuery: gamesListQuery,
    isActive: isActive,
    summary: summary,
    missingNote: missingNote,
    createSiteControl: createSiteControl
  };
})(window);
