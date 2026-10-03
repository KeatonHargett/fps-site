/*!
 * js/record-notes.js - Front Porch Sports: the on-field second line + footnote.
 *
 * The official NCAA record (program_stats.json `record`) is the main figure everywhere.
 * Where vacated wins or NCAA-ordered forfeits make the on-field record differ, pages show
 * it as a second, asterisked line. The footnote describes the ASTERISKED (on-field) number,
 * using recordAdjust from scripts/build_program_records.py:
 *   vacated   - wins later vacated by the NCAA (on field they count)
 *   forfeited - on-field wins the NCAA turned into losses (on field they count)
 *   awarded   - wins the NCAA awarded this team by an opponent's forfeit (on field they
 *               were losses or ties, so the on-field figure excludes them)
 * One shared copy so /team, /compare and /conference can never word it differently;
 * scripts/parity_check.js runs it for every program.
 *
 * Plain <script>, no build step, defines window.FPSRecordNote.
 */
(function (global) {
  'use strict';

  function plural(n) { return n === 1 ? '' : 's'; }

  /* Footnote text for one recordAdjust, or '' when official and on-field agree. */
  function note(a) {
    a = a || {};
    var vac = a.vacated | 0, forf = a.forfeited | 0, award = a.awarded | 0;
    var lost = vac + forf;
    var kind = vac && forf ? 'vacated or forfeited' : (vac ? 'vacated' : 'forfeited');
    var parts = [];
    if (lost) parts.push('includes ' + lost.toLocaleString('en-US') + ' win' + plural(lost) + ' later ' + kind);
    if (award) parts.push('excludes ' + award + ' win' + plural(award) + ' awarded by forfeit');
    if (!parts.length) return '';
    var s = parts.join('; ');
    return '*' + s.charAt(0).toUpperCase() + s.slice(1);
  }

  /* { rec, pct, note } for a program_stats row whose on-field record differs, else null. */
  function onField(ps) {
    if (!ps || !ps.record || !ps.recordOnField) return null;
    var o = ps.record, f = ps.recordOnField;
    if (o.wins === f.wins && o.losses === f.losses && o.ties === f.ties) return null;
    return { rec: f, pct: ps.winPctOnField, note: note(ps.recordAdjust) || '*Includes games later vacated by NCAA ruling' };
  }

  var MONTHS = ['Jan.', 'Feb.', 'March', 'April', 'May', 'June', 'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'];
  /* "2026-10-03" -> "Oct. 3, 2026". Parsed by hand: new Date('2026-10-03') is UTC midnight
     and would print the previous day in US time zones. */
  function formatDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    return m ? MONTHS[+m[2] - 1] + ' ' + (+m[3]) + ', ' + m[1] : (iso || '');
  }

  global.FPSRecordNote = { note: note, onField: onField, formatDate: formatDate };
})(typeof window !== 'undefined' ? window : this);
