/**
 * Help functionality
 */

class HelpManager {
    constructor() {
        // DOM Elements
        this.helpButton = document.getElementById('help-button');
        this.helpModal = document.getElementById('help-modal');
        this.closeHelpButton = document.getElementById('close-help');
        
        this.init();
    }
    
    /**
     * Initialize help functionality
     */
    init() {
        // Add event listeners
        if (this.helpButton) {
            this.helpButton.addEventListener('click', this.showHelpModal.bind(this));
        }
        
        if (this.closeHelpButton) {
            this.closeHelpButton.addEventListener('click', this.hideHelpModal.bind(this));
        }
        
        // Close modal when clicking outside
        if (this.helpModal) {
            this.helpModal.addEventListener('click', (e) => {
                if (e.target === this.helpModal) {
                    this.hideHelpModal();
                }
            });
        }
    }
    
    /**
     * Show help modal
     */
    showHelpModal() {
        if (this.helpModal) {
            this.helpModal.classList.remove('hidden');
        }
    }
    
    /**
     * Hide help modal
     */
    hideHelpModal() {
        if (this.helpModal) {
            this.helpModal.classList.add('hidden');
        }
    }
}

// Create global help manager
const helpManager = new HelpManager();