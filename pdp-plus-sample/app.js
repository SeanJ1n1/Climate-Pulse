(function () {
  const items = [
    { title: "Kenya Dashboard", pill: "KEN", href: "https://africageoportal.maps.arcgis.com/apps/dashboards/d1fd5155dc8c49c5b3873671fedc4c29", note: "Primary Climate Pulse ops view" },
    { title: "Kenya Experience", pill: "KEN", href: "https://experience.arcgis.com/experience/6da4c9d0cee24a54b7ddf310d64f456f", note: "Experience Builder (Owner-only)" },
    { title: "Kenya Stress Dashboard", pill: "KEN", href: "https://africageoportal.maps.arcgis.com/apps/dashboards/4ac53ce375a5458a8a9d60d5ef609d95", note: "Population-stress ADM1/ADM2" },
    { title: "Nigeria Dashboard", pill: "NGA", href: "https://africageoportal.maps.arcgis.com/apps/dashboards/e171cde9fdbb4e7c90aabf6c763bd71e", note: "Extended country demo" },
    { title: "Mexico Dashboard", pill: "MEX", href: "https://africageoportal.maps.arcgis.com/apps/dashboards/5c115185be254e958da415b32e89ea56", note: "Extended country demo" },
    { title: "India Dashboard", pill: "IND", href: "https://africageoportal.maps.arcgis.com/apps/dashboards/e50244312abd4e6188f477745aa0a538", note: "Extended country demo" },
    { title: "Multi4 Dashboard", pill: "4 countries", href: "https://africageoportal.maps.arcgis.com/apps/dashboards/875dcdccb58c4cd68add56a34d301d91", note: "Combined operational view" },
    { title: "Multi4 Web Map", pill: "Item", href: "https://africageoportal.maps.arcgis.com/home/item.html?id=5c054a072dd14ffcadcfc7b35cc9a53b", note: "Underlying web map item" }
  ];
  const root = document.getElementById("arcgis-cards");
  if (!root) return;
  root.innerHTML = items.map(function (it) {
    return (
      '<div class="card">' +
        '<span class="pill">' + it.pill + '</span>' +
        '<h4>' + it.title + '</h4>' +
        '<p>' + it.note + ' · Owner-only</p>' +
        '<a class="btn" href="' + it.href + '" target="_blank" rel="noopener">Open in ArcGIS</a>' +
      '</div>'
    );
  }).join("");
})();
