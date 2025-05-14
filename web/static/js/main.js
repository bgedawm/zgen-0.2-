// Local Scout AI Agent - Main JavaScript

// DOM Elements - Tabs
const tabButtons = document.querySelectorAll('.tab-button');
const tabPanes = document.querySelectorAll('.tab-pane');

// DOM Elements - Chat
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-message');
const chatMessages = document.getElementById('chat-messages');
const clearChatButton = document.getElementById('clear-chat');

// DOM Elements - Tasks
const taskList = document.getElementById('task-list');
const newTaskButton = document.getElementById('new-task');
const taskSearchInput = document.getElementById('task-search');
const taskStatusFilter = document.getElementById('task-status-filter');
const taskSort = document.getElementById('task-sort');

// DOM Elements - Schedules
const scheduleList = document.getElementById('schedule-list');

// DOM Elements - Connection Status
const connectionStatus = document.getElementById('connection-status');

// DOM Elements - Theme
const themeToggle = document.getElementById('theme-toggle');

// Modal Elements - New Task
const newTaskModal = document.getElementById('new-task-modal');
const taskNameInput = document.getElementById('task-name');
const taskDescriptionInput = document.getElementById('task-description');
const taskScheduleType = document.getElementById('task-schedule-type');
const scheduleOptions = document.getElementById('schedule-options');
const cancelTaskButton = document.getElementById('cancel-task');
const createTaskButton = document.getElementById('create-task');

// Modal Elements - Task Details
const taskDetailsModal = document.getElementById('task-details-modal');
const taskDetailsTitle = document.getElementById('task-details-title');
const taskDetailsDescription = document.getElementById('task-details-description');
const taskDetailsStatusBadge = document.getElementById('task-details-status-badge');
const taskDetailsProgress = document.getElementById('task-details-progress');
const taskDetailsProgressText = document.getElementById('task-details-progress-text');
const taskDetailsResultContainer = document.getElementById('task-details-result-container');
const taskDetailsResult = document.getElementById('task-details-result');
const taskDetailsErrorContainer = document.getElementById('task-details-error-container');
const taskDetailsError = document.getElementById('task-details-error');
const taskDetailsArtifactsContainer = document.getElementById('task-details-artifacts-container');
const taskDetailsArtifacts = document.getElementById('task-details-artifacts');
const taskDetailsScheduleContainer = document.getElementById('task-details-schedule-container');
const taskDetailsSchedule = document.getElementById('task-details-schedule');
const taskDetailsNextRun = document.getElementById('task-details-next-run');
const taskDetailsHistoryContainer = document.getElementById('task-details-history-container');
const taskDetailsHistory = document.getElementById('task-details-history');
const closeTaskDetailsButton = document.getElementById('close-task-details');
const deleteTaskButton = document.getElementById('delete-task');
const scheduleTaskButton = document.getElementById('schedule-task');
const runTaskNowButton = document.getElementById('run-task-now');
const taskDetailsScheduleActions = document.getElementById('task-details-schedule-actions');
const cancelScheduleButton = document.getElementById('cancel-schedule');

// Modal Elements - Schedule Task
const scheduleTaskModal = document.getElementById('schedule-task-modal');
const scheduleType = document.getElementById('schedule-type');
const scheduleTaskOptions = document.getElementById('schedule-task-options');
const cancelScheduleModal = document.getElementById('cancel-schedule-modal');
const saveScheduleButton = document.getElementById('save-schedule');

// State
let currentSessionId = generateSessionId();
let tasks = {};
let schedules = {};
let currentTaskId = null;
let websocket = null;
let reconnectAttempts = 0;
let reconnectInterval = null;

// Theme Management
function initTheme() {
    if (localStorage.getItem('color-theme') === 'dark' || 
        (!localStorage.getItem('color-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }
}

function toggleTheme() {
    if (document.documentElement.classList.contains('dark')) {
        document.documentElement.classList.remove('dark');
        localStorage.setItem('color-theme', 'light');
    } else {
        document.documentElement.classList.add('dark');
        localStorage.setItem('color-theme', 'dark');
    }
}

// Tab Management
function setActiveTab(tabId) {
    // Update tab buttons
    tabButtons.forEach(button => {
        if (button.id === `${tabId}-tab`) {
            button.classList.add('text-primary-600', 'border-primary-600', 'dark:text-primary-500', 'dark:border-primary-500', 'active');
            button.classList.remove('border-transparent', 'hover:text-gray-600', 'hover:border-gray-300', 'dark:hover:text-gray-300');
        } else {
            button.classList.remove('text-primary-600', 'border-primary-600', 'dark:text-primary-500', 'dark:border-primary-500', 'active');
            button.classList.add('border-transparent', 'hover:text-gray-600', 'hover:border-gray-300', 'dark:hover:text-gray-300');
        }
    });

    // Update tab panes
    tabPanes.forEach(pane => {
        if (pane.id === `${tabId}-content`) {
            pane.classList.remove('hidden');
            pane.classList.add('active');
        } else {
            pane.classList.add('hidden');
            pane.classList.remove('active');
        }
    });
}

// Chat Functions
function addMessageToChat(message, isUser = false, attachments = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'flex items-start message-enter';
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'flex-shrink-0 mr-3';
    
    const avatarInnerDiv = document.createElement('div');
    avatarInnerDiv.className = `h-10 w-10 rounded-full flex items-center justify-center text-white font-bold ${isUser ? 'bg-gray-600' : 'bg-primary-600'}`;
    avatarInnerDiv.textContent = isUser ? 'Y' : 'S';
    
    avatarDiv.appendChild(avatarInnerDiv);
    messageDiv.appendChild(avatarDiv);
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'flex flex-col';
    
    const nameSpan = document.createElement('span');
    nameSpan.className = 'text-xs text-gray-500 dark:text-gray-400';
    nameSpan.textContent = isUser ? 'You' : 'Scout';
    contentDiv.appendChild(nameSpan);
    
    const messageContentDiv = document.createElement('div');
    messageContentDiv.className = `${isUser ? 'bg-gray-200 dark:bg-gray-700' : 'bg-primary-100 dark:bg-primary-900'} rounded-lg p-3 text-gray-800 dark:text-gray-200`;
    messageContentDiv.innerHTML = formatMessageText(message);
    contentDiv.appendChild(messageContentDiv);
    
    // Add attachments if any
    if (attachments && attachments.length > 0) {
        const attachmentsDiv = document.createElement('div');
        attachmentsDiv.className = 'mt-2 space-y-2';
        
        attachments.forEach(attachment => {
            const attachmentLink = document.createElement('a');
            attachmentLink.href = attachment;
            attachmentLink.className = 'inline-flex items-center px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600';
            attachmentLink.target = '_blank';
            
            const icon = document.createElement('i');
            icon.className = 'fas fa-paperclip mr-2';
            attachmentLink.appendChild(icon);
            
            const fileName = attachment.split('/').pop();
            attachmentLink.appendChild(document.createTextNode(fileName));
            
            attachmentsDiv.appendChild(attachmentLink);
        });
        
        contentDiv.appendChild(attachmentsDiv);
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Animate the message entrance
    setTimeout(() => {
        messageDiv.classList.remove('message-enter');
        messageDiv.classList.add('message-enter-active');
    }, 10);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessageText(text) {
    // Simple formatting for code blocks
    let formatted = text.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 dark:bg-gray-600 p-2 rounded">$1</pre>');
    
    // Convert line breaks to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat(message, true);
    
    // Clear input
    chatInput.value = '';
    
    try {
        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'flex items-start loading-message';
        typingDiv.innerHTML = `
            <div class="flex-shrink-0 mr-3">
                <div class="h-10 w-10 rounded-full bg-primary-600 flex items-center justify-center text-white font-bold">
                    S
                </div>
            </div>
            <div class="flex flex-col">
                <span class="text-xs text-gray-500 dark:text-gray-400">Scout</span>
                <div class="bg-primary-100 dark:bg-primary-900 rounded-lg p-3 text-gray-800 dark:text-gray-200 loading">
                    Thinking
                </div>
            </div>
        `;
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Send to API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                input: message,
                session_id: currentSessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Remove typing indicator
        chatMessages.removeChild(typingDiv);
        
        // Add response to chat
        addMessageToChat(data.message, false, data.attachments);
        
        // If this was a task, refresh task list
        if (data.task_id) {
            await fetchTasks();
        }
    } catch (error) {
        console.error('Error sending message:', error);
        
        // Remove typing indicator if it exists
        const typingDiv = document.querySelector('.loading-message');
        if (typingDiv) {
            chatMessages.removeChild(typingDiv);
        }
        
        // Show error message
        addMessageToChat('Sorry, there was an error processing your request. Please try again.', false);
    }
}

function clearChat() {
    // Clear chat messages except the first one (welcome message)
    while (chatMessages.children.length > 1) {
        chatMessages.removeChild(chatMessages.lastChild);
    }
    
    // Generate a new session ID
    currentSessionId = generateSessionId();
}

// Task Functions
async function fetchTasks() {
    try {
        const response = await fetch('/api/tasks');
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const taskData = await response.json();
        
        // Update tasks state
        tasks = {};
        taskData.forEach(task => {
            tasks[task.id] = task;
        });
        
        // Update UI
        renderTasks();
    } catch (error) {
        console.error('Error fetching tasks:', error);
    }
}

async function fetchSchedules() {
    try {
        const response = await fetch('/api/schedules');
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            schedules = data.schedules;
            renderSchedules();
        }
    } catch (error) {
        console.error('Error fetching schedules:', error);
    }
}

function renderTasks() {
    // Get filter and sort settings
    const searchQuery = taskSearchInput.value.toLowerCase();
    const statusFilter = taskStatusFilter.value;
    const sortOption = taskSort.value;
    
    // Convert tasks object to array
    let taskArray = Object.values(tasks);
    
    // Apply search filter
    if (searchQuery) {
        taskArray = taskArray.filter(task => 
            task.name.toLowerCase().includes(searchQuery) || 
            task.description.toLowerCase().includes(searchQuery)
        );
    }
    
    // Apply status filter
    if (statusFilter !== 'all') {
        taskArray = taskArray.filter(task => task.status === statusFilter);
    }
    
    // Apply sort
    if (sortOption === 'newest') {
        taskArray.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortOption === 'oldest') {
        taskArray.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    } else if (sortOption === 'name') {
        taskArray.sort((a, b) => a.name.localeCompare(b.name));
    }
    
    // Clear task list
    taskList.innerHTML = '';
    
    if (taskArray.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'text-center text-gray-500 dark:text-gray-400 py-10';
        emptyDiv.textContent = 'No tasks found';
        taskList.appendChild(emptyDiv);
        return;
    }
    
    // Create task cards
    taskArray.forEach(task => {
        const taskCard = document.createElement('div');
        taskCard.className = 'task-card bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4 cursor-pointer hover:shadow-md';
        taskCard.dataset.taskId = task.id;
        
        // Status badge
        const statusBadge = getStatusBadgeHTML(task.status);
        
        // Progress bar (only for running tasks)
        let progressBar = '';
        if (task.status === 'running') {
            progressBar = `
                <div class="mt-2 flex items-center">
                    <div class="flex-grow h-2 bg-gray-200 dark:bg-gray-600 rounded">
                        <div class="h-2 bg-primary-600 rounded" style="width: ${task.progress}%"></div>
                    </div>
                    <span class="ml-2 text-xs text-gray-500 dark:text-gray-400">${task.progress}%</span>
                </div>
            `;
        }
        
        // Schedule indicator
        let scheduleIndicator = '';
        if (task.schedule) {
            scheduleIndicator = `
                <div class="mt-2 flex items-center">
                    <span class="text-xs text-primary-600 dark:text-primary-400">
                        <i class="fas fa-calendar-alt mr-1"></i>${escapeHTML(task.schedule)}
                    </span>
                </div>
            `;
        }
        
        taskCard.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex-grow">
                    <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${escapeHTML(task.name)}</h3>
                    <p class="text-sm text-gray-500 dark:text-gray-400 truncate">${escapeHTML(task.description)}</p>
                </div>
                <div>
                    ${statusBadge}
                </div>
            </div>
            ${progressBar}
            ${scheduleIndicator}
            <div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                ${formatDate(task.updated_at)}
            </div>
        `;
        
        taskCard.addEventListener('click', () => {
            showTaskDetails(task.id);
        });
        
        taskList.appendChild(taskCard);
    });
}

function renderSchedules() {
    scheduleList.innerHTML = '';
    
    const scheduledTasks = Object.values(schedules);
    
    if (scheduledTasks.length === 0) {
        scheduleList.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-10 text-center text-gray-500 dark:text-gray-400">
                    No scheduled tasks
                </td>
            </tr>
        `;
        return;
    }
    
    scheduledTasks.forEach(schedule => {
        const task = tasks[schedule.task_id];
        if (!task) return; // Skip if task doesn't exist
        
        const nextRunTime = schedule.next_run_time ? formatDate(schedule.next_run_time) : 'Not scheduled';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900 dark:text-white">${escapeHTML(task.name)}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500 dark:text-gray-400">${schedule.human_readable}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-500 dark:text-gray-400">${nextRunTime}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                ${getStatusBadgeHTML(task.status)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button class="text-primary-600 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-300 view-task" data-task-id="${task.id}">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300 ml-3 cancel-schedule" data-task-id="${task.id}">
                    <i class="fas fa-calendar-times"></i>
                </button>
            </td>
        `;
        
        // Add event listeners
        tr.querySelector('.view-task').addEventListener('click', (e) => {
            e.stopPropagation();
            showTaskDetails(task.id);
        });
        
        tr.querySelector('.cancel-schedule').addEventListener('click', (e) => {
            e.stopPropagation();
            cancelTaskSchedule(task.id);
        });
        
        scheduleList.appendChild(tr);
    });
}

function showNewTaskModal() {
    // Reset form
    taskNameInput.value = '';
    taskDescriptionInput.value = '';
    taskScheduleType.value = 'none';
    scheduleOptions.innerHTML = '';
    scheduleOptions.classList.add('hidden');
    
    // Show modal
    newTaskModal.classList.remove('hidden');
}

function hideNewTaskModal() {
    newTaskModal.classList.add('hidden');
}

function updateScheduleOptions() {
    const scheduleType = taskScheduleType.value;
    
    // Hide the options by default
    scheduleOptions.classList.add('hidden');
    scheduleOptions.innerHTML = '';
    
    if (scheduleType === 'none') {
        return;
    }
    
    // Show the options
    scheduleOptions.classList.remove('hidden');
    
    if (scheduleType === 'once') {
        scheduleOptions.innerHTML = `
            <div>
                <label for="once-datetime" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Date and Time</label>
                <input id="once-datetime" type="datetime-local" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
            </div>
        `;
    } else if (scheduleType === 'interval') {
        scheduleOptions.innerHTML = `
            <div class="flex space-x-2">
                <div class="flex-grow">
                    <label for="interval-value" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Every</label>
                    <input id="interval-value" type="number" min="1" value="1" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                </div>
                <div class="w-1/3">
                    <label for="interval-unit" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Unit</label>
                    <select id="interval-unit" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                        <option value="m">Minutes</option>
                        <option value="h">Hours</option>
                        <option value="d">Days</option>
                    </select>
                </div>
            </div>
        `;
    } else if (scheduleType === 'cron') {
        scheduleOptions.innerHTML = `
            <div>
                <label for="cron-expression" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Cron Expression</label>
                <input id="cron-expression" type="text" placeholder="* * * * *" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Format: minute hour day month day_of_week</p>
            </div>
        `;
    }
}

function updateScheduleTaskOptions() {
    const type = scheduleType.value;
    
    // Clear options
    scheduleTaskOptions.innerHTML = '';
    
    if (type === 'once') {
        scheduleTaskOptions.innerHTML = `
            <div>
                <label for="schedule-once-datetime" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Date and Time</label>
                <input id="schedule-once-datetime" type="datetime-local" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
            </div>
        `;
    } else if (type === 'interval') {
        scheduleTaskOptions.innerHTML = `
            <div class="flex space-x-2">
                <div class="flex-grow">
                    <label for="schedule-interval-value" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Every</label>
                    <input id="schedule-interval-value" type="number" min="1" value="1" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                </div>
                <div class="w-1/3">
                    <label for="schedule-interval-unit" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Unit</label>
                    <select id="schedule-interval-unit" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                        <option value="m">Minutes</option>
                        <option value="h">Hours</option>
                        <option value="d">Days</option>
                    </select>
                </div>
            </div>
        `;
    } else if (type === 'cron') {
        scheduleTaskOptions.innerHTML = `
            <div>
                <label for="schedule-cron-expression" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Cron Expression</label>
                <input id="schedule-cron-expression" type="text" placeholder="* * * * *" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Format: minute hour day month day_of_week</p>
            </div>
        `;
    }
}

async function createTask() {
    const name = taskNameInput.value.trim();
    const description = taskDescriptionInput.value.trim();
    
    if (!name) {
        alert('Please enter a task name');
        return;
    }
    
    if (!description) {
        alert('Please enter a task description');
        return;
    }
    
    // Prepare schedule string
    let schedule = null;
    
    const scheduleType = taskScheduleType.value;
    if (scheduleType === 'once') {
        const dateTimeInput = document.getElementById('once-datetime');
        if (!dateTimeInput.value) {
            alert('Please select a date and time');
            return;
        }
        
        const selectedDate = new Date(dateTimeInput.value);
        schedule = `at:${selectedDate.toISOString()}`;
    } else if (scheduleType === 'interval') {
        const valueInput = document.getElementById('interval-value');
        const unitSelect = document.getElementById('interval-unit');
        
        const value = parseInt(valueInput.value);
        if (isNaN(value) || value < 1) {
            alert('Please enter a valid interval value');
            return;
        }
        
        const unit = unitSelect.value;
        schedule = `every ${value}${unit}`;
    } else if (scheduleType === 'cron') {
        const cronInput = document.getElementById('cron-expression');
        if (!cronInput.value) {
            alert('Please enter a cron expression');
            return;
        }
        
        schedule = `cron:${cronInput.value}`;
    }
    
    try {
        // Create the task
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                description,
                schedule
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        // Hide modal
        hideNewTaskModal();
        
        // Refresh tasks
        await fetchTasks();
        
        // Switch to tasks tab
        setActiveTab('tasks');
    } catch (error) {
        console.error('Error creating task:', error);
        alert('Failed to create task. Please try again.');
    }
}

async function fetchTaskHistory(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/runs`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            return data.runs;
        } else {
            return [];
        }
    } catch (error) {
        console.error('Error fetching task history:', error);
        return [];
    }
}

async function showTaskDetails(taskId) {
    const task = tasks[taskId];
    if (!task) {
        console.error('Task not found:', taskId);
        return;
    }
    
    // Set current task ID
    currentTaskId = taskId;
    
    // Update modal content
    taskDetailsTitle.textContent = task.name;
    taskDetailsDescription.textContent = task.description;
    
    // Status and progress
    taskDetailsStatusBadge.className = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium status-${task.status}`;
    taskDetailsStatusBadge.textContent = capitalizeFirstLetter(task.status);
    taskDetailsProgress.style.width = `${task.progress}%`;
    taskDetailsProgressText.textContent = `${task.progress}%`;
    
    // Schedule
    if (task.schedule) {
        taskDetailsScheduleContainer.classList.remove('hidden');
        taskDetailsSchedule.textContent = task.schedule;
        
        if (task.next_run_time) {
            taskDetailsNextRun.textContent = `Next run: ${formatDate(task.next_run_time)}`;
        } else {
            taskDetailsNextRun.textContent = '';
        }
        
        // Show cancel schedule button
        taskDetailsScheduleActions.classList.remove('hidden');
    } else {
        taskDetailsScheduleContainer.classList.add('hidden');
        taskDetailsScheduleActions.classList.add('hidden');
    }
    
    // Result
    if (task.result) {
        taskDetailsResultContainer.classList.remove('hidden');
        taskDetailsResult.textContent = task.result;
    } else {
        taskDetailsResultContainer.classList.add('hidden');
    }
    
    // Error
    if (task.error) {
        taskDetailsErrorContainer.classList.remove('hidden');
        taskDetailsError.textContent = task.error;
    } else {
        taskDetailsErrorContainer.classList.add('hidden');
    }
    
    // Artifacts
    if (task.artifacts && task.artifacts.length > 0) {
        taskDetailsArtifactsContainer.classList.remove('hidden');
        taskDetailsArtifacts.innerHTML = '';
        
        task.artifacts.forEach((artifact, index) => {
            const li = document.createElement('li');
            li.className = 'py-3 flex items-center hover:bg-gray-50 dark:hover:bg-gray-800';
            
            const fileName = artifact.split('/').pop();
            const extension = fileName.split('.').pop().toLowerCase();
            let iconClass = 'fa-file';
            
            // Determine icon based on file extension
            if (['png', 'jpg', 'jpeg', 'gif', 'svg'].includes(extension)) {
                iconClass = 'fa-file-image';
            } else if (['pdf'].includes(extension)) {
                iconClass = 'fa-file-pdf';
            } else if (['doc', 'docx'].includes(extension)) {
                iconClass = 'fa-file-word';
            } else if (['xls', 'xlsx'].includes(extension)) {
                iconClass = 'fa-file-excel';
            } else if (['txt', 'md'].includes(extension)) {
                iconClass = 'fa-file-alt';
            } else if (['py', 'js', 'html', 'css', 'json'].includes(extension)) {
                iconClass = 'fa-file-code';
            }
            
            li.innerHTML = `
                <div class="artifact-icon bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 mr-3">
                    <i class="fas ${iconClass}"></i>
                </div>
                <div class="flex-grow">
                    <p class="text-sm font-medium text-gray-900 dark:text-white">${escapeHTML(fileName)}</p>
                </div>
                <a href="/api/tasks/${taskId}/artifacts/${index}" target="_blank" class="ml-2 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                    <i class="fas fa-download"></i>
                </a>
            `;
            
            taskDetailsArtifacts.appendChild(li);
        });
    } else {
        taskDetailsArtifactsContainer.classList.add('hidden');
    }
    
    // Fetch and show task history
    const history = await fetchTaskHistory(taskId);
    if (history.length > 0) {
        taskDetailsHistory.innerHTML = '';
        
        history.forEach(run => {
            const li = document.createElement('li');
            li.className = 'border-l-2 border-gray-200 dark:border-gray-700 pl-3 pb-2';
            
            const startTime = run.start_time ? formatDate(run.start_time) : 'Unknown';
            const endTime = run.end_time ? formatDate(run.end_time) : '';
            const duration = run.start_time && run.end_time ? 
                formatDuration(new Date(run.start_time), new Date(run.end_time)) : '';
            
            let statusIcon = '';
            if (run.status === 'completed') {
                statusIcon = '<i class="fas fa-check-circle text-green-500 mr-2"></i>';
            } else if (run.status === 'failed') {
                statusIcon = '<i class="fas fa-times-circle text-red-500 mr-2"></i>';
            } else {
                statusIcon = '<i class="fas fa-clock text-blue-500 mr-2"></i>';
            }
            
            li.innerHTML = `
                <div class="flex items-center mb-1">
                    ${statusIcon}
                    <span class="text-sm font-medium text-gray-900 dark:text-white">${capitalizeFirstLetter(run.status)}</span>
                    <span class="ml-auto text-xs text-gray-500 dark:text-gray-400">${startTime}</span>
                </div>
                ${duration ? `<div class="text-xs text-gray-500 dark:text-gray-400">Duration: ${duration}</div>` : ''}
                ${run.error ? `<div class="text-xs text-red-500 mt-1">${escapeHTML(run.error)}</div>` : ''}
            `;
            
            taskDetailsHistory.appendChild(li);
        });
    } else {
        taskDetailsHistory.innerHTML = `
            <li class="text-center text-gray-500 dark:text-gray-400 py-4">
                No execution history
            </li>
        `;
    }
    
    // Update button states
    deleteTaskButton.disabled = false;
    runTaskNowButton.disabled = task.status === 'running';
    
    // Show modal
    taskDetailsModal.classList.remove('hidden');
}

function hideTaskDetailsModal() {
    taskDetailsModal.classList.add('hidden');
    currentTaskId = null;
}

async function deleteTask() {
    if (!currentTaskId) return;
    
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tasks/${currentTaskId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        // Hide modal
        hideTaskDetailsModal();
        
        // Refresh tasks
        await fetchTasks();
        
        // Refresh schedules
        await fetchSchedules();
    } catch (error) {
        console.error('Error deleting task:', error);
        alert('Failed to delete task. Please try again.');
    }
}

async function runTaskNow() {
    if (!currentTaskId) return;
    
    try {
        // Reset the task and create a new execution
        const task = tasks[currentTaskId];
        
        const response = await fetch('/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: task.name,
                description: task.description
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        // Hide modal
        hideTaskDetailsModal();
        
        // Refresh tasks
        await fetchTasks();
    } catch (error) {
        console.error('Error running task:', error);
        alert('Failed to run task. Please try again.');
    }
}

function showScheduleTaskModal() {
    // Reset form
    scheduleType.value = 'once';
    updateScheduleTaskOptions();
    
    // Show modal
    scheduleTaskModal.classList.remove('hidden');
}

function hideScheduleTaskModal() {
    scheduleTaskModal.classList.add('hidden');
}

async function saveTaskSchedule() {
    if (!currentTaskId) return;
    
    // Get schedule based on type
    const type = scheduleType.value;
    let scheduleValue = '';
    
    if (type === 'once') {
        const dateTimeInput = document.getElementById('schedule-once-datetime');
        if (!dateTimeInput.value) {
            alert('Please select a date and time');
            return;
        }
        
        const selectedDate = new Date(dateTimeInput.value);
        scheduleValue = `at:${selectedDate.toISOString()}`;
    } else if (type === 'interval') {
        const valueInput = document.getElementById('schedule-interval-value');
        const unitSelect = document.getElementById('schedule-interval-unit');
        
        const value = parseInt(valueInput.value);
        if (isNaN(value) || value < 1) {
            alert('Please enter a valid interval value');
            return;
        }
        
        const unit = unitSelect.value;
        scheduleValue = `every ${value}${unit}`;
    } else if (type === 'cron') {
        const cronInput = document.getElementById('schedule-cron-expression');
        if (!cronInput.value) {
            alert('Please enter a cron expression');
            return;
        }
        
        scheduleValue = `cron:${cronInput.value}`;
    }
    
    try {
        const response = await fetch(`/api/tasks/${currentTaskId}/schedule`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                schedule: scheduleValue
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        // Hide modal
        hideScheduleTaskModal();
        
        // Hide task details modal
        hideTaskDetailsModal();
        
        // Refresh tasks and schedules
        await fetchTasks();
        await fetchSchedules();
    } catch (error) {
        console.error('Error scheduling task:', error);
        alert('Failed to schedule task. Please try again.');
    }
}

async function cancelTaskSchedule(taskId) {
    const id = taskId || currentTaskId;
    if (!id) return;
    
    if (!confirm('Are you sure you want to cancel this schedule?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tasks/${id}/schedule`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        // If this was called from task details modal, hide it
        if (currentTaskId === id) {
            hideTaskDetailsModal();
        }
        
        // Refresh tasks and schedules
        await fetchTasks();
        await fetchSchedules();
    } catch (error) {
        console.error('Error cancelling schedule:', error);
        alert('Failed to cancel schedule. Please try again.');
    }
}

// WebSocket Functions
function setupWebSocket() {
    // Close any existing connection
    if (websocket) {
        websocket.close();
    }
    
    // Update connection status
    updateConnectionStatus('connecting');
    
    // Create a new WebSocket connection
    websocket = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/ws`);
    
    websocket.onopen = () => {
        console.log('WebSocket connection established');
        updateConnectionStatus('connected');
        
        // Reset reconnection attempts
        reconnectAttempts = 0;
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    websocket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'initial_state') {
                // Update tasks with initial state
                tasks = {};
                data.tasks.forEach(task => {
                    tasks[task.id] = task;
                });
                renderTasks();
            } else if (data.type === 'schedules') {
                // Update schedules with initial state
                schedules = data.schedules;
                renderSchedules();
            } else if (data.type === 'task_update') {
                // Update a single task
                const task = data.task;
                tasks[task.id] = task;
                renderTasks();
                
                // Update task details modal if open
                if (currentTaskId === task.id) {
                    showTaskDetails(task.id);
                }
            } else if (data.type === 'schedule_update') {
                // Update schedules when a task is scheduled
                fetchSchedules();
            } else if (data.type === 'schedule_removed') {
                // Update schedules when a schedule is removed
                fetchSchedules();
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    };
    
    websocket.onclose = () => {
        console.log('WebSocket connection closed');
        updateConnectionStatus('disconnected');
        
        // Try to reconnect after a delay
        reconnectAttempts++;
        const delay = Math.min(30000, Math.pow(2, reconnectAttempts) * 1000); // Exponential backoff
        
        console.log(`Reconnecting in ${delay/1000} seconds...`);
        
        if (!reconnectInterval) {
            reconnectInterval = setTimeout(() => {
                setupWebSocket();
            }, delay);
        }
    };
    
    websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus('error');
    };
}

function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connection-status');
    
    if (status === 'connected') {
        statusElement.innerHTML = '<span class="h-2 w-2 rounded-full bg-green-500 mr-2"></span>Connected';
        statusElement.className = 'inline-flex items-center text-green-500';
    } else if (status === 'connecting') {
        statusElement.innerHTML = '<span class="h-2 w-2 rounded-full bg-yellow-500 mr-2"></span>Connecting...';
        statusElement.className = 'inline-flex items-center text-yellow-500';
    } else if (status === 'disconnected') {
        statusElement.innerHTML = '<span class="h-2 w-2 rounded-full bg-red-500 mr-2"></span>Disconnected';
        statusElement.className = 'inline-flex items-center text-red-500';
    } else if (status === 'error') {
        statusElement.innerHTML = '<span class="h-2 w-2 rounded-full bg-red-500 mr-2"></span>Connection Error';
        statusElement.className = 'inline-flex items-center text-red-500';
    }
}

// Helper Functions
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9);
}

function escapeHTML(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function formatDuration(startDate, endDate) {
    const diff = Math.abs(endDate - startDate) / 1000; // seconds
    
    if (diff < 60) {
        return `${Math.round(diff)} seconds`;
    } else if (diff < 3600) {
        return `${Math.round(diff / 60)} minutes`;
    } else {
        const hours = Math.floor(diff / 3600);
        const minutes = Math.round((diff % 3600) / 60);
        return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} minute${minutes !== 1 ? 's' : ''}`;
    }
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function getStatusBadgeHTML(status) {
    return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium status-${status}">${capitalizeFirstLetter(status)}</span>`;
}

// Event Listeners
function setupEventListeners() {
    // Tab navigation
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab.replace('-content', '');
            setActiveTab(tabId);
        });
    });
    
    // Chat
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    clearChatButton.addEventListener('click', clearChat);
    
    // Tasks
    newTaskButton.addEventListener('click', showNewTaskModal);
    cancelTaskButton.addEventListener('click', hideNewTaskModal);
    createTaskButton.addEventListener('click', createTask);
    taskScheduleType.addEventListener('change', updateScheduleOptions);
    taskSearchInput.addEventListener('input', renderTasks);
    taskStatusFilter.addEventListener('change', renderTasks);
    taskSort.addEventListener('change', renderTasks);
    
    // Task Details
    closeTaskDetailsButton.addEventListener('click', hideTaskDetailsModal);
    deleteTaskButton.addEventListener('click', deleteTask);
    runTaskNowButton.addEventListener('click', runTaskNow);
    scheduleTaskButton.addEventListener('click', showScheduleTaskModal);
    cancelScheduleButton.addEventListener('click', () => cancelTaskSchedule());
    
    // Schedule Task Modal
    scheduleType.addEventListener('change', updateScheduleTaskOptions);
    cancelScheduleModal.addEventListener('click', hideScheduleTaskModal);
    saveScheduleButton.addEventListener('click', saveTaskSchedule);
    
    // Theme
    themeToggle.addEventListener('click', toggleTheme);
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === newTaskModal) {
            hideNewTaskModal();
        }
        if (e.target === taskDetailsModal) {
            hideTaskDetailsModal();
        }
        if (e.target === scheduleTaskModal) {
            hideScheduleTaskModal();
        }
    });
}

// Initialize
(function init() {
    initTheme();
    setupEventListeners();
    setupWebSocket();
    fetchTasks();
    fetchSchedules();
    setActiveTab('chat');
    updateScheduleOptions();
    updateScheduleTaskOptions();
})();