/*!
 * js/range-filter.js - Front Porch Sports shared year-range filter.
 *
 * Extracted from the inline implementation in compare.html so more than one page
 * can drive the same dual-slider + Time Period control without another copy of it.
 * The module owns the control; it does NOT own the dataset. Callers keep their own
 * games array and re-filter it inside onChange.
 *
 * Two mounting modes:
 *   bind  - attach to markup the page already has (compare.html uses this, so its
 *           existing DOM and CSS are untouched and it renders exactly as before)
 *   build - render the markup into an empty container (for new pages)
 * The mode is auto-detected: if the container already holds the two range inputs
 * it binds, otherwise it builds.
 *
 * Build mode emits the same class names compare.html styles, so a consuming page
 * needs these rules present: .year-range-section, .year-range-header,
 * .year-range-title, .year-range-display, .year, .range-wrap, .range-track,
 * .range-fill, .range-labels, .time-period-cell, .preset-select.
 *
 * No dependencies, no build step, no module system - a plain <script> that defines
 * window.FPSRangeFilter, matching how every other script on this site loads.
 */
(function (global) {
  'use strict';

  /* First season in the dataset. Only the floor is a constant: the ceiling is always
     derived from the data (see setMaxYear / applyMaxSeasonFrom) so a new season shows
     up without a code change. */
  var DEFAULT_MIN_YEAR = 1887;

  /* Option list for the Time Period dropdown, in display order. The empty value is
     the "Custom range" sentinel a manual slider drag falls back to; it is hidden and
     disabled so it can never be picked deliberately. */
  var PRESET_OPTIONS = [
    { value: '',          label: 'Custom range', hidden: true, disabled: true },
    { value: 'all',       label: 'All-Time' },
    { value: 'last5',     label: 'Last 5 Matchups' },
    { value: 'last10',    label: 'Last 10 Matchups' },
    { value: 'past5',     label: 'Past 5yrs' },
    { value: 'past10',    label: 'Past 10yrs' },
    { value: 'past20',    label: 'Past 20yrs' },
    { value: 'cfp',       label: 'CFP Era (2014+)' },
    { value: 'bcs',       label: 'BCS Era (1998-2013)' },
    { value: 'modern',    label: 'Modern (1969-1997)' },
    { value: 'premodern', label: 'Pre-Modern (<1969)' }
  ];

  /* Count-based presets. These are deliberately NOT year ranges: "Last 5 Matchups"
     moves the sliders to the span those 5 games happen to cover, but the caller must
     still cut the list to 5 by count. Mixing the two up silently changes results for
     any pair that played twice in one season, so lastN stays a separate signal from
     startYear/endYear all the way through. */
  var COUNT_PRESETS = { last5: 5, last10: 10 };

  /* Year presets, recomputed against the live max season rather than a hardcoded one.
     Fixed-era boundaries (CFP/BCS/modern/pre-modern) are historical facts and stay
     literal; anything open-ended runs to maxYear. */
  function defaultPresetRanges(minYear, maxYear) {
    return {
      all:       { start: minYear,      end: maxYear },
      past5:     { start: maxYear - 4,  end: maxYear },
      past10:    { start: maxYear - 9,  end: maxYear },
      past20:    { start: maxYear - 19, end: maxYear },
      cfp:       { start: 2014,         end: maxYear },
      bcs:       { start: 1998,         end: 2013 },
      modern:    { start: 1969,         end: 1997 },
      premodern: { start: minYear,      end: 1968 }
    };
  }

  var uid = 0;

  function el(root, sel) {
    if (!sel) return null;
    if (sel.nodeType === 1) return sel;
    return root.querySelector(sel);
  }

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function create(options) {
    var opts = options || {};

    var container = opts.container || document;
    if (typeof container === 'string') container = document.querySelector(container);
    if (!container) throw new Error('FPSRangeFilter: container not found');
    var scope = container;

    var minYear = opts.minYear != null ? opts.minYear : DEFAULT_MIN_YEAR;
    var maxYear = opts.maxYear != null ? opts.maxYear : minYear;
    var debounceMs = opts.debounceMs != null ? opts.debounceMs : 120;
    var onChange = typeof opts.onChange === 'function' ? opts.onChange : null;
    var lastNResolver = typeof opts.lastNResolver === 'function' ? opts.lastNResolver : null;
    var makeRanges = typeof opts.presetRanges === 'function' ? opts.presetRanges : defaultPresetRanges;
    var countPresets = opts.countPresets || COUNT_PRESETS;
    var presetOptions = opts.presetOptions || PRESET_OPTIONS;
    var thumbStyleId = opts.thumbStyleId || 'slider-thumb-style';

    var sel = opts.selectors || {};
    var S = {
      startSlider:  sel.startSlider  || '#start-slider',
      endSlider:    sel.endSlider    || '#end-slider',
      displayStart: sel.displayStart || '#display-start',
      displayEnd:   sel.displayEnd   || '#display-end',
      rangeFill:    sel.rangeFill    || '#range-fill',
      presetSelect: sel.presetSelect || '#preset-select'
    };

    var instanceId = 'fps-rf-' + (++uid);
    var built = false;

    /* Auto-detect: bind to existing markup when it is there, otherwise build it. */
    if (!el(scope, S.startSlider) || !el(scope, S.endSlider)) {
      buildMarkup();
      built = true;
    }

    function buildMarkup() {
      if (scope.nodeType === 9) throw new Error('FPSRangeFilter: build mode needs a container element');
      var p = instanceId;
      S.startSlider  = '#' + p + '-start';
      S.endSlider    = '#' + p + '-end';
      S.displayStart = '#' + p + '-display-start';
      S.displayEnd   = '#' + p + '-display-end';
      S.rangeFill    = '#' + p + '-fill';
      S.presetSelect = '#' + p + '-preset';
      thumbStyleId = p + '-thumb-style';

      var presetMarkup = opts.buildPreset === false ? '' :
        '<div class="time-period-cell">' +
          '<label for="' + p + '-preset">' + esc(opts.presetLabel || 'Time Period') + '</label>' +
          '<select id="' + p + '-preset" class="preset-select" data-preset-select="">' +
            presetOptions.map(function (o) {
              return '<option value="' + esc(o.value) + '"' +
                (o.hidden ? ' hidden' : '') +
                (o.disabled ? ' disabled' : '') +
                (o.value === (opts.initialPreset || 'all') ? ' selected' : '') +
                '>' + esc(o.label) + '</option>';
            }).join('') +
          '</select>' +
        '</div>';

      container.innerHTML =
        '<div class="year-range-section">' +
          '<div class="year-range-header">' +
            '<span class="year-range-title">' + esc(opts.title || 'Year Range') + '</span>' +
            '<span class="year-range-display">' +
              '<span class="year" id="' + p + '-display-start">' + minYear + '</span> &mdash; ' +
              '<span class="year" id="' + p + '-display-end">' + maxYear + '</span>' +
            '</span>' +
          '</div>' +
          '<div class="range-wrap">' +
            '<div class="range-track"></div>' +
            '<div class="range-fill" id="' + p + '-fill"></div>' +
            '<input type="range" id="' + p + '-start" min="' + minYear + '" max="' + maxYear + '" value="' + minYear + '" step="1">' +
            '<input type="range" id="' + p + '-end" min="' + minYear + '" max="' + maxYear + '" value="' + maxYear + '" step="1">' +
          '</div>' +
          '<div class="range-labels"><span>Start Year</span><span>End Year</span></div>' +
        '</div>' + presetMarkup;
    }

    var nodes = {
      startSlider:  el(scope, S.startSlider),
      endSlider:    el(scope, S.endSlider),
      displayStart: el(scope, S.displayStart),
      displayEnd:   el(scope, S.displayEnd),
      rangeFill:    el(scope, S.rangeFill),
      presetSelect: el(scope, S.presetSelect)
    };
    if (!nodes.startSlider || !nodes.endSlider) {
      throw new Error('FPSRangeFilter: could not find the range inputs');
    }

    var PRESETS = makeRanges(minYear, maxYear);

    var state = {
      startYear: opts.initialStart != null ? opts.initialStart : minYear,
      endYear:   opts.initialEnd   != null ? opts.initialEnd   : maxYear,
      activePreset: opts.initialPreset !== undefined ? opts.initialPreset : 'all',
      lastN: null
    };

    /* ---- change emission ------------------------------------------------- */
    /* The audit flagged the filter re-scanning the whole games dataset on every
       `input` event, i.e. once per pixel of drag. The slider position, the year
       readout and the fill still update synchronously on every event, so the control
       itself feels exactly as it did; only the caller's onChange is coalesced, so the
       expensive work runs when the drag settles instead of ~60x a second. Discrete
       changes (preset pick, programmatic setRange) skip the debounce entirely, and a
       slider's `change` event - which fires on release and on every keyboard step -
       flushes any pending call immediately. */
    var timer = null;
    var pendingSource = null;

    function payload(source) {
      return {
        startYear: state.startYear,
        endYear: state.endYear,
        activePreset: state.activePreset,
        lastN: state.lastN,
        minYear: minYear,
        maxYear: maxYear,
        source: source
      };
    }

    function emit(source, immediate) {
      if (!onChange) return;
      if (immediate || !debounceMs) {
        if (timer) { clearTimeout(timer); timer = null; }
        pendingSource = null;
        onChange(payload(source));
        return;
      }
      pendingSource = source;
      if (timer) clearTimeout(timer);
      timer = setTimeout(function () {
        timer = null;
        var s = pendingSource;
        pendingSource = null;
        onChange(payload(s));
      }, debounceMs);
    }

    function flush() {
      if (!timer) return;
      clearTimeout(timer);
      timer = null;
      var s = pendingSource;
      pendingSource = null;
      if (onChange) onChange(payload(s));
    }

    /* ---- DOM sync -------------------------------------------------------- */
    function updateRangeFill() {
      var span = maxYear - minYear;
      if (!nodes.rangeFill || !span) return;
      var lpct = ((state.startYear - minYear) / span) * 100;
      var rpct = ((state.endYear - minYear) / span) * 100;
      nodes.rangeFill.style.left = lpct + '%';
      nodes.rangeFill.style.width = (rpct - lpct) + '%';
    }

    /* Mirrors the original setSliders(): write state, write the DOM, then either drop
       out of the active preset (manual drag) or keep it (preset-driven move). */
    function apply(start, end, fromPreset, source, immediate) {
      state.startYear = start;
      state.endYear = end;
      nodes.startSlider.value = start;
      nodes.endSlider.value = end;
      if (nodes.displayStart) nodes.displayStart.textContent = start;
      if (nodes.displayEnd) nodes.displayEnd.textContent = end;
      updateRangeFill();
      if (!fromPreset) {
        // Manual slider drag drops out of any preset - reset the dropdown to Custom range.
        if (nodes.presetSelect) nodes.presetSelect.value = '';
        state.activePreset = null;
        state.lastN = null;
      }
      emit(source, immediate);
    }

    /* ---- listeners ------------------------------------------------------- */
    var ac = typeof AbortController === 'function' ? new AbortController() : null;
    var listenerOpts = ac ? { signal: ac.signal } : false;

    nodes.startSlider.addEventListener('input', function (e) {
      var s = parseInt(e.target.value);
      if (s > state.endYear) { s = state.endYear; e.target.value = s; }
      state.activePreset = null;
      apply(s, state.endYear, false, 'slider', false);
    }, listenerOpts);

    nodes.endSlider.addEventListener('input', function (e) {
      var end = parseInt(e.target.value);
      if (end < state.startYear) { end = state.startYear; e.target.value = end; }
      state.activePreset = null;
      apply(state.startYear, end, false, 'slider', false);
    }, listenerOpts);

    // Fires on drag release and on each keyboard step: settle the pending scan now.
    nodes.startSlider.addEventListener('change', flush, listenerOpts);
    nodes.endSlider.addEventListener('change', flush, listenerOpts);

    if (nodes.presetSelect) {
      nodes.presetSelect.addEventListener('change', function () {
        selectPreset(nodes.presetSelect.value);
      }, listenerOpts);
    }

    function selectPreset(preset) {
      state.activePreset = preset;
      if (nodes.presetSelect && nodes.presetSelect.value !== preset) {
        nodes.presetSelect.value = preset;
      }
      var n = countPresets[preset];
      if (n) {
        // Count-based preset: show the span those N games cover, but filter by count.
        state.lastN = n;
        var seasons = (lastNResolver && lastNResolver(n)) || [];
        if (!seasons.length) {
          apply(minYear, maxYear, true, 'preset', true);
        } else {
          apply(Math.min.apply(null, seasons), Math.max.apply(null, seasons), true, 'preset', true);
        }
        return;
      }
      state.lastN = null;
      var p = PRESETS[preset];
      if (!p) return;
      apply(p.start, p.end, true, 'preset', true);
    }

    /* ---- public API ------------------------------------------------------ */
    var api = {
      /* Live filter state. Treat as read-only. */
      get state() { return state; },
      getState: function () { return payload('api'); },

      get minYear() { return minYear; },
      get maxYear() { return maxYear; },
      get presets() { return PRESETS; },

      /* The filter predicate, kept in one place so every consumer agrees on it. */
      matchesSeason: function (season) {
        return season >= state.startYear && season <= state.endYear;
      },

      /* When set, the caller must cut its result list to this many most-recent games
         AFTER applying matchesSeason. Null means range-only filtering. */
      get lastN() { return state.lastN; },

      /* The ?start=/?end= link contract that games.html reads. */
      queryString: function () { return 'start=' + state.startYear + '&end=' + state.endYear; },
      queryParams: function () { return { start: state.startYear, end: state.endYear }; },

      setRange: function (start, end, o) {
        o = o || {};
        apply(start, end, !!o.fromPreset, o.source || 'api', o.immediate !== false);
      },

      setPreset: selectPreset,

      /* Raise the ceiling from real data. Only ever moves up, so a partial dataset
         cannot shrink the range under a user mid-session. */
      setMaxYear: function (y) {
        y = y | 0;
        if (!(y > maxYear)) return false;
        maxYear = y;
        PRESETS = makeRanges(minYear, maxYear);
        nodes.startSlider.max = maxYear;
        nodes.endSlider.max = maxYear;
        if (parseInt(nodes.endSlider.value) <= y) nodes.endSlider.value = maxYear;
        if (nodes.displayEnd) nodes.displayEnd.textContent = maxYear;
        state.endYear = maxYear;
        updateRangeFill();
        return true;
      },

      /* Convenience: derive the ceiling from a games array instead of hardcoding it. */
      applyMaxSeasonFrom: function (games, accessor) {
        var get = accessor || function (g) { return g.season | 0; };
        var max = 0;
        for (var i = 0; i < games.length; i++) {
          var s = get(games[i]) | 0;
          if (s > max) max = s;
        }
        return api.setMaxYear(max);
      },

      /* Thumb + fill colors. The control has no opinion about what the colors mean;
         the page passes whatever it wants (compare.html passes the two team colors). */
      setThumbColors: function (startColor, endColor) {
        var styleEl = document.getElementById(thumbStyleId);
        if (!styleEl) {
          styleEl = document.createElement('style');
          styleEl.id = thumbStyleId;
          document.head.appendChild(styleEl);
        }
        var a = '#' + nodes.startSlider.id, b = '#' + nodes.endSlider.id;
        var f = nodes.rangeFill && nodes.rangeFill.id ? '#' + nodes.rangeFill.id : null;
        styleEl.textContent =
          a + '::-webkit-slider-thumb{background:' + startColor + ';}' +
          a + '::-moz-range-thumb{background:' + startColor + ';}' +
          b + '::-webkit-slider-thumb{background:' + endColor + ';}' +
          b + '::-moz-range-thumb{background:' + endColor + ';}' +
          (f ? f + '{background:linear-gradient(90deg,' + startColor + ',' + endColor + ');opacity:0.5;}' : '');
      },

      /* Re-sync the DOM from state without firing onChange. */
      refresh: function () {
        nodes.startSlider.value = state.startYear;
        nodes.endSlider.value = state.endYear;
        if (nodes.displayStart) nodes.displayStart.textContent = state.startYear;
        if (nodes.displayEnd) nodes.displayEnd.textContent = state.endYear;
        if (nodes.presetSelect) nodes.presetSelect.value = state.activePreset || '';
        updateRangeFill();
      },

      updateRangeFill: updateRangeFill,
      flush: flush,
      elements: nodes,
      wasBuilt: function () { return built; },

      destroy: function () {
        if (timer) { clearTimeout(timer); timer = null; }
        if (ac) ac.abort();
        var styleEl = document.getElementById(thumbStyleId);
        if (styleEl && built) styleEl.remove();
        if (built) container.innerHTML = '';
      }
    };

    return api;
  }

  global.FPSRangeFilter = {
    create: create,
    MIN_YEAR: DEFAULT_MIN_YEAR,
    PRESET_OPTIONS: PRESET_OPTIONS,
    COUNT_PRESETS: COUNT_PRESETS,
    defaultPresetRanges: defaultPresetRanges
  };
})(window);
