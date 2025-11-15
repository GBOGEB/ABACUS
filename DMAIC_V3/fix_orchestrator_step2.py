import re

# Read the file
with open('full_pipeline_orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Integration Point 2: Add bg_change_detector initialization in __init__
init_pattern = r'(if self\.enable_idempotency_flag:\s+enable_idempotency\(enabled=True\))'
init_replacement = r'''\1
        
        # Integration Point 2: Initialize background change detector
        state_dir = self.config.paths.output_root / "convergence_state"
        self.bg_change_detector = BackgroundChangeDetector(
            workspace_root=self.config.paths.workspace_root,
            state_dir=state_dir
        )'''
content = re.sub(init_pattern, init_replacement, content)

# Integration Point 3: Start background detector in execute_full_pipeline
start_pattern = r'(start_time = datetime\.now\(\)\s+phases_executed = \[\])'
start_replacement = r'''\1
        
        # Integration Point 3: Start background change detection
        self.bg_change_detector.start()'''
content = re.sub(start_pattern, start_replacement, content)

# Integration Points 4 & 5: Add finally block
finally_pattern = r'(except Exception as e:\s+print\(f"\\n\[ERROR\] Pipeline failed: \{e\}"\)\s+import traceback\s+traceback\.print_exc\(\)\s+return False)'
finally_replacement = r'''\1
        finally:
            # Integration Point 4: Stop background change detection
            self.bg_change_detector.stop()
            
            # Integration Point 5: Get and display final summary
            change_summary = self.bg_change_detector.get_summary()
            print(f"\\n{'='*80}")
            print("[Background Change Detection] Final Summary:")
            print(f"  Total changes detected: {change_summary.get('total', 0)}")
            print(f"  Files added: {change_summary.get('added', 0)}")
            print(f"  Files modified: {change_summary.get('modified', 0)}")
            print(f"  Files deleted: {change_summary.get('deleted', 0)}")
            if change_summary.get('timestamp'):
                print(f"  Last snapshot: {change_summary.get('timestamp')}")
            print(f"{'='*80}")'''
content = re.sub(finally_pattern, finally_replacement, content, flags=re.DOTALL)

# Write the file
with open('full_pipeline_orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('All 5 integration points added successfully!')
