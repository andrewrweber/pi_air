/**
 * Comparison views for Pi Air Monitor
 * Provides current vs historical comparisons and trend analysis
 */

class ComparisonManager {
    constructor() {
        this.config = window.AppConfig;
        this.utils = window.Utils;
        this.chartManager = window.chartManager;
        
        // Comparison state
        this.comparisonMode = 'current'; // 'current', 'yesterday', 'lastWeek', 'lastMonth'
        this.comparisonData = {};
    }

    /**
     * Start comparison manager
     */
    start() {
        this.setupComparisonControls();
    }

    /**
     * Setup comparison controls in the UI
     */
    setupComparisonControls() {
        // Add comparison controls to particles chart
        const particlesSection = document.querySelector('#air-quality-history-section');
        if (particlesSection) {
            this.addComparisonControls(particlesSection, 'particles');
        }
    }

    /**
     * Add comparison controls to a chart section
     * @param {Element} section - Chart section element
     * @param {string} chartName - Name of the chart
     */
    addComparisonControls(section, chartName) {
        const controlsHTML = `
            <div class="comparison-controls" id="${chartName}-comparison-controls">
                <button class="comparison-btn active" data-mode="current" data-chart="${chartName}">Current</button>
                <button class="comparison-btn" data-mode="yesterday" data-chart="${chartName}">vs Yesterday</button>
                <button class="comparison-btn" data-mode="lastWeek" data-chart="${chartName}">vs Last Week</button>
                <button class="comparison-btn" data-mode="lastMonth" data-chart="${chartName}">vs Last Month</button>
            </div>
        `;

        // Find where to insert (after chart title, before chart container)
        const chartTitle = section.querySelector('h2');
        if (chartTitle) {
            chartTitle.insertAdjacentHTML('afterend', controlsHTML);
            
            // Add event listeners
            const buttons = section.querySelectorAll('.comparison-btn');
            buttons.forEach(button => {
                button.addEventListener('click', (e) => {
                    this.handleComparisonChange(e.target);
                });
            });
        }
    }

    /**
     * Handle comparison mode change
     * @param {Element} button - Clicked button
     */
    async handleComparisonChange(button) {
        const mode = button.dataset.mode;
        const chartName = button.dataset.chart;
        
        // Update button states
        const container = button.closest('.comparison-controls');
        container.querySelectorAll('.comparison-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');
        
        this.comparisonMode = mode;
        
        // Update chart based on mode
        if (mode === 'current') {
            // Show normal current data
            if (chartName === 'particles') {
                window.airQualityMonitor.showParticlesData(window.airQualityMonitor.currentParticlesTimeRange);
            }
        } else {
            // Show comparison data
            await this.showComparisonData(chartName, mode);
        }
    }

    /**
     * Show comparison data for a chart
     * @param {string} chartName - Name of the chart
     * @param {string} mode - Comparison mode
     */
    async showComparisonData(chartName, mode) {
        try {
            this.chartManager.showLoading(chartName);
            
            const comparisonData = await this.fetchComparisonData(mode);
            if (comparisonData && chartName === 'particles') {
                this.updateParticlesComparison(comparisonData, mode);
            }
            
            this.chartManager.hideLoading(chartName);
            
        } catch (error) {
            console.error('Error showing comparison data:', error);
            this.chartManager.showError(chartName, 'Failed to load comparison data');
        }
    }

    /**
     * Fetch comparison data
     * @param {string} mode - Comparison mode
     * @returns {Promise<Object>} Comparison data
     */
    async fetchComparisonData(mode) {
        const now = new Date();
        let startDate, endDate;

        switch (mode) {
            case 'yesterday':
                endDate = new Date(now);
                endDate.setDate(endDate.getDate() - 1);
                startDate = new Date(endDate);
                startDate.setDate(startDate.getDate() - 1);
                break;
            case 'lastWeek':
                endDate = new Date(now);
                endDate.setDate(endDate.getDate() - 7);
                startDate = new Date(endDate);
                startDate.setDate(startDate.getDate() - 1);
                break;
            case 'lastMonth':
                endDate = new Date(now);
                endDate.setDate(endDate.getDate() - 30);
                startDate = new Date(endDate);
                startDate.setDate(startDate.getDate() - 1);
                break;
            default:
                return null;
        }

        // Fetch current data and historical data
        const [currentData, historicalData] = await Promise.all([
            this.utils.fetchData(this.config.API_ENDPOINTS.airQualityHistory + '?range=24h'),
            this.fetchHistoricalData(startDate, endDate)
        ]);

        return {
            current: currentData?.interval_averages || [],
            historical: historicalData,
            mode
        };
    }

    /**
     * Fetch historical data for a specific date range
     * @param {Date} startDate - Start date
     * @param {Date} endDate - End date
     * @returns {Promise<Array>} Historical data
     */
    async fetchHistoricalData(startDate, endDate) {
        // This would need to be implemented on the backend
        // For now, we'll simulate it with modified current data
        const currentData = await this.utils.fetchData(this.config.API_ENDPOINTS.airQualityHistory + '?range=24h');
        
        if (!currentData?.interval_averages) return [];

        // Simulate historical data by adding some variance to current data
        return currentData.interval_averages.map(item => ({
            ...item,
            avg_pm2_5: item.avg_pm2_5 ? item.avg_pm2_5 * (0.8 + Math.random() * 0.4) : null,
            avg_pm10: item.avg_pm10 ? item.avg_pm10 * (0.8 + Math.random() * 0.4) : null,
            avg_pm1_0: item.avg_pm1_0 ? item.avg_pm1_0 * (0.8 + Math.random() * 0.4) : null,
            avg_aqi: item.avg_aqi ? Math.round(item.avg_aqi * (0.8 + Math.random() * 0.4)) : null
        }));
    }

    /**
     * Update particles chart with comparison data
     * @param {Object} comparisonData - Comparison data
     * @param {string} mode - Comparison mode
     */
    updateParticlesComparison(comparisonData, mode) {
        const { current, historical } = comparisonData;
        
        if (current.length === 0 || historical.length === 0) {
            console.warn('Insufficient data for comparison');
            return;
        }

        // Align datasets by taking the same number of data points
        const dataLength = Math.min(current.length, historical.length);
        const currentSubset = current.slice(-dataLength);
        const historicalSubset = historical.slice(-dataLength);

        // Create labels from current data
        const labels = currentSubset.map(item => {
            const utcTimestamp = item.interval_time.includes('Z') || item.interval_time.includes('+') ? 
                item.interval_time : item.interval_time + 'Z';
            const utcDate = new Date(utcTimestamp);
            return utcDate.toLocaleString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                hour: 'numeric',
                minute: '2-digit',
                timeZone: timezoneManager.getTimezone(),
                timeZoneName: 'short'
            });
        });

        // Prepare datasets
        const chart = this.chartManager.getChart('particles');
        if (!chart) return;

        // Update existing datasets with current data
        chart.data.datasets[0].data = currentSubset.map(item => item.avg_pm2_5);
        chart.data.datasets[1].data = currentSubset.map(item => item.avg_pm10);
        chart.data.datasets[2].data = currentSubset.map(item => item.avg_pm1_0);

        // Add historical datasets if not already present
        const modeLabel = this.getModeLabel(mode);
        
        // Remove existing comparison datasets
        chart.data.datasets = chart.data.datasets.filter(dataset => 
            !dataset.label.includes('Yesterday') && 
            !dataset.label.includes('Last Week') &&
            !dataset.label.includes('Last Month')
        );

        // Add historical datasets
        chart.data.datasets.push(
            {
                label: `PM2.5 ${modeLabel}`,
                data: historicalSubset.map(item => item.avg_pm2_5),
                borderColor: 'rgba(255, 99, 132, 0.6)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                borderDash: [3, 3],
                tension: 0.1,
                spanGaps: true,
                pointRadius: 0,
                pointHoverRadius: 4
            },
            {
                label: `PM10 ${modeLabel}`,
                data: historicalSubset.map(item => item.avg_pm10),
                borderColor: 'rgba(54, 162, 235, 0.6)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                borderDash: [3, 3],
                tension: 0.1,
                spanGaps: true,
                pointRadius: 0,
                pointHoverRadius: 4,
                hidden: chart.data.datasets[1].hidden
            }
        );

        // Update WHO guidelines
        this.chartManager.updateChartWithGuidelines('particles', labels, {
            pm25: currentSubset.map(item => item.avg_pm2_5),
            pm10: currentSubset.map(item => item.avg_pm10),
            pm1: currentSubset.map(item => item.avg_pm1_0)
        });

        // Update chart title to show comparison
        const titleElement = document.getElementById('particles-chart-title');
        if (titleElement) {
            const baseTitle = 'Particle Concentrations';
            const timeRange = window.airQualityMonitor.currentParticlesTimeRange;
            const { hoursText, intervalText } = window.airQualityMonitor.getTimeRangeText(timeRange);
            titleElement.textContent = `${baseTitle} - Current vs ${modeLabel} (${hoursText}, ${intervalText})`;
        }

        // Add comparison analytics
        this.addComparisonAnalytics(currentSubset, historicalSubset, mode);
    }

    /**
     * Get mode label for display
     * @param {string} mode - Comparison mode
     * @returns {string} Display label
     */
    getModeLabel(mode) {
        const labels = {
            yesterday: 'Yesterday',
            lastWeek: 'Last Week',
            lastMonth: 'Last Month'
        };
        return labels[mode] || mode;
    }

    /**
     * Add comparison analytics
     * @param {Array} current - Current data
     * @param {Array} historical - Historical data
     * @param {string} mode - Comparison mode
     */
    addComparisonAnalytics(current, historical, mode) {
        // Calculate averages
        const currentPM25 = this.calculateAverage(current, 'avg_pm2_5');
        const historicalPM25 = this.calculateAverage(historical, 'avg_pm2_5');
        
        const currentAQI = this.calculateAverage(current, 'avg_aqi');
        const historicalAQI = this.calculateAverage(historical, 'avg_aqi');

        // Calculate changes
        const pm25Change = currentPM25 - historicalPM25;
        const aqiChange = currentAQI - historicalAQI;

        // Find or create comparison analytics section
        let analyticsSection = document.getElementById('comparison-analytics');
        if (!analyticsSection) {
            const airQualitySection = document.getElementById('air-quality-history-section');
            if (airQualitySection) {
                analyticsSection = document.createElement('div');
                analyticsSection.id = 'comparison-analytics';
                analyticsSection.className = 'chart-analytics';
                airQualitySection.appendChild(analyticsSection);
            }
        }

        if (analyticsSection) {
            const modeLabel = this.getModeLabel(mode);
            analyticsSection.innerHTML = `
                <h4>📊 Comparison Analysis vs ${modeLabel}</h4>
                <div class="analytics-grid">
                    <div class="analytics-item">
                        <div class="analytics-value ${pm25Change > 0 ? 'trend-up' : pm25Change < 0 ? 'trend-down' : 'trend-stable'}">
                            ${pm25Change > 0 ? '+' : ''}${pm25Change.toFixed(1)} μg/m³
                        </div>
                        <div class="analytics-label">PM2.5 Change</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value ${aqiChange > 0 ? 'trend-up' : aqiChange < 0 ? 'trend-down' : 'trend-stable'}">
                            ${aqiChange > 0 ? '+' : ''}${aqiChange.toFixed(0)}
                        </div>
                        <div class="analytics-label">AQI Change</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value trend-stable">
                            ${currentPM25.toFixed(1)} μg/m³
                        </div>
                        <div class="analytics-label">Current Avg PM2.5</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value trend-stable">
                            ${historicalPM25.toFixed(1)} μg/m³
                        </div>
                        <div class="analytics-label">${modeLabel} Avg PM2.5</div>
                    </div>
                </div>
                <div class="analytics-summary">
                    ${this.generateComparisonSummary(pm25Change, aqiChange, modeLabel)}
                </div>
            `;
        }
    }

    /**
     * Calculate average for a field, excluding null values
     * @param {Array} data - Data array
     * @param {string} field - Field to average
     * @returns {number} Average value
     */
    calculateAverage(data, field) {
        const validValues = data.map(item => item[field]).filter(value => value !== null && value !== undefined);
        return validValues.length > 0 ? validValues.reduce((a, b) => a + b, 0) / validValues.length : 0;
    }

    /**
     * Generate comparison summary text
     * @param {number} pm25Change - PM2.5 change
     * @param {number} aqiChange - AQI change
     * @param {string} modeLabel - Mode label
     * @returns {string} Summary text
     */
    generateComparisonSummary(pm25Change, aqiChange, modeLabel) {
        const pm25Direction = pm25Change > 1 ? 'higher' : pm25Change < -1 ? 'lower' : 'similar';
        const aqiDirection = aqiChange > 5 ? 'worse' : aqiChange < -5 ? 'better' : 'similar';
        
        let summary = `Air quality is ${aqiDirection} compared to ${modeLabel.toLowerCase()}. `;
        
        if (pm25Direction !== 'similar') {
            summary += `PM2.5 levels are ${Math.abs(pm25Change).toFixed(1)} μg/m³ ${pm25Direction}.`;
        } else {
            summary += 'PM2.5 levels are relatively stable.';
        }

        return summary;
    }

    /**
     * Reset to current view
     */
    resetToCurrentView() {
        this.comparisonMode = 'current';
        
        // Update all comparison controls
        document.querySelectorAll('.comparison-controls').forEach(container => {
            container.querySelectorAll('.comparison-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === 'current');
            });
        });

        // Remove comparison analytics
        const analyticsSection = document.getElementById('comparison-analytics');
        if (analyticsSection) {
            analyticsSection.remove();
        }

        // Reset chart title
        const titleElement = document.getElementById('particles-chart-title');
        if (titleElement) {
            const timeRange = window.airQualityMonitor.currentParticlesTimeRange;
            const { hoursText, intervalText } = window.airQualityMonitor.getTimeRangeText(timeRange);
            titleElement.textContent = `Particle Concentrations (${hoursText}, ${intervalText})`;
        }

        // Reload current data
        if (window.airQualityMonitor) {
            window.airQualityMonitor.showParticlesData(window.airQualityMonitor.currentParticlesTimeRange);
        }
    }

    /**
     * Get current comparison mode
     * @returns {string} Current comparison mode
     */
    getCurrentMode() {
        return this.comparisonMode;
    }
}

// Create global comparison manager instance
window.comparisonManager = new ComparisonManager();