const state = {
  politicians: [],
  profiles: {},
  meta: {},
  donors: null,
  disclosures: null,
};

async function loadData() {
  const responses = await Promise.all([
    fetch('data/politicians.json'),
    fetch('data/profiles.json'),
    fetch('data/meta.json'),
    fetch('data/donors.json').catch(() => null),
    fetch('data/disclosures.json').catch(() => null),
  ]);

  state.politicians = await responses[0].json();
  state.profiles = await responses[1].json();
  state.meta = await responses[2].json();

  if (responses[3]) {
    state.donors = await responses[3].json();
  }
  if (responses[4]) {
    state.disclosures = await responses[4].json();
  }
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

  const freshness = document.getElementById('dataFreshness');
  if (freshness && state.meta.generated_at) {
    const date = new Date(state.meta.generated_at);
    freshness.textContent = `Last refresh: ${date.toLocaleDateString()}`;
  }

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
    if (!featured.length) {
      featuredList.innerHTML = '<li>No featured profiles yet.</li>';
    }

    featured.forEach((p) => {
      const li = document.createElement('li');
      li.innerHTML = `<a href="profile.html?id=${p.id}">${p.name}</a><span>${p.party || 'Independent'}</span>`;
      featuredList.appendChild(li);
    });
  }

  renderPopular();
  renderCharts(parties, house, senate);
  renderCards(partyFilter);
  renderDonors();
}

function renderPopular() {
  const popularGrid = document.getElementById('popularGrid');
  if (!popularGrid) return;

  const popular = state.politicians.filter((p) => p.featured).slice(0, 6);
  popularGrid.innerHTML = '';

  popular.forEach((p) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <h4>${p.name} <span class="featured-pill">Featured</span></h4>
      <div class="tags">
        <span class="tag">${p.chamber}</span>
        <span class="tag">${p.party || 'Independent'}</span>
      </div>
      <p class="muted">${p.electorate || ''}</p>
      <a href="profile.html?id=${p.id}">View profile</a>
    `;
    popularGrid.appendChild(card);
  });

  if (!popular.length) {
    popularGrid.innerHTML = '<p class="muted">No featured profiles yet.</p>';
  }
}

function renderCharts(parties, house, senate) {
  const chamberCanvas = document.getElementById('chamberChart');
  if (chamberCanvas) {
    new Chart(chamberCanvas, {
      type: 'doughnut',
      data: {
        labels: ['House', 'Senate'],
        datasets: [{
          data: [house, senate],
          backgroundColor: ['#f7b267', '#7bdff2'],
        }],
      },
      options: { plugins: { legend: { labels: { color: '#f2f2f2' } } } },
    });
  }

  const partyCanvas = document.getElementById('partyChart');
  if (partyCanvas) {
    const counts = {};
    state.politicians.forEach((p) => {
      const party = p.party || 'Independent';
      counts[party] = (counts[party] || 0) + 1;
    });
    const labels = Object.keys(counts).slice(0, 8);
    const values = labels.map((label) => counts[label]);

    new Chart(partyCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: '#f7b267',
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#f2f2f2' } },
          y: { ticks: { color: '#f2f2f2' } },
        },
      },
    });
  }
}

function renderCards(partyFilter) {
  const cardGrid = document.getElementById('cardGrid');
  if (!cardGrid) return;

  const searchInput = document.getElementById('searchInput');
  const chamberFilter = document.getElementById('chamberFilter');
  const resultsCount = document.getElementById('resultsCount');

  const renderList = () => {
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
        <h4>${p.name} ${p.featured ? '<span class="featured-pill">Featured</span>' : ''}</h4>
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
    el.addEventListener('input', renderList);
    el.addEventListener('change', renderList);
  });

  renderList();
}

function renderDonors() {
  if (!state.donors) return;
  const select = document.getElementById('donorPartySelect');
  const list = document.getElementById('donorList');
  const meta = document.getElementById('donorMeta');
  const trendCanvas = document.getElementById('donorTrendChart');

  if (!select || !list) return;

  select.innerHTML = '<option value="">Select a party</option>';
  state.donors.parties.forEach((party) => {
    const option = document.createElement('option');
    option.value = party.party;
    option.textContent = party.party;
    select.appendChild(option);
  });

  let trendChart = null;

  const renderList = () => {
    const partyName = select.value;
    const partyData = state.donors.parties.find((p) => p.party === partyName);
    list.innerHTML = '';

    if (!partyData || !partyData.top_donors.length) {
      list.innerHTML = '<p class="muted">Select a party to see the top disclosed donors.</p>';
      if (trendChart) {
        trendChart.destroy();
        trendChart = null;
      }
      return;
    }

    const donors = partyData.top_donors || [];
    const initial = donors.slice(0, 5);
    const extra = donors.slice(5);

    initial.forEach((donor) => {
      const card = document.createElement('div');
      card.className = 'donor-card';
      card.innerHTML = `
        <h4>${donor.name}</h4>
        <p class="muted">${formatCurrency(donor.amount)}</p>
      `;
      list.appendChild(card);
    });

    if (extra.length) {
      const toggle = document.createElement('button');
      toggle.className = 'donor-toggle';
      toggle.textContent = 'Show more';
      let expanded = false;

      toggle.addEventListener('click', () => {
        expanded = !expanded;
        toggle.textContent = expanded ? 'Show less' : 'Show more';
        list.querySelectorAll('.donor-extra').forEach((node) => node.remove());
        if (expanded) {
          extra.forEach((donor) => {
            const card = document.createElement('div');
            card.className = 'donor-card donor-extra';
            card.innerHTML = `
              <h4>${donor.name}</h4>
              <p class="muted">${formatCurrency(donor.amount)}</p>
            `;
            list.appendChild(card);
          });
        }
      });

      list.appendChild(toggle);
    }

    if (trendCanvas) {
      const years = (partyData.yearly_totals || []).map((item) => item.year);
      const values = (partyData.yearly_totals || []).map((item) => item.amount);
      if (trendChart) {
        trendChart.destroy();
      }
      trendChart = new Chart(trendCanvas, {
        type: 'line',
        data: {
          labels: years,
          datasets: [{
            data: values,
            borderColor: '#7bdff2',
            backgroundColor: 'rgba(123, 223, 242, 0.2)',
            fill: true,
          }],
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: '#f2f2f2' } },
            y: { ticks: { color: '#f2f2f2' } },
          },
        },
      });
    }
  };

  select.addEventListener('change', renderList);
  renderList();

  if (meta) {
    meta.textContent = `Source: ${state.donors.source} · Financial year: ${state.donors.financial_year}`;
  }
}

function formatCurrency(value) {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 0,
  }).format(value);
}

function renderDisclosureLinks(data) {
  const panel = document.getElementById('disclosurePanel');
  const links = document.getElementById('disclosureLinks');
  if (!panel || !links) return;

  if (!state.disclosures) {
    panel.style.display = 'none';
    return;
  }

  links.innerHTML = '';
  if (!data) {
    links.innerHTML = '<p class="muted">No disclosure document available. View the register below.</p>';
  }

  if (data.house_url) {
    links.innerHTML += `<a href="${data.house_url}" target="_blank">House Register PDF</a>`;
  }
  if (data.senate_urls && data.senate_urls.length) {
    data.senate_urls.forEach((url, idx) => {
      links.innerHTML += `<a href="${url}" target="_blank">Senate Register PDF ${idx + 1}</a>`;
    });
  }

  if (!data.house_url && (!data.senate_urls || !data.senate_urls.length)) {
    links.innerHTML += `<a href="https://www.aph.gov.au/Senators_and_Members/Members/Register" target="_blank">House Register Index</a>`;
    links.innerHTML += `<a href="https://www.aph.gov.au/Parliamentary_Business/Committees/Senate/Senators_Interests/Tabled_volumes" target="_blank">Senate Register Index</a>`;
  }
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
      <h1>${data.name} ${data.featured ? '<span class="featured-pill">Featured</span>' : ''}</h1>
      <p class="muted">${data.party || 'Independent'} • ${data.electorate || ''}</p>
    `;
  }

  setSummaryCard('summaryChamber', 'Chamber', data.chamber || 'Unknown');
  setSummaryCard('summaryInvestments', 'Investments', `${profile.investments?.length || 0}`);
  setSummaryCard('summaryPolicies', 'Policy signals', `${profile.policies?.length || 0}`);
  setSummaryCard('summaryFlags', 'Flags', `${profile.correlations?.length || 0}`);

  const disclosureData = buildDisclosureData(data);
  renderDisclosureLinks(disclosureData);

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

function buildDisclosureData(pol) {
  if (!state.disclosures) return null;
  const result = { house_url: null, senate_urls: [] };

  if (pol.chamber === 'House') {
    const last = pol.name.split(' ').slice(-1)[0].toLowerCase();
    const entry = state.disclosures.house[last] || state.disclosures.house[normalizeKey(last)];
    if (entry) {
      result.house_url = entry.url;
    }
  } else if (pol.chamber === 'Senate') {
    result.senate_urls = state.disclosures.senate.map((item) => item.url);
  }

  return result;
}

function normalizeKey(value) {
  return (value || '').toLowerCase().replace(/[^a-z]/g, '');
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
