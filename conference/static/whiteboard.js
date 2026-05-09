// Белая доска с поддержкой страниц, синхронизации, сохранения в PDF
class Whiteboard {
    constructor(containerId, socket, isTeacher = false, roomId = 'teacher_room') {
        this.container = document.getElementById(containerId);
        this.socket = socket;
        this.isTeacher = isTeacher;
        this.roomId = roomId;
        
        this.pages = []; // массив холстов для каждой страницы
        this.currentPage = 0;
        this.drawing = false;
        this.lastX = 0;
        this.lastY = 0;
        this.color = '#000000';
        this.size = 3;
        this.isErasing = false;
        
        this.initUI();
        this.initCanvas();
        this.setupSocketEvents();
    }
    
    initUI() {
        // Создаём панель управления цветом, толщиной, очисткой, страницами
        const toolbar = document.createElement('div');
        toolbar.className = 'whiteboard-toolbar';
        toolbar.innerHTML = `
            <button id="wb-clear">🧽 Очистить</button>
            <label>🎨 Цвет: <input type="color" id="wb-color" value="#000000"></label>
            <label>✏️ Размер: <input type="range" id="wb-size" min="1" max="20" value="3"></label>
            <button id="wb-erase">🧽 Ластик</button>
            <button id="wb-pen">✏️ Ручка</button>
            <button id="wb-new-page">📄 Новая страница</button>
            <button id="wb-prev-page">◀ Назад</button>
            <span id="wb-page-indicator">Страница 1</span>
            <button id="wb-next-page">Вперед ▶</button>
            <button id="wb-save-pdf">💾 Сохранить PDF</button>
        `;
        this.container.appendChild(toolbar);
        
        // Контейнер для canvas
        this.canvasContainer = document.createElement('div');
        this.canvasContainer.className = 'whiteboard-canvas-container';
        this.container.appendChild(this.canvasContainer);
        
        // Создаём первую страницу
        this.addNewPage();
    }
    
    addNewPage() {
        const canvas = document.createElement('canvas');
        canvas.width = 800;
        canvas.height = 600;
        canvas.style.border = '1px solid #ccc';
        canvas.style.backgroundColor = 'white';
        canvas.style.display = 'none';
        canvas.classList.add('whiteboard-canvas');
        this.canvasContainer.appendChild(canvas);
        this.pages.push(canvas);
        
        this.initCanvasEvents(canvas);
        this.setCurrentPage(this.pages.length - 1);
        
        if (this.isTeacher) {
            // Уведомляем всех о новой странице
            this.socket.emit('whiteboard_page_added', { room: this.roomId, pageIndex: this.pages.length - 1 });
        }
    }
    
    setCurrentPage(index) {
        if (index < 0 || index >= this.pages.length) return;
        this.pages[this.currentPage].style.display = 'none';
        this.currentPage = index;
        this.pages[this.currentPage].style.display = 'block';
        const indicator = document.getElementById('wb-page-indicator');
        if (indicator) indicator.innerText = `Страница ${this.currentPage + 1}`;
        
        if (this.isTeacher) {
            this.socket.emit('whiteboard_change_page', { room: this.roomId, pageIndex: this.currentPage });
        }
    }
    
    nextPage() {
        if (this.currentPage < this.pages.length - 1) {
            this.setCurrentPage(this.currentPage + 1);
        } else {
            this.addNewPage();
        }
    }
    
    prevPage() {
        if (this.currentPage > 0) {
            this.setCurrentPage(this.currentPage - 1);
        }
    }
    
    initCanvasEvents(canvas) {
        const ctx = canvas.getContext('2d');
        let drawing = false;
        let lastX = 0, lastY = 0;
        
        const getCoords = (e) => {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            let clientX, clientY;
            if (e.touches) {
                clientX = e.touches[0].clientX;
                clientY = e.touches[0].clientY;
            } else {
                clientX = e.clientX;
                clientY = e.clientY;
            }
            let x = (clientX - rect.left) * scaleX;
            let y = (clientY - rect.top) * scaleY;
            x = Math.min(Math.max(0, x), canvas.width);
            y = Math.min(Math.max(0, y), canvas.height);
            return { x, y };
        };
        
        const startDrawing = (e) => {
            drawing = true;
            const { x, y } = getCoords(e);
            lastX = x;
            lastY = y;
            ctx.beginPath();
            ctx.moveTo(x, y);
            e.preventDefault();
        };
        
        const draw = (e) => {
            if (!drawing) return;
            const { x, y } = getCoords(e);
            ctx.strokeStyle = this.isErasing ? '#FFFFFF' : this.color;
            ctx.lineWidth = this.size;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.lineTo(x, y);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x, y);
            
            // Отправляем событие синхронизации
            if (this.isTeacher) {
                this.socket.emit('whiteboard_draw', {
                    room: this.roomId,
                    pageIndex: this.currentPage,
                    type: 'draw',
                    data: {
                        x0: lastX, y0: lastY,
                        x1: x, y1: y,
                        color: this.color,
                        size: this.size,
                        erasing: this.isErasing
                    }
                });
            }
            lastX = x;
            lastY = y;
            e.preventDefault();
        };
        
        const stopDrawing = () => {
            drawing = false;
        };
        
        canvas.addEventListener('mousedown', startDrawing);
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', stopDrawing);
        canvas.addEventListener('mouseleave', stopDrawing);
        canvas.addEventListener('touchstart', startDrawing);
        canvas.addEventListener('touchmove', draw);
        canvas.addEventListener('touchend', stopDrawing);
    }
    
    clearCurrentPage() {
        const canvas = this.pages[this.currentPage];
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        if (this.isTeacher) {
            this.socket.emit('whiteboard_clear', { room: this.roomId, pageIndex: this.currentPage });
        }
    }
    
    setColor(color) {
        this.color = color;
        this.isErasing = false;
    }
    
    setSize(size) {
        this.size = size;
    }
    
    setErasing(erasing) {
        this.isErasing = erasing;
    }
    
    saveAsPDF() {
        // Используем html2canvas + jsPDF
        // Сначала покажем страницы по очереди
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('landscape');
        let promiseChain = Promise.resolve();
        this.pages.forEach((canvas, idx) => {
            promiseChain = promiseChain.then(() => {
                return html2canvas(canvas, { scale: 2 }).then(imgData => {
                    if (idx !== 0) pdf.addPage();
                    pdf.addImage(imgData, 'JPEG', 10, 10, 280, 190);
                });
            });
        });
        promiseChain.then(() => {
            pdf.save('whiteboard.pdf');
        });
    }
    
    syncDraw(data) {
        if (this.isTeacher) return; // учитель не синхронизирует от других
        const { pageIndex, type, data: drawData } = data;
        if (pageIndex !== this.currentPage) return;
        const canvas = this.pages[pageIndex];
        const ctx = canvas.getContext('2d');
        ctx.beginPath();
        ctx.moveTo(drawData.x0, drawData.y0);
        ctx.lineTo(drawData.x1, drawData.y1);
        ctx.strokeStyle = drawData.erasing ? '#FFFFFF' : drawData.color;
        ctx.lineWidth = drawData.size;
        ctx.stroke();
    }
    
    syncClear(pageIndex) {
        if (this.isTeacher) return;
        if (pageIndex === this.currentPage) {
            const canvas = this.pages[this.currentPage];
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'white';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }
    }
    
    addPageFromTeacher(pageIndex) {
        if (!this.isTeacher) {
            // Ученик: добавляет новую страницу
            this.addNewPage();
            // Если учитель переключился на эту страницу, ученик переключится позднее
        }
    }
    
    changePage(pageIndex) {
        if (!this.isTeacher) {
            this.setCurrentPage(pageIndex);
        }
    }
    
    setupSocketEvents() {
        if (!this.socket) return;
        this.socket.on('whiteboard_draw', (data) => this.syncDraw(data));
        this.socket.on('whiteboard_clear', (data) => this.syncClear(data.pageIndex));
        this.socket.on('whiteboard_page_added', (data) => this.addPageFromTeacher(data.pageIndex));
        this.socket.on('whiteboard_change_page', (data) => this.changePage(data.pageIndex));
    }
    
    initCanvas() {
        // Привязываем кнопки управления
        document.getElementById('wb-clear')?.addEventListener('click', () => this.clearCurrentPage());
        document.getElementById('wb-color')?.addEventListener('change', (e) => this.setColor(e.target.value));
        document.getElementById('wb-size')?.addEventListener('input', (e) => this.setSize(parseInt(e.target.value)));
        document.getElementById('wb-erase')?.addEventListener('click', () => this.setErasing(true));
        document.getElementById('wb-pen')?.addEventListener('click', () => this.setErasing(false));
        document.getElementById('wb-new-page')?.addEventListener('click', () => this.addNewPage());
        document.getElementById('wb-prev-page')?.addEventListener('click', () => this.prevPage());
        document.getElementById('wb-next-page')?.addEventListener('click', () => this.nextPage());
        document.getElementById('wb-save-pdf')?.addEventListener('click', () => this.saveAsPDF());
    }
}