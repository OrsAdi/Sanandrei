// Tabele sortabile: <table class="data sortable"> și <th class="sortable" data-type="num">
document.querySelectorAll("table.sortable").forEach((table) => {
  const headers = table.querySelectorAll("th.sortable");
  headers.forEach((th) => {
    th.addEventListener("click", () => {
      const index = Array.from(th.parentNode.children).indexOf(th);
      const numeric = th.dataset.type === "num";
      // al doilea click inversează ordinea; implicit: numere descrescător, text crescător
      const asc = th.classList.contains("sorted-desc") ? true
        : th.classList.contains("sorted-asc") ? false : !numeric;
      headers.forEach((h) => h.classList.remove("sorted-asc", "sorted-desc"));
      th.classList.add(asc ? "sorted-asc" : "sorted-desc");
      const body = table.tBodies[0];
      const rows = Array.from(body.rows);
      const value = (row) => {
        const cell = row.children[index];
        const raw = (cell.dataset.value ?? cell.textContent).trim();
        return numeric ? parseFloat(raw.replace(",", ".")) || 0 : raw.toLowerCase();
      };
      rows.sort((a, b) => {
        const va = value(a), vb = value(b);
        if (va < vb) return asc ? -1 : 1;
        if (va > vb) return asc ? 1 : -1;
        return 0;
      });
      rows.forEach((r) => body.appendChild(r));
    });
  });
});

// Numărătoare inversă până la următorul meci: <div class="countdown" data-kickoff="ISO">
document.querySelectorAll(".countdown[data-kickoff]").forEach((el) => {
  const target = new Date(el.dataset.kickoff).getTime();
  const parts = { d: el.querySelector("[data-d]"), h: el.querySelector("[data-h]"), m: el.querySelector("[data-m]"), s: el.querySelector("[data-s]") };
  const tick = () => {
    let diff = Math.max(0, Math.floor((target - Date.now()) / 1000));
    const d = Math.floor(diff / 86400); diff -= d * 86400;
    const h = Math.floor(diff / 3600); diff -= h * 3600;
    const m = Math.floor(diff / 60); const s = diff - m * 60;
    parts.d.textContent = d; parts.h.textContent = String(h).padStart(2, "0");
    parts.m.textContent = String(m).padStart(2, "0"); parts.s.textContent = String(s).padStart(2, "0");
  };
  tick();
  setInterval(tick, 1000);
});

// Filtru rapid pentru tabele: <input data-filter="#id-tabel">
document.querySelectorAll("input[data-filter]").forEach((input) => {
  const table = document.querySelector(input.dataset.filter);
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    table.querySelectorAll("tbody tr").forEach((tr) => {
      tr.hidden = q && !tr.textContent.toLowerCase().includes(q);
    });
  });
});
