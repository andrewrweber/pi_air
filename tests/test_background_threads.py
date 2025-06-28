"""
Unit tests for background thread functionality in app.py
"""

import pytest
import time
import threading
from unittest.mock import patch, Mock, MagicMock
from collections import deque
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import app


@pytest.mark.unit
class TestBackgroundThreads:
    """Test background thread functionality"""
    
    def test_temperature_history_initialization(self):
        """Test temperature history deque initialization"""
        # Test that temperature_history is properly initialized
        assert hasattr(app, 'temperature_history')
        assert isinstance(app.temperature_history, deque)
        assert app.temperature_history.maxlen == 120
        
        # Test thread lock exists
        assert hasattr(app, 'temperature_lock')
        assert isinstance(app.temperature_lock, threading.Lock)
    
    def test_latest_temperature_storage(self):
        """Test latest temperature variable storage"""
        # Test that latest_temperature exists and can be modified
        assert hasattr(app, 'latest_temperature')
        
        # Test thread-safe access
        with app.temperature_lock:
            original_temp = app.latest_temperature
            app.latest_temperature = 55.5
            assert app.latest_temperature == 55.5
            app.latest_temperature = original_temp
    
    @patch('app.get_cpu_temperature')
    @patch('app.database.insert_system_reading')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_sample_temperature_and_system_stats_success(self, mock_memory, mock_cpu_percent, 
                                                       mock_insert, mock_get_temp):
        """Test successful system stats sampling"""
        # Setup mocks
        mock_get_temp.return_value = 56.7
        mock_cpu_percent.return_value = 25.5
        
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 42.3
        mock_memory.return_value = mock_memory_obj
        
        # Clear temperature history for clean test
        app.temperature_history.clear()
        
        # Mock time.sleep to control the infinite loop
        def side_effect_sleep(duration):
            if side_effect_sleep.call_count >= 2:  # Stop after 2 iterations
                raise KeyboardInterrupt()
            side_effect_sleep.call_count += 1
        side_effect_sleep.call_count = 0
        
        with patch('time.sleep', side_effect=side_effect_sleep):
            try:
                app.sample_temperature_and_system_stats()
            except KeyboardInterrupt:
                pass  # Expected to stop the loop
            
            # Verify temperature was sampled
            mock_get_temp.assert_called()
            
            # Verify latest temperature was updated
            assert app.latest_temperature == 56.7
            
            # Verify temperature was added to history
            assert len(app.temperature_history) > 0
    
    @patch('app.get_cpu_temperature')
    def test_sample_temperature_and_system_stats_temp_failure(self, mock_get_temp):
        """Test system stats sampling when temperature fails"""
        # Setup mock to return None (temperature read failure)
        mock_get_temp.return_value = None
        
        original_temp = app.latest_temperature
        app.temperature_history.clear()
        
        # Mock time.sleep to control the infinite loop
        def side_effect_sleep(duration):
            if side_effect_sleep.call_count >= 1:  # Stop after 1 iteration
                raise KeyboardInterrupt()
            side_effect_sleep.call_count += 1
        side_effect_sleep.call_count = 0
        
        with patch('time.sleep', side_effect=side_effect_sleep):
            try:
                app.sample_temperature_and_system_stats()
            except KeyboardInterrupt:
                pass  # Expected to stop the loop
            
            # Verify temperature read was attempted
            mock_get_temp.assert_called()
            
            # Latest temperature should remain unchanged when read fails
            assert app.latest_temperature == original_temp
            
            # Database write should be skipped when temp is None (verified by no exception)
            # The actual implementation skips DB write when temp is None
    
    @patch('app.database.insert_system_reading')
    @patch('app.get_cpu_temperature')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_database_write_interval(self, mock_memory, mock_cpu_percent, 
                                   mock_get_temp, mock_insert):
        """Test that database writes happen at correct intervals"""
        mock_get_temp.return_value = 55.0
        mock_cpu_percent.return_value = 30.0
        
        mock_memory_obj = Mock()
        mock_memory_obj.percent = 50.0
        mock_memory.return_value = mock_memory_obj
        
        # Mock time to control write intervals
        with patch('time.time') as mock_time:
            # Simulate time progression to trigger database write
            mock_time.side_effect = [0, 5, 10, 35]  # 30+ second gap triggers write
            
            # Mock time.sleep to control the infinite loop
            def side_effect_sleep(duration):
                if side_effect_sleep.call_count >= 2:  # Stop after triggering DB write
                    raise KeyboardInterrupt()
                side_effect_sleep.call_count += 1
            side_effect_sleep.call_count = 0
            
            with patch('time.sleep', side_effect=side_effect_sleep):
                try:
                    app.sample_temperature_and_system_stats()
                except KeyboardInterrupt:
                    pass  # Expected to stop the loop
                
                # Database insert should have been called
                mock_insert.assert_called()
                
                # Verify correct parameters were passed
                call_args = mock_insert.call_args[1]
                assert call_args['cpu_temp'] == 55.0
                assert call_args['cpu_usage'] == 30.0
                assert call_args['memory_usage'] == 50.0
    
    @patch('app.database.insert_system_reading')
    def test_database_write_error_handling(self, mock_insert):
        """Test error handling when database write fails"""
        # Setup mock to raise exception
        mock_insert.side_effect = Exception("Database write failed")
        
        with patch('app.get_cpu_temperature', return_value=55.0), \
             patch('psutil.cpu_percent', return_value=25.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('time.time', side_effect=[0, 35]):  # Trigger write
            
            mock_memory_obj = Mock()
            mock_memory_obj.percent = 40.0
            mock_memory.return_value = mock_memory_obj
            
            # Mock time.sleep to control the infinite loop
            def side_effect_sleep(duration):
                if side_effect_sleep.call_count >= 2:  # Stop after triggering DB write
                    raise KeyboardInterrupt()
                side_effect_sleep.call_count += 1
            side_effect_sleep.call_count = 0
            
            with patch('time.sleep', side_effect=side_effect_sleep):
                # Should not raise exception even if database write fails
                try:
                    app.sample_temperature_and_system_stats()
                except KeyboardInterrupt:
                    pass  # Expected to stop the loop
                
                # Database insert should have been attempted
                mock_insert.assert_called()
    
    def test_temperature_history_maxlen_behavior(self):
        """Test that temperature history respects maxlen limit"""
        app.temperature_history.clear()
        
        # Add more than maxlen items
        for i in range(150):
            timestamp = f"2023-01-01T10:{i:02d}:00"
            app.temperature_history.append((timestamp, float(i)))
        
        # Should be limited to maxlen
        assert len(app.temperature_history) == 120
        
        # Should contain the most recent entries
        assert app.temperature_history[-1][1] == 149.0  # Last entry
        assert app.temperature_history[0][1] == 30.0    # First entry after rotation
    
    def test_thread_safety_temperature_access(self):
        """Test thread-safe access to temperature data"""
        app.temperature_history.clear()
        
        def writer_thread():
            for i in range(10):
                with app.temperature_lock:
                    timestamp = f"2023-01-01T10:{i:02d}:00"
                    app.temperature_history.append((timestamp, float(i)))
                    app.latest_temperature = float(i)
                time.sleep(0.001)
        
        def reader_thread():
            readings = []
            for i in range(10):
                with app.temperature_lock:
                    readings.append(len(app.temperature_history))
                    temp = app.latest_temperature
                time.sleep(0.001)
            return readings
        
        # Start both threads
        writer = threading.Thread(target=writer_thread)
        reader = threading.Thread(target=reader_thread)
        
        writer.start()
        reader.start()
        
        writer.join(timeout=1.0)
        reader.join(timeout=1.0)
        
        # Both threads should complete without deadlock
        assert not writer.is_alive()
        assert not reader.is_alive()
        
        # Final state should be consistent
        assert len(app.temperature_history) == 10
        assert app.latest_temperature == 9.0