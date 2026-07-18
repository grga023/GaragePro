/* GaragePro — custom month calendar (no external deps; CSP-safe).
 * Renders a month grid, loads appointments from the JSON feed, and opens a
 * "day detail" modal (the tapped day gets bigger, listing every booking).
 * All user-supplied text is inserted via textContent to prevent XSS.
 */
(function () {
  var root = document.getElementById('calendar');
  if (!root) return;

  var eventsUrl = root.dataset.eventsUrl;
  var newUrl = root.dataset.newUrl;
  var isAdmin = root.dataset.isAdmin === '1';
  var initialDate = root.dataset.initialDate;

  var titleEl = root.querySelector('[data-cal="title"]');
  var gridEl = root.querySelector('[data-cal="grid"]');
  var weekdaysEl = root.querySelector('[data-cal="weekdays"]');
  var loadingEl = root.querySelector('[data-cal="loading"]');
  var workerFilter = document.getElementById('cal-worker-filter');

  var MONTHS = ['januar', 'februar', 'mart', 'april', 'maj', 'jun', 'jul',
    'avgust', 'septembar', 'oktobar', 'novembar', 'decembar'];
  var WEEK_SHORT = ['Pon', 'Uto', 'Sre', 'Čet', 'Pet', 'Sub', 'Ned'];
  var WEEK_FULL = ['ponedeljak', 'utorak', 'sreda', 'četvrtak', 'petak', 'subota', 'nedelja'];
  var PALETTE = ['#0d6efd', '#198754', '#dc3545', '#6f42c1', '#fd7e14',
    '#20c997', '#d63384', '#0dcaf0'];

  function workerColor(id) { return PALETTE[Math.abs(id || 0) % PALETTE.length]; }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function fmtISO(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function mondayIndex(d) { return (d.getDay() + 6) % 7; }  // 0=Mon .. 6=Sun
  function sameYMD(a, b) {
    return a.getFullYear() === b.getFullYear()
      && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  }
  function parseDate(s) {
    if (!s) return null;
    var p = s.split('-');
    if (p.length !== 3) return null;
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }

  var view = parseDate(initialDate) || new Date();
  view.setDate(1);
  var eventsByDate = {};

  var modalEl = document.getElementById('dayModal');
  var dayModal = (modalEl && window.bootstrap) ? new bootstrap.Modal(modalEl) : null;

  // ── Grid ────────────────────────────────────────────────────────────
  function renderWeekdays() {
    weekdaysEl.innerHTML = '';
    WEEK_SHORT.forEach(function (w) {
      var c = document.createElement('div');
      c.className = 'cal-weekday';
      c.textContent = w;
      weekdaysEl.appendChild(c);
    });
  }

  function gridStartDate() {
    var first = new Date(view.getFullYear(), view.getMonth(), 1);
    var start = new Date(first);
    start.setDate(first.getDate() - mondayIndex(first));
    return start;
  }

  function chip(ev) {
    var c = document.createElement('div');
    c.className = 'cal-event status-' + ev.status;
    c.style.borderLeftColor = workerColor(ev.worker_id);
    var t = document.createElement('span');
    t.className = 'cal-time';
    t.textContent = ev.start_time + ' ';
    var p = document.createElement('span');
    p.className = 'cal-plate';
    p.textContent = ev.plate;
    c.appendChild(t);
    c.appendChild(p);
    return c;
  }

  function render() {
    titleEl.textContent = cap(MONTHS[view.getMonth()]) + ' ' + view.getFullYear();
    gridEl.innerHTML = '';
    var start = gridStartDate();
    var today = new Date();
    for (var i = 0; i < 42; i++) {
      var d = new Date(start);
      d.setDate(start.getDate() + i);
      var iso = fmtISO(d);
      var cell = document.createElement('div');
      cell.className = 'cal-cell';
      if (d.getMonth() !== view.getMonth()) cell.classList.add('other-month');
      if (sameYMD(d, today)) cell.classList.add('today');
      cell.dataset.date = iso;

      var head = document.createElement('div');
      head.className = 'cal-dayhead';
      var num = document.createElement('span');
      num.className = 'cal-daynum';
      num.textContent = d.getDate();
      head.appendChild(num);

      var list = eventsByDate[iso] || [];
      if (list.length) {
        var cnt = document.createElement('span');
        cnt.className = 'cal-count';
        cnt.textContent = list.length;
        head.appendChild(cnt);
      }
      cell.appendChild(head);

      var evWrap = document.createElement('div');
      evWrap.className = 'cal-events';
      list.slice(0, 3).forEach(function (ev) { evWrap.appendChild(chip(ev)); });
      if (list.length > 3) {
        var more = document.createElement('div');
        more.className = 'cal-more';
        more.textContent = '+' + (list.length - 3) + ' više';
        evWrap.appendChild(more);
      }
      cell.appendChild(evWrap);

      cell.addEventListener('click', (function (dd) {
        return function () { openDay(dd); };
      })(new Date(d)));
      gridEl.appendChild(cell);
    }
  }

  function fetchEvents(cb) {
    var start = gridStartDate();
    var end = new Date(start);
    end.setDate(start.getDate() + 42);
    var url = eventsUrl + '?start=' + fmtISO(start) + '&end=' + fmtISO(end);
    if (isAdmin && workerFilter && workerFilter.value) {
      url += '&worker_id=' + encodeURIComponent(workerFilter.value);
    }
    if (loadingEl) loadingEl.classList.remove('d-none');
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (items) {
        eventsByDate = {};
        items.forEach(function (ev) {
          (eventsByDate[ev.date] = eventsByDate[ev.date] || []).push(ev);
        });
        render();
        if (cb) cb();
      })
      .catch(function () { render(); })
      .then(function () { if (loadingEl) loadingEl.classList.add('d-none'); });
  }

  // ── Day detail modal ────────────────────────────────────────────────
  function linkBtn(text, cls, href) {
    var a = document.createElement('a');
    a.className = 'btn btn-sm ' + cls;
    a.href = href;
    a.textContent = text;
    return a;
  }

  function postForm(url, fields) {
    var f = document.createElement('form');
    f.method = 'post';
    f.action = url;
    var t = document.createElement('input');
    t.type = 'hidden';
    t.name = 'csrf_token';
    t.value = window.CSRF_TOKEN || '';
    f.appendChild(t);
    Object.keys(fields || {}).forEach(function (k) {
      var i = document.createElement('input');
      i.type = 'hidden';
      i.name = k;
      i.value = fields[k];
      f.appendChild(i);
    });
    document.body.appendChild(f);
    f.submit();
  }

  function actionBtn(text, cls, url, fields, confirmMsg) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'btn btn-sm ' + cls;
    b.textContent = text;
    b.addEventListener('click', function () {
      if (confirmMsg && !window.confirm(confirmMsg)) return;
      postForm(url, fields);
    });
    return b;
  }

  function apptCard(ev) {
    var card = document.createElement('div');
    card.className = 'cal-appt status-' + ev.status;
    card.style.borderLeftColor = workerColor(ev.worker_id);

    var row = document.createElement('div');
    row.className = 'd-flex justify-content-between align-items-center gap-2';
    var timeEl = document.createElement('strong');
    timeEl.textContent = ev.start_time + '–' + ev.end_time;
    var badge = document.createElement('span');
    badge.className = 'badge';
    badge.style.backgroundColor = ev.service_type_color || '#6c757d';
    badge.style.color = '#fff';
    badge.textContent = ev.service_type_label;
    row.appendChild(timeEl);
    row.appendChild(badge);
    card.appendChild(row);

    var carLine = document.createElement('div');
    carLine.className = 'mt-1';
    var plate = document.createElement('span');
    plate.className = 'plate-badge';
    plate.textContent = ev.plate;
    carLine.appendChild(plate);
    if (ev.car_desc) {
      var desc = document.createElement('span');
      desc.className = 'ms-2';
      desc.textContent = ev.car_desc;
      carLine.appendChild(desc);
    }
    card.appendChild(carLine);

    if (ev.owner || ev.phone) {
      var owner = document.createElement('div');
      owner.className = 'small text-muted';
      owner.textContent = ev.owner + (ev.phone ? ' · ' + ev.phone : '');
      card.appendChild(owner);
    }

    if (isAdmin && ev.worker) {
      var wk = document.createElement('div');
      wk.className = 'small';
      wk.textContent = 'Radnik: ' + ev.worker;
      card.appendChild(wk);
    }

    var st = document.createElement('span');
    st.className = 'badge cal-status-' + ev.status + ' mt-1';
    st.textContent = ev.status_label;
    card.appendChild(st);

    if (ev.note) {
      var note = document.createElement('div');
      note.className = 'small mt-1';
      note.textContent = ev.note;
      card.appendChild(note);
    }

    var actions = document.createElement('div');
    actions.className = 'd-flex flex-wrap gap-1 mt-2';
    actions.appendChild(linkBtn('🚗 Vozilo', 'btn-outline-primary', ev.car_url));
    actions.appendChild(linkBtn('🔧 Napravi servis', 'btn-outline-success', ev.service_url));
    if (ev.can_edit) {
      actions.appendChild(linkBtn('✏️ Izmeni', 'btn-outline-secondary', ev.edit_url));
      if (ev.status !== 'done') {
        actions.appendChild(actionBtn('✓ Završi', 'btn-outline-success', ev.status_url, { status: 'done' }));
      }
      if (ev.status !== 'cancelled') {
        actions.appendChild(actionBtn('✕ Otkaži', 'btn-outline-warning', ev.status_url, { status: 'cancelled' }));
      }
      actions.appendChild(actionBtn('🗑️', 'btn-outline-danger', ev.delete_url, {}, 'Obrisati ovaj termin?'));
    }
    card.appendChild(actions);
    return card;
  }

  function openDay(d) {
    if (!dayModal) return;
    var iso = fmtISO(d);
    var list = (eventsByDate[iso] || []).slice().sort(function (a, b) {
      return a.start_time.localeCompare(b.start_time);
    });
    var dayTitle = modalEl.querySelector('[data-cal="day-title"]');
    var body = modalEl.querySelector('[data-cal="day-body"]');
    var addBtn = modalEl.querySelector('[data-cal="day-add"]');

    dayTitle.textContent = cap(WEEK_FULL[mondayIndex(d)]) + ', ' + d.getDate()
      + '. ' + MONTHS[d.getMonth()] + ' ' + d.getFullYear() + '.';
    addBtn.href = newUrl + '?date=' + iso;

    body.innerHTML = '';
    if (!list.length) {
      var em = document.createElement('p');
      em.className = 'text-muted text-center py-3 mb-0';
      em.textContent = 'Nema zakazanih termina za ovaj dan.';
      body.appendChild(em);
    }
    list.forEach(function (ev) { body.appendChild(apptCard(ev)); });
    dayModal.show();
  }

  // ── Wire up ─────────────────────────────────────────────────────────
  root.querySelector('[data-cal="prev"]').addEventListener('click', function () {
    view.setMonth(view.getMonth() - 1);
    fetchEvents();
  });
  root.querySelector('[data-cal="next"]').addEventListener('click', function () {
    view.setMonth(view.getMonth() + 1);
    fetchEvents();
  });
  root.querySelector('[data-cal="today"]').addEventListener('click', function () {
    view = new Date();
    view.setDate(1);
    fetchEvents();
  });
  if (workerFilter) workerFilter.addEventListener('change', function () { fetchEvents(); });

  renderWeekdays();

  // On first load, if navigated with an explicit ?date=, open that day.
  var autoOpen = null;
  try {
    var qs = new URLSearchParams(window.location.search);
    if (qs.has('date')) autoOpen = parseDate(qs.get('date'));
  } catch (e) { autoOpen = null; }

  fetchEvents(autoOpen ? function () { openDay(autoOpen); } : null);
})();
