/**
 * Task management functionality
 */

class TaskManager {
    constructor() {
        // DOM Elements
        this.taskList = document.getElementById('task-list');
        this.newTaskButton = document.getElementById('new-task');
        this.taskSearchInput = document.getElementById('task-search');
        this.taskStatusFilter = document.getElementById('task-status-filter');
        this.taskSort = document.getElementById('task-sort');
        
        // Tasks summary elements
        this.totalTasksElement = document.getElementById('total-tasks');
        this.pendingTasksElement = document.getElementById('pending-tasks');
        this.completedTasksElement = document.getElementById('completed-tasks');
        this.failedTasksElement = document.getElementById('failed-tasks');
        
        // Banner elements
        this.bannerCreateTaskButton = document.getElementById('banner-create-task');
        
        // New Task Modal Elements
        this.newTaskModal = document.getElementById('new-task-modal');
        this.taskNameInput = document.getElementById('task-name');
        this.taskDescriptionInput = document.getElementById('task-description');
        this.taskScheduleType = document.getElementById('task-schedule-type');
        this.scheduleOptions = document.getElementById('schedule-options');
        this.cancelTaskButton = document.getElementById('cancel-task');
        this.createTaskButton = document.getElementById('create-task');
        this.taskAddFileButton = document.getElementById('task-add-file');
        this.taskFileUploadInput = document.getElementById('task-file-upload');
        this.taskFilePreview = document.getElementById('task-file-preview');
        
        // Task Details Modal Elements
        this.taskDetailsModal = document.getElementById('task-details-modal');
        this.taskDetailsTitle = document.getElementById('task-details-title');
        this.taskDetailsDescription = document.getElementById('task-details-description');
        this.taskDetailsStatusBadge = document.getElementById('task-details-status-badge');
        this.taskDetailsProgress = document.getElementById('task-details-progress');
        this.taskDetailsProgressText = document.getElementById('task-details-progress-text');
        this.taskDetailsResultContainer = document.getElementById('task-details-result-container');
        this.taskDetailsResult = document.getElementById('task-details-result');
        this.copyResultButton = document.getElementById('copy-result');
        this.taskDetailsErrorContainer = document.getElementById('task-details-error-container');
        this.taskDetailsError = document.getElementById('task-details-error');
        this.taskDetailsArtifactsContainer = document.getElementById('task-details-artifacts-container');
        this.taskDetailsArtifacts = document.getElementById('task-details-artifacts');
        this.taskDetailsScheduleContainer = document.getElementById('task-details-schedule-container');
        this.taskDetailsSchedule = document.getElementById('task-details-schedule');
        this.taskDetailsNextRun = document.getElementById('task-details-next-run');
        this.taskDetailsHistoryContainer = document.getElementById('task-details-history-container');
        this.taskDetailsHistory = document.getElementById('task-details-history');
        this.closeTaskDetailsButton = document.getElementById('close-task-details');
        this.deleteTaskButton = document.getElementById('delete-task');
        this.scheduleTaskButton = document.getElementById('schedule-task');
        this.runTaskNowButton = document.getElementById('run-task-now');
        this.taskDetailsScheduleActions = document.getElementById('task-details-schedule-actions');
        this.cancelScheduleButton = document.getElementById('cancel-schedule');
        
        // State
        this.tasks = {};
        this.currentTaskId = null;
        this.taskFiles = [];
        
        this.init();
    }
    
    /**
     * Initialize task manager
     */
    init() {
        // Add event listeners to New Task Modal
        if (this.newTaskButton) {
            this.newTaskButton.addEventListener('click', this.showNewTaskModal.bind(this));
        }
        
        if (this.bannerCreateTaskButton) {
            this.bannerCreateTaskButton.addEventListener('click', this.showNewTaskModal.bind(this));
        }
        
        if (this.cancelTaskButton) {
            this.cancelTaskButton.addEventListener('click', this.hideNewTaskModal.bind(this));
        }
        
        if (this.createTaskButton) {
            this.createTaskButton.addEventListener('click', this.createTask.bind(this));
        }
        
        if (this.taskScheduleType) {
            this.taskScheduleType.addEventListener('change', this.updateScheduleOptions.bind(this));
        }
        
        // Add event listeners to Task Details Modal
        if (this.closeTaskDetailsButton) {
            this.closeTaskDetailsButton.addEventListener('click', this.hideTaskDetailsModal.bind(this));
        }
        
        if (this.deleteTaskButton) {
            this.deleteTaskButton.addEventListener('click', this.deleteTask.bind(this));
        }
        
        if (this.runTaskNowButton) {
            this.runTaskNowButton.addEventListener('click', this.runTaskNow.bind(this));
        }
        
        if (this.scheduleTaskButton) {
            this.scheduleTaskButton.addEventListener('click', this.scheduleTask.bind(this));
        }
        
        if (this.cancelScheduleButton) {
            this.cancelScheduleButton.addEventListener('click', this.cancelTaskSchedule.bind(this));
        }
        
        if (this.copyResultButton) {
            this.copyResultButton.addEventListener('click', this.copyTaskResult.bind(this));
        }
        
        // Add event listeners for task filtering
        if (this.taskSearchInput) {
            this.taskSearchInput.addEventListener('input', this.renderTasks.bind(this));
        }
        
        if (this.taskStatusFilter) {
            this.taskStatusFilter.addEventListener('change', this.renderTasks.bind(this));
        }
        
        if (this.taskSort) {
            this.taskSort.addEventListener('change', this.renderTasks.bind(this));
        }
        
        // File upload handling
        if (this.taskAddFileButton) {
            this.taskAddFileButton.addEventListener('click', () => {
                this.taskFileUploadInput.click();
            });
        }
        
        if (this.taskFileUploadInput) {
            this.taskFileUploadInput.addEventListener('change', this.handleTaskFileUpload.bind(this));
        }
        
        // Close modals when clicking outside
        if (this.newTaskModal) {
            this.newTaskModal.addEventListener('click', (e) => {
                if (e.target === this.newTaskModal) {
                    this.hideNewTaskModal();
                }
            });
        }
        
        if (this.taskDetailsModal) {
            this.taskDetailsModal.addEventListener('click', (e) => {
                if (e.target === this.taskDetailsModal) {
                    this.hideTaskDetailsModal();
                }
            });
        }
        
        // Initialize schedule options
        this.updateScheduleOptions();
    }
    
    /**
     * Update schedule options based on selected type
     */
    updateScheduleOptions() {
        if (!this.taskScheduleType || !this.scheduleOptions) return;
        
        const scheduleType = this.taskScheduleType.value;
        
        // Hide the options by default
        this.scheduleOptions.classList.add('hidden');
        this.scheduleOptions.innerHTML = '';
        
        if (scheduleType === 'none') {
            return;
        }
        
        // Show the options
        this.scheduleOptions.classList.remove('hidden');
        
        if (scheduleType === 'once') {
            this.scheduleOptions.innerHTML = `
                <div>
                    <label for="once-datetime" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Date and Time</label>
                    <input id="once-datetime" type="datetime-local" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                </div>
            `;
            
            // Set default time to 1 hour from now
            const defaultTime = new Date();
            defaultTime.setHours(defaultTime.getHours() + 1);
            const dateTimeInput = document.getElementById('once-datetime');
            if (dateTimeInput) {
                dateTimeInput.value = this.formatDateTimeLocal(defaultTime);
            }
        } else if (scheduleType === 'interval') {
            this.scheduleOptions.innerHTML = `
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
            this.scheduleOptions.innerHTML = `
                <div>
                    <label for="cron-expression" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Cron Expression</label>
                    <input id="cron-expression" type="text" placeholder="* * * * *" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Format: minute hour day month day_of_week</p>
                </div>
                <div class="mt-4">
                    <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Common patterns</label>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <button type="button" class="cron-preset text-left px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 text-sm" data-value="0 * * * *">
                            Hourly (0 * * * *)
                        </button>
                        <button type="button" class="cron-preset text-left px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 text-sm" data-value="0 0 * * *">
                            Daily at midnight (0 0 * * *)
                        </button>
                        <button type="button" class="cron-preset text-left px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 text-sm" data-value="0 9 * * 1-5">
                            Weekdays at 9am (0 9 * * 1-5)
                        </button>
                        <button type="button" class="cron-preset text-left px-3 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 text-sm" data-value="0 0 * * 0">
                            Weekly on Sunday (0 0 * * 0)
                        </button>
                    </div>
                </div>
            `;
            
            // Add event listeners to cron presets
            document.querySelectorAll('.cron-preset').forEach(button => {
                button.addEventListener('click', (e) => {
                    const value = e.currentTarget.dataset.value;
                    document.getElementById('cron-expression').value = value;
                });
            });
        }
    }
    
    /**
     * Format a date for datetime-local input
     * @param {Date} date - The date object
     * @returns {string} Formatted date string
     */
    formatDateTimeLocal(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    }
    
    /**
     * Handle file upload for task attachments
     * @param {Event} event - The change event
     */
    handleTaskFileUpload(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        // Add files to task files array
        for (let i = 0; i < files.length; i++) {
            this.taskFiles.push(files[i]);
        }
        
        // Update preview
        this.updateTaskFilePreview();
        
        // Reset file input
        this.taskFileUploadInput.value = '';
    }
    
    /**
     * Update task file preview
     */
    updateTaskFilePreview() {
        if (!this.taskFilePreview) return;
        
        this.taskFilePreview.innerHTML = '';
        
        this.taskFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'flex items-center bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-2 mb-2';
            
            // Determine icon based on file type
            let iconClass = 'fa-file';
            const fileType = file.type.split('/')[0];
            if (fileType === 'image') {
                iconClass = 'fa-file-image';
            } else if (fileType === 'audio') {
                iconClass = 'fa-file-audio';
            } else if (fileType === 'video') {
                iconClass = 'fa-file-video';
            } else if (fileType === 'text') {
                iconClass = 'fa-file-alt';
            } else if (file.name.endsWith('.pdf')) {
                iconClass = 'fa-file-pdf';
            } else if (file.name.match(/\.(doc|docx)$/i)) {
                iconClass = 'fa-file-word';
            } else if (file.name.match(/\.(xls|xlsx)$/i)) {
                iconClass = 'fa-file-excel';
            }
            
            fileItem.innerHTML = `
                <i class="fas ${iconClass} mr-2 text-gray-500 dark:text-gray-400"></i>
                <span class="flex-grow text-sm text-gray-800 dark:text-gray-200 truncate">${file.name}</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 mr-2">${this.formatFileSize(file.size)}</span>
                <button type="button" class="text-gray-500 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400 remove-task-file" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            this.taskFilePreview.appendChild(fileItem);
        });
        
        // Add event listeners to remove buttons
        document.querySelectorAll('.remove-task-file').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index, 10);
                this.removeTaskFile(index);
            });
        });
    }
    
    /**
     * Format file size for display
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    formatFileSize(bytes) {
        if (bytes < 1024) {
            return bytes + ' B';
        } else if (bytes < 1024 * 1024) {
            return (bytes / 1024).toFixed(1) + ' KB';
        } else if (bytes < 1024 * 1024 * 1024) {
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        } else {
            return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
        }
    }
    
    /**
     * Remove task file by index
     * @param {number} index - The file index
     */
    removeTaskFile(index) {
        if (index >= 0 && index < this.taskFiles.length) {
            this.taskFiles.splice(index, 1);
            this.updateTaskFilePreview();
        }
    }
    
    /**
     * Show new task modal
     */
    showNewTaskModal() {
        if (!this.newTaskModal) return;
        
        // Reset form
        this.taskNameInput.value = '';
        this.taskDescriptionInput.value = '';
        this.taskScheduleType.value = 'none';
        this.scheduleOptions.innerHTML = '';
        this.scheduleOptions.classList.add('hidden');
        this.taskFiles = [];
        this.updateTaskFilePreview();
        
        // Show modal
        this.newTaskModal.classList.remove('hidden');
    }
    
    /**
     * Hide new task modal
     */
    hideNewTaskModal() {
        if (!this.newTaskModal) return;
        
        this.newTaskModal.classList.add('hidden');
    }
    
    /**
     * Create a new task
     */
    async createTask() {
        const name = this.taskNameInput.value.trim();
        const description = this.taskDescriptionInput.value.trim();
        
        if (!name) {
            toast.error('Please enter a task name');
            return;
        }
        
        if (!description) {
            toast.error('Please enter a task description');
            return;
        }
        
        // Prepare schedule string
        let schedule = null;
        
        const scheduleType = this.taskScheduleType.value;
        if (scheduleType === 'once') {
            const dateTimeInput = document.getElementById('once-datetime');
            if (!dateTimeInput.value) {
                toast.error('Please select a date and time');
                return;
            }
            
            const selectedDate = new Date(dateTimeInput.value);
            schedule = `at:${selectedDate.toISOString()}`;
        } else if (scheduleType === 'interval') {
            const valueInput = document.getElementById('interval-value');
            const unitSelect = document.getElementById('interval-unit');
            
            const value = parseInt(valueInput.value, 10);
            if (isNaN(value) || value < 1) {
                toast.error('Please enter a valid interval value');
                return;
            }
            
            const unit = unitSelect.value;
            schedule = `every ${value}${unit}`;
        } else if (scheduleType === 'cron') {
            const cronInput = document.getElementById('cron-expression');
            if (!cronInput.value) {
                toast.error('Please enter a cron expression');
                return;
            }
            
            schedule = `cron:${cronInput.value}`;
        }
        
        try {
            // Prepare form data for file uploads
            const formData = new FormData();
            formData.append('name', name);
            formData.append('description', description);
            if (schedule) {
                formData.append('schedule', schedule);
            }
            
            // Add files
            this.taskFiles.forEach(file => {
                formData.append('files', file);
            });
            
            // Create the task
            const response = await fetch('/api/tasks', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Hide modal
            this.hideNewTaskModal();
            
            // Refresh tasks
            await this.fetchTasks();
            
            // Show toast notification
            toast.success('Task created successfully');
            
            // Show task details
            this.showTaskDetails(data.id);
        } catch (error) {
            console.error('Error creating task:', error);
            toast.error('Failed to create task. Please try again.');
        }
    }
    
    /**
     * Fetch all tasks from the API
     */
    async fetchTasks() {
        try {
            const response = await fetch('/api/tasks');
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const taskData = await response.json();
            
            // Update tasks state
            this.tasks = {};
            taskData.forEach(task => {
                this.tasks[task.id] = task;
            });
            
            // Update UI
            this.renderTasks();
            this.updateTaskSummary();
        } catch (error) {
            console.error('Error fetching tasks:', error);
            toast.error('Failed to load tasks');
        }
    }
    
    /**
     * Get all tasks
     * @returns {Array} Array of tasks
     */
    getTasks() {
        return Object.values(this.tasks);
    }
    
    /**
     * Get a specific task by ID
     * @param {string} taskId - The task ID
     * @returns {Object|null} The task object or null if not found
     */
    getTask(taskId) {
        return this.tasks[taskId] || null;
    }
    
    /**
     * Update task summary counters
     */
    updateTaskSummary() {
        const tasks = Object.values(this.tasks);
        
        const total = tasks.length;
        const pending = tasks.filter(task => task.status === 'pending').length;
        const running = tasks.filter(task => task.status === 'running').length;
        const completed = tasks.filter(task => task.status === 'completed').length;
        const failed = tasks.filter(task => task.status === 'failed').length;
        
        if (this.totalTasksElement) {
            this.totalTasksElement.textContent = total;
        }
        
        if (this.pendingTasksElement) {
            this.pendingTasksElement.textContent = pending + running;
        }
        
        if (this.completedTasksElement) {
            this.completedTasksElement.textContent = completed;
        }
        
        if (this.failedTasksElement) {
            this.failedTasksElement.textContent = failed;
        }
    }
    
    /**
     * Render tasks in the task list
     */
    renderTasks() {
        if (!this.taskList) return;
        
        // Get filter and sort settings
        const searchQuery = this.taskSearchInput ? this.taskSearchInput.value.toLowerCase() : '';
        const statusFilter = this.taskStatusFilter ? this.taskStatusFilter.value : 'all';
        const sortOption = this.taskSort ? this.taskSort.value : 'newest';
        
        // Convert tasks object to array
        let taskArray = Object.values(this.tasks);
        
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
        this.taskList.innerHTML = '';
        
        if (taskArray.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'text-center text-gray-500 dark:text-gray-400 py-10';
            emptyDiv.textContent = 'No tasks found';
            this.taskList.appendChild(emptyDiv);
            return;
        }
        
        // Create task cards
        taskArray.forEach(task => {
            const taskCard = document.createElement('div');
            taskCard.className = `task-card task-${task.status} bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg p-4 cursor-pointer hover:shadow-md`;
            taskCard.dataset.taskId = task.id;
            
            // Status badge
            const statusBadge = this.getStatusBadgeHTML(task.status);
            
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
                            <i class="fas fa-calendar-alt mr-1"></i>${this.escapeHTML(task.schedule)}
                        </span>
                    </div>
                `;
            }
            
            // Artifact indicator
            let artifactsIndicator = '';
            if (task.artifacts && task.artifacts.length > 0) {
                artifactsIndicator = `
                    <div class="mt-2 flex items-center">
                        <span class="text-xs text-blue-600 dark:text-blue-400">
                            <i class="fas fa-paperclip mr-1"></i>${task.artifacts.length} artifact${task.artifacts.length !== 1 ? 's' : ''}
                        </span>
                    </div>
                `;
            }
            
            taskCard.innerHTML = `
                <div class="flex justify-between items-start task-header">
                    <div class="flex-grow">
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${this.escapeHTML(task.name)}</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400 truncate">${this.escapeHTML(task.description)}</p>
                    </div>
                    <div>
                        ${statusBadge}
                    </div>
                </div>
                ${progressBar}
                <div class="flex flex-wrap gap-2">
                    ${scheduleIndicator}
                    ${artifactsIndicator}
                </div>
                <div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    ${this.formatDate(task.updated_at)}
                </div>
            `;
            
            taskCard.addEventListener('click', () => {
                this.showTaskDetails(task.id);
            });
            
            this.taskList.appendChild(taskCard);
        });
    }
    
    /**
     * Show task details modal
     * @param {string} taskId - The task ID
     */
    async showTaskDetails(taskId) {
        const task = this.tasks[taskId];
        if (!task) {
            console.error('Task not found:', taskId);
            return;
        }
        
        // Set current task ID
        this.currentTaskId = taskId;
        
        // Update modal content
        this.taskDetailsTitle.textContent = task.name;
        this.taskDetailsDescription.textContent = task.description;
        
        // Status and progress
        this.taskDetailsStatusBadge.className = `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium status-${task.status}`;
        this.taskDetailsStatusBadge.textContent = this.capitalizeFirstLetter(task.status);
        this.taskDetailsProgress.style.width = `${task.progress}%`;
        this.taskDetailsProgressText.textContent = `${task.progress}%`;
        
        // Schedule
        if (task.schedule) {
            this.taskDetailsScheduleContainer.classList.remove('hidden');
            this.taskDetailsSchedule.textContent = task.schedule;
            
            if (task.next_run_time) {
                this.taskDetailsNextRun.textContent = `Next run: ${this.formatDate(task.next_run_time)}`;
            } else {
                this.taskDetailsNextRun.textContent = '';
            }
            
            // Show cancel schedule button
            this.taskDetailsScheduleActions.classList.remove('hidden');
        } else {
            this.taskDetailsScheduleContainer.classList.add('hidden');
            this.taskDetailsScheduleActions.classList.add('hidden');
        }
        
        // Result
        if (task.result) {
            this.taskDetailsResultContainer.classList.remove('hidden');
            this.taskDetailsResult.textContent = task.result;
        } else {
            this.taskDetailsResultContainer.classList.add('hidden');
        }
        
        // Error
        if (task.error) {
            this.taskDetailsErrorContainer.classList.remove('hidden');
            this.taskDetailsError.textContent = task.error;
        } else {
            this.taskDetailsErrorContainer.classList.add('hidden');
        }
        
        // Artifacts
        if (task.artifacts && task.artifacts.length > 0) {
            this.taskDetailsArtifactsContainer.classList.remove('hidden');
            this.taskDetailsArtifacts.innerHTML = '';
            
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
                        <p class="text-sm font-medium text-gray-900 dark:text-white">${this.escapeHTML(fileName)}</p>
                    </div>
                    <a href="/api/tasks/${taskId}/artifacts/${index}" target="_blank" class="ml-2 text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300">
                        <i class="fas fa-download"></i>
                    </a>
                `;
                
                this.taskDetailsArtifacts.appendChild(li);
            });
        } else {
            this.taskDetailsArtifactsContainer.classList.add('hidden');
        }
        
        // Fetch and show task history
        const history = await this.fetchTaskHistory(taskId);
        if (history.length > 0) {
            this.taskDetailsHistory.innerHTML = '';
            
            history.forEach(run => {
                const li = document.createElement('li');
                li.className = 'border-l-2 border-gray-200 dark:border-gray-700 pl-3 pb-2';
                
                const startTime = run.start_time ? this.formatDate(run.start_time) : 'Unknown';
                const endTime = run.end_time ? this.formatDate(run.end_time) : '';
                const duration = run.start_time && run.end_time ? 
                    this.formatDuration(new Date(run.start_time), new Date(run.end_time)) : '';
                
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
                        <span class="text-sm font-medium text-gray-900 dark:text-white">${this.capitalizeFirstLetter(run.status)}</span>
                        <span class="ml-auto text-xs text-gray-500 dark:text-gray-400">${startTime}</span>
                    </div>
                    ${duration ? `<div class="text-xs text-gray-500 dark:text-gray-400">Duration: ${duration}</div>` : ''}
                    ${run.error ? `<div class="text-xs text-red-500 mt-1">${this.escapeHTML(run.error)}</div>` : ''}
                `;
                
                this.taskDetailsHistory.appendChild(li);
            });
        } else {
            this.taskDetailsHistory.innerHTML = `
                <li class="text-center text-gray-500 dark:text-gray-400 py-4">
                    No execution history
                </li>
            `;
        }
        
        // Update button states
        this.deleteTaskButton.disabled = false;
        this.runTaskNowButton.disabled = task.status === 'running';
        
        // Show modal
        this.taskDetailsModal.classList.remove('hidden');
    }
    
    /**
     * Hide task details modal
     */
    hideTaskDetailsModal() {
        if (!this.taskDetailsModal) return;
        
        this.taskDetailsModal.classList.add('hidden');
        this.currentTaskId = null;
    }
    
    /**
     * Fetch task execution history
     * @param {string} taskId - The task ID
     * @returns {Promise<Array>} Array of task runs
     */
    async fetchTaskHistory(taskId) {
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
    
    /**
     * Delete a task
     */
    async deleteTask() {
        if (!this.currentTaskId) return;
        
        if (!confirm('Are you sure you want to delete this task?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/tasks/${this.currentTaskId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            // Hide modal
            this.hideTaskDetailsModal();
            
            // Remove task from local state
            delete this.tasks[this.currentTaskId];
            
            // Update UI
            this.renderTasks();
            this.updateTaskSummary();
            
            // Show toast notification
            toast.success('Task deleted successfully');
            
            // Update schedules if available
            if (window.scheduleManager && typeof window.scheduleManager.fetchSchedules === 'function') {
                window.scheduleManager.fetchSchedules();
            }
        } catch (error) {
            console.error('Error deleting task:', error);
            toast.error('Failed to delete task. Please try again.');
        }
    }
    
    /**
     * Run a task now
     */
    async runTaskNow() {
        if (!this.currentTaskId) return;
        
        try {
            const task = this.tasks[this.currentTaskId];
            
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
            
            const data = await response.json();
            
            // Hide modal
            this.hideTaskDetailsModal();
            
            // Refresh tasks
            await this.fetchTasks();
            
            // Show toast notification
            toast.success('Task started successfully');
            
            // Show new task details
            this.showTaskDetails(data.id);
        } catch (error) {
            console.error('Error running task:', error);
            toast.error('Failed to run task. Please try again.');
        }
    }
    
    /**
     * Schedule a task
     */
    scheduleTask() {
        if (!this.currentTaskId) return;
        
        if (window.scheduleManager && typeof window.scheduleManager.showScheduleTaskModal === 'function') {
            // Hide task details modal
            this.hideTaskDetailsModal();
            
            // Show schedule modal
            window.scheduleManager.showScheduleTaskModal(this.currentTaskId);
        } else {
            toast.error('Schedule manager not available');
        }
    }
    
    /**
     * Cancel a task schedule
     */
    async cancelTaskSchedule() {
        if (!this.currentTaskId) return;
        
        if (!confirm('Are you sure you want to cancel this schedule?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/tasks/${this.currentTaskId}/schedule`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            // Hide modal
            this.hideTaskDetailsModal();
            
            // Refresh tasks
            await this.fetchTasks();
            
            // Show toast notification
            toast.success('Schedule cancelled successfully');
            
            // Update schedules if available
            if (window.scheduleManager && typeof window.scheduleManager.fetchSchedules === 'function') {
                window.scheduleManager.fetchSchedules();
            }
        } catch (error) {
            console.error('Error cancelling schedule:', error);
            toast.error('Failed to cancel schedule. Please try again.');
        }
    }
    
    /**
     * Copy task result to clipboard
     */
    copyTaskResult() {
        if (!this.taskDetailsResult) return;
        
        const resultText = this.taskDetailsResult.textContent;
        
        // Copy to clipboard
        navigator.clipboard.writeText(resultText)
            .then(() => {
                toast.success('Result copied to clipboard');
            })
            .catch(() => {
                toast.error('Failed to copy to clipboard');
            });
    }
    
    /**
     * Format date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date string
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString();
    }
    
    /**
     * Format duration between two dates
     * @param {Date} startDate - Start date
     * @param {Date} endDate - End date
     * @returns {string} Formatted duration
     */
    formatDuration(startDate, endDate) {
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
    
    /**
     * Get HTML for status badge
     * @param {string} status - The task status
     * @returns {string} HTML for status badge
     */
    getStatusBadgeHTML(status) {
        return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium status-${status}">${this.capitalizeFirstLetter(status)}</span>`;
    }
    
    /**
     * Capitalize first letter of a string
     * @param {string} string - The input string
     * @returns {string} String with first letter capitalized
     */
    capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }
    
    /**
     * Escape HTML special characters
     * @param {string} html - The HTML string to escape
     * @returns {string} Escaped HTML
     */
    escapeHTML(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }
}

// Create global task manager
const taskManager = new TaskManager();