const state = {
  politicians: [],
  profiles: {},
};

async function loadData() {
  const [polRes, profileRes] = await Promise.all([
    fetch('data/politicians.json'),
    fetch('data/profiles.json'),
  ]);
  state.politicians = await polRes.json();
  state.profiles = await profileRes.json();
}

function renderHome() {
  const total = state.politicians.length;
  const house = state.politicians.filter((p) => p.chamber === 'House').length;
  const senate = state.politicians.filter((p) => p.chamber === 'Senate').length;

  const metricTotal = document.getElementById('metricTotal');
  const metricHouse = document.getElementById('metricHouse');
  const metricSenate = document.getElementById('metricSenate');
  if (metricTotal) metricTotal.textContent = total || '—';
  if (metricHouse) metricHouse.textContent = house || '—';
  if (metricSenate) metricSenate.textContent = senate || '—';

  const parties = new Set(state.politicians.map((p) => p.party).filter(Boolean));
  const partyFilter = document.getElementById('partyFilter');
  if (partyFilter) {
    [...parties].sort().forEach((party) => {
      const option = document.createElement('option');
      option.value = party;
      option.textContent = party;
      partyFilter.appendChild(option);
    });
  }

  const featuredList = document.getElementById('featuredList');
  if (featuredList) {
    const featured = state.politicians
      .filter((p) => p.featured)
      .slice(0, 5);

    featuredList.innerHTML = '';
    featured.forEach((p) => {
      const li = document.createElement('li');
      li.innerHTML = `<a href="profile.html?id=${p.id}">${p.name}</a><span>${p.party || 'Independent'}</span>`;
      featuredList.appendChild(li);
    });
  }

  const cardGrid = document.getElementById('cardGrid');
  if (!cardGrid) return;

  const searchInput = document.getElementById('searchInput');
  const chamberFilter = document.getElementById('chamberFilter');
  const resultsCount = document.getElementById('resultsCount');

  const renderCards = () => {
    const term = (searchInput?.value || '').toLowerCase();
    const party = partyFilter?.value || '';
    const chamber = chamberFilter?.value || '';

    const filtered = state.politicians.filter((p) => {
      const blob = `${p.name} ${p.party} ${p.electorate}`.toLowerCase();
      return (
        (!term || blob.includes(term)) &&
        (!party || p.party === party) &&
        (!chamber || p.chamber === chamber)
      );
    });

    cardGrid.innerHTML = '';
    filtered.forEach((p) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <h4>${p.name}</h4>
        <div class="tags">
          <span class="tag">${p.chamber}</span>
          <span class="tag">${p.party || 'Independent'}</span>
        </div>
        <p class="muted">${p.electorate || ''}</p>
        <a href="profile.html?id=${p.id}">View profile</a>
      `;
      cardGrid.appendChild(card);
    });

    if (resultsCount) {
      resultsCount.textContent = `${filtered.length} results`;
    }
  };

  [searchInput, partyFilter, chamberFilter].forEach((el) => {
    if (!el) return;
    el.addEventListener('input', renderCards);
    el.addEventListener('change', renderCards);
  });

  renderCards();
}

function renderProfile() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');
  const data = state.politicians.find((p) => p.id === id);
  const profile = state.profiles[id] || {};

  if (!data) return;

  const summary = document.getElementById('profileSummary');
  if (summary) {
    summary.innerHTML = `
      <h1>${data.name}</h1>
      <p class="muted">${data.party || 'Independent'} • ${data.electorate || ''}</p>
    `;
  }

  setSummaryCard('summaryChamber', 'Chamber', data.chamber || 'Unknown');
  setSummaryCard('summaryInvestments', 'Investments', `${profile.investments?.length || 0}`);
  setSummaryCard('summaryPolicies', 'Policy signals', `${profile.policies?.length || 0}`);
  setSummaryCard('summaryFlags', 'Flags', `${profile.correlations?.length || 0}`);

  renderTable('correlationTable', ['Policy', 'Asset', 'Signal'], profile.correlations || [], (row) => [
    row.policy || '—',
    row.asset || '—',
    row.details || '—',
  ]);

  renderTable('investmentTable', ['Asset', 'Date', 'Source'], profile.investments || [], (row) => [
    row.asset || '—',
    row.date || '—',
    row.source || '—',
  ]);

  renderTable('policyTable', ['Policy', 'Date', 'Source'], profile.policies || [], (row) => [
    row.title || '—',
    row.date || '—',
    row.source || '—',
  ]);
}

function setSummaryCard(id, label, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<span class="muted">${label}</span><h3>${value}</h3>`;
}

function renderTable(containerId, headers, rows, mapper) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (!rows.length) {
    container.innerHTML = '<p class="muted">No records available yet.</p>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'table';
  const thead = document.createElement('thead');
  thead.innerHTML = `<tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr>`;
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  rows.forEach((row) => {
    const tr = document.createElement('tr');
    mapper(row).forEach((cell) => {
      const td = document.createElement('td');
      td.textContent = cell;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  container.innerHTML = '';
  container.appendChild(table);
}

(async function init() {
  try {
    await loadData();
    if (document.getElementById('cardGrid')) {
      renderHome();
    }
    if (document.getElementById('profileSummary')) {
      renderProfile();
    }
  } catch (err) {
    console.error('Failed to load data', err);
  }
})();
