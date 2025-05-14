/**
 * Toast notification system
 */

class ToastManager {
    constructor() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - The type of toast (success, error, info)
     * @param {number} duration - Duration in milliseconds to show the toast
     */
    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        // Create icon based on type
        let iconClass = 'fa-info-circle';
        if (type === 'success') {
            iconClass = 'fa-check-circle';
        } else if (type === 'error') {
            iconClass = 'fa-exclamation-circle';
        }
        
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${iconClass} mr-2"></i>
                <span>${message}</span>
                <button class="ml-auto toast-close">
                    <i class="fas fa-times text-sm"></i>
                </button>
            </div>
        `;
        
        // Add to container
        this.container.appendChild(toast);
        
        // Force reflow to trigger transition
        void toast.offsetWidth;
        
        // Add show class to animate in
        toast.classList.add('show');
        
        // Setup close button
        const closeButton = toast.querySelector('.toast-close');
        closeButton.addEventListener('click', () => {
            this.close(toast);
        });
        
        // Auto close after duration
        setTimeout(() => {
            this.close(toast);
        }, duration);
        
        return toast;
    }
    
    /**
     * Show a success toast
     * @param {string} message 
     * @param {number} duration 
     */
    success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }
    
    /**
     * Show an error toast
     * @param {string} message 
     * @param {number} duration 
     */
    error(message, duration = 5000) {
        return this.show(message, 'error', duration);
    }
    
    /**
     * Show an info toast
     * @param {string} message 
     * @param {number} duration 
     */
    info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }
    
    /**
     * Close a toast element
     * @param {HTMLElement} toast 
     */
    close(toast) {
        // Remove show class to animate out
        toast.classList.remove('show');
        
        // Remove element after animation
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }
}

// Create global toast manager
const toast = new ToastManager();