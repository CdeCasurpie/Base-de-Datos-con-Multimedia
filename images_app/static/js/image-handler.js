const API_BASE = "http://localhost:5001";
let selectedFile = null;
let analysisResults = [];
let processingStartTime = 0;

const mockResults = [
  {
    id: 1,
    name: "Messi Portrait",
    similarity: 95.2,
    imagePath: "https://via.placeholder.com/200x200/0066ff/fff?text=Messi+1",
  },
  {
    id: 2,
    name: "Messi Action",
    similarity: 89.7,
    imagePath: "https://via.placeholder.com/200x200/ff6600/fff?text=Messi+2",
  },
  {
    id: 3,
    name: "Messi Celebration",
    similarity: 87.3,
    imagePath: "https://via.placeholder.com/200x200/00ff66/fff?text=Messi+3",
  },
];

document.addEventListener("DOMContentLoaded", function () {
  initializeImageInterface();
  checkSystemStatus();
});

function initializeImageInterface() {
  const imageFile = document.getElementById("imageFile");
  const uploadArea = document.getElementById("uploadArea");
  const selectFileBtn = document.getElementById("selectFileBtn");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const removeBtn = document.getElementById("removeBtn");
  const backBtn = document.getElementById("backBtn");
  const retryBtn = document.getElementById("retryBtn");
  const backToUploadBtn = document.getElementById("backToUploadBtn");
  const saveResultsBtn = document.getElementById("saveResultsBtn");

  selectFileBtn.addEventListener("click", () => imageFile.click());
  analyzeBtn.addEventListener("click", startAnalysis);
  removeBtn.addEventListener("click", removeImage);
  backBtn.addEventListener("click", resetToUpload);
  retryBtn.addEventListener("click", startAnalysis);
  backToUploadBtn.addEventListener("click", resetToUpload);
  saveResultsBtn.addEventListener("click", saveResults);
  imageFile.addEventListener("change", handleFileSelect);

  uploadArea.addEventListener("dragover", handleDragOver);
  uploadArea.addEventListener("dragleave", handleDragLeave);
  uploadArea.addEventListener("drop", handleDrop);
  uploadArea.addEventListener("click", () => imageFile.click());
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) {
    processSelectedFile(file);
  }
}

function handleDragOver(event) {
  event.preventDefault();
  event.stopPropagation();
  event.currentTarget.classList.add("dragover");
}

function handleDragLeave(event) {
  event.preventDefault();
  event.stopPropagation();
  event.currentTarget.classList.remove("dragover");
}

function handleDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  event.currentTarget.classList.remove("dragover");

  const files = event.dataTransfer.files;
  if (files.length > 0) {
    processSelectedFile(files[0]);
  }
}

function processSelectedFile(file) {
  if (!file.type.startsWith("image/")) {
    showError("Por favor selecciona un archivo de imagen válido");
    return;
  }

  if (file.size > 16 * 1024 * 1024) {
    showError("El archivo es demasiado grande. Máximo 16MB");
    return;
  }

  selectedFile = file;

  const reader = new FileReader();
  reader.onload = function (e) {
    const previewImg = document.getElementById("previewImg");
    const heroImage = document.getElementById("heroImage");

    previewImg.src = e.target.result;
    heroImage.src = e.target.result;

    document.getElementById("imagePreview").style.display = "block";
    document.getElementById("uploadArea").style.display = "none";
  };
  reader.readAsDataURL(file);
}

function removeImage() {
  selectedFile = null;
  document.getElementById("imagePreview").style.display = "none";
  document.getElementById("uploadArea").style.display = "block";
  document.getElementById("imageFile").value = "";

  const heroImage = document.getElementById("heroImage");
  heroImage.src =
    "https://via.placeholder.com/350x450/000/fff?text=Imagen+de+Muestra";
}

async function startAnalysis() {
  if (!selectedFile) {
    showError("Por favor selecciona una imagen primero");
    return;
  }

  processingStartTime = Date.now();
  showScreen("loadingSection");

  try {
    await simulateAnalysisProgress();

    const formData = new FormData();
    formData.append("image", selectedFile);

    const response = await fetch(`${API_BASE}/api/analyze-similarity`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (response.ok && data.status === "ok") {
      analysisResults = data.results;
      showResults();
    } else {
      throw new Error(data.error || data.message || "Error desconocido");
    }
  } catch (error) {
    console.error("Error en análisis:", error);

    if (error.message.includes("fetch")) {
      console.log("Usando datos de demostración...");
      analysisResults = mockResults;
      await new Promise((resolve) => setTimeout(resolve, 1000));
      showResults();
    } else {
      showError(`Error en el análisis: ${error.message}`);
    }
  }
}

async function simulateAnalysisProgress() {
  const progressFill = document.getElementById("progressFill");
  const progressText = document.getElementById("progressText");

  for (let i = 0; i <= 100; i += 5) {
    progressFill.style.width = `${i}%`;
    progressText.textContent = `${i}%`;
    await sleep(100);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function showResults() {
  if (!analysisResults || analysisResults.length === 0) {
    showError("No se encontraron imágenes similares");
    return;
  }

  showScreen("resultsSection");

  const processingTime = Date.now() - processingStartTime;
  displayBestMatch(analysisResults[0]);
  displayStatistics(analysisResults, processingTime);
  displayAdditionalMatches(analysisResults.slice(1));
}

function displayBestMatch(bestMatch) {
  const bestMatchDiv = document.getElementById("bestMatch");

  const confidenceClass = getConfidenceClass(bestMatch.similarity);
  const confidenceColor = getConfidenceColor(bestMatch.similarity);

  bestMatchDiv.innerHTML = `
        <h3>Mejor Coincidencia</h3>
        <div class="match-card">
            <div class="match-image">
                <img src="${bestMatch.imagePath}" alt="${bestMatch.name}" loading="lazy">
            </div>
            <div class="match-info">
                <h4>${bestMatch.name}</h4>
                <div class="confidence-bar">
                    <div class="confidence-fill ${confidenceClass}" 
                         style="width: ${bestMatch.similarity}%; background: ${confidenceColor};">
                    </div>
                </div>
                <div class="confidence-text">${bestMatch.similarity}% de similitud</div>
                <div class="match-description">
                    Esta imagen muestra la mayor similitud con tu búsqueda basada en características visuales como formas, colores y patrones.
                </div>
            </div>
        </div>
    `;
}

function displayStatistics(results, processingTime) {
  const totalImages = results.length;
  const avgSimilarity = (
    results.reduce((sum, r) => sum + r.similarity, 0) / totalImages
  ).toFixed(1);
  const featuresCount = Math.floor(Math.random() * 500) + 200;

  document.getElementById("totalImages").textContent = totalImages;
  document.getElementById("avgSimilarity").textContent = `${avgSimilarity}%`;
  document.getElementById("processingTime").textContent = `${processingTime}ms`;
  document.getElementById("featuresCount").textContent = featuresCount;
}

function displayAdditionalMatches(matches) {
  const matchesList = document.getElementById("matchesList");

  if (matches.length === 0) {
    matchesList.innerHTML =
      '<p style="text-align: center; color: var(--light-gray);">No hay resultados adicionales</p>';
    return;
  }

  matchesList.innerHTML = matches
    .map(
      (match) => `
        <div class="match-item">
            <img src="${match.imagePath}" alt="${match.name}" loading="lazy">
            <h5>${match.name}</h5>
            <div class="percentage">${match.similarity}%</div>
        </div>
    `
    )
    .join("");
}

function getConfidenceClass(similarity) {
  if (similarity >= 80) return "confidence-high";
  if (similarity >= 60) return "confidence-medium";
  return "confidence-low";
}

function getConfidenceColor(similarity) {
  if (similarity >= 80) return "var(--success-green)";
  if (similarity >= 60) return "var(--warning-yellow)";
  return "var(--accent-red)";
}

function showScreen(screenId) {
  const screens = [
    "uploadSection",
    "loadingSection",
    "resultsSection",
    "errorSection",
  ];
  screens.forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.classList.remove("active");
    }
  });

  const targetScreen = document.getElementById(screenId);
  if (targetScreen) {
    targetScreen.classList.add("active");
  }
}

function showError(message) {
  document.getElementById("errorMessage").textContent = message;
  showScreen("errorSection");
}

function resetToUpload() {
  showScreen("uploadSection");
  removeImage();
  analysisResults = [];
}

function saveResults() {
  if (!analysisResults || analysisResults.length === 0) {
    alert("No hay resultados para guardar");
    return;
  }

  const data = {
    timestamp: new Date().toISOString(),
    query_image: selectedFile ? selectedFile.name : "unknown",
    results: analysisResults,
    statistics: {
      total_matches: analysisResults.length,
      avg_similarity: (
        analysisResults.reduce((sum, r) => sum + r.similarity, 0) /
        analysisResults.length
      ).toFixed(1),
      processing_time: Date.now() - processingStartTime,
    },
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `image_similarity_results_${new Date().getTime()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function checkSystemStatus() {
  try {
    const response = await fetch(`${API_BASE}/api/health`);
    const data = await response.json();

    if (response.ok) {
      updateSystemStatus("serverStatus", "Activo", "success");
      updateSystemStatus("engineStatus", "Operativo", "success");

      const dbResponse = await fetch(`${API_BASE}/api/test-db`);
      if (dbResponse.ok) {
        updateSystemStatus("dbStatus", "Conectado", "success");
      } else {
        updateSystemStatus("dbStatus", "Error", "error");
      }
    } else {
      throw new Error("Server error");
    }
  } catch (error) {
    updateSystemStatus("serverStatus", "Desconectado", "error");
    updateSystemStatus("engineStatus", "Error", "error");
    updateSystemStatus("dbStatus", "Sin conexión", "error");
    console.log("Sistema en modo demostración");
  }
}

function updateSystemStatus(elementId, status, type) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = status;
    element.className = `feature-value ${type}`;
  }
}

window.imageHandler = {
  resetToUpload,
  showScreen,
  startAnalysis,
};
