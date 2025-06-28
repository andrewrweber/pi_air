/**
 * Utility functions for Pi Air Monitor
 */

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
 * Format timestamp for display in Pacific Time
 * @param {string} timestamp - UTC timestamp from database
 * @returns {string} Formatted timestamp string
 */
function formatTimestamp(timestamp) {
    // SQLite CURRENT_TIMESTAMP is in UTC format: 'YYYY-MM-DD HH:MM:SS'
    // Add 'Z' to explicitly indicate UTC timezone for proper parsing
    const utcTimestamp = timestamp.includes('Z') ? timestamp : timestamp + 'Z';
    const utcDate = new Date(utcTimestamp);
    
    // Format directly to Pacific Time using the timezone option
    const formattedDate = utcDate.toLocaleDateString('en-US', {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
        timeZone: 'America/Los_Angeles'
    });
    
    const formattedTime = utcDate.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'America/Los_Angeles'
    });
    
    // Get the timezone abbreviation (PDT or PST)
    const timeZoneAbbr = utcDate.toLocaleDateString('en-US', {
        timeZoneName: 'short',
        timeZone: 'America/Los_Angeles'
    }).split(', ')[1];
    
    return `${formattedDate} at ${formattedTime} ${timeZoneAbbr}`;
}

/**
 * Format a date for chart labels
 * @param {string} timestamp - Timestamp to format
 * @param {boolean} includeSeconds - Whether to include seconds
 * @returns {string} Formatted time string
 */
function formatChartLabel(timestamp, includeSeconds = false) {
    const date = new Date(timestamp);
    const options = {
        hour: 'numeric',
        minute: '2-digit',
        timeZone: 'America/Los_Angeles',
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
window.Utils = {
    getAQILevelAndClass,
    formatTimestamp,
    formatChartLabel,
    fetchData,
    updateElementText,
    updateAQIElement,
    isMobile,
    debounce
};