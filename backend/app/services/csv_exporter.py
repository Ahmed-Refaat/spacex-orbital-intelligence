"""
CSV export for trajectory data.

Story 3.4: CSV Export
Exports simulation results to CSV format for analysis in Excel/MATLAB/Python.
"""
import csv
import io
from dataclasses import dataclass, asdict
from typing import List
from pathlib import Path


@dataclass
class TrajectoryPoint:
    """
    Single point in trajectory.
    
    Attributes:
        time: Time since liftoff (seconds)
        altitude_km: Altitude above sea level (km)
        velocity_km_s: Velocity magnitude (km/s)
        downrange_km: Downrange distance from launch site (km)
        mass_kg: Vehicle mass (kg)
        acceleration_g: Acceleration (g's)
    """
    time: float
    altitude_km: float
    velocity_km_s: float
    downrange_km: float
    mass_kg: float
    acceleration_g: float


class TrajectoryCSVExporter:
    """
    Export trajectory data to CSV format.
    
    Produces CSV files compatible with Excel, MATLAB, Python pandas, etc.
    
    Methods:
        export_to_string(): Export to CSV string
        export_to_file(): Export to CSV file
    
    Example:
        >>> exporter = TrajectoryCSVExporter()
        >>> trajectory = [TrajectoryPoint(...), ...]
        >>> csv_string = exporter.export_to_string(trajectory)
        >>> exporter.export_to_file(trajectory, "trajectory.csv")
    """
    
    def __init__(self):
        # Column order (logical progression)
        self.fieldnames = [
            'time',
            'altitude_km',
            'velocity_km_s',
            'downrange_km',
            'mass_kg',
            'acceleration_g'
        ]
    
    def export_to_string(self, trajectory: List[TrajectoryPoint]) -> str:
        """
        Export trajectory to CSV string.
        
        Args:
            trajectory: List of TrajectoryPoint objects
        
        Returns:
            CSV-formatted string
        
        Example:
            >>> csv_string = exporter.export_to_string(trajectory)
            >>> print(csv_string)
            time,altitude_km,velocity_km_s,...
            0.0,0.0,0.0,...
            10.0,0.5,0.1,...
        """
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=self.fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write data rows
        for point in trajectory:
            row = asdict(point)
            writer.writerow(row)
        
        csv_string = output.getvalue()
        output.close()
        
        return csv_string
    
    def export_to_file(self, trajectory: List[TrajectoryPoint], filepath: str):
        """
        Export trajectory to CSV file.
        
        Args:
            trajectory: List of TrajectoryPoint objects
            filepath: Output file path
        
        Example:
            >>> exporter.export_to_file(trajectory, "results/trajectory.csv")
        """
        csv_string = self.export_to_string(trajectory)
        
        # Ensure parent directory exists
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(filepath, 'w', newline='') as f:
            f.write(csv_string)
    
    def export_with_metadata(
        self,
        trajectory: List[TrajectoryPoint],
        metadata: dict
    ) -> str:
        """
        Export trajectory with metadata header.
        
        Metadata is added as commented lines at the top of the file.
        
        Args:
            trajectory: List of TrajectoryPoint objects
            metadata: Dictionary with metadata (vehicle, mission, etc.)
        
        Returns:
            CSV string with metadata header
        
        Example:
            >>> metadata = {
            ...     'vehicle': 'Falcon 9 Block 5',
            ...     'mission': 'CRS-21',
            ...     'date': '2020-12-06'
            ... }
            >>> csv = exporter.export_with_metadata(trajectory, metadata)
        """
        output = io.StringIO()
        
        # Write metadata as comments
        output.write("# Trajectory Export\n")
        for key, value in metadata.items():
            output.write(f"# {key}: {value}\n")
        output.write("#\n")
        
        # Write CSV data
        csv_data = self.export_to_string(trajectory)
        output.write(csv_data)
        
        result = output.getvalue()
        output.close()
        
        return result
