const AppState = {
    results: {},
    lastPayload: null,
    zoneCount: 0,
    resistanceNames: { tempo: 'Tempo', distancia: 'Distância', preco: 'Preço' },
    toastInstance: null,
    hasAnalysisRun: false,
    isAnalysisRunning: false,
    interactiveHistory: [],
};

// --- Debounce Utility ---
function debounce(func, delay) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}

// --- Theme Toggler ---
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-bs-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    const icon = document.querySelector('#theme-toggler i');
    icon.classList.toggle('bi-moon-stars-fill', newTheme === 'dark');
    icon.classList.toggle('bi-sun-fill', newTheme === 'light');
}

document.addEventListener('DOMContentLoaded', () => {
    // --- Load Theme ---
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
    const icon = document.querySelector('#theme-toggler i');
    icon.classList.toggle('bi-moon-stars-fill', savedTheme === 'dark');
    icon.classList.toggle('bi-sun-fill', savedTheme === 'light');

    const toastEl = document.getElementById('notification-toast');
    if (toastEl) AppState.toastInstance = new bootstrap.Toast(toastEl, { delay: 3500 });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'F11') {
            event.preventDefault();
            window.pywebview.api.toggle_fullscreen();
        }
        if (event.ctrlKey && (event.key === 'r' || event.key === 'R')) {
            event.preventDefault();
            const runButton = document.getElementById('run-analysis-button');
            if (runButton && !runButton.disabled) {
                runFullAnalysis();
            }
        }
    });

    const debouncedRun = debounce(runInteractiveScenario, 300);
    ['alpha-slider', 'beta-slider', 'gamma-slider'].forEach(id => {
        const slider = document.getElementById(id);
        slider.addEventListener('input', (e) => {
            document.getElementById(id.replace('-slider', '-value')).textContent = e.target.value;
            debouncedRun();
        });
    });


    initializeEmptyTables(5);
});

function showPane(paneId) {
    document.querySelectorAll('.content-pane').forEach(p => p.classList.remove('active'));
    document.getElementById(paneId).classList.add('active');

    document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
    const link = document.querySelector(`.sidebar a[onclick*="${paneId}"]`);
    if (link) {
        link.classList.add('active');
    }

    if (paneId === 'analise-pane' && !document.getElementById('analise-nav-link').classList.contains('disabled') && !AppState.isAnalysisRunning) {
        const isOutdated = !document.getElementById('results-outdated-indicator').classList.contains('d-none');
        if (!AppState.hasAnalysisRun || isOutdated) {
            runFullAnalysis();
        }
    }
}

function toggleSpinner(show) {
    AppState.isAnalysisRunning = show;
    document.getElementById('loading-spinner')?.classList.toggle('d-none', !show);
    document.getElementById('analise-nav-link')?.classList.toggle('disabled', show);

    const runButton = document.getElementById('run-analysis-button');
    if (runButton) {
        runButton.disabled = show;
        runButton.innerHTML = show
            ? `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Executando...`
            : `<i class="bi bi-play-circle-fill me-2"></i>Executar Análise Completa`;
    }
}

function setResultsOutdated(isOutdated) {
    document.getElementById('results-outdated-indicator')?.classList.toggle('d-none', !isOutdated);
    document.getElementById('export-button').disabled = isOutdated;
}

function validateAllCells() {
    const cells = document.querySelectorAll('.editable-table .form-control-plaintext');
    let allValid = true;
    cells.forEach(cell => {
        if (!cell.validity.valid || cell.value.trim() === '' || parseFloat(cell.value) < 0) {
            allValid = false;
        }
    });

    const runButton = document.getElementById('run-analysis-button');
    if (runButton) runButton.disabled = !allValid && !AppState.isAnalysisRunning;

    if (!AppState.isAnalysisRunning) {
        ['analise-nav-link', 'interactive-nav-link', 'dashboard-nav-link', 'analysis-tools-nav-link'].forEach(id => {
            document.getElementById(id)?.classList.toggle('disabled', !allValid);
        });
    }

    return allValid;
}

function addValidationListeners() {
    document.querySelectorAll('.editable-table .form-control-plaintext').forEach(cell => {
        cell.addEventListener('input', (e) => {
            const isValid = e.target.validity.valid && e.target.value.trim() !== '' && parseFloat(e.target.value) >= 0;
            e.target.classList.toggle('is-invalid', !isValid);
            e.target.classList.add('cell-modified');
            if (AppState.hasAnalysisRun) {
                setResultsOutdated(true);
            }
            validateAllCells();
        });
    });
}

function clearModifiedStatus() {
    document.querySelectorAll('.cell-modified').forEach(cell => cell.classList.remove('cell-modified'));
}

function gatherDataFromTables(forSaving = false) {
    if (!validateAllCells() && !forSaving) {
        showNotification("Existem valores inválidos ou vazios nas tabelas. Por favor, corrija.", "bi-exclamation-triangle-fill text-danger");
        return null;
    }
    const odTable = document.getElementById('od-table').rows;
    const zonas = Array.from(odTable).slice(1).map(row => row.cells[0].textContent.trim());
    const o_raw = Array.from(odTable).slice(1).map(row => row.cells[1].querySelector('input').value);
    const d_raw = Array.from(odTable).slice(1).map(row => row.cells[2].querySelector('input').value);

    const matrices_raw = {};
    Object.keys(AppState.resistanceNames).forEach(key => {
        const table = document.getElementById(`matrix-${key}`);
        matrices_raw[key] = Array.from(table.rows).slice(1).map(row => Array.from(row.cells).slice(1).map(cell => cell.querySelector('input').value));
    });

    const maxIter = parseInt(document.getElementById('max-iter-input').value, 10);
    const tolerance = parseFloat(document.getElementById('tolerance-input').value);
    const allowIntrazonal = document.getElementById('intrazonal-switch').checked;
    const impedanceFunc = document.querySelector('input[name="impedanceFunction"]:checked').value;

    const config = {
        furness: {
            "max_iter": isNaN(maxIter) ? 200 : maxIter,
            "tolerancia": isNaN(tolerance) ? 0.0005 : tolerance
        },
        allow_intrazonal: allowIntrazonal,
        impedancia: {
            "tipo": impedanceFunc
        }
    };

    if (forSaving) {
        return { zonas, dados: { o: o_raw, d: d_raw, ...matrices_raw }, resistance_names: AppState.resistanceNames };
    }

    const dados = { o: o_raw.map(v => parseFloat(v) || 0), d: d_raw.map(v => parseFloat(v) || 0) };
    Object.keys(matrices_raw).forEach(key => dados[key] = matrices_raw[key].map(row => row.map(cell => parseFloat(cell) || 0)));

    return { zonas, dados, resistance_names: AppState.resistanceNames, config: config };
}


function addZone() {
    if (AppState.zoneCount >= 15) return;
    const currentData = gatherDataFromTables(true);
    currentData.zonas.push(`Zona ${AppState.zoneCount + 1}`);
    currentData.dados.o.push('0');
    currentData.dados.d.push('0');
    Object.keys(AppState.resistanceNames).forEach(key => {
        currentData.dados[key].forEach(row => row.push('0'));
        currentData.dados[key].push(Array(AppState.zoneCount + 1).fill('0'));
    });
    populateEditableData(currentData);
}

function removeZone() {
    if (AppState.zoneCount <= 2) return;
    const currentData = gatherDataFromTables(true);
    currentData.zonas.pop();
    currentData.dados.o.pop();
    currentData.dados.d.pop();
    Object.keys(AppState.resistanceNames).forEach(key => {
        currentData.dados[key].pop();
        currentData.dados[key].forEach(row => row.pop());
    });
    populateEditableData(currentData);
}

function initializeEmptyTables(numZonas) {
    const zonas = Array.from({ length: numZonas }, (_, i) => `Zona ${i + 1}`);
    const emptyO = Array(numZonas).fill('0');
    const emptyMatrix = Array(numZonas).fill(null).map(() => Array(numZonas).fill('0'));
    populateEditableData({ zonas, dados: { o: emptyO, d: emptyO, tempo: emptyMatrix, distancia: emptyMatrix, preco: emptyMatrix }, resistance_names: { tempo: 'Tempo', distancia: 'Distância', preco: 'Preço' } });
}

function populateEditableData(data) {
    AppState.zoneCount = data.zonas.length;
    AppState.resistanceNames = data.resistance_names;
    const odTable = document.getElementById('od-table');
    odTable.innerHTML = `<thead><tr><th>Zona</th><th>Origens (O)</th><th>Destinos (D)</th></tr></thead><tbody>${data.zonas.map((zona, i) => `<tr><th contenteditable="true" onblur="updateZoneNames(this, ${i})">${zona}</th><td><input type="number" class="form-control-plaintext" value="${data.dados.o[i]}" min="0" step="any" required></td><td><input type="number" class="form-control-plaintext" value="${data.dados.d[i]}" min="0" step="any" required></td></tr>`).join('')}</tbody>`;

    const tabsContainer = document.getElementById('cost-matrix-tabs');
    const tabsContentContainer = document.getElementById('cost-matrix-tabs-content');
    tabsContainer.innerHTML = '';
    tabsContentContainer.innerHTML = '';

    Object.keys(AppState.resistanceNames).forEach((key, index) => {
        const isActive = index === 0;
        tabsContainer.innerHTML += `<li class="nav-item" role="presentation"><button class="nav-link ${isActive ? 'active' : ''}" id="tab-${key}" data-bs-toggle="tab" data-bs-target="#pane-${key}" type="button" role="tab">${AppState.resistanceNames[key]}</button></li>`;
        let tableHTML = `<div class="tab-pane fade ${isActive ? 'show active' : ''}" id="pane-${key}" role="tabpanel"><table class="table table-sm editable-table mt-2" id="matrix-${key}">`;
        tableHTML += `<thead><tr><th>&nbsp;</th>${data.zonas.map(z => `<th>${z}</th>`).join('')}</tr></thead>`;
        tableHTML += `<tbody>${data.zonas.map((zona, i) => `<tr><th>${zona}</th>${data.dados[key][i].map(val => `<td><input type="number" class="form-control-plaintext" value="${val}" min="0" step="any" required></td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
        tabsContentContainer.innerHTML += tableHTML;
    });

    addValidationListeners();
    validateAllCells();
    clearModifiedStatus();
    if (AppState.hasAnalysisRun) setResultsOutdated(true);
}

function updateZoneNames(element, rowIndex) {
    const newName = element.textContent.trim();
    if (newName === "") {
        populateEditableData(gatherDataFromTables(true)); return;
    }
    const currentData = gatherDataFromTables(true);
    currentData.zonas[rowIndex] = newName;
    populateEditableData(currentData);
}

function runFullAnalysis() {
    const payload = gatherDataFromTables();
    if (!payload) return;
    toggleSpinner(true);
    showNotification("Executando análise completa...", "bi-hourglass-split");
    AppState.lastPayload = payload;
    AppState.interactiveHistory = [];
    window.pywebview.api.run_analysis(payload);
}

function runInteractiveScenario() {
    const payload = gatherDataFromTables();
    if (!payload) return;
    AppState.lastPayload = payload;
    payload.params = {
        alpha: parseFloat(document.getElementById('alpha-slider').value),
        beta: parseFloat(document.getElementById('beta-slider').value),
        gamma: parseFloat(document.getElementById('gamma-slider').value),
    };
    window.pywebview.api.run_interactive_scenario(payload);
}

function displayResults(results) {
    AppState.results = results;
    AppState.hasAnalysisRun = true;

    buildSummaryTable(results.summary_data);

    const scenarioButtonsContainer = document.getElementById('scenario-nav-buttons');
    scenarioButtonsContainer.innerHTML = results.detailed_scenarios.map((scenario, index) => `<button class="nav-link ${index === 0 ? 'active' : ''}" onclick="displayScenario(${index})">${scenario.Cenário}</button>`).join('');

    displayScenario(0);
    buildDashboard(results);
    populateToolSelectors();

    document.getElementById('export-button').disabled = false;
    toggleSpinner(false);
    clearModifiedStatus();
    setResultsOutdated(false);
    showPane('analise-pane');
}

function buildSummaryTable(data) {
    const container = document.getElementById('summary-table-container');
    const table = document.createElement('table');
    table.className = 'table table-hover';

    const thead = table.createTHead();
    const headerRow = thead.insertRow();
    const headers = ['Cenário', 'α', 'β', 'γ', 'Iterações', 'Erro O. (%)', 'Erro D. (%)'];
    headers.forEach(text => {
        const th = document.createElement('th');
        th.textContent = text;
        headerRow.appendChild(th);
    });

    const tbody = table.createTBody();
    data.forEach(rowData => {
        const row = tbody.insertRow();
        Object.values(rowData).forEach(text => {
            const cell = row.insertCell();
            cell.textContent = text;
        });
    });

    container.innerHTML = '';
    container.appendChild(table);
}

function buildDashboard(results) {
    const container = document.getElementById('dashboard-content');
    const baseScenario = results.detailed_scenarios[0];
    const totalTrips = baseScenario.matriz_viagens.flat().reduce((a, b) => a + b, 0);

    const tempoTotal = baseScenario.metrics.custo_tempo;
    const distanciaTotal = baseScenario.metrics.custo_distancia;

    const tempoMedio = totalTrips > 0 ? (tempoTotal / totalTrips) : 0;
    const distanciaMedia = totalTrips > 0 ? (distanciaTotal / totalTrips) : 0;

    container.innerHTML = `
        <div class="row g-4">
            <div class="col-md-4">
                <div class="card text-center h-100">
                    <div class="card-body">
                        <h6 class="card-subtitle text-body-secondary">Total de Viagens (Base)</h6>
                        <p class="display-4 fw-bold mb-0">${Math.round(totalTrips)}</p>
                    </div>
                </div>
            </div>
             <div class="col-md-4">
                <div class="card text-center h-100">
                    <div class="card-body">
                        <h6 class="card-subtitle text-body-secondary">Tempo Médio de Viagem</h6>
                        <p class="display-4 fw-bold mb-0">${tempoMedio.toFixed(2)} <span class="fs-4 text-muted">h</span></p>
                    </div>
                </div>
            </div>
             <div class="col-md-4">
                <div class="card text-center h-100">
                    <div class="card-body">
                        <h6 class="card-subtitle text-body-secondary">Distância Média de Viagem</h6>
                        <p class="display-4 fw-bold mb-0">${distanciaMedia.toFixed(2)} <span class="fs-4 text-muted">km</span></p>
                    </div>
                </div>
            </div>
        </div>
    `;

    buildCostComparisonChart(results.detailed_scenarios, results.resistance_names);
    buildGenerationAttractionChart(results.dados_base, baseScenario, results.zonas);
    buildTripDistributionHistograms(baseScenario, results.dados_base, results.resistance_names);
}

function buildCostComparisonChart(scenarios, resistanceNames) {
    const container = document.getElementById('cost-comparison-chart-container');
    const costs = {
        tempo: { label: resistanceNames.tempo, values: [] },
        distancia: { label: resistanceNames.distancia, values: [] },
        preco: { label: resistanceNames.preco, values: [] },
    };
    const scenarioNames = scenarios.map(s => s.Cenário);

    scenarios.forEach(s => {
        costs.tempo.values.push(s.metrics.custo_tempo);
        costs.distancia.values.push(s.metrics.custo_distancia);
        costs.preco.values.push(s.metrics.custo_preco);
    });

    const maxValues = {
        tempo: Math.max(...costs.tempo.values),
        distancia: Math.max(...costs.distancia.values),
        preco: Math.max(...costs.preco.values),
    };

    let chartHtml = `
        <div class="card-header"><h5 class="mb-0">Comparativo de Custos Totais por Cenário</h5></div>
        <div class="card-body">
            <div class="row g-4">`;

    Object.keys(costs).forEach(key => {
        chartHtml += `
            <div class="col-md-4">
                <h6>${costs[key].label}</h6>
                <div class="chart-container">
        `;
        costs[key].values.forEach((value, index) => {
            const percentage = maxValues[key] > 0 ? (value / maxValues[key]) * 100 : 0;
            chartHtml += `
                <div class="bar-wrapper">
                    <div class="bar-label">${scenarioNames[index]}</div>
                    <div class="bar" style="width: ${percentage}%;" title="${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}"></div>
                    <div class="bar-value">${value.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}</div>
                </div>
            `;
        });
        chartHtml += `</div></div>`;
    });

    chartHtml += `</div></div>`;
    container.innerHTML = chartHtml;
}

function buildGenerationAttractionChart(dadosBase, baseScenario, zonas) {
    const container = document.getElementById('generation-attraction-chart-container');
    const calculatedO = Array(zonas.length).fill(0);
    const calculatedD = Array(zonas.length).fill(0);

    baseScenario.matriz_viagens.forEach((row, i) => {
        row.forEach((val, j) => {
            calculatedO[i] += val;
            calculatedD[j] += val;
        });
    });

    let tableHtml = `
        <div class="card-header"><h5 class="mb-0">Geração e Atração por Zona (Cenário Base)</h5></div>
        <div class="card-body table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Zona</th>
                        <th>Geração Original (O)</th>
                        <th>Geração Calculada (ΣTij)</th>
                        <th>Atração Original (D)</th>
                        <th>Atração Calculada (ΣTij)</th>
                    </tr>
                </thead>
                <tbody>
    `;

    zonas.forEach((zona, i) => {
        tableHtml += `
            <tr>
                <td>${zona}</td>
                <td>${dadosBase.o[i].toFixed(0)}</td>
                <td>${calculatedO[i].toFixed(0)}</td>
                <td>${dadosBase.d[i].toFixed(0)}</td>
                <td>${calculatedD[i].toFixed(0)}</td>
            </tr>
        `;
    });

    tableHtml += `</tbody></table></div>`;
    container.innerHTML = tableHtml;
}


function buildTripDistributionHistograms(baseScenario, dadosBase, resistanceNames) {
    const container = document.getElementById('trip-distribution-histograms-container');
    const trips = [];
    baseScenario.matriz_viagens.forEach((row, i) => {
        row.forEach((numTrips, j) => {
            if (numTrips > 0) {
                trips.push({
                    count: numTrips,
                    tempo: dadosBase.tempo[i][j],
                    distancia: dadosBase.distancia[i][j],
                    preco: dadosBase.preco[i][j],
                });
            }
        });
    });

    const createHistogram = (data, title, unit) => {
        const values = data.flatMap(d => Array(Math.round(d.count)).fill(d.value));
        if (values.length === 0) return `<p>Sem dados para ${title}.</p>`;

        const maxVal = Math.max(...values);
        const binCount = 5;
        const binSize = maxVal / binCount;
        const bins = Array(binCount).fill(0);

        values.forEach(val => {
            const binIndex = Math.min(Math.floor(val / binSize), binCount - 1);
            bins[binIndex]++;
        });

        const maxBinValue = Math.max(...bins);
        let histogramHtml = `<h6>${title}</h6><div class="histogram">`;
        bins.forEach((count, i) => {
            const percentage = maxBinValue > 0 ? (count / maxBinValue) * 100 : 0;
            const rangeStart = (i * binSize).toFixed(1);
            const rangeEnd = ((i + 1) * binSize).toFixed(1);
            histogramHtml += `
                <div class="hist-bar-wrapper">
                    <div class="hist-bar" style="height: ${percentage}%;" title="${count} viagens"></div>
                    <div class="hist-label">${rangeStart}-${rangeEnd} ${unit}</div>
                </div>
            `;
        });
        histogramHtml += `</div>`;
        return histogramHtml;
    };

    const tempoData = trips.map(t => ({ value: t.tempo, count: t.count }));
    const distanciaData = trips.map(t => ({ value: t.distancia, count: t.count }));
    const precoData = trips.map(t => ({ value: t.preco, count: t.count }));

    container.innerHTML = `
        <div class="card-header"><h5 class="mb-0">Distribuição de Viagens por Custo (Cenário Base)</h5></div>
        <div class="card-body">
            <div class="row text-center">
                <div class="col-md-4">${createHistogram(tempoData, resistanceNames.tempo, 'h')}</div>
                <div class="col-md-4">${createHistogram(distanciaData, resistanceNames.distancia, 'km')}</div>
                <div class="col-md-4">${createHistogram(precoData, resistanceNames.preco, 'R$')}</div>
            </div>
        </div>
    `;
}

function displayScenario(index) {
    document.querySelectorAll('#scenario-nav-buttons .nav-link').forEach((btn, i) => btn.classList.toggle('active', i === index));
    const scenario = AppState.results.detailed_scenarios[index];
    const baseData = { zonas: AppState.results.zonas, dados: AppState.results.dados_base, resistance_names: AppState.results.resistance_names };

    let metricsHtml = `<h6 class="mb-3">Métricas de Desempenho</h6><ul class="list-group list-group-flush">`;
    metricsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">Tempo Total: <span class="badge fs-5 bg-secondary-subtle text-secondary-emphasis rounded-pill">${scenario.metrics.custo_tempo.toLocaleString('pt-BR', {maximumFractionDigits: 0})} h</span></li>`;
    metricsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">Distância Total: <span class="badge fs-5 bg-secondary-subtle text-secondary-emphasis rounded-pill">${scenario.metrics.custo_distancia.toLocaleString('pt-BR', {maximumFractionDigits: 0})} km</span></li>`;
    metricsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">Preço Total: <span class="badge fs-5 bg-secondary-subtle text-secondary-emphasis rounded-pill">${scenario.metrics.custo_preco.toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'})}</span></li>`;
    metricsHtml += `</ul>`;

    document.getElementById('metrics-container').innerHTML = metricsHtml;
    generateHtmlHeatmap('results-heatmap-wrapper', scenario, baseData);
}

function displayInteractiveResult(result) {
    const params = {
        alpha: parseFloat(document.getElementById('alpha-slider').value),
        beta: parseFloat(document.getElementById('beta-slider').value),
        gamma: parseFloat(document.getElementById('gamma-slider').value),
    };
    const scenarioData = { matriz_viagens: result.matriz_viagens, params };
    const baseData = AppState.lastPayload;

    const custo_tempo = parseFloat(result.metrics['Tempo Total'].replace(/[^\d,]/g, '').replace(',', '.'));
    const custo_distancia = parseFloat(result.metrics['Distância Total'].replace(/[^\d,]/g, '').replace(',', '.'));
    const custo_preco_str = (result.metrics['Preço Total'] || "R$ 0,00").replace("R$ ", "").replace(".", "").replace(",", ".");
    const custo_preco = parseFloat(custo_preco_str);

    updateSensitivityChart(params, { tempo: custo_tempo, distancia: custo_distancia, preco: custo_preco });

    document.getElementById('interactive-metrics').innerHTML = `<h6 class="mb-3">Métricas do Cenário</h6><ul class="list-group list-group-flush"><li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">${baseData.resistance_names.tempo} Total: <span class="badge bg-secondary-subtle text-secondary-emphasis rounded-pill">${result.metrics['Tempo Total']}</span></li><li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">${baseData.resistance_names.distancia} Total: <span class="badge bg-secondary-subtle text-secondary-emphasis rounded-pill">${result.metrics['Distância Total']}</span></li><li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">${baseData.resistance_names.preco} Total: <span class="badge bg-secondary-subtle text-secondary-emphasis rounded-pill">${result.metrics['Preço Total']}</span></li></ul><hr/><p class="text-body-secondary small">Convergiu em <b>${result.num_iter}</b> iterações.</p>`;
    generateHtmlHeatmap('interactive-heatmap', scenarioData, baseData);
}


function generateHtmlHeatmap(containerId, scenarioData, baseData) {
    const matrix = scenarioData.matriz_viagens;
    const container = document.getElementById(containerId);
    if (!matrix || !baseData || !baseData.zonas || !container) return;

    container.innerHTML = '';

    const flatMatrix = matrix.flat().filter(v => v > 0);
    const minVal = flatMatrix.length > 0 ? Math.min(...flatMatrix) : 0;
    const maxVal = flatMatrix.length > 0 ? Math.max(...flatMatrix) : 0;

    let tableHtml = '<table class="heatmap-table"><thead><tr><th>O↓|D→</th>';
    baseData.zonas.forEach(zona => tableHtml += `<th>${zona}</th>`);
    tableHtml += '</tr></thead><tbody>';

    matrix.forEach((row, i) => {
        tableHtml += `<tr><th>${baseData.zonas[i]}</th>`;
        row.forEach((value, j) => {
            const { background, color } = getThemedColorForValue(value, minVal, maxVal);
            tableHtml += `<td style="background-color: ${background}; color: ${color};" data-row="${i}" data-col="${j}" data-value="${value.toFixed(2)}">${Math.round(value)}</td>`;
        });
        tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table>';

    const legendHtml = `
        <div class="mt-3">
            <div class="heatmap-legend"></div>
            <div class="d-flex justify-content-between small text-muted mt-1">
                <span>${minVal.toFixed(0)}</span>
                <span>Nº de Viagens</span>
                <span>${maxVal.toFixed(0)}</span>
            </div>
        </div>
    `;

    container.innerHTML = tableHtml + legendHtml;
    addTooltipEvents(containerId, scenarioData, baseData);
}

function getThemedColorForValue(value, min, max, diverging = false) {
    const theme = document.documentElement.getAttribute('data-bs-theme');
    const neutralBg = theme === 'dark' ? 'hsl(220, 10%, 25%)' : 'hsl(220, 10%, 95%)';
    const neutralText = theme === 'dark' ? 'var(--bs-gray-400)' : 'var(--bs-gray-700)';
    const darkText = 'var(--bs-dark)';
    const lightText = 'var(--bs-light)';

    if (!diverging) {
        if (value <= 0 || max <= min) return { background: neutralBg, color: neutralText };

        const t = (value - min) / (max - min);

        const h = (1 - t) * 120; // 120 (Green) -> 0 (Red)
        const s = 85;
        const l = 60 - 25 * Math.abs(t - 0.5) * 2; // 50 at Green/Red, 60 at Yellow

        const textColor = l > 55 ? darkText : lightText;

        return { background: `hsl(${h}, ${s}%, ${l}%)`, color: textColor };
    } else {
        const absMax = Math.max(Math.abs(min), Math.abs(max));
        if (absMax === 0) return { background: neutralBg, color: neutralText };

        const t = value / absMax; // t from -1 to 1

        const neutralLightness = theme === 'dark' ? 20 : 100;

        let h, s, l;

        if (t < 0) { // Blue range
            h = 240; s = 85;
            l = neutralLightness - (t * (neutralLightness - 55));
        } else { // Red range
            h = 0; s = 85;
            l = neutralLightness - (t * (neutralLightness - 55));
        }

        const textColor = l > 65 ? darkText : lightText;
        return { background: `hsl(${h}, ${s}%, ${l}%)`, color: textColor };
    }
}


function addTooltipEvents(containerId, scenarioData, baseData) {
    const tooltip = document.getElementById('heatmap-tooltip');
    document.getElementById(containerId).querySelectorAll('td').forEach(cell => {
        cell.addEventListener('mouseover', e => {
            const i = parseInt(e.target.dataset.row);
            const j = parseInt(e.target.dataset.col);
            const p = scenarioData.params;
            const r_names = baseData.resistance_names;

            if (!baseData.dados || !baseData.dados.tempo[i] || !baseData.dados.distancia[i] || !baseData.dados.preco[i]) return;

            const impedanceFunc = AppState.lastPayload.config.impedancia.tipo;
            let impedancia;
            if (impedanceFunc === 'exponencial') {
                impedancia = Math.exp(
                    baseData.dados.tempo[i][j] * p.alpha +
                    baseData.dados.distancia[i][j] * p.beta +
                    baseData.dados.preco[i][j] * p.gamma
                );
            } else { // Potência
                impedancia = Math.pow(baseData.dados.tempo[i][j], p.alpha) * Math.pow(baseData.dados.distancia[i][j], p.beta) * Math.pow(baseData.dados.preco[i][j], p.gamma);
            }

            tooltip.innerHTML = `<b>${baseData.zonas[i]} → ${baseData.zonas[j]}</b><hr class="my-1"><b>Viagens: ${parseFloat(e.target.dataset.value).toFixed(2)}</b><hr class="my-1">${r_names.tempo}: ${Number(baseData.dados.tempo[i][j]).toFixed(1)} h<br>${r_names.distancia}: ${Number(baseData.dados.distancia[i][j]).toFixed(1)} km<br>${r_names.preco}: R$ ${Number(baseData.dados.preco[i][j]).toFixed(2)}<hr class="my-1">Resistência: ${impedancia.toFixed(2)}`;

            const rect = e.target.getBoundingClientRect();
            tooltip.style.left = `${rect.right + 10}px`;
            tooltip.style.top = `${rect.top}px`;
            tooltip.classList.add('active');
        });
        cell.addEventListener('mouseout', () => { tooltip.classList.remove('active'); });
    });
}

function showNotification(message, iconClass) {
    const toast = document.getElementById('notification-toast');
    const toastIcon = document.getElementById('notification-icon');
    const toastText = document.getElementById('notification-text');

    toastIcon.innerHTML = `<i class="bi ${iconClass}"></i>`;
    toastText.textContent = message;

    toast.classList.remove('bg-danger');
    if (iconClass.includes('text-danger')) {
        toast.classList.add('bg-danger');
    }

    if (AppState.toastInstance) AppState.toastInstance.show();
}

function exportResultsToPdf() {
    window.pywebview.api.export_to_pdf_dialog();
}

function exportToExcel() {
    const payload = gatherDataFromTables(true);
    if(payload) {
        window.pywebview.api.export_data_to_excel_dialog(payload);
    }
}

// --- NOVAS FUNÇÕES DAS FERRAMENTAS ---

function populateToolSelectors() {
    const scenarios = AppState.results.detailed_scenarios;
    if (!scenarios) return;

    const options = scenarios.map((s, i) => `<option value="${i}">${s.Cenário}</option>`).join('');

    document.getElementById('intrazonal-scenario-select').innerHTML = options;
    document.getElementById('diff-scenario-a-select').innerHTML = options;
    document.getElementById('diff-scenario-b-select').innerHTML = options;

    if (scenarios.length > 1) {
        document.getElementById('diff-scenario-b-select').selectedIndex = 1;
    }
}


function runIntrazonalAnalysis() {
    const scenarioIndex = document.getElementById('intrazonal-scenario-select').value;
    const scenario = AppState.results.detailed_scenarios[scenarioIndex];
    if (!scenario) return;

    let intraZonalTrips = 0;
    let totalTrips = 0;

    scenario.matriz_viagens.forEach((row, i) => {
        row.forEach((value, j) => {
            totalTrips += value;
            if (i === j) {
                intraZonalTrips += value;
            }
        });
    });

    const interZonalTrips = totalTrips - intraZonalTrips;
    const intraPercent = totalTrips > 0 ? (intraZonalTrips / totalTrips) * 100 : 0;
    const interPercent = totalTrips > 0 ? (interZonalTrips / totalTrips) * 100 : 0;

    const container = document.getElementById('intrazonal-results-container');
    container.innerHTML = `
        <div class="row mt-3 text-center">
            <div class="col-6">
                <div class="card bg-secondary-subtle">
                    <div class="card-body">
                        <h6 class="card-subtitle text-body-secondary">Viagens Intrazonais</h6>
                        <p class="display-6 fw-bold mb-0">${Math.round(intraZonalTrips)}</p>
                        <p class="mb-0">(${intraPercent.toFixed(2)}%)</p>
                    </div>
                </div>
            </div>
            <div class="col-6">
                <div class="card">
                     <div class="card-body">
                        <h6 class="card-subtitle text-body-secondary">Viagens Interzonais</h6>
                        <p class="display-6 fw-bold mb-0">${Math.round(interZonalTrips)}</p>
                         <p class="mb-0">(${interPercent.toFixed(2)}%)</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function runScenarioDifferenceAnalysis() {
    const indexA = document.getElementById('diff-scenario-a-select').value;
    const indexB = document.getElementById('diff-scenario-b-select').value;
    const type = document.querySelector('input[name="diff-type"]:checked').value;

    if (indexA === indexB) {
        showNotification("Por favor, selecione dois cenários diferentes para comparar.", "bi-exclamation-triangle-fill text-warning");
        return;
    }

    const scenarioA = AppState.results.detailed_scenarios[indexA];
    const scenarioB = AppState.results.detailed_scenarios[indexB];

    const diffMatrix = scenarioA.matriz_viagens.map((row, i) =>
        row.map((val, j) => {
            const valA = val;
            const valB = scenarioB.matriz_viagens[i][j];
            if (type === 'absolute') {
                return valA - valB;
            } else { // percentage
                return valB === 0 ? (valA > 0 ? 100 : 0) : ((valA - valB) / valB) * 100;
            }
        })
    );

    generateDifferenceHeatmap(diffMatrix, type);
}

function generateDifferenceHeatmap(matrix, type) {
    const container = document.getElementById('difference-heatmap-container');
    const baseData = AppState.results;

    const flatMatrix = matrix.flat().filter(isFinite);
    const minVal = Math.min(...flatMatrix);
    const maxVal = Math.max(...flatMatrix);

    let tableHtml = `<h6 class="text-center mt-3">Diferença ${type === 'absolute' ? 'Absoluta' : 'Percentual'}</h6>`;
    tableHtml += '<table class="heatmap-table"><thead><tr><th>O↓|D→</th>';
    baseData.zonas.forEach(zona => tableHtml += `<th>${zona}</th>`);
    tableHtml += '</tr></thead><tbody>';

    matrix.forEach((row, i) => {
        tableHtml += `<tr><th>${baseData.zonas[i]}</th>`;
        row.forEach((value, j) => {
            const { background, color } = getThemedColorForValue(value, minVal, maxVal, true);
            const displayValue = isFinite(value) ? (type === 'absolute' ? Math.round(value) : `${value.toFixed(1)}%`) : 'N/A';
            tableHtml += `<td style="background-color: ${background}; color: ${color};" title="${isFinite(value) ? value.toFixed(2) : 'N/A'}">${displayValue}</td>`;
        });
        tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table>';

    const legendHtml = `
        <div class="mt-3">
            <div class="heatmap-legend-diff"></div>
            <div class="d-flex justify-content-between small text-muted mt-1">
                <span>${minVal.toFixed(1)}</span>
                <span>Diferença</span>
                <span>+${maxVal.toFixed(1)}</span>
            </div>
        </div>
    `;

    container.innerHTML = tableHtml + legendHtml;
}


function updateSensitivityChart(params, costs) {
    const label = `α:${params.alpha}, β:${params.beta}, γ:${params.gamma}`;
    const existingIndex = AppState.interactiveHistory.findIndex(h => h.label === label);

    if (existingIndex === -1) {
        AppState.interactiveHistory.push({ label, costs });
    } else {
        AppState.interactiveHistory[existingIndex].costs = costs;
    }

    const container = document.getElementById('sensitivity-chart-container');
    const maxTempo = Math.max(...AppState.interactiveHistory.map(h => h.costs.tempo));
    const maxDist = Math.max(...AppState.interactiveHistory.map(h => h.costs.distancia));
    const maxPreco = Math.max(...AppState.interactiveHistory.map(h => h.costs.preco));

    let chartHtml = `
        <div class="card-header"><h5 class="mb-0">Histórico de Custos (Cenário Interativo)</h5></div>
        <div class="card-body">
             <div class="row g-4">
                <div class="col-md-4">
                    <h6>${AppState.resistanceNames.tempo}</h6>
                    <div class="chart-container">
                        ${AppState.interactiveHistory.map(item => `
                            <div class="bar-wrapper">
                                <div class="bar-label" title="${item.label}">${item.label}</div>
                                <div class="bar" style="width: ${maxTempo > 0 ? (item.costs.tempo / maxTempo) * 100 : 0}%;" title="${item.costs.tempo.toLocaleString('pt-BR')}"></div>
                                <div class="bar-value">${item.costs.tempo.toLocaleString('pt-BR', {maximumFractionDigits: 0})}</div>
                            </div>`).join('')}
                    </div>
                </div>
                <div class="col-md-4">
                    <h6>${AppState.resistanceNames.distancia}</h6>
                     <div class="chart-container">
                        ${AppState.interactiveHistory.map(item => `
                            <div class="bar-wrapper">
                                <div class="bar-label" title="${item.label}">${item.label}</div>
                                <div class="bar" style="width: ${maxDist > 0 ? (item.costs.distancia / maxDist) * 100 : 0}%;" title="${item.costs.distancia.toLocaleString('pt-BR')}"></div>
                                <div class="bar-value">${item.costs.distancia.toLocaleString('pt-BR', {maximumFractionDigits: 0})}</div>
                            </div>`).join('')}
                    </div>
                </div>
                <div class="col-md-4">
                    <h6>${AppState.resistanceNames.preco}</h6>
                     <div class="chart-container">
                        ${AppState.interactiveHistory.map(item => `
                            <div class="bar-wrapper">
                                <div class="bar-label" title="${item.label}">${item.label}</div>
                                <div class="bar" style="width: ${maxPreco > 0 ? (item.costs.preco / maxPreco) * 100 : 0}%;" title="${item.costs.preco.toLocaleString('pt-BR')}"></div>
                                <div class="bar-value">${item.costs.preco.toLocaleString('pt-BR', {maximumFractionDigits: 0})}</div>
                            </div>`).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
    container.innerHTML = chartHtml;
}

function runAccessibilityAnalysis() {
    const payload = gatherDataFromTables();
    if (!payload) return;

    showNotification("Calculando Acessibilidade...", "bi-hourglass-split");

    payload.params = {
        alpha: parseFloat(document.getElementById('alpha-slider').value),
        beta: parseFloat(document.getElementById('beta-slider').value),
        gamma: parseFloat(document.getElementById('gamma-slider').value),
    };

    window.pywebview.api.run_accessibility_analysis(payload);
}

function displayAccessibilityResults(results) {
    const container = document.getElementById('accessibility-results-container');
    if (!results || results.length === 0) {
        container.innerHTML = '<div class="alert alert-warning">Não foi possível calcular a acessibilidade.</div>';
        return;
    }

    let tableHtml = `
        <table class="table table-striped">
            <thead>
                <tr>
                    <th>Zona</th>
                    <th>Índice de Acessibilidade (Normalizado)</th>
                    <th>Pontuação Bruta</th>
                </tr>
            </thead>
            <tbody>
    `;

    results.forEach(item => {
        tableHtml += `
            <tr>
                <td>${item.zona}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress" style="height: 20px; flex-grow: 1; margin-right: 10px;" role="progressbar" aria-valuenow="${item.score_normalizado.toFixed(2)}" aria-valuemin="0" aria-valuemax="100">
                            <div class="progress-bar" style="width: ${item.score_normalizado.toFixed(2)}%;">${item.score_normalizado.toFixed(2)}</div>
                        </div>
                    </div>
                </td>
                <td>${item.score.toFixed(2)}</td>
            </tr>
        `;
    });

    tableHtml += `
            </tbody>
        </table>
    `;
    container.innerHTML = tableHtml;
    showNotification("Cálculo de acessibilidade concluído!", "bi-check-circle-fill text-success");
}