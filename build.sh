#!/bin/bash
# Clean releases
echo "Removing existing deployment-package (if there is one)"
rm ./release/deployment-package.zip
echo "Copying zip file from others directory"
# Make a copy of the zip file
cp others/googleapiclient-googleoauth2tools-dev-package.zip release/deployment-package.zip
# Zip the src into the development package
zip -g release/deployment-package.zip lambda_function.py
