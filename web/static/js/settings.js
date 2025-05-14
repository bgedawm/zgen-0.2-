/**
 * Settings management
 */

class SettingsManager {
    constructor() {
        // Default settings
        this.defaultSettings = {
            theme: 'system',
            showSuggestions: true,
            notifyTaskCompletion: true,
            notifyTaskFailure: true,
            maxHistory: 100
        };
        
        // Current settings
        this.settings = { ...this.defaultSettings };
        
        // DOM Elements
        this.settingsButton = document.getElementById('settings-button');
        this.settingsModal = document.getElementById('settings-modal');
        this.closeSettingsButton = document.getElementById('close-settings');
        this.saveSettingsButton = document.getElementById('save-settings');
        this.resetSettingsButton = document.getElementById('reset-settings');
        
        // Settings form elements
        this.themeSelect = document.getElementById('theme-select');
        this.showSuggestionsCheckbox = document.getElementById('show-suggestions');
        this.notifyTaskCompletionCheckbox = document.getElementById('notify-task-completion');
        this.notifyTaskFailureCheckbox = document.getElementById('notify-task-failure');
        this.maxHistorySelect = document.getElementById('max-history');
        
        this.init();
    }
    
    /**
     * Initialize settings and event listeners
     */
    init() {
        // Load settings from local storage
        this.loadSettings();
        
        // Apply settings
        this.applySettings();
        
        // Add event listeners
        if (this.settingsButton) {
            this.settingsButton.addEventListener('click', this.showSettingsModal.bind(this));
        }
        
        if (this.closeSettingsButton) {
            this.closeSettingsButton.addEventListener('click', this.hideSettingsModal.bind(this));
        }
        
        if (this.saveSettingsButton) {
            this.saveSettingsButton.addEventListener('click', this.saveSettings.bind(this));
        }
        
        if (this.resetSettingsButton) {
            this.resetSettingsButton.addEventListener('click', this.resetSettings.bind(this));
        }
        
        // Close modal when clicking outside
        if (this.settingsModal) {
            this.settingsModal.addEventListener('click', (e) => {
                if (e.target === this.settingsModal) {
                    this.hideSettingsModal();
                }
            });
        }
    }
    
    /**
     * Load settings from local storage
     */
    loadSettings() {
        try {
            const savedSettings = localStorage.getItem('scoutSettings');
            if (savedSettings) {
                const parsedSettings = JSON.parse(savedSettings);
                this.settings = { ...this.defaultSettings, ...parsedSettings };
            }
        } catch (error) {
            console.error('Error loading settings:', error);
            this.settings = { ...this.defaultSettings };
        }
    }
    
    /**
     * Save settings to local storage
     */
    saveSettings() {
        // Get values from form
        if (this.themeSelect) {
            this.settings.theme = this.themeSelect.value;
        }
        
        if (this.showSuggestionsCheckbox) {
            this.settings.showSuggestions = this.showSuggestionsCheckbox.checked;
        }
        
        if (this.notifyTaskCompletionCheckbox) {
            this.settings.notifyTaskCompletion = this.notifyTaskCompletionCheckbox.checked;
        }
        
        if (this.notifyTaskFailureCheckbox) {
            this.settings.notifyTaskFailure = this.notifyTaskFailureCheckbox.checked;
        }
        
        if (this.maxHistorySelect) {
            this.settings.maxHistory = parseInt(this.maxHistorySelect.value, 10);
        }
        
        // Save to local storage
        try {
            localStorage.setItem('scoutSettings', JSON.stringify(this.settings));
            toast.success('Settings saved successfully');
        } catch (error) {
            console.error('Error saving settings:', error);
            toast.error('Failed to save settings');
        }
        
        // Apply settings
        this.applySettings();
        
        // Hide modal
        this.hideSettingsModal();
    }
    
    /**
     * Reset settings to defaults
     */
    resetSettings() {
        // Reset to defaults
        this.settings = { ...this.defaultSettings };
        
        // Update form
        this.updateSettingsForm();
        
        // Save to local storage
        try {
            localStorage.setItem('scoutSettings', JSON.stringify(this.settings));
            toast.info('Settings reset to defaults');
        } catch (error) {
            console.error('Error saving settings:', error);
        }
        
        // Apply settings
        this.applySettings();
    }
    
    /**
     * Apply settings to the application
     */
    applySettings() {
        // Apply theme
        this.applyTheme();
        
        // Apply show suggestions
        this.applyShowSuggestions();
        
        // Apply other settings as needed
        
        // Update form
        this.updateSettingsForm();
    }
    
    /**
     * Apply theme setting
     */
    applyTheme() {
        const { theme } = this.settings;
        
        if (theme === 'light') {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('color-theme', 'light');
        } else if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
        } else {
            // System default
            if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            localStorage.removeItem('color-theme');
        }
    }
    
    /**
     * Apply show suggestions setting
     */
    applyShowSuggestions() {
        const suggestionsContainer = document.getElementById('suggestions-container');
        if (suggestionsContainer) {
            if (this.settings.showSuggestions) {
                suggestionsContainer.classList.remove('hidden');
            } else {
                suggestionsContainer.classList.add('hidden');
            }
        }
    }
    
    /**
     * Update settings form with current values
     */
    updateSettingsForm() {
        if (this.themeSelect) {
            this.themeSelect.value = this.settings.theme;
        }
        
        if (this.showSuggestionsCheckbox) {
            this.showSuggestionsCheckbox.checked = this.settings.showSuggestions;
        }
        
        if (this.notifyTaskCompletionCheckbox) {
            this.notifyTaskCompletionCheckbox.checked = this.settings.notifyTaskCompletion;
        }
        
        if (this.notifyTaskFailureCheckbox) {
            this.notifyTaskFailureCheckbox.checked = this.settings.notifyTaskFailure;
        }
        
        if (this.maxHistorySelect) {
            this.maxHistorySelect.value = this.settings.maxHistory;
        }
    }
    
    /**
     * Show settings modal
     */
    showSettingsModal() {
        if (this.settingsModal) {
            this.settingsModal.classList.remove('hidden');
            this.updateSettingsForm();
        }
    }
    
    /**
     * Hide settings modal
     */
    hideSettingsModal() {
        if (this.settingsModal) {
            this.settingsModal.classList.add('hidden');
        }
    }
    
    /**
     * Get a specific setting
     * @param {string} key - The setting key
     * @param {any} defaultValue - Default value if setting not found
     * @returns {any} The setting value
     */
    getSetting(key, defaultValue = undefined) {
        return this.settings[key] !== undefined ? this.settings[key] : defaultValue;
    }
}

// Create global settings manager
const settingsManager = new SettingsManager();