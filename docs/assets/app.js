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
      li.innerHTML = `<a href="${buildProfileLink(p)}" target="_blank">${p.name}</a><span>${p.party || 'Independent'}</span>`;
      featuredList.appendChild(li);
    });
  }

  renderPopular();
  renderCharts(parties, house, senate);
  renderCards(partyFilter);
  renderDonors();
}

function buildProfileLink(p) {
  const disclosure = buildDisclosureData(p);
  if (disclosure && disclosure.house_urls.length) {
    return disclosure.house_urls[0];
  }
  return `profile.html?id=${p.id}`;
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
      <a href="${buildProfileLink(p)}" target="_blank">View disclosure</a>
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
      const link = buildProfileLink(p);
      const target = link.endsWith('.pdf') ? 'target="_blank"' : '';
      card.innerHTML = `
        <h4>${p.name} ${p.featured ? '<span class="featured-pill">Featured</span>' : ''}</h4>
        <div class="tags">
          <span class="tag">${p.chamber}</span>
          <span class="tag">${p.party || 'Independent'}</span>
        </div>
        <p class="muted">${p.electorate || ''}</p>
        <a href="${link}" ${target}>View disclosure</a>
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
    links.innerHTML = '<p class="muted">No disclosure document available.</p>';
    return;
  }

  if (data.house_urls.length) {
    data.house_urls.forEach((item) => {
      links.innerHTML += `<a href="${item.url}" target="_blank">${item.label} (House)</a>`;
    });
  }

  if (data.senate_urls.length) {
    data.senate_urls.forEach((url, idx) => {
      links.innerHTML += `<a href="${url}" target="_blank">Senate Register PDF ${idx + 1}</a>`;
    });
  }

  if (!data.house_urls.length && !data.senate_urls.length) {
    links.innerHTML = '<p class="muted">No disclosure document found for this name.</p>';
  }
}

function renderProfile() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get('id');
  const data = state.politicians.find((p) => p.id === id);

  if (!data) return;

  const summary = document.getElementById('profileSummary');
  if (summary) {
    summary.innerHTML = `
      <h1>${data.name}</h1>
      <p class="muted">${data.party || 'Independent'} • ${data.electorate || ''}</p>
    `;
  }

  setSummaryCard('summaryChamber', 'Chamber', data.chamber || 'Unknown');
  setSummaryCard('summaryInvestments', 'Investments', 'See disclosure');
  setSummaryCard('summaryPolicies', 'Policy signals', 'See disclosure');
  setSummaryCard('summaryFlags', 'Flags', 'See disclosure');

  const disclosureData = buildDisclosureData(data);
  renderDisclosureLinks(disclosureData);
}

function buildDisclosureData(pol) {
  if (!state.disclosures) return null;
  const result = { house_urls: [], senate_urls: [] };

  if (pol.chamber === 'House') {
    const surname = extractSurname(pol.name);
    const key = normalizeKey(surname);
    const entries = state.disclosures.house[key] || [];
    result.house_urls = entries;
  } else if (pol.chamber === 'Senate') {
    result.senate_urls = state.disclosures.senate.map((item) => item.url);
  }

  return result;
}

function normalizeKey(value) {
  return (value || '').toLowerCase().replace(/[^a-z]/g, '');
}

function extractSurname(fullName) {
  if (!fullName) return '';
  let cleaned = fullName
    .replace(/\b(Mr|Ms|Mrs|Dr|Hon|Senator|Member)\b/gi, '')
    .replace(/\b(MP|AM|AO|OBE|QC|KC)\b/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
  const parts = cleaned.split(' ').filter(Boolean);
  return parts.length ? parts[parts.length - 1].toLowerCase() : '';
}

function setSummaryCard(id, label, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<span class="muted">${label}</span><h3>${value}</h3>`;
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
