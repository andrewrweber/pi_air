/**
 * Air quality monitoring functionality for Pi Air Monitor
 */

class AirQualityMonitor {
    constructor() {
        this.config = window.AppConfig;
        this.utils = window.Utils;
        this.chartManager = window.chartManager;
        
        // State
        this.currentParticlesTimeRange = '24h';
        this.currentAQITimeRange = '24h';
        this.cachedAirQualityData = {
            '1h': null,
            '6h': null,
            '24h': null
        };
        
        // Touch handling for mobile swipe
        this.touchStartX = 0;
        this.touchEndX = 0;
        
        this.updateInterval = null;
    }

    /**
     * Start monitoring air quality
     */
    start() {
        // Initial updates
        this.updateLatestReading();
        this.updateWorstAirQuality();
        this.showParticlesData('24h');
        this.showAQIData('24h');
        
        // Set up periodic updates
        this.updateInterval = setInterval(() => {
            this.updateLatestReading();
            this.updateWorstAirQuality();
        }, this.config.UPDATE_INTERVALS.airQuality);
        
        // Set up event listeners
        this.setupEventListeners();
        this.setupMobileSwipeNavigation();
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
     * Update latest air quality reading
     */
    async updateLatestReading() {
        const data = await this.utils.fetchData(this.config.API_ENDPOINTS.airQualityLatest);
        if (!data || !data.latest_reading) {
            this.setNoDataState();
            return;
        }

        const reading = data.latest_reading;
        
        // Update AQI value and level
        this.utils.updateElementText('aqi-value', reading.aqi || '--');
        this.utils.updateAQIElement('aqi-level', reading.aqi);
        
        // Update particle values
        this.utils.updateElementText('pm1-value', 
            reading.pm1_0 !== null ? reading.pm1_0.toFixed(1) : '--');
        this.utils.updateElementText('pm25-value', 
            reading.pm2_5 !== null ? reading.pm2_5.toFixed(1) : '--');
        this.utils.updateElementText('pm10-value', 
            reading.pm10 !== null ? reading.pm10.toFixed(1) : '--');
        
        // Update last updated time
        if (reading.timestamp) {
            const date = new Date(reading.timestamp);
            const timeString = date.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                second: '2-digit',
                timeZone: 'America/Los_Angeles',
                timeZoneName: 'short'
            });
            this.utils.updateElementText('last-update', timeString);
        }
    }

    /**
     * Update worst air quality in last 24h
     */
    async updateWorstAirQuality() {
        const data = await this.utils.fetchData(this.config.API_ENDPOINTS.airQualityWorst24h);
        
        if (!data || !data.worst_reading) {
            this.utils.updateElementText('worst-aqi-value', '--');
            this.utils.updateElementText('worst-pm1-value', '--');
            this.utils.updateElementText('worst-pm25-value', '--');
            this.utils.updateElementText('worst-pm10-value', '--');
            this.utils.updateElementText('worst-time', 'No data available');
            this.utils.updateElementText('worst-aqi-level', '--');
            return;
        }

        const reading = data.worst_reading;
        
        // Update worst values
        this.utils.updateElementText('worst-aqi-value', reading.aqi || '--');
        this.utils.updateElementText('worst-pm1-value', 
            reading.pm1_0 !== null ? reading.pm1_0.toFixed(1) : '--');
        this.utils.updateElementText('worst-pm25-value', 
            reading.pm2_5 !== null ? reading.pm2_5.toFixed(1) : '--');
        this.utils.updateElementText('worst-pm10-value', 
            reading.pm10 !== null ? reading.pm10.toFixed(1) : '--');
        
        // Update time when worst reading occurred
        this.utils.updateElementText('worst-time', 
            this.utils.formatTimestamp(reading.timestamp));
        
        // Update AQI level and color
        this.utils.updateAQIElement('worst-aqi-level', reading.aqi);
    }

    /**
     * Set no data state for air quality display
     */
    setNoDataState() {
        this.utils.updateElementText('aqi-value', '--');
        this.utils.updateElementText('aqi-level', 'No Data');
        this.utils.updateElementText('pm1-value', '--');
        this.utils.updateElementText('pm25-value', '--');
        this.utils.updateElementText('pm10-value', '--');
        this.utils.updateElementText('last-update', 'No sensor data available');
    }

    /**
     * Fetch air quality data for a specific time range
     * @param {string} timeRange - '1h', '6h', or '24h'
     * @returns {Promise<Array>} Air quality data
     */
    async fetchAirQualityData(timeRange) {
        // Check cache first
        if (this.cachedAirQualityData[timeRange]) {
            return this.cachedAirQualityData[timeRange];
        }

        const endpoint = `${this.config.API_ENDPOINTS.airQualityHistory}?range=${timeRange}`;
        const data = await this.utils.fetchData(endpoint);
        
        if (data && data.interval_averages) {
            this.cachedAirQualityData[timeRange] = data.interval_averages;
            
            // Clear cache after 5 minutes
            setTimeout(() => {
                this.cachedAirQualityData[timeRange] = null;
            }, 5 * 60 * 1000);
            
            return data.interval_averages;
        }
        
        return [];
    }

    /**
     * Filter data by time range
     * @param {Array} data - Data to filter
     * @param {string} timeRange - Time range to filter by
     * @returns {Array} Filtered data
     */
    filterDataByTimeRange(data, timeRange) {
        const now = new Date();
        let hoursAgo;
        
        switch(timeRange) {
            case '1h':
                hoursAgo = 1;
                break;
            case '6h':
                hoursAgo = 6;
                break;
            default:
                hoursAgo = 24;
        }
        
        const cutoffTime = new Date(now.getTime() - (hoursAgo * 60 * 60 * 1000));
        
        return data.filter(item => {
            const itemTime = new Date(item.interval_time + 'Z');
            return itemTime >= cutoffTime;
        });
    }

    /**
     * Update particles chart
     * @param {Array} allData - All air quality data
     */
    updateParticlesChart(allData) {
        const filteredData = this.filterDataByTimeRange(allData, this.currentParticlesTimeRange);
        
        if (filteredData.length === 0) {
            const hoursAgo = this.currentParticlesTimeRange === '1h' ? 1 : 
                           (this.currentParticlesTimeRange === '6h' ? 6 : 24);
            const noDataMsg = `No data in the last ${hoursAgo} hour${hoursAgo > 1 ? 's' : ''}`;
            
            this.chartManager.updateChart('particles', [noDataMsg], {
                pm25: [],
                pm10: [],
                pm1: []
            });
            return;
        }

        const labels = filteredData.map(item => {
            const utcDate = new Date(item.interval_time + 'Z');
            return utcDate.toLocaleString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                hour: 'numeric',
                minute: '2-digit',
                timeZone: 'America/Los_Angeles',
                timeZoneName: 'short'
            });
        });
        
        const pm1Data = filteredData.map(item => item.avg_pm1_0);
        const pm25Data = filteredData.map(item => item.avg_pm2_5);
        const pm10Data = filteredData.map(item => item.avg_pm10);
        
        // Calculate dynamic max values for better scaling
        const maxPM = Math.max(
            ...pm1Data.filter(v => v !== null),
            ...pm25Data.filter(v => v !== null),
            ...pm10Data.filter(v => v !== null),
            10  // minimum
        );
        
        const particlesChart = this.chartManager.getChart('particles');
        particlesChart.options.scales.y.suggestedMax = Math.ceil(maxPM * 1.2);
        
        this.chartManager.updateChart('particles', labels, {
            pm25: pm25Data,
            pm10: pm10Data,
            pm1: pm1Data
        });
    }

    /**
     * Update AQI chart
     * @param {Array} allData - All air quality data
     */
    updateAQIChart(allData) {
        const filteredData = this.filterDataByTimeRange(allData, this.currentAQITimeRange);
        
        if (filteredData.length === 0) {
            const hoursAgo = this.currentAQITimeRange === '1h' ? 1 : 
                           (this.currentAQITimeRange === '6h' ? 6 : 24);
            const noDataMsg = `No data in the last ${hoursAgo} hour${hoursAgo > 1 ? 's' : ''}`;
            
            this.chartManager.updateChart('aqi', [noDataMsg], []);
            return;
        }

        const labels = filteredData.map(item => {
            const utcDate = new Date(item.interval_time + 'Z');
            return utcDate.toLocaleString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                hour: 'numeric',
                minute: '2-digit',
                timeZone: 'America/Los_Angeles',
                timeZoneName: 'short'
            });
        });
        
        const aqiData = filteredData.map(item => item.avg_aqi);
        const maxAQI = Math.max(...aqiData.filter(v => v !== null), 50);
        
        const aqiChart = this.chartManager.getChart('aqi');
        aqiChart.options.scales.y.suggestedMax = Math.ceil(maxAQI * 1.2);
        
        // Ensure we show AQI scale up to at least 200 to show color bands
        if (aqiChart.options.scales.y.suggestedMax < 200) {
            aqiChart.options.scales.y.suggestedMax = 200;
        }
        
        // Color the AQI line based on the current value
        const currentAQI = aqiData[aqiData.length - 1];
        if (currentAQI !== null && currentAQI !== undefined) {
            let lineColor;
            const levels = this.config.AQI_LEVELS;
            
            if (currentAQI <= levels.good.max) lineColor = levels.good.color;
            else if (currentAQI <= levels.moderate.max) lineColor = levels.moderate.color;
            else if (currentAQI <= levels.unhealthySensitive.max) lineColor = levels.unhealthySensitive.color;
            else if (currentAQI <= levels.unhealthy.max) lineColor = levels.unhealthy.color;
            else if (currentAQI <= levels.veryUnhealthy.max) lineColor = levels.veryUnhealthy.color;
            else lineColor = levels.hazardous.color;
            
            aqiChart.data.datasets[0].borderColor = lineColor;
            aqiChart.data.datasets[0].backgroundColor = lineColor + '1A';
        }
        
        this.chartManager.updateChart('aqi', labels, aqiData);
    }

    /**
     * Show particles data for specific time range
     * @param {string} timeRange - '1h', '6h', or '24h'
     */
    async showParticlesData(timeRange) {
        this.currentParticlesTimeRange = timeRange;
        
        // Update button states
        ['1h', '6h', '24h'].forEach(range => {
            const btn = document.getElementById(`particles-${range}-btn`);
            if (btn) btn.classList.toggle('active', range === timeRange);
        });
        
        // Update chart title
        const titleElement = document.getElementById('particles-chart-title');
        if (titleElement) {
            const { hoursText, intervalText } = this.getTimeRangeText(timeRange);
            titleElement.textContent = `Particle Concentrations (${hoursText}, ${intervalText})`;
        }
        
        // Fetch and update data
        const data = await this.fetchAirQualityData(timeRange);
        this.updateParticlesChart(data);
    }

    /**
     * Show AQI data for specific time range
     * @param {string} timeRange - '1h', '6h', or '24h'
     */
    async showAQIData(timeRange) {
        this.currentAQITimeRange = timeRange;
        
        // Update button states
        ['1h', '6h', '24h'].forEach(range => {
            const btn = document.getElementById(`aqi-${range}-btn`);
            if (btn) btn.classList.toggle('active', range === timeRange);
        });
        
        // Update chart title
        const titleElement = document.getElementById('aqi-chart-title');
        if (titleElement) {
            const { hoursText, intervalText } = this.getTimeRangeText(timeRange);
            titleElement.textContent = `Air Quality Index (${hoursText}, ${intervalText})`;
        }
        
        // Fetch and update data
        const data = await this.fetchAirQualityData(timeRange);
        this.updateAQIChart(data);
    }

    /**
     * Get time range text for display
     * @param {string} timeRange - Time range
     * @returns {object} Hours and interval text
     */
    getTimeRangeText(timeRange) {
        const texts = {
            '1h': { hoursText: '1 hour', intervalText: '2-minute intervals' },
            '6h': { hoursText: '6 hours', intervalText: '5-minute intervals' },
            '24h': { hoursText: '24 hours', intervalText: '15-minute intervals' }
        };
        return texts[timeRange] || texts['24h'];
    }

    /**
     * Handle swipe gesture for chart navigation
     * @param {string} chartType - 'particles' or 'aqi'
     */
    handleSwipeGesture(chartType) {
        const swipeThreshold = 50;
        const swipeDistance = this.touchEndX - this.touchStartX;
        
        if (Math.abs(swipeDistance) < swipeThreshold) return;
        
        const timeRanges = ['1h', '6h', '24h'];
        const currentRange = chartType === 'particles' ? 
            this.currentParticlesTimeRange : this.currentAQITimeRange;
        const currentIndex = timeRanges.indexOf(currentRange);
        
        let newIndex;
        if (swipeDistance > 0) {
            // Swipe right - go to previous time range
            newIndex = currentIndex > 0 ? currentIndex - 1 : timeRanges.length - 1;
        } else {
            // Swipe left - go to next time range
            newIndex = currentIndex < timeRanges.length - 1 ? currentIndex + 1 : 0;
        }
        
        const newRange = timeRanges[newIndex];
        if (chartType === 'particles') {
            this.showParticlesData(newRange);
        } else {
            this.showAQIData(newRange);
        }
    }

    /**
     * Set up mobile swipe navigation
     */
    setupMobileSwipeNavigation() {
        const particlesChart = document.getElementById('particlesChart');
        const aqiChart = document.getElementById('aqiChart');
        
        [particlesChart, aqiChart].forEach((chart, index) => {
            if (!chart) return;
            
            const chartType = index === 0 ? 'particles' : 'aqi';
            
            chart.addEventListener('touchstart', (e) => {
                this.touchStartX = e.changedTouches[0].screenX;
            }, { passive: true });
            
            chart.addEventListener('touchend', (e) => {
                this.touchEndX = e.changedTouches[0].screenX;
                this.handleSwipeGesture(chartType);
            }, { passive: true });
        });
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Expose methods to global scope for button onclick handlers
        window.showParticlesData = (range) => this.showParticlesData(range);
        window.showAQIData = (range) => this.showAQIData(range);
    }
}

// Create global air quality monitor instance
window.airQualityMonitor = new AirQualityMonitor();