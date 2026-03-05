(function () {
  var KEY = "songhefte_theme";
  var ACCESS_KEY = "songhefte_access_v1";
  var ACCESS_PASSWORD_HASH = "20d2c5c599fb17e227d9b2e324aa490ba32f1fad373a8126a83579ca4fca7c36"; // "allsongtilfolket"

  function sha256Hex(text) {
    if (!window.crypto || !window.crypto.subtle || !window.TextEncoder) {
      return Promise.resolve("");
    }
    var bytes = new TextEncoder().encode(text);
    return window.crypto.subtle.digest("SHA-256", bytes).then(function (buf) {
      var arr = Array.from(new Uint8Array(buf));
      return arr.map(function (b) { return b.toString(16).padStart(2, "0"); }).join("");
    });
  }

  function initAccessGate() {
    var expected = (ACCESS_PASSWORD_HASH || "").trim().toLowerCase();
    if (!expected) return Promise.resolve();

    var saved = "";
    try { saved = (localStorage.getItem(ACCESS_KEY) || "").trim().toLowerCase(); } catch (e) {}
    if (saved === expected) return Promise.resolve();

    document.body.setAttribute("data-locked", "true");

    return new Promise(function (resolve) {
      var gate = document.createElement("section");
      gate.className = "access-gate";
      gate.innerHTML =
        '<div class="access-gate__card">' +
          '<h1 class="access-gate__title">Torbjørns utvalde songar</h1>' +
          '<p class="access-gate__text">Skriv inn passord for å opne sida.</p>' +
          '<form class="access-gate__form">' +
            '<label class="access-gate__label" for="access-password">Passord</label>' +
            '<input id="access-password" class="access-gate__input" type="password" autocomplete="current-password" required />' +
            '<button class="access-gate__button" type="submit">Opne</button>' +
            '<p class="access-gate__error" role="alert" aria-live="polite"></p>' +
          "</form>" +
        "</div>";
      document.body.appendChild(gate);

      var form = gate.querySelector(".access-gate__form");
      var input = gate.querySelector(".access-gate__input");
      var error = gate.querySelector(".access-gate__error");
      var btn = gate.querySelector(".access-gate__button");
      if (input) input.focus();

      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!input) return;
        var candidate = input.value || "";
        btn.disabled = true;
        error.textContent = "";

        sha256Hex(candidate).then(function (hash) {
          if ((hash || "").toLowerCase() === expected) {
            try { localStorage.setItem(ACCESS_KEY, expected); } catch (err) {}
            document.body.removeAttribute("data-locked");
            gate.remove();
            resolve();
            return;
          }
          error.textContent = "Feil passord. Prøv igjen.";
          input.select();
        }).catch(function () {
          error.textContent = "Klarte ikkje sjekke passord. Prøv igjen.";
        }).finally(function () {
          btn.disabled = false;
        });
      });
    });
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    var btn = document.querySelector(".dark-toggle");
    if (!btn) return;
    var dark = theme === "dark";
    btn.setAttribute("aria-pressed", String(dark));
    var icon = btn.querySelector(".dark-toggle__icon");
    var txt = btn.querySelector(".dark-toggle__text");
    if (icon) icon.textContent = dark ? "☀︎" : "☾";
    if (txt) txt.textContent = dark ? "Lys" : "Mørk";
  }

  function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) {}
    var prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(saved || (prefersDark ? "dark" : "light"));

    var btn = document.querySelector(".dark-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var now = document.documentElement.getAttribute("data-theme") || "light";
      var next = now === "dark" ? "light" : "dark";
      setTheme(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
    });
  }

  function initPrint() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-song-print]");
      if (!btn) return;
      e.preventDefault();
      window.print();
    });
  }

  function initToTop() {
    var btn = document.querySelector(".to-top");
    if (!btn) return;

    function update() {
      btn.style.display = window.scrollY > 400 ? "inline-flex" : "none";
    }

    window.addEventListener("scroll", update, { passive: true });
    update();

    btn.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function initSearchAndFilter() {
    var input = document.getElementById("song-live-search");
    var results = document.querySelector(".song-search__results");
    var toc = document.querySelector(".song-toc");
    var jump = document.querySelector(".song-toc-jump");
    var langRoot = document.querySelector(".song-language-filter");

    if (!input || !results || !toc) return;

    var index = [];
    fetch("data/sok-index.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) { index = Array.isArray(data) ? data : []; })
      .catch(function () { index = []; });

    var activeLang = "";

    function applyLangFilter() {
      var sections = toc.querySelectorAll(".song-toc-section");
      sections.forEach(function (sec) {
        var visible = 0;
        var items = sec.querySelectorAll(".song-toc-list li[data-sprak]");
        items.forEach(function (li) {
          var codes = (li.getAttribute("data-sprak") || "").trim();
          var arr = codes ? codes.split(/\s+/) : [];
          var show = !activeLang || arr.indexOf(activeLang) !== -1;
          li.style.display = show ? "" : "none";
          if (show) visible += 1;
        });
        sec.style.display = visible ? "" : "none";
        if (jump) {
          var st = sec.getAttribute("data-songtype");
          var jumpItem = jump.querySelector('.song-toc-jump__item[data-songtype="' + st + '"]');
          if (jumpItem) jumpItem.style.display = visible ? "" : "none";
        }
      });
    }

    if (langRoot) {
      langRoot.addEventListener("click", function (e) {
        var btn = e.target.closest("button[data-sprak]");
        if (!btn) return;
        activeLang = btn.getAttribute("data-sprak") || "";
        langRoot.querySelectorAll("button[data-sprak]").forEach(function (b) {
          b.setAttribute("aria-pressed", "false");
        });
        btn.setAttribute("aria-pressed", "true");
        applyLangFilter();
      });
    }

    function renderResults(items, q) {
      if (!q || q.length < 2) {
        results.innerHTML = "";
        toc.style.display = "";
        if (jump) jump.style.display = "";
        if (langRoot) langRoot.style.display = "";
        applyLangFilter();
        return;
      }

      if (!items.length) {
        results.innerHTML = '<div class="song-search__empty">Ingen treff.</div>';
        toc.style.display = "none";
        if (jump) jump.style.display = "none";
        if (langRoot) langRoot.style.display = "none";
        return;
      }

      var html = '<div class="song-search__count">Treff: ' + items.length + '</div><ul class="song-search__list">';
      items.forEach(function (it) {
        html += '<li><a href="' + it.link + '">' + it.title + '</a></li>';
      });
      html += "</ul>";
      results.innerHTML = html;
      toc.style.display = "none";
      if (jump) jump.style.display = "none";
      if (langRoot) langRoot.style.display = "none";
    }

    var timer = null;
    input.addEventListener("input", function () {
      var q = (input.value || "").trim().toLowerCase();
      clearTimeout(timer);
      timer = setTimeout(function () {
        if (q.length < 2) {
          renderResults([], q);
          return;
        }
        var hits = index.filter(function (it) {
          return (it.text || "").toLowerCase().indexOf(q) !== -1;
        }).slice(0, 200);
        renderResults(hits, q);
      }, 120);
    });

    applyLangFilter();
  }

  initTheme();
  initAccessGate().then(function () {
    initPrint();
    initToTop();
    initSearchAndFilter();
  });
})();
