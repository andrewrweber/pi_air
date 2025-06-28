"""
Unit tests for logging configuration module
"""

import pytest
import tempfile
import os
import logging
from unittest.mock import patch, mock_open
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging_config


@pytest.mark.unit
class TestLoggingConfig:
    """Test logging configuration functionality"""
    
    def test_setup_logging_default(self):
        """Test setup_logging with default parameters"""
        with patch('logging.getLogger') as mock_get_logger, \
             patch('logging.StreamHandler') as mock_stream_handler:
            
            mock_logger = mock_get_logger.return_value
            mock_handler = mock_stream_handler.return_value
            
            result = logging_config.setup_logging()
            
            # Verify logger configuration
            mock_get_logger.assert_called()
            mock_logger.setLevel.assert_called_with(logging.INFO)
            mock_logger.addHandler.assert_called_with(mock_handler)
            
            # Verify console handler was created
            mock_stream_handler.assert_called_once()
            
            # Should return the logger
            assert result == mock_logger
    
    def test_setup_logging_with_log_file(self):
        """Test setup_logging with file logging enabled"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            log_file = tmp_file.name
        
        try:
            with patch('logging.getLogger') as mock_get_logger, \
                 patch('logging.StreamHandler') as mock_stream_handler, \
                 patch('logging.FileHandler') as mock_file_handler:
                
                mock_logger = mock_get_logger.return_value
                mock_file_handler_instance = mock_file_handler.return_value
                
                logging_config.setup_logging(log_file=log_file)
                
                # Verify file handler was created
                mock_file_handler.assert_called_once_with(log_file)
                
                # Verify both handlers were added to logger
                assert mock_logger.addHandler.call_count == 2
                
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_setup_logging_debug_level(self):
        """Test setup_logging with debug level"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            
            logging_config.setup_logging(log_level='DEBUG')
            
            # Verify debug level was set
            mock_logger.setLevel.assert_called_with(logging.DEBUG)
    
    def test_setup_logging_file_handler_error(self):
        """Test setup_logging handles file handler creation errors"""
        with patch('logging.getLogger') as mock_get_logger, \
             patch('logging.StreamHandler'), \
             patch('logging.FileHandler') as mock_file_handler:
            
            mock_file_handler.side_effect = PermissionError("Access denied")
            
            # Should raise the exception since no error handling in actual implementation
            with pytest.raises(PermissionError):
                logging_config.setup_logging(log_file="/invalid/path/log.txt")
    
    def test_setup_logging_specific_loggers(self):
        """Test setup_logging configures specific loggers"""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = mock_get_logger.return_value
            
            logging_config.setup_logging()
            
            # Verify specific loggers were configured
            expected_calls = [
                ('',),  # Root logger
                ('pms7003',),
                ('werkzeug',)
            ]
            
            # Check that getLogger was called for specific loggers
            assert mock_get_logger.call_count >= 3
            
            # Verify setLevel was called multiple times for different loggers
            assert mock_logger.setLevel.call_count >= 3