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

// ---------------------------------------------------------------------------
// Site static (GitHub Pages): coșul, formularele și căutarea rulează în browser.
// ---------------------------------------------------------------------------
const SITE = window.SITE || {};
const CART_KEY = "sanandrei-cart";
const lei = (n) => n.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const jsonData = (id) => { const el = document.getElementById(id); return el ? JSON.parse(el.textContent) : null; };

const cart = {
  load() { try { return JSON.parse(localStorage.getItem(CART_KEY)) || []; } catch { return []; } },
  save(items) { try { localStorage.setItem(CART_KEY, JSON.stringify(items)); } catch { /* mod privat */ } updateBadge(); },
  add(slug, size, qty) {
    const items = cart.load();
    const found = items.find((i) => i.slug === slug && i.size === size);
    if (found) found.qty = Math.min(found.qty + qty, 99); else items.push({ slug, size, qty });
    cart.save(items);
  },
  // doar produsele care mai există și sunt în stoc
  lines(catalog) {
    return cart.load().filter((i) => catalog[i.slug] && catalog[i.slug].in_stock)
      .map((i) => ({ ...i, product: catalog[i.slug], subtotal: catalog[i.slug].price * i.qty }));
  },
};

function updateBadge() {
  const count = cart.load().reduce((s, i) => s + i.qty, 0);
  document.querySelectorAll("[data-cart-count]").forEach((el) => { el.textContent = count; el.hidden = !count; });
}
updateBadge();

// Pagina produsului: „Adaugă în coș”
document.querySelectorAll("form[data-add-to-cart]").forEach((form) => {
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const qty = Math.max(1, Math.min(20, parseInt(form.quantity.value, 10) || 1));
    cart.add(form.dataset.addToCart, form.size ? form.size.value : "", qty);
    form.querySelector(".form-status").hidden = false;
  });
});

// Pagina coșului
const cartView = document.querySelector("[data-cart-view]");
if (cartView) {
  const catalog = jsonData("shop-catalog") || {};
  const render = () => {
    const lines = cart.lines(catalog);
    cartView.querySelector("[data-cart-filled]").hidden = !lines.length;
    cartView.querySelector("[data-cart-empty]").hidden = !!lines.length;
    cartView.querySelector("[data-cart-rows]").innerHTML = lines.map((l, i) => `
      <tr>
        <td><a href="${esc(l.product.url)}">${esc(l.product.name)}</a></td>
        <td>${esc(l.size || "–")}</td>
        <td class="num">${lei(l.product.price)} lei</td>
        <td class="num"><input class="input" type="number" min="0" max="99" value="${l.qty}" data-line="${i}" style="width:72px;padding:6px" aria-label="Cantitate"></td>
        <td class="num pts">${lei(l.subtotal)} lei</td>
        <td><button class="btn btn-ghost btn-sm" type="button" data-remove="${i}" title="Elimină">✕</button></td>
      </tr>`).join("");
    cartView.querySelector("[data-cart-total]").textContent = lei(lines.reduce((s, l) => s + l.subtotal, 0));
  };
  const setQty = (index, qty) => {
    const lines = cart.lines(catalog);
    lines[index].qty = Math.max(0, Math.min(99, qty));
    cart.save(lines.filter((l) => l.qty > 0).map(({ slug, size, qty }) => ({ slug, size, qty })));
    render();
  };
  cartView.addEventListener("change", (e) => { if (e.target.dataset.line) setQty(+e.target.dataset.line, parseInt(e.target.value, 10) || 0); });
  cartView.addEventListener("click", (e) => { const b = e.target.closest("[data-remove]"); if (b) setQty(+b.dataset.remove, 0); });
  render();
}

// Pagina de finalizare a comenzii: sumarul
const checkout = document.querySelector("[data-checkout]");
let orderLines = [];
if (checkout) {
  const catalog = jsonData("shop-catalog") || {};
  orderLines = cart.lines(catalog);
  if (!orderLines.length) {
    checkout.hidden = true;
    document.querySelector("[data-cart-empty]").hidden = false;
  }
  checkout.querySelector("[data-checkout-summary]").innerHTML = orderLines.map((l) => `
    <div style="display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid var(--line)">
      <span>${l.qty} × ${esc(l.product.name)}${l.size ? ` (${esc(l.size)})` : ""}</span><b class="nowrap">${lei(l.subtotal)} lei</b>
    </div>`).join("");
  checkout.querySelector("[data-cart-total]").textContent = lei(orderLines.reduce((s, l) => s + l.subtotal, 0));
}

// Formulare trimise pe emailul clubului prin Web3Forms (contact și comenzi)
document.querySelectorAll("form[data-web3form]").forEach((form) => {
  const status = form.querySelector(".form-status");
  const show = (ok, html) => { status.className = `form-status ${ok ? "ok" : "err"}`; status.innerHTML = html; status.hidden = false; };
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const data = Object.fromEntries(new FormData(form));
    if (data.botcheck) return;
    const isOrder = form.dataset.web3form === "order";
    const body = isOrder ? {
      subject: `${form.dataset.subject} – ${data.name}`,
      from_name: `Magazin ${SITE.clubName || ""}`.trim(),
      Nume: data.name, Telefon: data.phone, Email: data.email || "–", "Observații": data.note || "–",
      Produse: orderLines.map((l) => `${l.qty} × ${l.product.name}${l.size ? ` (mărime ${l.size})` : ""} = ${lei(l.subtotal)} lei`).join("\n"),
      Total: `${lei(orderLines.reduce((s, l) => s + l.subtotal, 0))} lei (plata la ridicare)`,
    } : {
      subject: `${form.dataset.subject}: ${data.subject}`,
      from_name: data.name,
      Nume: data.name, Email: data.email, Telefon: data.phone || "–", Subiect: data.subject, Mesaj: data.message,
    };
    if (data.email) body.replyto = data.email;

    // Fără cheie Web3Forms configurată: deschidem aplicația de email a vizitatorului.
    if (!SITE.web3formsKey) {
      const text = Object.entries(body).filter(([k]) => !["subject", "from_name", "replyto"].includes(k))
        .map(([k, v]) => `${k}: ${v}`).join("\n");
      window.location.href = `mailto:${SITE.clubEmail}?subject=${encodeURIComponent(body.subject)}&body=${encodeURIComponent(text)}`;
      return;
    }
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const res = await fetch("https://api.web3forms.com/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ access_key: SITE.web3formsKey, botcheck: false, ...body }),
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok || json.success === false) throw new Error(json.message || res.status);
      form.reset();
      if (isOrder) {
        cart.save([]);
        show(true, `Mulțumim, ${esc(data.name)}! Comanda a fost trimisă. Vă sunăm la <b>${esc(data.phone)}</b> când produsele sunt pregătite de ridicare.`);
      } else {
        show(true, "Mulțumim! Mesajul a fost trimis, vă vom răspunde în curând.");
      }
    } catch (err) {
      show(false, `Mesajul nu a putut fi trimis. Încercați din nou sau scrieți-ne la <a href="mailto:${esc(SITE.clubEmail)}">${esc(SITE.clubEmail)}</a>.`);
    } finally {
      button.disabled = false;
    }
  });
});

// Căutare jucători și echipe (lista completă e în pagină)
const searchForm = document.querySelector("form[data-search]");
if (searchForm) {
  const index = jsonData("search-index") || { players: [], teams: [] };
  const box = document.querySelector("[data-search-results]");
  const norm = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const run = () => {
    const q = norm(searchForm.q.value.trim());
    const url = new URL(window.location);
    if (q) url.searchParams.set("q", searchForm.q.value.trim()); else url.searchParams.delete("q");
    history.replaceState(null, "", url);
    box.hidden = q.length < 2;
    if (q.length < 2) return;
    const players = index.players.filter((p) => norm(p.n).includes(q) || norm(p.t).includes(q)).slice(0, 50);
    const teams = index.teams.filter((t) => norm(t.n).includes(q)).slice(0, 20);
    box.querySelector('[data-count="players"]').textContent = players.length;
    box.querySelector('[data-count="teams"]').textContent = teams.length;
    box.querySelector('[data-list="players"]').innerHTML = players.map((p) => `
      <div style="display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px solid var(--line)">
        <a href="${esc(p.u)}">${esc(p.n)}</a><span class="small muted">${esc(p.t)}</span></div>`).join("") || '<p class="muted">Niciun rezultat.</p>';
    box.querySelector('[data-list="teams"]').innerHTML = teams.map((t) => `
      <a class="team-cell" style="padding:7px 0" href="${esc(t.u)}"><img src="${esc(t.l)}" alt="">${esc(t.n)}</a>`).join("") || '<p class="muted">Niciun rezultat.</p>';
  };
  searchForm.addEventListener("submit", (e) => { e.preventDefault(); run(); });
  searchForm.q.addEventListener("input", run);
  searchForm.q.value = new URLSearchParams(window.location.search).get("q") || "";
  run();
}

// ---------------------------------------------------------------------------
// Meniul complet (butonul „Meniu” din bara din stânga / de sus)
// ---------------------------------------------------------------------------
(() => {
  const panel = document.getElementById("menu-panel");
  if (!panel) return;
  const backdrop = document.querySelector(".menu-backdrop");
  const openers = document.querySelectorAll("[data-menu-open]");
  let lastFocus = null;
  const setOpen = (open) => {
    panel.hidden = backdrop.hidden = !open;
    openers.forEach((b) => b.setAttribute("aria-expanded", String(open)));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) { lastFocus = document.activeElement; panel.querySelector("a, button").focus(); }
    else if (lastFocus) lastFocus.focus();
  };
  openers.forEach((b) => b.addEventListener("click", () => setOpen(true)));
  document.querySelectorAll("[data-menu-close]").forEach((b) => b.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !panel.hidden) setOpen(false); });
  panel.addEventListener("click", (e) => { if (e.target.closest("a")) setOpen(false); });
})();

// ---------------------------------------------------------------------------
// Slideshow pe pagina principală
// ---------------------------------------------------------------------------
document.querySelectorAll("[data-slider]").forEach((slider) => {
  const slides = [...slider.querySelectorAll("[data-slide]")];
  const captions = [...slider.querySelectorAll("[data-caption]")];
  const dots = [...slider.querySelectorAll("[data-dot]")];
  if (slides.length < 2) return;
  const DELAY = 6500;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  slider.style.setProperty("--slide-ms", `${DELAY}ms`);
  let index = 0, timer = null, paused = false;

  const show = (next) => {
    index = (next + slides.length) % slides.length;
    slider.classList.add("is-changing");
    setTimeout(() => slider.classList.remove("is-changing"), 700);
    const toggle = (list) => list.forEach((el, i) => {
      const on = i === index;
      el.classList.toggle("is-active", on);
      el.setAttribute("aria-hidden", String(!on));
      el.querySelectorAll("a").forEach((a) => (on ? a.removeAttribute("tabindex") : a.setAttribute("tabindex", "-1")));
    });
    toggle(slides); toggle(captions);
    dots.forEach((d, i) => {
      d.classList.remove("is-active");
      d.setAttribute("aria-selected", String(i === index));
    });
    // repornește bara de progres a punctului activ
    void slider.offsetWidth;
    dots[index]?.classList.add("is-active");
    restart();
  };
  const restart = () => {
    clearTimeout(timer);
    if (!paused && !reduced) timer = setTimeout(() => show(index + 1), DELAY);
  };
  const pause = (on) => { paused = on; slider.classList.toggle("is-paused", on); restart(); };

  slider.querySelector("[data-next]")?.addEventListener("click", () => show(index + 1));
  slider.querySelector("[data-prev]")?.addEventListener("click", () => show(index - 1));
  dots.forEach((d) => d.addEventListener("click", () => show(+d.dataset.dot)));
  slider.addEventListener("mouseenter", () => pause(true));
  slider.addEventListener("mouseleave", () => pause(false));
  slider.addEventListener("focusin", () => pause(true));
  slider.addEventListener("focusout", () => pause(false));
  document.addEventListener("visibilitychange", () => pause(document.hidden));
  slider.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") show(index + 1);
    if (e.key === "ArrowLeft") show(index - 1);
  });
  // glisare pe telefon
  let startX = null;
  slider.addEventListener("touchstart", (e) => { startX = e.touches[0].clientX; }, { passive: true });
  slider.addEventListener("touchend", (e) => {
    if (startX === null) return;
    const dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) > 50) show(index + (dx < 0 ? 1 : -1));
    startX = null;
  });
  if (reduced) dots[0]?.classList.add("is-active");
  restart();
});
