#!/usr/bin/env python3
"""
Smart Street Light Dashboard Server
Run this script on your Raspberry Pi to start the backend server.
"""

from backend import app
import os

if __name__ == '__main__':
    print("Starting Smart Street Light Dashboard Server...")
    print("Make sure you're running this on a Raspberry Pi with GPIO access")
    print("Server will be available at: http://localhost:5000")
    print("Dashboard: http://localhost:5000/static/index.html")

    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
