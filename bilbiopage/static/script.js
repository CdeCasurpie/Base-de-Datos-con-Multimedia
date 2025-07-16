let resultados = [];
let paginaActual = 1;
const resultadosPorPagina = 5;

document.getElementById('btn-buscar').onclick = function() {
    const query = document.getElementById('busqueda').value;
    fetch('/buscar', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query})
    })
    .then(res => res.json())
    .then(data => {
        resultados = data;
        paginaActual = 1;
        mostrarResultados();
        // Cambia el video al de resultados
        cambiarVideo('/static/video/resultado.mp4');
        document.getElementById('buscador-section').style.display = 'none';
        document.getElementById('resultados-section').style.display = 'block';
    });
};

document.getElementById('btn-nueva-busqueda').onclick = function() {
    document.getElementById('buscador-section').style.display = 'block';
    document.getElementById('resultados-section').style.display = 'none';
    cambiarVideo('/static/video/videomenu.mp4');
};

function mostrarResultados() {
    const lista = document.getElementById('resultados-lista');
    lista.innerHTML = '';
    const inicio = (paginaActual - 1) * resultadosPorPagina;
    const fin = Math.min(inicio + resultadosPorPagina, resultados.length);
    for (let i = inicio; i < fin; i++) {
        const res = resultados[i];
        const div = document.createElement('div');
        div.className = 'resultado-item';
        div.innerHTML = `<img src="${res.imagen}" title="${res.titulo}" style="width:100px;cursor:pointer;">`;
        div.onclick = () => window.location = `/documento/${res.id}`;
        lista.appendChild(div);
    }
    mostrarPaginacion();
}

function mostrarPaginacion() {
    const pagDiv = document.getElementById('paginacion');
    pagDiv.innerHTML = '';
    const totalPaginas = Math.ceil(resultados.length / resultadosPorPagina);
    if (totalPaginas <= 1) return;
    if (paginaActual > 1) {
        const prev = document.createElement('button');
        prev.textContent = 'Anterior';
        prev.onclick = () => { paginaActual--; mostrarResultados(); };
        pagDiv.appendChild(prev);
    }
    if (paginaActual < totalPaginas) {
        const next = document.createElement('button');
        next.textContent = 'Siguiente';
        next.onclick = () => { paginaActual++; mostrarResultados(); };
        pagDiv.appendChild(next);
    }
}

function cambiarVideo(src) {
    const video = document.getElementById('video-biblioteca');
    video.pause();
    video.setAttribute('src', src);
    video.load();
    video.play();
}
