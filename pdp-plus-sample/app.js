/* Climate Pulse · unofficial PDP layout sample — hash router, no build step */
(function () {
  "use strict";

  var VIEWS = ["home", "viewer", "climate-pulse", "visualizations", "metadata"];

  var ARCGIS = [
    {
      title: "KE Dashboard",
      blurb: "Kenya Climate Pulse operational dashboard",
      url: "https://africageoportal.maps.arcgis.com/apps/dashboards/d1fd5155dc8c49c5b3873671fedc4c29"
    },
    {
      title: "KE Experience",
      blurb: "Kenya Experience Builder app",
      url: "https://experience.arcgis.com/experience/6da4c9d0cee24a54b7ddf310d64f456f"
    },
    {
      title: "KE Stress",
      blurb: "Kenya stress / latest-month focus dashboard",
      url: "https://africageoportal.maps.arcgis.com/apps/dashboards/4ac53ce375a5458a8a9d60d5ef609d95"
    },
    {
      title: "NGA Dashboard",
      blurb: "Nigeria extended demo",
      url: "https://africageoportal.maps.arcgis.com/apps/dashboards/e171cde9fdbb4e7c90aabf6c763bd71e"
    },
    {
      title: "MEX Dashboard",
      blurb: "Mexico extended demo",
      url: "https://africageoportal.maps.arcgis.com/apps/dashboards/5c115185be254e958da415b32e89ea56"
    },
    {
      title: "IND Dashboard",
      blurb: "India extended demo",
      url: "https://africageoportal.maps.arcgis.com/apps/dashboards/e50244312abd4e6188f477745aa0a538"
    },
    {
      title: "Multi4 Dashboard",
      blurb: "KEN · NGA · MEX · IND combined view",
      url: "https://africageoportal.maps.arcgis.com/apps/dashboards/875dcdccb58c4cd68add56a34d301d91"
    },
    {
      title: "Multi4 Web Map",
      blurb: "Multi-country web map item",
      url: "https://africageoportal.maps.arcgis.com/home/item.html?id=5c054a072dd14ffcadcfc7b35cc9a53b"
    }
  ];

  var COUNTRIES = {
    kenya: {
      title: "Kenya",
      desc: "Primary Track 1 country. Local risk-map preview; live ArcGIS views are Owner-only.",
      img: "assets/ke_adm1_risk_map.png",
      alt: "Kenya ADM1 climate-demographic risk preview",
      arcgis: "https://africageoportal.maps.arcgis.com/apps/dashboards/d1fd5155dc8c49c5b3873671fedc4c29",
      cta: "Open Climate Pulse operational view",
      ctaPrimary: true
    },
    nigeria: {
      title: "Nigeria",
      desc: "Extended demo. Age-sex still national-share proxy. Open Owner-only dashboard.",
      img: null,
      alt: "",
      arcgis: "https://africageoportal.maps.arcgis.com/apps/dashboards/e171cde9fdbb4e7c90aabf6c763bd71e",
      cta: "Open Climate Pulse (extended demo)",
      ctaPrimary: false
    },
    mexico: {
      title: "Mexico",
      desc: "Extended demo. Fertility-only DIOS when present. Open Owner-only dashboard.",
      img: null,
      alt: "",
      arcgis: "https://africageoportal.maps.arcgis.com/apps/dashboards/5c115185be254e958da415b32e89ea56",
      cta: "Open Climate Pulse (extended demo)",
      ctaPrimary: false
    },
    india: {
      title: "India",
      desc: "Extended demo. Short SPI reference; no DIOS on disk. Open Owner-only dashboard.",
      img: null,
      alt: "",
      arcgis: "https://africageoportal.maps.arcgis.com/apps/dashboards/e50244312abd4e6188f477745aa0a538",
      cta: "Open Climate Pulse (extended demo)",
      ctaPrimary: false
    }
  };

  function parseHash() {
    var h = (location.hash || "#/").replace(/^#\/?/, "");
    h = h.split("?")[0].split("/")[0];
    if (!h || h === "") return "home";
    if (VIEWS.indexOf(h) === -1) return "home";
    return h;
  }

  function showView(name) {
    if (VIEWS.indexOf(name) === -1) name = "home";
    document.querySelectorAll(".view").forEach(function (el) {
      el.classList.toggle("active", el.getAttribute("data-view") === name);
    });
    /* Climate Pulse is nested under Visualizations (not a top-nav product) */
    var navActive = name === "climate-pulse" ? "visualizations" : name;
    document.querySelectorAll(".main-nav a").forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-nav") === navActive);
    });
    window.scrollTo(0, 0);
  }

  function go(name) {
    if (name === "home") {
      location.hash = "#/";
    } else {
      location.hash = "#/" + name;
    }
    showView(name);
  }

  function renderOpGrid() {
    var grid = document.getElementById("op-grid");
    if (!grid) return;
    grid.innerHTML = ARCGIS.map(function (item) {
      return (
        '<article class="op-card">' +
        "<div><h4>" +
        item.title +
        '</h4><p>' +
        item.blurb +
        ' · Owner-only</p></div>' +
        '<a class="btn btn-primary" href="' +
        item.url +
        '" target="_blank" rel="noopener">Open</a>' +
        "</article>"
      );
    }).join("");
  }

  function setCountry(key) {
    var c = COUNTRIES[key] || COUNTRIES.kenya;
    document.querySelectorAll("#country-list button").forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-country") === key);
    });
    var title = document.getElementById("float-title");
    var desc = document.getElementById("float-desc");
    var link = document.getElementById("float-arcgis");
    var cta = document.getElementById("float-cp-cta");
    var stage = document.getElementById("map-stage");
    if (title) title.textContent = c.title;
    if (desc) desc.textContent = c.desc;
    if (link) link.href = c.arcgis;
    if (cta) {
      cta.textContent = c.cta || "Open Climate Pulse operational view";
      cta.classList.toggle("btn-primary", !!c.ctaPrimary);
      cta.classList.toggle("btn-secondary", !c.ctaPrimary);
      cta.classList.toggle("btn-soft", !c.ctaPrimary);
    }
    if (!stage) return;
    if (c.img) {
      stage.innerHTML =
        '<img id="map-img" src="' +
        c.img +
        '" alt="' +
        c.alt +
        '" />';
    } else {
      stage.innerHTML =
        '<div class="map-placeholder">' +
        "<p><strong>" +
        c.title +
        "</strong></p>" +
        "<p>No local preview asset for this country.</p>" +
        '<p><a class="btn btn-primary" href="' +
        c.arcgis +
        '" target="_blank" rel="noopener">Open ArcGIS dashboard</a></p>' +
        "</div>";
    }
  }

  function onReady() {
    renderOpGrid();

    document.querySelectorAll("[data-go]").forEach(function (el) {
      el.addEventListener("click", function (e) {
        e.preventDefault();
        go(el.getAttribute("data-go"));
      });
    });

    document.querySelectorAll("[data-nav]").forEach(function (el) {
      el.addEventListener("click", function () {
        /* hash change handler will sync; allow default for <a href="#/..."> */
      });
    });

    document.querySelectorAll("#country-list button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setCountry(btn.getAttribute("data-country"));
      });
    });

    window.addEventListener("hashchange", function () {
      showView(parseHash());
    });

    showView(parseHash());
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }
})();
