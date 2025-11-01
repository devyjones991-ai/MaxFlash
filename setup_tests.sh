#!/bin/bash
# Setup script for installing test dependencies

echo "Installing test dependencies..."
pip install pytest pytest-cov pytest-mock

echo "Running tests..."
pytest tests/ -v

echo "Tests completed!"
