"""
Quick test script to verify a single model selection works
"""

import time
from vram_calculator_automation import VRAMCalculatorAutomation


def quick_test():
    """Quick test with a single configuration"""
    print("=" * 60)
    print("VRAM Calculator - QUICK TEST")
    print("=" * 60)
    
    automation = VRAMCalculatorAutomation(headless=False)
    
    try:
        automation.setup_driver()
        automation.navigate_to_calculator()
        
        # Switch to manual input mode
        automation.switch_to_manual_mode()
        
        # Select hardware
        automation.select_hardware("H200 (141GB)")
        time.sleep(1)
        
        # Test a single configuration
        print("\n" + "=" * 40)
        print("TEST 1: Gemma 3 27B, FP16, BS=1, 2K, 1 user")
        print("=" * 40)
        
        result1 = automation.collect_single_configuration(
            model_display_name="Gemma-3-27B-IT (FP16)",
            model_site_name="Gemma 3 27B",
            quantization="FP16",
            batch_size=1,
            context_length=2048,
            context_label="2K",
            concurrent_users=1
        )
        
        print(f"\nResult 1: {result1}")
        
        # Test second configuration with different users
        print("\n" + "=" * 40)
        print("TEST 2: Same model, but 4 users")
        print("=" * 40)
        
        result2 = automation.collect_single_configuration(
            model_display_name="Gemma-3-27B-IT (FP16)",
            model_site_name="Gemma 3 27B",
            quantization="FP16",
            batch_size=1,
            context_length=2048,
            context_label="2K",
            concurrent_users=4
        )
        
        print(f"\nResult 2: {result2}")
        
        # Compare results
        print("\n" + "=" * 60)
        print("COMPARISON")
        print("=" * 60)
        
        if result1 and result2:
            vram1 = result1.get('VRAM (GB)')
            vram2 = result2.get('VRAM (GB)')
            
            print(f"VRAM with 1 user:  {vram1} GB")
            print(f"VRAM with 4 users: {vram2} GB")
            
            if vram1 and vram2:
                if vram1 != vram2:
                    print(f"\n✓ SUCCESS: VRAM values differ as expected!")
                    print(f"  Difference: {vram2 - vram1:.2f} GB")
                else:
                    print(f"\n⚠ WARNING: VRAM values are the same - may indicate an issue")
            
            if vram1 and vram1 > 50:
                print(f"\n✓ Model selection appears correct (VRAM > 50GB for 27B model)")
            elif vram1:
                print(f"\n✗ Model selection may have failed (VRAM = {vram1} GB is too low for 27B)")
        
        # Keep browser open for verification
        print("\n\nBrowser will stay open for 20 seconds for manual verification...")
        time.sleep(20)
        
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if automation.driver:
            automation.driver.quit()


if __name__ == "__main__":
    quick_test()
