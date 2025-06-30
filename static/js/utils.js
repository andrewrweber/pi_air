/**
 * Utility functions for Pi Air Monitor
 */

/**
 * Timezone Manager for handling user timezone preferences
 */
class TimezoneManager {
    constructor() {
        this.defaultTimezone = 'America/Los_Angeles'; // PDT/PST default
        this.userTimezone = this.detectUserTimezone();
        this.preferredTimezone = this.getPreferredTimezone();
    }

    /**
     * Detect user's browser timezone
     * @returns {string} IANA timezone name
     */
    detectUserTimezone() {
        try {
            return Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch (e) {
            console.warn('Could not detect user timezone, using default:', e);
            return this.defaultTimezone;
        }
    }

    /**
     * Get preferred timezone from localStorage or use detected/default
     * @returns {string} IANA timezone name
     */
    getPreferredTimezone() {
        try {
            const stored = localStorage.getItem('piair_timezone');
            if (stored && this.isValidTimezone(stored)) {
                return stored;
            }
        } catch (e) {
            console.warn('Could not access localStorage for timezone preference:', e);
        }
        
        // Use detected timezone if it's valid, otherwise use default
        return this.isValidTimezone(this.userTimezone) ? this.userTimezone : this.defaultTimezone;
    }

    /**
     * Set user's preferred timezone
     * @param {string} timezone - IANA timezone name
     */
    setPreferredTimezone(timezone) {
        if (!this.isValidTimezone(timezone)) {
            console.warn('Invalid timezone:', timezone);
            return false;
        }
        
        try {
            localStorage.setItem('piair_timezone', timezone);
            this.preferredTimezone = timezone;
            return true;
        } catch (e) {
            console.warn('Could not save timezone preference:', e);
            return false;
        }
    }

    /**
     * Check if timezone is valid
     * @param {string} timezone - IANA timezone name
     * @returns {boolean} True if valid
     */
    isValidTimezone(timezone) {
        try {
            Intl.DateTimeFormat(undefined, { timeZone: timezone });
            return true;
        } catch (e) {
            return false;
        }
    }

    /**
     * Get current preferred timezone
     * @returns {string} IANA timezone name
     */
    getTimezone() {
        return this.preferredTimezone;
    }

    /**
     * Get timezone info for display
     * @returns {object} Timezone info
     */
    getTimezoneInfo() {
        const now = new Date();
        return {
            timezone: this.preferredTimezone,
            isUserDetected: this.preferredTimezone === this.userTimezone,
            isDefault: this.preferredTimezone === this.defaultTimezone,
            abbreviation: now.toLocaleDateString('en-US', {
                timeZoneName: 'short',
                timeZone: this.preferredTimezone
            }).split(', ')[1] || 'UTC'
        };
    }
}

// Global timezone manager instance
const timezoneManager = new TimezoneManager();

/**
 * Get AQI level and CSS class based on AQI value
 * @param {number} aqi - The AQI value
 * @returns {object} Object containing level and cssClass
 */
function getAQILevelAndClass(aqi) {
    const levels = window.AppConfig.AQI_LEVELS;
    
    if (aqi <= levels.good.max) {
        return { level: levels.good.label, cssClass: 'aqi-good' };
    } else if (aqi <= levels.moderate.max) {
        return { level: levels.moderate.label, cssClass: 'aqi-moderate' };
    } else if (aqi <= levels.unhealthySensitive.max) {
        return { level: levels.unhealthySensitive.label, cssClass: 'aqi-unhealthy-sensitive' };
    } else if (aqi <= levels.unhealthy.max) {
        return { level: levels.unhealthy.label, cssClass: 'aqi-unhealthy' };
    } else if (aqi <= levels.veryUnhealthy.max) {
        return { level: levels.veryUnhealthy.label, cssClass: 'aqi-very-unhealthy' };
    } else {
        return { level: levels.hazardous.label, cssClass: 'aqi-hazardous' };
    }
}

/**
 * Format timestamp for display in user's preferred timezone
 * @param {string} timestamp - UTC timestamp from database
 * @param {boolean} includeSeconds - Whether to include seconds
 * @returns {string} Formatted timestamp string
 */
function formatTimestamp(timestamp, includeSeconds = false) {
    // Ensure UTC timezone indicator for proper parsing
    const utcTimestamp = timestamp.includes('Z') || timestamp.includes('+') ? timestamp : timestamp + 'Z';
    const utcDate = new Date(utcTimestamp);
    
    if (isNaN(utcDate.getTime())) {
        console.warn('Invalid timestamp:', timestamp);
        return 'Invalid Date';
    }
    
    const timezone = timezoneManager.getTimezone();
    
    // Format date and time in user's preferred timezone
    const formattedDate = utcDate.toLocaleDateString('en-US', {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
        timeZone: timezone
    });
    
    const timeOptions = {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: timezone
    };
    
    if (includeSeconds) {
        timeOptions.second = '2-digit';
    }
    
    const formattedTime = utcDate.toLocaleTimeString('en-US', timeOptions);
    
    // Get the timezone abbreviation
    const timeZoneAbbr = utcDate.toLocaleDateString('en-US', {
        timeZoneName: 'short',
        timeZone: timezone
    }).split(', ')[1] || 'UTC';
    
    return `${formattedDate} at ${formattedTime} ${timeZoneAbbr}`;
}

/**
 * Format a date for chart labels
 * @param {string} timestamp - Timestamp to format
 * @param {boolean} includeSeconds - Whether to include seconds
 * @returns {string} Formatted time string
 */
function formatChartLabel(timestamp, includeSeconds = false) {
    const utcTimestamp = timestamp.includes('Z') || timestamp.includes('+') ? timestamp : timestamp + 'Z';
    const date = new Date(utcTimestamp);
    
    if (isNaN(date.getTime())) {
        console.warn('Invalid timestamp for chart label:', timestamp);
        return 'Invalid';
    }
    
    const timezone = timezoneManager.getTimezone();
    const options = {
        hour: 'numeric',
        minute: '2-digit',
        timeZone: timezone,
        timeZoneName: 'short'
    };
    
    if (includeSeconds) {
        options.second = '2-digit';
    }
    
    return date.toLocaleString('en-US', options);
}

/**
 * Fetch data from an API endpoint with error handling
 * @param {string} endpoint - API endpoint to fetch from
 * @param {object} options - Fetch options
 * @returns {Promise<object|null>} Response data or null on error
 */
async function fetchData(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, options);
        if (!response.ok) {
            console.error(`API error: ${response.status} ${response.statusText}`);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error(`Fetch error for ${endpoint}:`, error);
        return null;
    }
}

/**
 * Update element text content safely
 * @param {string} elementId - Element ID
 * @param {string} text - Text to set
 * @param {string} defaultText - Default text if element not found
 */
function updateElementText(elementId, text, defaultText = '--') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text || defaultText;
    }
}

/**
 * Update element with AQI styling
 * @param {string} elementId - Element ID
 * @param {number} aqi - AQI value
 * @param {string} defaultText - Default text if no AQI
 */
function updateAQIElement(elementId, aqi, defaultText = '--') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (aqi !== null && aqi !== undefined) {
        const { level, cssClass } = getAQILevelAndClass(aqi);
        
        // Remove any existing AQI classes
        element.className = element.className.replace(/aqi-\w+/g, '');
        // Add the new AQI class
        element.classList.add(cssClass);
        element.textContent = level;
    } else {
        element.textContent = defaultText;
    }
}

/**
 * Check if running on mobile device
 * @returns {boolean} True if mobile device
 */
function isMobile() {
    return window.innerWidth < window.AppConfig.MOBILE_BREAKPOINT;
}

/**
 * Debounce function to limit API calls
 * @param {function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export utilities
/**
 * Get AQI color for forecast display
 * @param {number} aqi - The AQI value
 * @returns {string} CSS color value
 */
function getAQIColor(aqi) {
    if (aqi === null || aqi === undefined) return '#666';
    if (aqi <= 50) return '#00e400';
    if (aqi <= 100) return '#cccc00';
    if (aqi <= 150) return '#ff7e00';
    if (aqi <= 200) return '#ff0000';
    if (aqi <= 300) return '#8f3f97';
    return '#7e0023';
}

/**
 * Get AQI color class for forecast cards
 * @param {number} aqi - The AQI value
 * @returns {string} CSS class name
 */
function getAQIColorClass(aqi) {
    if (aqi === null || aqi === undefined) return '';
    if (aqi <= 50) return 'good';
    if (aqi <= 100) return 'moderate';
    if (aqi <= 150) return 'unhealthy-sensitive';
    if (aqi <= 200) return 'unhealthy';
    if (aqi <= 300) return 'very-unhealthy';
    return 'hazardous';
}

/**
 * Format AQI level text for display
 * @param {string} level - The AQI level string
 * @returns {string} Formatted level text
 */
function formatAQILevel(level) {
    if (!level) return 'Unknown';
    return level.replace('Unhealthy for Sensitive Groups', 'Unhealthy*');
}

/**
 * Format day name for forecast cards
 * @param {Date} date - The date object
 * @returns {string} Day name (Today, Tomorrow, or day name)
 */
function formatDayName(date) {
    // Convert to user's preferred timezone for comparison
    const timezone = timezoneManager.getTimezone();
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    // Compare dates in user's preferred timezone
    const dateInTZ = date.toLocaleDateString('en-US', { timeZone: timezone });
    const todayInTZ = today.toLocaleDateString('en-US', { timeZone: timezone });
    const tomorrowInTZ = tomorrow.toLocaleDateString('en-US', { timeZone: timezone });
    
    if (dateInTZ === todayInTZ) {
        return 'Today';
    } else if (dateInTZ === tomorrowInTZ) {
        return 'Tomorrow';
    } else {
        return date.toLocaleDateString('en-US', { 
            weekday: 'short',
            timeZone: timezone
        });
    }
}

/**
 * Format time for chart labels based on range
 * @param {Date} date - The date object
 * @param {string} range - Time range (12h, 24h, 48h, 72h)
 * @returns {string} Formatted time string
 */
function formatTimeForChart(date, range) {
    const timezone = timezoneManager.getTimezone();
    const hour = date.toLocaleTimeString('en-US', { 
        hour: 'numeric',
        hour12: true,
        timeZone: timezone
    });
    
    if (range === '12h') {
        // For 12-hour view, show time only
        return hour;
    } else if (range === '24h' || range === '48h' || range === '72h') {
        // For longer ranges, show day and hour
        const day = date.toLocaleDateString('en-US', { 
            weekday: 'short',
            timeZone: timezone
        });
        
        // For midnight hours, emphasize the day transition
        const hourNum = date.toLocaleString('en-US', {
            hour: 'numeric',
            hour12: false,
            timeZone: timezone
        });
        
        if (hourNum === '0') {
            // Midnight - show day prominently
            return `${day} 12 AM`;
        } else {
            // Other hours - show abbreviated format
            return `${day.slice(0, 3)} ${hour}`;
        }
    } else {
        // Fallback: show time only
        return hour;
    }
}

/**
 * Format provider name for display
 * @param {string} provider - Provider identifier
 * @returns {string} Formatted provider name
 */
function formatProviderName(provider) {
    const providerMap = {
        'open-meteo': 'Open-Meteo',
        'epa-airnow': 'EPA AirNow',
        'iqair': 'IQAir'
    };
    return providerMap[provider] || provider;
}

window.Utils = {
    getAQILevelAndClass,
    formatTimestamp,
    formatChartLabel,
    fetchData,
    updateElementText,
    updateAQIElement,
    isMobile,
    debounce,
    getAQIColor,
    getAQIColorClass,
    formatAQILevel,
    formatDayName,
    formatTimeForChart,
    formatProviderName
};