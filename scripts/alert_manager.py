#!/usr/bin/env python3
"""
Alert Manager CLI Tool
Command-line utility for managing the Pi Air Monitor alert system
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from config import config
from alert_integration import (send_test_alert, test_alert_notifications, 
                              get_alert_stats, get_alert_history, is_alerting_enabled)


def print_status():
    """Print current alert system status"""
    print("Pi Air Monitor - Alert System Status")
    print("=" * 40)
    
    enabled = is_alerting_enabled()
    print(f"Status: {'ENABLED' if enabled else 'DISABLED'}")
    
    if not enabled:
        print("\nTo enable alerts, update your config.json file:")
        print('  "alerts": { "enabled": true, ... }')
        return
    
    try:
        stats = get_alert_stats()
        
        print(f"Alerts in last 24h: {stats.get('total_alerts_24h', 0)}")
        print(f"Active rules: {stats.get('active_rules', 0)}")
        print(f"Notification methods: {stats.get('notification_methods', 0)}")
        print(f"Rate limits active: {stats.get('rate_limits_active', 0)}")
        
        # Show alert counts by type
        alert_types = stats.get('alert_types_24h', {})
        if alert_types:
            print("\nAlert types (24h):")
            for alert_type, count in alert_types.items():
                print(f"  {alert_type}: {count}")
        
        # Show alert counts by severity
        severity_counts = stats.get('severity_counts_24h', {})
        if severity_counts:
            print("\nAlert severity (24h):")
            for severity, count in severity_counts.items():
                print(f"  {severity}: {count}")
                
    except Exception as e:
        print(f"Error getting alert stats: {e}")


def print_history(limit=10):
    """Print recent alert history"""
    print(f"Recent Alert History (last {limit})")
    print("=" * 40)
    
    if not is_alerting_enabled():
        print("Alerting is disabled")
        return
    
    try:
        history = get_alert_history(limit)
        
        if not history:
            print("No alerts in history")
            return
        
        for record in history[-limit:]:  # Show most recent first
            alert = record['alert']
            sent_time = record['sent_time']
            
            # Format timestamp
            from datetime import datetime
            dt = datetime.fromtimestamp(sent_time)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\n[{time_str}] {alert['severity'].upper()}")
            print(f"  Type: {alert['alert_type']}")
            print(f"  Title: {alert['title']}")
            print(f"  Message: {alert['message']}")
            
    except Exception as e:
        print(f"Error getting alert history: {e}")


def test_alerts():
    """Test the alert system"""
    print("Testing Alert System")
    print("=" * 20)
    
    if not is_alerting_enabled():
        print("ERROR: Alerting is disabled")
        print("Enable alerts in config.json first")
        return False
    
    print("Sending test alert...")
    try:
        success = send_test_alert()
        if success:
            print("✓ Test alert sent successfully")
        else:
            print("✗ Failed to send test alert")
            return False
    except Exception as e:
        print(f"✗ Error sending test alert: {e}")
        return False
    
    print("\nTesting notification methods...")
    try:
        results = test_alert_notifications()
        for method, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {method}: {'OK' if success else 'FAILED'}")
    except Exception as e:
        print(f"Error testing notifications: {e}")
        return False
    
    return True


def validate_config():
    """Validate alert configuration"""
    print("Validating Alert Configuration")
    print("=" * 32)
    
    alerts_config = config.alerts
    
    if not alerts_config:
        print("✗ No alerts configuration found")
        return False
    
    print(f"✓ Alerts enabled: {alerts_config.get('enabled', False)}")
    
    # Check notifications
    notifications = alerts_config.get('notifications', {})
    print(f"✓ Notification methods configured: {len(notifications)}")
    
    for method, config_data in notifications.items():
        enabled = config_data.get('enabled', False)
        status = "✓" if enabled else "○"
        print(f"  {status} {method}: {'enabled' if enabled else 'disabled'}")
        
        # Validate specific notification configs
        if method == 'email' and enabled:
            smtp_config = config_data.get('smtp', {})
            required_fields = ['server', 'port', 'username', 'password']
            missing = [f for f in required_fields if not smtp_config.get(f)]
            if missing:
                print(f"    ✗ Missing SMTP fields: {', '.join(missing)}")
            else:
                print(f"    ✓ SMTP configuration complete")
        
        elif method == 'webhook' and enabled:
            if not config_data.get('url'):
                print(f"    ✗ Missing webhook URL")
            else:
                print(f"    ✓ Webhook URL configured")
    
    # Check rules
    rules = alerts_config.get('rules', [])
    enabled_rules = [r for r in rules if r.get('enabled', True)]
    print(f"✓ Alert rules: {len(enabled_rules)} enabled, {len(rules) - len(enabled_rules)} disabled")
    
    # Check rate limits
    rate_limits = alerts_config.get('rate_limits', {})
    print(f"✓ Rate limits configured: {len(rate_limits)}")
    
    return True


def show_templates():
    """Show available configuration templates"""
    print("Available Alert Configuration Templates")
    print("=" * 42)
    
    templates_dir = Path(__file__).parent.parent / 'config_templates'
    
    templates = {
        'alerts_basic.json': 'Basic alerting with log notifications only',
        'alerts_email_only.json': 'Email notifications for critical events',
        'alerts_webhook_slack.json': 'Slack webhook integration with emoji',
        'alerts_comprehensive.json': 'Full-featured alerting with all notification types'
    }
    
    for template_file, description in templates.items():
        template_path = templates_dir / template_file
        exists = "✓" if template_path.exists() else "✗"
        print(f"{exists} {template_file}")
        print(f"   {description}")
        if template_path.exists():
            print(f"   Path: {template_path}")
        print()


def apply_template(template_name):
    """Apply a configuration template"""
    templates_dir = Path(__file__).parent.parent / 'config_templates'
    template_path = templates_dir / template_name
    
    if not template_path.exists():
        print(f"Template not found: {template_path}")
        return False
    
    print(f"Applying template: {template_name}")
    
    try:
        # Load template
        with open(template_path, 'r') as f:
            template_config = json.load(f)
        
        # Load current config
        config_path = Path(__file__).parent.parent / 'config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                current_config = json.load(f)
        else:
            current_config = {}
        
        # Merge template into current config
        current_config.update(template_config)
        
        # Backup current config
        backup_path = config_path.with_suffix('.json.backup')
        if config_path.exists():
            import shutil
            shutil.copy2(config_path, backup_path)
            print(f"Backed up current config to: {backup_path}")
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(current_config, f, indent=2)
        
        print(f"✓ Applied template to: {config_path}")
        print("⚠  Remember to update notification settings with your credentials")
        
        return True
        
    except Exception as e:
        print(f"Error applying template: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Pi Air Monitor Alert Management Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status              # Show alert system status
  %(prog)s history             # Show recent alert history
  %(prog)s test                # Test alert system
  %(prog)s validate            # Validate configuration
  %(prog)s templates           # List available templates
  %(prog)s apply basic         # Apply basic template
        """
    )
    
    parser.add_argument('command', 
                       choices=['status', 'history', 'test', 'validate', 'templates', 'apply'],
                       help='Command to execute')
    
    parser.add_argument('template', nargs='?', 
                       help='Template name (for apply command)')
    
    parser.add_argument('--limit', type=int, default=10,
                       help='Number of history entries to show (default: 10)')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        print_status()
        
    elif args.command == 'history':
        print_history(args.limit)
        
    elif args.command == 'test':
        success = test_alerts()
        sys.exit(0 if success else 1)
        
    elif args.command == 'validate':
        success = validate_config()
        sys.exit(0 if success else 1)
        
    elif args.command == 'templates':
        show_templates()
        
    elif args.command == 'apply':
        if not args.template:
            parser.error("Template name required for apply command")
        
        # Add .json extension if not provided
        template_name = args.template
        if not template_name.endswith('.json'):
            template_name = f'alerts_{template_name}.json'
        
        success = apply_template(template_name)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()