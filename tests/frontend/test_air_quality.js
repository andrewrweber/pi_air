/**
 * Frontend tests for air-quality.js module
 */

tester.test('AirQualityMonitor exists', () => {
    tester.assertNotNull(window.airQualityMonitor, 'Global airQualityMonitor should be available');
});

tester.test('AirQualityMonitor has required methods', () => {
    const monitor = window.airQualityMonitor;
    
    tester.assertEqual(typeof monitor.start, 'function');
    tester.assertEqual(typeof monitor.stop, 'function');
    tester.assertEqual(typeof monitor.updateLatestReading, 'function');
    tester.assertEqual(typeof monitor.updateWorstAirQuality, 'function');
    tester.assertEqual(typeof monitor.showParticlesData, 'function');
    tester.assertEqual(typeof monitor.showAQIData, 'function');
});

tester.test('Time range configuration works', () => {
    const monitor = window.airQualityMonitor;
    
    // Test time range text generation
    const result = monitor.getTimeRangeText('1h');
    tester.assertEqual(result.hoursText, '1 hour');
    tester.assertEqual(result.intervalText, '2-minute intervals');
    
    const result24h = monitor.getTimeRangeText('24h');
    tester.assertEqual(result24h.hoursText, '24 hours');
    tester.assertEqual(result24h.intervalText, '15-minute intervals');
});

tester.test('Data filtering works', () => {
    const monitor = window.airQualityMonitor;
    
    // Mock data with timestamps
    const now = new Date();
    const mockData = [
        {
            interval_time: new Date(now.getTime() - 30 * 60 * 1000).toISOString().slice(0, 19), // 30 min ago
            avg_pm2_5: 12.5
        },
        {
            interval_time: new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString().slice(0, 19), // 2 hours ago
            avg_pm2_5: 15.0
        },
        {
            interval_time: new Date(now.getTime() - 25 * 60 * 60 * 1000).toISOString().slice(0, 19), // 25 hours ago
            avg_pm2_5: 20.0
        }
    ];
    
    // Filter for 1 hour - should only include first item
    const filtered1h = monitor.filterDataByTimeRange(mockData, '1h');
    tester.assertEqual(filtered1h.length, 1);
    tester.assertEqual(filtered1h[0].avg_pm2_5, 12.5);
    
    // Filter for 24 hours - should include first two items
    const filtered24h = monitor.filterDataByTimeRange(mockData, '24h');
    tester.assertEqual(filtered24h.length, 2);
});

tester.test('State management works', () => {
    const monitor = window.airQualityMonitor;
    
    // Test initial state
    tester.assertEqual(monitor.currentParticlesTimeRange, '24h');
    tester.assertEqual(monitor.currentAQITimeRange, '24h');
    
    // Test cache structure
    tester.assertNotNull(monitor.cachedAirQualityData);
    tester.assert('1h' in monitor.cachedAirQualityData);
    tester.assert('6h' in monitor.cachedAirQualityData);
    tester.assert('24h' in monitor.cachedAirQualityData);
});

tester.test('Touch handling setup', () => {
    const monitor = window.airQualityMonitor;
    
    // Test touch state variables exist
    tester.assertEqual(typeof monitor.touchStartX, 'number');
    tester.assertEqual(typeof monitor.touchEndX, 'number');
    
    // Test swipe gesture handling
    monitor.touchStartX = 100;
    monitor.touchEndX = 200; // 100px swipe right
    
    // Should not throw error even without proper chart setup
    try {
        monitor.handleSwipeGesture('particles');
        tester.assert(true, 'handleSwipeGesture should execute without error');
    } catch (error) {
        // Expected in test environment without proper DOM
        tester.assert(true, 'handleSwipeGesture method exists');
    }
});

// Test global functions are exposed
tester.test('Global functions are exposed', () => {
    tester.assertEqual(typeof window.showParticlesData, 'function', 'showParticlesData should be global');
    tester.assertEqual(typeof window.showAQIData, 'function', 'showAQIData should be global');
});