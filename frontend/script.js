// frontend/script.js
const API_URL = "http://localhost:8080";

let currentSessionId = null;
let currentUserId = null;
let currentQuestions = [];

// Функция для рендеринга формул (отложенный вызов)
function renderMath() {
    if (window.MathJax) {
        setTimeout(() => {
            MathJax.typesetPromise().catch(err => console.log('MathJax error:', err));
        }, 100);
    }
}

async function startLearning() {
    const name = document.getElementById('userName').value;
    const email = document.getElementById('userEmail').value;
    const exam = document.getElementById('examName').value;
    
    if (!name || !email || !exam) {
        alert('Пожалуйста, заполните все поля');
        return;
    }
    
    try {
        console.log("1. Создаём пользователя...");
        const userRes = await fetch(`${API_URL}/api/users`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, email})
        });
        if (!userRes.ok) throw new Error(`HTTP ${userRes.status}: ${await userRes.text()}`);
        const user = await userRes.json();
        currentUserId = user.id;
        console.log("Пользователь создан:", user);
        
        console.log("2. Создаём сессию...");
        const sessionRes = await fetch(`${API_URL}/api/sessions?user_id=${currentUserId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({exam_name: exam})
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
        // НЕ ДЕЛАЕМ НИКАКИХ ЗАМЕН
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
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ answers: answers })
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
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({session_id: currentSessionId, days})
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
    alert("startLearningMode вызвана!");
    console.log("===== startLearningMode вызвана =====");
    console.log("currentSessionId:", currentSessionId);
    document.getElementById('step4').style.display = 'none';
    document.getElementById('step5').style.display = 'block';
    await loadNextLesson();
}

async function loadNextLesson() {
    alert("loadNextLesson вызвана");
    alert("currentSessionId = " + currentSessionId);
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
    
    let theoryText = content.theory || 'Нет теории';
    // Если сервер присылает \\\(, заменяем на \(
    theoryText = theoryText.replace(/\\\\\(/g, '\\(').replace(/\\\\\)/g, '\\)');
    
    let examplesHtml = '';
    if (content.examples && content.examples.length) {
        examplesHtml = '<h3>📝 Примеры:</h3>' + content.examples.map(ex => `
            <div class="example">
                <strong>Задача:</strong> ${ex.problem}<br>
                <strong>Решение:</strong> ${ex.solution}
            </div>
        `).join('');
    }
    
    let tasksHtml = '';
    if (content.tasks && content.tasks.length) {
        tasksHtml = '<h3>✍️ Задачи для самостоятельного решения:</h3>' + 
            content.tasks.map((task, idx) => `
                <div class="task">
                    <p><strong>Задача ${idx+1}:</strong> ${task.task}</p>
                    <input type="text" id="task_${idx}" placeholder="Ваш ответ" class="answer-input">
                </div>
            `).join('') + 
            `<button onclick="submitLesson(${lessonData.lesson_id})" class="btn-primary">Отправить ответы</button>`;
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
    `;

    // Добавляем блок чата с ботом
    const chatHtml = `
        <div class="bot-chat">
            <h3>🤖 Помощник ИИ</h3>
            <div id="chatMessages" style="height: 200px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px;"></div>
            <input type="text" id="chatQuestion" placeholder="Задайте вопрос по теме урока..." style="width: 80%;">
            <button onclick="askBot(${lessonData.lesson_id})">Спросить</button>
        </div>
    `;
    container.innerHTML += chatHtml;
    renderMath();
}

async function submitLesson(lessonId) {
    const tasks = document.querySelectorAll('[id^="task_"]');
    const answers = {};
    tasks.forEach((task, idx) => { answers[idx] = task.value; });
    try {
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/submit_lesson`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: currentSessionId,
                lesson_id: lessonId,
                user_answers: answers
            })
        });
        const result = await response.json();
        if (result.status === 'failed') {
            // Показываем подсказки
            let feedbackHtml = '<div class="feedback-errors"><h3>Ошибки в задачах:</h3><ul>';
            for (let r of result.results) {
                if (!r.correct) {
                    feedbackHtml += `<li>Задача ${r.task_index+1}: ${r.hint}</li>`;
                }
            }
            feedbackHtml += '</ul><p>Исправьте ответы и отправьте снова.</p></div>';
            document.getElementById('lessonContent').insertAdjacentHTML('beforeend', feedbackHtml);
        } else if (result.status === 'success') {
            alert(`Урок завершен! Результат: ${result.score}%`);
            await loadNextLesson();
        }
    } catch (error) {
        console.error(error);
        alert('Ошибка при отправке ответов');
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
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: currentSessionId,
                question: question
            })
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
        const response = await fetch(`${API_URL}/api/sessions/${currentSessionId}/progress_test`, {method: 'POST'});
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
            const lastProgress = history[history.length-1];
            const profile = lastProgress.profile_snapshot || {};
            const values = Object.values(profile);
            const avgProgress = values.length ? values.reduce((a,b)=>a+b,0)/values.length : 0;
            const fill = document.getElementById('progressFill');
            if (fill) {
                fill.style.width = `${avgProgress}%`;
                fill.textContent = `${Math.round(avgProgress)}%`;
            }
            document.getElementById('progressStats').innerHTML = `<p>Общий прогресс: ${Math.round(avgProgress)}%</p><p>Изучено тем: ${Object.keys(profile).length}</p>`;
        }
    } catch(e) { console.error(e); }
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

// Привязка кнопки "Начать обучение"
document.addEventListener('DOMContentLoaded', function() {
    const startLearningBtn = document.getElementById('startLearningBtn');
    if (startLearningBtn) {
        startLearningBtn.addEventListener('click', function(e) {
            console.log("Клик по кнопке 'Начать обучение'");
            startLearningMode();
        });
        console.log("Обработчик для кнопки 'Начать обучение' добавлен");
    } else {
        console.error("Кнопка 'Начать обучение' не найдена");
    }
});