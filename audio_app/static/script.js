import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

// Variables globales
let scene, camera, renderer, jukebox, isZoomed = false;
let composer, bloomPass; // Para el efecto glow

// VARIABLES DE DISTANCIA - Modifica estos valores
const DISTANCIA_INICIAL = 200   ;    // Distancia inicial de la cámara
const DISTANCIA_ACERCAMIENTO = 70; // Distancia cuando se acerca

// VARIABLES DE GLOW/EMISIÓN
const BLOOM_STRENGTH = 1;     // Intensidad del glow
const BLOOM_RADIUS = 0.2;       // Radio del glow
const BLOOM_THRESHOLD = 0.1;    // Umbral para el glow
const EMISSION_INTENSITY = 25.0; // Intensidad de emisión de materiales

// Inicializar Three.js
function init() {
    // Crear escena
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);

    // Crear cámara - usando variable de distancia inicial
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 2, DISTANCIA_INICIAL);

    // Crear renderer con configuración para glow
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ReinhardToneMapping;
    renderer.toneMappingExposure = 1.0;
    document.getElementById('container').appendChild(renderer.domElement);

    // Configurar post-processing para el efecto glow
    setupGlowEffect();

    // Luces mejoradas
    const ambientLight = new THREE.AmbientLight(0x404040, 0.5); // Más luz ambiental
    scene.add(ambientLight);

    // Cargar rockola
    createJukebox();
    
    // Event listeners
    setupEventListeners();
    
    // Iniciar loop de renderizado
    animate();
    
    // Ocultar loading
    document.getElementById('loading').style.display = 'none';
}

function createJukebox() {
    const fbxLoader = new FBXLoader();
    fbxLoader.load('ROCKOLA.fbx', (object) => {
        object.scale.setScalar(1.0); // Escala más grande (era 0.01)
        object.position.set(0, -90, 0); // Bajar la rockola al suelo
        
        // Procesar materiales para activar emisión y glow
        object.traverse((child) => {
            if (child.isMesh) {
                child.castShadow = true;
                child.receiveShadow = true;
                
                // Activar mapas de emisión si existen
                if (child.material) {
                    processEmissiveMaterial(child.material);
                }
            }
        });
        
        jukebox = object;
        scene.add(jukebox);
        document.getElementById('loading').style.display = 'none';
    }, (progress) => {
        console.log('Loading FBX:', (progress.loaded / progress.total * 100) + '%');
    }, (error) => {
        console.error('Error loading FBX:', error);
        document.getElementById('loading').textContent = 'Error cargando ROCKOLA.fbx';
    });
    
    // Plano de sombra al nivel del suelo
    const planeGeometry = new THREE.PlaneGeometry(20, 20);
    const planeMaterial = new THREE.ShadowMaterial({ opacity: 0.3 });
    const plane = new THREE.Mesh(planeGeometry, planeMaterial);
    plane.rotation.x = -Math.PI / 2;
    plane.position.set(0, -1, 0); // Mismo nivel que la rockola
    plane.receiveShadow = true;
    scene.add(plane);
}

function setupEventListeners() {
    // Click en la rockola
    renderer.domElement.addEventListener('click', onJukeboxClick);
    
    // Resize
    window.addEventListener('resize', onWindowResize);
}

function onJukeboxClick(event) {
    const mouse = new THREE.Vector2();
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, camera);

    if (jukebox) {
        const intersects = raycaster.intersectObjects(jukebox.children || [jukebox], true);
        
        if (intersects.length > 0) {
            if (!isZoomed) {
                zoomToJukebox();
            } else {
                zoomOut();
            }
        }
    }
}

function zoomToJukebox() {
    isZoomed = true;
    document.getElementById('clickHint').style.display = 'none';
    
    // Animar cámara usando variable de acercamiento
    animateCamera(camera.position, { x: 0, y: 2, z: DISTANCIA_ACERCAMIENTO }, 1500);
    
    // Mostrar hologramas
    setTimeout(() => {
        document.getElementById('hologram1').classList.add('active');
    }, 800);
}

function zoomOut() {
    isZoomed = false;
    
    // Ocultar hologramas
    document.getElementById('hologram1').classList.remove('active');
    
    // Animar cámara de vuelta usando variable inicial
    animateCamera(camera.position, { x: 0, y: 2, z: DISTANCIA_INICIAL }, 1500);
    
    setTimeout(() => {
        document.getElementById('clickHint').style.display = 'block';
    }, 1000);
}

function animateCamera(from, to, duration) {
    const startTime = Date.now();
    const startPos = { x: from.x, y: from.y, z: from.z };
    
    function update() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing
        const eased = 1 - Math.pow(1 - progress, 3);
        
        camera.position.x = startPos.x + (to.x - startPos.x) * eased;
        camera.position.y = startPos.y + (to.y - startPos.y) * eased;
        camera.position.z = startPos.z + (to.z - startPos.z) * eased;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    update();
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    
    // Actualizar composer también
    if (composer) {
        composer.setSize(window.innerWidth, window.innerHeight);
    }
}

function animate() {
    requestAnimationFrame(animate);
    
    // NO rotar la rockola - mantenerla estática
    // if (jukebox) {
    //     jukebox.rotation.y += 0.002;
    // }
    
    // Usar composer para renderizar con glow
    if (composer) {
        composer.render();
    } else {
        renderer.render(scene, camera);
    }
}

// Configurar efecto glow/bloom
function setupGlowEffect() {
    composer = new EffectComposer(renderer);
    
    // Pass de render normal
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);
    
    // Pass de bloom para el efecto glow
    bloomPass = new UnrealBloomPass(
        new THREE.Vector2(window.innerWidth, window.innerHeight),
        BLOOM_STRENGTH,  // strength
        BLOOM_RADIUS,    // radius
        BLOOM_THRESHOLD  // threshold
    );
    composer.addPass(bloomPass);
}

// Procesar materiales para activar emisión
function processEmissiveMaterial(material) {
    // Si es un array de materiales
    if (Array.isArray(material)) {
        material.forEach(mat => processEmissiveMaterial(mat));
        return;
    }
    
    // Si el material tiene mapa de emisión
    if (material.emissiveMap) {
        console.log('Mapa de emisión encontrado:', material.name);
        material.emissive = new THREE.Color(0x404040); // Color base de emisión
        material.emissiveIntensity = EMISSION_INTENSITY;
        material.needsUpdate = true;
    }
    
    // Buscar texturas que puedan ser de emisión por nombre
    if (material.map && material.map.name) {
        const textureName = material.map.name.toLowerCase();
        if (textureName.includes('emission') || 
            textureName.includes('emissive') || 
            textureName.includes('glow') ||
            textureName.includes('light')) {
            
            console.log('Textura de emisión detectada:', material.map.name);
            material.emissiveMap = material.map;
            material.emissive = new THREE.Color(0xffffff);
            material.emissiveIntensity = EMISSION_INTENSITY;
            material.needsUpdate = true;
        }
    }
    
    // Para materiales que deben brillar (pantallas, luces, etc.)
    if (material.name && material.name.toLowerCase().includes('screen') ||
        material.name && material.name.toLowerCase().includes('light') ||
        material.name && material.name.toLowerCase().includes('display')) {
        
        console.log('Material de pantalla/luz detectado:', material.name);
        material.emissive = new THREE.Color(0x002200); // Verde tenue
        material.emissiveIntensity = EMISSION_INTENSITY * 0.5;
        material.needsUpdate = true;
    }
}

// Inicializar cuando se carga la página
window.addEventListener('load', init);