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

  document.addEventListener('DOMContentLoaded', function () {
    initSparklines();
    initCoverFallback();
    initKeyNav();
  });
})();
