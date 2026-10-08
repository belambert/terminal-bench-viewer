// client-side filtering and sorting for the task table
const $ = (id) => document.getElementById(id);
const tbody = document.querySelector("#tasks tbody");
const rows = [...tbody.rows];
const rank = { easy: 0, medium: 1, hard: 2 };
const params = new URLSearchParams(location.search);

for (const id of ["q", "difficulty", "category"]) {
  if (params.has(id)) $(id).value = params.get(id);
  $(id).addEventListener("input", filter);
}

function filter() {
  const q = $("q").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const d = $("difficulty").value, c = $("category").value;
  let n = 0;
  for (const r of rows) {
    const show =
      (!d || r.dataset.difficulty === d) &&
      (!c || r.dataset.category === c) &&
      q.every((w) => r.dataset.text.includes(w));
    r.hidden = !show;
    n += show;
  }
  $("count").textContent = `${n} of ${rows.length}`;

  // keep filters in the url so views are shareable
  const p = new URLSearchParams();
  if ($("q").value) p.set("q", $("q").value);
  if (d) p.set("difficulty", d);
  if (c) p.set("category", c);
  history.replaceState(null, "", p.size ? `?${p}` : location.pathname);
}

let sortKey = null, asc = true;
for (const th of document.querySelectorAll("th[data-sort]")) {
  th.addEventListener("click", () => {
    const k = th.dataset.sort;
    asc = sortKey === k ? !asc : true;
    sortKey = k;
    const val = (r) =>
      k === "difficulty" ? rank[r.dataset.difficulty] ?? 9
      : k === "expert" ? parseFloat(r.dataset.expert) || Infinity
      : r.dataset[k];
    rows.sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * (asc ? 1 : -1));
    tbody.append(...rows);
    document.querySelectorAll("th").forEach((h) => h.removeAttribute("aria-sort"));
    th.setAttribute("aria-sort", asc ? "ascending" : "descending");
  });
}

filter();
