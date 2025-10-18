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
    validateAllCells();
    setResultsOutdated(false);
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
    // document.getElementById('analise-nav-link')?.classList.toggle('disabled', show); // Removido daqui, validateAllCells vai cuidar disso

    const runButton = document.getElementById('run-analysis-button');
    if (runButton) {
        runButton.disabled = show; // O botão fica desabilitado ENQUANTO roda
        runButton.innerHTML = show
            ? `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Executando...`
            : `<i class="bi bi-play-circle-fill me-2"></i>Executar Análise Completa`;
    }

    // Adiciona a chamada aqui
    validateAllCells(); // Reavalia o estado dos botões/links após o spinner mudar
}

function setResultsOutdated(isOutdated) {
    const resultsLink = document.getElementById('analise-nav-link');
    const exportButton = document.getElementById('export-button');
    const linksToToggle = ['interactive-nav-link', 'dashboard-nav-link', 'analysis-tools-nav-link'];

    // Mostra/Esconde o indicador de aviso (!) APENAS se uma análise já foi feita E está desatualizado
    document.getElementById('results-outdated-indicator')?.classList.toggle('d-none', !(isOutdated && AppState.hasAnalysisRun));

    // Desabilita exportação se desatualizado OU se nenhuma análise foi feita
    if (exportButton) {
        exportButton.disabled = isOutdated || !AppState.hasAnalysisRun;
    }

    // Habilita/Desabilita o link "Resultados"
    if (resultsLink) {
        // Desabilita se está desatualizado OU se nenhuma análise foi feita
        const shouldDisable = isOutdated || !AppState.hasAnalysisRun;
        resultsLink.classList.toggle('disabled', shouldDisable);
        if (shouldDisable) {
            resultsLink.classList.remove('active');
        }
    }

    // Habilita/Desabilita os outros links dependentes
    linksToToggle.forEach(id => {
        const link = document.getElementById(id);
        if (link) {
            const shouldDisable = isOutdated || !AppState.hasAnalysisRun;
            link.classList.toggle('disabled', shouldDisable);
            if (shouldDisable) {
                link.classList.remove('active');
            }
        }
    });
}

function validateAllCells() {
    const cells = document.querySelectorAll('.editable-table .form-control-plaintext');
    let allValid = true;
    cells.forEach(cell => {
        const value = cell.value.trim();
        const numValue = parseFloat(value);
        if (!cell.validity.valid || value === '' || isNaN(numValue) || numValue < 0) {
            allValid = false;
            cell.classList.add('is-invalid');
        } else {
             cell.classList.remove('is-invalid');
        }
    });

    const runButton = document.getElementById('run-analysis-button');

    // Habilita/Desabilita APENAS o botão principal de análise
    if (runButton) {
        // Desabilita se não for válido OU se uma análise já estiver rodando
        runButton.disabled = !allValid || AppState.isAnalysisRunning;
    }

    // NÃO mais habilita/desabilita os links aqui diretamente

    // // Se os dados são inválidos E a aba de entrada de dados não está ativa,
    // // força a exibição da aba de entrada de dados. (Opcional manter)
    // const dataPaneActive = document.getElementById('data-pane').classList.contains('active');
    // if (!allValid && !dataPaneActive && !AppState.isAnalysisRunning) {
    //     showPane('data-pane');
    // }

    return allValid;
}

function addValidationListeners() {
    document.querySelectorAll('.editable-table .form-control-plaintext').forEach(cell => {
        cell.addEventListener('input', (e) => {
            e.target.classList.add('cell-modified');

            // --- Adicionado aqui ---
            // Se uma análise já foi feita, qualquer edição desatualiza os resultados
            if (AppState.hasAnalysisRun) {
                setResultsOutdated(true); // Isso vai desabilitar o link 'Resultados'
            }
            // --- Fim da adição ---

            // Chama a validação GERAL (que agora só afeta o botão Executar)
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
    // Reseta o estado, pois novos dados foram carregados/inicializados
    AppState.hasAnalysisRun = false; // Importante para a lógica do setResultsOutdated

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
    clearModifiedStatus();
    validateAllCells();
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
    AppState.hasAnalysisRun = true; // Marca que uma análise já foi executada

    buildSummaryTable(results.summary_data);

    const scenarioButtonsContainer = document.getElementById('scenario-nav-buttons');
    scenarioButtonsContainer.innerHTML = results.detailed_scenarios.map((scenario, index) => `<button class="nav-link ${index === 0 ? 'active' : ''}" onclick="displayScenario(${index})">${scenario.Cenário}</button>`).join('');

    displayScenario(0);
    // As chamadas para buildDashboard e populateToolSelectors já foram removidas

    document.getElementById('export-button').disabled = false; // Habilita exportação
    toggleSpinner(false); // Esconde o spinner
    clearModifiedStatus(); // Remove marcação de células modificadas

    // --- Adicionado/Modificado aqui ---
    // Marca os resultados como NÃO desatualizados e HABILITA os links
    setResultsOutdated(false);
    // Garante especificamente que o link 'Resultados' está habilitado
    document.getElementById('analise-nav-link')?.classList.remove('disabled');
    // Habilita também os outros links dependentes (se necessário no futuro)
    const linksToEnable = ['interactive-nav-link', 'dashboard-nav-link', 'analysis-tools-nav-link'];
    linksToEnable.forEach(id => {
         document.getElementById(id)?.classList.remove('disabled');
    });
    // --- Fim da modificação ---

    showPane('analise-pane'); // Mostra a aba de resultados
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

// --- INÍCIO DO TRECHO PARA SUBSTITUIR ---

function getViridisColor(t) {
    // Pontos aproximados do colormap Viridis (t=0 a t=1) -> [r, g, b]
    const colors = [
        [68, 1, 84],    // 0.0 Púrpura escuro
        [59, 82, 139],  // 0.25 Azul
        [33, 145, 140], // 0.5 Verde-azulado
        [94, 200, 99],  // 0.75 Verde
        [253, 231, 37]  // 1.0 Amarelo
    ];

    // Garante que t esteja no intervalo [0, 1]
    t = Math.max(0, Math.min(1, t));

    // Encontra os dois pontos de cor entre os quais t se encontra
    const i = Math.floor(t * (colors.length - 1));
    const localT = (t * (colors.length - 1)) - i;

    // Trata os casos extremos
    if (i >= colors.length - 1) return colors[colors.length - 1];

    const c1 = colors[i];
    const c2 = colors[i + 1];

    // Interpola linearmente entre as cores c1 e c2
    const r = Math.round(c1[0] + (c2[0] - c1[0]) * localT);
    const g = Math.round(c1[1] + (c2[1] - c1[1]) * localT);
    const b = Math.round(c1[2] + (c2[2] - c1[2]) * localT);

    return [r, g, b];
}

function getTextColorForBackground(rgb) {
    // Verificação simples de brilho para cor do texto (claro ou escuro)
    // Fórmula de luminosidade percebida
    const brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000;
    // Retorna a variável CSS correspondente para texto escuro ou claro
    return brightness > 128 ? 'var(--bs-dark)' : 'var(--bs-light)';
}

function getThemedColorForValue(value, min, max, diverging = false) {
    const theme = document.documentElement.getAttribute('data-bs-theme');
    const neutralBg = theme === 'dark' ? 'hsl(220, 10%, 25%)' : 'hsl(220, 10%, 95%)';
    const neutralText = theme === 'dark' ? 'var(--bs-gray-400)' : 'var(--bs-gray-700)';

    if (diverging) {
         const darkText = 'var(--bs-dark)';
         const lightText = 'var(--bs-light)';
         const absMax = Math.max(Math.abs(min), Math.abs(max));
         // Retorna cor neutra se o valor máximo absoluto for zero ou se o valor não for finito
         if (absMax === 0 || !isFinite(value)) return { background: neutralBg, color: neutralText };

         const t = value / absMax; // t varia de -1 a 1
         const neutralLightness = theme === 'dark' ? 20 : 100; // Ajuste a claridade neutra para temas escuro/claro
         let h, s, l;

         // Define a cor baseada no valor ser negativo (azul) ou positivo (vermelho)
         if (t < 0) { // Faixa Azul
             h = 240; s = 85;
             l = neutralLightness + (t * (neutralLightness - 55)); // Interpola a claridade
         } else { // Faixa Vermelha
             h = 0; s = 85;
             l = neutralLightness - (t * (neutralLightness - 55)); // Interpola a claridade
         }
         // Garante que a claridade esteja no intervalo [0, 100]
         l = Math.max(0, Math.min(100, l));

         // Determina a cor do texto com base na claridade do fundo
         const textColor = l > 65 ? darkText : lightText; // Ajuste o limiar se necessário
         return { background: `hsl(${h}, ${s}%, ${l}%)`, color: textColor };
    }
    // --- NOVA lógica Viridis para heatmap padrão ---
    else {
        // Retorna cor neutra para valores inválidos, zero, ou se min >= max
        if (value <= 0 || max <= min || !isFinite(value)) return { background: neutralBg, color: neutralText };

        const t = (value - min) / (max - min); // Normaliza o valor para o intervalo 0-1
        const rgb = getViridisColor(t); // Obtém a cor Viridis correspondente
        const bgColor = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`; // Formata como string RGB
        const textColor = getTextColorForBackground(rgb); // Determina a cor do texto

        return { background: bgColor, color: textColor };
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
