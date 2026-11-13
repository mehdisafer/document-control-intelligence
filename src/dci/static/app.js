"use strict";
const $ = id => document.getElementById(id);
let token = sessionStorage.getItem("dci-token") || "";
let actor = null, currentCase = null, currentDocument = null, selectedField = null, originalUrl = null;
function node(tag, text, cls) { const n = document.createElement(tag); if(text !== undefined) n.textContent = text; if(cls) n.className = cls; return n; }
function notice(text, error = false) { $("notice").textContent = text; $("notice").hidden = !text; $("notice").classList.toggle("error", error); }
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
  actor = await api("/api/me"); sessionStorage.setItem("dci-token", token);
  $("actor-name").textContent = actor.name; $("actor-roles").textContent = actor.roles.join(" · ");
  $("login-panel").hidden = true; $("workspace").hidden = false; $("new-case").disabled = !can("operator");
  $("correct-field").disabled = !can("operator");
  $("correct-kind").disabled = true;
  notice(""); await refresh();
}
$("login-form").onsubmit = async event => { event.preventDefault(); token = $("token").value.trim(); try { await connect(); $("token").value = ""; } catch(e) { notice(e.message, true); } };
$("switch-actor").onclick = () => { currentDocument=null; selectedField=null; $("review").hidden=true; $("correct-field").disabled=true; $("correct-kind").disabled=true; $("new-case").disabled=true; if(originalUrl)URL.revokeObjectURL(originalUrl); originalUrl=null; $("original-frame").removeAttribute("src"); $("original-download").removeAttribute("href"); sessionStorage.removeItem("dci-token"); token = ""; actor = null; $("login-panel").hidden = false; $("workspace").hidden = true; $("actor-name").textContent = "Not connected"; $("actor-roles").textContent = ""; $("token").focus(); };
function findingNodes(findings) { const fragment = document.createDocumentFragment(); for (const f of findings) { const n = node("div", undefined, `finding ${f.severity}`); n.append(node("span", f.code, "code"), node("span", f.message)); fragment.append(n); } return fragment; }
async function refresh() {
  if(!token) return;
  try {
    const [cases, ready] = await Promise.all([api("/api/cases"), api("/api/ready")]);
    $("case-count").textContent = cases.length; $("metric-cases").textContent = cases.length;
    $("metric-pending").textContent = (ready.queue.jobs.queued||0)+(ready.queue.jobs.running||0);
    $("metric-published").textContent = ready.queue.publications;
    $("case-list").replaceChildren();
    for (const c of cases) { const row=node("button",undefined,`case-row ${currentCase?.id===c.id?"active":""}`); row.append(node("strong",c.name),node("small",`${c.published_fingerprint?"Published":c.accepted_fingerprint?"Accepted":"In review"} · ${stamp(c.created_at)}`)); row.onclick=()=>loadCase(c.id).catch(e=>notice(e.message,true)); $("case-list").append(row); }
    if(currentCase) await loadCase(currentCase.id, false); else if(cases.length) await loadCase(cases[0].id);
  } catch(e) { notice(e.message, true); }
}
$("refresh").onclick = refresh; $("reload").onclick = refresh;
async function loadCase(id, reset = true) {
  if(reset && currentCase?.id !== id) { currentDocument = null; selectedField = null; $("review").hidden=true; }
  currentCase = await api(`/api/cases/${id}`);
  $("empty").hidden=true; $("case-detail").hidden=false;
  $("case-name").textContent=currentCase.name; $("case-revision").textContent=`Revision ${currentCase.revision} · ${currentCase.documents.length} current documents`;
  const status=currentCase.published?"published":currentCase.accepted?"accepted":currentCase.reconciliation.status;
  $("case-status").textContent=title(status); $("case-status").className=`badge ${status}`;
  $("reconciliation").replaceChildren(findingNodes(currentCase.reconciliation.findings));
  $("upload-document").disabled=!can("operator"); $("accept-case").disabled=!can("approver")||!currentCase.eligible_for_acceptance||currentCase.accepted;
  $("publish-case").disabled=!can("publisher")||!currentCase.accepted||currentCase.published; $("export-case").disabled=!currentCase.published;
  $("acceptance-note").textContent=currentCase.accepted?`Accepted by ${currentCase.accepted_by}. Any correction or new document version requires a new acceptance.`:"Viewing a dossier does not approve it. Acceptance and publication are explicit actions.";
  $("document-list").replaceChildren();
  for(const d of currentCase.documents) { const b=node("button",undefined,`doc-row ${d.id===currentDocument?.id?"active":""}`); const label=node("span",undefined,"doc-name"); label.append(node("strong",d.filename),node("small",`${d.document_key} · Version ${d.version} · Revision ${d.revision}`)); b.append(node("span","PDF","pdf-icon"),label,node("span",title(d.status),"small-badge")); b.onclick=()=>loadDocument(d.id).catch(e=>notice(e.message,true)); $("document-list").append(b); }
  const history=await api(`/api/cases/${id}/audit`); $("audit-list").replaceChildren();
  for(const event of history.slice().reverse()) { const entry=node("div",undefined,"audit-entry"), text=node("div",undefined,"audit-text"); text.append(node("b",`${event.actor} · ${event.action.replaceAll("."," ")}`)); let detail=event.details.justification||event.details.reason||event.details.error_code||""; if(event.action==="classification.reviewed") detail=`${title(event.details.old_kind)} → ${title(event.details.new_kind)} · ${detail}`; if(event.action==="field.corrected") detail=`${event.details.field}: ${event.details.old.normalized??"—"} → ${event.details.new.normalized} · ${detail}`; text.append(node("small",detail)); entry.append(node("time",stamp(event.at),"audit-time"),text); $("audit-list").append(entry); }
  if(currentDocument) {
    const latest=currentCase.documents.find(d=>d.id===currentDocument.id);
    if(!latest) { currentDocument=null; selectedField=null; $("review").hidden=true; }
    else if(reset || latest.revision!==currentDocument.revision || latest.status!==currentDocument.status) await loadDocument(currentDocument.id);
  }
}
async function loadDocument(id) {
  currentDocument=await api(`/api/documents/${id}`); $("review").hidden=false; $("evidence").hidden=true; selectedField=null;
  const d=currentDocument, x=d.extraction; $("extraction-profile").textContent=x?.profile||d.profile;
  $("document-status").textContent=x?`${title(x.kind)} · ${x.model_version} · ${d.current?"Current version":"Historical version"}`:`${title(d.status)}${d.error_code?" · "+d.error_code:""}`;
  $("correct-kind").disabled=!can("operator")||!d.current||d.status!=="ready"||!x;
  const proposal=d.classification_proposal, review=d.classification_review;
  $("classification-review").textContent=review?`Human type decision: ${title(review.new_kind)} · ${review.actor} · ${stamp(review.at)}. Original model proposal: ${title(proposal?.kind||"unknown")}. Reason: ${review.reason}`:proposal?`Model type proposal: ${title(proposal.kind)} · score ${Number(proposal.confidence).toFixed(3)}. A score does not replace source review.`:"";
  $("document-findings").replaceChildren(findingNodes(d.checks?.findings||[])); $("field-rows").replaceChildren(); $("line-items").replaceChildren();
  if(x) { for(const [key,f] of Object.entries(x.fields)) fieldRow($("field-rows"),key,f); x.line_items.forEach((line,index)=>{ const section=node("section"); section.append(node("h3",`Line item ${index+1}`,"line-heading")); const table=node("table"), body=node("tbody"); Object.entries(line.fields).forEach(([key,f])=>fieldRow(body,`line_items.${index}.${key}`,f)); table.append(body); section.append(table); $("line-items").append(section); }); }
  if(originalUrl) URL.revokeObjectURL(originalUrl); originalUrl=null; $("original-frame").removeAttribute("src"); $("original-download").removeAttribute("href");
  if(d.parsed) { const blob=await api(`/api/documents/${id}/original`,{binary:true}); originalUrl=URL.createObjectURL(blob); $("original-frame").src=originalUrl; $("original-download").href=originalUrl; $("original-message").textContent=`${d.parsed.pages.length} page(s) · ${d.parsed.pages.map(p=>`p${p.number}: ${p.method}`).join(" · ")}`; }
  else { $("original-message").textContent="Preview becomes available after document inspection."; }
}
function fieldRow(body,key,field) { const row=node("tr"); row.append(node("td",title(key.split(".").at(-1))),node("td",field.normalized??"—")); const td=node("td");td.append(node("span",title(field.status),`field-state ${field.status}`));row.append(td);row.tabIndex=0;row.onclick=()=>selectField(key,field,row);row.onkeydown=e=>{if(e.key==="Enter")selectField(key,field,row)};body.append(row); }
function selectField(key,field,row) {
  document.querySelectorAll("tr.selected").forEach(n=>n.classList.remove("selected"));row.classList.add("selected");selectedField={key,field};$("evidence").hidden=false;$("evidence-field").textContent=title(key);
  const evidence=field.evidence.at(-1);$("evidence-meta").textContent=evidence?`Page ${evidence.page} · Text ${evidence.start}–${evidence.end}${evidence.bbox?" · Box "+evidence.bbox.map(n=>n.toFixed(1)).join(", ")+" pt":""}`:"No supported source span. This field requires review.";
  $("evidence-quote").replaceChildren();
  for(const citation of field.evidence) { const page=currentDocument.parsed.pages.find(p=>p.number===citation.page);const before=page.text.slice(Math.max(0,citation.start-45),citation.start),after=page.text.slice(citation.end,citation.end+45);$("evidence-quote").append(document.createTextNode(`Page ${citation.page} · source ${citation.start}–${citation.end}\n`),document.createTextNode(before),node("mark",citation.quote),document.createTextNode(after+"\n\n")); }
  if(evidence && originalUrl)$("original-frame").src=`${originalUrl}#page=${evidence.page}`;
  $("evidence-transforms").textContent=`Raw: ${field.raw??"absent"}. ${field.transformations.join(" → ")||"No transformation"}.${field.origin==="human"?" Human correction; the original quoted value is retained for audit.":""}${field.reason?" "+field.reason:""}`;
  $("correct-field").disabled=!can("operator")||!currentDocument.current;
}
function dialog(titleText,note,fields,submitLabel,onSubmit) {
  $("dialog-title").textContent=titleText;$("dialog-note").textContent=note;$("dialog-submit").textContent=submitLabel;$("dialog-fields").replaceChildren();
  for(const spec of fields) { const label=node("label",spec.label);label.htmlFor=`dialog-${spec.name}`;const input=node(spec.type==="textarea"?"textarea":spec.type==="select"?"select":"input");input.id=`dialog-${spec.name}`;input.name=spec.name;input.required=spec.required!==false;if(!["textarea","select"].includes(spec.type))input.type=spec.type||"text";if(spec.type==="select")for(const value of spec.options){const option=node("option",title(value));option.value=value;input.append(option);}if(spec.type==="file")input.accept="application/pdf";else input.value=spec.value||"";input.maxLength=spec.name==="reason"?1000:200;$("dialog-fields").append(label,input); }
  $("dialog-form").onsubmit=async event=>{event.preventDefault();const data={};for(const spec of fields){const input=$(`dialog-${spec.name}`);data[spec.name]=spec.type==="file"?input.files[0]:input.value;}$("dialog-submit").disabled=true;try{await onSubmit(data);$("dialog").close();notice("");await refresh();}catch(e){notice(e.message,true);}finally{$("dialog-submit").disabled=false;}};
  $("dialog").showModal();
}
$("dialog-cancel").onclick=()=>$("dialog").close();
$("new-case").onclick=()=>dialog("New control dossier","Group one purchase order with its delivery notes and invoices.",[{name:"name",label:"Dossier name"}],"Create",async d=>{currentCase=await post("/api/cases",d);currentDocument=null;$("review").hidden=true;});
$("upload-document").onclick=()=>dialog("Add a document","Reuse a document key for a corrected version. Identical content is not queued twice.",[{name:"key",label:"Stable document key (for example INV-001)"},{name:"file",label:"PDF document",type:"file"}],"Queue document",async d=>{await api(`/api/cases/${currentCase.id}/documents?document_key=${encodeURIComponent(d.key)}&filename=${encodeURIComponent(d.file.name)}`,{method:"POST",headers:{"Content-Type":"application/pdf"},body:d.file});});
$("correct-field").onclick=()=>dialog("Record a field correction","The extracted value and its evidence remain in the audit history. A different approver must accept the corrected dossier.",[{name:"value",label:"Corrected value",value:selectedField.field.normalized||""},{name:"reason",label:"Justification",type:"textarea"}],"Record correction",async d=>{await post(`/api/documents/${currentDocument.id}/corrections`,{...d,field:selectedField.key,expected_revision:currentDocument.revision});await loadDocument(currentDocument.id);});
$("correct-kind").onclick=()=>dialog("Review document type","Inspect the original before choosing its type. The original model proposal is retained and another approver must accept this human decision.",[{name:"kind",label:"Reviewed document type",type:"select",options:["purchase_order","delivery_note","invoice","unknown"],value:currentDocument.extraction.kind},{name:"reason",label:"Justification",type:"textarea"}],"Record type decision",async d=>{await post(`/api/documents/${currentDocument.id}/classification-review`,{...d,expected_revision:currentDocument.revision});await loadDocument(currentDocument.id);});
$("accept-case").onclick=()=>dialog("Accept this revision","Confirm that you have reviewed the current originals, supported fields and reconciliation. This action does not publish a result.",[{name:"reason",label:"Acceptance reason",type:"textarea"}],"Accept revision",async d=>{await post(`/api/cases/${currentCase.id}/accept`,{...d,expected_revision:currentCase.revision});});
$("publish-case").onclick=()=>dialog("Publish the accepted result","The exported control dossier will bind the accepted document versions, corrections and decision history.",[],"Publish",async()=>{await post(`/api/cases/${currentCase.id}/publish`,{expected_revision:currentCase.revision});});
$("export-case").onclick=async()=>{try{const blob=await api(`/api/cases/${currentCase.id}/export.zip`,{binary:true}),url=URL.createObjectURL(blob),a=node("a");a.href=url;a.download=`control-dossier-${currentCase.id}.zip`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){notice(e.message,true);}};
setInterval(()=>{if(token && !$("dialog").open)refresh();},5000);
$("new-case").disabled=true;
if(token)connect().catch(e=>{sessionStorage.removeItem("dci-token");notice(e.message,true);});
