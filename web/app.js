const I18N = {
  zh: {
    subtitle: "原站 stslinks.pages.dev · 分类筛选 + 小鲸鱼",
    add: "添加",
    settings: "设置",
    clickCats: "点击分类以显示对应的内容：",
    logic: "多选逻辑：",
    and: "并且",
    or: "或者",
    showAll: "显示所有",
    hideAll: "隐藏所有",
    searchPh: "搜索标题 / 网址，或用小鲸鱼描述需求",
    local: "本地搜",
    ai: "小鲸鱼搜",
    editTitle: "链接",
    fTitle: "标题",
    fTags: "标签（| 或逗号分隔）",
    fDesc: "描述",
    cancel: "取消",
    save: "保存",
    setHint: "任意 OpenAI 兼容接口。换模型只改 base_url、key、model。",
    thinking: "思考过程（DeepSeek 等）",
    none: "没有符合条件的链接。点「显示所有」或换分类。",
    whale: "小鲸鱼：",
    keySet: "已保存密钥",
    keyEmpty: "还没有密钥",
  },
  en: {
    subtitle: "from stslinks.pages.dev · tags + whale search",
    add: "Add",
    settings: "Settings",
    clickCats: "Click a category:",
    logic: "Combine:",
    and: "AND",
    or: "OR",
    showAll: "Show all",
    hideAll: "Hide all",
    searchPh: "Search title/url, or ask the whale",
    local: "Local",
    ai: "Whale",
    editTitle: "Link",
    fTitle: "Title",
    fTags: "Tags (| or comma)",
    fDesc: "Notes",
    cancel: "Cancel",
    save: "Save",
    setHint: "Any OpenAI-compatible API. Switch provider via base_url + key + model.",
    thinking: "Thinking traces (DeepSeek etc.)",
    none: "No links. Try Show all or another tag.",
    whale: "Whale: ",
    keySet: "Key saved",
    keyEmpty: "No API key yet",
  },
};

const state = {
  locale: localStorage.getItem("locale") || "zh",
  items: [],
  tags: [],
  selected: new Set(),
  mode: "and",
  query: "",
  aiItems: null,
};

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
  const days = ["4-4", "5-12", "9-3", "12-13", "12-17", "9-18", "7-7"];
  document.documentElement.classList.toggle("zh-memorial", days.includes(key));
}

async function load() {
  const res = await fetch("/api/links");
  const data = await res.json();
  state.items = data.items;
  state.tags = data.tags;
  renderChips();
  renderLinks();
}

function renderChips() {
  const box = document.getElementById("chips");
  box.innerHTML = "";
  for (const tag of state.tags) {
    const wrap = document.createElement("div");
    wrap.className = "chip";
    const id = "tag-" + encodeURIComponent(tag);
    wrap.innerHTML = `<input type="checkbox" id="${id}"><label for="${id}"></label>`;
    wrap.querySelector("label").textContent = tag;
    wrap.querySelector("input").checked = state.selected.has(tag);
    wrap.querySelector("input").addEventListener("change", (e) => {
      if (e.target.checked) state.selected.add(tag);
      else state.selected.delete(tag);
      state.aiItems = null;
      renderLinks();
    });
    box.appendChild(wrap);
  }
}

function matchLink(item) {
  const q = state.query.trim().toLowerCase();
  if (q) {
    const blob = `${item.title} ${item.url} ${item.desc} ${item.tags.join(" ")}`.toLowerCase();
    if (!blob.includes(q)) return false;
  }
  const selected = [...state.selected];
  if (!selected.length) return false;
  const have = new Set(item.tags);
  if (state.mode === "and") return selected.every((t) => have.has(t));
  return selected.some((t) => have.has(t));
}

function renderLinks() {
  const root = document.getElementById("links");
  const source = state.aiItems || state.items;
  const shown = state.aiItems ? source : source.filter(matchLink);
  root.innerHTML = "";
  if (!shown.length) {
    const p = document.createElement("p");
    p.style.margin = "1rem";
    p.textContent = t("none");
    root.appendChild(p);
    return;
  }
  for (const item of shown) {
    const a = document.createElement("a");
    a.className = "link on";
    a.href = item.url;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.textContent = item.title;
    const ed = document.createElement("span");
    ed.className = "edit";
    ed.textContent = "✎";
    ed.title = t("editTitle");
    ed.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      openEdit(item);
    });
    a.appendChild(ed);
    a.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      if (confirm(`${item.title}\n${item.url}`)) {
        navigator.clipboard.writeText(item.url);
      }
    });
    root.appendChild(a);
  }
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg || "";
}

document.getElementById("showall").onclick = () => {
  state.selected = new Set(state.tags);
  state.mode = "or";
  document.querySelector('input[name="mode"][value="or"]').checked = true;
  state.aiItems = null;
  renderChips();
  renderLinks();
};
document.getElementById("hiddenall").onclick = () => {
  state.selected = new Set();
  state.mode = "and";
  document.querySelector('input[name="mode"][value="and"]').checked = true;
  state.aiItems = null;
  renderChips();
  renderLinks();
};
document.querySelectorAll('input[name="mode"]').forEach((el) => {
  el.addEventListener("change", () => {
    state.mode = document.querySelector('input[name="mode"]:checked').value;
    state.aiItems = null;
    renderLinks();
  });
});

document.getElementById("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  state.query = document.getElementById("q").value;
  state.aiItems = null;
  if (!state.selected.size) {
    state.selected = new Set(state.tags);
    state.mode = "or";
    document.querySelector('input[name="mode"][value="or"]').checked = true;
    renderChips();
  }
  renderLinks();
});

document.getElementById("ai-search").onclick = async () => {
  const query = document.getElementById("q").value.trim();
  if (!query) {
    setStatus(t("searchPh"));
    return;
  }
  setStatus("…");
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, local: false }),
  });
  const data = await res.json();
  state.aiItems = data.items || [];
  setStatus((t("whale") + (data.msg || "")).trim());
  renderLinks();
};

document.getElementById("btn-lang").onclick = () => {
  state.locale = state.locale === "zh" ? "en" : "zh";
  localStorage.setItem("locale", state.locale);
  applyI18n();
  renderLinks();
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
  if (editingId) {
    await fetch(`/api/links/${editingId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } else {
    await fetch("/api/links", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }
  editDlg.close();
  await load();
});

const setDlg = document.getElementById("set-dlg");
const setForm = document.getElementById("set-form");
document.getElementById("btn-settings").onclick = async () => {
  const cfg = await (await fetch("/api/config")).json();
  setForm.base_url.value = cfg.base_url || "";
  setForm.model.value = cfg.model || "";
  setForm.thinking.checked = !!cfg.thinking;
  setForm.api_key.value = "";
  setForm.api_key.placeholder = cfg.api_key_set ? cfg.api_key_masked : "";
  document.getElementById("key-state").textContent = cfg.api_key_set ? t("keySet") : t("keyEmpty");
  setDlg.showModal();
};
setForm.addEventListener("submit", async (e) => {
  if (e.submitter && e.submitter.value === "cancel") return;
  e.preventDefault();
  const body = {
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
load();
