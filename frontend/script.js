// frontend/script.js
const API_URL = "http://localhost:8080";

let currentSessionId = null;
let currentUserId = null;
let currentQuestions = [];
let currentUserRole = 'student';

// Таймеры для отслеживания времени
let lessonStartTime = null;
let taskStartTimes = {};
let currentLessonId = null;

// ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function renderMath() {
    if (window.MathJax) {
        setTimeout(() => {
            MathJax.typesetPromise().catch(err => console.log('MathJax error:', err));
        }, 100);
    }
}

function showModal(content) {
    const oldModals = document.querySelectorAll('.custom-modal');
    oldModals.forEach(modal => modal.remove());
    const oldOverlays = document.querySelectorAll('.modal-overlay');
    oldOverlays.forEach(overlay => overlay.remove());

    const modalHtml = `
        <div class="custom-modal" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                    background: white; padding: 30px; border-radius: 20px; 
                    max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3); z-index: 1001;">
            <button onclick="this.closest('.custom-modal').remove(); document.querySelector('.modal-overlay')?.remove();" 
                    style="float: right; background: #dc3545; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer;">✕</button>
            <div style="clear: both;"></div>
            ${content}
        </div>
    `;

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.background = 'rgba(0,0,0,0.5)';
    overlay.style.zIndex = '1000';
    overlay.onclick = () => {
        overlay.remove();
        const modal = document.querySelector('.custom-modal');
        if (modal) modal.remove();
    };

    const modalDiv = document.createElement('div');
    modalDiv.innerHTML = modalHtml;
    document.body.appendChild(overlay);
    document.body.appendChild(modalDiv);
}

// ========== ФУНКЦИИ ТАЙМЕРОВ ==========
function startLessonTimer() {
    lessonStartTime = Date.now();
    taskStartTimes = {};
    console.log("Lesson timer started");
}

function startTaskTimer(taskId) {
    taskStartTimes[taskId] = Date.now();
    console.log(`Task ${taskId} timer started`);
}

function stopTaskTimer(taskId) {
    if (taskStartTimes[taskId]) {
        const spent = (Date.now() - taskStartTimes[taskId]) / 1000;
        if (!window.taskTimes) window.taskTimes = {};
        window.taskTimes[taskId] = (window.taskTimes[taskId] || 0) + spent;
        delete taskStartTimes[taskId];
        console.log(`Task ${taskId} time: ${spent.toFixed(1)}s, total: ${window.taskTimes[taskId].toFixed(1)}s`);
    }
}

function getTotalLessonTime() {
    if (lessonStartTime) {
        return (Date.now() - lessonStartTime) / 1000;
    }
    return 0;
}

// ========== ГЛОБАЛЬНАЯ ФУНКЦИЯ ДЛЯ onchange СЕЛЕКТОРА ==========
window.setRole = function(role) {
    currentUserRole = role;
    const teacherPanel = document.getElementById('teacherPanel');
    if (teacherPanel) {
        if (role === 'teacher' && currentUserId) {
            teacherPanel.style.display = 'block';
        } else {
            teacherPanel.style.display = 'none';
        }
    }
};

// ========== ОСНОВНЫЕ ФУНКЦИИ ОБУЧЕНИЯ ==========
async function startLearning() {
    const name = document.getElementById('userName').value;
    const email = document.getElementById('userEmail').value;
    const exam = document.getElementById('examName').value;

    if (!name || !email || !exam) {
        alert('Пожалуйста, заполните все поля');
        return;
    }

    try {
        const role = document.getElementById('userRole') ? document.getElementById('userRole').value : 'student';
        console.log("1. Создаём пользователя с ролью:", role);

        const userRes = await fetch(`${API_URL}/api/users?role=${role}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email })
        });
        if (!userRes.ok) throw new Error(`HTTP ${userRes.status}: ${await userRes.text()}`);
        const user = await userRes.json();
        currentUserId = user.id;

        console.log("Пользователь создан:", user);

        if (role === 'teacher') {
            currentUserRole = 'teacher';
            alert(`Добро пожаловать, учитель ${name}!`);
            document.getElementById('step1').style.display = 'none';
            document.getElementById('teacherPanel').style.display = 'block';
            document.getElementById('studentPanel').style.display = 'none';
            return;
        }

        currentUserRole = 'student';
        alert(`Добро пожаловать, ${name}! Вы можете вступить в школу через кнопку "Вступить в школу" или продолжить обучение.`);

        document.getElementById('teacherPanel').style.display = 'none';
        document.getElementById('studentPanel').style.display = 'block';

        console.log("2. Создаём сессию...");
        const sessionRes = await fetch(`${API_URL}/api/sessions?user_id=${currentUserId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exam_name: exam })
        });
        if (!sessionRes.ok) throw new Error(`HTTP ${sessionRes.status}: ${await sessionRes.text()}`);
        const session = await sessionRes.json();
        currentSessionId = session.id;
        console.log("Сессия создана:", session);

        console.log("3. Получаем тест...");
        const testRes = await fetch(`${API_URL}/api/sessions/${currentSessionId}`);
        if (!testRes.ok) throw new Error(`HTTP ${testRes.status}: ${await testRes.text()}`);
        const sessionData = await testRes.json();
        if (!sessionData.test_results || sessionData.test_results.length === 0) throw new Error("Тест не найден");
        const testResult = sessionData.test_results[0];
        currentQuestions = testResult.questions;
        console.log(`Загружено ${currentQuestions.length} вопросов`);

        displayTest(currentQuestions);
        document.getElementById('step1').style.display = 'none';
        document.getElementById('step2').style.display = 'block';

    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка: ' + error.message);
    }
}

function displayTest(questions) {
    const container = document.getElementById('testQuestions');
    container.innerHTML = '';
    questions.forEach((q, idx) => {
        const difficultyClass = q.difficulty === 'легкий' ? 'easy' : (q.difficulty === 'средний' ? 'medium' : 'hard');
        let questionText = q.question || q.text || 'Нет текста';
        const questionHtml = `
            <div class="question-card">
                <h3>${q.topic || 'Без темы'}</h3>
                <span class="difficulty ${difficultyClass}">${q.difficulty || 'средний'}</span>
                <p>${questionText}</p>
                <div class="answer-input">
                    <input type="text" id="answer_${idx}" placeholder="Ваш ответ">
                </div>
            </div>
        `;
        container.innerHTML += questionHtml;
    });
    renderMath();
}

async function submitTest() {
    const answers = {};
    currentQuestions.forEach((_, idx) => {
        const answerInput = document.getElementById(`answer_${idx}`);
        if (answerInput) answers[idx] = answerInput.value;
    });
    try {
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/submit_test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answers })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        const result = await response.json();
        displayTestResults(result);
        document.getElementById('step2').style.display = 'none';
        document.getElementById('step3').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка при отправке теста: ' + error.message);
    }
}

function displayTestResults(results) {
    const container = document.getElementById('testResults');
    const topicsHtml = Object.entries(results.topic_scores || {}).map(([topic, score]) => `
        <div class="question-card">
            <h3>${topic}</h3>
            <div class="progress-bar" style="height:20px"><div class="progress-fill" style="width:${score}%">${score}%</div></div>
        </div>
    `).join('');
    container.innerHTML = `
        <div class="lesson-card">
            <h3>Общий результат: ${results.overall_score || 0}%</h3>
            <p><strong>Сильные темы:</strong> ${results.strong_topics?.join(', ') || 'нет'}</p>
            <p><strong>Слабые темы:</strong> ${results.weak_topics?.join(', ') || 'нет'}</p>
            <div class="theory"><strong>Детальный анализ:</strong><br>${results.detailed_feedback || 'Нет анализа'}</div>
            <h4>Результаты по темам:</h4>
            ${topicsHtml}
        </div>
    `;
    renderMath();
}

async function setTimeAndPlan() {
    const days = parseInt(document.getElementById('daysAvailable').value);
    if (!days || days < 1) { alert('Укажите количество дней'); return; }
    try {
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/set_time`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ days })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        const plan = await response.json();
        displayPlan(plan);
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step4').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка при создании плана: ' + error.message);
    }
}

function displayPlan(plan) {
    const container = document.getElementById('studyPlan');
    const scheduleHtml = (plan.schedule || []).map(day => `
        <div class="lesson-card">
            <h3>День ${day.day}</h3>
            <p><strong>Темы:</strong> ${day.topics?.join(', ') || 'тестирование'}</p>
            <p><strong>Часов:</strong> ${day.hours || 3}</p>
            <p><strong>Тип:</strong> ${day.type === 'theory' ? 'Теория' : (day.type === 'test' ? 'Тестирование' : day.type)}</p>
            <p>${day.description || day.tasks || ''}</p>
        </div>
    `).join('');
    container.innerHTML = `
        <div class="lesson-card">
            <h3>Стратегия подготовки</h3>
            <p>${plan.strategy || 'Индивидуальный план'}</p>
            <p><strong>Всего дней:</strong> ${plan.total_days || plan.schedule?.length || 30}</p>
            <p><strong>Часов в день:</strong> ${plan.hours_per_day || 3}</p>
        </div>
        <h3>Расписание:</h3>
        ${scheduleHtml}
    `;
    renderMath();
}

async function startLearningMode() {
    console.log("===== startLearningMode вызвана =====");
    console.log("currentSessionId:", currentSessionId);
    document.getElementById('step4').style.display = 'none';
    document.getElementById('step5').style.display = 'block';
    await loadNextLesson();
}

async function loadNextLesson() {
    console.log("===== loadNextLesson вызвана =====");
    console.log("sessionId:", currentSessionId);

    if (!currentSessionId) {
        console.error("Нет sessionId!");
        document.getElementById('lessonContent').innerHTML = '<p style="color:red;">Ошибка: сессия не найдена</p>';
        return;
    }

    try {
        const url = `${API_URL}/api/sessions/${currentSessionId}/next_lesson`;
        console.log("Запрос:", url);
        const response = await fetch(url);
        console.log("Статус ответа:", response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error("Ошибка сервера:", errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        console.log("Данные урока:", data);

        if (data.status === 'completed') {
            showCompletionMessage(data.message);
        } else if (data.status === 'test_needed') {
            console.log("Требуется промежуточный тест");
            document.getElementById('lessonContent').innerHTML = '<p>Пройдите промежуточное тестирование</p>';
            await loadProgressTest();
        } else if (data.status === 'lesson') {
            console.log("Урок получен, тема:", data.topic);
            displayLesson(data);
            startLessonTimer();
        } else {
            console.warn("Неизвестный статус:", data);
            document.getElementById('lessonContent').innerHTML = `<p>Статус: ${data.status}. Сообщение: ${data.message || 'нет'}</p>`;
        }

        await updateProgress();

    } catch (error) {
        console.error('Ошибка при загрузке урока:', error);
        document.getElementById('lessonContent').innerHTML = `<p style="color:red;">Ошибка: ${error.message}</p>`;
    }
}

function displayLesson(lessonData) {
    console.log("Отображение урока:", lessonData);
    const container = document.getElementById('lessonContent');
    const content = lessonData.content || {};
    currentLessonId = lessonData.lesson_id;

    let theoryText = content.theory || 'Нет теории';
    theoryText = theoryText.replace(/\\\\\(/g, '\\(').replace(/\\\\\)/g, '\\)');

    let examplesHtml = '';
    if (content.examples && content.examples.length) {
        examplesHtml = '<h3>📝 Примеры:</h3>' + content.examples.map((ex, idx) => `
            <div class="example">
                <strong>Задача:</strong> ${ex.problem}<br>
                <strong>Решение:</strong> ${ex.solution}
            </div>
        `).join('');
    }

    let tasksHtml = '';
    if (content.tasks && content.tasks.length) {
        tasksHtml = '<h3>✍️ Задачи для самостоятельного решения:</h3>';
        tasksHtml += '<div id="tasks-container">';
        tasksHtml += content.tasks.map((task, idx) => `
            <div class="task" data-task-idx="${idx}">
                <p><strong>Задача ${idx + 1}:</strong> ${task.task}</p>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <input type="text" id="task_${idx}" placeholder="Ваш ответ" class="answer-input" style="flex: 1;" onfocus="startTaskTimer(${idx})" onblur="stopTaskTimer(${idx})">
                    <button class="btn-secondary" style="padding: 5px 10px;" onclick="uploadPhotoForTask(${idx})">📷 Загрузить фото</button>
                </div>
            </div>
        `).join('');
        tasksHtml += '</div>';
        tasksHtml += `<button onclick="submitLesson(${lessonData.lesson_id})" class="btn-primary">Отправить ответы</button>`;
    }

    let tipsHtml = '';
    if (content.tips && content.tips.length) {
        tipsHtml = '<div class="tips"><strong>💡 Советы:</strong><br>' + content.tips.map(tip => `• ${tip}<br>`).join('') + '</div>';
    }

    container.innerHTML = `
        <div class="lesson-card">
            <h2>${lessonData.topic || 'Новая тема'}</h2>
            <div class="theory"><strong>📖 Теория:</strong><br>${marked.parse(theoryText)}</div>
            ${examplesHtml}
            ${tasksHtml}
            ${tipsHtml}
        </div>
        <div class="video-section">
            <button onclick="generateVideo(${lessonData.lesson_id})" class="btn-secondary">🎬 Создать видео-урок</button>
            <div id="videoStatus_${lessonData.lesson_id}" style="margin-top: 10px;"></div>
        </div>
        <div class="bot-chat">
            <h3>🤖 Помощник ИИ</h3>
            <div id="chatMessages" style="height: 200px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px;"></div>
            <input type="text" id="chatQuestion" placeholder="Задайте вопрос по теме урока..." style="width: 80%;">
            <button onclick="askBot(${lessonData.lesson_id})">Спросить</button>
        </div>
    `;

    renderMath();
    window.taskTimes = {};
}

async function submitLesson(lessonId) {
    // Останавливаем все активные таймеры задач
    for (let taskId in taskStartTimes) {
        stopTaskTimer(parseInt(taskId));
    }

    const totalTime = getTotalLessonTime();
    const tasks = document.querySelectorAll('[id^="task_"]');
    const answers = {};
    tasks.forEach((task, idx) => { answers[idx] = task.value; });

    console.log(`Submitting lesson ${lessonId}, time spent: ${totalTime.toFixed(1)}s, task times:`, window.taskTimes);

    try {
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/submit_lesson`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lesson_id: lessonId,
                user_answers: answers,
                time_spent_seconds: Math.round(totalTime),
                task_times: window.taskTimes || {}
            })
        });
        const result = await response.json();

        if (result.status === 'failed') {
            let feedbackHtml = '<div class="feedback-errors"><h3>❌ Ошибки в задачах:</h3><ul>';
            for (let r of result.results) {
                if (!r.correct) {
                    feedbackHtml += `<li>
                        <strong>Задача ${r.task_index + 1}:</strong><br>
                        Ваш ответ: "${r.user_answer || '(пусто)'}"<br>
                        Правильный ответ: "${r.correct_answer}"<br>
                        <span style="color: #666;">${r.hint || 'Проверьте решение'}</span>
                    </li>`;
                }
            }
            feedbackHtml += '</ul><p>Исправьте ответы и отправьте снова.</p></div>';
            const lessonContent = document.getElementById('lessonContent');
            const existingFeedback = document.querySelector('.feedback-errors');
            if (existingFeedback) existingFeedback.remove();
            lessonContent.insertAdjacentHTML('afterbegin', feedbackHtml);
        } else if (result.status === 'success') {
            alert(`✅ Урок завершен! Результат: ${result.score}%`);
            window.taskTimes = {};
            lessonStartTime = null;
            await loadNextLesson();
            await updateProgress();
        }
    } catch (error) {
        console.error(error);
        alert('Ошибка при отправке ответов: ' + error.message);
    }
}

async function askBot(lessonId) {
    const question = document.getElementById('chatQuestion').value;
    if (!question) return;
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML += `<div><b>Вы:</b> ${question}</div>`;
    document.getElementById('chatQuestion').value = '';
    try {
        const response = await fetch(`${API_URL}/api/lessons/${lessonId}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, question: question })
        });
        const data = await response.json();
        chatMessages.innerHTML += `<div><b>Бот:</b> ${data.answer}</div>`;
        chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (error) {
        chatMessages.innerHTML += `<div><b>Бот:</b> Ошибка, попробуйте позже.</div>`;
    }
}

async function loadProgressTest() {
    try {
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/progress_test`, { method: 'POST' });
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        const data = await response.json();
        displayTest(data.questions);
        document.getElementById('lessonContent').style.display = 'none';
        document.getElementById('testContent').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка при загрузке теста: ' + error.message);
    }
}

async function updateProgress() {
    try {
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/progress`);
        if (!response.ok) return;
        const history = await response.json();
        if (history && history.length) {
            const lastProgress = history[history.length - 1];
            const profile = lastProgress.profile_snapshot || {};
            const values = Object.values(profile);
            const avgProgress = values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
            const fill = document.getElementById('progressFill');
            if (fill) {
                fill.style.width = `${avgProgress}%`;
                fill.textContent = `${Math.round(avgProgress)}%`;
            }
            document.getElementById('progressStats').innerHTML = `<p>Общий прогресс: ${Math.round(avgProgress)}%</p><p>Изучено тем: ${Object.keys(profile).length}</p>`;
        }
    } catch (e) { console.error(e); }
}

function showCompletionMessage(message) {
    document.getElementById('lessonContent').innerHTML = `
        <div class="lesson-card" style="text-align:center; background:#d4edda;">
            <h2>🎉 ${message}</h2>
            <p>Вы успешно завершили курс!</p>
            <button onclick="location.reload()" class="btn-primary">Начать новый курс</button>
        </div>
    `;
    renderMath();
}

// ========== ПОЛЬЗОВАТЕЛЬСКИЕ ТЕСТЫ ==========
let currentCustomTestId = null;
let currentCustomQuestions = [];

function showTestCreator() {
    document.getElementById('customTestName').value = '';
    document.getElementById('customTestDesc').value = '';
    document.getElementById('questionsList').innerHTML = '';
    addQuestionField();
    document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
    document.getElementById('step6').style.display = 'block';
}

function addQuestionField() {
    const container = document.getElementById('questionsList');
    const questionId = Date.now();
    const questionHtml = `
        <div id="question_${questionId}" class="question-card">
            <h4>Вопрос ${container.children.length + 1}</h4>
            <textarea id="q_text_${questionId}" placeholder="Текст вопроса" rows="3" style="width:100%"></textarea>
            <input type="text" id="q_answer_${questionId}" placeholder="Правильный ответ">
            <textarea id="q_hint_${questionId}" placeholder="Пояснение (необязательно)" rows="2" style="width:100%"></textarea>
            <button onclick="removeQuestionField(${questionId})" class="remove-question">Удалить вопрос</button>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', questionHtml);
}

function removeQuestionField(questionId) {
    const element = document.getElementById(`question_${questionId}`);
    if (element) element.remove();
    const titles = document.querySelectorAll('#questionsList .question-card h4');
    titles.forEach((title, idx) => {
        title.textContent = `Вопрос ${idx + 1}`;
    });
}

async function saveCustomTest() {
    const name = document.getElementById('customTestName').value.trim();
    if (!name) {
        alert('Введите название теста');
        return;
    }

    const questionDivs = document.querySelectorAll('#questionsList .question-card');
    const questions = [];
    for (let div of questionDivs) {
        const textarea = div.querySelector('textarea');
        const answerInput = div.querySelector('input[type="text"]');
        const hintTextarea = div.querySelectorAll('textarea')[1];
        const text = textarea?.value.trim();
        const answer = answerInput?.value.trim();
        const hint = hintTextarea?.value.trim();
        if (!text || !answer) {
            alert('Заполните текст вопроса и правильный ответ для всех вопросов');
            return;
        }
        questions.push({ text: text, correct_answer: answer, explanation: hint || '' });
    }

    if (questions.length === 0) {
        alert('Добавьте хотя бы один вопрос');
        return;
    }

    const description = document.getElementById('customTestDesc').value.trim();

    try {
        const response = await fetch(`${API_URL}/api/custom_tests?user_id=${currentUserId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, description: description, questions: questions })
        });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        alert(`Тест "${data.name}" сохранён! ID: ${data.id}`);
        showCustomTestsList();
    } catch (error) {
        console.error(error);
        alert('Ошибка сохранения теста: ' + error.message);
    }
}

async function showCustomTestsList() {
    try {
        const response = await fetch(`${API_URL}/api/custom_tests?user_id=${currentUserId}`);
        const tests = await response.json();
        const container = document.getElementById('customTestsList');
        container.innerHTML = '';
        if (tests.length === 0) {
            container.innerHTML = '<p>У вас пока нет созданных тестов.</p>';
        } else {
            for (let test of tests) {
                const testDiv = document.createElement('div');
                testDiv.className = 'test-item';
                testDiv.innerHTML = `
                    <h3>${escapeHtml(test.name)}</h3>
                    <p>${test.description || 'Без описания'}</p>
                    <p><strong>Вопросов:</strong> ${test.questions.length}</p>
                    <div class="test-buttons">
                        <button onclick="startCustomTest(${test.id})">▶ Пройти тест</button>
                        <button onclick="deleteCustomTest(${test.id})">🗑 Удалить</button>
                        <button onclick="trainExistingTest(${test.id}, '${escapeHtml(test.name)}')">🤖 Обучить ИИ</button>
                        <button onclick="generateSimilar(${test.id}, '${escapeHtml(test.name)}')">🎲 Похожие вопросы</button>
                    </div>
                `;
                container.appendChild(testDiv);
            }
        }
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step7').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка загрузки тестов: ' + error.message);
    }
}

async function deleteCustomTest(testId) {
    if (!confirm('Удалить этот тест?')) return;
    try {
        const response = await fetch(`${API_URL}/api/custom_tests/${testId}?user_id=${currentUserId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await response.text());
        alert('Тест удалён');
        showCustomTestsList();
    } catch (error) {
        console.error(error);
        alert('Ошибка удаления: ' + error.message);
    }
}

async function trainExistingTest(testId, testName) {
    try {
        const response = await fetch(`${API_URL}/api/custom_tests/${testId}/train`, { method: 'POST' });
        const result = await response.json();
        alert(`Тест "${testName}" обучен!\n${result.message}`);
    } catch (error) {
        console.error(error);
        alert('Ошибка обучения: ' + error.message);
    }
}

async function startCustomTest(testId) {
    try {
        const response = await fetch(`${API_URL}/api/custom_tests/${testId}`);
        const test = await response.json();
        currentCustomTestId = test.id;
        currentCustomQuestions = test.questions;
        document.getElementById('takingTestName').textContent = test.name;
        const container = document.getElementById('takingTestQuestions');
        container.innerHTML = '';
        test.questions.forEach((q, idx) => {
            container.innerHTML += `
                <div class="question-card">
                    <h3>Вопрос ${idx + 1}</h3>
                    <p>${escapeHtml(q.text)}</p>
                    <div class="answer-input">
                        <input type="text" id="custom_answer_${idx}" placeholder="Ваш ответ">
                    </div>
                </div>
            `;
        });
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step8').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка загрузки теста: ' + error.message);
    }
}

async function submitCustomTest() {
    const answers = {};
    for (let i = 0; i < currentCustomQuestions.length; i++) {
        const input = document.getElementById(`custom_answer_${i}`);
        if (input) answers[i] = input.value;
    }
    try {
        const response = await fetch(`${API_URL}/api/custom_tests/${currentCustomTestId}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_id: currentCustomTestId, answers: answers })
        });
        const result = await response.json();
        let resultsHtml = `
            <div class="lesson-card">
                <h3>${escapeHtml(result.test_name)}</h3>
                <p><strong>Результат:</strong> ${result.correct}/${result.total} (${result.score.toFixed(1)}%)</p>
                <p><strong>Оценка:</strong> ${result.grade}</p>
                <h4>Разбор ответов:</h4>
        `;
        for (let i = 0; i < result.results.length; i++) {
            const r = result.results[i];
            const icon = r.is_correct ? '✅' : '❌';
            resultsHtml += `
                <div class="question-card" style="${r.is_correct ? 'border-left-color: green;' : 'border-left-color: red;'}">
                    <h4>${icon} Вопрос ${i + 1}</h4>
                    <p><strong>Вопрос:</strong> ${escapeHtml(r.question)}</p>
                    <p><strong>Ваш ответ:</strong> ${escapeHtml(r.user_answer) || '(пусто)'}</p>
                    <p><strong>Правильный ответ:</strong> ${escapeHtml(r.correct_answer)}</p>
                    ${r.explanation ? `<p><strong>Пояснение:</strong> ${escapeHtml(r.explanation)}</p>` : ''}
                </div>
            `;
        }
        resultsHtml += `</div>`;
        document.getElementById('customTestResults').innerHTML = resultsHtml;
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step9').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка отправки ответов: ' + error.message);
    }
}

async function generateSimilar(testId, testName) {
    const num = prompt('Сколько вопросов сгенерировать?', 5);
    if (!num) return;
    try {
        const response = await fetch(`${API_URL}/api/custom_tests/${testId}/generate_similar?num_questions=${num}`, { method: 'POST' });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        if (data.error) {
            alert('Ошибка: ' + data.error);
            return;
        }
        if (!data.questions || !Array.isArray(data.questions) || data.questions.length === 0) {
            alert('Не удалось сгенерировать вопросы. Попробуйте ещё раз.');
            return;
        }
        let msg = `Сгенерировано ${data.questions.length} вопросов по образцу "${testName}":\n\n`;
        data.questions.forEach((q, i) => {
            msg += `${i + 1}. ${q.question}\n   Ответ: ${q.correct_answer}\n\n`;
        });
        alert(msg);
        if (confirm('Хотите создать новый тест из этих вопросов?')) {
            document.getElementById('customTestName').value = `${testName} (копия)`;
            document.getElementById('customTestDesc').value = `Сгенерировано на основе теста "${testName}"`;
            const container = document.getElementById('questionsList');
            container.innerHTML = '';
            for (let q of data.questions) {
                const questionId = Date.now() + Math.random();
                container.insertAdjacentHTML('beforeend', `
                    <div id="question_${questionId}" class="question-card">
                        <h4>Вопрос</h4>
                        <textarea id="q_text_${questionId}" rows="3" style="width:100%">${escapeHtml(q.question)}</textarea>
                        <input type="text" id="q_answer_${questionId}" value="${escapeHtml(q.correct_answer)}">
                        <textarea id="q_hint_${questionId}" rows="2" style="width:100%">${escapeHtml(q.explanation || '')}</textarea>
                        <button onclick="removeQuestionField(${questionId})" class="remove-question">Удалить вопрос</button>
                    </div>
                `);
            }
            showTestCreator();
        }
    } catch (error) {
        console.error('Ошибка генерации:', error);
        alert('Ошибка генерации: ' + error.message);
    }
}

// ========== КУРСЫ И УРОКИ ==========
async function showCoursesList() {
    if (!currentUserId) { alert('Сначала создайте пользователя'); return; }
    try {
        const response = await fetch(`${API_URL}/api/courses?user_id=${currentUserId}`);
        const courses = await response.json();
        const container = document.getElementById('userCoursesList');
        container.innerHTML = '';
        if (courses.length === 0) {
            container.innerHTML = '<p>У вас пока нет созданных курсов.</p>';
        } else {
            for (let course of courses) {
                container.innerHTML += `
                    <div class="test-item">
                        <h3>${escapeHtml(course.name)}</h3>
                        <p>${escapeHtml(course.description || 'Без описания')}</p>
                        <p><strong>Статус:</strong> ${course.status}</p>
                        <div class="test-buttons">
                            <button onclick="viewCourse(${course.id})">👁️ Просмотр</button>
                            <button onclick="deleteCourse(${course.id})">🗑 Удалить</button>
                        </div>
                    </div>
                `;
            }
        }
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step10').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка загрузки курсов: ' + error.message);
    }
}

async function viewCourse(courseId) {
    try {
        const response = await fetch(`${API_URL}/api/courses/${courseId}`);
        const course = await response.json();
        window.currentCourseId = courseId;
        document.getElementById('courseViewTitle').textContent = course.name;
        document.getElementById('courseViewDescription').textContent = course.description || 'Нет описания';
        document.getElementById('courseViewCriteria').textContent = course.success_criteria || 'Не указаны';
        const modulesContainer = document.getElementById('courseModulesList');
        modulesContainer.innerHTML = '';
        for (let module of course.modules) {
            modulesContainer.innerHTML += `
                <div class="lesson-card">
                    <h3>📁 ${escapeHtml(module.title)}</h3>
                    <p>${escapeHtml(module.description || '')}</p>
                    <div style="margin-left: 20px;">
                        ${module.lessons.map(lesson => `
                            <div class="test-item" style="margin: 10px 0; cursor: pointer;" onclick="viewCourseLesson(${courseId}, ${lesson.id}, '${escapeHtml(lesson.title)}')">
                                <strong>📖 ${escapeHtml(lesson.title)}</strong>
                                <button class="btn-secondary" style="margin-left: 10px;" onclick="event.stopPropagation(); generateLessonContent(${courseId}, ${lesson.id})">✨ Сгенерировать содержание</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step10')?.setAttribute('step', 'step11');
        document.getElementById('step11').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка загрузки курса: ' + error.message);
    }
}

async function deleteCourse(courseId) {
    if (!confirm('Удалить этот курс?')) return;
    try {
        const response = await fetch(`${API_URL}/api/courses/${courseId}?user_id=${currentUserId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await response.text());
        alert('Курс удалён');
        showCoursesList();
    } catch (error) {
        console.error(error);
        alert('Ошибка удаления: ' + error.message);
    }
}

function showCreateCourseForm() {
    document.getElementById('newCourseName').value = '';
    document.getElementById('newCourseDesc').value = '';
    document.getElementById('newCourseCriteria').value = '';
    document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
    document.getElementById('step13').style.display = 'block';
}

async function createCourse() {
    if (!currentUserId) { alert('Сначала создайте пользователя'); return; }
    const name = document.getElementById('newCourseName').value.trim();
    if (!name) { alert('Введите название курса'); return; }
    const description = document.getElementById('newCourseDesc').value.trim();
    const successCriteria = document.getElementById('newCourseCriteria').value.trim();
    try {
        const response = await fetch(`${API_URL}/api/courses/generate?user_id=${currentUserId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, success_criteria: successCriteria })
        });
        if (!response.ok) throw new Error(await response.text());
        const course = await response.json();
        alert(`Курс "${course.name}" создан!`);
        showCoursesList();
    } catch (error) {
        console.error(error);
        alert('Ошибка: ' + error.message);
    }
}

async function showLessonsList() {
    if (!currentUserId) { alert('Сначала создайте пользователя'); return; }
    try {
        const response = await fetch(`${API_URL}/api/lessons?user_id=${currentUserId}`);
        const lessons = await response.json();
        const container = document.getElementById('userLessonsList');
        container.innerHTML = '';
        if (lessons.length === 0) {
            container.innerHTML = '<p>У вас пока нет созданных уроков.</p>';
        } else {
            for (let lesson of lessons) {
                container.innerHTML += `
                    <div class="test-item">
                        <h3>${escapeHtml(lesson.title)}</h3>
                        <p><strong>Предмет:</strong> ${escapeHtml(lesson.subject)}</p>
                        <p>${escapeHtml(lesson.description || 'Без описания')}</p>
                        <div class="test-buttons">
                            <button onclick="viewLesson(${lesson.id})">👁️ Просмотр</button>
                            <button onclick="deleteLesson(${lesson.id})">🗑 Удалить</button>
                        </div>
                    </div>
                `;
            }
        }
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step14').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка загрузки уроков: ' + error.message);
    }
}

async function viewLesson(lessonId) {
    try {
        const response = await fetch(`${API_URL}/api/lessons/${lessonId}`);
        const lesson = await response.json();
        document.getElementById('lessonViewTitle').textContent = lesson.title;
        document.getElementById('lessonViewSubject').textContent = lesson.subject;
        const content = lesson.content;
        let contentHtml = `
            <div class="lesson-card">
                <h3>📖 Теория</h3>
                <div class="theory">${marked.parse(content.theory || 'Теория не сгенерирована')}</div>
            </div>
            <div class="lesson-card">
                <h3>✍️ Практические задания</h3>
                ${(content.practice || []).map((p, i) => `
                    <div class="task">
                        <p><strong>Задача ${i + 1}:</strong> ${p.task}</p>
                        <p><em>Ответ: ${p.answer}</em></p>
                    </div>
                `).join('')}
            </div>
        `;
        document.getElementById('lessonViewContent').innerHTML = contentHtml;
        document.getElementById('lessonViewHomework').innerHTML = `
            <div class="lesson-card">
                <h3>🏠 Домашнее задание</h3>
                ${(content.homework || []).map((h, i) => `
                    <div class="task">
                        <p><strong>Задача ${i + 1}:</strong> ${h.task}</p>
                        <p><em>Ответ: ${h.answer}</em></p>
                    </div>
                `).join('')}
            </div>
        `;
        document.getElementById('lessonViewYoutube').innerHTML = `
            <div class="lesson-card">
                <h3>🎥 Видео по теме</h3>
                ${(lesson.youtube_urls || []).map(url => `<div><a href="${url}" target="_blank">${url}</a></div>`).join('')}
                ${lesson.youtube_urls?.length === 0 ? '<p>Нет видео</p>' : ''}
            </div>
        `;
        window.currentLessonId = lessonId;
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step12').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка загрузки урока: ' + error.message);
    }
}

async function deleteLesson(lessonId) {
    if (!confirm('Удалить этот урок?')) return;
    try {
        const response = await fetch(`${API_URL}/api/lessons/${lessonId}?user_id=${currentUserId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await response.text());
        alert('Урок удалён');
        showLessonsList();
    } catch (error) {
        console.error(error);
        alert('Ошибка удаления: ' + error.message);
    }
}

function showCreateLessonForm() {
    document.getElementById('newLessonTitle').value = '';
    document.getElementById('newLessonSubject').value = '';
    document.getElementById('newLessonDesc').value = '';
    document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
    document.getElementById('step15').style.display = 'block';
}

async function createLesson() {
    if (!currentUserId) { alert('Сначала создайте пользователя'); return; }
    const title = document.getElementById('newLessonTitle').value.trim();
    if (!title) { alert('Введите название урока'); return; }
    const subject = document.getElementById('newLessonSubject').value.trim();
    if (!subject) { alert('Введите предмет'); return; }
    const description = document.getElementById('newLessonDesc').value.trim();
    try {
        const response = await fetch(`${API_URL}/api/lessons/generate?user_id=${currentUserId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, subject, description })
        });
        if (!response.ok) throw new Error(await response.text());
        const lesson = await response.json();
        alert(`Урок "${lesson.title}" создан!`);
        showLessonsList();
    } catch (error) {
        console.error(error);
        alert('Ошибка: ' + error.message);
    }
}

async function generatePresentation() {
    if (!window.currentLessonId) return;
    try {
        const response = await fetch(`${API_URL}/api/lessons/${window.currentLessonId}/generate_presentation`, { method: 'POST' });
        const data = await response.json();
        if (data.presentation_url) window.open(data.presentation_url, '_blank');
        else alert('Ошибка генерации презентации');
    } catch (error) {
        console.error(error);
        alert('Ошибка: ' + error.message);
    }
}

async function generateVideo(lessonId) {
    const statusDiv = document.getElementById(`videoStatus_${lessonId}`);
    if (!statusDiv) return;
    statusDiv.innerHTML = '⏳ Генерация видео... (20-40 секунд)';
    try {
        const response = await fetch(`${API_URL}/api/lessons/${lessonId}/generate_video`, { method: 'POST' });
        const data = await response.json();
        if (data.video_url) statusDiv.innerHTML = `<a href="${data.video_url}" target="_blank">▶ Смотреть видео-урок</a>`;
        else statusDiv.innerHTML = data.message;
    } catch (error) {
        statusDiv.innerHTML = '❌ Ошибка: ' + error.message;
    }
}

async function showStudentPlan() {
    if (!currentSessionId) {
        alert("Сначала создайте сессию (начните обучение)");
        return;
    }
    try {
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/study_plan`);
        if (!response.ok) throw new Error(await response.text());
        const plan = await response.json();
        // Показываем план в модальном окне, а не в displayPlan
        let planHtml = `
            <h3>📅 Мой план подготовки</h3>
            <p><strong>Стратегия:</strong> ${plan.strategy || 'Не указана'}</p>
            <p><strong>Всего дней:</strong> ${plan.total_days || 0}</p>
            <p><strong>Часов в день:</strong> ${plan.hours_per_day || 0}</p>
            <h4>Расписание:</h4>
        `;
        if (plan.schedule && plan.schedule.length) {
            for (let day of plan.schedule) {
                const typeIcon = day.type === 'theory' ? '📖' : (day.type === 'test' ? '📝' : '🔄');
                planHtml += `
                    <div style="border-bottom:1px solid #ccc; margin-bottom: 10px;">
                        <strong>${typeIcon} День ${day.day}:</strong> ${day.type === 'theory' ? 'Теория' : (day.type === 'test' ? 'Тест' : 'Повторение')}<br>
                        Темы: ${day.topics?.join(', ') || '—'}<br>
                        Часов: ${day.hours || 3}<br>
                        Описание: ${day.description || day.tasks || ''}
                    </div>
                `;
            }
        } else {
            planHtml += '<p>Нет расписания</p>';
        }
        showModal(planHtml);
    } catch (error) {
        console.error(error);
        alert('Ошибка загрузки плана: ' + error.message);
    }
}

async function showStudentPlanForTeacher(studentId, schoolId) {
    const sessionId = prompt("Введите ID сессии ученика (можно узнать у ученика или из БД):");
    if (!sessionId) return;
    try {
        const response = await fetch(`${API_URL}/api/sessions/${sessionId}/study_plan`);
        if (!response.ok) throw new Error(await response.text());
        const plan = await response.json();
        showModal(`
            <h3>📅 План ученика (сессия ${sessionId})</h3>
            <p><strong>Стратегия:</strong> ${plan.strategy || 'Не указана'}</p>
            <p><strong>Всего дней:</strong> ${plan.total_days || 0}</p>
            <p><strong>Часов в день:</strong> ${plan.hours_per_day || 0}</p>
            <h4>Расписание:</h4>
            ${(plan.schedule || []).map(day => `
                <div style="border-bottom:1px solid #ccc; margin-bottom: 10px;">
                    <strong>День ${day.day}:</strong> ${day.type === 'theory' ? '📖 Теория' : (day.type === 'test' ? '📝 Тест' : '🔄 Повторение')}<br>
                    Темы: ${day.topics?.join(', ') || '—'}<br>
                    Часов: ${day.hours || 3}<br>
                    Описание: ${day.description || day.tasks || ''}
                </div>
            `).join('')}
        `);
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

// ========== УЧИТЕЛЬСКИЕ ФУНКЦИИ ==========
async function showCreateSchoolForm() {
    const name = prompt("Название школы:");
    if (!name) return;
    const description = prompt("Описание школы (необязательно):");
    const response = await fetch(`${API_URL}/api/schools/create?user_id=${currentUserId}&name=${encodeURIComponent(name)}&description=${encodeURIComponent(description || '')}`, { method: 'POST' });
    const result = await response.json();
    if (response.ok) alert(`Школа "${result.name}" создана! Код: ${result.invite_code}`);
    else alert("Ошибка: " + result.detail);
}

async function showJoinSchoolForm() {
    const inviteCode = prompt("Введите код приглашения:");
    if (!inviteCode) return;
    const response = await fetch(`${API_URL}/api/schools/join?user_id=${currentUserId}&invite_code=${inviteCode}`, { method: 'POST' });
    const result = await response.json();
    if (response.ok) alert(`Вы присоединились к школе "${result.school_name}" как ${result.role}`);
    else alert("Ошибка: " + result.detail);
}

async function askStudentSessionId(studentId) {
    const sessionId = prompt(`Введите ID активной сессии ученика ${studentId} (можно посмотреть в БД или спросить у ученика):`);
    if (!sessionId) return;
    try {
        const response = await fetch(`${API_URL}/api/sessions/${sessionId}/study_plan`);
        if (!response.ok) throw new Error(await response.text());
        const plan = await response.json();
        let planHtml = `
            <h3>📅 План подготовки ученика (сессия ${sessionId})</h3>
            <p><strong>Стратегия:</strong> ${plan.strategy || 'Не указана'}</p>
            <p><strong>Всего дней:</strong> ${plan.total_days || 0}</p>
            <p><strong>Часов в день:</strong> ${plan.hours_per_day || 0}</p>
            <h4>Расписание:</h4>
        `;
        if (plan.schedule && plan.schedule.length) {
            for (let day of plan.schedule) {
                const typeIcon = day.type === 'theory' ? '📖' : (day.type === 'test' ? '📝' : '🔄');
                planHtml += `
                    <div style="border-bottom:1px solid #ccc; margin-bottom: 10px;">
                        <strong>${typeIcon} День ${day.day}:</strong> ${day.type === 'theory' ? 'Теория' : (day.type === 'test' ? 'Тест' : 'Повторение')}<br>
                        Темы: ${day.topics?.join(', ') || '—'}<br>
                        Часов: ${day.hours || 3}<br>
                        Описание: ${day.description || day.tasks || ''}
                    </div>
                `;
            }
        } else {
            planHtml += '<p>Нет расписания</p>';
        }
        showModal(planHtml);
    } catch (error) {
        alert('Ошибка загрузки плана: ' + error.message);
    }
}

async function showSchoolStats() {
    const schoolId = prompt("Введите ID школы:");
    if (!schoolId) return;
    
    if (!currentUserId) {
        alert("Сначала создайте пользователя");
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/api/schools/${schoolId}/stats?teacher_id=${currentUserId}`);
        if (!response.ok) throw new Error(await response.text());
        
        const data = await response.json();
        
        let html = `<h3>📊 ${escapeHtml(data.school_name)}</h3>`;
        html += `<p>👥 Всего учеников: ${data.total_students}</p>`;
        
        if (data.students && data.students.length > 0) {
            html += '<table style="width:100%; border-collapse: collapse;">';
            html += '<tr style="background: #667eea; color: white;"><th style="padding: 10px;">ID</th><th style="padding: 10px;">Имя</th><th style="padding: 10px;">Средний уровень</th><th style="padding: 10px;">Время (ч)</th><th style="padding: 10px;">Прогресс</th><th style="padding: 10px;">План</th></tr>';
            
            for (let student of data.students) {
                const avgMastery = student.average_mastery || 0;
                const totalTime = student.total_time_spent_hours || 0;
                html += `<tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 10px;">${student.user_id}</td>
                            <td style="padding: 10px;">${escapeHtml(student.name)}</td>
                            <td style="padding: 10px;">${avgMastery.toFixed(1)}%</td>
                            <td style="padding: 10px;">${totalTime.toFixed(1)} ч</td>
                            <td style="padding: 10px;"><button onclick="viewStudentGraphs(${student.user_id}, ${schoolId})">📈 Графы</button></td>
                            <td style="padding: 10px;"><button onclick="askStudentSessionId(${student.user_id})">📅 План</button></td>
                          </tr>`;
            }
            html += '</table>';
        } else {
            html += '<p>Нет учеников в школе</p>';
        }
        
        showModal(html);
        
    } catch (error) {
        console.error(error);
        alert('Ошибка: ' + error.message);
    }
}

async function showTeacherGraphs() {
    const schoolId = prompt("Введите ID школы:");
    if (!schoolId) return;
    
    if (!currentUserId) {
        alert("Сначала создайте пользователя");
        return;
    }
    
    try {
        // Получаем список учеников школы
        const statsResponse = await fetch(`${API_URL}/api/schools/${schoolId}/stats?teacher_id=${currentUserId}`);
        if (!statsResponse.ok) throw new Error(await statsResponse.text());
        const statsData = await statsResponse.json();
        
        if (!statsData.students || statsData.students.length === 0) {
            alert("В этой школе нет учеников.");
            return;
        }
        
        let studentList = "Выберите ученика:\n";
        statsData.students.forEach(s => {
            studentList += `${s.user_id} - ${s.name}\n`;
        });
        const studentId = prompt(studentList + "\nВведите ID ученика:");
        if (!studentId) return;
        
        await viewStudentGraphs(parseInt(studentId), parseInt(schoolId));
        
    } catch (error) {
        console.error(error);
        alert('Ошибка: ' + error.message);
    }
}

async function viewStudentGraphs(studentId, schoolId) {
    try {
        const response = await fetch(`${API_URL}/api/users/${studentId}/learning_graphs?school_id=${schoolId}`);
        if (!response.ok) throw new Error(await response.text());
        
        const data = await response.json();
        
        let html = `<h3>📊 Графы знаний ученика ID ${studentId}</h3>`;
        
        // Целевой граф
        html += '<h4>🎯 Целевой граф (экзамен)</h4>';
        if (data.target_graph && data.target_graph.length > 0) {
            html += '<ul>';
            for (let t of data.target_graph) {
                const value = t.value || 0;
                const hours = t.hours || 0;
                const difficulty = t.difficulty || 'средний';
                html += `<li><strong>${escapeHtml(t.topic)}</strong>: вес ${value}%, ${hours} часов, сложность ${difficulty}</li>`;
            }
            html += '</ul>';
        } else {
            html += '<p>Нет данных. Постройте целевой граф для этого ученика.</p>';
        }
        
        // Текущий граф
        html += '<h4>📈 Текущий граф (прогресс)</h4>';
        if (data.current_graph && data.current_graph.length > 0) {
            html += '<ul>';
            for (let t of data.current_graph) {
                const value = t.value || 0;
                html += `<li><strong>${escapeHtml(t.topic)}</strong>: ${value.toFixed(1)}%</li>`;
            }
            html += '</ul>';
        } else {
            html += '<p>Нет данных о прогрессе.</p>';
        }
        
        // Коэффициент успеваемости
        const coefRes = await fetch(`${API_URL}/api/users/${studentId}/coefficient?school_id=${schoolId}`);
        if (coefRes.ok) {
            const coefData = await coefRes.json();
            if (coefData && coefData.coefficient !== undefined) {
                html += `<h4>📐 Коэффициент успеваемости: ${coefData.coefficient.toFixed(1)}%</h4>`;
                html += `<p>${coefData.recommendation || ''}</p>`;
            }
        }
        
        showModal(html);
        
    } catch (error) {
        console.error(error);
        alert('Ошибка: ' + error.message);
    }
}

async function buildTargetGraph() {
    const examName = document.getElementById('examName').value;
    if (!examName) {
        alert("Введите название экзамена");
        return;
    }
    const studentId = prompt("Для какого ученика построить целевой граф? (введите ID ученика):");
    if (!studentId) return;
    const schoolId = prompt("Введите ID школы, в которой состоит ученик:");
    if (!schoolId) return;
    
    const response = await fetch(`${API_URL}/api/users/${studentId}/build_target_graph?exam_name=${encodeURIComponent(examName)}&school_id=${schoolId}`, {
        method: 'POST'
    });
    const data = await response.json();
    
    if (response.ok) {
        alert(`Целевой граф для ученика ${studentId} (школа ${schoolId}) построен! Рекомендуемое время: ${data.total_days} дней`);
        if (confirm("Показать графы этого ученика?")) {
            viewStudentGraphs(parseInt(studentId), parseInt(schoolId));
        }
    } else {
        alert("Ошибка: " + data.detail);
    }
}

// ========== ФУНКЦИИ ДЛЯ УЧЕНИКА ==========
async function showStudentGraphs() {
    if (!currentUserId) {
        alert("Сначала создайте пользователя");
        return;
    }
    try {
        const perfResponse = await fetch(`${API_URL}/api/user/detailed_stats?user_id=${currentUserId}`);
        if (!perfResponse.ok) throw new Error(await perfResponse.text());
        const stats = await perfResponse.json();
        
        // Фильтруем только темы, где были попытки (total_count > 0)
        const topicsWithProgress = stats.topics_detail?.filter(t => t.total_count > 0) || [];
        
        if (!topicsWithProgress.length) {
            alert("Нет данных о прогрессе. Пройдите несколько уроков.");
            return;
        }
        
        let html = '<h3>📊 Моя успеваемость</h3>';
        for (let item of topicsWithProgress) {
            const mastery = item.mastery_level || 0;
            const color = mastery >= 70 ? '#28a745' : (mastery >= 40 ? '#ffc107' : '#dc3545');
            const status = mastery >= 70 ? '✅ Освоено' : (mastery >= 40 ? '⚠️ В процессе' : '❌ Требует внимания');
            html += `
                <div style="margin:15px 0;padding:15px;background:#f8f9fa;border-radius:10px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                        <strong>${escapeHtml(item.topic)}</strong>
                        <span style="color:${color}">${status}</span>
                    </div>
                    <div style="background:#e0e0e0;height:25px;border-radius:12px;overflow:hidden">
                        <div style="background:${color};width:${mastery}%;height:25px;text-align:center;color:white;font-size:12px;line-height:25px">${mastery.toFixed(0)}%</div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:#666">
                        <span>✅ ${item.correct_count}/${item.total_count}</span>
                        <span>⏱️ ${item.total_time_spent_minutes?.toFixed(1) || 0} мин</span>
                    </div>
                </div>
            `;
        }
        const avgLevel = stats.average_mastery || 0;
        html += `
            <div style="margin-top:20px;padding:15px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:10px;color:white;text-align:center">
                <h4>📈 Общий прогресс</h4>
                <div style="font-size:36px;font-weight:bold">${avgLevel.toFixed(0)}%</div>
                <div style="background:rgba(255,255,255,0.3);height:10px;border-radius:5px;margin-top:10px">
                    <div style="background:white;width:${avgLevel}%;height:10px;border-radius:5px"></div>
                </div>
                <p>Изучено тем: ${topicsWithProgress.length}</p>
            </div>
        `;
        // Добавляем кнопку для просмотра плана подготовки
        if (currentSessionId) {
            html += `<div style="margin-top:20px;text-align:center">
                        <button onclick="showStudentPlan()" class="btn-primary">📅 Мой план подготовки</button>
                    </div>`;
        }
        showModal(html);
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function joinSchool() {
    if (!currentUserId) { alert("Сначала создайте пользователя"); return; }
    const inviteCode = prompt("Введите код приглашения:");
    if (!inviteCode) return;
    try {
        const response = await fetch(`${API_URL}/api/schools/join?user_id=${currentUserId}&invite_code=${inviteCode}`, { method: 'POST' });
        if (!response.ok) throw new Error(await response.text());
        const result = await response.json();
        alert(`✅ Вы присоединились к школе "${result.school_name}"!`);
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function showMySchools() {
    if (!currentUserId) { alert("Сначала создайте пользователя"); return; }
    try {
        const response = await fetch(`${API_URL}/api/schools/my?user_id=${currentUserId}`);
        if (!response.ok) throw new Error(await response.text());
        const schools = await response.json();
        let html = '<h3>🏫 Мои школы</h3>';
        if (schools.length === 0) html += '<p>Вы не состоите ни в одной школе</p>';
        else {
            for (let school of schools) {
                html += `
                    <div style="border:1px solid #ddd;border-radius:10px;padding:15px;margin:10px 0">
                        <h4>${escapeHtml(school.name)} ${school.is_owner ? '👑' : ''}</h4>
                        <p>${escapeHtml(school.description || '')}</p>
                        <p><strong>👥 Учеников:</strong> ${school.students_count}</p>
                        <p><strong>🔑 Код:</strong> <code>${school.invite_code}</code></p>
                        <button onclick="viewSchoolDetails(${school.id})" class="btn-secondary">📋 Подробнее</button>
                        ${!school.is_owner ? `<button onclick="leaveSchool(${school.id})" style="background:#dc3545;margin-left:10px">🚪 Покинуть</button>` : ''}
                    </div>
                `;
            }
        }
        showModal(html);
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function viewSchoolDetails(schoolId) {
    try {
        const response = await fetch(`${API_URL}/api/schools/${schoolId}?user_id=${currentUserId}`);
        if (!response.ok) throw new Error(await response.text());
        const school = await response.json();
        let html = `<h3>🏫 ${escapeHtml(school.name)}</h3>
            <p><strong>Описание:</strong> ${escapeHtml(school.description || 'Нет')}</p>
            <p><strong>Владелец:</strong> ${school.is_owner ? 'Вы' : 'Учитель'}</p>
            <p><strong>Код:</strong> <code>${school.invite_code}</code></p>
            <h4>👥 Участники (${school.total_members})</h4>
            <table style="width:100%"><tr><th>Имя</th><th>Роль</th></tr>`;
        for (let member of school.members) {
            html += `<tr><td>${escapeHtml(member.name)}</td><td>${member.role === 'teacher' ? '👨‍🏫 Учитель' : '🎓 Ученик'}</td></tr>`;
        }
        html += `</table><button onclick="closeModal()" class="btn-secondary">Закрыть</button>`;
        showModal(html);
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function leaveSchool(schoolId) {
    if (!confirm('Покинуть школу?')) return;
    try {
        const response = await fetch(`${API_URL}/api/schools/${schoolId}?user_id=${currentUserId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await response.text());
        alert('Вы покинули школу');
        showMySchools();
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function deleteSchool(schoolId) {
    if (!confirm('Удалить школу? Это необратимо.')) return;
    try {
        const response = await fetch(`${API_URL}/api/schools/${schoolId}/delete?user_id=${currentUserId}`, { method: 'DELETE' });
        if (!response.ok) throw new Error(await response.text());
        alert('Школа удалена');
        showMySchools();
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
}

async function processVideo() {
    const url = document.getElementById('videoUrl').value;
    const language = document.getElementById('targetLang').value;
    if (!url) { alert('Введите URL видео'); return; }
    const resultDiv = document.getElementById('videoResult');
    resultDiv.innerHTML = '<p>Обработка видео...</p>';
    try {
        const response = await fetch(`${API_URL}/api/video/transcribe`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, language })
        });
        const data = await response.json();
        resultDiv.innerHTML = `<div class="lesson-card"><h3>Оригинал</h3><p>${data.original_text}</p><h3>Перевод</h3><p>${data.translated_text}</p></div>`;
    } catch (error) {
        resultDiv.innerHTML = `<p style="color:red">Ошибка: ${error.message}</p>`;
    }
}

function backToMainMenu() {
    if (currentSessionId) {
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step5').style.display = 'block';
    } else {
        document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
        document.getElementById('step1').style.display = 'block';
    }
}

function backToLessonsList() { showLessonsList(); }
function closeModal() {
    document.querySelectorAll('.custom-modal').forEach(m => m.remove());
    document.querySelectorAll('.modal-overlay').forEach(o => o.remove());
}

document.addEventListener('DOMContentLoaded', function() {
    const startLearningBtn = document.getElementById('startLearningBtn');
    if (startLearningBtn) {
        startLearningBtn.addEventListener('click', function(e) { startLearningMode(); });
    }
    const showTestCreatorBtn = document.getElementById('showTestCreatorBtn');
    if (showTestCreatorBtn) {
        showTestCreatorBtn.addEventListener('click', function(e) {
            if (currentUserId) showTestCreator();
            else alert('Сначала зарегистрируйтесь');
        });
    }
    const roleSelect = document.getElementById('userRole');
    if (roleSelect) {
        setRole(roleSelect.value);
        roleSelect.addEventListener('change', function(e) { setRole(e.target.value); });
    }
});

// ========== АВТОРИЗАЦИЯ ==========
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// Сохраняем токен в localStorage при успешном входе
function setAuthToken(token, userData) {
    authToken = token;
    currentUser = userData;
    localStorage.setItem('authToken', token);
    localStorage.setItem('currentUser', JSON.stringify(userData));
}

// Выход
function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    document.getElementById('profileHeader').style.display = 'none';
    document.getElementById('step1').style.display = 'block';
    document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
    document.getElementById('step1').style.display = 'block';
    alert('Вы вышли из системы');
}

// Показать модальное окно профиля
async function showProfileModal() {
    if (!authToken) {
        alert('Сначала войдите в систему');
        return;
    }
    try {
        const response = await fetch(`${API_URL}/api/auth/profile`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error(await response.text());
        const profile = await response.json();
        
        document.getElementById('modalAvatar').src = profile.avatar_url || 'https://api.dicebear.com/7.x/avataaars/svg?seed=default';
        document.getElementById('profileName').textContent = profile.name;
        document.getElementById('profileEmail').textContent = profile.email;
        document.getElementById('profileRole').textContent = profile.role === 'teacher' ? 'Учитель' : 'Ученик';
        document.getElementById('profileUsername').textContent = profile.username;
        
        document.getElementById('profileModal').style.display = 'block';
        
        // ВАЖНО: добавляем клик на аватар
        const modalAvatar = document.getElementById('modalAvatar');
        const avatarUpload = document.getElementById('avatarUpload');
        modalAvatar.onclick = () => avatarUpload.click();
        
    } catch (error) {
        alert('Ошибка загрузки профиля: ' + error.message);
    }
}

function closeProfileModal() {
    document.getElementById('profileModal').style.display = 'none';
}

// Загрузка аватара
document.getElementById('avatarUpload')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onloadend = async function() {
        const avatarUrl = reader.result;
        const response = await fetch(`${API_URL}/api/auth/avatar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ avatar_url: avatarUrl })
        });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('avatarImg').src = data.avatar_url;
            document.getElementById('modalAvatar').src = data.avatar_url;
            alert('Аватар обновлён');
        } else {
            alert('Ошибка обновления аватара');
        }
    };
    reader.readAsDataURL(file);
});

// Форма регистрации/логина
function showAuthModal() {
    const modalHtml = `
        <div id="authModal" style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 20px; max-width: 400px; width: 90%; z-index: 1002;">
            <h3>Вход / Регистрация</h3>
            <div style="margin-bottom: 15px;">
                <input type="text" id="authUsername" placeholder="Username" style="width: 100%; padding: 10px; margin-bottom: 10px;">
                <input type="password" id="authPassword" placeholder="Пароль" style="width: 100%; padding: 10px; margin-bottom: 10px;">
                <input type="text" id="authName" placeholder="Имя (при регистрации)" style="width: 100%; padding: 10px; margin-bottom: 10px;">
                <input type="email" id="authEmail" placeholder="Email (при регистрации)" style="width: 100%; padding: 10px; margin-bottom: 10px;">
                <select id="authRole" style="width: 100%; padding: 10px; margin-bottom: 10px;">
                    <option value="student">Ученик</option>
                    <option value="teacher">Учитель</option>
                </select>
            </div>
            <button onclick="authLogin()" class="btn-primary" style="margin-right: 10px;">Войти</button>
            <button onclick="authRegister()" class="btn-secondary">Зарегистрироваться</button>
            <button onclick="closeAuthModal()" class="btn-outline" style="margin-top: 10px;">Закрыть</button>
        </div>
    `;
    const overlay = document.createElement('div');
    overlay.id = 'authOverlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.background = 'rgba(0,0,0,0.5)';
    overlay.style.zIndex = '1001';
    overlay.onclick = closeAuthModal;
    document.body.appendChild(overlay);
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

async function authLogin() {
    const username = document.getElementById('authUsername').value;
    const password = document.getElementById('authPassword').value;
    if (!username || !password) {
        alert('Введите username и пароль');
        return;
    }
    try {
        const response = await fetch(`${API_URL}/api/auth/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        setAuthToken(data.access_token, data);
        document.getElementById('avatarImg').src = data.avatar_url;
        document.getElementById('userNameDisplay').textContent = data.name;
        document.getElementById('userRoleDisplay').textContent = data.role === 'teacher' ? 'Учитель' : 'Ученик';
        document.getElementById('profileHeader').style.display = 'flex';
        closeAuthModal();
        
        currentUserId = data.user_id;
        currentUserRole = data.role;
        
        if (data.role === 'teacher') {
            document.getElementById('teacherPanel').style.display = 'block';
            document.getElementById('studentPanel').style.display = 'none';
            document.getElementById('step1').style.display = 'none';
        } else {
            // Ученик
            document.getElementById('teacherPanel').style.display = 'none';
            document.getElementById('studentPanel').style.display = 'block';
            document.getElementById('step1').style.display = 'none';
            
            // Предлагаем начать обучение (выбрать экзамен)
            const examName = prompt('Введите название экзамена (например: ЕНТ математика, SAT, IELTS):');
            if (examName) {
                await startNewSession(examName);
            } else {
                // Если не ввел – показываем главное меню для выбора экзамена (шаг 1)
                document.getElementById('step1').style.display = 'block';
                document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
                document.getElementById('step1').style.display = 'block';
            }
        }
    } catch (error) {
        alert('Ошибка входа: ' + error.message);
    }
}

async function authRegister() {
    const username = document.getElementById('authUsername').value;
    const password = document.getElementById('authPassword').value;
    const name = document.getElementById('authName').value;
    const email = document.getElementById('authEmail').value;
    const role = document.getElementById('authRole').value;
    if (!username || !password || !name || !email) {
        alert('Заполните все поля');
        return;
    }
    try {
        const response = await fetch(`${API_URL}/api/auth/register?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}&name=${encodeURIComponent(name)}&email=${encodeURIComponent(email)}&role=${role}`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        setAuthToken(data.access_token, data);
        document.getElementById('avatarImg').src = data.avatar_url;
        document.getElementById('userNameDisplay').textContent = data.name;
        document.getElementById('userRoleDisplay').textContent = data.role === 'teacher' ? 'Учитель' : 'Ученик';
        document.getElementById('profileHeader').style.display = 'flex';
        closeAuthModal();
        
        currentUserId = data.user_id;
        currentUserRole = data.role;
        
        if (data.role === 'teacher') {
            document.getElementById('teacherPanel').style.display = 'block';
            document.getElementById('studentPanel').style.display = 'none';
            document.getElementById('step1').style.display = 'none';
        } else {
            // Ученик
            document.getElementById('teacherPanel').style.display = 'none';
            document.getElementById('studentPanel').style.display = 'block';
            document.getElementById('step1').style.display = 'none';
            
            const examName = prompt('Введите название экзамена (например: ЕНТ математика, SAT, IELTS):');
            if (examName) {
                await startNewSession(examName);
            } else {
                document.getElementById('step1').style.display = 'block';
                document.querySelectorAll('.step').forEach(step => step.style.display = 'none');
                document.getElementById('step1').style.display = 'block';
            }
        }
    } catch (error) {
        alert('Ошибка регистрации: ' + error.message);
    }
}

function closeAuthModal() {
    const modal = document.getElementById('authModal');
    const overlay = document.getElementById('authOverlay');
    if (modal) modal.remove();
    if (overlay) overlay.remove();
}

// Обновляем startLearning - теперь не нужен, используем авторизацию
// Но оставим для совместимости

// ========== ЧАТ ==========
let currentChatSchoolId = null;
let currentChatTab = 'general';
let chatPollingInterval = null;

async function openChatModal() {
    if (!currentUserId) {
        alert('Сначала войдите в систему');
        return;
    }
    // Получаем школы пользователя
    const schoolsResp = await fetch(`${API_URL}/api/schools/my?user_id=${currentUserId}`);
    if (!schoolsResp.ok) return alert('Ошибка загрузки школ');
    const schools = await schoolsResp.json();
    if (schools.length === 0) {
        alert('Вы не состоите ни в одной школе');
        return;
    }
    let schoolId;
    if (schools.length === 1) {
        schoolId = schools[0].id;
    } else {
        const choice = prompt('Выберите школу:\n' + schools.map(s => `${s.id} - ${s.name}`).join('\n') + '\nВведите ID школы:');
        if (!choice) return;
        schoolId = parseInt(choice);
        if (!schools.find(s => s.id === schoolId)) {
            alert('Неверный ID школы');
            return;
        }
    }
    currentChatSchoolId = schoolId;
    
    // Загружаем список участников школы для личных сообщений
    const membersResp = await fetch(`${API_URL}/api/schools/${schoolId}?user_id=${currentUserId}`);
    if (membersResp.ok) {
        const schoolData = await membersResp.json();
        const select = document.getElementById('privateRecipientId');
        select.innerHTML = '<option value="">Выберите получателя</option>';
        for (let m of schoolData.members) {
            if (m.id !== currentUserId) {
                select.innerHTML += `<option value="${m.id}">${m.name} (${m.role === 'teacher' ? 'Учитель' : 'Ученик'})</option>`;
            }
        }
    }
    
    document.getElementById('chatModal').style.display = 'flex';
    switchChatTab('general');
    startChatPolling();
}

function closeChatModal() {
    document.getElementById('chatModal').style.display = 'none';
    if (chatPollingInterval) clearInterval(chatPollingInterval);
    chatPollingInterval = null;
}

function startChatPolling() {
    if (chatPollingInterval) clearInterval(chatPollingInterval);
    loadChatMessages();
    chatPollingInterval = setInterval(() => loadChatMessages(), 3000);
}

async function loadChatMessages() {
    if (!currentChatSchoolId) return;
    const container = document.getElementById('chatMessagesContainer');
    try {
        let url;
        if (currentChatTab === 'general') {
            url = `${API_URL}/api/chat/school/${currentChatSchoolId}/messages`;
        } else {
            const recipientId = document.getElementById('privateRecipientId').value;
            if (!recipientId) {
                container.innerHTML = '<p>Выберите получателя для личных сообщений.</p>';
                return;
            }
            url = `${API_URL}/api/chat/private/${recipientId}`;
        }
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!response.ok) throw new Error(await response.text());
        const messages = await response.json();
        
        container.innerHTML = '';
        for (let msg of messages) {
            const isMe = (msg.user_id === currentUserId);
            const avatarUrl = msg.avatar_url || 'https://api.dicebear.com/7.x/avataaars/svg?seed=default';
            container.innerHTML += `
                <div style="margin-bottom: 15px; display: flex; align-items: flex-start; ${isMe ? 'flex-direction: row-reverse;' : ''}">
                    <img src="${avatarUrl}" style="width: 35px; height: 35px; border-radius: 50%; margin: ${isMe ? '0 0 0 10px' : '0 10px 0 0'}">
                    <div style="background: ${isMe ? '#667eea' : '#f1f1f1'}; color: ${isMe ? 'white' : 'black'}; padding: 8px 12px; border-radius: 15px; max-width: 70%;">
                        <div style="font-size: 12px; font-weight: bold;">${escapeHtml(msg.user_name)}</div>
                        <div>${escapeHtml(msg.message)}</div>
                        <div style="font-size: 10px; opacity: 0.7;">${new Date(msg.created_at).toLocaleTimeString()}</div>
                    </div>
                </div>
            `;
        }
        container.scrollTop = container.scrollHeight;
    } catch (err) {
        console.error(err);
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    try {
        let url, body;
        if (currentChatTab === 'general') {
            url = `${API_URL}/api/chat/school/${currentChatSchoolId}/send`;
            body = JSON.stringify({ message });
        } else {
            const recipientId = document.getElementById('privateRecipientId').value;
            if (!recipientId) {
                alert('Выберите получателя');
                return;
            }
            url = `${API_URL}/api/chat/private/send`;
            body = JSON.stringify({ recipient_id: parseInt(recipientId), message });
        }
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: body
        });
        if (!response.ok) throw new Error(await response.text());
        loadChatMessages();
    } catch (err) {
        alert('Ошибка отправки: ' + err.message);
    }
}

function switchChatTab(tab) {
    currentChatTab = tab;
    const generalBtn = document.getElementById('chatTabGeneral');
    const privateBtn = document.getElementById('chatTabPrivate');
    const recipientSelect = document.getElementById('chatRecipientSelect');
    if (tab === 'general') {
        generalBtn.style.background = '#667eea';
        generalBtn.style.color = 'white';
        privateBtn.style.background = '#ccc';
        privateBtn.style.color = 'black';
        recipientSelect.style.display = 'none';
    } else {
        privateBtn.style.background = '#667eea';
        privateBtn.style.color = 'white';
        generalBtn.style.background = '#ccc';
        generalBtn.style.color = 'black';
        recipientSelect.style.display = 'block';
    }
    loadChatMessages();
}

// ========== OCR ДЛЯ ЗАДАЧ ==========
async function uploadPhotoForTask(taskIndex) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            // Показываем индикатор загрузки
            const taskContainer = document.querySelector(`.task[data-task-idx="${taskIndex}"]`);
            const originalBtn = taskContainer.querySelector('button');
            originalBtn.textContent = '⏳ Распознаю...';
            originalBtn.disabled = true;
            
            const response = await fetch(`${API_URL}/api/ocr/recognize`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                },
                body: formData
            });
            if (!response.ok) throw new Error(await response.text());
            const data = await response.json();
            
            // Вставляем распознанный текст в поле ответа
            const answerInput = document.getElementById(`task_${taskIndex}`);
            if (answerInput) {
                answerInput.value = data.text;
                // Останавливаем таймер задачи (если был активен) и запускаем заново? Не обязательно
            }
            alert(`Распознано: "${data.text}"\nУверенность: ${data.confidence * 100}%`);
        } catch (err) {
            alert('Ошибка распознавания: ' + err.message);
        } finally {
            const taskContainer = document.querySelector(`.task[data-task-idx="${taskIndex}"]`);
            const originalBtn = taskContainer.querySelector('button');
            originalBtn.textContent = '📷 Загрузить фото';
            originalBtn.disabled = false;
        }
    };
    input.click();
}

async function startNewSession(examName) {
    if (!currentUserId) {
        alert('Сначала войдите в систему');
        return;
    }
    try {
        const sessionRes = await fetch(`${API_URL}/api/sessions?user_id=${currentUserId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exam_name: examName })
        });
        if (!sessionRes.ok) throw new Error(`HTTP ${sessionRes.status}: ${await sessionRes.text()}`);
        const session = await sessionRes.json();
        currentSessionId = session.id;
        
        const testRes = await fetch(`${API_URL}/api/sessions/${currentSessionId}`);
        if (!testRes.ok) throw new Error(`HTTP ${testRes.status}: ${await testRes.text()}`);
        const sessionData = await testRes.json();
        if (!sessionData.test_results || sessionData.test_results.length === 0) throw new Error("Тест не найден");
        const testResult = sessionData.test_results[0];
        currentQuestions = testResult.questions;
        
        displayTest(currentQuestions);
        document.getElementById('step1').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
    } catch (error) {
        console.error(error);
        alert('Ошибка создания сессии: ' + error.message);
    }
}

// PDF RAG
let currentPdfDocId = null;

document.getElementById('uploadPdfBtn')?.addEventListener('click', async () => {
    const fileInput = document.getElementById('pdfFile');
    const file = fileInput.files[0];
    if (!file) {
        alert('Выберите PDF файл');
        return;
    }
    const formData = new FormData();
    formData.append('file', file);
    const statusDiv = document.getElementById('pdfChatStatus');
    statusDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка и индексация...';
    try {
        const response = await fetch('/api/upload-pdf', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('authToken')}` },
            body: formData
        });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        currentPdfDocId = data.document_id;
        statusDiv.innerHTML = `<span class="text-green-400">✅ PDF "${data.filename}" загружен, проиндексировано ${data.chunks} фрагментов.</span>`;
        document.getElementById('pdfQuestionBlock').style.display = 'block';
    } catch (err) {
        statusDiv.innerHTML = `<span class="text-red-400">❌ Ошибка: ${err.message}</span>`;
    }
});

document.getElementById('askPdfBtn')?.addEventListener('click', async () => {
    const question = document.getElementById('pdfQuestion').value.trim();
    if (!question) {
        alert('Введите вопрос');
        return;
    }
    if (!currentPdfDocId) {
        alert('Сначала загрузите PDF');
        return;
    }
    const answerDiv = document.getElementById('pdfAnswer');
    answerDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Поиск ответа...';
    try {
        const response = await fetch('/api/ask-pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('authToken')}` },
            body: JSON.stringify({ document_id: currentPdfDocId, question: question })
        });
        if (!response.ok) throw new Error(await response.text());
        const data = await response.json();
        answerDiv.innerHTML = `<div class="prose prose-invert max-w-none">${marked.parse(data.answer)}</div>`;
    } catch (err) {
        answerDiv.innerHTML = `<span class="text-red-400">Ошибка: ${err.message}</span>`;
    }
});