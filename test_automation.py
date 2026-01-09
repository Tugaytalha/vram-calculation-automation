"""
Test script to verify VRAM calculator automation works correctly
Tests with a small subset of configurations
"""

import time
from vram_calculator_automation import VRAMCalculatorAutomation

# Test with just 1 model, 1 batch size, 1 context, 2 user counts
TEST_MODELS = [
    ("Gemma-3-27B-IT (FP16)", "Gemma 3 27B", "FP16"),
]

TEST_BATCH_SIZES = [1]
TEST_CONTEXT_LENGTHS = [(2048, "2K")]
TEST_CONCURRENT_USERS = [1, 4]


def test_automation():
    """Test the automation with a small subset"""
    print("=" * 60)
    print("VRAM Calculator Automation - TEST MODE")
    print("=" * 60)
    
    automation = VRAMCalculatorAutomation(headless=False)
    
    try:
        automation.setup_driver()
        automation.navigate_to_calculator()
        
        # Switch to manual input mode
        automation.switch_to_manual_mode()
        
        total = len(TEST_MODELS) * len(TEST_BATCH_SIZES) * len(TEST_CONTEXT_LENGTHS) * len(TEST_CONCURRENT_USERS)
        current = 0
        
        print(f"\nTesting {total} configurations...")
        
        for model_display, model_site, quantization in TEST_MODELS:
            for batch_size in TEST_BATCH_SIZES:
                for context_tokens, context_label in TEST_CONTEXT_LENGTHS:
                    for users in TEST_CONCURRENT_USERS:
                        current += 1
                        print(f"\n[{current}/{total}]", end="")
                        
                        result = automation.collect_single_configuration(
                            model_display_name=model_display,
                            model_site_name=model_site,
                            quantization=quantization,
                            batch_size=batch_size,
                            context_length=context_tokens,
                            context_label=context_label,
                            concurrent_users=users
                        )
                        
                        if result:
                            automation.results.append(result)
                            print(f"  ✓ Success: VRAM={result['VRAM (GB)']} GB")
                        else:
                            print(f"  ✗ Failed")
                        
                        time.sleep(0.5)
        
        print(f"\n\nTest complete! Collected {len(automation.results)} configurations.")
        
        # Save test results
        if automation.results:
            automation.save_results("test_results.xlsx")
            
            # Print summary
            print("\n" + "=" * 60)
            print("Test Results:")
            print("=" * 60)
            for r in automation.results:
                print(f"  {r['Model']}, BS={r['Batch Size']}, CTX={r['Context Length']}, Users={r['Concurrent Users']}")
                print(f"    VRAM: {r['VRAM (GB)']} GB, Per-User: {r['Tokens per User (tok/s)']} tok/s, Total: {r['Total Throughput (tok/s)']} tok/s")
        
        # Keep browser open for manual verification
        print("\n\nBrowser will stay open for 30 seconds for manual verification...")
        print("Check if the values displayed match the extracted values.")
        time.sleep(30)
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if automation.driver:
            automation.driver.quit()


if __name__ == "__main__":
    test_automation()
