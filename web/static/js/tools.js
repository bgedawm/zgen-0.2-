/**
 * Tools management
 */

const TOOL_CATEGORIES = {
    file: {
        name: 'File Operations',
        icon: 'fa-file',
        color: 'blue'
    },
    web: {
        name: 'Web Tools',
        icon: 'fa-globe',
        color: 'purple'
    },
    code: {
        name: 'Code Execution',
        icon: 'fa-code',
        color: 'green'
    },
    data: {
        name: 'Data Processing',
        icon: 'fa-database',
        color: 'orange'
    }
};

class ToolsManager {
    constructor() {
        this.tools = [];
        this.container = document.getElementById('tools-grid');
        this.searchInput = document.getElementById('tools-search');
        this.categoryFilters = document.querySelectorAll('.tool-category-filter');
        
        this.activeCategory = 'all';
        
        // Add event listeners
        if (this.searchInput) {
            this.searchInput.addEventListener('input', this.filterTools.bind(this));
        }
        
        this.categoryFilters.forEach(button => {
            button.addEventListener('click', (e) => {
                const category = e.currentTarget.dataset.category;
                this.setActiveCategory(category);
                this.filterTools();
            });
        });
    }
    
    /**
     * Set the active category filter
     * @param {string} category 
     */
    setActiveCategory(category) {
        this.activeCategory = category;
        
        // Update UI
        this.categoryFilters.forEach(button => {
            const buttonCategory = button.dataset.category;
            if (buttonCategory === category) {
                button.classList.add('bg-primary-100', 'dark:bg-primary-900', 'text-primary-800', 'dark:text-primary-200');
                button.classList.remove('bg-gray-100', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
                button.classList.add('active');
            } else {
                button.classList.remove('bg-primary-100', 'dark:bg-primary-900', 'text-primary-800', 'dark:text-primary-200');
                button.classList.add('bg-gray-100', 'dark:bg-gray-700', 'text-gray-800', 'dark:text-gray-200');
                button.classList.remove('active');
            }
        });
    }
    
    /**
     * Fetch available tools from the API
     */
    async fetchTools() {
        try {
            const response = await fetch('/api/tools');
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success) {
                this.tools = data.tools;
                this.renderTools();
            }
        } catch (error) {
            console.error('Error fetching tools:', error);
            this.showError();
        }
    }
    
    /**
     * Show an error message in the tools grid
     */
    showError() {
        if (this.container) {
            this.container.innerHTML = `
                <div class="text-center text-gray-500 dark:text-gray-400 py-10 col-span-3">
                    <i class="fas fa-exclamation-circle text-3xl mb-2"></i>
                    <p>Failed to load tools. Please try again later.</p>
                </div>
            `;
        }
    }
    
    /**
     * Filter tools based on search query and category
     */
    filterTools() {
        const searchQuery = this.searchInput ? this.searchInput.value.toLowerCase() : '';
        
        // Filter tools
        const filteredTools = this.tools.filter(tool => {
            // Category filter
            if (this.activeCategory !== 'all' && tool.category !== this.activeCategory) {
                return false;
            }
            
            // Search filter
            if (searchQuery) {
                return (
                    tool.name.toLowerCase().includes(searchQuery) ||
                    tool.description.toLowerCase().includes(searchQuery)
                );
            }
            
            return true;
        });
        
        this.renderToolsList(filteredTools);
    }
    
    /**
     * Render all tools
     */
    renderTools() {
        if (!this.tools || this.tools.length === 0) {
            // If no tools data yet, use mock data
            this.loadMockTools();
            return;
        }
        
        this.filterTools();
    }
    
    /**
     * Render a filtered list of tools
     * @param {Array} tools 
     */
    renderToolsList(tools) {
        if (!this.container) return;
        
        if (tools.length === 0) {
            this.container.innerHTML = `
                <div class="text-center text-gray-500 dark:text-gray-400 py-10 col-span-3">
                    No tools match your search
                </div>
            `;
            return;
        }
        
        this.container.innerHTML = '';
        
        tools.forEach(tool => {
            const category = TOOL_CATEGORIES[tool.category] || {
                name: 'Other',
                icon: 'fa-wrench',
                color: 'gray'
            };
            
            const toolCard = document.createElement('div');
            toolCard.className = 'bg-white dark:bg-gray-700 rounded-lg shadow-sm hover:shadow-md transition-all p-4 border border-gray-200 dark:border-gray-600';
            
            toolCard.innerHTML = `
                <div class="flex items-start">
                    <div class="flex-shrink-0 mr-3">
                        <div class="h-10 w-10 rounded-full bg-${category.color}-100 dark:bg-${category.color}-900 flex items-center justify-center text-${category.color}-500 dark:text-${category.color}-400">
                            <i class="fas ${category.icon}"></i>
                        </div>
                    </div>
                    <div>
                        <h3 class="text-lg font-medium text-gray-900 dark:text-white">${tool.name}</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">${tool.description}</p>
                        <div class="mt-2">
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-${category.color}-100 text-${category.color}-800 dark:bg-${category.color}-900 dark:text-${category.color}-200">
                                ${category.name}
                            </span>
                        </div>
                    </div>
                </div>
            `;
            
            this.container.appendChild(toolCard);
        });
    }
    
    /**
     * Load mock tools for development purposes
     */
    loadMockTools() {
        this.tools = [
            {
                name: 'File Reader',
                description: 'Read file contents from your local system',
                category: 'file',
                parameters: [
                    { name: 'path', type: 'string', description: 'Path to the file' }
                ]
            },
            {
                name: 'File Writer',
                description: 'Write content to a file on your local system',
                category: 'file',
                parameters: [
                    { name: 'path', type: 'string', description: 'Path to the file' },
                    { name: 'content', type: 'string', description: 'Content to write' }
                ]
            },
            {
                name: 'Web Search',
                description: 'Search the web for information',
                category: 'web',
                parameters: [
                    { name: 'query', type: 'string', description: 'Search query' }
                ]
            },
            {
                name: 'Web Scraper',
                description: 'Extract data from websites',
                category: 'web',
                parameters: [
                    { name: 'url', type: 'string', description: 'URL to scrape' },
                    { name: 'selector', type: 'string', description: 'CSS selector for the data' }
                ]
            },
            {
                name: 'Python Executor',
                description: 'Execute Python code',
                category: 'code',
                parameters: [
                    { name: 'code', type: 'string', description: 'Python code to execute' }
                ]
            },
            {
                name: 'JavaScript Executor',
                description: 'Execute JavaScript code',
                category: 'code',
                parameters: [
                    { name: 'code', type: 'string', description: 'JavaScript code to execute' }
                ]
            },
            {
                name: 'CSV Processor',
                description: 'Process CSV data',
                category: 'data',
                parameters: [
                    { name: 'file', type: 'string', description: 'Path to CSV file' },
                    { name: 'operation', type: 'string', description: 'Operation to perform' }
                ]
            },
            {
                name: 'Data Analyzer',
                description: 'Analyze and visualize data',
                category: 'data',
                parameters: [
                    { name: 'data', type: 'array', description: 'Data array to analyze' },
                    { name: 'type', type: 'string', description: 'Type of analysis' }
                ]
            },
            {
                name: 'Shell Command',
                description: 'Execute shell commands',
                category: 'code',
                parameters: [
                    { name: 'command', type: 'string', description: 'Command to execute' }
                ]
            }
        ];
        
        this.renderTools();
    }
}

// Create global tools manager
const toolsManager = new ToolsManager();