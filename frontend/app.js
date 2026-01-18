// const API_BASE = 'https://tourism-api-wgam.onrender.com';
const API_BASE = 'http://127.0.0.1:8000';

const canvas = document.getElementById('mapCanvas');
const ctx = canvas.getContext('2d');

// State
let allNodes = [];
let allEdges = [];
let nodeMap = {}; // id -> node

let startNodeId = null;
let endNodeId = null;
let currentPath = []; // List of node IDs in path

// Viewport transform
let transform = {
    scale: 1,
    offsetX: 0,
    offsetY: 0
};

// UI Elements
const elStart = document.getElementById('start-node');
const elEnd = document.getElementById('end-node');
const btnNav = document.getElementById('nav-btn');
const btnReset = document.getElementById('reset-btn');
const elLoading = document.getElementById('loading');
const elResult = document.getElementById('result-panel');
const elInfo = document.getElementById('node-info');

// Constants
const NODE_RADIUS = 6;
const COLOR_DEFAULT = '#3b82f6';
const COLOR_START = '#10b981'; // Green
const COLOR_END = '#ef4444';   // Red
const COLOR_PATH = '#f59e0b';  // Orange

// --- Initialization ---

async function init() {
    try {
        const res = await fetch(`${API_BASE}/graph`);
        if (!res.ok) throw new Error('API Error');
        const data = await res.json();
        
        allNodes = data.nodes;
        allEdges = data.edges;
        
        // Build map for quick lookup
        allNodes.forEach(n => nodeMap[n.id] = n);
        
        fitMapToScreen();
        render();
        elLoading.style.display = 'none';
        
    } catch (err) {
        elLoading.innerText = '加载失败，请确保后端服务已启动';
        console.error(err);
    }
}

// --- Rendering ---

function fitMapToScreen() {
    if (allNodes.length === 0) return;
    
    // Calculate bounds
    const xs = allNodes.map(n => n.x);
    const ys = allNodes.map(n => n.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    
    const mapWidth = maxX - minX;
    const mapHeight = maxY - minY;
    
    // Resize canvas
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
    
    // Calculate scale to fit with padding
    const padding = 50;
    const scaleX = (canvas.width - padding * 2) / mapWidth;
    const scaleY = (canvas.height - padding * 2) / mapHeight;
    const scale = Math.min(scaleX, scaleY);
    
    transform.scale = scale;
    // Center it
    transform.offsetX = (canvas.width - mapWidth * scale) / 2 - minX * scale;
    transform.offsetY = (canvas.height - mapHeight * scale) / 2 - minY * scale;
}

function toScreen(x, y) {
    return {
        x: x * transform.scale + transform.offsetX,
        y: y * transform.scale + transform.offsetY
    };
}

function fromScreen(sx, sy) {
    return {
        x: (sx - transform.offsetX) / transform.scale,
        y: (sy - transform.offsetY) / transform.scale
    };
}

function render() {
    // Clear
    ctx.fillStyle = '#e5e7eb';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 1. Draw Edges
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#9ca3af'; // Grey
    
    allEdges.forEach(edge => {
        const u = nodeMap[edge.u];
        const v = nodeMap[edge.v];
        if(!u || !v) return;
        
        const posU = toScreen(u.x, u.y);
        const posV = toScreen(v.x, v.y);
        
        // Check if this edge is part of the path
        const isPath = isEdgeInPath(edge.u, edge.v);
        
        ctx.beginPath();
        ctx.moveTo(posU.x, posU.y);
        ctx.lineTo(posV.x, posV.y);
        
        if (isPath) {
            ctx.save();
            ctx.strokeStyle = COLOR_PATH;
            ctx.lineWidth = 4;
            ctx.stroke();
            ctx.restore();
        } else {
            ctx.stroke();
        }
    });
    
    // 2. Draw Nodes
    allNodes.forEach(node => {
        const pos = toScreen(node.x, node.y);
        
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, NODE_RADIUS, 0, Math.PI * 2);
        
        let color = COLOR_DEFAULT;
        let radius = NODE_RADIUS;
        
        if (node.id === startNodeId) {
            color = COLOR_START;
            radius = NODE_RADIUS * 1.5;
        } else if (node.id === endNodeId) {
            color = COLOR_END;
            radius = NODE_RADIUS * 1.5;
        } else if (currentPath.includes(node.id)) {
            color = COLOR_PATH;
        }
        
        ctx.fillStyle = color;
        ctx.fill();
        
        // Draw Label
        ctx.fillStyle = '#374151';
        ctx.font = '12px Arial';
        ctx.fillText(node.name, pos.x + 10, pos.y + 4);
    });
}

function isEdgeInPath(u, v) {
    if (currentPath.length < 2) return false;
    for (let i = 0; i < currentPath.length - 1; i++) {
        const p1 = currentPath[i];
        const p2 = currentPath[i+1];
        if ((p1 === u && p2 === v) || (p1 === v && p2 === u)) {
            return true;
        }
    }
    return false;
}

// --- Interaction ---

canvas.addEventListener('mousedown', e => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Check click on nodes
    // Use screen coordinates directly for easier hit testing
    const clickedNode = allNodes.find(node => {
        const pos = toScreen(node.x, node.y);
        const dist = Math.hypot(pos.x - x, pos.y - y);
        return dist < NODE_RADIUS * 2; // Hit area
    });
    
    if (clickedNode) {
        handleNodeClick(clickedNode);
    }
});

function handleNodeClick(node) {
    // Show Info
    document.getElementById('info-name').innerText = node.name;
    document.getElementById('info-category').innerText = `类型: ${node.category}`;
    document.getElementById('info-desc').innerText = node.desc || '暂无描述';
    elInfo.classList.remove('hidden');
    
    // Selection Logic
    if (startNodeId === null) {
        startNodeId = node.id;
        elStart.innerText = node.name;
        elStart.classList.remove('placeholder');
        elStart.classList.add('selected');
    } else if (endNodeId === null && node.id !== startNodeId) {
        endNodeId = node.id;
        elEnd.innerText = node.name;
        elEnd.classList.remove('placeholder');
        elEnd.classList.add('selected');
        
        btnNav.disabled = false;
    } else {
        // Reset or restart? Let's implement reset first for simplicity
        // Or re-select start if clicked again
        if (node.id === startNodeId) {
            // Deselect Start
            startNodeId = null;
            elStart.innerText = '请在地图上点击';
            elStart.classList.add('placeholder');
            elStart.classList.remove('selected');
            btnNav.disabled = true;
        } else if (node.id === endNodeId) {
            // Deselect End
            endNodeId = null;
            elEnd.innerText = '请在地图上点击';
            elEnd.classList.add('placeholder');
            elEnd.classList.remove('selected');
            btnNav.disabled = true;
        }
    }
    
    // Clear path if selection changes
    if (currentPath.length > 0 && (startNodeId === null || endNodeId === null)) {
        currentPath = [];
        elResult.classList.add('hidden');
    }
    
    render();
}

btnReset.addEventListener('click', () => {
    startNodeId = null;
    endNodeId = null;
    currentPath = [];
    
    elStart.innerText = '请在地图上点击';
    elStart.classList.add('placeholder');
    elStart.classList.remove('selected');
    
    elEnd.innerText = '请在地图上点击';
    elEnd.classList.add('placeholder');
    elEnd.classList.remove('selected');
    
    btnNav.disabled = true;
    elResult.classList.add('hidden');
    elInfo.classList.add('hidden');
    
    render();
});

btnNav.addEventListener('click', async () => {
    if (startNodeId === null || endNodeId === null) return;
    
    const strategy = document.getElementById('strategy').value;
    
    try {
        btnNav.innerText = '规划中...';
        btnNav.disabled = true;
        
        const res = await fetch(`${API_BASE}/navigate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_id: startNodeId,
                end_id: endNodeId,
                strategy: strategy
            })
        });
        
        if (!res.ok) {
            const errModel = await res.json();
            alert(errModel.detail || '导航失败');
            return;
        }
        
        const data = await res.json();
        
        // Update State
        currentPath = data.path_ids;
        
        // Update UI
        document.getElementById('total-cost').innerText = Math.round(data.total_cost) + ' 米';
        const list = document.getElementById('path-steps');
        list.innerHTML = '';
        data.path_names.forEach(name => {
            const li = document.createElement('li');
            li.innerText = name;
            list.appendChild(li);
        });
        elResult.classList.remove('hidden');
        
        render(); // Re-draw path
        
    } catch (err) {
        console.error(err);
        alert('请求失败');
    } finally {
        btnNav.innerText = '开始导航';
        btnNav.disabled = false;
    }
});

// Resize listener
window.addEventListener('resize', () => {
    fitMapToScreen();
    render();
});

// Start
init();
