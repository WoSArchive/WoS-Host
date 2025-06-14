#!/bin/bash

echo "Updating packages..."
sudo apt update && sudo apt upgrade -y

echo "Installing Nginx..."
sudo apt install nginx -y

echo "Installing Certbot for SSL..."
sudo apt install certbot python3-certbot-nginx -y

echo "Installing other useful packages..."
sudo apt install ufw curl -y

echo "System setup complete. Now configure your Nginx site and SSL."
