"""
VRAM Calculator Automation Script - Improved Version
Automates data collection from https://apxml.com/tools/vram-calculator

Uses undetected-chromedriver to bypass Cloudflare protection.
Improved with placeholder-based selectors and proper React state triggering.
"""

import time
import re
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from config import (
    MODELS,
    BATCH_SIZES,
    CONTEXT_LENGTHS,
    CONCURRENT_USERS,
    KV_CACHE_QUANTIZATION,
    VRAM_CALCULATOR_URL,
    OPERATION_DELAY,
    PAGE_LOAD_DELAY,
    RESULT_UPDATE_DELAY,
)


class VRAMCalculatorAutomation:
    """Automates VRAM calculation data collection from apxml.com"""
    
    # Reliable placeholder-based selectors
    SELECTORS = {
        "model": 'input[placeholder="Choose a model"]',
        "quantization": 'input[placeholder="Select quantization"]',
        "kv_cache": 'input[placeholder="Select KV cache precision"]',
        "hardware": 'input[placeholder="Select Hardware"]',
        "batch_size": 'input[placeholder="Enter batch size"]',
        "sequence_length": 'input[placeholder="Enter sequence length"]',
        "concurrent_users": 'input[placeholder="Enter number of concurrent users"]',
    }
    
    def __init__(self, headless: bool = False):
        """Initialize the automation with Chrome driver"""
        self.driver = None
        self.headless = headless
        self.results: List[Dict] = []
        
    def setup_driver(self):
        """Set up undetected Chrome driver"""
        options = uc.ChromeOptions()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Create driver with undetected-chromedriver
        self.driver = uc.Chrome(options=options, version_main=None)
        self.driver.implicitly_wait(10)
        
    def navigate_to_calculator(self):
        """Navigate to the VRAM calculator page"""
        print(f"Navigating to {VRAM_CALCULATOR_URL}...")
        self.driver.get(VRAM_CALCULATOR_URL)
        time.sleep(PAGE_LOAD_DELAY)
        
        # Wait for the page to fully load by checking for the model input
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.SELECTORS["model"]))
            )
            print("Page loaded successfully!")
        except TimeoutException:
            print("Warning: Page load timeout, but continuing...")
    
    def execute_js(self, script: str):
        """Execute JavaScript and return result"""
        return self.driver.execute_script(script)
    
    def switch_to_manual_mode(self):
        """Switch input parameters from Slider to Manual mode using JavaScript"""
        script = """
        (() => {
            // Find the toggle by looking for a label containing "Slider" or "Manual"
            const labels = Array.from(document.querySelectorAll('label'));
            const toggleLabel = labels.find(el => 
                el.textContent.includes('Manual') || el.textContent.includes('Slider')
            );
            
            if (toggleLabel) {
                const input = toggleLabel.querySelector('input');
                if (input && !input.checked) {
                    input.click();
                    return "Switched to Manual mode";
                } else if (input && input.checked) {
                    return "Already in Manual mode";
                }
            }
            return "Toggle not found";
        })()
        """
        result = self.execute_js(script)
        print(f"Mode toggle: {result}")
        time.sleep(OPERATION_DELAY)
        return "Manual" in str(result) or "Already" in str(result)
    
    def select_dropdown_option(self, selector: str, option_text: str) -> bool:
        """Select an option from a Mantine dropdown using JavaScript for reliability"""
        script = f"""
        (() => {{
            const input = document.querySelector('{selector}');
            if (!input) return "Input not found: {selector}";
            
            // Focus and clear the input
            input.focus();
            input.value = '';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            // Type the search text
            input.value = '{option_text}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            // Wait a bit for dropdown to appear
            return "Typed: {option_text}";
        }})()
        """
        self.execute_js(script)
        time.sleep(0.5)
        
        # Now click the matching option
        click_script = f"""
        (() => {{
            const options = document.querySelectorAll('.mantine-Select-option, [role="option"]');
            for (const opt of options) {{
                if (opt.textContent.trim().includes('{option_text}')) {{
                    opt.click();
                    return "Selected: " + opt.textContent.trim();
                }}
            }}
            return "Option not found: {option_text}";
        }})()
        """
        result = self.execute_js(click_script)
        time.sleep(OPERATION_DELAY)
        return "Selected" in str(result)
    
    def select_model(self, model_name: str) -> bool:
        """Select a model from the model dropdown"""
        return self.select_dropdown_option(self.SELECTORS["model"], model_name)
    
    def select_quantization(self, quantization: str) -> bool:
        """Select inference quantization"""
        return self.select_dropdown_option(self.SELECTORS["quantization"], quantization)
    
    def select_kv_cache_quantization(self) -> bool:
        """Select KV Cache quantization (should always be FP16/BF16)"""
        return self.select_dropdown_option(self.SELECTORS["kv_cache"], "FP16")
    
    def select_hardware(self, hardware: str = "H200 (141GB)") -> bool:
        """Select hardware configuration"""
        return self.select_dropdown_option(self.SELECTORS["hardware"], hardware)
    
    def set_input_value_js(self, selector: str, value: int) -> bool:
        """
        Set a numeric input value using JavaScript with proper React state triggering.
        Uses document.execCommand('insertText') for reliable React state updates.
        """
        script = f"""
        (() => {{
            const input = document.querySelector('{selector}');
            if (!input) return "Input not found: {selector}";
            
            // Focus the input
            input.focus();
            
            // Select all existing text
            input.select();
            
            // Use execCommand to insert text (triggers React state properly)
            document.execCommand('insertText', false, '{value}');
            
            // Dispatch events to ensure React picks up the change
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            // Blur to finalize
            input.blur();
            
            return "Set " + input.placeholder + " to " + input.value;
        }})()
        """
        result = self.execute_js(script)
        time.sleep(OPERATION_DELAY)
        return "Set" in str(result)
    
    def set_batch_size(self, batch_size: int) -> bool:
        """Set the batch size"""
        return self.set_input_value_js(self.SELECTORS["batch_size"], batch_size)
    
    def set_sequence_length(self, length: int) -> bool:
        """Set the sequence length (context length)"""
        return self.set_input_value_js(self.SELECTORS["sequence_length"], length)
    
    def set_concurrent_users(self, users: int) -> bool:
        """Set the number of concurrent users"""
        return self.set_input_value_js(self.SELECTORS["concurrent_users"], users)
    
    def verify_configuration(self) -> Dict:
        """Verify the current configuration by checking the summary line"""
        script = """
        (() => {
            const body = document.body.innerText;
            const batchMatch = body.match(/Batch:\\s*(\\d+)/);
            const usersMatch = body.match(/Users:\\s*(\\d+)/);
            
            return {
                batch: batchMatch ? parseInt(batchMatch[1]) : null,
                users: usersMatch ? parseInt(usersMatch[1]) : null
            };
        })()
        """
        return self.execute_js(script)
    
    def extract_results(self) -> Dict:
        """Extract VRAM, throughput, and per-user speed from the results panel using JavaScript"""
        time.sleep(RESULT_UPDATE_DELAY)
        
        script = """
        (() => {
            // Find the results container
            const findResultsHeader = () => {
                const headers = document.querySelectorAll('p, h1, h2, h3, h4, span, div');
                for (const h of headers) {
                    if (h.textContent.trim() === 'Performance & Memory Results') return h;
                }
                return null;
            };
            
            const header = findResultsHeader();
            if (!header) return { error: "Results header not found" };
            
            const resultsContainer = header.parentElement;
            const allText = resultsContainer.innerText;
            
            // Extract VRAM - looking for the main VRAM display value
            // Pattern: "X.XX GB" or "X,XX GB" followed by "of Y GB VRAM"
            const vramMatch = allText.match(/(\\d+[.,]\\d+)\\s*GB\\s*of\\s*\\d+/i) || 
                              allText.match(/OKAY\\s*(\\d+[.,]\\d+)\\s*GB/i) ||
                              allText.match(/(\\d+[.,]\\d+)\\s*GB/);
            
            // Extract Total Throughput
            const throughputMatch = allText.match(/Total Throughput:\\s*~?(\\d+(?:[.,]\\d+)?)\\s*tok\\/s/i);
            
            // Extract Per-User Speed
            const perUserMatch = allText.match(/Per-User Speed:\\s*~?(\\d+(?:[.,]\\d+)?)\\s*tok\\/s/i) ||
                                 allText.match(/Generation Speed:\\s*~?(\\d+(?:[.,]\\d+)?)\\s*tok\\/s/i);
            
            // Extract configuration verification
            const batchMatch = allText.match(/Batch:\\s*(\\d+)/);
            const usersMatch = allText.match(/Users:\\s*(\\d+)/);
            
            return {
                vram_gb: vramMatch ? vramMatch[1].replace(',', '.') : null,
                total_throughput: throughputMatch ? throughputMatch[1].replace(',', '.') : null,
                per_user_speed: perUserMatch ? perUserMatch[1].replace(',', '.') : null,
                verified_batch: batchMatch ? batchMatch[1] : null,
                verified_users: usersMatch ? usersMatch[1] : null,
                raw_text: allText.substring(0, 500)
            };
        })()
        """
        
        result = self.execute_js(script)
        
        extracted = {
            "vram_gb": None,
            "total_throughput": None,
            "per_user_speed": None,
        }
        
        if result and not result.get("error"):
            if result.get("vram_gb"):
                extracted["vram_gb"] = float(result["vram_gb"])
            if result.get("total_throughput"):
                extracted["total_throughput"] = float(result["total_throughput"])
            if result.get("per_user_speed"):
                extracted["per_user_speed"] = float(result["per_user_speed"])
                
        return extracted
    
    def collect_single_configuration(
        self,
        model_display_name: str,
        model_site_name: str,
        quantization: str,
        batch_size: int,
        context_length: int,
        context_label: str,
        concurrent_users: int
    ) -> Optional[Dict]:
        """Collect data for a single configuration"""
        
        print(f"\n--- Collecting: {model_display_name}, BS={batch_size}, CTX={context_label}, Users={concurrent_users} ---")
        
        # Set all parameters
        model_ok = self.select_model(model_site_name)
        if not model_ok:
            print(f"  Warning: Could not select model {model_site_name}")
        
        quant_ok = self.select_quantization(quantization)
        if not quant_ok:
            print(f"  Warning: Could not select quantization {quantization}")
            
        # Ensure KV Cache is FP16
        kv_ok = self.select_kv_cache_quantization()
        if not kv_ok:
            print("  Warning: Could not set KV Cache to FP16")
        
        # Set input parameters
        batch_ok = self.set_batch_size(batch_size)
        if not batch_ok:
            print(f"  Warning: Could not set batch size {batch_size}")
            
        seq_ok = self.set_sequence_length(context_length)
        if not seq_ok:
            print(f"  Warning: Could not set sequence length {context_length}")
            
        users_ok = self.set_concurrent_users(concurrent_users)
        if not users_ok:
            print(f"  Warning: Could not set concurrent users {concurrent_users}")
        
        # Wait for results to update
        time.sleep(RESULT_UPDATE_DELAY)
        
        # Verify configuration was applied
        verification = self.verify_configuration()
        if verification:
            print(f"  Verified: Batch={verification.get('batch')}, Users={verification.get('users')}")
        
        # Extract results
        extracted = self.extract_results()
        
        result = {
            "Model": model_display_name,
            "Quantization": quantization,
            "Batch Size": batch_size,
            "Context Length": context_label,
            "Concurrent Users": concurrent_users,
            "VRAM (GB)": extracted["vram_gb"],
            "Tokens per User (tok/s)": extracted["per_user_speed"],
            "Total Throughput (tok/s)": extracted["total_throughput"],
        }
        
        print(f"  Results: VRAM={result['VRAM (GB)']} GB, Per-User={result['Tokens per User (tok/s)']} tok/s, Total={result['Total Throughput (tok/s)']} tok/s")
        
        return result
    
    def run_full_collection(self):
        """Run the full data collection for all configurations"""
        try:
            self.setup_driver()
            self.navigate_to_calculator()
            
            # Switch to manual input mode
            self.switch_to_manual_mode()
            
            # Select hardware (H200 with 141GB to fit all models)
            self.select_hardware("H200 (141GB)")
            
            total_combinations = len(MODELS) * len(BATCH_SIZES) * len(CONTEXT_LENGTHS) * len(CONCURRENT_USERS)
            current = 0
            
            print(f"\nStarting collection of {total_combinations} configurations...")
            
            for model_display, model_site, quantization in MODELS:
                for batch_size in BATCH_SIZES:
                    for context_tokens, context_label in CONTEXT_LENGTHS:
                        for users in CONCURRENT_USERS:
                            current += 1
                            print(f"\n[{current}/{total_combinations}]", end="")
                            
                            result = self.collect_single_configuration(
                                model_display_name=model_display,
                                model_site_name=model_site,
                                quantization=quantization,
                                batch_size=batch_size,
                                context_length=context_tokens,
                                context_label=context_label,
                                concurrent_users=users
                            )
                            
                            if result:
                                self.results.append(result)
                            
                            # Small delay between configurations
                            time.sleep(0.3)
            
            print(f"\n\nCollection complete! Collected {len(self.results)} configurations.")
            
        except Exception as e:
            print(f"Error during collection: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if self.driver:
                self.driver.quit()
    
    def save_results(self, output_path: str = "vram_results.xlsx"):
        """Save results to Excel file"""
        if not self.results:
            print("No results to save!")
            return None
            
        df = pd.DataFrame(self.results)
        
        # Reorder columns
        columns = [
            "Model",
            "Quantization",
            "Batch Size",
            "Context Length",
            "Concurrent Users",
            "VRAM (GB)",
            "Tokens per User (tok/s)",
            "Total Throughput (tok/s)",
        ]
        df = df[columns]
        
        # Save to Excel
        df.to_excel(output_path, index=False, sheet_name="VRAM Results")
        print(f"Results saved to {output_path}")
        
        # Also save to CSV as backup
        csv_path = output_path.replace(".xlsx", ".csv")
        df.to_csv(csv_path, index=False)
        print(f"Backup saved to {csv_path}")
        
        return df


def main():
    """Main entry point"""
    print("=" * 60)
    print("VRAM Calculator Automation")
    print("=" * 60)
    
    automation = VRAMCalculatorAutomation(headless=False)
    
    try:
        automation.run_full_collection()
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"vram_results_{timestamp}.xlsx"
        
        df = automation.save_results(output_file)
        
        if df is not None:
            print("\n" + "=" * 60)
            print("Results Preview:")
            print("=" * 60)
            print(df.head(20).to_string())
            
    except KeyboardInterrupt:
        print("\n\nCollection interrupted by user.")
        if automation.results:
            automation.save_results("vram_results_partial.xlsx")
    except Exception as e:
        print(f"\nError: {e}")
        if automation.results:
            automation.save_results("vram_results_error.xlsx")
        raise


if __name__ == "__main__":
    main()
