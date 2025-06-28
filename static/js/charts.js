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
     * Initialize particles chart
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
                        spanGaps: true
                    },
                    {
                        label: 'PM10 (μg/m³)',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        spanGaps: true
                    },
                    {
                        label: 'PM1.0 (μg/m³)',
                        data: [],
                        borderColor: 'rgb(255, 205, 86)',
                        backgroundColor: 'rgba(255, 205, 86, 0.1)',
                        tension: 0.1,
                        spanGaps: true,
                        hidden: true  // Hidden by default
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
                // Mobile-optimized settings
                elements: {
                    point: {
                        radius: window.innerWidth < 768 ? 2 : 3,
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
                        borderWidth: 3,
                        pointRadius: 4,
                        pointHoverRadius: 6
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
                        radius: window.innerWidth < 768 ? 2 : 4,
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