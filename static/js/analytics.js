/**
 * Analytics module for Pi Air Monitor
 * Provides trend analysis, data quality indicators, and advanced insights
 */

class AnalyticsManager {
    constructor() {
        this.config = window.AppConfig;
        this.utils = window.Utils;
        this.chartManager = window.chartManager;
        
        // Analytics state
        this.trendData = {};
        this.dataQuality = {};
        this.predictions = {};
        this.alertThresholds = {
            pm25: { good: 5, moderate: 15, unhealthy: 25 },
            pm10: { good: 15, moderate: 45, unhealthy: 75 },
            aqi: { good: 50, moderate: 100, unhealthy: 150 }
        };
    }

    /**
     * Start analytics monitoring
     */
    start() {
        this.setupAnalyticsDisplay();
        this.updateAnalytics();
        
        // Update analytics every 30 seconds
        setInterval(() => {
            this.updateAnalytics();
        }, 30000);
    }

    /**
     * Setup analytics display elements
     */
    setupAnalyticsDisplay() {
        // Add analytics sections to the air quality tab
        const airQualitySection = document.getElementById('air-quality-history-section');
        if (airQualitySection) {
            this.addAnalyticsSection(airQualitySection);
        }
    }

    /**
     * Add analytics section to existing air quality display
     * @param {Element} parentElement - Parent element to add analytics to
     */
    addAnalyticsSection(parentElement) {
        const analyticsHTML = `
            <div class="chart-analytics" id="air-quality-analytics">
                <h4>📊 Real-time Analytics</h4>
                <div class="analytics-grid">
                    <div class="analytics-item">
                        <div class="analytics-value" id="trend-pm25">--</div>
                        <div class="analytics-label">PM2.5 Trend</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value" id="trend-aqi">--</div>
                        <div class="analytics-label">AQI Trend</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value" id="data-quality">--</div>
                        <div class="analytics-label">Data Quality</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value" id="next-hour-prediction">--</div>
                        <div class="analytics-label">Next Hour</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value" id="who-compliance">--</div>
                        <div class="analytics-label">WHO Compliance</div>
                    </div>
                    <div class="analytics-item">
                        <div class="analytics-value" id="avg-today">--</div>
                        <div class="analytics-label">Today's Avg</div>
                    </div>
                </div>
                <div class="analytics-alerts" id="analytics-alerts">
                    <!-- Dynamic alerts will be added here -->
                </div>
            </div>
        `;
        
        parentElement.insertAdjacentHTML('beforeend', analyticsHTML);
    }

    /**
     * Update all analytics
     */
    async updateAnalytics() {
        try {
            const data = await this.fetchAnalyticsData();
            if (data) {
                this.calculateTrends(data);
                this.assessDataQuality(data);
                this.generatePredictions(data);
                this.updateAnalyticsDisplay();
                this.checkAlerts(data);
            }
        } catch (error) {
            console.error('Error updating analytics:', error);
        }
    }

    /**
     * Fetch data needed for analytics
     * @returns {Promise<Object>} Analytics data
     */
    async fetchAnalyticsData() {
        const [latest, history24h, history1h] = await Promise.all([
            this.utils.fetchData(this.config.API_ENDPOINTS.airQualityLatest),
            this.utils.fetchData(this.config.API_ENDPOINTS.airQualityHistory + '?range=24h'),
            this.utils.fetchData(this.config.API_ENDPOINTS.airQualityHistory + '?range=1h')
        ]);

        return {
            latest: latest?.latest_reading,
            history24h: history24h?.interval_averages || [],
            history1h: history1h?.interval_averages || []
        };
    }

    /**
     * Calculate trends for key metrics
     * @param {Object} data - Analytics data
     */
    calculateTrends(data) {
        const { history1h, history24h } = data;
        
        // PM2.5 trends
        this.trendData.pm25 = {
            shortTerm: this.calculateShortTermTrend(history1h, 'avg_pm2_5'),
            longTerm: this.calculateLongTermTrend(history24h, 'avg_pm2_5'),
            velocity: this.calculateVelocity(history1h, 'avg_pm2_5')
        };

        // AQI trends
        this.trendData.aqi = {
            shortTerm: this.calculateShortTermTrend(history1h, 'avg_aqi'),
            longTerm: this.calculateLongTermTrend(history24h, 'avg_aqi'),
            velocity: this.calculateVelocity(history1h, 'avg_aqi')
        };
    }

    /**
     * Calculate short-term trend (last hour)
     * @param {Array} data - Historical data
     * @param {string} field - Field to analyze
     * @returns {Object} Trend analysis
     */
    calculateShortTermTrend(data, field) {
        if (data.length < 4) return { direction: 'insufficient', change: 0 };

        const recent = data.slice(-4).map(d => d[field]).filter(v => v !== null);
        if (recent.length < 3) return { direction: 'insufficient', change: 0 };

        const avgRecent = recent.slice(-2).reduce((a, b) => a + b, 0) / 2;
        const avgEarlier = recent.slice(0, 2).reduce((a, b) => a + b, 0) / 2;
        const change = avgRecent - avgEarlier;

        let direction;
        if (Math.abs(change) < 1) direction = 'stable';
        else if (change > 0) direction = 'rising';
        else direction = 'falling';

        return { direction, change: Math.round(change * 10) / 10 };
    }

    /**
     * Calculate long-term trend (last 24 hours)
     * @param {Array} data - Historical data
     * @param {string} field - Field to analyze
     * @returns {Object} Trend analysis
     */
    calculateLongTermTrend(data, field) {
        if (data.length < 8) return { direction: 'insufficient', change: 0 };

        const values = data.map(d => d[field]).filter(v => v !== null);
        if (values.length < 8) return { direction: 'insufficient', change: 0 };

        // Simple linear regression for trend
        const n = values.length;
        const x = Array.from({length: n}, (_, i) => i);
        const sumX = x.reduce((a, b) => a + b, 0);
        const sumY = values.reduce((a, b) => a + b, 0);
        const sumXY = x.map((xi, i) => xi * values[i]).reduce((a, b) => a + b, 0);
        const sumXX = x.map(xi => xi * xi).reduce((a, b) => a + b, 0);

        const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
        const change = slope * n; // Change over the entire period

        let direction;
        if (Math.abs(change) < 2) direction = 'stable';
        else if (change > 0) direction = 'rising';
        else direction = 'falling';

        return { direction, change: Math.round(change * 10) / 10 };
    }

    /**
     * Calculate velocity (rate of change)
     * @param {Array} data - Historical data
     * @param {string} field - Field to analyze
     * @returns {number} Velocity
     */
    calculateVelocity(data, field) {
        if (data.length < 2) return 0;

        const values = data.slice(-6).map(d => d[field]).filter(v => v !== null);
        if (values.length < 2) return 0;

        const changes = [];
        for (let i = 1; i < values.length; i++) {
            changes.push(values[i] - values[i-1]);
        }

        return changes.reduce((a, b) => a + b, 0) / changes.length;
    }

    /**
     * Assess data quality
     * @param {Object} data - Analytics data
     */
    assessDataQuality(data) {
        const { history1h, latest } = data;
        
        let quality = 100;
        let issues = [];

        // Check data freshness
        if (latest) {
            const lastUpdate = new Date(latest.timestamp);
            const minutesOld = (Date.now() - lastUpdate.getTime()) / (1000 * 60);
            if (minutesOld > 10) {
                quality -= 20;
                issues.push('Data is stale');
            }
        } else {
            quality -= 40;
            issues.push('No recent data');
        }

        // Check data completeness
        const validReadings = history1h.filter(d => 
            d.avg_pm2_5 !== null && d.avg_pm10 !== null
        ).length;
        const completeness = validReadings / Math.max(history1h.length, 1);
        
        if (completeness < 0.8) {
            quality -= 30;
            issues.push('Missing readings');
        } else if (completeness < 0.9) {
            quality -= 15;
            issues.push('Some gaps in data');
        }

        // Check for sensor anomalies
        if (latest) {
            const { pm2_5, pm10 } = latest;
            if (pm2_5 > pm10 && pm10 > 0) {
                quality -= 10;
                issues.push('Sensor anomaly detected');
            }
        }

        this.dataQuality = {
            score: Math.max(0, quality),
            issues,
            status: quality >= 90 ? 'Excellent' : 
                   quality >= 70 ? 'Good' : 
                   quality >= 50 ? 'Fair' : 'Poor'
        };
    }

    /**
     * Generate predictions
     * @param {Object} data - Analytics data
     */
    generatePredictions(data) {
        const { latest, history1h } = data;
        
        if (!latest || history1h.length < 4) {
            this.predictions.nextHour = { pm25: null, aqi: null, confidence: 'low' };
            return;
        }

        // Simple trend-based prediction
        const pm25Trend = this.trendData.pm25;
        const aqiTrend = this.trendData.aqi;
        
        const pm25Prediction = latest.pm2_5 + (pm25Trend.velocity * 6); // 6 intervals = ~1 hour
        const aqiPrediction = latest.aqi + (aqiTrend.velocity * 6);

        // Confidence based on trend stability
        const pm25Stability = Math.abs(pm25Trend.velocity) < 2;
        const aqiStability = Math.abs(aqiTrend.velocity) < 5;
        const confidence = pm25Stability && aqiStability ? 'high' : 
                          pm25Stability || aqiStability ? 'medium' : 'low';

        this.predictions.nextHour = {
            pm25: Math.max(0, Math.round(pm25Prediction * 10) / 10),
            aqi: Math.max(0, Math.round(aqiPrediction)),
            confidence
        };
    }

    /**
     * Update analytics display
     */
    updateAnalyticsDisplay() {
        // Update trend displays
        this.updateTrendDisplay('trend-pm25', this.trendData.pm25);
        this.updateTrendDisplay('trend-aqi', this.trendData.aqi);

        // Update data quality
        const qualityEl = document.getElementById('data-quality');
        if (qualityEl) {
            qualityEl.textContent = this.dataQuality.status;
            qualityEl.className = 'analytics-value';
            if (this.dataQuality.score >= 90) qualityEl.classList.add('trend-stable');
            else if (this.dataQuality.score >= 70) qualityEl.classList.add('trend-stable');
            else qualityEl.classList.add('trend-up');
        }

        // Update predictions
        const predictionEl = document.getElementById('next-hour-prediction');
        if (predictionEl && this.predictions.nextHour.pm25 !== null) {
            const pm25 = this.predictions.nextHour.pm25;
            const confidence = this.predictions.nextHour.confidence;
            predictionEl.textContent = `${pm25} μg/m³`;
            predictionEl.className = 'analytics-value';
            
            if (confidence === 'low') predictionEl.classList.add('trend-up');
            else if (confidence === 'medium') predictionEl.classList.add('trend-stable');
            else predictionEl.classList.add('trend-down');
        }

        // Update WHO compliance and today's average
        this.updateWHOCompliance();
        this.updateTodayAverage();
    }

    /**
     * Update trend display for a specific metric
     * @param {string} elementId - Element ID
     * @param {Object} trendData - Trend data
     */
    updateTrendDisplay(elementId, trendData) {
        const element = document.getElementById(elementId);
        if (!element || !trendData) return;

        const { direction, change } = trendData.shortTerm;
        let displayText = direction.charAt(0).toUpperCase() + direction.slice(1);
        
        if (direction !== 'insufficient' && direction !== 'stable') {
            displayText += ` (${change > 0 ? '+' : ''}${change})`;
        }

        element.textContent = displayText;
        element.className = 'analytics-value';
        
        if (direction === 'rising') element.classList.add('trend-up');
        else if (direction === 'falling') element.classList.add('trend-down');
        else element.classList.add('trend-stable');
    }

    /**
     * Update WHO compliance display
     */
    updateWHOCompliance() {
        const element = document.getElementById('who-compliance');
        if (!element) return;

        // Get current PM2.5 value
        const latestEl = document.getElementById('pm25-value');
        if (!latestEl) return;

        const pm25Value = parseFloat(latestEl.textContent);
        if (isNaN(pm25Value)) {
            element.textContent = '--';
            return;
        }

        const dailyLimit = 15; // WHO daily limit
        const annualLimit = 5; // WHO annual limit

        let status, className;
        if (pm25Value <= annualLimit) {
            status = 'Excellent';
            className = 'trend-down';
        } else if (pm25Value <= dailyLimit) {
            status = 'Good';
            className = 'trend-stable';
        } else {
            status = 'Exceeded';
            className = 'trend-up';
        }

        element.textContent = status;
        element.className = `analytics-value ${className}`;
    }

    /**
     * Update today's average display
     */
    async updateTodayAverage() {
        const element = document.getElementById('avg-today');
        if (!element) return;

        try {
            const data = await this.utils.fetchData(this.config.API_ENDPOINTS.airQualityHistory + '?range=24h');
            if (!data || !data.interval_averages) {
                element.textContent = '--';
                return;
            }

            // Calculate today's average from available data
            const today = new Date().toDateString();
            const todayData = data.interval_averages.filter(item => {
                const itemDate = new Date(item.interval_time).toDateString();
                return itemDate === today;
            });

            if (todayData.length === 0) {
                element.textContent = '--';
                return;
            }

            const validPM25 = todayData
                .map(d => d.avg_pm2_5)
                .filter(v => v !== null && v !== undefined);

            if (validPM25.length === 0) {
                element.textContent = '--';
                return;
            }

            const average = validPM25.reduce((a, b) => a + b, 0) / validPM25.length;
            element.textContent = `${Math.round(average * 10) / 10} μg/m³`;
            element.className = 'analytics-value trend-stable';

        } catch (error) {
            console.error('Error calculating today\'s average:', error);
            element.textContent = '--';
        }
    }

    /**
     * Check for alerts and display them
     * @param {Object} data - Analytics data
     */
    checkAlerts(data) {
        const alertsContainer = document.getElementById('analytics-alerts');
        if (!alertsContainer) return;

        const alerts = [];
        const { latest } = data;

        if (latest) {
            // Check PM2.5 levels
            if (latest.pm2_5 > this.alertThresholds.pm25.unhealthy) {
                alerts.push({
                    type: 'warning',
                    message: `PM2.5 levels (${latest.pm2_5} μg/m³) are unhealthy. Consider limiting outdoor activities.`
                });
            }

            // Check trends
            if (this.trendData.pm25 && this.trendData.pm25.shortTerm.direction === 'rising' && 
                this.trendData.pm25.shortTerm.change > 5) {
                alerts.push({
                    type: 'info',
                    message: `PM2.5 levels are rising rapidly (+${this.trendData.pm25.shortTerm.change} μg/m³).`
                });
            }

            // Check data quality
            if (this.dataQuality.score < 70) {
                alerts.push({
                    type: 'warning',
                    message: `Data quality is ${this.dataQuality.status.toLowerCase()}. ${this.dataQuality.issues.join(', ')}.`
                });
            }
        }

        // Update alerts display
        alertsContainer.innerHTML = alerts.map(alert => `
            <div class="analytics-alert alert-${alert.type}">
                ${alert.message}
            </div>
        `).join('');
    }

    /**
     * Get analytics summary for external use
     * @returns {Object} Analytics summary
     */
    getAnalyticsSummary() {
        return {
            trends: this.trendData,
            dataQuality: this.dataQuality,
            predictions: this.predictions
        };
    }
}

// Create global analytics manager instance
window.analyticsManager = new AnalyticsManager();