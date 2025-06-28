/**
 * Hardware monitoring functionality for Pi Air Monitor
 */

class HardwareMonitor {
    constructor() {
        this.config = window.AppConfig;
        this.utils = window.Utils;
        this.updateInterval = null;
        this.currentTemperatureView = 'realtime';
    }

    /**
     * Start monitoring hardware stats
     */
    start() {
        // Initial update
        this.updateStats();
        this.updateSystemInfo();
        this.updateTemperatureHistory();
        this.updateSystemHistory();
        
        // Set up periodic updates
        this.updateInterval = setInterval(() => {
            this.updateStats();
        }, this.config.UPDATE_INTERVALS.stats);
        
        // Set up chart updates
        setInterval(() => {
            this.updateTemperatureHistory();
            this.updateSystemHistory();
        }, this.config.UPDATE_INTERVALS.charts);
        
        // Set up event listeners
        this.setupEventListeners();
    }

    /**
     * Stop monitoring
     */
    stop() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Update real-time stats
     */
    async updateStats() {
        const data = await this.utils.fetchData(this.config.API_ENDPOINTS.stats);
        if (!data) return;

        // Update CPU usage
        this.utils.updateElementText('cpu-usage', `${data.cpu_percent.toFixed(1)}%`);
        
        // Update memory usage
        this.utils.updateElementText('memory-usage', `${data.memory_percent.toFixed(1)}%`);
        
        // Update temperature
        if (data.cpu_temp !== null && data.cpu_temp !== undefined) {
            this.utils.updateElementText('cpu-temp', `${data.cpu_temp.toFixed(1)}°C`);
        } else {
            this.utils.updateElementText('cpu-temp', 'N/A');
        }
    }

    /**
     * Update system information
     */
    async updateSystemInfo() {
        const data = await this.utils.fetchData(this.config.API_ENDPOINTS.system);
        if (!data) return;

        // Update memory details
        const memoryDetail = `${data.memory_used} / ${data.memory_total}`;
        this.utils.updateElementText('memory-detail', memoryDetail);
        
        // Update system info
        const systemInfoHtml = `
            <div class="info-item">Hostname: ${data.hostname}</div>
            <div class="info-item">Platform: ${data.platform} ${data.platform_release}</div>
            <div class="info-item">Architecture: ${data.architecture}</div>
            <div class="info-item">CPU Cores: ${data.total_cores}</div>
            <div class="info-item">Boot Time: ${data.boot_time}</div>
        `;
        const systemInfoElement = document.getElementById('system-info');
        if (systemInfoElement) {
            systemInfoElement.innerHTML = systemInfoHtml;
        }
        
        // Update network info
        const networkInfoHtml = data.network_info.map(net => `
            <div class="info-item">${net.interface}: ${net.ip}</div>
        `).join('');
        const networkInfoElement = document.getElementById('network-info');
        if (networkInfoElement) {
            networkInfoElement.innerHTML = networkInfoHtml;
        }
        
        // Update disk info
        const diskInfoHtml = data.disk_info.map(disk => `
            <div class="disk-item">
                <div class="disk-header">${disk.device} (${disk.mountpoint})</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${disk.percentage}"></div>
                </div>
                <div class="disk-details">
                    ${disk.used} used of ${disk.total_size} (${disk.percentage})
                </div>
            </div>
        `).join('');
        const diskInfoElement = document.getElementById('disk-info');
        if (diskInfoElement) {
            diskInfoElement.innerHTML = diskInfoHtml;
        }
    }

    /**
     * Update temperature history chart
     */
    async updateTemperatureHistory() {
        const data = await this.utils.fetchData(this.config.API_ENDPOINTS.temperatureHistory);
        if (!data) return;

        const chartManager = window.chartManager;
        let labels, temperatures;

        if (this.currentTemperatureView === 'realtime' && data.real_time_history && data.real_time_history.length > 0) {
            // Format timestamps for real-time data
            labels = data.real_time_history.map(item => {
                const date = new Date(item.timestamp);
                return date.toLocaleString('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                    second: '2-digit',
                    timeZone: 'America/Los_Angeles',
                    timeZoneName: 'short'
                });
            });
            temperatures = data.real_time_history.map(item => item.temperature);
        } else if (this.currentTemperatureView === 'database' && data.database_history && data.database_history.length > 0) {
            // Format timestamps for database data
            labels = data.database_history.map(item => {
                const date = new Date(item.timestamp);
                return date.toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    timeZone: 'America/Los_Angeles',
                    timeZoneName: 'short'
                });
            });
            temperatures = data.database_history.map(item => item.cpu_temp);
        } else {
            labels = ['No data available'];
            temperatures = [];
        }

        chartManager.updateChart('temperature', labels, temperatures);
    }

    /**
     * Update system metrics history chart
     */
    async updateSystemHistory() {
        const data = await this.utils.fetchData(this.config.API_ENDPOINTS.systemHistory);
        if (!data || !data.hourly_averages || data.hourly_averages.length === 0) return;

        const chartManager = window.chartManager;
        
        // Format labels
        const labels = data.hourly_averages.map(item => {
            const date = new Date(item.hour_timestamp + 'Z');
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                timeZone: 'America/Los_Angeles',
                timeZoneName: 'short'
            });
        });

        // Extract data for each metric
        const cpuData = data.hourly_averages.map(item => item.avg_cpu_usage);
        const memoryData = data.hourly_averages.map(item => item.avg_memory_usage);
        const diskData = data.hourly_averages.map(item => item.avg_disk_usage);
        const tempData = data.hourly_averages.map(item => item.avg_cpu_temp);

        chartManager.updateChart('systemMetrics', labels, {
            cpu: cpuData,
            memory: memoryData,
            disk: diskData,
            temperature: tempData
        });
    }

    /**
     * Show temperature data view (realtime or database)
     * @param {string} view - 'realtime' or 'database'
     */
    showTemperatureData(view) {
        this.currentTemperatureView = view;
        
        // Update button states
        document.getElementById('temp-realtime-btn').classList.toggle('active', view === 'realtime');
        document.getElementById('temp-database-btn').classList.toggle('active', view === 'database');
        
        // Update chart
        this.updateTemperatureHistory();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Temperature view toggle buttons
        window.showTemperatureData = (view) => this.showTemperatureData(view);
        
        // System metrics checkboxes
        const checkboxes = [
            { id: 'show-cpu-usage', datasetIndex: 0 },
            { id: 'show-memory-usage', datasetIndex: 1 },
            { id: 'show-disk-usage', datasetIndex: 2 },
            { id: 'show-cpu-temp', datasetIndex: 3 }
        ];
        
        checkboxes.forEach(({ id, datasetIndex }) => {
            const checkbox = document.getElementById(id);
            if (checkbox) {
                checkbox.addEventListener('change', () => {
                    window.chartManager.toggleDataset('systemMetrics', datasetIndex);
                });
            }
        });
    }
}

// Create global hardware monitor instance
window.hardwareMonitor = new HardwareMonitor();