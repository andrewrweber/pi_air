/**
 * Enhanced Chart management for Pi Air Monitor
 * Features: WHO guidelines, zoom/pan, trend analysis, data export
 */

class ChartManager {
    constructor() {
        this.charts = {};
        this.whoGuidelines = this.initializeWHOGuidelines();
        this.loadingStates = {};
        this.errorStates = {};
        this.dataCache = {};
        
        // Register Chart.js plugins
        this.registerPlugins();
        
        this.initializeCharts();
    }

    /**
     * Register Chart.js plugins
     */
    registerPlugins() {
        if (typeof Chart !== 'undefined' && window.zoomPlugin) {
            Chart.register(window.zoomPlugin);
        }
    }

    /**
     * Initialize WHO Air Quality Guidelines
     */
    initializeWHOGuidelines() {
        return {
            pm25: {
                daily: 15,      // μg/m³ 24-hour mean
                annual: 5,      // μg/m³ annual mean
                label: 'WHO PM2.5 Guidelines',
                color: 'rgba(255, 165, 0, 0.7)',
                dailyLabel: 'WHO Daily (15 μg/m³)',
                annualLabel: 'WHO Annual (5 μg/m³)'
            },
            pm10: {
                daily: 45,      // μg/m³ 24-hour mean
                annual: 15,     // μg/m³ annual mean
                label: 'WHO PM10 Guidelines',
                color: 'rgba(255, 140, 0, 0.7)',
                dailyLabel: 'WHO Daily (45 μg/m³)',
                annualLabel: 'WHO Annual (15 μg/m³)'
            }
        };
    }

    /**
     * Initialize all charts
     */
    initializeCharts() {
        this.initializeTemperatureChart();
        this.initializeSystemMetricsChart();
        this.initializeParticlesChart();
        this.initializeAQIChart();
    }

    /**
     * Initialize temperature chart
     */
    initializeTemperatureChart() {
        const ctx = document.getElementById('temperatureChart').getContext('2d');
        
        this.charts.temperature = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Temperature (°C)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Temperature (°C)'
                        },
                        suggestedMin: 30,
                        suggestedMax: 80
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    /**
     * Initialize system metrics chart
     */
    initializeSystemMetricsChart() {
        const ctx = document.getElementById('systemMetricsChart').getContext('2d');
        
        this.charts.systemMetrics = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU Usage (%)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y-percentage',
                        spanGaps: true
                    },
                    {
                        label: 'Memory Usage (%)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y-percentage',
                        spanGaps: true
                    },
                    {
                        label: 'Disk Usage (%)',
                        data: [],
                        borderColor: 'rgb(255, 205, 86)',
                        backgroundColor: 'rgba(255, 205, 86, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y-percentage',
                        spanGaps: true
                    },
                    {
                        label: 'CPU Temperature (°C)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y-temperature',
                        spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    'y-percentage': {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Usage (%)'
                        },
                        min: 0,
                        max: 100
                    },
                    'y-temperature': {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Temperature (°C)'
                        },
                        min: 30,
                        max: 80,
                        grid: {
                            drawOnChartArea: false
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
    }

    /**
     * Initialize particles chart with WHO guidelines and advanced features
     */
    initializeParticlesChart() {
        const ctx = document.getElementById('particlesChart').getContext('2d');
        const isMobile = window.Utils.isMobile();
        
        this.charts.particles = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'PM2.5 (μg/m³)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        spanGaps: true,
                        pointRadius: 0,
                        pointHoverRadius: 6,
                        borderWidth: 2
                    },
                    {
                        label: 'PM10 (μg/m³)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        spanGaps: true,
                        pointRadius: 0,
                        pointHoverRadius: 6,
                        borderWidth: 2
                    },
                    {
                        label: 'PM1.0 (μg/m³)',
                        data: [],
                        borderColor: 'rgb(255, 205, 86)',
                        backgroundColor: 'rgba(255, 205, 86, 0.1)',
                        tension: 0.1,
                        spanGaps: true,
                        hidden: true,  // Hidden by default
                        pointRadius: 0,
                        pointHoverRadius: 6,
                        borderWidth: 2
                    },
                    // WHO PM2.5 Daily Guideline
                    {
                        label: this.whoGuidelines.pm25.dailyLabel,
                        data: [],
                        borderColor: this.whoGuidelines.pm25.color,
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false,
                        spanGaps: true,
                        tension: 0
                    },
                    // WHO PM10 Daily Guideline
                    {
                        label: this.whoGuidelines.pm10.dailyLabel,
                        data: [],
                        borderColor: this.whoGuidelines.pm10.color,
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false,
                        spanGaps: true,
                        tension: 0,
                        hidden: true  // Hidden by default since PM10 is secondary
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                // Enable zoom and pan
                plugins: {
                    zoom: {
                        zoom: {
                            wheel: {
                                enabled: !isMobile,
                                speed: 0.1
                            },
                            pinch: {
                                enabled: isMobile
                            },
                            mode: 'x'
                        },
                        pan: {
                            enabled: true,
                            mode: 'x',
                            onPanComplete: ({chart}) => {
                                this.updateChartAnalytics('particles');
                            }
                        },
                        limits: {
                            x: {min: 'original', max: 'original'}
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: window.innerWidth < 768 ? 8 : 15,
                            font: {
                                size: window.innerWidth < 768 ? 10 : 12
                            },
                            boxWidth: window.innerWidth < 768 ? 8 : 12,
                            filter: (legendItem, data) => {
                                // Show/hide WHO guidelines based on mobile view
                                if (isMobile && legendItem.text.includes('WHO')) {
                                    return false;
                                }
                                return true;
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            afterBody: (context) => {
                                return this.generateTooltipAnalytics(context, 'particles');
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: window.innerWidth >= 768,
                            text: 'Time',
                            font: {
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        ticks: {
                            maxTicksLimit: window.innerWidth < 768 ? 6 : 10,
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: window.innerWidth >= 768,
                            text: 'Particulate Matter (μg/m³)',
                            font: {
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        min: 0,
                        suggestedMax: 50,
                        ticks: {
                            beginAtZero: true,
                            maxTicksLimit: window.innerWidth < 768 ? 6 : 8,
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            }
                        }
                    }
                },
                // Mobile-optimized settings
                elements: {
                    point: {
                        radius: 0,  // No points to keep lines clear
                        hoverRadius: window.innerWidth < 768 ? 4 : 6
                    }
                }
            }
        });
    }

    /**
     * Initialize AQI chart
     */
    initializeAQIChart() {
        const ctx = document.getElementById('aqiChart').getContext('2d');
        
        this.charts.aqi = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Air Quality Index',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1,
                        spanGaps: true,
                        borderWidth: 3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        title: {
                            display: window.innerWidth >= 768,
                            text: 'Time',
                            font: {
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        ticks: {
                            maxTicksLimit: window.innerWidth < 768 ? 6 : 10,
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: window.innerWidth >= 768,
                            text: 'Air Quality Index',
                            font: {
                                size: window.innerWidth < 768 ? 10 : 12
                            }
                        },
                        min: 0,
                        suggestedMax: 100,
                        ticks: {
                            beginAtZero: true,
                            stepSize: 50,
                            maxTicksLimit: window.innerWidth < 768 ? 4 : 6,
                            font: {
                                size: window.innerWidth < 768 ? 9 : 11
                            },
                            callback: function(value) {
                                // Mobile-optimized AQI labels
                                if (window.innerWidth < 768) {
                                    if (value === 0) return '0';
                                    if (value === 50) return '50';
                                    if (value === 100) return '100';
                                    if (value === 150) return '150';
                                    return value;
                                } else {
                                    // Full labels for desktop
                                    if (value === 0) return '0';
                                    if (value === 50) return '50 (Good)';
                                    if (value === 100) return '100 (Moderate)';
                                    if (value === 150) return '150 (Unhealthy for Sensitive)';
                                    if (value === 200) return '200 (Unhealthy)';
                                    if (value === 300) return '300 (Very Unhealthy)';
                                    return value;
                                }
                            }
                        },
                        grid: {
                            color: function(context) {
                                const value = context.tick.value;
                                // Highlight AQI threshold lines with different colors
                                if (value === 50) return 'rgba(0, 228, 0, 0.3)';   // Good
                                if (value === 100) return 'rgba(255, 255, 0, 0.3)'; // Moderate
                                if (value === 150) return 'rgba(255, 126, 0, 0.3)'; // Unhealthy for Sensitive
                                if (value === 200) return 'rgba(255, 0, 0, 0.3)';   // Unhealthy
                                if (value === 300) return 'rgba(143, 63, 151, 0.3)'; // Very Unhealthy
                                return 'rgba(0, 0, 0, 0.05)';
                            },
                            lineWidth: function(context) {
                                const value = context.tick.value;
                                if ([50, 100, 150, 200, 300].includes(value)) {
                                    return 2;  // Thicker lines for AQI thresholds
                                }
                                return 1;
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: window.innerWidth < 768 ? 8 : 15,
                            font: {
                                size: window.innerWidth < 768 ? 10 : 12
                            },
                            boxWidth: window.innerWidth < 768 ? 8 : 12
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 0,  // No points to keep lines clear
                        hoverRadius: window.innerWidth < 768 ? 4 : 6
                    }
                }
            }
        });
    }

    /**
     * Get a specific chart
     * @param {string} chartName - Name of the chart
     * @returns {Chart} Chart instance
     */
    getChart(chartName) {
        return this.charts[chartName];
    }

    /**
     * Update chart data
     * @param {string} chartName - Name of the chart
     * @param {Array} labels - Chart labels
     * @param {Array|Object} data - Chart data
     * @param {string} updateMode - Update animation mode
     */
    updateChart(chartName, labels, data, updateMode = 'none') {
        const chart = this.charts[chartName];
        if (!chart) return;

        chart.data.labels = labels;
        
        if (Array.isArray(data)) {
            // Single dataset
            chart.data.datasets[0].data = data;
        } else {
            // Multiple datasets
            Object.keys(data).forEach((key, index) => {
                if (chart.data.datasets[index]) {
                    chart.data.datasets[index].data = data[key];
                }
            });
        }
        
        chart.update(updateMode);
    }

    /**
     * Toggle dataset visibility
     * @param {string} chartName - Name of the chart
     * @param {number} datasetIndex - Index of the dataset
     */
    toggleDataset(chartName, datasetIndex) {
        const chart = this.charts[chartName];
        if (!chart) return;

        const dataset = chart.data.datasets[datasetIndex];
        if (dataset) {
            dataset.hidden = !dataset.hidden;
            chart.update();
        }
    }

    /**
     * Update chart with WHO guidelines
     * @param {string} chartName - Name of the chart
     * @param {Array} labels - Chart labels
     * @param {Array|Object} data - Chart data
     * @param {string} updateMode - Update animation mode
     */
    updateChartWithGuidelines(chartName, labels, data, updateMode = 'none') {
        const chart = this.charts[chartName];
        if (!chart) return;

        // Update main data
        this.updateChart(chartName, labels, data, updateMode);

        // Update WHO guideline data if applicable
        if (chartName === 'particles') {
            const pm25GuidelineIndex = 3; // WHO PM2.5 Daily guideline dataset
            const pm10GuidelineIndex = 4; // WHO PM10 Daily guideline dataset
            
            // Fill WHO guideline arrays with constant values
            const pm25GuidelineData = new Array(labels.length).fill(this.whoGuidelines.pm25.daily);
            const pm10GuidelineData = new Array(labels.length).fill(this.whoGuidelines.pm10.daily);
            
            if (chart.data.datasets[pm25GuidelineIndex]) {
                chart.data.datasets[pm25GuidelineIndex].data = pm25GuidelineData;
            }
            if (chart.data.datasets[pm10GuidelineIndex]) {
                chart.data.datasets[pm10GuidelineIndex].data = pm10GuidelineData;
            }
        }

        chart.update(updateMode);
    }

    /**
     * Generate tooltip analytics for enhanced information
     * @param {Array} context - Chart.js tooltip context
     * @param {string} chartType - Type of chart
     * @returns {Array} Additional tooltip lines
     */
    generateTooltipAnalytics(context, chartType) {
        if (!context || context.length === 0) return [];
        
        const dataIndex = context[0].dataIndex;
        const chart = context[0].chart;
        const analytics = [];

        if (chartType === 'particles') {
            const pm25Data = chart.data.datasets[0]?.data;
            const pm10Data = chart.data.datasets[1]?.data;
            
            if (pm25Data && pm25Data[dataIndex] !== undefined) {
                const pm25Value = pm25Data[dataIndex];
                const who25Daily = this.whoGuidelines.pm25.daily;
                const who25Annual = this.whoGuidelines.pm25.annual;
                
                if (pm25Value > who25Daily) {
                    analytics.push(`⚠️ Above WHO daily guideline (${who25Daily} μg/m³)`);
                } else if (pm25Value > who25Annual) {
                    analytics.push(`⚠️ Above WHO annual guideline (${who25Annual} μg/m³)`);
                } else {
                    analytics.push(`✓ Within WHO guidelines`);
                }
            }

            // Add trend information if available
            const trend = this.calculateTrend(chart.data.datasets[0]?.data, dataIndex);
            if (trend) {
                analytics.push(`Trend: ${trend}`);
            }
        }

        return analytics;
    }

    /**
     * Calculate trend for data point
     * @param {Array} data - Data array
     * @param {number} index - Current index
     * @returns {string} Trend description
     */
    calculateTrend(data, index) {
        if (!data || index < 3) return null;
        
        const current = data[index];
        const prev1 = data[index - 1];
        const prev2 = data[index - 2];
        const prev3 = data[index - 3];
        
        if ([current, prev1, prev2, prev3].some(v => v === null || v === undefined)) {
            return null;
        }

        const shortTrend = current - prev1;
        const mediumTrend = (current + prev1) / 2 - (prev2 + prev3) / 2;
        
        if (Math.abs(shortTrend) < 1) {
            return 'Stable';
        } else if (shortTrend > 0 && mediumTrend > 0) {
            return 'Rising ↗';
        } else if (shortTrend < 0 && mediumTrend < 0) {
            return 'Falling ↘';
        } else {
            return shortTrend > 0 ? 'Rising ↗' : 'Falling ↘';
        }
    }

    /**
     * Update chart analytics display
     * @param {string} chartName - Name of the chart
     */
    updateChartAnalytics(chartName) {
        const chart = this.charts[chartName];
        if (!chart) return;

        // This would be called when pan/zoom completes
        // Can be used to show visible data statistics
        console.log(`Updated analytics for ${chartName}`);
    }

    /**
     * Export chart data
     * @param {string} chartName - Name of the chart
     * @param {string} format - Export format ('csv' or 'json')
     * @returns {string} Exported data
     */
    exportChartData(chartName, format = 'csv') {
        const chart = this.charts[chartName];
        if (!chart) return null;

        const data = {
            labels: chart.data.labels,
            datasets: chart.data.datasets.map(dataset => ({
                label: dataset.label,
                data: dataset.data
            }))
        };

        if (format === 'json') {
            return JSON.stringify(data, null, 2);
        } else if (format === 'csv') {
            return this.convertToCSV(data);
        }

        return null;
    }

    /**
     * Convert chart data to CSV format
     * @param {Object} data - Chart data object
     * @returns {string} CSV string
     */
    convertToCSV(data) {
        if (!data.labels || !data.datasets) return '';

        const headers = ['Time', ...data.datasets.map(d => d.label)];
        const rows = data.labels.map((label, index) => {
            const values = data.datasets.map(dataset => {
                const value = dataset.data[index];
                return value !== null && value !== undefined ? value : '';
            });
            return [label, ...values];
        });

        return [headers, ...rows]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');
    }

    /**
     * Download chart data as file
     * @param {string} chartName - Name of the chart
     * @param {string} format - File format ('csv' or 'json')
     */
    downloadChartData(chartName, format = 'csv') {
        const data = this.exportChartData(chartName, format);
        if (!data) return;

        const blob = new Blob([data], { 
            type: format === 'json' ? 'application/json' : 'text/csv' 
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        
        link.href = url;
        link.download = `pi-air-${chartName}-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    /**
     * Reset chart zoom
     * @param {string} chartName - Name of the chart
     */
    resetZoom(chartName) {
        const chart = this.charts[chartName];
        if (chart && chart.resetZoom) {
            chart.resetZoom();
        }
    }

    /**
     * Show loading state for chart
     * @param {string} chartName - Name of the chart
     */
    showLoading(chartName) {
        this.loadingStates[chartName] = true;
        // You could add visual loading indicators here
    }

    /**
     * Hide loading state for chart
     * @param {string} chartName - Name of the chart
     */
    hideLoading(chartName) {
        this.loadingStates[chartName] = false;
    }

    /**
     * Show error state for chart
     * @param {string} chartName - Name of the chart
     * @param {string} message - Error message
     */
    showError(chartName, message) {
        this.errorStates[chartName] = message;
        // You could add visual error indicators here
    }

    /**
     * Clear error state for chart
     * @param {string} chartName - Name of the chart
     */
    clearError(chartName) {
        delete this.errorStates[chartName];
    }

    /**
     * Destroy all charts (for cleanup)
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
        this.loadingStates = {};
        this.errorStates = {};
        this.dataCache = {};
    }
}

// Create global chart manager instance
window.chartManager = new ChartManager();