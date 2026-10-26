"use strict";

/* ================= helpers ================= */

const ICONS = {
  dress: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"><path d="M9 3v3.5L7.5 10 4.5 20.5h15L16.5 10 15 6.5V3"/><path d="M9 6.5c1.8 1.3 4.2 1.3 6 0M7.5 10h9"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3.5 12a8.5 8.5 0 1 0 2.5-6"/><path d="M3 4v4h4"/><path d="M12 7.5V12l3 2"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
  image: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m3 18 5-5 4 4 3-3 6 6"/></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M3 6h6l2 2h10v11H3z"/></svg>',
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const icon = (name) => ICONS[name] || "";
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function hydrateIcons(root = document) {
  for (const el of $$("[data-icon]", root)) {
    if (!el.dataset.iconDone) {
      el.insertAdjacentHTML("afterbegin", icon(el.dataset.icon));
      el.dataset.iconDone = "1";
    }
  }
}

/** Call a Python function; throws an Error with a readable message on failure. */
async function api(name, ...args) {
  const res = await window.pywebview.api[name](...args);
  if (!res || !res.ok) throw new Error(res ? res.error : "No response from the app.");
  return res.data;
}

/** Run an async action and show any error as a toast. */
function guard(fn) {
  return async (...args) => {
    try {
      await fn(...args);
    } catch (e) {
      toast(e.message, true);
    }
  };
}

function toast(message, isError = false) {
  const el = document.createElement("div");
  el.className = "toast" + (isError ? " error" : "");
  el.textContent = message;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), isError ? 5000 : 2800);
}

/* ---------- dates ('YYYY-MM-DD' strings) ---------- */

function parseDate(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}
function isoDate(dt) {
  const p = (n) => String(n).padStart(2, "0");
  return `${dt.getFullYear()}-${p(dt.getMonth() + 1)}-${p(dt.getDate())}`;
}
function addDays(s, n) {
  const d = parseDate(s);
  d.setDate(d.getDate() + n);
  return isoDate(d);
}
function addMonths(s, n) {
  const d = parseDate(s);
  const day = d.getDate();
  d.setDate(1);
  d.setMonth(d.getMonth() + n);
  const lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  d.setDate(Math.min(day, lastDay));
  return isoDate(d);
}
function daysBetween(a, b) {
  return Math.round((parseDate(b) - parseDate(a)) / 86400000);
}
function fmtDate(s) {
  return s ? parseDate(s).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "";
}
function fmtShort(s) {
  return s ? parseDate(s).toLocaleDateString("en-GB", { day: "numeric", month: "short" }) : "";
}
function dueInfo(due) {
  const n = daysBetween(state.today, due);
  if (n < 0) return { text: `${plural(-n, "day")} overdue`, cls: "overdue-text" };
  if (n === 0) return { text: "Due today", cls: "soon-text" };
  if (n <= 2) return { text: `Due in ${plural(n, "day")}`, cls: "soon-text" };
  return { text: `Due in ${n} days`, cls: "" };
}

/* ---------- small renderers ---------- */

function photoHtml(url) {
  return `<div class="photo">${url ? `<img src="${url}" alt="">` : icon("dress")}</div>`;
}
function statusBadge(c) {
  if (c.status !== "rented") return '<span class="badge badge-available">Available</span>';
  return c.overdue ? '<span class="badge badge-overdue">Overdue</span>' : '<span class="badge badge-rented">Rented</span>';
}
function costumeMeta(c, withRegion) {
  return [c.inventory_no && `#${c.inventory_no}`, c.size && `Size ${c.size}`, withRegion && c.region]
    .filter(Boolean).map(esc).join(" · ");
}

/* ================= state ================= */

const state = {
  view: "costumes",
  regionId: null, // null = all costumes
  search: "",
  historySearch: "",
  regions: [],
  today: "",
  overdue: 0,
  detailId: null,
};

const main = () => $("#main");

/** Reload everything that may have changed: sidebar, current page, open detail panel. */
async function refresh() {
  const [summary, regions] = await Promise.all([api("summary"), api("list_regions")]);
  state.today = summary.today;
  state.overdue = summary.overdue_count;
  state.regions = regions;
  if (state.regionId !== null && !regions.some((r) => r.id === state.regionId)) state.regionId = null;
  renderSidebar();
  await renderView();
  if (state.detailId !== null) await renderDrawer();
}

function go(view, regionId = state.regionId) {
  const changed = view !== state.view || regionId !== state.regionId;
  state.view = view;
  state.regionId = regionId;
  if (changed) state.search = "";
  if (state.detailId !== null) closeDrawer();
  renderSidebar();
  guard(renderView)();
}

/* ================= sidebar ================= */

function renderSidebar() {
  for (const btn of $$(".nav-item")) {
    btn.classList.toggle("active", btn.dataset.view === state.view && !(state.view === "costumes" && state.regionId !== null));
  }
  const badge = $("#overdue-badge");
  badge.hidden = state.overdue === 0;
  badge.textContent = state.overdue;

  const total = state.regions.reduce((sum, r) => sum + r.costume_count, 0);
  const item = (id, name, count, photoUrl, iconName) => {
    const active = state.view === "costumes" && state.regionId === id;
    const thumb = photoUrl ? `<img src="${photoUrl}" alt="">` : icon(iconName);
    return `<button class="region-item ${active ? "active" : ""}" data-region="${id ?? ""}">
      <span class="region-thumb">${thumb}</span>
      <span class="region-text"><span class="region-name">${esc(name)}</span>
      <span class="region-count">${plural(count, "costume")}</span></span></button>`;
  };
  $("#regions").innerHTML =
    item(null, "All costumes", total, null, "dress") +
    state.regions.map((r) => item(r.id, r.name, r.costume_count, r.photo_url, "folder")).join("");
  for (const btn of $$(".region-item")) {
    btn.onclick = () => go("costumes", btn.dataset.region ? Number(btn.dataset.region) : null);
  }
}

/* ================= pages ================= */

function renderView() {
  if (state.view === "rentals") return renderRentals();
  if (state.view === "history") return renderHistory();
  return renderCostumes();
}

/* ---------- costumes ---------- */

async function renderCostumes() {
  const region = state.regions.find((r) => r.id === state.regionId);
  main().innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">${esc(region ? region.name : "All costumes")}</h1>
        <div class="page-subtitle" id="costume-count">&nbsp;</div>
      </div>
      <div class="page-actions">
        <label class="search">${icon("search")}<input id="costume-search" placeholder="Search costumes" value="${esc(state.search)}"></label>
        ${region ? `<button class="icon-btn" id="rename-region" title="Rename region">${icon("edit")}</button>
                    <button class="icon-btn" id="delete-region" title="Delete region">${icon("trash")}</button>` : ""}
        <button class="btn btn-primary" id="add-costume">${icon("plus")}Add costume</button>
      </div>
    </div>
    <div id="costume-grid"></div>`;

  let timer;
  $("#costume-search").oninput = (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { state.search = e.target.value; guard(renderGrid)(); }, 200);
  };
  $("#add-costume").onclick = () => costumeForm();
  if (region) {
    $("#rename-region").onclick = () => regionForm(region);
    $("#delete-region").onclick = () => deleteRegion(region);
  }
  await renderGrid();
}

let gridRequest = 0;
async function renderGrid() {
  const request = ++gridRequest;
  const costumes = await api("list_costumes", state.regionId, state.search);
  const grid = $("#costume-grid");
  if (!grid || request !== gridRequest) return; // a newer search already ran

  const available = costumes.filter((c) => c.status === "available").length;
  $("#costume-count").textContent = `${plural(costumes.length, "costume")} · ${available} available`;

  grid.className = "";
  if (!state.regions.length) {
    grid.innerHTML = `<div class="empty"><h3>Welcome!</h3>Costumes are grouped by region. Start by adding the first region.
      <div><button class="btn btn-primary" id="empty-add-region">${icon("plus")}Add region</button></div></div>`;
    $("#empty-add-region").onclick = () => regionForm();
    return;
  }
  if (!costumes.length) {
    grid.innerHTML = state.search
      ? `<div class="empty"><h3>No matches</h3>No costume matches “${esc(state.search)}”.</div>`
      : `<div class="empty"><h3>No costumes here yet</h3>Add the first costume with its photo.
          <div><button class="btn btn-primary" id="empty-add-costume">${icon("plus")}Add costume</button></div></div>`;
    $("#empty-add-costume")?.addEventListener("click", () => costumeForm());
    return;
  }

  grid.className = "grid";
  grid.innerHTML = costumes.map((c) => `
    <button class="card ${c.id === state.detailId ? "selected" : ""}" data-id="${c.id}">
      <div class="card-photo">${photoHtml(c.photo_url)}${statusBadge(c)}</div>
      <div class="card-body">
        <div class="card-name">${esc(c.name)}</div>
        <div class="card-meta">${costumeMeta(c, state.regionId === null) || "&nbsp;"}</div>
        ${c.status === "rented" ? `<div class="card-rented ${c.overdue ? "overdue" : ""}">${esc(c.borrower)} · until ${fmtShort(c.due_on)}</div>` : ""}
      </div>
    </button>`).join("");
  for (const card of $$(".card", grid)) card.onclick = () => openCostume(Number(card.dataset.id));
}

/* ---------- rentals ---------- */

async function renderRentals() {
  const rentals = await api("list_active_rentals");
  if (state.view !== "rentals") return;
  const overdue = rentals.filter((r) => r.overdue);
  const onTime = rentals.filter((r) => !r.overdue);

  const head = `<div class="row row-head rental-row"><span></span><span>Costume</span><span>Borrower</span><span>Borrowed</span><span>Return by</span><span></span></div>`;
  const row = (r) => {
    const due = dueInfo(r.due_on);
    return `<div class="row rental-row" data-costume="${r.costume_id}">
      <div class="row-thumb">${photoHtml(r.photo_url)}</div>
      <div><div class="row-title">${esc(r.costume)}</div><div class="row-sub">${costumeMeta(r, true)}</div></div>
      <div>${esc(r.borrower)}${r.notes ? `<div class="row-sub">${esc(r.notes)}</div>` : ""}</div>
      <div>${fmtDate(r.borrowed_on)}</div>
      <div>${fmtDate(r.due_on)}<div class="row-sub ${due.cls}">${due.text}</div></div>
      <div><button class="btn btn-outline btn-sm" data-return="${r.id}">Return</button></div>
    </div>`;
  };
  const section = (title, items, cls = "") =>
    items.length ? `<div class="section-title ${cls}">${title}</div><div class="list">${head}${items.map(row).join("")}</div>` : "";

  main().innerHTML = `
    <div class="page-header"><div>
      <h1 class="page-title">Rentals</h1>
      <div class="page-subtitle">${plural(rentals.length, "costume")} out${overdue.length ? ` · <span class="overdue-text">${overdue.length} overdue</span>` : ""}</div>
    </div></div>
    ${rentals.length
      ? section("Overdue", overdue, "danger") + section(overdue.length ? "Out on time" : "Out", onTime)
      : `<div class="empty"><h3>Nothing is rented out</h3>Rent out a costume from the Costumes page.</div>`}`;

  for (const el of $$(".row[data-costume]")) el.onclick = () => openCostume(Number(el.dataset.costume));
  for (const btn of $$("[data-return]")) {
    btn.onclick = (e) => {
      e.stopPropagation();
      returnForm(rentals.find((r) => r.id === Number(btn.dataset.return)));
    };
  }
}

/* ---------- history ---------- */

async function renderHistory() {
  main().innerHTML = `
    <div class="page-header">
      <div><h1 class="page-title">History</h1><div class="page-subtitle" id="history-count">&nbsp;</div></div>
      <div class="page-actions">
        <label class="search">${icon("search")}<input id="history-search" placeholder="Search borrower or costume" value="${esc(state.historySearch)}"></label>
      </div>
    </div>
    <div id="history-list"></div>`;
  let timer;
  $("#history-search").oninput = (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { state.historySearch = e.target.value; guard(renderHistoryList)(); }, 200);
  };
  await renderHistoryList();
}

let historyRequest = 0;
async function renderHistoryList() {
  const request = ++historyRequest;
  const items = await api("list_history", state.historySearch);
  const list = $("#history-list");
  if (!list || request !== historyRequest) return;
  $("#history-count").textContent = plural(items.length, "returned rental");

  if (!items.length) {
    list.innerHTML = state.historySearch
      ? `<div class="empty"><h3>No matches</h3>Nothing matches “${esc(state.historySearch)}”.</div>`
      : `<div class="empty"><h3>No history yet</h3>Returned costumes will show up here.</div>`;
    return;
  }
  list.innerHTML = `<div class="list">
    <div class="row row-head history-row"><span></span><span>Costume</span><span>Borrower</span><span>Borrowed</span><span>Returned</span><span>Result</span></div>
    ${items.map((h) => {
      const late = daysBetween(h.due_on, h.returned_on);
      return `<div class="row history-row" ${h.costume_deleted ? "" : `data-costume="${h.costume_id}"`}>
        <div class="row-thumb">${photoHtml(h.photo_url)}</div>
        <div><div class="row-title">${esc(h.costume)}</div><div class="row-sub">${h.costume_deleted ? "Deleted costume" : costumeMeta(h, true)}</div></div>
        <div>${esc(h.borrower)}</div>
        <div>${fmtDate(h.borrowed_on)}</div>
        <div>${fmtDate(h.returned_on)}<div class="row-sub">${plural(daysBetween(h.borrowed_on, h.returned_on), "day")}</div></div>
        <div>${late > 0 ? `<span class="badge badge-overdue">${plural(late, "day")} late</span>` : '<span class="badge badge-available">On time</span>'}</div>
      </div>`;
    }).join("")}</div>`;
  for (const el of $$(".row[data-costume]", list)) el.onclick = () => openCostume(Number(el.dataset.costume));
}

/* ================= costume detail panel ================= */

async function openCostume(id) {
  state.detailId = id;
  await guard(renderDrawer)();
  for (const card of $$(".card")) card.classList.toggle("selected", Number(card.dataset.id) === id);
}

function closeDrawer() {
  state.detailId = null;
  $("#drawer").classList.remove("open");
  $("#drawer").setAttribute("aria-hidden", "true");
  $("#drawer-scrim").hidden = true;
  for (const card of $$(".card.selected")) card.classList.remove("selected");
}

async function renderDrawer() {
  let c;
  try {
    c = await api("get_costume", state.detailId);
  } catch (e) {
    closeDrawer();
    throw e;
  }
  const drawer = $("#drawer");
  const rented = c.status === "rented";
  const due = rented ? dueInfo(c.due_on) : null;

  drawer.innerHTML = `
    <div class="drawer-top">
      <span class="row-sub">${esc(c.region || "")}</span>
      <button class="icon-btn" id="drawer-close" title="Close">${icon("close")}</button>
    </div>
    <div class="drawer-photo">${photoHtml(c.photo_url)}</div>
    <div class="drawer-body">
      <h2 class="drawer-title">${esc(c.name)}</h2>
      <div class="drawer-meta">${costumeMeta(c, false)}</div>
      ${c.description ? `<div class="drawer-desc">${esc(c.description)}</div>` : ""}

      <div class="status-box">
        <div class="status-line"><span>Status</span>${statusBadge(c)}</div>
        ${rented ? `
          <div class="status-grid">
            <div class="full"><div class="label">Rented by</div><div class="value">${esc(c.borrower)}</div></div>
            <div><div class="label">Borrowed on</div><div class="value">${fmtDate(c.borrowed_on)}</div></div>
            <div><div class="label">Return by</div><div class="value">${fmtDate(c.due_on)}</div><div class="row-sub ${due.cls}">${due.text}</div></div>
            ${c.notes ? `<div class="full"><div class="label">Notes</div><div class="value">${esc(c.notes)}</div></div>` : ""}
          </div>`
        : `<div class="row-sub" style="margin-top:6px">Ready to rent out.</div>`}
      </div>

      ${rented
        ? `<button class="btn btn-outline btn-block" id="drawer-return">Take back (return)</button>`
        : `<button class="btn btn-primary btn-block" id="drawer-rent">Rent out this costume</button>`}
      <div class="drawer-actions">
        <button class="btn btn-ghost" id="drawer-edit">${icon("edit")}Edit</button>
        <button class="btn btn-danger" id="drawer-delete">${icon("trash")}Delete</button>
      </div>

      <div class="mini-history">
        <div class="section-title">Rental history</div>
        ${c.history.length ? c.history.map((h) => `
          <div class="mini-history-item">
            <span>${esc(h.borrower)}</span>
            <span class="row-sub">${fmtShort(h.borrowed_on)} – ${fmtDate(h.returned_on)}${h.late ? ' · <span class="overdue-text">late</span>' : ""}</span>
          </div>`).join("") : '<div class="row-sub">Not rented out yet.</div>'}
      </div>
    </div>`;

  $("#drawer-close").onclick = closeDrawer;
  $("#drawer-edit").onclick = () => costumeForm(c);
  $("#drawer-delete").onclick = () => deleteCostume(c);
  $("#drawer-rent")?.addEventListener("click", () => rentForm(c));
  $("#drawer-return")?.addEventListener("click", () =>
    returnForm({ id: c.rental_id, costume: c.name, inventory_no: c.inventory_no, borrower: c.borrower, borrowed_on: c.borrowed_on, due_on: c.due_on, photo_url: c.photo_url }));

  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  $("#drawer-scrim").hidden = false;
}

/* ================= modals & forms ================= */

let onModalClose = null;

/** Open a form dialog. Returns the <form>; its submit button is labelled `submitLabel`. */
function openModal({ title, body, submitLabel, danger = false, wide = false, onClose = null }) {
  const modal = $("#modal");
  modal.className = "modal" + (wide ? " wide" : "");
  modal.innerHTML = `
    <form novalidate>
      <div class="modal-header"><h2 class="modal-title">${esc(title)}</h2>
        <button type="button" class="icon-btn" data-close title="Close">${icon("close")}</button></div>
      <div class="modal-body"><div class="form-error" hidden></div>${body}</div>
      <div class="modal-footer">
        <button type="button" class="btn btn-ghost" data-close>Cancel</button>
        <button type="submit" class="btn ${danger ? "btn-danger" : "btn-primary"}">${esc(submitLabel)}</button>
      </div>
    </form>`;
  onModalClose = onClose;
  $("#modal-scrim").hidden = false;
  for (const btn of $$("[data-close]", modal)) btn.onclick = closeModal;
  const form = $("form", modal);
  setTimeout(() => $("input:not([type=hidden]), textarea, select", form)?.focus(), 0);
  return form;
}

function closeModal() {
  if ($("#modal-scrim").hidden) return;
  $("#modal-scrim").hidden = true;
  $("#modal").innerHTML = "";
  const cb = onModalClose;
  onModalClose = null;
  cb?.();
}

/** Submit handler: disables the button while saving and shows errors inside the form. */
function onSubmit(form, action) {
  form.onsubmit = async (e) => {
    e.preventDefault();
    const button = $("button[type=submit]", form);
    const error = $(".form-error", form);
    button.disabled = true;
    error.hidden = true;
    try {
      await action();
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
    }
  };
}

const field = (form, name) => form.elements[name].value;

/* ---------- regions ---------- */

function regionForm(region = null) {
  const form = openModal({
    title: region ? "Rename region" : "Add region",
    submitLabel: region ? "Save" : "Add region",
    body: `<div class="field"><label for="f-name">Region name</label>
      <input class="input" id="f-name" name="name" value="${esc(region?.name)}" placeholder="e.g. Opoczyński" autocomplete="off"></div>`,
  });
  onSubmit(form, async () => {
    if (region) {
      await api("rename_region", region.id, field(form, "name"));
    } else {
      state.regionId = await api("add_region", field(form, "name"));
      state.view = "costumes";
      state.search = "";
    }
    closeModal();
    toast(region ? "Region renamed" : "Region added");
    await refresh();
  });
}

function deleteRegion(region) {
  const form = openModal({
    title: "Delete region?",
    submitLabel: "Delete region",
    danger: true,
    body: `<p>Delete <b>${esc(region.name)}</b>? This only works when the region has no costumes.</p>`,
  });
  onSubmit(form, async () => {
    await api("delete_region", region.id);
    closeModal();
    toast("Region deleted");
    state.regionId = null;
    await refresh();
  });
}

/* ---------- costumes ---------- */

function costumeForm(costume = null) {
  if (!state.regions.length) {
    toast("Add a region first", true);
    regionForm();
    return;
  }
  const original = costume?.photo ?? null;
  let photo = original;
  let photoUrl = costume?.photo_url ?? null;
  const regionId = costume?.region_id ?? state.regionId ?? (state.regions.length === 1 ? state.regions[0].id : null);
  const discardPicked = () => { if (photo && photo !== original) api("discard_photo", photo).catch(() => {}); };

  const form = openModal({
    title: costume ? "Edit costume" : "Add costume",
    submitLabel: costume ? "Save changes" : "Add costume",
    wide: true,
    onClose: discardPicked,
    body: `
      <div class="costume-form">
        <div>
          <button type="button" class="photo-picker" id="photo-picker"></button>
          <div class="photo-picker-actions">
            <button type="button" class="btn btn-ghost btn-sm" id="photo-change">Choose photo</button>
            <button type="button" class="btn btn-danger btn-sm" id="photo-remove">Remove</button>
          </div>
        </div>
        <div>
          <div class="field"><label for="f-region">Region</label>
            <select class="select" id="f-region" name="region">
              <option value="">Choose a region…</option>
              ${state.regions.map((r) => `<option value="${r.id}" ${r.id === regionId ? "selected" : ""}>${esc(r.name)}</option>`).join("")}
            </select></div>
          <div class="field"><label for="f-name">Name</label>
            <input class="input" id="f-name" name="name" value="${esc(costume?.name)}" placeholder="e.g. Women's costume" autocomplete="off"></div>
          <div class="field-row">
            <div class="field"><label for="f-inv">Inventory number <span class="hint">(optional)</span></label>
              <input class="input" id="f-inv" name="inventory_no" value="${esc(costume?.inventory_no)}" placeholder="e.g. OP-12" autocomplete="off"></div>
            <div class="field"><label for="f-size">Size <span class="hint">(optional)</span></label>
              <input class="input" id="f-size" name="size" value="${esc(costume?.size)}" placeholder="e.g. M" autocomplete="off"></div>
          </div>
          <div class="field"><label for="f-desc">Description <span class="hint">(optional)</span></label>
            <textarea class="textarea" id="f-desc" name="description" placeholder="Parts, condition, notes…">${esc(costume?.description)}</textarea></div>
        </div>
      </div>`,
  });
  // Focus the name rather than the region select
  setTimeout(() => form.elements.name.focus(), 0);

  const showPhoto = () => {
    $("#photo-picker").innerHTML = photoUrl
      ? photoHtml(photoUrl)
      : `<div class="photo">${icon("image")}<span>Click to add a photo</span></div>`;
    $("#photo-remove").hidden = !photo;
    $("#photo-change").textContent = photo ? "Change photo" : "Choose photo";
  };
  const pick = guard(async () => {
    const picked = await api("pick_photo");
    if (!picked) return;
    discardPicked();
    photo = picked.photo;
    photoUrl = picked.photo_url;
    showPhoto();
  });
  $("#photo-picker").onclick = pick;
  $("#photo-change").onclick = pick;
  $("#photo-remove").onclick = () => {
    discardPicked();
    photo = null;
    photoUrl = null;
    showPhoto();
  };
  showPhoto();

  onSubmit(form, async () => {
    const data = {
      region_id: field(form, "region") ? Number(field(form, "region")) : null,
      name: field(form, "name"),
      inventory_no: field(form, "inventory_no"),
      size: field(form, "size"),
      description: field(form, "description"),
      photo,
    };
    if (costume) {
      await api("update_costume", costume.id, data);
    } else {
      state.detailId = await api("add_costume", data);
    }
    onModalClose = null; // photo is saved now, don't discard it
    closeModal();
    toast(costume ? "Costume saved" : "Costume added");
    await refresh();
  });
}

function deleteCostume(c) {
  const form = openModal({
    title: "Delete costume?",
    submitLabel: "Delete costume",
    danger: true,
    body: `<p>Delete <b>${esc(c.name)}</b>${c.inventory_no ? ` (#${esc(c.inventory_no)})` : ""}? It disappears from the costume list, but its past rentals stay in History.</p>`,
  });
  onSubmit(form, async () => {
    await api("delete_costume", c.id);
    closeModal();
    closeDrawer();
    toast("Costume deleted");
    await refresh();
  });
}

/* ---------- renting & returning ---------- */

async function rentForm(c) {
  const names = await api("borrower_names").catch(() => []);
  const form = openModal({
    title: "Rent out costume",
    submitLabel: "Confirm rental",
    body: `
      <div class="rent-summary">
        <div class="row-thumb">${photoHtml(c.photo_url)}</div>
        <div><div class="row-title">${esc(c.name)}</div><div class="row-sub">${costumeMeta(c, true)}</div></div>
      </div>
      <div class="field"><label for="f-borrower">Borrower's name</label>
        <input class="input" id="f-borrower" name="borrower" list="borrower-names" placeholder="e.g. Ania Kowalska" autocomplete="off">
        <datalist id="borrower-names">${names.map((n) => `<option value="${esc(n)}">`).join("")}</datalist></div>
      <div class="field-row">
        <div class="field"><label for="f-from">Borrowed on</label>
          <input class="input" type="date" id="f-from" name="borrowed_on" value="${state.today}"></div>
        <div class="field"><label for="f-due">Return by</label>
          <input class="input" type="date" id="f-due" name="due_on" value="${addDays(state.today, 7)}"></div>
      </div>
      <div class="chips">
        <button type="button" class="chip" data-days="7">1 week</button>
        <button type="button" class="chip" data-days="14">2 weeks</button>
        <button type="button" class="chip" data-months="1">1 month</button>
      </div>
      <div class="field"><label for="f-notes">Notes <span class="hint">(optional)</span></label>
        <textarea class="textarea" id="f-notes" name="notes" placeholder="e.g. for the Christmas show, missing belt"></textarea></div>`,
  });
  for (const chip of $$(".chip", form)) {
    chip.onclick = () => {
      const from = field(form, "borrowed_on") || state.today;
      form.elements.due_on.value = chip.dataset.days ? addDays(from, Number(chip.dataset.days)) : addMonths(from, Number(chip.dataset.months));
    };
  }
  onSubmit(form, async () => {
    await api("rent", c.id, {
      borrower: field(form, "borrower"),
      borrowed_on: field(form, "borrowed_on"),
      due_on: field(form, "due_on"),
      notes: field(form, "notes"),
    });
    closeModal();
    toast(`${c.name} rented to ${field(form, "borrower").trim()}`);
    await refresh();
  });
}

function returnForm(r) {
  const form = openModal({
    title: "Take back costume",
    submitLabel: "Confirm return",
    body: `
      <div class="rent-summary">
        <div class="row-thumb">${photoHtml(r.photo_url)}</div>
        <div><div class="row-title">${esc(r.costume)}${r.inventory_no ? ` <span class="row-sub">#${esc(r.inventory_no)}</span>` : ""}</div>
          <div class="row-sub">Rented by <b>${esc(r.borrower)}</b> since ${fmtDate(r.borrowed_on)} · return by ${fmtDate(r.due_on)}</div></div>
      </div>
      <div class="field"><label for="f-ret">Returned on</label>
        <input class="input" type="date" id="f-ret" name="returned_on" value="${state.today}"></div>`,
  });
  onSubmit(form, async () => {
    await api("return_rental", r.id, field(form, "returned_on"));
    closeModal();
    toast(`${r.costume} returned`);
    await refresh();
  });
}

/* ================= start ================= */

let started = false;
async function init() {
  if (started) return;
  started = true;
  hydrateIcons();
  for (const btn of $$(".nav-item")) btn.onclick = () => go(btn.dataset.view, null);
  $("#add-region").onclick = () => regionForm();
  $("#drawer-scrim").onclick = closeDrawer;
  $("#modal-scrim").addEventListener("mousedown", (e) => { if (e.target.id === "modal-scrim") closeModal(); });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#modal-scrim").hidden) closeModal();
    else if (state.detailId !== null) closeDrawer();
  });
  await guard(refresh)();
}

window.addEventListener("pywebviewready", init);
if (window.pywebview?.api?.summary) init();
