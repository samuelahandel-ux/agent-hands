#!/bin/bash
# Update DuckDNS - run after getting token from duckdns.org

DOMAIN="agenthands"
TOKEN="${DUCKDNS_TOKEN:-your_token_here}"
IP=$(curl -s http://checkip.amazonaws.com)

curl -s "https://www.duckdns.org/update?domains=$DOMAIN&token=$TOKEN&ip=$IP"
echo ""
