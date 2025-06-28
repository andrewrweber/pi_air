/**
 * Frontend tests for utils.js module
 */

// Test utility functions
tester.test('Utils module exists', () => {
    tester.assertNotNull(window.Utils, 'Utils module should be available');
});

tester.test('getAQILevelAndClass function works', () => {
    const utils = window.Utils;
    
    // Test Good range
    let result = utils.getAQILevelAndClass(25);
    tester.assertEqual(result.level, 'Good');
    tester.assertEqual(result.cssClass, 'aqi-good');
    
    // Test Moderate range
    result = utils.getAQILevelAndClass(75);
    tester.assertEqual(result.level, 'Moderate');
    tester.assertEqual(result.cssClass, 'aqi-moderate');
    
    // Test Unhealthy range
    result = utils.getAQILevelAndClass(175);
    tester.assertEqual(result.level, 'Unhealthy');
    tester.assertEqual(result.cssClass, 'aqi-unhealthy');
    
    // Test Hazardous range
    result = utils.getAQILevelAndClass(350);
    tester.assertEqual(result.level, 'Hazardous');
    tester.assertEqual(result.cssClass, 'aqi-hazardous');
});

tester.test('formatTimestamp function works', () => {
    const utils = window.Utils;
    
    // Test UTC timestamp formatting
    const testTimestamp = '2023-01-01 12:00:00';
    const formatted = utils.formatTimestamp(testTimestamp);
    
    tester.assert(formatted.includes('at'), 'Formatted timestamp should include "at"');
    tester.assert(formatted.includes('2023') || formatted.includes('1/1'), 'Should include date');
    tester.assert(formatted.includes('PDT') || formatted.includes('PST'), 'Should include timezone');
});

tester.test('formatChartLabel function works', () => {
    const utils = window.Utils;
    
    const testTimestamp = '2023-01-01T12:00:00Z';
    const formatted = utils.formatChartLabel(testTimestamp);
    
    tester.assert(typeof formatted === 'string', 'Should return a string');
    tester.assert(formatted.length > 0, 'Should not be empty');
});

tester.test('fetchData function exists', () => {
    const utils = window.Utils;
    tester.assertEqual(typeof utils.fetchData, 'function', 'fetchData should be a function');
});

tester.test('updateElementText function works', () => {
    const utils = window.Utils;
    
    // Create test element
    const testElement = document.createElement('div');
    testElement.id = 'test-element';
    document.body.appendChild(testElement);
    
    // Test updating element
    utils.updateElementText('test-element', 'Test Text');
    tester.assertEqual(testElement.textContent, 'Test Text');
    
    // Test with default value
    utils.updateElementText('non-existent-element', 'Test', 'Default');
    // Should not throw error
    
    // Clean up
    document.body.removeChild(testElement);
});

tester.test('isMobile function works', () => {
    const utils = window.Utils;
    const result = utils.isMobile();
    tester.assertEqual(typeof result, 'boolean', 'isMobile should return boolean');
});

tester.test('debounce function works', async () => {
    const utils = window.Utils;
    
    let callCount = 0;
    const testFn = () => { callCount++; };
    const debouncedFn = utils.debounce(testFn, 50);
    
    // Call multiple times quickly
    debouncedFn();
    debouncedFn();
    debouncedFn();
    
    // Should not have been called yet
    tester.assertEqual(callCount, 0, 'Function should not be called immediately');
    
    // Wait for debounce delay
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Should have been called once
    tester.assertEqual(callCount, 1, 'Function should be called once after delay');
});