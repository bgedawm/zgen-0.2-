/**
 * Schedule management
 */

class ScheduleManager {
    constructor() {
        // DOM Elements
        this.scheduleList = document.getElementById('schedule-list');
        this.scheduleTimeline = document.getElementById('schedule-timeline');
        this.newScheduleButton = document.getElementById('new-schedule');
        
        // Schedule Modal Elements
        this.scheduleTaskModal = document.getElementById('schedule-task-modal');
        this.scheduleType = document.getElementById('schedule-type');
        this.scheduleTaskOptions = document.getElementById('schedule-task-options');
        this.cancelScheduleModal = document.getElementById('cancel-schedule-modal');
        this.saveScheduleButton = document.getElementById('save-schedule');
        
        // State
        this.schedules = {};
        this.selectedTaskId = null;
        
        this.init();
    }
    
    /**
     * Initialize schedule functionality
     */
    init() {
        // Add event listeners
        if (this.newScheduleButton) {
            this.newScheduleButton.addEventListener('click', this.showNewScheduleModal.bind(this));
        }
        
        if (this.scheduleType) {
            this.scheduleType.addEventListener('change', this.updateScheduleOptions.bind(this));
        }
        
        if (this.cancelScheduleModal) {
            this.cancelScheduleModal.addEventListener('click', this.hideScheduleModal.bind(this));
        }
        
        if (this.saveScheduleButton) {
            this.saveScheduleButton.addEventListener('click', this.saveSchedule.bind(this));
        }
        
        // Close modal when clicking outside
        if (this.scheduleTaskModal) {
            this.scheduleTaskModal.addEventListener('click', (e) => {
                if (e.target === this.scheduleTaskModal) {
                    this.hideScheduleModal();
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
        if (!this.scheduleType || !this.scheduleTaskOptions) return;
        
        const type = this.scheduleType.value;
        
        // Clear options
        this.scheduleTaskOptions.innerHTML = '';
        
        if (type === 'once') {
            this.scheduleTaskOptions.innerHTML = `
                <div>
                    <label for="schedule-once-datetime" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Date and Time</label>
                    <input id="schedule-once-datetime" type="datetime-local" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
                </div>
            `;
        } else if (type === 'interval') {
            this.scheduleTaskOptions.innerHTML = `
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
            this.scheduleTaskOptions.innerHTML = `
                <div>
                    <label for="schedule-cron-expression" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Cron Expression</label>
                    <input id="schedule-cron-expression" type="text" placeholder="* * * * *" class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500">
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
                    document.getElementById('schedule-cron-expression').value = value;
                });
            });
        }
    }
    
    /**
     * Fetch all schedules from the API
     */
    async fetchSchedules() {
        try {
            const response = await fetch('/api/schedules');
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.schedules = data.schedules;
                this.renderSchedules();
                this.renderTimeline();
            }
        } catch (error) {
            console.error('Error fetching schedules:', error);
            toast.error('Failed to load schedules');
        }
    }
    
    /**
     * Render schedules table
     */
    renderSchedules() {
        if (!this.scheduleList) return;
        
        const scheduledTasks = Object.values(this.schedules);
        
        if (scheduledTasks.length === 0) {
            this.scheduleList.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-10 text-center text-gray-500 dark:text-gray-400">
                        No scheduled tasks
                    </td>
                </tr>
            `;
            return;
        }
        
        this.scheduleList.innerHTML = '';
        
        scheduledTasks.forEach(schedule => {
            const task = window.taskManager ? window.taskManager.getTask(schedule.task_id) : null;
            if (!task) return; // Skip if task doesn't exist
            
            const nextRunTime = schedule.next_run_time ? this.formatDate(schedule.next_run_time) : 'Not scheduled';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${this.escapeHtml(task.name)}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-500 dark:text-gray-400">${schedule.human_readable}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-500 dark:text-gray-400">${nextRunTime}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${this.getStatusBadgeHTML(task.status)}
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
                this.viewTaskDetails(task.id);
            });
            
            tr.querySelector('.cancel-schedule').addEventListener('click', (e) => {
                e.stopPropagation();
                this.cancelTaskSchedule(task.id);
            });
            
            this.scheduleList.appendChild(tr);
        });
    }
    
    /**
     * Render timeline of upcoming schedules
     */
    renderTimeline() {
        if (!this.scheduleTimeline) return;
        
        const scheduledTasks = Object.values(this.schedules);
        
        if (scheduledTasks.length === 0) {
            this.scheduleTimeline.innerHTML = `
                <div class="text-center text-gray-500 dark:text-gray-400 py-4">
                    No upcoming scheduled tasks
                </div>
            `;
            return;
        }
        
        // Get tasks with valid next run times
        const tasksWithTimes = scheduledTasks
            .filter(schedule => schedule.next_run_time)
            .map(schedule => {
                const task = window.taskManager ? window.taskManager.getTask(schedule.task_id) : null;
                if (!task) return null;
                
                return {
                    schedule,
                    task,
                    nextRunTime: new Date(schedule.next_run_time)
                };
            })
            .filter(Boolean)
            .sort((a, b) => a.nextRunTime - b.nextRunTime);
        
        if (tasksWithTimes.length === 0) {
            this.scheduleTimeline.innerHTML = `
                <div class="text-center text-gray-500 dark:text-gray-400 py-4">
                    No upcoming scheduled tasks
                </div>
            `;
            return;
        }
        
        // Group by day
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        const nextWeek = new Date(today);
        nextWeek.setDate(nextWeek.getDate() + 7);
        
        const tasksByGroup = {
            today: [],
            tomorrow: [],
            nextWeek: [],
            future: []
        };
        
        tasksWithTimes.forEach(item => {
            const date = new Date(item.nextRunTime);
            const itemDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
            
            if (itemDate.getTime() === today.getTime()) {
                tasksByGroup.today.push(item);
            } else if (itemDate.getTime() === tomorrow.getTime()) {
                tasksByGroup.tomorrow.push(item);
            } else if (date < nextWeek) {
                tasksByGroup.nextWeek.push(item);
            } else {
                tasksByGroup.future.push(item);
            }
        });
        
        // Render timeline
        this.scheduleTimeline.innerHTML = '';
        
        // Today
        if (tasksByGroup.today.length > 0) {
            const todayGroup = document.createElement('div');
            todayGroup.innerHTML = `
                <div class="flex items-center mb-2">
                    <div class="h-3 w-3 rounded-full bg-primary-500 mr-3"></div>
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">Today</h3>
                </div>
            `;
            
            const todayList = document.createElement('div');
            todayList.className = 'ml-6 space-y-3';
            
            tasksByGroup.today.forEach(item => {
                const timeItem = document.createElement('div');
                timeItem.className = 'flex items-center';
                timeItem.innerHTML = `
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300 w-16">
                        ${item.nextRunTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div class="ml-4 flex-grow">
                        <div class="font-medium text-gray-900 dark:text-white">${this.escapeHtml(item.task.name)}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${item.schedule.human_readable}</div>
                    </div>
                    <button class="text-primary-600 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-300 view-task" data-task-id="${item.task.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                `;
                
                // Add event listener
                timeItem.querySelector('.view-task').addEventListener('click', () => {
                    this.viewTaskDetails(item.task.id);
                });
                
                todayList.appendChild(timeItem);
            });
            
            todayGroup.appendChild(todayList);
            this.scheduleTimeline.appendChild(todayGroup);
        }
        
        // Tomorrow
        if (tasksByGroup.tomorrow.length > 0) {
            const tomorrowGroup = document.createElement('div');
            tomorrowGroup.className = 'mt-6';
            tomorrowGroup.innerHTML = `
                <div class="flex items-center mb-2">
                    <div class="h-3 w-3 rounded-full bg-blue-500 mr-3"></div>
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">Tomorrow</h3>
                </div>
            `;
            
            const tomorrowList = document.createElement('div');
            tomorrowList.className = 'ml-6 space-y-3';
            
            tasksByGroup.tomorrow.forEach(item => {
                const timeItem = document.createElement('div');
                timeItem.className = 'flex items-center';
                timeItem.innerHTML = `
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300 w-16">
                        ${item.nextRunTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                    <div class="ml-4 flex-grow">
                        <div class="font-medium text-gray-900 dark:text-white">${this.escapeHtml(item.task.name)}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${item.schedule.human_readable}</div>
                    </div>
                    <button class="text-primary-600 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-300 view-task" data-task-id="${item.task.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                `;
                
                // Add event listener
                timeItem.querySelector('.view-task').addEventListener('click', () => {
                    this.viewTaskDetails(item.task.id);
                });
                
                tomorrowList.appendChild(timeItem);
            });
            
            tomorrowGroup.appendChild(tomorrowList);
            this.scheduleTimeline.appendChild(tomorrowGroup);
        }
        
        // Next Week
        if (tasksByGroup.nextWeek.length > 0) {
            const weekGroup = document.createElement('div');
            weekGroup.className = 'mt-6';
            weekGroup.innerHTML = `
                <div class="flex items-center mb-2">
                    <div class="h-3 w-3 rounded-full bg-purple-500 mr-3"></div>
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">This Week</h3>
                </div>
            `;
            
            const weekList = document.createElement('div');
            weekList.className = 'ml-6 space-y-3';
            
            tasksByGroup.nextWeek.forEach(item => {
                const timeItem = document.createElement('div');
                timeItem.className = 'flex items-center';
                timeItem.innerHTML = `
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300 w-16">
                        ${item.nextRunTime.toLocaleDateString([], { weekday: 'short' })}
                    </div>
                    <div class="ml-4 flex-grow">
                        <div class="font-medium text-gray-900 dark:text-white">${this.escapeHtml(item.task.name)}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${item.schedule.human_readable}</div>
                    </div>
                    <button class="text-primary-600 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-300 view-task" data-task-id="${item.task.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                `;
                
                // Add event listener
                timeItem.querySelector('.view-task').addEventListener('click', () => {
                    this.viewTaskDetails(item.task.id);
                });
                
                weekList.appendChild(timeItem);
            });
            
            weekGroup.appendChild(weekList);
            this.scheduleTimeline.appendChild(weekGroup);
        }
        
        // Future
        if (tasksByGroup.future.length > 0) {
            const futureGroup = document.createElement('div');
            futureGroup.className = 'mt-6';
            futureGroup.innerHTML = `
                <div class="flex items-center mb-2">
                    <div class="h-3 w-3 rounded-full bg-gray-500 mr-3"></div>
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white">Future</h3>
                </div>
            `;
            
            const futureList = document.createElement('div');
            futureList.className = 'ml-6 space-y-3';
            
            tasksByGroup.future.forEach(item => {
                const timeItem = document.createElement('div');
                timeItem.className = 'flex items-center';
                timeItem.innerHTML = `
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300 w-16">
                        ${item.nextRunTime.toLocaleDateString()}
                    </div>
                    <div class="ml-4 flex-grow">
                        <div class="font-medium text-gray-900 dark:text-white">${this.escapeHtml(item.task.name)}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">${item.schedule.human_readable}</div>
                    </div>
                    <button class="text-primary-600 hover:text-primary-900 dark:text-primary-400 dark:hover:text-primary-300 view-task" data-task-id="${item.task.id}">
                        <i class="fas fa-eye"></i>
                    </button>
                `;
                
                // Add event listener
                timeItem.querySelector('.view-task').addEventListener('click', () => {
                    this.viewTaskDetails(item.task.id);
                });
                
                futureList.appendChild(timeItem);
            });
            
            futureGroup.appendChild(futureList);
            this.scheduleTimeline.appendChild(futureGroup);
        }
    }
    
    /**
     * View task details
     * @param {string} taskId - The task ID
     */
    viewTaskDetails(taskId) {
        if (window.taskManager && typeof window.taskManager.showTaskDetails === 'function') {
            window.taskManager.showTaskDetails(taskId);
        }
    }
    
    /**
     * Show new schedule modal
     */
    showNewScheduleModal() {
        // Get tasks to choose from
        const tasks = window.taskManager ? window.taskManager.getTasks() : [];
        
        if (tasks.length === 0) {
            toast.error('No tasks available to schedule');
            return;
        }
        
        // Create a task selection modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
                <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Select a Task to Schedule</h3>
                
                <div class="space-y-4">
                    <div class="max-h-[60vh] overflow-y-auto">
                        <div class="space-y-2" id="task-selection-list">
                            <!-- Tasks will be loaded here -->
                        </div>
                    </div>
                </div>
                
                <div class="mt-6 flex justify-end">
                    <button id="cancel-task-selection" class="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700">Cancel</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Populate tasks
        const taskList = modal.querySelector('#task-selection-list');
        tasks.forEach(task => {
            // Skip already scheduled tasks
            if (task.schedule) return;
            
            const taskItem = document.createElement('div');
            taskItem.className = 'p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer task-item';
            taskItem.dataset.taskId = task.id;
            
            taskItem.innerHTML = `
                <div class="flex items-center">
                    <div class="flex-grow">
                        <div class="font-medium text-gray-900 dark:text-white">${this.escapeHtml(task.name)}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400 truncate">${this.escapeHtml(task.description)}</div>
                    </div>
                    <div>
                        ${this.getStatusBadgeHTML(task.status)}
                    </div>
                </div>
            `;
            
            taskList.appendChild(taskItem);
        });
        
        // Add event listeners
        modal.querySelector('#cancel-task-selection').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
        
        // Add event listeners to task items
        modal.querySelectorAll('.task-item').forEach(item => {
            item.addEventListener('click', () => {
                const taskId = item.dataset.taskId;
                document.body.removeChild(modal);
                this.showScheduleTaskModal(taskId);
            });
        });
    }
    
    /**
     * Show schedule task modal for a specific task
     * @param {string} taskId - The task ID
     */
    showScheduleTaskModal(taskId) {
        if (!this.scheduleTaskModal) return;
        
        this.selectedTaskId = taskId;
        
        // Reset form
        this.scheduleType.value = 'once';
        this.updateScheduleOptions();
        
        // Set default time for once option to 1 hour from now
        const defaultTime = new Date();
        defaultTime.setHours(defaultTime.getHours() + 1);
        const dateTimeInput = document.getElementById('schedule-once-datetime');
        if (dateTimeInput) {
            dateTimeInput.value = this.formatDateTimeLocal(defaultTime);
        }
        
        // Show modal
        this.scheduleTaskModal.classList.remove('hidden');
    }
    
    /**
     * Hide schedule task modal
     */
    hideScheduleModal() {
        if (!this.scheduleTaskModal) return;
        
        this.scheduleTaskModal.classList.add('hidden');
        this.selectedTaskId = null;
    }
    
    /**
     * Save task schedule
     */
    async saveSchedule() {
        if (!this.selectedTaskId) return;
        
        // Get schedule based on type
        const type = this.scheduleType.value;
        let scheduleValue = '';
        
        if (type === 'once') {
            const dateTimeInput = document.getElementById('schedule-once-datetime');
            if (!dateTimeInput || !dateTimeInput.value) {
                toast.error('Please select a date and time');
                return;
            }
            
            const selectedDate = new Date(dateTimeInput.value);
            scheduleValue = `at:${selectedDate.toISOString()}`;
        } else if (type === 'interval') {
            const valueInput = document.getElementById('schedule-interval-value');
            const unitSelect = document.getElementById('schedule-interval-unit');
            
            if (!valueInput || !unitSelect) {
                toast.error('Missing required fields');
                return;
            }
            
            const value = parseInt(valueInput.value, 10);
            if (isNaN(value) || value < 1) {
                toast.error('Please enter a valid interval value');
                return;
            }
            
            const unit = unitSelect.value;
            scheduleValue = `every ${value}${unit}`;
        } else if (type === 'cron') {
            const cronInput = document.getElementById('schedule-cron-expression');
            if (!cronInput || !cronInput.value) {
                toast.error('Please enter a cron expression');
                return;
            }
            
            scheduleValue = `cron:${cronInput.value}`;
        }
        
        try {
            const response = await fetch(`/api/tasks/${this.selectedTaskId}/schedule`, {
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
            this.hideScheduleModal();
            
            // Refresh schedules
            await this.fetchSchedules();
            
            // Show toast notification
            toast.success('Task scheduled successfully');
        } catch (error) {
            console.error('Error scheduling task:', error);
            toast.error('Failed to schedule task. Please try again.');
        }
    }
    
    /**
     * Cancel a task schedule
     * @param {string} taskId - The task ID
     */
    async cancelTaskSchedule(taskId) {
        if (!taskId) return;
        
        if (!confirm('Are you sure you want to cancel this schedule?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/tasks/${taskId}/schedule`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            // Refresh schedules
            await this.fetchSchedules();
            
            // Show toast notification
            toast.success('Schedule cancelled successfully');
        } catch (error) {
            console.error('Error cancelling schedule:', error);
            toast.error('Failed to cancel schedule. Please try again.');
        }
    }
    
    /**
     * Format a date for display
     * @param {string} dateString - ISO date string
     * @returns {string} Formatted date
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString();
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
    escapeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }
}

// Create global schedule manager
const scheduleManager = new ScheduleManager();