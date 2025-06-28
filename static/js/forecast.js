/**
 * Air quality forecast functionality for Pi Air Monitor
 */

class ForecastManager {
    constructor() {
        this.config = window.AppConfig;
        this.utils = window.Utils;
        this.chartManager = window.chartManager;
        
        // State
        this.currentTimeRange = '24h';
        this.cachedForecastData = {
            '12h': null,
            '24h': null,
            '48h': null,
            '72h': null
        };
        this.cachedSummaryData = null;
        this.forecastChart = null;
        
        // Cache timestamps
        this.lastForecastUpdate = null;
        this.lastSummaryUpdate = null;
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
        
        this.updateInterval = null;
    }

    /**
     * Start forecast monitoring
     */
    start() {
        // Initial updates
        this.updateForecastSummary();
        this.showForecastData('24h');
        
        // Set up periodic updates
        this.updateInterval = setInterval(() => {
            this.updateForecastSummary();
            this.refreshCurrentForecastData();
        }, this.config.UPDATE_INTERVALS.forecast || 10 * 60 * 1000); // 10 minutes
        
        // Set up event listeners
        this.setupEventListeners();
    }

    /**
     * Stop forecast monitoring
     */
    stop() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        if (this.forecastChart) {
            this.forecastChart.destroy();
            this.forecastChart = null;
        }
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Forecast time range buttons
        const buttons = ['12h', '24h', '48h', '72h'];
        buttons.forEach(range => {
            const btn = document.getElementById(`forecast-${range}-btn`);
            if (btn) {
                btn.addEventListener('click', () => this.showForecastData(range));
            }
        });
    }

    /**
     * Update forecast summary cards
     */
    async updateForecastSummary() {
        try {
            // Check cache first
            if (this.cachedSummaryData && this.lastSummaryUpdate) {
                const cacheAge = Date.now() - this.lastSummaryUpdate;
                if (cacheAge < this.cacheTimeout) {
                    this.displayForecastSummary(this.cachedSummaryData);
                    return;
                }
            }

            const data = await this.utils.fetchData('/api/air-quality-forecast-summary?days=3');
            if (!data || !data.forecast) {
                console.warn('No forecast summary data available');
                this.displayForecastError('No forecast data available');
                return;
            }

            // Cache the data
            this.cachedSummaryData = data;
            this.lastSummaryUpdate = Date.now();

            this.displayForecastSummary(data);
            this.updateForecastMeta(data);

        } catch (error) {
            console.error('Error updating forecast summary:', error);
            this.displayForecastError('Unable to load forecast data');
        }
    }

    /**
     * Display forecast summary cards
     */
    displayForecastSummary(data) {
        const container = document.getElementById('forecast-cards');
        if (!container) return;

        if (!data.forecast || data.forecast.length === 0) {
            container.innerHTML = '<div class="info-placeholder">No forecast data available</div>';
            return;
        }

        const cards = data.forecast.map(day => {
            const date = new Date(day.date);
            const dayName = this.utils.formatDayName(date);
            const aqiColor = this.utils.getAQIColorClass(day.aqi_avg);
            
            return `
                <div class="forecast-card">
                    <h4>${dayName}</h4>
                    <div class="forecast-date">${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>
                    <div class="forecast-aqi" style="color: ${this.utils.getAQIColor(day.aqi_avg)}">${day.aqi_avg || '--'}</div>
                    <div class="forecast-aqi-level ${aqiColor}">${this.utils.formatAQILevel(day.aqi_level)}</div>
                    <div class="forecast-pm25">PM2.5: ${day.pm2_5_avg ? day.pm2_5_avg.toFixed(1) : '--'} μg/m³</div>
                </div>
            `;
        }).join('');

        container.innerHTML = cards;
    }

    /**
     * Show forecast data for specified time range
     */
    async showForecastData(range) {
        try {
            // Update active button
            this.updateActiveButton(range, 'forecast');
            this.currentTimeRange = range;

            // Check cache first
            if (this.cachedForecastData[range] && this.lastForecastUpdate) {
                const cacheAge = Date.now() - this.lastForecastUpdate;
                if (cacheAge < this.cacheTimeout) {
                    this.displayForecastChart(this.cachedForecastData[range], range);
                    return;
                }
            }

            // Fetch fresh data
            const hours = this.parseTimeRangeToHours(range);
            const data = await this.utils.fetchData(`/api/air-quality-forecast?hours=${hours}`);
            
            if (!data || !data.forecast) {
                console.warn(`No forecast data available for ${range}`);
                this.displayChartError('No forecast data available');
                return;
            }

            // Cache the data
            this.cachedForecastData[range] = data;
            this.lastForecastUpdate = Date.now();

            this.displayForecastChart(data, range);

        } catch (error) {
            console.error(`Error loading forecast data for ${range}:`, error);
            this.displayChartError('Unable to load forecast data');
        }
    }

    /**
     * Display forecast chart
     */
    displayForecastChart(data, range) {
        const canvas = document.getElementById('forecastChart');
        if (!canvas) return;

        // Update chart title
        const title = document.getElementById('forecast-chart-title');
        if (title) {
            const hours = this.parseTimeRangeToHours(range);
            title.textContent = `Hourly PM2.5 Forecast (Next ${range === '72h' ? '3 days' : hours + ' hours'})`;
        }

        // Destroy existing chart
        if (this.forecastChart) {
            this.forecastChart.destroy();
        }

        if (!data.forecast || data.forecast.length === 0) {
            this.displayChartError('No forecast data available');
            return;
        }

        // Prepare chart data
        const labels = [];
        const pm25Data = [];
        const aqiData = [];

        data.forecast.forEach(point => {
            // Ensure timestamp is interpreted as UTC
            const timeStr = point.time.includes('Z') || point.time.includes('+') ? point.time : point.time + 'Z';
            const date = new Date(timeStr);
            labels.push(this.utils.formatTimeForChart(date, range));
            pm25Data.push(point.pm2_5);
            aqiData.push(point.aqi);
        });

        // Create chart
        const ctx = canvas.getContext('2d');
        this.forecastChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'PM2.5 (μg/m³)',
                        data: pm25Data,
                        borderColor: '#ff6b35',
                        backgroundColor: 'rgba(255, 107, 53, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointHoverRadius: 6,
                        yAxisID: 'y'
                    },
                    {
                        label: 'AQI',
                        data: aqiData,
                        borderColor: '#4285f4',
                        backgroundColor: 'rgba(66, 133, 244, 0.1)',
                        fill: false,
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        yAxisID: 'y1'
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
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const index = context[0].dataIndex;
                                const point = data.forecast[index];
                                const date = new Date(point.time);
                                return date.toLocaleString('en-US', {
                                    timeZone: 'America/Los_Angeles',
                                    month: 'short',
                                    day: 'numeric',
                                    hour: 'numeric',
                                    minute: '2-digit'
                                });
                            },
                            afterBody: function(context) {
                                const index = context[0].dataIndex;
                                const point = data.forecast[index];
                                return [
                                    `AQI Level: ${point.aqi_level || 'Unknown'}`,
                                    `Provider: ${point.provider}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        ticks: {
                            maxTicksLimit: range === '72h' ? 12 : 8
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'PM2.5 (μg/m³)'
                        },
                        beginAtZero: true
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'AQI'
                        },
                        beginAtZero: true,
                        max: 200,
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }

    /**
     * Refresh current forecast data
     */
    async refreshCurrentForecastData() {
        // Clear cache to force refresh
        this.cachedForecastData[this.currentTimeRange] = null;
        await this.showForecastData(this.currentTimeRange);
    }

    /**
     * Update forecast metadata
     */
    updateForecastMeta(data) {
        const locationEl = document.getElementById('forecast-location');
        const providerEl = document.getElementById('forecast-provider');
        const updatedEl = document.getElementById('forecast-updated');

        if (locationEl && data.location) {
            locationEl.textContent = data.location.name || 'Unknown Location';
        }

        if (providerEl) {
            providerEl.textContent = this.utils.formatProviderName(data.provider);
        }

        if (updatedEl && data.forecast_time) {
            const updateTime = new Date(data.forecast_time);
            updatedEl.textContent = `Updated: ${updateTime.toLocaleTimeString('en-US', {
                timeZone: 'America/Los_Angeles',
                hour: 'numeric',
                minute: '2-digit'
            })}`;
        }
    }

    /**
     * Display forecast error message
     */
    displayForecastError(message) {
        const container = document.getElementById('forecast-cards');
        if (container) {
            container.innerHTML = `<div class="info-placeholder">${message}</div>`;
        }
    }

    /**
     * Display chart error message
     */
    displayChartError(message) {
        const canvas = document.getElementById('forecastChart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#666';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(message, canvas.width / 2, canvas.height / 2);
        }
    }

    /**
     * Update active button state
     */
    updateActiveButton(range, prefix) {
        // Remove active class from all buttons
        const buttons = document.querySelectorAll(`[id^="${prefix}-"][id$="-btn"]`);
        buttons.forEach(btn => btn.classList.remove('active'));

        // Add active class to selected button
        const activeBtn = document.getElementById(`${prefix}-${range}-btn`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
    }

    /**
     * Parse time range string to hours
     */
    parseTimeRangeToHours(range) {
        const rangeMap = {
            '12h': 12,
            '24h': 24,
            '48h': 48,
            '72h': 72
        };
        return rangeMap[range] || 24;
    }

    /**
     * Clear all cached data
     */
    clearCache() {
        this.cachedForecastData = {
            '12h': null,
            '24h': null,
            '48h': null,
            '72h': null
        };
        this.cachedSummaryData = null;
        this.lastForecastUpdate = null;
        this.lastSummaryUpdate = null;
    }

    /**
     * Get current forecast data for testing
     */
    getCurrentForecastData() {
        return this.cachedForecastData[this.currentTimeRange];
    }

    /**
     * Get cached summary data for testing
     */
    getSummaryData() {
        return this.cachedSummaryData;
    }
}

// Global forecast manager instance
window.forecastManager = new ForecastManager();

// Global functions for HTML onclick handlers
window.showForecastData = function(range) {
    window.forecastManager.showForecastData(range);
};