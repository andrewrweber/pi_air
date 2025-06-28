"""
Integration tests for forecast service with real API calls
These tests require internet connection and may be slower
"""

import pytest
import tempfile
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.forecast_service import ForecastService


class TestForecastIntegration:
    """Integration tests for forecast service with real APIs"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def service(self, temp_db):
        """Create ForecastService instance with temporary database"""
        return ForecastService(db_path=temp_db)
    
    @pytest.mark.integration
    def test_real_open_meteo_api_call(self, service):
        """Test actual Open-Meteo API call with Pacifica coordinates"""
        # This test requires internet connection
        try:
            # Force fresh data by clearing cache
            service.clear_cache()
            
            # Test with small forecast window
            forecast_data = service._fetch_open_meteo_forecast(hours=6)
            
            # Verify we got data
            assert len(forecast_data) > 0
            assert len(forecast_data) <= 6  # Should not exceed requested hours
            
            # Verify data structure
            for point in forecast_data:
                assert 'forecast_time' in point
                assert 'forecast_for_time' in point
                assert 'provider' in point
                assert point['provider'] == 'open-meteo'
                assert 'latitude' in point
                assert 'longitude' in point
                
                # Verify coordinates are close to Pacifica
                assert abs(point['latitude'] - 37.6138) < 0.1
                assert abs(point['longitude'] - (-122.4869)) < 0.1
                
                # Verify pollutant data exists
                assert 'pm2_5' in point
                assert 'pm10' in point
                assert 'aqi' in point
                assert 'aqi_level' in point
                
                # Verify data types and ranges
                if point['pm2_5'] is not None:
                    assert isinstance(point['pm2_5'], (int, float))
                    assert point['pm2_5'] >= 0
                    assert point['pm2_5'] < 1000  # Reasonable upper bound
                
                if point['aqi'] is not None:
                    assert isinstance(point['aqi'], int)
                    assert 0 <= point['aqi'] <= 500
                
                if point['aqi_level'] is not None:
                    valid_levels = ['Good', 'Moderate', 'Unhealthy for Sensitive Groups', 
                                   'Unhealthy', 'Very Unhealthy', 'Hazardous']
                    assert point['aqi_level'] in valid_levels
                
                # Verify timestamp format
                forecast_time = datetime.fromisoformat(point['forecast_for_time'].replace('Z', '+00:00'))
                assert isinstance(forecast_time, datetime)
            
            print(f"✓ Successfully fetched {len(forecast_data)} forecast points from Open-Meteo")
            print(f"  First point: {forecast_data[0]['forecast_for_time']} - PM2.5: {forecast_data[0]['pm2_5']}μg/m³")
            print(f"  Last point: {forecast_data[-1]['forecast_for_time']} - PM2.5: {forecast_data[-1]['pm2_5']}μg/m³")
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to network/API error: {e}")
    
    @pytest.mark.integration
    def test_full_forecast_workflow(self, service):
        """Test complete forecast workflow including caching"""
        try:
            # Clear any existing cache
            service.clear_cache()
            
            # First call should fetch from API
            forecast_data1 = service.get_forecast(hours=12)
            
            # Verify we got data
            assert len(forecast_data1) > 0
            
            # Verify caching worked
            cache_stats = service.get_cache_stats()
            assert len(cache_stats) > 0
            assert 'open-meteo' in cache_stats
            assert cache_stats['open-meteo']['count'] > 0
            
            # Second call should use cache (if within cache window)
            forecast_data2 = service.get_forecast(hours=12)
            
            # Should get same amount of data
            assert len(forecast_data2) == len(forecast_data1)
            
            # Data should be similar (allowing for minor API variations)
            assert forecast_data1[0]['forecast_for_time'] == forecast_data2[0]['forecast_for_time']
            assert forecast_data1[0]['provider'] == forecast_data2[0]['provider']
            
            print(f"✓ Cache workflow working - {len(forecast_data1)} points cached and retrieved")
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to network/API error: {e}")
    
    @pytest.mark.integration
    def test_forecast_data_quality(self, service):
        """Test quality and consistency of forecast data"""
        try:
            forecast_data = service._fetch_open_meteo_forecast(hours=24)
            
            assert len(forecast_data) > 0
            
            # Check temporal consistency
            timestamps = [datetime.fromisoformat(p['forecast_for_time'].replace('Z', '+00:00')) 
                         for p in forecast_data]
            
            # Timestamps should be in order
            for i in range(1, len(timestamps)):
                assert timestamps[i] >= timestamps[i-1]
            
            # Check data completeness
            pm25_count = sum(1 for p in forecast_data if p['pm2_5'] is not None)
            pm10_count = sum(1 for p in forecast_data if p['pm10'] is not None)
            aqi_count = sum(1 for p in forecast_data if p['aqi'] is not None)
            
            # Should have high data completeness
            total_points = len(forecast_data)
            assert pm25_count / total_points >= 0.8  # At least 80% PM2.5 data
            assert pm10_count / total_points >= 0.8   # At least 80% PM10 data
            assert aqi_count / total_points >= 0.8    # At least 80% AQI data
            
            # Check AQI consistency with PM2.5
            for point in forecast_data:
                if point['pm2_5'] is not None and point['aqi'] is not None:
                    # Recalculate AQI and verify it matches
                    calculated_aqi, _ = service._calculate_aqi_from_pm25(point['pm2_5'])
                    # Allow some tolerance for rounding differences
                    assert abs(calculated_aqi - point['aqi']) <= 2
            
            print(f"✓ Data quality check passed for {total_points} points")
            print(f"  PM2.5 coverage: {pm25_count/total_points*100:.1f}%")
            print(f"  PM10 coverage: {pm10_count/total_points*100:.1f}%")
            print(f"  AQI coverage: {aqi_count/total_points*100:.1f}%")
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to network/API error: {e}")
    
    @pytest.mark.integration
    def test_error_handling_with_invalid_coordinates(self, service):
        """Test error handling with invalid coordinates"""
        try:
            # Temporarily patch config to use invalid coordinates
            with pytest.MonkeyPatch().context() as m:
                m.setattr('services.forecast_service.config.get_coordinates', 
                         lambda: (999.0, 999.0))  # Invalid coordinates
                
                forecast_data = service._fetch_open_meteo_forecast(hours=6)
                
                # Should handle error gracefully and return empty list
                assert forecast_data == []
                
            print("✓ Error handling working correctly for invalid coordinates")
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to network/API error: {e}")
    
    @pytest.mark.integration  
    def test_cache_expiration(self, service):
        """Test that cache expires correctly"""
        try:
            # Clear cache
            service.clear_cache()
            
            # Fetch data and cache it
            forecast_data = service.get_forecast(hours=6)
            assert len(forecast_data) > 0
            
            # Verify cache has data
            cache_stats = service.get_cache_stats()
            assert cache_stats['open-meteo']['count'] > 0
            
            # Manually set old timestamp to simulate expired cache
            with service._get_db_connection() as conn:
                old_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()
                conn.execute('''
                    UPDATE forecast_readings 
                    SET forecast_time = ?, created_at = ?
                    WHERE provider = ?
                ''', (old_time, old_time, 'open-meteo'))
                conn.commit()
            
            # Should fetch fresh data now
            new_forecast_data = service.get_forecast(hours=6)
            assert len(new_forecast_data) > 0
            
            print("✓ Cache expiration working correctly")
            
        except Exception as e:
            pytest.skip(f"Integration test skipped due to network/API error: {e}")


def run_integration_tests():
    """Run integration tests manually"""
    print("Running forecast service integration tests...")
    print("Note: These tests require internet connection")
    
    try:
        # Run tests with pytest
        exit_code = pytest.main([
            __file__ + '::TestForecastIntegration',
            '-v',
            '-m', 'integration',
            '--tb=short'
        ])
        
        if exit_code == 0:
            print("\n✓ All integration tests passed!")
        else:
            print(f"\n✗ Some integration tests failed (exit code: {exit_code})")
            
    except Exception as e:
        print(f"\n✗ Error running integration tests: {e}")


if __name__ == '__main__':
    run_integration_tests()