/**
 * ==================================================================================
 * 模块 1：全局配置与状态管理
 * 负责定义后端 API 地址、Canvas 上下文、核心数据结构以及用户认证状态
 * ==================================================================================
 */

// 后端 API 基础地址 (本地调试环境)
// const API_BASE = 'https://tourism-api-wgam.onrender.com';
const API_BASE = 'http://127.0.0.1:8000';

// 获取地图 Canvas 及其 2D 绘图上下文
const canvas = document.getElementById('mapCanvas');
const ctx = canvas.getContext('2d');

// --- 核心状态变量 ---
let allNodes = [];    // 存储所有景点节点数据
let allEdges = [];    // 存储所有路径边数据
let nodeMap = {};     // 节点 ID 到节点的快速映射 (id -> node)

// --- 路径规划与交互状态 ---
let startNodeId = null;   // 导航起点 ID
let endNodeId = null;     // 导航终点 ID
let currentPath = [];     // 当前计算出的路径 (节点 ID 列表)
let currentSpotId = null; // 当前选中的景点 ID (用于查看详情或写日记)

// --- 用户认证状态 ---
// 从 LocalStorage 恢复登录状态
let authToken = localStorage.getItem('token');
let currentUser = localStorage.getItem('user');

// --- 地图视图变换状态 ---
// 用于实现地图的缩放和平移
let transform = {
    scale: 1,     // 缩放比例
    offsetX: 0,   // X 轴偏移量
    offsetY: 0    // Y 轴偏移量
};

/**
 * ==================================================================================
 * 模块 2：UI 元素引用
 * 缓存所有需要交互的 DOM 元素，避免重复查询
 * ==================================================================================
 */
// 导航与主体 UI
const elStart = document.getElementById('start-node');
const elEnd = document.getElementById('end-node');
const btnNav = document.getElementById('nav-btn');
const btnReset = document.getElementById('reset-btn');
const elLoading = document.getElementById('loading');
const elResult = document.getElementById('result-panel');
const elInfo = document.getElementById('node-info');

// Auth UI
const elUserPanel = document.getElementById('user-panel');
const elLoggedOut = document.getElementById('logged-out-view');
const elLoggedIn = document.getElementById('logged-in-view');
const elUsername = document.getElementById('current-username');
const btnShowLogin = document.getElementById('btn-show-login');
const btnLogout = document.getElementById('btn-logout');
const modalAuth = document.getElementById('auth-modal');
const btnSubmitAuth = document.getElementById('btn-submit-auth');
const authTitle = document.getElementById('auth-title');
const btnToggleAuth = document.getElementById('btn-toggle-auth-mode');

// Chat UI
const elChatPanel = document.getElementById('chat-panel');
const elChatHeader = document.getElementById('chat-header');
const elChatInput = document.getElementById('chat-input');
const btnChatSend = document.getElementById('btn-chat-send');
const elChatMessages = document.getElementById('chat-messages');

// Diary UI
const tabContainer = document.querySelector('.tab-container');
const tabContents = document.querySelectorAll('.tab-content');
const btnViewSpotDiaries = document.getElementById('btn-view-spot-diaries');
const elDiaryList = document.getElementById('diary-list-container');
const elDiarySearchInput = document.getElementById('diary-search-input');
const btnDiarySearch = document.getElementById('btn-diary-search');
const elDiarySort = document.getElementById('diary-sort');
const btnRefreshDiaries = document.getElementById('btn-refresh-diaries');

// Diary Modals
const modalDiary = document.getElementById('diary-modal');
const btnSubmitDiary = document.getElementById('btn-submit-diary');
const modalDiaryDetail = document.getElementById('diary-detail-modal');
const btnSubmitComment = document.getElementById('btn-submit-comment');

// Constants
const NODE_RADIUS = 6;
const COLOR_DEFAULT = '#3b82f6';
const COLOR_START = '#10b981'; // Green
const COLOR_END = '#ef4444';   // Red
const COLOR_PATH = '#f59e0b';  // Orange

/**
 * ==================================================================================
 * 模块 3：工具函数
 * 处理 API 请求封装
 * ==================================================================================
 */

/**
 * 通用 API 请求函数
 * @param {string} endpoint - API 端点 (例如 '/graph')
 * @param {string} method - HTTP 方法 (GET, POST 等)
 * @param {object|FormData} body - 请求体数据
 * @param {boolean} isFile - 是否为文件上传 (如果是，则不设置 JSON Content-Type)
 */
async function apiCall(endpoint, method = 'GET', body = null, isFile = false) {
    const headers = {};
    // 如果不是文件上传，默认使用 JSON 格式
    if (!isFile) {
        headers['Content-Type'] = 'application/json';
    }
    // 如果已登录，添加 JWT Token 到请求头
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const config = {
        method,
        headers,
    };

    if (body) {
        config.body = isFile ? body : JSON.stringify(body);
    }

    const res = await fetch(`${API_BASE}${endpoint}`, config);
    if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'API Request Failed');
    }
    return await res.json();
}

/**
 * ==================================================================================
 * 模块 4：初始化逻辑
 * 页面加载时执行，恢复状态并获取地图数据
 * ==================================================================================
 */

async function init() {
    updateAuthUI(); // 更新登录界面状态
    try {
        // 请求后端获取图结构数据 (节点和边)
        const data = await apiCall('/graph');
        
        allNodes = data.nodes;
        allEdges = data.edges;
        
        // 构建快速查找表 index: id -> node
        allNodes.forEach(n => nodeMap[n.id] = n);
        
        fitMapToScreen(); // 自动调整地图视角适配屏幕
        render();         // 绘制地图
        elLoading.style.display = 'none'; // 隐藏加载提示
        
    } catch (err) {
        elLoading.innerText = '加载失败，请确保后端服务已启动';
        console.error(err);
    }
}

/**
 * ==================================================================================
 * 模块 5：用户认证系统
 * 处理注册、登录、注销以及认证 UI 的状态切换
 * ==================================================================================
 */

function updateAuthUI() {
    if (authToken && currentUser) {
        // 已登录状态：隐藏非登录面板，显示用户信息
        elLoggedOut.classList.add('hidden');
        elLoggedIn.classList.remove('hidden');
        elLoggedIn.style.display = 'flex'; // 修正 hidden 样式覆盖问题
        elUsername.innerText = currentUser;
    } else {
        // 未登录状态
        elLoggedOut.classList.remove('hidden');
        elLoggedIn.classList.add('hidden');
    }
}

let isLoginMode = true; // 当前弹窗是否为登录模式 (false 为注册模式)

// 点击“登录/注册”按钮显示弹窗
btnShowLogin.addEventListener('click', () => {
    modalAuth.classList.remove('hidden');
    isLoginMode = true;
    authTitle.innerText = "用户登录";
    btnSubmitAuth.innerText = "登录";
    btnToggleAuth.innerText = "没有账号? 去注册";
});

// 切换登录/注册模式
btnToggleAuth.addEventListener('click', () => {
    isLoginMode = !isLoginMode;
    if (isLoginMode) {
        authTitle.innerText = "用户登录";
        btnSubmitAuth.innerText = "登录";
        btnToggleAuth.innerText = "没有账号? 去注册";
    } else {
        authTitle.innerText = "用户注册";
        btnSubmitAuth.innerText = "注册";
        btnToggleAuth.innerText = "已有账号? 去登录";
    }
});

// 提交认证表单
btnSubmitAuth.addEventListener('click', async () => {
    const user = document.getElementById('auth-username').value;
    const pass = document.getElementById('auth-password').value;
    
    if (!user || !pass) return alert("请输入完整信息");

    try {
        if (isLoginMode) {
            // --- 登录逻辑 ---
            const data = await apiCall('/auth/login', 'POST', { username: user, password: pass });
            authToken = data.access_token; // 获取 Access Token
            
            // 下面尝试解码 JWT 获取用户名 (虽然我们已知 username, 但通常从 Token 解析更安全)
            try {
               const payload = JSON.parse(atob(authToken.split('.')[1]));
               currentUser = payload.name || user;
            } catch(e) { currentUser = user; }
            
            // 持久化存储
            localStorage.setItem('token', authToken);
            localStorage.setItem('user', currentUser);
            alert("登录成功");
        } else {
            // --- 注册逻辑 ---
            await apiCall('/auth/register', 'POST', { username: user, password: pass });
            alert("注册成功，请登录");
            isLoginMode = true; // 注册成功后自动切回登录模式
            btnToggleAuth.click(); // 触发切换以更新 UI 文本
            return; // 此时不关闭弹窗，让用户继续登录
        }
        updateAuthUI();
        modalAuth.classList.add('hidden');
    } catch (err) {
        alert(err.message);
    }
});

// 注销逻辑
btnLogout.addEventListener('click', () => {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    updateAuthUI();
});

/**
 * ==================================================================================
 * 模块 6：Tab 切换系统
 * 控制左侧面板的功能切换 (导航/日记/设置等)
 * ==================================================================================
 */

tabContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('tab')) {
        // UI 状态切换
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        e.target.classList.add('active');
        
        // 内容区域切换
        const tabId = `tab-${e.target.dataset.tab}`;
        tabContents.forEach(c => c.classList.add('hidden'));
        document.getElementById(tabId).classList.remove('hidden');
        
        // 如果切到了日记 Tab，自动加载默认日记列表
        if (e.target.dataset.tab === 'diary') {
            loadDiaries(); 
        }
    }
});

/**
 * ==================================================================================
 * 模块 7：日记系统
 * 包含日记列表加载、日记发布、搜索、详情查看逻辑
 * ==================================================================================
 */

async function loadDiaries(spotId = null) {
    elDiaryList.innerHTML = '<div style="text-align: center; color: #999;">加载中...</div>';
    const sort = elDiarySort.value;
    
    try {
        let endpoint = '';
        if (spotId) {
             // 场景 1: 获取特定景点的日记
             endpoint = `/diaries/spot/${spotId}?sort_by=${sort}`;
        } else {
             // 场景 2: 全局搜索或浏览
             const keyword = elDiarySearchInput.value.trim();
             if (keyword) {
                 endpoint = `/diaries/search?keyword=${encodeURIComponent(keyword)}&sort_by=${sort}`;
             } else {
                 endpoint = `/diaries/search?sort_by=${sort}`; // 默认推荐列表
             }
        }
        
        const diaries = await apiCall(endpoint);
        renderDiaries(diaries);
    } catch (err) {
        elDiaryList.innerText = '加载失败';
        console.error(err);
    }
}

function renderDiaries(list) {
    elDiaryList.innerHTML = '';
    if (list.length === 0) {
        elDiaryList.innerHTML = '<div style="text-align: center; padding: 20px;">暂无日记</div>';
        return;
    }
    
    list.forEach(diary => {
        const item = document.createElement('div');
        item.className = 'diary-item';
        // 简单日期格式化
        const date = new Date(diary.created_at).toLocaleDateString();
        
        item.innerHTML = `
            <h4>${diary.title}</h4>
            <div style="font-size: 13px; color: #4b5563; margin-bottom: 5px;">
                ${diary.content.substring(0, 50)}...
            </div>
            <div class="diary-meta">
                <span>👤 ${diary.user_name}</span>
                <span>🔥 ${diary.view_count} | ⭐ ${diary.score}</span>
                <span>📅 ${date}</span>
            </div>
        `;
        item.addEventListener('click', () => openDiaryDetail(diary.id));
        elDiaryList.appendChild(item);
    });
}

// 搜索框与排序变更监听
btnDiarySearch.addEventListener('click', () => loadDiaries(null));
elDiarySort.addEventListener('change', () => loadDiaries(null)); // 注意: 这会重置景点筛选
btnRefreshDiaries.addEventListener('click', () => loadDiaries(null));

// “查看该景点日记”按钮事件 (通常在地图选中景点后出现)
btnViewSpotDiaries.addEventListener('click', () => {
    // 自动切换到日记 Tab
    document.querySelector('.tab[data-tab="diary"]').click();
    // 清空搜索框
    elDiarySearchInput.value = '';
    if (currentSpotId) {
        loadDiaries(currentSpotId);
        // 在列表顶部添加一个“写日记”的快捷入口
        const div = document.createElement('div');
        div.style.marginBottom = '10px';
        div.innerHTML = `<button class="btn-primary full-width" onclick="openCreateDiaryModal()">✍️ 在此写一篇日记</button>`;
        elDiaryList.prepend(div); 
    }
});

// 修改: 添加创建日记逻辑
// 注意: 为了让嵌入 HTML 的 onclick 能调用，需要挂载到 window 对象
window.openCreateDiaryModal = function() {
    if (!authToken) {
        alert("请先登录");
        btnShowLogin.click();
        return;
    }
    if (!currentSpotId) return alert("请先在地图上选择一个景点");
    
    const node = nodeMap[currentSpotId];
    // 预填充景点名称
    document.getElementById('diary-spot-name').innerText = node.name;
    document.getElementById('diary-title').value = '';
    document.getElementById('diary-content').value = '';
    document.getElementById('diary-file').value = '';
    
    modalDiary.classList.remove('hidden');
}

btnSubmitDiary.addEventListener('click', async () => {
    const title = document.getElementById('diary-title').value;
    const content = document.getElementById('diary-content').value;
    const fileInput = document.getElementById('diary-file');
    
    if (!title || !content) return alert("标题和内容不能为空");
    
    try {
        btnSubmitDiary.innerText = "发布中...";
        btnSubmitDiary.disabled = true;
        
        const mediaFiles = [];
        // 处理文件上传 (如果有)
        if (fileInput.files.length > 0) {
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            // 这是一个多步操作：1. 先上传文件 2. 获取 URL 3. 提交日记
            const uploadRes = await apiCall('/upload', 'POST', formData, true);
            mediaFiles.push(uploadRes.url);
        }
        
        // 创建日记记录
        await apiCall('/diaries/', 'POST', {
            spot_id: currentSpotId,
            title,
            content,
            media_files: mediaFiles
        });
        
        alert("发布成功！");
        modalDiary.classList.add('hidden');
        loadDiaries(currentSpotId); // 刷新列表
        
    } catch(err) {
        alert("发布失败: " + err.message);
    } finally {
        btnSubmitDiary.innerText = "发布";
        btnSubmitDiary.disabled = false;
    }
});

// --- 日记详情与评论模块 ---
let currentDetailId = null;

async function openDiaryDetail(id) {
    try {
        currentDetailId = id;
        const diary = await apiCall(`/diaries/detail/${id}`);
        
        // 渲染详情内容
        document.getElementById('detail-title').innerText = diary.title;
        document.getElementById('detail-author').innerText = diary.user_name;
        document.getElementById('detail-score').innerText = diary.score;
        document.getElementById('detail-views').innerText = diary.view_count;
        document.getElementById('detail-content').innerText = diary.content;
        
        // 渲染图片
        const imgContainer = document.getElementById('detail-images');
        imgContainer.innerHTML = '';
        if (diary.media_files && diary.media_files.length > 0) {
            diary.media_files.forEach(url => {
                const img = document.createElement('img');
                img.src = `${API_BASE}${url}`;
                imgContainer.appendChild(img);
            });
        }
        
        modalDiaryDetail.classList.remove('hidden');
        loadComments(id);
        
        // 根据登录状态显示/隐藏评论框
        if(authToken) {
            document.getElementById('comment-form-box').classList.remove('hidden');
            document.getElementById('comment-login-hint').classList.add('hidden');
        } else {
            document.getElementById('comment-form-box').classList.add('hidden');
            document.getElementById('comment-login-hint').classList.remove('hidden');
        }
        
    } catch(err) {
        console.error(err);
        alert("加载详情失败");
    }
}

async function loadComments(id) {
    const list = document.getElementById('detail-comments');
    list.innerHTML = '加载评论...';
    try {
        const comments = await apiCall(`/diaries/${id}/comments`);
        list.innerHTML = '';
        if (comments.length === 0) {
            list.innerHTML = '<div style="color:#999; font-size:12px;">暂无评论，快来抢沙发</div>';
            return;
        }
        comments.forEach(c => {
            const div = document.createElement('div');
            div.style.borderBottom = '1px solid #eee';
            div.style.padding = '8px 0';
            div.innerHTML = `
                <div style="font-size:12px; font-weight:bold;">${c.user_name} <span style="font-weight:normal; color:#666;">打分: ${c.score}</span></div>
                <div style="font-size:13px; margin-top:4px;">${c.content}</div>
                <div style="font-size:10px; color:#ccc; margin-top:2px;">${new Date(c.created_at).toLocaleString()}</div>
            `;
            list.appendChild(div);
        });
    } catch(e) {
        list.innerHTML = '评论加载失败';
    }
}

btnSubmitComment.addEventListener('click', async () => {
    const content = document.getElementById('comment-content').value;
    const score = parseFloat(document.getElementById('comment-score').value);
    
    if(!content) return alert("写点什么吧");
    
    try {
        await apiCall('/diaries/comment', 'POST', {
            diary_id: currentDetailId,
            content,
            score
        });
        document.getElementById('comment-content').value = '';
        loadComments(currentDetailId); // 重新加载评论
        // 重新获取详情以更新评分
        const d = await apiCall(`/diaries/detail/${currentDetailId}`);
        document.getElementById('detail-score').innerText = d.score;
        
    } catch(err) {
        alert(err.message);
    }
});


/**
 * ==================================================================================
 * 模块 8：AI 智能问答系统
 * 包含聊天窗口的拖拽、最小化以及 RAG 对话交互
 * ==================================================================================
 */

// --- 1. 窗口拖拽逻辑 ---
let isDragging = false;
let dragOffsetX = 0;
let dragOffsetY = 0;

elChatHeader.style.cursor = 'move';
elChatHeader.style.userSelect = 'none';

elChatHeader.addEventListener('mousedown', (e) => {
    // 忽略最小化按钮的点击
    if (e.target.id === 'chat-toggle') return;

    isDragging = true;
    const rect = elChatPanel.getBoundingClientRect();
    dragOffsetX = e.clientX - rect.left;
    dragOffsetY = e.clientY - rect.top;

    // 将定位方式从 CSS 默认转换为 JS 绝对定位
    elChatPanel.style.right = 'auto';
    elChatPanel.style.bottom = 'auto';
    elChatPanel.style.left = rect.left + 'px';
    elChatPanel.style.top = rect.top + 'px';
});

document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    e.preventDefault(); // 防止文字选中
    
    let newX = e.clientX - dragOffsetX;
    let newY = e.clientY - dragOffsetY;
    
    // 边界检查，防止窗口拖出屏幕
    newX = Math.max(0, Math.min(newX, window.innerWidth - elChatPanel.offsetWidth));
    newY = Math.max(0, Math.min(newY, window.innerHeight - 30)); // 允许底部留一点空隙

    elChatPanel.style.left = newX + 'px';
    elChatPanel.style.top = newY + 'px';
});

document.addEventListener('mouseup', () => {
    isDragging = false;
});

// --- 2. 窗口最小化/展开逻辑 ---
let isChatOpen = true; 

function toggleChat() {
    isChatOpen = !isChatOpen;
    const btn = document.getElementById('chat-toggle');
    if (isChatOpen) {
        elChatPanel.style.height = '400px';
        btn.innerText = '_';
    } else {
        elChatPanel.style.height = '40px';
        btn.innerText = '□';
    }
}

// 仅点击按钮时触发
document.getElementById('chat-toggle').addEventListener('click', (e) => {
    e.stopPropagation();
    toggleChat();
});

// 双击标题栏也能切换
elChatHeader.addEventListener('dblclick', toggleChat);


// --- 3. 消息发送逻辑 ---
btnChatSend.addEventListener('click', sendMessage);
elChatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
    const text = elChatInput.value.trim();
    if (!text) return;
    
    // 显示用户消息
    addMessage(text, 'user');
    elChatInput.value = '';
    
    // 添加 AI 正在思考的占位符
    const loadingId = addMessage('AI 正在思考...', 'ai');
    
    try {
        // 调用 RAG 问答接口
        const res = await apiCall('/ai/rag_chat', 'POST', { message: text });
        
        // 移除思考占位符
        document.getElementById(loadingId).remove();
        
        // AI 返回格式: { reply: "...", source: "..." }
        const replyText = res.reply || "AI 暂时没有回答";

        // 简单格式化 (换行符转 BR)
        const formatted = replyText.replace(/\n/g, '<br>');
        addMessage(formatted, 'ai', true); // isHTML=true 支持渲染简单 HTML
        
    } catch(err) {
        document.getElementById(loadingId).innerText = "Error: " + err.message;
    }
}

function addMessage(text, role, isHTML = false) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.id = 'msg-' + Date.now();
    if (isHTML) div.innerHTML = text;
    else div.innerText = text;
    elChatMessages.appendChild(div);
    // 自动滚动到底部
    elChatMessages.scrollTop = elChatMessages.scrollHeight;
    return div.id;
}


/**
 * ==================================================================================
 * 模块 9：地图交互核心逻辑
 * 处理节点点击、选中状态、以及与导航栏的联动
 * ==================================================================================
 */

function handleNodeClick(node) {
    currentSpotId = node.id;
    
    // 显示右侧信息面板内容
    document.getElementById('info-name').innerText = node.name;
    document.getElementById('info-category').innerText = `类型: ${node.category}`;
    document.getElementById('info-desc').innerText = node.desc || '暂无描述';
    elInfo.classList.remove('hidden');
    
    // 强制切回导航 Tab，方便用户操作
    document.querySelector('.tab[data-tab="nav"]').click();

    // 起点/终点 自动选择逻辑
    if (startNodeId === null) {
        // 还没选起点 -> 设为起点
        startNodeId = node.id;
        elStart.innerText = node.name;
        elStart.classList.remove('placeholder');
        elStart.classList.add('selected');
    } else if (endNodeId === null && node.id !== startNodeId) {
        // 有起点没终点 -> 设为终点
        endNodeId = node.id;
        elEnd.innerText = node.name;
        elEnd.classList.remove('placeholder');
        elEnd.classList.add('selected');
        
        btnNav.disabled = false; // 激活导航按钮
    } else {
         // 已满，或者是再次点击 -> 取消选择
         if (node.id === startNodeId) {
            startNodeId = null;
            elStart.innerText = '请在地图上点击';
            elStart.classList.add('placeholder');
            elStart.classList.remove('selected');
            btnNav.disabled = true;
        } else if (node.id === endNodeId) {
            endNodeId = null;
            elEnd.innerText = '请在地图上点击';
            elEnd.classList.add('placeholder');
            elEnd.classList.remove('selected');
            btnNav.disabled = true;
        }
    }
    
    // 如果修改了起终点，之前的路径就无效了
    if (currentPath.length > 0 && (startNodeId === null || endNodeId === null)) {
        currentPath = [];
        elResult.classList.add('hidden');
    }
    
    render(); // 重绘地图以显示选中状态颜色
}

// 自动缩放地图以适应屏幕
function fitMapToScreen() {
    if (allNodes.length === 0) return;
    // 计算所有节点的边界框 (Bounding Box)
    const xs = allNodes.map(n => n.x);
    const ys = allNodes.map(n => n.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    
    // 地图真实尺寸
    const mapWidth = maxX - minX;
    const mapHeight = maxY - minY;
    
    // 设置 Canvas 分辨率
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
    
    const padding = 50; // 留白
    const scaleX = (canvas.width - padding * 2) / mapWidth;
    const scaleY = (canvas.height - padding * 2) / mapHeight;
    const scale = Math.min(scaleX, scaleY);
    
    // 更新全局变换矩阵
    transform.scale = scale;
    transform.offsetX = (canvas.width - mapWidth * scale) / 2 - minX * scale;
    transform.offsetY = (canvas.height - mapHeight * scale) / 2 - minY * scale;
}

// --- 地图平移与缩放 (Map Pan & Zoom) ---

let isMapDragging = false;
let lastMouseX = 0;
let lastMouseY = 0;

// 1. 平移逻辑 (鼠标拖拽)
canvas.addEventListener('mousedown', e => {
    isMapDragging = true;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
});

canvas.addEventListener('mousemove', e => {
    if (isMapDragging) {
        const dx = e.clientX - lastMouseX;
        const dy = e.clientY - lastMouseY;
        
        // 直接更新偏移量
        transform.offsetX += dx;
        transform.offsetY += dy;
        
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
        
        render(); // 实时重绘
    }
});

canvas.addEventListener('mouseup', () => {
    isMapDragging = false;
});

canvas.addEventListener('mouseleave', () => {
    isMapDragging = false;
});

// 2. 缩放逻辑 (鼠标滚轮)
canvas.addEventListener('wheel', e => {
    e.preventDefault();
    
    const zoomIntensity = 0.1; // 缩放灵敏度
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // 计算鼠标当前指向的“世界坐标”(World Coordinates)
    // 缩放前后，鼠标指向的世界坐标应该保持不变，从而实现以鼠标为中心的缩放
    const worldX = (mouseX - transform.offsetX) / transform.scale;
    const worldY = (mouseY - transform.offsetY) / transform.scale;

    // 更新缩放比例
    if (e.deltaY < 0) {
        // 向上滚动 -> 放大
        transform.scale *= (1 + zoomIntensity);
    } else {
        // 向下滚动 -> 缩小
        transform.scale *= (1 - zoomIntensity);
    }
    
    // 限制缩放范围
    transform.scale = Math.max(0.1, Math.min(transform.scale, 20));

    // 反推新的偏移量： offsetX = mouseX - worldX * newScale
    transform.offsetX = mouseX - worldX * transform.scale;
    transform.offsetY = mouseY - worldY * transform.scale;
    
    render();
}, { passive: false });

// 3. 点击逻辑 (区分拖拽和点击)
// 我们需要跟踪是否发生了显著移动，如果只是微小抖动，仍视为点击
let dragDistance = 0;

canvas.addEventListener('mousedown', e => {
    dragDistance = 0;
    // ... isMapDragging 已在上方处理 ...
});

canvas.addEventListener('mousemove', e => {
    if (isMapDragging) {
        dragDistance += Math.hypot(e.movementX, e.movementY);
    }
});

canvas.addEventListener('mouseup', e => {
    // 移动距离小于 5 像素才视为点击
    if (dragDistance < 5) {
        handleCanvasClick(e);
    }
    isMapDragging = false;
});

function handleCanvasClick(e) {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // 查找点击命中的节点
    const clickedNode = allNodes.find(node => {
        const pos = toScreen(node.x, node.y);
        const dist = Math.hypot(pos.x - x, pos.y - y);
        // 点击判定区域随缩放微调，方便操作
        const hitRadius = Math.max(NODE_RADIUS, NODE_RADIUS * transform.scale * 0.5);
        return dist < Math.max(10, hitRadius); // 至少 10px 点击范围
    });
    
    if (clickedNode) {
        handleNodeClick(clickedNode);
    }
}

// 坐标转换工具：世界坐标 -> 屏幕坐标
function toScreen(x, y) {
    return {
        x: x * transform.scale + transform.offsetX,
        y: y * transform.scale + transform.offsetY
    };
}

// --- 渲染引擎 ---
function render() {
    // 清空背景
    ctx.fillStyle = '#e5e7eb';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 1. 绘制边 (路径)
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#9ca3af'; 
    allEdges.forEach(edge => {
        const u = nodeMap[edge.u];
        const v = nodeMap[edge.v];
        if(!u || !v) return;
        
        const posU = toScreen(u.x, u.y);
        const posV = toScreen(v.x, v.y);
        const isPath = isEdgeInPath(edge.u, edge.v);
        
        ctx.beginPath();
        ctx.moveTo(posU.x, posU.y);
        ctx.lineTo(posV.x, posV.y);
        
        // 如果是导航路径的一部分，高亮绘制
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
    
    // 2. 绘制节点 (圆点)
    allNodes.forEach(node => {
        const pos = toScreen(node.x, node.y);
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, NODE_RADIUS, 0, Math.PI * 2);
        
        // 颜色状态判定
        let color = COLOR_DEFAULT;
        if (node.id === startNodeId) color = COLOR_START;
        else if (node.id === endNodeId) color = COLOR_END;
        else if (currentPath.includes(node.id)) color = COLOR_PATH;
        
        ctx.fillStyle = color;
        ctx.fill();
        
        // 绘制文字标签
        ctx.fillStyle = '#374151';
        ctx.font = '12px Arial';
        ctx.fillText(node.name, pos.x + 10, pos.y + 4);
    });
}


// 判断边是否在当前规划的路径中
function isEdgeInPath(u, v) {
    if (currentPath.length < 2) return false;
    for (let i = 0; i < currentPath.length - 1; i++) {
        const p1 = currentPath[i];
        const p2 = currentPath[i+1];
        // 路径是无向的，所以要双向判断
        if ((p1 === u && p2 === v) || (p1 === v && p2 === u)) return true;
    }
    return false;
}

/**
 * ==================================================================================
 * 模块 10：导航控制逻辑
 * 处理重置、导航请求发送以及结果显示
 * ==================================================================================
 */

// 重置按钮逻辑
btnReset.addEventListener('click', () => {
    // 清空状态
    startNodeId = null;
    endNodeId = null;
    currentPath = [];
    currentSpotId = null;
    
    // 重置 UI
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

// 开始导航按钮逻辑
btnNav.addEventListener('click', async () => {
    if (startNodeId === null || endNodeId === null) return;
    const strategy = document.getElementById('strategy').value;
    const transport = document.getElementById('transport').value; // 获取出行方式

    try {
        btnNav.innerText = '规划中...';
        btnNav.disabled = true;
        
        // 发送导航请求
        const data = await apiCall('/navigate', 'POST', {
            start_id: startNodeId,
            end_id: endNodeId,
            strategy: strategy,
            transport: transport // 传递 transport 参数 (walk/bike)
        });
        
        // 保存路径数据
        currentPath = data.path_ids;
        
        // 显示结果 (处理单位：米 或 秒)
        // 后端通常返回 cost_unit，如果没有则 fallback
        let unit = '米';
        if (data.cost_unit) {
            unit = data.cost_unit;
        } else {
             // 简单的回退猜测逻辑
             unit = strategy === 'time' ? '秒' : '米';
        }
        document.getElementById('total-cost').innerText = Math.round(data.total_cost) + ' ' + unit;

        const list = document.getElementById('path-steps');
        list.innerHTML = '';
        data.path_names.forEach(name => {
            const li = document.createElement('li');
            li.innerText = name;
            list.appendChild(li);
        });
        elResult.classList.remove('hidden');
        
        render(); // 在地图上高亮路径
        
    } catch (err) {
        alert(err.message);
    } finally {
        btnNav.innerText = '开始导航';
        btnNav.disabled = false;
    }
});

// 窗口大小变化自适应
window.addEventListener('resize', () => {
    fitMapToScreen();
    render();
});

// 启动程序
init();