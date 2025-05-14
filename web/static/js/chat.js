/**
 * Chat functionality
 */

class ChatManager {
    constructor() {
        // DOM Elements
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-message');
        this.clearChatButton = document.getElementById('clear-chat');
        this.chatSuggestionsButton = document.getElementById('chat-suggestions');
        this.suggestionsContainer = document.getElementById('suggestions-container');
        this.uploadAttachmentButton = document.getElementById('upload-attachment');
        this.fileUploadInput = document.getElementById('file-upload');
        this.attachmentsPreview = document.getElementById('attachments-preview');
        
        // State
        this.sessionId = this.generateSessionId();
        this.isProcessing = false;
        this.attachments = [];
        
        this.init();
    }
    
    /**
     * Initialize the chat functionality
     */
    init() {
        // Add event listeners
        if (this.sendButton) {
            this.sendButton.addEventListener('click', this.sendMessage.bind(this));
        }
        
        if (this.chatInput) {
            this.chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        if (this.clearChatButton) {
            this.clearChatButton.addEventListener('click', this.clearChat.bind(this));
        }
        
        if (this.chatSuggestionsButton) {
            this.chatSuggestionsButton.addEventListener('click', this.toggleSuggestions.bind(this));
        }
        
        if (this.uploadAttachmentButton) {
            this.uploadAttachmentButton.addEventListener('click', () => {
                this.fileUploadInput.click();
            });
        }
        
        if (this.fileUploadInput) {
            this.fileUploadInput.addEventListener('change', this.handleFileUpload.bind(this));
        }
        
        // Add event listeners to suggestion chips
        document.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                this.chatInput.value = e.target.textContent.trim();
                this.sendMessage();
            });
        });
    }
    
    /**
     * Generate a random session ID
     * @returns {string} The session ID
     */
    generateSessionId() {
        return 'session_' + Math.random().toString(36).substring(2, 15);
    }
    
    /**
     * Add a message to the chat UI
     * @param {string} message - The message text
     * @param {boolean} isUser - Whether the message is from the user
     * @param {Array} attachments - Optional attachments to display
     */
    addMessageToChat(message, isUser = false, attachments = []) {
        if (!this.chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex items-start message-enter mb-4';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'flex-shrink-0 mr-3';
        
        const avatarInnerDiv = document.createElement('div');
        avatarInnerDiv.className = `h-10 w-10 rounded-full flex items-center justify-center text-white font-bold ${isUser ? 'bg-gray-600' : 'bg-primary-600'}`;
        avatarInnerDiv.textContent = isUser ? 'Y' : 'S';
        
        avatarDiv.appendChild(avatarInnerDiv);
        messageDiv.appendChild(avatarDiv);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'flex flex-col max-w-[85%]';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'text-xs text-gray-500 dark:text-gray-400';
        nameSpan.textContent = isUser ? 'You' : 'Scout';
        contentDiv.appendChild(nameSpan);
        
        const messageContentDiv = document.createElement('div');
        messageContentDiv.className = `${isUser ? 'bg-gray-200 dark:bg-gray-700' : 'bg-primary-100 dark:bg-primary-900'} rounded-lg p-3 text-gray-800 dark:text-gray-200`;
        messageContentDiv.innerHTML = this.formatMessageText(message);
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
        this.chatMessages.appendChild(messageDiv);
        
        // Animate the message entrance
        setTimeout(() => {
            messageDiv.classList.remove('message-enter');
            messageDiv.classList.add('message-enter-active');
        }, 10);
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    /**
     * Format message text with markdown-like syntax
     * @param {string} text - The raw message text
     * @returns {string} Formatted HTML
     */
    formatMessageText(text) {
        // Escape HTML
        let escaped = this.escapeHtml(text);
        
        // Format code blocks
        escaped = escaped.replace(/```([\\s\\S]*?)```/g, '<pre class="bg-gray-100 dark:bg-gray-600 p-2 rounded">$1</pre>');
        
        // Format inline code
        escaped = escaped.replace(/`([^`]+)`/g, '<code class="bg-gray-100 dark:bg-gray-600 px-1 rounded">$1</code>');
        
        // Format bold text
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Format italic text
        escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // Convert URLs to links
        escaped = escaped.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="text-primary-600 dark:text-primary-400 hover:underline">$1</a>');
        
        // Convert line breaks to <br>
        escaped = escaped.replace(/\n/g, '<br>');
        
        return escaped;
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
    
    /**
     * Scroll the chat container to the bottom
     */
    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }
    
    /**
     * Send a message to the API
     */
    async sendMessage() {
        if (!this.chatInput) return;
        
        const message = this.chatInput.value.trim();
        if (!message && this.attachments.length === 0) return;
        
        // Prevent double submission
        if (this.isProcessing) return;
        this.isProcessing = true;
        
        // Add user message to chat
        this.addMessageToChat(message, true);
        
        // Clear input
        this.chatInput.value = '';
        
        try {
            // Show typing indicator
            this.showTypingIndicator();
            
            // Prepare form data for file uploads
            const formData = new FormData();
            formData.append('input', message);
            formData.append('session_id', this.sessionId);
            
            // Add attachments
            this.attachments.forEach(file => {
                formData.append('files', file);
            });
            
            // Clear attachments after sending
            this.clearAttachments();
            
            // Send to API
            const response = await fetch('/api/chat', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Remove typing indicator
            this.removeTypingIndicator();
            
            // Add response to chat
            this.addMessageToChat(data.message, false, data.attachments);
            
            // If this was a task, refresh task list
            if (data.task_id) {
                // Notify task listeners if available
                if (typeof refreshTasks === 'function') {
                    refreshTasks();
                }
                
                // Show toast notification
                toast.success('Task created successfully');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            
            // Remove typing indicator
            this.removeTypingIndicator();
            
            // Show error message
            this.addMessageToChat('Sorry, there was an error processing your request. Please try again.', false);
            
            // Show toast notification
            toast.error('Failed to send message');
        } finally {
            this.isProcessing = false;
        }
    }
    
    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        if (!this.chatMessages) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'flex items-start loading-message mb-4';
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
        
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    /**
     * Remove typing indicator
     */
    removeTypingIndicator() {
        if (!this.chatMessages) return;
        
        const typingDiv = this.chatMessages.querySelector('.loading-message');
        if (typingDiv) {
            this.chatMessages.removeChild(typingDiv);
        }
    }
    
    /**
     * Clear chat messages
     */
    clearChat() {
        if (!this.chatMessages) return;
        
        // Keep only the first message (welcome message)
        while (this.chatMessages.children.length > 1) {
            this.chatMessages.removeChild(this.chatMessages.lastChild);
        }
        
        // Generate a new session ID
        this.sessionId = this.generateSessionId();
        
        // Show toast notification
        toast.info('Chat cleared');
    }
    
    /**
     * Toggle suggestions visibility
     */
    toggleSuggestions() {
        if (!this.suggestionsContainer) return;
        
        this.suggestionsContainer.classList.toggle('hidden');
    }
    
    /**
     * Handle file upload for attachments
     * @param {Event} event - The change event
     */
    handleFileUpload(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;
        
        // Add files to attachments
        for (let i = 0; i < files.length; i++) {
            this.attachments.push(files[i]);
        }
        
        // Update preview
        this.updateAttachmentsPreview();
        
        // Reset file input
        this.fileUploadInput.value = '';
    }
    
    /**
     * Update attachments preview
     */
    updateAttachmentsPreview() {
        if (!this.attachmentsPreview) return;
        
        this.attachmentsPreview.innerHTML = '';
        
        this.attachments.forEach((file, index) => {
            const attachment = document.createElement('div');
            attachment.className = 'bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-1 flex items-center';
            
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
            
            attachment.innerHTML = `
                <i class="fas ${iconClass} mr-2 text-gray-500 dark:text-gray-400"></i>
                <span class="text-sm text-gray-800 dark:text-gray-200 truncate max-w-[180px]">${file.name}</span>
                <button type="button" class="ml-2 text-gray-500 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400 remove-attachment" data-index="${index}">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            this.attachmentsPreview.appendChild(attachment);
        });
        
        // Add event listeners to remove buttons
        document.querySelectorAll('.remove-attachment').forEach(button => {
            button.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index, 10);
                this.removeAttachment(index);
            });
        });
    }
    
    /**
     * Remove attachment by index
     * @param {number} index - The attachment index
     */
    removeAttachment(index) {
        if (index >= 0 && index < this.attachments.length) {
            this.attachments.splice(index, 1);
            this.updateAttachmentsPreview();
        }
    }
    
    /**
     * Clear all attachments
     */
    clearAttachments() {
        this.attachments = [];
        this.updateAttachmentsPreview();
    }
}

// Create global chat manager
const chatManager = new ChatManager();