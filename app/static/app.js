const wordInput = document.getElementById('word-input');
const lemmaInput = document.getElementById('lemma-input');

wordInput.addEventListener('keydown', e => { if (e.key === 'Enter') analyzeWord(); });
lemmaInput.addEventListener('keydown', e => { if (e.key === 'Enter') showParadigm(); });

function setAndAnalyze(word) {
  wordInput.value = word;
  analyzeWord();
}

async function analyzeWord() {
  const word = wordInput.value.trim();
  const div = document.getElementById('results');
  if (!word) { div.innerHTML = ''; return; }
  div.innerHTML = '<div class="loading">Анализирую...</div>';

  const resp = await fetch('/analyze', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({word})
  });
  const data = await resp.json();
  if (data.error) { div.innerHTML = `<div class="error-msg">${data.error}</div>`; return; }

  if (!data.results || data.results.length === 0) {
    div.innerHTML = '<div class="empty-msg">Слово не найдено и не удалось предсказать анализ.</div>';
    return;
  }

  const sourceLabel = {fst: 'FST-анализ', lookup: 'в словаре', heuristic: 'предсказано'};
  const sourceBadge = {fst: 'badge-fst', lookup: 'badge-known', heuristic: 'badge-unknown'};

  div.innerHTML = data.results.map(r => `
    <div class="result-item ${r.is_known ? 'known' : 'unknown'}">
      <span class="badge ${sourceBadge[r.source] || (r.is_known ? 'badge-known' : 'badge-unknown')}">
        ${sourceLabel[r.source] || (r.is_known ? 'в словаре' : 'предсказано')}
      </span>
      <div class="result-lemma">${r.lemma}</div>
      <div class="result-tags">${r.tags}</div>
      <div class="result-desc">${r.description}</div>
      <span class="paradigm-link" onclick="showLemmaParadigm('${r.lemma}')">
        показать всю парадигму →
      </span>
    </div>
  `).join('');
}

async function showParadigm() {
  const lemma = lemmaInput.value.trim();
  renderParadigm(lemma);
}

async function showLemmaParadigm(lemma) {
  lemmaInput.value = lemma;
  renderParadigm(lemma);
  document.getElementById('paradigm-results').scrollIntoView({behavior: 'smooth'});
}

async function renderParadigm(lemma) {
  const div = document.getElementById('paradigm-results');
  if (!lemma) { div.innerHTML = ''; return; }
  div.innerHTML = '<div class="loading">Загружаю парадигму...</div>';

  const resp = await fetch('/paradigm', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({lemma})
  });
  const data = await resp.json();
  if (data.error) { div.innerHTML = `<div class="error-msg">${data.error}</div>`; return; }

  if (!data.forms || data.forms.length === 0) {
    div.innerHTML = `<div class="empty-msg">Лемма «${lemma}» не найдена в словаре.</div>`;
    return;
  }

  const rows = data.forms.map(f => `
    <tr>
      <td><strong>${f.form}</strong></td>
      <td><code>${f.tags}</code></td>
      <td>${f.description}</td>
    </tr>
  `).join('');

  div.innerHTML = `
    <p style="margin-bottom:0.8rem;color:#4a5568">
      Парадигма леммы <strong>${data.lemma}</strong> — ${data.forms.length} форм
    </p>
    <table>
      <thead><tr><th>Словоформа</th><th>Теги</th><th>Описание</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}
