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
        with patch('logging.basicConfig') as mock_basic, \
             patch('logging.getLogger') as mock_get_logger:
            
            mock_logger = mock_basic.return_value
            mock_get_logger.return_value = mock_logger
            
            logging_config.setup_logging()
            
            # Verify basicConfig was called
            mock_basic.assert_called_once()
            
            # Check that logging level and format were configured
            call_args = mock_basic.call_args[1]
            assert call_args['level'] == logging.INFO
            assert 'format' in call_args
            assert 'datefmt' in call_args
    
    def test_setup_logging_with_log_file(self):
        """Test setup_logging with file logging enabled"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            log_file = tmp_file.name
        
        try:
            with patch('logging.basicConfig') as mock_basic, \
                 patch('logging.getLogger') as mock_get_logger, \
                 patch('logging.FileHandler') as mock_file_handler:
                
                mock_logger = mock_basic.return_value
                mock_get_logger.return_value = mock_logger
                mock_handler = mock_file_handler.return_value
                
                logging_config.setup_logging(log_file=log_file)
                
                # Verify file handler was created
                mock_file_handler.assert_called_once_with(log_file)
                
                # Verify logger configuration
                mock_basic.assert_called_once()
                
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_setup_logging_debug_level(self):
        """Test setup_logging with debug level"""
        with patch('logging.basicConfig') as mock_basic:
            logging_config.setup_logging(level=logging.DEBUG)
            
            call_args = mock_basic.call_args[1]
            assert call_args['level'] == logging.DEBUG
    
    def test_setup_logging_file_handler_error(self):
        """Test setup_logging handles file handler creation errors"""
        with patch('logging.basicConfig') as mock_basic, \
             patch('logging.FileHandler') as mock_file_handler:
            
            mock_file_handler.side_effect = PermissionError("Access denied")
            
            # Should not raise exception, should fall back gracefully
            logging_config.setup_logging(log_file="/invalid/path/log.txt")
            
            # Basic config should still be called
            mock_basic.assert_called_once()
    
    def test_setup_logging_creates_log_directory(self):
        """Test setup_logging creates log directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "logs", "test.log")
            
            with patch('logging.basicConfig'), \
                 patch('logging.FileHandler') as mock_file_handler:
                
                logging_config.setup_logging(log_file=log_file)
                
                # Verify directory was created
                assert os.path.exists(os.path.dirname(log_file))
                
                # Verify file handler was attempted
                mock_file_handler.assert_called_once_with(log_file)