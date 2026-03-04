#!/bin/bash
# Test the AgentHands API

API_URL="${API_URL:-http://localhost:8080}"

echo "🧪 Testing AgentHands API at $API_URL"
echo ""

# Health check
echo "1. Health check..."
curl -s "$API_URL/health" | jq .
echo ""

# Get capabilities
echo "2. Get capabilities..."
curl -s "$API_URL/v1/capabilities" | jq '.capabilities | length' | xargs echo "   Available capabilities:"
echo ""

# Create account
echo "3. Create account..."
ACCOUNT_RESPONSE=$(curl -s -X POST "$API_URL/v1/accounts" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"name": "Test Agent"}}')
echo "$ACCOUNT_RESPONSE" | jq .
echo ""

API_KEY=$(echo "$ACCOUNT_RESPONSE" | jq -r '.api_key')
ACCOUNT_ID=$(echo "$ACCOUNT_RESPONSE" | jq -r '.account_id')

if [ "$API_KEY" == "null" ]; then
    echo "❌ Failed to create account"
    exit 1
fi

echo "   API Key: $API_KEY"
echo "   Account ID: $ACCOUNT_ID"
echo ""

# Note: In production, you'd need to fund the account first
# For testing, we can add credits manually to the database

echo "4. Submit task (will fail without balance)..."
TASK_RESPONSE=$(curl -s -X POST "$API_URL/v1/tasks" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "capability": "browser.screenshot",
    "input": {"url": "https://example.com"}
  }')
echo "$TASK_RESPONSE" | jq .

echo ""
echo "✅ API is working!"
echo ""
echo "To fund the account for testing, run:"
echo "  sqlite3 data/agenthands.db \"UPDATE accounts SET balance_usdc = 10.0 WHERE account_id = '$ACCOUNT_ID'\""
