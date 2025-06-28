/**
 * Main application controller for Pi Air Monitor
 */

class PiAirMonitorApp {
    constructor() {
        this.currentTab = 'air-quality';  // Default to air-quality tab like original
        this.hardwareMonitor = null;
        this.airQualityMonitor = null;
        this.isInitialized = false;
    }

    /**
     * Initialize the application
     */
    async init() {
        if (this.isInitialized) return;
        
        try {
            // Wait for all dependencies to load
            await this.waitForDependencies();
            
            // Initialize monitors
            this.hardwareMonitor = window.hardwareMonitor;
            this.airQualityMonitor = window.airQualityMonitor;
            
            // Set up tab navigation
            this.setupTabNavigation();
            
            // Start monitoring
            this.hardwareMonitor.start();
            this.airQualityMonitor.start();
            
            // Show initial tab (air-quality is default)
            this.showTab('air-quality');
            
            // Set up global error handling
            this.setupErrorHandling();
            
            this.isInitialized = true;
            console.log('Pi Air Monitor initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize Pi Air Monitor:', error);
            this.showError('Failed to initialize application. Please refresh the page.');
        }
    }

    /**
     * Wait for all dependencies to be loaded
     */
    async waitForDependencies() {
        const maxWaitTime = 5000; // 5 seconds
        const checkInterval = 100; // 100ms
        const startTime = Date.now();
        
        while (Date.now() - startTime < maxWaitTime) {
            if (window.AppConfig && 
                window.Utils && 
                window.chartManager && 
                window.hardwareMonitor && 
                window.airQualityMonitor &&
                typeof Chart !== 'undefined') {
                return;
            }
            await new Promise(resolve => setTimeout(resolve, checkInterval));
        }
        
        throw new Error('Dependencies not loaded in time');
    }

    /**
     * Set up tab navigation
     */
    setupTabNavigation() {
        // Add click listeners to tab buttons
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const tabName = e.target.getAttribute('data-tab');
                if (tabName) {
                    this.showTab(tabName);
                }
            });
        });
        
        // Expose showTab to global scope for backward compatibility
        window.showTab = (tabName) => this.showTab(tabName);
    }

    /**
     * Show a specific tab
     * @param {string} tabName - Name of the tab to show
     */
    showTab(tabName) {
        // Hide all tab contents
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => content.classList.remove('active'));
        
        // Deactivate all tab buttons
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => button.classList.remove('active'));
        
        // Show selected tab content
        const selectedContent = document.getElementById(`${tabName}-tab`);
        if (selectedContent) {
            selectedContent.classList.add('active');
        }
        
        // Activate selected tab button - find by onclick attribute content
        const allButtons = document.querySelectorAll('.tab-button');
        allButtons.forEach(button => {
            const onclick = button.getAttribute('onclick');
            if (onclick && onclick.includes(`'${tabName}'`)) {
                button.classList.add('active');
            }
        });
        
        this.currentTab = tabName;
        
        // Trigger chart resize on tab change
        setTimeout(() => {
            window.dispatchEvent(new Event('resize'));
        }, 100);
        
        // If switching to air quality tab, update current readings immediately
        if (tabName === 'air-quality') {
            if (this.airQualityMonitor) {
                this.airQualityMonitor.updateLatestReading();
                this.airQualityMonitor.updateWorstAirQuality();
            }
        }
    }

    /**
     * Set up global error handling
     */
    setupErrorHandling() {
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            // Don't show error messages for expected issues like network failures
            if (!event.message.includes('fetch')) {
                this.showError('An error occurred. Check the console for details.');
            }
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            // Don't show error messages for expected issues
            if (!event.reason.message || !event.reason.message.includes('fetch')) {
                this.showError('An error occurred. Check the console for details.');
            }
        });
    }

    /**
     * Show error message to user
     * @param {string} message - Error message to display
     */
    showError(message) {
        // Create error toast if it doesn't exist
        let errorToast = document.getElementById('error-toast');
        if (!errorToast) {
            errorToast = document.createElement('div');
            errorToast.id = 'error-toast';
            errorToast.className = 'error-toast';
            document.body.appendChild(errorToast);
        }
        
        errorToast.textContent = message;
        errorToast.classList.add('show');
        
        // Hide after 5 seconds
        setTimeout(() => {
            errorToast.classList.remove('show');
        }, 5000);
    }

    /**
     * Clean up resources
     */
    destroy() {
        if (this.hardwareMonitor) {
            this.hardwareMonitor.stop();
        }
        if (this.airQualityMonitor) {
            this.airQualityMonitor.stop();
        }
        if (window.chartManager) {
            window.chartManager.destroy();
        }
        this.isInitialized = false;
    }
}

// Create and initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.piAirMonitorApp = new PiAirMonitorApp();
    window.piAirMonitorApp.init();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.piAirMonitorApp) {
        window.piAirMonitorApp.destroy();
    }
});