#!/bin/bash
# Ensure pip is installed
if ! command -v pip &> /dev/null
then
    echo "pip could not be found, installing pip..."
    apt-get update && apt-get install -y python3-pip
fi

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Django management commands or other build steps
python manage.py collectstatic --noinput
python manage.py migrate

pip install -r requirements.txt
python3.9 manage.py collectstatic
