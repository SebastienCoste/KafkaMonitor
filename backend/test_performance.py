#!/usr/bin/env python3
"""
Performance testing script for KafkaMonitor environment switching
"""
import asyncio
import httpx
import time
import psutil
import logging
from typing import List, Dict, Any
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.environments = ['DEV', 'TEST', 'INT', 'LOAD', 'PROD']
        self.process = psutil.Process()
        self.test_results = []
    
    async def test_environment_switching(self, cycles: int = 10):
        """Test rapid environment switching for memory leaks"""
        logger.info(f"🧪 Starting environment switching test ({cycles} cycles)")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for cycle in range(cycles):
                cycle_start = time.time()
                memory_before = self.process.memory_info().rss / 1024 / 1024
                
                for env in self.environments:
                    switch_start = time.time()
                    
                    try:
                        response = await client.post(
                            f"{self.base_url}/api/environments/switch",
                            json={"environment": env}
                        )
                        
                        if response.status_code != 200:
                            logger.error(f"❌ Switch to {env} failed: {response.status_code}")
                            continue
                        
                        # Wait for switch to complete
                        await asyncio.sleep(2)
                        
                        switch_duration = time.time() - switch_start
                        memory_after = self.process.memory_info().rss / 1024 / 1024
                        memory_delta = memory_after - memory_before
                        
                        result = {
                            'cycle': cycle + 1,
                            'environment': env,
                            'switch_duration': switch_duration,
                            'memory_before_mb': memory_before,
                            'memory_after_mb': memory_after,
                            'memory_delta_mb': memory_delta,
                            'timestamp': time.time()
                        }
                        
                        self.test_results.append(result)
                        
                        logger.info(
                            f"Cycle {cycle+1}/{cycles} -> {env}: "
                            f"{switch_duration:.2f}s, "
                            f"Memory: {memory_before:.1f} -> {memory_after:.1f}MB "
                            f"({memory_delta:+.1f}MB)"
                        )
                        
                        # Alert if memory growth is excessive
                        if memory_delta > 50:
                            logger.warning(f"🚨 EXCESSIVE MEMORY GROWTH: {memory_delta:.1f}MB")
                        
                        memory_before = memory_after
                        
                    except Exception as e:
                        logger.error(f"❌ Error switching to {env}: {e}")
                
                cycle_duration = time.time() - cycle_start
                logger.info(f"✅ Cycle {cycle+1} completed in {cycle_duration:.2f}s")
                
                # Brief pause between cycles
                await asyncio.sleep(1)
    
    async def test_concurrent_operations(self, concurrent_requests: int = 10):
        """Test concurrent API operations for race conditions"""
        logger.info(f"🧪 Testing concurrent operations ({concurrent_requests} requests)")
        
        async def make_stats_request(client, request_id):
            try:
                start_time = time.time()
                response = await client.get(f"{self.base_url}/api/statistics")
                duration = time.time() - start_time
                
                return {
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'duration': duration,
                    'success': response.status_code == 200
                }
            except Exception as e:
                return {
                    'request_id': request_id,
                    'error': str(e),
                    'success': False
                }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [
                make_stats_request(client, i)
                for i in range(concurrent_requests)
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_duration = time.time() - start_time
            
            successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
            avg_duration = sum(r.get('duration', 0) for r in results if isinstance(r, dict)) / len(results)
            
            logger.info(
                f"✅ Concurrent test completed: "
                f"{successful}/{concurrent_requests} successful, "
                f"avg duration: {avg_duration:.2f}s, "
                f"total time: {total_duration:.2f}s"
            )
            
            return results
    
    def analyze_results(self):
        """Analyze test results and generate report"""
        if not self.test_results:
            logger.warning("No test results to analyze")
            return
        
        # Memory analysis
        memory_deltas = [r['memory_delta_mb'] for r in self.test_results]
        total_memory_growth = sum(memory_deltas)
        avg_memory_growth = total_memory_growth / len(memory_deltas)
        max_memory_growth = max(memory_deltas)
        
        # Duration analysis
        durations = [r['switch_duration'] for r in self.test_results]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        # Environment analysis
        env_stats = {}
        for env in self.environments:
            env_results = [r for r in self.test_results if r['environment'] == env]
            if env_results:
                env_stats[env] = {
                    'count': len(env_results),
                    'avg_memory_delta': sum(r['memory_delta_mb'] for r in env_results) / len(env_results),
                    'avg_duration': sum(r['switch_duration'] for r in env_results) / len(env_results)
                }
        
        report = {
            'summary': {
                'total_switches': len(self.test_results),
                'total_memory_growth_mb': total_memory_growth,
                'avg_memory_growth_mb': avg_memory_growth,
                'max_memory_growth_mb': max_memory_growth,
                'avg_switch_duration': avg_duration,
                'max_switch_duration': max_duration
            },
            'environment_stats': env_stats,
            'thresholds': {
                'memory_growth_per_switch_mb': 10,  # Should be < 10MB
                'switch_duration_seconds': 5,       # Should be < 5 seconds
                'total_memory_growth_mb': 50        # Should be < 50MB total
            }
        }
        
        # Evaluate against thresholds
        passed_tests = []
        failed_tests = []
        
        if avg_memory_growth < report['thresholds']['memory_growth_per_switch_mb']:
            passed_tests.append(f"✅ Average memory growth: {avg_memory_growth:.1f}MB")
        else:
            failed_tests.append(f"❌ Average memory growth: {avg_memory_growth:.1f}MB (threshold: {report['thresholds']['memory_growth_per_switch_mb']}MB)")
        
        if avg_duration < report['thresholds']['switch_duration_seconds']:
            passed_tests.append(f"✅ Average switch duration: {avg_duration:.2f}s")
        else:
            failed_tests.append(f"❌ Average switch duration: {avg_duration:.2f}s (threshold: {report['thresholds']['switch_duration_seconds']}s)")
        
        if total_memory_growth < report['thresholds']['total_memory_growth_mb']:
            passed_tests.append(f"✅ Total memory growth: {total_memory_growth:.1f}MB")
        else:
            failed_tests.append(f"❌ Total memory growth: {total_memory_growth:.1f}MB (threshold: {report['thresholds']['total_memory_growth_mb']}MB)")
        
        # Print report
        logger.info("="*80)
        logger.info("📊 PERFORMANCE TEST REPORT")
        logger.info("="*80)
        
        for test in passed_tests:
            logger.info(test)
        
        for test in failed_tests:
            logger.error(test)
        
        logger.info(f"\nEnvironment Statistics:")
        for env, stats in env_stats.items():
            logger.info(
                f"  {env}: {stats['count']} switches, "
                f"avg memory: {stats['avg_memory_delta']:+.1f}MB, "
                f"avg duration: {stats['avg_duration']:.2f}s"
            )
        
        # Save detailed results
        with open('performance_test_results.json', 'w') as f:
            json.dump({
                'report': report,
                'detailed_results': self.test_results
            }, f, indent=2)
        
        logger.info(f"\n📄 Detailed results saved to: performance_test_results.json")
        logger.info("="*80)
        
        return len(failed_tests) == 0  # Return True if all tests passed

async def main():
    """Run performance tests"""
    tester = PerformanceTester()
    
    try:
        # Test environment switching
        await tester.test_environment_switching(cycles=5)
        
        # Test concurrent operations
        await tester.test_concurrent_operations(concurrent_requests=20)
        
        # Analyze and report results
        success = tester.analyze_results()
        
        if success:
            logger.info("🎉 All performance tests PASSED!")
            return 0
        else:
            logger.error("💥 Some performance tests FAILED!")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
