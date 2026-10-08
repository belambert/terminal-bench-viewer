// filtering, sorting, and hover tooltips for the results heatmap
const $ = (id) => document.getElementById(id);
const table = $("heat");
const tbody = table.tBodies[0];
const rows = [...tbody.rows];
const heads = [...table.querySelectorAll("th.sub")];
const tip = $("tip");

function filter() {
  const q = $("q").value.trim().toLowerCase();
  const c = $("category").value;
  for (const r of rows)
    r.hidden = (c && r.dataset.category !== c) || (q && !r.dataset.name.includes(q));
}

function sort() {
  const k = $("sort").value;
  const solve = (r) => parseFloat(r.dataset.solve);
  const byName = (a, b) => a.dataset.name.localeCompare(b.dataset.name);
  rows.sort(
    k === "name" ? byName
    : (a, b) => (k === "hard" ? 1 : -1) * (solve(a) - solve(b)) || byName(a, b)
  );
  tbody.append(...rows);
}

$("q").addEventListener("input", filter);
$("category").addEventListener("input", filter);
$("sort").addEventListener("input", sort);
$("counts").addEventListener("change", (e) => table.classList.toggle("counts", e.target.checked));

// tooltip plus row/column highlight on hover
let col = null;
table.addEventListener("mouseover", (e) => {
  const td = e.target.closest("td.c");
  if (col !== null) heads[col].classList.remove("hot");
  if (!td) { tip.hidden = true; col = null; return; }
  col = +td.dataset.col;
  heads[col].classList.add("hot");
  const task = td.parentElement.dataset.name;
  const result = td.textContent ? `${td.textContent} trials passed` : "not run";
  const hack = HACKS[col] ? `<br>⚑ ${HACKS[col].toFixed(1)}% of this submission's trials were judged reward hacks` : "";
  tip.innerHTML = `<b></b><br><span></span><br>${result}${hack}`;
  tip.querySelector("b").textContent = task;
  tip.querySelector("span").textContent = SUBS[col];
  tip.hidden = false;
});
table.addEventListener("mousemove", (e) => {
  if (tip.hidden) return;
  // flip to the left of the cursor near the right edge
  const x = e.clientX + 14 + tip.offsetWidth > innerWidth ? e.clientX - 14 - tip.offsetWidth : e.clientX + 14;
  tip.style.transform = `translate(${x}px, ${e.clientY + 14}px)`;
});
table.addEventListener("mouseleave", () => {
  tip.hidden = true;
  if (col !== null) heads[col].classList.remove("hot");
  col = null;
});
