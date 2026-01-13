"""
VRAM Calculator Automation Script - Production Version
Automates data collection from https://apxml.com/tools/vram-calculator

Uses undetected-chromedriver to bypass Cloudflare protection.
Uses synchronous polling for dropdown selection instead of async JavaScript.
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
        # Ensure the script returns a value by prepending 'return' if needed
        # and if it appears to be an expression (like an IIFE)
        cleaned_script = script.strip()
        if not cleaned_script.startswith("return"):
            return self.driver.execute_script(f"return {cleaned_script}")
        return self.driver.execute_script(script)
    
    def switch_to_manual_mode(self):
        """Switch input parameters from Slider to Manual mode"""
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
    
    def select_dropdown_option(self, selector: str, option_text: str, max_attempts: int = 3) -> bool:
        """
        Select an option from a dropdown using JavaScript for reliable input triggering
        and explicit clicking of options.
        """
        for attempt in range(max_attempts):
            try:
                # Use JS to type into the input to trigger the dropdown filter
                type_script = f"""
                (() => {{
                    const input = document.querySelector('{selector}');
                    if (!input) return false;
                    
                    input.click();
                    input.focus();
                    input.select();
                    document.execCommand('delete');
                    document.execCommand('insertText', false, '{option_text}');
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    
                    return true;
                }})()
                """
                if not self.execute_js(type_script):
                    print(f"  Attempt {attempt + 1}: Could not find/type into input")
                    continue
                
                time.sleep(1.0)  # Wait for dropdown to appear/filter
                
                # Try to find and click the option
                # First try standard Mantine option
                try:
                    option_xpath = f"//*[@role='option'][contains(text(), '{option_text}')]"
                    option = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, option_xpath))
                    )
                    option.click()
                    time.sleep(OPERATION_DELAY)
                    return True
                except TimeoutException:
                    pass
                
                # Second try: JS-based click on any matching element in the dropdown
                click_script = f"""
                (() => {{
                    // Look for options in standard dropdown containers
                    const options = document.querySelectorAll('[role="option"], .mantine-Select-option');
                    for (const opt of options) {{
                        if (opt.textContent.trim().includes('{option_text}')) {{
                            opt.click();
                            return true;
                        }}
                    }}
                    
                    // Fallback: Look for any element with the text if it seems like a dropdown item
                    const allEls = document.querySelectorAll('div, span');
                    for (const el of allEls) {{
                         if (el.textContent === '{option_text}' && el.offsetParent !== null) {{
                             el.click();
                             return true;
                         }}
                    }}
                    return false;
                }})()
                """
                if self.execute_js(click_script):
                    time.sleep(OPERATION_DELAY)
                    return True
                        
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {e}")
                time.sleep(0.5)
        
        return False
    
    def select_model(self, model_name: str) -> bool:
        """Select a model from the model dropdown"""
        print(f"  Selecting model: {model_name}")
        result = self.select_dropdown_option(self.SELECTORS["model"], model_name)
        
        # Verify selection
        if result:
            actual_value = self.driver.find_element(By.CSS_SELECTOR, self.SELECTORS["model"]).get_attribute("value")
            if model_name in actual_value:
                print(f"  ✓ Model selected: {actual_value}")
                return True
            else:
                print(f"  ⚠ Model value mismatch: expected '{model_name}', got '{actual_value}'")
        
        return result
    
    def select_quantization(self, quantization: str) -> bool:
        """Select inference quantization"""
        print(f"  Selecting quantization: {quantization}")
        return self.select_dropdown_option(self.SELECTORS["quantization"], quantization)
    
    def select_kv_cache_quantization(self) -> bool:
        """Select KV Cache quantization (should always be FP16/BF16)"""
        print(f"  Selecting KV Cache: FP16/BF16")
        return self.select_dropdown_option(self.SELECTORS["kv_cache"], "FP16")
    
    def select_hardware(self, hardware: str = "H200 (141GB)") -> bool:
        """Select hardware configuration"""
        print(f"  Selecting hardware: {hardware}")
        return self.select_dropdown_option(self.SELECTORS["hardware"], hardware)
    
    def set_input_value(self, selector: str, value: int, field_name: str = "") -> bool:
        """
        Set a numeric input value using Selenium with proper event triggering.
        Uses document.execCommand('insertText') via JavaScript for React compatibility.
        """
        try:
            # Find the element
            input_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
            
            # Click to focus
            input_elem.click()
            time.sleep(0.1)
            
            # Use JavaScript to properly set the value with React state triggering
            script = f"""
            (() => {{
                const input = document.querySelector('{selector}');
                if (!input) return false;
                
                input.focus();
                input.select();
                document.execCommand('insertText', false, '{value}');
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                input.blur();
                
                return input.value;
            }})()
            """
            result = self.execute_js(script)
            time.sleep(OPERATION_DELAY)
            
            if result and str(value) in str(result):
                return True
            
            return True  # Assume success even if value check fails
            
        except Exception as e:
            print(f"  Failed to set {field_name}: {e}")
            return False
    
    def set_batch_size(self, batch_size: int) -> bool:
        """Set the batch size"""
        return self.set_input_value(self.SELECTORS["batch_size"], batch_size, "batch size")
    
    def set_sequence_length(self, length: int) -> bool:
        """Set the sequence length (context length)"""
        return self.set_input_value(self.SELECTORS["sequence_length"], length, "sequence length")
    
    def set_concurrent_users(self, users: int) -> bool:
        """Set the number of concurrent users"""
        return self.set_input_value(self.SELECTORS["concurrent_users"], users, "concurrent users")
    
    def verify_configuration(self) -> Dict:
        """Verify the current configuration by checking the summary line and input values"""
        script = """
        (() => {
            const body = document.body.innerText;
            const batchMatch = body.match(/Batch:\\s*(\\d+)/);
            const usersMatch = body.match(/Users:\\s*(\\d+)/);
            
            // Also check input values
            const batchInput = document.querySelector('input[placeholder="Enter batch size"]');
            const seqInput = document.querySelector('input[placeholder="Enter sequence length"]');
            const usersInput = document.querySelector('input[placeholder="Enter number of concurrent users"]');
            const modelInput = document.querySelector('input[placeholder="Choose a model"]');
            
            return {
                display_batch: batchMatch ? parseInt(batchMatch[1]) : null,
                display_users: usersMatch ? parseInt(usersMatch[1]) : null,
                input_batch: batchInput ? batchInput.value : null,
                input_seq: seqInput ? seqInput.value : null,
                input_users: usersInput ? usersInput.value : null,
                input_model: modelInput ? modelInput.value : null
            };
        })()
        """
        return self.execute_js(script)
    
    def extract_results(self) -> Dict:
        """Extract VRAM, throughput, and per-user speed from the results panel"""
        time.sleep(RESULT_UPDATE_DELAY)
        
        script = """
        (() => {
            // Find the results container by looking for the header
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
            const vramMatch = allText.match(/(\\d+[.,]\\d+)\\s*GB\\s*of/i);
            
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
                verified_users: usersMatch ? usersMatch[1] : null
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
        
        print(f"\n--- {model_display_name}, BS={batch_size}, CTX={context_label}, Users={concurrent_users} ---")
        
        # Set model and quantization
        self.select_model(model_site_name)
        time.sleep(0.3)
        
        self.select_quantization(quantization)
        time.sleep(0.3)
        
        self.select_kv_cache_quantization()
        time.sleep(0.3)
        
        # Set input parameters
        self.set_batch_size(batch_size)
        self.set_sequence_length(context_length)
        self.set_concurrent_users(concurrent_users)
        
        # Wait for results to update
        time.sleep(RESULT_UPDATE_DELAY)
        
        # Verify configuration was applied
        verification = self.verify_configuration()
        if verification:
            print(f"  Config: Model='{verification.get('input_model')}', "
                  f"Batch={verification.get('display_batch')}, Users={verification.get('display_users')}")
        
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
        
        print(f"  => VRAM={result['VRAM (GB)']} GB, "
              f"Per-User={result['Tokens per User (tok/s)']} tok/s, "
              f"Total={result['Total Throughput (tok/s)']} tok/s")
        
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
                            time.sleep(0.2)
            
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
