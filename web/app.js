const I18N = {
  zh: {
    searchPh: "要找什么？像问搜索引擎一样说",
    search: "搜索",
    local: "仅本地",
    add: "添加",
    settings: "设置",
    empty: "说你要干什么。短标签先收窄，再用长描述筛一遍。",
    editTitle: "链接",
    fTitle: "标题",
    fTags: "标签",
    fDesc: "描述",
    cancel: "取消",
    save: "保存",
    setHint: "可加多层接口。当前层先用，失败再试下一层。",
    active: "当前层",
    thinking: "思考过程",
    none: "没有结果。换个说法，或把站点加进收藏。",
    fail: "模型没跑起来（多半是欠费或 key）。设计上仍走两层 AI，不是改成纯本地。",
    keySet: "已保存密钥",
    keyEmpty: "还没有密钥，搜索会走本地",
    searching: "正在搜…",
  },
  en: {
    searchPh: "What do you need?",
    search: "Search",
    local: "Local only",
    add: "Add",
    settings: "Settings",
    empty: "Say what you need. Short tags first, long descriptions second.",
    editTitle: "Link",
    fTitle: "Title",
    fTags: "Tags",
    fDesc: "Notes",
    cancel: "Cancel",
    save: "Save",
    setHint: "Multiple OpenAI-compatible layers. Active first, then fallback.",
    active: "Active",
    thinking: "Thinking traces",
    none: "Nothing found. Try another query, or add the site.",
    fail: "Model call failed (billing or key). The product is still two-layer AI.",
    keySet: "Key saved",
    keyEmpty: "No API key; search is local",
    searching: "Searching…",
  },
};

const state = { locale: localStorage.getItem("locale") || "zh", items: [] };

function t(key) {
  return (I18N[state.locale] || I18N.zh)[key] || key;
}

function applyI18n() {
  document.documentElement.lang = state.locale;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.getElementById("btn-lang").textContent = state.locale === "zh" ? "EN" : "中文";
}

function memorial() {
  const d = new Date();
  const key = `${d.getMonth() + 1}-${d.getDate()}`;
  document.documentElement.classList.toggle(
    "zh-memorial",
    ["4-4", "5-12", "9-3", "12-13", "12-17", "9-18", "7-7"].includes(key),
  );
}

function setHome(on) {
  document.body.classList.toggle("home", on);
  document.getElementById("empty").hidden = !on;
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg || "";
}

function render(items, msg) {
  const root = document.getElementById("results");
  root.innerHTML = "";
  setStatus(msg || "");
  setHome(false);
  if (!items.length) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = t("none");
    root.appendChild(p);
    return;
  }
  for (const item of items) {
    const div = document.createElement("article");
    div.className = "hit";
    const url = document.createElement("div");
    url.className = "url";
    url.textContent = item.url;
    const a = document.createElement("a");
    a.className = "title";
    a.href = item.url;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.textContent = item.title;
    const ed = document.createElement("button");
    ed.className = "edit";
    ed.type = "button";
    ed.textContent = "编辑";
    ed.addEventListener("click", () => openEdit(item));
    const desc = document.createElement("div");
    desc.className = "desc";
    desc.textContent = item.desc || "";
    const tags = document.createElement("div");
    tags.className = "tags";
    for (const tag of item.tags || []) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = tag;
      b.addEventListener("click", () => runSearch(tag, true));
      tags.appendChild(b);
    }
    div.append(url, a, ed, desc, tags);
    root.appendChild(div);
  }
}

async function runSearch(query, local) {
  query = (query || "").trim();
  if (!query) {
    setHome(true);
    document.getElementById("results").innerHTML = "";
    setStatus("");
    return;
  }
  document.getElementById("q").value = query;
  setStatus(t("searching"));
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, local: !!local }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok && !local) {
    setHome(false);
    setStatus(typeof data.detail === "string" ? data.detail : t("fail"));
    document.getElementById("results").innerHTML = "";
    return;
  }
  state.items = data.items || [];
  render(state.items, data.msg || "");
}

document.getElementById("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  runSearch(document.getElementById("q").value, false);
});
document.getElementById("btn-local").onclick = () => {
  runSearch(document.getElementById("q").value, true);
};
document.getElementById("btn-home").onclick = () => {
  document.getElementById("q").value = "";
  runSearch("", true);
};
document.getElementById("btn-lang").onclick = () => {
  state.locale = state.locale === "zh" ? "en" : "zh";
  localStorage.setItem("locale", state.locale);
  applyI18n();
};

const editDlg = document.getElementById("edit-dlg");
const editForm = document.getElementById("edit-form");
let editingId = null;

function openEdit(item) {
  editingId = item ? item.id : null;
  editForm.title.value = item ? item.title : "";
  editForm.url.value = item ? item.url : "";
  editForm.tags.value = item ? item.tags.join("|") : "";
  editForm.desc.value = item ? item.desc : "";
  editDlg.showModal();
}

document.getElementById("btn-add").onclick = () => openEdit(null);
editForm.addEventListener("submit", async (e) => {
  if (e.submitter && e.submitter.value === "cancel") return;
  e.preventDefault();
  const body = {
    title: editForm.title.value,
    url: editForm.url.value,
    tags: editForm.tags.value,
    desc: editForm.desc.value,
  };
  const url = editingId ? `/api/links/${editingId}` : "/api/links";
  const method = editingId ? "PUT" : "POST";
  await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  editDlg.close();
  const q = document.getElementById("q").value.trim();
  if (q) runSearch(q, true);
});

const setDlg = document.getElementById("set-dlg");
const setForm = document.getElementById("set-form");
function fillProviders(cfg) {
  const sel = document.getElementById("cfg-active");
  sel.innerHTML = "";
  for (const p of cfg.providers || []) {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = `${p.name} · ${p.model}`;
    opt.selected = p.name === cfg.active;
    sel.appendChild(opt);
  }
  const current = (cfg.providers || []).find((p) => p.name === cfg.active) || cfg.providers?.[0];
  setForm.name.value = current?.name || "";
  setForm.base_url.value = current?.base_url || cfg.base_url || "";
  setForm.model.value = current?.model || cfg.model || "";
  setForm.thinking.checked = !!(current?.thinking ?? cfg.thinking);
  setForm.api_key.value = "";
  setForm.api_key.placeholder = current?.api_key_set ? current.api_key_masked : "";
  document.getElementById("key-state").textContent = current?.api_key_set ? t("keySet") : t("keyEmpty");
}

document.getElementById("btn-settings").onclick = async () => {
  const cfg = await (await fetch("/api/config")).json();
  fillProviders(cfg);
  setDlg.showModal();
};
document.getElementById("cfg-active").addEventListener("change", async (e) => {
  await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ active: e.target.value }),
  });
  fillProviders(await (await fetch("/api/config")).json());
});
setForm.addEventListener("submit", async (e) => {
  if (e.submitter && e.submitter.value === "cancel") return;
  e.preventDefault();
  const body = {
    name: setForm.name.value.trim() || "default",
    base_url: setForm.base_url.value,
    model: setForm.model.value,
    thinking: setForm.thinking.checked,
  };
  if (setForm.api_key.value.trim()) body.api_key = setForm.api_key.value.trim();
  await fetch("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  setDlg.close();
});

memorial();
applyI18n();
setHome(true);
