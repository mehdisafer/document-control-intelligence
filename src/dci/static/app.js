"use strict";
const $ = id => document.getElementById(id);
let token = sessionStorage.getItem("dci-token") || "";
let actor = null, currentCase = null, currentDocument = null, selectedField = null, originalUrl = null, previewUrl = null;
let previewGeneration = 0, previewPage = 1, previewCount = 0;
let sessionGeneration = 0, refreshGeneration = 0, caseGeneration = 0, documentGeneration = 0, dialogGeneration = 0;
let selectedCaseId = null, selectedDocumentId = null;
let pendingDocumentSummary = null;
function node(tag, text, cls) { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; }
function notice(text, error = false) { $("notice").textContent = text; $("notice").hidden = !text; $("notice").classList.toggle("error", error); }
function clearDocument() {
  documentGeneration++; selectedDocumentId = null; currentDocument = null; selectedField = null; pendingDocumentSummary = null;
  $("review").hidden = true; $("evidence").hidden = true;
  $("correct-field").disabled = true; $("correct-kind").disabled = true;
  if(originalUrl) URL.revokeObjectURL(originalUrl);
  originalUrl = null; $("original-download").removeAttribute("href");
  previewGeneration++; if(previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = null; previewPage = 1; previewCount = 0;
  $("original-frame").removeAttribute("src"); $("original-frame").hidden = true;
  $("preview-controls").hidden = true; $("preview-placeholder").hidden = false;
  $("preview-placeholder").textContent = "Select a processed document to display its verified source page.";
  $("original-message").textContent = "";
}
function clearCase() {
  caseGeneration++; selectedCaseId = null; currentCase = null; clearDocument();
  $("case-detail").hidden = true; $("document-list").replaceChildren(); $("audit-list").replaceChildren();
  for(const id of ["upload-document", "accept-case", "publish-case", "export-case"]) $(id).disabled = true;
}
function canCorrectDocument() {
  return can("operator") && !!currentDocument?.current && currentDocument.status === "ready" && !!currentDocument.extraction;
}
async function api(path, options = {}) {
  const headers = {Authorization: `Bearer ${token}`, ...options.headers};
  const response = await fetch(path, {...options, headers});
  if (!response.ok) { let body; try { body = await response.json(); } catch { body = {}; }
    throw new Error(`${body.code || response.status}: ${typeof body.detail === "string" ? body.detail : body.message || "Request could not be completed."}`); }
  return options.binary ? response.blob() : response.json();
}
function post(path, body) { return api(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)}); }
function can(role) { return !!actor?.roles.includes(role); }
function title(value) { return String(value).replaceAll("_", " "); }
function stamp(value) { return new Date(value * 1000).toLocaleString([], {dateStyle:"short",timeStyle:"short"}); }
async function connect() {
  const session = ++sessionGeneration, connectingToken = token;
  refreshGeneration++; actor = null; clearCase(); $("new-case").disabled = true;
  try {
    const identity = await api("/api/me");
    if(session !== sessionGeneration || token !== connectingToken) return false;
    actor = identity; sessionStorage.setItem("dci-token", token);
    $("actor-name").textContent = actor.name; $("actor-roles").textContent = actor.roles.join(" · ");
    $("login-panel").hidden = true; $("workspace").hidden = false; $("new-case").disabled = !can("operator");
    notice(""); await refresh(); return true;
  } catch(e) {
    if(session === sessionGeneration) { sessionStorage.removeItem("dci-token"); notice(e.message, true); }
    return false;
  }
}
$("login-form").onsubmit = async event => { event.preventDefault(); token = $("token").value.trim(); if(await connect()) $("token").value = ""; };
$("switch-actor").onclick = () => {
  sessionGeneration++; refreshGeneration++; dialogGeneration++; $("dialog").close(); clearCase();
  $("new-case").disabled = true; sessionStorage.removeItem("dci-token"); token = ""; actor = null;
  $("login-panel").hidden = false; $("workspace").hidden = true;
  $("actor-name").textContent = "Not connected"; $("actor-roles").textContent = ""; $("token").focus();
};
function findingNodes(findings) { const fragment = document.createDocumentFragment(); for (const f of findings) { const n = node("div", undefined, `finding ${f.severity}`); n.append(node("span", f.code, "code"), node("span", f.message)); fragment.append(n); } return fragment; }
async function refresh() {
  if(!token || !actor) return;
  const session = sessionGeneration, request = ++refreshGeneration, selection = caseGeneration;
  const active = () => session === sessionGeneration && request === refreshGeneration;
  try {
    const [cases, ready] = await Promise.all([api("/api/cases"), api("/api/ready")]);
    if(!active()) return;
    $("case-count").textContent = cases.length; $("metric-cases").textContent = cases.length;
    $("metric-pending").textContent = (ready.queue.jobs.queued||0)+(ready.queue.jobs.running||0);
    $("metric-published").textContent = ready.queue.publications;
    $("case-list").replaceChildren();
    for (const c of cases) { const row=node("button",undefined,`case-row ${selectedCaseId===c.id?"active":""}`); row.append(node("strong",c.name),node("small",`${c.published_fingerprint?"Published":c.accepted_fingerprint?"Accepted":"In review"} · ${stamp(c.created_at)}`)); row.onclick=()=>loadCase(c.id); $("case-list").append(row); }
    // A list refresh started before a selection must not navigate away from it.
    if(selection !== caseGeneration) return;
    if(selectedCaseId) await loadCase(selectedCaseId, false); else if(cases.length) await loadCase(cases[0].id);
  } catch(e) { if(active() && selection === caseGeneration) notice(e.message, true); }
}
$("refresh").onclick = refresh; $("reload").onclick = refresh;
async function loadCase(id, reset = true) {
  if(!token || !actor) return;
  if(selectedCaseId !== id) { clearCase(); notice(""); }
  selectedCaseId = id;
  const session = sessionGeneration, request = ++caseGeneration;
  const active = () => session === sessionGeneration && request === caseGeneration && selectedCaseId === id;
  try {
  const dossier = await api(`/api/cases/${id}`);
  if(!active()) return;
  const history = await api(`/api/cases/${id}/audit`);
  if(!active()) return;
  currentCase = dossier;
  $("empty").hidden=true; $("case-detail").hidden=false;
  $("case-name").textContent=currentCase.name; $("case-revision").textContent=`Revision ${currentCase.revision} · ${currentCase.documents.length} current documents`;
  const status=currentCase.published?"published":currentCase.accepted?"accepted":currentCase.reconciliation.status;
  $("case-status").textContent=title(status); $("case-status").className=`badge ${status}`;
  $("reconciliation").replaceChildren(findingNodes(currentCase.reconciliation.findings));
  $("upload-document").disabled=!can("operator"); $("accept-case").disabled=!can("approver")||!currentCase.eligible_for_acceptance||currentCase.accepted;
  $("publish-case").disabled=!can("publisher")||!currentCase.accepted||currentCase.published; $("export-case").disabled=!currentCase.published;
  $("acceptance-note").textContent=currentCase.accepted?`Accepted by ${currentCase.accepted_by}. Any correction or new document version requires a new acceptance.`:"Viewing a dossier does not approve it. Acceptance and publication are explicit actions.";
  $("document-list").replaceChildren();
  for(const d of currentCase.documents) { const b=node("button",undefined,`doc-row ${d.id===selectedDocumentId?"active":""}`); const label=node("span",undefined,"doc-name"); label.append(node("strong",d.filename),node("small",`${d.document_key} · Version ${d.version} · Revision ${d.revision}`)); b.append(node("span","PDF","pdf-icon"),label,node("span",title(d.status),"small-badge")); b.onclick=()=>loadDocument(d.id); $("document-list").append(b); }
  $("audit-list").replaceChildren();
  for(const event of history.slice().reverse()) { const entry=node("div",undefined,"audit-entry"), text=node("div",undefined,"audit-text"); text.append(node("b",`${event.actor} · ${event.action.replaceAll("."," ")}`)); let detail=event.details.justification||event.details.reason||event.details.error_code||""; if(event.action==="classification.reviewed") detail=`${title(event.details.old_kind)} → ${title(event.details.new_kind)} · ${detail}`; if(event.action==="field.corrected") detail=`${event.details.field}: ${event.details.old.normalized??"—"} → ${event.details.new.normalized} · ${detail}`; text.append(node("small",detail)); entry.append(node("time",stamp(event.at),"audit-time"),text); $("audit-list").append(entry); }
  if(selectedDocumentId) {
    const latest=currentCase.documents.find(d=>d.id===selectedDocumentId);
    const displayedOrPending=currentDocument || pendingDocumentSummary;
    if(!latest) clearDocument();
    else if(!displayedOrPending || reset || latest.revision!==displayedOrPending.revision || latest.status!==displayedOrPending.status) await loadDocument(selectedDocumentId);
  }
  } catch(e) { if(active()) notice(e.message, true); }
}
async function loadDocument(id) {
  const summary=currentCase?.documents.find(d=>d.id===id);
  if(!token || !actor || !summary) return;
  const session = sessionGeneration, caseId = selectedCaseId;
  if(selectedDocumentId !== id) notice("");
  clearDocument(); selectedDocumentId = id;
  // A case refresh can advance a document before its metadata request returns.
  // Remember the requested state so that change fences and reloads it once.
  pendingDocumentSummary = { revision: summary.revision, status: summary.status };
  const request = documentGeneration;
  const active = () => session === sessionGeneration && request === documentGeneration && caseId === selectedCaseId && selectedDocumentId === id;
  try {
  const loaded = await api(`/api/documents/${id}`);
  if(!active()) return;
  currentDocument=loaded; $("review").hidden=false;
  const d=currentDocument, x=d.extraction; $("extraction-profile").textContent=x?.profile||d.profile;
  $("document-status").textContent=x?`${title(x.kind)} · ${x.model_version} · ${d.current?"Current version":"Historical version"}`:`${title(d.status)}${d.error_code?" · "+d.error_code:""}`;
  $("correct-kind").disabled=!canCorrectDocument();
  const proposal=d.classification_proposal, review=d.classification_review;
  $("classification-review").textContent=review?`Human type decision: ${title(review.new_kind)} · ${review.actor} · ${stamp(review.at)}. Original model proposal: ${title(proposal?.kind||"unknown")}. Reason: ${review.reason}`:proposal?`Model type proposal: ${title(proposal.kind)} · score ${Number(proposal.confidence).toFixed(3)}. A score does not replace source review.`:"";
  $("document-findings").replaceChildren(findingNodes(d.checks?.findings||[])); $("field-rows").replaceChildren(); $("line-items").replaceChildren();
  if(x) { for(const [key,f] of Object.entries(x.fields)) fieldRow($("field-rows"),key,f); x.line_items.forEach((line,index)=>{ const section=node("section"); section.append(node("h3",`Line item ${index+1}`,"line-heading")); const table=node("table"), body=node("tbody"); Object.entries(line.fields).forEach(([key,f])=>fieldRow(body,`line_items.${index}.${key}`,f)); table.append(body); section.append(table); $("line-items").append(section); }); }
  if(d.parsed) {
    const blob=await api(`/api/documents/${id}/original`,{binary:true});
    if(!active()) return;
    originalUrl=URL.createObjectURL(blob);
    $("original-download").href=originalUrl;
    $("original-message").textContent=`${d.parsed.pages.length} page(s) · ${d.parsed.pages.map(p=>`p${p.number}: ${p.method}`).join(" · ")} · Original SHA-256 verified before rasterization`;
    await showPreview(1);
  }
  else { $("original-message").textContent="Preview becomes available after document inspection."; }
  } catch(e) { if(active()) notice(e.message, true); }
}
async function showPreview(number) {
  const doc = currentDocument;
  if(!doc?.parsed?.pages?.length) return;
  if(!Number.isInteger(number) || number < 1 || number > doc.parsed.pages.length) return;
  const session = sessionGeneration, requestDoc = documentGeneration, caseId = selectedCaseId;
  const request = ++previewGeneration, id = doc.id;
  const active = () => session === sessionGeneration && request === previewGeneration &&
    requestDoc === documentGeneration && caseId === selectedCaseId &&
    selectedDocumentId === id && currentDocument === doc;
  previewPage = number; previewCount = doc.parsed.pages.length;
  $("preview-controls").hidden = false;
  $("preview-position").textContent = `Page ${number} of ${previewCount}`;
  $("preview-prev").disabled = number <= 1;
  $("preview-next").disabled = number >= previewCount;
  $("preview-placeholder").textContent = `Rendering original page ${number}…`;
  $("preview-placeholder").hidden = false;
  try {
    const image = await api(`/api/documents/${id}/preview/${number}`, {binary:true});
    if(!active()) return;
    if(image?.type && image.type !== "image/png") throw Error("Preview response is not PNG.");
    const url = URL.createObjectURL(image);
    if(previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = url;
    const target = $("original-frame");
    target.onload = () => {
      if(!active() || previewUrl !== url) return;
      if(!target.naturalWidth || !target.naturalHeight) {
        target.hidden = true; $("preview-placeholder").hidden = false;
        $("preview-placeholder").textContent = "Unable to decode preview; download the verified original.";
        return;
      }
      target.hidden = false; $("preview-placeholder").hidden = true;
    };
    target.onerror = () => {
      if(!active() || previewUrl !== url) return;
      target.hidden = true; $("preview-placeholder").hidden = false;
      $("preview-placeholder").textContent = "Unable to display preview; download the verified original.";
    };
    target.src = url; target.hidden = false;
  } catch(e) {
    if(!active()) return;
    $("original-frame").hidden = true; $("preview-placeholder").hidden = false;
    $("preview-placeholder").textContent = `Preview unavailable: ${e.message}. Download the original for inspection.`;
  }
}
$("preview-prev").onclick = () => { if(previewPage > 1) void showPreview(previewPage-1); };
$("preview-next").onclick = () => { if(previewPage < previewCount) void showPreview(previewPage+1); };
function fieldRow(body,key,field) { const row=node("tr"), source=currentDocument; row.append(node("td",title(key.split(".").at(-1))),node("td",field.normalized??"—")); const td=node("td");td.append(node("span",title(field.status),`field-state ${field.status}`));row.append(td);row.tabIndex=0;row.onclick=()=>{if(currentDocument===source)selectField(key,field,row);};row.onkeydown=e=>{if(e.key==="Enter")row.onclick();};body.append(row); }
function selectField(key,field,row) {
  if(!currentDocument) return;
  document.querySelectorAll("tr.selected").forEach(n=>n.classList.remove("selected"));row.classList.add("selected");selectedField={key,field,documentId:currentDocument.id,revision:currentDocument.revision};$("evidence").hidden=false;$("evidence-field").textContent=title(key);
  const evidence=field.evidence.at(-1);$("evidence-meta").textContent=evidence?`Page ${evidence.page} · Text ${evidence.start}–${evidence.end}${evidence.bbox?" · Box "+evidence.bbox.map(n=>n.toFixed(1)).join(", ")+" pt":""}`:"No supported source span. This field requires review.";
  $("evidence-quote").replaceChildren();
  for(const citation of field.evidence) { const page=currentDocument.parsed.pages.find(p=>p.number===citation.page);const before=page.text.slice(Math.max(0,citation.start-45),citation.start),after=page.text.slice(citation.end,citation.end+45);$("evidence-quote").append(document.createTextNode(`Page ${citation.page} · source ${citation.start}–${citation.end}\n`),document.createTextNode(before),node("mark",citation.quote),document.createTextNode(after+"\n\n")); }
  if(evidence && originalUrl && (previewPage !== evidence.page || !previewUrl)) void showPreview(evidence.page);
  $("evidence-transforms").textContent=`Raw: ${field.raw??"absent"}. ${field.transformations.join(" → ")||"No transformation"}.${field.origin==="human"?" Human correction; the original quoted value is retained for audit.":""}${field.reason?" "+field.reason:""}`;
  $("correct-field").disabled=!canCorrectDocument();
}
function dialog(titleText,note,fields,submitLabel,onSubmit) {
  const session = sessionGeneration, request = ++dialogGeneration;
  const active = () => session === sessionGeneration && request === dialogGeneration && $("dialog").open;
  let submitting = false;
  $("dialog-title").textContent=titleText;$("dialog-note").textContent=note;$("dialog-submit").textContent=submitLabel;$("dialog-fields").replaceChildren();
  $("dialog-submit").disabled = false;
  for(const spec of fields) { const label=node("label",spec.label);label.htmlFor=`dialog-${spec.name}`;const input=node(spec.type==="textarea"?"textarea":spec.type==="select"?"select":"input");input.id=`dialog-${spec.name}`;input.name=spec.name;input.required=spec.required!==false;if(!["textarea","select"].includes(spec.type))input.type=spec.type||"text";if(spec.type==="select")for(const value of spec.options){const option=node("option",title(value));option.value=value;input.append(option);}if(spec.type==="file")input.accept="application/pdf";else input.value=spec.value||"";input.maxLength=spec.name==="reason"?1000:200;$("dialog-fields").append(label,input); }
  $("dialog-form").onsubmit=async event=>{event.preventDefault();if(!active()||submitting)return;const data={};for(const spec of fields){const input=$(`dialog-${spec.name}`);data[spec.name]=spec.type==="file"?input.files[0]:input.value;}submitting=true;$("dialog-submit").disabled=true;notice("");try{await onSubmit(data,active);if(!active())return;$("dialog").close();await refresh();}catch(e){if(active())notice(e.message,true);}finally{submitting=false;if(session===sessionGeneration&&request===dialogGeneration)$("dialog-submit").disabled=false;}};
  $("dialog").showModal();
}
$("dialog-cancel").onclick=()=>{dialogGeneration++;$("dialog").close();};
$("dialog").oncancel=()=>{dialogGeneration++;};
$("new-case").onclick=()=>{
  if(!can("operator")) return;
  dialog("New control dossier","Group one purchase order with its delivery notes and invoices.",[{name:"name",label:"Dossier name"}],"Create",async(d,active)=>{const created=await post("/api/cases",d);if(active())await loadCase(created.id);});
};
$("upload-document").onclick=()=>{
  if(!can("operator")||!currentCase) return;
  const caseId=currentCase.id;
  dialog("Add a document","Reuse a document key for a corrected version. Identical content is not queued twice.",[{name:"key",label:"Stable document key (for example INV-001)"},{name:"file",label:"PDF document",type:"file"}],"Queue document",async d=>{await api(`/api/cases/${caseId}/documents?document_key=${encodeURIComponent(d.key)}&filename=${encodeURIComponent(d.file.name)}`,{method:"POST",headers:{"Content-Type":"application/pdf"},body:d.file});});
};
$("correct-field").onclick=()=>{
  if(!canCorrectDocument()||!selectedField||selectedField.documentId!==currentDocument.id||selectedField.revision!==currentDocument.revision) return;
  const {id,revision}=currentDocument, {key,field}=selectedField;
  dialog("Record a field correction","The extracted value and its evidence remain in the audit history. A different approver must accept the corrected dossier.",[{name:"value",label:"Corrected value",value:field.normalized||""},{name:"reason",label:"Justification",type:"textarea"}],"Record correction",async(d,active)=>{await post(`/api/documents/${id}/corrections`,{...d,field:key,expected_revision:revision});if(active()&&selectedDocumentId===id)await loadDocument(id);});
};
$("correct-kind").onclick=()=>{
  if(!canCorrectDocument()) return;
  const {id,revision,extraction}=currentDocument;
  dialog("Review document type","Inspect the original before choosing its type. The original model proposal is retained and another approver must accept this human decision.",[{name:"kind",label:"Reviewed document type",type:"select",options:["purchase_order","delivery_note","invoice","unknown"],value:extraction.kind},{name:"reason",label:"Justification",type:"textarea"}],"Record type decision",async(d,active)=>{await post(`/api/documents/${id}/classification-review`,{...d,expected_revision:revision});if(active()&&selectedDocumentId===id)await loadDocument(id);});
};
$("accept-case").onclick=()=>{
  if(!can("approver")||!currentCase?.eligible_for_acceptance||currentCase.accepted) return;
  const {id,revision}=currentCase;
  dialog("Accept this revision","Confirm that you have reviewed the current originals, supported fields and reconciliation. This action does not publish a result.",[{name:"reason",label:"Acceptance reason",type:"textarea"}],"Accept revision",async d=>{await post(`/api/cases/${id}/accept`,{...d,expected_revision:revision});});
};
$("publish-case").onclick=()=>{
  if(!can("publisher")||!currentCase?.accepted||currentCase.published) return;
  const {id,revision}=currentCase;
  dialog("Publish the accepted result","The exported control dossier will bind the accepted document versions, corrections and decision history.",[],"Publish",async()=>{await post(`/api/cases/${id}/publish`,{expected_revision:revision});});
};
$("export-case").onclick=async()=>{
  if(!actor||!currentCase?.published) return;
  const {id}=currentCase, session=sessionGeneration;
  try {const blob=await api(`/api/cases/${id}/export.zip`,{binary:true});if(session!==sessionGeneration)return;const url=URL.createObjectURL(blob),a=node("a");a.href=url;a.download=`control-dossier-${id}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){if(session===sessionGeneration&&selectedCaseId===id)notice(e.message,true);}
};
setInterval(()=>{if(token && !$("dialog").open)refresh();},5000);
$("new-case").disabled=true;
clearCase();
if(token)connect();
