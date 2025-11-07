"""Differential and mathematical operations on spectra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np

from .spectrum import Spectrum
from .units_service import UnitsService


@dataclass
class MathService:
    """Provide subtraction and ratio operations with provenance logging."""

    units_service: UnitsService
    epsilon: float = 1e-9

    def subtract(self, a: Spectrum, b: Spectrum) -> Tuple[Spectrum | None, Dict[str, object]]:
        """Compute ``a - b`` if non-trivial, otherwise suppress result.
        
        Propagates uncertainties as: σ_diff = √(σ_a² + σ_b²)
        Combines quality flags with bitwise OR.
        """
        x_canon, a_canon_y, b_canon_y = self._aligned_canonical(a, b)
        a_sigma, b_sigma = self._aligned_uncertainties(a, b, x_canon)
        a_flags, b_flags = self._aligned_quality_flags(a, b, x_canon)
        
        diff = a_canon_y - b_canon_y
        if np.allclose(diff, 0.0, atol=self.epsilon):
            return None, {
                'status': 'suppressed_trivial',
                'operation': 'subtract',
                'message': 'Spectra are identical within tolerance; result suppressed.',
                'parents': [a.id, b.id],
            }

        # Propagate uncertainty: σ_diff = √(σ_a² + σ_b²)
        result_sigma = None
        if a_sigma is not None or b_sigma is not None:
            a_sig = a_sigma if a_sigma is not None else np.zeros_like(diff)
            b_sig = b_sigma if b_sigma is not None else np.zeros_like(diff)
            result_sigma = np.sqrt(a_sig**2 + b_sig**2)
        
        # Combine quality flags with OR
        result_flags = None
        if a_flags is not None or b_flags is not None:
            a_flg = a_flags if a_flags is not None else np.zeros(len(diff), dtype=np.uint8)
            b_flg = b_flags if b_flags is not None else np.zeros(len(diff), dtype=np.uint8)
            result_flags = a_flg | b_flg

        metadata: Dict[str, Any] = {
            'operation': {
                'name': 'subtract',
                'parameters': {
                    'epsilon': self.epsilon,
                    'wavelength_range': [float(np.nanmin(x_canon)), float(np.nanmax(x_canon))],
                    'points': int(x_canon.size),
                },
                'parents': [a.id, b.id],
            },
            'primary_metadata': dict(a.metadata),
            'secondary_metadata': dict(b.metadata),
        }
        result_x, result_y, _ = self.units_service.convert_arrays(
            x_canon,
            diff,
            'nm',
            'absorbance',
            a.x_unit,
            a.y_unit,
        )
        
        # Convert uncertainty back to output units if present
        result_sigma_converted = None
        if result_sigma is not None:
            _, result_sigma_converted, _ = self.units_service.convert_arrays(
                x_canon,
                result_sigma,
                'nm',
                'absorbance',
                a.x_unit,
                a.y_unit,
            )
        
        spectrum = Spectrum.create(
            name=f"{a.name} - {b.name}",
            x=result_x,
            y=result_y,
            x_unit=a.x_unit,
            y_unit=a.y_unit,
            metadata=metadata,
            uncertainty=result_sigma_converted,
            quality_flags=result_flags,
        )
        return spectrum, {'status': 'ok', 'operation': 'subtract', 'result_id': spectrum.id}

    def ratio(self, a: Spectrum, b: Spectrum) -> Tuple[Spectrum, Dict[str, object]]:
        """Compute ``a / b`` with epsilon protection and uncertainty propagation.
        
        Propagates uncertainties as: σ_ratio = |a/b| * √((σ_a/a)² + (σ_b/b)²)
        Combines quality flags with bitwise OR.
        """
        x_canon, a_canon_y, b_canon_y = self._aligned_canonical(a, b)
        a_sigma, b_sigma = self._aligned_uncertainties(a, b, x_canon)
        a_flags, b_flags = self._aligned_quality_flags(a, b, x_canon)
        denom = b_canon_y.copy()
        mask = np.abs(denom) < self.epsilon
        denom[mask] = np.nan  # mark invalid points
        values = np.divide(a_canon_y, denom)
        
        # Propagate uncertainty: σ_ratio = |a/b| * √((σ_a/a)² + (σ_b/b)²)
        result_sigma = None
        if a_sigma is not None or b_sigma is not None:
            a_sig = a_sigma if a_sigma is not None else np.zeros_like(values)
            b_sig = b_sigma if b_sigma is not None else np.zeros_like(values)
            
            # Avoid division by zero in uncertainty calculation
            with np.errstate(divide='ignore', invalid='ignore'):
                rel_a = np.divide(a_sig, np.abs(a_canon_y), where=np.abs(a_canon_y) > self.epsilon)
                rel_b = np.divide(b_sig, np.abs(b_canon_y), where=np.abs(b_canon_y) > self.epsilon)
                result_sigma = np.abs(values) * np.sqrt(rel_a**2 + rel_b**2)
                result_sigma[mask] = np.nan  # Mark as invalid where denominator was near-zero
        
        # Combine quality flags with OR
        result_flags = None
        if a_flags is not None or b_flags is not None:
            a_flg = a_flags if a_flags is not None else np.zeros(len(values), dtype=np.uint8)
            b_flg = b_flags if b_flags is not None else np.zeros(len(values), dtype=np.uint8)
            result_flags = a_flg | b_flg
        
        metadata: Dict[str, Any] = {
            'operation': {
                'name': 'ratio',
                'parameters': {
                    'epsilon': self.epsilon,
                    'masked_points': int(mask.sum()),
                    'wavelength_range': [float(np.nanmin(x_canon)), float(np.nanmax(x_canon))],
                    'points': int(x_canon.size),
                },
                'parents': [a.id, b.id],
            },
            'primary_metadata': dict(a.metadata),
            'secondary_metadata': dict(b.metadata),
        }
        result_x, result_y, conversion_meta = self.units_service.convert_arrays(
            x_canon,
            values,
            'nm',
            'absorbance',
            a.x_unit,
            a.y_unit,
        )
        if conversion_meta:
            metadata['unit_conversions'] = dict(conversion_meta)
        
        # Convert uncertainty back to output units if present
        result_sigma_converted = None
        if result_sigma is not None:
            _, result_sigma_converted, _ = self.units_service.convert_arrays(
                x_canon,
                result_sigma,
                'nm',
                'absorbance',
                a.x_unit,
                a.y_unit,
            )
        
        spectrum = Spectrum.create(
            name=f"{a.name} / {b.name}",
            x=result_x,
            y=result_y,
            x_unit=a.x_unit,
            y_unit=a.y_unit,
            metadata=metadata,
            uncertainty=result_sigma_converted,
            quality_flags=result_flags,
        )
        return spectrum, {
            'status': 'ok',
            'operation': 'ratio',
            'result_id': spectrum.id,
            'masked_points': int(mask.sum()),
        }

    def normalized_difference(self, a: Spectrum, b: Spectrum) -> Tuple[Spectrum | None, Dict[str, object]]:
        """Compute the normalized difference (A - B) / (A + B).

        Suppresses trivial all-zero ND across valid points. Propagates uncertainties using a
        conservative relative-uncertainty combination:
            σ_nd ≈ |ND| * sqrt( (σ_a/|a|)² + (σ_b/|b|)² ), with safeguards.

        Returns None if the computed ND is trivial (all zeros within tolerance) or if there are
        no valid (non-masked) points due to a nearly-zero denominator.
        """
        x_canon, a_canon_y, b_canon_y = self._aligned_canonical(a, b)
        a_sigma, b_sigma = self._aligned_uncertainties(a, b, x_canon)
        a_flags, b_flags = self._aligned_quality_flags(a, b, x_canon)

        num = a_canon_y - b_canon_y
        denom = a_canon_y + b_canon_y
        with np.errstate(divide='ignore', invalid='ignore'):
            denom_mask = np.abs(denom) < self.epsilon
            denom_safe = denom.copy()
            denom_safe[denom_mask] = np.nan
            nd = np.divide(num, denom_safe)

        # Determine valid points (where denominator wasn't too small)
        valid_mask = ~denom_mask & ~np.isnan(nd)
        if not np.any(valid_mask):
            return None, {
                'status': 'no_valid_points',
                'operation': 'normalized_difference',
                'message': 'All points masked due to near-zero denominator; no valid ND to compute.',
                'parents': [a.id, b.id],
            }
        # Suppress trivial case where ND is ~0 across all valid points (e.g., a == b)
        if np.allclose(nd[valid_mask], 0.0, atol=self.epsilon):
            return None, {
                'status': 'suppressed_trivial',
                'operation': 'normalized_difference',
                'message': 'Normalized difference is zero across valid range; result suppressed.',
                'parents': [a.id, b.id],
            }

        # Propagate uncertainty (simplified): treat nd = f(a,b); approximate via relative uncertainties
        result_sigma = None
        if a_sigma is not None or b_sigma is not None:
            a_sig = a_sigma if a_sigma is not None else np.zeros_like(nd)
            b_sig = b_sigma if b_sigma is not None else np.zeros_like(nd)
            with np.errstate(divide='ignore', invalid='ignore'):
                rel_a = np.divide(a_sig, np.abs(a_canon_y), where=np.abs(a_canon_y) > self.epsilon)
                rel_b = np.divide(b_sig, np.abs(b_canon_y), where=np.abs(b_canon_y) > self.epsilon)
                # Heuristic: scaled combination of relative uncertainties
                result_sigma = np.abs(nd) * np.sqrt(rel_a**2 + rel_b**2)
            if result_sigma is not None:
                result_sigma[denom_mask] = np.nan

        result_flags = None
        if a_flags is not None or b_flags is not None:
            a_flg = a_flags if a_flags is not None else np.zeros(len(nd), dtype=np.uint8)
            b_flg = b_flags if b_flags is not None else np.zeros(len(nd), dtype=np.uint8)
            result_flags = a_flg | b_flg

        metadata: Dict[str, Any] = {
            'operation': {
                'name': 'normalized_difference',
                'parameters': {
                    'epsilon': self.epsilon,
                    'masked_points': int(denom_mask.sum()),
                    'wavelength_range': [float(np.nanmin(x_canon)), float(np.nanmax(x_canon))],
                    'points': int(x_canon.size),
                },
                'parents': [a.id, b.id],
            },
            'primary_metadata': dict(a.metadata),
            'secondary_metadata': dict(b.metadata),
        }
        result_x, result_y, _ = self.units_service.convert_arrays(
            x_canon,
            nd,
            'nm',
            'absorbance',
            a.x_unit,
            a.y_unit,
        )

        result_sigma_converted = None
        if result_sigma is not None:
            _, result_sigma_converted, _ = self.units_service.convert_arrays(
                x_canon,
                result_sigma,
                'nm',
                'absorbance',
                a.x_unit,
                a.y_unit,
            )

        spectrum = Spectrum.create(
            name=f"ND({a.name}, {b.name})",
            x=result_x,
            y=result_y,
            x_unit=a.x_unit,
            y_unit=a.y_unit,
            metadata=metadata,
            uncertainty=result_sigma_converted,
            quality_flags=result_flags,
        )
        return spectrum, {
            'status': 'ok',
            'operation': 'normalized_difference',
            'result_id': spectrum.id,
            'masked_points': int(denom_mask.sum()),
        }

    def _aligned_canonical(self, a: Spectrum, b: Spectrum) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Align two spectra to a common wavelength grid via interpolation.
        
        Returns:
            Tuple of (common_x_nm, a_y_interp, b_y_interp) in canonical units
            
        Raises:
            ValueError: If spectra have no overlap or insufficient data points
            Warning: If interpolation involves large gaps (>10% of median spacing)
        """
        ax, ay, _ = self.units_service.to_canonical(a.x, a.y, a.x_unit, a.y_unit)
        bx, by, _ = self.units_service.to_canonical(b.x, b.y, b.x_unit, b.y_unit)
        
        # If grids already match, no interpolation needed
        if ax.shape == bx.shape and np.allclose(ax, bx, atol=self.epsilon):
            return ax, ay, by
        
        # Find overlapping range
        min_wl = max(float(np.nanmin(ax)), float(np.nanmin(bx)))
        max_wl = min(float(np.nanmax(ax)), float(np.nanmax(bx)))
        
        if min_wl >= max_wl:
            raise ValueError('Spectra have no overlapping wavelength range')
        
        # Use the finer grid as target (smaller median spacing)
        ax_mask = (ax >= min_wl) & (ax <= max_wl)
        bx_mask = (bx >= min_wl) & (bx <= max_wl)
        
        ax_range = ax[ax_mask]
        bx_range = bx[bx_mask]
        
        if ax_range.size < 2 or bx_range.size < 2:
            raise ValueError('Insufficient data points in overlapping range')
        
        ax_spacing = np.median(np.diff(ax_range)) if ax_range.size > 1 else float('inf')
        bx_spacing = np.median(np.diff(bx_range)) if bx_range.size > 1 else float('inf')
        
        # Validate interpolation quality
        self._validate_interpolation_gaps(ax, bx, min_wl, max_wl, a.name, b.name)
        
        # Use finer grid as target
        if ax_spacing < bx_spacing:
            target_x = ax_range
            ay_interp = ay[ax_mask]
            by_interp = np.interp(target_x, bx, by)
        else:
            target_x = bx_range
            ay_interp = np.interp(target_x, ax, ay)
            by_interp = by[bx_mask]
        
        return target_x, ay_interp, by_interp

    def _validate_interpolation_gaps(
        self, ax: np.ndarray, bx: np.ndarray, min_wl: float, max_wl: float, name_a: str, name_b: str
    ) -> None:
        """Check for large gaps that may cause poor interpolation quality.
        
        Issues a warning if gaps exceed 10% of the median spacing.
        """
        import warnings
        
        # Check for large gaps in the overlapping region
        ax_overlap = ax[(ax >= min_wl) & (ax <= max_wl)]
        bx_overlap = bx[(bx >= min_wl) & (bx <= max_wl)]
        
        if ax_overlap.size > 1:
            ax_diffs = np.diff(ax_overlap)
            ax_median_spacing = np.median(ax_diffs)
            ax_max_gap = np.max(ax_diffs)
            
            if ax_max_gap > 1.5 * ax_median_spacing:
                warnings.warn(
                    f"Large gap detected in '{name_a}': {ax_max_gap:.2f}nm "
                    f"(>1.5x median spacing of {ax_median_spacing:.2f}nm). "
                    f"Interpolation accuracy may be reduced.",
                    UserWarning,
                    stacklevel=3,
                )
        
        if bx_overlap.size > 1:
            bx_diffs = np.diff(bx_overlap)
            bx_median_spacing = np.median(bx_diffs)
            bx_max_gap = np.max(bx_diffs)
            
            if bx_max_gap > 1.5 * bx_median_spacing:
                warnings.warn(
                    f"Large gap detected in '{name_b}': {bx_max_gap:.2f}nm "
                    f"(>1.5x median spacing of {bx_median_spacing:.2f}nm). "
                    f"Interpolation accuracy may be reduced.",
                    UserWarning,
                    stacklevel=3,
                )

    def _aligned_uncertainties(
        self, a: Spectrum, b: Spectrum, target_x: np.ndarray
    ) -> Tuple[np.ndarray | None, np.ndarray | None]:
        """Align uncertainties from two spectra to common wavelength grid.
        
        Args:
            a: First spectrum
            b: Second spectrum
            target_x: Target wavelength array in canonical units (nm)
            
        Returns:
            Tuple of (a_sigma_interp, b_sigma_interp) or (None, None) if neither has uncertainty
        """
        ax, _, _ = self.units_service.to_canonical(a.x, a.y, a.x_unit, a.y_unit)
        bx, _, _ = self.units_service.to_canonical(b.x, b.y, b.x_unit, b.y_unit)
        
        a_sigma_interp = None
        if a.uncertainty is not None:
            a_sigma_interp = np.interp(target_x, ax, a.uncertainty)
        
        b_sigma_interp = None
        if b.uncertainty is not None:
            b_sigma_interp = np.interp(target_x, bx, b.uncertainty)
        
        return a_sigma_interp, b_sigma_interp

    def _aligned_quality_flags(
        self, a: Spectrum, b: Spectrum, target_x: np.ndarray
    ) -> Tuple[np.ndarray | None, np.ndarray | None]:
        """Align quality flags from two spectra to common wavelength grid.
        
        Uses nearest-neighbor interpolation for flags (no averaging).
        
        Args:
            a: First spectrum
            b: Second spectrum
            target_x: Target wavelength array in canonical units (nm)
            
        Returns:
            Tuple of (a_flags_interp, b_flags_interp) or (None, None) if neither has flags
        """
        ax, _, _ = self.units_service.to_canonical(a.x, a.y, a.x_unit, a.y_unit)
        bx, _, _ = self.units_service.to_canonical(b.x, b.y, b.x_unit, b.y_unit)
        
        a_flags_interp = None
        if a.quality_flags is not None:
            # Nearest-neighbor for discrete flags
            indices_a = np.searchsorted(ax, target_x)
            indices_a = np.clip(indices_a, 0, len(ax) - 1)
            a_flags_interp = a.quality_flags[indices_a]
        
        b_flags_interp = None
        if b.quality_flags is not None:
            indices_b = np.searchsorted(bx, target_x)
            indices_b = np.clip(indices_b, 0, len(bx) - 1)
            b_flags_interp = b.quality_flags[indices_b]
        
        return a_flags_interp, b_flags_interp

    def average(self, spectra: List[Spectrum], name: str | None = None) -> Tuple[Spectrum, Dict[str, object]]:
        """Compute average of multiple spectra by interpolating to common wavelength grid.
        
        Args:
            spectra: List of spectra to average
            name: Optional name for the result (defaults to "Average of N spectra")
            
        Returns:
            Tuple of (averaged spectrum, operation metadata)
        """
        if not spectra:
            raise ValueError('Cannot average empty list of spectra')

        if len(spectra) == 1:
            spec = spectra[0]
            result_name = name or f"Copy of {spec.name}"
            metadata: Dict[str, Any] = {
                'operation': {
                    'name': 'average',
                    'parameters': {'count': 1},
                    'parents': [spec.id],
                },
                'primary_metadata': dict(spec.metadata),
            }
            result = Spectrum.create(
                name=result_name,
                x=spec.x.copy(),
                y=spec.y.copy(),
                x_unit=spec.x_unit,
                y_unit=spec.y_unit,
                metadata=metadata,
            )
            return result, {'status': 'ok', 'operation': 'average', 'result_id': result.id, 'count': 1}

        canonical_sets: List[Tuple[Spectrum, np.ndarray, np.ndarray]] = []
        for spec in spectra:
            x_canon, y_canon, _ = self.units_service.to_canonical(spec.x, spec.y, spec.x_unit, spec.y_unit)
            canonical_sets.append((spec, x_canon, y_canon))

        min_wl = max(arr.min() for _, arr, _ in canonical_sets)
        max_wl = min(arr.max() for _, arr, _ in canonical_sets)

        if min_wl >= max_wl:
            raise ValueError('Spectra have no overlapping wavelength range')

        target_x = None
        min_spacing = float('inf')

        for spec, x_canon, _ in canonical_sets:
            mask = (x_canon >= min_wl) & (x_canon <= max_wl)
            x_range = x_canon[mask]
            if x_range.size > 1:
                spacing = np.median(np.diff(x_range))
                if spacing < min_spacing:
                    min_spacing = spacing
                    target_x = x_range

        if target_x is None or target_x.size < 2:
            raise ValueError('Insufficient data in overlapping range')

        interpolated_y: List[np.ndarray] = []
        interpolated_sigma: List[np.ndarray] = []
        all_flags: List[np.ndarray] = []
        
        for spec, x_canon, y_canon in canonical_sets:
            mask = (x_canon >= min_wl) & (x_canon <= max_wl)
            interpolated_y.append(np.interp(target_x, x_canon[mask], y_canon[mask]))
            
            # Interpolate uncertainty if present
            if spec.uncertainty is not None:
                sigma_interp = np.interp(target_x, x_canon[mask], spec.uncertainty[mask])
                interpolated_sigma.append(sigma_interp)
            
            # Align quality flags with nearest-neighbor
            if spec.quality_flags is not None:
                indices = np.searchsorted(x_canon[mask], target_x)
                indices = np.clip(indices, 0, mask.sum() - 1)
                all_flags.append(spec.quality_flags[mask][indices])

        y_avg = np.mean(interpolated_y, axis=0)
        
        # Propagate uncertainty: σ_avg = σ_individual / √N (assuming independent measurements)
        result_sigma = None
        if interpolated_sigma:
            # Average of uncertainties divided by √N
            sigma_combined = np.mean(interpolated_sigma, axis=0)
            result_sigma = sigma_combined / np.sqrt(len(spectra))
        
        # Combine quality flags with OR across all spectra
        result_flags = None
        if all_flags:
            result_flags = np.zeros(len(target_x), dtype=np.uint8)
            for flags in all_flags:
                result_flags |= flags

        result_name = name or f"Average of {len(spectra)} spectra"
        parent_ids = [spec.id for spec in spectra]
        metadata: Dict[str, Any] = {
            'operation': {
                'name': 'average',
                'parameters': {
                    'count': len(spectra),
                    'wavelength_range': [float(min_wl), float(max_wl)],
                    'points': int(target_x.size),
                },
                'parents': parent_ids,
            },
            'source_spectra': [{'id': spec.id, 'name': spec.name} for spec in spectra],
        }

        baseline = spectra[0]
        result_x, result_y, conversion_meta = self.units_service.convert_arrays(
            target_x,
            y_avg,
            'nm',
            'absorbance',
            baseline.x_unit,
            baseline.y_unit,
        )
        if conversion_meta:
            metadata['unit_conversions'] = dict(conversion_meta)

        # Convert uncertainty back to output units if present
        result_sigma_converted = None
        if result_sigma is not None:
            _, result_sigma_converted, _ = self.units_service.convert_arrays(
                target_x,
                result_sigma,
                'nm',
                'absorbance',
                baseline.x_unit,
                baseline.y_unit,
            )

        result = Spectrum.create(
            name=result_name,
            x=result_x,
            y=result_y,
            x_unit=baseline.x_unit,
            y_unit=baseline.y_unit,
            metadata=metadata,
            uncertainty=result_sigma_converted,
            quality_flags=result_flags,
        )

        return result, {
            'status': 'ok',
            'operation': 'average',
            'result_id': result.id,
            'count': len(spectra),
            'wavelength_range': [float(min_wl), float(max_wl)],
        }
