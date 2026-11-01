"""Rectangular 3D viewport with equal screen scale in both directions."""

import numpy as np
from mpl_toolkits.mplot3d.axes3d import Axes3D
from matplotlib.projections import register_projection


class BlochAxes3D(Axes3D):
    name = "entrela_bloch"

    def apply_aspect(self, position=None):
        # Axes3D normally shrinks this rectangle to a centered square.
        # Keep the whole viewport; compensate in the projection, not geometry.
        if position is None:
            position = self.get_position(original=True)
        self._set_position(position, "active")

    def get_proj(self):
        matrix = super().get_proj()
        width, height = self.bbox.width, self.bbox.height
        if width > 0 and height > 0:
            correction = np.diag(
                [min(1.0, height / width), min(1.0, width / height), 1.0, 1.0]
            )
            matrix = correction @ matrix
        return matrix


register_projection(BlochAxes3D)
