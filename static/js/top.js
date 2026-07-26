(function () {
  'use strict';

  var SVG_NS = 'http://www.w3.org/2000/svg';

  // resolve img/w.png relative to this script's own URL, so it works at any
  // page depth (/, /en/wikipedia/2026/7/10.html, ...)
  var FALLBACK_COVER = document.currentScript ?
    document.currentScript.src.replace(/js\/top\.js.*$/, 'img/w.png') : '/img/w.png';

  function initSparklines() {
    var spans = document.querySelectorAll('span.sparkline');
    for (var i = 0; i < spans.length; i++) {
      var span = spans[i];
      var raw = span.textContent.split(',');
      var values = [];
      for (var j = 0; j < raw.length; j++) {
        var n = parseFloat(raw[j]);
        if (isNaN(n)) { values = []; break; }
        values.push(n);
      }
      if (values.length === 0) { continue; }

      var min = values[0];
      var max = values[0];
      for (var k = 1; k < values.length; k++) {
        if (values[k] < min) { min = values[k]; }
        if (values[k] > max) { max = values[k]; }
      }

      var w = 50;
      var h = 14;
      var range = max - min || 1;
      var points = '';
      for (var p = 0; p < values.length; p++) {
        var x = values.length > 1 ? (p / (values.length - 1)) * w : w / 2;
        var y = h - ((values[p] - min) / range) * h;
        if (p > 0) { points += ' '; }
        points += x.toFixed(1) + ',' + y.toFixed(1);
      }

      var svg = document.createElementNS(SVG_NS, 'svg');
      svg.setAttribute('class', 'peity');
      svg.setAttribute('width', String(w));
      svg.setAttribute('height', String(h));

      var polyline = document.createElementNS(SVG_NS, 'polyline');
      polyline.setAttribute('points', points);
      polyline.setAttribute('fill', 'none');
      polyline.setAttribute('stroke', 'rgba(116,131,138,0.7)');
      polyline.setAttribute('stroke-width', '1');
      svg.appendChild(polyline);

      span.insertAdjacentElement('afterend', svg);
    }
  }

  function initCoverFallback() {
    var imgs = document.querySelectorAll('.cover-art img');
    function swap(img) {
      if (img.getAttribute('data-fallback')) { return; }
      img.setAttribute('data-fallback', '1');
      img.src = FALLBACK_COVER;
    }
    for (var i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      img.addEventListener('error', function (event) { swap(event.target); });
      if (img.complete && img.naturalWidth === 0) { swap(img); }
    }
  }

  function initKeyNav() {
    var currentIndex = -1;

    document.addEventListener('keydown', function (event) {
      if (event.metaKey || event.ctrlKey || event.altKey) { return; }

      var key = event.key;
      if (key !== 'j' && key !== 'k') { return; }

      var rows = document.querySelectorAll('li.row');
      if (rows.length === 0) { return; }

      if (key === 'j') {
        currentIndex = currentIndex < rows.length - 1 ? currentIndex + 1 : rows.length - 1;
      } else {
        currentIndex = currentIndex > 0 ? currentIndex - 1 : 0;
      }

      rows[currentIndex].scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  // bumped when the hint's wording changes, so a stale dismissal doesn't hide new copy
  var A2HS_KEY = 'a2hs-dismissed-v2';

  // iOS Share glyph: tray with an arrow leaving the top
  var SHARE_SVG = '<svg class="a2hs-share" viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true" focusable="false">' +
    '<path d="M12 15V3"/><path d="M8 7l4-4 4 4"/>' +
    '<path d="M8 10H6a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2h-2"/></svg>';

  // Only Safari and (since 2025) Chrome expose "Add to Home Screen" on iOS.
  // Brave ships Safari's UA with "Brave" appended and also exposes navigator.brave.
  function iosBrowser() {
    var ua = navigator.userAgent;
    if (/CriOS/.test(ua)) { return {name: 'Chrome', canInstall: true}; }
    if (/FxiOS/.test(ua)) { return {name: 'Firefox', canInstall: false}; }
    if (/EdgiOS/.test(ua)) { return {name: 'Edge', canInstall: false}; }
    if (/OPiOS|OPT\//.test(ua)) { return {name: 'Opera', canInstall: false}; }
    if (/\bBrave\b/.test(ua) || navigator.brave) { return {name: 'Brave', canInstall: false}; }
    return {name: 'Safari', canInstall: true};
  }

  function dismissed() {
    try {
      return window.localStorage.getItem(A2HS_KEY) === '1';
    } catch (e) { return false; }  // private browsing: show the hint, just don't persist
  }

  function rememberDismissal() {
    try { window.localStorage.setItem(A2HS_KEY, '1'); } catch (e) { /* ignore */ }
  }

  function alreadyInstalled() {
    return !!navigator.standalone ||
      window.matchMedia('(display-mode: standalone)').matches;
  }

  function eligible() {
    if (alreadyInstalled()) { return false; }
    if ((document.documentElement.lang || 'en').slice(0, 2) !== 'en') { return false; }
    return !dismissed();
  }

  function whenReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  // Builds the bottom bar. `action` is optional: present only where the browser
  // gives us a real one-tap install (Chrome/Edge via beforeinstallprompt).
  function showBar(titleHTML, stepsHTML, action) {
    var existing = document.querySelector('.a2hs');
    if (existing) { existing.parentNode.removeChild(existing); }

    var bar = document.createElement('div');
    bar.className = 'a2hs';

    var body = document.createElement('div');
    body.className = 'a2hs-body';

    var title = document.createElement('p');
    title.className = 'a2hs-title';
    title.innerHTML = titleHTML;
    body.appendChild(title);

    if (stepsHTML) {
      var steps = document.createElement('p');
      steps.className = 'a2hs-steps';
      steps.innerHTML = stepsHTML;
      body.appendChild(steps);
    }

    bar.appendChild(body);

    if (action) {
      var go = document.createElement('button');
      go.type = 'button';
      go.className = 'a2hs-go';
      go.textContent = action.label;
      go.addEventListener('click', function () { action.onClick(bar); });
      bar.appendChild(go);
    }

    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'a2hs-close';
    close.setAttribute('aria-label', 'Dismiss');
    close.innerHTML = '&times;';
    close.addEventListener('click', function () {
      removeBar();
      rememberDismissal();
    });
    bar.appendChild(close);

    document.body.appendChild(bar);
  }

  function removeBar() {
    var bar = document.querySelector('.a2hs');
    if (bar && bar.parentNode) { bar.parentNode.removeChild(bar); }
  }

  // --- iOS: no install API exists, so all we can do is point at the Share menu.
  function initAddToHome() {
    var ua = navigator.userAgent;
    var isIOS = /iP(hone|od|ad)/.test(navigator.platform) ||
      (navigator.maxTouchPoints > 1 && /Mac/.test(ua) && 'ontouchend' in document);
    if (!isIOS || !eligible()) { return; }

    var browser = iosBrowser();
    var steps;
    if (browser.name === 'Chrome') {
      steps = 'Tap ' + SHARE_SVG + ' next to the address bar, pick ' +
        '\u201CAdd to Home Screen,\u201D then turn on <b>Open as Web App</b>.';
    } else if (browser.canInstall) {
      steps = 'Tap ' + SHARE_SVG + ' in the Safari toolbar, then pick ' +
        '\u201CAdd to Home Screen.\u201D';
    } else {
      steps = browser.name + ' for iOS can\u2019t do this. Open this page in ' +
        '<b>Safari</b>, tap ' + SHARE_SVG + ', then pick \u201CAdd to Home Screen.\u201D';
    }
    showBar('Add <b>Top 100</b> to your Home Screen', steps, null);
  }

  // --- Chrome/Edge (Android + desktop): a genuine one-tap install.
  var deferredPrompt = null;

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    if (!eligible()) { return; }
    whenReady(function () {
      showBar('Install <b>Top 100</b>', 'Get the daily chart as an app.', {
        label: 'Install',
        onClick: function () {
          if (!deferredPrompt) { return; }
          var prompt = deferredPrompt;
          deferredPrompt = null;
          prompt.prompt();
          prompt.userChoice.then(function (choice) {
            // either way, stop asking: accepted installs, dismissed means no
            removeBar();
            if (choice.outcome !== 'accepted') { rememberDismissal(); }
          });
        }
      });
    });
  });

  window.addEventListener('appinstalled', function () {
    deferredPrompt = null;
    removeBar();
    rememberDismissal();
  });

  // Registering a fetch-handling worker is what makes Chrome fire
  // beforeinstallprompt at all; it also keeps the installed app usable offline.
  function initServiceWorker() {
    if (!('serviceWorker' in navigator) || !window.isSecureContext) { return; }
    navigator.serviceWorker.register('/sw.js', {scope: '/'}).catch(function () {
      /* registration is an enhancement; never break the page over it */
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initSparklines();
    initCoverFallback();
    initKeyNav();
    initAddToHome();
  });

  window.addEventListener('load', initServiceWorker);
})();
