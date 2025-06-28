/**
 * Chart management for Pi Air Monitor
 */

class ChartManager {
    constructor() {
        this.charts = {};
        this.initializeCharts();
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
        const config = window.AppConfig;
        
        this.charts.temperature = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Temperature (°C)',
                    data: [],
                    borderColor: config.CHART_COLORS.primary,
                    backgroundColor: `${config.CHART_COLORS.primary}33`,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: window.Utils.isMobile() ? 0 : 3,
                    pointHoverRadius: window.Utils.isMobile() ? 4 : 6
                }]
            },
            options: {
                ...config.CHART_DEFAULTS,
                scales: {
                    ...config.CHART_DEFAULTS.scales,
                    y: {
                        ...config.CHART_DEFAULTS.scales.y,
                        beginAtZero: false,
                        suggestedMin: 30,
                        suggestedMax: 80,
                        title: {
                            display: true,
                            text: 'Temperature (°C)',
                            font: {
                                size: window.Utils.isMobile() ? 10 : 12
                            }
                        }
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
        const config = window.AppConfig;
        
        this.charts.systemMetrics = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU Usage (%)',
                        data: [],
                        borderColor: config.CHART_COLORS.primary,
                        backgroundColor: `${config.CHART_COLORS.primary}33`,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y-percentage',
                        pointRadius: 0
                    },
                    {
                        label: 'Memory Usage (%)',
                        data: [],
                        borderColor: config.CHART_COLORS.secondary,
                        backgroundColor: `${config.CHART_COLORS.secondary}33`,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y-percentage',
                        pointRadius: 0
                    },
                    {
                        label: 'Disk Usage (%)',
                        data: [],
                        borderColor: config.CHART_COLORS.tertiary,
                        backgroundColor: `${config.CHART_COLORS.tertiary}33`,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y-percentage',
                        pointRadius: 0
                    },
                    {
                        label: 'CPU Temperature (°C)',
                        data: [],
                        borderColor: config.CHART_COLORS.danger,
                        backgroundColor: `${config.CHART_COLORS.danger}33`,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y-temperature',
                        pointRadius: 0
                    }
                ]
            },
            options: {
                ...config.CHART_DEFAULTS,
                scales: {
                    ...config.CHART_DEFAULTS.scales,
                    'y-percentage': {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        min: 0,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Usage (%)',
                            font: {
                                size: window.Utils.isMobile() ? 10 : 12
                            }
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            font: {
                                size: window.Utils.isMobile() ? 9 : 11
                            }
                        }
                    },
                    'y-temperature': {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 20,
                        max: 90,
                        title: {
                            display: true,
                            text: 'Temperature (°C)',
                            font: {
                                size: window.Utils.isMobile() ? 10 : 12
                            }
                        },
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            font: {
                                size: window.Utils.isMobile() ? 9 : 11
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize particles chart
     */
    initializeParticlesChart() {
        const ctx = document.getElementById('particlesChart').getContext('2d');
        const config = window.AppConfig;
        const isMobile = window.Utils.isMobile();
        
        this.charts.particles = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'PM2.5',
                        data: [],
                        borderColor: config.CHART_COLORS.danger,
                        backgroundColor: `${config.CHART_COLORS.danger}1A`,
                        borderWidth: isMobile ? 2 : 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: isMobile ? 2 : 3,
                        pointHoverRadius: isMobile ? 4 : 6
                    },
                    {
                        label: 'PM10',
                        data: [],
                        borderColor: config.CHART_COLORS.warning,
                        backgroundColor: `${config.CHART_COLORS.warning}1A`,
                        borderWidth: isMobile ? 2 : 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: isMobile ? 2 : 3,
                        pointHoverRadius: isMobile ? 4 : 6
                    },
                    {
                        label: 'PM1.0',
                        data: [],
                        borderColor: config.CHART_COLORS.info,
                        backgroundColor: `${config.CHART_COLORS.info}1A`,
                        borderWidth: isMobile ? 2 : 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: isMobile ? 2 : 3,
                        pointHoverRadius: isMobile ? 4 : 6
                    }
                ]
            },
            options: {
                ...config.CHART_DEFAULTS,
                scales: {
                    ...config.CHART_DEFAULTS.scales,
                    x: {
                        ...config.CHART_DEFAULTS.scales.x,
                        ticks: {
                            ...config.CHART_DEFAULTS.scales.x.ticks,
                            maxTicksLimit: isMobile ? 6 : 12
                        }
                    },
                    y: {
                        ...config.CHART_DEFAULTS.scales.y,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Concentration (μg/m³)',
                            font: {
                                size: isMobile ? 10 : 12
                            }
                        }
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
        const config = window.AppConfig;
        const isMobile = window.Utils.isMobile();
        
        this.charts.aqi = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Air Quality Index',
                    data: [],
                    borderColor: config.CHART_COLORS.primary,
                    backgroundColor: 'rgba(197, 26, 74, 0.1)',
                    borderWidth: isMobile ? 2 : 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: isMobile ? 2 : 3,
                    pointHoverRadius: isMobile ? 4 : 6
                }]
            },
            options: {
                ...config.CHART_DEFAULTS,
                scales: {
                    ...config.CHART_DEFAULTS.scales,
                    x: {
                        ...config.CHART_DEFAULTS.scales.x,
                        ticks: {
                            ...config.CHART_DEFAULTS.scales.x.ticks,
                            maxTicksLimit: isMobile ? 6 : 12
                        }
                    },
                    y: {
                        ...config.CHART_DEFAULTS.scales.y,
                        beginAtZero: true,
                        suggestedMax: 200,
                        title: {
                            display: true,
                            text: 'AQI Value',
                            font: {
                                size: isMobile ? 10 : 12
                            }
                        },
                        ticks: {
                            ...config.CHART_DEFAULTS.scales.y.ticks,
                            callback: function(value) {
                                const labels = {
                                    0: 'Good',
                                    50: 'Moderate',
                                    100: 'Unhealthy for Sensitive',
                                    150: 'Unhealthy',
                                    200: 'Very Unhealthy',
                                    300: 'Hazardous'
                                };
                                return labels[value] || value;
                            }
                        },
                        grid: {
                            color: function(context) {
                                const value = context.tick.value;
                                const levels = window.AppConfig.AQI_LEVELS;
                                
                                if (value === levels.good.max) return levels.good.color + '40';
                                if (value === levels.moderate.max) return levels.moderate.color + '40';
                                if (value === levels.unhealthySensitive.max) return levels.unhealthySensitive.color + '40';
                                if (value === levels.unhealthy.max) return levels.unhealthy.color + '40';
                                if (value === levels.veryUnhealthy.max) return levels.veryUnhealthy.color + '40';
                                return 'rgba(0, 0, 0, 0.05)';
                            },
                            lineWidth: function(context) {
                                const value = context.tick.value;
                                if ([50, 100, 150, 200, 300].includes(value)) {
                                    return 2;
                                }
                                return 1;
                            }
                        }
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
     * Destroy all charts (for cleanup)
     */
    destroy() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }
}

// Create global chart manager instance
window.chartManager = new ChartManager();