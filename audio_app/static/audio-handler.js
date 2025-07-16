// ===== MANEJADOR DE AUDIO Y SIMILITUD =====

// Variables globales
let selectedFile = null;
let currentPlayingId = null;
let globalAudioPlayer = null;
let analysisResults = [];

// Mock data para simulación
const mockResults = [
    {
        id: 1,
        title: "Bohemian Rhapsody",
        artist: "Queen",
        similarity: 95.2,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav" // Mock audio
    },
    {
        id: 2,
        title: "Hotel California",
        artist: "Eagles",
        similarity: 89.7,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 3,
        title: "Sweet Child O' Mine",
        artist: "Guns N' Roses",
        similarity: 87.3,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 4,
        title: "Stairway to Heaven",
        artist: "Led Zeppelin",
        similarity: 85.9,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 5,
        title: "Imagine",
        artist: "John Lennon",
        similarity: 83.1,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 6,
        title: "Yesterday",
        artist: "The Beatles",
        similarity: 81.8,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 7,
        title: "Like a Rolling Stone",
        artist: "Bob Dylan",
        similarity: 79.4,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 8,
        title: "Purple Haze",
        artist: "Jimi Hendrix",
        similarity: 77.6,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 9,
        title: "The Sound of Silence",
        artist: "Simon & Garfunkel",
        similarity: 75.2,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 10,
        title: "Paint It Black",
        artist: "The Rolling Stones",
        similarity: 73.8,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 11,
        title: "Hey Jude",
        artist: "The Beatles",
        similarity: 71.5,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    },
    {
        id: 12,
        title: "Wonderwall",
        artist: "Oasis",
        similarity: 69.3,
        audioPath: "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav"
    }
];

// Inicialización cuando se carga el DOM
document.addEventListener('DOMContentLoaded', function() {
    initializeAudioInterface();
});

function initializeAudioInterface() {
    // Obtener elementos del DOM
    const audioFile = document.getElementById('audioFile');
    const uploadArea = document.getElementById('uploadArea');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const selectedFileDiv = document.getElementById('selectedFile');
    const backBtn = document.getElementById('backBtn');
    
    globalAudioPlayer = document.getElementById('globalAudioPlayer');

    // Event listeners
    selectFileBtn.addEventListener('click', () => audioFile.click());
    analyzeBtn.addEventListener('click', startAnalysis);
    backBtn.addEventListener('click', resetToUpload);
    audioFile.addEventListener('change', handleFileSelect);

    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('click', () => audioFile.click());

    // Audio player events
    globalAudioPlayer.addEventListener('ended', handleAudioEnd);
    globalAudioPlayer.addEventListener('loadstart', () => updatePlayButton(currentPlayingId, 'loading'));
    globalAudioPlayer.addEventListener('canplay', () => updatePlayButton(currentPlayingId, 'pause'));
}

// ===== MANEJO DE ARCHIVOS =====
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        processSelectedFile(file);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('dragover');
    
    const files = event.dataTransfer.files;
    if (files.length > 0) {
        processSelectedFile(files[0]);
    }
}

function processSelectedFile(file) {
    // Validar tipo de archivo
    const validTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/m4a'];
    if (!validTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.mp3')) {
        alert('Por favor selecciona un archivo de audio válido (MP3, WAV, M4A)');
        return;
    }

    selectedFile = file;
    
    // Mostrar información del archivo
    const selectedFileDiv = document.getElementById('selectedFile');
    const fileName = selectedFileDiv.querySelector('.file-name');
    const fileSize = selectedFileDiv.querySelector('.file-size');
    
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    
    selectedFileDiv.style.display = 'flex';
    document.getElementById('analyzeBtn').disabled = false;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ===== ANÁLISIS DE SIMILITUD =====
async function startAnalysis() {
    if (!selectedFile) return;
    
    showScreen('loadingScreen');
    
    try {
        // Simular progreso inicial
        await simulateAnalysisProgress();
        
        // Llamada real al backend
        const results = await analyzeAudioSimilarity(selectedFile);
        
        if (results && results.length > 0) {
            analysisResults = results;
            showResults();
        } else {
            // No se encontraron resultados
            showNoResults();
        }
        
    } catch (error) {
        console.error('Error en análisis:', error);
        showError(error.message || 'Error al analizar el audio');
    }
}

async function simulateAnalysisProgress() {
    const progressFill = document.getElementById('progressFill');
    const loadingText = document.querySelector('.loading-text');
    
    const steps = [
        { text: "Cargando archivo de audio...", progress: 20 },
        { text: "Enviando a servidor...", progress: 40 },
        { text: "Extrayendo características MFCC...", progress: 60 },
        { text: "Comparando con base de datos...", progress: 80 }
    ];
    
    for (const step of steps) {
        loadingText.textContent = step.text;
        progressFill.style.width = step.progress + '%';
        await sleep(600); // Progreso más rápido
    }
    
    loadingText.textContent = "Procesando resultados...";
    progressFill.style.width = '90%';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ===== MOSTRAR RESULTADOS =====
function showResults() {
    showScreen('resultsScreen');
    
    const matchCount = document.getElementById('matchCount');
    const resultsContainer = document.getElementById('resultsContainer');
    
    matchCount.textContent = analysisResults.length;
    
    // Limpiar resultados anteriores
    resultsContainer.innerHTML = '';
    
    if (analysisResults.length === 0) {
        showNoResults();
        return;
    }
    
    // Crear elementos de resultado
    analysisResults.forEach(result => {
        const resultElement = createResultItem(result);
        resultsContainer.appendChild(resultElement);
    });
}

function showNoResults() {
    showScreen('resultsScreen');
    
    const matchCount = document.getElementById('matchCount');
    const resultsContainer = document.getElementById('resultsContainer');
    
    matchCount.textContent = '0';
    resultsContainer.innerHTML = `
        <div style="text-align: center; padding: 40px; opacity: 0.7;">
            <div style="font-size: 48px; margin-bottom: 20px;">🎵</div>
            <h3>No se encontraron canciones similares</h3>
            <p>Intenta con otro archivo de audio</p>
        </div>
    `;
}

function showError(message) {
    showScreen('resultsScreen');
    
    const matchCount = document.getElementById('matchCount');
    const resultsContainer = document.getElementById('resultsContainer');
    
    matchCount.textContent = '0';
    resultsContainer.innerHTML = `
        <div style="text-align: center; padding: 40px; color: #ff6b6b;">
            <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
            <h3>Error en el análisis</h3>
            <p>${message}</p>
            <button onclick="resetToUpload()" style="margin-top: 20px; padding: 10px 20px; background: rgba(255,107,107,0.2); border: 1px solid #ff6b6b; color: white; border-radius: 5px; cursor: pointer;">
                Intentar de nuevo
            </button>
        </div>
    `;
}

function createResultItem(result) {
    const item = document.createElement('div');
    item.className = 'result-item';
    
    // Usar la URL completa del backend para el audio
    const audioUrl = `http://localhost:5000${result.audioPath}`;
    
    item.innerHTML = `
        <div class="song-info">
            <div class="song-title">${result.title}</div>
            <div class="song-artist">${result.artist}</div>
            <div class="similarity-score">${result.similarity}% similitud</div>
        </div>
        <button class="play-button" data-id="${result.id}" data-state="play" data-audio="${audioUrl}">
        </button>
    `;
    
    // Agregar event listener al botón de reproducción
    const playButton = item.querySelector('.play-button');
    playButton.addEventListener('click', () => toggleAudio(result.id, audioUrl));
    
    return item;
}

// ===== REPRODUCCIÓN DE AUDIO =====
function toggleAudio(id, audioPath) {
    if (currentPlayingId === id) {
        // Pausar el audio actual
        pauseCurrentAudio();
    } else {
        // Reproducir nuevo audio
        playAudio(id, audioPath);
    }
}

function playAudio(id, audioPath) {
    // Pausar cualquier audio que esté reproduciéndose
    pauseCurrentAudio();
    
    currentPlayingId = id;
    updatePlayButton(id, 'loading');
    
    globalAudioPlayer.src = audioPath;
    globalAudioPlayer.load();
    
    globalAudioPlayer.play().then(() => {
        updatePlayButton(id, 'pause');
    }).catch(error => {
        console.error('Error playing audio:', error);
        updatePlayButton(id, 'play');
        currentPlayingId = null;
    });
}

function pauseCurrentAudio() {
    if (currentPlayingId) {
        globalAudioPlayer.pause();
        updatePlayButton(currentPlayingId, 'play');
        currentPlayingId = null;
    }
}

function handleAudioEnd() {
    if (currentPlayingId) {
        updatePlayButton(currentPlayingId, 'play');
        currentPlayingId = null;
    }
}

function updatePlayButton(id, state) {
    const button = document.querySelector(`[data-id="${id}"]`);
    if (button) {
        button.setAttribute('data-state', state);
        button.classList.toggle('playing', state === 'pause');
    }
}

// ===== NAVEGACIÓN ENTRE PANTALLAS =====
function showScreen(screenId) {
    // Ocultar todas las pantallas
    document.querySelectorAll('.hologram-screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Mostrar la pantalla solicitada
    document.getElementById(screenId).classList.add('active');
}

function resetToUpload() {
    // Pausar cualquier audio reproduciéndose
    pauseCurrentAudio();
    
    // Limpiar archivo seleccionado
    selectedFile = null;
    document.getElementById('audioFile').value = '';
    document.getElementById('selectedFile').style.display = 'none';
    document.getElementById('analyzeBtn').disabled = true;
    
    // Limpiar resultados
    analysisResults = [];
    
    // Volver a la pantalla de subida
    showScreen('uploadScreen');
}

// ===== API CALLS =====
async function analyzeAudioSimilarity(file) {
    const formData = new FormData();
    formData.append('audio', file);
    
    try {
        const response = await fetch('http://localhost:5000/api/analyze-similarity', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error en el análisis');
        }
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            // Finalizar barra de progreso
            const progressFill = document.getElementById('progressFill');
            const loadingText = document.querySelector('.loading-text');
            
            progressFill.style.width = '100%';
            loadingText.textContent = 'Análisis completado!';
            
            await sleep(500); // Pausa breve para mostrar completado
            
            return data.results;
        } else {
            throw new Error(data.message || 'Error desconocido en el servidor');
        }
        
    } catch (error) {
        console.error('Error analyzing audio:', error);
        throw error;
    }
}

// Exportar funciones para uso global si es necesario
window.audioHandler = {
    resetToUpload,
    showScreen,
    toggleAudio
};
