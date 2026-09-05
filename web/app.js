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
    setHint: "可加多层接口。当前层先用，失败再试下一层。搜索时提示词和思考全文展示。",
    active: "当前层",
    thinking: "思考过程",
    none: "没有结果。换个说法，或把站点加进收藏。",
    fail: "模型没跑起来（多半是欠费或 key）。设计上仍走两层 AI，不是改成纯本地。",
    keySet: "已保存密钥",
    keyEmpty: "还没有密钥，搜索会走本地",
    searching: "正在搜…",
    traceTitle: "小鲸鱼运算",
    traceNote: "提示词和思考全文展示，不做隐藏。",
    promptLabel: "发给模型的提示词（完整，未隐藏）",
    thinkLabel: "思考",
    outLabel: "输出",
    layerTags: "第一层 · 短标签",
    layerLinks: "第二层 · 长描述",
    tokens: "tokens",
    done: "算完了",
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
    setHint: "Multiple OpenAI-compatible layers. Active first, then fallback. Prompts and thinking are shown in full.",
    active: "Active",
    thinking: "Thinking traces",
    none: "Nothing found. Try another query, or add the site.",
    fail: "Model call failed (billing or key). The product is still two-layer AI.",
    keySet: "Key saved",
    keyEmpty: "No API key; search is local",
    searching: "Searching…",
    traceTitle: "Whale computing",
    traceNote: "Prompts and thinking are shown in full. Nothing is hidden.",
    promptLabel: "Prompt sent to the model (complete, unredacted)",
    thinkLabel: "Thinking",
    outLabel: "Output",
    layerTags: "Layer 1 · tags",
    layerLinks: "Layer 2 · descriptions",
    tokens: "tokens",
    done: "Done",
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

function setWhale(msg) {
  const el = document.getElementById("whale");
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

function setPhase(text) {
  document.getElementById("trace-phase").textContent = text || "";
}

function resetTrace(show) {
  const el = document.getElementById("trace");
  const body = document.getElementById("trace-body");
  body.innerHTML = "";
  el.hidden = !show;
  el.classList.toggle("running", !!show);
  setPhase(show ? t("searching") : "");
  el._layers = {};
  el._current = null;
}

function layerBox(ev) {
  const root = document.getElementById("trace");
  const key = String(ev.layer || "x") + ":" + (ev.provider || "") + ":" + (root._layers && Object.keys(root._layers).length);
  const body = document.getElementById("trace-body");
  const sec = document.createElement("section");
  sec.className = "trace-layer";
  const h = document.createElement("h4");
  const title = ev.title || (ev.layer === "links" ? t("layerLinks") : t("layerTags"));
  const meta = [ev.provider, ev.model].filter(Boolean).join(" / ");
  h.textContent = meta ? `${title} · ${meta}` : title;
  const details = document.createElement("details");
  details.open = true;
  const sum = document.createElement("summary");
  sum.textContent = t("promptLabel");
  const sys = document.createElement("pre");
  sys.className = "trace-sys";
  sys.textContent = "SYSTEM\n" + (ev.system || "");
  const usr = document.createElement("pre");
  usr.className = "trace-usr";
  usr.textContent = "USER\n" + (ev.user || "");
  details.append(sum, sys, usr);
  const thinkWrap = document.createElement("div");
  thinkWrap.className = "trace-think";
  thinkWrap.hidden = true;
  const thinkLab = document.createElement("div");
  thinkLab.className = "trace-label";
  thinkLab.textContent = t("thinkLabel");
  const think = document.createElement("pre");
  thinkWrap.append(thinkLab, think);
  const outWrap = document.createElement("div");
  outWrap.className = "trace-out";
  outWrap.hidden = true;
  const outLab = document.createElement("div");
  outLab.className = "trace-label";
  outLab.textContent = t("outLabel");
  const out = document.createElement("pre");
  outWrap.append(outLab, out);
  const usage = document.createElement("div");
  usage.className = "trace-label";
  sec.append(h, details, thinkWrap, outWrap, usage);
  body.appendChild(sec);
  const box = { think, thinkWrap, out, outWrap, usage, el: sec };
  root._layers[key] = box;
  root._current = box;
  think.scrollTop = think.scrollHeight;
  return box;
}

function currentLayer() {
  const root = document.getElementById("trace");
  return root._current;
}

function appendPre(pre, wrap, chunk) {
  wrap.hidden = false;
  pre.textContent += chunk || "";
  pre.scrollTop = pre.scrollHeight;
}

function handleTrace(ev) {
  const kind = ev.type;
  if (kind === "status" && ev.text) {
    setPhase(ev.text);
    setStatus(ev.text);
    return;
  }
  if (kind === "prompt") {
    document.getElementById("trace").hidden = false;
    layerBox(ev);
    setPhase(ev.title || t("searching"));
    return;
  }
  if (kind === "think") {
    const box = currentLayer();
    if (box) appendPre(box.think, box.thinkWrap, ev.text);
    return;
  }
  if (kind === "content") {
    const box = currentLayer();
    if (box) appendPre(box.out, box.outWrap, ev.text);
    return;
  }
  if (kind === "usage") {
    const box = currentLayer();
    if (box && ev.total_tokens != null) {
      box.usage.textContent = `${ev.total_tokens} ${t("tokens")}`;
    }
    return;
  }
  if (kind === "fallback") {
    const p = document.createElement("p");
    p.className = "trace-fallback";
    p.textContent = `${ev.provider || ""} 失败${ev.next ? "，试 " + ev.next : ""}：${ev.error || ""}`;
    document.getElementById("trace-body").appendChild(p);
    setStatus(p.textContent);
  }
}

function paintTrace(trace) {
  if (!trace || !trace.length) return;
  resetTrace(true);
  document.getElementById("trace").classList.remove("running");
  for (const step of trace) {
    handleTrace({ type: "prompt", ...step });
    if (step.think) handleTrace({ type: "think", text: step.think });
    if (step.content) handleTrace({ type: "content", text: step.content });
    if (step.total_tokens != null) handleTrace({ type: "usage", total_tokens: step.total_tokens });
  }
}

async function readSSE(res, onEvent, signal) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    if (signal && signal.aborted) {
      try { await reader.cancel(); } catch (_) { /* ignore */ }
      throw new DOMException("aborted", "AbortError");
    }
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop();
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      let ev;
      try {
        ev = JSON.parse(line.slice(6));
      } catch (_) {
        continue;
      }
      onEvent(ev);
    }
  }
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

let searchAbort = null;

async function runSearch(query, local) {
  query = (query || "").trim();
  if (searchAbort) searchAbort.abort();
  if (!query) {
    setHome(true);
    document.getElementById("results").innerHTML = "";
    setStatus("");
    setWhale("");
    resetTrace(false);
    return;
  }
  document.getElementById("q").value = query;
  setHome(false);
  document.getElementById("results").innerHTML = "";
  setWhale("");
  resetTrace(!local);
  setStatus(t("searching"));
  const ac = new AbortController();
  searchAbort = ac;
  try {
    const res = await fetch("/api/search/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ query, local: !!local }),
      signal: ac.signal,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setStatus(typeof data.detail === "string" ? data.detail : t("fail"));
      document.getElementById("trace").classList.remove("running");
      return;
    }
    let result = null;
    await readSSE(res, (ev) => {
      if (ev.type === "done") {
        result = ev.result || {};
        return;
      }
      if (ev.type === "error") {
        result = { error: ev.msg || t("fail") };
        return;
      }
      if (!local) handleTrace(ev);
    }, ac.signal);
    document.getElementById("trace").classList.remove("running");
    if (!result) {
      setStatus(t("fail"));
      return;
    }
    if (result.error) {
      setPhase("");
      setStatus(result.error);
      return;
    }
    if (local) resetTrace(false);
    else setPhase(t("done"));
    state.items = result.items || [];
    setWhale(result.msg || "");
    render(state.items, "");
  } catch (err) {
    if (err && err.name === "AbortError") return;
    setStatus(t("fail"));
    document.getElementById("trace").classList.remove("running");
  }
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
