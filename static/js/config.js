/**
 * Configuration and constants for Pi Air Monitor
 */

// API endpoints
const API_ENDPOINTS = {
    system: '/api/system',
    stats: '/api/stats',
    airQualityLatest: '/api/air-quality-latest',
    airQualityWorst24h: '/api/air-quality-worst-24h',
    airQualityHistory: '/api/air-quality-history',
    temperatureHistory: '/api/temperature-history',
    systemHistory: '/api/system-history'
};

// Chart colors
const CHART_COLORS = {
    primary: 'rgb(197, 26, 74)',
    secondary: 'rgb(75, 192, 192)',
    tertiary: 'rgb(255, 159, 64)',
    quaternary: 'rgb(153, 102, 255)',
    danger: 'rgb(255, 99, 132)',
    warning: 'rgb(255, 206, 86)',
    success: 'rgb(75, 192, 192)',
    info: 'rgb(54, 162, 235)'
};

// AQI levels and colors
const AQI_LEVELS = {
    good: { max: 50, label: 'Good', color: '#00e400', textColor: 'white' },
    moderate: { max: 100, label: 'Moderate', color: '#ffff00', textColor: 'black' },
    unhealthySensitive: { max: 150, label: 'Unhealthy for Sensitive Groups', color: '#ff7e00', textColor: 'white' },
    unhealthy: { max: 200, label: 'Unhealthy', color: '#ff0000', textColor: 'white' },
    veryUnhealthy: { max: 300, label: 'Very Unhealthy', color: '#8f3f97', textColor: 'white' },
    hazardous: { max: 500, label: 'Hazardous', color: '#7e0023', textColor: 'white' }
};

// Update intervals (milliseconds)
const UPDATE_INTERVALS = {
    stats: 2000,        // 2 seconds
    airQuality: 5000,   // 5 seconds
    charts: 30000       // 30 seconds
};

// Mobile breakpoint
const MOBILE_BREAKPOINT = 768;

// Chart default options
const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
    },
    plugins: {
        legend: {
            display: true,
            position: 'top',
            labels: {
                boxWidth: 12,
                padding: 10,
                font: {
                    size: window.innerWidth < MOBILE_BREAKPOINT ? 10 : 12
                }
            }
        },
        tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleFont: {
                size: window.innerWidth < MOBILE_BREAKPOINT ? 11 : 13
            },
            bodyFont: {
                size: window.innerWidth < MOBILE_BREAKPOINT ? 10 : 12
            }
        }
    },
    scales: {
        x: {
            display: true,
            grid: {
                display: false
            },
            ticks: {
                maxRotation: 45,
                minRotation: 45,
                font: {
                    size: window.innerWidth < MOBILE_BREAKPOINT ? 9 : 11
                }
            }
        },
        y: {
            display: true,
            position: 'left',
            grid: {
                color: 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
                font: {
                    size: window.innerWidth < MOBILE_BREAKPOINT ? 9 : 11
                }
            }
        }
    }
};

// Export for use in other modules
window.AppConfig = {
    API_ENDPOINTS,
    CHART_COLORS,
    AQI_LEVELS,
    UPDATE_INTERVALS,
    MOBILE_BREAKPOINT,
    CHART_DEFAULTS
};