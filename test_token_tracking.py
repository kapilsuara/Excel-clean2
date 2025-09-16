#!/usr/bin/env python3
"""
Test script to demonstrate token tracking and cost calculation
"""

from ai_service import get_ai_service
import json

def test_token_tracking():
    """Test the token tracking functionality"""
    
    print("=" * 60)
    print("TOKEN TRACKING & COST CALCULATION TEST")
    print("=" * 60)
    
    # Get AI service instance
    service = get_ai_service()
    
    # Check if service is available
    if not service.is_available():
        print("❌ No AI service available. Please configure API keys.")
        return
    
    print(f"✅ AI Service Status: {service.get_status()}")
    print()
    
    # Show initial token usage
    initial_usage = service.get_token_usage()
    print("📊 Initial Token Usage:")
    print(f"   Input Tokens: {initial_usage['input_tokens']:,}")
    print(f"   Output Tokens: {initial_usage['output_tokens']:,}")
    print(f"   Total Cost: ${initial_usage['total_cost']:.4f}")
    print()
    
    # Make a test API call
    print("🤖 Making a test API call...")
    prompt = "What is 2+2? Answer in one word only."
    response = service.call(prompt, max_tokens=10)
    
    if response:
        print(f"   Response: {response}")
        print()
        
        # Show updated token usage
        updated_usage = service.get_token_usage()
        print("📊 Updated Token Usage:")
        print(f"   Input Tokens: {updated_usage['input_tokens']:,}")
        print(f"   Output Tokens: {updated_usage['output_tokens']:,}")
        print(f"   Total Cost: ${updated_usage['total_cost']:.4f}")
        print(f"   Provider Used: {updated_usage['provider']}")
        print()
        
        # Calculate tokens used in this call
        tokens_used = updated_usage['total_tokens'] - initial_usage['total_tokens']
        cost_incurred = updated_usage['total_cost'] - initial_usage['total_cost']
        
        print("📈 This API Call:")
        print(f"   Tokens Used: {tokens_used:,}")
        print(f"   Cost Incurred: ${cost_incurred:.6f}")
        print()
        
        # Show pricing information
        if updated_usage['provider'] == 'anthropic':
            print("💰 Claude Pricing Information:")
            print("   Input: $3 per million tokens")
            print("   Output: $15 per million tokens")
        elif updated_usage['provider'] == 'openai':
            print("💰 OpenAI Pricing Information:")
            print("   Input: ~$30 per million tokens")
            print("   Output: ~$60 per million tokens")
        
        print()
        print("✅ Token tracking test completed successfully!")
        
        # Reset token usage
        print()
        print("🔄 Resetting token counter...")
        service.reset_token_usage()
        
        final_usage = service.get_token_usage()
        print(f"   Token counter reset: {final_usage['total_tokens']} tokens, ${final_usage['total_cost']:.4f}")
        
    else:
        print("❌ API call failed")

if __name__ == "__main__":
    test_token_tracking()