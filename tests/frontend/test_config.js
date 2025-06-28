/**
 * Frontend tests for config.js module
 */

tester.test('AppConfig module exists', () => {
    tester.assertNotNull(window.AppConfig, 'AppConfig module should be available');
});

tester.test('API endpoints are defined', () => {
    const config = window.AppConfig;
    
    tester.assertNotNull(config.API_ENDPOINTS, 'API_ENDPOINTS should be defined');
    tester.assertEqual(typeof config.API_ENDPOINTS.system, 'string');
    tester.assertEqual(typeof config.API_ENDPOINTS.stats, 'string');
    tester.assertEqual(typeof config.API_ENDPOINTS.airQualityLatest, 'string');
    tester.assertEqual(typeof config.API_ENDPOINTS.airQualityWorst24h, 'string');
    tester.assertEqual(typeof config.API_ENDPOINTS.airQualityHistory, 'string');
});

tester.test('Chart colors are defined', () => {
    const config = window.AppConfig;
    
    tester.assertNotNull(config.CHART_COLORS, 'CHART_COLORS should be defined');
    tester.assertEqual(typeof config.CHART_COLORS.primary, 'string');
    tester.assertEqual(typeof config.CHART_COLORS.secondary, 'string');
    tester.assert(config.CHART_COLORS.primary.startsWith('rgb'), 'Colors should be RGB format');
});

tester.test('AQI levels are defined', () => {
    const config = window.AppConfig;
    
    tester.assertNotNull(config.AQI_LEVELS, 'AQI_LEVELS should be defined');
    tester.assertNotNull(config.AQI_LEVELS.good, 'Good AQI level should be defined');
    tester.assertNotNull(config.AQI_LEVELS.moderate, 'Moderate AQI level should be defined');
    tester.assertNotNull(config.AQI_LEVELS.hazardous, 'Hazardous AQI level should be defined');
    
    // Check structure
    tester.assertEqual(typeof config.AQI_LEVELS.good.max, 'number');
    tester.assertEqual(typeof config.AQI_LEVELS.good.label, 'string');
    tester.assertEqual(typeof config.AQI_LEVELS.good.color, 'string');
});

tester.test('Update intervals are defined', () => {
    const config = window.AppConfig;
    
    tester.assertNotNull(config.UPDATE_INTERVALS, 'UPDATE_INTERVALS should be defined');
    tester.assertEqual(typeof config.UPDATE_INTERVALS.stats, 'number');
    tester.assertEqual(typeof config.UPDATE_INTERVALS.airQuality, 'number');
    tester.assertEqual(typeof config.UPDATE_INTERVALS.charts, 'number');
    
    // Check reasonable values
    tester.assert(config.UPDATE_INTERVALS.stats > 0, 'Stats interval should be positive');
    tester.assert(config.UPDATE_INTERVALS.airQuality > 0, 'Air quality interval should be positive');
});

tester.test('Mobile breakpoint is defined', () => {
    const config = window.AppConfig;
    
    tester.assertEqual(typeof config.MOBILE_BREAKPOINT, 'number');
    tester.assert(config.MOBILE_BREAKPOINT > 0, 'Mobile breakpoint should be positive');
});

tester.test('Chart defaults are defined', () => {
    const config = window.AppConfig;
    
    tester.assertNotNull(config.CHART_DEFAULTS, 'CHART_DEFAULTS should be defined');
    tester.assertEqual(typeof config.CHART_DEFAULTS.responsive, 'boolean');
    tester.assertEqual(typeof config.CHART_DEFAULTS.maintainAspectRatio, 'boolean');
    tester.assertNotNull(config.CHART_DEFAULTS.plugins, 'Chart plugins should be defined');
    tester.assertNotNull(config.CHART_DEFAULTS.scales, 'Chart scales should be defined');
});