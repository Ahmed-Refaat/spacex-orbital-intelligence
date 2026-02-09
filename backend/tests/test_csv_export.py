"""
Tests for CSV export functionality.

Story 3.4: CSV Export
Tests exporting trajectory data to CSV format.
"""
import pytest
import csv
import io
from app.services.csv_exporter import TrajectoryCSVExporter, TrajectoryPoint


class TestTrajectoryPoint:
    """Test TrajectoryPoint dataclass."""
    
    def test_trajectory_point_creation(self):
        """Should create trajectory point with all fields."""
        point = TrajectoryPoint(
            time=100.0,
            altitude_km=50.0,
            velocity_km_s=2.0,
            downrange_km=70.0,
            mass_kg=400000,
            acceleration_g=3.5
        )
        
        assert point.time == 100.0
        assert point.altitude_km == 50.0
        assert point.velocity_km_s == 2.0


class TestCSVExporter:
    """Test CSV export functionality."""
    
    def test_export_to_string(self):
        """Should export trajectory to CSV string."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(0.0, 0.0, 0.0, 0.0, 500000, 0.0),
            TrajectoryPoint(10.0, 0.5, 0.1, 0.5, 490000, 1.5),
            TrajectoryPoint(20.0, 2.0, 0.3, 2.0, 480000, 2.0),
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        
        assert "time" in csv_string.lower()
        assert "altitude" in csv_string.lower()
        assert "0.0" in csv_string
        assert "10.0" in csv_string
    
    def test_csv_has_header(self):
        """CSV should have header row."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(0.0, 0.0, 0.0, 0.0, 500000, 0.0),
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        lines = csv_string.strip().split('\n')
        
        # First line should be header
        header = lines[0]
        assert "time" in header.lower()
        assert "altitude" in header.lower()
        assert "velocity" in header.lower()
    
    def test_csv_correct_number_of_rows(self):
        """CSV should have correct number of rows (header + data)."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(i, i * 0.5, i * 0.1, i * 0.5, 500000 - i * 1000, i * 0.1)
            for i in range(100)
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        lines = csv_string.strip().split('\n')
        
        # Header + 100 data rows
        assert len(lines) == 101
    
    def test_csv_parseable(self):
        """CSV should be parseable by standard CSV reader."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(0.0, 0.0, 0.0, 0.0, 500000, 0.0),
            TrajectoryPoint(10.0, 0.5, 0.1, 0.5, 490000, 1.5),
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        
        # Parse with csv module
        reader = csv.DictReader(io.StringIO(csv_string))
        rows = list(reader)
        
        assert len(rows) == 2
        assert 'time' in rows[0]
        assert float(rows[0]['time']) == 0.0
        assert float(rows[1]['time']) == 10.0
    
    def test_export_to_file(self, tmp_path):
        """Should export trajectory to file."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(0.0, 0.0, 0.0, 0.0, 500000, 0.0),
            TrajectoryPoint(10.0, 0.5, 0.1, 0.5, 490000, 1.5),
        ]
        
        filepath = tmp_path / "trajectory.csv"
        exporter.export_to_file(trajectory, str(filepath))
        
        # File should exist
        assert filepath.exists()
        
        # Should be readable
        with open(filepath) as f:
            content = f.read()
            assert "time" in content.lower()
            assert "0.0" in content


class TestCSVFormat:
    """Test CSV format details."""
    
    def test_csv_uses_comma_delimiter(self):
        """CSV should use comma as delimiter."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(0.0, 0.0, 0.0, 0.0, 500000, 0.0),
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        
        # Should contain commas
        assert ',' in csv_string
    
    def test_csv_column_order(self):
        """CSV columns should be in logical order."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(0.0, 0.0, 0.0, 0.0, 500000, 0.0),
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        header = csv_string.split('\n')[0]
        
        # Time should come first
        assert header.startswith('time') or header.startswith('Time')
    
    def test_csv_numeric_precision(self):
        """CSV should have appropriate numeric precision."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(
                time=123.456789,
                altitude_km=50.123456,
                velocity_km_s=2.345678,
                downrange_km=70.234567,
                mass_kg=456789.123,
                acceleration_g=3.456789
            ),
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        
        # Should have decimal places (not rounded to integers)
        assert '123.4' in csv_string or '123.' in csv_string
        assert '50.1' in csv_string or '50.' in csv_string


class TestEmptyTrajectory:
    """Test handling of empty or invalid data."""
    
    def test_empty_trajectory(self):
        """Should handle empty trajectory gracefully."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = []
        
        csv_string = exporter.export_to_string(trajectory)
        
        # Should at least have header
        assert "time" in csv_string.lower()
    
    def test_single_point(self):
        """Should handle single trajectory point."""
        exporter = TrajectoryCSVExporter()
        
        trajectory = [
            TrajectoryPoint(0.0, 0.0, 0.0, 0.0, 500000, 0.0),
        ]
        
        csv_string = exporter.export_to_string(trajectory)
        lines = csv_string.strip().split('\n')
        
        # Header + 1 data row
        assert len(lines) == 2


class TestCSVWithRealData:
    """Test CSV export with realistic trajectory data."""
    
    def test_export_falcon9_trajectory(self):
        """Should export realistic Falcon 9 trajectory."""
        exporter = TrajectoryCSVExporter()
        
        # Simplified Falcon 9 ascent profile
        trajectory = []
        for t in range(0, 540, 10):  # 0 to 9 minutes
            if t < 160:
                # First stage burn
                altitude = t * 0.4
                velocity = t * 0.013
                mass = 549000 - t * 2500
            elif t < 520:
                # Second stage burn
                altitude = 68 + (t - 160) * 0.4
                velocity = 2.1 + (t - 160) * 0.016
                mass = 120000 - (t - 160) * 300
            else:
                # Coast to orbit
                altitude = 210
                velocity = 7.8
                mass = 20000
            
            downrange = t * 0.4
            accel = 2.0 if t < 160 else 1.5
            
            point = TrajectoryPoint(
                time=t,
                altitude_km=altitude,
                velocity_km_s=velocity,
                downrange_km=downrange,
                mass_kg=mass,
                acceleration_g=accel
            )
            trajectory.append(point)
        
        csv_string = exporter.export_to_string(trajectory)
        
        # Should contain all data points
        lines = csv_string.strip().split('\n')
        assert len(lines) == len(trajectory) + 1  # +1 for header
        
        # Should be parseable
        reader = csv.DictReader(io.StringIO(csv_string))
        rows = list(reader)
        assert len(rows) == len(trajectory)
