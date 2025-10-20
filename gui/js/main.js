const AppState = {
    results: {},
    lastPayload: null, // Guarda a última estrutura de dados enviada para análise
    zoneCount: 0,
    resistanceNames: [], // AGORA É UM ARRAY DINÂMICO de strings
    resistanceData: {}, // Guarda temporariamente os dados das resistências ao adicionar/remover zonas
    toastInstance: null,
    hasAnalysisRun: false,
    isAnalysisRunning: false,
    interactiveHistory: [],
};

const MAX_RESISTANCES = 5; // Define o limite máximo

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
    // --- Load Theme --- (Manter como está)
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
    const icon = document.querySelector('#theme-toggler i');
    icon.classList.toggle('bi-moon-stars-fill', savedTheme === 'dark');
    icon.classList.toggle('bi-sun-fill', savedTheme === 'light');

    // --- Toast Initialization --- (Manter como está)
    const toastEl = document.getElementById('notification-toast');
    if (toastEl) AppState.toastInstance = new bootstrap.Toast(toastEl, { delay: 3500 });

    // --- Atalhos de Teclado --- (Manter como está)
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

    // --- Listener para Sliders Interativos (removido daqui) ---
    // A secção forEach que adicionava listeners aos sliders fixos ('alpha-slider', etc.) FOI REMOVIDA

    // --- Inicialização das Tabelas ---
    initializeEmptyTables(5); // Inicializa com 5 zonas e 1 resistência padrão
    validateAllCells(); // Validação inicial
    setResultsOutdated(false); // Estado inicial dos resultados
    updateAddRemoveResistanceButtons(); // Atualiza estado dos botões +/- resistência
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

// Substitua a função addValidationListeners existente por esta
function addValidationListeners() {
    // Seleciona todos os inputs DENTRO dos containers corretos
    document.querySelectorAll('#od-table input, #dynamic-resistance-content-container input.form-control-plaintext').forEach(cell => {
        // Remove listener antigo para evitar duplicação ao repopular
        cell.removeEventListener('input', handleCellInput);
        // Adiciona o novo listener
        cell.addEventListener('input', handleCellInput);
    });
    // Adiciona listener para nomes das zonas na tabela OD
     document.querySelectorAll('#od-table th[contenteditable="true"]').forEach(th => {
         th.removeEventListener('blur', handleZoneNameBlur); // Evita duplicados
         th.addEventListener('blur', handleZoneNameBlur);
     });
}

// Nova função handler separada para facilitar remoção/adição
function handleCellInput(e) {
    e.target.classList.add('cell-modified');
    if (AppState.hasAnalysisRun) {
        setResultsOutdated(true);
    }
    validateAllCells();
}
// Handler para o blur do nome da zona
function handleZoneNameBlur(e) {
     const rowIndex = Array.from(e.target.closest('tbody').children).indexOf(e.target.closest('tr'));
     updateZoneNames(e.target, rowIndex);
 }

function clearModifiedStatus() {
    document.querySelectorAll('.cell-modified').forEach(cell => cell.classList.remove('cell-modified'));
}

// Substitua a função gatherDataFromTables existente por esta
function gatherDataFromTables(forSaving = false) {
    if (!validateAllCells() && !forSaving) {
        showNotification("Existem valores inválidos ou vazios nas tabelas. Por favor, corrija.", "bi-exclamation-triangle-fill text-danger");
        return null;
    }

    const odTable = document.getElementById('od-table');
    const zonas = Array.from(odTable.querySelectorAll('tbody th')).map(th => th.textContent.trim());
    const o_raw = Array.from(odTable.querySelectorAll('tbody td:nth-child(2) input')).map(input => input.value);
    const d_raw = Array.from(odTable.querySelectorAll('tbody td:nth-child(3) input')).map(input => input.value);

    // Coleta dados das resistências dinâmicas
    const resistances_raw = {};
    const resistancePanes = document.querySelectorAll('#dynamic-resistance-content-container .tab-pane');
    resistancePanes.forEach(pane => {
        const resistanceName = pane.getAttribute('data-resistance-name');
        if (resistanceName) {
            const table = pane.querySelector('table');
            resistances_raw[resistanceName] = Array.from(table.rows).slice(1).map(row =>
                Array.from(row.cells).slice(1).map(cell => cell.querySelector('input').value)
            );
        }
    });

    // Se não houver resistências definidas e não for para salvar, retorna erro
    if (Object.keys(resistances_raw).length === 0 && !forSaving) {
        showNotification("Nenhuma matriz de resistência foi definida. Adicione pelo menos uma.", "bi-exclamation-triangle-fill text-danger");
        return null;
    }


    // --- Configurações (Furness, Impedância, Intrazonal) ---
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
    // --- Fim Configurações ---


    // Se for apenas para salvar (ex: ao adicionar/remover zona/resistência)
    if (forSaving) {
        // Retorna a estrutura que populateEditableData espera
        return {
             zonas,
             dados: {
                 o: o_raw,
                 d: d_raw,
                 resistencias: resistances_raw // Dicionário {nome: matriz_raw}
             }
             // resistance_names não é mais necessário aqui, será derivado das chaves
        };
    }

    // Se for para análise, converte para números
    const dados = {
        o: o_raw.map(v => parseFloat(v) || 0),
        d: d_raw.map(v => parseFloat(v) || 0),
        resistencias: {} // Dicionário {nome: matriz_numérica}
    };
    Object.keys(resistances_raw).forEach(key => {
        dados.resistencias[key] = resistances_raw[key].map(row => row.map(cell => parseFloat(cell) || 0));
    });

    // Retorna payload completo para a API Python
    return {
        zonas,
        dados, // Contém o, d, e o dict resistencias
        config: config
        // resistance_names não é mais enviado, a API deriva do dict `dados.resistencias`
    };
}


// Substitua as funções addZone e removeZone existentes

function addZone() {
    if (AppState.zoneCount >= 15) return; // Limite de zonas (ajuste se necessário)
    const currentData = gatherDataFromTables(true); // Coleta dados no formato {zonas, dados:{o, d, resistencias}}
    const newZoneIndex = AppState.zoneCount;

    // Tenta restaurar dados da zona removida (se implementado anteriormente)
    // const restoredZoneData = AppState.removedZoneData?.pop();
    // const newZoneName = restoredZoneData ? restoredZoneData.zona : `Zona ${newZoneIndex + 1}`;
    // const newO = restoredZoneData ? restoredZoneData.o : '0';
    // const newD = restoredZoneData ? restoredZoneData.d : '0';
    // Se não usar a restauração de zona:
    const newZoneName = `Zona ${newZoneIndex + 1}`;
    const newO = '0';
    const newD = '0';


    currentData.zonas.push(newZoneName);
    currentData.dados.o.push(newO);
    currentData.dados.d.push(newD);

    // Itera sobre CADA matriz de resistência existente
    Object.keys(currentData.dados.resistencias).forEach(key => {
        const matrix = currentData.dados.resistencias[key];
        // Adiciona nova COLUNA às linhas existentes
        matrix.forEach(row => row.push('0')); // Adiciona '0' no final de cada linha
        // Adiciona nova LINHA preenchida com '0's
        matrix.push(Array(newZoneIndex + 1).fill('0'));
    });

    populateEditableData(currentData); // Repopula tudo
}

function removeZone() {
    if (AppState.zoneCount <= 2) return; // Mínimo de 2 zonas
    const currentData = gatherDataFromTables(true);

    // --- Guardar dados da última zona (opcional, se usar restauração) ---
    // const removedIndex = AppState.zoneCount - 1;
    // const removedData = { ... }; // Lógica de guardar que você tinha
    // AppState.removedZoneData.push(removedData);
    // --- Fim da secção de guardar ---

    currentData.zonas.pop();
    currentData.dados.o.pop();
    currentData.dados.d.pop();

    // Itera sobre CADA matriz de resistência
    Object.keys(currentData.dados.resistencias).forEach(key => {
        const matrix = currentData.dados.resistencias[key];
        matrix.pop(); // Remove a última linha
        matrix.forEach(row => row.pop()); // Remove o último elemento (coluna) de cada linha restante
    });

    populateEditableData(currentData);
}


function initializeEmptyTables(numZonas) {
    const zonas = Array.from({ length: numZonas }, (_, i) => `Zona ${i + 1}`);
    const emptyO = Array(numZonas).fill('0');
    const emptyMatrix = Array(numZonas).fill(null).map(() => Array(numZonas).fill('0'));

    // Inicializa com UMA resistência padrão chamada "Resistencia1"
    const initialResistances = {
        "Resistencia1": emptyMatrix
    };

    populateEditableData({
        zonas,
        dados: {
            o: emptyO,
            d: emptyO,
            resistencias: initialResistances // Usa o dicionário
        }
    });
}

// Adicione estas novas funções ao ficheiro

function updateAddRemoveResistanceButtons() {
    const addButton = document.getElementById('add-resistance-btn');
    // Desabilita Adicionar se atingiu o limite
    if (addButton) addButton.disabled = AppState.resistanceNames.length >= MAX_RESISTANCES;

    // Habilita/Desabilita botões de remover individuais (se existirem)
     document.querySelectorAll('.remove-resistance-btn').forEach(btn => {
         // Desabilita remover se for a única resistência
         btn.disabled = AppState.resistanceNames.length <= 1;
     });
}

function addResistance() {
    if (AppState.resistanceNames.length >= MAX_RESISTANCES) {
        showNotification(`Máximo de ${MAX_RESISTANCES} resistências atingido.`, "bi-info-circle-fill text-info");
        return;
    }
    const currentData = gatherDataFromTables(true);
    let newResistanceName = `Resistencia${AppState.resistanceNames.length + 1}`;
    let counter = 2;
    // Garante nome único
    while (currentData.dados.resistencias.hasOwnProperty(newResistanceName)) {
        newResistanceName = `Resistencia${AppState.resistanceNames.length + counter}`;
        counter++;
    }

    // Cria nova matriz vazia (preenchida com '0')
    const numZonas = currentData.zonas.length;
    const newMatrix = Array(numZonas).fill(null).map(() => Array(numZonas).fill('0'));
    currentData.dados.resistencias[newResistanceName] = newMatrix;

    populateEditableData(currentData); // Repopula a UI
    // Opcional: Ativar a aba recém-criada
    const newTabButton = document.querySelector(`#resistance-tabs button[data-bs-target="#pane-${newResistanceName}"]`);
    if (newTabButton) {
        const tab = new bootstrap.Tab(newTabButton);
        tab.show();
    }
}

function removeResistance(resistanceName) {
    if (AppState.resistanceNames.length <= 1) {
         showNotification("Deve haver pelo menos uma resistência.", "bi-exclamation-triangle-fill text-warning");
        return;
    }
    // Confirmação (opcional mas recomendado)
    if (!confirm(`Tem certeza que deseja remover a resistência "${resistanceName}"?`)) {
        return;
    }

    const currentData = gatherDataFromTables(true);
    if (currentData.dados.resistencias.hasOwnProperty(resistanceName)) {
        delete currentData.dados.resistencias[resistanceName]; // Remove do dicionário
        populateEditableData(currentData); // Repopula a UI
         // Marca resultados como desatualizados se uma análise já foi feita
        if (AppState.hasAnalysisRun) {
            setResultsOutdated(true);
        }
    } else {
        console.error("Tentativa de remover resistência inexistente:", resistanceName);
    }
}

function renameResistance(oldName) {
    const newName = prompt(`Digite o novo nome para a resistência "${oldName}":`, oldName);
    if (newName && newName.trim() !== "" && newName !== oldName) {
        const trimmedNewName = newName.trim();
        const currentData = gatherDataFromTables(true);

        // Verifica se o novo nome já existe
        if (currentData.dados.resistencias.hasOwnProperty(trimmedNewName)) {
            showNotification(`O nome "${trimmedNewName}" já está em uso.`, "bi-exclamation-triangle-fill text-warning");
            return;
        }

        if (currentData.dados.resistencias.hasOwnProperty(oldName)) {
            // Renomeia a chave no dicionário
            currentData.dados.resistencias[trimmedNewName] = currentData.dados.resistencias[oldName];
            delete currentData.dados.resistencias[oldName];
            populateEditableData(currentData); // Repopula a UI
            // Marca resultados como desatualizados se uma análise já foi feita
             if (AppState.hasAnalysisRun) {
                 setResultsOutdated(true);
             }
            // Opcional: Reativar a aba renomeada
            const newTabButton = document.querySelector(`#resistance-tabs button[data-bs-target="#pane-${trimmedNewName}"]`);
            if (newTabButton) {
                 const tab = new bootstrap.Tab(newTabButton);
                 tab.show();
            }
        }
    } else if (newName !== null && newName !== oldName) { // Se não cancelou mas o nome é inválido
        showNotification("Nome inválido.", "bi-exclamation-triangle-fill text-warning");
    }
}

// Nova função auxiliar para gerar a UI das resistências
function generateResistanceTabsAndContent(resistenciasDict, zonas) {
    const tabsContainer = document.getElementById('resistance-tabs');
    const contentContainer = document.getElementById('dynamic-resistance-content-container');
    tabsContainer.innerHTML = ''; // Limpa abas existentes
    contentContainer.innerHTML = ''; // Limpa conteúdo existente
    AppState.resistanceNames = Object.keys(resistenciasDict); // Atualiza nomes no estado

    let isFirstTab = true;
    AppState.resistanceNames.forEach(name => {
        const isActive = isFirstTab;
        const safeNameId = name.replace(/\s+/g, '-'); // Cria ID seguro para HTML

        // Cria Botão da Aba
        const tabButton = `
            <li class="nav-item" role="presentation">
                <button class="nav-link ${isActive ? 'active' : ''}" id="tab-${safeNameId}" data-bs-toggle="tab" data-bs-target="#pane-${safeNameId}" type="button" role="tab" title="Duplo clique para renomear">
                    <span ondblclick="renameResistance('${name}')">${name}</span>
                    <button class="btn btn-sm btn-outline-danger border-0 ms-2 py-0 remove-resistance-btn" onclick="removeResistance('${name}')" title="Remover Resistência">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </button>
            </li>`;
        tabsContainer.innerHTML += tabButton;

        // Cria Painel com Tabela
        let tableHTML = `<div class="tab-pane fade ${isActive ? 'show active' : ''}" id="pane-${safeNameId}" role="tabpanel" data-resistance-name="${name}">`; // Guarda o nome original aqui
        tableHTML += `<table class="table table-sm editable-table mt-2" id="matrix-${safeNameId}">`;
        tableHTML += `<thead><tr><th> </th>${zonas.map(z => `<th>${z}</th>`).join('')}</tr></thead>`;
        tableHTML += `<tbody>`;
        const matrixData = resistenciasDict[name];
        zonas.forEach((zona, i) => {
            tableHTML += `<tr><th>${zona}</th>`;
            if (matrixData && matrixData.length > i) { // Verifica se a linha existe
                 tableHTML += matrixData[i].map(val => `<td><input type="number" class="form-control-plaintext" value="${val}" min="0" step="any" required></td>`).join('');
            } else {
                // Linha faltando? Preenche com inputs vazios/zeros
                tableHTML += zonas.map(() => `<td><input type="number" class="form-control-plaintext" value="0" min="0" step="any" required></td>`).join('');
                 console.warn(`Dados ausentes para resistência '${name}', zona '${zona}' (linha ${i})`);
            }
            tableHTML += `</tr>`;
        });
        tableHTML += `</tbody></table></div>`;
        contentContainer.innerHTML += tableHTML;

        isFirstTab = false;
    });

    updateAddRemoveResistanceButtons(); // Atualiza estado dos botões + e -
}

// Substitua a função populateEditableData existente por esta
function populateEditableData(data) {
    console.log("Populating data:", data); // Para debug
    // Reseta o estado, pois novos dados foram carregados/inicializados
    AppState.hasAnalysisRun = false; // Importante para a lógica do setResultsOutdated

    AppState.zoneCount = data.zonas.length;
    // AppState.resistanceNames será atualizado por generateResistanceTabsAndContent

    // --- Popula Tabela O/D ---
    const odTableBody = document.getElementById('od-table').querySelector('tbody');
    if (!odTableBody) { // Cria a tabela OD se não existir (primeira carga)
        const odTable = document.getElementById('od-table');
        odTable.innerHTML = `<thead><tr><th>Zona</th><th>Origens (O)</th><th>Destinos (D)</th></tr></thead><tbody></tbody>`;
    }
    document.getElementById('od-table').querySelector('tbody').innerHTML = data.zonas.map((zona, i) =>
        `<tr>
            <th contenteditable="true">${zona}</th>
            <td><input type="number" class="form-control-plaintext" value="${data.dados.o[i]}" min="0" step="any" required></td>
            <td><input type="number" class="form-control-plaintext" value="${data.dados.d[i]}" min="0" step="any" required></td>
         </tr>`
    ).join('');

    // --- Gera UI Dinâmica para Resistências ---
    generateResistanceTabsAndContent(data.dados.resistencias, data.zonas);

    // --- Adiciona Listeners e Valida ---
    addValidationListeners(); // Adiciona listeners aos novos inputs
    clearModifiedStatus(); // Limpa marcações de modificação
    validateAllCells(); // Valida todos os campos

    // --- Atualiza UI Interativa (Sliders) ---
    updateInteractiveSliders();

    // --- Atualiza Estado dos Resultados ---
    // Como estamos populando com novos dados, os resultados anteriores (se existirem) ficam inválidos
    setResultsOutdated(true); // Marca como desatualizado
     // Esconde conteúdo da análise detalhada se estava visível
    document.getElementById('detailed-analysis-content')?.classList.add('d-none');
    document.getElementById('detailed-analysis-placeholder')?.classList.remove('d-none');
     // Limpa botões de cenário
     document.getElementById('scenario-nav-buttons').innerHTML = '';
}

function updateZoneNames(element, rowIndex) {
    const newName = element.textContent.trim();
    if (newName === "") {
        // Se o nome ficar vazio, restaura o nome anterior ou um padrão
        showNotification("O nome da zona não pode ficar vazio.", "bi-exclamation-triangle-fill text-danger");
        // Força repopulação para restaurar visualmente (ou pega o nome antigo do AppState se guardado)
        populateEditableData(gatherDataFromTables(true));
        return;
    }
    // Apenas repopula para garantir que os cabeçalhos das matrizes sejam atualizados
    // Não é a forma mais eficiente, mas garante consistência visual
    populateEditableData(gatherDataFromTables(true));
}

function runFullAnalysis() {
    const payload = gatherDataFromTables();
    if (!payload) return;
    toggleSpinner(true);
    showNotification("Executando análise completa...", "bi-hourglass-split");
    AppState.lastPayload = payload;
    AppState.interactiveHistory = []; // Limpa o histórico interativo ao rodar análise completa
    window.pywebview.api.run_analysis(payload);
}

function updateInteractiveSliders() {
    const container = document.getElementById('dynamic-param-sliders-container');
    container.innerHTML = ''; // Limpa sliders antigos

    if (AppState.resistanceNames.length === 0) {
        container.innerHTML = '<p class="text-muted small">Adicione pelo menos uma resistência na aba "Dados de Entrada".</p>';
        return;
    }

    AppState.resistanceNames.forEach(name => {
        // Tenta buscar valor anterior se existir, senão default 1.0
        const sliderId = `param-${name.replace(/\s+/g, '-')}-slider`;
        const valueId = `param-${name.replace(/\s+/g, '-')}-value`;
        const previousValue = document.getElementById(sliderId)?.value || "1.0"; // Guarda valor anterior

        container.innerHTML += `
            <div class="mb-2">
                <label for="${sliderId}" class="form-label">${name}: <span id="${valueId}">${previousValue}</span></label>
                <input type="range" class="form-range param-slider" min="0" max="5" step="0.1" value="${previousValue}" id="${sliderId}" data-param-name="${name}">
            </div>`;
    });

    // Adiciona listener DEPOIS de criar os sliders
    addInteractiveSliderListeners();
}

// Adicione esta nova função
function addInteractiveSliderListeners() {
    // A função debounce não é mais necessária aqui, pois handleSliderInput a chama diretamente
    document.querySelectorAll('.param-slider').forEach(slider => {
        const valueSpanId = slider.id.replace('-slider', '-value');
        const valueSpan = document.getElementById(valueSpanId);

        // Remove listener antigo para evitar duplicação
        slider.removeEventListener('input', handleSliderInput);
        // Adiciona novo listener
        slider.addEventListener('input', handleSliderInput);

        // Atualiza o valor inicial (caso não tenha sido pego corretamente)
        if(valueSpan) valueSpan.textContent = slider.value;
    });
}

function handleSliderInput(e) {
    const valueSpanId = e.target.id.replace('-slider', '-value');
    const valueSpan = document.getElementById(valueSpanId);
    if (valueSpan) valueSpan.textContent = e.target.value;
    // Chama a função debounced que executa o cenário
    debounce(runInteractiveScenario, 300)(); // Chama imediatamente a versão debounced
}

function runInteractiveScenario() {
    const payload = gatherDataFromTables(); // Coleta dados atuais (incluindo resistências)
    if (!payload) return;

    // Coleta parâmetros dinâmicos dos sliders
    payload.params = {};
    document.querySelectorAll('.param-slider').forEach(slider => {
        const paramName = slider.getAttribute('data-param-name');
        if (paramName) {
            payload.params[paramName] = parseFloat(slider.value);
        }
    });

    // Guarda o payload para referência (ex: tooltips)
    AppState.lastPayload = payload; // lastPayload agora tem a estrutura dinâmica

    console.log("Running interactive scenario with payload:", payload); // Debug
    window.pywebview.api.run_interactive_scenario(payload); // Chama a API Python
}

function displayResults(results) {
    // results agora contém: { summary_data: [...], detailed_scenarios: [...], zonas: [], resistance_names: [], dados_base: {o, d, resistencias} }
    AppState.results = results; // Guarda os resultados completos
    AppState.hasAnalysisRun = true;

    // --- Constrói Tabela Resumo (precisa ser adaptada) ---
    buildSummaryTable(results.summary_data, results.resistance_names);

    // --- Cria Botões de Cenário ---
    const scenarioButtonsContainer = document.getElementById('scenario-nav-buttons');
    scenarioButtonsContainer.innerHTML = results.detailed_scenarios.map((scenario, index) =>
        `<button class="nav-link ${index === 0 ? 'active' : ''}" onclick="displayScenario(${index})">${scenario.Cenário}</button>`
    ).join('');

    // --- Exibe Primeiro Cenário ---
    displayScenario(0);

    // --- Habilita Controles e Atualiza Estado ---
    document.getElementById('export-button').disabled = false;
    toggleSpinner(false);
    clearModifiedStatus();
    setResultsOutdated(false); // Marca como atualizado
    document.getElementById('analise-nav-link')?.classList.remove('disabled');
    const linksToEnable = ['interactive-nav-link', 'dashboard-nav-link', 'analysis-tools-nav-link'];
    linksToEnable.forEach(id => {
         document.getElementById(id)?.classList.remove('disabled');
    });

     // Mostra conteúdo da análise detalhada e esconde placeholder
     document.getElementById('detailed-analysis-content')?.classList.remove('d-none');
     document.getElementById('detailed-analysis-placeholder')?.classList.add('d-none');


    showPane('analise-pane');
}

function buildSummaryTable(summaryData, resistanceNames) {
    // summaryData é um array de objetos, cada um com:
    // { Cenário, param_NomeRes1, param_NomeRes2, ..., Iterações, "Erro O. (%)", "Erro D. (%)" }
    const container = document.getElementById('summary-table-container');
    if (!summaryData || summaryData.length === 0) {
         container.innerHTML = '<p class="text-center text-muted mt-3">Nenhum resultado de cenário para exibir.</p>';
         return;
    }
    const table = document.createElement('table');
    table.className = 'table table-hover table-sm small'; // Tabela menor

    // --- Cria Cabeçalho Dinâmico ---
    const thead = table.createTHead();
    const headerRow = thead.insertRow();
    // Cabeçalhos fixos iniciais
    ['Cenário'].forEach(text => {
        const th = document.createElement('th'); th.textContent = text; headerRow.appendChild(th);
    });
    // Cabeçalhos de Parâmetros Dinâmicos
    resistanceNames.forEach(name => {
        const th = document.createElement('th'); th.textContent = `P: ${name}`; th.title = `Parâmetro ${name}`; headerRow.appendChild(th); // Abreviação 'P:'
    });
    // Cabeçalhos fixos finais
    ['Iterações', 'Erro O (%)', 'Erro D (%)'].forEach(text => { // Texto mais curto
        const th = document.createElement('th'); th.textContent = text; headerRow.appendChild(th);
    });

    // --- Cria Corpo da Tabela ---
    const tbody = table.createTBody();
    summaryData.forEach(rowData => {
        const row = tbody.insertRow();
        // Coluna Cenário
        let cell = row.insertCell(); cell.textContent = rowData['Cenário'];
        // Colunas de Parâmetros
        resistanceNames.forEach(name => {
            cell = row.insertCell(); cell.textContent = parseFloat(rowData[`param_${name}`] || 0).toFixed(1); // Formata com 1 decimal
        });
        // Colunas de Métricas
        cell = row.insertCell(); cell.textContent = rowData['Iterações'];
        cell = row.insertCell(); cell.textContent = rowData['Erro O. (%)'];
        cell = row.insertCell(); cell.textContent = rowData['Erro D. (%)'];
    });

    container.innerHTML = ''; // Limpa container
    container.appendChild(table); // Adiciona a nova tabela
}



function displayScenario(index) {
    // Marca o botão correto como ativo
    document.querySelectorAll('#scenario-nav-buttons .nav-link').forEach((btn, i) => btn.classList.toggle('active', i === index));

    // Obtém os dados do cenário selecionado e os dados base do AppState
    const scenario = AppState.results.detailed_scenarios[index];
    const baseData = AppState.results.dados_base; // {o, d, resistencias:{nome:matriz}}
    const resistanceNames = AppState.results.resistance_names; // Lista de nomes

    // --- Monta HTML das Métricas ---
    let metricsHtml = `<h6 class="mb-3">Métricas de Desempenho (${scenario.Cenário})</h6><ul class="list-group list-group-flush">`;
    resistanceNames.forEach(name => {
        const costKey = `custo_${name}`;
        const costValue = scenario.metrics.custos_brutos[costKey] || 0;
        const costVsBase = scenario.metrics.custos_vs_base[name] || 0;
        let badgeColor = 'secondary';
        if (costVsBase > 1) badgeColor = 'danger';
        if (costVsBase < -1) badgeColor = 'success';

        // Formatação simples, pode melhorar com unidades
        const formattedCost = costValue.toLocaleString('pt-BR', {maximumFractionDigits: 0});

        metricsHtml += `
            <li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">
                Custo ${name}:
                <div>
                    <span class="badge bg-${badgeColor}-subtle text-${badgeColor}-emphasis rounded-pill me-2" title="Variação vs Base">
                        ${costVsBase >= 0 ? '+' : ''}${costVsBase.toFixed(1)}%
                    </span>
                    <span class="badge fs-6 bg-secondary-subtle text-secondary-emphasis rounded-pill">${formattedCost}</span>
                 </div>
            </li>`;
    });
    metricsHtml += `</ul>`; // Fecha a lista de custos
     // Adiciona outras métricas se necessário (Iterações, Erros já estão na tabela resumo)

    document.getElementById('metrics-container').innerHTML = metricsHtml;

    // --- Gera Heatmap ---
    // Passa os dados base completos para generateHtmlHeatmap
    const fullBaseDataForHeatmap = {
         zonas: AppState.results.zonas,
         dados: baseData, // Contém {o, d, resistencias}
         resistance_names: resistanceNames // Passa a lista de nomes explicitamente
    };
    generateHtmlHeatmap('results-heatmap-wrapper', scenario, fullBaseDataForHeatmap);
}

function displayInteractiveResult(result) {
    // result agora contém: { matriz_viagens, num_iter, metrics: { "NomeRes Total": "valor_formatado" } }

    const currentParams = {}; // Recria params a partir dos sliders atuais
    document.querySelectorAll('.param-slider').forEach(slider => {
        const paramName = slider.getAttribute('data-param-name');
        if (paramName) currentParams[paramName] = parseFloat(slider.value);
    });

    const scenarioData = { matriz_viagens: result.matriz_viagens, params: currentParams };
    const baseData = AppState.lastPayload; // Usa o payload guardado

    // --- Atualiza Gráfico de Histórico (precisa ser adaptado) ---
    // A função updateSensitivityChart precisará ser reescrita para lidar
    // com um número variável de custos (result.metrics) e formatar o label.
    // updateSensitivityChart(currentParams, result.metrics); // ADIADO - Requer refatoração

    // --- Atualiza Métricas na UI ---
    let metricsHtml = `<h6 class="mb-3">Métricas do Cenário</h6><ul class="list-group list-group-flush">`;
    Object.entries(result.metrics).forEach(([key, value]) => {
         // Formata chave para exibição (ex: "Tempo Total" -> "Tempo Total")
        metricsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center bg-transparent px-0">${key}: <span class="badge bg-secondary-subtle text-secondary-emphasis rounded-pill">${value}</span></li>`;
    });
     metricsHtml += `</ul><hr/><p class="text-body-secondary small">Convergiu em <b>${result.num_iter}</b> iterações.</p>`;
    document.getElementById('interactive-metrics').innerHTML = metricsHtml;

    // --- Gera Heatmap ---
    // A função generateHtmlHeatmap precisará ser adaptada para ler
    // os custos dinâmicos do baseData (AppState.lastPayload) para os tooltips.
    generateHtmlHeatmap('interactive-heatmap', scenarioData, baseData); // Passa baseData atualizado
}


function generateHtmlHeatmap(containerId, scenarioData, baseData) {
    // scenarioData: { Cenário, params, matriz_viagens, metrics }
    // baseData: { zonas, dados: {o, d, resistencias}, resistance_names }
    const matrix = scenarioData.matriz_viagens;
    const container = document.getElementById(containerId);
    if (!matrix || !baseData || !baseData.zonas || !container) {
        container.innerHTML = '<p class="text-muted text-center">Dados insuficientes para gerar heatmap.</p>';
        return;
    }

    container.innerHTML = ''; // Limpa

    const flatMatrix = matrix.flat().filter(v => v > 0);
    const minVal = flatMatrix.length > 0 ? Math.min(...flatMatrix) : 0;
    const maxVal = flatMatrix.length > 0 ? Math.max(...flatMatrix) : 0;

    let tableHtml = '<table class="heatmap-table"><thead><tr><th>O↓|D→</th>';
    baseData.zonas.forEach(zona => tableHtml += `<th>${zona}</th>`);
    tableHtml += '</tr></thead><tbody>';

    matrix.forEach((row, i) => {
        tableHtml += `<tr><th>${baseData.zonas[i]}</th>`;
        row.forEach((value, j) => {
            // getThemedColorForValue não precisa mudar se já usa min/max
            const { background, color } = getThemedColorForValue(value, minVal, maxVal);
            tableHtml += `<td style="background-color: ${background}; color: ${color};" data-row="${i}" data-col="${j}" data-value="${value.toFixed(2)}">${Math.round(value)}</td>`;
        });
        tableHtml += '</tr>';
    });
    tableHtml += '</tbody></table>';

    // Legenda (sem alterações)
    const legendHtml = `
        <div class="mt-3">
            <div class="heatmap-legend"></div>
            <div class="d-flex justify-content-between small text-muted mt-1">
                <span>${Math.round(minVal)}</span>
                <span>Nº de Viagens</span>
                <span>${Math.round(maxVal)}</span>
            </div>
        </div>
    `;

    container.innerHTML = tableHtml + legendHtml;
    // Passa baseData completo para tooltips
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
    // scenarioData: { Cenário, params, matriz_viagens, metrics }
    // baseData: { zonas, dados: {o, d, resistencias}, resistance_names }
    const tooltip = document.getElementById('heatmap-tooltip');
    const container = document.getElementById(containerId);
    if (!container || !baseData.dados || !baseData.dados.resistencias) return;

    // Define os handlers *antes* do loop para que tenham a referência correta ao remover/adicionar
    function handleTooltipMouseover(e) {
            const i = parseInt(e.target.dataset.row);
            const j = parseInt(e.target.dataset.col);
            const params = scenarioData.params || {}; // Parâmetros usados neste cenário
            const resistanceNames = baseData.resistance_names || []; // Nomes das resistências

            let costsHtml = '';
            let impedanceValue = NaN;

            // Calcula impedância e monta string de custos dinamicamente
            try {
                 const impedanceConfig = AppState.lastPayload?.config?.impedancia || { tipo: "potencia" }; // Pega config do último run
                 const tipoFuncao = impedanceConfig.tipo;
                 let accumulatedImpedance;

                 if (tipoFuncao === 'exponencial') {
                     accumulatedImpedance = 0;
                     resistanceNames.forEach(name => {
                        const costMatrix = baseData.dados.resistencias[name];
                        const cost = (costMatrix && costMatrix.length > i && costMatrix[i].length > j) ? Number(costMatrix[i][j]) : 0;
                        const param = Number(params[name] || 0);
                        accumulatedImpedance += cost * param;
                        costsHtml += `${name}: ${cost.toFixed(1)}<br>`; // Assumindo 1 decimal para custos
                     });
                     impedanceValue = Math.exp(accumulatedImpedance);
                 } else { // Potência
                    accumulatedImpedance = 1;
                    let allParamsZero = true;
                    resistanceNames.forEach(name => {
                         if((params[name] || 0) !== 0) allParamsZero = false;
                    });

                    if(allParamsZero){
                         impedanceValue = 1.0; // Impedância é 1 se todos params são 0
                         resistanceNames.forEach(name => {
                            const costMatrix = baseData.dados.resistencias[name];
                            const cost = (costMatrix && costMatrix.length > i && costMatrix[i].length > j) ? Number(costMatrix[i][j]) : 0;
                            costsHtml += `${name}: ${cost.toFixed(1)}<br>`;
                         });
                    } else {
                        resistanceNames.forEach(name => {
                            const costMatrix = baseData.dados.resistencias[name];
                            const cost = (costMatrix && costMatrix.length > i && costMatrix[i].length > j) ? Number(costMatrix[i][j]) : 0;
                            const param = Number(params[name] || 0);

                            let term = 1.0;
                            const EPSILON = 1e-9;
                            if (param === 0) { term = 1.0; }
                            else if (param > 0) { term = (cost < EPSILON ? 0.0 : cost) ** param; }
                            else { term = (cost < EPSILON ? Infinity : cost) ** param; } // 0^neg = inf

                            accumulatedImpedance *= term;
                            costsHtml += `${name}: ${cost.toFixed(1)}<br>`; // Assumindo 1 decimal para custos
                        });
                        impedanceValue = accumulatedImpedance;
                    }

                 }
            } catch (error) {
                 console.error("Erro calculando impedância no tooltip:", error);
                 impedanceValue = NaN; // Marca como erro
                 costsHtml = "Erro ao ler custos.<br>";
            }

            const f_inv = (impedanceValue > 0 && isFinite(impedanceValue)) ? (1.0 / impedanceValue) : 0;

            tooltip.innerHTML = `<b>${baseData.zonas[i]} → ${baseData.zonas[j]}</b><hr class="my-1">`
                                + `<b>Viagens: ${parseFloat(e.target.dataset.value).toFixed(2)}</b><hr class="my-1">`
                                + `${costsHtml}<hr class="my-1">`
                                + `Impedância (f): ${impedanceValue.toFixed(2)}<br>`
                                + `Atratividade (1/f): ${f_inv.toFixed(4)}`;

            const rect = e.target.getBoundingClientRect();
            tooltip.style.left = `${window.scrollX + rect.right + 10}px`; // Adiciona scrollX
            tooltip.style.top = `${window.scrollY + rect.top}px`;     // Adiciona scrollY
            tooltip.classList.add('active');
      };

     function handleTooltipMouseout() {
            tooltip.classList.remove('active');
     };

    // Agora, o loop apenas remove e adiciona os handlers nomeados
    container.querySelectorAll('td').forEach(cell => {
        cell.removeEventListener('mouseover', handleTooltipMouseover);
        cell.removeEventListener('mouseout', handleTooltipMouseout);
        cell.addEventListener('mouseover', handleTooltipMouseover);
        cell.addEventListener('mouseout', handleTooltipMouseout);
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
