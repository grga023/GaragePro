(function () {
  "use strict";

  function fmt(n) {
    n = Number(n) || 0;
    var s = n.toLocaleString("sr-RS", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return s + " " + (window.CURRENCY || "RSD");
  }

  function recalc() {
    var rows = document.querySelectorAll("#partsBody .part-row");
    var partsTotal = 0;
    rows.forEach(function (row) {
      var qty = parseFloat(row.querySelector(".qty").value) || 0;
      var price = parseFloat(row.querySelector(".price").value) || 0;
      var line = qty * price;
      partsTotal += line;
      row.querySelector(".line-total").textContent = fmt(line);
    });
    var labor = parseFloat(document.getElementById("laborPrice").value) || 0;

    document.getElementById("partsTotal").textContent = fmt(partsTotal);
    document.getElementById("sumParts").textContent = fmt(partsTotal);
    document.getElementById("sumLabor").textContent = fmt(labor);
    document.getElementById("sumTotal").textContent = fmt(partsTotal + labor);
  }

  function addRow() {
    var tpl = document.getElementById("partRowTemplate");
    var clone = tpl.content.cloneNode(true);
    document.getElementById("partsBody").appendChild(clone);
    recalc();
  }

  document.addEventListener("click", function (e) {
    if (e.target && e.target.id === "addPart") {
      addRow();
    }
    if (e.target && e.target.classList.contains("remove-part")) {
      var row = e.target.closest(".part-row");
      if (row) { row.remove(); recalc(); }
    }
  });

  document.addEventListener("input", function (e) {
    if (e.target && (e.target.classList.contains("qty") ||
                     e.target.classList.contains("price") ||
                     e.target.classList.contains("disc") ||
                     e.target.id === "laborPrice")) {
      recalc();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    // start with one empty row if none exist
    if (document.querySelectorAll("#partsBody .part-row").length === 0) {
      addRow();
    }
    recalc();
  });
})();
