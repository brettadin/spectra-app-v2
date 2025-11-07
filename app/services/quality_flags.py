"""Quality flags for spectral data points.

These bit flags indicate data quality issues that may affect analysis.
Multiple flags can be combined using bitwise OR.

Example:
    flags = QualityFlags.BAD_PIXEL | QualityFlags.LOW_SNR
"""

from enum import IntFlag


class QualityFlags(IntFlag):
    """Bit flags for marking data quality issues in spectral data.
    
    These flags can be combined using bitwise OR (|) to mark multiple
    issues at a single data point.
    """
    
    GOOD = 0x00  # No issues detected
    BAD_PIXEL = 0x01  # Known bad/dead detector pixel
    COSMIC_RAY = 0x02  # Cosmic ray hit detected
    SATURATED = 0x04  # Detector saturation
    LOW_SNR = 0x08  # Signal-to-noise ratio below threshold
    INTERPOLATED = 0x10  # Value was interpolated from neighbors
    EXTRAPOLATED = 0x20  # Value was extrapolated (beyond original range)
    USER_FLAGGED = 0x40  # Manually flagged by user
    QUESTIONABLE = 0x80  # Automatically flagged as suspicious
