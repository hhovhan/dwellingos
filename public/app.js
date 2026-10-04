let records = [];
let system = null;
const search = document.querySelector('#search');
const matches = document.querySelector('#matches');
const passport = document.querySelector('#passport');
const asOf = document.querySelector('#as-of');
let active = null;
let bostonProgram = 'unknown';
let newarkRentStatus = 'unknown';
let sfRentStatus = 'unknown';
let sanDiegoSharedFacilities = 'unknown';
let changeContext = null;
const scenarioFacts = () => ({
  DND_or_BPDA_program_participation: bostonProgram,
  rent_control_status: active?.legal_city === 'San Francisco' ? sfRentStatus : newarkRentStatus,
  owner_occupied_shared_kitchen_or_bath: sanDiegoSharedFacilities
});

async function loadPassports() {
  const manifestResponse = await fetch('passports-manifest.json');
  if (manifestResponse.ok) {
    const manifest = await manifestResponse.json();
    const chunks = await Promise.all(manifest.chunks.map(async name => {
      const response = await fetch(name);
      if (!response.ok) throw new Error(`Passport chunk unavailable: ${name}`);
      return response.json();
    }));
    const passports = chunks.flatMap(chunk => chunk.passports);
    if (passports.length !== manifest.count) throw new Error('Passport count does not match manifest');
    return {passports};
  }
  const response = await fetch('passports.json');
  if (!response.ok) throw new Error('Passport data unavailable');
  return response.json();
}

Promise.all([loadPassports(), fetch('system.json').then(response => response.json())])
  .then(([data, status]) => {
    records = data.passports;
    system = status;
    renderMetrics();
    renderChanges();
    renderCoverage();
    if (search.value.trim()) search.dispatchEvent(new Event('input'));
  }).catch(error => {
    document.querySelector('#metrics').innerHTML = `<p class="error">Data pipeline unavailable: ${esc(error.message)}</p>`;
  });

const esc = value => String(value ?? 'Missing').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));

function renderList(items) {
  matches.innerHTML = items.length ? items.map(item => `<button data-id="${item.id}"><b>${esc(item.address)}</b><span>${esc(item.postal_city)}, ${item.state} · ${item.id}</span></button>`).join('') : '<p class="no-results">No property found in the 500-record sample. Check the address or ID.</p>';
}

function categoryAnswer(group) {
  const values = group.rules.map(rule => rule.displayResult);
  const current = values.includes('applies');
  const unresolved = values.includes('unknown');
  const applicable = group.rules.find(rule => rule.displayResult === 'applies');
  const unknown = group.rules.find(rule => rule.displayResult === 'unknown' && rule.key_value) || group.rules.find(rule => rule.displayResult === 'unknown');
  const future = group.rules.find(rule => ['pending','not_yet_effective'].includes(rule.displayResult));
  const explain = rule => {
    const sourceText = rule.requirement || '';
    const cleanTitle = rule.title.includes(' | ') ? rule.citation : rule.title;
    const detail = rule.key_value || (sourceText.includes(' | ') || sourceText.startsWith('An eviction is') || sourceText.startsWith('Bill Text') || /^\([a-z0-9]+\) Notwithstanding/i.test(sourceText) ? cleanTitle : sourceText) || cleanTitle;
    return detail.length > 145 ? `${detail.slice(0,142).trimEnd()}…` : detail;
  };
  const missing = rule => rule?.displayDecision?.missing_coverage_facts?.map(fact => fact.replaceAll('_',' ')).join(', ');
  if (!values.length) return ['No source record', 'No matched source in this corpus; further source review is needed.', null];
  if (current && unresolved) return ['Partly confirmed', `${explain(applicable)} Other coverage needs ${missing(unknown) || 'property facts'}.`, applicable];
  if (current) return ['Applies', explain(applicable), applicable];
  if (unresolved) return ['Needs facts', explain(unknown), unknown];
  if (future) return ['Upcoming or proposed', `The captured ${humanize(group.category).toLowerCase()} rule is not current law on this date.`, future];
  return ['No current matched rule', 'Matched records are excluded or displaced by another rule.', group.rules[0]];
}

function decisionBrief(item, groups) {
  if (item.legal_city === 'Newark' && newarkRentStatus !== 'unknown') {
    const rule = groups.flatMap(group => group.rules).find(candidate => candidate.decision_table?.scenario_field === 'rent_control_status' && candidate.key_value);
    if (rule) return `<div class="decision-brief"><div><span>HYPOTHETICAL RESULT</span><strong>${esc(newarkRentStatus === 'covered' ? rule.key_value : 'Newark 4% ceiling excluded for this scenario')}</strong><p>${esc(rule.citation)} · ${esc(rule.displayDecision.result.replaceAll('_',' '))} only under the selected assumption.</p></div><div><span>REAL-WORLD NEXT ACTION</span><strong>Verify rent control status</strong><p>The actual sample record still lacks this fact. Check city records before applying this result.</p><button type="button" data-verify-control="newark-rent-fact">Change the assumption ↗</button></div></div>`;
  }
  const unresolved = groups.flatMap(group => group.rules.map(rule => ({...rule, category:group.category})))
    .filter(rule => rule.displayResult === 'unknown' && rule.displayDecision.missing_coverage_facts?.length);
  const priority = unresolved.find(rule => rule.key_value && rule.jurisdiction?.includes(item.legal_city))
    || unresolved.find(rule => rule.key_value) || unresolved[0];
  if (!priority) return '<p class="decision-brief-note">No coverage-fact action is available for this address on this date. Inspect the source evidence below.</p>';
  const field = priority.displayDecision.missing_coverage_facts[0];
  const name = field.replaceAll('_',' ');
  const value = priority.key_value || priority.title;
  const control = field === 'rent_control_status' && item.legal_city === 'Newark' ? 'newark-rent-fact'
    : field === 'rent_control_status' && item.legal_city === 'San Francisco' ? 'sf-rent-fact'
    : field === 'DND_or_BPDA_program_participation' && item.legal_city === 'Boston' ? 'program-fact'
    : field === 'owner_occupied_shared_kitchen_or_bath' && item.legal_city === 'San Diego' ? 'sd-shared-fact' : '';
  return `<div class="decision-brief"><div><span>WHAT WE KNOW</span><strong>${esc(value)}</strong><p>${esc(priority.citation)} · ${esc(humanize(priority.category))}. This is a conditional rule, not a confirmed limit for this building.</p></div><div><span>NEXT OPERATOR ACTION</span><strong>Verify ${esc(name)}</strong><p>Check the property record or responsible authority. Until this fact is verified, coverage stays unknown.</p>${control ? `<button type="button" data-verify-control="${control}">Explore a hypothetical fact ↗</button>` : `<button type="button" data-open-evidence="true">Inspect evidence gap ↗</button>`}</div></div>`;
}

function changeSpotlight(item) {
  if (!changeContext || !system?.change_tests[changeContext]) return '';
  const spec = {
    T1: {label:'California algorithmic rent rule', before:'2025-12-31', after:'2026-01-02', rule:'CA-ALG-01'},
    T3: {label:'New Jersey FAIR Act', before:'2026-10-01', after:'2027-07-02', rule:'NJ-ALG-01'},
  }[changeContext];
  if (!spec) return `<aside class="change-spotlight"><strong>${esc(changeContext)} · ${esc(item.id)}</strong><p>${esc(system.change_tests[changeContext].notes)}</p><p>Property coverage and legal conflicts still require review.</p></aside>`;
  const rule = item.rules.find(value => value.team_rule_id === spec.rule);
  if (!rule) return '';
  const before = scenarioDecision(rule, spec.before).result.replaceAll('_',' ');
  const after = scenarioDecision(rule, spec.after).result.replaceAll('_',' ');
  return `<aside class="change-spotlight"><strong>${esc(spec.label)} · ${esc(item.id)}</strong><p>${esc(spec.before)}: ${esc(before)} → ${esc(spec.after)}: ${esc(after)}.</p><p>${esc(rule.citation)} · Building-level coverage may still need facts.</p><button type="button" data-show-change-date="${esc(spec.after)}">Show after date in passport</button></aside>`;
}

function dateSpotlight(item, date) {
  if (item.id !== 'A0001' || !['2025-12-31','2026-01-02'].includes(date)) return '';
  const rule = item.rules.find(value => value.team_rule_id === 'CA-ALG-01');
  if (!rule) return '';
  const before = scenarioDecision(rule, '2025-12-31').result.replaceAll('_',' ');
  const after = scenarioDecision(rule, '2026-01-02').result.replaceAll('_',' ');
  const target = date === '2025-12-31' ? '2026-01-02' : '2025-12-31';
  return `<aside class="change-spotlight"><strong>WATCH THE DATE CHANGE THE ANSWER</strong><p>Dec 31: ${esc(before)} → Jan 2: ${esc(after)} · ${esc(rule.citation)}</p><button type="button" data-show-change-date="${target}">Show ${target === '2026-01-02' ? 'after' : 'before'} date ↗</button></aside>`;
}

function renderPassport(item) {
  if (!item) return;
  const jurisdictionChanged = item.postal_city !== item.legal_city;
  const date = asOf.validity.valid && asOf.value ? asOf.value : '2026-10-01';
  const groups = item.categories.map(group => ({...group, rules: group.rules.map(rule => {
    const displayDecision = scenarioDecision(rule, date);
    return {...rule, displayDecision, displayResult: displayDecision.result};
  })}));
  const decisions = groups.flatMap(group => group.rules);
  const counts = Object.fromEntries(['applies', 'unknown', 'pending', 'not_yet_effective', 'excluded', 'superseded'].map(key => [key, decisions.filter(rule => rule.displayResult === key).length]));
  const hypothetical = [bostonProgram,newarkRentStatus,sfRentStatus,sanDiegoSharedFacilities].some(value => value !== 'unknown');
  passport.classList.remove('hidden');
  passport.innerHTML = `
    <div class="demo-switcher" aria-label="Demo scenes"><span>DEMO PATH</span><button type="button" data-demo-step="1">01 · UNKNOWN</button><button type="button" data-demo-step="2">02 · CITY</button><button type="button" data-demo-step="3">03 · DATE</button><button type="button" data-demo-step="4">04 · IMPACT</button></div>
    <header><div><p class="eyebrow">${esc(item.id)} · SCENARIO ${esc(date)}</p><h2>${esc(item.address)}</h2><p>${esc(item.legal_city)}, ${esc(item.state)} ${esc(item.zip)}</p></div><span class="status">EVIDENCE PASSPORT</span></header>
    <div class="answer-lead"><strong>${counts.applies} supported rule${counts.applies === 1 ? '' : 's'} apply · ${counts.unknown} need coverage checks</strong><p>For ${esc(date)}, these decisions use the supplied corpus and provisional sample city assignment. Missing property facts remain unresolved.</p></div>
    ${hypothetical ? '<p class="hypothetical-warning">Hypothetical fact selected for demonstration. This property fact has not been verified or saved.</p>' : ''}
    ${decisionBrief(item,groups)}
    ${changeSpotlight(item)}
    ${dateSpotlight(item,date)}
    <p class="jurisdiction-caution">${item.zip_state_conflict ? 'Address conflict: ZIP and state disagree. ' : ''}${jurisdictionChanged ? 'Mailing city maps through a sample alias. ' : ''}${item.geocoder?.status === 'matched' ? `Census address-range match: ${esc(item.geocoder.legal_city)}. ` : `Census geography unresolved (${esc(item.geocoder?.status || 'not checked')}). `}City-law matches are provisional: parcel-level municipal boundary has not been verified.</p>
    <div class="answer-grid" aria-label="Six-category answer">${groups.map(group => { const [label,reason,source] = categoryAnswer(group); const missing = source?.displayResult === 'unknown' ? source.displayDecision.missing_coverage_facts?.join(', ').replaceAll('_',' ') : ''; return `<article><span class="result result-${esc(source?.displayResult || 'unknown')}">${esc(label)}</span><strong>${esc(humanize(group.category))}</strong><p>${esc(reason)}</p>${missing ? `<p class="card-next"><b>To decide:</b> verify ${esc(missing)}.</p>` : ''}${source ? `<p><a href="${esc(source.source_url)}" target="_blank" rel="noreferrer">Source: ${esc(source.citation)} ↗</a></p>` : ''}</article>`; }).join('')}</div>
    ${item.legal_city === 'Boston' ? `<div class="scenario-control"><label for="program-fact">What if this property is in a DND/BPDA housing program?</label><select id="program-fact"><option value="unknown" ${bostonProgram === 'unknown' ? 'selected' : ''}>Unknown</option><option value="yes" ${bostonProgram === 'yes' ? 'selected' : ''}>Yes, supported by evidence</option><option value="no" ${bostonProgram === 'no' ? 'selected' : ''}>No, supported by evidence</option></select><p class="caption">Temporary scenario; the sample record is unchanged.</p></div>` : ''}
    ${item.legal_city === 'Newark' ? `<div class="scenario-control"><label for="newark-rent-fact">What if this unit is covered by Newark rent control?</label><select id="newark-rent-fact"><option value="unknown" ${newarkRentStatus === 'unknown' ? 'selected' : ''}>Unknown — verify city records</option><option value="covered" ${newarkRentStatus === 'covered' ? 'selected' : ''}>Hypothetically covered</option><option value="exempt" ${newarkRentStatus === 'exempt' ? 'selected' : ''}>Hypothetically exempt</option></select><p class="caption">Temporary, unsaved scenario; registration and compliance need separate review.</p></div>` : ''}
    ${item.legal_city === 'San Francisco' ? `<div class="scenario-control"><label for="sf-rent-fact">Is this unit covered by San Francisco rent control?</label><select id="sf-rent-fact"><option value="unknown" ${sfRentStatus === 'unknown' ? 'selected' : ''}>Unknown — verify Rent Board coverage</option><option value="covered" ${sfRentStatus === 'covered' ? 'selected' : ''}>Covered, supported by evidence</option><option value="exempt" ${sfRentStatus === 'exempt' ? 'selected' : ''}>Exempt, supported by evidence</option></select><p class="caption">Temporary scenario; actual building coverage is unverified.</p></div>` : ''}
    ${item.legal_city === 'San Diego' ? `<div class="scenario-control"><label for="sd-shared-fact">Does the owner or family share a kitchen or bathroom with the tenant?</label><select id="sd-shared-fact"><option value="unknown" ${sanDiegoSharedFacilities === 'unknown' ? 'selected' : ''}>Unknown</option><option value="no" ${sanDiegoSharedFacilities === 'no' ? 'selected' : ''}>No, supported by evidence</option><option value="yes" ${sanDiegoSharedFacilities === 'yes' ? 'selected' : ''}>Yes, supported by evidence</option></select><p class="caption">Temporary scenario; the sample record is unchanged.</p></div>` : ''}
    <details class="evidence-drawer" id="evidence"><summary>Inspect property facts, gaps and full rule evidence</summary>
    <div class="decision-overview" aria-label="Decision overview"><div><strong>${counts.applies}</strong><span>supported as applicable</span></div><div><strong>${counts.unknown}</strong><span>need coverage facts</span></div><div><strong>${counts.pending + counts.not_yet_effective}</strong><span>not current law</span></div><div><strong>${counts.superseded + counts.excluded}</strong><span>superseded or excluded</span></div></div>
    <p class="caption">These counts describe matched source records, not a legal clearance or a count of all applicable laws.</p>
    ${jurisdictionChanged ? `<div class="notice">Mailing city <b>${esc(item.postal_city)}</b> maps to <b>${esc(item.legal_city)}</b> using a reviewed sample alias. The municipal boundary still needs independent verification.</div>` : ''}
    ${item.zip_state_conflict ? '<div class="notice danger-notice"><b>Address conflict:</b> the supplied ZIP prefix does not match the supplied state. The location and city-specific conclusions must be verified independently before relying on this passport.</div>' : ''}
    ${item.city_boundary_needs_verification ? '<div class="notice">City is taken from the sample property record. A mapped municipal boundary is still needed before relying on city-specific conclusions.</div>' : ''}
    <div class="facts">
      ${fact('Year built', item.year_built)}${fact('Units', item.units)}${fact('Use code', item.use_code)}${fact('Source', item.source)}
    </div>
    ${item.geocoder?.geocoder_url ? `<p class="caption"><a href="${esc(item.geocoder.geocoder_url)}" target="_blank" rel="noreferrer">Inspect Census geocoder evidence ↗</a> · Address-range match, not parcel-level proof.</p>` : ''}
    <h3>Evidence gaps</h3>
    <div class="gaps">${item.missing.map(g => `<article><span>${esc(g.field.replaceAll('_',' '))}</span><p>${esc(g.reason)}</p></article>`).join('') || '<p>No recorded gaps.</p>'}</div>
    <h3>Six-category legal passport <small>${item.rules.length} matched source records</small></h3>
    <div class="rules">${groups.map(group => `<article><b>${esc(humanize(group.category))}</b><strong>${group.rules.length} visible source record${group.rules.length === 1 ? '' : 's'}</strong>${group.rules.map(r => `<details class="rule-detail"><summary><span class="result result-${esc(r.displayResult)}">${esc(r.displayResult.replaceAll('_',' '))}</span> ${esc(r.title)}</summary><p class="decision-reason">${esc(r.displayDecision.explanation)}</p><p class="requirement">${esc(r.requirement)}</p>${r.key_value ? `<p><b>Limit or formula:</b> ${esc(r.key_value)}</p>` : ''}<p><b>Coverage:</b> ${esc(r.coverage_conditions || 'Specific conditions require review.')}</p>${r.exemptions ? `<p><b>Exemptions:</b> ${esc(r.exemptions)}</p>` : ''}${r.displayDecision.missing_coverage_facts?.length ? `<p><b>Missing facts:</b> ${esc(r.displayDecision.missing_coverage_facts.join(', '))}</p>` : ''}<blockquote>${esc(r.quoted_span)}</blockquote><p class="citation"><a href="${esc(r.source_url)}" target="_blank" rel="noreferrer">${esc(r.citation)} ↗</a> · ${esc(r.source_doc_id)} · Retrieved ${esc(r.retrieved_at || 'date not supplied')} · Effective ${esc(r.effective_date || 'date not established')}${r.valid_through ? ` · Source rate through ${esc(r.valid_through)}` : ''}</p></details>`).join('') || '<p>No supported rule record for this category; coverage remains unknown.</p>'}</article>`).join('')}</div></details>`;
}

function scenarioDecision(rule, date) {
  const table = rule.decision_table;
  const fact = table.scenario_field && scenarioFacts()[table.scenario_field];
  const choice = fact && fact !== 'unknown' ? table.choices?.[fact] : null;
  const time = rule.effective_date && date < rule.effective_date ? 'before' :
    rule.valid_through ? (date > rule.valid_through ? 'after' : 'active') :
    table.scenario_window && date >= table.scenario_window.start && date <= table.scenario_window.end ? 'active' : 'after';
  return (choice || table.default)[time];
}

function fact(label, value) { return `<div><span>${label}</span><b class="${value == null ? 'missing' : ''}">${esc(value)}</b></div>`; }
function humanize(value) { return value.replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase()); }

function renderMetrics() {
  document.querySelector('#metrics').innerHTML = [
    ['Sample homes', system.properties], ['Rule categories', 6],
    ['Live demo paths', 4], ['Source-linked rules', system.rules]
  ].map(([label,value]) => `<div><b>${esc(value)}</b><span>${label}</span></div>`).join('');
}

function renderChanges() {
  const section = document.querySelector('#changes');
  section.classList.remove('hidden');
  section.innerHTML = `<p class="eyebrow">CHANGE TRACKER</p><h2>Five supplied scenarios, evaluated across the sample.</h2><p class="caption">These counts are jurisdiction candidates. Open an address to compare the rule before and after; building coverage still needs its own facts.</p><div class="timeline">${Object.entries(system.change_tests).map(([id,test]) => `<article><span>${id}</span><b>${test.affected} candidate addresses</b>${test.conflicts ? `<em>${test.conflicts} possible conflicts</em>` : ''}<p>${esc(test.notes)}</p>${test.affected_address_ids?.length ? `<details><summary>Browse all ${test.affected} addresses</summary><div class="example-ids">${test.affected_address_ids.map(addressId => `<button type="button" data-property="${esc(addressId)}">${esc(addressId)}</button>`).join('')}</div></details>` : '<p>Confirmed affected set is empty.</p>'}</article>`).join('')}</div>`;
}

function renderCoverage() {
  const gaps = system.source_gaps;
  const section = document.querySelector('#coverage');
  section.classList.remove('hidden');
  section.innerHTML = `<p class="eyebrow">SOURCE COVERAGE</p><h2>Gaps are reported, never hidden.</h2><div class="timeline coverage-grid"><article><span>${gaps.recovered_official}</span><b>Official-source recoveries</b><p>Link-only records replaced with short, traceable official city excerpts.</p></article><article><span>${gaps.supplemented}</span><b>Verified supplements</b><p>Critical city rules recovered from separately verified sources.</p></article><article><span>${gaps.terms_review}</span><b>Terms review</b><p>Publisher pages deliberately not bulk-captured.</p></article><article><span>${gaps.capture_blocked}</span><b>Official source blocked</b><p>Recorded as unresolved evidence, not replaced by a guess.</p></article><article><span>${gaps.context_only}</span><b>Secondary context</b><p>Excluded when official legal evidence is preferred.</p></article></div>`;
}

search.addEventListener('input', () => {
  const q = search.value.trim().toLowerCase();
  if (!q) { matches.innerHTML = ''; return; }
  const found = records.filter(r => [r.id,r.address,r.postal_city,r.legal_city,r.state].join(' ').toLowerCase().includes(q)).slice(0,8);
  renderList(found);
  if (active && search.value.trim().toLowerCase() !== active.id.toLowerCase()) {
    active = null;
    changeContext = null;
    passport.classList.add('hidden');
    passport.innerHTML = '';
  }
});

search.addEventListener('keydown', event => {
  if (event.key !== 'Enter') return;
  const first = matches.querySelector('button[data-id]');
  if (!first) return;
  event.preventDefault();
  openRecord(first.dataset.id);
});

matches.addEventListener('click', event => {
  const button = event.target.closest('button[data-id]');
  if (!button) return;
  openRecord(button.dataset.id);
});

function openRecord(id, date, changeId = null) {
  active = records.find(record => record.id === id);
  if (!active) return;
  if (date) asOf.value = date;
  changeContext = changeId;
  bostonProgram = 'unknown';
  newarkRentStatus = 'unknown';
  sfRentStatus = 'unknown';
  sanDiegoSharedFacilities = 'unknown';
  renderPassport(active);
  search.value = active.id;
  matches.innerHTML = '';
}

document.querySelector('#demo-paths').addEventListener('click', event => {
  const property = event.target.closest('button[data-demo-property]');
  if (property) {
    openRecord(property.dataset.demoProperty, property.dataset.demoDate);
    passport.scrollIntoView({behavior: 'auto', block: 'start'});
  }
  if (event.target.closest('button[data-demo-changes]')) {
    document.querySelector('#changes').scrollIntoView({behavior: 'auto', block: 'start'});
  }
});
asOf.addEventListener('change', () => {
  if (!asOf.validity.valid || !asOf.value) { asOf.reportValidity(); return; }
  if (active) renderPassport(active);
});
document.querySelector('.date-shortcuts').addEventListener('click', event => {
  const button = event.target.closest('button[data-date]');
  if (!button) return;
  asOf.value = button.dataset.date;
  if (active) renderPassport(active);
});
passport.addEventListener('change', event => {
  if (event.target.id === 'program-fact') {
    bostonProgram = event.target.value;
    renderPassport(active);
  }
  if (event.target.id === 'newark-rent-fact') {
    newarkRentStatus = event.target.value;
    renderPassport(active);
  }
  if (event.target.id === 'sf-rent-fact') {
    sfRentStatus = event.target.value;
    renderPassport(active);
  }
  if (event.target.id === 'sd-shared-fact') {
    sanDiegoSharedFacilities = event.target.value;
    renderPassport(active);
  }
});
passport.addEventListener('click', event => {
  const verify = event.target.closest('[data-verify-control]');
  if (verify) {
    const control = document.getElementById(verify.dataset.verifyControl);
    control?.scrollIntoView({behavior:'auto',block:'center'});
    control?.focus();
    return;
  }
  if (event.target.closest('[data-open-evidence]')) {
    const drawer = document.getElementById('evidence');
    drawer.open = true;
    drawer.scrollIntoView({behavior:'auto',block:'start'});
    return;
  }
  const step = event.target.closest('[data-demo-step]');
  if (step) {
    const examples = {1:['A0013','2026-10-01'],2:['A0065','2026-10-01'],3:['A0001','2025-12-31']};
    if (examples[step.dataset.demoStep]) {
      openRecord(...examples[step.dataset.demoStep]);
      passport.scrollIntoView({behavior:'auto',block:'start'});
    } else document.querySelector('#changes').scrollIntoView({behavior:'auto',block:'start'});
    return;
  }
  const button = event.target.closest('[data-show-change-date]');
  if (!button || !active) return;
  asOf.value = button.dataset.showChangeDate;
  renderPassport(active);
});
document.querySelector('#changes').addEventListener('click', event => {
  const button = event.target.closest('button[data-property]');
  if (!button) return;
  const changeId = button.closest('article')?.querySelector('span')?.textContent.trim();
  const date = changeId === 'T1' ? '2025-12-31' : changeId === 'T3' ? '2026-10-01' : '2026-10-01';
  openRecord(button.dataset.property, date, changeId);
  passport.scrollIntoView({behavior:'auto', block:'start'});
});

async function operatorRequest(payload) {
  const response = await fetch('/api/operator', {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok || result.error) throw new Error(result.error || 'Operator service failed');
  return result;
}

fetch('/api/health').then(response => response.json()).then(status => {
  if (status.ready) document.querySelector('#operator').classList.remove('hidden');
}).catch(() => {});

document.querySelector('#property-form').addEventListener('submit', async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const resultBox = document.querySelector('#property-result');
  const values = Object.fromEntries(new FormData(form));
  resultBox.textContent = 'Saving and evaluating…';
  try {
    const result = await operatorRequest({action:'import_property', property:values});
    const rules = result.passport.rules;
    const counts = rules.reduce((totals, rule) => { totals[rule.result] = (totals[rule.result] || 0) + 1; return totals; }, {});
    resultBox.innerHTML = `<strong>Saved ${esc(result.passport.address_id)} · ${esc(result.portfolio_properties)} indexed properties</strong><p>${esc(counts.applies || 0)} applies, ${esc(counts.unknown || 0)} unknown, ${esc(counts.not_yet_effective || 0)} not yet effective. City boundary remains unverified, so city rules are withheld.</p><ul>${rules.slice(0,6).map(rule => `<li>${esc(rule.result.replaceAll('_',' '))} · <a href="${esc(rule.source_url)}" target="_blank" rel="noreferrer">${esc(rule.citation)}</a></li>`).join('')}</ul>`;
  } catch (error) { resultBox.innerHTML = `<p class="error">${esc(error.message)}</p>`; }
});

document.querySelector('#law-form').addEventListener('submit', async event => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget));
  const resultBox = document.querySelector('#law-result');
  const reviewed = values.title.trim() && values.citation.trim() && values.coverage_conditions.trim();
  const payload = {
    action:'preview_law', source_text:values.source_text, source_url:values.source_url,
    jurisdiction:values.jurisdiction, retrieved_at:new Date().toISOString().slice(0,10),
    as_of:asOf.value || '2026-10-01'
  };
  if (reviewed) payload.review = {
    title:values.title, citation:values.citation, status:values.status,
    effective_date:values.effective_date || null,
    coverage_conditions:values.coverage_conditions,
    coverage_spec:values.min_units ? [{field:'units',op:'gte',value:Number(values.min_units)}] : values.jurisdiction_wide ? [] : null
  };
  resultBox.textContent = 'Extracting source text…';
  try {
    const result = await operatorRequest(payload);
    if (!result.candidate_count) { resultBox.textContent = 'No actionable rule clause was found. Check the full source text and review it manually.'; return; }
    resultBox.innerHTML = `<strong>${esc(result.candidate_count)} candidate clause${result.candidate_count === 1 ? '' : 's'} extracted</strong><p>${esc(result.review_status.replaceAll('_',' '))} · ${esc(result.candidate.category.replaceAll('_',' '))} · ${esc(result.candidate.jurisdiction)}</p><blockquote>${esc(result.candidate.quoted_span)}</blockquote>${result.impact ? `<p>${esc(result.impact.candidates)} indexed jurisdiction candidates: ${Object.entries(result.impact.results).map(([key,value]) => `${esc(value)} ${esc(key.replaceAll('_',' '))}`).join(', ')}.</p><p>Preview only. Publication requires source and legal review.</p>` : '<p>Fill all reviewer fields to preview impact through the same Python evaluator.</p>'}`;
  } catch (error) { resultBox.innerHTML = `<p class="error">${esc(error.message)}</p>`; }
});

document.querySelector('#load-law-example').addEventListener('click', () => {
  const form = document.querySelector('#law-form');
  form.elements.source_url.value = 'https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260AB325';
  form.elements.jurisdiction.value = 'CA';
  form.elements.source_text.value = '(a) It shall be unlawful for a person to use or distribute a common pricing algorithm as part of a contract, combination in the form of a trust, or conspiracy to restrain trade or commerce in violation of this chapter.';
  form.elements.title.value = 'California common pricing algorithm restriction — source recheck';
  form.elements.citation.value = 'Cal. Bus. & Prof. Code § 16756.1';
  form.elements.status.value = 'in_force';
  form.elements.effective_date.value = '2026-01-01';
  form.elements.coverage_conditions.value = 'Statewide restriction on use or distribution of a common pricing algorithm in the conduct specified by the source.';
  form.elements.jurisdiction_wide.checked = true;
  form.querySelector('details').open = true;
  document.querySelector('#law-result').innerHTML = '<p>This rechecks a captured official source already in the starter corpus. The preview does not add a duplicate live rule.</p>';
});
