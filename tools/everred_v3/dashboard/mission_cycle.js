"use strict";
(() => {
  const byId = (id) => document.getElementById(id);
  const element = (tag, cls, text) => {
    const x = document.createElement(tag);
    if (cls) x.className = cls;
    if (text !== undefined) x.textContent = text;
    return x;
  };
  const add = (parent, tag, cls, text) => {
    const x = element(tag, cls, text);
    parent.appendChild(x);
    return x;
  };
  const parsed = JSON.parse(byId("guidance").textContent);
  if (parsed.schema !== "abacus.everred.mission-guidance.v1" ||
      parsed.merge_authorized !== false ||
      parsed.authority_transfer !== false ||
      parsed.security_waiver !== false ||
      !Array.isArray(parsed.stages) || !parsed.cards) {
    byId("count").textContent = "INVALID SOURCE CONTRACT: ADMISSION HOLD";
    return;
  }
  const icons = ["Target", "Plan", "Observe", "Verify", "Assign", "Repeat"];
  parsed.stages.forEach((stage, index) => {
    if (index) add(byId("cycle"), "span", "arrow", "→");
    const box = add(byId("cycle"), "div", "stage");
    add(box, "strong", "", stage);
    add(box, "small", "", icons[index] || "Evidence");
  });
  const makeDetails = (parent, label) => {
    const d = add(parent, "details");
    add(d, "summary", "", label);
    return d;
  };
  const options = (control, entries, selected) => {
    entries.forEach((x) => {
      const opt = add(control, "option", "", x);
      opt.value = x;
    });
    control.value = selected;
  };
  const cards = Object.entries(parsed.cards);
  function buildCard(id, g) {
    const card = element("article", "card");
    card.dataset.hard = String(g.priority_policy === "P0_HARD_GATE_FIRST");
    const top = add(card, "div", "top");
    const p = add(top, "button", "pbtn " + g.p.toLowerCase(), g.p);
    p.type = "button";
    p.setAttribute("aria-label", "Open priority and decision for " + id);
    const name = add(top, "button", "titlebtn", id);
    name.type = "button";
    const metrics = add(card, "div", "metricrow");
    const display = (value) => value === null || value === undefined ? "UNKNOWN" : String(value);
    add(metrics, "span", "metric" + (g.p === "P0" ? " w" : ""), g.priority_policy);
    add(metrics, "span", "metric", "PCA " + display(g.pca_component));
    add(metrics, "span", "metric", "BT " + display(g.bt_rank));
    add(metrics, "span", "metric", "RP " + display(g.reverse_pressure));
    add(metrics, "span", "metric", "Unlock " + display(g.unlock_yield_pct) +
        (g.unlock_yield_pct === null ? "" : "%"));
    const decision = makeDetails(card, "Decision — why / unlock / next");
    const line = (label, value) => {
      const row = add(decision, "div", "mini");
      add(row, "span", "stepname", label);
      add(row, "span", "", value);
    };
    line("Why this ranks", g.why_this_ranks);
    line("What it unblocks", g.what_it_unblocks);
    line("Next action", g.next_action);
    const selection = add(decision, "div", "row");
    const left = add(selection, "div");
    const label = add(left, "label", "", "Decision");
    const response = add(left, "select");
    response.id = "decision-" + id;
    label.htmlFor = response.id;
    options(response, ["Pending", "Yes", "No"], "Pending");
    const right = add(selection, "div");
    const pLabel = add(right, "label", "", "Proposed priority");
    const proposal = add(right, "select");
    proposal.id = "proposed-" + id;
    pLabel.htmlFor = proposal.id;
    options(proposal, ["P0", "P1", "P2", "P3"], g.p);
    const commentBlock = add(decision, "div", "comment");
    const cLabel = add(commentBlock, "label", "", "Comment / justification");
    const comment = add(commentBlock, "textarea");
    comment.id = "comment-" + id;
    comment.placeholder = "Optional, no GitHub mutation";
    cLabel.htmlFor = comment.id;
    const cta = add(decision, "div", "cta");
    const save = add(cta, "button", "", "Prepare decision record");
    save.type = "button";
    const feedback = add(cta, "span", "minor", "Local only · no merge approval");
    const output = add(decision, "pre", "output", "");
    output.hidden = true;
    save.addEventListener("click", () => {
      const record = {
        schema: "code-purple.operator-decision.v1",
        family_id: id,
        observed_priority: g.p,
        proposed_priority: proposal.value,
        decision: response.value.toUpperCase(),
        comment: comment.value,
        required_action: g.next_action,
        unlock_status: g.unlock_status,
        unlock_yield_pct: g.unlock_yield_pct,
        proof: "UNVERIFIED_LOCAL_PROPOSAL",
        disposition: "DRAFT_NOT_SUBMITTED",
        admission: "HOLD",
        authority_transfer: false
      };
      const text = JSON.stringify(record, null, 2);
      output.textContent = text;
      output.hidden = false;
      feedback.textContent = "Prepared, not sent";
    });
    const deeper = makeDetails(card, "Method / DoV / source evidence");
    line.call(null, "", "");
    add(deeper, "p", "minor", "PCA readiness: " + g.pca_readiness +
        " · BT readiness: " + g.bt_readiness +
        " · Unlock evidence: " + g.unlock_status);
    add(deeper, "p", "mini", "DoV: " + g.dov);
    const link = add(deeper, "a", "minor", "Native evidence leaves in BD queue");
    link.href = "bd_queue.html#" + encodeURIComponent(id);
    p.addEventListener("click", () => { decision.open = !decision.open; });
    name.addEventListener("click", () => { decision.open = !decision.open; });
    return card;
  }
  function render() {
    const q = byId("find").value.trim().toLowerCase();
    const prio = byId("filter").value;
    const visible = cards.filter(([id, g]) =>
      (prio === "ALL" || prio === g.p) &&
      JSON.stringify({id, ...g}).toLowerCase().includes(q));
    byId("cards").replaceChildren();
    visible.forEach(([id, g]) => byId("cards").appendChild(buildCard(id, g)));
    byId("count").textContent = visible.length + "/" + cards.length +
      " BD families · all local decisions unsubmitted · release HOLD";
  }
  byId("find").addEventListener("input", render);
  byId("filter").addEventListener("change", render);
  render();
})();
