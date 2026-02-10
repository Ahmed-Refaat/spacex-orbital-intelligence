#!/usr/bin/env python3
"""
Profile orbital propagation under realistic load.

Usage:
    python scripts/profile_orbital_propagation.py

Output:
    - Console: Top 20 functions by cumulative time
    - File: profiling/propagation_baseline.txt
"""
import sys
import os
import cProfile
import pstats
from io import StringIO
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

def profile_propagation():
    """
    Profile orbital propagation for 1000 satellites.
    
    Simulates realistic load:
    - 1000 satellites (typical constellation subset)
    - Sequential propagation (worst case)
    - Fresh TLE data
    """
    # Import after path setup
    from app.services.orbital_engine import orbital_engine
    from datetime import datetime, timezone
    
    print("=" * 60)
    print("PROFILING: Orbital Propagation")
    print("=" * 60)
    print(f"Satellites: 1000")
    print(f"Mode: Sequential (worst-case)")
    print("=" * 60)
    print()
    
    # Load satellites
    satellites = list(orbital_engine.satellites.keys())[:1000]
    if not satellites:
        print("❌ No satellites loaded!")
        print("Run backend first to populate TLE data.")
        return
    
    print(f"✅ Loaded {len(satellites)} satellite IDs")
    
    timestamp = datetime.now(timezone.utc)
    
    # Profile
    pr = cProfile.Profile()
    pr.enable()
    
    # Execute propagation
    positions = []
    for sat_id in satellites:
        try:
            pos = orbital_engine.propagate(sat_id, timestamp)
            positions.append(pos)
        except Exception as e:
            # Ignore failures (incomplete TLEs)
            pass
    
    pr.disable()
    
    print(f"✅ Propagated {len(positions)} satellites")
    print()
    
    # Print stats to console
    s = StringIO()
    ps = pstats.Stats(pr, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(20)
    
    output = s.getvalue()
    print(output)
    
    # Save to file
    output_dir = Path(__file__).parent.parent / "profiling"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "propagation_baseline.txt"
    with open(output_file, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("ORBITAL PROPAGATION PROFILING - BASELINE\n")
        f.write("=" * 60 + "\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Satellites: {len(satellites)}\n")
        f.write(f"Successfully propagated: {len(positions)}\n")
        f.write("=" * 60 + "\n\n")
        f.write(output)
    
    print(f"📊 Results saved to: {output_file}")
    print()
    
    # Analyze results
    analyze_profiling_results(ps, len(positions))


def analyze_profiling_results(stats: pstats.Stats, satellite_count: int):
    """
    Analyze profiling results and provide actionable insights.
    
    Args:
        stats: pstats.Stats object
        satellite_count: Number of satellites propagated
    """
    print("=" * 60)
    print("ANALYSIS & RECOMMENDATIONS")
    print("=" * 60)
    
    # Get top functions
    stats_dict = stats.stats
    sorted_stats = sorted(
        stats_dict.items(),
        key=lambda x: x[1][3],  # cumulative time
        reverse=True
    )
    
    if not sorted_stats:
        print("❌ No profiling data available")
        return
    
    # Total time
    total_time = sorted_stats[0][1][3]
    time_per_sat = (total_time / satellite_count) * 1000  # ms
    
    print(f"\n📊 Performance Summary:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Per satellite: {time_per_sat:.2f}ms")
    print(f"  Throughput: {satellite_count / total_time:.0f} sat/s")
    print()
    
    # Identify bottlenecks
    print("🔍 Hot Paths (>10% total time):")
    for func, timing in sorted_stats[:10]:
        func_name = f"{func[0]}:{func[1]}({func[2]})"
        cumtime = timing[3]
        percent = (cumtime / total_time) * 100
        
        if percent > 10:
            print(f"  {percent:5.1f}% - {func_name}")
    
    print()
    
    # Recommendations
    print("💡 Optimization Opportunities:")
    
    if time_per_sat > 1.0:
        print("  ⚠️  SLOW: >1ms per satellite")
        print("     → Consider caching positions (60s TTL)")
        print("     → Parallelize propagation (multiprocessing)")
    elif time_per_sat > 0.5:
        print("  🟡 MODERATE: 0.5-1ms per satellite")
        print("     → Caching recommended for high load")
    else:
        print("  ✅ FAST: <0.5ms per satellite")
        print("     → Performance is excellent")
    
    print()
    
    # Cache recommendation
    if time_per_sat > 0.3:
        cache_hit_rate = 0.90  # Assume 90% hit rate
        speedup = 1 / (1 - cache_hit_rate + cache_hit_rate * 0.01)  # Assume cache is 100x faster
        print(f"  📈 With 90% cache hit rate:")
        print(f"     Effective latency: {time_per_sat * (1 - cache_hit_rate):.2f}ms")
        print(f"     Speedup: {speedup:.1f}x")


if __name__ == '__main__':
    try:
        profile_propagation()
    except KeyboardInterrupt:
        print("\n❌ Profiling cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
