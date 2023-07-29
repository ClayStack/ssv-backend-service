#!/bin/bash

cd src/test

# Get owner nonce
git clone https://github.com/bloxapp/ssv-scanner.git
cd ssv-scanner
yarn install

cd ..

# Clone the ssv-keys repository
git clone https://github.com/bloxapp/ssv-keys.git

# Install yarn globally
npm install -g yarn

# Navigate to the ssv-keys directory
cd /app/ssv-keys

# Checkout the v3 branch
git checkout v3

cd ssv-keys

# Install project dependencies using yarn
yarn install