#!/bin/bash
# Clean releases
echo "Removing existing devpack (if there is one)"
rm ./release/devpack.zip
echo "Copying zip file from others directory"
# Make a copy of the zip file
cp others/googleapiclient-googleoauth2tools-dev-package.zip release/devpack.zip
# Zip the src into the development package
zip -g release/devpack.zip lambda_function.py
