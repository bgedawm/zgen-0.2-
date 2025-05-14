/**
 * Monitoring Dashboard JavaScript
 * -------------------------------
 * Handles the functionality for the monitoring dashboard including data fetching,
 * chart rendering, and interactive features.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the monitoring dashboard
    const MonitoringDashboard = {
        // Chart objects
        charts: {},
        
        // Current monitoring state
        monitoringActive: false,
        
        // Auto-refresh timer
        refreshTimer: null,
        
        // Last refresh timestamp
        lastRefresh: null,
        
        // Tab state
        currentTab: 'system',
        
        // Initialize the dashboard
        init() {
            this.setupEventListeners();
            this.setupTabs();
            this.refreshDashboard();
            this.startAutoRefresh();
        },
        
        // Set up event listeners
        setupEventListeners() {
            // Tab navigation
            document.querySelectorAll('.tab-button').forEach(button => {
                button.addEventListener('click', () => {
                    this.switchTab(button.dataset.tab);
                });
            });
            
            // Refresh button
            document.getElementById('refresh-now').addEventListener('click', () => {
                this.refreshDashboard();
            });
            
            // Toggle monitoring button
            document.getElementById('toggle-monitoring').addEventListener('click', () => {
                this.toggleMonitoring();
            });
            
            // Auto-refresh selector
            document.getElementById('auto-refresh').addEventListener('change', (e) => {
                this.setAutoRefresh(parseInt(e.target.value));
            });
            
            // Create alert form
            document.getElementById('create-alert-form').addEventListener('submit', (e) => {
                e.preventDefault();
                this.createAlert();
            });
            
            // Log filters
            document.getElementById('log-level').addEventListener('change', () => {
                this.filterLogs();
            });
            
            document.getElementById('log-component').addEventListener('change', () => {
                this.filterLogs();
            });
            
            document.getElementById('log-search').addEventListener('input', () => {
                this.filterLogs();
            });
            
            document.getElementById('clear-logs').addEventListener('click', () => {
                this.clearLogFilters();
            });
            
            // Performance filters
            document.getElementById('performance-category').addEventListener('change', () => {
                this.loadPerformanceMetrics();
            });
            
            document.getElementById('performance-metric').addEventListener('change', () => {
                this.updatePerformanceChart();
            });
            
            document.getElementById('performance-time-range').addEventListener('change', () => {
                this.loadPerformanceMetrics();
            });
        },
        
        // Set up tabs
        setupTabs() {
            const tabButtons = document.querySelectorAll('.tab-button');
            const tabPanes = document.querySelectorAll('.tab-pane');
            
            // Show the active tab
            this.switchTab('system');
        },
        
        // Switch between tabs
        switchTab(tabName) {
            // Update current tab
            this.currentTab = tabName;
            
            // Update tab buttons
            document.querySelectorAll('.tab-button').forEach(button => {
                if (button.dataset.tab === tabName) {
                    button.classList.add('active');
                } else {
                    button.classList.remove('active');
                }
            });
            
            // Update tab content
            document.querySelectorAll('.tab-pane').forEach(pane => {
                if (pane.id === `tab-${tabName}`) {
                    pane.classList.add('active');
                } else {
                    pane.classList.remove('active');
                }
            });
            
            // Load data for the selected tab
            this.loadTabData(tabName);
        },
        
        // Load data for the selected tab
        loadTabData(tabName) {
            switch (tabName) {
                case 'system':
                    this.loadSystemMetrics();
                    break;
                case 'performance':
                    this.loadPerformanceMetrics();
                    break;
                case 'alerts':
                    this.loadAlerts();
                    break;
                case 'logs':
                    this.loadLogs();
                    break;
            }
        },
        
        // Start automatic refresh
        startAutoRefresh() {
            const refreshInterval = parseInt(document.getElementById('auto-refresh').value);
            this.setAutoRefresh(refreshInterval);
        },
        
        // Set auto-refresh interval
        setAutoRefresh(seconds) {
            // Clear existing timer
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
                this.refreshTimer = null;
            }
            
            // Create new timer if seconds > 0
            if (seconds > 0) {
                this.refreshTimer = setInterval(() => {
                    this.refreshDashboard();
                }, seconds * 1000);
            }
        },
        
        // Refresh the current dashboard
        refreshDashboard() {
            // Update last refresh timestamp
            this.lastRefresh = new Date();
            document.getElementById('last-updated').textContent = `Last updated: ${this.formatTime(this.lastRefresh)}`;
            
            // Refresh the current tab
            this.loadTabData(this.currentTab);
            
            // Check monitoring status
            this.checkMonitoringStatus();
        },
        
        // Toggle monitoring on/off
        toggleMonitoring() {
            const button = document.getElementById('toggle-monitoring');
            
            if (this.monitoringActive) {
                // Stop monitoring
                fetch('/api/monitoring/control/stop', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        this.monitoringActive = false;
                        button.textContent = 'Start Monitoring';
                        button.classList.remove('btn-danger');
                        button.classList.add('btn-primary');
                        this.showToast('Monitoring stopped');
                    } else {
                        this.showToast('Failed to stop monitoring', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error stopping monitoring:', error);
                    this.showToast('Error stopping monitoring', 'error');
                });
            } else {
                // Start monitoring
                fetch('/api/monitoring/control/start', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        this.monitoringActive = true;
                        button.textContent = 'Stop Monitoring';
                        button.classList.remove('btn-primary');
                        button.classList.add('btn-danger');
                        this.showToast('Monitoring started');
                    } else {
                        this.showToast('Failed to start monitoring', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error starting monitoring:', error);
                    this.showToast('Error starting monitoring', 'error');
                });
            }
        },
        
        // Check monitoring system status
        checkMonitoringStatus() {
            fetch('/api/monitoring')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'active') {
                        this.monitoringActive = true;
                        const button = document.getElementById('toggle-monitoring');
                        button.textContent = 'Stop Monitoring';
                        button.classList.remove('btn-primary');
                        button.classList.add('btn-danger');
                    } else {
                        this.monitoringActive = false;
                    }
                })
                .catch(error => {
                    console.error('Error checking monitoring status:', error);
                });
        },
        
        // Load system metrics
        loadSystemMetrics() {
            fetch('/api/monitoring/metrics?category=system')
                .then(response => response.json())
                .then(data => {
                    this.updateSystemCharts(data);
                    this.updateSystemInfo();
                })
                .catch(error => {
                    console.error('Error loading system metrics:', error);
                });
        },
        
        // Update system charts
        updateSystemCharts(metricsData) {
            // Process CPU metrics
            const cpuMetrics = {};
            const memoryMetrics = {};
            const diskMetrics = {};
            const networkMetrics = {};
            
            // Group metrics by type
            Object.entries(metricsData).forEach(([name, values]) => {
                if (name.includes('cpu')) {
                    cpuMetrics[name] = values;
                } else if (name.includes('memory')) {
                    memoryMetrics[name] = values;
                } else if (name.includes('disk')) {
                    diskMetrics[name] = values;
                } else if (name.includes('network')) {
                    networkMetrics[name] = values;
                }
            });
            
            // Update CPU chart
            this.updateCpuChart(cpuMetrics);
            
            // Update Memory chart
            this.updateMemoryChart(memoryMetrics);
            
            // Update Disk chart
            this.updateDiskChart(diskMetrics);
            
            // Update Network chart
            this.updateNetworkChart(networkMetrics);
            
            // Update metric tables
            this.updateMetricTable('cpu-metrics', cpuMetrics);
            this.updateMetricTable('memory-metrics', memoryMetrics);
            this.updateMetricTable('disk-metrics', diskMetrics);
            this.updateMetricTable('network-metrics', networkMetrics);
        },
        
        // Update CPU chart
        updateCpuChart(cpuMetrics) {
            // Get CPU percent data
            const cpuPercentData = cpuMetrics['system.cpu_percent'] || [];
            
            // Prepare chart data
            const labels = cpuPercentData.map(item => this.formatTime(new Date(item[0])));
            const data = cpuPercentData.map(item => item[1]);
            
            // Create or update chart
            if (!this.charts.cpu) {
                const ctx = document.getElementById('cpu-chart').getContext('2d');
                this.charts.cpu = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'CPU Usage',
                            data: data,
                            borderColor: 'rgb(75, 192, 192)',
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            tension: 0.2,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Usage (%)'
                                }
                            },
                            x: {
                                ticks: {
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 10
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        }
                    }
                });
            } else {
                this.charts.cpu.data.labels = labels;
                this.charts.cpu.data.datasets[0].data = data;
                this.charts.cpu.update();
            }
        },
        
        // Update Memory chart
        updateMemoryChart(memoryMetrics) {
            // Get memory percent data
            const memoryPercentData = memoryMetrics['system.memory_percent'] || [];
            
            // Prepare chart data
            const labels = memoryPercentData.map(item => this.formatTime(new Date(item[0])));
            const data = memoryPercentData.map(item => item[1]);
            
            // Create or update chart
            if (!this.charts.memory) {
                const ctx = document.getElementById('memory-chart').getContext('2d');
                this.charts.memory = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Memory Usage',
                            data: data,
                            borderColor: 'rgb(153, 102, 255)',
                            backgroundColor: 'rgba(153, 102, 255, 0.2)',
                            tension: 0.2,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Usage (%)'
                                }
                            },
                            x: {
                                ticks: {
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 10
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        }
                    }
                });
            } else {
                this.charts.memory.data.labels = labels;
                this.charts.memory.data.datasets[0].data = data;
                this.charts.memory.update();
            }
        },
        
        // Update Disk chart
        updateDiskChart(diskMetrics) {
            // Get disk percent data for root or first available disk
            let diskPercentData = [];
            Object.entries(diskMetrics).forEach(([name, values]) => {
                if (name.includes('percent') && diskPercentData.length === 0) {
                    diskPercentData = values;
                }
            });
            
            // Prepare chart data
            const labels = diskPercentData.map(item => this.formatTime(new Date(item[0])));
            const data = diskPercentData.map(item => item[1]);
            
            // Create or update chart
            if (!this.charts.disk) {
                const ctx = document.getElementById('disk-chart').getContext('2d');
                this.charts.disk = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Disk Usage',
                            data: data,
                            borderColor: 'rgb(255, 159, 64)',
                            backgroundColor: 'rgba(255, 159, 64, 0.2)',
                            tension: 0.2,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'Usage (%)'
                                }
                            },
                            x: {
                                ticks: {
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 10
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        }
                    }
                });
            } else {
                this.charts.disk.data.labels = labels;
                this.charts.disk.data.datasets[0].data = data;
                this.charts.disk.update();
            }
        },
        
        // Update Network chart
        updateNetworkChart(networkMetrics) {
            // Get network data
            const networkRecvData = networkMetrics['system.network_total_bytes_recv_per_sec'] || [];
            const networkSentData = networkMetrics['system.network_total_bytes_sent_per_sec'] || [];
            
            // Use timestamps from received data
            const labels = networkRecvData.map(item => this.formatTime(new Date(item[0])));
            
            // Prepare receive data (convert to KB/s)
            const recvData = networkRecvData.map(item => item[1] / 1024);
            
            // Prepare sent data (convert to KB/s)
            const sentData = networkSentData.map(item => item[1] / 1024);
            
            // Create or update chart
            if (!this.charts.network) {
                const ctx = document.getElementById('network-chart').getContext('2d');
                this.charts.network = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Received',
                                data: recvData,
                                borderColor: 'rgb(54, 162, 235)',
                                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                tension: 0.2,
                                fill: false
                            },
                            {
                                label: 'Sent',
                                data: sentData,
                                borderColor: 'rgb(255, 99, 132)',
                                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                tension: 0.2,
                                fill: false
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'KB/s'
                                }
                            },
                            x: {
                                ticks: {
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 10
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        }
                    }
                });
            } else {
                this.charts.network.data.labels = labels;
                this.charts.network.data.datasets[0].data = recvData;
                this.charts.network.data.datasets[1].data = sentData;
                this.charts.network.update();
            }
        },
        
        // Update metric table with the latest values
        updateMetricTable(tableId, metrics) {
            const table = document.getElementById(tableId);
            if (!table) return;
            
            // Clear the table
            table.innerHTML = '';
            
            // Get the latest values for each metric
            Object.entries(metrics).forEach(([name, values]) => {
                if (values.length === 0) return;
                
                // Get the latest value
                const latestValue = values[values.length - 1][1];
                
                // Format the metric name for display
                const displayName = name.replace('system.', '').replace(/_/g, ' ');
                
                // Format the value based on the metric type
                let formattedValue = '';
                
                if (name.includes('percent')) {
                    formattedValue = `${latestValue.toFixed(2)}%`;
                } else if (name.includes('bytes')) {
                    // Convert bytes to appropriate unit
                    formattedValue = this.formatBytes(latestValue);
                } else if (name.includes('per_sec')) {
                    // Format rate metrics
                    if (name.includes('bytes')) {
                        formattedValue = `${this.formatBytes(latestValue)}/s`;
                    } else {
                        formattedValue = `${latestValue.toFixed(2)}/s`;
                    }
                } else {
                    formattedValue = latestValue.toString();
                }
                
                // Create the metric row
                const row = document.createElement('div');
                row.innerHTML = `
                    <span class="metric-name">${displayName}</span>
                    <span class="metric-value">${formattedValue}</span>
                `;
                
                table.appendChild(row);
            });
        },
        
        // Update system information
        updateSystemInfo() {
            fetch('/api/monitoring')
                .then(response => response.json())
                .then(data => {
                    const systemInfo = data.system_info;
                    const infoContainer = document.getElementById('system-info');
                    
                    if (!systemInfo || !infoContainer) return;
                    
                    // Clear the container
                    infoContainer.innerHTML = '';
                    
                    // Add basic system info
                    this.addSystemInfoItem(infoContainer, 'Platform', systemInfo.platform);
                    this.addSystemInfoItem(infoContainer, 'Hostname', systemInfo.hostname);
                    this.addSystemInfoItem(infoContainer, 'Architecture', systemInfo.architecture);
                    this.addSystemInfoItem(infoContainer, 'Processor', systemInfo.processor);
                    this.addSystemInfoItem(infoContainer, 'Python Version', systemInfo.python_version);
                    
                    // Add CPU info if available
                    if (systemInfo.cpu) {
                        this.addSystemInfoItem(infoContainer, 'CPU Cores (Physical)', systemInfo.cpu.physical_cores);
                        this.addSystemInfoItem(infoContainer, 'CPU Cores (Logical)', systemInfo.cpu.logical_cores);
                        
                        if (systemInfo.cpu.frequency) {
                            this.addSystemInfoItem(infoContainer, 'CPU Frequency', `${systemInfo.cpu.frequency.current} MHz`);
                        }
                    }
                    
                    // Add memory info if available
                    if (systemInfo.memory) {
                        this.addSystemInfoItem(infoContainer, 'Total Memory', this.formatBytes(systemInfo.memory.total));
                        this.addSystemInfoItem(infoContainer, 'Available Memory', this.formatBytes(systemInfo.memory.available));
                    }
                    
                    // Add uptime if available
                    if (systemInfo.uptime_seconds) {
                        this.addSystemInfoItem(infoContainer, 'System Uptime', this.formatDuration(systemInfo.uptime_seconds));
                    }
                })
                .catch(error => {
                    console.error('Error loading system info:', error);
                });
        },
        
        // Add a system info item to the container
        addSystemInfoItem(container, label, value) {
            const item = document.createElement('div');
            item.className = 'system-info-item';
            item.innerHTML = `
                <span class="info-label">${label}:</span>
                <span class="info-value">${value}</span>
            `;
            container.appendChild(item);
        },
        
        // Load performance metrics
        loadPerformanceMetrics() {
            const category = document.getElementById('performance-category').value;
            const timeRange = document.getElementById('performance-time-range').value;
            
            // Get performance stats
            fetch(`/api/monitoring/performance${category ? `?category=${category}` : ''}`)
                .then(response => response.json())
                .then(data => {
                    this.updatePerformanceTable(data);
                    this.populatePerformanceMetricOptions(data);
                    this.updatePerformanceChart();
                })
                .catch(error => {
                    console.error('Error loading performance metrics:', error);
                });
        },
        
        // Update performance metrics table
        updatePerformanceTable(metricsData) {
            const tableBody = document.querySelector('#performance-metrics-table tbody');
            if (!tableBody) return;
            
            // Clear table
            tableBody.innerHTML = '';
            
            // Sort metrics by category and name
            const sortedMetrics = [];
            
            Object.entries(metricsData).forEach(([category, metrics]) => {
                Object.entries(metrics).forEach(([name, stats]) => {
                    sortedMetrics.push({
                        name: name.replace(/_duration$/, ''),
                        category,
                        latest: stats.latest,
                        average: stats.average,
                        min: stats.min,
                        max: stats.max,
                        count: stats.count
                    });
                });
            });
            
            // Sort by category then name
            sortedMetrics.sort((a, b) => {
                if (a.category === b.category) {
                    return a.name.localeCompare(b.name);
                }
                return a.category.localeCompare(b.category);
            });
            
            // Add rows
            sortedMetrics.forEach(metric => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${metric.name}</td>
                    <td>${metric.category}</td>
                    <td>${metric.latest.toFixed(4)}s</td>
                    <td>${metric.average.toFixed(4)}s</td>
                    <td>${metric.min.toFixed(4)}s</td>
                    <td>${metric.max.toFixed(4)}s</td>
                    <td>${metric.count}</td>
                `;
                tableBody.appendChild(row);
            });
            
            // Update category filter if needed
            this.updatePerformanceCategoryOptions(metricsData);
        },
        
        // Update performance category options
        updatePerformanceCategoryOptions(metricsData) {
            const categorySelect = document.getElementById('performance-category');
            if (!categorySelect) return;
            
            // Get current value
            const currentValue = categorySelect.value;
            
            // Get categories
            const categories = Object.keys(metricsData);
            
            // Clear options (except the first one)
            while (categorySelect.options.length > 1) {
                categorySelect.remove(1);
            }
            
            // Add categories
            categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categorySelect.appendChild(option);
            });
            
            // Set the previous value if still valid
            if (currentValue && categories.includes(currentValue)) {
                categorySelect.value = currentValue;
            }
        },
        
        // Populate performance metric options
        populatePerformanceMetricOptions(metricsData) {
            const metricSelect = document.getElementById('performance-metric');
            if (!metricSelect) return;
            
            // Get current value
            const currentValue = metricSelect.value;
            
            // Get current category
            const category = document.getElementById('performance-category').value;
            
            // Get metrics for the selected category, or all metrics if no category selected
            let metrics = [];
            
            if (category) {
                // Get metrics for the specific category
                if (metricsData[category]) {
                    metrics = Object.keys(metricsData[category]);
                }
            } else {
                // Get all metrics
                Object.values(metricsData).forEach(categoryMetrics => {
                    metrics = metrics.concat(Object.keys(categoryMetrics));
                });
            }
            
            // Clear options (except the first one)
            while (metricSelect.options.length > 1) {
                metricSelect.remove(1);
            }
            
            // Add metrics
            metrics.forEach(metric => {
                const displayName = metric.replace(/_duration$/, '');
                const option = document.createElement('option');
                option.value = metric;
                option.textContent = displayName;
                metricSelect.appendChild(option);
            });
            
            // Set the previous value if still valid
            if (currentValue && metrics.includes(currentValue)) {
                metricSelect.value = currentValue;
            } else if (metrics.length > 0) {
                // Set the first metric if available
                metricSelect.selectedIndex = 1;
            }
        },
        
        // Update performance chart
        updatePerformanceChart() {
            const metricSelect = document.getElementById('performance-metric');
            const categorySelect = document.getElementById('performance-category');
            
            if (!metricSelect || metricSelect.selectedIndex <= 0) return;
            
            const metricName = metricSelect.value;
            const category = categorySelect.value;
            
            // Build the full metric name
            const fullMetricName = category ? `${category}.${metricName}` : metricName;
            
            // Fetch metric history
            fetch(`/api/monitoring/metrics/${fullMetricName}?limit=100`)
                .then(response => response.json())
                .then(data => {
                    this.renderPerformanceChart(data.name, data.values);
                })
                .catch(error => {
                    console.error(`Error fetching metric ${fullMetricName}:`, error);
                });
        },
        
        // Render performance chart
        renderPerformanceChart(metricName, metricValues) {
            // Prepare chart data
            const labels = metricValues.map(item => this.formatTime(new Date(item[0])));
            const data = metricValues.map(item => item[1]);
            
            // Format display name
            const displayName = metricName.replace(/_duration$/, '').split('.').pop();
            
            // Create or update chart
            if (!this.charts.performance) {
                const ctx = document.getElementById('performance-chart').getContext('2d');
                this.charts.performance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: displayName,
                            data: data,
                            borderColor: 'rgb(75, 192, 192)',
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            tension: 0.2,
                            fill: false
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Duration (seconds)'
                                }
                            },
                            x: {
                                ticks: {
                                    maxRotation: 0,
                                    autoSkip: true,
                                    maxTicksLimit: 10
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            },
                            title: {
                                display: true,
                                text: `Performance Metric: ${displayName}`
                            }
                        }
                    }
                });
            } else {
                // Update chart title
                this.charts.performance.options.plugins.title.text = `Performance Metric: ${displayName}`;
                
                // Update dataset
                this.charts.performance.data.labels = labels;
                this.charts.performance.data.datasets[0].label = displayName;
                this.charts.performance.data.datasets[0].data = data;
                this.charts.performance.update();
            }
        },
        
        // Load alerts and alert history
        loadAlerts() {
            // Load active alerts
            fetch('/api/monitoring/alerts')
                .then(response => response.json())
                .then(data => {
                    this.updateAlertStatus(data);
                    this.renderActiveAlerts(data.alerts);
                })
                .catch(error => {
                    console.error('Error loading alerts:', error);
                });
            
            // Load alert history
            fetch('/api/monitoring/alerts/history')
                .then(response => response.json())
                .then(data => {
                    this.renderAlertHistory(data.history);
                })
                .catch(error => {
                    console.error('Error loading alert history:', error);
                });
        },
        
        // Update alert status counts
        updateAlertStatus(alertData) {
            // Count alerts by severity
            const severityCounts = {
                'critical': 0,
                'error': 0,
                'warning': 0,
                'info': 0
            };
            
            // Count active alerts by severity
            alertData.alerts.forEach(alert => {
                const severity = alert.severity;
                if (severityCounts.hasOwnProperty(severity)) {
                    severityCounts[severity]++;
                }
            });
            
            // Update status counts
            Object.entries(severityCounts).forEach(([severity, count]) => {
                const element = document.querySelector(`#alert-status-${severity} .status-count`);
                if (element) {
                    element.textContent = count;
                }
            });
        },
        
        // Render active alerts
        renderActiveAlerts(alerts) {
            const container = document.getElementById('active-alerts-container');
            if (!container) return;
            
            // Clear container
            container.innerHTML = '';
            
            if (alerts.length === 0) {
                container.innerHTML = '<div class="no-alerts-message">No active alerts</div>';
                return;
            }
            
            // Sort alerts by severity (critical first)
            const sortedAlerts = [...alerts].sort((a, b) => {
                const severityOrder = {
                    'critical': 0,
                    'error': 1,
                    'warning': 2,
                    'info': 3
                };
                
                return severityOrder[a.severity] - severityOrder[b.severity];
            });
            
            // Render each alert
            sortedAlerts.forEach(alert => {
                const alertElement = document.createElement('div');
                alertElement.className = `alert-item alert-${alert.severity}`;
                
                // Format triggered time
                const triggeredTime = alert.triggered_at ? new Date(alert.triggered_at) : null;
                const triggeredTimeStr = triggeredTime ? this.formatDateTime(triggeredTime) : 'Unknown';
                
                // Format acknowledged time
                const acknowledgedTime = alert.acknowledged_at ? new Date(alert.acknowledged_at) : null;
                const acknowledgedTimeStr = acknowledgedTime ? this.formatDateTime(acknowledgedTime) : null;
                
                // Calculate duration
                let durationStr = '';
                if (triggeredTime) {
                    const duration = Math.floor((new Date() - triggeredTime) / 1000);
                    durationStr = this.formatDuration(duration);
                }
                
                // Format details
                let detailsHtml = '';
                if (alert.details && Object.keys(alert.details).length > 0) {
                    detailsHtml = '<div class="alert-details">';
                    Object.entries(alert.details).forEach(([key, value]) => {
                        detailsHtml += `<div><strong>${key}:</strong> ${value}</div>`;
                    });
                    detailsHtml += '</div>';
                }
                
                // Create alert HTML
                alertElement.innerHTML = `
                    <div class="alert-header">
                        <span class="alert-name">${alert.name}</span>
                        <span class="alert-severity ${alert.severity}">${alert.severity.toUpperCase()}</span>
                        <span class="alert-status">${alert.status.toUpperCase()}</span>
                    </div>
                    <div class="alert-content">
                        <div class="alert-description">${alert.description}</div>
                        <div class="alert-metadata">
                            <div><strong>Category:</strong> ${alert.category}</div>
                            <div><strong>Triggered:</strong> ${triggeredTimeStr} (${durationStr} ago)</div>
                            ${acknowledgedTimeStr ? `<div><strong>Acknowledged:</strong> ${acknowledgedTimeStr} by ${alert.acknowledged_by || 'System'}</div>` : ''}
                        </div>
                        ${detailsHtml}
                        <div class="alert-actions">
                            ${alert.status === 'active' ? `<button class="btn btn-small" data-action="acknowledge" data-alert="${alert.name}">Acknowledge</button>` : ''}
                            <button class="btn btn-small" data-action="resolve" data-alert="${alert.name}">Resolve</button>
                            <button class="btn btn-small" data-action="silence" data-alert="${alert.name}" data-silenced="${alert.silenced}">
                                ${alert.silenced ? 'Unsilence' : 'Silence'}
                            </button>
                        </div>
                    </div>
                `;
                
                // Add alert to container
                container.appendChild(alertElement);
                
                // Add event listeners for alert actions
                const actionButtons = alertElement.querySelectorAll('.alert-actions button');
                actionButtons.forEach(button => {
                    button.addEventListener('click', () => {
                        const action = button.dataset.action;
                        const alertName = button.dataset.alert;
                        
                        if (action === 'acknowledge') {
                            this.acknowledgeAlert(alertName);
                        } else if (action === 'resolve') {
                            this.resolveAlert(alertName);
                        } else if (action === 'silence') {
                            const isSilenced = button.dataset.silenced === 'true';
                            this.silenceAlert(alertName, !isSilenced);
                        }
                    });
                });
            });
        },
        
        // Render alert history
        renderAlertHistory(history) {
            const tableBody = document.querySelector('#alert-history-table tbody');
            if (!tableBody) return;
            
            // Clear table
            tableBody.innerHTML = '';
            
            if (history.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="5">No alert history available</td>';
                tableBody.appendChild(row);
                return;
            }
            
            // Render each history entry
            history.forEach(entry => {
                const row = document.createElement('tr');
                
                // Format time
                const time = new Date(entry.timestamp);
                const timeStr = this.formatDateTime(time);
                
                // Format details
                let detailsStr = '';
                if (entry.details) {
                    const detailsArray = [];
                    Object.entries(entry.details).forEach(([key, value]) => {
                        if (key !== 'timestamp' && value !== null && value !== undefined) {
                            detailsArray.push(`${key}: ${value}`);
                        }
                    });
                    detailsStr = detailsArray.join(', ');
                }
                
                // Format severity
                let severityStr = '';
                if (entry.details && entry.details.severity) {
                    severityStr = `<span class="alert-severity ${entry.details.severity}">${entry.details.severity.toUpperCase()}</span>`;
                }
                
                row.innerHTML = `
                    <td>${timeStr}</td>
                    <td>${entry.alert}</td>
                    <td>${entry.action.replace('_', ' ')}</td>
                    <td>${severityStr}</td>
                    <td>${detailsStr}</td>
                `;
                
                tableBody.appendChild(row);
            });
        },
        
        // Acknowledge an alert
        acknowledgeAlert(alertName) {
            fetch(`/api/monitoring/alerts/${alertName}/acknowledge`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user: 'admin' })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.showToast(`Alert "${alertName}" acknowledged`);
                    this.loadAlerts();
                } else {
                    this.showToast(`Failed to acknowledge alert: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error acknowledging alert:', error);
                this.showToast('Error acknowledging alert', 'error');
            });
        },
        
        // Resolve an alert
        resolveAlert(alertName) {
            fetch(`/api/monitoring/alerts/${alertName}/resolve`, {
                method: 'PUT'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.showToast(`Alert "${alertName}" resolved`);
                    this.loadAlerts();
                } else {
                    this.showToast(`Failed to resolve alert: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error resolving alert:', error);
                this.showToast('Error resolving alert', 'error');
            });
        },
        
        // Silence or unsilence an alert
        silenceAlert(alertName, silence) {
            fetch(`/api/monitoring/alerts/${alertName}/silence`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ silence })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.showToast(`Alert "${alertName}" ${silence ? 'silenced' : 'unsilenced'}`);
                    this.loadAlerts();
                } else {
                    this.showToast(`Failed to ${silence ? 'silence' : 'unsilence'} alert: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error(`Error ${silence ? 'silencing' : 'unsilencing'} alert:`, error);
                this.showToast(`Error ${silence ? 'silencing' : 'unsilencing'} alert`, 'error');
            });
        },
        
        // Create a new alert
        createAlert() {
            const name = document.getElementById('alert-name').value;
            const description = document.getElementById('alert-description').value;
            const severity = document.getElementById('alert-severity').value;
            const category = document.getElementById('alert-category').value;
            
            if (!name || !description) {
                this.showToast('Alert name and description are required', 'error');
                return;
            }
            
            // Create alert
            fetch('/api/monitoring/alerts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    description,
                    severity,
                    category
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    this.showToast(`Alert "${name}" created`);
                    
                    // Reset form
                    document.getElementById('alert-name').value = '';
                    document.getElementById('alert-description').value = '';
                    
                    // Reload alerts
                    this.loadAlerts();
                } else {
                    this.showToast(`Failed to create alert: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error('Error creating alert:', error);
                this.showToast('Error creating alert', 'error');
            });
        },
        
        // Load logs
        loadLogs() {
            // Check if log level chart exists
            if (!this.charts.logLevels) {
                this.initLogLevelChart();
            }
            
            // TODO: Implement actual log loading from API
            // For now, just simulate some logs
            this.simulateLogs();
        },
        
        // Initialize log level chart
        initLogLevelChart() {
            const ctx = document.getElementById('log-levels-chart').getContext('2d');
            this.charts.logLevels = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    datasets: [{
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: [
                            'rgba(156, 204, 101, 0.7)',
                            'rgba(100, 181, 246, 0.7)',
                            'rgba(255, 183, 77, 0.7)',
                            'rgba(229, 115, 115, 0.7)',
                            'rgba(240, 98, 146, 0.7)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right'
                        },
                        title: {
                            display: true,
                            text: 'Log Levels'
                        }
                    }
                }
            });
        },
        
        // Simulate logs for demonstration
        simulateLogs() {
            const container = document.getElementById('logs-container');
            if (!container) return;
            
            // Placeholder logs
            const simulatedLogs = [
                { timestamp: '2025-05-14T12:00:00', level: 'INFO', component: 'system', message: 'System started' },
                { timestamp: '2025-05-14T12:00:01', level: 'INFO', component: 'agent', message: 'Agent initialization complete' },
                { timestamp: '2025-05-14T12:00:10', level: 'INFO', component: 'api', message: 'API server listening on port 8001' },
                { timestamp: '2025-05-14T12:01:05', level: 'DEBUG', component: 'agent', message: 'Processing task #1234' },
                { timestamp: '2025-05-14T12:01:23', level: 'WARNING', component: 'agent', message: 'Task processing taking longer than expected' },
                { timestamp: '2025-05-14T12:02:15', level: 'ERROR', component: 'api', message: 'Failed to connect to external service: Connection timeout' },
                { timestamp: '2025-05-14T12:03:42', level: 'INFO', component: 'scheduler', message: 'Scheduled task executed successfully' },
                { timestamp: '2025-05-14T12:04:30', level: 'DEBUG', component: 'memory', message: 'Memory cache optimized' },
                { timestamp: '2025-05-14T12:05:12', level: 'INFO', component: 'agent', message: 'Task #1234 completed successfully' },
                { timestamp: '2025-05-14T12:07:03', level: 'CRITICAL', component: 'system', message: 'Out of disk space on /var/log' },
                { timestamp: '2025-05-14T12:07:45', level: 'WARNING', component: 'scheduler', message: 'Task #4567 delayed due to resource constraints' },
                { timestamp: '2025-05-14T12:08:20', level: 'INFO', component: 'api', message: 'Received request for /api/tasks' },
                { timestamp: '2025-05-14T12:09:11', level: 'DEBUG', component: 'agent', message: 'Loaded model from cache' },
                { timestamp: '2025-05-14T12:10:30', level: 'ERROR', component: 'scheduler', message: 'Failed to execute scheduled task: Task not found' },
                { timestamp: '2025-05-14T12:11:55', level: 'INFO', component: 'system', message: 'Disk space cleanup completed' }
            ];
            
            // Clear container
            container.innerHTML = '';
            
            // Add log entries
            simulatedLogs.forEach(log => {
                const logEntry = document.createElement('div');
                logEntry.className = `log-entry log-${log.level}`;
                logEntry.innerHTML = `
                    <span class="log-timestamp">${log.timestamp}</span>
                    <span class="log-level">[${log.level}]</span>
                    <span class="log-component">${log.component}:</span>
                    <span class="log-message">${log.message}</span>
                `;
                container.appendChild(logEntry);
            });
            
            // Update log level counts
            const levelCounts = {
                'DEBUG': 0,
                'INFO': 0,
                'WARNING': 0,
                'ERROR': 0,
                'CRITICAL': 0
            };
            
            simulatedLogs.forEach(log => {
                levelCounts[log.level]++;
            });
            
            // Update chart
            this.charts.logLevels.data.datasets[0].data = [
                levelCounts.DEBUG,
                levelCounts.INFO,
                levelCounts.WARNING,
                levelCounts.ERROR,
                levelCounts.CRITICAL
            ];
            this.charts.logLevels.update();
            
            // Update log stats
            const logStats = document.getElementById('log-stats');
            if (logStats) {
                logStats.innerHTML = '';
                
                Object.entries(levelCounts).forEach(([level, count]) => {
                    const item = document.createElement('div');
                    item.innerHTML = `
                        <span class="log-stat-label">${level}:</span>
                        <span class="log-stat-value">${count}</span>
                    `;
                    logStats.appendChild(item);
                });
                
                // Add total
                const totalItem = document.createElement('div');
                totalItem.innerHTML = `
                    <span class="log-stat-label">Total:</span>
                    <span class="log-stat-value">${simulatedLogs.length}</span>
                `;
                logStats.appendChild(totalItem);
            }
            
            // Populate component filter
            const componentSelect = document.getElementById('log-component');
            if (componentSelect) {
                // Clear options except first
                while (componentSelect.options.length > 1) {
                    componentSelect.remove(1);
                }
                
                // Get unique components
                const components = [...new Set(simulatedLogs.map(log => log.component))];
                
                // Add options
                components.forEach(component => {
                    const option = document.createElement('option');
                    option.value = component;
                    option.textContent = component;
                    componentSelect.appendChild(option);
                });
            }
        },
        
        // Filter logs based on selected filters
        filterLogs() {
            const level = document.getElementById('log-level').value;
            const component = document.getElementById('log-component').value;
            const search = document.getElementById('log-search').value.toLowerCase();
            
            const logEntries = document.querySelectorAll('.log-entry');
            
            logEntries.forEach(entry => {
                let visible = true;
                
                // Filter by level
                if (level && !entry.classList.contains(`log-${level}`)) {
                    visible = false;
                }
                
                // Filter by component
                if (component && !entry.querySelector('.log-component').textContent.includes(component)) {
                    visible = false;
                }
                
                // Filter by search
                if (search && !entry.textContent.toLowerCase().includes(search)) {
                    visible = false;
                }
                
                // Show or hide entry
                entry.style.display = visible ? '' : 'none';
            });
        },
        
        // Clear log filters
        clearLogFilters() {
            document.getElementById('log-level').selectedIndex = 0;
            document.getElementById('log-component').selectedIndex = 0;
            document.getElementById('log-search').value = '';
            
            // Show all logs
            document.querySelectorAll('.log-entry').forEach(entry => {
                entry.style.display = '';
            });
        },
        
        // Format bytes to human-readable string
        formatBytes(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';
            
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
            
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        },
        
        // Format time for charts
        formatTime(date) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        },
        
        // Format date and time
        formatDateTime(date) {
            return date.toLocaleString([], {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        },
        
        // Format duration in seconds to a human-readable string
        formatDuration(seconds) {
            if (seconds < 60) {
                return `${seconds} seconds`;
            } else if (seconds < 3600) {
                const minutes = Math.floor(seconds / 60);
                return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
            } else if (seconds < 86400) {
                const hours = Math.floor(seconds / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                return `${hours} hour${hours !== 1 ? 's' : ''} ${minutes} minute${minutes !== 1 ? 's' : ''}`;
            } else {
                const days = Math.floor(seconds / 86400);
                const hours = Math.floor((seconds % 86400) / 3600);
                return `${days} day${days !== 1 ? 's' : ''} ${hours} hour${hours !== 1 ? 's' : ''}`;
            }
        },
        
        // Show a toast notification
        showToast(message, type = 'success') {
            // Check if toast container exists
            let toastContainer = document.querySelector('.toast-container');
            
            // Create container if it doesn't exist
            if (!toastContainer) {
                toastContainer = document.createElement('div');
                toastContainer.className = 'toast-container';
                document.body.appendChild(toastContainer);
            }
            
            // Create toast
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            
            // Add toast to container
            toastContainer.appendChild(toast);
            
            // Animate toast
            setTimeout(() => {
                toast.classList.add('show');
            }, 10);
            
            // Remove toast after delay
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    toast.remove();
                }, 300);
            }, 3000);
        }
    };
    
    // Initialize the dashboard
    MonitoringDashboard.init();
});