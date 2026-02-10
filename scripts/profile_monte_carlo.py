#!/usr/bin/env python3
"""
Profile Monte Carlo launch simulation.

Usage:
    python scripts/profile_monte_carlo.py [--runs N]

Output:
    - Console: Top 20 functions by cumulative time
    - File: profiling/monte_carlo_baseline.txt
"""
import sys
import os
import cProfile
import pstats
import argparse
from io import StringIO
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def profile_monte_carlo(n_runs: int = 100, parallel: bool = False):
    """
    Profile Monte Carlo simulation.
    
    Args:
        n_runs: Number of simulation runs
        parallel: Use parallel execution
    """
    from app.services.launch_simulator import MonteCarloEngine, LaunchParameters
    
    print("=" * 60)
    print("PROFILING: Monte Carlo Launch Simulation")
    print("=" * 60)
    print(f"Runs: {n_runs}")
    print(f"Parallel: {parallel}")
    print("=" * 60)
    print()
    
    # Create engine
    params = LaunchParameters()
    engine = MonteCarloEngine(params)
    
    # Profile
    pr = cProfile.Profile()
    pr.enable()
    
    result = engine.run_simulation(n_runs=n_runs, seed=42, parallel=parallel)
    
    pr.disable()
    
    print(f"✅ Simulation complete")
    print(f"   Success rate: {result.success_rate:.1%}")
    print(f"   Runtime: {result.runtime_seconds:.2f}s")
    print()
    
    # Print stats to console
    s = StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(30)
    
    output = s.getvalue()
    print(output)
    
    # Save to file
    output_dir = Path(__file__).parent.parent / "profiling"
    output_dir.mkdir(exist_ok=True)
    
    mode = "parallel" if parallel else "sequential"
    output_file = output_dir / f"monte_carlo_baseline_{mode}_{n_runs}runs.txt"
    
    with open(output_file, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write(f"MONTE CARLO SIMULATION PROFILING - {mode.upper()}\n")
        f.write("=" * 60 + "\n")
        from datetime import datetime
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Runs: {n_runs}\n")
        f.write(f"Success rate: {result.success_rate:.1%}\n")
        f.write(f"Runtime: {result.runtime_seconds:.2f}s\n")
        f.write("=" * 60 + "\n\n")
        f.write(output)
    
    print(f"📊 Results saved to: {output_file}")
    print()
    
    # Analyze
    analyze_monte_carlo_results(ps, n_runs, result.runtime_seconds, parallel)


def analyze_monte_carlo_results(
    stats: pstats.Stats,
    n_runs: int,
    runtime: float,
    parallel: bool
):
    """
    Analyze Monte Carlo profiling results.
    
    Args:
        stats: pstats.Stats object
        n_runs: Number of runs
        runtime: Total runtime in seconds
        parallel: Whether parallel execution was used
    """
    print("=" * 60)
    print("ANALYSIS & RECOMMENDATIONS")
    print("=" * 60)
    
    time_per_run = (runtime / n_runs) * 1000  # ms
    
    print(f"\n📊 Performance Summary:")
    print(f"  Total runtime: {runtime:.2f}s")
    print(f"  Per simulation: {time_per_run:.1f}ms")
    print(f"  Throughput: {n_runs / runtime:.1f} sims/s")
    print()
    
    # Performance assessment
    print("💡 Performance Assessment:")
    
    if not parallel:
        print("  ℹ️  Sequential mode (single-threaded)")
        
        if time_per_run > 100:
            print("  ⚠️  SLOW: >100ms per run")
            print("     → Enable parallel mode for production")
            print("     → Expected speedup: 4-8x")
        elif time_per_run > 50:
            print("  🟡 MODERATE: 50-100ms per run")
            print("     → Consider parallel mode for large runs (>1000)")
        else:
            print("  ✅ FAST: <50ms per run")
    else:
        print("  ⚡ Parallel mode (multi-process)")
        
        if time_per_run > 50:
            print("  ⚠️  SLOW: >50ms per run (parallelized)")
            print("     → Physics engine may be bottleneck")
            print("     → Profile physics calculations")
        else:
            print("  ✅ FAST: Good parallel performance")
    
    print()
    
    # Get top functions
    stats_dict = stats.stats
    sorted_stats = sorted(
        stats_dict.items(),
        key=lambda x: x[1][3],  # cumulative time
        reverse=True
    )
    
    if sorted_stats:
        total_time = sorted_stats[0][1][3]
        
        print("🔍 Hot Paths (>5% total time):")
        for func, timing in sorted_stats[:15]:
            func_name = f"{func[2]}"
            if len(func_name) > 40:
                func_name = func_name[:37] + "..."
            
            cumtime = timing[3]
            percent = (cumtime / total_time) * 100
            
            if percent > 5:
                print(f"  {percent:5.1f}% - {func_name}")
        
        print()
    
    # Recommendations
    print("🎯 Optimization Recommendations:")
    print()
    
    if not parallel and n_runs >= 100:
        print("  1. Enable parallel execution:")
        print("     result = engine.run_simulation(n_runs=N, parallel=True)")
        print()
    
    print("  2. Physics optimizations (if needed):")
    print("     → Vectorize calculations (NumPy)")
    print("     → Pre-compute constants")
    print("     → Reduce function calls in hot loops")
    print()
    
    print("  3. Cache simulation results:")
    print("     → Same parameters → same result (deterministic)")
    print("     → Redis TTL: 1 hour")
    print()
    
    # Production recommendations
    target_throughput = 100 / time_per_run  # sims/sec
    print(f"📈 Production Capacity Estimate:")
    print(f"  Current: {target_throughput:.0f} simulations/second")
    
    if parallel:
        print(f"  Max concurrent users (100 runs each): {target_throughput / 100:.0f}/sec")
        if target_throughput > 10:
            print("  ✅ Sufficient for production load")
        else:
            print("  ⚠️  May need optimization for high load")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Profile Monte Carlo launch simulation'
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=100,
        help='Number of simulation runs (default: 100)'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel execution'
    )
    
    args = parser.parse_args()
    
    try:
        profile_monte_carlo(n_runs=args.runs, parallel=args.parallel)
    except KeyboardInterrupt:
        print("\n❌ Profiling cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
