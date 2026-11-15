/**
 * JavaScript state/unit regressions using a small DOM and deferred-fetch harness.
 * This executes the real app.js state handlers, not a browser, layout engine,
 * PDF viewer, HTTP server or accessibility implementation.
 * Run: node --test tests/test_ui_state.mjs
 * DCI_UI_SOURCE may select a preserved historical script for a negative check.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";
import vm from "node:vm";

const source = readFileSync(process.env.DCI_UI_SOURCE
  ? resolve(process.env.DCI_UI_SOURCE)
  : new URL("../src/dci/static/app.js", import.meta.url), "utf8");
const markup = readFileSync(new URL("../src/dci/static/index.html", import.meta.url), "utf8");
const tick = () => new Promise(resolve => setImmediate(resolve));

function harness() {
  const elements = new Map(), allElements = [], requests = [], urls = [], revoked = [], downloads = [];
  class Element {
    constructor(tag = "div") {
      this.tag = tag; this.children = []; this.hidden = false; this.disabled = false;
      this.open = false; this.value = ""; this.className = ""; this._text = "";
      this.classList = {
        contains: value => this.className.split(/\s+/).includes(value),
        add: value => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), value])].join(" "); },
        remove: value => { this.className = this.className.split(/\s+/).filter(name => name !== value).join(" "); },
        toggle: (value, enabled) => { if(enabled ?? !this.classList.contains(value)) this.classList.add(value); else this.classList.remove(value); },
      };
      allElements.push(this);
    }
    set id(value) { this._id = value; elements.set(value, this); }
    get id() { return this._id; }
    set textContent(value) { this._text = String(value); this.children = []; }
    get textContent() { return this._text + this.children.map(child => child.textContent ?? String(child)).join(""); }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this._text = ""; this.children = children; }
    removeAttribute(name) { delete this[name]; }
    showModal() { this.open = true; }
    close() { this.open = false; }
    focus() { this.focused = true; }
    click() {
      if(this.disabled) return;
      if(this.tag === "a") downloads.push({ href: this.href, download: this.download });
      return this.onclick?.({ preventDefault() {} });
    }
  }
  for(const match of markup.matchAll(/<([a-z][a-z0-9]*)\b[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const element = new Element(match[1]); element.id = match[2];
    element.hidden = /\bhidden\b/.test(match[0]); element.disabled = /\bdisabled\b/.test(match[0]);
  }
  const storage = new Map();
  const context = vm.createContext({
    document: {
      getElementById: id => { assert.ok(elements.has(id), `Unknown DOM fixture id ${id}`); return elements.get(id); },
      createElement: tag => new Element(tag),
      createDocumentFragment: () => new Element("fragment"),
      createTextNode: text => ({ textContent: String(text) }),
      querySelectorAll: selector => {
        assert.equal(selector, "tr.selected");
        return allElements.filter(element => element.tag === "tr" && element.classList.contains("selected"));
      },
    },
    sessionStorage: {
      getItem: key => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value),
      removeItem: key => storage.delete(key),
    },
    URL: {
      createObjectURL: blob => { const url = `blob:unit-${urls.length + 1}`; urls.push({ url, blob }); return url; },
      revokeObjectURL: url => revoked.push(url),
    },
    fetch: (path, options = {}) => new Promise((resolve, reject) => {
      const request = { path, options, answered: false,
        respond(body, status = 200) {
          assert.equal(request.answered, false); request.answered = true;
          resolve({ ok: status >= 200 && status < 300, status,
                    json: async () => body, blob: async () => body });
        },
        fail(message = "network failed") { request.answered = true; reject(new Error(message)); },
      };
      requests.push(request);
    }),
    setInterval: () => 1, setTimeout: () => 1, console,
  });
  vm.runInContext(source, context, { filename: "app.js" });
  const run = code => vm.runInContext(code, context);
  run("token='unit-token'; actor={name:'unit-operator',roles:['reader','operator','approver','publisher']}; sessionGeneration=1;");
  return {
    elements, requests, urls, revoked, downloads, storage, run,
    get: id => elements.get(id),
    pending(path, method = "GET") {
      const request = requests.find(request => !request.answered && request.path === path && (request.options.method ?? "GET") === method);
      assert.ok(request, `Expected pending ${method} ${path}; pending: ${requests.filter(r => !r.answered).map(r => r.path).join(", ")}`);
      return request;
    },
    state: () => JSON.parse(run("JSON.stringify({caseId:currentCase?.id??null,documentId:currentDocument?.id??null,revision:currentDocument?.revision??null,selected:selectedField?.key??null,actor:actor?.name??null})")),
    seedCase(value) { run(`currentCase=${JSON.stringify(value)}; selectedCaseId=currentCase.id;`); },
    selectFirstField() { elements.get("field-rows").children[0].click(); },
    submit(values = {}) {
      for(const [key, value] of Object.entries(values)) elements.get(`dialog-${key}`).value = value;
      return elements.get("dialog-form").onsubmit({ preventDefault() {} });
    },
  };
}

function dossier(id = "C", documentIds = ["A", "B"], revision = 3, extra = {}) {
  return { id, name: `Dossier ${id}`, revision, accepted: false, published: false,
    eligible_for_acceptance: true, reconciliation: { status: "matched", findings: [] },
    documents: documentIds.map(id => ({ id, filename: `${id}.pdf`, document_key: id, version: 1, revision: 0, status: "ready" })),
    ...extra };
}
function documentValue(id = "A", revision = 0, extra = {}) {
  const text = `Subtotal: ${id}`;
  return { id, case_id: "C", current: true, status: "ready", revision, profile: "baseline",
    parsed: { pages: [{ number: 1, text, method: "native" }] },
    checks: { findings: [] },
    extraction: { kind: "invoice", profile: "baseline", model_version: "unit-fixture", line_items: [],
      fields: { subtotal: { normalized: id, raw: id, status: "supported", origin: "extracted",
        transformations: [], evidence: [{ page: 1, start: 0, end: text.length, quote: text }] } } },
    ...extra };
}
function audit(actor) { return [{ at: 1, actor, action: "case.created", details: { reason: actor } }]; }
async function finishCase(h, value, history = []) {
  h.pending(`/api/cases/${value.id}`).respond(value); await tick();
  h.pending(`/api/cases/${value.id}/audit`).respond(history); await tick();
}
async function loadReadyDocument(h, value = documentValue()) {
  const work = h.run(`loadDocument(${JSON.stringify(value.id)})`);
  h.pending(`/api/documents/${value.id}`).respond(value); await tick();
  if(value.parsed) h.pending(`/api/documents/${value.id}/original`).respond(`PDF-${value.id}-${value.revision}`);
  await work;
}

test("correction stays disabled until a current ready field is selected", async () => {
  const h = harness(); h.seedCase(dossier());
  assert.equal(h.get("correct-field").disabled, true);
  await loadReadyDocument(h);
  assert.equal(h.get("correct-field").disabled, true);
  assert.doesNotThrow(() => h.get("correct-field").onclick());
  assert.equal(h.get("dialog").open, false);
  h.selectFirstField();
  assert.equal(h.get("correct-field").disabled, false);
  h.get("correct-field").click();
  assert.equal(h.get("dialog").open, true);
  h.get("dialog-cancel").click();
  await loadReadyDocument(h, documentValue("B", 0, { current: false }));
  h.selectFirstField();
  assert.equal(h.get("correct-field").disabled, true);
  assert.equal(h.get("correct-kind").disabled, true);
});

test("late original PDF cannot replace the newly selected document", async () => {
  const h = harness(); h.seedCase(dossier());
  const old = h.run("loadDocument('A')");
  h.pending("/api/documents/A").respond(documentValue("A")); await tick();
  const oldPdf = h.pending("/api/documents/A/original");
  await loadReadyDocument(h, documentValue("B"));
  const currentUrl = h.get("original-frame").src;
  oldPdf.respond("PDF-A-late"); await old;
  assert.equal(h.state().documentId, "B");
  assert.match(h.get("field-rows").textContent, /B/);
  assert.equal(h.get("original-frame").src, currentUrl);
  assert.deepEqual(h.urls.map(item => item.blob), ["PDF-B-0"]);
});

test("obsolete document metadata cannot trigger another original fetch", async () => {
  const h = harness(); h.seedCase(dossier());
  const old = h.run("loadDocument('A')");
  await loadReadyDocument(h, documentValue("B"));
  h.pending("/api/documents/A").respond(documentValue("A")); await old;
  assert.equal(h.state().documentId, "B");
  assert.equal(h.requests.some(request => request.path === "/api/documents/A/original"), false);
});

test("obsolete document and PDF errors do not overwrite current feedback", async () => {
  const h = harness(); h.seedCase(dossier());
  const oldMetadata = h.run("loadDocument('A')");
  await loadReadyDocument(h, documentValue("B"));
  h.run("notice('Current view')");
  h.pending("/api/documents/A").fail("obsolete metadata error"); await oldMetadata;
  assert.equal(h.get("notice").textContent, "Current view");
  const oldPdfWork = h.run("loadDocument('A')");
  h.pending("/api/documents/A").respond(documentValue("A")); await tick();
  const oldPdf = h.pending("/api/documents/A/original");
  await loadReadyDocument(h, documentValue("B"));
  h.run("notice('Current view')");
  oldPdf.fail("obsolete PDF error"); await oldPdfWork;
  assert.equal(h.get("notice").textContent, "Current view");
  const current = h.run("loadDocument('B')");
  h.pending("/api/documents/B").fail("current document error"); await current;
  assert.match(h.get("notice").textContent, /current document error/);
  assert.equal(h.state().documentId, null);
});

test("switching documents immediately clears the source and field selection", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h); h.selectFirstField();
  const row = h.get("field-rows").children[0], url = h.get("original-download").href;
  const next = h.run("loadDocument('B')");
  assert.equal(h.state().selected, null);
  assert.equal(h.get("review").hidden, true);
  assert.equal(h.get("correct-field").disabled, true);
  assert.equal(h.get("correct-kind").disabled, true);
  assert.equal(h.get("original-frame").src, undefined);
  assert.ok(h.revoked.includes(url));
  row.click();
  assert.equal(h.state().selected, null, "Detached field handlers must not select an old field");
  h.pending("/api/documents/B").respond(documentValue("B", 0, { parsed: null })); await next;
  assert.match(h.get("original-message").textContent, /after document inspection/);
});

test("late case metadata and audit cannot replace the selected case", async () => {
  const h = harness();
  const first = h.run("loadCase('A')");
  const second = h.run("loadCase('B')");
  await finishCase(h, dossier("B"), audit("current-B")); await second;
  h.pending("/api/cases/A").respond(dossier("A")); await first;
  assert.equal(h.state().caseId, "B");
  assert.equal(h.requests.some(request => request.path === "/api/cases/A/audit"), false);
  const third = h.run("loadCase('A')");
  h.pending("/api/cases/A").respond(dossier("A")); await tick();
  const lateAudit = h.pending("/api/cases/A/audit");
  const fourth = h.run("loadCase('B')");
  await finishCase(h, dossier("B"), audit("new-B")); await fourth;
  lateAudit.respond(audit("obsolete-A")); await third;
  assert.equal(h.get("case-name").textContent, "Dossier B");
  assert.match(h.get("audit-list").textContent, /new-B/);
  assert.doesNotMatch(h.get("audit-list").textContent, /obsolete-A/);
});

test("obsolete case audit errors are ignored and current audit failures are visible", async () => {
  const h = harness();
  const old = h.run("loadCase('A')");
  h.pending("/api/cases/A").respond(dossier("A")); await tick();
  const lateAudit = h.pending("/api/cases/A/audit");
  const current = h.run("loadCase('B')");
  await finishCase(h, dossier("B"), audit("B")); await current;
  h.run("notice('Current case B')");
  lateAudit.fail("obsolete audit error"); await old;
  assert.equal(h.get("notice").textContent, "Current case B");
  const refresh = h.run("loadCase('B', false)");
  h.pending("/api/cases/B").respond(dossier("B")); await tick();
  h.pending("/api/cases/B/audit").fail("current audit error"); await refresh;
  assert.match(h.get("notice").textContent, /current audit error/);
});

test("switching cases invalidates a pending PDF and resets correction controls", async () => {
  const h = harness(); h.seedCase(dossier());
  const documentWork = h.run("loadDocument('A')");
  h.pending("/api/documents/A").respond(documentValue("A")); await tick();
  h.selectFirstField(); const latePdf = h.pending("/api/documents/A/original");
  const caseWork = h.run("loadCase('D')");
  assert.equal(h.state().selected, null);
  assert.equal(h.get("correct-field").disabled, true);
  latePdf.respond("obsolete PDF"); await documentWork;
  await finishCase(h, dossier("D", ["D1"])); await caseWork;
  assert.equal(h.state().documentId, null);
  assert.equal(h.get("original-frame").src, undefined);
  assert.equal(h.urls.length, 0);
});

test("a legitimate refreshed revision reloads fields and its original", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h); h.selectFirstField();
  const value = dossier(); value.documents[0].revision = 1;
  const work = h.run("loadCase('C', false)");
  await finishCase(h, value, audit("fresh revision"));
  h.pending("/api/documents/A").respond(documentValue("A", 1)); await tick();
  h.pending("/api/documents/A/original").respond("PDF-new-revision"); await work;
  assert.equal(h.state().revision, 1);
  assert.equal(h.state().selected, null);
  assert.equal(h.get("correct-field").disabled, true);
  assert.equal(h.urls.at(-1).blob, "PDF-new-revision");
});

for(const change of ["revision", "status"]) {
  test(`case ${change} change fences metadata that is still pending and reloads once`, async () => {
    const h = harness(), originalCase = dossier();
    if(change === "status") originalCase.documents[0].status = "processing";
    h.seedCase(originalCase);
    const oldWork = h.run("loadDocument('A')");
    const oldMetadata = h.pending("/api/documents/A");
    const latestCase = dossier();
    const latestRevision = change === "revision" ? 1 : 0;
    latestCase.documents[0].revision = latestRevision;
    const refresh = h.run("loadCase('C', false)");
    await finishCase(h, latestCase);
    const metadataRequests = h.requests.filter(request => request.path === "/api/documents/A");
    assert.equal(metadataRequests.length, 2, "Advancing case metadata must start exactly one replacement request");
    metadataRequests[1].respond(documentValue("A", latestRevision)); await tick();
    h.pending("/api/documents/A/original").respond("PDF-current-state"); await refresh;
    oldMetadata.respond(documentValue("A", 0, change === "status"
      ? { status: "processing", parsed: null, extraction: null } : {}));
    await oldWork;
    assert.equal(h.state().revision, latestRevision);
    assert.equal(h.urls.at(-1).blob, "PDF-current-state");
    assert.equal(h.requests.filter(request => request.path === "/api/documents/A/original").length, 1);
    const unchanged = h.run("loadCase('C', false)");
    await finishCase(h, latestCase); await unchanged;
    assert.equal(h.requests.filter(request => request.path === "/api/documents/A").length, 2,
      "The unchanged current summary must not start a reload loop");
  });
}

test("a superseded selected document cannot finish its pending original fetch", async () => {
  const h = harness(); h.seedCase(dossier());
  const documentWork = h.run("loadDocument('A')");
  h.pending("/api/documents/A").respond(documentValue("A")); await tick();
  const latePdf = h.pending("/api/documents/A/original");
  const refresh = h.run("loadCase('C', false)");
  await finishCase(h, dossier("C", ["A-v2", "B"])); await refresh;
  latePdf.respond("superseded original"); await documentWork;
  assert.equal(h.state().documentId, null);
  assert.equal(h.get("review").hidden, true);
  assert.equal(h.get("original-frame").src, undefined);
});

test("an old list refresh does not navigate away from a subsequent explicit selection", async () => {
  const h = harness();
  const refresh = h.run("refresh()");
  const selected = h.run("loadCase('B')");
  await finishCase(h, dossier("B")); await selected;
  h.pending("/api/cases").respond([dossier("A"), dossier("B")]);
  h.pending("/api/ready").respond({ queue: { jobs: {}, publications: 0 } }); await refresh;
  assert.equal(h.state().caseId, "B");
  assert.equal(h.requests.filter(request => request.path === "/api/cases/B").length, 1);
  assert.equal(h.requests.some(request => request.path === "/api/cases/A"), false);
});

test("changing actor invalidates metadata, original, list and login responses", async () => {
  const h = harness(); h.seedCase(dossier());
  const documentWork = h.run("loadDocument('A')");
  h.pending("/api/documents/A").respond(documentValue("A")); await tick();
  const pdf = h.pending("/api/documents/A/original");
  const refresh = h.run("refresh()");
  h.get("switch-actor").click();
  pdf.respond("old actor PDF"); await documentWork;
  h.pending("/api/cases").respond([dossier()]);
  h.pending("/api/ready").respond({ queue: { jobs: {}, publications: 0 } }); await refresh;
  assert.equal(h.state().actor, null);
  assert.equal(h.state().documentId, null);
  assert.equal(h.get("workspace").hidden, true);
  assert.equal(h.urls.length, 0);
  h.run("token='another-token'");
  const login = h.run("connect()");
  h.get("switch-actor").click();
  h.pending("/api/me").respond({ name: "stale actor", roles: ["operator"] }); await login;
  assert.equal(h.state().actor, null);
  assert.equal(h.storage.has("dci-token"), false);
});

test("field dialog retains its original document, revision and field target", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h, documentValue("A", 3)); h.selectFirstField();
  h.get("correct-field").click();
  await loadReadyDocument(h, documentValue("B", 9)); h.selectFirstField();
  const submission = h.submit({ value: "12.00", reason: "reviewed source A" });
  const request = h.pending("/api/documents/A/corrections", "POST");
  assert.deepEqual(JSON.parse(request.options.body), { value: "12.00", reason: "reviewed source A", field: "subtotal", expected_revision: 3 });
  request.respond({ code: "STALE_REVISION", message: "Old reviewed revision" }, 409); await submission;
  assert.match(h.get("notice").textContent, /STALE_REVISION/);
  assert.equal(h.state().documentId, "B");
});

test("type dialog does not silently use a newer revision", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h, documentValue("A", 3)); h.get("correct-kind").click();
  await loadReadyDocument(h, documentValue("A", 4));
  const submission = h.submit({ kind: "delivery_note", reason: "reviewed revision 3" });
  const request = h.pending("/api/documents/A/classification-review", "POST");
  assert.equal(JSON.parse(request.options.body).expected_revision, 3);
  request.respond({ code: "STALE_REVISION" }, 409); await submission;
});

for(const action of ["accept", "publish"]) {
  test(`${action} dialog keeps the case and revision reviewed when it opened`, async () => {
    const h = harness(); h.seedCase(dossier("A", [], 3, { accepted: action === "publish" }));
    h.get(`${action}-case`).onclick();
    h.seedCase(dossier("B", [], 9, { accepted: true }));
    const submission = h.submit(action === "accept" ? { reason: "reviewed A" } : {});
    const request = h.pending(`/api/cases/A/${action}`, "POST");
    assert.equal(JSON.parse(request.options.body).expected_revision, 3);
    request.respond({ code: "STALE_REVISION" }, 409); await submission;
    assert.equal(h.state().caseId, "B");
  });
}

test("upload dialog is bound to the selected case and cannot submit after actor switch", async () => {
  const h = harness(); h.seedCase(dossier("A")); h.get("upload-document").onclick();
  h.seedCase(dossier("B"));
  h.get("dialog-file").files = [{ name: "source.pdf" }];
  const submission = h.submit({ key: "INV-A" });
  const request = h.pending("/api/cases/A/documents?document_key=INV-A&filename=source.pdf", "POST");
  request.respond({ code: "QUEUE_FULL" }, 429); await submission;
  h.get("dialog-cancel").click(); h.get("upload-document").onclick();
  const submit = h.get("dialog-form").onsubmit, before = h.requests.length;
  h.get("switch-actor").click(); await submit({ preventDefault() {} });
  assert.equal(h.requests.length, before);
});

test("old dialog completion cannot close a newer dialog or replace its error", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h); h.selectFirstField(); h.get("correct-field").click();
  const oldSubmit = h.submit({ value: "1.00", reason: "old correction" });
  const oldRequest = h.pending("/api/documents/A/corrections", "POST");
  h.get("dialog-cancel").click(); h.get("correct-kind").click();
  h.run("notice('New dialog context')");
  oldRequest.respond({ code: "STALE_REVISION", message: "obsolete submission" }, 409); await oldSubmit;
  assert.equal(h.get("dialog").open, true);
  assert.equal(h.get("dialog-title").textContent, "Review document type");
  assert.equal(h.get("dialog-submit").disabled, false);
  assert.equal(h.get("notice").textContent, "New dialog context");
});

test("cancelled creation cannot navigate to its late successful result", async () => {
  const h = harness(); h.seedCase(dossier("A"));
  h.get("new-case").onclick();
  const submission = h.submit({ name: "New dossier" });
  const created = h.pending("/api/cases", "POST");
  h.get("dialog-cancel").click();
  const selection = h.run("loadCase('B')");
  await finishCase(h, dossier("B")); await selection;
  created.respond(dossier("created"), 201); await submission;
  assert.equal(h.state().caseId, "B");
  assert.equal(h.requests.some(request => request.path === "/api/cases/created"), false);
});

test("cancelled correction success does not reload beneath a newer review dialog", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h); h.selectFirstField(); h.get("correct-field").click();
  const submission = h.submit({ value: "1.00", reason: "old correction" });
  const corrected = h.pending("/api/documents/A/corrections", "POST");
  h.get("dialog-cancel").click(); h.get("correct-kind").click();
  corrected.respond(documentValue("A", 1)); await submission;
  assert.equal(h.get("dialog").open, true);
  assert.equal(h.get("dialog-title").textContent, "Review document type");
  assert.equal(h.requests.filter(request => request.path === "/api/documents/A").length, 1);
});

test("a current successful correction reloads its document and completes the dialog", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h); h.selectFirstField(); h.get("correct-field").click();
  const submission = h.submit({ value: "1.00", reason: "current source" });
  h.pending("/api/documents/A/corrections", "POST").respond(documentValue("A", 1)); await tick();
  h.pending("/api/documents/A").respond(documentValue("A", 1)); await tick();
  h.pending("/api/documents/A/original").respond("PDF-after-correction"); await tick();
  h.pending("/api/cases").respond([dossier()]);
  h.pending("/api/ready").respond({ queue: { jobs: {}, publications: 0 } }); await tick();
  const value = dossier(); value.documents[0].revision = 1;
  await finishCase(h, value); await submission;
  assert.equal(h.get("dialog").open, false);
  assert.equal(h.state().revision, 1);
  assert.equal(h.state().selected, null);
  assert.equal(h.get("correct-field").disabled, true);
  assert.equal(h.urls.at(-1).blob, "PDF-after-correction");
});

test("preview request is deduplicated and a displayed page stays visible while reviewing fields", async () => {
  const h = harness(); h.seedCase(dossier());
  await loadReadyDocument(h);
  const preview=h.pending("/api/documents/A/preview?page=1");
  h.selectFirstField();
  assert.equal(h.requests.filter(request => request.path === "/api/documents/A/preview?page=1").length, 1);
  preview.respond("PNG-rendered-page-A");
  await tick(); await tick();
  assert.equal(h.get("original-frame").hidden, false);
  assert.equal(h.urls.at(-1).blob, "PNG-rendered-page-A");
  const expectedUrl=h.get("original-frame").src;
  h.selectFirstField();
  assert.equal(h.get("original-frame").src, expectedUrl);
  assert.equal(h.get("original-frame").hidden, false);
  assert.equal(h.requests.filter(request => request.path === "/api/documents/A/preview?page=1").length, 1);
});
